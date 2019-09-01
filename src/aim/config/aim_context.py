import os
import aim.config.aws_credentials
import aim.core.log
import aim.controllers
import aim.models.services
import pkg_resources
from aim.models import load_project_from_yaml
from aim.models import references
from aim.config import ConfigProcessor
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.models import vocabulary
from aim.models.references import Reference

class AccountContext(object):

    def __init__(self,
                 aim_ctx,
                 name,
                 mfa_account = None):
        self.name = name
        self.client_cache = {}
        self.resource_cache = {}
        self.aim_ctx = aim_ctx
        if name in aim_ctx.project['accounts'].keys():
            self.config = aim_ctx.project['accounts'][name]
        else:
            self.config = None
        self.mfa_account = mfa_account
        self.aws_session = None
        cache_filename = '-'.join(['aim', aim_ctx.project.name, 'account', self.name])
        self.cli_cache = os.path.join(os.path.expanduser('~'),
                                      '.aws/cli/cache',
                                      cache_filename)
        admin_creds = self.aim_ctx.project['credentials']
        self.admin_iam_role_arn = 'arn:aws:iam::{}:role/{}'.format(
                admin_creds.master_account_id,
                admin_creds.admin_iam_role_name
            )
        if name == "master":
            self.get_mfa_session(admin_creds)

    def get_name(self):
        return self.name

    def gen_ref(self):
        return 'aim.ref account.%s' % (self.get_name())

    def get_temporary_credentials(self):
        return self.aws_session.get_temporary_credentials()

    def get_mfa_session(self, admin_creds):
        if self.aws_session == None:
            self.aws_session = aim.config.aws_credentials.Sts(
                self,
                temporary_credentials_path=self.cli_cache,
                mfa_arn=admin_creds.mfa_role_arn,
                admin_creds=admin_creds,
                admin_iam_role_arn=self.admin_iam_role_arn
            )

        return self.aws_session.get_temporary_session()

    def get_session(self):
        if self.aws_session == None:
            self.aws_session = aim.config.aws_credentials.Sts(
                    self,
                    temporary_credentials_path=self.cli_cache,
                    mfa_account=self.mfa_account,
                    admin_iam_role_arn=self.admin_iam_role_arn
            )

        return self.aws_session.get_temporary_session()

    @property
    def id(self):
        return self.config.account_id

    def get_id(self):
        return self.config.account_id

    def get_aws_client(self, client_name, aws_region=None, client_config=None):
        client_id = client_name
        if aws_region != None:
            client_id += aws_region
        if client_id not in self.client_cache.keys():
            session = self.get_session()
            self.client_cache[client_id] = session.client(
                client_name, region_name=aws_region, config=client_config)
        return self.client_cache[client_id]

    def get_aws_resource(self, resource_name, aws_region=None, resource_config=None):
        if resource_name not in self.resource_cache.keys():
            session = self.get_session()
            self.resource_cache[resource_name] = session.resource(
                resource_name, region_name=aws_region, config=resource_config)
        return self.resource_cache[resource_name]


