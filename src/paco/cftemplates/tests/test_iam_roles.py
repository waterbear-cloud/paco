from awacs.aws import PolicyDocument, Principal, Statement, Allow, Action, Condition, ForAnyValueStringLike, Policy
from awacs.aws import StringEquals
from paco.cftemplates.iam_roles import role_to_troposphere
from paco.models.loader import load_yaml, apply_attributes_from_config
from paco.models.iam import RoleDefaultEnabled
from unittest import TestCase
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
