
import random
import string
import troposphere
import troposphere.iam

from paco import utils
from paco.cftemplates.cftemplates import CFTemplate
from awacs.aws import Allow, Deny, Action, Principal, Statement, PolicyDocument, \
    MultiFactorAuthPresent, Condition
from awacs.aws import Bool as AWACSBool
from awacs.sts import AssumeRole


class IAMUsers(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 stack_hooks,

                 iam_users_config,
                 config_ref):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_hooks=stack_hooks,
            iam_capabilities=['CAPABILITY_NAMED_IAM']
        )
        self.set_aws_name('Accounts')

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        self.template = troposphere.Template()
        self.template.add_version('2010-09-09')
        self.template.add_description('IAM Users')
        self.template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        # IAM Users
        for user_name in iam_users_config.keys():
            iam_user_config = iam_users_config[user_name]
            if iam_user_config.is_enabled() == False:
                continue
            self.add_iam_user(iam_user_config)

        # Generate the Template
        self.set_template(self.template.to_yaml())

    def add_iam_user(self, iam_user_config):
        # ---------------------------------------------------------------------------
        # Parameters

        username_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('Username'+utils.md5sum(str_data=iam_user_config.username)),
            param_type='String',
            description='The name of the user.',
            value=iam_user_config.username,
            use_troposphere=True
        )
        self.template.add_parameter(username_param)

        if iam_user_config.console_access_enabled == True:
            user_password = utils.md5sum(str_data=iam_user_config.username)[:8]
            if self.paco_ctx.legacy_flag('iam_user_default_password_2019_10_12') == False:
                user_password += '@Aim19!'
            print("{}: default password: {}".format(iam_user_config.username, user_password))
            password_param = self.create_cfn_parameter(
                name=self.create_cfn_logical_id('Password'+utils.md5sum(str_data=user_password)),
                param_type='String',
                description='The password to assign of the user',
                noecho=True,
                value=user_password,
                use_troposphere=True
            )
            self.template.add_parameter(password_param)

        # ---------------------------------------------------------------------------
        # Resources

        # IAMUser
        iam_user_dict = {
            'UserName': troposphere.Ref(username_param),
        }
        # Console Access
        if iam_user_config.console_access_enabled == True:
            iam_user_dict['LoginProfile'] = {
                'Password': troposphere.Ref(password_param),
                'PasswordResetRequired': True
            }

        iam_user_res = troposphere.iam.User.from_dict(
            self.create_cfn_logical_id('IAMUser'+iam_user_config.name),
            iam_user_dict
        )
        self.template.add_resource(iam_user_res)

        # Account Delegate Assume Role
        #   - A list of account delegate roles in each of the accounts
        assume_role_arn_list = []
        account_list = iam_user_config.account_whitelist
        if iam_user_config.account_whitelist[0] == 'all':
            account_list = self.paco_ctx.project['accounts'].keys()
        for account_name in account_list:
            account_ref = 'paco.ref accounts.'+account_name
            account_id = self.paco_ctx.get_ref(account_ref+'.id')
            delegate_role_arn = "arn:aws:iam::{}:role/IAM-User-Account-Delegate-Role-{}".format(
                account_id,
                self.create_resource_name(iam_user_config.name, filter_id='IAM.Role.RoleName')
            )
            assume_role_arn_list.append(delegate_role_arn)

        if len(assume_role_arn_list) > 0:
            user_policy_dict = {
                'ManagedPolicyName': 'IAM-User-AssumeRole-Policy-{}'.format(
                    self.create_resource_name(iam_user_config.name, '-').capitalize()
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
                                Resource=['arn:aws:iam::*:user/{}'.format(iam_user_config.username)]
                            ),
                            Statement(
                                Sid='AllowManageOwnVirtualMFADevice',
                                Effect=Allow,
                                Action=[
                                    Action('iam', 'CreateVirtualMFADevice'),
                                    Action('iam', 'DeleteVirtualMFADevice'),
                                ],
                                Resource=['arn:aws:iam::*:mfa/{}'.format(iam_user_config.username)]
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
                                Resource=['arn:aws:iam::*:user/{}'.format(iam_user_config.username)]
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
                self.create_cfn_logical_id('IAMUserPolicy'+iam_user_config.name),
                user_policy_dict
            )
            self.template.add_resource(user_policy_res)

        # ---------------------------------------------------------------------------
        # Outputs
        #example_output = troposphere.Output(
        #    title='ExampleResourceId',
        #    Description="Example resource Id.",
        #    Value=troposphere.Ref(example_res)
        #)
        #self.template.add_output(example_output)

        # Paco Stack Output Registration
        #self.register_stack_output_config(self.config_ref + ".id", example_output.title)

