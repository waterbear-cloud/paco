import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class LBClassicResourceEngine(ResourceEngine):

    def init_resource(self):
        elb_config = self.resource[res_id]
        aws_name = '-'.join([self.grp_id, self.res_id])
        paco.cftemplates.ELB(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            elb_config,
            self.resource.paco_ref_parts
        )