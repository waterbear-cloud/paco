import troposphere
import troposphere.secretsmanager

from paco import utils
from paco.cftemplates.cftemplates import CFTemplate

class SecretsManager(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        secrets_config,
        config_ref
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('SecretsManager')
        self.init_template('Secrets Manager')
        self.paco_ctx.log_action_col("Init", "Secrets", "Manager")

        is_enabled = False
        for secret_app in secrets_config.values():
            for secret_group in secret_app.values():
                for secret_name in secret_group.keys():
                    secret_config = secret_group[secret_name]
                    if secret_config.is_enabled() == False:
                        continue
                    is_enabled = True
                    secret_hash = utils.md5sum(str_data=secret_config.paco_ref_parts)

                    # Secret resource
                    cfn_export_dict = {
                        'Name': secret_config.paco_ref_parts
                    }
                    if secret_config.generate_secret_string.enabled:
                        cfn_export_dict['GenerateSecretString'] = secret_config.generate_secret_string.cfn_export_dict
                    else:
                        # Secret will be changed later
                        cfn_export_dict['SecretString'] = 'placeholder'
                    secret_resource = troposphere.secretsmanager.Secret.from_dict(
                        self.create_cfn_logical_id('Secret' + secret_hash),
                        cfn_export_dict
                    )
                    self.template.add_resource(secret_resource)

                    # Secret resource Output
                    secret_arn_output_logical_id = self.create_cfn_logical_id('Secret' + secret_hash + 'Arn')
                    self.template.add_output(
                        troposphere.Output(
                            title=secret_arn_output_logical_id,
                            Value=troposphere.Ref(secret_resource)
                        )
                    )
                    self.register_stack_output_config(
                        secret_config.paco_ref_parts + '.arn',
                        secret_arn_output_logical_id
                    )

        self.enabled = is_enabled
        self.set_template(self.template.to_yaml())


