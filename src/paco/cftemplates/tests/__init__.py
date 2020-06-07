from paco.tests import cwd_to_fixtures
from paco.stack import Stack
import paco.config.paco_context
import unittest


class BaseTestProject(unittest.TestCase):

    fixture_name = 'config_city'
    app_name = 'app'
    netenv_name = 'res'
    group_name = 'things'
    region_name = 'us-west-2'
    env_name = 'test'

    def setUp(self):
        # change cwd to the fixtures dir
        path = cwd_to_fixtures()
        home = path / self.fixture_name
        self.paco_ctx = paco.config.paco_context.PacoContext(home)
        self.paco_ctx.load_project(project_only=True)
        self.project = self.paco_ctx.project

    @property
    def netenv(self):
        return self.project['netenv'][self.netenv_name]

    @property
    def env_region(self):
        return self.project['netenv'][self.netenv_name][self.env_name][self.region_name]

    def create_stack(self, resource, account_ctx=None, aws_region='us-west-2'):
        "Create a Stack for testing"
        return Stack(
            self.paco_ctx,
            account_ctx,
            self,
            resource,
            aws_region=aws_region,
        )

    def get_resource_by_type(self, res_type):
        return self.project['netenv'][self.netenv_name][self.env_name][self.region_name].applications[self.app_name].groups[self.group_name].resources[res_type]

    def get_network(self):
        return self.project['netenv'][self.netenv_name][self.env_name][self.region_name].network
