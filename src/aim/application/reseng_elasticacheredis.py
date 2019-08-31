from aim import models, cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class ElastiCacheRedisResourceEngine(ResourceEngine):

    def init_resource(self, grp_id, res_id, res_config, res_stack_tags):
          # ElastiCache Redis CloudFormation
        aws_name = '-'.join([grp_id, res_id])
        cftemplates.ElastiCache(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,

            aws_name,
            self.app_id,
            grp_id,
            res_config,
            res_config.aim_ref_parts
        )
