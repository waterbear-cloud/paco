import boto3
import os
import pathlib
import sys
import time
from aim import utils
from aim.core.exception import StackException
from aim.core.exception import AimException, AimErrorCode
from botocore.exceptions import ClientError, WaiterError
from enum import Enum
from aim.core.yaml import YAML
from aim.utils import md5sum, dict_of_dicts_merge
from copy import deepcopy

log_next_header = None

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

StackEnum = Enum('StackEnum', 'vpc segment')

StackStatus = Enum('StackStatus', 'NONE DOES_NOT_EXIST CREATE_IN_PROGRESS CREATE_FAILED CREATE_COMPLETE ROLLBACK_IN_PROGRESS ROLLBACK_FAILED ROLLBACK_COMPLETE DELETE_IN_PROGRESS DELETE_FAILED DELETE_COMPLETE UPDATE_IN_PROGRESS UPDATE_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_COMPLETE UPDATE_ROLLBACK_IN_PROGRESS UPDATE_ROLLBACK_FAILED UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_ROLLBACK_COMPLETE REVIEW_IN_PROGRESS')

StackOrder = Enum('StackOrder', 'PROVISION WAIT WAITLAST')

class StackOutputsManager():
    def __init__(self):
        self.outputs_path = {}
        self.outputs_dict = {}

    def load(self, project_folder, key):
        self.outputs_path[key] = pathlib.Path(
            os.path.join(
                project_folder,
                'Outputs',
                key+'.yaml'
            ))
        if self.outputs_path[key].exists():
            with open(self.outputs_path[key], "r") as output_fd:
                self.outputs_dict[key] = yaml.load(output_fd)
        else:
            self.outputs_dict[key] = {}

    def save(self, key):
        if self.outputs_path[key] == None:
            raise StackException(AimErrorCode.Unknown, message="Outputs file has not been loaded.")

        self.outputs_path[key].parent.mkdir(parents=True, exist_ok=True)

        with open(self.outputs_path[key], "w") as output_fd:
            yaml.dump(self.outputs_dict[key], output_fd)

    def add(self, project_folder, new_outputs_dict):
        if len(new_outputs_dict.keys()) > 1:
            raise StackException(AimErrorCode.Unknown, message="Outputs dict should only have one key. Investigate!")
        if len(new_outputs_dict.keys()) == 0:
            return
        key = list(new_outputs_dict.keys())[0]
        self.load(project_folder, key)
        self.outputs_dict[key] = dict_of_dicts_merge(self.outputs_dict[key], new_outputs_dict)
        self.save(key)

stack_outputs_manager = StackOutputsManager()

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


class StackOrderItem():
    def __init__(self, order, stack):
        self.order = order
        self.stack = stack

class StackHooks():

    def __init__(self, aim_ctx):
         # Init Stack Hooks
        self.aim_ctx = aim_ctx
        self.stack = None
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
        if self.stack == None or self.stack.template.enabled == False:
            return
        for stack_action_id in self.hooks.keys():
            action_config = self.hooks[stack_action_id]
            for timing_id in action_config.keys():
                timing_config = action_config[timing_id]
                for hook in timing_config:
                    self.stack.log_action("Init", "Hook", message=": {}: {}: {}".format(hook['name'], timing_id, stack_action_id))

    def add(self, name, stack_action, stack_timing, hook_method, cache_method, hook_arg=None):
        hook = {
            'name': name,
            'method': hook_method,
            'cache_method': cache_method,
            'arg': hook_arg,
            'stack_action': stack_action,
            'stack_timing': stack_timing
        }
        self.hooks[stack_action][stack_timing].append(hook)
        if self.stack != None:
            if self.stack.template.enabled == True:
                self.stack.log_action("Init", "Hook", message=": {}: {}: {}".format(name, stack_action, stack_timing))

    def merge(self, new_hooks):
        if new_hooks == None:
            return
        for stack_action in self.hooks.keys():
            for hook_timing in self.hooks[stack_action].keys():
                for new_hook_item in new_hooks.hooks[stack_action][hook_timing]:
                    self.hooks[stack_action][hook_timing].append(new_hook_item)


    def run(self, stack_action, stack_timing, stack):
        for hook in self.hooks[stack_action][stack_timing]:
            stack.log_action('Run', "Hook", message=": {}: {}: {}".format(hook['name'], stack_timing, stack_action))
            hook['method'](hook, hook['arg'])

    def gen_cache_id(self):
        cache_id = ""
        for action in ['create', 'update']:
            for timing in self.hooks[action].keys():
                for hook in self.hooks[action][timing]:
                    if hook['cache_method'] != None:
                        cache_id += hook['cache_method'](hook, hook['arg'])
        return cache_id

