import aim.cftemplates
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class MonitoringStackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 mon_config,
                 controller):

        super().__init__(aim_ctx,
                         account_ctx,
                         account_ctx.get_name(),
                         'Monitoring',
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.config = mon_config
        self.stack_list = []
        self.config_ref_prefix = 'monitoring'
        self.account_ctx = account_ctx
        self.aws_region = self.config.aws_region

    def init(self):
        # Monitoring
        self.aim_ctx.log("StackGroup: Governance: Monitoring: init")
        # Lambda Monitoring Service
        # Monitoring Repository
        for [res_id, res_config] in self.config.resources.items():
            if res_config.type == 'Lambda':
                config_ref = '.'.join([self.config_ref, 'resources', res_id])
                aws_name = 'Res-'+res_id
                lambda_template = aim.cftemplates.Lambda(self.aim_ctx,
                                                        self.account_ctx,
                                                        aws_name,
                                                        self.config,
                                                        config_ref)
                lambda_stack = Stack(aim_ctx=self.aim_ctx,
                                account_ctx=self.account_ctx,
                                grp_ctx=self,
                                stack_config=self.config,
                                template=lambda_template,
                                aws_region=self.aws_region)

                lambda_stack.set_termination_protection(True)
                self.stack_list.append(lambda_stack)
                self.add_stack_order(lambda_stack)

    def validate(self):
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
