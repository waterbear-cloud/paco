
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
        stack_order,

        user_config,
        permissions_list,
        config_ref
    ):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_order=stack_order,
            iam_capabilities=['CAPABILITY_NAMED_IAM']
        )
        self.set_aws_name('Account-Delegates', user_config.name[0].upper())

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
        if user_config.is_enabled() == True:
            if user_config.account_whitelist[0] == 'all' or account_ctx.get_name() in user_config.account_whitelist:
                self.user_delegate_role_and_policies(user_config, permissions_list)

        # Generate the Template
        self.set_template(self.template.to_yaml())

    def user_delegate_role_and_policies(self, user_config, permissions_list):
        user_arn = 'arn:aws:iam::{}:user/{}'.format(self.master_account_id, user_config.username)
        #user_arn = 'arn:aws:iam::{}:root'.format(self.master_account_id)
        assume_role_res = troposphere.iam.Role(
            "UserAccountDelegateRole",
            RoleName="IAM-User-Account-Delegate-Role-{}".format(
                self.create_resource_name(user_config.name, filter_id='IAM.Role.RoleName')
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
        # Iterate over permissions and create a delegate role and policices
        for permission_config in permissions_list:
            init_method = getattr(self, "init_{}_permission".format(permission_config.type.lower()))
            init_method(permission_config, assume_role_res)

        self.template.add_resource(assume_role_res)
        self.template.add_output(troposphere.Output(
            title='SigninUrl',
            Value=troposphere.Sub('https://signin.aws.amazon.com/switchrole?account=${AWS::AccountId}&roleName=${UserAccountDelegateRole}')
        ))


    def init_administrator_permission(self, permission_config, assume_role_res):
        if 'ManagedPolicyArns' not in assume_role_res.properties.keys():
            assume_role_res.properties['ManagedPolicyArns'] = []
        if permission_config.read_only == True:
            policy_arn = 'arn:aws:iam::aws:policy/ReadOnlyAccess'
        else:
            policy_arn = 'arn:aws:iam::aws:policy/AdministratorAccess'
        assume_role_res.properties['ManagedPolicyArns'].append(policy_arn)


    def init_codecommit_permission(self, permission_config, assume_role_res):

        statement_list = []
        readwrite_repo_arns = []
        readonly_repo_arns = []

        readonly_codecommit_actions = [
            Action('codecommit', 'BatchGet*'),
            Action('codecommit', 'BatchDescribe*'),
            Action('codecommit', 'List*'),
            Action('codecommit', 'GitPull*')
        ]

        readwrite_codecommit_actions = [
            Action('codecommit', '*'),
        ]
        for repo_config in permission_config.repositories:
            repo_account_id = self.aim_ctx.get_ref(repo_config.codecommit+'.account_id')
            if repo_account_id != self.account_id:
                continue

            codecommit_repo_arn = self.aim_ctx.get_ref(repo_config.codecommit+'.arn')

            if repo_config.permission == 'ReadWrite':
                if codecommit_repo_arn not in readwrite_repo_arns:
                    readwrite_repo_arns.append(codecommit_repo_arn)
            elif repo_config.permission == 'ReadOnly':
                if codecommit_repo_arn not in readonly_repo_arns:
                    readonly_repo_arns.append(codecommit_repo_arn)


        if len(readwrite_repo_arns) > 0:
            statement_list.append(
                Statement(
                    Sid='CodeCommitReadWrite',
                    Effect=Allow,
                    Action=readwrite_codecommit_actions,
                    Resource=readwrite_repo_arns
                )
            )
        if len(readonly_repo_arns) > 0:
            statement_list.append(
                Statement(
                    Sid='CodeCommitReadOnly',
                    Effect=Allow,
                    Action=readonly_codecommit_actions,
                    Resource=readonly_repo_arns
                )
            )

        statement_list.append(
            Statement(
                Effect=Allow,
                Action=[Action('codecommit', 'ListRepositories')],
                Resource=['*']
            )
        )

        managed_policy_res = troposphere.iam.ManagedPolicy(
            title=self.create_cfn_logical_id(
                "CodeCommitPolicy"
            ),
            PolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=statement_list
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

