"""
CloudFormation template for CloudWatch Alarms
"""

from paco import utils
from paco.models import schemas
from paco.models import vocabulary
from paco.cftemplates.cftemplates import StackTemplate
from paco.models.locations import get_parent_by_interface
from paco.models.registry import CW_ALARM_HOOKS
from paco.utils import prefixed_name
from paco.core.exception import InvalidLogSetConfiguration, InvalidAlarmConfiguration
import troposphere


class CFBaseAlarm(StackTemplate):
    "Methods shared by different CFTemplates that can create a CloudWatch Alarm"
    # allow services the chance to send notifications to another region
    notification_region = None

    def create_notification_params(self, alarm):
        "Create a Parameter for each SNS Topic an alarm should notify. Return a list of Refs to those Params."
        notification_paco_refs = []
        for group in alarm.notification_groups:
            if not self.notification_region:
                region = alarm.region_name
            else:
                region = self.notification_region
            notification_paco_refs.append(
                self.paco_ctx.project['resource']['snstopics'][region][group].paco_ref + '.arn'
            )

        notification_cfn_refs = []
        for notification_paco_ref in notification_paco_refs:
            # Create parameter
            param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_paco_ref))
            if param_name in self.notification_param_map.keys():
                notification_param = self.notification_param_map[param_name]
            else:
                notification_param = self.create_cfn_parameter(
                    param_type='String',
                    name=param_name,
                    description='SNS Topic to notify',
                    value=notification_paco_ref,
                    min_length=1, # prevent borked empty values from breaking notification
                )
                self.notification_param_map[param_name] = notification_param
            notification_cfn_refs.append(troposphere.Ref(notification_param))
        return notification_cfn_refs

    def set_alarm_actions_to_cfn_export(self, alarm, cfn_export_dict):
        "Sets the AlarmActions, OKActions and InsufficientDataActions for a Troposphere dict"
        alarm_action_list = []
        notification_groups = self.paco_ctx.project['resource']['snstopics'][alarm.region_name]
        for alarm_action in alarm.get_alarm_actions_paco_refs(notification_groups):
            # Create parameter
            param_name = 'AlarmAction{}'.format(utils.md5sum(str_data=alarm_action))
            if param_name in self.alarm_action_param_map.keys():
                alarm_action_param = self.alarm_action_param_map[param_name]
            else:
                alarm_action_param = self.create_cfn_parameter(
                    param_type='String',
                    name=param_name,
                    description='SNSTopic for Alarm to notify.',
                    value=alarm_action
                )
                self.alarm_action_param_map[param_name] = alarm_action_param
            alarm_action_list.append(troposphere.Ref(alarm_action_param))

        cfn_export_dict['AlarmActions'] = alarm_action_list
        if getattr(alarm, 'enable_ok_actions', False):
            cfn_export_dict['OKActions'] = alarm_action_list
        if getattr(alarm, 'enable_insufficient_data_actions', False):
            cfn_export_dict['InsufficientDataActions'] = alarm_action_list


