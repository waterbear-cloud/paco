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
        self.init_accounts_cache_id = "20190612"
        self.master_account_ctx = None
        self.master_account_config = None

        #self.aim_ctx.log("AWS Account Service")

    def validate(self):
        self.master_stack_group.validate()
        for stack_group in self.org_stack_group_list:
            stack_group.validate()

    def provision(self):
        self.master_stack_group.provision()
        for stack_group in self.org_stack_group_list:
            stack_group.provision()

    def delete(self):
        self.master_stack_group.delete()
        for stack_group in self.org_stack_group_list:
            stack_group.delete()

    def cache_id(self, hook, hook_arg):
        return self.init_accounts_cache_id

    def init(self, config_arg):
        # Get the master account config
        self.master_account_config = None
        for account_id in self.aim_ctx.project['accounts']:
            account_config = self.aim_ctx.project['accounts'][account_id]
            if account_config.is_master == True:
                self.master_account_config = account_config
                master_account_id = account_id
                self.master_account_ctx = self.aim_ctx.get_account_context(account_name=account_id)
                break

        if self.master_account_config == None:
            raise StackException(AimErrorCode.Unknown)

        # Master account goes first
        # Setup stack hooks to call the AWS Organization setup method
        stack_hooks = StackHooks(self.aim_ctx)
        stack_hooks.add('AccountInit', 'create', 'post',
                        self.init_accounts_stack_hook, self.cache_id)
        stack_hooks.add('AccountInit', 'update', 'post',
                        self.init_accounts_stack_hook, self.cache_id)

        self.master_stack_group = AccountStackGroup(self.aim_ctx,
                                                    self.master_account_ctx,
                                                    master_account_id,
                                                    self.master_account_config,
                                                    stack_hooks,
                                                    self)
        self.master_stack_group.init(do_not_cache=True)

    def init_org_accounts(self, org_client):
        # Next we process the Master account's organization accounts
        for org_account_id in self.master_account_config.organization_account_ids:
            # Check if things already exist
            # Config Check
            config_exists = False
            account_config = None
            if org_account_id in self.aim_ctx.project['accounts']:
                config_exists = True
                account_config = self.aim_ctx.project['accounts'][org_account_id]

            # Account Check
            org_account_list = org_client.list_accounts()
            account_exists = False
            aws_account_id = None
            for account_info in org_account_list['Accounts']:
                if account_info['Name'] == org_account_id:
                    account_exists = True
                    aws_account_id = account_info['Id']
                    break
            if config_exists == True and account_exists == True:
                print("Organization Account and Config already exist, skipping: %s" % (org_account_id))
                continue

            if config_exists == False:
                print("Initializing Organization Account Configuration: %s\n" % (org_account_id))
                correct_value = False
                while correct_value == False:
                    # Ask for Each Account Input
                    account_config = {
                        'account_type': 'AWS',
                        'admin_delegate_role_name': 'Waterbear-Cloud-Admin-Delegate-Role',
                        'region': None,
                        'name': None,
                        'title': None,
                        'root_email': None,
                    }
                    account_defaults = {
                        'name': None,
                        'title': None,
                        'region': None,
                        'root_email': None,
                    }
                    if org_account_id in self.aim_ctx.project['accounts']:
                        yesno = self.aim_ctx.input("Configuration already exists, skip?", yes_no_prompt=True)
                        if yesno == True:
                            # Break out of the while loop and onto the next account id
                            break
                        account_config = project['accounts'][org_account_id]
                        account_defaults['name'] = account_config['name']
                        account_defaults['title'] = account_config['title']
                        account_defaults['region'] = account_config['region']
                    account_config['name'] = self.aim_ctx.input("  Friendly name", account_defaults['name'])
                    account_config['title'] = self.aim_ctx.input("  Title", account_defaults['title'])
                    account_config['region'] = self.aim_ctx.input("  Region", account_defaults['region'])
                    account_config['root_email'] = self.aim_ctx.input("  Root email address", account_defaults['root_email'])

                    # Verify the information collected
                    print("\n%s: Account Configuration\n" % (org_account_id))
                    yaml.dump(account_config, sys.stdout)
                    print("")
                    correct_value = self.aim_ctx.input("Is this the correct configuration for: %s ?" % (org_account_id),
                                                        yes_no_prompt=True)

                # Create the account unter the Organization
                if account_exists == False:
                    print("Creating account: %s" % (org_account_id))
                    try:
                        account_status = org_client.create_account( Email=account_config['root_email'],
                                                                AccountName=org_account_id,
                                                                RoleName=account_config['admin_delegate_role_name'] )

                    except ClientError as e:
                        if e.response['Error']['Message'] == 'You have exceeded the allowed number of AWS accounts.':
                            print("Error: The number of AWS Accounts limit has been reached, contact AWS support to increase.")
                            sys.exit(1)
                    print("Account status:\n")
                    yaml.dump(account_status, sys.stdout)
                    print("")

                    # account_config['account_id'] = account_status['CreateAccountStatus']
                else:
                    account_config['account_id'] = aws_account_id

                # Save account config to yaml
                account_yaml_path = os.path.join(self.aim_ctx.project_folder, 'Accounts', org_account_id+".yaml")
                with open(account_yaml_path, "w") as output_fd:
                    yaml.dump(data=account_config,
                                stream=output_fd)

            # Wait for account creation to complete

            # Initialize Account CloudFormation stacks
            org_account_ctx = self.aim_ctx.get_account_context(account_name=org_account_id)
            org_account_config = self.aim_ctx.project['accounts'][org_account_id]
            stack_group = AccountStackGroup(self.aim_ctx,
                                            org_account_ctx,
                                            org_account_id,
                                            org_account_config,
                                            self)
            self.org_stack_group_list.append(stack_group)
            stack_group.init()

    def init_accounts_stack_hook(self, hook, hook_arg):
        org_client = self.master_account_ctx.get_aws_client('organizations')
        # Create Organization
        try:
            account_info = org_client.describe_account(AccountId=self.master_account_ctx.get_id())
        except org_client.exceptions.AWSOrganizationsNotInUseException as e:
            print("Creating Master AWS Organization,")
            org_client.create_organization(FeatureSet='ALL')
        else:
            print("Master AWS Organization already created.")

        # Loop through
        self.init_org_accounts(org_client)

    def get_value_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.aim_ref.parse_ref(aim_ref)
        ref_parts = ref_dict['ref_parts']
        config_ref = ref_dict['ref']

        raise StackException(AimErrorCode.Unknown)
