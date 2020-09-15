from paco.stack import StackGroup
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode


class AccountStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, account_name, account_config, stack_hooks, controller):
        super().__init__(
            paco_ctx,
            account_ctx,
            account_name,
            "Configuration",
            controller
        )
        self.account_name = account_name
        self.account_config = account_config
        self.account_config_ref = f'paco.ref accounts.{account_name}'
        self.stack_hooks = stack_hooks

    def init(self, do_not_cache=False):
        pass

    def resolve_ref(self, ref):
        raise StackException(PacoErrorCode.Unknown)
