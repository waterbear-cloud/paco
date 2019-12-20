from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup
from paco.models import schemas
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
import paco.cftemplates


class AccountStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, account_id, account_config, stack_hooks, controller):
        super().__init__(
            paco_ctx,
            account_ctx,
            account_id,
            "Configuration",
            controller
        )
        self.account_id = account_id
        self.account_config = account_config
        self.account_config_ref = 'paco.ref accounts.%s' % (account_id)
        self.stack_hooks = stack_hooks

    def init(self, do_not_cache=False):
        if self.account_config.is_master == True:
            # Create Managed Policy to allow the Administrator to switch to this org accounts delegagte role
            resource_list = ""
            for org_account_name in self.account_config.organization_account_ids:
                org_account_ctx = self.paco_ctx.get_account_context(account_name=org_account_name)
                resource_list += "\n      - arn:aws:iam::{}:role/{}".format(
                    org_account_ctx.get_id(), self.account_config.admin_delegate_role_name
                )
            user_list = "  - {}".format(self.paco_ctx.project['credentials'].master_admin_iam_username)
            if self.account_config.admin_iam_users != None:
                for iam_user in self.account_config.admin_iam_users.keys():
                    user_list += "\n  - {}".format(self.account_config.admin_iam_users[iam_user].username)

            # Build Policy
            policy_config_yaml = """
enabled: true
name: 'OrgAccountDelegate-{}'
statement:
  - effect: Allow
    action:
      - sts:AssumeRole
    resource:{}
users:
{}
    """.format(org_account_name, resource_list, user_list)
            ctl_iam = self.paco_ctx.get_controller('iam')
            ctl_iam.create_managed_policy(
                self.paco_ctx,
                self.account_ctx,
                self.account_config.region,
                'organization',
                'iam-delegate',
                'config.ref account.master.organization_account_ids.policy',
                policy_config_yaml,
                parent_config=self.account_config,
                stack_group=self,
                template_params=None,
                stack_tags=None,
                change_protected=False
            )

            # Account Stack
            #
            # The Account template creates Admin IAM users.
            # Since we add the .credentials master admin iam user name to this list automatically,
            # we do not want to recreate it here until we have a cloudformation custom resource
            # that can handle existing users.
            # TODO: Switch to CustomResource to allow for existing users
            #custom_resource_complete = False
            #if custom_resource_complete:
            #    account_template = paco.cftemplates.Account(self.paco_ctx,
            #                                            self.account_ctx,
            #                                            self,
            #                                            self.stack_hooks,
            #                                            self.account_id,
            #                                            self.account_config,
            #                                            self.account_config_ref)

            #    self.account_stack = account_template.stack

        print("Account Group Init: %s: Completed" % self.account_id)

    def resolve_ref(self, ref):
        raise StackException(PacoErrorCode.Unknown)

    def validate(self):
        super().validate()

    def provision(self):
        super().provision()
