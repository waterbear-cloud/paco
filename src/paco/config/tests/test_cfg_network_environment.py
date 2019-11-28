import paco.config.paco_context
from paco.tests import cwd_to_fixtures


class TestNetEnvConfig():

    fixture_name = 'web_config_ui_demo'
    net_env_one = 'my-web-app'

    def setup(self):
        # change cwd to the fixtures dir
        path = cwd_to_fixtures()
        self.paco_ctx = paco.config.paco_context.PacoContext()
        self.paco_ctx.load_project()

class TestNetEnvConfigDogFoodOne(TestNetEnvConfig):

    fixture_name = 'dogfood_one'
    net_env_one = 'pacodemo'