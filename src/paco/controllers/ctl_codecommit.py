import click
import os
from paco.stack_grps.grp_codecommit import CodeCommitStackGroup
from paco.stack_grps.grp_iam import IAMStackGroup
from paco.stack_group import stack_group
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.controllers.controllers import Controller
from paco.core.yaml import YAML

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False


class CodeCommitController(Controller):
    def __init__(self, paco_ctx):
        if paco_ctx.legacy_flag('codecommit_controller_type_2019_09_18') == True:
            controller_type = 'Service'
        else:
            controller_type = 'Resource'
        super().__init__(paco_ctx,
                         controller_type,
                         "CodeCommit")
        if not 'codecommit' in self.paco_ctx.project['resource']:
            self.init_done = True
            return
        self.config = None
        self.name = None
        self.stack_grps = []
        self.init_done = False

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_done = True
        self.paco_ctx.log_action_col("Init", "CodeCommit")
        if model_obj:
            self.name = model_obj.paco_ref_list[1]
        self.config = self.paco_ctx.project['resource']['codecommit']
        # Sets the CodeCommit reference resolver object to forward all
        # all paco.ref resource.codecommit.* calls to self.resolve_ref()
        if self.config != None:
            self.config.resolve_ref_obj = self
            self.init_stack_groups()
        self.paco_ctx.log_action_col("Init", "CodeCommit", "Completed")

    def init_stack_groups(self):
        # CodeCommit Repository
        for account_id in self.config.repo_account_ids():
            for repo_region in self.config.account_region_ids(account_id):
                account_ctx = self.paco_ctx.get_account_context(account_ref=account_id)
                repo_list = self.config.repo_list_dict(account_id, repo_region)
                codecommit_stack_grp = CodeCommitStackGroup(self.paco_ctx,
                                                            account_ctx,
                                                            repo_region,
                                                            self.config,
                                                            repo_list,
                                                            self)

                self.stack_grps.append(codecommit_stack_grp)
                codecommit_stack_grp.init()

    def gen_iam_roles_config_dict(self, repo_list):

        role_yaml = """
assume_role_policy:
  aws:
    - paco.sub '${{paco.ref accounts.master}}'
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
            repo_config = repo_info['config']
            account_ctx = self.paco_ctx.get_account_context(repo_config.account)
            repo_table = { 'repo_name':  repo_config.name,
                           'repo_region': repo_config.region,
                           'repo_account_id': account_ctx.get_id() }
            role_config = yaml.load(role_yaml.format(repo_table))
            role_list_config[repo_info['repo_id']] = role_config

        return role_list_config

    def delete(self):
        for stack_grp in self.stack_grps:
            stack_grp.delete()

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        self.confirm_yaml_changes(self.config)
        for stack_grp in self.stack_grps:
            stack_grp.provision()
        self.apply_model_obj()

    def resolve_ref(self, ref):
        # codecommit.example.app1.name
        group_id = ref.parts[2]
        repo_id = ref.parts[3]
        repo_config = self.stack_grps[0].config.repository_groups[group_id][repo_id]
        if ref.last_part == "name":
            return repo_config.name
        if ref.last_part == "arn":
            account_ref = repo_config.account
            account_ctx = self.paco_ctx.get_account_context(account_ref)
            aws_region = repo_config.region
            repo_name =  repo_config.name
            return "arn:aws:codecommit:{0}:{1}:{2}".format(aws_region, account_ctx.get_id(), repo_name)
        elif ref.last_part == "account_id":
            account_ref = repo_config.account
            account_ctx = self.paco_ctx.get_account_context(account_ref)
            return account_ctx.get_id()
        elif ref.last_part == 'account':
            return repo_config.account
        else:
            if ref.ref == 'resource.codecommit.{}.{}'.format(group_id, repo_id):
                return repo_config

        return None
