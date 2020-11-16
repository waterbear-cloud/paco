from enum import unique
from paco.tests import cwd_to_fixtures
from paco.stack import Stack
from paco.models.applications import EBS
from paco.models.project import Project
import paco.config.paco_context
import unittest


class BaseTestStack(unittest.TestCase):
    """Stack for testing"""
    fixture_name = 'config_city'

    def setUp(self):

        # miniml Project with EBS resource
        project = Project('test', None)
        ebs = EBS('ebs', project)
        ebs.enabled = True
        ebs.size_gib = 20
        ebs.volume_type = 'gp2'
        ebs.availability_zone = 1

        # minimal PacoContext
        path = cwd_to_fixtures()
        home = path / self.fixture_name
        self.paco_ctx = paco.config.paco_context.PacoContext(home)
        self.paco_ctx.project = project

        self.stack = Stack(
            paco_ctx=self.paco_ctx,
            account_ctx=None,
            stack_group=self,
            resource=ebs,
            aws_region='us-west-2',
        )


class BaseTestProject(unittest.TestCase):
    """Complete mock Paco Project for testing"""

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
        self.paco_ctx.development = True
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
