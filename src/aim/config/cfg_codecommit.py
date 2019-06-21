from aim.config.config import Config
import os
import copy


class CodeCommitConfig(Config):
    def __init__(self, aim_ctx, name):
        #aim_ctx.log("CodeCommitConfig Init")

        # config/Services/CodeCommit.yaml
        config_folder = os.path.join(aim_ctx.config_folder, "Services")
        super().__init__(aim_ctx, config_folder, "CodeCommit")
        self.name = name
        #self.aim_ctx.log("CodeCommitConfig Loaded: %s, Yaml: %s" % (name, self.yaml_path))
        self.repo_by_account = {}

    def load_defaults(self):
        super().load()
        defaults_config = []
        default_config['defaults'] = self.config_dict['defaults']
        self.config_dict = default_config

    def load(self):
        super().load()
        for group_id in self.get_group_ids():
            for repo_id in self.get_repo_ids(group_id):
                account_ref = self.get_account(group_id, repo_id)
                repo_region = self.get_repo_aws_region(group_id, repo_id)
                account_dict = { 'group_id': group_id,
                                 'repo_id': repo_id,
                                 'account_ref': account_ref,
                                 'aws_region': repo_region }
                if account_ref in self.repo_by_account.keys():
                    if repo_region in self.repo_by_account[account_ref].keys():
                        self.repo_by_account[account_ref][repo_region].append(account_dict)
                    else:
                        self.repo_by_account[account_ref][repo_region] = [account_dict]
                else:
                    self.repo_by_account[account_ref] = {repo_region: [account_dict]}

    def enabled(self):
        return True

    def get_repo_list_dict(self, account_id, aws_region):
         return self.repo_by_account[account_id][aws_region]

    def get_repo_account_ids(self):
        return self.repo_by_account.keys()

    def get_account(self, group_id, repo_id):
        return self.config_dict[group_id][repo_id]['account']

    def get_group_ids(self):
        return self.config_dict.keys()

    def get_repo_ids(self, group_id):
        return self.config_dict[group_id].keys()

    def get_account_region_ids(self, account_id):
        return self.repo_by_account[account_id].keys()

    def get_repo_name(self, group_id, repo_id):
        return self.config_dict[group_id][repo_id]['name']

    def get_repo_description(self, group_id, repo_id):
        return self.config_dict[group_id][repo_id]['description']

    def get_repo_aws_region(self, group_id, repo_id):
        return self.config_dict[group_id][repo_id]['aws_region']
