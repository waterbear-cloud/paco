from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.models.references import get_model_obj_from_ref
from paco.stack import StackHooks
from paco.utils import md5sum
from paco.aws_api.ecs.capacityprovider import ECSCapacityProviderClient
import paco.cftemplates
import paco.models


yaml=YAML()
yaml.default_flow_sytle = False

class ASGResourceEngine(ResourceEngine):

    @property
    def stack_name(self):
        name_list = [
            self.app_engine.get_aws_name(),
            self.grp_id,
            self.res_id
        ]

        if self.paco_ctx.legacy_flag('cftemplate_aws_name_2019_09_17') == True:
            name_list.insert(1, 'ASG')
        else:
            name_list.append('ASG')

        stack_name = '-'.join(name_list)

        # The following code duplicates the function in stack.py:BaseStack().create_stack_name()
        # because we need the name of the stack before the stack is created.
        # TODO: Merge this into one function somewhere.
        if stack_name.isalnum():
            return stack_name

        new_name = ""
        for ch in stack_name:
            if ch.isalnum() == False:
                ch = '-'
            new_name += ch

        return new_name

    def init_resource(self):
        # Create instance role
        role_profile_arn = None

        if self.resource.instance_iam_role.enabled == False:
            role_config_yaml = """
instance_profile: false
path: /
role_name: %s""" % ("ASGInstance")
            role_config_dict = yaml.load(role_config_yaml)
            role_config = paco.models.iam.Role('instance_iam_role', self.resource)
            role_config.apply_config(role_config_dict)
        else:
            role_config = self.resource.instance_iam_role

        # The ID to give this role is: group.resource.instance_iam_role
        instance_iam_role_ref = self.resource.paco_ref_parts + '.instance_iam_role'
        instance_iam_role_id = self.gen_iam_role_id(self.res_id, 'instance_iam_role')
        # If no assume policy has been added, force one here since we know its
        # an EC2 instance using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'service': ['ec2.amazonaws.com'] }
            if self.resource.instance_ami_type == 'amazon_ecs':
                policy_dict['service'].append('ecs.amazonaws.com')
            role_config.set_assume_role_policy(policy_dict)
        elif role_config.assume_role_policy.service != None:
            if 'ecs.amazonaws.com' not in role_config.assume_role_policy.service:
                raise AttributeError('ECS Instance Role: AssumeRole: Service must include ecs.amazonaws.com')

        # Always turn on instance profiles for ASG instances
        role_config.instance_profile = True
        role_config.enabled = self.resource.is_enabled()
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=instance_iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
        )
        role_profile_arn = iam_ctl.role_profile_arn(instance_iam_role_ref)

        # EC2 Launch Manger Bundles
        bucket = self.app_engine.ec2_launch_manager.process_bundles(self.resource, instance_iam_role_ref)

        # Create ASG stack
        ec2_manager_user_data_script = self.app_engine.ec2_launch_manager.user_data_script(
            self.resource,
            self.stack_name
        )
        self.ec2lm_cache_id = self.app_engine.ec2_launch_manager.get_cache_id(self.resource)
        self.stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ASG,
            stack_tags=self.stack_tags,
            extra_context={
                'role_profile_arn': role_profile_arn,
                'ec2_manager_user_data_script': ec2_manager_user_data_script,
                'ec2_manager_cache_id': self.ec2lm_cache_id,
            },
        )
        self.stack.hooks.add(
            name='UpdateExistingInstances.' + self.resource.name,
            stack_action='update',
            stack_timing='pre',
            hook_method=self.app_engine.ec2_launch_manager.ec2lm_update_instances_hook,
            cache_method=self.app_engine.ec2_launch_manager.ec2lm_update_instances_cache,
            hook_arg=(bucket.paco_ref_parts, self.resource)
        )
        # For ECS ASGs add an ECS Hook
        if self.resource.ecs != None and self.resource.is_enabled() == True:
            self.stack.hooks.add(
                name='ProvisionECSCapacityProvider.' + self.resource.name,
                stack_action=['create', 'update'],
                stack_timing='post',
                hook_method=self.provision_ecs_capacity_provider,
                cache_method=self.provision_ecs_capacity_provider_cache,
                hook_arg=self.resource
            )

    def get_ec2lm_cache_id(self, hook, hook_arg):
        "EC2LM cache id"
        return self.ec2lm_cache_id

    def provision_ecs_capacity_provider_cache(self, hook, asg):
        "Cache method for ECS ASG"
        cp = asg.ecs.capacity_provider
        return md5sum(str_data=f"{cp.managed_instance_protection}-{asg.paco_ref}-{cp.is_enabled()}-{cp.target_capacity}-{cp.minimum_scaling_step_size}-{cp.maximum_scaling_step_size}")

    def provision_ecs_capacity_provider(self, hook, asg):
        "Hook to add an ECS Capacity Provider to the ECS Cluster the ASG belongs to"
        # create a Capacity Provider
        asg.ecs.capacity_provider.aws_name = asg.ecs.capacity_provider.get_aws_name()
        asg_name = asg.stack.get_outputs_value('ASGName')
        asg_client = self.account_ctx.get_aws_client('autoscaling', self.aws_region)
        response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        asg_arn = response['AutoScalingGroups'][0]['AutoScalingGroupARN']
        capacity_provider_client = ECSCapacityProviderClient(
            self.paco_ctx.project,
            self.account_ctx,
            self.aws_region,
            asg.ecs.capacity_provider,
            asg_arn,
            asg,
        )
        capacity_provider_client.provision()
