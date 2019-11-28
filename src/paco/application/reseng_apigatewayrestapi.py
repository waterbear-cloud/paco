import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class ApiGatewayRestApiResourceEngine(ResourceEngine):

    def init_resource(self):
        paco.cftemplates.ApiGatewayRestApi(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.paco_ref_parts
        )
