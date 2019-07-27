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
from aim.core.yaml import YAML
from cookiecutter.main import cookiecutter
from jinja2.ext import Extension


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

    def init(self, controller_args):
        if self.init_done == True:
            return
        self.init_done = True

    def init_command(self, controller_args):
        use_cookie_cutter = True
        # TODO: project_component == 'credentials' so we can: aim init project credentials
        #project_component = controller_args['arg_1']
        if use_cookie_cutter == True:
            print("\nAIM Project initialization")
            print("--------------------------\n")
            print("About to create a new AIM Project directory at {}\n".format(os.getcwd()))
            cookiecutter(os.path.join(os.path.dirname(__file__), '../commands', 'aim-cookiecutter'))
        else:
            project_name = controller_args['arg_1']
            project_folder = controller_args['arg_2']

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

            try:
                os.chmod(credentials_path, stat.S_IRWXU)
            except FileNotFoundError:
                pass

            pathlib.Path(project_folder).mkdir(parents=True, exist_ok=True)
            with open(credentials_path, "w") as output_fd:
                yaml.dump(data=self.credentials,
                        stream=output_fd)

            os.chmod(credentials_path, stat.S_IRUSR)



