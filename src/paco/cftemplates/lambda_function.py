from paco.cftemplates.cftemplates import CFTemplate
from paco.models.locations import get_parent_by_interface
from paco.models.loader import get_all_nodes
from paco.models.references import resolve_ref, get_model_obj_from_ref, Reference
from paco.models import schemas
from paco.utils import hash_smaller
from io import StringIO
from enum import Enum
import os



class Lambda(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        grp_id,
        res_id,
        lambda_config,
        lambda_config_ref
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=lambda_config_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            enabled=lambda_config.is_enabled()
        )
        self.set_aws_name('Lambda', grp_id, res_id)
        self.set_parameter('FunctionDescription', lambda_config.description)
        self.set_parameter('Handler', lambda_config.handler)
        self.set_parameter('Runtime', lambda_config.runtime)
        self.set_parameter('RoleArn', lambda_config.iam_role.get_arn())
        self.set_parameter('RoleName', lambda_config.iam_role.resolve_ref_obj.role_name)
        self.set_parameter('MemorySize', lambda_config.memory_size)
        self.set_parameter('ReservedConcurrentExecutions', lambda_config.reserved_concurrent_executions)
        self.set_parameter('Timeout', lambda_config.timeout)
        self.set_parameter('EnableSDBCache', lambda_config.sdb_cache)

        # Code object: S3 Bucket or inline ZipFile?
        s3_code = ""
        code_resource = ""
        if lambda_config.code.s3_bucket:
            if lambda_config.code.s3_bucket.startswith('paco.ref '):
                self.set_parameter('CodeS3Bucket', lambda_config.code.s3_bucket + ".name")
            else:
                self.set_parameter('CodeS3Bucket', lambda_config.code.s3_bucket)
            self.set_parameter('CodeS3Key', lambda_config.code.s3_key)
            code_resource = """
        S3Bucket: !Ref CodeS3Bucket
        S3Key: !Ref CodeS3Key
"""
            s3_code = """
  CodeS3Bucket:
    Description: "An Amazon S3 bucket in the same AWS Region as your function. The bucket can be in a different AWS account."
    Type: String

  CodeS3Key:
    Description: "The Amazon S3 key of the deployment package."
    Type: String
"""
        else:
            padding = "          "
            code_resource = """
        ZipFile: |
"""
            for line in lambda_config.code.zipfile.split('\n'):
                code_resource += padding + line + '\n'

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lambda Function'

Parameters:
  FunctionDescription:
    Description: "A description of the Lamdba Function."
    Type: String

  Handler:
    Description: "The name of the function to call upon execution."
    Type: String

  Runtime:
    Description: "The name of the runtime language."
    Type: String

  RoleArn:
    Description: "The execution role for the Lambda Function."
    Type: String

  RoleName:
    Description: "The execution role name for the Lambda Function."
    Type: String

  MemorySize:
    Description: "The amount of memory that your function has access to. Increasing the function's memory also increases its CPU allocation. The default value is 128 MB. The value must be a multiple of 64 MB."
    Type: Number

  ReservedConcurrentExecutions:
    Description: "The number of simultaneous executions to reserve for the function."
    Type: Number
    Default: 0

  Timeout:
    Description: "The amount of time that Lambda allows a function to run before stopping it. "
    Type: Number
{0[s3_code]:s}

  EnableSDBCache:
    Description: "Boolean indicating whether an SDB Domain will be created to be used as a cache."
    Type: String

  Layers:
    Description: "List of up to 5 Lambda Layer ARNs."
    Type: CommaDelimitedList
    Default: ""

{0[parameters]:s}

Conditions:
  ReservedConcurrentExecutionsIsEnabled: !Not [!Equals [!Ref ReservedConcurrentExecutions, 0]]
  SDBCacheIsEnabled: !Equals [!Ref EnableSDBCache, 'true']
  LayersExist: !Not [!Equals [!Join ["", !Ref Layers], ""]]

Resources:

