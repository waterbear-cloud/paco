from awacs.aws import PolicyDocument, Principal, Statement, Allow, Action, Condition, ForAnyValueStringLike, Policy
from awacs.aws import StringEquals
from paco.cftemplates.iam_roles import role_to_troposphere
from paco.models.loader import load_yaml, apply_attributes_from_config
from paco.models.iam import RoleDefaultEnabled
from unittest import TestCase
import paco.models.iam
import troposphere.iam
import json


unauth_cognito_role_yaml = """
policies:
  - name: CognitoSyncAll
    statement:
      - effect: Allow
        action:
          - "cognito-sync:*"
        resource:
           - '*'
"""

auth_cognito_role_yaml = """
enabled: true
policies:
  - name: ViewDescribe
    statement:
      - effect: Allow
        action:
          - "cognito-sync:*"
          - "cognito-identity:*"
        resource:
          - '*'
      - effect: Allow
        action:
          - "lambda:InvokeFunction"
        resource:
          - '*'

"""


auth_cognito_role_json = '{"Properties": {"AssumeRolePolicyDocument": {"Statement": [{"Effect": "Allow", "Principal": {"Federated": "cognito-identity.amazonaws.com"}, "Action": ["sts:AssumeRoleWithWebIdentity"], "Condition": {"StringEquals": {"cognito-identity.amazonaws.com:aud": "some-resource"}, "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"}}}]}, "Policies": [{"PolicyName": "ViewDescribe", "PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": ["cognito-sync:*", "cognito-identity:*"], "Resource": ["*"]}, {"Effect": "Allow", "Action": ["lambda:InvokeFunction"], "Resource": ["*"]}]}}]}, "Type": "AWS::IAM::Role"}'

backup_role_json = '{"Properties": {"AssumeRolePolicyDocument": {"Statement": [{"Effect": "Allow", "Principal": {"Service": ["backup.amazonaws.com"]}, "Action": ["sts:AssumeRole"]}]}, "ManagedPolicyArns": ["arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup", "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"]}, "Type": "AWS::IAM::Role"}'

aws_principal_role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '*'
policies:
  - name: AllowS3Get
    statement:
      - effect: Allow
        action:
          - 's3:GetObject'
        resource:
          - '*'
"""

aws_principal_role_json = '{"Properties": {"AssumeRolePolicyDocument": {"Statement": [{"Effect": "Allow", "Principal": {"AWS": ["*"]}, "Action": ["sts:AssumeRole"]}]}, "Policies": [{"PolicyName": "AllowS3Get", "PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["*"]}]}}]}, "Type": "AWS::IAM::Role"}'

aws_condition_role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '*'
policies:
  - name: AllowS3Get
    statement:
      - effect: Allow
        action:
          - 's3:GetObject'
        resource:
          - '*'
        condition:
          StringEquals:
            s3:x-amz-acl:
              "public-read"
          IpAddress:
            "aws:SourceIp": "192.0.2.0/24"
          NotIpAddress:
            "aws:SourceIp": "192.0.2.188/32"

"""

condition_role_json = '{"Properties": {"AssumeRolePolicyDocument": {"Statement": [{"Effect": "Allow", "Principal": {"AWS": ["*"]}, "Action": ["sts:AssumeRole"]}]}, "Policies": [{"PolicyName": "AllowS3Get", "PolicyDocument": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["*"], "Condition": {"StringEquals": {"s3:x-amz-acl": "public-read"}, "IpAddress": {"aws:SourceIp": "192.0.2.0/24"}, "NotIpAddress": {"aws:SourceIp": "192.0.2.188/32"}}}]}}]}, "Type": "AWS::IAM::Role"}'

def create_role_from_yaml(yaml):
    config = load_yaml(yaml)
    role = RoleDefaultEnabled('role', None)
    apply_attributes_from_config(role, config)
    return role


class TestIAMRoles(TestCase):

    def test_role_to_troposphere(self):
        # unauthenticated cognito role
        role = create_role_from_yaml(unauth_cognito_role_yaml)
        unauthenticated_assume_role_policy = PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal('Federated',"cognito-identity.amazonaws.com"),
                    Action=[Action('sts', 'AssumeRoleWithWebIdentity')],
                    Condition=Condition([
                        StringEquals({"cognito-identity.amazonaws.com:aud": 'some-resource'}),
                        ForAnyValueStringLike({"cognito-identity.amazonaws.com:amr": "unauthenticated"})
                    ]),
                ),
            ],
        )
        resource = role_to_troposphere(
            role,
            'UnauthenticatedRole',
            assume_role_policy=unauthenticated_assume_role_policy,
        )
        assert isinstance(resource, troposphere.iam.Role), True
        policy = resource.properties['Policies'][0].properties
        assert policy['PolicyName'], 'CognitoSyncAll'
        assert policy['PolicyDocument'].properties['Statement'][0].properties['Resource'], ['*']

        # authenticated cognito role
        role = create_role_from_yaml(auth_cognito_role_yaml)
        authenticated_assume_role_policy = PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Principal=Principal('Federated',"cognito-identity.amazonaws.com"),
                    Action=[Action('sts', 'AssumeRoleWithWebIdentity')],
                    Condition=Condition([
                        StringEquals({"cognito-identity.amazonaws.com:aud": 'some-resource'}),
                        ForAnyValueStringLike({"cognito-identity.amazonaws.com:amr": "authenticated"})
                    ]),
                ),
            ],
        )
        resource = role_to_troposphere(
            role,
            'AuthenticatedRole',
            assume_role_policy=authenticated_assume_role_policy
        )
        assert auth_cognito_role_json, json.dumps(resource.to_dict())

        # AWS Backup Role
        policy_arns = [
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup',
            'arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores'
        ]
        role_dict = {
            'enabled': True,
            'path': '/',
            'role_name': 'Backup',
            'managed_policy_arns': policy_arns,
            'assume_role_policy': {'effect': 'Allow', 'service': ['backup.amazonaws.com']}
        }
        role = paco.models.iam.Role('Backup', None)
        role.apply_config(role_dict)
        resource = role_to_troposphere(role, 'Backup')
        assert backup_role_json, json.dumps(resource.to_dict())

        # Simple AWS Principal Role
        role = create_role_from_yaml(aws_principal_role_yaml)
        resource = role_to_troposphere(role, 'SimpleAWS')
        assert backup_role_json, json.dumps(resource.to_dict())

        # Role with a Condition
        role = create_role_from_yaml(aws_condition_role_yaml)
        resource = role_to_troposphere(role, 'Condition')
        assert condition_role_json, json.dumps(resource.to_dict())
