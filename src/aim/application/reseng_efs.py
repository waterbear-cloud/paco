from aim import models, cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class EFSResourceEngine(ResourceEngine):

    def init_resource(self, grp_id, res_id, res_config, res_stack_tags, env_ctx):
          # ElastiCache Redis CloudFormation
        aws_name = '-'.join([grp_id, res_id])
        cftemplates.EFS(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,

            aws_name,
            env_ctx,
            self.app_id,
            grp_id,
            res_config,
            res_config.aim_ref_parts
        )
