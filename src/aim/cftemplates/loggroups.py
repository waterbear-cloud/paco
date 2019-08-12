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
            aws_name=aws_name
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
            'expire_events_after': None,
        }
        log_groups_yaml = ""
        cw_log_groups = get_parent_by_interface(resource, schemas.IProject)['cloudwatch_log_groups']
        default_retention = cw_log_groups.expire_events_after
        for log_source in self.resource.monitoring.log_sets.get_all_log_sources():
            loggroup_table['name'] = self.normalize_resource_name(log_source.name)
            loggroup_table['properties'] = "Properties:\n"
            loggroup_table['log_group_name'] = "      LogGroupName: '{}'".format(prefixed_name(resource, log_source.log_group_name))

            # override default retention?
            # 1. log_source.expire_events_after <- specific to single log group
            # 2. log_category.expire_events_after <- applies to an entire log_category
            # 3. log_groups.expire_events_after <- global default
            override_retention = None
            log_category = log_source.__parent__.name
            if log_source.expire_events_after:
                retention = log_source.expire_events_after
            elif log_category in cw_log_groups.log_category:
                retention = cw_log_groups.log_category[log_category].expire_events_after
            else:
                retention = default_retention
            if retention == 'Never':
                loggroup_table['retention'] = ''
            else:
                loggroup_table['retention'] = "      RetentionInDays: '{}'".format(retention)

            log_groups_yaml += log_group_fmt.format(loggroup_table)

        template_table['log_groups'] = log_groups_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        super().validate()

