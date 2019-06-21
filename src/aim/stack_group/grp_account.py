from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup
from aim import models
from aim.models import schemas
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
import aim.cftemplates


class AccountStackGroup(StackGroup):
    def __init__(self, aim_ctx, account_ctx, account_id, account_config, stack_hooks, controller):

        super().__init__(aim_ctx,
                         account_ctx,
                         account_id,
                         "Configuration",
                         controller)

        self.account_id = account_id
        self.account_config = account_config
        self.account_config_ref = 'config.ref accounts.%s' % (account_id)
        self.stack_hooks = stack_hooks

    def init(self):
        # Network Stack Templates
        if self.account_config.admin_iam_users == None:
            print("Account Group: %s *disabeld no admin_iam_users*" % (self.account_id))
            return
        print("Account Group: %s" % (self.account_id))
        # VPC Stack
        account_template = aim.cftemplates.Account(self.aim_ctx,
                                                   self.account_ctx,
                                                   self.account_id,
                                                   self.account_config,
                                                   self.account_config_ref)

        self.account_stack = Stack(aim_ctx=self.aim_ctx,
                                    account_ctx=self.account_ctx,
                                    grp_ctx=self,
                                    stack_config=self.account_config,
                                    template=account_template,
                                    aws_region=self.account_config.region,
                                    hooks=self.stack_hooks)

        self.add_stack_order(self.account_stack)

        print("Account Group Init: Completed")

    def resolve_ref(self, ref):
        raise StackException(AimErrorCode.Unknown)

    def validate(self):
        # Generate Stacks
        # VPC Stack
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
