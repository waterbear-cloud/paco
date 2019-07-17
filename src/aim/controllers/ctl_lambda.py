import os
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
import aim.cftemplates
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks

class LambdaController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "Lambda")

        self.init_done = False
        self.permission_stacks = {}

        if not 'lambda' in self.aim_ctx.project:
            self.init_done = True
            return
        self.config = self.aim_ctx.project['lambda']
        if self.config != None:
            self.config.resolve_ref_obj = self

        #self.aim_ctx.log("Route53 Service: Configuration: %s" % (name)

    def init(self, init_config):
        if self.init_done:
            return
        self.config.resolv_ref_obj = self
        self.init_done = True

    def add_permission( self,
                        aim_ctx,
                        account_ctx,
                        aws_region,
                        stack_group,
                        config_ref,
                        function_name,
                        principal,
                        source_account,
                        source_arn):
        permission_template = aim.cftemplates.LambdaPermission( self.aim_ctx,
                                                                account_ctx,
                                                                aws_region,
                                                                function_name,
                                                                principal,
                                                                source_account,
                                                                source_arn,
                                                                config_ref)



        permission_stack = Stack(   self.aim_ctx,
                                    account_ctx,
                                    stack_group,
                                    self,
                                    permission_template,
                                    aws_region=aws_region,
                                    hooks=None)

        self.permission_stacks[config_ref] = permission_stack
        stack_group.add_stack_order(permission_stack)

    def validate(self):
        pass

    def provision(self):
        pass

    def delete(self):
        pass

    def get_permission_stack(self, config_ref):
        return self.permission_stacks[config_ref]

    def resolve_ref(self, ref):

        return None
