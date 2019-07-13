import aim.cftemplates
import json
import os
import pathlib
import tarfile
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.models import loader, vocabulary
from aim import models
from aim.core.yaml import YAML
from aim.application.app_engine import ApplicationEngine

yaml=YAML()
yaml.default_flow_sytle = False

class ApplicationStackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 subenv_ctx,
                 app_id):
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
                                             'netenv.ref',
                                             self.subenv_ctx)
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

    def OLD_get_app_grp_res(self, ref):
        app_idx = ref.parts.index('applications')
        grp_idx = ref.parts.index('groups')
        res_idx = ref.parts.index('resources')

        app_id = ref.parts[app_idx+1]
        grp_id = ref.parts[grp_idx+1]
        res_id = ref.parts[res_idx+1]
        return [app_id, grp_id, res_id]

