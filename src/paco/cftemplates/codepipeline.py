from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole
from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.cftemplates.eventsrule import create_event_rule_name
from paco.models.references import get_model_obj_from_ref, Reference, is_ref
import awacs.codepipeline
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.events
import troposphere.iam
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
        'properties_method': 'create_github_source_properties',
    },
    'ECR.Source': {
        'Name': 'ECR',
        'Category': 'Source',
        'Owner': 'AWS',
        'Version': '1',
        'Provider': 'ECR',
        'properties_method': 'create_ecr_source_properties',
    },
    'S3.Deploy': {
        'Name': 'S3Deploy',
        'Category': 'Deploy',
        'Owner': 'AWS',
        'Version': '1',
        'Provider': 'S3',
        'properties_method': 'create_s3deploy_properties',
    },
    'CodeDeploy.Deploy': {
        # ToDo
    },
    'CodeCommit.Source': {
        # ToDo
    },
    'Lambda.Invoke': {
        'Name': 'LambdaInvoke',
        'Category': 'Invoke',
        'Owner': 'AWS',
        'Version': '1',
        'Provider': 'Lambda',
        'OutputArtifacts': [],
        'properties_method': 'create_lambda_invoke_properties',
    },
    'ManualApproval': {
        # ToDo
    },
    'ECS.Deploy': {
        # ToDo
    },
}


