import os
from paco.cftemplates.cftemplates import CFTemplate

from io import StringIO
from enum import Enum


class CodeCommit(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 stack_hooks,
                 codecommit_config,
                 repo_list):
        #paco_ctx.log("CodeCommit CF Template init")


        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=None,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_hooks=stack_hooks
        )
        self.set_aws_name('Repositories')


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

        codecommit_user_fmt = """
  {0[cf_resource_name_prefix]:s}User:
    Type: AWS::IAM::User
    Properties:
      UserName: {0[username]:s}
"""
        codecommit_user_table = {
            'cf_resource_name_prefix': None,
            'username': None
        }

        codecommit_readwrite_fmt = """
  {0[cf_repo_name_prefix]:s}RWPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      # PolicyName: {0[cf_repo_name_prefix]:s}
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action:
              - codecommit:BatchGetRepositories
              - codecommit:CreateBranch
              - codecommit:CreateRepository
              - codecommit:Get*
              - codecommit:GitPull
              - codecommit:GitPush
              - codecommit:List*
              - codecommit:Put*
              - codecommit:Post*
              - codecommit:Merge*
              - codecommit:TagResource
              - codecommit:Test*
              - codecommit:UntagResource
              - codecommit:Update*
            Resource: !GetAtt {0[cf_repo_name_prefix]:s}Repository.Arn
      Users:{0[users]:s}
"""

        codecommit_readwrite_table = {
            'cf_resource_name_prefix': None,
            'users': None
        }

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

        unique_users = {}
        policy_users = {}
        for repo_item in repo_list:
            repo_config = repo_item['repo_config']
            if repo_config.is_enabled() == False:
                continue
            codecommit_repo_table['repository_name'] = repo_config.repository_name
            codecommit_repo_table['repository_description'] = repo_config.description
            cf_repo_name = '_'.join([repo_item['group_id'], repo_item['repo_id']])
            repo_name_prefix = self.gen_cf_logical_name(cf_repo_name)
            codecommit_repo_table['cf_resource_name_prefix'] = repo_name_prefix

            # A user may have access to more than one repository.
            # Build a list so we can attach them later.
            codecommit_readwrite_table['users'] = ""
            if repo_config.users:
                for user_key in repo_config.users.keys():
                    user = repo_config.users[user_key]
                    if user.username not in unique_users.keys():
                        unique_users[user.username] = []
                    unique_users[user.username].append(repo_name_prefix)
                    if repo_name_prefix not in policy_users.keys():
                        policy_users[repo_name_prefix] = []

                    policy_users[repo_name_prefix].append(self.gen_cf_logical_name(user.username))

            resources_yaml += codecommit_repo_fmt.format(codecommit_repo_table)
            #outputs_yaml += codecommit_repo_outputs_fmt.format(codecommit_repo_table)

        # Users
        for username in unique_users.keys():
            codecommit_user_table['cf_resource_name_prefix'] = self.gen_cf_logical_name(username)
            codecommit_user_table['username'] = username
            resources_yaml += codecommit_user_fmt.format(codecommit_user_table)

        # Policies
        for cf_repo_name_prefix in policy_users.keys():
            user_list_yaml = ""
            for cf_user_name_prefix in policy_users[cf_repo_name_prefix]:
                user_list_yaml += "\n        - !Ref %sUser" % cf_user_name_prefix

            codecommit_readwrite_table['cf_repo_name_prefix'] = cf_repo_name_prefix
            codecommit_readwrite_table['users'] = user_list_yaml

            resources_yaml += codecommit_readwrite_fmt.format(codecommit_readwrite_table)

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))


