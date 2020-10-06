from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.core.exception import InvalidAWSConfiguration
from paco.models.references import get_model_obj_from_ref
from paco.models import schemas
from paco import models
import os
import pathlib
import shutil


yaml=YAML()
yaml.default_flow_sytle = False

class DeploymentPipelineResourceEngine(ResourceEngine):

    def __init__(self, app_engine, grp_id, res_id, resource, stack_tags):
        super().__init__(app_engine, grp_id, res_id, resource, stack_tags)
        self.pipeline_account_ctx = None
        self.pipeline = resource
        self.kms_stack = None
        self.kms_crypto_principle_list = []
        self.artifacts_bucket_policy_resource_arns = []
        self.artifacts_bucket_meta = {
            'obj': None,
            'ref': None,
            'arn': None,
            'name': None,
        }
        self.codecommit_role_name = 'codecommit_role'
        self.github_role_name = 'github_role'
        self.source_stage = None

    def init_stage(self, stage_config):
        "Initialize an Action in a Stage: for source/build/deploy-style"
        if stage_config == None:
            return
        for action_name in stage_config.keys():
            action_config = stage_config[action_name]
            action_config.resolve_ref_obj = self
            method_name = 'init_stage_action_' + action_config.type.replace('.', '_').lower()
            method = getattr(self, method_name)
            method(action_config)

    def init_stage_action(self, stage, action):
        "Initialize an Action in a Stage: for flexible stage/action-style"
        # dynamically calls a method with the format:
        # init_action_<action_type>(action)
        action.resolve_ref_obj = self
        method_name = 'init_action_' + action.type.replace('.', '_').lower()
        method = getattr(self, method_name, None)
        if method != None:
            method(stage, action)

    def init_resource(self):
        self.pipeline.resolve_ref_obj = self
        self.pipeline.configuration.resolve_ref_obj = self
        self.pipeline_account_ctx = self.paco_ctx.get_account_context(self.pipeline.configuration.account)

        # S3 Artifacts Bucket:
        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_bucket = get_model_obj_from_ref(self.pipeline.configuration.artifacts_bucket, self.paco_ctx.project)
        self.artifacts_bucket_meta['obj'] = s3_bucket
        self.artifacts_bucket_meta['ref'] = self.pipeline.configuration.artifacts_bucket
        self.artifacts_bucket_meta['arn'] = s3_ctl.get_bucket_arn(self.artifacts_bucket_meta['ref'])
        self.artifacts_bucket_meta['name'] = s3_bucket.get_bucket_name()

        # Resource can be in a Service or an Environment
        if hasattr(self, 'env_ctx'):
            self.base_aws_name = self.env_ctx.get_aws_name()
            self.deploy_region = self.env_ctx.region
        else:
            # deploy region is the same as the Service region
            # ToDo: use-cases to have this be another region?
            self.deploy_region = self.aws_region
            self.base_aws_name = self.stack_group.get_aws_name()

        # KMS Key
        kms_refs = {}
        # Application Account
        kms_refs['paco.ref accounts.{}'.format(self.account_ctx.name)] = None

        # CodeCommit Account(s)
        # ToDo: allows ALL CodeCommit accounts access, filter out non-CI/CD CodeCommit repos?
        for codecommit_group in self.paco_ctx.project['resource']['codecommit'].values():
            for repo in codecommit_group.values():
                kms_refs[repo.account] = None

        for key in kms_refs.keys():
            self.kms_crypto_principle_list.append(
                "paco.sub 'arn:aws:iam::${%s}:root'" % (key)
            )

        # KMS stack
        kms_config_dict = {
            'admin_principal': {
                'aws': [ "!Sub 'arn:aws:iam::${{AWS::AccountId}}:root'" ]
            },
            'crypto_principal': {
                'aws': self.kms_crypto_principle_list
            }
        }
        self.kms_stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.KMS,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            support_resource_ref_ext='kms',
            extra_context={'kms_config_dict': kms_config_dict}
        )

        # Initialize Stages
        if self.pipeline.stages != None:
            # flexible stages
            self.s3deploy_bucket_refs = {}
            self.s3deploy_delegate_role_arns = {}
            # Initialize actions
            for stage in self.pipeline.stages.values():
                for action in stage.values():
                    self.init_stage_action(stage, action)
            # if there are S3.Deploy actions, provide a Role
            if len(self.s3deploy_bucket_refs.keys()) > 0:
                self.init_s3_deploy_roles()
        else:
            # source/build/deploy-only stages
            self.init_stage(self.pipeline.source)
            self.init_stage(self.pipeline.build)
            self.init_stage(self.pipeline.deploy)

        # CodePipeline
        self.pipeline._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodePipeline,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'deploy_region': self.deploy_region,
                'app_name': self.app.name,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name']
            },
        )

        # Add Hooks to the CodePipeline Stack
        if self.pipeline.source != None:
            for action in self.pipeline.source.values():
                if action.type == 'ECR.Source':
                    self.add_ecr_source_hooks(action)

        # Add CodeBuild Role ARN to KMS Key principal now that the role is created
        kms_config_dict['crypto_principal']['aws'] = self.kms_crypto_principle_list
        kms_stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.KMS,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            support_resource_ref_ext='kms',
            extra_context={'kms_config_dict': kms_config_dict}
        )
        kms_stack.set_dependency(self.kms_stack, 'post-pipeline')

        # Get the ASG Instance Role ARN
        if not self.pipeline.is_enabled():
            return
        self.artifacts_bucket_policy_resource_arns.append(
            "paco.sub '${%s}'" % (self.pipeline.paco_ref + '.codepipeline_role.arn')
        )
        cpbd_s3_bucket_policy = {
            'aws': self.artifacts_bucket_policy_resource_arns,
            'action': [ 's3:*' ],
            'effect': 'Allow',
            'resource_suffix': [ '/*', '' ]
        }
        # the S3 Bucket Policy can be added to by multiple DeploymentPipelines
        s3_ctl.add_bucket_policy(self.artifacts_bucket_meta['ref'], cpbd_s3_bucket_policy)

    def init_stage_action_github_source(self, action_config):
        "Initialize a GitHub.Source action"
        if not action_config.is_enabled():
            return

    def init_stage_action_codecommit_source(self, action_config):
        "Initialize an IAM Role for the CodeCommit action"
        if not action_config.is_enabled():
            return

        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[tools_account_id]:s}'
