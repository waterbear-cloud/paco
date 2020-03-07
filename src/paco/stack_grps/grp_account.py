from paco.stack import StackOrder, Stack, StackGroup
from paco.models import schemas
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
import paco.cftemplates


class AccountStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, account_id, account_config, stack_hooks, controller):
        super().__init__(
            paco_ctx,
            account_ctx,
            account_id,
            "Configuration",
            controller
        )
        self.account_id = account_id
        self.account_config = account_config
        self.account_config_ref = 'paco.ref accounts.%s' % (account_id)
        self.stack_hooks = stack_hooks

    def init(self, do_not_cache=False):
        pass

    def resolve_ref(self, ref):
        raise StackException(PacoErrorCode.Unknown)
