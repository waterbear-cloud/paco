from aim.config.config import Config
import os
import copy


class ACMConfig(Config):
    def __init__(self, aim_ctx, account_ctx, name, config=None):
        # config/Services/ACM.yaml
        config_folder = os.path.join(aim_ctx.config_folder, "Services")
        super().__init__(aim_ctx, config_folder, "ACM")
        self.name = name
        self.account_ctx = account_ctx
        if config != None:
            self.config = config[name]

    def load(self):
        # This is unexpected territory
        super().load()
        config_dict = self.config_dict[self.name]
        self.config_dict = config_dict

    def enabled(self, cert_id):
        if 'enabled' not in self.config_dict[cert_id]:
            return False
        return self.config_dict[cert_id].enabled

    # AIM Ids, not Certificate ARN
    def get_certificate_ids(self):
        if self.config_dict != None:
            return self.config_dict.keys()
        return None

    def get_certificate_domain(self, cert_id):
        if self.config_dict != None:
            return self.config_dict[cert_id].domain_name
        return None

    def get_subject_alternative_names(self, cert_id):
        if self.config_dict != None:
            return self.config_dict[cert_id].subject_alternative_names
        return None

#    def add_certificate_config(self, cert_id, config_dict):
#        self.config_dict[cert_id] = config_dict
