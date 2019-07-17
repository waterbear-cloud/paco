import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class CodeCommit(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 codecommit_config,
                 repo_list):
        #aim_ctx.log("CodeCommit CF Template init")

        aws_name = '-'.join(["Repositories"])

        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=None,
                         aws_name=aws_name,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])


        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'CodeCommit Repositories'

#Parameters:
#{0[parameters_yaml]:s}

Resources:
{0[resources_yaml]:s}

#Outputs:
#{0[outputs_yaml]:s}
"""
        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

#        codecommit_params_fmt ="""
#  {0[?_name]:s}:
#    Type: String
#    Description: 'The path associated with the {0[role_path_param_name]:s} IAM Role'
#"""

        codecommit_repo_fmt = """
  {0[cf_resource_name_prefix]:s}Repository:
    Type: AWS::CodeCommit::Repository
    Properties:
        RepositoryName: {0[repository_name]:s}
        RepositoryDescription: {0[repository_description]:s}
"""

        codecommit_repo_outputs_fmt = """
"""

        codecommit_repo_table = {
            'repository_name': None,
            'repository_description': None,
            'cf_resource_name_prefix': None
        }

        parameters_yaml = ""
        resources_yaml = ""
        outputs_yaml = ""

        for repo_item in repo_list:
            repo_config = repo_item['repo_config']
            codecommit_repo_table['repository_name'] = repo_config.name
            codecommit_repo_table['repository_description'] = repo_config.description
            cf_repo_name = '_'.join([repo_item['group_id'], repo_item['repo_id']])
            codecommit_repo_table['cf_resource_name_prefix'] = self.gen_cf_logical_name(cf_repo_name, '_')

            resources_yaml += codecommit_repo_fmt.format(codecommit_repo_table)
            #outputs_yaml += codecommit_repo_outputs_fmt.format(codecommit_repo_table)

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))

    def validate(self):
        #self.aim_ctx.log("Validating CodeCommit Template")
        super().validate()

    def get_outputs_key_from_ref(self, aim_ref):
        return None
