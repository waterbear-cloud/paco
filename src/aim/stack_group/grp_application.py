from aim.stack_group import StackGroup, StackTags
from aim.core.yaml import YAML
from aim.application.app_engine import ApplicationEngine

yaml=YAML()
yaml.default_flow_sytle = False

class ApplicationStackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 subenv_ctx,
                 app_id,
                 stack_tags):
        aws_name = '-'.join(['App', app_id])
        super().__init__(aim_ctx,
                         account_ctx,
                         app_id,
                         aws_name,
                         subenv_ctx)

        self.subenv_ctx = subenv_ctx
        self.app_id = app_id
        #self.netenv_config = netenv_ctx.config
        self.config_ref_prefix = self.subenv_ctx.config_ref_prefix
        self.aws_region = self.subenv_ctx.region
        self.subenv_id = self.subenv_ctx.subenv_id
        self.stack_tags = stack_tags

    def init(self):
               # Old config_ref
        #str.join('.',[self.subenv_ctx.netenv_id,
    #                                self.subenv_id,
    #                                'applications',
    #                                 self.app_id])
        self.app_engine = ApplicationEngine( self.aim_ctx,
                                             self.account_ctx,
                                             self.aws_region,
                                             self.app_id,
                                             self.subenv_ctx.config.applications[self.app_id],
                                             self.config_ref_prefix,
                                             self,
                                             'netenv',
                                             stack_tags=self.stack_tags,
                                             subenv_ctx=self.subenv_ctx)
        self.app_engine.init()

    def validate(self):
        super().validate()

    def provision(self):
        # Provision any SSL Cerificates
        acm_ctl = self.aim_ctx.get_controller('ACM')
        acm_ctl.provision()

        # Provison Application Group
        super().provision()

    def delete(self):
        super().delete()


