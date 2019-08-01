import os
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
import aim.cftemplates
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks

class CloudWatchController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
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
        event_template = aim.cftemplates.CWEventRule( self.aim_ctx,
                                                      account_ctx,
                                                      aws_region,
                                                      event_description,
                                                      schedule_expression,
                                                      target_arn,
                                                      target_id,
                                                      config_ref)


        event_stack = Stack(self.aim_ctx,
                            account_ctx,
                            stack_group,
                            self,
                            event_template,
                            aws_region=aws_region,
                            hooks=None)

        self.event_stacks[config_ref] = event_stack
        stack_group.add_stack_order(event_stack)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def delete(self):
        pass

    def get_event_stack(self, config_ref):
        return self.event_stacks[config_ref]

    def resolve_ref(self, ref):

        return None
