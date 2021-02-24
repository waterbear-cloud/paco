from botocore.exceptions import ClientError, WaiterError
from copy import deepcopy
from enum import Enum
from paco.models.exceptions import InvalidPacoReference
from paco import utils
from paco.core.yaml import YAML
from paco.core.exception import StackException, PacoErrorCode, PacoException, StackOutputException
from paco.models import references
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.stack.interfaces import IStack, ICloudFormationStack
from paco.utils import md5sum, dict_of_dicts_merge, list_to_comma_string, write_to_file
from shutil import copyfile
from deepdiff import DeepDiff
from zope.interface import implementer
import base64
import os.path
import pathlib
import re
import ruamel.yaml
import sys


yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

log_next_header = None

StackStatus = Enum('StackStatus', 'NONE DOES_NOT_EXIST CREATE_IN_PROGRESS CREATE_FAILED CREATE_COMPLETE ROLLBACK_IN_PROGRESS ROLLBACK_FAILED ROLLBACK_COMPLETE DELETE_IN_PROGRESS DELETE_FAILED DELETE_COMPLETE UPDATE_IN_PROGRESS UPDATE_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_COMPLETE UPDATE_ROLLBACK_IN_PROGRESS UPDATE_ROLLBACK_FAILED UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_ROLLBACK_COMPLETE REVIEW_IN_PROGRESS')

class StackOutputConfig():
    """
Maps from a Stacks Output Key to a reference. For example,
the CloudFormationStack for an SNSTopic:

  key: 'SNSTopicArnsnstopic',
  confif_ref: 'service.notification.tools.us-west-2.topic.groups.topic.resources.snstopic.arn',

    """
    def __init__(self, config_ref, key):
        self.key = key
        self.config_ref = config_ref

    def get_config_dict(self, stack):
        conf_dict = current = last_dict = {}
        ref_part = None
        ref_part_list = self.config_ref.split('.')
        for ref_part in ref_part_list:
            current[ref_part] = {}
            last_dict = current
            current = current[ref_part]

        last_dict[ref_part]['__name__'] = stack.get_outputs_value(self.key)

        return conf_dict

    def __repr__(self):
        return f'config_ref: {self.config_ref}, key: {self.key}'


class StackOutputParam():
    """
    Holds a list of dicts describing a stack and the outputs that are required
    to populate another stacks input parameter.
    A list of outputs can be provided which will allow the generation of a list
    to pass into a stack parameter (e.g. Security Group lists).
    """

    def __init__(
        self,
        param_key,
        stack=None,
        stack_output_key=None,
        param_template=None,
        ignore_changes=False
    ):
        self.key = param_key
        self.entry_list = []
        self.use_previous_value = False
        self.resolved_value = ""
        self.stack = stack
        self.param_template = param_template
        self.ignore_changes = ignore_changes
        if stack !=None and stack_output_key !=None:
            self.add_stack_output( stack, stack_output_key)

    def add_stack_output(self, stack, stack_output_key):
        if stack_output_key == None:
            raise PacoException(PacoErrorCode.Unknown, message="Stack Output key is unset")
        self.stack = stack
        for entry in self.entry_list:
            if entry['stack'] == stack:
                entry['output_keys'].append(stack_output_key)
                return

        entry = {
            'stack': stack,
            'output_keys': [stack_output_key]
        }
        self.entry_list.append(entry)

    def gen_parameter_value(self):
        param_value = ""
        comma = ''
        for entry in self.entry_list:
            for output_key in entry['output_keys']:
                output_value = entry['stack'].get_outputs_value(output_key)
                param_value += comma + output_value
                comma = ','

        return param_value

    def gen_parameter(self):
        """
        Generate a parameter entry
        All stacks are queried, their output values gathered and are placed
        in a single comma delimited list to be passed to the next stacks
        parameter as a single value
        """
        param_value = self.gen_parameter_value()
        return Parameter(
            self.param_template,
            self.key, param_value,
            self.use_previous_value,
            self.resolved_value,
            self.ignore_changes
        )

class Parameter():
    def __init__(
        self,
        template,
        key,
        value,
        use_previous_value=False,
        resolved_value="",
        ignore_changes=False
    ):
        self.key = key
        self.value = marshal_value_to_cfn_yaml(value)
        self.use_previous_value = use_previous_value
        self.resolved_value = resolved_value
        self.ignore_changes = ignore_changes

    def gen_parameter_value(self):
        return self.value

    def gen_parameter(self):
        return self


def marshal_value_to_cfn_yaml(value):
    "Cast a Python value to a string usable as a CloudFormation YAML value"
    if type(value) == bool:
        if value:
            return "true"
        else:
            return "false"
    elif type(value) == int:
        return str(value)
    elif type(value) == str:
        return value
    else:
        raise PacoException(
            PacoErrorCode.Unknown,
            message="Parameter could not be cast to a YAML value: {}".format(type(value))
        )

class StackTags():
    def __init__(self, stack_tags=None):
        if stack_tags != None:
            self.tags = deepcopy(stack_tags.tags)
        else:
            self.tags = {}

    def add_tag(self, key, value):
        self.tags[key] = value

    def cf_list(self):
        tag_list = []
        for key, value in self.tags.items():
            tag_dict = {
                'Key': key,
                'Value': value
            }
            tag_list.append(tag_dict)
        return tag_list

    def gen_cache_id(self):
        return md5sum(str_data=yaml.dump(self.tags))


class StackHooks():
    """Contains hooks which will be called before or after a Stack has a create, update or delete operation.

    StackHooks objects can be created before a Stack and passed to the StackGroup.add_new_stack() method.
    The Stack constructor will set the stack attribute on the StackHooks. New StackHooks can also be made
    without a Stack and then merged into an existing StackHooks that is associated with a Stack.
    """

    def __init__(self, stack=None):
        self.stack = stack
        self.hooks = {
            'create': {
                'pre': [],
                'post': []
            },
            'update': {
                'pre': [],
                'post': []
            },
            'delete': {
                'pre': [],
                'post': []
            },

        }

    def log_hooks(self):
        "Log hook initialization"
        enabled = False
        if ICloudFormationStack.providedBy(self.stack):
            enabled = self.stack.template.enabled
        else:
            enabled = self.stack.enabled
        if self.stack == None or enabled == False:
            return
        for stack_action_id in self.hooks.keys():
            action_config = self.hooks[stack_action_id]
            for timing_id in action_config.keys():
                timing_config = action_config[timing_id]
                for hook in timing_config:
                    self.stack.log_action("Init", "Hook", message=": {}: {}: {}".format(hook['name'], timing_id, stack_action_id))

    def add(self, name, stack_action, stack_timing, hook_method, cache_method=None, hook_arg=None):
        "Add a hook"
        if not isinstance(stack_action, list):
            stack_action = [stack_action]
        for action in stack_action:
            hook = {
                'name': name,
                'method': hook_method,
                'cache_method': cache_method,
                'arg': hook_arg,
                'stack_action': action,
                'stack_timing': stack_timing,
                'stack': None,
            }
            self.hooks[action][stack_timing].append(hook)
            if self.stack != None:
                if self.stack.template.enabled == True:
                    self.stack.log_action("Init", "Hook", message=": {}: {}: {}".format(name, action, stack_timing))

    def merge(self, new_hooks):
        "Merge another StackHooks' hooks into this StackHooks' hooks"
        if new_hooks == None:
            return
        for stack_action in self.hooks.keys():
            for hook_timing in self.hooks[stack_action].keys():
                for new_hook_item in new_hooks.hooks[stack_action][hook_timing]:
                    self.hooks[stack_action][hook_timing].append(new_hook_item)

    def run(self, stack_action, stack_timing, stack):
        "Invoke a hook"
        for hook in self.hooks[stack_action][stack_timing]:
            stack.log_action('Run', "Hook", message="{}.{}: {}".format(stack_timing, stack_action, hook['name']))
            hook['stack'] = stack
            hook['method'](hook, hook['arg'])

    def gen_cache_id(self):
        "Generate a cache id for the hook"
        cache_id = ""
        for action in ['create', 'update']:
            for timing in self.hooks[action].keys():
                for hook in self.hooks[action][timing]:
                    if hook['cache_method'] != None:
                        cache_id += hook['cache_method'](hook, hook['arg'])
        return cache_id


