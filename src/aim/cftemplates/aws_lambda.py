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

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Lambda Function'

Parameters:
  FunctionHandler:
    Description: "The name of the function to call upon execution."
    Type: String

  # https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
  Runtime:
    Description: "The name of the runtime language."
    Type: String

{0[parameters]:s}

Resources:
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: {0[role_name]:s}
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - lambda.amazonaws.com
            Action: sts:AssumeRole

  Function:
    Type: AWS::Lambda::Function
    Properties:
      # Important: If you specify a name, you cannot perform updates that require
      # replacement of this resource. You can perform updates that require no or
      # some interruption. If you must replace the resource, specify a new name.
      # FunctionName: # We will allow CloudFormation to choose the name as it will
      #                 already be based on the stack name.
      Code:
        ZipFile: !Sub |
          # Placeholder Function
          import logger
          logger = logging.getLogger()
          logger.setLevel(logging.DEBUG)
          def lambda_handler(event, context):
              logger.error("Lambda source placeholder.")
      Handler: !Ref FunctionHandler
      Role: !GetAtt LambdaRole.Arn
      Runtime: !Ref Runtime
{0[environment]:s}

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
          {0[key]:s}: !Ref EnvVar{0[value]:s}
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
        outputs_yaml = ""
        env_yaml = ""
        env_config = lambda_config.environment
        if env_config != None:
            if env_config.variables != None:
                if len(env_config.variables) > 0:
                    env_yaml += vars_header
                for env in env_config.variabels:
                    var_table['key'] = env.key
                    var_table['value'] = env.value
                    parameters_yaml += var_param_fmt.format(var_table)
                    env_yaml += var_fmt.format(var_table)

        if env_yaml != "":
          template_table['environment'] = env_header + env_yaml

        template_table['parameters'] = parameters_yaml

        self.set_template(template_fmt.format(template_table))

    def get_outputs_key_from_ref(self, ref):
       pass
