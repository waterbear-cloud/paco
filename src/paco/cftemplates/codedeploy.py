from paco.cftemplates.cftemplates import StackTemplate


class CodeDeploy(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        base_aws_name,
        app_name,
        action_config,
        artifacts_bucket_name
    ):
        pipeline_config = stack.resource
        cpbd_config_ref = action_config.paco_ref_parts
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('CodeDeploy', self.resource_group_name, self.resource.name)
        self.res_name_prefix = self.create_resource_name_join(
            name_list=[base_aws_name, app_name, self.resource_group_name, self.resource.name],
            separator='-',
            camel_case=True
        )
        if not action_config.is_enabled():
            self.init_template('Code Deploy')
            self.set_template(self.template.to_yaml())
            return

        self.codedeploy_tools_delegate_role_name = self.get_tools_delegate_role_name()
        self.codedeploy_service_role_name = self.get_role_name()
        self.application_name = self.res_name_prefix

        # Initialize Parameters
        self.set_parameter('ResourceNamePrefix', self.res_name_prefix)
        self.set_parameter('ApplicationName', self.application_name)
        self.set_parameter('CodeDeployASGName', action_config.auto_scaling_group+'.name')
        self.set_parameter('ELBName', action_config.elb_name)
        if action_config.alb_target_group == None:
            alb_target_group_name = ""
        else:
            alb_target_group_name = action_config.alb_target_group+'.name'
        self.set_parameter('ALBTargetGroupName', alb_target_group_name)
        self.set_parameter('ArtifactsBucketName', artifacts_bucket_name)
        self.set_parameter('CodeDeployAutoRollbackEnabled', action_config.auto_rollback_enabled)
        self.set_parameter('CodeDeployStyleOption', action_config.deploy_style_option)
        self.set_parameter('CodeDeployConfigType', action_config.minimum_healthy_hosts.type)
        self.set_parameter('CodeDeployConfigValue', action_config.minimum_healthy_hosts.value)
        self.set_parameter('ToolsAccountId', pipeline_config.configuration.account+'.id')
        deploy_kms_ref = pipeline_config.paco_ref + '.kms.arn'
        self.set_parameter('CMKArn', deploy_kms_ref)
        self.set_parameter('TargetInstanceRoleName', action_config.auto_scaling_group+'.instance_iam_role.name')

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Code Deploy'

Parameters:

  ResourceNamePrefix:
    Description: The name to prefix to AWS resources
    Type: String

  ApplicationName:
    Description: The name of the CodeDeploy Application
    Type: String

  ArtifactsBucketName:
    Description: The bname of the S3 Bucket to create that will hold deployment artifacts
    Type: String

  CodeDeployASGName:
    Description: The name of the AutoScaling Group of the deployment workload
    Type: String

  CodeDeployAutoRollbackEnabled:
    Description: Boolean indicating whether CodeDeploy will rollback a deployment if an error is encountered
    Type: String
    AllowedValues:
      - true
      - false

  CodeDeployConfigType:
    Description: The minimum healthy instance type HOST_COUNT or FLEET_PERCENT
    Type: String
    AllowedValues:
      - HOST_COUNT
      - FLEET_PERCENT

  CodeDeployStyleOption:
    Description: Either WITH_TRAFFIC_CONTROL or WITHOUT_TRAFFIC_CONTROL
    Type: String

  CodeDeployConfigValue:
    Description: The minimum number or percent of healthy hosts relevant to the chosen ConfigType
    Type: String

  ELBName:
    Description: The name of the ELB that will be managed by CodeDeploy during deployment
    Type: String

  ALBTargetGroupName:
    Description: The name of the target group that will be managed by CodeDeploy during deployment
    Type: String

  ToolsAccountId:
    Description: The AWS Account ID of the Tools account
    Type: String

  CMKArn:
    Description: The KMS CMK Arn of the key used to encrypt deployment artifacts
    Type: String

  TargetInstanceRoleName:
    Description: The ARN of the Role attached to the EC2 instance CodeDeploy deploys to
    Type: String

Conditions:
  ELBNameIsEmpty: !Equals [!Ref ELBName, ""]
  ALBTargetGroupNameIsEmpty: !Equals [!Ref ALBTargetGroupName, ""]

Resources:

