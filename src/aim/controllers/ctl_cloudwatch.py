import os
import aim.cftemplates
from aim.controllers.controllers import Controller
from aim.stack_group import Stack, StackGroup


class CloudWatchController(Controller):
    def __init__(self, aim_ctx):
        if aim_ctx.legacy_flag('cloudwatch_controller_type_2019_09_18') == True:
            controller_type = 'Service'
        else:
            controller_type = 'Resource'
        super().__init__(aim_ctx,
                         controller_type,
                         "CloudWatch")


        self.event_stacks = {}
        self.second = False
        self.init_done = False

        if not 'cloudwatch' in self.aim_ctx.project:
            self.init_done = True
            return
        self.config = self.aim_ctx.project['cloudwatch']
        if self.config != None:
            self.config.resolve_ref_obj = self

        #self.aim_ctx.log("Route53 Service: Configuration: %s" % (name)

    def init(self, controller_args):
        if self.init_done:
            return
        self.config.resolv_ref_obj = self
        self.init_done = True

    def create_event_rule(  self,
                            aim_ctx,
                            account_ctx,
                            aws_region,
                            stack_group,
                            event_description,
                            schedule_expression,
                            target_arn,
                            target_id,
                            config_ref):
        event_rule_template = aim.cftemplates.CWEventRule(
            self.aim_ctx,
            account_ctx,
            aws_region,
            stack_group,
            None, # stack_tags
            event_description,
            schedule_expression,
            target_arn,
            target_id,
            config_ref
        )

        self.event_stacks[config_ref] = event_rule_template.stack

    def validate(self):
        pass

    def provision(self):
        pass

    def delete(self):
        pass

    def get_event_stack(self, config_ref):
        return self.event_stacks[config_ref]

    def resolve_ref(self, ref):

        return None
