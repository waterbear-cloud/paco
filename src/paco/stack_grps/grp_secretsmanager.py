from paco.stack import StackOrder, Stack, StackGroup, StackTags
from paco.models import schemas
import paco.cftemplates


class SecretsManagerStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, env_ctx, config, stack_tags):
        super().__init__(
            paco_ctx,
            account_ctx,
            env_ctx.netenv.name,
            "Secrets",
            env_ctx
        )
        self.env_ctx = env_ctx
        self.region = self.env_ctx.region
        self.config = config
        self.config.resolve_ref_obj = self
        self.stack_tags = stack_tags

    def init(self):
        # Initialize resolve_ref_obj
        for app_config in self.config.values():
            for grp_config in app_config.values():
                for secret_config in grp_config.values():
                    secret_config.resolve_ref_obj = self
        self.secrets_stack = self.add_new_stack(
            self.region,
            self.config,
            paco.cftemplates.SecretsManager,
            stack_tags=StackTags(self.stack_tags),
        )

    def resolve_ref(self, ref):
        if schemas.ISecretsManagerSecret.providedBy(ref.resource):
            return self.secrets_stack
        return None
