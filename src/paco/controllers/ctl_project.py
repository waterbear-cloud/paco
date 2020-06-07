import click
import importlib
import os
import pathlib
import stat
import sys
import time
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.controllers.controllers import Controller
from paco.models import loader, vocabulary
from paco.core.yaml import YAML
from paco.utils import enhanced_input
from cookiecutter.main import cookiecutter
from jinja2.ext import Extension


yaml=YAML()
yaml.default_flow_sytle = False

prompt_help_mapping = {
    'project_title': "Project title - Describe this Paco project",
    'budget': "Budget - Lower cost but less robust set-up?",
    'network_environment_name': "NetworkEnvironment name - Short alphanumeric string to identify a network environment",
    'network_environment_title': "NetworkEnvironment title - Long description for a network environment",
    'application_name': "Application name - Short alphanumeric string to identify this application",
    'application_title': "Application title - Long description for this application",
    'aws_default_region': "AWS Region name - e.g. us-west-2, us-east-1 or ca-central-1",
    'aws_default_region_allowed_values': vocabulary.aws_regions.keys(),
    'master_account_id': "AWS account id this project will connect to",
    'master_root_email': "Root email for the AWS account",

    # multi-account prompts
    'dev_account': "Development account name - e.g. dev or devstage",
    'staging_account': "Staging account name - e.g. staging or devstage",
    'prod_account': "Production account name - e.g. prod",
    'tools_account': "Tools account name - e.g. tools",
    'admin_username': "Administrator name - access to AWS and CodeCommit repo",
    'admin_email': "Administrator email",
    'admin_ssh_public_key': "Administrator SSH Public key",
    'domain_name': "Domain Name",

    # multi-region prompts
    'aws_second_region': "Second AWS Region name - e.g. us-west-2, us-east-1 or ca-central-1",
    'aws_second_region_allowed_values': vocabulary.aws_regions.keys(),

}

