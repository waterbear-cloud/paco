from paco import cftemplates
from paco.application.res_engine import ResourceEngine

class DashboardResourceEngine(ResourceEngine):

    def init_resource(self):
        # CloudWatch Dashboard CloudFormation
        cftemplates.CloudWatchDashboard(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource
        )
