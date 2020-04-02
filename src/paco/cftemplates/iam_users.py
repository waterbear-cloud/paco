from awacs.aws import Allow, Deny, Action, Principal, Statement, PolicyDocument, MultiFactorAuthPresent, Condition
from awacs.aws import Bool as AWACSBool
from awacs.sts import AssumeRole
from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
import random
import string
import troposphere
import troposphere.iam


class IAMUsers(StackTemplate):
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx, iam_capabilities=['CAPABILITY_NAMED_IAM'])
        self.set_aws_name('Accounts')

        # Troposphere Template Initialization
        self.init_template('IAM Users')
        template = self.template

        # IAM Users
        is_enabled = False
        for iam_user in self.resource.values():
            if iam_user.is_enabled() == False:
                continue
            self.add_iam_user(iam_user)
            is_enabled = True
        self.set_enabled(is_enabled)

    def add_iam_user(self, iam_user):
        # Parameters
        username_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('Username'+utils.md5sum(str_data=iam_user.username)),
            param_type='String',
            description='The name of the user.',
            value=iam_user.username,
        )

        if iam_user.console_access_enabled == True:
            user_password = utils.md5sum(str_data=iam_user.username)[:8]
            if self.paco_ctx.legacy_flag('iam_user_default_password_2019_10_12') == False:
                user_password += '@Aim19!'
            print("{}: default password: {}".format(iam_user.username, user_password))
            password_param = self.create_cfn_parameter(
                name=self.create_cfn_logical_id('Password'+utils.md5sum(str_data=user_password)),
                param_type='String',
                description='The password to assign of the user',
                noecho=True,
                value=user_password,
            )

        # IAMUser Resource
        iam_user_dict = {
            'UserName': troposphere.Ref(username_param),
        }
        # Console Access
        if iam_user.console_access_enabled == True:
            iam_user_dict['LoginProfile'] = {
                'Password': troposphere.Ref(password_param),
                'PasswordResetRequired': True
            }

        iam_user_res = troposphere.iam.User.from_dict(
            self.create_cfn_logical_id('IAMUser'+iam_user.name),
            iam_user_dict
        )
        self.template.add_resource(iam_user_res)

        # Account Delegate Assume Role
        #   - A list of account delegate roles in each of the accounts
        assume_role_arn_list = []
        account_list = iam_user.account_whitelist
        if iam_user.account_whitelist[0] == 'all':
            account_list = self.paco_ctx.project['accounts'].keys()

        for account_name in account_list:
            account_ref = 'paco.ref accounts.'+account_name
            account_id = self.paco_ctx.get_ref(account_ref+'.id')
            delegate_role_arn = "arn:aws:iam::{}:role/IAM-User-Account-Delegate-Role-{}".format(
                account_id,
                self.create_resource_name(iam_user.name, filter_id='IAM.Role.RoleName')
            )
            assume_role_arn_list.append(delegate_role_arn)

        if len(assume_role_arn_list) > 0:
            user_policy_dict = {
                'ManagedPolicyName': 'IAM-User-AssumeRole-Policy-{}'.format(
                    self.create_resource_name(iam_user.name, '-').capitalize()
                ),
                'PolicyDocument': PolicyDocument(
                        Version="2012-10-17",
                        Statement=[
                            Statement(
                                Effect=Allow,
                                Action=[AssumeRole],
                                Resource=assume_role_arn_list
                            ),
                            Statement(
                                Sid='AllowViewAccountInfo',
                                Effect=Allow,
                                Action=[
                                    Action('iam', 'GetAccountPasswordPolicy'),
                                    Action('iam', 'GetAccountSummary'),
                                    Action('iam', 'ListVirtualMFADevices'),
                                    Action('iam', 'ListUsers'),
                                ],
                                Resource=['*']
                            ),
                            Statement(
                                Sid='AllowManageOwnPasswords',
                                Effect=Allow,
                                Action=[
                                    Action('iam', 'ChangePassword'),
                                    Action('iam', 'GetUser'),
                                ],
                                Resource=['arn:aws:iam::*:user/{}'.format(iam_user.username)]
                            ),
                            Statement(
                                Sid='AllowManageOwnVirtualMFADevice',
                                Effect=Allow,
                                Action=[
                                    Action('iam', 'CreateVirtualMFADevice'),
                                    Action('iam', 'DeleteVirtualMFADevice'),
                                ],
                                Resource=['arn:aws:iam::*:mfa/{}'.format(iam_user.username)]
                            ),
                            Statement(
                                Sid='AllowManageOwnUserMFA',
                                Effect=Allow,
                                Action=[
                                    Action('iam', 'DeactivateMFADevice'),
                                    Action('iam', 'EnableMFADevice'),
                                    Action('iam', 'ListMFADevices'),
                                    Action('iam', 'ResyncMFADevice'),
                                ],
                                Resource=['arn:aws:iam::*:user/{}'.format(iam_user.username)]
                            ),
                            Statement(
                                Sid='DenyAllExceptListedIfNoMFA',
                                Effect=Deny,
                                NotAction=[
                                    Action('iam', 'CreateVirtualMFADevice'),
                                    Action('iam', 'EnableMFADevice'),
                                    Action('iam', 'ChangePassword'),
                                    Action('iam', 'GetUser'),
                                    Action('iam', 'ListMFADevices'),
                                    Action('iam', 'ListVirtualMFADevices'),
                                    Action('iam', 'ResyncMFADevice'),
                                    Action('sts', 'GetSessionToken'),
                                    Action('iam', 'ListUsers'),
                                ],
                                Resource=['*'],
                                Condition=Condition(
                                    [
                                        AWACSBool({
                                            MultiFactorAuthPresent: False
                                        })
                                    ]
                                )
                            ) ],
                    ),
                'Users': [troposphere.Ref(iam_user_res)]
            }
            # Policy
            user_policy_res = troposphere.iam.ManagedPolicy.from_dict(
                self.create_cfn_logical_id('IAMUserPolicy'+iam_user.name),
                user_policy_dict
            )
            self.template.add_resource(user_policy_res)
