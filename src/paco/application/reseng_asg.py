from paco import models
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.models.references import get_model_obj_from_ref
from paco.stack import StackHooks
from paco.utils import md5sum, prefixed_name
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
        self.windows_log_groups = {
            'Windows-System': '',
            'Windows-Security': ''
        }

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

        self.ec2lm_cache_id = ""
        ec2_manager_user_data_script = None
        if self.resource.instance_ami_type.startswith("windows") == False:
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
        if self.resource.instance_ami_type.startswith("windows") == False:
            # Linux uses EC2LM
            self.stack.hooks.add(
                name='EC2LMUpdateInstances.' + self.resource.name,
                stack_action='update',
                stack_timing='pre',
                hook_method=self.app_engine.ec2_launch_manager.ec2lm_update_instances_hook,
                cache_method=self.app_engine.ec2_launch_manager.ec2lm_update_instances_cache,
                hook_arg=(bucket.paco_ref_parts, self.resource)
            )
        else:
            # Windows uses SSM
            self.update_windows_ssm_agent()
            self.update_windows_cloudwatch_agent()
            self.update_windows_patching()


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
            if self.resource.ecs.capacity_provider and self.resource.ecs.capacity_provider.is_enabled():
                self.resource.ecs.capacity_provider.resolve_ref_obj = self

    def get_ec2lm_cache_id(self, hook, hook_arg):
        "EC2LM cache id"
        return self.ec2lm_cache_id

    def update_windows_patching(self):
        pass

    def asg_hook_update_ssm_agent(self, hook, asg):
        ssm_ctl = self.paco_ctx.get_controller('SSM')
        ssm_ctl.command_update_ssm_agent(asg, self.account_ctx, self.aws_region)

    def update_windows_ssm_agent(self):
        iam_policy_name = '-'.join([self.resource.name, 'ssmagent-policy'])
        ssm_prefixed_name = prefixed_name(self.resource, 'paco_ssm', self.paco_ctx.legacy_flag)
        # allows instance to create a LogGroup with any name - this is a requirement of the SSM Agent
        # if you limit the resource to just the LogGroups names you want SSM to use, the agent will not work
        ssm_log_group_arn = f"arn:aws:logs:{self.aws_region}:{self.account_ctx.id}:log-group:*"
        ssm_log_stream_arn = f"arn:aws:logs:{self.aws_region}:{self.account_ctx.id}:log-group:{ssm_prefixed_name}:log-stream:*"
        policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    action:
      - ssmmessages:CreateControlChannel
      - ssmmessages:CreateDataChannel
      - ssmmessages:OpenControlChannel
      - ssmmessages:OpenDataChannel
      - ec2messages:AcknowledgeMessage
      - ec2messages:DeleteMessage
      - ec2messages:FailMessage
      - ec2messages:GetEndpoint
      - ec2messages:GetMessages
      - ec2messages:SendReply
      - ssm:UpdateInstanceInformation
      - ssm:ListInstanceAssociations
      - ssm:DescribeInstanceProperties
      - ssm:DescribeDocumentParameters
      - ssm:PutInventory
      - ssm:GetDeployablePatchSnapshotForInstance
      - ssm:PutInventory
    resource:
      - '*'
  - effect: Allow
    action:
      - s3:GetEncryptionConfiguration
      - ssm:GetManifest
    resource:
      - '*'
  - effect: Allow
    action:
      - s3:GetObject
    resource:
      - 'arn:aws:s3:::aws-ssm-{self.aws_region}/*'
      - 'arn:aws:s3:::aws-windows-downloads-{self.aws_region}/*'
      - 'arn:aws:s3:::amazon-ssm-{self.aws_region}/*'
      - 'arn:aws:s3:::amazon-ssm-packages-{self.aws_region}/*'
      - 'arn:aws:s3:::{self.aws_region}-birdwatcher-prod/*'
      - 'arn:aws:s3:::patch-baseline-snapshot-{self.aws_region}/*'
  - effect: Allow
    action:
      - logs:CreateLogGroup
      - logs:CreateLogStream
      - logs:DescribeLogGroups
      - logs:DescribeLogStreams
    resource:
      - {ssm_log_group_arn}
  - effect: Allow
    action:
      - logs:PutLogEvents
    resource:
      - {ssm_log_stream_arn}
