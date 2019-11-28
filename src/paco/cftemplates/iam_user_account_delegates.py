
import troposphere
import troposphere.cloudformation
import troposphere.iam


from paco import utils
from paco.cftemplates.cftemplates import CFTemplate
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.models.references import Reference
from awacs.aws import Allow, Action, Principal, Statement, Condition, MultiFactorAuthPresent, PolicyDocument, StringEquals
from awacs.aws import Bool as AWACSBool
from awacs.sts import AssumeRole
from getpass import getpass


class IAMUserAccountDelegates(CFTemplate):
    def __init__(
        self,
        paco_ctx,
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
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_order=stack_order,
            iam_capabilities=['CAPABILITY_NAMED_IAM']
        )

        #self.set_aws_name('Account-Delegates', user_config.name)

        username = self.create_resource_name(
            user_config.name,
            camel_case=True
        )
        username = username[0].upper() + username[1:]

        if self.paco_ctx.legacy_flag('cftemplate_iam_user_delegates_2019_10_02') == True:
            self.set_aws_name(username, 'Account-Delegates')
        else:
            self.set_aws_name('Account-Delegates', username)

        self.account_id = account_ctx.id
        self.master_account_id = self.paco_ctx.get_ref('paco.ref accounts.master.id')

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

    def init_custompolicy_permission(self, permission_config, assume_role_res):
        for policy in permission_config.policies:
            policy_statements = []
            for policy_statement in policy.statement:
                statement_dict = {
                    'Effect': policy_statement.effect,
                    'Action': [
                        Action(*action.split(':')) for action in policy_statement.action
                    ],
                }

                # Resource
                statement_dict['Resource'] = policy_statement.resource

                policy_statements.append(
                    Statement(**statement_dict)
                )
            # Make the policy
            managed_policy_res = troposphere.iam.ManagedPolicy(
                title=self.create_cfn_logical_id_join(
                    str_list=["CustomPolicy", policy.name],
                    camel_case=True
                ),
                PolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=policy_statements
                ),
                Roles=[ troposphere.Ref(assume_role_res) ]
            )
            self.template.add_resource(managed_policy_res)

    def init_codebuild_permission(self, permission_config, assume_role_res):
        """CodeBuild Web Console Permissions"""
        if 'ManagedPolicyArns' not in assume_role_res.properties.keys():
            assume_role_res.properties['ManagedPolicyArns'] = []

        statement_list = []
        #readwrite_codebuild_arns = []
        readonly_codebuild_arns = []
        for resource in permission_config.resources:
            codebuild_ref = Reference(resource.codebuild)
            codebuild_account_ref = 'paco.ref ' + '.'.join(codebuild_ref.parts[:-2]) + '.configuration.account'
            codebuild_account_ref = self.paco_ctx.get_ref(codebuild_account_ref)
            codebuild_account_id = self.paco_ctx.get_ref(codebuild_account_ref+'.id')
            if codebuild_account_id != self.account_id:
                continue

            codebuild_arn = self.paco_ctx.get_ref(resource.codebuild+'.project.arn')

            if resource.permission == 'ReadOnly':
                if codebuild_arn not in readonly_codebuild_arns:
                    readonly_codebuild_arns.append(codebuild_arn)

        readonly_codebuild_actions = [
            Action('codebuild', 'BatchGet*'),
            Action('codebuild', 'Get*'),
            Action('codebuild', 'List*'),
            Action('cloudwatch', 'GetMetricStatistics*'),
            Action('events', 'DescribeRule'),
            Action('events', 'ListTargetsByRule'),
            Action('events', 'ListRuleNamesByTarget'),
            Action('logs', 'GetLogEvents')
        ]
        if len(readonly_codebuild_arns) > 0:
            statement_list.append(
                Statement(
                    Sid='CodeBuildReadOnly',
                    Effect=Allow,
                    Action=readonly_codebuild_actions,
                    Resource=['*']#readonly_codebuild_arns
                )
            )
            #statement_list.append(
            #    Statement(
            #        Sid='OtherReadOnly',
            #        Effect=Allow,
            #        Action=readonly_other_actions,
            #        Resource=['*']
            #    )
            #)

        managed_policy_res = troposphere.iam.ManagedPolicy(
            title=self.create_cfn_logical_id("CodeBuildPolicy"),
            PolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=statement_list
            ),
            Roles=[ troposphere.Ref(assume_role_res) ]
        )
        self.template.add_resource(managed_policy_res)#

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
            repo_account_id = self.paco_ctx.get_ref(repo_config.codecommit+'.account_id')
            if repo_account_id != self.account_id:
                continue

            codecommit_repo_arn = self.paco_ctx.get_ref(repo_config.codecommit+'.arn')

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

        # Paco Stack Output Registration
        #self.register_stack_output_config(self.config_ref + ".id", example_output.title)