instance_profile: false
path: /
role_name: CodeCommit
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - codecommit:BatchGetRepositories
          - codecommit:Get*
          - codecommit:GitPull
          - codecommit:List*
          - codecommit:CancelUploadArchive
          - codecommit:UploadArchive
        resource:
          - {0[codecommit_ref]:s}
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
        codecommit_ref = action_config.codecommit_repository
        role_table = {
            'codecommit_account_id': "paco.sub '${{{0}.account_id}}'".format(codecommit_ref),
            'tools_account_id': self.pipeline_account_ctx.get_id(),
            'codecommit_ref': "paco.sub '${{{0}.arn}}'".format(codecommit_ref),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }
        role_config_dict = yaml.load(role_yaml.format(role_table))
        codecommit_iam_role_config = models.iam.Role(self.codecommit_role_name, action_config)
        codecommit_iam_role_config.apply_config(role_config_dict)
        codecommit_iam_role_config.enabled = action_config.is_enabled()

        iam_ctl = self.paco_ctx.get_controller('IAM')
        # The ID to give this role is: group.resource.instance_iam_role
        codecommit_iam_role_id = self.gen_iam_role_id(self.res_id, self.codecommit_role_name)
        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s.%s.arn}'" % (action_config.paco_ref, self.codecommit_role_name))
        # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        codecommit_account_ref = self.paco_ctx.get_ref(action_config.codecommit_repository + '.account')
        codecommit_account_ctx = self.paco_ctx.get_account_context(codecommit_account_ref)
        iam_ctl.add_role(
            account_ctx=codecommit_account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=codecommit_iam_role_config,
            iam_role_id=codecommit_iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params,
        )

    def init_action_s3_deploy(self, stage, action):
        "Initialize an IAM Role stack to allow access to the S3 Bucket for the action"
        bucket = get_model_obj_from_ref(action.bucket, self.paco_ctx.project)
        if bucket.account not in self.s3deploy_bucket_refs:
            self.s3deploy_bucket_refs[bucket.account] = {}
        self.s3deploy_bucket_refs[bucket.account][action.bucket] = None

    def init_s3_deploy_roles(self):
        "Create Role for every account with an S3.Deploy bucket to allow access to all S3 Bucket(s) for S3.Deploy Actions in that account"
        for account_ref in self.s3deploy_bucket_refs.keys():
            account = get_model_obj_from_ref(account_ref, self.paco_ctx.project)
            bucket_arns = []
            for ref in self.s3deploy_bucket_refs[account_ref].keys():
                bucket_arn = self.paco_ctx.get_ref(ref + '.arn')
                bucket_arns.append(bucket_arn)
                bucket_arns.append(bucket_arn + '/*')
            role_dict = {
                'assume_role_policy': {'effect': 'Allow', 'aws': [ self.pipeline_account_ctx.get_id() ]},
                'instance_profile': False,
                'path': '/',
                'role_name': 'S3Deploy',
                'enabled': True,
                'policies': [{
                    'name': 'DeploymentPipeline',
                    'statement': [
                        {'effect': 'Allow', 'action': ['s3:*'], 'resource': bucket_arns, },
                        { 'effect': 'Allow',
                          'action': ['s3:*'],
                          'resource': [self.artifacts_bucket_meta['arn'], self.artifacts_bucket_meta['arn'] + '/*']
                        },
                        { 'effect': 'Allow', 'action': 'kms:*', 'resource': ["!Ref CMKArn"] },
                    ]
                }],
            }
            role_name = 's3deploydelegate_{}'.format(account.name)
            role = models.iam.Role(role_name, self.pipeline)
            role.apply_config(role_dict)

            iam_ctl = self.paco_ctx.get_controller('IAM')
            role_id = self.gen_iam_role_id(self.res_id, role_name)
            self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (role.paco_ref + '.arn'))

            # IAM Roles Parameters
            iam_role_params = [{
                'key': 'CMKArn',
                'value': self.pipeline.paco_ref + '.kms.arn',
                'type': 'String',
                'description': 'DeploymentPipeline KMS Key Arn'
            }]
            iam_ctl.add_role(
                account_ctx=self.paco_ctx.get_account_context(account_ref),
                region=self.aws_region,
                resource=self.resource,
                role=role,
                iam_role_id=role_id,
                stack_group=self.stack_group,
                stack_tags=self.stack_tags,
                template_params=iam_role_params,
            )
            self.s3deploy_delegate_role_arns[account_ref] = iam_ctl.role_arn(role.paco_ref_parts)

    def init_stage_action_s3_deploy(self, action_config):
        "Initialize an IAM Role stack to allow access to the S3 Bucket for the action"
        # Create a role to allow access to the S3 Bucket
        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[codepipeline_account_id]}'
