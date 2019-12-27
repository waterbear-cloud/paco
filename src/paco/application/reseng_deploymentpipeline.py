from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.core.yaml import YAML
from paco.models import schemas
from paco import models

yaml=YAML()
yaml.default_flow_sytle = False

class DeploymentPipelineResourceEngine(ResourceEngine):

    def __init__(self, app_engine, grp_id, res_id, resource, stack_tags):
        super().__init__(app_engine, grp_id, res_id, resource, stack_tags)
        self.pipeline_account_ctx = None
        self.pipeline_config = resource
        self.kms_template = None
        self.kms_crypto_principle_list = []
        self.artifacts_bucket_policy_resource_arns = []
        self.artifacts_bucket_meta = {
            'ref': None,
            'arn': None,
            'name': None,
        }
        self.codecommit_role_name = 'codecommit_role'
        self.source_stage = None

    def init_stage(self, stage_config):
        if stage_config == None:
            return
        for action_name in stage_config.keys():
            action_config = stage_config[action_name]
            action_config.resolve_ref_obj = self
            method_name = 'init_stage_action_' + action_config.type.replace('.', '_').lower()
            method = getattr(self, method_name)
            method(action_config)

    def init_resource(self):
        self.pipeline_config.resolve_ref_obj = self
        self.pipeline_config.configuration.resolve_ref_obj = self
        self.pipeline_account_ctx = self.paco_ctx.get_account_context(self.pipeline_config.configuration.account)

        # S3 Artifacts Bucket:
        s3_ctl = self.paco_ctx.get_controller('S3')
        self.artifacts_bucket_meta['ref'] = self.pipeline_config.configuration.artifacts_bucket
        self.artifacts_bucket_meta['arn'] = s3_ctl.get_bucket_arn(self.artifacts_bucket_meta['ref'])
        self.artifacts_bucket_meta['name'] = s3_ctl.get_bucket_name(self.artifacts_bucket_meta['ref'])

        # KMS Key
        kms_refs = {}
        # Application Account
        aws_account_ref = 'paco.ref ' + self.parent_config_ref + '.network.aws_account'
        app_account = self.paco_ctx.get_ref(aws_account_ref)
        kms_refs[app_account] = None

        # CodeCommit Account(s)
        # ToDo: allows ALL CodeCommit accounts access, filter out non-CI/CD CodeCommit repos?
        for subdict in self.paco_ctx.project['resource']['codecommit'].repository_groups.values():
            for repo in subdict.values():
                kms_refs[repo.account] = None
        for key in kms_refs.keys():
            self.kms_crypto_principle_list.append(
                "paco.sub 'arn:aws:iam::${%s}:root'" % (key)
            )

        kms_config_dict = {
            'admin_principal': {
                'aws': [ "!Sub 'arn:aws:iam::${{AWS::AccountId}}:root'" ]
            },
            'crypto_principal': {
                'aws': self.kms_crypto_principle_list
            }
        }
        kms_config_ref = self.pipeline_config.paco_ref_parts + '.kms'
        self.kms_template = cftemplates.KMS(
            self.paco_ctx,
            self.pipeline_account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.grp_id,
            self.res_id,
            self.resource,
            kms_config_ref,
            kms_config_dict
        )

        # Stages
        self.init_stage(self.pipeline_config.source)
        self.init_stage(self.pipeline_config.build)
        self.init_stage(self.pipeline_config.deploy)

        # CodePipeline
        codepipeline_config_ref = self.pipeline_config.paco_ref_parts + '.codepipeline'
        self.pipeline_config._template = cftemplates.CodePipeline(
            self.paco_ctx,
            self.pipeline_account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.artifacts_bucket_meta['name'],
            codepipeline_config_ref
        )

        # Add CodeBuild Role ARN to KMS Key principal now that the role is created
        kms_config_dict['crypto_principal']['aws'] = self.kms_crypto_principle_list
        kms_template = cftemplates.KMS(
            self.paco_ctx,
            self.pipeline_account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.grp_id,
            self.res_id,
            self.resource,
            kms_config_ref,
            kms_config_dict
        )
        # Adding a file id allows us to generate a second template without overwritting
        # the first one. This is needed as we need to update the KMS policy with the
        # Codebuild Arn after the Codebuild has been created.
        kms_template.set_dependency(self.kms_template, 'post-pipeline')

        # Get the ASG Instance Role ARN
        if not self.pipeline_config.is_enabled():
            return
        self.artifacts_bucket_policy_resource_arns.append(
            "paco.sub '${%s}'" % (self.pipeline_config.paco_ref + '.codepipeline_role.arn')
        )
        cpbd_s3_bucket_policy = {
            'aws': self.artifacts_bucket_policy_resource_arns,
            'action': [ 's3:*' ],
            'effect': 'Allow',
            'resource_suffix': [ '/*', '' ]
        }
        s3_ctl.add_bucket_policy(self.artifacts_bucket_meta['ref'], cpbd_s3_bucket_policy)

    def init_stage_action_codecommit_source(self, action_config):
        if not action_config.is_enabled():
            return

        # -------------------------------------------
        # CodeCommit Delegate Role
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
        iam_role_params = [
            {
                'key': 'CMKArn',
                'value': self.pipeline_config.paco_ref + '.kms.arn',
                'type': 'String',
                'description': 'DeploymentPipeline KMS Key Arn'
            }
        ]
        codecommit_account_ref = self.paco_ctx.get_ref(action_config.codecommit_repository+'.account')
        codecommit_account_ctx = self.paco_ctx.get_account_context(codecommit_account_ref)
        codecommit_iam_role_ref = '{}.{}'.format(action_config.paco_ref_parts, self.codecommit_role_name)
        iam_ctl.add_role(
            paco_ctx=self.paco_ctx,
            account_ctx=codecommit_account_ctx,
            region=self.aws_region,
            group_id=self.grp_id,
            role_id=codecommit_iam_role_id,
            role_ref=codecommit_iam_role_ref,
            role_config=codecommit_iam_role_config,
            stack_group=self.stack_group,
            template_params=iam_role_params,
            stack_tags=self.stack_tags
        )

    # S3 Deploy
    def init_stage_action_s3_deploy(self, action_config):
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
        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.delegate_role.arn'))
        # IAM Roles Parameters
        iam_role_params = [
            {
                'key': 'CMKArn',
                'value': self.pipeline_config.paco_ref + '.kms.arn',
                'type': 'String',
                'description': 'DeploymentPipeline KMS Key Arn'
            }
        ]
        bucket_account_ctx = self.paco_ctx.get_account_context(bucket_config.account)
        role_ref = '{}.delegate_role'.format(action_config.paco_ref_parts)
        iam_ctl.add_role(
            paco_ctx=self.paco_ctx,
            account_ctx=bucket_account_ctx,
            region=self.aws_region,
            group_id=self.grp_id,
            role_id=role_id,
            role_ref=role_ref,
            role_config=role_config,
            stack_group=self.stack_group,
            template_params=iam_role_params,
            stack_tags=self.stack_tags
        )
        action_config._delegate_role_arn = iam_ctl.role_arn(role_ref)


    # Code Deploy
    def init_stage_action_codedeploy_deploy(self, action_config):
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.codedeploy_tools_delegate_role.arn'))
        self.artifacts_bucket_policy_resource_arns.append(self.paco_ctx.get_ref(action_config.auto_scaling_group+'.instance_iam_role.arn'))
        codedeploy_config_ref = action_config.paco_ref_parts
        action_config._template = cftemplates.CodeDeploy(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.pipeline_config,
            action_config,
            self.artifacts_bucket_meta['name'],
            codedeploy_config_ref
        )

    def init_stage_action_codebuild_build(self, action_config):
        if not action_config.is_enabled():
            return

        self.artifacts_bucket_policy_resource_arns.append("paco.sub '${%s}'" % (action_config.paco_ref + '.project_role.arn'))
        self.kms_crypto_principle_list.append("paco.sub '${%s}'" % (action_config.paco_ref+'.project_role.arn'))
        codebuild_config_ref = action_config.paco_ref_parts
        action_config._template = cftemplates.CodeBuild(
            self.paco_ctx,
            self.pipeline_account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.pipeline_config,
            action_config,
            self.artifacts_bucket_meta['name'],
            codebuild_config_ref
        )

    def init_stage_action_manualapproval(self, action_config):
        pass

    def resolve_ref(self, ref):
        if schemas.IDeploymentPipelineDeployS3.providedBy(ref.resource):
            if ref.resource_ref == 'delegate_role.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
        if schemas.IDeploymentPipelineDeployCodeDeploy.providedBy(ref.resource):
            # CodeDeploy
            if ref.resource_ref == 'deployment_group.name':
                return ref.resource._template.stack
            elif ref.resource_ref == 'codedeploy_tools_delegate_role.arn':
                return ref.resource._template.get_tools_delegate_role_arn()
            elif ref.resource_ref == 'codedeploy_application_name':
                return ref.resource._template.get_application_name()
            elif ref.resource_ref == 'deployment_group.name':
                return ref.resource._template.stack
        elif schemas.IDeploymentPipeline.providedBy(ref.resource):
            # DeploymentPipeline
            if ref.resource_ref.startswith('kms.'):
                return self.kms_template.stack
            elif ref.resource_ref == 'codepipeline_role.arn':
                return ref.resource._template.get_codepipeline_role_arn()
        elif schemas.IDeploymentPipelineSourceCodeCommit.providedBy(ref.resource):
            # CodeCommit
            if ref.resource_ref == self.codecommit_role_name+'.arn':
                iam_ctl = self.paco_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
            elif ref.resource_ref == 'codecommit.arn':
                codecommit_ref = ref.resource.codecommit_repository
                return self.paco_ctx.get_ref(codecommit_ref+".arn")
        elif schemas.IDeploymentPipelineBuildCodeBuild.providedBy(ref.resource):
            # CodeBuild
            if ref.resource_ref == 'project_role.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._template.get_project_role_arn()
            elif ref.resource_ref == 'project.arn':
                # self.cpbd_codepipebuild_template will fail if there are two deployments
                # this application... corner case, but might happen?
                return ref.resource._template.get_project_arn()