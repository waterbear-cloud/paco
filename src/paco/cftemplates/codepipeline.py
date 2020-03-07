from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole
from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns




ACTION_MAP = {
    'CodeBuild.Build': {
        'Name': 'CodeBuild',
        'Category': 'Build',
        'Owner': 'AWS',
        'Version': '1',
        'Provider': 'CodeBuild',
    },
    'GitHub.Source': {
        'Name': 'GitHub',
        'Category': 'Source',
        'Owner': 'ThirdParty',
        'Version': '1',
        'Provider': 'GitHub',
        'OutputArtifacts': [ troposphere.codepipeline.OutputArtifacts(Name='GitHubArtifact') ],
        'configuration_method': 'create_github_source_configuration',
    },
    'Lambda.Invoke': {
        'Name': 'LambdaInvoke',
        'Category': 'Invoke',
        'Owner': 'AWS',
        'Version': '1',
        'Provider': 'Lambda',
        'OutputArtifacts': [],
        'configuration_method': 'create_lambda_invoke_configuration',
    },
}

class CodePipeline(StackTemplate):
    def __init__(self, stack, paco_ctx, env_ctx, app_name, artifacts_bucket_name):
        self.pipeline = stack.resource
        self.env_ctx = env_ctx
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('CodePipeline', self.resource_group_name, self.resource.name)

        # Troposphere Template Initialization
        self.init_template('Deployment: CodePipeline')

        if not self.pipeline.is_enabled():
            return

        # If a CodeCommit.Source action is enabled, it flips this flag so that the Role will have access
        self.codecommit_source = False
        self.github_source = False
        self.codebuild_access = False
        self.lambda_invoke = False
        self.codedeploy_deploy_assume_role_statement = None
        self.s3_deploy_assume_role_statement = None

        self.res_name_prefix = self.create_resource_name_join(
            name_list=[env_ctx.get_aws_name(), app_name, self.resource_group_name, self.resource.name],
            separator='-',
            camel_case=True
        )
        self.resource_name_prefix_param = self.create_cfn_parameter(
            param_type='String',
            name='ResourceNamePrefix',
            description='The name to prefix resource names.',
            value=self.res_name_prefix,
        )
        self.cmk_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='CMKArn',
            description='The KMS CMK Arn of the key used to encrypt deployment artifacts.',
            value=self.pipeline.paco_ref + '.kms.arn',
        )
        self.artifacts_bucket_name_param = self.create_cfn_parameter(
            param_type='String',
            name='ArtifactsBucketName',
            description='The name of the S3 Bucket to create that will hold deployment artifacts',
            value=artifacts_bucket_name,
        )
        self.manual_approval_is_enabled = False
        if self.pipeline.stages != None:
            self.create_pipeline_from_stages()
        else:
            self.create_pipeine_from_sourcebuilddeploy()

    def create_pipeline_from_stages(self):
        "Create CodePipeilne resources based on the .stages field"
        stages = []
        for stage in self.pipeline.stages.values():
            actions = []
            for action in stage.values():
                if not action.is_enabled():
                    continue
                info = ACTION_MAP[action.type]
                if action.type == 'GitHub.Source':
                    self.github_source = True
                elif action.type == 'Lambda.Invoke':
                    self.lambda_invoke = True
                configuration = getattr(self, info['configuration_method'])(stage, action)
                action_resource = troposphere.codepipeline.Actions(
                    Name=self.create_cfn_logical_id(info['Name'] + stage.name + action.name),
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category=info['Category'],
                        Owner=info['Owner'],
                        Version=info['Version'],
                        Provider=info['Provider'],
                    ),
                    Configuration = configuration,
                    InputArtifacts = [],
                    OutputArtifacts = info['OutputArtifacts'],
                    RunOrder = action.run_order
                )
                actions.append(action_resource)
            stage_resource = troposphere.codepipeline.Stages(
                Name=self.create_cfn_logical_id('PipelineStage' + stage.name),
                Actions=actions
            )
            stages.append(stage_resource)

        pipeline_service_role_res = self.add_pipeline_service_role()
        pipeline_res = troposphere.codepipeline.Pipeline(
            title = 'CodePipeline',
            template = self.template,
            DependsOn='CodePipelinePolicy',
            RoleArn = troposphere.GetAtt(pipeline_service_role_res, 'Arn'),
            Name = troposphere.Ref(self.resource_name_prefix_param),
            Stages = stages,
            ArtifactStore = troposphere.codepipeline.ArtifactStore(
                Type = 'S3',
                Location = troposphere.Ref(self.artifacts_bucket_name_param),
                EncryptionKey = troposphere.codepipeline.EncryptionKey(
                    Type = 'KMS',
                    Id = troposphere.Ref(self.cmk_arn_param),
                )
            )
        )

    def create_lambda_invoke_configuration(self, stage, action):
        function_arn_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('Lambda' + stage.name + action.name),
            description='The name of the Lambda for stage {} and action {}'.format(stage.name, action.name),
            value=action.target_lambda + '.arn',
        )
        user_parameters_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('UserParameters' + stage.name + action.name),
            description='The UserParameters for stage {} and action {}'.format(stage.name, action.name),
            value=action.user_parameters,
        )
        lambda_function_name = troposphere.Join(
            '', [
                troposphere.Select(
                    6, troposphere.Split(':', troposphere.Ref(function_arn_param))
                )
            ]
        )
        return {
            'FunctionName': lambda_function_name,
            'UserParameters': troposphere.Ref(user_parameters_param),
        }

    def create_github_source_configuration(self, stage, action):
        github_token_param = self.create_cfn_parameter(
            param_type='AWS::SSM::Parameter::Value<String>',
            name=self.create_cfn_logical_id('GitHubTokenSSMParameterName' + stage.name + action.name),
            description='The name of the SSM Parameter with the GitHub OAuth Token',
            value=action.github_token_parameter_name,
        )
        github_owner_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubOwner' + stage.name + action.name),
            description='The name of the GitHub owner',
            value=action.github_owner,
        )
        github_repo_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubRepository' + stage.name + action.name),
            description='The name of the GitHub Repository',
            value=action.github_repository,
        )
        github_deploy_branch_name_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubDeploymentBranchName' + stage.name + action.name),
            description='The name of the branch where commits will trigger a build.',
            value=action.deployment_branch_name,
        )
        return {
            'Owner': troposphere.Ref(github_owner_param),
            'Repo': troposphere.Ref(github_repo_param),
            'Branch': troposphere.Ref(github_deploy_branch_name_param),
            'OAuthToken': troposphere.Ref(github_token_param),
            'PollForSourceChanges': False
        }

    def add_pipeline_service_role(self):
        "Create a CodePipeline Service Role resource and add it to the template"
        self.pipeline_service_role_name = self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodePipeline-Service'],
            filter_id='IAM.Role.RoleName'
        )
        pipeline_service_role_res = troposphere.iam.Role(
            title='CodePipelineServiceRole',
            template = self.template,
            RoleName=self.pipeline_service_role_name,
            AssumeRolePolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[ AssumeRole ],
                        Principal=Principal("Service", ['codepipeline.amazonaws.com']),
                    )
                ]
            )
        )
        pipeline_policy_statement_list = [
            Statement(
                Sid='CodePipelineAccess',
                Effect=Allow,
                Action=[
                    Action('codepipeline', '*'),
                    Action('sns', 'Publish'),
                    Action('s3', 'ListAllMyBuckets'),
                    Action('s3', 'GetBucketLocation'),
                    Action('iam', 'ListRoles'),
                    Action('iam', 'PassRole'),
                ],
                Resource=[ '*' ]
            ),
            Statement(
                Sid='S3Access',
                Effect=Allow,
                Action=[
                    Action('s3', 'PutObject'),
                    Action('s3', 'GetBucketPolicy'),
                    Action('s3', 'GetObject'),
                    Action('s3', 'ListBucket'),
                ],
                Resource=[
                    troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}/*'),
                    troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}')
                ]
            ),
            Statement(
                Sid='KMSCMK',
                Effect=Allow,
                Action=[
                    Action('kms', 'Decrypt'),
                ],
                Resource=[ troposphere.Ref(self.cmk_arn_param) ]
            ),
        ]
        if self.lambda_invoke:
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='LambdaInvoke',
                    Effect=Allow,
                    Action=[
                        Action('lambda', 'InvokeFunction'),
                    ],
                    Resource=['*'],
                )
            )
        if self.codebuild_access:
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='CodeBuildAccess',
                    Effect=Allow,
                    Action=[
                        Action('codebuild', 'BatchGetBuilds'),
                        Action('codebuild', 'StartBuild')
                    ],
                    Resource=[ troposphere.Ref(self.codebuild_project_arn_param) ]
                )
            )
        if self.codecommit_source:
            # Add Statements to allow CodeCommit if a CodeCommit.Source is enabled
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='CodeCommitAssumeRole',
                    Effect=Allow,
                    Action=[
                        Action('sts', 'AssumeRole'),
                    ],
                    Resource=[ troposphere.Ref(self.codecommit_role_arn_param) ]
                )
            )
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='CodeCommitAccess',
                    Effect=Allow,
                    Action=[
                        Action('codecommit', 'List*'),
                        Action('codecommit', 'Get*'),
                        Action('codecommit', 'GitPull'),
                        Action('codecommit', 'UploadArchive'),
                        Action('codecommit', 'CancelUploadArchive'),
                    ],
                    Resource=[
                        troposphere.Ref(self.codecommit_repo_arn_param),
                    ]
                )
            )
        if self.github_source:
            # Add Statement to allow GitHub if a GitHub.Source is enabled
            cmk_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='SourceCMKArn',
                description='The CMK Arn',
                value=self.pipeline.paco_ref + '.kms.arn',
            )
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='CMK',
                    Effect=Allow,
                    Action=[
                        Action('kms', '*'),
                    ],
                    Resource=[ troposphere.Ref(cmk_arn_param) ]
                )
            )

        if self.codedeploy_deploy_assume_role_statement != None:
            pipeline_policy_statement_list.append(self.codedeploy_deploy_assume_role_statement)
        if self.s3_deploy_assume_role_statement != None:
            pipeline_policy_statement_list.append(self.s3_deploy_assume_role_statement)
        troposphere.iam.PolicyType(
            title='CodePipelinePolicy',
            template = self.template,
            DependsOn = 'CodePipelineServiceRole',
            PolicyName=troposphere.Sub('${ResourceNamePrefix}-CodePipeline-Policy'),
            PolicyDocument=PolicyDocument(
                Statement=pipeline_policy_statement_list,
            ),
            Roles=[troposphere.Ref(pipeline_service_role_res)]
        )
        return pipeline_service_role_res

    def create_pipeine_from_sourcebuilddeploy(self):
        # CodePipeline
        # Source Actions
        source_stage_actions = []
        # Source Actions
        for action in self.pipeline.source.values():
            self.build_input_artifacts = []

            # Manual Approval Action
            if action.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(action)
                source_stage_actions.append(manual_approval_action)

            # GitHub Action
            elif action.type == 'GitHub.Source':
                if action.is_enabled():
                    self.github_source = True
                github_token_param = self.create_cfn_parameter(
                    param_type='AWS::SSM::Parameter::Value<String>',
                    name='GitHubTokenSSMParameterName',
                    description='The name of the SSM Parameter with the GitHub OAuth Token',
                    value=action.github_token_parameter_name,
                )
                github_owner_param = self.create_cfn_parameter(
                    param_type='String',
                    name='GitHubOwner',
                    description='The name of the GitHub owner',
                    value=action.github_owner,
                )
                github_repo_param = self.create_cfn_parameter(
                    param_type='String',
                    name='GitHubRepository',
                    description='The name of the GitHub Repository',
                    value=action.github_repository,
                )
                github_deploy_branch_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='GitHubDeploymentBranchName',
                    description='The name of the branch where commits will trigger a build.',
                    value=action.deployment_branch_name,
                )

                github_source_action = troposphere.codepipeline.Actions(
                    Name='GitHub',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Source',
                        Owner = 'ThirdParty',
                        Version = '1',
                        Provider = 'GitHub'
                    ),
                    Configuration = {
                        'Owner': troposphere.Ref(github_owner_param),
                        'Repo': troposphere.Ref(github_repo_param),
                        'Branch': troposphere.Ref(github_deploy_branch_name_param),
                        'OAuthToken': troposphere.Ref(github_token_param),
                        'PollForSourceChanges': False
                    },
                    OutputArtifacts = [
                        troposphere.codepipeline.OutputArtifacts(
                            Name = 'GitHubArtifact'
                        )
                    ],
                    RunOrder = action.run_order,
                )
                source_stage_actions.append(github_source_action)
                self.build_input_artifacts.append(
                    troposphere.codepipeline.InputArtifacts(
                        Name = 'GitHubArtifact'
                    )
                )

            # CodeCommit Action
            elif action.type == 'CodeCommit.Source':
                if action.is_enabled():
                    self.codecommit_source = True
                self.codecommit_repo_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRepositoryArn',
                    description='The Arn of the CodeCommit repository',
                    value='{}.codecommit.arn'.format(action.paco_ref),
                )
                self.codecommit_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRoleArn',
                    description='The Arn of the CodeCommit Role',
                    value='{}.codecommit_role.arn'.format(action.paco_ref),
                )
                codecommit_repo_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRepositoryName',
                    description='The name of the CodeCommit repository',
                    value=action.codecommit_repository+'.name',
                )
                deploy_branch_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitDeploymentBranchName',
                    description='The name of the branch where commits will trigger a build.',
                    value=action.deployment_branch_name,
                )

                codecommit_source_action = troposphere.codepipeline.Actions(
                    Name='CodeCommit',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Source',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'CodeCommit'
                    ),
                    Configuration = {
                        'RepositoryName': troposphere.Ref(codecommit_repo_name_param),
                        'BranchName': troposphere.Ref(deploy_branch_name_param)
                    },
                    OutputArtifacts = [
                        troposphere.codepipeline.OutputArtifacts(
                            Name = 'CodeCommitArtifact'
                        )
                    ],
                    RunOrder = action.run_order,
                    RoleArn = troposphere.Ref(self.codecommit_role_arn_param)
                )
                source_stage_actions.append(codecommit_source_action)
                self.build_input_artifacts.append(
                    troposphere.codepipeline.InputArtifacts(
                        Name = 'CodeCommitArtifact'
                    )
                )

        source_stage = troposphere.codepipeline.Stages(
            Name="Source",
            Actions = source_stage_actions
        )

        # Build Actions
        build_stage_actions = []
        for action in self.pipeline.build.values():

            # Manual Approval Action
            if action.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(action)
                build_stage_actions.append(manual_approval_action)

            # CodeBuild Build Action
            elif action.type == 'CodeBuild.Build':
                self.codebuild_access = True
                self.codebuild_project_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeBuildProjectArn',
                    description='The arn of the CodeBuild project',
                    value='{}.project.arn'.format(action.paco_ref),
                )
                codebuild_build_action = troposphere.codepipeline.Actions(
                    Name='CodeBuild',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Build',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'CodeBuild'
                    ),
                    Configuration = {
                        'ProjectName': troposphere.Ref(self.resource_name_prefix_param),
                    },
                    InputArtifacts = self.build_input_artifacts,
                    OutputArtifacts = [
                        troposphere.codepipeline.OutputArtifacts(
                            Name = 'CodeBuildArtifact'
                        )
                    ],
                    RunOrder = action.run_order
                )
                build_stage_actions.append(codebuild_build_action)
        build_stage = troposphere.codepipeline.Stages(
            Name="Build",
            Actions = build_stage_actions
        )
        # Deploy Action
        [ deploy_stage,
          self.s3_deploy_assume_role_statement,
          self.codedeploy_deploy_assume_role_statement ] = self.init_deploy_stage()

        # Manual Deploy Enabled/Disable
        manual_approval_enabled_param = self.create_cfn_parameter(
            param_type='String',
            name='ManualApprovalEnabled',
            description='Boolean indicating whether a manual approval is enabled or not.',
            value=self.manual_approval_is_enabled,
        )
        self.template.add_condition(
            'ManualApprovalIsEnabled',
            troposphere.Equals(troposphere.Ref(manual_approval_enabled_param), 'true')
        )

        pipeline_stages = []
        if source_stage != None: pipeline_stages.append(source_stage)
        if build_stage != None: pipeline_stages.append(build_stage)
        if deploy_stage != None: pipeline_stages.append(deploy_stage)

        pipeline_service_role_res = self.add_pipeline_service_role()
        pipeline_res = troposphere.codepipeline.Pipeline(
            title = 'BuildCodePipeline',
            template = self.template,
            DependsOn='CodePipelinePolicy',
            RoleArn = troposphere.GetAtt(pipeline_service_role_res, 'Arn'),
            Name = troposphere.Ref(self.resource_name_prefix_param),
            Stages = pipeline_stages,
            ArtifactStore = troposphere.codepipeline.ArtifactStore(
                Type = 'S3',
                Location = troposphere.Ref(self.artifacts_bucket_name_param),
                EncryptionKey = troposphere.codepipeline.EncryptionKey(
                    Type = 'KMS',
                    Id = troposphere.Ref(self.cmk_arn_param),
                )
            )
        )

        return pipeline_res

    def init_manual_approval_action(self, action):
        self.manual_approval_is_enabled = action.is_enabled()
        # Manual Approval Deploy Action
        subscription_list = []
        for approval_email in action.manual_approval_notification_email:
            email_hash = utils.md5sum(str_data=approval_email)
            manual_approval_notification_email_param = self.create_cfn_parameter(
                param_type='String',
                name='ManualApprovalNotificationEmail'+email_hash,
                description='Email to send notifications to when a deployment requires approval.',
                value=approval_email,
            )
            subscription_list.append(
                troposphere.sns.Subscription(
                    Endpoint=troposphere.Ref(manual_approval_notification_email_param),
                    Protocol = 'email'
                )
            )

        manual_approval_sns_res = troposphere.sns.Topic(
            title = 'ManualApprovalSNSTopic',
            template=self.template,
            Condition = 'ManualApprovalIsEnabled',
            TopicName = troposphere.Sub('${ResourceNamePrefix}-Approval'),
            Subscription = subscription_list
        )
        manual_deploy_action = troposphere.codepipeline.Actions(
            Name='Approval',
            ActionTypeId = troposphere.codepipeline.ActionTypeId(
                Category = 'Approval',
                Owner = 'AWS',
                Version = '1',
                Provider = 'Manual'
            ),
            Configuration = {
                'NotificationArn': troposphere.Ref(manual_approval_sns_res),
            },
            RunOrder = action.run_order
        )
        manual_deploy_action = troposphere.If(
            'ManualApprovalIsEnabled',
            manual_deploy_action,
            troposphere.Ref('AWS::NoValue')
        )

        return manual_deploy_action

    def init_deploy_stage(self):
        if self.pipeline.deploy == None:
            return [None, None, None]
        deploy_stage_actions = []
        for action in self.pipeline.deploy.values():
            if action.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(action)
                deploy_stage_actions.append(manual_approval_action)

            # S3.Deploy
            s3_deploy_assume_role_statement = None
            if action.type == 'S3.Deploy':
                s3_deploy_bucket_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployBucketName',
                    description='The name of the S3 bucket to deploy to.',
                    value=action.bucket+'.name',
                )
                s3_deploy_extract_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployExtract',
                    description='Boolean indicating whether the deployment artifact will be extracted.',
                    value=action.extract,
                )
                s3_deploy_object_key_param = 'AWS::NoValue'
                if action.object_key != None:
                    s3_deploy_object_key_param = self.create_cfn_parameter(
                        param_type='String',
                        name='S3DeployObjectKey',
                        description='S3 object key to store the deployment artifact as.',
                        value=action.object_key,
                    )
                s3_deploy_delegate_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployDelegateRoleArn',
                    description='The Arn of the IAM Role CodePipeline will assume to gain access to the deployment bucket.',
                    value=action._delegate_role_arn,
                )
                # CodeDeploy Deploy Action
                s3_deploy_action = troposphere.codepipeline.Actions(
                    Name='S3',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Deploy',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'S3'
                    ),
                    Configuration = {
                        'BucketName': troposphere.Ref(s3_deploy_bucket_name_param),
                        'Extract': troposphere.Ref(s3_deploy_extract_param),
                        'ObjectKey': troposphere.Ref(s3_deploy_object_key_param),
                    },
                    InputArtifacts = [
                        troposphere.codepipeline.InputArtifacts(
                            Name = 'CodeBuildArtifact'
                        )
                    ],
                    RoleArn = troposphere.Ref(s3_deploy_delegate_role_arn_param),
                    RunOrder = troposphere.If('ManualApprovalIsEnabled', 2, 1)
                )
                s3_deploy_assume_role_statement = Statement(
                    Sid='S3AssumeRole',
                    Effect=Allow,
                    Action=[
                        Action('sts', 'AssumeRole'),
                    ],
                    Resource=[ troposphere.Ref(s3_deploy_delegate_role_arn_param) ]
                )
                deploy_stage_actions.append(s3_deploy_action)

            self.codedeploy_deploy_assume_role_statement = None
            if action.type == 'CodeDeploy.Deploy':
                codedeploy_tools_delegate_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployToolsDelegateRoleArn',
                    description='The Arn of the CodeDeploy Delegate Role',
                    value=action.paco_ref + '.codedeploy_tools_delegate_role.arn',
                )
                codedeploy_application_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployApplicationName',
                    description='The CodeDeploy Application name to deploy to.',
                    value=action.paco_ref+'.codedeploy_application_name',
                )
                codedeploy_group_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployGroupName',
                    description='The name of the CodeDeploy deployment group.',
                    value=action.paco_ref + '.deployment_group.name',
                )
                codedeploy_region_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployRegion',
                    description='The AWS Region where deployments to CodeDeploy will be sent.',
                    value=self.env_ctx.region,
                )
                # CodeDeploy Deploy Action
                codedeploy_deploy_action = troposphere.codepipeline.Actions(
                    Name='CodeDeploy',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Deploy',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'CodeDeploy'
                    ),
                    Configuration = {
                        'ApplicationName': troposphere.Ref(codedeploy_application_name_param),
                        'DeploymentGroupName': troposphere.Ref(codedeploy_group_name_param)
                    },
                    InputArtifacts = [
                        troposphere.codepipeline.InputArtifacts(
                            Name = 'CodeBuildArtifact'
                        )
                    ],
                    RoleArn = troposphere.Ref(codedeploy_tools_delegate_role_arn_param),
                    Region = troposphere.Ref(codedeploy_region_param),
                    RunOrder = troposphere.If('ManualApprovalIsEnabled', 2, 1)
                )
                codedeploy_deploy_assume_role_statement = Statement(
                    Sid='CodeDeployAssumeRole',
                    Effect=Allow,
                    Action=[
                        Action('sts', 'AssumeRole'),
                    ],
                    Resource=[ troposphere.Ref(codedeploy_tools_delegate_role_arn_param) ]
                )
                deploy_stage_actions.append(codedeploy_deploy_action)
        deploy_stage = troposphere.codepipeline.Stages(
            Name="Deploy",
            Actions = deploy_stage_actions
        )
        return [deploy_stage, s3_deploy_assume_role_statement, codedeploy_deploy_assume_role_statement]

    def get_codepipeline_role_arn(self):
        return "arn:aws:iam::{}:role/{}".format(
            self.account_ctx.get_id(),
            self.pipeline_service_role_name
        )
