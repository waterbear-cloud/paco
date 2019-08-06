import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from aim.models.references import Reference
from aim.utils import normalized_join
from io import StringIO
from enum import Enum
import base64


class ASG(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 env_ctx,
                 aws_name,
                 app_id,
                 grp_id,
                 asg_id,
                 asg_config,
                 asg_config_ref,
                 role_profile_arn,
                 ec2_manager_user_data_script,
                 ec2_manager_cache_id ):

        #aim_ctx.log("ASG CF Template init")
        self.env_ctx = env_ctx
        self.ec2_manager_cache_id = ec2_manager_cache_id
        segment_stack = self.env_ctx.get_segment_stack(asg_config.segment)

        # Super Init:
        aws_name='-'.join(["ASG", aws_name])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=asg_config_ref,
                         aws_name=aws_name)

        self.asg_config = asg_config

        # Initialize Parameters
        self.set_parameter('LCEBSOptimized', asg_config.ebs_optimized)
        self.set_parameter('LCInstanceAMI', asg_config.instance_ami)
        self.set_parameter('LCInstanceType', asg_config.instance_type)
        self.set_parameter('LCInstanceMonitoring', asg_config.instance_monitoring)
        self.set_parameter('LCInstanceKeyPair', asg_config.instance_key_pair)
        self.set_parameter('LCAssociatePublicIpAddress', asg_config.associate_public_ip_address)
        if role_profile_arn != None:
          self.set_parameter('LCIamInstanceProfile', role_profile_arn)

        # Security Group List
        sg_output_param = StackOutputParam('LCSecurityGroupList')
        for sg_ref in asg_config.security_groups:
            # TODO: Better name for self.get_stack_outputs_key_from_ref?
            sg_output_key = self.get_stack_outputs_key_from_ref(Reference(sg_ref))
            sg_stack = self.aim_ctx.get_ref(sg_ref)
            sg_output_param.add_stack_output(sg_stack, sg_output_key)
        self.set_parameter(sg_output_param)

        asg_name = normalized_join([self.env_ctx.netenv_id, self.env_ctx.env_id, app_id, grp_id, asg_id], '', True)
        self.set_parameter('ASGName', asg_name)
        self.set_parameter('ASGDesiredCapacity', asg_config.desired_capacity)
        self.set_parameter('ASGHealthCheckGracePeriodSecs', asg_config.health_check_grace_period_secs)
        self.set_parameter('ASGHealthCheckType', asg_config.health_check_type)
        self.set_parameter('ASGMaxSize', asg_config.max_instances)
        self.set_parameter('ASGMinSize', asg_config.min_instances)
        self.set_parameter('ASGCooldownSecs', asg_config.cooldown_secs)

        # Termination Policies List
        self.set_parameter('ASGTerminationPolicies', asg_config.termination_policies)

        self.set_parameter('ASGUpdatePolicyMaxBatchSize', asg_config.update_policy_max_batch_size)
        self.set_parameter('ASGUpdatePolicyMinInstancesInService', asg_config.update_policy_min_instances_in_service)

        # Segment SubnetList is a Segment stack Output based on availability zones
        subnet_list_output_key = 'SubnetList' + str(self.env_ctx.availability_zones())
        self.set_parameter(StackOutputParam('ASGSubnetList', segment_stack, subnet_list_output_key))

        # Load Balancers: A list of aim.ref netenv.to ELBs
        if asg_config.load_balancers != None and len(asg_config.load_balancers) > 0:
            lb_param = StackOutputParam('ASGLoadBalancerNames')
            for load_balancer in asg_config.load_balancers:
                elb_stack = self.aim_ctx.get_ref(load_balancer)
                elb_output_key = self.get_stack_outputs_key_from_ref(Reference(load_balancer))
                lb_param.add_stack_output(elb_stack, elb_output_key)
            self.set_parameter(lb_param)

        # Target Group Arns
        if asg_config.target_groups != None and len(asg_config.target_groups) > 0:
            lb_param = StackOutputParam('TargetGroupArns')
            for target_group_arn in asg_config.target_groups:
                alb_stack = self.aim_ctx.get_ref(target_group_arn)
                alb_output_key = self.get_stack_outputs_key_from_ref(Reference(target_group_arn))
                lb_param.add_stack_output(alb_stack, alb_output_key)
            self.set_parameter(lb_param)

        if asg_config.user_data_script != '':
            user_data_script = ec2_manager_user_data_script
            user_data_script += asg_config.user_data_script.replace('#!/bin/bash', '')
            user_data_64 = base64.b64encode(user_data_script.encode('ascii'))
            self.set_parameter('UserDataScript', user_data_64.decode('ascii'))

        enable_metrics_collection = False
        if asg_config.monitoring != None and asg_config.monitoring.enabled == True and len(asg_config.monitoring.asg_metrics) > 0:
            enable_metrics_collection = True
            self.set_parameter('MetricsCollectionList', asg_config.monitoring.asg_metrics)
        self.set_parameter('EnableMetricsCollection', enable_metrics_collection)

        # Scale in/out policies
        if asg_config.scaling_policy_cpu_average > 0:
          self.set_parameter('CPUAverageScalingEnabled', True)
          self.set_parameter('CPUAverageScalingTargetValue', asg_config.scaling_policy_cpu_average)
        else:
          self.set_parameter('CPUAverageScalingEnabled', False)

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ASG: Auto Scaling Group and Launch Configuration'