# ----------------------------------------------------------------------------------
class AimContext(object):

    def __init__(self, home=None):
        self.home = home
        self.verbose = False
        self.nocache = False
        self.aim_path = os.getcwd()
        self.build_folder = None
        self.aws_name = "AIM"
        self.controllers = {}
        self.services = {}
        self.accounts = {}
        self.logger = aim.core.log.get_aim_logger()
        self.project = None
        self.master_account = None

    def get_account_context(self, account_ref=None, account_name=None, netenv_ref=None):
        if account_ref != None:
            ref = Reference(account_ref)
            account_name = ref.parts[1]
        elif netenv_ref != None:
            account_ref = netenv_ref.split(' ')[1]
            account_ref = 'aim.ref netenv.'+'.'.join(account_ref.split('.', 4)[:-1])+".network.aws_account"
            account_ref = self.get_ref(account_ref)
            return self.get_account_context(account_ref=account_ref)
        elif account_name == None:
            raise StackException(AimErrorCode.Unknown, message = "get_account_context was only passed None: Not enough context to get account.")

        if account_name in self.accounts:
            return self.accounts[account_name]

        account_ctx = AccountContext(aim_ctx=self,
                                     name=account_name,
                                     mfa_account=self.master_account)

        return account_ctx

    def get_region_from_ref(self, netenv_ref):
        region = netenv_ref.split(' ')[1]
        # aimdemo.dev.us-west-2.applications
        region = region.split('.')[3]
        if region not in vocabulary.aws_regions.keys():
            return None
        return region

    def load_project(self, project_init=False):
        print("Project: %s" % (self.home))
        self.project_folder = self.home
        if project_init == True:
            return

        # Config Processor Init
        self.config_processor = ConfigProcessor(self)
        self.project = load_project_from_yaml(self.project_folder, None) #self.config_processor.load_yaml)
        self.build_folder = os.path.join(self.home, "build", self.project.name)
        self.master_account = AccountContext(aim_ctx=self,
                                             name='master',
                                             mfa_account=None)
        # Set Default AWS Region
        os.environ['AWS_DEFAULT_REGION'] = self.project['credentials'].aws_default_region

        # Initialize Controllers so they can initiaize their
        # resolve_ref_obj's to allow reference lookups
        self.get_controller('Route53')
        self.get_controller('CodeCommit')
        self.get_controller('S3').init({'name': 'buckets'})

        # Load the Service Plugins
        service_plugins = aim.models.services.list_service_plugins()
        for plugin_name, plugin_module in service_plugins.items():
            try:
                print("Init: Service Plugin: %s" % (plugin_name))
                service = plugin_module.instantiate_class(self, self.project['service'][plugin_name.lower()])
                service.init(None)
                self.services[plugin_name.lower()] = service
                print("Init: Service Plugin: %s: Completed" % (plugin_name))
            except KeyError:
                # ignore if no config files for a registered service
                print("Skipping Service: {}".format(plugin_name))

    def get_controller(self, controller_type, controller_args=None):
        """Gets a controller by name and calls .init() on it with any controller args"""
        controller_type = controller_type.lower()
        controller = None
        if controller_type != 'service':
            if controller_type in self.controllers:
                controller = self.controllers[controller_type]
            if controller == None:
                controller = aim.controllers.klass[controller_type](self)
                self.controllers[controller_type] = controller
        else:
            service_name = controller_args['arg_1']
            if service_name.lower() not in self.services:
                message = "Could not find Service: {}".format(service_name)
                raise StackException(AimErrorCode.Unknown, message = message)
            controller = self.services[service_name.lower()]

        controller.init(controller_args)
        return controller

    def log(self, msg, *args):
        """Logs a message to aim logger."""
        if args:
            msg %= args
        self.logger.info(msg)
        print(msg)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def get_stack_filename(self, stack_group_type, stack_type):
        return os.path.join(self.stacks_folder, stack_group_type+"/"+stack_type+".yml")

    def get_ref(self, aim_ref, account_ctx=None):
        """Takes an AIM reference string (aim.ref <type>.<part>) and returns
        the object or value that is being referenced.

        Note that for `aim.ref accounts.<account-name>` references, the acount id is returned
        and not the object.
        """
        return references.resolve_ref(
            aim_ref,
            self.project,
            account_ctx=account_ctx
        )

    def input(self,
                prompt,
                default=None,
                yes_no_prompt=False,
                allowed_values=None,
                return_bool_on_allowed_value=False,
                case_sensitive=True):

        try_again = True
        while try_again:
            suffix = ": "
            if yes_no_prompt == True:
                suffix += "Y/N: "
                if default == None:
                    default = "N"
            if default != None:
                suffix += "[%s]: " % str(default)

            value = input(prompt+suffix) or default

            if yes_no_prompt == True:
                if value == None:
                    return False
                if value.lower() == "y" or value.lower() == "yes":
                    return True
                elif value.lower() == "n" or value.lower() == "no":
                    return False
                else:
                    print("Invalid response: %s: Try again." % (value))
                    continue

            if allowed_values != None:
                for allowed_value in allowed_values:
                    value_match = False
                    if isinstance(value, str) and case_sensitive == False:
                        if allowed_value.lower() == value.lower():
                            value_match = True
                    elif allowed_value == value:
                        value_match = True
                    if value_match == True:
                        if return_bool_on_allowed_value == True:
                            return True
                        else:
                            return value
                print("Invalid value: %s" % (value))
                print("Allowed values: %s\n" % ', '.join(allowed_values))
                continue

            try_again = False
        return value
