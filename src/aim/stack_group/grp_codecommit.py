from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup
from aim.config import CodeCommitConfig
import aim.cftemplates
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class CodeCommitStackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 codecommit_config,
                 repo_list,
                 controller):

        super().__init__(aim_ctx,
                         account_ctx,
                         account_ctx.get_name(),
                         'Git',
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.config = codecommit_config
        self.stack_list = []
        self.config_ref_prefix = 'codecommit'
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.repo_list = repo_list

    def init(self):
        # CodeCommit Cross-Account Delegate Rol

        self.aim_ctx.log("StackGroup: CodeCommit: init")
        # CodeCommit Repository
        codecommit_template = aim.cftemplates.CodeCommit(self.aim_ctx,
                                                         self.account_ctx,
                                                         self.config,
                                                         self.repo_list)
        codecommit_stack = Stack(aim_ctx=self.aim_ctx,
                                 account_ctx=self.account_ctx,
                                 grp_ctx=self,
                                 stack_config=self.config,
                                 template=codecommit_template,
                                 aws_region=self.aws_region)

        codecommit_stack.set_termination_protection(True)
        self.stack_list.append(codecommit_stack)

        self.add_stack_order(codecommit_stack)

    def validate(self):
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
