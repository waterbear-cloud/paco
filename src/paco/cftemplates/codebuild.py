from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action, Condition, StringEquals, StringLike, ArnEquals
from awacs.sts import AssumeRole
from paco.cftemplates.cftemplates import StackTemplate
from paco.core.exception import PacoException
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import get_model_obj_from_ref, Reference
from paco.utils import md5sum
import troposphere
import troposphere.codepipeline
import troposphere.codebuild
import troposphere.sns


class CodeBuild(StackTemplate):
    def __init__(self, stack, paco_ctx, env_ctx, base_aws_name, app_name, action_config, artifacts_bucket_name):
        pipeline_config = stack.resource
        config_ref = action_config.paco_ref_parts
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('CodeBuild', self.resource_group_name, self.resource.name)
        self.env_ctx = env_ctx
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
        self.enable_artifacts_bucket = True
        if pipeline_config.configuration.disable_codepipeline == False:
            self.cmk_arn_param = self.create_cfn_parameter(
                param_type='String',
                name='CMKArn',
                description='The KMS CMK Arn of the key used to encrypt deployment artifacts.',
                value=pipeline_config.paco_ref + '.kms.arn',
            )
        elif action_config.artifacts == None or action_config.artifacts.type == 'NO_ARTIFACTS':
            self.enable_artifacts_bucket = False

        if self.enable_artifacts_bucket:
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
        policy_statements = []
        if self.enable_artifacts_bucket:
            policy_statements.append(
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
                )
            )
        if pipeline_config.configuration.disable_codepipeline == False:
            policy_statements.append(
                Statement(
                    Sid='KMSCMK',
                    Effect=Allow,
                    Action=[
                        Action('kms', '*')
                    ],
                    Resource=[ troposphere.Ref(self.cmk_arn_param) ]
                )
            )
        policy_statements.append(
            Statement(
                Sid='CloudWatchLogsAccess',
                Effect=Allow,
                Action=[
                    Action('logs', 'CreateLogGroup'),
                    Action('logs', 'CreateLogStream'),
                    Action('logs', 'PutLogEvents'),
                ],
                Resource=[ 'arn:aws:logs:*:*:*' ]
            )
        )

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
        project_policy_res.DependsOn = project_role_res
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
        self.set_ecr_repositories_statements(
            action_config.ecr_repositories,
            template,
            f'{self.res_name_prefix}-CodeBuild-Project',
            [troposphere.Ref(project_role_res)]
        )

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
                'Name': 'DeploymentEnvironmentName',
                'Value': troposphere.Ref(deploy_env_name_param)
            }
        ]
        if pipeline_config.configuration.disable_codepipeline == False:
            codebuild_env_vars.append(
                {
                    'Name': 'KMSKey',
                    'Value': troposphere.Ref(self.cmk_arn_param)
                }
            )
        if self.enable_artifacts_bucket:
            codebuild_env_vars.append(
                {
                    'Name': 'ArtifactsBucket',
                    'Value': troposphere.Ref(self.artifacts_bucket_name_param),
                }
            )
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
        project_dict = {
            'Name': troposphere.Ref(self.resource_name_prefix_param),
            'Artifacts': {
                'Type': 'NO_ARTIFACTS'
            },
            'Description': troposphere.Ref('AWS::StackName'),
            'ServiceRole': troposphere.GetAtt('CodeBuildProjectRole', 'Arn'),
            'Environment': {
                'Type': 'LINUX_CONTAINER',
                'ComputeType': troposphere.Ref(compute_type_param),
                'Image': troposphere.Ref(image_param),
                'EnvironmentVariables': codebuild_env_vars,
                'PrivilegedMode': action_config.privileged_mode
            },
            'Source': {
                'Type': 'NO_SOURCE'
            },
            'TimeoutInMinutes': troposphere.Ref(timeout_mins_param),
            'Tags': troposphere.codebuild.Tags(
                Name=troposphere.Ref(self.resource_name_prefix_param)
            )
        }

        if action_config.buildspec:
            project_dict['Source']['BuildSpec'] = action_config.buildspec

        if pipeline_config.configuration.disable_codepipeline == False:
            project_dict['EncryptionKey'] = troposphere.Ref(self.cmk_arn_param)
            project_dict['Artifacts'] = {
                'Type': 'CODEPIPELINE'
            }
            project_dict['Source']['Type'] = 'CODEPIPELINE'
        else:
            if action_config.artifacts == None or action_config.artifacts.type == 'NO_ARTIFACTS':
                project_dict['Artifacts'] = {
                    'Type': 'NO_ARTIFACTS',
                }
            else:
                project_dict['Artifacts'] = {
                    'Type': action_config.artifacts.type,
                    'Location': troposphere.Ref(self.artifacts_bucket_name_param),
                    'NamespaceType': action_config.artifacts.namespace_type,
                    'Packaging': action_config.artifacts.packaging,
                    'Name': action_config.artifacts.name
                }
                if action_config.artifacts.path != None:
                    project_dict['Artifacts']['Path'] = action_config.artifacts.path
            if action_config.source.github != None:
                github_config = action_config.source.github
                project_dict['Source']['Type'] = 'GITHUB'
                location = f'https://github.com/{github_config.github_owner}/{github_config.github_repository}.git'
                project_dict['Source']['Location'] = location
                project_dict['Source']['ReportBuildStatus'] = github_config.report_build_status
                if github_config.deployment_branch_name != None:
                    project_dict['SourceVersion'] = github_config.deployment_branch_name
            else:
                raise PacoException("CodeBuild source must be configured when Codepipeline is disabled.")

        if action_config.concurrent_build_limit > 0:
            project_dict['ConcurrentBuildLimit'] = action_config.concurrent_build_limit

        if action_config.vpc_config != None:
            vpc_config = action_config.vpc_config
            vpc_id_param = self.create_cfn_parameter(
                name='VPC',
                param_type='AWS::EC2::VPC::Id',
                description='The VPC Id',
                value='paco.ref netenv.{}.<environment>.<region>.network.vpc.id'.format(self.env_ctx.netenv.name),
            )

            security_group_list = []
            for sg_ref in vpc_config.security_groups:
                ref = Reference(sg_ref)
                sg_param_name = self.gen_cf_logical_name('SecurityGroupId'+ref.parts[-2]+ref.parts[-1])
                sg_param = self.create_cfn_parameter(
                    name=sg_param_name,
                    param_type='String',
                    description='Security Group Id',
                    value=sg_ref + '.id',
                )
                security_group_list.append(troposphere.Ref(sg_param))

            # security_group_list_param = self.create_cfn_ref_list_param(
            #     param_type='List<AWS::EC2::SecurityGroup::Id>',
            #     name='SecurityGroupList',
            #     description='List of security group ids to attach to CodeBuild.',
            #     value=vpc_config.security_groups,
            #     ref_attribute='id',
            # )
            subnet_id_list = []
            subnet_arn_list = []
            az_size = self.env_ctx.netenv[self.account_ctx.name][self.aws_region].network.availability_zones
            for segment_ref in vpc_config.segments:
                for az_idx in range(1, az_size+1):
                    # Subnet Ids
                    segment_name = self.create_cfn_logical_id(f"Segment{segment_ref.split('.')[-1]}AZ{az_idx}")
                    subnet_id_param = self.create_cfn_parameter(
                        name=segment_name,
                        param_type='AWS::EC2::Subnet::Id',
                        description=f'VPC Subnet Id in AZ{az_idx} for CodeBuild VPC Config',
                        value=segment_ref + f'.az{az_idx}.subnet_id'
                    )
                    subnet_id_list.append(troposphere.Ref(subnet_id_param))
                    # Subnet Arns
                    subnet_arn_param = self.create_cfn_parameter(
                        name=segment_name+'Arn',
                        param_type='String',
                        description=f'VPC Subnet Id ARN in AZ{az_idx} for CodeBuild VPC Config',
                        value=segment_ref + f'.az{az_idx}.subnet_id.arn'
                    )
                    subnet_arn_list.append(troposphere.Ref(subnet_arn_param))

            if len(subnet_id_list) == 0:
                raise PacoException("CodeBuild VPC Config must have at least one segment defined.")


            # VPC Config Permissions
            policy_statements.append(
                Statement(
                    Sid='VpcConfigPermissions',
                    Effect=Allow,
                    Action=[
                        Action('ec2', 'CreateNetworkInterface'),
                        Action('ec2', 'DescribeDhcpOptions'),
                        Action('ec2', 'DescribeNetworkInterfaces'),
                        Action('ec2', 'DeleteNetworkInterface'),
                        Action('ec2', 'DescribeSubnets'),
                        Action('ec2', 'DescribeSecurityGroups'),
                        Action('ec2', 'DescribeVpcs'),
                    ],
                    Resource=[ '*' ]
                )
            )
            policy_statements.append(
                Statement(
                    Sid='VpcConfigNetworkInterface',
                    Effect=Allow,
                    Action=[
                        Action('ec2', 'CreateNetworkInterfacePermission'),
                    ],
                    Resource=[ f'arn:aws:ec2:{self.aws_region}:{self.account_ctx.id}:network-interface/*' ],
                    Condition=Condition(
                        [
                            StringEquals({
                                "ec2:AuthorizedService": "codebuild.amazonaws.com"
                            }),
                            ArnEquals({
                                "ec2:Subnet": subnet_arn_list
                            })
                        ]
                    )
                )
            )

            project_dict['VpcConfig'] = {
                'VpcId': troposphere.Ref(vpc_id_param),
                'SecurityGroupIds': security_group_list,
                'Subnets': subnet_id_list
            }

        # Batch Build Config
        batch_service_role_res = None
        if action_config.build_batch_config != None and action_config.build_batch_config.is_enabled():
            batch_config = action_config.build_batch_config

            batch_service_role_name = self.create_iam_resource_name(
                name_list=[self.res_name_prefix, 'CodeBuild-BuildBatch-ServiceRole'],
                filter_id='IAM.Role.RoleName'
            )
            batch_service_role_res = troposphere.iam.Role(
                title='CodeBuildBuildBatchConfigServiceRole',
                template=template,
                RoleName=batch_service_role_name,
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

            project_dict['BuildBatchConfig'] = {
                'BatchReportMode': batch_config.batch_report_mode,
                'CombineArtifacts': batch_config.combine_artifacts,
                'TimeoutInMins': batch_config.timeout_in_mins,
                'ServiceRole': troposphere.GetAtt(batch_service_role_res, 'Arn'),
                'Restrictions': {
                    'ComputeTypesAllowed': batch_config.restrictions.compute_types_allowed,
                    'MaximumBuildsAllowed': batch_config.restrictions.maximum_builds_allowed
                }
            }

        project_res = troposphere.codebuild.Project.from_dict(
            'CodeBuildProject',
            project_dict
        )
        project_res.DependsOn = project_policy_res
        if action_config.build_batch_config != None and action_config.build_batch_config.is_enabled():
            project_res.DependsOn = batch_service_role_res

        self.template.add_resource(project_res)

        if batch_service_role_res != None:
            build_batch_policy_statements = []
            build_batch_policy_statements.append(
                Statement(
                    Sid='BatchServiceRole',
                    Effect=Allow,
                    Action=[
                        Action('codebuild', 'StartBuild'),
                        Action('codebuild', 'StopBuild'),
                        Action('codebuild', 'RetryBuild')
                    ],
                    Resource=[ troposphere.GetAtt(project_res, 'Arn')]
                )
            )

            batch_policy_name = self.create_iam_resource_name(
                name_list=[self.res_name_prefix, 'CodeBuild-BatchPolicy'],
                filter_id='IAM.Policy.PolicyName'
            )
            batch_policy_res = troposphere.iam.PolicyType(
                title='CodeBuildBuildBatchPolicy',
                template=template,
                PolicyName=batch_policy_name,
                PolicyDocument=PolicyDocument(
                    Statement=build_batch_policy_statements
                ),
                Roles=[troposphere.Ref(batch_service_role_res)]
            )

            batch_policy_res.DependsOn = project_res

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

    def get_project_name(self):
        return self.res_name_prefix