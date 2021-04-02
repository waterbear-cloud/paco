from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import registry
import troposphere
import troposphere.codestarnotifications


class NotificationRules(StackTemplate):
    def __init__(self, stack, paco_ctx, app_name, env_name):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('NotificationRules', self.resource_group_name, self.resource.name)
        self.app_name = app_name
        self.env_name = env_name

        # Troposphere Template Initialization
        self.init_template('CodeStar Notification Rules Template')

        self.notification_groups = {}
        rule_target_list = []
        if self.resource.monitoring != None and self.resource.monitoring.notifications != None:
            for notify_group_name in self.resource.monitoring.notifications.keys():
                for sns_group_name in self.resource.monitoring.notifications[notify_group_name].groups:
                    notify_param = self.create_notification_param(sns_group_name)
                    rule_target_list.append(
                        {
                            'TargetAddress': troposphere.Ref(notify_param),
                            'TargetType': 'SNS'
                        }
                    )

            event_id_list = []
            for event_id in self.resource.notification_events:
                event_id_list.append(f'codepipeline-pipeline-pipeline-execution-{event_id}')


            codepipeline_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='CodePipelineArn',
                description='CodePipeline resource ARN',
                value=f'{self.resource.paco_ref}.arn'
            )

            rule_name = self.create_resource_name(f'{self.env_name}-{self.app_name}-{self.resource_group_name}-{self.resource.name}-{self.aws_region}')
            rule_dict = {
                'DetailType': 'FULL',
                'EventTypeIds': event_id_list,
                'Name': rule_name,
                'Resource': troposphere.Ref(codepipeline_arn_param),
                'Targets': rule_target_list
            }
            rule_logical_id = self.create_cfn_logical_id_join(['NotificationRule', rule_name], True)
            rule_res = troposphere.codestarnotifications.NotificationRule.from_dict(
                rule_logical_id,
                rule_dict
            )

            self.template.add_resource( rule_res )

        # # Outputs
        # self.create_output(
        #     title='ExampleResourceId',
        #     description="Example resource Id.",
        #     value=troposphere.Ref(example_res),
        #     ref=self.resource.paco_ref_parts + ".id"
        # )


    def create_notification_param(self, group):
        "Create a CFN Parameter for a Notification Group"
        if registry.CODESTAR_NOTIFICATION_RULE_HOOK != None:
            notification_ref = registry.CODESTAR_NOTIFICATION_RULE_HOOK(self.resource, self.account_ctx.name, self.aws_region)
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