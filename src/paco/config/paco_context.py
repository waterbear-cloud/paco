import paco.config.aws_credentials
import paco.core.log
import paco.controllers
import paco.models.services
import os, sys, re
import pathlib
import pkg_resources
import ruamel.yaml
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.models import vocabulary
from paco.models.references import Reference
from paco.models import references
from paco.models import load_project_from_yaml
from paco.core.yaml import read_yaml_file
from shutil import copyfile

# deepdiff turns on Deprecation warnings, we need to turn them back off
# again right after import, otherwise 3rd libs spam dep warnings all over the place
from deepdiff import DeepDiff
import warnings
warnings.simplefilter("ignore")


class AccountContext(object):
    "Manages the credentials and connection to an AWS Account"

    def __init__(
        self,
        paco_ctx,
        name,
        mfa_account=None
    ):
        self.name = name
        self.client_cache = {}
        self.resource_cache = {}
        self.paco_ctx = paco_ctx
        self.config = paco_ctx.project['accounts'][name]
        self.mfa_account = mfa_account
        self.aws_session = None
        self.temp_aws_session = None
        role_cache_filename = '-'.join(['paco', paco_ctx.project.name, self.name]) + '.role'
        cache_dir = pathlib.Path.home() / '.aws' / 'cli' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.role_cache_path = cache_dir / role_cache_filename
        session_cache_filename = '-'.join(['paco', paco_ctx.project.name]) + '.session'
        self.session_cache_path = cache_dir /session_cache_filename
        self.admin_creds = self.paco_ctx.project['credentials']

        # check that account_id has been set
        # account YAML files are created without an account_id until they are provisioned
        if self.config.account_id == None:
            print("""
The account '{}' is missing an account_id field.
Add this manually or run `paco provision accounts` for this project.
""".format(self.config.name)
            )
            sys.exit()

        self.admin_iam_role_arn = 'arn:aws:iam::{}:role/{}'.format(
            self.config.account_id,
            self.admin_creds.admin_iam_role_name
        )
        self.org_admin_iam_role_arn = 'arn:aws:iam::{}:role/{}'.format(
            self.config.account_id,
            self.config.admin_delegate_role_name
        )
        self.mfa_session_expiry_secs = self.admin_creds.mfa_session_expiry_secs
        self.assume_role_session_expiry_secs = self.admin_creds.assume_role_session_expiry_secs
        if name == "master":
            self.get_mfa_session(self.admin_creds)

    def get_name(self):
        return self.name

    def gen_ref(self):
        return 'paco.ref accounts.%s' % (self.get_name())

    def get_temporary_credentials(self):
        return self.aws_session.get_temporary_credentials()

    def get_mfa_session(self, admin_creds):
        if self.aws_session == None:
            self.aws_session = paco.config.aws_credentials.PacoSTS(
                self,
                session_creds_path=self.session_cache_path,
                role_creds_path=self.role_cache_path,
                mfa_arn=admin_creds.mfa_role_arn,
                admin_creds=admin_creds,
                admin_iam_role_arn=self.admin_iam_role_arn,
                org_admin_iam_role_arn=self.org_admin_iam_role_arn,
                mfa_session_expiry_secs=self.mfa_session_expiry_secs,
                assume_role_session_expiry_secs=self.assume_role_session_expiry_secs
            )
        return self.aws_session.get_temporary_session()

    def get_session(self, force=False):
        if self.aws_session == None:
            self.aws_session = paco.config.aws_credentials.PacoSTS(
                    self,
                    session_creds_path=self.session_cache_path,
                    role_creds_path=self.role_cache_path,
                    mfa_account=self.mfa_account,
                    admin_creds=self.admin_creds,
                    admin_iam_role_arn=self.admin_iam_role_arn,
                    org_admin_iam_role_arn=self.org_admin_iam_role_arn,
                    mfa_session_expiry_secs=self.mfa_session_expiry_secs,
                    assume_role_session_expiry_secs=self.assume_role_session_expiry_secs
            )
        if self.temp_aws_session == None or force == True:
            self.temp_aws_session = self.aws_session.get_temporary_session()

        return self.temp_aws_session

    @property
    def id(self):
        return self.config.account_id

    def get_id(self):
        return self.config.account_id

    def get_aws_client(self, client_name, aws_region=None, client_config=None, force=False):
        client_id = client_name
        if aws_region != None:
            client_id += aws_region
        if client_id not in self.client_cache.keys() or force == True:
            session = self.get_session(force)
            self.client_cache[client_id] = session.client(
                client_name, region_name=aws_region, config=client_config)
        return self.client_cache[client_id]

    def get_aws_resource(self, resource_name, aws_region=None, resource_config=None):
        resource_id = resource_name
        if aws_region != None:
            resource_id += aws_region
        if resource_id not in self.resource_cache.keys():
            session = self.get_session()
            self.resource_cache[resource_id] = session.resource(
                resource_name, region_name=aws_region, config=resource_config)
        return self.resource_cache[resource_id]


