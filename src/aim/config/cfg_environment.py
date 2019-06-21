from aim.config.config import Config

class EnvironmentConfig(Config):
    def __init__(self, aim_ctx, project_ctx, name):
        #aim_ctx.log("EnvironmentConfig Init")
        super().__init__(aim_ctx)

        self.name = name
        self.project_ctx = project_ctx

        # Get the environment dict from the project config
        self.set_config_dict( project_ctx.config.environment(name) )

        #self.aim_ctx.log("EnvironmentConfig Loaded: %s, Yaml: %s" % (name, self.yaml_path))

    def network_name(self):
        return self.config_dict['network']['name']

    def network(self):
        return self.config_dict['network']

    def enabled(self):
        return self.config_dict['enabled']

    def default_network(self):
        return self.project_ctx.config.network(self.network_name())

    def default_application(self, name):
        return self.project_ctx.config.application(name)

    def default_iam(self, name):
        return self.project_ctx.config.iam(name)

    def application(self, name):
        return self.config_dict['applications'][name]

    def applications(self):
        return self.config_dict['applications']

    def iam(self):
        return self.config_dict['iam']
