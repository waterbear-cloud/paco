from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class ECRRepositoryResourceEngine(ResourceEngine):
    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.ECRRepository,
            stack_tags=self.stack_tags,
            # Default to using the Tools account
            account_ctx=self.paco_ctx.get_account_context(account_ref='paco.ref accounts.tools')
        )
