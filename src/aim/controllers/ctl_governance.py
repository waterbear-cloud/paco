import click
import os
from aim.stack_group import MonitoringStackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller


class GovernanceController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Governance",
                         None)

        self.stack_grps = []
        self.init_done = False
        self.config = None

    def init(self, init_config):
        if self.init_done:
            return
        self.init_done = True
        return
        # Under Construction
        self.init_monitoring()

    def init_monitoring(self):
        mon_config = self.aim_ctx.project['governance']['Monitoring']

        account_ctx = self.aim_ctx.get_account_context(mon_config['account'])

        self.monitoring_stack_grp = MonitoringStackGroup(self.aim_ctx,
                                                        account_ctx,
                                                        mon_config,
                                                        self)

    def validate(self):
        pass
        #self.monitoring_stack_grp.validate()

    def provision(self):
        pass
        #self.monitoring_stack_grp.provision()