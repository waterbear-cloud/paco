from paco.cftemplates.tests import BaseTestProject
from paco.cftemplates.codecommit import CodeCommit
from paco.stack import Stack


class TestCodeCommit(BaseTestProject):

    fixture_name = 'config_city'

    def test_codecommmit(self):
        codecommit_model = self.project['resource']['codecommit']
        account_ctx = None
        for account_id in codecommit_model.repo_account_ids():
            for repo_region in codecommit_model.account_region_ids(account_id):
                stack = Stack(
                    self.paco_ctx,
                    account_ctx,
                    self,
                    codecommit_model,
                    aws_region=repo_region,
                )
                repo_list = codecommit_model.repo_list_dict(account_id, repo_region)
                codecommit_st = CodeCommit(stack, self.paco_ctx, repo_list)
                cf_tmpl = codecommit_st.body
                # us-west-2 is a simple single repo
                if repo_region == 'us-west-2':
                    assert cf_tmpl.find('RepositoryName: demo') != -1
                    assert cf_tmpl.find('RepositoryDescription: Demo repository') != -1
                # ca-central-1 has a single user
                elif repo_region == 'ca-central-1':
                    assert cf_tmpl.find('RepositoryName: bobdog') != -1
                    assert cf_tmpl.find('UserName: bobdog@example.com') != -1
                    assert cf_tmpl.find('!Ref BobdogExampleComUser') != -1
                # eu-central-1 has multi-repo with users sharing access
                elif repo_region == 'eu-central-1':
                    assert cf_tmpl.count('!GetAtt FixturecityMultiuserRepository.Arn') == 2
                    assert cf_tmpl.count('!GetAtt FixturecityMultiusertwoRepository.Arn') == 2
