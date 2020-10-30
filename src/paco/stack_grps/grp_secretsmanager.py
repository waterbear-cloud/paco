from troposphere import Not
from paco.stack import StackOrder, Stack, StackGroup, StackTags
from paco.models import schemas
from paco.models import references
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
        self.secrets_stack = {}
        self.secret_account_lookup = {}

    def init(self):
        # Initialize resolve_ref_obj and accounts
        accounts = {}
        for app_config in self.config.values():
            for grp_config in app_config.values():
                for secret in grp_config.values():
                    secret.resolve_ref_obj = self
                    if secret.account != None:
                        secret._account_ref = secret.account
                        accounts[secret._account_ref] = True
                        self.secret_account_lookup[secret.paco_ref] = secret._account_ref
                    else:
                        secret._account_ref = self.account_ctx.paco_ref
                        accounts[secret._account_ref] = True
                        self.secret_account_lookup[secret.paco_ref] = secret._account_ref

        for account_ref in accounts.keys():
            self.secrets_stack[account_ref] = self.add_new_stack(
                self.region,
                self.config,
                paco.cftemplates.SecretsManager,
                account_ctx=self.paco_ctx.get_account_context(account_ref),
                stack_tags=StackTags(self.stack_tags),
            )

    def resolve_ref(self, ref):
        ref_obj = ref
        if isinstance(ref, str):
            ref_obj = references.Reference(ref)
        base_ref_obj = ref_obj.secret_base_ref()
        return self.secrets_stack[self.secret_account_lookup[base_ref_obj.raw]]