# Dependency Tree
#
# InvokePolicy
# FunctionSQSQueue
#
# FunctionSQSMapping
#   - FunctionSQSQueue
#   - Function
#     - LambdaSDBCacheDomain
#     - SQSExecutionPolicy
#        - FunctionSQSQueue
#     - SSMExecutionPolicy
#        - InvokePolicyParam
#          - InvokePolicy
#
# FunctionSQSQueue
#
# FunctionSQSMapping
#   - Function
#   - FunctionSQSQueue
#
# InvokePolicyParam
#   - InvokePolicy
#
# SSMExecutionPolicy
#   - InvokePolicyParam

  LambdaSDBCacheDomain:
    Type: AWS::SDB::Domain
    Condition: SDBCacheIsEnabled
    Properties:
      Description: "Lambda Function Domain"

  LambdaSDBCacheDomainPolicy:
      Type: AWS::IAM::Policy
      Condition: SDBCacheIsEnabled
      DependsOn:
        - LambdaSDBCacheDomain
      Properties:
        PolicyName: 'SDBDomain'
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Effect: Allow
              Action:
                - sdb:*
              Resource: !Sub
                - arn:aws:sdb:${{AWS::Region}}:${{AWS::AccountId}}:domain/${{DomainName}}
                - {{ DomainName: !Ref LambdaSDBCacheDomain}}
        Roles:
          - !Ref RoleName

  Function:
    Type: AWS::Lambda::Function
    DependsOn:
      - SQSExecutionPolicy
{0[sdb_dependency]:s}
    Properties:
      # Important: If you specify a name, you cannot perform updates that require
      # replacement of this resource. You can perform updates that require no or
      # some interruption. If you must replace the resource, specify a new name.
      # FunctionName: # We will allow CloudFormation to choose the name as it will
      #                 already be based on the stack name.
      Code:
{0[code_resource]:s}
      Handler: !Ref Handler
      Role: !Ref RoleArn
      Runtime: !Ref Runtime
      MemorySize: !Ref MemorySize
      ReservedConcurrentExecutions:
        !If
          - ReservedConcurrentExecutionsIsEnabled
          - !Ref ReservedConcurrentExecutions
          - !Ref AWS::NoValue
      Timeout: !Ref Timeout{0[environment]:s}
      Layers:
        !If
          - LayersExist
          - !Ref Layers
          - !Ref AWS::NoValue
{0[vpc_config]:s}

  InvokePolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action: lambda:InvokeFunction
            Resource: !GetAtt Function.Arn

  FunctionSQSQueue:
    Type: AWS::SQS::Queue
    Properties:
      # Not specifying a name allows CloudFormation to recreate this
      # resource if needed.
      QueueName: !Sub '${{AWS::StackName}}'
      #FifoQueue: True
      VisibilityTimeout: !Ref Timeout

  FunctionSQSMapping:
    Type: AWS::Lambda::EventSourceMapping
    DependsOn:
      - Function
      - FunctionSQSQueue
    Properties:
      EventSourceArn: !GetAtt FunctionSQSQueue.Arn
      FunctionName: !GetAtt Function.Arn
      BatchSize: 1

  InvokePolicyParam:
    Type: "AWS::SSM::Parameter"
    DependsOn:
      - InvokePolicy
    Properties:
      Name: !Sub '${{AWS::StackName}}-InvokePolicy'
      Type: String
      Value: !Ref InvokePolicy
      Tier: Standard
      Description: "Stores a Lambda functions InvokePolicy Arn"

  SSMExecutionPolicy:
      Type: AWS::IAM::Policy
      DependsOn:
        - InvokePolicyParam
      Properties:
        PolicyName: 'SSMPolicy'
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Sid: SSMParameter
              Effect: Allow
              Action:
                - ssm:GetParameter
                - ssm:GetParameters
              Resource: !Sub
                - arn:aws:ssm:${{AWS::Region}}:${{AWS::AccountId}}:parameter/${{ParamName}}
                - {{ ParamName: !Ref InvokePolicyParam }}
        Roles:
          - !Ref RoleName

  SQSExecutionPolicy:
      Type: AWS::IAM::Policy
      DependsOn:
        - FunctionSQSQueue
      Properties:
        PolicyName: 'SQSPolicy'
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Sid: SQSQueue
              Effect: Allow
              Action:
                - sqs:ReceiveMessage
                - sqs:DeleteMessage
                - sqs:GetQueueAttributes
              Resource: !GetAtt FunctionSQSQueue.Arn
        Roles:
          - !Ref RoleName

