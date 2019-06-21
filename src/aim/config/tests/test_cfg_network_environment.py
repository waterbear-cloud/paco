import aim.config.aim_context
from aim.config.cfg_network_environment import NetEnvConfig
from aim.tests import cwd_to_fixtures


class TestNetEnvConfig():

    fixture_name = 'web_config_ui_demo'
    net_env_one = 'my-web-app'

    def setup(self):
        # change cwd to the fixtures dir
        path = cwd_to_fixtures()
        self.aim_ctx = aim.config.aim_context.AimContext()
        self.aim_ctx.init_project(self.fixture_name)

#    def test_create_NetEnvConfig(self):
#        net_env = NetEnvConfig(self.aim_ctx, self.net_env_one)
#        assert isinstance(net_env, NetEnvConfig)


class TestNetEnvConfigDogFoodOne(TestNetEnvConfig):

    fixture_name = 'dogfood_one'
    net_env_one = 'aimdemo'