# ----------------------------------------------------------------------------
# CodeDeploy

  ToolsDelegateRole:
    Type: AWS::IAM::Role
    DependsOn:
      - CodeDeployGroup
      - CodeDeployConfiguration
      - CodeDeployApplication
    Properties:
      RoleName: %s
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              AWS:
                - !Ref ToolsAccountId
            Action:
              - sts:AssumeRole
      Path: /
      Policies:
        - PolicyName: CodeDeploy
          PolicyDocument:
            Version: 2012-10-17
            Statement:
              - Effect: Allow
                Action:
                  - 'codedeploy:CreateDeployment'
                  - 'codedeploy:GetDeployment'
                  - 'codedeploy:GetDeploymentConfig'
                  - 'codedeploy:GetApplicationRevision'
                  - 'codedeploy:RegisterApplicationRevision'
                Resource:
                  - !Sub 'arn:aws:codedeploy:${AWS::Region}:${AWS::AccountId}:deploymentgroup:${CodeDeployApplication}/${CodeDeployGroup}'
                  - !Sub 'arn:aws:codedeploy:${AWS::Region}:${AWS::AccountId}:application:${CodeDeployApplication}'
                  - !Sub 'arn:aws:codedeploy:${AWS::Region}:${AWS::AccountId}:deploymentconfig:${CodeDeployConfiguration}'
              - Sid: KMSCMK
                Effect: Allow
                Action:
                  - 'kms:DescribeKey'
                  - 'kms:GenerateDataKey*'
                  - 'kms:Encrypt'
                  - 'kms:ReEncrypt*'
                  - 'kms:Decrypt'
                Resource: !Ref CMKArn
              - Sid: S3ArtifactsBucket
                Effect: Allow
                Action:
                  - 's3:GetObject*'
                  - 's3:PutObject'
                  - 's3:PutObjectAcl'
                Resource:
                  - !Sub 'arn:aws:s3:::${ArtifactsBucketName}/*'
                  - !Sub 'arn:aws:s3:::${ArtifactsBucketName}'

  CodeDeployServiceRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: %s
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - codedeploy.amazonaws.com
            Action:
              - sts:AssumeRole
      Path: /

  CodeDeployServicePolicy:
    Type: AWS::IAM::Policy
    DependsOn:
      - CodeDeployServiceRole
    Properties:
      PolicyName: CodeDeployService
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action:
              - autoscaling:CompleteLifecycleAction
              - autoscaling:DeleteLifecycleHook
              - autoscaling:DescribeAutoScalingGroups
              - autoscaling:DescribeLifecycleHooks
              - autoscaling:PutLifecycleHook
              - autoscaling:RecordLifecycleActionHeartbeat
              - autoscaling:CreateAutoScalingGroup
              - autoscaling:UpdateAutoScalingGroup
              - autoscaling:EnableMetricsCollection
              - autoscaling:DescribeAutoScalingGroups
              - autoscaling:DescribePolicies
              - autoscaling:DescribeScheduledActions
              - autoscaling:DescribeNotificationConfigurations
              - autoscaling:DescribeLifecycleHooks
              - autoscaling:SuspendProcesses
              - autoscaling:ResumeProcesses
              - autoscaling:AttachLoadBalancers
              - autoscaling:PutScalingPolicy
              - autoscaling:PutScheduledUpdateGroupAction
              - autoscaling:PutNotificationConfiguration
              - autoscaling:PutLifecycleHook
              - autoscaling:DescribeScalingActivities
              - autoscaling:DeleteAutoScalingGroup
              - ec2:DescribeInstances
              - ec2:DescribeInstanceStatus
              - ec2:TerminateInstances
              - tag:GetTags
              - tag:GetResources
              - sns:Publish
              - cloudwatch:DescribeAlarms
              - cloudwatch:PutMetricAlarm
              - elasticloadbalancing:DescribeLoadBalancers
              - elasticloadbalancing:DescribeInstanceHealth
              - elasticloadbalancing:RegisterInstancesWithLoadBalancer
              - elasticloadbalancing:DeregisterInstancesFromLoadBalancer
              - elasticloadbalancing:DescribeTargetGroups
              - elasticloadbalancing:DescribeTargetHealth
              - elasticloadbalancing:RegisterTargets
              - elasticloadbalancing:DeregisterTargets
            Resource: "*"
      Roles:
        - !Ref CodeDeployServiceRole

  CodeDeployTargetInstancePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action:
              - 'kms:DescribeKey'
              - 'kms:GenerateDataKey*'
              - 'kms:Encrypt'
              - 'kms:ReEncrypt*'
              - 'kms:Decrypt'
            Resource:
              - !Ref CMKArn
          - Effect: Allow
            Action:
              - 's3:Get*'
            Resource:
              - !Sub 'arn:aws:s3:::${ArtifactsBucketName}/*'
              - !Sub 'arn:aws:s3:::aws-codedeploy-${AWS::Region}/*'
          - Effect: Allow
            Action:
              - 'autoscaling:DescribeAutoScalingGroups'
              - 'autoscaling:DescribeAutoScalingInstances'
            Resource:
              - '*' # XXX: Secure this
          - Effect: Allow
            Action:
              - 'autoscaling:UpdateAutoScalingGroup'
              - 'autoscaling:EnterStandby'
              - 'autoscaling:ExitStandby'
            Resource:
              - '*' # XXX: Secure this
      Roles:
        - !Ref TargetInstanceRoleName

  CodeDeployApplication:
    Type: AWS::CodeDeploy::Application
    Properties:
      ApplicationName: !Ref ApplicationName
      ComputePlatform: Server

  CodeDeployConfiguration:
    Type: AWS::CodeDeploy::DeploymentConfig
    Properties:
      DeploymentConfigName: !Ref ResourceNamePrefix
      MinimumHealthyHosts:
        Type: !Ref CodeDeployConfigType
        Value: !Ref CodeDeployConfigValue

  CodeDeployGroup:
    Type: AWS::CodeDeploy::DeploymentGroup
    DependsOn:
      - CodeDeployServicePolicy
      - CodeDeployServiceRole
      - CodeDeployApplication
      - CodeDeployConfiguration
    Properties:
      DeploymentGroupName: !Sub '${ResourceNamePrefix}-Group'
      ApplicationName: !Ref CodeDeployApplication
      AutoScalingGroups:
        - !Ref CodeDeployASGName
      AutoRollbackConfiguration:
        Enabled: !Ref CodeDeployAutoRollbackEnabled
        Events:
          - DEPLOYMENT_FAILURE
          - DEPLOYMENT_STOP_ON_ALARM
          - DEPLOYMENT_STOP_ON_REQUEST
      DeploymentConfigName: !Ref CodeDeployConfiguration
      ServiceRoleArn: !GetAtt CodeDeployServiceRole.Arn
      DeploymentStyle:
        DeploymentOption: !Ref CodeDeployStyleOption
        DeploymentType: IN_PLACE
      LoadBalancerInfo:
        ElbInfoList:
          !If
            - ELBNameIsEmpty
            - !Ref AWS::NoValue
            - - Name: !Ref ELBName
        TargetGroupInfoList:
          !If
            - ALBTargetGroupNameIsEmpty
            - !Ref AWS::NoValue
            - - Name: !Ref ALBTargetGroupName

Outputs:
  DeploymentGroupName:
     Value: !Ref CodeDeployGroup

"""

        self.stack.register_stack_output_config(cpbd_config_ref+'.deployment_group.name', 'DeploymentGroupName')
        self.set_template(template_fmt % (
            self.codedeploy_tools_delegate_role_name,
            self.codedeploy_service_role_name
        ))

    def get_role_name(self):
        return self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodeDeploy-Service'],
            filter_id='IAM.Role.RoleName'
        )

    def get_role_arn(self):
        account_id = self.account_ctx.get_id()

        return "arn:aws:iam::{0}:role/{1}".format(
            account_id,
            self.codedeploy_service_role_name
        )

    def get_tools_delegate_role_name(self):
        return self.create_iam_resource_name(
            name_list=[self.res_name_prefix, 'CodeDeploy-Tools-Delegate'],
            filter_id='IAM.Role.RoleName'
        )

    def get_tools_delegate_role_arn(self):
        account_id = self.account_ctx.get_id()
        return "arn:aws:iam::{0}:role/{1}".format(
            account_id,
            self.codedeploy_tools_delegate_role_name
        )

    def get_application_name(self):
        return self.application_name