# EC2 Manager Cache ID: %s

Parameters:
  LCEBSOptimized:
    Description: 'Boolean to toggle Optimized EBS I/O.'
    Type: String
    AllowedValues:
      - true
      - false

  LCInstanceAMI:
    Description: 'The Amazon Machine Image Id to raise instances with.'
    Type: AWS::EC2::Image::Id

  LCInstanceType:
    Description: 'The compute type for EC2 instances'
    Type: String

  LCInstanceMonitoring:
    Description: 'Boolean to toggle detailed instance montoring.'
    Type: String
    AllowedValues:
      - true
      - false

  LCInstanceAMI:
    Description: 'AMI Id to launch instances with.'
    Type: String

  LCInstanceKeyPair:
    Description: SSH Keypair to use for the instances created by the ASG
    Type: AWS::EC2::KeyPair::KeyName

  LCAssociatePublicIpAddress:
    Description: Set to True if you wish the instances in the ASG to have a public IP.
    Type: String

  LCIamInstanceProfile:
    Description: 'The IAM Role to attach to instances'
    Type: String
    Default: ""

  LCSecurityGroupList:
    Description: 'A list of Security Groups Ids'
    Type: List<AWS::EC2::SecurityGroup::Id>

  ASGName:
    Description: 'The name of the Auto Scaling Group'
    Type: String

  ASGDesiredCapacity:
    Description: 'The default number of instances to have running'
    Type: Number

  ASGHealthCheckGracePeriodSecs:
    Description: 'The amount of time after the ASG launches a new instance beacuse it begins checking its health.'
    Type: Number

  ASGHealthCheckType:
    Description: 'Where the ASG will query its status from. ELB or EC2'
    Type: String
    AllowedValues:
      - ELB
      - EC2

  ASGMaxSize:
    Description: 'The maximum number of instances the ASG will have running at any time.'
    Type: Number

  ASGMinSize:
    Description: 'The minimum number of instances the ASG will have running at any time.'
    Type: Number

  ASGCooldownSecs:
    Description: 'The amount of time after a scaling activity before any new activities will start.'
    Type: Number

  ASGTerminationPolicies:
    Description: 'ASG Termination Policy'
    Type: List<String>

  ASGUpdatePolicyMaxBatchSize:
    Description: Specifies the maximum number of instances that AWS CloudFormation updates at a time.
    Type: Number

  ASGUpdatePolicyMinInstancesInService:
    Description: 'The minimum number of instances the ASG must have during an update.'
    Type: Number

  ASGSubnetList:
    Description: 'A list of subnets where the ASG will launch instances'
    Type: List<AWS::EC2::Subnet::Id>

  ASGLoadBalancerNames:
    Description: 'A list of load balancer names to attach to the ASG'
    Type: List<String>
    Default: ""

  TargetGroupArns:
    Description: 'A list of Target Group ARNs to attach to the ASG'
    Type: List<String>
    Default: ""

  UserDataScript:
    Description: 'User Data script'
    Type: String

  EnableMetricsCollection:
    Description: 'Boolean indicating whether Group Metrics collection is enabled.'
    Type: String
    AllowedValues:
      - true
      - false

  MetricsCollectionList:
    Description: 'A list of ASG Metrics to collection'
    Type: List<String>
    Default: AWS::NoValue

  CPUAverageScalingEnabled:
    Description: 'A boolean indicating whether the ASG will scale based on CPU load'
    Type: String
    Default: false
    AllowedValues:
      - true
      - false

  CPUAverageScalingTargetValue:
    Description: 'An integer representing the average CPU percent load of the ASG threshold for scaling'
    Type: String
    Default: 0

