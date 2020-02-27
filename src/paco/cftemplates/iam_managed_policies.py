from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.stack import Parameter
from paco.utils import md5sum


class IAMManagedPolicies(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        policy,
        template_params,
    ):
        self.policy = policy
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        # existing Policy.policy_name's have been named in the format "<resource.name>-<policy.name>"
        # however, the policy.name is actually just 'policy' and the name used was a parent container that
        # contained the actual name for the policy.
        self.set_aws_name('Policy', self.resource_group_name, policy.policy_name)

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'IAM: Managed Policy'

{0[parameters_yaml]:s}

Resources:

  DummyResource:
    Type: AWS::CloudFormation::WaitConditionHandle

{0[resources_yaml]:s}

{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        policy_fmt = """
  {0[cfn_logical_id_prefix]:s}ManagedPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      #Description: String
      #Groups:
      #  - String
      ManagedPolicyName: {0[name]:s}
      Path: {0[path]:s}
{0[policy_document]}
{0[statement]}
{0[roles]}
{0[users]}
"""
        policy_document = """
      PolicyDocument:
        Version: "2012-10-17"
        Statement:"""

        policy_table = {
            'name': None,
            'path': None,
            'cfn_logical_id_prefix': None,
            'policy_document': None,
            'statement': None,
            'roles': None,
            'users': None
        }

        role_fmt = """        - %s
"""
        user_fmt = """        - %s
"""

        policy_outputs_fmt = """
  {0[cfn_logical_id_prefix]:s}ManagedPolicy:
    Value: !Ref {0[cfn_logical_id_prefix]:s}ManagedPolicy
"""

        parameters_yaml = ""
        resources_yaml = ""
        outputs_yaml = ""

        # Parameters
        parameter_fmt = """
  {0[key]:s}:
     Type: {0[type]:s}
     Description: {0[description]:s}
"""

        if policy.is_enabled() == True:
            policy_table.clear()
            if template_params:
                for param_table in template_params:
                    self.set_parameter(param_table['key'], param_table['value'])
                    parameters_yaml += parameter_fmt.format(param_table)

            policy_name = policy.policy_name
            # Name
            policy_table['name'] = self.gen_policy_name(policy_name)
            policy_table['cfn_logical_id_prefix'] = self.create_cfn_logical_id(policy_name)
            # Path
            policy_table['path'] = policy.path

            # Policy Document
            # Roles
            policy_table['roles'] = ""
            if policy.roles and len(policy.roles) > 0:
                policy_table['roles'] = """      Roles:
    """
                for role in policy.roles:
                    policy_table['roles'] += role_fmt % (role)

            # Users
            policy_table['users'] = ""
            if policy.users and len(policy.users) > 0:
                policy_table['users'] = "      Users:\n"
                for user in policy.users:
                    policy_table['users'] += user_fmt % (user)

            policy_table['policy_document'] = policy_document
            # Statement
            policy_table['statement'] = self.gen_statement_yaml(policy.statement)

            # Resources
            resources_yaml += policy_fmt.format(policy_table)

            # Initialize Parameters
            # Outputs
            outputs_yaml += policy_outputs_fmt.format(policy_table)

        # Parameters
        template_table['parameters_yaml'] = ""
        if parameters_yaml != "":
            template_table['parameters_yaml'] = "Parameters:\n"
        template_table['parameters_yaml'] += parameters_yaml

        # Resources
        template_table['resources_yaml'] = resources_yaml
        # Outputs
        template_table['outputs_yaml'] = ""
        if outputs_yaml != "":
            template_table['outputs_yaml'] = "Outputs:\n"
        template_table['outputs_yaml'] += outputs_yaml

        # Template
        self.set_template(template_fmt.format(template_table))


    def gen_policy_name(self, policy_name):
        "Generate a name valid in CloudFormation"
        policy_ref_hash = md5sum(str_data=self.policy.paco_ref_parts)[:8].upper()
        policy_name = self.create_resource_name_join(
            name_list=[policy_ref_hash, policy_name],
            separator='-',
            camel_case=False,
            filter_id='IAM.ManagedPolicy.ManagedPolicyName'
        )
        return policy_name

    def gen_statement_yaml(self, statements):
        statement_fmt = """
          - Effect: {0[effect]:s}
            Action:{0[action_list]:s}
            Resource:{0[resource_list]:s}
"""
        statement_table = {
            'effect': None,
            'action_list': None,
            'resource_list': None
        }

        quoted_list_fmt = """
              - '{0}'"""
        unquoted_list_fmt = """
              - {0}"""
        statement_yaml = ""
        for statement in statements:
            statement_table['effect'] = ""
            statement_table['action_list'] = ""
            statement_table['resource_list'] = ""
            statement_table['effect'] = statement.effect
            statement_table['principal'] = ""
            statement_table['condition'] = ""
            for action in statement.action:
                statement_table['action_list'] += quoted_list_fmt.format(action)
            for resource in statement.resource:
                if resource[0:1] == '!':
                    statement_table['resource_list'] += unquoted_list_fmt.format(resource)
                else:
                    statement_table['resource_list'] += quoted_list_fmt.format(resource)

            statement_yaml += statement_fmt.format(statement_table)

        return statement_yaml
