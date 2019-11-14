import aim.cftemplates
from aim.application.res_engine import ResourceEngine

class CodeDeployApplicationResourceEngine(ResourceEngine):

    def init_resource(self):
        aws_name = '-'.join([self.grp_id, self.res_id])
        aim.cftemplates.CodeDeployApplication(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.resource
        )
