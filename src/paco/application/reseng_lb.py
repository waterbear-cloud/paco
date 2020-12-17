import paco.cftemplates
from paco.application.res_engine import ResourceEngine


class LBApplicationResourceEngine(ResourceEngine):

    def init_resource(self):
        # Set resolve_ref object for TargetGroups
        for target_group in self.resource.target_groups.values():
            target_group.resolve_ref_obj = self.app_engine
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ALB,
            stack_tags=self.stack_tags,
            extra_context={'env_ctx': self.env_ctx, 'app_id': self.app_id}
        )

class LBNetworkResourceEngine(ResourceEngine):

    def init_resource(self):
        # Set resolve_ref object for TargetGroups
        for target_group in self.resource.target_groups.values():
            target_group.resolve_ref_obj = self.app_engine
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.NLB,
            stack_tags=self.stack_tags,
            extra_context={'env_ctx': self.env_ctx, 'app_id': self.app_id}
        )