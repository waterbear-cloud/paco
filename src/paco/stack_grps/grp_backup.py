from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags
import paco.cftemplates


class BackupVaultsStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        env_ctx,
        config,
        stack_tags
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            env_ctx.netenv_id,
            "BackupVaults",
            env_ctx
        )
        self.env_ctx = env_ctx
        self.config_ref_prefix = self.env_ctx.config_ref_prefix
        self.region = self.env_ctx.region
        self.config = config
        self.config.resolve_ref_obj = self
        self.stack_tags = stack_tags
        self.stack_list = []

    def log_init_status(self, name, description, is_enabled):
        "Logs the init status of BackupVaults"
        self.paco_ctx.log_action_col('Init', 'Backup', name, description, enabled=is_enabled)

    def create_iam_role(self):
        "Backup service Role"
        # if at least one vault is enabled, create an IAM Role
        vaults_enabled = False
        for vault in self.config.values():
            if vault.is_enabled():
                vaults_enabled = True
        if not vaults_enabled:
            return None

        role_name = "BackupService"
        policy_arns = [
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup',
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores'
        ]

        role_dict = {
            'enabled': True,
            'path': '/',
            'role_name': role_name,
            'managed_policy_arns': policy_arns,
            'assume_role_policy': {'effect': 'Allow', 'service': ['backup.amazonaws.com']}
        }
        role = paco.models.iam.Role(role_name, self.config)
        role.apply_config(role_dict)

        iam_role_ref = self.config.paco_ref_parts + '.' + role_name
        iam_role_id = 'Backup-' + self.env_ctx.env_id + '-' + role_name
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            paco_ctx=self.paco_ctx,
            account_ctx=self.account_ctx,
            region=self.env_ctx.region,
            group_id='',
            role_id=iam_role_id,
            role_ref=iam_role_ref,
            role_config=role,
            stack_group=self,
            template_params=None,
            stack_tags=StackTags(self.stack_tags)
        )
        return role

    def init(self):
        self.log_init_status('Backup', '', True)
        role = self.create_iam_role()
        for backup_vault in self.config.values():
            backup_vault.resolve_ref_obj = self
            backup_vault_template = paco.cftemplates.BackupVault(
                self.paco_ctx,
                self.account_ctx,
                self.region,
                self, # stack_group
                StackTags(self.stack_tags),
                backup_vault,
                role
            )
            self.stack_list.append(
                backup_vault_template.stack
            )
