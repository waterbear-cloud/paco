from awacs.aws import Allow, Deny, Action, Principal, Statement, PolicyDocument, Condition, Null, StringLike
from awacs.aws import Bool as AWACSBool
from paco.cftemplates.cftemplates import StackTemplate
from paco.models.references import get_model_obj_from_ref, is_ref
import troposphere.kms
import awacs.kms

class KMS(StackTemplate):
    def __init__(
      self,
      stack,
      paco_ctx,
      kms_config_dict=None, # config for DeploymentPipeline
      cloudtrail=None # config for CloudTrail
    ):
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('KMS', self.resource_group_name, self.resource.name)

        if cloudtrail != None:
          self.cloudtrail_template(cloudtrail)
        elif kms_config_dict != None:
          self.deployment_pipeline_template(kms_config_dict)

    def cloudtrail_template(self, cloudtrail):
        "Template for CloudTrail"
        # Troposphere Template Initialization
        self.init_template(f'KMS Customer Managed Key (CMK) for CloudTrail')
        users = []
        for user in cloudtrail.kms_users:
            if is_ref(user):
                user_obj = get_model_obj_from_ref(user, self.paco_ctx.project)
                user = user_obj.username
            users.append(
                f"arn:aws:iam::{self.paco_ctx.project['accounts']['master'].account_id}:user/{user}"
            )
        accounts = [
            f"arn:aws:cloudtrail:*:{account.account_id}:trail/*" for account in cloudtrail.get_accounts()
        ]
        cloudtrail_policy = PolicyDocument(
            Version='2012-10-17',
            Statement=[
                Statement(
                    Sid="Allows admin of the key",
                    Effect=Allow,
                    Principal=Principal("AWS", [f'arn:aws:iam::{self.stack.account_ctx.id}:root']),
                    Action=[
                        awacs.kms.CreateAlias,
                        awacs.kms.CreateCustomKeyStore,
                        awacs.kms.CreateGrant,
                        awacs.kms.CreateKey,
                        awacs.kms.DescribeCustomKeyStores,
                        awacs.kms.DescribeKey,
                        awacs.kms.EnableKey,
                        awacs.kms.EnableKeyRotation,
                        awacs.kms.ListAliases,
                        awacs.kms.ListGrants,
                        awacs.kms.ListKeyPolicies,
                        awacs.kms.ListKeys,
                        awacs.kms.ListResourceTags,
                        awacs.kms.ListRetirableGrants,
                        awacs.kms.PutKeyPolicy,
                        awacs.kms.UpdateAlias,
                        awacs.kms.UpdateCustomKeyStore,
                        awacs.kms.UpdateKeyDescription,
                        awacs.kms.RevokeGrant,
                        awacs.kms.DisableKey,
                        awacs.kms.DisableKeyRotation,
                        awacs.kms.GetKeyPolicy,
                        awacs.kms.GetKeyRotationStatus,
                        awacs.kms.GetParametersForImport,
                        awacs.kms.DeleteAlias,
                        awacs.kms.DeleteCustomKeyStore,
                        awacs.kms.DeleteImportedKeyMaterial,
                        awacs.kms.ScheduleKeyDeletion,
                        awacs.kms.CancelKeyDeletion,
                        awacs.kms.TagResource
                    ],
                    Resource=['*'],
                ),
                Statement(
                    Sid="Allow CloudTrail access",
                    Effect=Allow,
                    Principal=Principal("Service", ['cloudtrail.amazonaws.com']),
                    Action=[awacs.kms.DescribeKey],
                    Resource=['*'],
                ),
                Statement(
                    Sid="Allow CloudTrail log decrypt permissions",
                    Effect=Allow,
                    Action=[awacs.kms.Decrypt],
                    Principal=Principal("AWS", users),
                    Resource=['*'],
                    Condition=Condition(
                        [ Null( {"kms:EncryptionContext:aws:cloudtrail:arn": False} ) ]
                    )
                ),
                Statement(
                    Sid="Allow CloudTrail to encrypt logs",
                    Effect=Allow,
                    Principal=Principal("Service", ["cloudtrail.amazonaws.com"]),
                    Action=[awacs.kms.GenerateDataKey],
                    Resource=['*'],
                    Condition=Condition([
                        StringLike({
                            "kms:EncryptionContext:aws:cloudtrail:arn": accounts
                        })
                    ])
                ),
            ]
        )
        kms_dict = {
            'Description': 'CMK for CloudTrail',
            'EnableKeyRotation': True,
            'KeyPolicy': cloudtrail_policy,
        }
        kms_res = troposphere.kms.Key.from_dict(
            'KMS',
            kms_dict
        )
        self.template.add_resource(kms_res)

        # Outputs
        self.create_output(
            title='CMKArn',
            description="The CMK Arn",
            value=troposphere.GetAtt(kms_res, 'Arn'),
            ref=self.resource.paco_ref_parts + ".kms.arn",
        )
        self.create_output(
            title='CMKId',
            description="The CMK Id",
            value=troposphere.Ref(kms_res),
            ref=self.resource.paco_ref_parts + ".kms.id",
        )

    def deployment_pipeline_template(self, kms_config_dict):
        "Template for a DeploymentPipeline"
        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'

Description: KMS Customer Managed Key

#Parameters:

Resources:
  CMK:
    Type: AWS::KMS::Key
    Properties:
      Description: Paco Generic KMS Customer Managed Key
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
  CMKArn:
    Value: !GetAtt CMK.Arn

  CMKId:
    Value: !Ref CMK

"""
        principal_yaml = """
              AWS:"""
        for aws_principal in kms_config_dict['crypto_principal']['aws']:
            principal_yaml += """
                - '{0}'""".format(aws_principal)

        template_table = {
            'key_policy_principal': principal_yaml
        }
        self.stack.register_stack_output_config(self.resource.paco_ref_parts + '.kms.arn', 'CMKArn')
        self.stack.register_stack_output_config(self.resource.paco_ref_parts + '.kms.id', 'CMKId')
        self.set_template(template_fmt.format(template_table))

