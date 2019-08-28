import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


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


        self.ResourceName = self.create_resource_name_join(
            name_list=[env_ctx.get_aws_name(), app_id, grp_id, res_id],
            separator='-',
            camel_case=True)

        # Initialize Parameters
        self.set_parameter('ResourceNamePrefix', self.ResourceName)

        # Project Refereces
        self.set_parameter('CodeCommitRepositoryName', res_config.codecommit_repository + ".name" ) # Add .name attribute to aim.ref resource

        # Code Commit Role ARN lookup
        codecommit_role_arn_ref = res_config.aim_ref + '.codecommit_role.arn'
        codecommit_role_arn = self.aim_ctx.get_ref(codecommit_role_arn_ref)
        self.set_parameter('CodeCommitRoleArn', codecommit_role_arn)

        codecommit_repo_arn_ref = res_config.aim_ref + '.codecommit.arn'
        codecommit_repo_arn = self.aim_ctx.get_ref(codecommit_repo_arn_ref)
        self.set_parameter('CodeCommitRepositoryArn', codecommit_repo_arn)

        app_name_ref = res_config.aim_ref + '.codedeploy_application_name'
        codedeploy_application_name = self.aim_ctx.get_ref(app_name_ref)
        self.set_parameter('CodeDeployApplicationName', codedeploy_application_name)

        codedeploy_account_id_ref = 'aim.ref ' + self.env_ctx.config_ref_prefix + '.network.aws_account'
        codedeploy_account_id = self.aim_ctx.get_ref(codedeploy_account_id_ref)
        self.set_parameter('CodeDeployAccountId', codedeploy_account_id)

        codedeploy_aws_region = self.env_ctx.region
        self.set_parameter('CodeDeployRegion', codedeploy_aws_region)
        self.set_parameter('CodeDeployToolsDelegateRoleArn', codedeploy_tools_delegate_role_arn)
        self.set_parameter('ArtifactsBucketName', artifacts_bucket_name)
        self.set_parameter('DeploymentEnvironment', res_config.deployment_environment)
        self.set_parameter('DeploymentBranchName', res_config.deployment_branch_name)
        self.set_parameter('ManualApprovalEnabled', res_config.manual_approval_enabled)
        self.set_parameter('ManualApprovalNotificationEmail', res_config.manual_approval_notification_email)

        codedeploy_ref = res_config.aim_ref + '.deploy.deployment_group.name'
        self.set_parameter('CodeDeployGroupName', codedeploy_ref)

        kms_ref = res_config.aim_ref + '.kms.arn'
        self.set_parameter('CMKArn', kms_ref)

        # Define the Template
        self.set_template("""
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Deployment: CodePipeline and CodeBuild'

Parameters:

  ResourceNamePrefix:
    Description: The name to prefix to AWS resources
    Type: String

  CodeDeployApplicationName:
    Description: The name to prefix to AWS resources
    Type: String

  CodeCommitRepositoryName:
    Description: The name of the CodeCommit repository
    Type: String

  CodeCommitRoleArn:
    Description: The ARN to the CodeCommit Account Delegate Role
    Type: String

  CodeCommitRepositoryArn:
    Description: The ARN to the CodeCommit Repository
    Type: String

  CodeDeployAccountId:
    Description: The AWS Account Id where deployments to CodeDeploy will be sent
    Type: String

  CodeDeployRegion:
    Description: The AWS Region where deployments to CodeDeploy will be sent
    Type: String

  CodeDeployToolsDelegateRoleArn:
    Description: The Arn of the CodeDeploy Delegate Role
    Type: String

  ArtifactsBucketName:
    Description: The bname of the S3 Bucket to create that will hold deployment artifacts
    Type: String

  DeploymentEnvironment:
    Description: The name of the environment codebuild will be deploying into.
    Type: String

  DeploymentBranchName:
    Description: The name of the branch where commits will trigger a build
    Type: String

  ManualApprovalEnabled:
    Description: Boolean indicating whether a manual approval is enabled or not
    Type: String
    AllowedValues:
      - true
      - false

  ManualApprovalNotificationEmail:
    Description: Email to send notifications to when a deployment requires approval
    Type: String
    Default: AWS::NoValue

  CodeDeployGroupName:
    Description: The name of the CodeDeploy deployment group
    Type: String
    Default: AWS::NoValue

  CMKArn:
    Description: The KMS CMK Arn of the key used to encrypt deployment artifacts
    Type: String

Conditions:
  ManualApprovalEnabled: !Equals [!Ref ManualApprovalEnabled, "true"]

Resources:

# ----------------------------------------------------------------------------
# CodeBuild

  CodeBuildProjectRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${ResourceNamePrefix}-CodeBuild'
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          -
            Effect: Allow
            Principal:
              Service:
                - codebuild.amazonaws.com
            Action:
              - sts:AssumeRole
      Path: /

  CodeBuildProjectPolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: !Sub '${ResourceNamePrefix}-CodeBuild-Policy'
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Sid: S3Access
            Action:
              - s3:PutObject
              - s3:PutObjectAcl
              - s3:GetObject
              - s3:GetObjectAcl
              - s3:ListBucket
              - s3:DeleteObject
              - s3:GetBucketPolicy
            Effect: Allow
            Resource:
              - !Sub 'arn:aws:s3:::${ArtifactsBucketName}'
              - !Sub 'arn:aws:s3:::${ArtifactsBucketName}/*'
          - Sid: CloudWatchLogsAccess
            Effect: Allow
            Action:
              - logs:CreateLogGroup
              - logs:CreateLogStream
              - logs:PutLogEvents
            Resource: arn:aws:logs:*:*:*
          - Sid: KMSCMK
            Effect: Allow
            Action:
              - kms:*
            Resource: !Ref CMKArn
      Roles:
        - !Ref CodeBuildProjectRole

  CodeBuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: !Sub '${ResourceNamePrefix}'
      Description: !Ref CodeCommitRepositoryName
      ServiceRole: !GetAtt CodeBuildProjectRole.Arn
      EncryptionKey: !Ref CMKArn
      Artifacts:
        Type: CODEPIPELINE
      Environment:
        Type: linuxContainer
        ComputeType: BUILD_GENERAL1_SMALL
        #ComputeType: BUILD_GENERAL1_MEDIUM
        #ComputeType: BUILD_GENERAL1_LARGE
        Image: aws/codebuild/nodejs:6.3.1
        EnvironmentVariables:
          - Name: ArtifactsBucket
            Value: !Ref ArtifactsBucketName
          - Name: DeploymentEnvironment
            Value: !Ref DeploymentEnvironment
          - Name: KMSKey
            Value: !Ref CMKArn
      Source:
        Type: CODEPIPELINE
      TimeoutInMinutes: 10
      Tags:
        - Key: 'Name'
          Value: !Ref ResourceNamePrefix

# ----------------------------------------------------------------------------
# CodePipeline

  ManualApprovalSNSTopic:
    Type: AWS::SNS::Topic
    Condition: ManualApprovalEnabled
    Properties:
      TopicName: !Sub '${ResourceNamePrefix}-Approval'
      Subscription:
        - Endpoint: !Ref ManualApprovalNotificationEmail
          Protocol: email

  CodePipelineServiceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '${ResourceNamePrefix}-CodePipeline-Service'
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - codepipeline.amazonaws.com
            Action:
              - sts:AssumeRole
      Path: /

  CodePipelinePolicy:
    Type: AWS::IAM::Policy
    DependsOn:
      - CodePipelineServiceRole
    Properties:
      PolicyName: !Sub '${ResourceNamePrefix}-CodePipeline-Policy'
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Sid: CodeCommitAccess
            Effect: Allow
            Action:
              - codecommit:List*
              - codecommit:Get*
              - codecommit:GitPull
              - codecommit:UploadArchive
              - codecommit:CancelUploadArchive
            Resource:
              - !Ref CodeCommitRepositoryArn
          - Sid: 'CodePipelineAccess'
            Effect: Allow
            Action:
              - codepipeline:*
              - sns:Publish
              - s3:ListAllMyBuckets
              - s3:GetBucketLocation
              - iam:ListRoles
              - iam:PassRole
            Resource:
              - "*"
          - Sid: 'CodeBuildAccess'
            Effect: Allow
            Action:
              - codebuild:BatchGetBuilds
              - codebuild:StartBuild
            Resource:
              - !GetAtt CodeBuildProject.Arn
#          - Sid: 'CodeDeployAccess'
#            Effect: Allow
#            Action:
#              - codedeploy:Batch
#              - codedeploy:CreateDeployment
#              - codedeploy:Get*
#              - codedeploy:List*
#              - codedeploy:RegisterApplicationRevision
#            Resource:
#              - !Sub 'arn:aws:codedeploy:${CodeDeployRegion}:${CodeDeployAccountId}:deploymentgroup:${ResourceNamePrefix}/*'
#              - !Sub 'arn:aws:codedeploy:${CodeDeployRegion}:${CodeDeployAccountId}:application:${ResourceNamePrefix}'
#              - !Sub 'arn:aws:codedeploy:${CodeDeployRegion}:${CodeDeployAccountId}:deploymentconfig:${ResourceNamePrefix}'
          - Sid: 'S3Access'
            Effect: Allow
            Action:
              - s3:PutObject
              - s3:GetBucketPolicy
              - s3:GetObject
              - s3:ListBucket
            Resource:
              - !Sub 'arn:aws:s3:::${ArtifactsBucketName}/*'
              - !Sub 'arn:aws:s3:::${ArtifactsBucketName}'
          - Sid: 'KMSCMK'
            Effect: Allow
            Action:
              - kms:Decrypt
            Resource: !Ref CMKArn
          - Sid: 'CodeDeployAssumeRole'
            Effect: Allow
            Action:
              - sts:AssumeRole
            Resource:
              - !Ref CodeDeployToolsDelegateRoleArn
          - Sid: 'CodeCommitAssumeRole'
            Effect: Allow
            Action:
              - sts:AssumeRole
            Resource:
              - !Ref CodeCommitRoleArn
      Roles:
        - !Ref CodePipelineServiceRole

  # BuildPipeline is used when Manual Approval is disabled.
  BuildCodePipeline:
    Type: AWS::CodePipeline::Pipeline
    DependsOn:
      - CodePipelinePolicy
      - CodeBuildProject
    Properties:
      RoleArn: !GetAtt CodePipelineServiceRole.Arn
      Name: !Ref ResourceNamePrefix
      Stages:
        - Name: CodeCommitSource
          Actions:
            - Name: CodeCommit
              ActionTypeId:
                Category: Source
                Owner: AWS
                Version: 1
                Provider: CodeCommit
              Configuration:
                RepositoryName: !Ref CodeCommitRepositoryName
                BranchName: !Ref DeploymentBranchName
              OutputArtifacts:
                - Name: CodeCommitArtifact
              RunOrder: 1
              RoleArn: !Ref CodeCommitRoleArn
        - Name: Build
          Actions:
            - Name: Build
              ActionTypeId:
                Category: Build
                Owner: AWS
                Version: 1
                Provider: CodeBuild
              Configuration:
                ProjectName: !Ref ResourceNamePrefix
              RunOrder: 1
              InputArtifacts:
                - Name: CodeCommitArtifact
              OutputArtifacts:
                - Name: CodeDeployPackage
        - Name: Deploy
          Actions:
            - !If
              - ManualApprovalEnabled
              - Name: Approval
                InputArtifacts: []
                OutputArtifacts: []
                ActionTypeId:
                  Category: Approval
                  Owner: AWS
                  Version: 1
                  Provider: Manual
                RunOrder: 1
                Configuration:
                  NotificationArn: !Ref ManualApprovalSNSTopic
              - !Ref AWS::NoValue
            - Name: ExternalDeploy
              ActionTypeId:
                Category: Deploy
                Owner: AWS
                Version: 1
                Provider: CodeDeploy
              Configuration:
                ApplicationName: !Ref CodeDeployApplicationName
                DeploymentGroupName: !Ref CodeDeployGroupName
              RunOrder: !If [ManualApprovalEnabled, 2, 1]
              InputArtifacts:
                - Name: CodeDeployPackage
              RoleArn: !Ref CodeDeployToolsDelegateRoleArn
              Region: !Ref CodeDeployRegion
      ArtifactStore:
        Type: S3
        Location: !Ref ArtifactsBucketName
        EncryptionKey:
          Id: !Ref CMKArn
          Type: KMS
""")

    def get_codebuild_role_arn(self):
        return "arn:aws:iam::{0}:role/".format(self.account_ctx.get_id()) + self.ResourceName + "-CodeBuild"

    def get_codepipeline_role_arn(self):
        return "arn:aws:iam::{0}:role/".format(self.account_ctx.get_id()) + self.ResourceName + "-CodePipeline-Service"

