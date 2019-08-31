
class ResourceEngine():

    def __init__(self, app_engine):
        self.app_engine = app_engine

        self.aim_ctx = self.app_engine.aim_ctx
        self.parent_config_ref = self.app_engine.parent_config_ref
        self.aws_region = self.app_engine.aws_region
        self.stack_group = self.app_engine.stack_group
        self.account_ctx = self.app_engine.account_ctx
        self.env_ctx = self.app_engine.env_ctx
        self.app_id = self.app_engine.app_id
        self.gen_iam_role_id = self.app_engine.gen_iam_role_id
