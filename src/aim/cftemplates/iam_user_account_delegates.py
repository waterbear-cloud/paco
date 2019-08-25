
import troposphere
import troposphere.cloudformation
import troposphere.iam

from aim import utils
from aim.cftemplates.cftemplates import CFTemplate
from awacs.aws import Allow, Action, Principal, Statement, Condition, MultiFactorAuthPresent, PolicyDocument
from awacs.aws import Bool as AWACSBool
from awacs.sts import AssumeRole
from getpass import getpass


class IAMUserAccountDelegates(CFTemplate):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,

        user_config,
        permissions_list,
        config_ref
    ):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        aws_name = '-'.join(['Account-Delegates',user_config.name])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags,
            iam_capabilities=['CAPABILITY_NAMED_IAM']
        )

        self.account_id = account_ctx.id
        self.master_account_id = self.aim_ctx.get_ref('aim.ref accounts.master.id')

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        self.template = troposphere.Template()
        self.template.add_version('2010-09-09')
        self.template.add_description('IAM User Account Delegate Permissions')

        self.template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        )

        # Restrict account access here so that we can create an empty CloudFormation
        # template which will then delete permissions that have been revoked.
        if account_ctx.get_name() in user_config.account_whitelist:
            self.user_delegate_role_and_policies(user_config, permissions_list)

        # Generate the Template
        self.set_template(self.template.to_yaml())

    def user_delegate_role_and_policies(self, user_config, permissions_list):
        # Iterate over permissions and create a delegate role and policices
        for permission_config in permissions_list:
            user_arn = 'arn:aws:iam::{}:user/{}'.format(self.master_account_id, user_config.username)
            assume_role_res = troposphere.iam.Role(
                "UserAccountDelegateRole",
                RoleName="IAM-User-Account-Delegate-Role-{}".format(
                    utils.normalize_name(user_config.name, '-', True)
                ),
                AssumeRolePolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[ AssumeRole ],
                            Principal=Principal("AWS", [user_arn]),
                            Condition=Condition(
                                [
                                    AWACSBool({
                                        MultiFactorAuthPresent: True
                                    })
                                ]
                            )
                        )
                    ]
                )
            )

            self.template.add_output(troposphere.Output(
                title='SigninUrl',
                Value=troposphere.Sub('https://signin.aws.amazon.com/switchrole?account=${AWS::AccountId}&roleName=${UserAccountDelegateRole}')
            ))

            init_method = getattr(self, "init_{}_permission".format(permission_config.type.lower()))
            init_method(permission_config, assume_role_res)

            self.template.add_resource(assume_role_res)

    def init_administrator_permission(self, permission_config, assume_role_res):
        if 'ManagedPolicyArns' not in assume_role_res.properties.keys():
            assume_role_res.properties['ManagedPolicyArns'] = []
        assume_role_res.properties['ManagedPolicyArns'].append('arn:aws:iam::aws:policy/AdministratorAccess')

    def init_codecommit_permission(self, permission_config, assume_role_res):

        for repo_config in permission_config.repositories:
            repo_account_id = self.aim_ctx.get_ref(repo_config.codecommit+'.account_id')
            if repo_account_id != self.account_id:
                continue

            codecommit_repo_arn = self.aim_ctx.get_ref(repo_config.codecommit+'.arn')

            if repo_config.permission == 'ReadOnly':
                codecommit_actions = [
                    Action('codecommit', 'BatchGet*'),
                    Action('codecommit', 'BatchDescribe*'),
                    Action('codecommit', 'List*'),
                    Action('codecommit', 'GitPull*')
                ]
            elif repo_config.permission == 'ReadWrite':
                codecommit_actions = [
                    Action('codecommit', '*'),
                ]
            managed_policy_res = troposphere.iam.ManagedPolicy(
                "CodeCommitPolicy",
                PolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=codecommit_actions,
                            Resource=[ codecommit_repo_arn ]
                        ),
                        Statement(
                            Effect=Allow,
                            Action=[Action('codecommit', 'ListRepositories')],
                            Resource=['*']
                        )
                    ]
                ),
                Roles=[ troposphere.Ref(assume_role_res) ]
            )
            self.template.add_resource(managed_policy_res)


        # ---------------------------------------------------------------------------
        # Outputs
        #example_output = troposphere.Output(
        #    title='ExampleResourceId',
        #    Description="Example resource Id.",
        #    Value=troposphere.Ref(example_res)
        #)
        #self.template.add_output(example_output)

        # AIM Stack Output Registration
        #self.register_stack_output_config(self.config_ref + ".id", example_output.title)

