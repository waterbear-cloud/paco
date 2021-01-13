from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action, Condition, StringEquals, StringLike
from awacs.sts import AssumeRole
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import get_model_obj_from_ref, Reference
from paco.utils import md5sum
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns


class CodeBuild(StackTemplate):
    def __init__(self, stack, paco_ctx, base_aws_name, app_name, action_config, artifacts_bucket_name):
        pipeline_config = stack.resource
        config_ref = action_config.paco_ref_parts
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('CodeBuild', self.resource_group_name, self.resource.name)

        # Troposphere Template Initialization
        self.init_template('Deployment: CodeBuild')
        template = self.template
        if not action_config.is_enabled():
            return

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
            value=pipeline_config.paco_ref + '.kms.arn',
        )
        self.artifacts_bucket_name_param = self.create_cfn_parameter(
            param_type='String',
            name='ArtifactsBucketName',
            description='The name of the S3 Bucket to create that will hold deployment artifacts',
            value=artifacts_bucket_name,
        )
        self.codebuild_project_res = self.create_codebuild_cfn(
            template,
            pipeline_config,
            action_config,
            config_ref
        )

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
        )
        image_param = self.create_cfn_parameter(
            param_type='String',
            name='CodeBuildImage',
            description='The image tag or image digest that identifies the Docker image to use for this build project.',
            value=action_config.codebuild_image,
        )
        deploy_env_name_param = self.create_cfn_parameter(
            param_type='String',
            name='DeploymentEnvironmentName',
            description='The name of the environment codebuild will be deploying into.',
            value=action_config.deployment_environment,
        )
        # If ECS Release Phase, then create the needed parameters
        release_phase = action_config.release_phase
        ecs_release_phase_cluster_arn_param = []
        ecs_release_phase_cluster_name_param = []
        ecs_release_phase_service_arn_param = []
        if release_phase != None and release_phase.ecs != None:
            idx = 0
            for command in release_phase.ecs:
                service_obj = get_model_obj_from_ref(command.service, self.paco_ctx.project)
                service_obj = get_parent_by_interface(service_obj, schemas.IECSServices)
                cluster_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'ReleasePhaseECSClusterArn{idx}',
                    description='ECS Cluster Arn',
                    value=service_obj.cluster+'.arn',
                )
                ecs_release_phase_cluster_arn_param.append(cluster_arn_param)
                cluster_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'ReleasePhaseECSClusterName{idx}',
                    description='ECS Cluster Name',
                    value=service_obj.cluster+'.name',
                )
                ecs_release_phase_cluster_name_param.append(cluster_arn_param)
                service_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'ReleasePhaseECSServiceArn{idx}',
                    description='ECS Service Arn',
                    value=command.service+'.arn',
                )
                ecs_release_phase_service_arn_param.append(service_arn_param)
                idx += 1
        self.project_role_name = self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodeBuild-Project'],
            filter_id='IAM.Role.RoleName'
        )
        # codecommit_repo_users ManagedPolicies
        managed_policy_arns = []
        for user_ref in action_config.codecommit_repo_users:
            user = get_model_obj_from_ref(user_ref, self.paco_ctx.project)
            # codecommit_stack = user.__parent__.__parent__.__parent__.stack
            user_logical_id = self.gen_cf_logical_name(user.username)
            codecommit_user_policy_param = self.create_cfn_parameter(
                param_type='String',
                name='CodeCommitUserPolicy' + user_logical_id,
                description='The CodeCommit User Policy for ' + user.username,
                value=user_ref + '.policy.arn',
            )
            managed_policy_arns.append(troposphere.Ref(codecommit_user_policy_param))

        project_role_res = troposphere.iam.Role(
            title='CodeBuildProjectRole',
            template=template,
            RoleName=self.project_role_name,
            ManagedPolicyArns=managed_policy_arns,
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

        # Project Policy
        policy_statements = [
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
                    Action('s3', 'HeadObject'),
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
        ]

        release_phase = action_config.release_phase
        if release_phase != None and release_phase.ecs != None:
            ssm_doc = self.paco_ctx.project['resource']['ssm'].ssm_documents['paco_ecs_docker_exec']
            # SSM Exec Document
            policy_statements.append(
                Statement(
                    Sid='ECSReleasePhaseSSMCore',
                    Effect=Allow,
                    Action=[
                        Action('ssm', 'ListDocuments'),
                        Action('ssm', 'ListDocumentVersions'),
                        Action('ssm', 'DescribeDocument'),
                        Action('ssm', 'GetDocument'),
                        Action('ssm', 'DescribeInstanceInformation'),
                        Action('ssm', 'DescribeDocumentParameters'),
                        Action('ssm', 'CancelCommand'),
                        Action('ssm', 'ListCommands'),
                        Action('ssm', 'ListCommandInvocations'),
                        Action('ssm', 'DescribeAutomationExecutions'),
                        Action('ssm', 'DescribeInstanceProperties'),
                        Action('ssm', 'GetCommandInvocation'),
                        Action('ec2', 'DescribeInstanceStatus'),
                    ],
                    Resource=[ '*' ]
                )
            )
            policy_statements.append(
                Statement(
                    Sid=f'ECSReleasePhaseSSMSendCommandDocument',
                    Effect=Allow,
                    Action=[
                        Action('ssm', 'SendCommand'),
                    ],
                    Resource=[ f'arn:aws:ssm:{self.aws_region}:{self.account_ctx.get_id()}:document/paco_ecs_docker_exec' ]
                )
            )
            idx = 0
            for command in release_phase.ecs:
                policy_statements.append(
                    Statement(
                        Sid=f'ECSReleasePhaseSSMSendCommand{idx}',
                        Effect=Allow,
                        Action=[
                            Action('ssm', 'SendCommand'),
                        ],
                        Resource=[ f'arn:aws:ec2:*:*:instance/*' ],
                        Condition=Condition(
                            StringLike({
                                'ssm:resourceTag/Paco-ECSCluster-Name': troposphere.Ref(ecs_release_phase_cluster_name_param[idx])
                            })
                        )
                    )
                )

                policy_statements.append(
                    Statement(
                        Sid=f'ECSRelasePhaseClusterAccess{idx}',
                        Effect=Allow,
                        Action=[
                            Action('ecs', 'DescribeServices'),
                            Action('ecs', 'RunTask'),
                            Action('ecs', 'StopTask'),
                            Action('ecs', 'DescribeContainerInstances'),
                            Action('ecs', 'ListTasks'),
                            Action('ecs', 'DescribeTasks'),
                        ],
                        Resource=[ '*' ],
                        Condition=Condition(
                            StringEquals({
                                'ecs:cluster': troposphere.Ref(ecs_release_phase_cluster_arn_param[idx])
                            })
                        )
                    )
                )
                idx += 1

            policy_statements.append(
                Statement(
                    Sid='ECSReleasePhaseSSMAutomationExecution',
                    Effect=Allow,
                    Action=[
                        Action('ssm', 'StartAutomationExecution'),
                        Action('ssm', 'StopAutomationExecution'),
                        Action('ssm', 'GetAutomationExecution'),
                    ],
                    Resource=[ 'arn:aws:ssm:::automation-definition/' ]
                )
            )
            # ECS Policies
            policy_statements.append(
                Statement(
                    Sid='ECSRelasePhaseECS',
                    Effect=Allow,
                    Action=[
                        Action('ecs', 'DescribeTaskDefinition'),
                        Action('ecs', 'DeregisterTaskDefinition'),
                        Action('ecs', 'RegisterTaskDefinition'),
                        Action('ecs', 'ListTagsForResource'),
                        Action('ecr', 'DescribeImages')
                    ],
                    Resource=[ '*' ]
                )
            )

            # IAM Pass Role
            policy_statements.append(
                Statement(
                    Sid='IAMPassRole',
                    Effect=Allow,
                    Action=[
                        Action('iam', 'passrole')
                    ],
                    Resource=[ '*' ]
                )
            )


        if len(action_config.secrets) > 0:
            secrets_arn_list = []
            for secret_ref in action_config.secrets:
                name_hash = md5sum(str_data=secret_ref)
                secret_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='SecretsArn' + name_hash,
                    description='Secrets Manager Secret Arn to expose access to',
                    value=secret_ref+'.arn'
                )
                secrets_arn_list.append(troposphere.Ref(secret_arn_param))
            policy_statements.append(
                Statement(
                    Sid='SecretsManager',
                    Effect=Allow,
                    Action=[
                        Action('secretsmanager', 'GetSecretValue'),
                    ],
                    Resource=secrets_arn_list
                )
            )


        project_policy_res = troposphere.iam.PolicyType(
            title='CodeBuildProjectPolicy',
            PolicyName=project_policy_name,
            PolicyDocument=PolicyDocument(
                Statement=policy_statements
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

        # ECR Permission Policies
        index = 0
        pull_actions = [
            Action('ecr', 'GetDownloadUrlForLayer'),
            Action('ecr', 'BatchGetImage'),
        ]
        push_actions = [
            Action('ecr', 'GetDownloadUrlForLayer'),
            Action('ecr', 'BatchCheckLayerAvailability'),
            Action('ecr', 'PutImage'),
            Action('ecr', 'InitiateLayerUpload'),
            Action('ecr', 'UploadLayerPart'),
            Action('ecr', 'CompleteLayerUpload'),
        ]
        push_pull_actions = pull_actions + push_actions
        ecr_params = {}
        for ecr_permission in action_config.ecr_repositories:
            ecr_repo = get_model_obj_from_ref(ecr_permission.repository, self.paco_ctx.project)
            if ecr_repo.paco_ref not in ecr_params:
                param_name = ecr_repo.create_cfn_logical_id()
                ecr_repo_name_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'{param_name}ARN',
                    description='The ARN of the ECR repository',
                    value=ecr_repo.paco_ref + '.arn',
                )
                ecr_params[ecr_repo.paco_ref] = ecr_repo_name_param
        for ecr_permission in action_config.ecr_repositories:
            perm_name = f'PacoEcr{index}'
            policy_name = self.create_resource_name_join(
                name_list=[self.res_name_prefix, 'CodeBuild-Project', perm_name],
                separator='-',
                filter_id='IAM.Policy.PolicyName',
                hash_long_names=True,
                camel_case=True
            )
            statement_list = [
                Statement(
                    Effect='Allow',
                    Action=[
                        Action('ecr', 'GetAuthorizationToken'),
                    ],
                    Resource=['*'],
                ),
            ]
            ecr_repo = get_model_obj_from_ref(ecr_permission.repository, self.paco_ctx.project)
            if ecr_permission.permission == 'Pull':
                statement_list.append(
                    Statement(
                        Effect='Allow',
                        Action=pull_actions,
                        Resource=[
                            troposphere.Ref(ecr_params[ecr_repo.paco_ref])
                        ],
                    )
                )
            elif ecr_permission.permission == 'Push':
                statement_list.append(
                    Statement(
                        Effect='Allow',
                        Action=push_actions,
                        Resource=[
                            troposphere.Ref(ecr_params[ecr_repo.paco_ref])
                        ],
                    )
                )
            elif ecr_permission.permission == 'PushAndPull':
                statement_list.append(
                    Statement(
                        Effect='Allow',
                        Action=push_pull_actions,
                        Resource=[
                            troposphere.Ref(ecr_params[ecr_repo.paco_ref])
                        ],
                    )
                )

            troposphere.iam.PolicyType(
                title=self.create_cfn_logical_id('CodeBuildProjectPolicy' + perm_name, camel_case=True),
                template=template,
                PolicyName=policy_name,
                PolicyDocument=PolicyDocument(
                    Statement=statement_list,
                ),
                Roles=[troposphere.Ref(project_role_res)]
            )
            index += 1

        # CodeBuild Project Resource
        timeout_mins_param = self.create_cfn_parameter(
            param_type='String',
            name='TimeoutInMinutes',
            description='How long, in minutes, from 5 to 480 (8 hours), for AWS CodeBuild to wait before timing out any related build that did not get marked as completed.',
            value=action_config.timeout_mins,
        )

        # Environment Variables
        codebuild_env_vars = [
            {
                'Name': 'ArtifactsBucket',
                'Value': troposphere.Ref(self.artifacts_bucket_name_param),
            }, {
                'Name': 'DeploymentEnvironmentName',
                'Value': troposphere.Ref(deploy_env_name_param)
            }, {
                'Name': 'KMSKey',
                'Value': troposphere.Ref(self.cmk_arn_param)
            }]
        # If ECS Release Phase, then add the config to the environment
        release_phase = action_config.release_phase
        if release_phase != None and release_phase.ecs != None:
            idx = 0
            for command in release_phase.ecs:
                codebuild_env_vars.append({
                    'Name': f'PACO_CB_RP_ECS_CLUSTER_ID_{idx}',
                    'Value': troposphere.Ref(ecs_release_phase_cluster_arn_param[idx])
                })
                codebuild_env_vars.append({
                    'Name': f'PACO_CB_RP_ECS_SERVICE_ID_{idx}',
                    'Value': troposphere.Ref(ecs_release_phase_service_arn_param[idx])
                })
                idx += 1

        # CodeBuild: Environment
        environment = troposphere.codebuild.Environment(
            Type = 'LINUX_CONTAINER',
            ComputeType = troposphere.Ref(compute_type_param),
            Image = troposphere.Ref(image_param),
            EnvironmentVariables = codebuild_env_vars,
            PrivilegedMode = action_config.privileged_mode
        )
        source = troposphere.codebuild.Source(
            Type='CODEPIPELINE',
        )
        if action_config.buildspec != None and action_config.buildspec != '':
            source = troposphere.codebuild.Source(
                Type='CODEPIPELINE',
                BuildSpec=action_config.buildspec,
            )

        project_res = troposphere.codebuild.Project(
            title='CodeBuildProject',
            template=template,
            Name=troposphere.Ref(self.resource_name_prefix_param),
            Description=troposphere.Ref('AWS::StackName'),
            ServiceRole=troposphere.GetAtt('CodeBuildProjectRole', 'Arn'),
            EncryptionKey=troposphere.Ref(self.cmk_arn_param),
            Artifacts=troposphere.codebuild.Artifacts(
                Type='CODEPIPELINE'
            ),
            Environment=environment,
            Source=source,
            TimeoutInMinutes=troposphere.Ref(timeout_mins_param),
            Tags=troposphere.codebuild.Tags(
                Name=troposphere.Ref(self.resource_name_prefix_param)
            )
        )

        self.create_output(
            title='ProjectArn',
            value=troposphere.GetAtt(project_res, 'Arn'),
            description='CodeBuild Project Arn',
            ref=config_ref+'.project.arn'
        )

        return project_res

    def get_project_role_arn(self):
        return "arn:aws:iam::{}:role/{}".format(
            self.account_ctx.get_id(),
            self.project_role_name
        )

    def get_project_arn(self):
        return "arn:aws:codebuild:{}:{}:project/".format(self.aws_region, self.account_ctx.get_id()) + self.res_name_prefix