{0[permissions]:s}

Outputs:
    FunctionName:
      Value: !Ref Function

    FunctionArn:
      Value: !GetAtt Function.Arn

    InvokePolicyArn:
      Value: !Ref InvokePolicy
"""
        self.register_stack_output_config(lambda_config_ref+'.name', 'FunctionName')
        self.register_stack_output_config(lambda_config_ref+'.arn', 'FunctionArn')
        self.register_stack_output_config(lambda_config_ref+'.invoke_policy.arn', 'InvokePolicyArn')

        if lambda_config.sdb_cache:
          sdb_dependency = "      - LambdaSDBCacheDomain\n"
        else:
          sdb_dependency = ""
        template_table = {
            'parameters': "",
            'environment': "",
            'outputs': "",
            'sdb_dependency': sdb_dependency,
            'permissions': "",
            's3_code': s3_code,
            'code_resource': code_resource
        }

        env_header = """
      Environment:"""
        vars_header = """
        Variables:"""
        var_fmt = """
          {0[key]:s}: !Ref EnvVar{0[param_key]:s}
"""
        var_raw_fmt = """          {0[key]:s}: {0[value]:s}
"""
        var_param_fmt = """
  EnvVar{0[param_key]:s}:
    Description: 'An environment variable: {0[key]:s} = {0[value]:s}.'
    Type: String
"""
        var_table = {
          'param_key': '',
          'key': '',
          'value': ''
        }

        permission_fmt = """
  {0[name]:s}Permission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: "lambda:InvokeFunction"
      FunctionName: !GetAtt Function.Arn
      Principal: {0[principal]:s}
      SourceArn: {0[source_arn]:s}
"""

        permission_table = {
          'name': None,
          'principal': None,
          'source_arn': None
        }

        sns_subscription_fmt = """
  {0[name]:s}Subscription:
    Type: AWS::SNS::Subscription
    Properties:
      Endpoint: !GetAtt Function.Arn
      Protocol: lambda
      TopicArn: {0[topic_arn]:s}
      Region: {0[topic_region]:s}
