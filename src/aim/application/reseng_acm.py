import aim.cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class ACMResourceEngine(ResourceEngine):

    def init_resource(self):
        acm_ctl = self.aim_ctx.get_controller('ACM')
        cert_group_id = self.resource.aim_ref_parts
        acm_ctl.add_certificate_config(
            self.account_ctx,
            self.aws_region,
            cert_group_id,
            self.res_id,
            self.resource
        )