class StackOutputsManager():
    def __init__(self):
        self.outputs_path = {}
        self.outputs_dict = {}

    def load(self, outputs_path, key):
        self.outputs_path[key] = (outputs_path / key).with_suffix('.yaml')
        if self.outputs_path[key].exists():
            try:
                with open(self.outputs_path[key], "r") as output_fd:
                    self.outputs_dict[key] = yaml.load(output_fd)
            # this can happen if Paco is force quit while writing to this file
            except ruamel.yaml.parser.ParserError:
                self.outputs_dict[key] = {}
        else:
            self.outputs_dict[key] = {}

    def save(self, key):
        if self.outputs_path[key] == None:
            raise StackException(PacoErrorCode.Unknown, message="Outputs file has not been loaded.")

        write_to_file(self.outputs_path[key].parent, self.outputs_path[key].name, self.outputs_dict[key])
        #with open(self.outputs_path[key], "w") as output_fd:
        #    yaml.dump(self.outputs_dict[key], output_fd)

    def add(self, outputs_path, new_outputs_dict):
        if len(new_outputs_dict.keys()) > 1:
            raise StackException(PacoErrorCode.Unknown, message="Outputs dict should only have one key. Investigate!")
        if len(new_outputs_dict.keys()) == 0:
            return
        key = list(new_outputs_dict.keys())[0]
        self.load(outputs_path, key)
        self.outputs_dict[key] = dict_of_dicts_merge(self.outputs_dict[key], new_outputs_dict)
        self.save(key)

stack_outputs_manager = StackOutputsManager()


