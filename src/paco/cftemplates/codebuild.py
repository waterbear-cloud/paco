import os
from paco.cftemplates.cftemplates import CFTemplate
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns
from io import StringIO
from enum import Enum
from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole

class CodeBuild(CFTemplate):
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
        pipeline_config,
        action_config,
        artifacts_bucket_name,
        config_ref
    ):
        self.env_ctx = env_ctx
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=action_config.is_enabled(),
            config_ref=config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('CodeBuild', grp_id, res_id)

        # Troposphere Template Initialization
        self.init_template('Deployment: CodeBuild')
        template = self.template
        if not action_config.is_enabled():
            return

        self.res_name_prefix = self.create_resource_name_join(
            name_list=[env_ctx.get_aws_name(), app_id, grp_id, res_id],
            separator='-',
            camel_case=True
        )
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
            value=pipeline_config.paco_ref + '.kms.arn',
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
        self.codebuild_project_res = self.create_codebuild_cfn(
            template,
            pipeline_config,
            action_config,
            config_ref
        )
        self.set_template(template.to_yaml())

    def create_codebuild_cfn(
        self,
        template,
        pipeline_config,
        action_config,
        config_ref
    ):
        # CodeBuild
        compute_type_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeBuildComputeType',
            description='The type of compute environment. This determines the number of CPU cores and memory the build environment uses.',
            value=action_config.codebuild_compute_type,
            use_troposphere=True,
            troposphere_template=template,
        )
        image_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeBuildImage',
            description='The image tag or image digest that identifies the Docker image to use for this build project.',
            value=action_config.codebuild_image,
            use_troposphere=True,
            troposphere_template=template,
        )
        deploy_env_name_param = self.create_cfn_parameter(
            param_type='String',
            name='DeploymentEnvironmentName',
            description='The name of the environment codebuild will be deploying into.',
            value=action_config.deployment_environment,
            use_troposphere=True,
            troposphere_template=template,
        )
        self.project_role_name = self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodeBuild-Project'],
            filter_id='IAM.Role.RoleName'
        )
        project_role_res = troposphere.iam.Role(
            title='CodeBuildProjectRole',
            template=template,
            RoleName=self.project_role_name,
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

        project_policy_name = self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodeBuild-Project'],
            filter_id='IAM.Policy.PolicyName'
        )
        project_policy_res = troposphere.iam.PolicyType(
            title='CodeBuildProjectPolicy',
            PolicyName=project_policy_name,
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

        # User defined policies
        for policy in action_config.role_policies:
            policy_name = self.create_resource_name_join(
                name_list=[self.res_name_prefix, 'CodeBuild-Project', policy.name],
                separator='-',
                filter_id='IAM.Policy.PolicyName',
                hash_long_names=True,
                camel_case=True
            )
            statement_list = []

            for statement in policy.statement:
                action_list = []
                for action in statement.action:
                    action_parts = action.split(':')
                    action_list.append(Action(action_parts[0], action_parts[1]))
                statement_list.append(
                    Statement(
                        Effect=statement.effect,
                        Action=action_list,
                        Resource=statement.resource
                    )
                )
            troposphere.iam.PolicyType(
                title=self.create_cfn_logical_id('CodeBuildProjectPolicy'+policy.name, camel_case=True),
                template=template,
                PolicyName=policy_name,
                PolicyDocument=PolicyDocument(
                    Statement=statement_list,
                ),
                Roles=[troposphere.Ref(project_role_res)]
            )

        # CodeBuild Project Resource
        timeout_mins_param = self.create_cfn_parameter(
            param_type='String',
            name='TimeoutInMinutes',
            description='How long, in minutes, from 5 to 480 (8 hours), for AWS CodeBuild to wait before timing out any related build that did not get marked as completed.',
            value=action_config.timeout_mins,
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
            Description = troposphere.Ref('AWS::StackName'),
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

        troposphere.Output(
            title='ProjectArn',
            template=template,
            Value=troposphere.GetAtt(project_res, 'Arn'),
            Description='CodeBuild Project Arn'
        )

        self.register_stack_output_config(config_ref+'.project.arn', 'ProjectArn')

        return project_res

    def get_project_role_arn(self):
        return "arn:aws:iam::{}:role/{}".format(
            self.account_ctx.get_id(),
            self.project_role_name
        )

    def get_project_arn(self):
        return "arn:aws:codebuild:{}:{}:project/".format(self.aws_region, self.account_ctx.get_id()) + self.res_name_prefix