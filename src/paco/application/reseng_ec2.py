import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class EC2ResourceEngine(ResourceEngine):

    def init_resource(self):
        paco.cftemplates.EC2(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_id,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.paco_ref_parts
        )
