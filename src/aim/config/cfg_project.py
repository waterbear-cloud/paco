from aim.config.config import Config
import os

class ProjectConfig(Config):
    def __init__(self, aim_ctx, name):
        #aim_ctx.log("ProjectConfig Init")
        super().__init__(aim_ctx)

        self.name = name

        project_folder = os.path.join(aim_ctx.projects_folder, name)
        self.load_yaml_config(project_folder, aim_ctx.project_yaml)

        #self.aim_ctx.log("ProjectConfig Loaded: %s, Yaml: %s" % (name, self.yaml_path))

    def environment(self, name):
        return self.config_dict['environments'][name]

    def network(self, name):
        return self.config_dict['networks'][name]

    def application(self, name):
        return self.config_dict['applications'][name]

    def iam(self, name):
        return self.config_dict['iam'][name]
