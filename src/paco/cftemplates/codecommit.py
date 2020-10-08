from paco.cftemplates.cftemplates import StackTemplate


class CodeCommit(StackTemplate):
    "Provision repo_list which is a list of repositories by account"
    def __init__(self, stack, paco_ctx, repo_list):
        repo_config = stack.resource
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
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

Outputs:
{0[outputs_yaml]:s}
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
  {0[cf_resource_name_prefix]:s}ManagedPolicy:
    Type: AWS::IAM::ManagedPolicy
    DependsOn: {0[user]:s}
    Properties:
      # PolicyName: {0[cf_resource_name_prefix]:s}
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
            Resource:{0[repository_arns]:s}
      Users:{0[users]:s}
"""

        codecommit_readonly_fmt = """
  {0[cf_resource_name_prefix]:s}ManagedPolicy:
    Type: AWS::IAM::ManagedPolicy
    DependsOn: {0[user]:s}
    Properties:
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action:
              - codecommit:BatchGet*
              - codecommit:BatchDescribe*
              - codecommit:EvaluatePullRequestApprovalRules
              - codecommit:Get*
              - codecommit:Describe*
              - codecommit:List*
              - codecommit:GitPull
            Resource:{0[repository_arns]:s}
      Users:{0[users]:s}
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

        policy_outputs_fmt = """
  {0[cfn_logical_id_prefix]:s}ManagedPolicy:
    Value: !Ref {0[cfn_logical_id_prefix]:s}ManagedPolicy
"""
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

            if repo_config.external_resource == False:
                resources_yaml += codecommit_repo_fmt.format(codecommit_repo_table)

            # A user may have access to more than one repository.
            # Build a list so we can attach them later.
            if repo_config.users:
                for user_key in repo_config.users.keys():
                    user = repo_config.users[user_key]
                    if user.username not in unique_users:
                        unique_users[user.username] = {}
                    if user.permissions not in unique_users[user.username]:
                        unique_users[user.username][user.permissions] = {
                            'repo_name_prefix': [],
                            'repo_config': [],
                            'user_refs': [],
                        }
                    unique_users[user.username][user.permissions]['repo_name_prefix'].append(repo_name_prefix)
                    unique_users[user.username][user.permissions]['repo_config'].append(repo_config)
                    unique_users[user.username][user.permissions]['user_refs'].append(user.paco_ref_parts)
        # Users
        for username in unique_users.keys():
            # IAM User
            user_logical_id = self.gen_cf_logical_name(username)
            codecommit_user_table['cf_resource_name_prefix'] = user_logical_id
            codecommit_user_table['username'] = username
            resources_yaml += codecommit_user_fmt.format(codecommit_user_table)

            # User Policy
            codecommit_permissions_table = {}
            user_list_yaml = ""
            user_list_yaml += "\n        - !Ref %sUser" % user_logical_id
            codecommit_permissions_table['cf_resource_name_prefix'] = user_logical_id
            codecommit_permissions_table['users'] = user_list_yaml
            codecommit_permissions_table['user'] = user_logical_id + "User"

            for permission in unique_users[username].keys():
                if permission == 'ReadWrite':
                    repo_arns_yaml = ""
                    for repo_config in unique_users[username][permission]['repo_config']:
                        repo_idx = unique_users[username][permission]['repo_config'].index(repo_config)
                        repo_logical_id_prefix = unique_users[username][permission]['repo_name_prefix'][repo_idx]
                        if repo_config.external_resource == False:
                            repo_arns_yaml += "\n              - !GetAtt " + repo_logical_id_prefix + "Repository.Arn"
                        else:
                            repo_arns_yaml += "\n              - arn:aws:codecommit:{}:{}:{}".format(
                                stack.aws_region,
                                stack.account_ctx.get_id(),
                                repo_config.repository_name,
                            )
                    codecommit_permissions_table['repository_arns'] = repo_arns_yaml
                    resources_yaml += codecommit_readwrite_fmt.format(codecommit_permissions_table)
                    for user_ref in unique_users[username][permission]['user_refs']:
                        self.stack.register_stack_output_config(user_ref + '.policy.arn', user_logical_id + 'ManagedPolicy')
                elif permission == 'ReadOnly':
                    repo_arns_yaml = ""
                    for repo_config in unique_users[username][permission]['repo_config']:
                        repo_idx = unique_users[username][permission]['repo_config'].index(repo_config)
                        repo_logical_id_prefix = unique_users[username][permission]['repo_name_prefix'][repo_idx]
                        if repo_config.external_resource == False:
                            repo_arns_yaml += "\n              - !GetAtt " + repo_logical_id_prefix + "Repository.Arn"
                        else:
                            repo_arns_yaml += "\n              - arn:aws:codecommit:{}:{}:{}".format(
                                stack.aws_region,
                                stack.account_ctx.get_id(),
                                repo_config.repository_name,
                            )
                    codecommit_permissions_table['repository_arns'] = repo_arns_yaml
                    resources_yaml += codecommit_readonly_fmt.format(codecommit_permissions_table)
                    for user_ref in unique_users[username][permission]['user_refs']:
                        self.stack.register_stack_output_config(user_ref + '.policy.arn', user_logical_id + 'ManagedPolicy')
                outputs_yaml += policy_outputs_fmt.format(
                    {'cfn_logical_id_prefix': user_logical_id }
                )

        template_table['parameters_yaml'] = parameters_yaml
        template_table['resources_yaml'] = resources_yaml
        template_table['outputs_yaml'] = outputs_yaml
        self.set_template(template_fmt.format(template_table))


