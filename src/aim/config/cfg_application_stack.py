from aim.config.config import Config
import copy

class ApplicationStackConfig(Config):
    def __init__(self, aim_ctx, net_env_ctx, application_name):
        #aim_ctx.log("ApplicationStackConfig Init")
        super().__init__(aim_ctx)

        self.net_env_ctx = net_env_ctx
        # Copy the default network dict
        application_config = copy.deepcopy(net_env_ctx.config.default_application(application_name))
        # Update the default network dict copy with environment values
        application_config = self.config_override(application_config, net_env_ctx.config.application(application_name))

        self.set_config_dict( application_config )
        #self.aim_ctx.log("ApplicationStackConfig Loaded: %s, Yaml: %s" % (application_name, self.yaml_path))

    def resources(self):
        return self.config_dict['resources']
