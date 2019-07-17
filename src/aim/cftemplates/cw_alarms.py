import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum
import base64
from aim.models import vocabulary


class CWAlarms(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 sets_config,
                 res_type,
                 res_config_ref,
                 aws_name):

        #aim_ctx.log("CLoudWatch Alarms CF Template init")
        # Super Init:
        aws_name='-'.join([aws_name, 'Alarms'])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=res_config_ref,
                         aws_name=aws_name)

        self.sets_config = sets_config
        self.dimension = vocabulary.cloudwatch[res_type]['dimension']
        self.namespace = vocabulary.cloudwatch[res_type]['namespace']
        # Initialize Parameters
        self.set_parameter('AlarmResource', res_config_ref)

        # TOOD: Template needs Scale in/out policies

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch Alarms'

Parameters:

  AlarmResource:
    Description: "The resource name or id to assign the alarm dimenions"
    Type: String

Resources:

{0[alarms]:s}

Outputs:

{0[outputs]:s}
"""

        template_table = {
          'alarms': None,
          'outputs': None,
        }

        output_fmt = """
  Alarm{0[id]:s}:
    Value: !Ref Alarm{0[id]:s}
"""

        alarm_fmt = """
  Alarm{0[id]:s}:
    Type: AWS::CloudWatch::Alarm
    Properties:
      ActionsEnabled: False
      #AlarmActions:
      #  - String
      AlarmDescription: '{0[description]:s}'

      # Important: If you specify a name, you cannot perform updates that require
      # replacement of this resource. You can perform updates that require no or
      # some interruption. If you must replace the resource, specify a new name.
      # AlarmName: '{0[name]:s}'

      ComparisonOperator: {0[comparison_operator]:s}
      #DatapointsToAlarm: Integer
      Dimensions: {0[dimensions]:s}
      EvaluateLowSampleCountPercentile: {0[evaluate_low_sample_count_percentile]:s}
      EvaluationPeriods: {0[evaluation_periods]:d}
      ExtendedStatistic: {0[extended_statistic]:s}
      #InsufficientDataActions:
      #  - String
      MetricName: {0[metric_name]:s}
      #Metrics :
      #  - MetricDataQuery
      Namespace: {0[namespace]:s}
      #OKActions :
      #  - String
      Period: {0[period]:d}
      Statistic: {0[statistic]:s}
      Threshold: {0[threshold]:f}
      TreatMissingData: {0[treat_missing_data]:s}
      # Unit: String
"""
        dimensions_fmt = """
        - Name: %s
          Value: !Ref AlarmResource"""


        alarm_table = {
            'id': None,
            'description': None,
            'name': None,
            'comparison_operator': None,
            'dimensions': None,
            'evaluation_periods': 0,
            'metric_name': None,
            'namespace': None,
            'period': 0,
            'statistic': None,
            'threshold': 0,
            'treat_missing_data': None,
            'extended_statistic': None,
            'evaluate_low_sample_count_percentile': None
        }

        alarms_yaml = ""
        outputs_yaml = ""
        for alarm_set_id in sets_config.keys():
            alarm_set = sets_config[alarm_set_id]
            for alarm_id in alarm_set.keys():
                alarm_conf = alarm_set[alarm_id]
                normalized_set_id = self.normalize_resource_name(alarm_set_id)
                normalized_id = self.normalize_resource_name(alarm_id)
                alarm_table['id'] = normalized_set_id+normalized_id
                alarm_table['description'] = 'Part of alarm set ' + alarm_set_id
                alarm_table['name'] = alarm_id
                alarm_table['comparison_operator'] = alarm_conf.comparison_operator
                alarm_table['evaluation_periods'] = alarm_conf.evaluation_periods
                alarm_table['metric_name'] = alarm_conf.metric_name
                alarm_table['namespace'] = self.namespace
                alarm_table['dimensions'] = dimensions_fmt % (self.dimension)
                alarm_table['evaluation_periods'] = alarm_conf.evaluation_periods
                alarm_table['metric_name'] = alarm_conf.metric_name
                alarm_table['period'] = alarm_conf.period
                alarm_table['threshold'] = alarm_conf.threshold
                alarm_table['treat_missing_data'] = alarm_conf.treat_missing_data
                if alarm_conf.extended_statistic == None:
                    alarm_table['statistic'] = alarm_conf.statistic
                    alarm_table['extended_statistic'] = "!Ref AWS::NoValue"
                else:
                    alarm_table['statistic'] = '!Ref AWS::NoValue'
                    alarm_table['extended_statistic'] = alarm_conf.extended_statistic
                if alarm_conf.evaluate_low_sample_count_percentile == None:
                    alarm_table['evaluate_low_sample_count_percentile'] = "!Ref AWS::NoValue"
                else:
                    alarm_table['evaluate_low_sample_count_percentile'] = alarm_conf.evaluate_low_sample_count_percentile

                alarms_yaml += alarm_fmt.format(alarm_table)
                outputs_yaml += output_fmt.format(alarm_table)
                output_ref = '.'.join([res_config_ref, 'monitoring', 'alarm_sets', alarm_set_id, alarm_id])
                self.register_stack_output_config(output_ref, 'Alarm'+alarm_table['id'])

        template_table['alarms'] = alarms_yaml
        template_table['outputs'] = outputs_yaml

        self.set_template(template_fmt.format(template_table))

    def validate(self):
        #self.aim_ctx.log("Validating ASG Template")
        super().validate()

    def get_outputs_key_from_ref(self, aim_ref):
        # There is only one output key
        return None
