from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.secretsmanager


class SecretsManager(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        secrets_config = stack.resource
        config_ref = secrets_config.paco_ref_parts
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        self.set_aws_name('SecretsManager')
        self.init_template('Secrets Manager')

        is_enabled = False
        account_ref = self.account_ctx.paco_ref
        for secret_app in secrets_config.values():
            for secret_group in secret_app.values():
                for secret_name in secret_group.keys():
                    secret_config = secret_group[secret_name]
                    if secret_config.is_enabled() == False:
                        continue
                    # Secrets only created in the accounts they are declared/assumed
                    if secret_config._account_ref != account_ref:
                        continue
                    is_enabled = True
                    secret_hash = utils.md5sum(str_data=secret_config.paco_ref_parts)

                    # Secret resource
                    cfn_export_dict = {
                        'Name': secret_config.paco_ref_parts
                    }
                    if secret_config.generate_secret_string != None and secret_config.generate_secret_string.enabled:
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
                    self.create_output(
                        title=self.create_cfn_logical_id('Secret' + secret_hash + 'Arn'),
                        value=troposphere.Ref(secret_resource),
                        ref=secret_config.paco_ref_parts + '.arn'
                    )

        self.set_enabled(is_enabled)

    def warn_template_changes(self, deep_diff):
        """Inform the user about changes to generate_secret_string making new secrets"""
        for change in deep_diff.values():
            for diff_level in change:
                if 'GenerateSecretString' in diff_level.path():
                    print("WARNING: About to change the generate_secret_string CloudFormation for Secret(s).")
                    print("Applying this change will cause the existing Secret(s) to be re-generated!")
                    return


