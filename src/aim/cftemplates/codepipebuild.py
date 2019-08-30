import os
from aim.cftemplates.cftemplates import CFTemplate
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns
from io import StringIO
from enum import Enum
from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole

class CodePipeBuild(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 env_ctx,
                 aws_name,
                 app_id,
                 grp_id,
                 res_id,
                 res_config,
                 artifacts_bucket_name,
                 codedeploy_tools_delegate_role_arn,
                 cpbd_config_ref):
        self.env_ctx = env_ctx
        #aim_ctx.log("S3 CF Template init")
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         enabled=res_config.is_enabled(),
                         config_ref=cpbd_config_ref,
                         aws_name='-'.join(["CPBD-PipeBuild", aws_name]),
                         iam_capabilities=["CAPABILITY_NAMED_IAM"],
                         stack_group=stack_group,
                         stack_tags=stack_tags)


        # Troposphere Template Initialization
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('Deployment: CodePipeline and CodeBuild')
        #template.add_resource(
        #    troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
        #)

        self.res_name_prefix = self.create_resource_name_join(
            name_list=[env_ctx.get_aws_name(), app_id, grp_id, res_id],
            separator='-',
            camel_case=True)

        self.resource_name_prefix_param = self.create_cfn_parameter(
            param_type='String',
            name='ResourceNamePrefix',
            description='The name to prefix resource names.',
            value=self.res_name_prefix,
            use_troposphere=True,
            troposphere_template=template,
        )

        self.cmk_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='CMKArn',
            description='The KMS CMK Arn of the key used to encrypt deployment artifacts.',
            value=res_config.aim_ref + '.kms.arn',
            use_troposphere=True,
            troposphere_template=template,
        )
        self.artifacts_bucket_name_param = self.create_cfn_parameter(
            param_type='String',
            name='ArtifactsBucketName',
            description='The name of the S3 Bucket to create that will hold deployment artifacts',
            value=artifacts_bucket_name,
            use_troposphere=True,
            troposphere_template=template,
        )
        self.codecommit_repo_name_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeCommitRepositoryName',
            description='The name of the CodeCommit repository',
            value=res_config.codecommit_repository+'.name',
            use_troposphere=True,
            troposphere_template=template,
        )

        self.codebuild_project_res = self.create_codebuild_cfn(
            template,
            res_config,
        )
        self.create_codepipeline_cfn(
            template,
            res_config,
            codedeploy_tools_delegate_role_arn
        )

        self.set_template(template.to_yaml())

        return

    def create_codebuild_cfn(
        self,
        template,
        res_config,
    ):
        # CodeBuild
        compute_type_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeBuildComputeType',
            description='The type of compute environment. This determines the number of CPU cores and memory the build environment uses.',
            value=res_config.codebuild_compute_type,
            use_troposphere=True,
            troposphere_template=template,
        )
        image_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeBuildImage',
            description='The image tag or image digest that identifies the Docker image to use for this build project.',
            value=res_config.codebuild_image,
            use_troposphere=True,
            troposphere_template=template,
        )
        deploy_env_name_param = self.create_cfn_parameter(
            param_type='String',
            name='DeploymentEnvironmentName',
            description='The name of the environment codebuild will be deploying into.',
            value=res_config.deployment_environment,
            use_troposphere=True,
            troposphere_template=template,
        )

        project_role_res = troposphere.iam.Role(
            title='CodeBuildProjectRole',
            RoleName=troposphere.Sub('${ResourceNamePrefix}-CodeBuild'),
            AssumeRolePolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[ AssumeRole ],
                        Principal=Principal("Service", ['codebuild.amazonaws.com']),
                    )
                ]
            )
        )
        template.add_resource(project_role_res)

        project_policy_res = troposphere.iam.PolicyType(
            title='CodeBuildProjectPolicy',
            PolicyName=troposphere.Sub('${ResourceNamePrefix}-CodeBuildProject-Policy'),
            PolicyDocument=PolicyDocument(
                Statement=[
                    Statement(
                        Sid='S3Access',
                        Effect=Allow,
                        Action=[
                            Action('s3', 'PutObject'),
                            Action('s3', 'PutObjectAcl'),
                            Action('s3', 'GetObject'),
                            Action('s3', 'GetObjectAcl'),
                            Action('s3', 'ListBucket'),
                            Action('s3', 'DeleteObject'),
                            Action('s3', 'GetBucketPolicy'),
                        ],
                        Resource=[
                            troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}'),
                            troposphere.Sub('arn:aws:s3:::${ArtifactsBucketName}/*'),
                        ]
                    ),
                    Statement(
                        Sid='CloudWatchLogsAccess',
                        Effect=Allow,
                        Action=[
                            Action('logs', 'CreateLogGroup'),
                            Action('logs', 'CreateLogStream'),
                            Action('logs', 'PutLogEvents'),
                        ],
                        Resource=[ 'arn:aws:logs:*:*:*' ]
                    ),
                    Statement(
                        Sid='KMSCMK',
                        Effect=Allow,
                        Action=[
                            Action('kms', '*')
                        ],
                        Resource=[ troposphere.Ref(self.cmk_arn_param) ]
                    ),
                ],
            ),
            Roles=[troposphere.Ref(project_role_res)]
        )
        template.add_resource(project_policy_res)

        # CodeBuild Project Resource
        timeout_mins_param = self.create_cfn_parameter(
            param_type='String',
            name='TimeoutInMinutes',
            description='How long, in minutes, from 5 to 480 (8 hours), for AWS CodeBuild to wait before timing out any related build that did not get marked as completed.',
            value=res_config.timeout_mins,
            use_troposphere=True,
            troposphere_template=template,
        )

        # CodeBuild: Environment
        environment = troposphere.codebuild.Environment(
            Type = 'LINUX_CONTAINER',
            ComputeType = troposphere.Ref(compute_type_param),
            Image = troposphere.Ref(image_param),
            EnvironmentVariables = [{
                'Name': 'ArtifactsBucket',
                'Value': troposphere.Ref(self.artifacts_bucket_name_param),
            }, {
                'Name': 'DeploymentEnvironmentName',
                'Value': troposphere.Ref(deploy_env_name_param)
            }, {
                'Name': 'KMSKey',
                'Value': troposphere.Ref(self.cmk_arn_param)
            }]
        )
        project_res = troposphere.codebuild.Project(
            title = 'CodeBuildProject',
            template = template,
            Name = troposphere.Ref(self.resource_name_prefix_param),
            Description = troposphere.Ref(self.codecommit_repo_name_param),
            ServiceRole = troposphere.GetAtt('CodeBuildProjectRole', 'Arn'),
            EncryptionKey = troposphere.Ref(self.cmk_arn_param),
            Artifacts = troposphere.codebuild.Artifacts(
                Type = 'CODEPIPELINE'
            ),
            Environment = environment,
            Source = troposphere.codebuild.Source(
                Type = 'CODEPIPELINE'
            ),
            TimeoutInMinutes = troposphere.Ref(timeout_mins_param),
            Tags = troposphere.codebuild.Tags(
                Name = troposphere.Ref(self.resource_name_prefix_param)
            )
        )

        return project_res

    def create_codepipeline_cfn(
        self,
        template,
        res_config,
        codedeploy_tools_delegate_role_arn
    ):
        # CodePipeline
        deploy_branch_name_param = self.create_cfn_parameter(
            param_type='String',
            name='DeploymentBranchName',
            description='The name of the branch where commits will trigger a build.',
            value=res_config.deployment_branch_name,
            use_troposphere=True,
            troposphere_template=template,
        )
        manual_approval_notification_email_param = self.create_cfn_parameter(
            param_type='String',
            name='ManualApprovalNotificationEmail',
            description='Email to send notifications to when a deployment requires approval.',
            value=res_config.manual_approval_notification_email,
            use_troposphere=True,
            troposphere_template=template,
        )
        manual_approval_enabled_param = self.create_cfn_parameter(
            param_type='String',
            name='ManualApprovalEnabled',
            description='Boolean indicating whether a manual approval is enabled or not.',
            value=res_config.manual_approval_enabled,
            use_troposphere=True,
            troposphere_template=template,
        )

        template.add_condition(
            'ManualApprovalIsEnabled',
            troposphere.Equals(troposphere.Ref(manual_approval_enabled_param), 'true')
        )

        manual_approval_sns_res = troposphere.sns.Topic(
            title = 'ManualApprovalSNSTopic',
            template=template,
            Condition = 'ManualApprovalIsEnabled',
            TopicName = troposphere.Sub('${ResourceNamePrefix}-Approval'),
            Subscription = [
                troposphere.sns.Subscription(
                    Endpoint=troposphere.Ref(manual_approval_notification_email_param),
                    Protocol = 'email'
                )
            ]
        )

        pipeline_service_role_res = troposphere.iam.Role(
            title='CodePipelineServiceRole',
            template = template,
            RoleName=troposphere.Sub('${ResourceNamePrefix}-CodePipeline-Service'),
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
        # CodePipeline: Policy
        codecommit_repo_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeCommitRepositoryArn',
            description='The Arn of the CodeCommit repository',
            value=res_config.aim_ref + '.codecommit.arn',
            use_troposphere=True,
            troposphere_template=template
        )
        codecommit_role_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeCommitRoleArn',
            description='The Arn of the CodeCommit Role',
            value=res_config.aim_ref + '.codecommit_role.arn',
            use_troposphere=True,
            troposphere_template=template
        )

        codedeploy_tools_delegate_role_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeDeployToolsDelegateRoleArn',
            description='The Arn of the CodeDeploy Delegate Role',
            value=codedeploy_tools_delegate_role_arn,
            use_troposphere=True,
            troposphere_template=template
        )

        codedeploy_application_name_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeDeployApplicationName',
            description='The CodeDeploy Application name to deploy to.',
            value=res_config.aim_ref+'.codedeploy_application_name',
            use_troposphere=True,
            troposphere_template=template
        )
        codedeploy_group_name_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeDeployGroupName',
            description='The name of the CodeDeploy deployment group.',
            value=res_config.aim_ref + '.deploy.deployment_group.name',
            use_troposphere=True,
            troposphere_template=template
        )
        codedeploy_region_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeDeployRegion',
            description='The AWS Region where deployments to CodeDeploy will be sent.',
            value=self.env_ctx.region,
            use_troposphere=True,
            troposphere_template=template
        )

        troposphere.iam.PolicyType(
            title='CodePipelinePolicy',
            template = template,
            PolicyName=troposphere.Sub('${ResourceNamePrefix}-CodePipeline-Policy'),
            PolicyDocument=PolicyDocument(
                Statement=[
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
                            troposphere.Ref(codecommit_repo_arn_param),
                        ]
                    ),
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
                        Sid='CodeBuildAccess',
                        Effect=Allow,
                        Action=[
                            Action('codebuild', 'BatchGetBuilds'),
                            Action('codebuild', 'StartBuild')
                        ],
                        Resource=[ troposphere.GetAtt(self.codebuild_project_res, 'Arn') ]
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
                    Statement(
                        Sid='CodeDeployAssumeRole',
                        Effect=Allow,
                        Action=[
                            Action('sts', 'AssumeRole'),
                        ],
                        Resource=[ troposphere.Ref(codedeploy_tools_delegate_role_arn_param) ]
                    ),
                    Statement(
                        Sid='CodeCommitAssumeRole',
                        Effect=Allow,
                        Action=[
                            Action('sts', 'AssumeRole'),
                        ],
                        Resource=[ troposphere.Ref(codecommit_role_arn_param) ]
                    ),
                ],
            ),
            Roles=[troposphere.Ref(pipeline_service_role_res)]
        )

        # CodePipeline
        # Source Action
        source_stage_actions = []
        # CodeCommit Source Action
        codecommit_source_action = troposphere.codepipeline.Actions(
            Name='CodeCommit',
            ActionTypeId = troposphere.codepipeline.ActionTypeId(
                Category = 'Source',
                Owner = 'AWS',
                Version = '1',
                Provider = 'CodeCommit'
            ),
            Configuration = {
                'RepositoryName': troposphere.Ref(self.codecommit_repo_name_param),
                'BranchName': troposphere.Ref(deploy_branch_name_param)
            },
            OutputArtifacts = [
                troposphere.codepipeline.OutputArtifacts(
                    Name = 'CodeCommitArtifact'
                )
            ],
            RunOrder = 1,
            RoleArn = troposphere.Ref(codecommit_role_arn_param)
        )
        source_stage_actions.append(codecommit_source_action)
        source_stage = troposphere.codepipeline.Stages(
            Name="Source",
            Actions = source_stage_actions
        )
        # Build Action
        build_stage_actions = []
        # CodeBuild Build Action
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
            InputArtifacts = [
                troposphere.codepipeline.InputArtifacts(
                    Name = 'CodeCommitArtifact'
                )
            ],
            OutputArtifacts = [
                troposphere.codepipeline.OutputArtifacts(
                    Name = 'CodeBuildArtifact'
                )
            ],
            RunOrder = 1
        )
        build_stage_actions.append(codebuild_build_action)
        build_stage = troposphere.codepipeline.Stages(
            Name="Build",
            Actions = build_stage_actions
        )
        # Deploy Action
        deploy_stage_actions = []
        # Manual Approval Deploy Action
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
            RunOrder = 1
        )
        if_manual_deploy_action = troposphere.If(
            'ManualApprovalIsEnabled',
            manual_deploy_action,
            troposphere.Ref('AWS::NoValue')
        )
        deploy_stage_actions.append(if_manual_deploy_action)

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
        deploy_stage_actions.append(codedeploy_deploy_action)
        deploy_stage = troposphere.codepipeline.Stages(
            Name="Deploy",
            Actions = deploy_stage_actions
        )

        pipeline_stages = [
            source_stage,
            build_stage,
            deploy_stage
        ]

        pipeline_res = troposphere.codepipeline.Pipeline(
            title = 'BuildCodePipeline',
            template = template,
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

    def get_codebuild_role_arn(self):
        return "arn:aws:iam::{0}:role/".format(self.account_ctx.get_id()) + self.res_name_prefix + "-CodeBuild"

    def get_codepipeline_role_arn(self):
        return "arn:aws:iam::{0}:role/".format(self.account_ctx.get_id()) + self.res_name_prefix + "-CodePipeline-Service"