@implementer(IStack)
class BaseStack():
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        stack_group,
        resource,
        template=None,
        stack_suffix=None,
        aws_region=None,
        hooks=None,
        do_not_cache=False,
        stack_tags=None,
        change_protected=None,
        support_resource_ref_ext=None,
    ):
        self.paco_ctx = paco_ctx
        self.account_ctx = account_ctx
        self.grp_ctx = stack_group
        self.stack_group = stack_group
        self.resource = resource
        if change_protected == None:
            self.change_protected = getattr(resource, 'change_protected', False)
        else:
            self.change_protected = change_protected
        self.termination_protection = False
        self.stack_suffix = stack_suffix
        if aws_region == None:
            raise StackException(PacoErrorCode.Unknown, message="AWS Region is not supplied")
        self.aws_region = aws_region
        self.template = template
        self.status = StackStatus.NONE
        self.stack_id = None
        self.cached = False
        self.max_account_name_size = 12
        self.max_action_name_size = 12
        self.output_config_dict = None
        self.action = None
        self.do_not_cache = do_not_cache
        # Wait for stack to delete if this flag is set
        self.wait_for_delete = False
        self.tags = StackTags(stack_tags)
        self.tags.add_tag('Paco-Stack', 'true')
        self.outputs_value_cache = {}
        self.yaml_path = None
        self.applied_yaml_path = None
        self.parameters = []
        self.parameters_dict = {}
        self.template_file_id = None
        self.build_folder = paco_ctx.build_path / "templates"
        self.stack_output_config_list = []
        self.support_resource_ref_ext = support_resource_ref_ext
        self.dependency_stack = None
        self.dependency_group = False
        if hooks == None:
            self.hooks = StackHooks(self)
        else:
            self.hooks = hooks
            self.hooks.stack = self

    # Use properties here for just-in-time processing as the
    # template's yaml path may change if a template uses
    # the set_template_file_id() method
    @property
    def cache_filename(self):
        return self.get_yaml_path().with_suffix(".cache")

    @property
    def output_filename(self):
        return self.get_yaml_path().with_suffix(".output")

    def init_template_store_paths(self):
        new_file_path = pathlib.Path(self.get_yaml_path())
        applied_file_path = pathlib.Path(self.get_yaml_path(applied=True))
        return [applied_file_path, new_file_path]

    def apply_template_changes(self):
        applied_file_path, new_file_path = self.init_template_store_paths()
        if new_file_path.exists():
            copyfile(new_file_path, applied_file_path)

    def set_template_file_id(self, file_id):
        self.template_file_id = file_id
        self.yaml_path = None
        self.applied_yaml_path = None

    def get_yaml_path(self, applied=False):
        if self.yaml_path and applied == False:
            return self.yaml_path
        if self.applied_yaml_path and applied == True:
            return self.applied_yaml_path

        yaml_filename = self.get_name()
        if self.template_file_id != None:
            yaml_filename += "-" + self.template_file_id
        yaml_filename += ".yaml"

        if applied == False:
            yaml_path = self.build_folder / self.account_ctx.get_name()
        else:
            yaml_path = self.paco_ctx.applied_path / 'cloudformation' / self.account_ctx.get_name()

        if self.aws_region != None:
            yaml_path = yaml_path / self.aws_region
        else:
            raise StackException(PacoErrorCode.Unknown, message = "AWS region is unavailable: {}".format(yaml_path))

        pathlib.Path(yaml_path).mkdir(parents=True, exist_ok=True)
        yaml_path = yaml_path / yaml_filename

        if applied == True:
            self.applied_yaml_path = yaml_path
        else:
            self.yaml_path = yaml_path

        return yaml_path

    def init_applied_parameters_path(self, applied_template_path):
        return applied_template_path.with_suffix('.parameters')

    def create_stack_name(self, name):
        """Must contain only letters, numbers, dashes and start with an alpha character."""
        if name.isalnum():
            return name

        new_name = ""
        for ch in name:
            if ch.isalnum() == False:
                ch = '-'
            new_name += ch

        return new_name

    def stack_success(self):
        "Actions to perform when a stack action has been successfully finished"
        if self.action != "delete":
            # Create cache file
            new_cache_id = self.gen_cache_id()
            if new_cache_id != None:
                cache_filename = pathlib.Path(self.cache_filename)
                write_to_file(cache_filename.parent, cache_filename.name, new_cache_id)

            # Save stack outputs to yaml
            self.save_stack_outputs()
            self.apply_template_changes()
            self.apply_stack_parameters()

    def gen_cache_id(self):
        """Create an MD5 cache id that is an aggregate of the stack's template, parameter values,
        hook cache ids, tags and termination protection setting."""
        yaml_path = self.get_yaml_path()
        if yaml_path.exists() == False:
            return None
        template_md5 = md5sum(self.get_yaml_path())
        outputs_str = ""
        for param_entry in self.parameters:
            try:
                param_value = param_entry.gen_parameter_value()
            except StackOutputException:
                message = """Unable to find output for Parameter '{}' for the resource:

  {}

Attempting to resolve the paco.ref:

  {}

That Output should be provided by the CloudFormation Stack:

  {}

That Stack has potentially been disabled, deleted or modified. Check that the resource
is enabled. If the stack for that resource has been modified by another user,
your cache may be out of sync. Try running again the with the --nocache option.
""".format(param_entry.key, self.resource.paco_ref_parts, param_entry.stack.resource.paco_ref_parts, param_entry.stack.get_name())

                raise StackOutputException(message)
            outputs_str += param_value
        outputs_md5 = md5sum(str_data=outputs_str)
        new_cache_id = template_md5 + outputs_md5

        if new_cache_id == None:
            return None
        # Termination Protection toggle
        if self.termination_protection == True:
            new_cache_id += "TPEnabled"
        # Hooks
        new_cache_id += self.hooks.gen_cache_id()
        new_cache_id += self.tags.gen_cache_id()

        return new_cache_id

    def is_stack_cached(self):
        "Return True if the stack cache id is the same as a previously applied cache id"
        if self.paco_ctx.nocache or self.do_not_cache:
            #return False
            # XXX: Make this work
            if self.dependency_group == True:
                self.get_status()
                if self.status == StackStatus.DOES_NOT_EXIST:
                    return False
                elif self.template_file_id != None:
                    if self.template_file_id.startswith('parent-') == False:
                        return False
            else:
                return False
        try:
            new_cache_id = self.gen_cache_id()
        except PacoException as e:
            if e.code == PacoErrorCode.StackDoesNotExist:
                return False
            elif e.code == PacoErrorCode.StackOutputMissing:
                return False
            else:
                raise e

        if new_cache_id == None:
            return False

        cache_id = "none"
        if os.path.isfile(self.cache_filename):
            with open(self.cache_filename, "r") as cache_fd:
                cache_id = cache_fd.read()

        if cache_id == new_cache_id:
            self.cached = True
            # Load Stack Outputs
            try:
                with open(self.output_filename, "r") as output_fd:
                    self.output_config_dict = yaml.load(output_fd)
            except FileNotFoundError:
                pass
            return True

        return False

    # All things Parameter
    def apply_stack_parameters(self):
        parameter_list = self.generate_stack_parameters()
        applied_template_path, _ = self.init_template_store_paths()
        applied_param_file_path = self.init_applied_parameters_path(applied_template_path)
        applied_param_file_path_new = applied_param_file_path.with_suffix('.new')
        special_yaml = YAML(pure=True)
        with open(applied_param_file_path_new, 'w') as stream:
            special_yaml.dump(parameter_list, stream)
        applied_param_file_path_new.rename(applied_param_file_path)

    def generate_stack_parameters(self, action=None):
        """Sets Scheduled output parameters to be collected from one stacks Outputs.
        This is called after a stacks status has been polled.
        """
        parameter_list = []
        for param_entry in self.parameters:
            try:
                parameter = param_entry.gen_parameter()
            except StackOutputException:
                message = """Unable to find output for Parameter '{}' for the resource:

  {}

Attempting to resolve the paco.ref:

  {}

That Output should be provided by the CloudFormation Stack:

  {}

That Stack has potentially been disabled, deleted or modified. Check that the resource
is enabled. If the stack for that resource has been modified by another user,
your cache may be out of sync. Try running again the with the --nocache option.
""".format(param_entry.key, self.resource.paco_ref_parts, param_entry.stack.resource.paco_ref_parts, param_entry.stack.get_name())

                raise StackOutputException(message)

            # Do not update Parameters which have indicated they can be externally updated
            if action == "update" and parameter.ignore_changes == True:
                stack_param_entry = {
                    'ParameterKey': parameter.key,
                    'UsePreviousValue': True,
                }
            else:
                stack_param_entry = {
                    'ParameterKey': parameter.key,
                    'ParameterValue': parameter.value,
                    'UsePreviousValue': parameter.use_previous_value,
                    'ResolvedValue': parameter.resolved_value  # For resolving SSM Parameters
                }
            parameter_list.append(stack_param_entry)

        return parameter_list

    def confirm_stack_parameter_changes(self, parameter_list):
        """
        Display changes to a stack's Parameters and confirm changes
        """
        if self.paco_ctx.disable_validation == True:
            return
        applied_file_path, new_file_path = self.init_template_store_paths()
        param_applied_file_path = applied_file_path.with_suffix('.parameters')

        if param_applied_file_path.exists() == False:
            return
        yaml = YAML(pure=True)
        yaml.allow_duplicate_keys = True
        with open(param_applied_file_path, 'r') as stream:
            applied_parameter_list = yaml.load(stream)

        # Detect changes. Ignore changes where ignore_updates is True
        unchanged = True
        for parameter, applied in zip(parameter_list, applied_parameter_list):
            if parameter['UsePreviousValue'] == True:
                continue
            if parameter != applied:
                unchanged = False
                break

        if unchanged == True:
            return

        print("--------------------------------------------------------")
        print("Confirm changes to Parameters for CloudFormation Stack: " + self.get_name())
        print()
        print("{}".format(self.get_name()))
        if self.paco_ctx.verbose:
            print()
            print("Model: {}".format(self.resource.paco_ref_parts))
            print("Template:  {}".format(new_file_path))
            print("Applied template:  {}".format(applied_file_path))
            print("Applied parameters:  {}".format(param_applied_file_path))
        print('')

        col_3_size = 0
        for new_param in parameter_list:
            if self.paco_ctx.verbose == True or new_param not in applied_parameter_list:
                key_len = len(new_param['ParameterKey'])
                if col_3_size < key_len: col_3_size = key_len

        for new_param in parameter_list:
            if 'UsePreviousValue' in new_param and new_param['UsePreviousValue'] == True:
                continue
            col_2_size = 12
            if new_param in applied_parameter_list:
                applied_parameter_list.remove(new_param)
                if self.paco_ctx.verbose == True:
                    self.paco_ctx.log_action_col(
                        '  ',
                        col_2='Unchanged',
                        col_3=new_param['ParameterKey'],
                        col_4=': {}'.format(new_param['ParameterValue']),
                        col_1_size=2,
                        col_2_size=col_2_size,
                        col_3_size=col_3_size,
                        use_bars=False
                    )
            else:
                for applied_param in applied_parameter_list:
                    if new_param['ParameterKey'] == applied_param['ParameterKey']:
                        self.paco_ctx.log_action_col(
                            '  ', col_2='Changed', col_3=applied_param['ParameterKey'],
                            col_4='old: {}'.format(applied_param['ParameterValue']),
                            col_1_size=2, col_2_size=col_2_size, col_3_size=col_3_size,
                            col_4_size=80,
                            use_bars=False
                        )
                        self.paco_ctx.log_action_col(
                            '  ', col_2 = 'Changed', col_3 = new_param['ParameterKey'],
                            col_4 = 'new: {}'.format(new_param['ParameterValue']),
                            col_1_size = 2, col_2_size=col_2_size, col_3_size=col_3_size,
                            col_4_size = 80,
                            use_bars=False
                        )
                        # Parameter Changes
                        if new_param['ParameterKey'] == 'UserDataScript':
                            old_decoded = base64.b64decode(applied_param['ParameterValue'])
                            new_decoded = base64.b64decode(new_param['ParameterValue'])
                            self.paco_ctx.log_action_col(
                                '  ', col_2='Decoded', col_3='UserDataScript',
                                col_4='old: {}'.format(old_decoded.decode()),
                                col_1_size=-2, col_2_size=col_2_size, col_3_size=col_3_size,
                                col_4_size=80,
                                use_bars=False
                            )
                            self.paco_ctx.log_action_col(
                                '  ', col_2='Decoded', col_3='UserDataScript',
                                col_4='new: {}'.format(new_decoded.decode()),
                                col_1_size=2, col_2_size=col_2_size, col_3_size=col_3_size,
                                col_4_size=80,
                                use_bars=False
                            )

                    else:
                        # New parameter
                        self.paco_ctx.log_action_col(
                            '  ',
                            col_2 = 'New Param',
                            col_3 = new_param['ParameterKey'],
                            col_4 = ': {}'.format(new_param['ParameterValue']),
                            col_1_size = 2,
                            col_2_size = col_2_size,
                            col_3_size = col_3_size,
                            )
                    applied_parameter_list.remove(applied_param)
                    break

        # Deleted Parameters
        for applied_param in applied_parameter_list:
            print("Removed Parameter: {} = {}".format(applied_param['ParameterKey'], applied_param['ParameterValue']))

        print("--------------------------------------------------------")
        print("Stack: " + self.get_name())
        print("")
        answer = self.paco_ctx.input_confirm_action("\nAre these changes acceptable?")
        if answer == False:
            print("Aborted run.")
            sys.exit(1)
        print()

    # Stack Outputs and References
    @property
    def stack_ref(self):
        "The reference to the resource for the stack or a support resource"
        if self.support_resource_ref_ext != None:
            return self.resource.paco_ref_parts + '.' + self.support_resource_ref_ext
        else:
            return self.resource.paco_ref_parts

    def get_parameter_value_by_key(self, param_key):
        "Return the value of a Parameter named by it's key"
        for param in self.parameters:
            if param.key == param_key:
                return param.value
        return None

    def get_output_value_by_ref_extension(self, ref_extension):
        """
        Return the value of a Stack Output as named by it's reference suffix.

        For example, given a Stack for a Cognito UserPool with the reference:

          'service.login.dev.us-east-1.auth.groups.cog.resources.userpool'

        Then that reference with the suffix '.arn':

          'service.login.dev.us-east-1.auth.groups.cog.resources.userpool.arn'

        Would return the Stack Output with the key 'CognitoUserPoolArn' of that UserPool.
        """
        ref = f'paco.ref {self.stack_ref}.{ref_extension}'
        if not references.is_ref(ref):
            raise InvalidPacoReference(f"Can not resolve Parameter value for reference, as it is not well-formed:\n{ref}")
        key = self.get_outputs_key_from_ref(references.Reference(ref))
        return self.get_outputs_value(key)

    def get_outputs_key_from_ref(self, ref):
        "Return a key for an output from a Reference object"
        # Secrets .jsonfield ref special case
        # remove the .jsonfield part as Stacks do not provide an Output for that, the Output
        # is simply the Secret Arn
        if schemas.ISecretsManagerSecret.providedBy(ref.resource):
            base_ref = ref.secret_base_ref()
            ref = references.Reference(f'{base_ref.raw}.arn')

        for stack_output_config in self.stack_output_config_list:
            if stack_output_config.config_ref == ref.ref:
                return stack_output_config.key

        # raise an error if no key was found
        message = self.get_stack_error_message()
        message += "Error: Unable to find outputs key for ref: {}\n".format(ref.raw)
        raise StackException(
            PacoErrorCode.Unknown,
            message=message
        )

    def register_stack_output_config(self, config_ref, stack_output_key):
        "Register Stack Output"
        if config_ref.startswith('paco.ref'):
            raise PacoException(
                PacoErrorCode.Unknown,
                message='Registered stack output config reference must not start with paco.ref: ' + config_ref
            )
        stack_output_config = StackOutputConfig(config_ref, stack_output_key)
        self.stack_output_config_list.append(stack_output_config)

    def get_stack_outputs_key_from_ref(self, ref):
        "Gets the output key of a project reference"
        # ToDo: refactor - this should be a function and not a Stack method as it
        # doesn't apply to this Stack
        stack = ref.resolve(self.paco_ctx.project)
        return stack.get_outputs_key_from_ref(ref)

    def get_outputs_value(self, key):
        "Get Stack OutputValue by Stack OutputKey"
        if key in self.outputs_value_cache.keys():
            return self.outputs_value_cache[key]

        while True:
            try:
                stack_metadata = self.cfn_client.describe_stacks(StackName=self.get_name())
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationError' and e.response['Error']['Message'].find("does not exist") != -1:
                    message = self.get_stack_error_message()
                    message += 'Could not describe stack to get value for Outputs Key: {}\n'.format(key)
                    message += 'Account: ' + self.account_ctx.get_name()
                    raise StackException(PacoErrorCode.StackDoesNotExist, message = message)
                elif e.response['Error']['Code'] == 'ExpiredToken':
                    self.handle_token_expired()
                    continue
                else:
                    raise StackException(PacoErrorCode.Unknown, message=e.response['Error']['Message'])
            break

        if 'Outputs' not in stack_metadata['Stacks'][0].keys():
            # this error should be caught be the calling code and re-raised with more context
            # for example, if an ASG is looking for an EFS Id output, then the user needs to be
            # informed that the ASG stack is failing to in find the output from the EFS stack
            raise StackOutputException("Could not find the value for {}".format(key))

        for output in stack_metadata['Stacks'][0]['Outputs']:
            if output['OutputKey'] == key:
                self.outputs_value_cache[key] = output['OutputValue']
                return self.outputs_value_cache[key]

        message = self.get_stack_error_message()
        message += "Could not find Stack Output {} in stack_metadata:\n\n{}\n".format(key, stack_metadata)
        raise StackException(
            PacoErrorCode.StackOutputMissing,
            message=message
        )

    def save_stack_outputs(self):
        "Process and save Stack Outputs to disk and to the StackOutputsManager"
        # process stack output config
        self.output_config_dict = {}
        for output_config in self.stack_output_config_list:
            config_dict = output_config.get_config_dict(self)
            self.output_config_dict = dict_of_dicts_merge(self.output_config_dict, config_dict)
        # save to disk cache
        write_to_file(self.output_filename.parent, self.output_filename.name, self.output_config_dict)

        # add to StackOutputsManager
        stack_outputs_manager.add(self.paco_ctx.outputs_path, self.output_config_dict)

    def log_action_header(self):
        global log_next_header
        if log_next_header != None:
            self.paco_ctx.log_action_col(log_next_header, 'Account', 'Action', 'Stack Name')
            log_next_header = None

    def log_action(self, action, stack_action, account_name=None, stack_name=None, message=None, return_it=False):
        if self.paco_ctx.quiet_changes_only == True:
            if stack_action in ['Protected', 'Disabled', 'Cache', 'Wait', 'Done']:
                return
        if self.paco_ctx.verbose == False:
            if stack_action in ['Wait', 'Done']:
                return
        if account_name == None:
            msg_account_name = self.account_ctx.get_name()
        else:
            msg_account_name = account_name

        if stack_name == None:
            msg_stack_name = self.get_name()
        else:
            msg_stack_name = stack_name

        if self.template_file_id != None:
            msg_stack_name += ': dependency group: ' + self.template_file_id
        stack_message = msg_stack_name
        if message != None:
            stack_message += ': '+message
        global log_next_header
        if return_it == False:
            self.log_action_header()
        if action == "Init":
            col_2_size=19
        else:
            col_2_size=9
        log_message = self.paco_ctx.log_action_col(
            action,
            stack_action,
            msg_account_name + '.' + self.aws_region,
            'stack: ' + stack_message,
            return_it,
            col_2_size=col_2_size
        )
        if return_it == True:
            return log_message

