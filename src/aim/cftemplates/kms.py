import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class KMS(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 aws_name,
                 kms_config_ref,
                 kms_config_dict):

        #aim_ctx.log("S3 CF Template init")
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=kms_config_ref,
                         aws_name='-'.join(["KMS", aws_name]),
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'

Description: KMS Customer Managed Key

#Parameters:

Resources:
  CMK:
    Type: AWS::KMS::Key
    Properties:
      Description: AIM Generic KMS Customer Managed Key
      EnableKeyRotation: true
      KeyPolicy:
        Version: "2012-10-17"
        Id: !Ref AWS::StackName
        Statement:
          - Sid: Allows admin of the key
            Effect: Allow
            Principal:
              AWS:
                - !Sub 'arn:aws:iam::${{AWS::AccountId}}:root'
            Action:
              - "kms:Create*"
              - "kms:Describe*"
              - "kms:Enable*"
              - "kms:List*"
              - "kms:Put*"
              - "kms:Update*"
              - "kms:Revoke*"
              - "kms:Disable*"
              - "kms:Get*"
              - "kms:Delete*"
              - "kms:ScheduleKeyDeletion"
              - "kms:CancelKeyDeletion"
            Resource: "*"
          - Sid: Allow use of the key for CryptoGraphy Lambda
            Effect: Allow
            Principal: {0[key_policy_principal]:s}
            Action:
              - kms:Encrypt
              - kms:Decrypt
              - kms:ReEncrypt*
              - kms:GenerateDataKey*
              - kms:DescribeKey
            Resource: "*"

#  KMSAlias:
#    Type: AWS::KMS::Alias
#    Properties:
#      AliasName: alias/codepipeline-crossaccounts
#      TargetKeyId: !Ref CMK

Outputs:
  CMK:
    Value: !GetAtt CMK.Arn

"""


        principal_yaml = """
              AWS:"""
        for aws_principal in kms_config_dict['crypto_principal']['aws']:
            principal_yaml += """
                - '{0}'""".format(aws_principal)

        template_table = {
            'key_policy_principal': principal_yaml
        }

        self.set_template(template_fmt.format(template_table))


    def validate(self):
        #self.aim_ctx.log("Validating CodeDeploy Template")
        super().validate()

    def get_outputs_key_from_ref(self, aim_ref):
        return "CMK"
