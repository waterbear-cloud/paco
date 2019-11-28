import click
import os
import time
import stat
import pathlib
import sys
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.controllers.controllers import Controller
from paco.stack_grps.grp_account import AccountStackGroup
from paco.models import loader, vocabulary
from paco.core.yaml import YAML
from cookiecutter.main import cookiecutter
from jinja2.ext import Extension


yaml=YAML()
yaml.default_flow_sytle = False


class ProjectController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "Project",
            ""
        )
        self.init_done = False
        self.credentials_path = pathlib.Path(os.path.join(self.paco_ctx.home, '.credentials.yaml'))
        self.credentials = {
            'aws_access_key_id': None,
            'aws_secret_access_key': None,
            'aws_default_region': None,
            'master_account_id': None,
            'master_admin_iam_username': None
        }
        self.project_context_path = pathlib.Path(os.path.join(self.paco_ctx.home, '.project_context.yaml'))

        self.project_context = {
            'project_name': os.path.basename(os.path.normpath(self.paco_ctx.home)),
            'project_title': None,
            'network_environment_name': None,
            'network_environment_title': None,
            'application_name': None,
            'application_title': None,
            'aws_default_region': None,
            'aws_default_region_allowed_values': vocabulary.aws_regions.keys(),
            'master_account_id': None,
            'master_root_email': None,
        }
        if self.project_context_path.exists():
            self.load_project_context()

    def load_project_context(self):
        with self.project_context_path.open('r') as stream:
            context = yaml.load(stream)

        for key in self.project_context.keys():
            if key in context.keys():
                self.project_context[key] = context[key]

    def init(self, command=None, model_obj=None):
        if self.init_done == True:
            return
        self.init_done = True

    def choose_template(self, starting_templates):
        print("Choose a starting project template:\n")
        index = 1
        index_dict = {}
        for name, description in starting_templates.items():
            print(f"{index}: {name}\n   {description}")
            index_dict[str(index)] = name
            index += 1

        while True:
            answer = input("\nEnter a number or name: ")
            if answer in starting_templates:
                return answer
            if answer in index_dict:
                return index_dict[answer]
            print("Not a valid selection.")


    def init_project(self):
        starting_templates = {
            'simple-web-app': "A minimal skeleton with a simple web application.",
            'wordpress-single-tier': "A single-tier WordPress application.",
        }
        print("\nPaco project initialization")
        print("---------------------------\n")
        if self.project_context_path.exists() == True:
            print("Paco project has already been initialized.\n")
        else:
            print("About to create a new Paco project directory at %s\n" % self.paco_ctx.home)
            cookiecutter_project = self.choose_template(starting_templates)
            allowed_key_list = []
            for key in self.project_context.keys():
                if key.startswith('_computed_'): continue
                if self.project_context[key] == None:
                    allowed_key = key + "_allowed_values"
                    allowed_values = None
                    if allowed_key in self.project_context.keys():
                        allowed_values = self.project_context[allowed_key]
                        allowed_key_list.append(allowed_key)
                    self.project_context[key] = self.paco_ctx.input("%s" % key, allowed_values=allowed_values)

            self.project_context['_computed_paco_home_path'] = self.paco_ctx.home
            self.project_context['master_admin_iam_username'] = 'paco-project-init'
            # Remove the allowed key so we do not save it to the context file
            for key in allowed_key_list:
                del self.project_context[key]
            cookiecutter(
                os.path.join(os.path.dirname(__file__), '..', 'cookiecutters', cookiecutter_project),
                no_input=True,
                extra_context=self.project_context
            )

            # Save the project context
            with self.project_context_path.open(mode="w") as stream:
                yaml.dump(
                    data=self.project_context,
                    stream=stream
                )

    def init_credentials(self, force=False):
        print("\nPaco project credentials initialization")
        print("---------------------------------------\n")
        if self.project_context_path.exists() == False:
            print("Project does not exist: {}".format(self.project_context_path))
            print("Run this command to initialize a project:\n\npaco init project")
            sys.exit(1)

        if self.credentials_path.exists() and force == False:
            print("Credentials already exist, run this command to reinitialize:\n")
            print("paco init project credentials\n")
            return

        self.credentials['aws_default_region'] = self.project_context['aws_default_region']
        self.credentials['master_account_id'] = self.project_context['master_account_id']
        self.credentials['master_admin_iam_username'] = self.paco_ctx.input("master_admin_iam_username")
        self.credentials['admin_iam_role_name'] = self.paco_ctx.input("admin_iam_role_name")
        self.credentials['aws_access_key_id'] = self.paco_ctx.input("aws_access_key_id")
        self.credentials['aws_secret_access_key']  = self.paco_ctx.input("aws_secret_access_key")
        self.credentials['mfa_session_expiry_secs'] = 43200
        self.credentials['assume_role_session_expiry_secs'] = 3600

        try:
            os.chmod(self.credentials_path, stat.S_IRWXU)
        except FileNotFoundError:
            pass

        with open(self.credentials_path, "w") as output_fd:
            yaml.dump(
                data=self.credentials,
                stream=output_fd
            )
        os.chmod(self.credentials_path, stat.S_IRUSR)

    def init_accounts(self):
        # Initialize Accounts
        accounts_dir = os.path.join(self.paco_ctx.home, 'Accounts')
        master_account_file = loader.gen_yaml_filename(accounts_dir, 'master')
        with open(master_account_file, 'r') as stream:
            master_account_config = yaml.load(stream)

        print("\nAWS Account Initialization")
        print("---------------------------\n")
        if 'organization_account_ids' in master_account_config.keys():
            print("AWS Organization account names have already been defined: {}".format(','.join(master_account_config['organization_account_ids'])))
        else:
            print("Enter a comma delimited list of account names to add to this project:")
            account_ids = self.paco_ctx.input("Account Names: ", 'prod,tools,security,data,dev')
            master_account_config['organization_account_ids'] = account_ids.split(',')
            with open(master_account_file, 'w') as stream:
                yaml.dump(master_account_config, stream)

        self.paco_ctx.load_project()
        # Loading the account controller will initialize the account yamls
        account_ctl = self.paco_ctx.get_controller('account')
        account_ctl.init_accounts_yaml()


