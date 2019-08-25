"""
CloudFormation template for CloudWatch Alarms
"""

import aim.models.services
import json
import troposphere
from aim.cftemplates.cftemplates import CFTemplate
from aim.models import schemas
from aim.models import vocabulary


class CWAlarms(CFTemplate):
    """
    CloudFormation template for CloudWatch Alarms
    """
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
        aws_name
    ):
        aws_name='-'.join([aws_name, 'Alarms'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=res_config_ref,
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.alarm_sets = alarm_sets
        self.dimension = vocabulary.cloudwatch[res_type]['dimension']
        # build a list of Alarm objects
        alarms = []
        for alarm_set_id in alarm_sets.keys():
            alarm_set = alarm_sets[alarm_set_id]
            for alarm_id in alarm_set.keys():
                cfn_resource_name = 'Alarm{}{}'.format(
                    self.normalize_resource_name(alarm_set_id),
                    self.normalize_resource_name(alarm_id)
                )
                alarm_set[alarm_id].cfn_resource_name = cfn_resource_name
                alarms.append(alarm_set[alarm_id])

        # Define the Template
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('CloudWatch Alarms')

        # Add Parameters
        dimension_param = self.gen_parameter(
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
                    dimension.parameter = self.gen_parameter(
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

        self.set_template(template.to_yaml())