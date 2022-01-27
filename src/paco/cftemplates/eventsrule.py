"""
CloudWatch Events Rule template
"""

from paco.cftemplates.cftemplates import StackTemplate
from paco.models import vocabulary, schemas
from paco.models.references import get_model_obj_from_ref, Reference
from paco.utils import hash_smaller
from awacs.aws import Allow, Statement, Policy, Principal
from enum import Enum
from io import StringIO
import awacs.awslambda
import awacs.codebuild
import awacs.sts
import base64
import os
import troposphere
import troposphere.events
import troposphere.iam


def create_event_rule_name(eventsrule):
    "Create an Events Rule name"
    # also used by Lambda
    name = eventsrule.create_resource_name_join(eventsrule.paco_ref_parts.split('.'), '-')
    return hash_smaller(name, 64, suffix=True)

class EventsRule(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        eventsrule = stack.resource
        config_ref = eventsrule.paco_ref_parts
        self.set_aws_name('EventsRule', self.resource_group_name, self.resource_name)

        # Init a Troposphere template
        self.init_template('CloudWatch EventsRule')

        if eventsrule.is_enabled() == False:
            return

        # Parameters
        schedule_expression_param = self.create_cfn_parameter(
            param_type = 'String',
            name = 'ScheduleExpression',
            description = 'ScheduleExpression for the Event Rule.',
            value = eventsrule.schedule_expression,
        )
        description_param = self.create_cfn_parameter(
            param_type = 'String',
            name = 'EventDescription',
            description = 'Description for the Event Rule.',
            value = eventsrule.description,
        )

        # Targets
        targets = []
        self.target_params = {}
        for index in range(0, len(eventsrule.targets)):
            target = eventsrule.targets[index]
            # Target Parameters
            target_name = 'Target{}'.format(index)

            # Target CFN Parameters
            self.target_params[target_name + 'Arn'] = self.create_cfn_parameter(
                param_type='String',
                name=target_name + 'Arn',
                description=target_name + ' Arn for the Events Rule.',
                value=target.target + '.arn',
            )
            self.target_params[target_name] = self.create_cfn_parameter(
                param_type='String',
                name=target_name,
                description=target_name + ' for the Event Rule.',
                value=target_name,
            )

            # IAM Role
            # Lambda Policy Actions
            target_ref = Reference(target.target)
            if target_ref.parts[-1] == 'project' and target_ref.parts[-3] == 'build':
                codebuild_target_ref = f'paco.ref {".".join(target_ref.parts[:-1])}'
                target_model_obj = get_model_obj_from_ref(codebuild_target_ref, self.paco_ctx.project)
            else:
                target_model_obj = get_model_obj_from_ref(target.target, self.paco_ctx.project)

            # IAM Role Polcies by Resource type
            if schemas.IDeploymentPipelineBuildCodeBuild.providedBy(target_model_obj):
                # CodeBuild Project
                target_policy_actions = [awacs.codebuild.StartBuild]
            elif schemas.ILambda.providedBy(target_model_obj):
                # Lambda Function
                target_policy_actions = [awacs.awslambda.InvokeFunction]


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
                                    Action=target_policy_actions,
                                    Resource=[troposphere.Ref(self.target_params[target_name + 'Arn'])],
                                )
                            ]
                        )
                    )
                ],
            )
            self.template.add_resource(target_invocation_role_resource)

            # Create Target CFN Resources
            cfn_export_dict = {
                'Arn': troposphere.Ref(self.target_params[target_name + 'Arn']),
                'Id': troposphere.Ref(self.target_params[target_name]),
                'RoleArn': troposphere.GetAtt(target_invocation_role_resource, 'Arn')
            }
            if target.input_json != None:
                cfn_export_dict['Input'] = target.input_json

            # Events Rule Targets
            targets.append(
                troposphere.events.Target.from_dict(
                    target_name,
                    cfn_export_dict
                )
            )

        # Events Rule Resource
        # The Name is needed so that a Lambda can be created and it's Lambda ARN output
        # can be supplied as a Parameter to this Stack and a Lambda Permission can be
        # made with the Lambda. Avoids circular dependencies.
        name = create_event_rule_name(eventsrule)
        if eventsrule.enabled_state:
            enabled_state = 'ENABLED'
        else:
            enabled_state = 'DISABLED'
        event_rule_resource = troposphere.events.Rule(
            'EventRule',
            Name=name,
            Description=troposphere.Ref(description_param),
            ScheduleExpression=troposphere.Ref(schedule_expression_param),
            RoleArn=troposphere.GetAtt(target_invocation_role_resource, 'Arn'),
            Targets=targets,
            State=enabled_state
        )
        event_rule_resource.DependsOn = target_invocation_role_resource
        self.template.add_resource(event_rule_resource)

        # Outputs
        self.create_output(
            title="EventRuleId",
            value=troposphere.Ref(event_rule_resource),
            ref=config_ref + '.id',
        )
        self.create_output(
            title="EventRuleArn",
            value=troposphere.GetAtt(event_rule_resource, "Arn"),
            ref=config_ref + '.arn',
        )

