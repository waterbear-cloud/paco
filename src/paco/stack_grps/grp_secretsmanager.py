from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags
from paco.models import schemas
from pprint import pprint
import paco.cftemplates


class SecretsManagerStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, env_ctx, config, stack_tags):
        super().__init__(
            paco_ctx,
            account_ctx,
            env_ctx.netenv_id,
            "Secrets",
            env_ctx
        )
        self.env_ctx = env_ctx
        self.config_ref_prefix = self.env_ctx.config_ref_prefix
        self.region = self.env_ctx.region
        self.config = config
        self.config.resolve_ref_obj = self
        self.stack_tags = stack_tags

    def log_init_status(self, name, description, is_enabled):
        "Logs the init status of a secrets manager component"
        self.paco_ctx.log_action_col('Init', 'Secrets', name, description, enabled=is_enabled)

    def init(self):
        # Network Stack Templates
        # VPC Stack
        self.log_init_status('Secrets', '', True)
        # Initialize resolve_ref_obj
        for app_config in self.config.values():
            for grp_config in app_config.values():
                for secret_config in grp_config.values():
                    secret_config.resolve_ref_obj = self
        secrets_template = paco.cftemplates.SecretsManager(
            self.paco_ctx,
            self.account_ctx,
            self.region,
            self, # stack_group
            StackTags(self.stack_tags),
            self.config,
            self.config.paco_ref_parts)
        self.secrets_stack = secrets_template.stack

    def resolve_ref(self, ref):
        if schemas.ISecretsManagerSecret.providedBy(ref.resource):
            return self.secrets_stack
        return None

    def validate(self):
        # Generate Stacks
        # VPC Stack
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
