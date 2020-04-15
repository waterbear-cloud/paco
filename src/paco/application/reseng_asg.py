from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.stack import StackHooks
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
        return stack_name

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
            role_config.set_assume_role_policy(policy_dict)
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
        self.app_engine.ec2_launch_manager.process_bundles(self.resource, instance_iam_role_ref)

        # Create ASG stack
        ec2_manager_user_data_script = self.app_engine.ec2_launch_manager.user_data_script(
            self.resource,
            self.stack_name
        )
        self.ec2lm_cache_id = self.app_engine.ec2_launch_manager.get_cache_id(self.resource)
        self.stale_instances = False
        self.stack_tags.add_tag('Paco-EC2LM-CacheId', self.ec2lm_cache_id)
        stack_hooks = StackHooks()
        stack_hooks.add(
            name='EC2LM: Identify stale instances',
            stack_action='update',
            stack_timing='pre',
            hook_method=self.get_previous_ec2lm_cache_id,
            cache_method=self.get_ec2lm_cache_id,
        )
        stack_hooks.add(
            name='EC2LM: Update stale instances',
            stack_action='update',
            stack_timing='post',
            hook_method=self.update_ec2lm_state,
        )
        self.stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ASG,
            stack_tags=self.stack_tags,
            stack_hooks=stack_hooks,
            extra_context={
                'role_profile_arn': role_profile_arn,
                'ec2_manager_user_data_script': ec2_manager_user_data_script,
                'ec2_manager_cache_id': self.ec2lm_cache_id,
            },
        )

    def get_ec2lm_cache_id(self, hook, hook_arg):
        "EC2LM cache id"
        return self.ec2lm_cache_id

    def get_previous_ec2lm_cache_id(self, hook, hook_arg):
        "Detect if EC2 LaunchManager configuration has changed and Tag the ASG"
        # get existing EC2LM cache id from ASG Tag
        old_cache_id = ''
        asg_client = self.account_ctx.get_aws_client('autoscaling', aws_region=self.aws_region)
        for tags in asg_client.get_paginator('describe_tags').paginate(
            Filters=[{
                'Name': 'auto-scaling-group',
                'Values': [ self.resource.get_aws_name() ]
            },],
        ):
            for tag in tags['Tags']:
                if tag['Key'] == 'Paco-EC2LM-CacheId':
                    old_cache_id = tag['Value']

        # ToDo: detect UserData change and then do not mark stale instances?
        if old_cache_id != self.ec2lm_cache_id:
            self.stale_instances = True
            response = asg_client.create_or_update_tags(
                Tags=[{
                    'ResourceId': self.resource.get_aws_name(),
                    'ResourceType': 'auto-scaling-group',
                    'Key': 'Paco-EC2LM-StaleInstances',
                    'Value': 'true',
                    'PropagateAtLaunch': False
                },]
            )

    def update_ec2lm_state(self, hook, hook_arg):
        "Update EC2 LaunchManager state on running AutoScalingGroup instances"
        # check if ASG has stale instances
        # check the ASG Tag in case Paco has been interrupted and is being re-run
        if self.stale_instances != True:
            asg_client = self.account_ctx.get_aws_client('autoscaling', aws_region=self.aws_region)
            for tags in asg_client.get_paginator('describe_tags').paginate(
                Filters=[{
                    'Name': 'auto-scaling-group',
                    'Values': [ self.resource.get_aws_name() ]
                },],
            ):
                for tag in tags['Tags']:
                    if tag['Key'] == 'Paco-EC2LM-StaleInstances':
                        if tag['Value'] == 'true':
                            self.stale_instances == True
        if self.stale_instances:
            # send SSM command
            ssm_client = self.account_ctx.get_aws_client('ssm', aws_region=self.aws_region)
            ssm_client.send_command(
                Targets=[{
                    'Key': 'tag:aws:cloudformation:stack-name',
                    'Values': [self.stack.get_name()]
                },],
                DocumentName='paco_ec2lm_update_instance',
            )

