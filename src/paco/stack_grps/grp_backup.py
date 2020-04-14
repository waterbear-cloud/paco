from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.stack import StackOrder, Stack, StackGroup, StackTags
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
            env_ctx.netenv.name,
            "BackupVaults",
            env_ctx
        )
        self.env_ctx = env_ctx
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
        # BackupVault will create one IAM Role for each NetworkEnvironment/Environment combination,
        # this way a netenv/env can be created, have it's own Role, then a different netenv/env with a second Role
        # if the first netenv/env is deleted, the second one will not be impacted.
        vaults_enabled = False
        for vault in self.config.values():
            if vault.is_enabled():
                vaults_enabled = True
        if not vaults_enabled:
            return None

        netenv = get_parent_by_interface(self.config, schemas.INetworkEnvironment)
        iam_role_id = 'Backup-{}-{}'.format(netenv.name, self.env_ctx.env.name)
        policy_arns = [
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup',
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores'
        ]
        role_dict = {
            'enabled': True,
            'path': '/',
            'role_name': iam_role_id,
            'managed_policy_arns': policy_arns,
            'assume_role_policy': {'effect': 'Allow', 'service': ['backup.amazonaws.com']}
        }
        role = paco.models.iam.Role(iam_role_id, self.config)
        role.apply_config(role_dict)

        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.env_ctx.region,
            resource=self.config,
            role=role,
            iam_role_id=iam_role_id,
            stack_group=self,
            stack_tags=StackTags(self.stack_tags)
        )
        return role

    def init(self):
        self.log_init_status('Backup', '', True)
        role = self.create_iam_role()
        for backup_vault in self.config.values():
            backup_vault.resolve_ref_obj = self
            stack = self.add_new_stack(
                self.region,
                backup_vault,
                paco.cftemplates.BackupVault,
                stack_tags=StackTags(self.stack_tags),
                extra_context={'role': role}
            )
            self.stack_list.append(stack)
