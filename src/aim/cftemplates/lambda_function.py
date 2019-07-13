import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum

class Lambda(CFTemplate):
    def __init__(self, aim_ctx, account_ctx, aws_name, lambda_config, lambda_config_ref):
        #aim_ctx.log("Lambda CF Template init")
        aws_name += '-Lambda'

        super().__init__(aim_ctx,
                         account_ctx,
                         config_ref=None,
                         aws_name=aws_name,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

        self.set_parameter('FunctionDescription', lambda_config.description)
        self.set_parameter('Handler', lambda_config.handler)
        self.set_parameter('Runtime', lambda_config.runtime)
        self.set_parameter('RoleArn', lambda_config.iam_role.get_arn())
        self.set_parameter('MemorySize', lambda_config.memory_size)
        self.set_parameter('ReservedConcurrentExecutions', lambda_config.reserved_concurrent_executions)
        self.set_parameter('Timeout', lambda_config.timeout)

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

  CodeS3Bucket:
    Description: "An Amazon S3 bucket in the same AWS Region as your function. The bucket can be in a different AWS account."
    Type: String

  CodeS3Key:
    Description: "The Amazon S3 key of the deployment package."
    Type: String

{0[parameters]:s}

Resources:
  Function:
    Type: AWS::Lambda::Function
    Properties:
      # Important: If you specify a name, you cannot perform updates that require
      # replacement of this resource. You can perform updates that require no or
      # some interruption. If you must replace the resource, specify a new name.
      # FunctionName: # We will allow CloudFormation to choose the name as it will
      #                 already be based on the stack name.
      Code:
        S3Bucket: !Ref CodeS3Bucket
        S3Key: !Ref CodeS3Key
      Handler: !Ref Handler
      Role: !Ref RoleArn
      Runtime: !Ref Runtime
      MemorySize: !Ref MemorySize
      ReservedConcurrentExecutions: !Ref ReservedConcurrentExecutions
      Timeout: !Ref Timeout{0[environment]:s}

  #Permission:
  #  Type: AWS::Lambda::Permission
  #  Properties:
  #    Action: "lambda:InvokeFunction"
  #    FunctionName: !GetAtt Function.Arn
  #    Principal: events.amazonaws.com

Outputs:
    FunctionName:
      Value: !Ref Function

    FunctionArn:
      Value: !GetAtt Function.Arn
"""
        self.register_stack_output_config(lambda_config_ref+'.name', 'FunctionName')
        self.register_stack_output_config(lambda_config_ref+'.arn', 'FunctionArn')

        template_table = {
            'parameters': "",
            'environment': "",
            'outputs': ""
        }

        env_header = """
      Environment:"""
        vars_header = """
        Variables:"""
        var_fmt = """
          {0[key]:s}: !Ref EnvVar{0[key]:s}
"""
        var_param_fmt = """
  EnvVar{0[key]:s}:
    Description: 'An environment variable: {0[key]:s} = {0[value]:s}.'
    Type: String
"""
        var_table = {
          'key': '',
          'value': ''
        }

        parameters_yaml = ""
        env_yaml = ""
        env_config = lambda_config.environment
        if env_config != None:
            if env_config.variables != None:
                if len(env_config.variables) > 0:
                    env_yaml += vars_header
                for env in env_config.variables:
                    var_table['key'] = env.key
                    var_table['value'] = env.value
                    parameters_yaml += var_param_fmt.format(var_table)
                    env_yaml += var_fmt.format(var_table)
                    self.set_parameter('EnvVar%s' %(env.key), env.value)

        if env_yaml != "":
          template_table['environment'] = env_header + env_yaml

        template_table['parameters'] = parameters_yaml

        self.set_template(template_fmt.format(template_table))

    def get_outputs_key_from_ref(self, ref):
       pass