class ProjectController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "Project",
            ""
        )
        self.init_done = False
        self.credentials_path = self.paco_ctx.home / '.credentials.yaml'
        self.credentials = {
            'aws_access_key_id': None,
            'aws_secret_access_key': None,
            'aws_default_region': None,
            'master_account_id': None,
            'master_admin_iam_username': None
        }

    def init(self, command=None, model_obj=None):
        if self.init_done == True:
            return
        self.init_done = True

    def choose_template(self, starting_templates):
        "Ask user to choose a Paco project template"
        print("Choose a starter project template:\n")
        index = 1
        index_dict = {}
        for name, info in starting_templates.items():
            title = info[1]
            description = info[2]
            print(f"{index}: {title}:\n   {description}\n")
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
        "Create a Paco project skeleton from a template"
        starting_templates = {
            'wordpress-single-tier': ("wordpresssingletier", "WordPress Single-Tier", "A single-tier WordPress application."),
            'managed-webapp-cicd': ("managedwebappcicd", "Managed WebApp with CI/CD", "A managed web application with CI/CD and dev/staging/prod environments."),
            's3lambda': ("s3lambda", "S3 Bucket Lambda replicator", "An S3 Bucket that notifies a Lambda which replicates additions/deletions to S3 Bucket(s) in other regions."),
            'privatepypi': ("privatepypi", "Private PyPI server", "Private PyPI server with EFS filesystem behind a shared ALB."),
            'simple-web-app': ("simplewebapp", "Empty skeleton project", "A minimal skeleton to be used as boilerplate for a from-scratch project."),
        }
        print("\nPaco project initialization")
        print("---------------------------\n")
        if self.paco_ctx.home.exists():
            print("Directory at {} already exists.\n".format(self.paco_ctx.home))
        else:
            print("A Paco project is a directory of YAML files that describes a cloud architecture,")
            print("it's configuration and automation.\n")
            print("This command will create a new ready-to-run Paco project. Choose a starter project,")
            print("answer some quesetions and a new Paco project directory will be created at:\n")
            print("%s\n" % self.paco_ctx.home)
            print("Important: You will be asked to supply names. Paco names are short, alphanumeric identifiers.")
            print("Paco uses these names when creating cloud resources. After you provision resources")
            print("with Paco it is not possible to change these names. You may also be asked for titles,")
            print("these can contain any characters (including spaces) and can be freely changed. Titles are used")
            print("to help you organize your configuration more descriptively.")
            print()
            print("(Press Ctrl-D to abort)\n")
            name = self.choose_template(starting_templates)
            packagename = starting_templates[name][0]
            allowed_key_list = []
            project_context = importlib.import_module('paco.cookiecutters.{}'.format(packagename)).get_project_context(self.paco_ctx)
            for key in project_context.keys():
                if key.startswith('_computed_'): continue
                if key.endswith('_allowed_values'): continue
                if key == 'project_name': continue
                allowed_key = key + "_allowed_values"
                allowed_values = None
                if allowed_key in project_context.keys():
                    allowed_values = project_context[allowed_key]
                    allowed_key_list.append(allowed_key)
                project_context[key] = enhanced_input(
                    prompt_help_mapping[key],
                    default=project_context[key],
                    allowed_values=allowed_values
                )

            project_context['_computed_paco_home_path'] = str(self.paco_ctx.home)
            project_context['master_admin_iam_username'] = 'paco-project-init'
            # Remove the allowed key so we do not save it to the context file
            for key in allowed_key_list:
                del project_context[key]

            # Massage account names into a de-duplicated list
            accounts = {}
            for key, value in project_context.items():
                if key.endswith('_account'):
                    accounts[value] = None
            project_context['accounts'] = ''
            for key in accounts.keys():
                project_context['accounts'] += '  - ' + key + '\n'

            # short region name for second region  (s3lambda)
            if 'aws_second_region' in project_context:
                project_context['short_region_list'] = vocabulary.aws_regions[
                    project_context['aws_second_region']
                ]['short_name']

            # budget Y or N to True or False
            if 'budget' in project_context:
                if project_context['budget'].lower().startswith('y'):
                    project_context['budget'] = True
                else:
                    project_context['budget'] = False

            cookiecutter(
                os.path.join(os.path.dirname(__file__), '..', 'cookiecutters', packagename),
                no_input=True,
                extra_context=project_context
            )

            # create the .gitignore seperately that filename can't be nested in git repo
            # tried using {{['.gitignore']|join}} but the | character is a problem on Windows filesystems
            fh = open(self.paco_ctx.home / '.gitignore', 'w')
            fh.write(".credentials.yaml\n")
            fh.write(".credentials.yml\n")
            fh.write(".paco-work/build/\n")
            fh.close()

            print("\n\nPaco project created at:\n")
            print("%s\n" % self.paco_ctx.home)
            print("It is recommended to export the PACO_HOME environment variable to tell Paco")
            print("where your active Paco project is located, although you can also use the")
            print("`paco --home=/your/path` flag. Consider adding this to your BASH profile.\n")
            print("export PACO_HOME=%s\n" % self.paco_ctx.home)


    def init_credentials(self, force=False):
        "Create a .credentials file for a Paco project"
        print("\nPaco project credentials initialization")
        print("---------------------------------------\n")

        if self.credentials_path.exists() and force == False:
            print("A .credentials file already exists at:\n{}.credentials\n".format(self.paco_ctx.home))
            sys.exit()

        master = self.paco_ctx.project['accounts']['master']
        self.credentials['aws_default_region'] = master.region
        self.credentials['master_account_id'] = master.account_id
        self.credentials['master_admin_iam_username'] = enhanced_input("Paco Admin Username", default='paco-admin')
        self.credentials['admin_iam_role_name'] = 'Paco-Admin-Delegate-Role'
        self.credentials['aws_access_key_id'] = enhanced_input("AWS Access Key")
        self.credentials['aws_secret_access_key']  = enhanced_input("AWS Secret Key")
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

        print("Paco credentials file created at:\n")
        print( "%s\n" % self.credentials_path)
        print("It is NOT recommended to store this file in version control.")
        print("Paco starter project include a .gitignore file to prevent this.")
        print("You can store this file in a secrets mananger or re-create it again")
        print("by generating a new AWS Api Key for the Paco Admin User and re-running")
        print("this 'paco init credentials' command.\n")

    def init_accounts(self):
        "Initialize Accounts"
        accounts_dir = os.path.join(str(self.paco_ctx.home), 'Accounts')
        master_account_file = loader.gen_yaml_filename(accounts_dir, 'master')
        with open(master_account_file, 'r') as stream:
            master_account_config = yaml.load(stream)

        print("\nAWS Account Initialization")
        print("---------------------------\n")
        if 'organization_account_ids' in master_account_config.keys():
            print("AWS Organization account names have already been defined: {}".format(','.join(master_account_config['organization_account_ids'])))
        else:
            print("Enter a comma delimited list of account names to add to this project:")
            account_ids = enhanced_input("Account Names: ", 'prod,tools,security,data,dev')
            master_account_config['organization_account_ids'] = account_ids.split(',')
            with open(master_account_file, 'w') as stream:
                yaml.dump(master_account_config, stream)

        # Loading the account controller will initialize the account yamls
        account_ctl = self.paco_ctx.get_controller('account')
        account_ctl.init_accounts_yaml()

    def provision(self):
        account_ctl = self.aim_ctx.get_controller('account')
        account_ctl.provision()
        print("\nProject Provisioning Complete")

    def validate(self):
        account_ctl = self.aim_ctx.get_controller('account')
        account_ctl.validate()