# deep diff formatting
def getFromSquareBrackets(s):
    return re.findall(r"\['?([A-Za-z0-9_]+)'?\]", s.replace('{', '').replace('}',''))

def print_diff_list(change_t, level=1):
    print('', end='\n')
    for value in change_t:
        print("  {}-".format(' '*(level*2)), end='')
        if isinstance(value, list) == True:
            print_diff_list(value, level+1)
        elif isinstance(value, dict) == True:
            print_diff_dict(value, level+1)
        else:
            print("  {}".format(value))

def print_diff_dict(change_t, level=1):
    print('', end='\n')
    for key, value in change_t.items():
        print("  {}{}:".format(' '*(level*2), key), end='')
        if isinstance(value, list) == True:
            print_diff_list(value, level+1)
        elif isinstance(value, dict) == True:
            print_diff_dict(value, level+1)
        else:
            print("  {}".format(value))

def print_diff_object(diff_obj, diff_obj_key):
    if diff_obj_key not in diff_obj.keys():
        return
    for root_change in diff_obj[diff_obj_key]:
        node_str = '.'.join(getFromSquareBrackets(root_change.path()))
        if diff_obj_key.endswith('_removed'):
            change_t = root_change.t1
        elif diff_obj_key.endswith('_added'):
            change_t = root_change.t2
        elif diff_obj_key == 'values_changed':
            change_t = root_change.t1
        elif diff_obj_key == 'type_changes':
            change_t = root_change.t1
        print("    ({}) {}".format(type(change_t).__name__, node_str))
        if diff_obj_key == 'values_changed':
            print("\told: {}".format(root_change.t1))
            print("\tnew: {}\n".format(root_change.t2))
        elif isinstance(change_t, list) == True:
            print_diff_list(change_t)
        elif isinstance(change_t, dict) == True:
            print_diff_dict(change_t)
        else:
            print("{}".format(change_t))
        print('')

def create_log_col(col='', col_size=0, message_len=0, wrap_text=False):
    if col == '' or col == None:
        return ' '*col_size
    message_spc = ' '*message_len

    if col.find('\n') != -1:
        message = col.replace('\n', '\n'+message_spc)
    elif wrap_text == True and len(col) > col_size:
        pos = col_size
        while pos < len(col):
            col = col[:pos] + '\n' + message_spc + col[pos:]
            pos += message_len + col_size
        message = col
    else:
        message = '{}{} '.format(col[:col_size], ' '*(col_size-len(col[:col_size])))
    return message


