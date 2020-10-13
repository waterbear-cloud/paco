from paco.aws_api.iot.iotpolicy import IoTPolicyClient
from paco.stack.botostack import BotoStack


class IoTPolicyBotoStack(BotoStack):

    def init(self):
        "Prepare Resource State"
        self.register_stack_output_config(self.stack_ref + '.arn', 'IoTPolicyArn')
        self.enabled = self.resource.is_enabled()

    def get_outputs(self):
        "Get all Outputs of a Resource"
        return {'IoTPolicyArn': self.policy_arn}

    def provision(self):
        """
        Creates an IoT Policy if it does not exist, otherwise
        update the PolicyStatement with a new version if it's changed.
        """
        if not self.enabled:
            return

        iotpolicyclient = IoTPolicyClient(
            self.paco_ctx.project,
            self.account_ctx,
            self.aws_region,
            self.resource
        )
        self.policy_arn = iotpolicyclient.policy_exists()
        if not self.policy_arn:
            self.paco_ctx.log_action_col(
                'Provision',
                'Create',
                self.account_ctx.name + '.' + self.aws_region,
                'boto3: ' + self.resource.get_aws_name(),
                enabled=self.enabled,
                col_2_size=9
            )
            iotpolicyclient.create_policy()
        else:
            if not iotpolicyclient.is_policy_document_same():
                iotpolicyclient.update_policy_document()
                self.paco_ctx.log_action_col(
                    'Provision',
                    'Update',
                    self.account_ctx.name + '.' + self.aws_region,
                    'boto3: ' + self.resource.get_aws_name(),
                    col_2_size=9
                )
            else:
                self.paco_ctx.log_action_col(
                    'Provision',
                    'Cache',
                    self.account_ctx.name + '.' + self.aws_region,
                    'boto3: ' + self.resource.get_aws_name(),
                    col_2_size=9
                )
