from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.controllers.controllers import Controller
from paco.core.exception import PacoStateError
from paco.models.references import Reference
from paco.utils import md5sum
import copy
import json


yaml=YAML()
yaml.default_flow_sytle = False

class IAMRoleResourceEngine(ResourceEngine):

    def init_resource(self):
        # IAM User
        if self.resource.account != None:
            self.account_ctx = self.paco_ctx.get_account_context(account_ref=self.resource.account)

        iam_ctl = self.paco_ctx.get_controller('IAM')

        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=self.resource,
            iam_role_id=self.resource.paco_ref_parts,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags
        )