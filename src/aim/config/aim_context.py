import hashlib
import os
import aim.config.aws_credentials
import aim.core.log
import aim.controllers
from functools import partial
from aim.models import load_project_from_yaml
from aim.models import references
from copy import deepcopy
from aim.config import ConfigProcessor


class AccountContext(object):

    def __init__(self,
                 aim_ctx,
                 name,
                 mfa_account = None):
        self.name = name
        self.client_cache = {}
        self.resource_cache = {}
        self.aim_ctx = aim_ctx
        self.config = aim_ctx.project['accounts'][name]
        self.mfa_account = mfa_account
        self.aws_session = None
        cache_filename = '-'.join(['aim', aim_ctx.project.name, 'account', self.name])
        self.cli_cache = os.path.join(os.path.expanduser('~'),
                                      '.aws/cli/cache',
                                      cache_filename)
        if name == "master":
            self.get_mfa_session(self.aim_ctx.project['credentials'])

    def get_name(self):
        return self.name

    def get_temporary_credentials(self):
        return self.aws_session.get_temporary_credentials()

    def get_mfa_session(self, admin_creds):
        if self.aws_session == None:
            self.aws_session = aim.config.aws_credentials.Sts(
                self,
                role_arn=self.config.admin_delegate_role_arn,
                temporary_credentials_path=self.cli_cache,
                mfa_arn=admin_creds.mfa_role_arn,
                admin_creds=admin_creds
            )

        return self.aws_session.get_temporary_session()

    def get_session(self):
        if self.aws_session == None:
            self.aws_session = aim.config.aws_credentials.Sts(
                    self,
                    role_arn=self.config.admin_delegate_role_arn,
                    temporary_credentials_path=self.cli_cache,
                    mfa_account=self.mfa_account
            )

        return self.aws_session.get_temporary_session()

    def get_id(self):
        return self.config.account_id

    def get_aws_client(self, client_name, aws_region=None, client_config=None):
        if client_name not in self.client_cache.keys():
            session = self.get_session()
            self.client_cache[client_name] = session.client(
                client_name, region_name=aws_region, config=client_config)
        return self.client_cache[client_name]

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
        self.aim_path = os.getcwd()
        self.build_folder = None
        self.aws_name = "AIM"
        self.controllers = {}
        self.accounts = {}
        self.logger = aim.core.log.get_aim_logger()
        self.project = None
        self.master_account = None

    def get_account_context(self, account_ref=None, account_name=None):
        if account_ref != None:
            ref_dict = self.parse_ref(account_ref)
            account_name = ref_dict['ref_parts'][1]
        elif account_name == None:
            raise StackException(AimErrorCode.Unknown)

        if account_name in self.accounts:
            return self.accounts[account_name]

        account_ctx = AccountContext(aim_ctx=self,
                                     name=account_name,
                                     mfa_account=self.master_account)

        return account_ctx

    def init_project(self):
        print("Project: %s" % (self.home))
        self.project_folder = self.home
        # Config Processor Init
        self.config_processor = ConfigProcessor(self)
        self.project = load_project_from_yaml(self, self.project_folder, None) #self.config_processor.load_yaml)
        self.build_folder = os.path.join(os.getcwd(), "build", self.project.name)
        self.master_account = AccountContext(aim_ctx=self,
                                             name='master',
                                             mfa_account=None)
        # Set Default AWS Region
        os.environ['AWS_DEFAULT_REGION'] = self.project['credentials'].aws_default_region

    def get_controller(self, controller_type, config_arg=None):
        #print("Creating controller_type: " + controller_type)
        controller = None
        if controller_type in self.controllers:
            #print("Returning cached controller: " + controller_type)
            controller = self.controllers[controller_type]

        if controller == None:
            controller = aim.controllers.klass[controller_type](self)
            self.controllers[controller_type] = controller
            controller.init(config_arg)

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

#    def get_aws_name(self):
#        return '-'.join([ self.aws_name,
#                          self.controller.aws_name ])
#        return self.controller.aws_name

    def get_stack_filename(self, stack_group_type, stack_type):
        return os.path.join(self.stacks_folder, stack_group_type+"/"+stack_type+".yml")

    def is_ref(self, aim_ref):
        # duplicate: moved to aim.models.references.AimReference
        ref_types = ["netenv.ref", "service.ref", "config.ref"]
        for ref_type in ref_types:
            if aim_ref.startswith(ref_type):
                return True

        return False

    def parse_netenv_ref(self, aim_ref, ref_parts):
        # duplicate: moved to aim.models.references.AimReference
        ref_dict = {}
