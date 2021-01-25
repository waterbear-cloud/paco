from paco import cftemplates
from paco.application.res_engine import ResourceEngine


class ECRRepositoryResourceEngine(ResourceEngine):
    def init_resource(self):
        account_ctx = self.account_ctx
        if hasattr(self.resource, 'account') and self.resource.account != None:
            account_ctx = self.paco_ctx.get_account_context(account_ref=self.resource.account)
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.ECRRepository,
            stack_tags=self.stack_tags,
            account_ctx=account_ctx,
        )
