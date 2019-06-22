import click
import os
import time
import stat
import pathlib
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.stack_group import AccountStackGroup
from aim.models import loader
from aim.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False


class ProjectController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Account",
                         "")
        self.init_done = False

        self.credentials = {
            'aws_access_key_id': None,
            'aws_secret_access_key': None,
            'aws_default_region': None,
            'master_account_id': None,
            'master_admin_iam_username': None
        }
        self.credentials_yaml_file = self.aim_ctx.project_folder

        #self.aim_ctx.log("AWS Account Service")

    def init(self, project_config):
        if self.init_done == True:
            return
        self.init_done = True

    def init_command(self, project_config):
        project_name = project_config['name']
        project_folder = project_config['folder']

        # Ask for and create .credentials.yaml
        print("Initialize Project: %s" % (project_name))
        print()
        print("Master Account Administrator Settings")

        self.credentials['aws_access_key_id']         = input("  Admin AWS Access Key ID     : ")
        self.credentials['aws_secret_access_key']     = input("  Admin AWS Secret Access Key : ")
        self.credentials['aws_default_region']        = input("  Admin Default AWS Region    : ")
        self.credentials['master_account_id']         = input("  Master AWS Account Id       : ")
        self.credentials['master_admin_iam_username'] = input("  Master Admin IAM Username   : ")

        project_folder = os.path.join(self.aim_ctx.aim_path, project_folder, project_name)
        credentials_path = os.path.join(project_folder, '.credentials.yaml')

        os.chmod(credentials_path, stat.S_IRWXU)

        pathlib.Path(project_folder).mkdir(parents=True, exist_ok=True)
        with open(credentials_path, "w") as output_fd:
            yaml.dump(data=self.credentials,
                      stream=output_fd)

        os.chmod(credentials_path, stat.S_IRUSR)



