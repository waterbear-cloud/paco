from paco import cftemplates
from paco.application.res_engine import ResourceEngine

class EIPResourceEngine(ResourceEngine):

    def init_resource(self):
        # ElastiCache Redis CloudFormation
        cftemplates.EIP(
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
