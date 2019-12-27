import os
from paco.cftemplates.cftemplates import CFTemplate
from paco import utils
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns
from io import StringIO
from enum import Enum
from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole


class CodePipeline(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        res_id,
        res_config,
        artifacts_bucket_name,
        cpbd_config_ref
    ):
        self.env_ctx = env_ctx
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=res_config.is_enabled(),
            config_ref=cpbd_config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('CodePipeline', grp_id, res_id)

        # Troposphere Template Initialization
        self.init_template('Deployment: CodePipeline')
        template = self.template

        if not res_config.is_enabled():
            return

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
            value=res_config.paco_ref + '.kms.arn',
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
        self.manual_approval_is_enabled = False
        self.create_codepipeline_cfn(
            template,
            res_config,
        )
        self.set_template(template.to_yaml())

    def create_codepipeline_cfn(
        self,
        template,
        res_config,
    ):
        # CodePipeline
        # Source Actions
        source_stage_actions = []
        # Source Actions
        for action_name in res_config.source.keys():
            action_config = res_config.source[action_name]
            # Manual Approval Action
            if action_config.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(template, action_config)
                source_stage_actions.append(manual_approval_action)
            # CodeCommit Action
            if action_config.type == 'CodeCommit.Source':
                codecommit_repo_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRepositoryArn',
                    description='The Arn of the CodeCommit repository',
                    value='{}.codecommit.arn'.format(action_config.paco_ref),
                    use_troposphere=True,
                    troposphere_template=template
                )
                codecommit_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRoleArn',
                    description='The Arn of the CodeCommit Role',
                    value='{}.codecommit_role.arn'.format(action_config.paco_ref),
                    use_troposphere=True,
                    troposphere_template=template
                )
                codecommit_repo_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitRepositoryName',
                    description='The name of the CodeCommit repository',
                    value=action_config.codecommit_repository+'.name',
                    use_troposphere=True,
                    troposphere_template=template,
                )
                deploy_branch_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeCommitDeploymentBranchName',
                    description='The name of the branch where commits will trigger a build.',
                    value=action_config.deployment_branch_name,
                    use_troposphere=True,
                    troposphere_template=template,
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
                    RunOrder = action_config.run_order,
                    RoleArn = troposphere.Ref(codecommit_role_arn_param)
                )
                source_stage_actions.append(codecommit_source_action)

        source_stage = troposphere.codepipeline.Stages(
            Name="Source",
            Actions = source_stage_actions
        )
        # Build Actions
        build_stage_actions = []
        for action_name in res_config.build.keys():
            action_config = res_config.build[action_name]
            # Manual Approval Action
            if action_config.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(template, action_config)
                build_stage_actions.append(manual_approval_action)
            # CodeBuild Build Action
            elif action_config.type == 'CodeBuild.Build':
                codebuild_project_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeBuildProjectArn',
                    description='The arn of the CodeBuild project',
                    value='{}.project.arn'.format(action_config.paco_ref),
                    use_troposphere=True,
                    troposphere_template=template,
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
                    RunOrder = action_config.run_order
                )
                build_stage_actions.append(codebuild_build_action)
        build_stage = troposphere.codepipeline.Stages(
            Name="Build",
            Actions = build_stage_actions
        )
        # Deploy Action
        [ deploy_stage,
          s3_deploy_assume_role_statement,
          codedeploy_deploy_assume_role_statement ] = self.init_deploy_stage(res_config, template)

        # Manual Deploy Enabled/Disable
        manual_approval_enabled_param = self.create_cfn_parameter(
            param_type='String',
            name='ManualApprovalEnabled',
            description='Boolean indicating whether a manual approval is enabled or not.',
            value=self.manual_approval_is_enabled,
            use_troposphere=True,
            troposphere_template=template,
        )
        template.add_condition(
            'ManualApprovalIsEnabled',
            troposphere.Equals(troposphere.Ref(manual_approval_enabled_param), 'true')
        )

        # CodePipeline Role and Policy
        self.pipeline_service_role_name = self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodePipeline-Service'],
            filter_id='IAM.Role.RoleName'
        )
        pipeline_service_role_res = troposphere.iam.Role(
            title='CodePipelineServiceRole',
            template = template,
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
                Resource=[ troposphere.Ref(codebuild_project_arn_param) ]
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
                Sid='CodeCommitAssumeRole',
                Effect=Allow,
                Action=[
                    Action('sts', 'AssumeRole'),
                ],
                Resource=[ troposphere.Ref(codecommit_role_arn_param) ]
            ),
        ]

        if codedeploy_deploy_assume_role_statement != None:
            pipeline_policy_statement_list.append(codedeploy_deploy_assume_role_statement)
        if s3_deploy_assume_role_statement != None:
            pipeline_policy_statement_list.append(s3_deploy_assume_role_statement)
        troposphere.iam.PolicyType(
            title='CodePipelinePolicy',
            template = template,
            DependsOn = 'CodePipelineServiceRole',
            PolicyName=troposphere.Sub('${ResourceNamePrefix}-CodePipeline-Policy'),
            PolicyDocument=PolicyDocument(
                Statement=pipeline_policy_statement_list,
            ),
            Roles=[troposphere.Ref(pipeline_service_role_res)]
        )

        pipeline_stages = []
        if source_stage != None: pipeline_stages.append(source_stage)
        if build_stage != None: pipeline_stages.append(build_stage)
        if deploy_stage != None: pipeline_stages.append(deploy_stage)

        pipeline_res = troposphere.codepipeline.Pipeline(
            title = 'BuildCodePipeline',
            template = template,
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

    def init_manual_approval_action(self, template, action_config):
        self.manual_approval_is_enabled = action_config.is_enabled()
        # Manual Approval Deploy Action
        subscription_list = []
        for approval_email in action_config.manual_approval_notification_email:
            email_hash = utils.md5sum(str_data=approval_email)
            manual_approval_notification_email_param = self.create_cfn_parameter(
                param_type='String',
                name='ManualApprovalNotificationEmail'+email_hash,
                description='Email to send notifications to when a deployment requires approval.',
                value=approval_email,
                use_troposphere=True,
                troposphere_template=template,
            )
            subscription_list.append(
                troposphere.sns.Subscription(
                    Endpoint=troposphere.Ref(manual_approval_notification_email_param),
                    Protocol = 'email'
                )
            )

        manual_approval_sns_res = troposphere.sns.Topic(
            title = 'ManualApprovalSNSTopic',
            template=template,
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
            RunOrder = action_config.run_order
        )
        manual_deploy_action = troposphere.If(
            'ManualApprovalIsEnabled',
            manual_deploy_action,
            troposphere.Ref('AWS::NoValue')
        )

        return manual_deploy_action

    def init_deploy_stage(self, res_config, template):
        if res_config.deploy == None:
            return [None, None, None]
        deploy_stage_actions = []
        for action_name in res_config.deploy.keys():
            action_config = res_config.deploy[action_name]
            if action_config.type == 'ManualApproval':
                manual_approval_action = self.init_manual_approval_action(template, action_config)
                deploy_stage_actions.append(manual_approval_action)

            # S3.Deploy
            s3_deploy_assume_role_statement = None
            if action_config.type == 'S3.Deploy':
                s3_deploy_bucket_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployBucketName',
                    description='The name of the S3 bucket to deploy to.',
                    value=action_config.bucket+'.name',
                    use_troposphere=True,
                    troposphere_template=template
                )
                s3_deploy_extract_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployExtract',
                    description='Boolean indicating whether the deployment artifact will be extracted.',
                    value=action_config.extract,
                    use_troposphere=True,
                    troposphere_template=template
                )
                s3_deploy_object_key_param = 'AWS::NoValue'
                if action_config.object_key != None:
                    s3_deploy_object_key_param = self.create_cfn_parameter(
                        param_type='String',
                        name='S3DeployObjectKey',
                        description='S3 object key to store the deployment artifact as.',
                        value=action_config.object_key,
                        use_troposphere=True,
                        troposphere_template=template
                    )
                s3_deploy_delegate_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='S3DeployDelegateRoleArn',
                    description='The Arn of the IAM Role CodePipeline will assume to gain access to the deployment bucket.',
                    value=action_config._delegate_role_arn,
                    use_troposphere=True,
                    troposphere_template=template
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

            codedeploy_deploy_assume_role_statement = None
            if action_config.type == 'CodeDeploy.Deploy':
                codedeploy_tools_delegate_role_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployToolsDelegateRoleArn',
                    description='The Arn of the CodeDeploy Delegate Role',
                    value=action_config.paco_ref + '.codedeploy_tools_delegate_role.arn',
                    use_troposphere=True,
                    troposphere_template=template
                )
                codedeploy_application_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployApplicationName',
                    description='The CodeDeploy Application name to deploy to.',
                    value=action_config.paco_ref+'.codedeploy_application_name',
                    use_troposphere=True,
                    troposphere_template=template
                )
                codedeploy_group_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name='CodeDeployGroupName',
                    description='The name of the CodeDeploy deployment group.',
                    value=action_config.paco_ref + '.deployment_group.name',
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

