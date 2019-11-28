import os
import sys
from paco.cftemplates.cftemplates import CFTemplate, Parameter
from paco import utils
from paco.utils import md5sum
from enum import Enum
from io import StringIO


class IAMRoles(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 role_ref,
                 grp_id,
                 role_id,
                 role_config,
                 template_params,
                 change_protected):

        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=role_config.is_enabled(),
            config_ref=role_ref,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=change_protected
        )
        self.set_aws_name('Role', grp_id, role_id)

        self.role_ref = role_ref

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'IAM Roles: Roles and Instance Profiles'

Parameters:
{0[parameters_yaml]:s}

Resources:
{0[resources_yaml]:s}

Outputs:
{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        iam_role_params_fmt ="""
  {0[role_path_param_name]:s}:
    Type: String
    Description: 'The path associated with the {0[role_path_param_name]:s} IAM Role'
    Default: '/'
"""

        iam_role_fmt = """
  {0[cf_resource_name_prefix]:s}Role:
    Type: AWS::IAM::Role
    Properties:
      Path: !Ref {0[role_path_param_name]:s}
      RoleName: {0[role_name]:s}
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: "Allow"
            Principal:{0[assume_role_principal]:s}
            Action:
              - "sts:AssumeRole"
{0[managed_policy_arns]:s}
{0[inline_policies]:s}

{0[instance_profile]:s}
"""
        iam_role_table = {
            'role_name': None,
            'instance_profile': None,
            'profile_name': None,
            'cf_resource_name_prefix': None,
            'inline_policies': "",
            'managed_policy_arns': '',
        }

        iam_profile_fmt = """
  {0[cf_resource_name_prefix]:s}InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Path: !Ref {0[role_path_param_name]:s}
      InstanceProfileName: {0[profile_name]:s}
      Roles:
        - !Ref {0[cf_resource_name_prefix]:s}Role

"""
        iam_role_outputs_fmt = """
  {0[cf_resource_name_prefix]:s}Role:
    Value: !Ref {0[cf_resource_name_prefix]:s}Role
"""

        iam_profile_outputs_fmt = """
  {0[cf_resource_name_prefix]:s}InstanceProfile:
    Value: !Ref {0[cf_resource_name_prefix]:s}InstanceProfile
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

        iam_role_table.clear()
        if template_params:
            for param_table in template_params:
                self.set_parameter(param_table['key'], param_table['value'])
                parameters_yaml += parameter_fmt.format(param_table)

        # Role
        role_path_param_name = self.get_cf_resource_name_prefix(role_id) + "RolePath"
        iam_role_table['role_path_param_name'] = role_path_param_name
        if role_config.global_role_name:
            iam_role_table['role_name'] = role_config.role_name
        else:
            # Hashed name to avoid conflicts between environments, etc.
            iam_role_table['role_name'] = self.gen_iam_role_name("Role", role_id)
        iam_role_table['cf_resource_name_prefix'] = self.get_cf_resource_name_prefix(role_id)

        # Assume Role Principal
        principal_yaml = ""
        if role_config.assume_role_policy != None:
            if len(role_config.assume_role_policy.service) > 0:
                principal_yaml += """
              Service:"""
                for service_item in role_config.assume_role_policy.service:
                    principal_yaml += """
                - """ + service_item
            elif len(role_config.assume_role_policy.aws) > 0:
                principal_yaml += """
              AWS:"""
                for aws_item in role_config.assume_role_policy.aws:
                    principal_yaml += """
                - """ + aws_item
        else:
            pass
        iam_role_table['assume_role_principal'] = principal_yaml

        # Managed Policy ARNs
        if len(role_config.managed_policy_arns) > 0:
            iam_role_table['managed_policy_arns'] = "      ManagedPolicyArns:\n"
            for mp_arn in role_config.managed_policy_arns:
                iam_role_table['managed_policy_arns'] += "        - " + mp_arn + "\n"
        else:
            iam_role_table['managed_policy_arns'] = ""

        # Inline Policies
        if role_config.policies and role_config.is_enabled():
            iam_role_table['inline_policies'] = self.gen_role_policies(role_config.policies)
        else:
            iam_role_table['inline_policies'] = ""

        # Instance Profile
        if role_config.instance_profile == True:
            iam_role_table['profile_name'] = self.gen_iam_role_name("Profile", role_id)
            iam_role_table['instance_profile'] = iam_profile_fmt.format(iam_role_table)
        else:
            iam_role_table['instance_profile'] = ""

        parameters_yaml += iam_role_params_fmt.format(iam_role_table)
        resources_yaml += iam_role_fmt.format(iam_role_table)
        outputs_yaml += iam_role_outputs_fmt.format(iam_role_table)

        if role_config.instance_profile == True:
            outputs_yaml += iam_profile_outputs_fmt.format(iam_role_table)
        # Initialize Parameters
        self.set_parameter(role_path_param_name, role_config.path)

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    # Generate a name valid in CloudFormation
    def gen_iam_role_name(self, role_type, role_id):
        iam_context_hash = md5sum(str_data=self.role_ref)[:8].upper()
        role_name = self.create_resource_name_join(
            name_list=[iam_context_hash, role_type[0], role_id],
            separator='-',
            camel_case=True,
            filter_id='IAM.Role.RoleName'
        )
        return role_name

    def get_cf_resource_name_prefix(self, resource_name):
        norm_res_name = self.create_resource_name(resource_name)
        new_name = ""
        for name in norm_res_name.split('-'):
            new_name += name[0].upper() + name[1:]
        return new_name

    def gen_role_policies(self, policies):

        policies_yaml = "      Policies:"
        policy_fmt = """
        - PolicyName: {0[name]:s}
          PolicyDocument:
            Version: 2012-10-17
            Statement:{0[statement_list]:s}
"""
        policy_table = {
            'name': None,
            'statement_list': None
        }

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
        for inline_policy in policies:
            policy_table['name'] = ""
            policy_table['statement_list'] = ""
            policy_table['name'] = inline_policy.name
            for statement in inline_policy.statement:
                statement_table['effect'] = ""
                statement_table['action_list'] = ""
                statement_table['resource_list'] = ""
                statement_table['effect'] = statement.effect
                for action in statement.action:
                    statement_table['action_list'] += quoted_list_fmt.format(action)
                for resource in statement.resource:
                    if resource[0:1] == '!':
                        statement_table['resource_list'] += unquoted_list_fmt.format(resource)
                    else:
                        statement_table['resource_list'] += quoted_list_fmt.format(resource)

                policy_table['statement_list'] += statement_fmt.format(statement_table)

            policies_yaml += policy_fmt.format(policy_table)

        return policies_yaml
