import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco import models


yaml=YAML()
yaml.default_flow_sytle = False

class LambdaResourceEngine(ResourceEngine):

    def init_resource(self):
        # Create function execution role
        role_name = 'iam_role'
        if self.resource.iam_role.enabled == False:
            role_config_yaml = """
instance_profile: false
path: /
role_name: %s""" % ("LambdaFunction")
            role_config_dict = yaml.load(role_config_yaml)
            role_config = models.iam.Role(role_name, self.resource)
            role_config.apply_config(role_config_dict)
        else:
            role_config = self.resource.iam_role

        # Add CloudWatch Logs permissions
        cw_logs_policy = """
name: CloudWatchLogs
statement:
  - effect: Allow
    action:
      - logs:CreateLogGroup
      - logs:CreateLogStream
      - logs:PutLogEvents
    resource:
      - '*'
"""
        role_config.add_policy(yaml.load(cw_logs_policy))

        if self.resource.vpc_config != None:
            vpc_config_policy = """
name: VPCAccess
statement:
  - effect: Allow
    action:
      - ec2:CreateNetworkInterface
      - ec2:DescribeNetworkInterfaces
      - ec2:DeleteNetworkInterface
    resource:
      - '*'
"""
            role_config.add_policy(yaml.load(vpc_config_policy))

        # The ID to give this role is: group.resource.iam_role
        iam_role_ref = self.resource.paco_ref_parts + '.' + role_name
        iam_role_id = self.gen_iam_role_id(self.res_id, role_name)
        # If no assume policy has been added, force one here since we know its
        # a Lambda function using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'aws': ["paco.sub 'arn:aws:iam::${paco.ref accounts.%s}:root'" % (self.account_ctx.get_name())],
                            'service': ['lambda.amazonaws.com'] }
            role_config.set_assume_role_policy(policy_dict)
        # Always turn off instance profiles for Lambda functions
        role_config.instance_profile = False
        role_config.enabled = self.resource.is_enabled()
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            paco_ctx=self.paco_ctx,
            account_ctx=self.account_ctx,
            region=self.aws_region,
            group_id=self.grp_id,
            role_id=iam_role_id,
            role_ref=iam_role_ref,
            role_config=role_config,
            stack_group=self.stack_group,
            template_params=None,
            stack_tags=self.stack_tags
        )
        paco.cftemplates.Lambda(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.paco_ref_parts
        )
