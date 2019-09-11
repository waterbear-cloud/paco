import os
from aim.cftemplates.cftemplates import CFTemplate

from io import StringIO
from enum import Enum
import base64
from aim.models import vocabulary


class LambdaPermission(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 function_name,
                 principal,
                 source_account,
                 source_arn,
                 config_ref):

        #aim_ctx.log("CLoudWatch Alarms CF Template init")
        # Super Init:
        aws_name='-'.join(['LambdaPermission'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )

        # Initialize Parameters
        if source_arn == None:
          source_arn = ''
        if source_account == None:
          source_account = ''

        self.set_parameter('FunctionName', function_name)
        self.set_parameter('Principal', principal)
        self.set_parameter('SourceAccount', source_account)
        self.set_parameter('SourceArn', source_arn)

        # TOOD: Template needs Scale in/out policies

        # Define the Template
        template_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CloudWatch EventRule'

Parameters:

  FunctionName:
    Description: "The name of the Lambda function, version, or alias."
    Type: String

  Principal:
    Description: "The AWS service or account that invokes the function."
    Type: String

  SourceAccount:
    Description: "For AWS services, the ID of the account that owns the resource. Use this instead of SourceArn to grant permission to resources that are owned by another account."
    Type: String

  SourceArn:
    Description: "For AWS services, the ARN of the AWS resource that invokes the function."
    Type: String

Conditions:

  UseSourceAccount: !Not [!Equals [!Ref SourceAccount, '']]
  UseSourceArn: !Not [!Equals [!Ref SourceArn, '']]

Resources:

  LambdaInvokePermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref FunctionName
      Action: 'lambda:InvokeFunction'
      Principal: !Ref Principal
      SourceAccount: !If [UseSourceAccount, !Ref SourceAccount, !Ref 'AWS::NoValue']
      SourceArn: !If [UseSourceArn, !Ref SourceArn, !Ref 'AWS::NoValue']

#Outputs:

"""

        self.set_template(template_yaml)

