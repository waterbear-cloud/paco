import aim.cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class LBApplicationResourceEngine(ResourceEngine):

    def init_resource(self):
        # resolve_ref object for TargetGroups
        for target_group in self.resource.target_groups.values():
            target_group.resolve_ref_obj = self.app_engine
        aim.cftemplates.ALB(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.aim_ref_parts
        )
