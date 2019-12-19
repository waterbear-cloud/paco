import os
from paco.cftemplates.cftemplates import CFTemplate, Parameter
from paco.utils import md5sum
from paco import utils
from io import StringIO
from enum import Enum
import sys


class IAMManagedPolicies(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 policy_context,
                 grp_id,
                 res_id,
                 change_protected):

        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=policy_context['config'].is_enabled(),
            config_ref=policy_context['ref'],
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=change_protected
        )
        self.set_aws_name('Policy', grp_id, res_id)
        self.policy_context = policy_context
        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'IAM Roles: Roles and Instance Profiles'

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
        policy_config = policy_context['config']
        if policy_config.is_enabled() == True:
            policy_table.clear()
            if policy_context['template_params']:
                for param_table in policy_context['template_params']:
                    self.set_parameter(param_table['key'], param_table['value'])
                    parameters_yaml += parameter_fmt.format(param_table)

            policy_id = policy_context['id']
            # Name
            policy_table['name'] = self.gen_policy_name(policy_id)
            policy_table['cfn_logical_id_prefix'] = self.create_cfn_logical_id(policy_id)
            # Path
            policy_table['path'] = policy_config.path

            # Policy Document
            # Roles
            policy_table['roles'] = ""
            if policy_config.roles and len(policy_config.roles) > 0:
                policy_table['roles'] = """      Roles:
    """
                for role in policy_config.roles:
                    policy_table['roles'] += role_fmt % (role)

            # Users
            policy_table['users'] = ""
            if policy_config.users and len(policy_config.users) > 0:
                policy_table['users'] = "      Users:\n"
                for user in policy_config.users:
                    policy_table['users'] += user_fmt % (user)

            policy_table['policy_document'] = policy_document
            # Statement
            policy_table['statement'] = self.gen_statement_yaml(policy_config.statement)

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


    # Generate a name valid in CloudFormation
    def gen_policy_name(self, policy_id):
        policy_context_hash = md5sum(str_data=self.policy_context['ref'])[:8].upper()
        policy_name = self.create_resource_name_join(
            name_list=[policy_context_hash, policy_id],
            separator='-',
            camel_case=False,
            filter_id='IAM.ManagedPolicy.ManagedPolicyName'
        )
        return policy_name

    # TODO: This shares the same code in iam_roles.py. This should
    # be consolidated in cftemplates.py...
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
