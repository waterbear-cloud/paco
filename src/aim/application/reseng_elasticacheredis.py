from aim import models, cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class ElastiCacheRedisResourceEngine(ResourceEngine):

    def init_resource(self):
        # ElastiCache Redis CloudFormation
        cftemplates.ElastiCache(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.aim_ref_parts
        )
