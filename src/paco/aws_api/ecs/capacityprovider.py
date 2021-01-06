from botocore.config import Config
from botocore.exceptions import ClientError
from paco.models import references
from paco.models.references import get_model_obj_from_ref
from paco.stack.stack import Stack
from paco.utils import md5sum
import re


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

    def provision(self):
        "Provision ECS Capacity Provider resource"
        # get aws info
        response = self.ecs_client.describe_capacity_providers(
            capacityProviders=[self.capacity_provider.aws_name],
        )
        cap_info = response['capacityProviders']

        # delete if exists but is disabled
        if not self.capacity_provider.is_enabled():
            if len(cap_info) > 0:
                return self.delete()
            return

        # create if does not yet exist
        if len(cap_info) == 0:
            return self.create()
        elif cap_info[0]['status'] == 'INACTIVE':
            return self.create()

        # update if it's cache is different
        if self.is_changed(cap_info[0]):
            self.update(cap_info[0])

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

    def get_existing_capacity_providers(self):
        response = self.ecs_client.describe_capacity_providers()
        capacity_providers = []
        for cp in response['capacityProviders']:
            # check if capacity provider is already associated
            # ToDo: a better way to check this?
            if cp['status'] == 'ACTIVE':
                capacity_providers.append(cp['name'])
        return capacity_providers

    def create(self):
        "Create a new ECS Capacity Provider resource"
        existing_cps = self.get_existing_capacity_providers()
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

    def delete(self):
        "Delete ECS Capacity Provider resource"
        # before you can delete, you must disassociate the CP from the ASG
        # to do that you need to list ALL other CPs to remain associated
        existing_cps = self.get_existing_capacity_providers()
        new_cps = [cp_name for cp_name in existing_cps if cp_name != self.capacity_provider.aws_name]
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
                return
        response = self.ecs_client.delete_capacity_provider(capacityProvider=self.capacity_provider.aws_name)

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
