from aim import models, cftemplates
from aim.application.res_engine import ResourceEngine

class EIPResourceEngine(ResourceEngine):

    def init_resource(self):
        # ElastiCache Redis CloudFormation
        cftemplates.EIP(
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
