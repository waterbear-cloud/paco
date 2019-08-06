import click
import os, sys, time
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.stack_group import AccountStackGroup, StackHooks
from aim.models import loader
from botocore.exceptions import ClientError
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False


class AccountController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Account",
                         "")
        self.master_stack_group = None
        self.org_stack_group_list = []
        self.init_done = False
        self.init_accounts_cache_id = "20190613"
        self.master_account_ctx = None
        self.master_account_config = None
        # Load the master account config
        for account_id in self.aim_ctx.project['accounts'].keys():
            account_config = self.aim_ctx.project['accounts'][account_id]
            if account_config.is_master == True:
                self.master_account_config = account_config
                self.master_account_ctx = self.aim_ctx.get_account_context(account_name=account_id)
                break

        #self.aim_ctx.log("AWS Account Service")

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

    def init(self, controller_args):

        if self.master_account_config == None:
            raise StackException(AimErrorCode.Unknown)

        self.init_accounts_yaml()

    def init_master_stack_group(self):
        # Master account goes first
        self.master_stack_group = AccountStackGroup(self.aim_ctx,
                                                    self.master_account_ctx,
                                                    'master',
                                                    self.master_account_config,
                                                    None,
                                                    self)
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
        # Next we process the Master account's organization accounts
        for org_account_id in self.master_account_config.organization_account_ids:
            # Check if things already exist
            # Config Check
            account_config = None
            if org_account_id in self.aim_ctx.project['accounts'].keys():
                continue

            # Account Check
            print("\nInitializing Account Configuration: %s\n" % (org_account_id))
            correct_value = False
            while correct_value == False:
                # Ask for Each Account Input
                account_config = {
                    'account_type': 'AWS',
                    'admin_delegate_role_name': 'WaterbearCloud-AIM-Adminsitrator-Access-Role',
                    'region': None,
                    'name': None,
                    'title': None,
                    'root_email': None,
                }

                name_defaults = {
                    'prod': 'Production',
                    'dev': 'Development',
                }


                account_config['name'] = self.aim_ctx.input("  Friendly name", self.get_account_default('name', org_account_id))
                account_config['title'] = self.aim_ctx.input("  Title", self.get_account_default('title', org_account_id))
                account_config['region'] = self.aim_ctx.input("  Region", self.get_account_default('region'))
                account_config['root_email'] = self.aim_ctx.input("  Root email address")

                # Verify the information collected
                print("\n--- %s Configuration ---" % org_account_id)
                yaml.dump(account_config, sys.stdout)
                print("---\n")
                correct_value = self.aim_ctx.input("Is this the correct configuration for: %s ?" % (org_account_id),
                                                    yes_no_prompt=True)

                # Save account config to yaml
                account_yaml_path = os.path.join(self.aim_ctx.home, 'Accounts', org_account_id+".yaml")
                with open(account_yaml_path, "w") as stream:
                    yaml.dump(data=account_config,
                                stream=stream)

    def init_organization_stack_groups(self):
        # Next we process the Master account's organization accounts
        for org_account_id in self.master_account_config.organization_account_ids:
            org_account_ctx = self.aim_ctx.get_account_context(account_name=org_account_id)
            org_account_config = self.aim_ctx.project['accounts'][org_account_id]
            stack_group = AccountStackGroup(self.aim_ctx,
                                            org_account_ctx,
                                            org_account_id,
                                            org_account_config,
                                            stack_hooks=None,
                                            controller=self)
            self.org_stack_group_list.append(stack_group)
            stack_group.init()

    def provision_organization_accounts(self, org_client):
        # Next we process the Master account's organization accounts
        for org_account_id in self.master_account_config.organization_account_ids:
            # Check if things already exist
            # Config Check
            config_exists = False
            account_config = None
            account_yaml_path = loader.gen_yaml_filename(os.path.join(self.aim_ctx.home, 'Accounts'),  org_account_id)
            if org_account_id in self.aim_ctx.project['accounts'].keys():
                config_exists = True
                account_config = self.aim_ctx.project['accounts'][org_account_id]
                with open(account_yaml_path, "r") as stream:
                    account_config = yaml.load(stream)

            if config_exists == False:
                print("Missing account configuration for: %s" % org_account_id)
                sys.exit(1)

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
            correct_value = self.aim_ctx.input("Is this the correct configuration for '%s'?" % (org_account_id),
                                                yes_no_prompt=True)

            if correct_value == False:
                print("Configuration is not correct, skipping...\n")
                continue
            # Create the account unter the Organization
            print("Creating account: %s" % (org_account_id))
            try:
                account_status = org_client.create_account( Email=account_config['root_email'],
                                                        AccountName=org_account_id,
                                                        RoleName=account_config['admin_delegate_role_name'] )

            except ClientError as e:
                if e.response['Error']['Message'] == 'You have exceeded the allowed number of AWS accounts.':
                    print("Error: The number of AWS Accounts limit has been reached, contact AWS support to increase.")
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
        self.aim_ctx.load_project()