class PacoContext(object):
    """
    Contains `paco` CLI arguments and options and manages command-line interactions.
    """

    def __init__(self, home=None):
        self.home = home
        # CLI Flags
        self.verbose = False
        self.nocache = False
        self.yes = False
        self.quiet_changes_only = False
        self.paco_path = os.getcwd()
        self.build_folder = None
        self.aws_name = "Paco"
        self.controllers = {}
        self.services = {}
        self.accounts = {}
        self.logger = paco.core.log.get_paco_logger()
        self.project = None
        self.master_account = None
        self.command = None
        self.disable_validation = False

    def get_account_context(self, account_ref=None, account_name=None, netenv_ref=None):
        if account_ref != None:
            ref = Reference(account_ref)
            account_name = ref.parts[1]
        elif netenv_ref != None:
            account_ref = netenv_ref.split(' ')[1]
            account_ref = 'paco.ref netenv.'+'.'.join(account_ref.split('.', 4)[:-1])+".network.aws_account"
            account_ref = self.get_ref(account_ref)
            return self.get_account_context(account_ref=account_ref)
        elif account_name == None:
            raise StackException(PacoErrorCode.Unknown, message = "get_account_context was only passed None: Not enough context to get account.")

        if account_name in self.accounts:
            return self.accounts[account_name]

        account_ctx = AccountContext(
            paco_ctx=self,
            name=account_name,
            mfa_account=self.master_account
        )
        self.accounts[account_name] = account_ctx

        return account_ctx

    def get_region_from_ref(self, netenv_ref):
        region = netenv_ref.split(' ')[1]
        region = region.split('.')[3]
        if region not in vocabulary.aws_regions.keys():
            return None
        return region

    def load_project(self, project_init=False, project_only=False, master_only=False):
        "Load a Paco Project from YAML, initialize settings and controllers, and load Service plug-ins."
        self.project_folder = self.home
        if project_init == True:
            return

        # Load the model from YAML
        print("Loading Paco project: %s" % (self.home))
        self.project = load_project_from_yaml(self.project_folder, None)
        if project_only == True:
            return

        # Settings
        self.build_folder = os.path.join(self.home, "build", self.project.name)
        self.master_account = AccountContext(
            paco_ctx=self,
            name='master',
            mfa_account=None
        )
        os.environ['AWS_DEFAULT_REGION'] = self.project['credentials'].aws_default_region
        if master_only:
            return

        # Initialize Controllers so they can initialize their
        # resolve_ref_obj's to allow reference lookups
        self.get_controller('Route53')
        self.get_controller('CodeCommit')
        self.get_controller('S3').init({'name': 'buckets'})
        self.get_controller('NotificationGroups')

        # Load the Service plug-ins
        service_plugins = paco.models.services.list_service_plugins()
        for plugin_name, plugin_module in service_plugins.items():
            try:
                self.project['service'][plugin_name.lower()]
            except KeyError:
                # ignore if no config files for a registered service
                self.log_action_col("Skipping", 'Service', plugin_name)
                continue

            self.log_action_col('Init', 'Service', plugin_name)
            service = plugin_module.instantiate_class(self, self.project['service'][plugin_name.lower()])
            service.init(None)
            self.services[plugin_name.lower()] = service
            self.log_action_col('Init', 'Service', plugin_name, 'Completed')

    def get_controller(self, controller_type, command=None, model_obj=None):
        """Gets a controller by name and calls .init() on it with any controller args"""
        controller_type = controller_type.lower()
        controller = None
        if controller_type != 'service':
            if controller_type in self.controllers:
                controller = self.controllers[controller_type]
            if controller == None:
                controller = paco.controllers.klass[controller_type](self)
                self.controllers[controller_type] = controller
        else:
            service_name = model_obj.paco_ref_list[1]
            if service_name.lower() not in self.services:
                message = "Could not find Service: {}".format(service_name)
                raise StackException(PacoErrorCode.Unknown, message = message)
            controller = self.services[service_name.lower()]

        controller.init(command, model_obj)
        return controller

    def log(self, msg, *args):
        """Logs a message to paco logger if verbose is enabled."""
        if not self.verbose:
            return
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

    def get_ref(self, paco_ref, account_ctx=None):
        """Takes a Paco reference string (paco.ref <type>.<part>) and returns
        the object or value that is being referenced.

        Note that for `paco.ref accounts.<account-name>` references, the acount id is returned
        and not the object.
        """
        return references.resolve_ref(
            paco_ref,
            self.project,
            account_ctx=account_ctx
        )

    def confirm_yaml_changes(self, model_obj):
        """Confirm changes made to the Paco Project YAML from the last run"""
        if self.disable_validation == True:
            return
        applied_file_path, new_file_path = self.init_model_obj_store(model_obj)
        if applied_file_path.exists() == False:
            return
        applied_file_dict = read_yaml_file(applied_file_path)
        new_file_dict = read_yaml_file(new_file_path)
        deep_diff = DeepDiff(
            applied_file_dict,
            new_file_dict,
            verbose_level=1,
            view='tree'
        )
        if len(deep_diff.keys()) == 0:
            return

        print("---------------------------------------------------------")
        print("Confirm Paco Project changes from previous YAML file:\n")
        print("{}".format(new_file_path))
        if self.verbose:
            print()
            print("applied file: {}".format(applied_file_path))
        print()
        if 'values_changed' in deep_diff or \
            'type_changes' in deep_diff:
            print("\nChanged:")
            print_diff_object(deep_diff, 'values_changed')
            print_diff_object(deep_diff, 'type_changes')

        if 'dictionary_item_removed' in deep_diff or \
            'iterable_item_removed' in deep_diff or \
            'set_item_added' in deep_diff:
            print("Removed:")
            print_diff_object(deep_diff, 'dictionary_item_removed')
            print_diff_object(deep_diff, 'iterable_item_removed')
            print_diff_object(deep_diff, 'set_item_added')

        if 'dictionary_item_added' in deep_diff or \
            'iterable_item_added' in deep_diff or \
            'set_item_removed' in deep_diff:
            print("Added:")
            print_diff_object(deep_diff, 'dictionary_item_added')
            print_diff_object(deep_diff, 'iterable_item_added')
            print_diff_object(deep_diff, 'set_item_removed')

        print("---------------------------------------------------------")
        if self.yes == True:
            return
        answer = self.input_confirm_action("\nAre these changes acceptable?")
        if answer == False:
            print("Aborted run.")
            sys.exit(1)
        print()

    def input_confirm_action(
        self,
        question,
        default="n"
    ):
        """Ask for a input on the CLI unless the -y, --yes flag has been specified."""
        if self.yes:
            return True
        valid = {"yes": True, "y": True, "no": False, "n": False}
        if default == "y":
            prompt = " [Y/n] "
        elif default == "n":
            prompt = " [y/N] "
        else:
            raise ValueError("Invalid default answer: '%s'" % default)
        while True:
            answer = input(question + prompt).lower()
            if default is not None and answer == '':
                return valid[default]
            elif answer in valid:
                return valid[answer]
            else:
                print("Please respond with 'y' or 'n' (or 'yes' or 'no').\n")

    def legacy_flag(self, flag):
        if flag in self.project.legacy_flags:
            return True
        return False

    def init_model_obj_store(self, model_obj):
        """Create a directory for the applied YAML file.
        Returns a tuple of pathlib Paths for the already applied file
        and the new actual file to be applied.
        """
        project_folder_path = pathlib.Path(self.project_folder)
        changed_file_path = project_folder_path.joinpath(model_obj._read_file_path)
        applied_file_path = project_folder_path.joinpath(
            'aimdata',
            'applied',
            'model',
            model_obj._read_file_path
        )
        applied_file_path.parent.mkdir(parents=True, exist_ok=True)

        return (applied_file_path, changed_file_path)

    def apply_model_obj(self, model_obj):
        "Copies the YAML file after it has been provisioned to an applied cache dir"
        applied_file_path, new_file_path = self.init_model_obj_store(model_obj)
        copyfile(new_file_path, applied_file_path)

    def log_action_col(
        self,
        col_1,
        col_2=None,
        col_3=None,
        col_4=None,
        return_it=False,
        enabled=True,
        col_1_size=10,
        col_2_size=11,
        col_3_size=15,
        col_4_size=None
    ):
        # Skip verbose messages unless -v verbose is flagged
        if not self.verbose:
            if col_1 == 'Init':
                return
            elif col_1 == 'Skipping':
                return
        if col_2 == '': col_2 = None
        if col_3 == '': col_3 = None
        if col_4 == '': col_4 = None
        if col_4 != None and col_4_size == None: col_4_size = len(col_4)

        if enabled == False:
            col_1 = 'Disabled'

        col_2_wrap_text = False
        col_3_wrap_text = False
        col_4_wrap_text = False
        if col_2 == None:
            col_1_size = len(col_1)
            col_3 = None
            col_4 = None
        if col_3 == None and col_2 != None:
            col_2_size = len(col_2)
            col_4 = None
            col_2_wrap_text = True
        if col_4 == None and col_3 != None:
            col_3_size = len(col_3)
            col_3_wrap_text = True
        if col_4 != None:
            col_4_wrap_text = True

        message = create_log_col(col_1, col_1_size, 0)
        if col_2 != None:
            message += create_log_col(col_2, col_2_size, len(message), col_2_wrap_text)
            if col_3 != None:
                message += create_log_col(col_3, col_3_size, len(message), col_3_wrap_text)
                if col_4 != None:
                    message += create_log_col(col_4, col_4_size, len(message), col_4_wrap_text)
        if return_it == True:
            return message+'\n'
        print(message)
