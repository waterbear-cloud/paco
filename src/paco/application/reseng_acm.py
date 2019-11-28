import paco.cftemplates
from paco.application.res_engine import ResourceEngine

class ACMResourceEngine(ResourceEngine):

    def init_resource(self):
        acm_ctl = self.paco_ctx.get_controller('ACM')
        cert_group_id = self.resource.paco_ref_parts
        acm_ctl.add_certificate_config(
            self.account_ctx,
            self.aws_region,
            cert_group_id,
            self.res_id,
            self.resource
        )