@implementer(ICloudFormationStack)
class Stack(BaseStack):
    """
A Stack represent a CloudFormation template that is provisioned in an account and region in AWS.
A Stack is created empty and then has a template added to it. This allows the template to interact with the stack.
A Stack is provided a resource, a Paco model object that it is associated with - this model object can set attribtues
such as change_protected that change if the Stack is provisioned or not.
A Stack can interact with the CLI.
A Stack can cache it's templates to the filesystem or check them against AWS and get their status.
    """

    @property
    def cfn_client(self):
        if hasattr(self, '_cfn_client') == False:
            force = False
            if hasattr(self, "_cfn_client_expired") and self._cfn_client_expired == True:
                force = True
                self._cfn_client_expired = False
            self._cfn_client = self.account_ctx.get_aws_client('cloudformation', self.aws_region, force=force)
        return self._cfn_client

    def set_dependency(self, stack, dependency_name):
        """
        Makes a Stack dependent on another Stack.
        This is used when a stack needs to be created with an initial
        configuration, and then updated later when new information becomes
        available. This is used by KMS in the DeploymentPipeline app engine.
        """
        self.dependency_stack = stack
        self.dependency_group = True
        if stack.dependency_stack == None:
            stack.set_template_file_id('parent-' + dependency_name)
            stack.dependency_group = True

    def generate_template(self):
        "Write template to the filesystem"
        self.template.paco_sub()
        self.template.fix_troposphere_manual_ref()
        # Create folder and write template body to file
        self.build_folder.mkdir(parents=True, exist_ok=True)
        stream = open(self.get_yaml_path(), 'w')
        stream.write(self.template.body)
        stream.close()

        yaml_path = self.get_yaml_path()
        # Template size limit is 1,000,000 bytes (1 MB)
        if self.paco_ctx.warn:
            # Start warning if the template size gets close
            warning_size_limit_bytes = 950000
            if yaml_path.stat().st_size >= warning_size_limit_bytes:
                print("WARNING: Template is reaching size limit of 1 MB: Current size: {} bytes ".format(yaml_path.stat().st_size))
                print("template: {}".format(yaml_path))

    def set_parameter(
        self,
        param_key,
        param_value=None,
        use_previous_param_value=False,
        resolved_ssm_value="",
        ignore_changes=False
    ):
        """Adds a parameter to the stack.
        If param_key is a string, grabs the value of the key from the stack outputs,
        if a list, grabs the values of each key in the list and forms a single comma delimited string as the value.
        """
        param_entry = None
        if type(param_key) == StackOutputParam:
            param_entry = param_key
        elif type(param_key) == Parameter:
            param_entry = param_key
        elif isinstance(param_value, list):
            # Security Group List
            param_entry = Parameter(self, param_key, list_to_comma_string(param_value))
        elif isinstance(param_value, str) and references.is_ref(param_value):
            param_value = param_value.replace("<account>", self.account_ctx.get_name())
            environment = get_parent_by_interface(self.resource, schemas.IEnvironment)
            if environment != None:
                param_value = param_value.replace("<environment>", environment.name)
            elif param_value.find('<environment>') != -1:
                raise StackException(
                    PacoErrorCode.Unknown,
                    message="cftemplate: set_parameter: <environment> tag exists but no environment found: " + param_value
                )
            param_value = param_value.replace("<region>", self.aws_region)
            ref = references.Reference(param_value)
            ref.set_region(self.aws_region)
            ref_value = ref.resolve(self.paco_ctx.project, account_ctx=self.account_ctx)
            if ref_value == None:
                ref.resolve(self.paco_ctx.project, account_ctx=self.account_ctx)
                message = "Error: Unable to locate value for ref: {}\n".format(param_value)
                if self.template != None:
                    message += "Template: {}\n".format(self.template.aws_name)
                message += "Parameter: {}\n".format(param_key)
                raise StackException(PacoErrorCode.Unknown, message=message)
            if IStack.providedBy(ref_value):
                # If we need to query another stack, but that stack is not
                # enabled, then avoid setting this parameter to avoid lookup errors later
                if self.enabled == False and ref_value.enabled == False:
                    return None
                stack_output_key = ref_value.get_outputs_key_from_ref(ref)
                param_entry = StackOutputParam(param_key, ref_value, stack_output_key, self)
            else:
                param_entry = Parameter(
                    self,
                    param_key,
                    ref_value,
                    ignore_changes=ignore_changes
                )

        if param_entry == None:
            param_entry = Parameter(
                self,
                param_key,
                param_value,
                ignore_changes=ignore_changes
            )
            if param_entry == None:
                raise StackException(PacoErrorCode.Unknown, message = "set_parameter says NOOOOOOOOOO")

        # Add or update the Parameter
        # Parameters can be updated after initialization by StackHooks
        self.parameters_dict[param_key] = param_entry
        self.parameters = list(self.parameters_dict.values())

    def set_list_parameter(self, param_name, param_list, ref_att=None):
        "Sets a parameter from a list as a comma-separated value"
        # If we are not enabled, do not try to
        value_list = []
        is_stack_list = False
        for param_ref in param_list:
            if ref_att:
                param_ref += '.'+ref_att
            value = references.Reference(param_ref).resolve(self.paco_ctx.project)
            if isinstance(value, Stack):
                is_stack_list = True
                # If we need to query another stack, but that stack is not
                # enabled, then avoid setting this parameter to avoid lookup
                # errors later.
                if self.enabled == False and value.template.enabled == False:
                    return None
            elif is_stack_list == True:
                raise StackException(PacoErrorCode.Unknown, message = 'Cannot have mixed Stacks and non-Stacks in the list: ' + param_ref)
            if value == None:
                raise StackException(PacoErrorCode.Unknown, message = 'Unable to resolve reference: ' + param_ref)
            value_list.append([param_ref,value])

        # If this is the first time this stack has been provisioned,
        # we will need to deferr to the stack outputs
        if is_stack_list == True:
            output_param = StackOutputParam(param_name, param_template=self)
            for param_ref, stack in value_list:
                output_key = self.get_stack_outputs_key_from_ref(references.Reference(param_ref))
                output_param.add_stack_output(stack, output_key)
            self.set_parameter(output_param)
        else:
            param_list = []
            for param_ref, value in value_list:
                param_list.append(value)
            self.set_parameter(param_name, ','.join(param_list))

    def getFromSquareBrackets(self, s):
        return re.findall(r"\['?([A-Za-z0-9_]+)'?\]", s)

    def print_diff_list(self, change_t, level=1):
        print('', end='\n')
        for value in change_t:
            print("  {}-".format(' '*(level*2)), end='')
            if isinstance(value, list):
                self.print_diff_list(value, level+1)
            elif isinstance(value, dict):
                self.print_diff_dict(value, level+1)
            else:
                print("  {}".format(value))

    def print_diff_dict(self, change_t, level=1):
        print('', end='\n')
        for key, value in change_t.items():
            print("  {}{}:".format(' '*(level*2), key), end='')
            if isinstance(value, list):
                self.print_diff_list(value, level+1)
            elif isinstance(value, dict):
                self.print_diff_dict(value, level+1)
            else:
                print("  {}".format(value))

    def print_diff_object(self, diff_obj, diff_obj_key):
        if diff_obj_key not in diff_obj.keys():
            return
        last_root_node_str = None
        for root_change in diff_obj[diff_obj_key]:
            node_str = '.'.join(self.getFromSquareBrackets(root_change.path()))
            for root_node_str in ['Parameters', 'Resources', 'Outputs']:
                if node_str.startswith(root_node_str+'.'):
                    node_str = node_str[len(root_node_str+'.'):]
                    if last_root_node_str != root_node_str:
                        print(root_node_str+":")
                    last_root_node_str = root_node_str
                    break
            if diff_obj_key.endswith('_removed'):
                change_t = root_change.t1
            elif diff_obj_key.endswith('_added'):
                change_t = root_change.t2
            elif diff_obj_key == 'values_changed':
                change_t = root_change.t1
            print("  {}:".format(node_str), end='')
            if diff_obj_key == 'values_changed':
                print("\n    old: {}".format(root_change.t1))
                print("    new: {}\n".format(root_change.t2))
            elif isinstance(change_t, list) == True:
                self.print_diff_list(change_t)
            elif isinstance(change_t, dict) == True:
                self.print_diff_dict(change_t)
            else:
                print("{}".format(change_t))
            print('')

    def warn_template_changes(self, deep_diff):
        """
        Warn the user about template changes that might have unexpected consequences.
        """
        # base method: override this in the child class with the specific warning
        # this method is responsible for printing an appropriate warning. This warning
        # should include a newline above and below this warning and be prefixed with "WARNING: "
        return None

    def validate_template_changes(self):
        if self.paco_ctx.disable_validation == True:
            return
        elif self.enabled == False:
            return
        elif self.change_protected == True:
            return
        applied_file_path, new_file_path = self.init_template_store_paths()
        if applied_file_path.exists() == False:
            return

        yaml = YAML(pure=True)
        yaml.allow_duplicate_keys = True
        #yaml.default_flow_sytle = False
        with open(applied_file_path, 'r') as stream:
            applied_file_dict= yaml.load(stream)
        with open(new_file_path, 'r') as stream:
            new_file_dict= yaml.load(stream)

        deep_diff = DeepDiff(
            applied_file_dict,
            new_file_dict,
            verbose_level=1,
            view='tree'
        )
        if len(deep_diff.keys()) == 0:
            return
        print("--------------------------------------------------------")
        print(f"Confirm template changes to CloudFormation Stack: {self.account_ctx.get_name()}: {self.aws_region}: {self.get_name()}")
        print()
        print("{}".format(self.get_name()))
        if self.paco_ctx.verbose:
            print()
            print("model: {}".format(self.resource.paco_ref_parts))
            print("file: {}".format(new_file_path))
            print("applied file: {}".format(applied_file_path))

        if 'values_changed' in deep_diff.keys():
            print("\nooo Changed")
            self.print_diff_object(deep_diff, 'values_changed')
            print("ooo")

        if  'dictionary_item_removed' in deep_diff.keys() or \
            'iterable_item_removed' in deep_diff.keys() or \
            'set_item_added' in deep_diff.keys():
            print("\n--- Removed")
            self.print_diff_object(deep_diff, 'dictionary_item_removed')
            self.print_diff_object(deep_diff, 'iterable_item_removed')
            self.print_diff_object(deep_diff, 'set_item_added')
            print("---")

        if  'dictionary_item_added' in deep_diff.keys() or \
            'iterable_item_added' in deep_diff.keys() or \
            'set_item_removed' in deep_diff.keys():
            print("\n+++ Added")
            self.print_diff_object(deep_diff, 'dictionary_item_added')
            self.print_diff_object(deep_diff, 'iterable_item_added')
            self.print_diff_object(deep_diff, 'set_item_removed')
            print("+++")

        print("\n--------------------------------------------------------")
        print(f"Stack: {self.account_ctx.get_name()}: {self.aws_region}: {self.get_name()}")
        print(f"Template: {self.get_yaml_path()}")
        print("")
        if self.paco_ctx.warn:
            self.warn_template_changes(deep_diff)
        answer = self.paco_ctx.input_confirm_action("\nAre these changes acceptable?")
        if answer == False:
            print("Aborted run.")
            sys.exit(1)
        print('', end='\n')

    def handle_token_expired(self, location=''):
        """Resets the client handler to force a session reload. location is used for debugging
        to help identify the places where token expiry was failing."""
        if hasattr(self, '_cfn_client') == True:
            delattr(self, '_cfn_client')
        self._cfn_client_expired = True
        if location != '':
            location = '_' + location
        self.log_action("Token", "Retry" + location, "Expired")

    def set_template(self, template):
        self.template = template

    def add_hooks(self, hooks):
        "Add to Stack's StackHooks by merging supplied StackHooks"
        self.hooks.merge(hooks)

    def set_termination_protection(self, protection_enabled):
        self.termination_protection = protection_enabled

    def get_name(self):
        "Name of the stack in AWS. This can not be called until after the StackTemplate has been set."
        name = '-'.join([ self.grp_ctx.get_aws_name(), self.template.aws_name ])
        if self.stack_suffix != None:
            name = name + '-' + self.stack_suffix
        new_name = self.create_stack_name(name)
        if new_name[0].isalpha() == False:
            raise StackException(PacoErrorCode.InvalidStackName)
        return new_name

    def get_status(self):
        "Status of the Stack in AWS"
        while True:
            try:
                stack_list = self.cfn_client.describe_stacks(StackName=self.get_name())
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationError' and e.response['Error']['Message'].endswith("does not exist"):
                    self.status = StackStatus.DOES_NOT_EXIST
                elif e.response['Error']['Code'] == 'ClientError' and e.response['Error']['Message'].endswith("Rate exceeded"):
                    # Lets try again in a little bit
                    msg_prefix = self.log_action("Provision", "Warning", return_it=True)
                    print(msg_prefix+": Get Status throttled")
                    time.sleep(1)
                    continue
                elif e.response['Error']['Code'] == 'ExpiredToken':
                    self.handle_token_expired()
                    continue
                else:
                    message = self.get_stack_error_message(
                        prefix_message=e.response['Error']['Message'],
                        skip_status = True
                    )
                    raise StackException(PacoErrorCode.Unknown, message=message)
            else:
                self.status = StackStatus[stack_list['Stacks'][0]['StackStatus']]
                self.stack_id = stack_list['Stacks'][0]['StackId']
                self.cfn_stack_describe = stack_list['Stacks'][0]

            break

    def is_creating(self):
        if self.status == StackStatus.CREATE_IN_PROGRESS:
            return True
        return False

    def is_updating(self):
        if self.status == StackStatus.UPDATE_IN_PROGRESS:
            return True
        if self.status == StackStatus.UPDATE_COMPLETE_CLEANUP_IN_PROGRESS:
            return True
        return False

    def is_deleting(self):
        if self.status == StackStatus.DELETE_IN_PROGRESS:
            return True
        return False

    def is_complete(self):
        if "COMPLETE" in self.status.name:
            return True
        return False

    def is_failed(self):
        if 'FAILED' in self.status.name:
            return True
        return False

    def is_exists(self):
        if not "DOES_NOT_EXIST" in self.status.name:
            return True
        return False

    def sync_template_to_s3bucket(self):
        """
        Creates or updates the CloudFormation template body to a Paco Bucket
        Returns a template URL to object in the S3 Bucket
        """
        template_region = self.aws_region
        if self.paco_ctx.project.shared_state != None:
            if self.paco_ctx.project.shared_state.cloudformation_region != None:
                template_region = self.paco_ctx.project.shared_state.cloudformation_region
        s3_key = f"Paco/CloudFormationTemplates/{self.get_name()}.yaml"
        bucket_name = self.paco_ctx.paco_buckets.upload_fileobj(
            file_contents=self.template.body,
            s3_key=s3_key,
            account_ctx=self.account_ctx,
            region=template_region
        )
        # https://paco-waterbear-networks-tools-usw2-wbpaco88.s3-us-west-2.amazonaws.com/Paco/CloudFormationTemplates/NE-anet-dev-Secrets-SecretsManager.yaml
        if self.aws_region == 'us-east-1':
            # us-east-1 is a 'special' S3 region that does not include the region in the URL
            return f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        else:
            return f"https://{bucket_name}.s3-{template_region}.amazonaws.com/{s3_key}"

    def create_stack(self):
        "Create an AWS CloudFormation stack"
        if not self.enabled:
            self.log_action("Provision", "Disabled")
            return
        self.action = "create"
        self.hooks.run("create", "pre", self)
        self.log_action("Provision", "Create")
        try:
            stack_parameters = self.generate_stack_parameters()
        except StackException as e:
            e.message += "Error generating stack parameters for template\n"
            if e.code == PacoErrorCode.StackDoesNotExist:
                self.log_action("Provision", "Error")
                e.message += "Stack: {}\n".format(self.get_name())
                e.message += "Error: Depends on StackOutputs from a stack that does not yet exist.\n"
            raise e
        template_url = self.sync_template_to_s3bucket()
        response = self.cfn_client.create_stack(
            StackName=self.get_name(),
            TemplateURL=template_url,
            Parameters=stack_parameters,
            DisableRollback=True,
            Capabilities=self.template.capabilities,
            Tags=self.tags.cf_list(),
        )
        self.stack_id = response['StackId']

        self.cfn_client.update_termination_protection(
            EnableTerminationProtection=True,
            StackName=self.get_name()
        )

    def update_stack(self):
        "Update an AWS CloudFormation stack. Provides CLI interaction on Stack update."
        if self.change_protected == True:
            self.log_action("Provision", "Protected")
            return
        self.action = "update"
        self.hooks.run("update", "pre", self)
        self.log_action("Provision", "Update")
        stack_parameters = self.generate_stack_parameters(action=self.action)
        self.confirm_stack_parameter_changes(stack_parameters)
        self.validate_template_changes()
        while True:
            try:
                template_url = self.sync_template_to_s3bucket()
                self.cfn_client.update_stack(
                    StackName=self.get_name(),
                    TemplateURL=template_url,
                    Parameters=stack_parameters,
                    Capabilities=self.template.capabilities,
                    UsePreviousTemplate=False,
                    Tags=self.tags.cf_list()
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationError':
                    success = False
                    if e.response['Error']['Message'].endswith("No updates are to be performed."):
                        success = True
                    elif e.response['Error']['Message'].endswith("is in UPDATE_COMPLETE_CLEANUP_IN_PROGRESS state and can not be updated."):
                        success = True

                    if success == True:
                        self.log_action("Provision", "Done")
                        self.stack_success()
                    else:
                        message = self.get_stack_error_message()
                        message += "ValidationError: {}\n".format(e.response['Error']['Message'])
                        raise StackException(PacoErrorCode.Unknown, message = message)
                elif e.response['Error']['Code'] == 'ExpiredToken':
                    self.handle_token_expired()
                    continue
                else:
                    #message = "Stack: {}\nError: {}\n".format(self.get_name(), e.response['Error']['Message'])
                    message = self.get_stack_error_message()
                    raise StackException(PacoErrorCode.Unknown, message = message)
            break

        if self.cfn_stack_describe['EnableTerminationProtection'] == False:
            self.cfn_client.update_termination_protection(
                EnableTerminationProtection=True,
                StackName=self.get_name()
            )

    def delete_stack(self):
        "Delete an AWS CloudFormation stack"
        if self.change_protected == True:
            self.log_action("Delete", "Protected")
            return
        if self.paco_ctx.yes == False:
            print("\n"+self.get_name())
            answer = self.paco_ctx.input_confirm_action("DELETE stack? Are you sure?", default='n')
            if answer in ['N', 'n']:
                self.log_action("Delete", "Aborted")
                return
        self.get_status()
        self.action = "delete"
        if self.is_exists() == True:
            # Delete Stack
            if self.termination_protection == True:
                print("\nThis Stack has Termination Protection enabled!")
                print("Stack Name: {}\n".format(self.get_name()))
                answer = self.paco_ctx.input_confirm_action("Destroy this stack forever?")
                if answer == False:
                    print("Destruction aborted. Allowing stack to exist.")
                    return
            if self.is_deleting() == False:
                self.cfn_client.update_termination_protection(
                    EnableTerminationProtection=False,
                    StackName=self.get_name()
                )
        self.log_action("Delete", "Stack")
        self.hooks.run("delete", "pre", self)
        if self.is_exists() == True:
            self.cfn_client.delete_stack( StackName=self.get_name() )
            if self.wait_for_delete == True:
                self.wait_for_complete()


    def get_stack_error_message(self, prefix_message="", skip_status = False):
        "Formatted Stack error message"
        if skip_status == False:
            self.get_status()
        message = "\n"+prefix_message
        message += "Stack:         {}\n".format(self.get_name())
        message += "Template:      {}\n".format(self.get_yaml_path())
        message += "Stack Status:  {}\n".format(self.status)
        if self.is_exists():
            message += "Status Reasons:\n"
            col_size = 20
            message += "LogicalId {}  Status Reason\n".format(
                ' '*(col_size-len('LogicalId '))
            )
            message += "--------- {}  -------------\n".format(
                ' '*(col_size-len('LogicalId '))
            )
            while True:
                try:
                    stack_events = self.cfn_client.describe_stack_events(StackName=self.get_name())
                except ClientError as exc:
                    if exc.response['Error']['Code'] == 'ExpiredToken':
                        self.handle_token_expired('4')
                        continue
                    else:
                        raise sys.exc_info()
                break


            for stack_event in stack_events['StackEvents']:
                if stack_event['ResourceStatus'].find('FAILED') != -1:
                    spaces = col_size-len(stack_event['LogicalResourceId'])
                    if spaces < 0:
                        spaces = 0
                    message += '{} {} {}\n'.format(
                        stack_event['LogicalResourceId'][:col_size],
                        ' ' * spaces,
                        stack_event['ResourceStatusReason']
                    )
        return message

    def provision(self):
        "Provision Stack in AWS"
        self.generate_template()

        # skip the UPDATE action if the last applied cache id is equal to cache id
        if self.is_stack_cached() == True:
            if self.change_protected:
                self.log_action("Provision", "Protected")
            else:
                self.log_action("Provision", "Cache")
            return

        self.get_status()
        if self.is_failed():
            print("--------------------------------------------------------")
            self.log_action("Provision", "Failed")
            print("The stack is in a '{}' state.".format(self.status))
            stack_message = self.get_stack_error_message(skip_status=True)
            print(stack_message)
            print("--------------------------------------------------------")
            answer = self.paco_ctx.input_confirm_action("\nDelete it?", default='y')
            print('')
            if answer:
                self.delete()
                self.wait_for_complete()
            else:
                self.log_action("Provision", "Aborted")
                sys.exit(1)
            self.get_status()

        if self.status == StackStatus.DOES_NOT_EXIST:
            self.create_stack()
        elif self.is_complete():
            self.update_stack()
        elif self.is_creating():
            self.log_action("Provision", "Create")
            self.action = "create"
        elif self.is_deleting():
            self.log_action("Delete", "Stack")
            self.action = "delete"
        elif self.is_updating():
            self.log_action("Provision", "Update")
            self.action = "update"
        elif self.is_creating() == False and self.is_updating() == False:
            self.log_action("Provision", "Error")
            message = self.get_stack_error_message()
            raise StackException(PacoErrorCode.Unknown, message = message)

    def validate(self):
        "Validate Stack in AWS"
        applied_file_path, new_file_path = self.init_template_store_paths()
        short_yaml_path = str(new_file_path).replace(str(self.paco_ctx.home), '')
        if short_yaml_path[0] == '/':
            short_yaml_path = short_yaml_path[1:]
        if self.enabled == False:
            if self.paco_ctx.quiet_changes_only == False:
                self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name() + '.' + self.aws_region, "Disabled", short_yaml_path)
            return
        elif self.change_protected:
            if self.paco_ctx.quiet_changes_only == False:
                self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name() + '.' + self.aws_region, "Protected", short_yaml_path)
            return
        self.generate_template()
        new_str = ''
        if applied_file_path.exists() == False:
            new_str = ':new'
        self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name() + '.' + self.aws_region, "Template"+new_str, short_yaml_path)
        try:
            template_url = self.sync_template_to_s3bucket()
            self.cfn_client.validate_template(TemplateURL=template_url)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                message = "Validation Error: {}\nStack: {}\nTemplate: {}\n".format(
                    e.response['Error']['Message'],
                    self.get_name(),
                    self.get_yaml_path()
                )
                raise StackException(PacoErrorCode.TemplateValidationError, message=message)
        self.validate_template_changes()

    def delete(self):
        "Delete Stack from AWS"
        if self.change_protected == True:
            self.log_action("Delete", "Protected")
            return

        # Applied Template Data
        applied_template_path, _ = self.init_template_store_paths()
        applied_parameters_path = self.init_applied_parameters_path(applied_template_path)
        short_applied_template_path = str(applied_template_path).replace(str(self.paco_ctx.home), '')
        short_applied_parameters_path = str(applied_parameters_path).replace(str(self.paco_ctx.home), '')
        if self.paco_ctx.verbose == True:
            self.paco_ctx.log_action_col('Delete', 'Template', 'Applied', short_applied_template_path)
            self.paco_ctx.log_action_col('Delete', 'Parameters', 'Applied', short_applied_parameters_path)
        try:
            applied_template_path.unlink()
            applied_parameters_path.unlink()
        except FileNotFoundError:
            pass

        # The template itself
        short_yaml_path = str(self.get_yaml_path()).replace(str(self.paco_ctx.home), '')
        if self.paco_ctx.verbose == True:
            self.paco_ctx.log_action_col('Delete', 'Template', 'Build', short_yaml_path)
        try:
            self.get_yaml_path().unlink()
        except FileNotFoundError:
            pass
        pass

        self.delete_stack()
        utils.log_action('Delete', 'Stack', 'Cache', self.cache_filename)
        try:
            os.remove(self.cache_filename)
        except FileNotFoundError:
            pass
        utils.log_action('Delete', 'Stack', 'Outputs', self.output_filename)
        try:
            os.remove(self.output_filename)
        except FileNotFoundError:
            pass

    def wait_for_complete(self):
        "Wait for a Stack's action to COMPLETE and finish and take"
        # While loop to handle expired token retries
        while True:
            if self.action == None:
                return
            self.get_status()
            waiter = None
            action_name = "Provision"
            # get a waiter if Stack is not COMPLETE
            if self.is_updating():
                waiter = self.cfn_client.get_waiter('stack_update_complete')
            elif self.is_creating():
                waiter = self.cfn_client.get_waiter('stack_create_complete')
            elif self.is_deleting():
                action_name = "Delete"
                waiter = self.cfn_client.get_waiter('stack_delete_complete')
            elif self.is_complete():
                pass
            elif not self.is_exists():
                pass
            else:
                message = self.get_stack_error_message()
                raise StackException(
                    PacoErrorCode.WaiterError,
                    message=message
                )

            # wait ...
            if waiter != None:
                self.log_action(action_name, "Wait")
                try:
                    waiter.wait(StackName=self.get_name())
                except WaiterError as waiter_exception:
                    if str(waiter_exception).find('The security token included in the request is expired') != -1:
                        self.handle_token_expired()
                        continue
                    self.log_action(action_name, "Error")
                    message = "Waiter Error:  {}\n".format(waiter_exception)
                    message += self.get_stack_error_message(message)
                    raise StackException(PacoErrorCode.WaiterError, message = message)
                self.log_action(action_name, "Done")

            # handle success actions
            if self.is_exists():
                self.stack_success()

            # run post hooks
            if self.action == "create":
                self.hooks.run("create", "post", self)
            elif self.action == "update":
                self.hooks.run("update", "post", self)
            elif self.action == "delete":
                self.hooks.run("delete", "post", self)

            break

