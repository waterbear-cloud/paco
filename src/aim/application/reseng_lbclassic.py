import aim.cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class LBClassicResourceEngine(ResourceEngine):

    def init_resource(self):
        elb_config = self.resource[res_id]
        aws_name = '-'.join([self.grp_id, self.res_id])
        aim.cftemplates.ELB(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            elb_config,
            self.resource.aim_ref_parts
        )