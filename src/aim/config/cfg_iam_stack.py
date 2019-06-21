from aim.config.config import Config
import copy

class IAMStackConfig(Config):
    def __init__(self, aim_ctx, env_ctx, iam_name):
        #aim_ctx.log("IAMStackConfig Init")
        super().__init__(aim_ctx)

        self.env_ctx = env_ctx
        # Copy the default network dict
        iam_config = copy.deepcopy(env_ctx.config.default_iam(iam_name))

        # Update the default network dict copy with environment values
        iam_config = self.config_override(iam_config, env_ctx.config.iam())

        self.set_config_dict( iam_config )
        #self.aim_ctx.log("IAMStackConfig Loaded: %s, Yaml: %s" % (iam_name, self.yaml_path))

    def roles(self):
        return self.config_dict['roles']

    def get_role_config(self, role_name):
        return self.config_dict['roles'][role_name]
