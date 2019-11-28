"""
Initializes and configures the resources for applications by creating
CloudFormation templates, organizing the stacks into groups and configuring supporting resources.
"""

import paco.cftemplates
import os
from paco import models
from paco.application.ec2_launch_manager import EC2LaunchManager
from paco.models import schemas
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.stack_group import StackTags


class ApplicationEngine():
    """An ApplicationEngine initializes and configures applications.
    Applications are logical groupings of AWS Resources designed
    to suport a single workload.
    """

    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        app_id,
        config,
        parent_config_ref,
        stack_group,
        ref_type,
        stack_tags=StackTags(),
        env_ctx=None
    ):
        self.paco_ctx = paco_ctx
        self.config = config
        self.app_id = app_id
        self.parent_config_ref = parent_config_ref
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.stack_group = stack_group
        self.ref_type = ref_type
        self.env_ctx = env_ctx
        self.stack_tags = stack_tags
        self.stack_tags.add_tag( 'Paco-Application-Name', self.app_id )

    def get_aws_name(self):
        return self.stack_group.get_aws_name()

    def init(self):
        """
        Initializes an Application.

        Creates an EC2LaunchManager then iterates through the Application's ResourceGroups
        in order, then each Resource in that group in order, and calls an init specific
        to each Resource type.

        This will allow each Resource for an Application to do what it needs to be initialized,
        typically creating a CFTemplate for the Resource and adding it to the Application's
        StackGroup, and any supporting CFTemplates needed such as Alarms or IAM Policies.
        """
        self.paco_ctx.log_action_col('Init', 'Application', self.app_id, enabled=self.config.is_enabled())
        self.ec2_launch_manager = EC2LaunchManager(
            self.paco_ctx,
            self,
            self.app_id,
            self.account_ctx,
            self.aws_region,
            self.parent_config_ref,
            self.stack_group,
            self.stack_tags
        )

        # Resource Groups
        for grp_id, grp_config in self.config.groups_ordered():
            for res_id, resource in grp_config.resources_ordered():
                # initial resource
                stack_tags = StackTags(self.stack_tags)
                stack_tags.add_tag('Paco-Application-Group-Name', grp_id)
                stack_tags.add_tag('Paco-Application-Resource-Name', res_id)
                resource.resolve_ref_obj = self
                # Create a resource_engine object and initialize it
                resource_engine = getattr(paco.application, resource.type + 'ResourceEngine', None)(
                    self,
                    grp_id,
                    res_id,
                    resource,
                    StackTags(stack_tags),
                )
                resource_engine.log_init_status()
                resource_engine.init_resource()
                resource_engine.init_monitoring()

        self.init_app_monitoring()
        self.paco_ctx.log_action_col('Init', 'Application', self.app_id, 'Completed', enabled=self.config.is_enabled())

    def init_app_monitoring(self):
        "Application level Alarms are not specific to any Resource"
        if getattr(self.config, 'monitoring', None) == None:
            return

        # If health_checks exist, init them
        if getattr(self.config.monitoring, 'health_checks', None) != None and \
            len(self.config.monitoring.health_checks.values()) > 0:
            for health_check in self.config.monitoring.health_checks.values():
                stack_tags = StackTags(self.stack_tags)
                stack_tags.add_tag('Paco-Application-HealthCheck-Name', health_check.name)
                health_check.resolve_ref_obj = self
                # ToDo: enable other types when there is more than one
                if health_check.type == 'Route53HealthCheck':
                    paco.cftemplates.Route53HealthCheck(
                        self.paco_ctx,
                        self.account_ctx,
                        self.aws_region,
                        self.stack_group,
                        stack_tags,
                        health_check
                    )

        # If alarm_sets exist init alarms for them
        if getattr(self.config.monitoring, 'alarm_sets', None) != None and \
            len(self.config.monitoring.alarm_sets.values()) > 0:
            paco.cftemplates.CWAlarms(
                self.paco_ctx,
                self.account_ctx,
                self.aws_region,
                self.stack_group,
                self.stack_tags,
                self.config.monitoring.alarm_sets,
                self.config.paco_ref_parts,
                self.config,
            )

    def gen_iam_role_id(self, res_id, role_id):
        return '-'.join([res_id, role_id])

    def resolve_ref(self, ref):
        if isinstance(ref.resource, models.applications.SNSTopic):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.TargetGroup):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.ASG):
            if ref.resource_ref.startswith('instance_id'):
                asg_stack = self.stack_group.get_stack_from_ref(ref)
                asg_outputs_key = asg_stack.template.get_outputs_key_from_ref(ref)
                if asg_outputs_key == None:
                    raise StackException(
                        PacoErrorCode.Unknown,
                        message="Unable to find outputkey for ref: %s" % ref.raw)
                asg_name = asg_stack.get_outputs_value(asg_outputs_key)
                asg_client = self.account_ctx.get_aws_client('autoscaling')
                asg_response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                instance_id = asg_response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
                ssm_client = self.account_ctx.get_aws_client('ssm')
                ssm_client.start_session(Target=instance_id)
            else:
                return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.Lambda):
            lambda_stack = self.stack_group.get_stack_from_ref(ref)
            return lambda_stack
        elif isinstance(ref.resource, models.applications.CloudFrontViewerCertificate):
            acm_ctl = self.paco_ctx.get_controller('ACM')
            # Force the region to us-east-1 because CloudFront lives there
            ref.sub_part(ref.region, 'us-east-1')
            ref.region = 'us-east-1'
            return acm_ctl.resolve_ref(ref)
        elif isinstance(ref.resource, models.applications.CloudFrontFactory):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.LBApplication):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.EFS):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.EIP):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.RDS):
            return self.stack_group.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.EBS):
            return self.stack_group.get_stack_from_ref(ref)
        elif schemas.IDBParameterGroup.providedBy(ref.resource):
            return self.stack_group.get_stack_from_ref(ref)
        elif schemas.IElastiCache.providedBy(ref.resource):
            return self.stack_group.get_stack_from_ref(ref)
        elif schemas.ICodeDeployApplication.providedBy(ref.resource):
            return self.stack_group.get_stack_from_ref(ref)

        return None
