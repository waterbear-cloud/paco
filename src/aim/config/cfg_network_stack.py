from aim.config.config import Config
import copy

class NetworkStackConfig(Config):
    def __init__(self, aim_ctx, env_ctx):
        #aim_ctx.log("NetworkStackConfig Init")
        super().__init__(aim_ctx)

        self.env_ctx = env_ctx
        # Copy the default network dict
        network_config = copy.deepcopy(env_ctx.config.default_network())
        # Update the default network dict copy with environment values
        network_config = self.config_override(network_config, env_ctx.config.network())

        self.set_config_dict( network_config )
        #self.aim_ctx.log("NetworkStackConfig Loaded: %s, Yaml: %s" % (env_ctx.config.network_name(), self.yaml_path))

    def vpc(self):
        return self.config_dict['vpc']

    def segments(self):
        return self.config_dict['vpc']['segments']

    def segment(self, segment_name):
        return self.config_dict['vpc']['segments'][segment_name]

    def availability_zones(self):
        return self.config_dict['availability_zones']

    def security_groups(self):
        return self.config_dict['vpc']['security_groups']
