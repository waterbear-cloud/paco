from aim.config.config import Config
import os
import copy


class AccountConfig(Config):
    def __init__(self, aim_ctx, account_name):
        #aim_ctx.log("S3Config Init")

        config_folder = os.path.join(aim_ctx.config_folder, "Services")
        super().__init__(aim_ctx, aim_ctx.config_folder, "accounts")
        self.name = account_name
        super().load()
        self.config_dict = self.config_dict[account_name]

    def account_name(self):
        return self.name

    def aws_profile(self):
        return self.config_dict['aws_profile']

    def account_id(self):
        return self.config_dict['account_id']

    def admin_delegate_role_name(self):
        return self.config_dict['admin_delegate_role_name']

    def mfa_account_id(self):
        return self.config_dict['mfa_account_id']

    def mfa_iam_user_name(self):
        return self.config_dict['mfa_iam_user_name']

    def admin_delegate_role_arn(self):
        return 'arn:aws:iam::' + str(self.account_id()) + ':role/' + self.admin_delegate_role_name()

    def mfa_role_arn(self):
        return 'arn:aws:iam::' + str(self.mfa_account_id()) + ':mfa/' + self.mfa_iam_user_name()