class CWAlarms(CFBaseAlarm):
    """CloudFormation template for CloudWatch Alarms"""
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx)
        resource = stack.resource
        alarm_sets = resource.monitoring.alarm_sets
        if schemas.IResource.providedBy(resource):
            self.set_aws_name('Alarms', self.resource_group_name, self.resource_name, stack.resource.type)
        elif schemas.IRDSClusterInstance.providedBy(resource):
            # in this case resource is an RDSClusterInstance
            dbcluster = self.resource.dbcluster
            self.set_aws_name('Alarms', dbcluster.group_name, dbcluster.name, self.resource.name, stack.resource.type)
        else:
            # Application-level Alarms
            self.set_aws_name('Alarms')

        self.dimension = vocabulary.cloudwatch[resource.type]['dimension']

        # build a list of Alarm objects
        alarms = []
        # ECSServices can have Alarms for every Service
        if schemas.IECSServices.providedBy(resource):
            for service in resource.services.values():
                if getattr(service, 'monitoring', None) != None and getattr(service.monitoring, 'alarm_sets', None) != None:
                    alarm_sets = service.monitoring.alarm_sets
                    for alarm_set_name in alarm_sets.keys():
                        alarm_set = alarm_sets[alarm_set_name]
                        for alarm_name, alarm in alarm_set.items():
                            cfn_resource_name = 'Alarm{}{}'.format(
                                self.create_cfn_logical_id(alarm_set_name),
                                self.create_cfn_logical_id(alarm_name)
                            )
                            alarm_set[alarm_name].cfn_resource_name = cfn_resource_name
                            alarm._service = service
                            alarms.append(alarm_set[alarm_name])
        else:
            for alarm_set_name in alarm_sets.keys():
                alarm_set = alarm_sets[alarm_set_name]
                for alarm_name in alarm_set.keys():
                    cfn_resource_name = 'Alarm{}{}'.format(
                        self.create_cfn_logical_id(alarm_set_name),
                        self.create_cfn_logical_id(alarm_name)
                    )
                    alarm_set[alarm_name].cfn_resource_name = cfn_resource_name
                    alarms.append(alarm_set[alarm_name])

        # Define the Template
        self.init_template('CloudWatch Alarms')
        self.alarm_action_param_map = {}
        self.notification_param_map = {}
        alarms_are_enabled = False
        if resource.is_enabled() and resource.monitoring.enabled:
            alarms_are_enabled = self.add_alarms(alarms)
        self.template.enabled = alarms_are_enabled

    def add_alarms(self, alarms):
        "Add a list of Alarms to the template"
        alarms_are_enabled = False
        dimension_parameters = {}
        resource = self.resource

        # Dimension Parameters:
        # Each Dimension Parameter may be shared by multiple Alarms in one template
        #
        # Resources with a single Dimension look like:
        #
        #   - Resource Type: ASG
		#     Dimensions: ['AutoScalingGroupName', 'my-asg-name']
        #
        # There will be a single CloudFormation Parameter named 'DimensionResource' for these single Dimension resources.
        # Other Resources may need multiple Dimensions or can have sub-resources each with a different Dimension.

        # IoTAnalyticsPipeline: Dimensions for Channel, Pipeline and DataSet
        if schemas.IIoTAnalyticsPipeline.providedBy(resource):
            params_needed = {}
            for alarm in alarms:
                if alarm.metric_name not in params_needed:
                    params_needed[alarm.metric_name] = [alarm]
                else:
                    params_needed[alarm.metric_name].append(alarm)
            for metric_name, alarms in params_needed.items():
                if metric_name == 'IncomingMessages':
                    value = resource.paco_ref + '.channel.name'
                    dimension_parameters['ChannelName'] = self.create_cfn_parameter(
                        name='ChannelName',
                        param_type='String',
                        description='The ChannelName for the dimension.',
                        value=value
                    )
                elif metric_name == 'ActivityExecutionError':
                    value = resource.paco_ref + '.pipeline.name'
                    dimension_parameters['PipelineName'] = self.create_cfn_parameter(
                        name='PipelineName',
                        param_type='String',
                        description='The PipelineName for the dimension.',
                        value=value
                    )
                elif metric_name == 'ActionExecution':
                    dataset_names = {}
                    for alarm in alarms:
                        for dimension in alarm.dimensions:
                            if dimension.name.lower() == 'datasetname':
                                dataset_name = dimension.value
                                cfn_name = self.create_cfn_logical_id(f'{dataset_name}DatasetName')
                                dataset_names[dataset_name] = cfn_name
                                alarm._param_name = cfn_name
                    for dataset_name, cfn_name in dataset_names.items():
                        value = f'{resource.paco_ref}.dataset.{dataset_name}.name'
                        dimension_parameters[cfn_name] = self.create_cfn_parameter(
                            name=cfn_name,
                            param_type='String',
                            description=f'The DatasetName for {dataset_name}.',
                            value=value
                        )

        # ECSServices need the ClusterName Dimension and the ServiceName for each Service
        elif schemas.IECSServices.providedBy(resource):
            dimension_parameters['ClusterName'] = self.create_cfn_parameter(
                name='ClusterName',
                param_type='String',
                description='The ClusterName dimension.',
                value=resource.cluster + '.name'
            )
            for service in resource.services.values():
                name = self.create_cfn_logical_id(f'ServiceName{service.name}')
                service._dimension_name = name
                dimension_parameters[name] = self.create_cfn_parameter(
                    name=name,
                    param_type='String',
                    description='ServiceName for the Dimension.',
                    value=service.paco_ref + '.name'
                )
        # DBCluster with DBInstances
        elif schemas.IRDSClusterInstance.providedBy(resource):
            value = f"{resource.dbcluster.paco_ref}.db_instances.{resource.name}.name"
            dimension_parameters['ResourceName'] = self.create_cfn_parameter(
                name='DimensionResource',
                param_type='String',
                description='The resource id or name for the metric dimension.',
                value=value
            )
        # simple Resources with a single name and dimension
        elif schemas.IResource.providedBy(resource):
            value = resource.paco_ref + '.name'
            if schemas.IElastiCacheRedis.providedBy(resource):
                # Primary node uses the aws name with '-001' appended to it
                # ToDo: how to have Alarms for the read replica nodes?
                value = resource.get_aws_name() + '-001'
            dimension_parameters['ResourceName'] = self.create_cfn_parameter(
                name='DimensionResource',
                param_type='String',
                description='The resource id or name for the metric dimension.',
                value=value
            )

        for alarm in alarms:
            # Track if any alarms are enabled
            if alarm.enabled == True:
                alarms_are_enabled = True
            else:
                continue

            # Alarm hook: registered by Services using paco.extend.add_cw_alarm_hook
            for hook in CW_ALARM_HOOKS:
                hook(alarm)

            # Dimension Parameters
            if len(alarm.dimensions) > 0:
                for dimension in alarm.dimensions:
                    dimension.parameter = self.create_cfn_parameter(
                        name='DimensionResource{}{}'.format(alarm.cfn_resource_name, dimension.name),
                        param_type='String',
                        description='The resource id or name for the metric dimension.',
                        value=dimension.value,
                    )

            # compute dynamic attributes for cfn_export_dict
            alarm_export_dict = alarm.cfn_export_dict
            self.set_alarm_actions_to_cfn_export(alarm, alarm_export_dict)

            # AlarmDescription
            notification_cfn_refs = self.create_notification_params(alarm)
            alarm_export_dict['AlarmDescription'] = alarm.get_alarm_description(notification_cfn_refs)

            # Namespace
            if not alarm.namespace:
                if schemas.ICloudWatchLogAlarm.providedBy(alarm):
                    # Namespace look-up for LogAlarms
                    obj = get_parent_by_interface(alarm, schemas.IMonitorConfig)
                    try:
                        log_group = obj.log_sets[alarm.log_set_name].log_groups[alarm.log_group_name]
                    except KeyError:
                        raise InvalidLogSetConfiguration("""
Invalid Log Set configuration:

Log Set: {}
Log Group: {}
Resource: {} (type: {})
Resource paco.ref: {}

HINT: Ensure that the monitoring.log_sets for the resource is enabled and that the Log Set and Log Group names match.

""".format(alarm.log_set_name, alarm.log_group_name, resource.name, resource.type, resource.paco_ref)
                        )

                    if log_group.external_resource == False:
                        prefixed_log_group_name = prefixed_name(
                            resource, log_group.get_full_log_group_name(), self.paco_ctx.legacy_flag
                        )
                    else:
                        prefixed_log_group_name = log_group.get_full_log_group_name()
                    alarm_export_dict['Namespace'] = "Paco/" + prefixed_log_group_name
                else:
                    # if not supplied default to the Namespace for the Resource type
                    alarm_export_dict['Namespace'] = vocabulary.cloudwatch[resource.type]['namespace']
            else:
                # Use the Namespace as directly supplied
                alarm_export_dict['Namespace'] = alarm.namespace

            # Dimensions
            # If there are no dimensions, then fallback to the default of a primary Dimension and the resource's resource_name
            # This only happens for Resource-level Alarms. MetricFilter LogGroup Alarms have no Dimensions
            dimensions = []
            if not schemas.ICloudWatchLogAlarm.providedBy(alarm):
                if schemas.IRDSClusterInstance.providedBy(resource) and len(alarm.dimensions) < 1:
                    dimensions.append(
                        {'Name': vocabulary.cloudwatch[resource.type]['dimension'],
                         'Value': troposphere.Ref(dimension_parameters['ResourceName'])}
                    )
                elif schemas.IECSServices.providedBy(resource):
                    dimensions.append(
                        {'Name': 'ClusterName', 'Value': troposphere.Ref(dimension_parameters['ClusterName'])}
                    )
                    dimensions.append(
                        {'Name': 'ServiceName', 'Value': troposphere.Ref(
                            dimension_parameters[alarm._service._dimension_name]
                        )}
                    )
                # complex metric Resources that have more than one Dimension to select
                elif schemas.IASG.providedBy(resource) or schemas.IIoTTopicRule.providedBy(resource):
                    dimensions.append(
                        {'Name': vocabulary.cloudwatch[resource.type]['dimension'],
                        'Value': troposphere.Ref(dimension_parameters['ResourceName'])}
                    )
                elif schemas.IIoTAnalyticsPipeline.providedBy(resource):
                    # IoTAnalyticsPipeline can alarm on Channel, Pipeline, Datastore and Dataset dimensions
                    if alarm.metric_name == 'ActivityExecutionError':
                        dimensions.append(
                            {'Name': 'PipelineName',
                            'Value': troposphere.Ref(dimension_parameters['PipelineName'])}
                        )
                    elif alarm.metric_name == 'IncomingMessages':
                        dimensions.append(
                            {'Name': 'ChannelName',
                            'Value': troposphere.Ref(dimension_parameters['ChannelName'])}
                        )
                    elif alarm.metric_name == 'ActionExecution':
                        dimensions.append(
                            {'Name': 'DatasetName',
                            'Value': troposphere.Ref(dimension_parameters[alarm._param_name])}
                        )
                    else:
                        raise InvalidAlarmConfiguration(f"Unsuported metric_name '{alarm.metric_name}' specified for IoTAnalyticsPipeline alarm:\n{alarm.paco_ref_parts}")

                elif schemas.IResource.providedBy(resource) and len(alarm.dimensions) < 1:
                    # Resources with a single Dimension based on the resource type
                    dimensions.append(
                        {'Name': vocabulary.cloudwatch[resource.type]['dimension'],
                         'Value': troposphere.Ref(dimension_parameters['ResourceName'])}
                    )

                # Add ClientId (account id) dimension for ElasticsearchDomain
                if schemas.IElasticsearchDomain.providedBy(resource):
                    dimensions.append(
                        {'Name': 'ClientId',
                        'Value': self.stack.account_ctx.id }
                    )

                for dimension in alarm.dimensions:
                    if schemas.IIoTAnalyticsPipeline.providedBy(resource) and dimension.name == 'DatasetName':
                        continue
                    dimensions.append(
                        {'Name': dimension.name, 'Value': troposphere.Ref(dimension.parameter)}
                    )

            alarm_export_dict['Dimensions'] = dimensions

            # Add Alarm resource
            alarm_resource = troposphere.cloudwatch.Alarm.from_dict(
                alarm.cfn_resource_name,
                alarm_export_dict
            )
            self.template.add_resource(alarm_resource)

            # Alarm Output
            output_ref = '.'.join(
                [resource.paco_ref_parts, 'monitoring', 'alarm_sets', alarm.__parent__.name, alarm.name]
            )
            self.create_output(
                title=alarm.cfn_resource_name,
                value=troposphere.Ref(alarm_resource),
                ref=output_ref,
            )

        return alarms_are_enabled

