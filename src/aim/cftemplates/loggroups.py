"""
CloudFormation template for CloudWatch Log Groups
"""

from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references, schemas
from aim.models.locations import get_parent_by_interface
from aim.models.references import Reference
from aim.utils import prefixed_name
import troposphere
import troposphere.logs


class LogGroups(CFTemplate):
    """
    CloudFormation template for CloudWatch Log Groups
    """
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        group_name,
        resource,
        res_config_ref
    ):
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=res_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('LogGroups', group_name, resource.name)
        self.resource = resource

        # Troposphere Template Initialization
        template = troposphere.Template(
            Description = 'LogGroups',
        )
        template.set_version()
        template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        cw_logging = get_parent_by_interface(resource, schemas.IProject)['cw_logging']
        default_retention = cw_logging.expire_events_after_days
        for log_group in self.resource.monitoring.log_sets.get_all_log_groups():
            cfn_export_dict = {}
            log_group_name = log_group.get_log_group_name()
            loggroup_logical_id = self.create_cfn_logical_id('LogGroup' + log_group_name)

            # provide prefixed LogGroup name as a CFN Parameter
            param_name = 'Name' + loggroup_logical_id
            parameter = self.create_cfn_parameter(
                param_type = 'String',
                name = param_name,
                description = 'LogGroup name',
                value = prefixed_name(resource, log_group_name, self.aim_ctx.legacy_flag),
                use_troposphere = True
            )
            template.add_parameter(parameter)
            cfn_export_dict['LogGroupName'] = troposphere.Ref(param_name)

            # override default retention?
            # 1. log_group.expire_events_after_days <- specific to single log group
            # 2. log_set.expire_events_after_days <- applies to an entire log set
            # 3. cw_logging.expire_events_after_days <- global default
            log_set = get_parent_by_interface(log_group, schemas.ICloudWatchLogSet)
            if log_group.expire_events_after_days:
                retention = log_group.expire_events_after_days
            elif log_set.expire_events_after_days:
                retention = log_set.expire_events_after_days
            else:
                retention = default_retention
            if retention != 'Never':
                cfn_export_dict["RetentionInDays"] = retention

            log_group_resource = troposphere.logs.LogGroup.from_dict(
                loggroup_logical_id,
                cfn_export_dict
            )
            template.add_resource(log_group_resource)

        # Generate the Template
        self.set_template(template.to_yaml())