#        ref_dict['subenv_component'] = ""
        ref_dict['subenv_id'] = ""
        ref_dict['netenv_component'] = ""
        ref_dict['subenv_component'] = ""
        if ref_parts[0] == 'this':
            ref_dict['netenv_id'] = self.this_netenv_id
        else:
            ref_dict['netenv_id'] = ref_parts[0]

        if ref_parts[1] == 'subenv':
            ref_dict['subenv_component'] = ref_parts[1]
            ref_dict['subenv_id'] = ref_parts[2]
            ref_dict['subenv_region'] = ref_parts[3]
            ref_dict['netenv_component'] = ref_parts[4]
        else:
            ref_dict['netenv_component'] = ref_parts[1]
        return ref_dict

    def parse_ref(self, aim_ref):
        # duplicate: moved to aim.models.references.AimReference
        ref_parts = aim_ref.split(' ')
        if len(ref_parts) != 2:
            raise StackException(AimErrorCode.Unknown)
        ref_type = ref_parts[0]
        config_ref = ref_parts[1]
        location_parts = ref_parts[1].split('.')
        ref_dict = {}
        if ref_parts[0] == 'netenv.ref':
            ref_dict = self.parse_netenv_ref(aim_ref, location_parts)
        elif ref_parts[0] == 'service.ref':
            # print(aim_ref)
            pass
        elif ref_parts[0] == 'config.ref':
            # print(aim_ref)
            #raise StackException(AimErrorCode.Unknown)
            pass
        else:
            print(ref_parts[0])
            raise StackException(AimErrorCode.Unknown)

        # pprint(repr(location_parts))
        ref_dict['type'] = ref_type
        ref_dict['ref'] = config_ref
        ref_dict['ref_parts'] = location_parts
        ref_dict['raw'] = aim_ref

        return ref_dict

    def get_config_ref_value(self, config_ref, output_type):
        ref_dict = self.parse_ref(config_ref)
        if ref_dict['type'] != 'config.ref':
            raise StackException(AimErrorCode.Unknown)

        # Only config item is accounts at the moment
        account_ctx = self.get_account_context(config_ref)
        return account_ctx.get_id()

    def get_netenv_ref_value(self, netenv_ref, output_type):
        ref_dict = self.parse_ref(netenv_ref)
        if ref_dict['type'] != 'netenv.ref':
            raise StackException(AimErrorCode.Unknown)
        controller = self.get_controller('NetEnv')

        if output_type == 'value':
            return controller.get_value_from_ref(ref_dict)
        elif output_type == 'stack':
            return controller.get_stack_from_ref(ref_dict)
        else:
            raise StackException(AimErrorCode.Unknown)

    def get_service_ref_value(self, service_ref, output_type="value"):
        # print(service_ref)
        ref_parts = service_ref.split(' ')
        # print(ref_parts)
        if ref_parts[0] != 'service.ref':
            raise StackException(AimErrorCode.Unknown)
        service_parts = ref_parts[1].split('.')
        controller = None
        if service_parts[0] == "codecommit":
            config_name = service_parts[1]
            init_config = {'name': config_name}
            controller = self.get_controller('CodeCommit', init_config)
        elif service_parts[0] == "route53":
            config_name = service_parts[1]
            controller = self.get_controller('Route53')
        elif service_parts[0] == "acm":
            config_type = service_parts[1]
            if config_type == "domain":
                config_name = None
            elif config_type == "config":
                config_name = service_parts[2]
            else:
                raise StackException(AimErrorCode.Unknown)
            controller = self.get_controller(
                'ACM', config_name=config_name, config_type=config_type)

        return controller.get_service_ref_value(service_parts)

    def get_ref(self, aim_ref, output_type="value"):
        ref_dict = self.parse_ref(aim_ref)
        if ref_dict['type'] == "service.ref":
            # XXX: Port to Model Reference lookup
            return self.get_service_ref_value(aim_ref, output_type)
        elif ref_dict['type'] == "netenv.ref":
            return references.resolve_ref(aim_ref, self.project)
        elif ref_dict['type'] == "config.ref":
            return references.resolve_ref(aim_ref, self.project)
        else:
            raise StackException(AimErrorCode.Unknown)

    def normalize_name(self,
                       name,
                       replace_sep,
                       camel_case):
        normalized_name = ""
        name_list = name.split("_")
        first = True
        for name_item in name_list:
            if camel_case == True:
                name_item = name_item.title()
            if first == False:
                normalized_name += replace_sep
            first = False
            normalized_name += name_item

        return normalized_name

    def normalized_join(self,
                        str_list,
                        replace_sep,
                        camel_case):
        new_str = replace_sep.join(str_list)
        normalized_str = ""
        first = True
        for str_item in str_list:
            str_item = self.normalize_name(str_item, replace_sep, camel_case)
            if first == False:
                normalized_str += replace_sep
            first = False
            normalized_str += str_item

        return normalized_str

    def md5sum(self, filename=None, str_data=None):
        d = hashlib.md5()
        if filename != None:
            with open(filename, mode='rb') as f:
                for buf in iter(partial(f.read, 128), b''):
                    d.update(buf)
        elif str_data != None:
            d.update(bytearray(str_data, 'utf-8'))
        else:
            print("cli: md5sum: Filename or String data expected")
            raise StackException(AimErrorCode.Unknown)

        return d.hexdigest()

    def str_spc(self, str_data, size):
        new_str = str_data
        str_len = len(str_data)
        if str_len > size:
            print("ERROR: cli: str_spc: string size is larger than space size: {0} > {1}".format(
                str_len, size))
            raise StackException(AimErrorCode.Unknown)

        for idx in range(size - str_len):
            new_str += " "
        return new_str

    def dict_of_dicts_merge(self, x, y):
        z = {}
#        if isinstance(param_value, str)
        overlapping_keys = x.keys() & y.keys()
        for key in overlapping_keys:
            z[key] = self.dict_of_dicts_merge(x[key], y[key])
        for key in x.keys() - overlapping_keys:
            z[key] = deepcopy(x[key])
        for key in y.keys() - overlapping_keys:
            z[key] = deepcopy(y[key])
        return z

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
                    value_match == False
                    if is_instance(value, str) and case_sensitive == False:
                        if allowed_value.lower() == value.lower():
                            value_match = True
                    elif allowed_value == value:
                        value_match = True
                    if value_match == True:
                        if return_bool_on_allowed_value == True:
                            return True
                        else:
                            return value
                print("Invalid response: %s: Try again.\n" % (value))
                continue

            try_again = False
        return value
