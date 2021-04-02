from paco import models
from paco.application.res_engine import ResourceEngine
from paco.core import exception
from paco.core.yaml import YAML
from paco.models import vocabulary
import paco.cftemplates


yaml=YAML()
yaml.default_flow_sytle = False

class LambdaResourceEngine(ResourceEngine):

    def init_resource(self):
        # is this for Lambda@Edge?
        edge_enabled = False
        if self.resource.edge != None and self.resource.edge.is_enabled():
            edge_enabled = True

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

        # Note that CloudWatch LogGroup permissions are added in the Lambda stack
        # This is to allow CloudFormation to create the LogGroup to manage it's Retention policy
        # and to prevent the Lambda from being invoked and writing to the LogGroup before it's
        # created by CloudFormation and creating a LogGroup and causing a race condition in the stack.
        # Also, by setting the Policy after the Lambda it's possible to restrict the policy to just
        # the Lambda LogGroups and not leave it wide open like AWSLambdaBasicExecutionRole does.

        if self.resource.vpc_config != None:
            # ToDo: Security: restrict resource
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
        iam_role_id = self.gen_iam_role_id(self.res_id, role_name)
        # If no assume policy has been added, force one here since we know its
        # a Lambda function using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            service = ['lambda.amazonaws.com']
            # allow Edge if it's enabled
            if edge_enabled:
                service.append('edgelambda.amazonaws.com')
            policy_dict = {
                'effect': 'Allow',
                'aws': [f"arn:aws:iam::{self.account_ctx.get_id()}:root"],
                'service': service
            }
            role_config.set_assume_role_policy(policy_dict)
        # Always turn off instance profiles for Lambda functions
        role_config.instance_profile = False
        role_config.enabled = self.resource.is_enabled()
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags
        )

        self.stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.Lambda,
            stack_tags=self.stack_tags
        )

        # Provision Lambda subscriptions in the same region as the SNS Topics
        # This is required for cross account + cross region lambda/sns
        region_topic_list = {}
        for topic in self.resource.sns_topics:
            region_name = topic.split('.')[4]
            if region_name not in vocabulary.aws_regions.keys():
                raise exception.InvalidAWSRegion(f'Invalid SNS Topic region in reference: {region_name}: {topic}')
            if region_name not in region_topic_list.keys():
                region_topic_list[region_name] = []
            region_topic_list[region_name].append(topic)

        for region_name in region_topic_list.keys():
            topic_list = region_topic_list[region_name]
            self.stack = self.stack_group.add_new_stack(
                region_name,
                self.resource,
                paco.cftemplates.LambdaSNSSubscriptions,
                stack_tags=self.stack_tags,
                extra_context={'sns_topic_ref_list': topic_list}
            )