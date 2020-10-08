from paco.models.exceptions import InvalidPacoReference
from paco.controllers.controllers import Controller


class ACMController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "Resource",
            "ACM"
        )

    def init(self, command=None, model_obj=None):
        pass

    def validate(self):
        pass

    def provision(self):
        pass

    def get_cert_config(self, group_id, cert_id):
        for config in self.cert_config_map[group_id]:
            if config['id'] == cert_id:
                return config
        return None

    # def resolve_ref(self, ref):
    #     if ref.last_part == 'arn':
    #         breakpoint()
    #         # group_id = '.'.join(ref.parts[:-1])
    #         # cert_id = ref.parts[-2]
    #         # res_config = self.get_cert_config(group_id, cert_id)
    #         # if 'cert_arn_cache' in res_config.keys():
    #         #     return res_config['cert_arn_cache']

    #         # # create a BotoStack, initialize and return it
    #         # acmstack = ACMBotoStack(
    #         #     self.paco_ctx,
    #         #     res_config['account_ctx'],
    #         #     None, # do not need StackGroup?
    #         #     res_config['config'],
    #         #     aws_region=ref.region,
    #         # )
    #         # acmstack.init()
    #         # return acmstack

    #     raise InvalidPacoReference(f"Could not resolve reference to ACM Certificate.\n{ref.raw}")