Conditions:
  MetricsCollectionEnabled: !Equals [!Ref EnableMetricsCollection, "true" ]
  LoadBalancersExist: !Not [!Equals [!Join [',', !Ref ASGLoadBalancerNames], "" ]]
  TargetGroupArnsExist: !Not [!Equals [!Join [',', !Ref TargetGroupArns], "" ]]
  InstanceProfileExists: !Not [!Equals [!Ref LCIamInstanceProfile, "" ]]
  IsCPUAverageScalingEnabled: !Equals [!Ref CPUAverageScalingEnabled, "true" ]

Resources:

  LaunchConfiguration:
    Type: AWS::AutoScaling::LaunchConfiguration
    Properties:
      AssociatePublicIpAddress: !Ref LCAssociatePublicIpAddress
      EbsOptimized: !Ref LCEBSOptimized
      ImageId: !Ref LCInstanceAMI
      InstanceMonitoring: !Ref LCInstanceMonitoring
      InstanceType: !Ref LCInstanceType
      KeyName: !Ref LCInstanceKeyPair
      IamInstanceProfile:
        !If
          - InstanceProfileExists
          - !Ref LCIamInstanceProfile
          - !Ref AWS::NoValue
      SecurityGroups: !Ref LCSecurityGroupList
      UserData: !Ref UserDataScript

  ASG:
    Type: AWS::AutoScaling::AutoScalingGroup
    DependsOn: LaunchConfiguration
    Properties:
      AutoScalingGroupName: !Ref ASGName
      DesiredCapacity: !Ref ASGDesiredCapacity
      HealthCheckGracePeriod: !Ref ASGHealthCheckGracePeriodSecs
      LaunchConfigurationName: !Ref LaunchConfiguration
      MaxSize: !Ref ASGMaxSize
      MinSize: !Ref ASGMinSize
      Cooldown: !Ref ASGCooldownSecs
      HealthCheckType: !Ref ASGHealthCheckType
      TerminationPolicies: !Ref ASGTerminationPolicies
      VPCZoneIdentifier: !Ref ASGSubnetList
      LoadBalancerNames:
        !If
          - LoadBalancersExist
          - !Ref ASGLoadBalancerNames
          - !Ref AWS::NoValue
      TargetGroupARNs:
        !If
          - TargetGroupArnsExist
          - !Ref TargetGroupArns
          - !Ref AWS::NoValue
      MetricsCollection:
        - !If
          - MetricsCollectionEnabled
          - Granularity: 1Minute  # 1Minute is the only valid value
            Metrics: !Ref MetricsCollectionList
          - !Ref AWS::NoValue
      Tags:
        - Key: Name
          Value: !Ref ASGName
          PropagateAtLaunch: true
    UpdatePolicy:
      AutoScalingRollingUpdate:
        MaxBatchSize: !Ref ASGUpdatePolicyMaxBatchSize
        MinInstancesInService: !Ref ASGUpdatePolicyMinInstancesInService

  CPUAverageScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Condition: IsCPUAverageScalingEnabled
    Properties:
      AutoScalingGroupName: !Ref ASG
      PolicyType: TargetTrackingScaling
      TargetTrackingConfiguration:
        PredefinedMetricSpecification:
          PredefinedMetricType: ASGAverageCPUUtilization
        TargetValue: !Ref CPUAverageScalingTargetValue

Outputs:
  ASGName:
    Value: !Ref ASG
""" % self.ec2_manager_cache_id
        self.register_stack_output_config(asg_config_ref, 'ASGName')

        asg_table = {
            'load_balancer_names': '!Ref AWS::NoValue',
            'target_group_arns': '!Ref AWS::NoValue'
        }
        #if asg_config.load_balancers != None:
        #    asg_table['load_balancer_names'] = "!Ref ASGLoadBalancerNames"
        #if asg_config.target_groups != None:
        #    asg_table['target_group_arns'] = "!Ref TargetGroupArns"

        self.set_template(template_fmt.format(asg_table))

    def validate(self):
        #self.aim_ctx.log("Validating ASG Template")
        super().validate()

    def get_outputs_key_from_ref(self, ref):
        # There is only one output key
        return "ASGName"
