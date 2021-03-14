from botocore.config import Config
from botocore.exceptions import ClientError
from paco.models import references
from paco.models.references import get_model_obj_from_ref
from paco.stack.stack import Stack
from paco.utils import md5sum
import re
import time


class ECSCapacityProviderClient():

    def __init__(self, project, account_ctx, aws_region, capacity_provider, asg_arn, asg):
        self.project = project
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.capacity_provider = capacity_provider
        self.asg_arn = asg_arn
        self.asg = asg
        if self.capacity_provider.managed_instance_protection:
            self.managed_instance_protection = 'ENABLED'
        else:
            self.managed_instance_protection = 'DISABLED'

    @property
    def ecs_client(self):
        if hasattr(self, '_ecs_client') == False:
            self._ecs_client = self.account_ctx.get_aws_client('ecs', self.aws_region)
        return self._ecs_client

    @property
    def asg_client(self):
        if hasattr(self, '_asg_client') == False:
            self._asg_client = self.account_ctx.get_aws_client('autoscaling', self.aws_region)
        return self._asg_client

    def provision(self):
        "Provision ECS Capacity Provider resource"
        # get aws info
        response = self.ecs_client.describe_capacity_providers(
            #capacityProviders=[self.capacity_provider.aws_name],
        )
        provider_exists = False
        for cap_info in response['capacityProviders']:
            # Filter out providers that do not belong to the associated ASG
            if 'autoScalingGroupProvider' in cap_info and 'autoScalingGroupArn' in cap_info['autoScalingGroupProvider']:
                if cap_info['autoScalingGroupProvider']['autoScalingGroupArn'] != self.asg_arn:
                    if cap_info['name'] == self.capacity_provider.aws_name:
                        self.delete()
                    continue
            # Keep built-in capacity providers
            if cap_info['name'] in ['FARGATE', 'FARGATE_SPOT']:
                continue
            # Delete if the capacity provider does not exist in Paco config
            if cap_info['name'] != self.capacity_provider.aws_name:
                self.delete(cp_name_to_delete=cap_info['name'])
                continue
            else:
                # delete if exists but is disabled
                if self.capacity_provider.is_enabled() == False:
                    self.delete()
                    continue
                elif cap_info['status'] == 'INACTIVE':
                    self.create()
                elif self.is_changed(cap_info):
                    # update if it's cache is different
                    self.update(cap_info)
                provider_exists = True

        # Create if the provider does not exist
        if self.capacity_provider.is_enabled() == True and provider_exists == False:
            return self.create()

    def is_changed(self, capacity_provider_info):
        local_md5 = md5sum(str_data=f"{self.asg.paco_ref}-{self.capacity_provider.target_capacity}-{self.capacity_provider.minimum_scaling_step_size}-{self.capacity_provider.maximum_scaling_step_size}")
        aws_target_capacity = capacity_provider_info['autoScalingGroupProvider']['managedScaling']['targetCapacity']
        aws_minimum_scaling_step_size = capacity_provider_info['autoScalingGroupProvider']['managedScaling']['minimumScalingStepSize']
        aws_maximum_scaling_step_size = capacity_provider_info['autoScalingGroupProvider']['managedScaling']['maximumScalingStepSize']
        aws_md5 = md5sum(
            str_data=f"{self.managed_instance_protection}-{self.asg.paco_ref}-{aws_target_capacity}-{aws_minimum_scaling_step_size}-{aws_maximum_scaling_step_size}"
        )
        if aws_md5 != local_md5:
            return True
        return False

    def get_cluster_name(self):
        cluster = get_model_obj_from_ref(self.asg.ecs.cluster, self.project)
        return cluster.stack.get_outputs_value('ClusterName')

    def describe_capacity_provider(self, cp_name):
        response = self.ecs_client.describe_capacity_providers(
            capacityProviders=[cp_name],
        )
        return response['capacityProviders'][0]

    def get_existing_capacity_providers(self):
        response = self.ecs_client.describe_capacity_providers()
        capacity_providers = []
        for cp in response['capacityProviders']:
            # check if capacity provider is already associated
            # ToDo: a better way to check this?
            if cp['status'] != 'ACTIVE':
                continue
            # Only include providers assocated with the right ASG
            if 'autoScalingGroupProvider' not in cp:
                continue
            if 'autoScalingGroupArn' not in cp['autoScalingGroupProvider']:
                continue
            if cp['autoScalingGroupProvider']['autoScalingGroupArn'] != self.asg_arn:
                continue

            capacity_providers.append(cp['name'])
        return capacity_providers

    def create(self):
        "Create a new ECS Capacity Provider resource"
        existing_cps = self.get_existing_capacity_providers()
        if self.capacity_provider.aws_name in existing_cps:
            # Wait for Provider to
            while True:
                cap_info = self.describe_capacity_provider(self.capacity_provider.aws_name)
                if cap_info['updateStatus'] != 'DELETE_IN_PROGRESS':
                    print(f"ERROR: Capacity Provider already exists with update status: {cap_info['updateStatus']}")
                    raise
                time.sleep(1)

        response = self.ecs_client.create_capacity_provider(
            name=self.capacity_provider.aws_name,
            autoScalingGroupProvider={
                'autoScalingGroupArn': self.asg_arn,
                'managedScaling': {
                    'status': 'ENABLED',
                    'targetCapacity': self.capacity_provider.target_capacity,
                    'minimumScalingStepSize': self.capacity_provider.minimum_scaling_step_size,
                    'maximumScalingStepSize': self.capacity_provider.maximum_scaling_step_size,
                },
                'managedTerminationProtection': self.managed_instance_protection
            },
        )
        # attach Capacity Provider to the Cluster
        cluster_name = self.get_cluster_name()
        # during create/delete a deleted CP can still list itself as existing
        # ensure that it's only listed once
        if self.capacity_provider.aws_name not in existing_cps:
            existing_cps.append(self.capacity_provider.aws_name)
        self.ecs_client.put_cluster_capacity_providers(
            cluster=cluster_name,
            capacityProviders=existing_cps,
            defaultCapacityProviderStrategy=[],
        )

    def delete(self, cp_name_to_delete=None):
        "Delete ECS Capacity Provider resource"
        self.detach(cp_name_to_delete)
        if cp_name_to_delete == None:
            cp_name_to_delete = self.capacity_provider.aws_name
        response = self.ecs_client.delete_capacity_provider(capacityProvider=cp_name_to_delete)

    def detach(self, cp_name_to_detach):
        "Detach an ECS Capacity Provider from an ASG and Cluster"
        services = self.ecs_client.list_services(cluster=self.get_cluster_name())
        if len(services['serviceArns']) > 0:
            print('ERROR: ECS Capacity Provider config out of sync: All services must be deleted first.')
            raise
        print("!! Detaching Capacity Provider: Do not abort! Please wait...")
        if cp_name_to_detach == None:
            cp_name_to_detach = self.capacity_provider.aws_name
        try:
            response = self.ecs_client.update_capacity_provider(
                name=cp_name_to_detach,
                autoScalingGroupProvider={
                    'managedScaling': {
                        'status': 'DISABLED',
                    },
                    'managedTerminationProtection': 'DISABLED'
                },
            )
        except ClientError as error:
            print('ERROR: Could not update Capacity Provider')
            print(error.response['Error']['Code'])

        # Wait for the capacity provider to finish updating
        while True:
            cap_info = self.describe_capacity_provider(cp_name_to_detach)
            if cap_info['updateStatus'].find('PROGRESS') == -1:
                break
            time.sleep(1)

        # Remove scale-in protection from any ASG EC2 Instances
        asg_name = self.asg_arn.split('/')[1]
        asg_info = self.asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )['AutoScalingGroups'][0]

        protected_instance_ids = []
        for instance_info in asg_info['Instances']:
            if instance_info['ProtectedFromScaleIn'] == True:
                protected_instance_ids.append(instance_info['InstanceId'])
        if len(protected_instance_ids) > 0:
            self.asg_client.set_instance_protection(
                InstanceIds=protected_instance_ids,
                ProtectedFromScalIn=False,
                AutoScalingGroupName=asg_name
            )

        # before you detach the CP from the ASG you need to list
        # ALL other CPs to remain associated
        existing_cps = self.get_existing_capacity_providers()
        new_cps = [cp_name for cp_name in existing_cps if cp_name != cp_name_to_detach]
        #default_provider = []
        #if len(new_cps) == 0:
        #    default_provider=[{'capacityProvider': 'FARGATE', 'weight': 1, 'base': 1}]
        cluster_name = self.get_cluster_name()
        try:
            response = self.ecs_client.put_cluster_capacity_providers(
                cluster=cluster_name,
                capacityProviders=new_cps,
                defaultCapacityProviderStrategy=[],
            )
        except ClientError as error:
            if error.response['Error']['Code'] == 'ResourceInUseException':
                # capacity provider is in-use, do not attempt to delete
                print(f'ERROR: Unable to delete Capacity Provider: ResourceInUse: {cluster_name}')
                print(f'       Try removing the ECS services and try again.')
                return
        print("!! Detaching complete")

    def update(self, capacity_info):
        "Update an ECS Capacity Provider resource"
        # The ASG ARN can change, in which case the API needs to do a delete then create
        if self.asg_arn != capacity_info['autoScalingGroupProvider']['autoScalingGroupArn']:
            self.delete()
            self.create()
        try:
            response = self.ecs_client.update_capacity_provider(
                name=self.capacity_provider.aws_name,
                autoScalingGroupProvider={
                    'managedScaling': {
                        'status': 'ENABLED',
                        'targetCapacity': self.capacity_provider.target_capacity,
                        'minimumScalingStepSize': self.capacity_provider.minimum_scaling_step_size,
                        'maximumScalingStepSize': self.capacity_provider.maximum_scaling_step_size,
                    },
                    'managedTerminationProtection': self.managed_instance_protection
                },
            )
        except ClientError as error:
            print('ERROR: Could not update Capacity Provider')
            print(error.response['Error']['Code'])
