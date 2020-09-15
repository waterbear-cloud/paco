import click
import os, sys, time
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.controllers.controllers import Controller
from paco.stack import StackHooks
from paco.stack_grps.grp_account import AccountStackGroup
from paco.models import loader
from botocore.exceptions import ClientError
from paco.core.yaml import YAML
from paco.utils import enhanced_input

yaml=YAML()
yaml.default_flow_sytle = False


class AccountController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "Account", "")
        self.master_stack_group = None
        self.org_stack_group_list = []
        self.init_done = False
        self.init_accounts_cache_id = "20190613"
        self.master_account_ctx = None
        self.master_account_config = None
        # Load the master account config
        for account_name in self.paco_ctx.project['accounts'].keys():
            account_config = self.paco_ctx.project['accounts'][account_name]
            if account_config.is_master == True:
                self.master_account_config = account_config
                self.master_account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
                break

    def validate(self):
        self.init_master_stack_group()
        self.master_stack_group.validate()
        for stack_group in self.org_stack_group_list:
            stack_group.validate()

    def provision(self):
        self.provision_organization()
        self.init_master_stack_group()
        self.master_stack_group.provision()
        for stack_group in self.org_stack_group_list:
            stack_group.provision()

    def delete(self):
        self.init_master_stack_group()
        self.master_stack_group.delete()
        for stack_group in self.org_stack_group_list:
            stack_group.delete()

    def cache_id(self, hook, hook_arg):
        return self.init_accounts_cache_id

    def init(self, command=None, model_obj=None):
        if self.master_account_config == None:
            raise StackException(PacoErrorCode.Unknown)

    def init_master_stack_group(self):
        "Master account is first"
        self.master_stack_group = AccountStackGroup(
            self.paco_ctx,
            self.master_account_ctx,
            'master',
            self.master_account_config,
            None,
            self
        )
        self.master_stack_group.init(do_not_cache=True)
        self.init_organization_stack_groups()

    def get_account_default(self, key, arg_1=None):
        account_defaults = {
            'name': {
                'prod': 'Production',
                'dev': 'Development',
                'security': 'Security',
                'data': 'Data',
                'tools': 'Tools'
            },
            'title': {
                'prod': 'Production AWS Account',
                'dev': 'Development AWS Account',
                'security': 'Security AWS Account',
                'data': 'Data AWS Account',
                'tools': 'Tools AWS Account'
            },
            'region': self.master_account_config.region,
            'root_email': None,
        }
        if key == 'name' or key == 'title':
            if arg_1 in account_defaults[key].keys():
                return account_defaults[key][arg_1]
        else:
            return account_defaults[key]

    def init_accounts_yaml(self):
        """Process master account file and and create child account YAML files for the organization_account_ids
field, if the child account YAML does not already exist."""
        for org_account_id in self.master_account_config.organization_account_ids:
            # If account YAML already exists then skip it
            if org_account_id in self.paco_ctx.project['accounts'].keys():
                continue

            # Account Check
            print("\nInitializing Account Configuration: %s\n" % (org_account_id))
            account_config = None
            correct_value = False
            while correct_value == False:
                # Ask for Each Account Input
                account_config = {
                    'account_type': 'AWS',
                    'region': None,
                    'title': None,
                    'root_email': None,
                }
                name_defaults = {
                    'prod': 'Production',
                    'dev': 'Development',
                }
                account_config['title'] = enhanced_input("  Title", self.get_account_default('title', org_account_id))
                account_config['region'] = enhanced_input("  Region", self.get_account_default('region'))
                account_config['root_email'] = enhanced_input("  Root email address")

                # Verify the information collected
                print("\n--- %s Configuration ---" % org_account_id)
                yaml.dump(account_config, sys.stdout)
                print("---\n")
                correct_value = self.paco_ctx.input_confirm_action(
                    "Is this the correct configuration for %s ?" % (org_account_id)
                )

                # Save account config to yaml
                account_yaml_path = self.paco_ctx.home / 'Accounts' / (org_account_id + ".yaml")
                with open(account_yaml_path, "w") as stream:
                    yaml.dump(data=account_config, stream=stream)

    def init_organization_stack_groups(self):
        "Process the Master account's organization accounts"
        for org_account_id in self.master_account_config.organization_account_ids:
            org_account_ctx = self.paco_ctx.get_account_context(account_name=org_account_id)
            org_account_config = self.paco_ctx.project['accounts'][org_account_id]
            stack_group = AccountStackGroup(
                self.paco_ctx,
                org_account_ctx,
                org_account_id,
                org_account_config,
                stack_hooks=None,
                controller=self
            )
            self.org_stack_group_list.append(stack_group)
            stack_group.init()

    def provision_organization_accounts(self, org_client):
        "Process the Master account's organization accounts"
        for org_account_id in self.master_account_config.organization_account_ids:
            # Check if things already exist
            # Config Check
            config_exists = False
            account_config = None
            account_yaml_path = loader.gen_yaml_filename(os.path.join(str(self.paco_ctx.home), 'Accounts'),  org_account_id)
            if org_account_id in self.paco_ctx.project['accounts'].keys():
                config_exists = True
                account_config = self.paco_ctx.project['accounts'][org_account_id]
                with open(account_yaml_path, "r") as stream:
                    account_config = yaml.load(stream)

            if config_exists == False:
                print("Missing account configuration for: %s" % org_account_id)
                sys.exit(1)

            # Defaults
            if 'admin_delegate_role_name' not in account_config:
                account_config['admin_delegate_role_name'] = 'Paco-Organization-Account-Delegate-Role'

            # Account Check
            org_account_list = org_client.list_accounts()
            account_exists = False
            aws_account_id = None
            for account_info in org_account_list['Accounts']:
                if account_info['Name'] == org_account_id:
                    account_exists = True
                    aws_account_id = account_info['Id']
                    break

            if account_exists == True:
                print("Account already exists: " + org_account_id)
                continue

            # Verify the information collected
            print("\n--- %s Configuration ---" % org_account_id)
            yaml.dump(account_config, sys.stdout)
            print("---\n")
            correct_value = self.paco_ctx.input_confirm_action(
                "Is this the correct configuration for '%s'?" % (org_account_id)
            )
            if correct_value == False:
                print("Configuration is not correct, aborted.\n")
                sys.exit()

            # Create the account under the Organization
            print("Creating account: %s" % (org_account_id))
            try:
                account_status = org_client.create_account(
                    Email=account_config['root_email'],
                    AccountName=org_account_id,
                    RoleName=account_config['admin_delegate_role_name']
                )
            except ClientError as e:
                if e.response['Error']['Message'] == 'You have exceeded the allowed number of AWS accounts.':
                    print("Error: The number of AWS Accounts limit has been reached, contact AWS support to increase.")
                    sys.exit(1)
                else:
                    print("Problem creating account. Possible timeout on new account and try again?\nError: {}".format(e))
                    sys.exit(1)
            print("Account status: %s\n" % account_status['CreateAccountStatus']['State'])
            while account_status['CreateAccountStatus']['State'] == 'IN_PROGRESS':
                print("{}: Waiting for account to be created: Status: {}".format(org_account_id, account_status['CreateAccountStatus']['State']))
                account_status = org_client.describe_create_account_status(
                    CreateAccountRequestId=account_status['CreateAccountStatus']['Id']
                )
                time.sleep(10)
            if account_status['CreateAccountStatus']['State'] == 'FAILED':
                print("ERROR: Create account FAILED: {}".format(account_status['CreateAccountStatus']['FailureReason']))
                sys.exit(1)
            account_config['account_id'] = account_status['CreateAccountStatus']['AccountId']
            print("Account created successfully.")

            # Save account config to yaml
            with open(account_yaml_path, "w") as stream:
                yaml.dump(
                    data=account_config,
                    stream=stream
                )

    def provision_organization(self):
        org_client = self.master_account_ctx.get_aws_client('organizations')
        # Create Organization
        try:
            account_info = org_client.describe_account(AccountId=self.master_account_ctx.get_id())
        except org_client.exceptions.AWSOrganizationsNotInUseException as e:
            print("Creating Master AWS Organization")
            org_client.create_organization(FeatureSet='ALL')
        else:
            print("Master AWS Organization already created.")

        self.provision_organization_accounts(org_client)
        self.paco_ctx.load_project()

