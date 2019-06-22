import click
import os
from aim.stack_group import CodeCommitStackGroup
from aim.stack_group import IAMStackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.config import CodeCommitConfig
from aim.controllers.controllers import Controller
from aim.yaml import YAML

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False


class CodeCommitController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "CodeCommit")

        #self.aim_ctx.log("CodeCommit Service: Configuration: %s" % (name))
        self.config = None
        self.name = None
        self.stack_grps = []
        self.init_done = False

    def init(self, init_config):
        if self.init_done:
            return
        self.init_done = True

        self.name = init_config['name']
        self.config = CodeCommitConfig(self.aim_ctx, self.name)
        self.config.load()
        self.init_stack_groups()

    def init_stack_groups(self):
        # CodeCommit Repository
        for account_id in self.config.get_repo_account_ids():
            for repo_region in self.config.get_account_region_ids(account_id):
                account_ctx = self.aim_ctx.get_account_context(account_ref=account_id)
                repo_list = self.config.get_repo_list_dict(account_id, repo_region)
                codecommit_stack_grp = CodeCommitStackGroup(self.aim_ctx,
                                                            account_ctx,
                                                            repo_region,
                                                            self.config,
                                                            repo_list,
                                                            self)

                self.stack_grps.append(codecommit_stack_grp)
                codecommit_stack_grp.init()


                # IAM Account Delegate Role
                # Generate IAM Role dict config
                #iam_roles_dict = self.gen_iam_roles_config_dict(repo_list)
                #aws_name_prefix = self.get_aws_name()
                #iam_stack_grp = IAMStackGroup(self.aim_ctx,
                #                              account_ctx,
                #                              aws_name_prefix,
                #                              iam_roles_dict,
                #                              'codecommit',
                #                              'codecommit',
                #                              self)
                #self.stack_grps.append(iam_stack_grp)
                #iam_stack_grp.init()

    def gen_iam_roles_config_dict(self, repo_list):

        role_yaml = """
assume_role_policy:
  aws:
    - aim.sub '${{config.ref accounts.master}}'
instance_profile: false
path: /
role_name: Tools-Account-Delegate-Role
policies:
  - name: 'CodePipeline-CodeCommit-Policy'
    statement:
      - effect: Allow
        action:
          - codecommit:BatchGetRepositories
          - codecommit:Get*
          - codecommit:GitPull
          - codecommit:List*
          - codecommit:CancelUploadArchive
          - codecommit:UploadArchive
        resource:
          - 'arn:aws:codecommit:{0[repo_region]:s}:{0[repo_account_id]:s}:{0[repo_name]:s}'
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - '*'
"""
        role_list_config = { }
        for repo_info in repo_list:
            repo_account_ref = self.config.get_account(repo_info['group_id'], repo_info['repo_id'])
            account_ctx = self.aim_ctx.get_account_context(repo_account_ref)
            repo_table = { 'repo_name':  self.config.get_repo_name(repo_info['group_id'], repo_info['repo_id']),
                           'repo_region': repo_info['aws_region'],
                           'repo_account_id': account_ctx.get_id() }
            role_config = yaml.load(role_yaml.format(repo_table))
            role_list_config[repo_info['repo_id']] = role_config

        return role_list_config

    def validate(self):
        if self.config.enabled() == False:
            print("CodeCommit Service: validate: disabled")
            return

        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        if self.config.enabled() == False:
            print("CodeCommit Service: provision: disabled")
            return

        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def get_service_ref_value(self, service_parts):
        # codecommit.example.app1.name
        group_id = service_parts[1]
        repo_id = service_parts[2]
        if service_parts[3] == "name":
            return self.stack_grps[0].config.get_repo_name(group_id, repo_id)
        if service_parts[3] == "arn":
            account_ref = self.stack_grps[0].config.get_account(group_id, repo_id)
            account_ctx = self.aim_ctx.get_account_context(account_ref)
            aws_region = self.stack_grps[0].config.get_repo_aws_region(group_id, repo_id)
            repo_name =  self.stack_grps[0].config.get_repo_name(group_id, repo_id)
            return "arn:aws:codecommit:{0}:{1}:{2}".format(aws_region, account_ctx.get_id(), repo_name)
        elif service_parts[3] == "account_id":
            account_ref = self.stack_grps[0].config.get_account(group_id, repo_id)
            account_ctx = self.aim_ctx.get_account_context(account_ref)
            return account_ctx.get_id()

        return None
