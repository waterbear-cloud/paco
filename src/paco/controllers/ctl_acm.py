from paco.models.exceptions import InvalidPacoReference
from paco.controllers.controllers import Controller


class ACMController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "Resource", "ACM")
        self.cert_config_map = {}
        self.cert_config_list = []

    def init(self, command=None, model_obj=None):
        pass

    def validate(self):
        pass

    def provision(self):
        for acm_config in self.cert_config_list:
            acm_config['config'].stack.provision()

    def get_cert_config(self, group_id, cert_id):
        for config in self.cert_config_map[group_id]:
            if config['id'] == cert_id:
                return config
        return None

    def add_certificate_config(self, account_ctx, region, group_id, cert_id, cert_config):
        if group_id not in self.cert_config_map.keys():
            self.cert_config_map[group_id] = []
        map_config = {
            'group_id': group_id,
            'id': cert_id,
            'config': cert_config,
            'account_ctx': account_ctx,
            'region': region
        }
        self.cert_config_map[group_id].append(map_config)
        self.cert_config_list.append(map_config)
        cert_config.resolve_ref_obj = self
