from paco.core.exception import StackException
from paco.controllers.controllers import Controller
from paco.aws_api.iot.iotpolicy import IoTPolicyClient

class IoTPolicyController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "Resource", "IoTPolicy")
        self.iotpolicy_list = []
        self.iotpolicy_map = {}

    def init(self, command=None, model_obj=None):
        pass

    def validate(self):
        pass

    def provision(self, scope=None):
        """
        Creates an IoT Policy if it does not exist, otherwise
        update the PolicyStatement with a new version if it's changed.
        """
        for iotpolicy_dict in self.iotpolicy_list:
            account_ctx = iotpolicy_dict['account_ctx']
            aws_region = iotpolicy_dict['aws_region']
            iotpolicy = iotpolicy_dict['iotpolicy']
            if not iotpolicy.paco_ref_parts.startswith(scope):
                continue
            if iotpolicy.is_enabled() == False:
                continue
            iotpolicyclient = IoTPolicyClient(self.paco_ctx.project, account_ctx, aws_region, iotpolicy)
            if not iotpolicyclient.policy_exists():
                self.paco_ctx.log_action_col(
                    'Provision',
                    'Create',
                    account_ctx.name + '.' + aws_region,
                    'boto3: ' + iotpolicy.get_aws_name(),
                    enabled=iotpolicy.is_enabled(),
                    col_2_size=9
                )
                iotpolicyclient.create_policy()
            else:
                if not iotpolicyclient.is_policy_document_same():
                    iotpolicyclient.update_policy_document()
                    self.paco_ctx.log_action_col(
                        'Provision',
                        'Update',
                        account_ctx.name + '.' + aws_region,
                        'boto3: ' + iotpolicy.get_aws_name(),
                        col_2_size=9
                    )
                else:
                    self.paco_ctx.log_action_col(
                        'Provision',
                        'Cache',
                        account_ctx.name + '.' + aws_region,
                        'boto3: ' + iotpolicy.get_aws_name(),
                        col_2_size=9
                    )

    def add_iotpolicy(self, account_ctx, aws_region, iotpolicy):
        "Add an IoTPolicy resource to the controller"
        iotpolicy.resolve_ref_obj = self
        map_config = {
            'iotpolicy': iotpolicy,
            'account_ctx': account_ctx,
            'aws_region': aws_region,
        }
        self.iotpolicy_map[iotpolicy.paco_ref_parts] = map_config
        self.iotpolicy_list.append(map_config)
