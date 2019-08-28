"""
CloudFormation template for CloudWatch Log Groups
"""

from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references, schemas
from aim.models.locations import get_parent_by_interface
from aim.models.references import Reference
from aim.utils import prefixed_name

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
        aws_name,
        resource,
        res_config_ref
    ):
        aws_name='-'.join([aws_name, 'LogGroups'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=res_config_ref,
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.resource = resource

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch Log Groups'

Resources:

{0[log_groups]:s}
"""
        template_table = {
          'log_groups': ""
        }
        log_group_fmt = """
  LogGroup{0[name]:s}:
    Type: AWS::Logs::LogGroup
    Properties:
{0[log_group_name]:s}
{0[retention]:s}\n"""
        loggroup_table = {
            'name': None,
            'expire_events_after_days': None,
        }
        log_groups_yaml = ""

        cw_logging = get_parent_by_interface(resource, schemas.IProject)['cw_logging']
        default_retention = cw_logging.expire_events_after_days
        for log_group in self.resource.monitoring.log_sets.get_all_log_groups():
            log_group_name = log_group.get_log_group_name()
            loggroup_table['name'] = self.create_cfn_logical_id(log_group_name)
            loggroup_table['properties'] = "Properties:\n"
            loggroup_table['log_group_name'] = "      LogGroupName: '{}'".format(prefixed_name(resource, log_group_name))

            # override default retention?
            # 1. log_group.expire_events_after_days <- specific to single log group
            # 2. log_set.expire_events_after_days <- applies to an entire log set
            # 3. cw_logging.expire_events_after_days <- global default
            override_retention = None
            log_set = get_parent_by_interface(log_group, schemas.ICloudWatchLogSet)
            if log_group.expire_events_after_days:
                retention = log_group.expire_events_after_days
            elif log_set.expire_events_after_days:
                retention = log_set.expire_events_after_days
            else:
                retention = default_retention
            if retention == 'Never':
                loggroup_table['retention'] = ''
            else:
                loggroup_table['retention'] = "      RetentionInDays: '{}'".format(retention)

            log_groups_yaml += log_group_fmt.format(loggroup_table)

        template_table['log_groups'] = log_groups_yaml
        self.set_template(template_fmt.format(template_table))


