"""
CloudFormation template for CloudWatch Alarms
"""

import aim.models.services
import json
import troposphere
from aim import utils
from aim.models import schemas
from aim.models import vocabulary
from aim.cftemplates.cftemplates import CFTemplate
from aim.models.locations import get_parent_by_interface

class CWAlarms(CFTemplate):
    """
    CloudFormation template for CloudWatch Alarms
    """
    notification_region = None # allow services the chance to send notifications to another region

    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        alarm_sets,
        res_type,
        res_config_ref,
        resource,
        grp_id,
        res_id,
        resource_type,
    ):
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            enabled=resource.is_enabled(),
            config_ref=res_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('Alarms', grp_id, res_id, resource_type)
        self.alarm_sets = alarm_sets
        self.dimension = vocabulary.cloudwatch[res_type]['dimension']

        # build a list of Alarm objects
        alarms = []
        for alarm_set_id in alarm_sets.keys():
            alarm_set = alarm_sets[alarm_set_id]
            for alarm_id in alarm_set.keys():
                cfn_resource_name = 'Alarm{}{}'.format(
                    self.create_cfn_logical_id(alarm_set_id),
                    self.create_cfn_logical_id(alarm_id)
                )
                alarm_set[alarm_id].cfn_resource_name = cfn_resource_name
                alarms.append(alarm_set[alarm_id])

        # Define the Template
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('CloudWatch Alarms')
        template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        self.alarm_action_param_map = {}
        self.notification_param_map = {}
        if resource.is_enabled() and resource.monitoring.enabled:
            self.add_alarms(
                template,
                alarms,
                resource,
                res_type,
                res_config_ref,
                self.aim_ctx.project,
                alarm_id,
                alarm_set_id,
            )
        self.set_template(template.to_yaml())

    def add_alarms(
            self,
            template,
            alarms,
            resource,
            res_type,
            res_config_ref,
            project,
            alarm_id,
            alarm_set_id,
        ):
        # Add Parameters
        dimension_param = self.create_cfn_parameter(
            param_type = 'String',
            name = 'DimensionResource',
            description = 'The resource id or name for the metric dimension.',
            value = resource.aim_ref + '.name',
            use_troposphere = True
        )
        template.add_parameter(dimension_param)
        for alarm in alarms:
            if len(alarm.dimensions) > 1:
                for dimension in alarm.dimensions:
                    dimension.parameter = self.create_cfn_parameter(
                        param_type = 'String',
                        name = 'DimensionResource{}{}'.format(alarm.cfn_resource_name, dimension.name),
                        description = 'The resource id or name for the metric dimension.',
                        value = dimension.value,
                        use_troposphere = True
                    )
                    template.add_parameter(dimension.parameter)

        # Add Alarm resources
        for alarm in alarms:
            # compute dynamic attributes for cfn_export_dict
            alarm_export_dict = alarm.cfn_export_dict
            alarm_action_list = []
            for alarm_action in alarm.get_alarm_actions_aim_refs():
                # Create parameter
                param_name = 'AlarmAction{}'.format(utils.md5sum(str_data=alarm_action))
                if param_name in self.alarm_action_param_map.keys():
                    alarm_action_param = self.alarm_action_param_map[param_name]
                else:
                    alarm_action_param = self.create_cfn_parameter(
                        param_type = 'String',
                        name = param_name,
                        description = 'SNSTopic for Alarm to notify.',
                        value = alarm_action,
                        use_troposphere = True
                    )
                    template.add_parameter(alarm_action_param)
                    self.alarm_action_param_map[param_name] = alarm_action_param
                alarm_action_list.append(troposphere.Ref(alarm_action_param))

            alarm_export_dict['AlarmActions'] = alarm_action_list

            # AlarmDescription
            notification_aim_refs = []
            for group in alarm.notification_groups:
                if not self.notification_region:
                    region = alarm.region_name
                else:
                    region = self.notification_region
                notification_aim_refs.append(
                    project['resource']['notificationgroups'][region][group].aim_ref + '.arn'
                )

            notification_cfn_refs = []
            for notification_aim_ref in notification_aim_refs:
                # Create parameter
                param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_aim_ref))
                if param_name in self.notification_param_map.keys():
                    notification_param = self.notification_param_map[param_name]
                else:
                    notification_param = self.create_cfn_parameter(
                        param_type = 'String',
                        name = param_name,
                        description = 'SNS Topic to notify',
                        value = notification_aim_ref,
                        use_troposphere = True
                    )
                    template.add_parameter(notification_param)
                    self.notification_param_map[param_name] = notification_param
                notification_cfn_refs.append(troposphere.Ref(notification_param))
            alarm_export_dict['AlarmDescription'] = self.get_alarm_description(alarm, notification_cfn_refs)

            # Namespace - if not supplied default to the Namespace for the Resource type
            if 'Namespace' not in alarm_export_dict:
                alarm_export_dict['Namespace'] = vocabulary.cloudwatch[res_type]['namespace']

            # Dimensions
            # if there are no dimensions, then fallback to the default of
            # a primary dimension and the resource's resource_name
            if len(alarm.dimensions) < 1:
                dimensions = [
                    {'Name': vocabulary.cloudwatch[res_type]['dimension'],
                     'Value': troposphere.Ref(dimension_param)}
                ]
            else:
                dimensions = []
                for dimension in alarm.dimensions:
                    dimensions.append(
                        {'Name': dimension.name, 'Value': troposphere.Ref(dimension.parameter)}
                    )
            alarm_export_dict['Dimensions'] = dimensions

            # Add Alarm resource
            alarm_resource = troposphere.cloudwatch.Alarm.from_dict(
                alarm.cfn_resource_name,
                alarm_export_dict
            )
            template.add_resource(alarm_resource)

            # Alarm Output
            output_ref = '.'.join([res_config_ref, 'monitoring', 'alarm_sets', alarm_set_id, alarm_id])
            self.register_stack_output_config(output_ref, alarm.cfn_resource_name)
            alarm_output = troposphere.Output(
                alarm.cfn_resource_name,
                Value=troposphere.Ref(alarm_resource)
            )
            template.add_output(alarm_output)

    def get_alarm_description(self, alarm, notification_cfn_refs):
        """Create an Alarm Description in JSON format with AIM Alarm information"""
        project = get_parent_by_interface(alarm, schemas.IProject)
        netenv = get_parent_by_interface(alarm, schemas.INetworkEnvironment)
        env = get_parent_by_interface(alarm, schemas.IEnvironment)
        envreg = get_parent_by_interface(alarm, schemas.IEnvironmentRegion)
        app = get_parent_by_interface(alarm, schemas.IApplication)
        group = get_parent_by_interface(alarm, schemas.IResourceGroup)
        resource = get_parent_by_interface(alarm, schemas.IResource)

        # SNS Topic ARNs are supplied Paramter Refs
        topic_arn_subs = []
        sub_dict = {}
        for action_ref in notification_cfn_refs:
            ref_id = action_ref.data['Ref']
            topic_arn_subs.append('${%s}' % ref_id)
            sub_dict[ref_id] = action_ref

        # Base alarm info - used for standalone alarms not part of an application
        description = {
            "project_name": project.name,
            "project_title": project.title,
            "account_name": alarm.account_name,
            "alarm_name": alarm.name,
            "classification": alarm.classification,
            "severity": alarm.severity,
            "topic_arns": topic_arn_subs
        }

        # conditional fields:
        if alarm.description:
            description['description'] = alarm.description
        if alarm.runbook_url:
            description['runbook_url'] = alarm.runbook_url

        if app != None:
            # Service applications and apps not part of a NetEnv
            description["app_name"] = app.name
            description["app_title"] = app.title
            description["resource_group_name"] = group.name
            description["resource_group_title"] = group.title
            description["resource_name"] = resource.name
            description["resource_title"] = resource.title

        if netenv != None:
            # NetEnv information
            description["netenv_name"] = netenv.name
            description["netenv_title"] = netenv.title
            description["env_name"] = env.name
            description["env_title"] = env.title
            description["envreg_name"] = envreg.name
            description["envreg_title"] = envreg.title

        description_json = json.dumps(description)

        return troposphere.Sub(
            description_json,
            sub_dict
        )
