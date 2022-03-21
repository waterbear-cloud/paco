"""
CloudWatch Events Rule template
"""

from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.core.exception import InvalidEventsRuleEventPatternSource
from paco.models import vocabulary, schemas, registry
from paco.models.locations import get_parent_by_interface
from paco.models.references import get_model_obj_from_ref, Reference, is_ref
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
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False


def create_event_rule_name(eventsrule):
    "Create an Events Rule name"
    # also used by Lambda
    name = eventsrule.create_resource_name_join(eventsrule.paco_ref_parts.split('.'), '-')
    return hash_smaller(name, 64, suffix=True)

class EventsRule(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx
    ):
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        eventsrule = stack.resource
        config_ref = eventsrule.paco_ref_parts
        self.set_aws_name('EventsRule', self.resource_group_name, self.resource_name)

        self.notification_groups = {}

        # Init a Troposphere template
        self.init_template('CloudWatch EventsRule')

        if eventsrule.is_enabled() == False:
            return

        # Parameters
        schedule_expression_param = None
        if eventsrule.schedule_expression:
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

        # Monitoring Target
        monitoring = self.resource.monitoring
        if monitoring != None and monitoring.is_enabled() == True:
            notifications = None
            if monitoring.notifications != None and len(monitoring.notifications.keys()) > 0:
                notifications = monitoring.notifications
            else:
                app_config = get_parent_by_interface(self.resource, schemas.IApplication)
                notifications = app_config.notifications

            if notifications != None and len(notifications.keys()) > 0:
                # Create the CF Param for the SNS ARN we need to Publish to
                notify_param_cache = []
                for notify_group_name in notifications.keys():
                    for sns_group_name in notifications[notify_group_name].groups:
                        notify_param = self.create_notification_param(sns_group_name)
                        # Only append if the are unique
                        if notify_param not in notify_param_cache:
                            eventsrule.targets.append(notify_param)
                            notify_param_cache.append(notify_param)

        # Targets
        targets = []
        self.target_params = {}
        target_invocation_role_resource = None
        for index in range(0, len(eventsrule.targets)):
            target = eventsrule.targets[index]
            # Target Parameters
            target_name = 'Target{}'.format(index)

            # Target CFN Parameters
            # Check if we already have a parameter object
            target_policy_actions = None
            if isinstance(target, troposphere.Parameter):
                self.target_params[target_name + 'Arn'] = target
            else:
                self.target_params[target_name + 'Arn'] = self.create_cfn_parameter(
                    param_type='String',
                    name=target_name + 'Arn',
                    description=target_name + ' Arn for the Events Rule.',
                    value=target.target + '.arn',
                )

                # If the target is a reference, get the target object from the model
                # to check what type of resource we need to configure for
                target_ref = Reference(target.target)
                if target_ref.parts[-1] == 'project' and target_ref.parts[-3] == 'build':
                    codebuild_target_ref = f'paco.ref {".".join(target_ref.parts[:-1])}'
                    target_model_obj = get_model_obj_from_ref(codebuild_target_ref, self.paco_ctx.project)
                else:
                    target_model_obj = get_model_obj_from_ref(target.target, self.paco_ctx.project)

                # Lambda Policy Actions
                if schemas.IDeploymentPipelineBuildCodeBuild.providedBy(target_model_obj):
                    # CodeBuild Project
                    target_policy_actions = [awacs.codebuild.StartBuild]
                elif schemas.ILambda.providedBy(target_model_obj):
                    # Lambda Function
                    target_policy_actions = [awacs.awslambda.InvokeFunction]

            self.target_params[target_name] = self.create_cfn_parameter(
                param_type='String',
                name=target_name,
                description=target_name + ' for the Event Rule.',
                value=target_name,
            )

            # IAM Role Polcies by Resource type
            if target_policy_actions != None:
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
                'Id': troposphere.Ref(self.target_params[target_name])
            }

            if target_invocation_role_resource != None:
                cfn_export_dict['RoleArn'] = troposphere.GetAtt(target_invocation_role_resource, 'Arn')
            if hasattr(target, 'input_json') and target.input_json != None:
                cfn_export_dict['Input'] = target.input_json

            # Events Rule Targets
            targets.append(cfn_export_dict)

        # Events Rule Resource
        # The Name is needed so that a Lambda can be created and it's Lambda ARN output
        # can be supplied as a Parameter to this Stack and a Lambda Permission can be
        # made with the Lambda. Avoids circular dependencies.
        name = create_event_rule_name(eventsrule)
        if eventsrule.enabled_state:
            enabled_state = 'ENABLED'
        else:
            enabled_state = 'DISABLED'

        events_rule_dict = {
            'Name': name,
            'Description': troposphere.Ref(description_param),
            'Targets': targets,
            'State': enabled_state
        }

        if target_invocation_role_resource != None:
            events_rule_dict['RoleArn'] = troposphere.GetAtt(target_invocation_role_resource, 'Arn')

        if schedule_expression_param != None:
            events_rule_dict['ScheduleExpression'] = troposphere.Ref(schedule_expression_param)
        elif eventsrule.event_pattern != None:
            source_value_list = []
            project_name_list = []
            for pattern_source in eventsrule.event_pattern.source:
                if is_ref(pattern_source):
                    source_obj = get_model_obj_from_ref(pattern_source, self.paco_ctx.project)
                    if schemas.IDeploymentPipelineBuildCodeBuild.providedBy(source_obj):
                        source_value_list.append('aws.codebuild')
                        project_name_list.append(source_obj._stack.template.get_project_name())
                    else:
                        raise InvalidEventsRuleEventPatternSource(pattern_source)
                else:
                    source_value_list.append(pattern_source)

            if len(project_name_list) > 0:
                eventsrule.event_pattern.detail['project-name'] = project_name_list

            event_pattern_dict = {
                'source': source_value_list,
                'detail-type': utils.obj_to_dict(eventsrule.event_pattern.detail_type),
                'detail': utils.obj_to_dict(eventsrule.event_pattern.detail),
            }
            event_pattern_yaml = yaml.dump(event_pattern_dict)
            events_rule_dict['EventPattern'] = yaml.load(event_pattern_yaml)
        else:
            # Defaults to a CodePipeline events rule
            event_pattern_yaml = """
source:
    - aws.codepipeline
detail-type:
    - 'CodePipeline Pipeline Execution State Change'
detail:
    state:
    - STARTED
"""
            events_rule_dict['EventPattern'] = yaml.load(event_pattern_yaml)

        event_rule_resource = troposphere.events.Rule.from_dict(
            'EventRule',
            events_rule_dict
        )
        if target_invocation_role_resource != None:
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



    def create_notification_param(self, group):
        "Create a CFN Parameter for a Notification Group"
        if registry.EVENTSRULE_NOTIFICATION_RULE_HOOK != None:
            notification_ref = registry.EVENTSRULE_NOTIFICATION_RULE_HOOK(self.resource, self.account_ctx.name, self.aws_region)
        else:
            notification_ref = self.paco_ctx.project['resource']['sns'].computed[self.account_ctx.name][self.stack.aws_region][group].paco_ref + '.arn'

        # Re-use existing Parameter or create new one
        param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_ref))
        if param_name not in self.notification_groups:
            notification_param = self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='SNS Topic to notify',
                value=notification_ref,
                min_length=1, # prevent borked empty values from breaking notification
            )
            self.notification_groups[param_name] = notification_param
        return self.notification_groups[param_name]
