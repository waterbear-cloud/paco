"""
CloudFormation template for CloudWatch Log Groups
"""

from paco.cftemplates.cftemplates import StackTemplate
from paco.models import references, schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference
from paco.utils import prefixed_name
import troposphere
import troposphere.logs


class LogGroups(StackTemplate):
    """
    CloudFormation template for CloudWatch Log Groups
    """
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('LogGroups', self.resource_group_name, self.resource_name)

        # Troposphere Template Initialization
        self.init_template('LogGroups')
        template = self.template

        # CloudWatch Agent logging
        cw_logging = get_parent_by_interface(stack.resource, schemas.IProject)['cw_logging']
        default_retention = cw_logging.expire_events_after_days
        if schemas.IRDSAurora.providedBy(stack.resource):
            monitoring = stack.resource.default_instance.monitoring
        else:
            monitoring = stack.resource.monitoring
        for log_group in monitoring.log_sets.get_all_log_groups():
            cfn_export_dict = {}
            log_group_name = log_group.get_full_log_group_name()
            if log_group.external_resource == False:
                prefixed_log_group_name = prefixed_name(stack.resource, log_group_name, self.paco_ctx.legacy_flag)
            else:
                prefixed_log_group_name = log_group_name
            loggroup_logical_id = self.create_cfn_logical_id('LogGroup' + log_group_name)

            # provide prefixed LogGroup name as a CFN Parameter
            param_name = 'Name' + loggroup_logical_id
            log_group_name_parameter = self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='LogGroup name',
                value=prefixed_log_group_name,
            )
            cfn_export_dict['LogGroupName'] = troposphere.Ref(log_group_name_parameter)

            # override default retention?
            # 1. log_group.expire_events_after_days <- specific to single log group
            # 2. log_set.expire_events_after_days <- applies to an entire log set
            # 3. cw_logging.expire_events_after_days <- global default
            log_set = get_parent_by_interface(log_group, schemas.ICloudWatchLogSet)
            if hasattr(log_set, 'expire_events_after_days') and log_group.expire_events_after_days:
                retention = log_group.expire_events_after_days
            elif hasattr(log_set, 'expire_events_after_days') and log_set.expire_events_after_days:
                retention = log_set.expire_events_after_days
            else:
                retention = default_retention
            if retention != 'Never':
                cfn_export_dict["RetentionInDays"] = retention

            # Avoid creating loggroup if it already exists as an external resource
            if log_group.external_resource == False:
                log_group_resource = troposphere.logs.LogGroup.from_dict(
                    loggroup_logical_id,
                    cfn_export_dict
                )
                template.add_resource(log_group_resource)

            # Metric Filters
            for metric_filter in log_group.metric_filters.values():
                mf_dict = {
                    'LogGroupName': troposphere.Ref(log_group_name_parameter),
                    'FilterPattern': metric_filter.filter_pattern,
                }
                mt_list = []
                for transf in metric_filter.metric_transformations:
                    # If MetricNamespace is not set, use a dynamic 'Paco/{log-group-name}' namespace
                    if transf.metric_namespace:
                        namespace = transf.metric_namespace
                    else:
                        namespace = 'Paco/' + prefixed_log_group_name
                    mts_dict = {
                        'MetricName': transf.metric_name,
                        'MetricNamespace': namespace,
                        'MetricValue': transf.metric_value
                    }
                    if isinstance(transf.default_value, float):
                        mts_dict['DefaultValue'] = transf.default_value
                    mt_list.append(mts_dict)
                mf_dict['MetricTransformations'] = mt_list
                metric_filter_resource = troposphere.logs.MetricFilter.from_dict(
                    self.create_cfn_logical_id('MetricFilter' + metric_filter.name),
                    mf_dict,
                )
                if log_group.external_resource == False:
                    metric_filter_resource.DependsOn = log_group_resource
                template.add_resource(metric_filter_resource)

        # SSM Agent logging
        if schemas.IASG.providedBy(stack.resource):
            if stack.resource.launch_options.ssm_agent:
                loggroup_logical_id = 'SSMLogGroup'
                cfn_export_dict = {}
                # LogGroup name is prefixed as a CFN Parameter
                # ToDo: make paco_ssm a reserved word?
                prefixed_log_group_name = prefixed_name(stack.resource, 'paco_ssm', self.paco_ctx.legacy_flag)
                param_name = 'Name' + loggroup_logical_id
                log_group_name_parameter = self.create_cfn_parameter(
                    param_type='String',
                    name=param_name,
                    description='SSM LogGroup name',
                    value=prefixed_log_group_name,
                )
                cfn_export_dict['LogGroupName'] = troposphere.Ref(log_group_name_parameter)
                retention = stack.resource.launch_options.ssm_expire_events_after_days
                if retention != 'Never':
                    cfn_export_dict["RetentionInDays"] = retention
                log_group_resource = troposphere.logs.LogGroup.from_dict(
                    loggroup_logical_id,
                    cfn_export_dict
                )
                template.add_resource(log_group_resource)
