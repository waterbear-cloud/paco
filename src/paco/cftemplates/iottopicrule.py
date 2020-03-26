"""
IoT TopicRule template
"""

from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.iot



class IoTTopicRule(StackTemplate):
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('IoTTopicRule', self.resource_group_name, self.resource_name)
        iottopicrule = self.resource

        # Init Troposphere template
        self.init_template('IoT Topic Rule')
        if not iottopicrule.is_enabled():
            return

        iottopicrule_logical_id = 'IoTTopicRule'
        # flip rule_enabled to opposite for RuleDisabled CFN
        if iottopicrule.rule_enabled:
            disabled_rule = False
        else:
            disabled_rule = True
        cfn_export_dict = {}
        cfn_export_dict['TopicRulePayload'] = {}
        cfn_export_dict['TopicRulePayload']['AwsIotSqlVersion'] = iottopicrule.aws_iot_sql_version
        cfn_export_dict['TopicRulePayload']['RuleDisabled'] = disabled_rule
        cfn_export_dict['TopicRulePayload']['Sql'] = iottopicrule.sql
        cfn_export_dict['TopicRulePayload']['Actions'] = []
        if iottopicrule.title != '':
            cfn_export_dict['TopicRulePayload']['Description'] = iottopicrule.title

        idx = 0
        for action in iottopicrule.actions:
            action_dict = {}
            if action.awslambda != None:
                action_dict['Lambda'] = {}
                self.create_cfn_parameter
                lambda_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'LambdaArn{idx}',
                    description=f'Lambda Function Arn for Action{idx}',
                    value=action.awslambda.function + '.arn',
                )
                action_dict['Lambda']['FunctionArn'] = troposphere.Ref(lambda_param)
            cfn_export_dict['TopicRulePayload']['Actions'].append(action_dict)
            idx += 1

        iottopicrule_resource = troposphere.iot.TopicRule.from_dict(
            iottopicrule_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(iottopicrule_resource)
