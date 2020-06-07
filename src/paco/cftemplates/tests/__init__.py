from paco.tests import cwd_to_fixtures
import paco.config.paco_context


class BaseTestProject():

    def setup(self):
        # change cwd to the fixtures dir
        path = cwd_to_fixtures()
        home = path / self.fixture_name
        self.paco_ctx = paco.config.paco_context.PacoContext(home)
        self.paco_ctx.load_project(project_only=True)
        self.project = self.paco_ctx.project