class Stack():
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        grp_ctx,
        template,
        stack_suffix=None,
        aws_region=None,
        hooks=None,
        do_not_cache=False,
        stack_tags=None,
        update_only=False,
        change_protected=False
    ):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.grp_ctx = grp_ctx
        self.termination_protection = False
        self.stack_suffix = stack_suffix
        if aws_region == None:
            raise StackException(AimErrorCode.Unknown, message="AWS Region is not supplied")
        self.aws_region = aws_region
        # Load the template
        template.stack = self
        self.template = template
        self.status = StackStatus.NONE
        self.stack_id = None
        self.cached = False
        self.max_account_name_size = 12
        self.max_action_name_size = 12
        self.output_config_dict = None
        self.action = None
        self.do_not_cache = do_not_cache
        self.update_only = update_only
        self.change_protected = change_protected
        # Wait for stack to delete if this flag is set
        self.wait_for_delete = False

        self.tags = StackTags(stack_tags)
        self.tags.add_tag('AIM-Stack', 'true')
        self.tags.add_tag('AIM-Stack-Name', self.get_name())

        self.outputs_value_cache = {}

        if hooks == None:
            self.hooks = StackHooks(self.aim_ctx)
        else:
            self.hooks = hooks
            self.hooks.stack = self
            self.hooks.log_hooks()

    #--------------------------------------------------------
    # Use properties here for just-in-time processing as the
    # template's yaml path may change if a template uses
    # the set_template_file_id() method
    @property
    def cache_filename(self):
        return self.template.get_yaml_path() + ".cache"
    @property
    def output_filename(self):
        return self.template.get_yaml_path() + ".output"
    @property
    def cfn_client(self):
        if hasattr(self, '_cfn_client') == False:
            self._cfn_client = self.account_ctx.get_aws_client('cloudformation', self.aws_region, force=True)
        return self._cfn_client


    #--------------------------------------------------------

    def set_template(self, template):
        self.template = template
        self.template.stack = self

    def add_hooks(self, hooks):
        self.hooks.merge(hooks)

    def set_termination_protection(self, protection_enabled):
        self.termination_protection = protection_enabled

    def get_stack_output_config(self):
        return self.output_config_dict

    def create_stack_name(self, name):
        """
        Must contain only letters, numbers, dashes and start with an alpha character.
        """
        if name.isalnum():
            return name

        new_name = ""
        for ch in name:
            if ch.isalnum() == False:
                ch = '-'
            new_name += ch

        return new_name

    def get_name(self):
        name = '-'.join([ self.grp_ctx.get_aws_name(),
                          self.template.aws_name])
        if self.stack_suffix != None:
            name = name + '-' + self.stack_suffix

        new_name = self.create_stack_name(name)

        if new_name[0].isalpha() == False:
            raise StackException(AimErrorCode.InvalidStackName)

        return new_name


    def validate(self):
        self.template.validate()

    def get_status(self):
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
                    delattr(self, '_cfn_client')
                    self.log_action("Token", "Expired", "Retry")
                    continue
                else:
                    message = self.get_stack_error_message(
                        prefix_message=e.response['Error']['Message'],
                        skip_status = True
                    )
                    raise StackException(AimErrorCode.Unknown, message=message)
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

    def get_outputs_value(self, key):

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
                    raise StackException(AimErrorCode.StackDoesNotExist, message = message)
                elif e.response['Error']['Code'] == 'ExpiredToken':
                    delattr(self, '_cfn_client')
                    self.log_action("Token", "Expired", "Retry")
                    # XXX: This doesn't seem to work and its tricky to get here. Debug it!
                    breakpoint()
                    continue
                else:
                    raise StackException(AimErrorCode.Unknown, message=e.response['Error']['Message'])
            break

        if 'Outputs' not in stack_metadata['Stacks'][0].keys():
            raise StackException(AimErrorCode.StackOutputMissing, message='No outputs are registered for this stack. This can happen if there are register_stack_output_config() calls in a cftemplate for Outputs that do not exist.')

        for output in stack_metadata['Stacks'][0]['Outputs']:
            if output['OutputKey'] == key:
                self.outputs_value_cache[key] = output['OutputValue']
                return self.outputs_value_cache[key]

        message = self.get_stack_error_message()
        message += "Could not find Stack Output {} in stack_metadata:\n\n{}\n".format(key, stack_metadata)
        raise StackException(
            AimErrorCode.StackOutputMissing,
            message=message
        )

    def get_outputs_key_from_ref(self, ref):

        key = self.template.get_outputs_key_from_ref(ref)
        if key == None:
            message = self.get_stack_error_message()
            message += "Error: Unable to find outputs key for ref: {}\n".format(ref.raw)
            raise StackException(
                AimErrorCode.Unknown,
                message=message)
        return key

    def gen_cache_id(self):
        # CloudFormation Template
        new_cache_id = self.template.gen_cache_id()
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
        if self.aim_ctx.nocache or self.do_not_cache:
            #return False
            # XXX: Make this work
            if self.template.dependency_group == True:
                self.get_status()
                if self.status == StackStatus.DOES_NOT_EXIST:
                    return False
                elif self.template.template_file_id != None:
                    if self.template.template_file_id.startswith('parent-') == False:
                        return False
            else:
                return False
        try:
            new_cache_id = self.gen_cache_id()
        except AimException as e:
            if e.code == AimErrorCode.StackDoesNotExist:
                return False
            elif e.code == AimErrorCode.StackOutputMissing:
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

    def save_stack_outputs(self):
        self.output_config_dict = self.template.process_stack_output_config(self)

        with open(self.output_filename, "w") as output_fd:
            yaml.dump(
                data=self.output_config_dict,
                stream=output_fd
            )

        stack_outputs_manager.add(self.aim_ctx.home, self.output_config_dict)

    # Actions to perform when a stack has been successfully created or updated
    def stack_success(self):
        if self.action != "delete":
            # Create cache file
            new_cache_id = self.gen_cache_id()
            with open(self.cache_filename, "w") as cache_fd:
                cache_fd.write(new_cache_id)

            # Save stack outputs to yaml
            self.save_stack_outputs()
            self.template.apply_template_changes()
            self.template.apply_stack_parameters()

    def create_stack(self):
        # Create Stack
        if self.update_only == True:
            self.log_action("Provision", "Disabled")
            return
        self.action = "create"
        self.log_action("Provision", "Create")
        try:
            stack_parameters = self.template.generate_stack_parameters()
        except StackException as e:
            e.message += "Error generating stack parameters for template\n"
            if e.code == AimErrorCode.StackDoesNotExist:
                self.log_action("Provision", "Error")
                e.message += "Stack: {}\n".format(self.get_name())
                e.message += "Error: Depends on StackOutputs from a stack that does not yet exist.\n"
            raise e
        self.hooks.run("create", "pre", self)
        response = self.cfn_client.create_stack(
            StackName=self.get_name(),
            TemplateBody=self.template.body,
            Parameters=stack_parameters,
            DisableRollback=True,
            Capabilities=self.template.capabilities,
            Tags=self.tags.cf_list()
            # EnableTerminationProtection=False
        )
        self.stack_id = response['StackId']

        self.cfn_client.update_termination_protection(
            EnableTerminationProtection=True,
            StackName=self.get_name()
        )

    def update_stack(self):
        # Update Stack
        if self.change_protected == True:
            self.log_action("Provision", "Protected")
            return
        self.action = "update"
        self.log_action("Provision", "Update")
        stack_parameters = self.template.generate_stack_parameters()
        self.template.confirm_stack_parameter_changes(stack_parameters)
        self.template.validate_template_changes()

        if True == False and self.aim_ctx.yes == False:
            print("A Stack is about to be modified: {}".format(self.get_name()))
            answer = self.aim_ctx.input_confirm_action("Make changes to the stack?")
            if answer == False:
                print("Stack update aborted.")
                return

        self.hooks.run("update", "pre", self)
        while True:
            try:
                self.cfn_client.update_stack(
                    StackName=self.get_name(),
                    TemplateBody=self.template.body,
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
                        raise StackException(AimErrorCode.Unknown, message = message)
                elif e.response['Error']['Code'] == 'ExpiredToken':
                    delattr(self, '_cfn_client')
                    self.log_action("Token", "Expired", "Retry")
                    # XXX: This doesn't seem to work and its tricky to get here. Debug it!
                    breakpoint()
                    continue
                else:
                    #message = "Stack: {}\nError: {}\n".format(self.get_name(), e.response['Error']['Message'])
                    message = self.get_stack_error_message()
                    raise StackException(AimErrorCode.Unknown, message = message)
            break

        if self.cfn_stack_describe['EnableTerminationProtection'] == False:
            self.cfn_client.update_termination_protection(
                EnableTerminationProtection=True,
                StackName=self.get_name()
            )

    def delete_stack(self):
        self.get_status()
        self.action = "delete"
        if self.is_exists() == True:
            # Delete Stack
            if self.termination_protection == True:
                print("\n!! This Stack has 'Termination Protection' enabled.")
                print("\n!! Stack Name: {}\n".format(self.get_name()))
                answer = self.aim_ctx.input_confirm_action("Destroy this stack forever?")
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
        if skip_status == False:
            self.get_status()
        message = "\n"+prefix_message
        message += "Stack:         {}\n".format(self.get_name())
        message += "Template:      {}\n".format(self.template.get_yaml_path())
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
                        delattr(self, '_cfn_client')
                        self.log_action("Token", "Expired", "Retry")
                        # XXX: This doesn't seem to work and its tricky to get here. Debug it!
                        breakpoint()
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
        self.template.provision()

        # If last md5 is equal, then we no changes are required
        if self.is_stack_cached() == True:
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
            answer = self.aim_ctx.input_confirm_action("\nDelete it?", default='y')
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
            raise StackException(AimErrorCode.Unknown, message = message)

    def delete(self):
        self.template.delete()
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

    def log_action_header(self):
        global log_next_header
        if log_next_header != None:
            self.aim_ctx.log_action_col(log_next_header, 'Account', 'Action', 'Stack Name')
            log_next_header = None


    def log_action(self, action, stack_action, account_name=None, stack_name=None, message=None, return_it=False):
        if account_name == None:
            msg_account_name = self.account_ctx.get_name()
        else:
            msg_account_name = account_name

        if stack_name == None:
            msg_stack_name = self.get_name()
        else:
            msg_stack_name = stack_name

        if self.template.template_file_id != None:
            msg_stack_name += ': dependency group: ' + self.template.template_file_id
        stack_message = msg_stack_name
        if message != None:
            stack_message += ': '+message
        global log_next_header
        if return_it == False:
            self.log_action_header()
        log_message = self.aim_ctx.log_action_col(
            action,
            msg_account_name,
            stack_action,
            stack_message,
            return_it
        )
        if return_it == True:
            return log_message

    def wait_for_complete(self, verbose=False):
        if self.action == None:
            return
        self.get_status()
        waiter = None
        action_name = "Provision"
        if self.is_updating():
            if verbose:
                self.log_action("Provision", "Update")
            waiter = self.cfn_client.get_waiter('stack_update_complete')
        elif self.is_creating():
            if verbose:
                self.log_action("Provision", "Create")
            waiter = self.cfn_client.get_waiter('stack_create_complete')
        elif self.is_deleting():
            if verbose:
                self.log_action("Delete", "Stack")
            action_name = "Delete"
            waiter = self.cfn_client.get_waiter('stack_delete_complete')
        elif self.is_complete():
            pass
        elif not self.is_exists():
            pass
        else:
            message = self.get_stack_error_message()
            raise StackException(
                AimErrorCode.WaiterError,
                message=message
            )

        if waiter != None:
            self.log_action(action_name, "Wait")
            try:
                waiter.wait(StackName=self.get_name())
            except WaiterError as waiter_exception:
                self.log_action(action_name, "Error")
                message = "Waiter Error:  {}\n".format(waiter_exception)
                message += self.get_stack_error_message(message)
                raise StackException(AimErrorCode.WaiterError, message = message)
            self.log_action(action_name, "Done")

        if self.is_exists():
            self.stack_success()

        if self.action == "create":
            self.hooks.run("create", "post", self)
        elif self.action == "update":
            self.hooks.run("update", "post", self)
        elif self.action == "delete":
            self.hooks.run("delete", "post", self)

class StackGroup():
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 group_name,
                 aws_name,
                 controller):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.controller = controller
        self.name = group_name
        self.aws_name = aws_name
        self.stacks = []
        self.stack_orders = []
        self.controller.cur_stack_grp = self
        self.stack_output_config = {}
        self.state = None
        self.prev_state = None
        self.filter_config = controller.stack_group_filter
        self.state_filename = '-'.join([self.get_aws_name(), self.name, "StackGroup-State.yaml"])
        self.state_filepath = os.path.join(self.aim_ctx.build_folder, self.state_filename)

    def delete_stack(self, account_name, region, stack_name):
        pass
        # XXX: not used
        # Delete Stack
        #account_ctx = self.aim_ctx.get_account_context(account_name=account_name)
        #cf_client = account_ctx.get_aws_client('cloudformation', region)
        #cf_client.delete_stack( StackName=stack_name )

    def new_state(self):
        state = {
            'stack_names': [],
            'account_names': [],
            'regions': []
        }
        return state

    def load_state(self):
        if os.path.isfile(self.state_filepath) == False:
            return self.new_state()
        with open(self.state_filepath, "r") as stream:
            state = yaml.load(stream)
        if state == None:
            return self.new_state()
        return state

    def gen_state(self):
        state = self.new_state()

        for stack in self.stacks:
            state['stack_names'].append(stack.get_name())
            state['account_names'].append(stack.account_ctx.get_name())
            state['regions'].append(stack.aws_region)

        return state

    def update_state(self):
        cur_state = self.load_state()
        new_state = self.gen_state()
        deleted_stacks = []
        for stack_name in cur_state['stack_names']:
            if stack_name not in new_state['stack_names']:
                stack_idx = cur_state['stack_names'].index(stack_name)
                deleted_stacks.append(stack_idx)

        if len(deleted_stacks) > 0:
            print("The following Stacks are no longer needed:\n")
            for idx in deleted_stacks:
                print("   - %s.%s: %s" % (
                    cur_state['account_names'][idx],
                    cur_state['regions'][idx],
                    cur_state['stack_names'][idx]
                ))
            answer = self.aim_ctx.input_confirm_action("\nDelete them from your AWS environment?")
            if answer == True:
                for idx in deleted_stacks:
                    self.delete_stack(
                        cur_state['account_names'][idx],
                        cur_state['regions'][idx],
                        cur_state['stack_names'][idx]
                    )

                    # TODO: Wait for the stacks

        with open(self.state_filepath, "w") as output_fd:
                yaml.dump(  data=new_state,
                            stream=output_fd)

    def filtered_stack_action(self, stack, action_method):
        if self.filter_config != None:
            if stack.template.config_ref.startswith(self.filter_config):
                action_method()
            else:
                stack.log_action(
                    action_method.__func__.__name__.capitalize(),
                    'Filtered'
                )
        else:
            action_method()

    def validate(self):
        # Loop through stacks and validate each
        for order_item in self.stack_orders:
            if order_item.order == StackOrder.PROVISION:
                self.filtered_stack_action(
                    order_item.stack,
                    order_item.stack.validate
                )

    def provision(self):
        # Loop through stacks and provision each one
        wait_last_list = []
        for order_item in self.stack_orders:
            if order_item.order == StackOrder.PROVISION:
                self.filtered_stack_action(
                    order_item.stack,
                    order_item.stack.provision
                )
            elif order_item.order == StackOrder.WAIT:
                if order_item.stack.cached == False:
                    order_item.stack.wait_for_complete(verbose=False)
            elif order_item.order == StackOrder.WAITLAST:
                wait_last_list.append(order_item)

        for order_item in wait_last_list:
            if order_item.stack.cached == False:
                order_item.stack.wait_for_complete(verbose=False)

        # Disabling stack state for now as it seems stacks are being
        # suggested to be deleted when they shouldn't be.
        # self.update_state()

    def delete(self):
        # Loop through stacks and deletes each one
        for order_item in reversed(self.stack_orders):
            if order_item.order == StackOrder.PROVISION:
                self.filtered_stack_action(
                    order_item.stack,
                    order_item.stack.delete
                )

        for order_item in reversed(self.stack_orders):
            if order_item.order == StackOrder.WAIT:
                order_item.stack.wait_for_complete(verbose=False)

    def get_stack_order(self, stack, order):
        for stack_order in self.stack_orders:
            if stack_order.stack == stack and stack_order.order == order:
                return stack_order
        return None

    def pop_stack_order(self, stack, order):
        stack_order = self.get_stack_order(stack, order)
        if stack_order == None:
            # If one does not exist, create a new one
            return StackOrderItem(order, stack)
        self.stack_orders.remove(stack_order)
        return stack_order

    def add_stack_order(self, stack, orders=[StackOrder.PROVISION, StackOrder.WAIT]):
        for order in orders:
            stack_order = self.pop_stack_order(stack=stack,
                                               order=order)
            self.stack_orders.append(stack_order)
        if not stack in self.stacks:
            self.stacks.append(stack)

    def get_aws_name(self):
        name = '-'.join([self.controller.get_aws_name(),
                         self.aws_name])
        return name