"""

        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role=self.resource.instance_iam_role,
            resource=self.resource,
            policy_name='policy',
            policy_config_yaml=policy_config_yaml,
            extra_ref_names=['ec2lm','ssmagent'],
        )

        # TODO: Make this work with Linux too
        self.stack.hooks.add(
            name='UpdateSSMAgent.' + self.resource.name,
            stack_action=['create', 'update'],
            stack_timing='post',
            hook_method=self.asg_hook_update_ssm_agent,
            cache_method=None,
            hook_arg=self.resource
        )

    def update_windows_cloudwatch_agent(self):

        iam_policy_name = '-'.join([self.resource.name, 'cloudwatchagent'])
        policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    resource: "*"
    action:
      - "cloudwatch:PutMetricData"
      - "autoscaling:Describe*"
      - "ec2:DescribeTags"
"""
        policy_config_yaml += """      - "logs:CreateLogGroup"\n"""
        log_group_resources = ""
        log_stream_resources = ""
        for log_group_name in self.windows_log_groups.keys():
            lg_name = prefixed_name(self.resource, log_group_name, self.paco_ctx.legacy_flag)
            self.windows_log_groups[log_group_name] = lg_name
            log_group_resources += "      - arn:aws:logs:{}:{}:log-group:{}:*\n".format(
                self.aws_region,
                self.account_ctx.id,
                lg_name,
            )
            log_stream_resources += "      - arn:aws:logs:{}:{}:log-group:{}:log-stream:*\n".format(
                self.aws_region,
                self.account_ctx.id,
                lg_name,
            )
        policy_config_yaml += f"""
  - effect: Allow
    action:
      - "logs:DescribeLogStreams"
      - "logs:DescribeLogGroups"
      - "logs:CreateLogStream"
    resource:
{log_group_resources}
  - effect: Allow
    action:
      - "logs:PutLogEvents"
    resource:
{log_stream_resources}
"""
        policy_name = 'policy_ssm_cloudwatchagent'
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role=self.resource.instance_iam_role,
            resource=self.resource,
            policy_name='policy',
            policy_config_yaml=policy_config_yaml,
            extra_ref_names=['ssm','cloudwatchagent'],
        )

        # TODO: Make this work with Linux too
        self.stack.hooks.add(
            name='UpdateCloudWatchAgent.' + self.resource.name,
            stack_action=['create', 'update'],
            stack_timing='post',
            hook_method=self.asg_hook_update_cloudwatch_agent,
            cache_method=self.asg_hook_update_cloudwatch_agent_cache,
            hook_arg=self.resource
        )

    def gen_windows_cloudwatch_agent_config(self):
        # """Unused Metrics

        #                 "PhysicalDisk": {
        #                         "measurement": [
        #                                 "%% Disk Time",
        #                                 "Disk Write Bytes/sec",
        #                                 "Disk Read Bytes/sec",
        #                                 "Disk Writes/sec",
        #                                 "Disk Reads/sec"
        #                         ],
        #                         "metrics_collection_interval": 60,
        #                         "resources": [
        #                                 "*"
        #                         ]
        #                 },
        #                 "Processor": {
        #                         "measurement": [
        #                                 "%% User Time",
        #                                 "%% Idle Time",
        #                                 "%% Interrupt Time"
        #                         ],
        #                         "metrics_collection_interval": 60,
        #                         "resources": [
        #                                 "*"
        #                         ]
        #                 },
        # """

        cloudwatch_config = """{
        "logs": {
                "logs_collected": {
                        "windows_events": {
                                "collect_list": [
                                        {
                                                "event_format": "xml",
                                                "event_levels": [
                                                        "VERBOSE",
                                                        "INFORMATION",
                                                        "WARNING",
                                                        "ERROR",
                                                        "CRITICAL"
                                                ],
                                                "event_name": "System",
                                                "log_group_name": "%s",
                                                "log_stream_name": "{instance_id}"
                                        },
                                        {
                                                "event_format": "xml",
                                                "event_levels": [
                                                        "VERBOSE",
                                                        "INFORMATION",
                                                        "WARNING",
                                                        "ERROR",
                                                        "CRITICAL"
                                                ],
                                                "event_name": "Security",
                                                "log_group_name": "%s",
                                                "log_stream_name": "{instance_id}"
                                        }
                                ]
                        }
                }
        },
        "metrics": {
                "append_dimensions": {
                        "AutoScalingGroupName": "${aws:AutoScalingGroupName}",
                        "ImageId": "${aws:ImageId}",
                        "InstanceId": "${aws:InstanceId}",
                        "InstanceType": "${aws:InstanceType}"
                },
                "metrics_collected": {
                        "LogicalDisk": {
                                "measurement": [
                                        "%% Free Space"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ]
                        },
                        "Memory": {
                                "measurement": [
                                        "%% Committed Bytes In Use"
                                ],
                                "metrics_collection_interval": 60
                        },
                        "Paging File": {
                                "measurement": [
                                        "%% Usage"
                                ],
                                "metrics_collection_interval": 60,
                                "resources": [
                                        "*"
                                ]
                        },
                        "TCPv4": {
                                "measurement": [
                                        "Connections Established"
                                ],
                                "metrics_collection_interval": 60
                        },
                        "TCPv6": {
                                "measurement": [
                                        "Connections Established"
                                ],
                                "metrics_collection_interval": 60
                        },
                        "statsd": {
                                "metrics_aggregation_interval": 60,
                                "metrics_collection_interval": 60,
                                "service_address": ":8125"
                        }
                }
        }
}""" % (self.windows_log_groups['Windows-System'], self.windows_log_groups['Windows-Security'])
        return cloudwatch_config

    def asg_hook_update_cloudwatch_agent_cache(self, hook, asg):
        "Cache method for ECS ASG"
        cloudwatch_config = self.gen_windows_cloudwatch_agent_config()
        return md5sum(str_data=cloudwatch_config)


    def asg_hook_update_cloudwatch_agent(self, hook, asg):
        ssm_ctl = self.paco_ctx.get_controller('SSM')
        cloudwatch_config = self.gen_windows_cloudwatch_agent_config()
        ssm_ctl.command_update_cloudwatch_agent(asg, self.account_ctx, self.aws_region, cloudwatch_config)


    def provision_ecs_capacity_provider_cache(self, hook, asg):
        "Cache method for ECS ASG"
        cp = asg.ecs.capacity_provider
        return cp.obj_hash()

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

    def resolve_ref(self, ref):
        if isinstance(ref.resource, models.applications.ECSCapacityProvider):
            if ref.resource_ref == 'name':
                return ref.resource.get_aws_name()
        return None
