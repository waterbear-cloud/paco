from awacs.aws import PolicyDocument, Allow
from paco.cftemplates.tests import BaseTestStack
from paco.cftemplates.iam_managed_policies import IAMManagedPolicies
from paco.models.iam import ManagedPolicy
from paco.core.yaml import YAML
import paco.models.loader
import troposphere
import troposphere.iam

yaml=YAML(typ='safe')

class TestIAMManagedPolicies(BaseTestStack):

    def test_simple_managed_policy(self):

        policy_config_yaml = f"""
policy_name: 'simple-ec2lm'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:DescribeTags"
    resource:
      - '*'
"""
        policy_dict = yaml.load(policy_config_yaml)
        policy = ManagedPolicy('simple', None)
        paco.models.loader.apply_attributes_from_config(policy, policy_dict)

        managed_policy_stack_template = IAMManagedPolicies(
            self.stack,
            self.paco_ctx,
            policy,
            template_params=None,
        )
        troposphere_tmpl = managed_policy_stack_template.template
        tmpl_policy = troposphere_tmpl.resources['simpleec2lmManagedPolicy']

        # Assert resource simpleec2lmManagedPolicy
        assert tmpl_policy.resource_type, troposphere.iam.ManagedPolicy.resource_type

        # Assert ManagedPolicyName: D41D8CD9-simple-ec2lm
        assert tmpl_policy.properties['ManagedPolicyName'], 'D41D8CD9-simple-ec2lm'

        # Assert PolicyDocument has Statement with Effect/Action/Resource
        tmpl_policy.resource['Properties']['PolicyDocument'].properties['Statement'][0].properties['Effect']
        assert tmpl_policy.properties['PolicyDocument'], PolicyDocument
        statement = tmpl_policy.properties['PolicyDocument'].properties['Statement'][0]
        assert statement.properties['Effect'] == 'Allow'
        assert statement.properties['Action'][0].prefix == "ec2"
        assert statement.properties['Action'][0].action == "DescribeTags"
        assert statement.properties['Resource'][0] == "*"

        # Assert output simpleec2lmManagedPolicy
        self.assertIsInstance(troposphere_tmpl.outputs['simpleec2lmManagedPolicy'], troposphere.Output)

    def test_role_managed_policy(self):
        policy_config_yaml = f"""
policy_name: 'rolled-ec2lm'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:DescribeTags"
    resource:
      - '*'
"""
        policy_dict = yaml.load(policy_config_yaml)
        policy_dict['roles'] = [ 'MyMockRole', 'YourMockRole' ]
        policy = ManagedPolicy('rolled', None)
        paco.models.loader.apply_attributes_from_config(policy, policy_dict)

        managed_policy_stack_template = IAMManagedPolicies(
            self.stack,
            self.paco_ctx,
            policy,
            template_params=None,
        )
        troposphere_tmpl = managed_policy_stack_template.template
        tmpl_policy = troposphere_tmpl.resources['rolledec2lmManagedPolicy']

        # Assert resource rolledc2lmManagedPolicy
        assert tmpl_policy.resource_type, troposphere.iam.ManagedPolicy.resource_type

        # Assert Roles
        assert tmpl_policy.properties['Roles'][0], 'MyMockRole'
        assert tmpl_policy.properties['Roles'][1], 'YourMockRole'

    def test_params_managed_policy(self):
        template_params = [
            {
                'description': 'Secrets Manager Secret ARN',
                'type': 'String',
                'key': 'SecretArnOne',
                'value': "arn:aws:secretsmanager:region:123456789012:secret:tutorials/SecretOne-jiObOV",
            },
            {
                'description': 'Secrets Manager Secret ARN',
                'type': 'String',
                'key': 'SecretArnTwo',
                'value': "arn:aws:secretsmanager:region:123456789012:secret:tutorials/SecretTwo-bjy6fT",
            }
        ]

        policy_config_yaml = f"""
policy_name: 'secret-ec2lm'
enabled: true
statement:
  - effect: Allow
    action:
      - secretsmanager:GetSecretValue
    resource:
      - !Ref SecretArnOne
      - !Ref SecretArnTwo
"""

        policy_dict = yaml.load(policy_config_yaml)
        policy = ManagedPolicy('simple', None)
        paco.models.loader.apply_attributes_from_config(policy, policy_dict)

        managed_policy_stack_template = IAMManagedPolicies(
            self.stack,
            self.paco_ctx,
            policy,
            template_params=template_params,
        )
        troposphere_tmpl = managed_policy_stack_template.template

        # Assert SecretArnOne Param
        assert self.stack.parameters[0].key == 'SecretArnOne'
        assert self.stack.parameters[0].value == 'arn:aws:secretsmanager:region:123456789012:secret:tutorials/SecretOne-jiObOV'

        # Assert SecretArnTwo Param
        assert self.stack.parameters[1].key == 'SecretArnTwo'
        assert self.stack.parameters[1].value == 'arn:aws:secretsmanager:region:123456789012:secret:tutorials/SecretTwo-bjy6fT'

        # Assert ManagedPolicyName: D41D8CD9-simple-ec2lm
        tmpl_policy = troposphere_tmpl.resources['secretec2lmManagedPolicy']
        assert tmpl_policy.properties['ManagedPolicyName'], 'D41D8CD9-secret-ec2lm'

        # Assert Statement has Resource with Refs to SecretArnOne and SecretArnTwo
        statement = tmpl_policy.properties['PolicyDocument'].properties['Statement'][0]
        assert statement.properties['Resource'][0] == '!Ref SecretArnOne'
        assert statement.properties['Resource'][1] == '!Ref SecretArnTwo'

        # When a Troposphere template is converted to YAML, it uses the cfn-flip library
        # this in turn uses PyYAML, which puts single-quotes (') around tagged strings.
        # This:
        #   - !Ref SecretArnOne
        # Becomes invalid CloudFormation
        #   - '!Ref SecretArnOne'
        assert managed_policy_stack_template.body.find("'!Ref SecretArnOne'") == -1
