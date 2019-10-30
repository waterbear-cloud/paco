import troposphere
import troposphere.secretsmanager

from aim import utils
from aim.cftemplates.cftemplates import CFTemplate

class SecretsManager(CFTemplate):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        secrets_config,
        config_ref):
        #aim_ctx.log("Route53 CF Template init")
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('SecretsManager')

        self.init_template('Secrets Manager')

        self.aim_ctx.log_action_col("Init", "Secrets", "Manager")

        is_enabled = False
        for secret_app in secrets_config.values():
            for secret_group in secret_app.values():
                for secret_name in secret_group.keys():
                    secret_config = secret_group[secret_name]
                    if secret_config.is_enabled() == False:
                        continue
                    is_enabled = True
                    secret_hash = utils.md5sum(str_data=secret_config.aim_ref_parts)
                    secret_res = troposphere.secretsmanager.Secret(
                        title=self.create_cfn_logical_id('Secret'+secret_hash),
                        template=self.template,
                        Name=secret_config.aim_ref_parts,
                        SecretString='placeholder' # Will be changed later
                    )
                    secret_arn_output_logical_id = self.create_cfn_logical_id('Secret'+secret_hash+'Arn')
                    self.template.add_output(
                        troposphere.Output(
                            title=secret_arn_output_logical_id,
                            Value=troposphere.Ref(secret_res)
                        )
                    )
                    self.register_stack_output_config(secret_config.aim_ref_parts+'.arn', secret_arn_output_logical_id)

        self.enabled = is_enabled
        self.set_template(self.template.to_yaml())