class CodePipeline(StackTemplate):
    def __init__(self, stack, paco_ctx, base_aws_name, deploy_region, app_name, artifacts_bucket_name):
        self.pipeline = stack.resource
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('CodePipeline', self.resource_group_name, self.resource.name)
        self.deploy_region = deploy_region

        # Troposphere Template Initialization
        self.init_template('Deployment: CodePipeline')

        if not self.pipeline.is_enabled():
            return

        # Flags set to False, they will be set to True if there is an Action to indicate they will need Role support
        self.codecommit_source_enabled = False
        self.ecr_source_enabled = False
        self.s3_source_enabled = False
        self.github_source_enabled = False
        self.codebuild_access_enabled = False
        self.lambda_invoke_enabled = False
        self.s3_deploy_enabled = False
        self.manual_approval_is_enabled = False
        self.s3_deploy_statements = []
        self.ecs_deploy_assume_role_statement = None

        self.codedeploy_deploy_assume_role_statement = None
        self.s3_deploy_assume_role_statement = None

        self.res_name_prefix = self.create_resource_name_join(
            name_list=[base_aws_name, app_name, self.resource_group_name, self.resource.name],
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

        if self.pipeline.stages != None:
            self.create_pipeline_from_stages()
        else:
            self.create_pipeline_from_sourcebuilddeploy(deploy_region)

    @property
    def troposphere_pipeline_arn(self):
        return troposphere.Join(
            ':', [
                f"arn:aws:codepipeline:{self.stack.aws_region}:{self.stack.account_ctx.get_id()}",
                self.res_name_prefix
            ]
        )
    @property
    def pipeline_arn(self):
        return ':'.join([f"arn:aws:codepipeline:{self.stack.aws_region}:{self.stack.account_ctx.get_id()}",self.res_name_prefix])

    def add_github_webhook(self, pipeline_res, stage_name, action, sourcebuilddeploy=False):
        "Add a CodePipeline WebHook"
        if sourcebuilddeploy == True:
            target_action = 'GitHub'
        else:
            target_action = f'GitHub{stage_name}{action.name}'
        logical_id = f'Webhook{stage_name}{action.name}'
        if action.github_access_token.startswith('paco.ref '):
            github_access_token = "{{resolve:secretsmanager:%s}}" % Reference(action.github_access_token).ref
        else:
            github_access_token = action.github_access_token
        cfn_export_dict= {
            'Authentication': 'GITHUB_HMAC',
            'AuthenticationConfiguration': {
                'SecretToken': github_access_token,
            },
            'Filters': [{'JsonPath': "$.ref", 'MatchEquals': 'refs/heads/{Branch}'}],
            'TargetAction': target_action,
            'RegisterWithThirdParty': True,
            'TargetPipeline': troposphere.Ref(pipeline_res),
            'TargetPipelineVersion': troposphere.GetAtt(pipeline_res, 'Version'),
        }
        webhook_resource = troposphere.codepipeline.Webhook.from_dict(
            logical_id,
            cfn_export_dict,
        )
        self.template.add_resource(webhook_resource)

    def create_pipeline_from_stages(self):
        "Create CodePipeline Actions resources based on the .stages field"
        # create the Stages/Actions resources
        # set flags
        self.s3deploy_buckets = {}
        for stage in self.pipeline.stages.values():
            for action in stage.values():
                if not action.is_enabled():
                    continue
                if action.type == 'GitHub.Source':
                    self.github_source_enabled = True
                elif action.type == 'Lambda.Invoke':
                    self.lambda_invoke_enabled = True
                elif action.type == 'Paco.CreateThenDeployImage':
                    self.lambda_invoke_enabled = True
                elif action.type == 'S3.Deploy':
                    self.s3_deploy_enabled = True
                    bucket = get_model_obj_from_ref(action.bucket, self.paco_ctx.project)
                    account = get_model_obj_from_ref(bucket.account, self.paco_ctx.project)
                    self.s3deploy_buckets[account.name] = None
                elif action.type == 'ManualApproval':
                    self.manual_approval_enabled = True

        # Parameters for shared Roles
        for account_name in self.s3deploy_buckets.keys():
            self.s3deploy_buckets[account_name] = self.create_cfn_parameter(
                param_type='String',
                name='{}S3DeployDelegateRoleArn'.format(account_name),
                description='The Arn of the IAM Role CodePipeline will assume to gain access to the deployment bucket.',
                value=self.pipeline.paco_ref + '.s3deploydelegate_{}.arn'.format(account_name),
            )
            s3_deploy_assume_role_statement = Statement(
                Sid='S3AssumeRole',
                Effect=Allow,
                Action=[
                    Action('sts', 'AssumeRole'),
                ],
                Resource=[ troposphere.Ref(self.s3deploy_buckets[account_name]) ]
            )
            self.s3_deploy_statements.append(s3_deploy_assume_role_statement)

        stages = []
        for stage in self.pipeline.stages.values():
            actions = []
            for action in stage.values():
                if not action.is_enabled():
                    continue
                info = ACTION_MAP[action.type]
                action_kwargs = {
                    'ActionTypeId': troposphere.codepipeline.ActionTypeId(
                        Category=info['Category'],
                        Owner=info['Owner'],
                        Version=info['Version'],
                        Provider=info['Provider'],
                    ),
                }
                properties = getattr(self, info['properties_method'])(stage, action, info)
                # run order can be supplied from action.run_order
                if 'RunOrder' not in properties:
                    properties['RunOrder'] = action.run_order
                # if no OutputArtifacts/InputArtifacts default to []
                if 'InputArtifacts' not in properties:
                    properties['InputArtifacts'] = []
                if 'OutputArtifacts' not in properties:
                    properties['OutputArtifacts'] = []
                for key, value in properties.items():
                    action_kwargs[key] = value
                action_resource = troposphere.codepipeline.Actions(
                    Name=self.create_cfn_logical_id(info['Name'] + stage.name + action.name),
                    **action_kwargs,
                )
                actions.append(action_resource)
            stage_resource = troposphere.codepipeline.Stages(
                Name=self.create_cfn_logical_id('PipelineStage' + stage.name),
                Actions=actions
            )
            stages.append(stage_resource)

        pipeline_service_role_res = self.add_pipeline_service_role()
        pipeline_res = troposphere.codepipeline.Pipeline(
            title='BuildCodePipeline',
            template=self.template,
            DependsOn='CodePipelinePolicy',
            RoleArn=troposphere.GetAtt(pipeline_service_role_res, 'Arn'),
            Name=troposphere.Ref(self.resource_name_prefix_param),
            Stages=stages,
            ArtifactStore=troposphere.codepipeline.ArtifactStore(
                Type='S3',
                Location=troposphere.Ref(self.artifacts_bucket_name_param),
                EncryptionKey=troposphere.codepipeline.EncryptionKey(
                    Type='KMS',
                    Id=troposphere.Ref(self.cmk_arn_param),
                )
            )
        )

        # Add GitHub WebHook after pipeline_res is created
        for stage in self.pipeline.stages.values():
            for action in stage.values():
                if not action.is_enabled():
                    continue
                if action.type == 'GitHub.Source' and action.poll_for_source_changes == False:
                    self.add_github_webhook(pipeline_res, stage.name, action)

    # methods to return Properties dictionaries specific to their Action.Type
    # begin create_<action_type>_properties
    def create_lambda_invoke_properties(self, stage, action, info):
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
            'Configuration': {
                'FunctionName': lambda_function_name,
                'UserParameters': troposphere.Ref(user_parameters_param),
            },
        }

    def create_s3deploy_properties(self, stage, action, info):
        base_name = stage.name + action.name
        s3_deploy_bucket_name_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('S3DeployBucketName' + base_name),
            description='The name of the S3 bucket to deploy to.',
            value=action.bucket + '.name',
        )
        s3_deploy_extract_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('S3DeployExtract' + base_name),
            description='Boolean indicating whether the deployment artifact will be extracted.',
            value=action.extract,
        )
        s3_deploy_object_key_param = 'AWS::NoValue'
        if action.object_key != None:
            s3_deploy_object_key_param = self.create_cfn_parameter(
                param_type='String',
                name=self.create_cfn_logical_id('S3DeployObjectKey' + base_name),
                description='S3 object key to store the deployment artifact as.',
                value=action.object_key,
            )

        bucket = get_model_obj_from_ref(action.bucket, self.paco_ctx.project)
        account = get_model_obj_from_ref(bucket.account, self.paco_ctx.project)
        input_artifacts = []
        for artifact in action.input_artifacts:
            stage_name, action_name = artifact.split('.')
            source_action = self.pipeline.stages[stage_name][action_name]
            input_name = '{}Artifact{}{}'.format(
                ACTION_MAP[source_action.type]['Name'],
                stage_name,
                action_name,
            )
            input_artifacts.append(
                troposphere.codepipeline.InputArtifacts(Name=input_name)
            )
        return {
            'Configuration': {
                'BucketName': troposphere.Ref(s3_deploy_bucket_name_param),
                'Extract': troposphere.Ref(s3_deploy_extract_param),
                'ObjectKey': troposphere.Ref(s3_deploy_object_key_param),
            },
            'InputArtifacts': input_artifacts,
            'RoleArn': troposphere.Ref(self.s3deploy_buckets[account.name]),
            #'RunOrder': troposphere.If('ManualApprovalIsEnabled', 2, 1)
        }

    def create_github_source_properties(self, stage, action, info):

        github_owner_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubOwner' + stage.name + action.name),
            description='The name of the GitHub owner',
            value=action.github_owner
        )
        github_repo_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubRepository' + stage.name + action.name),
            description='The name of the GitHub Repository',
            value=action.github_repository
        )
        github_deploy_branch_name_param = self.create_cfn_parameter(
            param_type='String',
            name=self.create_cfn_logical_id('GitHubDeploymentBranchName' + stage.name + action.name),
            description='The name of the branch where commits will trigger a build.',
            value=action.deployment_branch_name
        )
        output_artifact_name = '{}Artifact{}{}'.format(info['Name'], stage.name, action.name)
        if action.github_access_token.startswith('paco.ref '):
            github_access_token = "{{resolve:secretsmanager:%s}}" % Reference(action.github_access_token).ref
        else:
            github_access_token = action.github_access_token
        return {
            'Configuration': {
                'Owner': troposphere.Ref(github_owner_param),
                'Repo': troposphere.Ref(github_repo_param),
                'Branch': troposphere.Ref(github_deploy_branch_name_param),
                'OAuthToken': github_access_token,
                'PollForSourceChanges': action.poll_for_source_changes,
            },
            'OutputArtifacts': [ troposphere.codepipeline.OutputArtifacts(Name=output_artifact_name) ]
        }

    # end create_<action_type>_properties

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
                Sid='KMSCMK',
                Effect=Allow,
                Action=[
                    Action('kms', 'Decrypt'),
                ],
                Resource=[ troposphere.Ref(self.cmk_arn_param) ]
            ),
        ]
        # S3.Source Action requires more generous permissions on the Artifacts S3 Bucket
        if self.s3_source_enabled:
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='S3Access',
                    Effect=Allow,
                    Action=[
                        Action('s3', 'ReplicateObject'),
                        Action('s3', 'Put*'),
                        Action('s3', 'Get*'),
                        Action('s3', 'List*'),
                    ],
                    Resource=[
                        troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}/*'),
                        troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}')
                    ]
                ),
            )
        else:
            pipeline_policy_statement_list.append(
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
            )
        if self.lambda_invoke_enabled:
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
        if self.codebuild_access_enabled:
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
        if self.ecr_source_enabled:
            # Add Statement to allow ECR
            pipeline_policy_statement_list.append(
                Statement(
                    Sid='ECRPullAccess',
                    Effect=Allow,
                    Action=[
                        Action('ecr', 'Describe*'),
                        Action('ecr', 'List*'),
                        Action('ecr', 'Get*'),
                    ],
                    Resource=['*']
                )
            )
        if self.codecommit_source_enabled:
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
        if self.github_source_enabled:
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

        if self.ecs_deploy_assume_role_statement != None:
            pipeline_policy_statement_list.append(self.ecs_deploy_assume_role_statement)
        for statement in self.s3_deploy_statements:
            pipeline_policy_statement_list.append(statement)
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

    def create_pipeline_from_sourcebuilddeploy(self, deploy_region):
        """
        Use the fixed YAML of source/build/deploy to create the pipeline actions:
          source:
          build:
          deploy:
        """
        # CodePipeline
        # Source Actions
        source_stage_actions = []
        # Source Actions
        for action in self.pipeline.source.values():
            self.build_input_artifacts = []
            self.deploy_input_artifacts = []

            # Manual Approval Action
            if action.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(action)
                source_stage_actions.append(manual_approval_action)

            # GitHub Action
            elif action.type == 'GitHub.Source':
                if action.is_enabled():
                    self.github_source_enabled = True
                #github_token_param = self.create_cfn_parameter(
                #    param_type='AWS::SSM::Parameter::Value<String>',
                #    name='GitHubTokenSSMParameterName',
                #    description='The name of the SSM Parameter with the GitHub OAuth Token',
                #    value=action.github_token_parameter_name,
                #)
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

                if action.github_access_token.startswith('paco.ref '):
                    github_access_token = "{{resolve:secretsmanager:%s}}" % Reference(action.github_access_token).ref
                else:
                    github_access_token = action.github_access_token
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
                        'OAuthToken': github_access_token,
                        'PollForSourceChanges': False,
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
                        Name='GitHubArtifact'
                    )
                )
            # ECR.Source Action
            elif action.type == 'ECR.Source':
                if action.is_enabled():
                    self.ecr_source_enabled = True
                    self.s3_source_enabled = True
                if is_ref(action.repository):
                    ecr = get_model_obj_from_ref(action.repository, self.paco_ctx.project)
                    ecr_name = ecr.repository_name
                else:
                    ecr_name = action.repository
                ecr_repo_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='ECRRepositoryARN',
                    description='The ARN of the ECR repository',
                    value=ecr_name,
                )
                ecr_source_action = troposphere.codepipeline.Actions(
                    Name='ECR',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Source',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'ECR'
                    ),
                    Configuration = {
                        'RepositoryName': troposphere.Ref(ecr_repo_name_param),
                        'ImageTag': action.image_tag,
                    },
                    OutputArtifacts = [
                        troposphere.codepipeline.OutputArtifacts(
                            Name='ECRArtifact'
                        )
                    ],
                    RunOrder = action.run_order,
                )
                source_stage_actions.append(ecr_source_action)

                # EventRule that is invoked when ECR image is tagged
                events_rule_role_resource = troposphere.iam.Role(
                    title='EventsRuleRole',
                    template=self.template,
                    AssumeRolePolicyDocument=Policy(
                        Version='2012-10-17',
                        Statement=[
                            Statement(
                                Effect=Allow,
                                Action=[AssumeRole],
                                Principal=Principal('Service',['events.amazonaws.com'])
                            )
                        ],
                    ),
                    Policies=[
                        troposphere.iam.Policy(
                            PolicyName="TargetInvocation",
                            PolicyDocument=Policy(
                                Version='2012-10-17',
                                Statement=[
                                    Statement(
                                        Effect=Allow,
                                        Action=[awacs.codepipeline.StartPipelineExecution],
                                        Resource=[self.troposphere_pipeline_arn],
                                    )
                                ]
                            )
                        )
                    ],
                )

                event_rule_name = create_event_rule_name(self.resource)
                ecr_event_pattern = {
                    "source": ["aws.ecr"],
                    "detail": {
                        "action-type": ["PUSH"],
                        "image-tag": [action.image_tag],
                        "repository-name": [ecr_name],
                        "result": ["SUCCESS"],
                    },
                    "detail-type": ["ECR Image Action"]
                }
                pipeline_target = troposphere.events.Target(
                    'PipelineTarget',
                    Id='ECRPipelineTarget',
                    Arn=self.troposphere_pipeline_arn,
                    RoleArn=troposphere.GetAtt(events_rule_role_resource, 'Arn'),
                )
                event_rule_resource = troposphere.events.Rule(
                    title='ECRSourceEventRule',
                    template=self.template,
                    Name=event_rule_name,
                    Description='Automatically start CodePipeline when a change occurs in an Amazon ECR image tag.',
                    State='ENABLED',
                    EventPattern=ecr_event_pattern,
                    Targets=[pipeline_target],
                )

                # static S3 imagedefinitions.json workaround
                # ECR.Source outputs an imageDetails.json file while ECS.Deploy expects and imageDefinitions.json
                # the later file contains the name of the ECS Service to deploy to. As a workaround, a file
                # with an imageDefinitions.json is placed in the S3 artifacts bucket and that file needs to be
                # used as a S3 Source
                # https://stackoverflow.com/questions/55339872/codepipeline-ecr-source-ecs-deploy-configuration
                s3_source_action = troposphere.codepipeline.Actions(
                    Name='S3ECRImageDefinitionsSource',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category='Source',
                        Owner='AWS',
                        Version='1',
                        Provider='S3'
                    ),
                    Configuration={
                        'S3Bucket': troposphere.Ref(self.artifacts_bucket_name_param),
                        'S3ObjectKey': troposphere.Join(
                            '-',
                            [troposphere.Ref('AWS::StackName'), 'imagedef.zip']
                        ),
                        'PollForSourceChanges': False,
                    },
                    OutputArtifacts=[
                        troposphere.codepipeline.OutputArtifacts(
                            Name='S3ImageDefArtifact'
                        )
                    ],
                    RunOrder=action.run_order,
                )
                source_stage_actions.append(s3_source_action)

                self.deploy_input_artifacts.append(
                    troposphere.codepipeline.InputArtifacts(Name='S3ImageDefArtifact')
                )

            # CodeCommit Action
            elif action.type == 'CodeCommit.Source':
                if action.is_enabled():
                    self.codecommit_source_enabled = True
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
                        Name='CodeCommitArtifact'
                    )
                )

        source_stage = troposphere.codepipeline.Stages(
            Name="Source",
            Actions = source_stage_actions
        )

        # Build Actions
        build_stage = None
        build_stage_actions = []
        if self.pipeline.build != None:
            for action in self.pipeline.build.values():

                # Manual Approval Action
                if action.type == 'ManualApproval':
                    manual_approval_action = self.init_manual_approval_action(action)
                    build_stage_actions.append(manual_approval_action)

                # CodeBuild Build Action
                elif action.type == 'CodeBuild.Build':
                    self.codebuild_access_enabled = True
                    self.codebuild_project_arn_param = self.create_cfn_parameter(
                        param_type='String',
                        name='CodeBuildProjectArn',
                        description='The arn of the CodeBuild project',
                        value='{}.project.arn'.format(action.paco_ref),
                    )
                    codebuild_build_action = troposphere.codepipeline.Actions(
                        Name='CodeBuild',
                        ActionTypeId = troposphere.codepipeline.ActionTypeId(
                            Category='Build',
                            Owner='AWS',
                            Version='1',
                            Provider='CodeBuild',
                        ),
                        Configuration = {
                            'ProjectName': troposphere.Ref(self.resource_name_prefix_param),
                        },
                        InputArtifacts = self.build_input_artifacts,
                        OutputArtifacts = [
                            troposphere.codepipeline.OutputArtifacts(
                                Name='CodeBuildArtifact',
                            )
                        ],
                        RunOrder = action.run_order
                    )
                    build_stage_actions.append(codebuild_build_action)
            build_stage = troposphere.codepipeline.Stages(
                Name="Build",
                Actions=build_stage_actions,
            )

        # Deploy Actions
        [ deploy_stage,
          self.s3_deploy_assume_role_statement,
          self.codedeploy_deploy_assume_role_statement,
          self.ecs_deploy_assume_role_statement ] = self.init_deploy_stage(deploy_region)

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
            title='BuildCodePipeline',
            template=self.template,
            DependsOn='CodePipelinePolicy',
            RoleArn=troposphere.GetAtt(pipeline_service_role_res, 'Arn'),
            Name=troposphere.Ref(self.resource_name_prefix_param),
            Stages=pipeline_stages,
            ArtifactStore=troposphere.codepipeline.ArtifactStore(
                Type='S3',
                Location=troposphere.Ref(self.artifacts_bucket_name_param),
                EncryptionKey=troposphere.codepipeline.EncryptionKey(
                    Type='KMS',
                    Id=troposphere.Ref(self.cmk_arn_param),
                )
            )
        )

        # Output
        self.create_output(
            title='CodePipelineName',
            description="CodePipeline Name",
            value=troposphere.Ref(pipeline_res),
            ref=self.pipeline.paco_ref_parts + ".name"
        )

        # Add GitHub WebHook after pipeline_res is created
        for action in self.pipeline.source.values():
            if not action.is_enabled():
                continue
            if action.type == 'GitHub.Source' and action.poll_for_source_changes == False:
                self.add_github_webhook(pipeline_res, 'source', action, sourcebuilddeploy=True)

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
                Category='Approval',
                Owner='AWS',
                Version='1',
                Provider='Manual',
            ),
            Configuration = {
                'NotificationArn': troposphere.Ref(manual_approval_sns_res),
            },
            RunOrder = action.run_order
        )
        manual_deploy_action = troposphere.If(
            'ManualApprovalIsEnabled',
            manual_deploy_action,
            troposphere.Ref('AWS::NoValue'),
        )

        return manual_deploy_action

    def init_deploy_stage(self, deploy_region):
        "Initialize the Deploy Stage Action(s)"
        if self.pipeline.deploy == None:
            return [None, None, None, None]
        deploy_stage_actions = []
        s3_deploy_assume_role_statement = None
        codedeploy_deploy_assume_role_statement = None
        ecs_deploy_assume_role_statement = None
        for action in self.pipeline.deploy.values():
            if action.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(action)
                deploy_stage_actions.append(manual_approval_action)

            # S3.Deploy
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
                    value=self.deploy_region,
                )
                # CodeDeploy Deploy Action
                codedeploy_deploy_action = troposphere.codepipeline.Actions(
                    Name='CodeDeploy',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category='Deploy',
                        Owner='AWS',
                        Version='1',
                        Provider='CodeDeploy',
                    ),
                    Configuration = {
                        'ApplicationName': troposphere.Ref(codedeploy_application_name_param),
                        'DeploymentGroupName': troposphere.Ref(codedeploy_group_name_param)
                    },
                    InputArtifacts = [
                        troposphere.codepipeline.InputArtifacts(
                            Name='CodeBuildArtifact',
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
            if action.type == 'ECS.Deploy':
                # can take input from an ECR.Source output or a CodeBuild output
                if self.deploy_input_artifacts != []:
                    input_artifact_name = self.deploy_input_artifacts
                else:
                    input_artifact_name = [
                        troposphere.codepipeline.InputArtifacts(
                            Name='CodeBuildArtifact'
                        )
                    ]
                ecs_tools_delegate_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='ECSToolsDelegateRoleArn',
                    description='The Arn of the ECS Cluster Delegate Role',
                    value=action._delegate_role_arn
                )
                ecs_cluster_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='ECSClusterName',
                    description='The name of the ECS cluster to deploy to.',
                    value=action.cluster + '.name'
                )
                ecs_service_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='ECSClusterServiceName',
                    description='The name of the ECS cluster service to deploy to.',
                    value=action.service + '.name'
                )
                ecs_deploy_action = troposphere.codepipeline.Actions(
                    Name='ECS',
                    ActionTypeId = troposphere.codepipeline.ActionTypeId(
                        Category = 'Deploy',
                        Owner = 'AWS',
                        Version = '1',
                        Provider = 'ECS'
                    ),
                    Configuration = {
                        'ClusterName': troposphere.Ref(ecs_cluster_name_param),
                        'ServiceName': troposphere.Ref(ecs_service_name_param)
                    },
                    InputArtifacts=input_artifact_name,
                    RoleArn = troposphere.Ref(ecs_tools_delegate_role_arn_param),
                    Region = deploy_region,
                    RunOrder = troposphere.If('ManualApprovalIsEnabled', 2, 1)
                )
                ecs_deploy_assume_role_statement = Statement(
                    Sid='ECSAssumeRole',
                    Effect=Allow,
                    Action=[
                        Action('sts', 'AssumeRole'),
                    ],
                    Resource=[ troposphere.Ref(ecs_tools_delegate_role_arn_param) ]
                )
                deploy_stage_actions.append(ecs_deploy_action)
        deploy_stage = troposphere.codepipeline.Stages(
            Name="Deploy",
            Actions = deploy_stage_actions
        )
        return [deploy_stage, s3_deploy_assume_role_statement, codedeploy_deploy_assume_role_statement, ecs_deploy_assume_role_statement]

    def get_codepipeline_role_arn(self):
        return "arn:aws:iam::{}:role/{}".format(
            self.account_ctx.get_id(),
            self.pipeline_service_role_name
        )