instance_profile: false
path: /
role_name: S3
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - s3:*
        resource:
          - {0[bucket_arn]}
          - {0[bucket_arn]}/*
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
        bucket_config = self.paco_ctx.get_ref(action_config.bucket)
        role_table = {
            'codepipeline_account_id': self.pipeline_account_ctx.get_id(),
            'bucket_account_id': self.account_ctx.get_id(),
            'bucket_arn': self.paco_ctx.get_ref(bucket_config.paco_ref +'.arn'),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }

        role_config_dict = yaml.load(role_yaml.format(role_table))
        role_config = models.iam.Role('delegate', action_config)
        role_config.apply_config(role_config_dict)
        role_config.enabled = action_config.is_enabled()

        iam_ctl = self.paco_ctx.get_controller('IAM')
        # The ID to give this role is: group.resource.instance_iam_role
        role_id = self.gen_iam_role_id(self.res_id, 'delegate')
        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.delegate.arn'))
        # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        bucket_account_ctx = self.paco_ctx.get_account_context(bucket_config.account)
        role_ref = '{}.delegate'.format(action_config.paco_ref_parts)
        iam_ctl.add_role(
            account_ctx=bucket_account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params,
        )
        action_config._delegate_role_arn = iam_ctl.role_arn(role_ref)


    def init_stage_action_codedeploy_deploy(self, action_config):
        "Initialize a CodeDeploy stack for the action"
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.codedeploy_tools_delegate_role.arn'))
        self.artifacts_bucket_policy_resource_arns.append(self.paco_ctx.get_ref(action_config.auto_scaling_group+'.instance_iam_role.arn'))
        action_config._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodeDeploy,
            stack_tags=self.stack_tags,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'app_name': self.app.name,
                'action_config': action_config,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name'],
            },
        )

    def create_image_definitions_artifact_cache(self, hook, pipeline):
        "Create a cache id for the imageDefinitions service name"
        service = ''
        for action in pipeline.deploy.values():
            if action.type == 'ECS.Deploy':
                service = get_model_obj_from_ref(action.service, self.paco_ctx.project)
            return service.name + ':' + self.artifacts_bucket_meta['obj'].account

    def create_image_definitions_artifact(self, hook, pipeline):
        "Create an imageDefinitions file"
        ecr_uri = None
        service = None
        for action in pipeline.source.values():
            if action.type == 'ECR.Source':
                ecr_uri = f"{self.pipeline_account_ctx.get_id()}.dkr.ecr.{self.aws_region}.amazonaws.com/{action.repository}:{action.image_tag}"
        for action in pipeline.deploy.values():
            if action.type == 'ECS.Deploy':
                service = get_model_obj_from_ref(action.service, self.paco_ctx.project)
        file_contents = f"""[
  {{
    "name": "{service.name}",
    "imageUri": "{ecr_uri}"
  }}
]
"""
        # Create temp zip file of the imageDefinitions.json
        orig_cwd = os.getcwd()
        work_path = pathlib.Path(self.paco_ctx.build_path)
        work_path = work_path / 'DeploymentPipeline' / self.app.paco_ref_parts / self.pipeline_account_ctx.get_name()
        work_path = work_path / self.aws_region / self.app.name / self.resource.group_name / self.resource.name / 'ImageDefinitions'
        zip_path = work_path / 'zip'
        pathlib.Path(zip_path).mkdir(parents=True, exist_ok=True)
        os.chdir(zip_path)
        image_def_path = zip_path / 'imagedefinitions.json'
        with open(image_def_path, "w") as output_fd:
            output_fd.write(file_contents)
        archive_path = work_path / 'imagedef'
        shutil.make_archive(archive_path, 'zip', zip_path)
        os.chdir(orig_cwd)

        # Upload to S3
        bucket_name = self.artifacts_bucket_meta['name']
        s3_key = self.pipeline._stack.get_name() + '-imagedef.zip'
        bucket_account_ctx = self.paco_ctx.get_account_context(self.artifacts_bucket_meta['obj'].account)
        bucket_s3_client = bucket_account_ctx.get_aws_client('s3')
        pipeline_s3_client = self.pipeline_account_ctx.get_aws_client('s3')
        canonical_id = pipeline_s3_client.list_buckets()['Owner']['ID']
        bucket_s3_client.upload_file(
            str(archive_path) + '.zip',
            bucket_name,
            s3_key,
            ExtraArgs={
                'GrantFullControl': 'id="' + canonical_id + '"',
            },
        )

    def init_stage_action_ecr_source(self, action_config):
        "Initialize an ECR Source action"
        if not action_config.is_enabled():
            return

        # KMS principle
        self.kms_crypto_principle_list.append("paco.sub '${%s}'" % (self.pipeline.paco_ref + '.codepipeline_role.arn'))
        s3_bucket = self.artifacts_bucket_meta['obj']
        if s3_bucket.versioning != True:
            raise InvalidAWSConfiguration(f"""The DeploymentPipeline artifact bucket needs versioning enabled to support the ECR.Source action.
Enabled on the S3Bucket resource with `versioning: true`.

DeploymentPipeline: {self.pipeline.paco_ref}
ArtifactsBucket: {s3_bucket.paco_ref}
""")

    def add_ecr_source_hooks(self, action):
        if not action.is_enabled():
            return
        # Hook to create and upload imageDefinitions.json S3 source artifact
        self.pipeline._stack.hooks.add(
            name='CreateImageDefinitionsArtifact.' + self.resource.name,
            stack_action='update',
            stack_timing='post',
            hook_method=self.create_image_definitions_artifact,
            cache_method=self.create_image_definitions_artifact_cache,
            hook_arg=self.pipeline,
        )
        self.pipeline._stack.hooks.add(
            name='CreateImageDefinitionsArtifact.' + self.resource.name,
            stack_action='create',
            stack_timing='post',
            hook_method=self.create_image_definitions_artifact,
            cache_method=self.create_image_definitions_artifact_cache,
            hook_arg=self.pipeline,
        )

    def init_stage_action_ecs_deploy(self, action_config):
        "Initialize an ECS stack for the action"
        if not action_config.is_enabled():
            return

        role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[pipeline_account_id]}'
instance_profile: false
path: /
role_name: ECS
policies:
  - name: DeploymentPipeline
    statement:
      - effect: Allow
        action:
          - 'ecs:*'
          - 'ecr:*'
          - 'iam:PassRole'
        resource:
          - '*'
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
        role_table = {
            'pipeline_account_id': self.pipeline_account_ctx.get_id(),
            'artifact_bucket_arn': self.artifacts_bucket_meta['arn']
        }
        role_config_dict = yaml.load(role_yaml.format(role_table))
        role_config = models.iam.Role('ecs-delegate', action_config)
        role_config.apply_config(role_config_dict)
        role_config.enabled = action_config.is_enabled()
        iam_ctl = self.paco_ctx.get_controller('IAM')
        role_id = self.gen_iam_role_id(self.res_id, 'ecs-delegate')
         # IAM Roles Parameters
        iam_role_params = [{
            'key': 'CMKArn',
            'value': self.pipeline.paco_ref + '.kms.arn',
            'type': 'String',
            'description': 'DeploymentPipeline KMS Key Arn'
        }]
        iam_ctl.add_role(
            account_ctx=self.account_ctx,
            region=self.aws_region,
            resource=self.resource,
            role=role_config,
            iam_role_id=role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
            template_params=iam_role_params
        )

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (role_config.paco_ref + '.arn'))
        action_config._delegate_role_arn = iam_ctl.role_arn(role_config.paco_ref_parts)


    def init_stage_action_codebuild_build(self, action_config):
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.project_role.arn'))
        self.kms_crypto_principle_list.append("paco.sub '${%s}'" % (action_config.paco_ref+'.project_role.arn'))
        action_config._stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.CodeBuild,
            account_ctx=self.pipeline_account_ctx,
            stack_tags=self.stack_tags,
            extra_context={
                'base_aws_name': self.base_aws_name,
                'app_name': self.app.name,
                'action_config': action_config,
                'artifacts_bucket_name': self.artifacts_bucket_meta['name'],
            }
        )

    def init_stage_action_manualapproval(self, action_config):
        pass

    def resolve_ref(self, ref):
        if schemas.IDeploymentPipelineDeployECS.providedBy(ref.resource):
            if ref.resource_ref == 'ecs-delegate.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        if schemas.IDeploymentPipelineDeployS3.providedBy(ref.resource):
            if ref.resource_ref == 'delegate_role.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        if schemas.IDeploymentPipelineDeployCodeDeploy.providedBy(ref.resource):
            # CodeDeploy
            if ref.resource_ref == 'deployment_group.name':
                return ref.resource._stack
            elif ref.resource_ref == 'codedeploy_tools_delegate_role.arn':
                return ref.resource._stack.template.get_tools_delegate_role_arn()
            elif ref.resource_ref == 'codedeploy_application_name':
                return ref.resource._stack.template.get_application_name()
            elif ref.resource_ref == 'deployment_group.name':
                return ref.resource._stack
        elif schemas.IDeploymentPipeline.providedBy(ref.resource):
            # DeploymentPipeline
            if ref.resource_ref.startswith('kms.'):
                return self.kms_stack
            elif ref.resource_ref.startswith('s3deploydelegate_'):
                account_name = ref.resource_ref.split('.')[0][len('s3deploydelegate_'):]
                return self.s3deploy_delegate_role_arns['paco.ref accounts.' + account_name]
            elif ref.resource_ref == 'codepipeline_role.arn':
                return ref.resource._stack.template.get_codepipeline_role_arn()
            elif ref.resource_ref == 'arn':
                return ref.resource._stack.template.pipeline_arn

        elif schemas.IDeploymentPipelineSourceCodeCommit.providedBy(ref.resource):
            # CodeCommit
            if ref.resource_ref == self.codecommit_role_name+'.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
            elif ref.resource_ref == 'codecommit.arn':
                codecommit_ref = ref.resource.codecommit_repository
                return self.paco_ctx.get_ref(codecommit_ref+".arn")
        elif schemas.IDeploymentPipelineSourceGitHub.providedBy(ref.resource):
            # GitHub
            if ref.resource_ref == self.github_role_name + '.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        elif schemas.IDeploymentPipelineBuildCodeBuild.providedBy(ref.resource):
            # CodeBuild
            if ref.resource_ref == 'project_role.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._stack.template.get_project_role_arn()
            elif ref.resource_ref == 'project.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._stack.template.get_project_arn()
