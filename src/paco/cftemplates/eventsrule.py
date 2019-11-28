"""
CloudWatch Events Rule template
"""

from paco.cftemplates.cftemplates import CFTemplate
from paco.models import vocabulary
from paco.utils import hash_smaller
from awacs.aws import Allow, Statement, Policy, Principal
from enum import Enum
from io import StringIO
import awacs.awslambda
import awacs.sts
import base64
import os
import troposphere
import troposphere.events
import troposphere.iam


class EventsRule(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        res_id,
        eventsrule,
        config_ref,
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=eventsrule.is_enabled(),
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('EventsRule', grp_id, res_id)

        # Init a Troposphere template
        self.init_template('CloudWatch EventsRule')

        # Parameters
        schedule_expression_param = self.create_cfn_parameter(
            param_type = 'String',
            name = 'ScheduleExpression',
            description = 'ScheduleExpression for the Event Rule.',
            value = eventsrule.schedule_expression,
            use_troposphere = True
        )
        self.template.add_parameter(schedule_expression_param)
        description_param = self.create_cfn_parameter(
            param_type = 'String',
            name = 'EventDescription',
            description = 'Description for the Event Rule.',
            value = eventsrule.description,
            use_troposphere = True
        )
        self.template.add_parameter(description_param)

        # Targets
        targets = []
        self.target_params = {}
        for index in range(0, len(eventsrule.targets)):
            # Target Parameters
            target_name = 'Target{}'.format(index)
            self.target_params[target_name + 'Arn'] = self.create_cfn_parameter(
                param_type = 'String',
                name = target_name + 'Arn',
                description = target_name + 'Arn for the Events Rule.',
                value = eventsrule.targets[index] + '.arn',
                use_troposphere = True
            )
            self.template.add_parameter(self.target_params[target_name + 'Arn'])
            self.target_params[target_name] = self.create_cfn_parameter(
                param_type = 'String',
                name = target_name,
                description = target_name + ' for the Event Rule.',
                value = target_name,
                use_troposphere = True
            )
            self.template.add_parameter(self.target_params[target_name])

            # Events Rule Targets
            targets.append(
                troposphere.events.Target(
                    target_name,
                    Arn=troposphere.Ref(self.target_params[target_name + 'Arn']),
                    Id=troposphere.Ref(self.target_params[target_name]),
                )
            )

            # IAM Role Resources to allow Event to invoke Target
            target_invocation_role_resource = troposphere.iam.Role(
                'TargetInvocationRole',
                AssumeRolePolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal('Service',['events.amazonaws.com'])
                        )
                    ],
                ),
                Policies=[
                    troposphere.iam.Policy(
                        PolicyName="TargetInvocation",
                        PolicyDocument=Policy(
                            Version='2012-10-17',
                            Statement=[
                                Statement(
                                    Effect=Allow,
                                    Action=[awacs.awslambda.InvokeFunction],
                                    Resource=[troposphere.Ref(self.target_params[target_name + 'Arn'])],
                                )
                            ]
                        )
                    )
                ],
            )
            self.template.add_resource(target_invocation_role_resource)

        # Events Rule Resource
        # The Name is needed so that a Lambda can be created and it's Lambda ARN output
        # can be supplied as a Parameter to this Stack and a Lambda Permission can be
        # made with the Lambda. Avoids circular dependencies.
        name = self.create_cfn_logical_id("EventsRule" + eventsrule.paco_ref)
        name = hash_smaller(name, 64)
        event_rule_resource = troposphere.events.Rule(
            'EventRule',
            Name=name,
            Description=troposphere.Ref(description_param),
            ScheduleExpression=troposphere.Ref(schedule_expression_param),
            Targets=targets,
        )
        self.template.add_resource(event_rule_resource)

        # Outputs
        self.template.add_output(
            troposphere.Output(
                "EventRuleId",
                Value=troposphere.Ref(event_rule_resource)
            )
        )
        self.template.add_output(
            troposphere.Output(
                "EventRuleArn",
                Value=troposphere.GetAtt(event_rule_resource, "Arn")
            )
        )
        self.register_stack_output_config(config_ref + '.id', 'EventRuleId')
        self.register_stack_output_config(config_ref + '.arn', 'EventRuleArn')

        self.set_template(self.template.to_yaml())
