from paco.stack import StackGroup
from paco.application.app_engine import ApplicationEngine


class ApplicationStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        env_ctx,
        app,
        stack_tags
    ):
        aws_name = '-'.join(['App', app.name])
        super().__init__(
            paco_ctx,
            account_ctx,
            app.name,
            aws_name,
            env_ctx
        )
        self.env_ctx = env_ctx
        self.app = app
        self.aws_region = self.env_ctx.region
        self.env_name = self.env_ctx.env.name
        self.stack_tags = stack_tags

    def init(self):
        self.app_engine = ApplicationEngine(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.app,
            self,
            'netenv',
            stack_tags=self.stack_tags,
            env_ctx=self.env_ctx
        )
        self.app_engine.init()

