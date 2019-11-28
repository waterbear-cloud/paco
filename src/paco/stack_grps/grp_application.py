from paco.stack_group import StackGroup, StackTags
from paco.core.yaml import YAML
from paco.application.app_engine import ApplicationEngine

yaml=YAML()
yaml.default_flow_sytle = False

class ApplicationStackGroup(StackGroup):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 env_ctx,
                 app_id,
                 stack_tags):
        aws_name = '-'.join(['App', app_id])
        super().__init__(paco_ctx,
                         account_ctx,
                         app_id,
                         aws_name,
                         env_ctx)

        self.env_ctx = env_ctx
        self.app_id = app_id
        #self.netenv_config = netenv_ctx.config
        self.config_ref_prefix = self.env_ctx.config_ref_prefix
        self.aws_region = self.env_ctx.region
        self.env_id = self.env_ctx.env_id
        self.stack_tags = stack_tags

    def init(self):
               # Old config_ref
        #str.join('.',[self.env_ctx.netenv_id,
    #                                self.env_id,
    #                                'applications',
    #                                 self.app_id])
        self.app_engine = ApplicationEngine( self.paco_ctx,
                                             self.account_ctx,
                                             self.aws_region,
                                             self.app_id,
                                             self.env_ctx.config.applications[self.app_id],
                                             self.config_ref_prefix,
                                             self,
                                             'netenv',
                                             stack_tags=self.stack_tags,
                                             env_ctx=self.env_ctx)
        self.app_engine.init()

    def validate(self):
        super().validate()

    def provision(self):
        # Provision any SSL Cerificates
        acm_ctl = self.paco_ctx.get_controller('ACM')
        acm_ctl.provision()

        # Provison Application Group
        super().provision()

    def delete(self):
        super().delete()


