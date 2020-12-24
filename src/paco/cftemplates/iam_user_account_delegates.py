from awacs.aws import Allow, Action, Principal, Statement, Condition, MultiFactorAuthPresent, PolicyDocument, StringEquals
from awacs.aws import Bool as AWACSBool
from awacs.sts import AssumeRole
from getpass import getpass
from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.models.references import Reference
import troposphere
import troposphere.cloudformation
import troposphere.iam


class IAMUserAccountDelegates(StackTemplate):
    def __init__(self, stack, paco_ctx, master_account_id, account_id, permissions_list):
        user = stack.resource
        self.account_id = account_id
        account_ctx = stack.account_ctx
        self.master_account_id = master_account_id
        super().__init__(stack, paco_ctx, iam_capabilities=['CAPABILITY_NAMED_IAM'])

        username = self.create_resource_name(
            user.name,
            camel_case=True
        )
        username = username[0].upper() + username[1:]
        if self.paco_ctx.legacy_flag('cftemplate_iam_user_delegates_2019_10_02') == True:
            self.set_aws_name(username, 'Account-Delegates')
        else:
            self.set_aws_name('Account-Delegates', username)

        # Troposphere Template Initialization
        self.init_template('IAM User Account Delegate Permissions')

        # Restrict account access here so that we can create an empty CloudFormation
        # template which will then delete permissions that have been revoked.
        if user.is_enabled() == True:
            if user.account_whitelist[0] == 'all' or account_ctx.get_name() in user.account_whitelist:
                self.user_delegate_role_and_policies(user, permissions_list)


    def user_delegate_role_and_policies(self, user, permissions_list):
        "Create and add an account delegate Role to template"
        user_arn = 'arn:aws:iam::{}:user/{}'.format(self.master_account_id, user.username)
        assume_role_res = troposphere.iam.Role(
            "UserAccountDelegateRole",
            RoleName="IAM-User-Account-Delegate-Role-{}".format(
                self.create_resource_name(user.name, filter_id='IAM.Role.RoleName')
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
        for managed_policy in permission_config.managed_policies:
            if 'ManagedPolicyArns' not in assume_role_res.properties.keys():
                assume_role_res.properties['ManagedPolicyArns'] = []
            assume_role_res.properties['ManagedPolicyArns'].append('arn:aws:iam::aws:policy/' + managed_policy)
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

    def init_deploymentpipelines_permission(self, permission_config, assume_role_res):
        if 'ManagedPolicyArns' not in assume_role_res.properties.keys():
            assume_role_res.properties['ManagedPolicyArns'] = []

        pipeline_list = []
        for resource in permission_config.resources:
            pipeline_ref = Reference(resource.pipeline)
            pipeline = pipeline_ref.get_model_obj(self.paco_ctx.project)
            account_ref = pipeline.configuration.account
            account_name = self.paco_ctx.get_ref(account_ref + '.name')
            if account_name == self.account_ctx.name:
                pipeline_arn = self.paco_ctx.get_ref(pipeline.paco_ref+'.arn')
                pipeline_list.append(
                    {
                        'permission': resource.permission,
                        'pipeline': pipeline,
                        'pipeline_arn': pipeline_arn
                    }
                )


            # Some actions in the pipeline might be in different account so we must
            # iterate the pipeline stages and actions and add them too.
            # for action in pipeline_config.source:
            #     account_name = None
            #     if action.type == 'CodeDeploy.Deploy':
            #         asg_ref = Reference(action.auto_scaling_group)
            #         asg_config = asg_ref.resolve()
            #         account_name = self.paco_ctx.get_ref(asg_config.get_account().paco_ref + '.name')
            #         self.init_codedeploy_permission(pipeline_ref, assume_role_res)

            #for action in pipeline_config.build:
            #    account_name = None
            #    if action.type == 'CodeBuild.Build':
            #        self.init_codebuild_permission(pipeline_ref, assume_role_res)


        self.deployment_pipeline_codepipeline_permissions(pipeline_list, assume_role_res)
        self.deployment_pipeline_codebuild_permissions(pipeline_list, assume_role_res)

    def deployment_pipeline_codepipeline_permissions(self, pipeline_list, assume_role_res):
        statement_list = []

        list_pipelines_actions = [
            Action('codepipeline', 'ListPipelines')
        ]
        readonly_actions = [
            Action('codepipeline', 'GetPipeline'),
            Action('codepipeline', 'GetPipelineState'),
            Action('codepipeline', 'GetPipelineExecution'),
            Action('codepipeline', 'ListPipelineExecutions'),
            Action('codepipeline', 'ListActionExecutions'),
            Action('codepipeline', 'ListActionTypes'),
            Action('codepipeline', 'ListTagsForResource'),
            Action('codepipeline', 'StartPipelineExecution'),
            Action('codepipeline', 'StopPipelineExecution')
        ]
        retrystages_actions = [
            Action('codepipeline', 'RetryStageExecution')
        ]

        readonly_arn_list = []
        retrystages_arn_list = []
        for pipeline_ctx in pipeline_list:
            if pipeline_ctx['permission'].find('ReadOnly') != -1:
                readonly_arn_list.append(pipeline_ctx['pipeline_arn'])
            if pipeline_ctx['permission'].find('RetryStages') != -1:
                if pipeline_ctx['pipeline'].source:
                    retrystages_arn_list.append(pipeline_ctx['pipeline_arn']+'/Source')
                if pipeline_ctx['pipeline'].build:
                    retrystages_arn_list.append(pipeline_ctx['pipeline_arn']+'/Build')
                if pipeline_ctx['pipeline'].deploy:
                    retrystages_arn_list.append(pipeline_ctx['pipeline_arn']+'/Deploy')

        if len(readonly_arn_list) > 0:
            statement_list.append(
                Statement(
                    Sid='CodePipelineListAccess',
                    Effect=Allow,
                    Action=list_pipelines_actions,
                    Resource=['*']
                )
            )
            statement_list.append(
                Statement(
                    Sid='CodePipelineReadAccess',
                    Effect=Allow,
                    Action=readonly_actions,
                    Resource=readonly_arn_list
                )
            )

        if pipeline_ctx['permission'].find('RetryStages') != -1:
            statement_list.append(
                Statement(
                    Sid='CodePipelineRetryStagesAccess',
                    Effect=Allow,
                    Action=retrystages_actions,
                    Resource=retrystages_arn_list
                )
            )

        managed_policy_res = troposphere.iam.ManagedPolicy(
            title=self.create_cfn_logical_id("CodePipelinePolicy"),
            PolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=statement_list
            ),
            Roles=[ troposphere.Ref(assume_role_res) ]
        )
        self.template.add_resource(managed_policy_res)

    def deployment_pipeline_codebuild_permissions(self, pipeline_list, assume_role_res):
        statement_list = []

        list_pipelines_actions = [
            Action('codepipeline', 'ListPipelines')
        ]
        readonly_actions = [
            Action('codebuild', 'BatchGet*'),
            Action('codebuild', 'Get*'),
            Action('codebuild', 'List*'),
            Action('cloudwatch', 'GetMetricStatistics*'),
            Action('events', 'DescribeRule'),
            Action('events', 'ListTargetsByRule'),
            Action('events', 'ListRuleNamesByTarget'),
            Action('logs', 'GetLogEvents')
        ]

        readonly_arn_list = []
        retrystages_arn_list = []
        for pipeline_ctx in pipeline_list:
            if pipeline_ctx == None:
                continue
            if pipeline_ctx['permission'].find('ReadOnly') != -1 and pipeline_ctx['pipeline'].build != None:
                for action_name in pipeline_ctx['pipeline'].build:
                    action = pipeline_ctx['pipeline'].build[action_name]
                    if action.type == 'CodeBuild.Build':
                        codebuild_arn = self.paco_ctx.get_ref(action.paco_ref+'.project.arn')
                        readonly_arn_list.append(codebuild_arn)
        if len(readonly_arn_list) > 0:
            self.set_codebuild_permissions(readonly_arn_list, assume_role_res)

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

        self.set_codebuild_permissions(readonly_codebuild_arns, assume_role_res)

    def set_codebuild_permissions(self, readonly_codebuild_arns, assume_role_res):
        statement_list = []
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
                    Resource=readonly_codebuild_arns
                )
            )

        managed_policy_res = troposphere.iam.ManagedPolicy(
            title=self.create_cfn_logical_id("CodeBuildPolicy"),
            PolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=statement_list
            ),
            Roles=[ troposphere.Ref(assume_role_res) ]
        )
        self.template.add_resource(managed_policy_res)

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