"""

        sns_subscription_table = {
          'name': None,
          'topic_arn': None,
          'topic_region': '',
        }

        parameters_yaml = ""
        env_yaml = ""
        env_config = lambda_config.environment
        variables_exist = False
        if env_config != None and env_config.variables != None:
            variables_exist = True
        if lambda_config.sdb_cache == True:
            variables_exist = True


        if variables_exist:
            env_yaml += vars_header
            if env_config != None and env_config.variables != None:
                for env in env_config.variables:
                    var_table['param_key'] = env.key.replace('_','')
                    var_table['key'] = env.key
                    var_table['value'] = env.value
                    parameters_yaml += var_param_fmt.format(var_table)
                    env_yaml += var_fmt.format(var_table)
                    self.set_parameter('EnvVar%s' % (var_table['param_key']), var_table['value'])
            if lambda_config.sdb_cache == True:
                var_table['key'] = 'SDB_CACHE_DOMAIN'
                var_table['value'] = '!Ref LambdaSDBCacheDomain'
                env_yaml += var_raw_fmt.format(var_table)

        if env_yaml != "":
          template_table['environment'] = env_header + env_yaml

        template_table['permissions'] = ""
        # SNS Topic Permissions and Subscription
        idx = 1

        for sns_topic_ref in lambda_config.sns_topics:
            # SNS Topic Arn parameters
            param_name = 'SNSTopicArn%d' % idx
            parameters_yaml += self.create_cfn_parameter(
                param_type = 'String',
                name = param_name,
                description = 'An SNS Topic ARN to grant permission to.',
                value = sns_topic_ref + '.arn'
            )
            # Lambda Permissions
            permission_table['name'] = param_name
            permission_table['principal'] = 'sns.amazonaws.com'
            permission_table['source_arn'] = '!Ref %s' % param_name
            template_table['permissions'] += permission_fmt.format(permission_table)
            # SNS Topic Subscription
            sns_subscription_table['name'] = param_name
            sns_subscription_table['topic_arn'] = '!Ref %s' % param_name
            sns_topic = get_model_obj_from_ref(sns_topic_ref, self.paco_ctx.project)
            sns_subscription_table['topic_region'] = sns_topic.region_name
            template_table['permissions'] += sns_subscription_fmt.format(sns_subscription_table)
            idx += 1

        # S3 Bucket notification permission(s)
        app = get_parent_by_interface(lambda_config, schemas.IApplication)
        # detect if an S3Bucket resource in the application is configured to notify the Lambda
        for obj in get_all_nodes(app):
            if schemas.IS3Bucket.providedBy(obj):
                seen = {}
                if hasattr(obj, 'notifications'):
                    if hasattr(obj.notifications, 'lambdas'):
                        for lambda_notif in obj.notifications.lambdas:
                            if lambda_notif.function == lambda_config.paco_ref:
                                # yes, this Lambda gets notification from this S3Bucket
                                group = get_parent_by_interface(obj, schemas.IResourceGroup)
                                s3_logical_name = self.gen_cf_logical_name(group.name + obj.name, '_')
                                if s3_logical_name not in seen:
                                    permission_table['name'] = 'S3Bucket' + s3_logical_name
                                    permission_table['principal'] = 's3.amazonaws.com'
                                    permission_table['source_arn'] = 'arn:aws:s3:::' + obj.get_bucket_name()
                                    template_table['permissions'] += permission_fmt.format(permission_table)
                                    seen[s3_logical_name] = True

        # Events Rule permission(s)
        for obj in get_all_nodes(app):
            if schemas.IEventsRule.providedBy(obj):
                seen = {}
                for target in obj.targets:
                    target_ref = Reference(target)
                    target_ref.set_account_name(self.account_ctx.get_name())
                    target_ref.set_region(aws_region)
                    lambda_ref = Reference(lambda_config.paco_ref)

                    if target_ref.raw == lambda_ref.raw:
                        # yes, the Events Rule has a Target that is this Lambda
                        group = get_parent_by_interface(obj, schemas.IResourceGroup)
                        eventsrule_logical_name = self.gen_cf_logical_name(group.name + obj.name, '_')
                        if eventsrule_logical_name not in seen:
                            permission_table['name'] = 'EventsRule' + eventsrule_logical_name
                            permission_table['principal'] = 'events.amazonaws.com'
                            rule_name = self.create_cfn_logical_id("EventsRule" + obj.paco_ref)
                            rule_name = hash_smaller(rule_name, 64)
                            permission_table['source_arn'] = 'arn:aws:events:{}:{}:rule/{}'.format(
                                aws_region,
                                account_ctx.id,
                                rule_name
                            )
                            template_table['permissions'] += permission_fmt.format(permission_table)
                            seen[eventsrule_logical_name] = True

        # VPC Config
        template_table['vpc_config'] = ""
        if lambda_config.vpc_config != None:
            template_table['vpc_config'] += """
      VpcConfig:
        SecurityGroupIds: !Ref VpcSecurityGroupIdList
        SubnetIds: !Ref VpcSubnetIdList"""
            # Segment SubnetList is a Segment stack Output based on availability zones
            ref = Reference('paco.ref '+lambda_config_ref)

            segment_ref = lambda_config.vpc_config.segments[0] + '.subnet_id_list'
            parameters_yaml += self.create_cfn_parameter('List<AWS::EC2::Subnet::Id>', 'VpcSubnetIdList', 'VPC Subnet Id List', segment_ref)
            #self.set_parameter(StackOutputParam('SubnetList', segment_stack, subnet_list_key, self))

            #self.set_list_parameter('VpcSecurityGroupIdList', lambda_config.vpc_config.security_groups, 'id')
            parameters_yaml += self.create_cfn_ref_list_param(
                'List<AWS::EC2::SecurityGroup::Id>',
                'VpcSecurityGroupIdList',
                'VPC Security Group Id List',
                lambda_config.vpc_config.security_groups,
                'id')

        template_table['parameters'] = parameters_yaml

        self.set_template(template_fmt.format(template_table))


