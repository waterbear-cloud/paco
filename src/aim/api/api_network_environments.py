from aim.api.api import API
from enum import Enum
from aim.config import NetEnvConfig
import json

APICommands = Enum('APICommands', 'DescribeNetworkEnvironments CreateNetworkEnvironment UpdateNetworkEnvironment')

class NetworkEnvironments( API ):
    def __init__(self, aim_ctx, api_command, api_json):
        #aim_ctx.log("API NetworkEnvironment Init")
        super().__init__(aim_ctx, api_command, api_json)

        #self.aim_ctx.log("API NetworkEnvironment Loaded")

    def process(self):
        #self.aim_ctx.log("API Network Environment: process: %s", (self.api_command))

        if self.api_command == APICommands.DescribeNetworkEnvironments.name:
            self.describe_network_environments()
        elif self.api_command == APICommands.CreateNetworkEnvironment.name:
            self.create_network_environment()


    # Load Network Environment yaml config
    def describe_network_environments(self):
        #self.aim_ctx.log("API Network Environment: describe_network_environments: %s", (self.api_command))
        # Load Environment YAML configuration
        # return as a response
        pass

    def create_network_environment(self):
        #self.aim_ctx.log("API Network Environment: create_network_environments: %s", (self.api_command))

        api_data = json.loads(self.api_json)

        net_env_config = NetEnvConfig(self.aim_ctx, api_data["name"])
        net_env_config.set_config_dict(api_data["config"])
        net_env_config.save()

        controller = self.aim_ctx.get_controller("NetEnv", api_data["name"])
        controller.init()

        try:
            controller.validate()
        except StackException as e:
            aim_ctx.log("Error: " + e.response['code'] + ": " + e.response['message'])
            aim_ctx.log(e.get_error_str())


        #net_env_config.set_config(new_env_config["config"])

        # {
        #     name: "",
        #     config: {
        #          ... config/NetworkEnvironments/<name>/<name>.yml ...
        #     }
        # }
