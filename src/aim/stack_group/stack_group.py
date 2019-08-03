import boto3
import os
import sys
import time
from aim.core.exception import StackException
from aim.core.exception import AimException, AimErrorCode
from botocore.exceptions import ClientError
from enum import Enum
from aim.core.yaml import YAML
from aim.config import aim_context
from copy import deepcopy

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

StackEnum = Enum('StackEnum', 'vpc segment')

StackStatus = Enum('StackStatus', 'NONE DOES_NOT_EXIST CREATE_IN_PROGRESS CREATE_FAILED CREATE_COMPLETE ROLLBACK_IN_PROGRESS ROLLBACK_FAILED ROLLBACK_COMPLETE DELETE_IN_PROGRESS DELETE_FAILED DELETE_COMPLETE UPDATE_IN_PROGRESS UPDATE_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_COMPLETE UPDATE_ROLLBACK_IN_PROGRESS UPDATE_ROLLBACK_FAILED UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_ROLLBACK_COMPLETE REVIEW_IN_PROGRESS')

StackOrder = Enum('StackOrder', 'PROVISION WAIT')

#class StackOrder():
#    def __init__(self):
#        self.PROVISION = 0
#        self.WAIT = 1


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
        return aim_context.md5sum(str_data=yaml.dump(self.tags))


class StackOrderItem():
    def __init__(self, order, stack):
        self.order = order
        self.stack = stack

class StackHooks():

    def __init__(self, aim_ctx):
         # Init Stack Hooks
        self.aim_ctx = aim_ctx
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
        print("Adding hook: %s: %s: %s" % (name, stack_action, stack_timing))

    def merge(self, new_hooks):
        if new_hooks == None:
            return
        for stack_action in self.hooks.keys():
            for hook_timing in self.hooks[stack_action].keys():
                for new_hook_item in new_hooks.hooks[stack_action][hook_timing]:
                    self.hooks[stack_action][hook_timing].append(new_hook_item)


    def run(self, stack_action, stack_timing, stack):
        for hook in self.hooks[stack_action][stack_timing]:
            action_name = self.aim_ctx.str_spc("Hook:", stack.max_action_name_size)
            account_name = self.aim_ctx.str_spc(stack.account_ctx.get_name()+":", stack.max_account_name_size)
            print("{0} {1} {2}: {3}.{4}: {5}".format(account_name, action_name, stack.get_name(), stack_action, stack_timing, hook['name'] ))

            hook['method'](hook, hook['arg'])

    def gen_cache_id(self):
        cache_id = ""
        for action in ['create', 'update']:
            for timing in self.hooks[action].keys():
                for hook in self.hooks[action][timing]:
                    if hook['cache_method'] != None:
                        cache_id += hook['cache_method'](hook, hook['arg'])
                        break
        return cache_id

class Stack():
    def __init__(self, aim_ctx, account_ctx, grp_ctx, stack_config, template,
                 stack_suffix=None,
                 aws_region=None,
                 hooks=None,
                 do_not_cache=False,
                 stack_tags=None):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.grp_ctx = grp_ctx
        self.termination_protection = False
        self.stack_suffix = stack_suffix
        if aws_region == None:
            raise StackException(AimErrorCode.Unknown)
        self.aws_region = aws_region
        self.cf_client = self.account_ctx.get_aws_client('cloudformation', aws_region)
        # self.cf_res = boto3.resource('cloudformation')

        # Load the template
        template.stack = self
        self.template = template
        #self.config = stack_config
        self.status = StackStatus.NONE
        self.stack_id = None
        self.cached = False
        self.max_account_name_size = 7
        self.max_action_name_size = 8
        self.output_config_dict = None
        self.action = None
        self.do_not_cache = do_not_cache

        self.tags = StackTags(stack_tags)
        self.tags.add_tag('AIM-Stack', 'true')
        self.tags.add_tag('AIM-Stack-Name', self.get_name())

        self.cache_filename = self.template.get_yaml_path() + ".cache"
        self.output_filename = self.template.get_yaml_path() + ".output"

        self.outputs_value_cache = {}

        if hooks == None:
            self.hooks = StackHooks(self.aim_ctx)
        else:
            self.hooks = hooks

    def set_template(self, template):
        self.template = template
        self.template.stack = self

    def add_hooks(self, hooks):
        self.hooks.merge(hooks)

    def set_termination_protection(self, protection_enabled):
        self.termination_protection = protection_enabled

    def get_stack_output_config(self):
        return self.output_config_dict

    def get_name(self):
        name = '-'.join([ self.grp_ctx.get_aws_name(),
                          self.template.aws_name])
        if self.stack_suffix != None:
            name = name + '-' + self.stack_suffix

        #print("stack_group: get_name: Stack Name: " + name)
        return name


    def validate(self):
        self.template.validate()

    def get_status(self):
        #print("Get stack status: "+ self.get_name())
        while True:
            try:
                stack_list = self.cf_client.describe_stacks(StackName=self.get_name())
            except ClientError as e:
                #print(repr(e.response))
                if e.response['Error']['Code'] == 'ValidationError' and e.response['Error']['Message'].endswith("does not exist"):
                    self.status = StackStatus.DOES_NOT_EXIST
                elif e.response['Error']['Code'] == 'ClientError' and e.response['Error']['Message'].endswith("Rate exceeded"):
                    # Lets try again in a little bit
                    print("Warning: Get Status throttled")
                    time.sleep(1)
                    continue

                else:
                    print(e.response['Error']['Message'])
                    raise StackException(AimErrorCode.Unknown)
            else:
                #pprint(stack_list)
                self.status = StackStatus[stack_list['Stacks'][0]['StackStatus']]
                self.stack_id = stack_list['Stacks'][0]['StackId']
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
            #self.aim_ctx.log("is_complete is True: " + self.status.name)
            return True

        #self.aim_ctx.log("is_complete is False: " + self.status.name)
        return False

    def is_exists(self):
        if not "DOES_NOT_EXIST" in self.status.name:
            return True

    def get_outputs_value(self, key):
        if key in self.outputs_value_cache.keys():
            return self.outputs_value_cache[key]

        try:
            stack_metadata = self.cf_client.describe_stacks(StackName=self.get_name())
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError' and e.response['Error']['Message'].find("does not exist") != -1:
                # Debug how we got here and what to do about it
                print("Error: Stack does not exist: %s")
                print("  If it was manually deleted from the AWS Web Console, then this error is caused")
                print("  because the stack.cache file still exists.\n")
                print("  Try this and re-run aim:\n")
                print("  rm %s" % (self.cache_filename))
                os.remove(self.cache_filename)
                sys.exit(255)
                raise StackException(AimErrorCode.StackDoesNotExist)
            else:
                print(e.response['Error']['Message'])
                raise StackException(AimErrorCode.Unknown)
        #print(key + ": get_outputs_value: " + repr(stack_metadata['Stacks'][0]['Outputs']))
        if 'Outputs' not in stack_metadata['Stacks'][0].keys():
            # We get here sometimes after breaking and then
            # re-running the aim cli
            pass
        for output in stack_metadata['Stacks'][0]['Outputs']:
            #print(output['OutputKey'] + " == " + key)
            if output['OutputKey'] == key:
                #print("Returning: " + output['OutputValue'])
                self.outputs_value_cache[key] = output['OutputValue']
                return self.outputs_value_cache[key]

        breakpoint()
        raise StackException(
            AimErrorCode.Unknown,
            message="Could not find Stack Output {} in stack_metadata:\n\n{}".format(key, stack_metadata)
        )

    def get_outputs_key_from_ref(self, aim_ref):
        #print("Template: " + self.template.aws_name)
        key = self.template.get_outputs_key_from_ref(aim_ref)
        #pprint("get_outputs_key_from_ref: " + key)
        if key == None:
            raise StackException(AimErrorCode.Unknown)
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
            return False
        try:
            new_cache_id = self.gen_cache_id()
        except AimException as e:
            #AimErrorCode.StackDoesNotExist:
            if e.code == AimErrorCode.StackDoesNotExist:
                return False
            else:
                raise e


        #print("New Cache ID: " + new_cache_id)
        cache_id = "none"
        if os.path.isfile(self.cache_filename):
            with open(self.cache_filename, "r") as cache_fd:
                cache_id = cache_fd.read()

        #print("!!!!!!!!!! Cache ID check: new: {0} == old: {1}".format(new_cache_id, cache_id))
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

    # Actions to perform when a stack has been successfully created or updated
    def stack_success(self):
        if self.action != "delete":
            # Create cache file
            new_cache_id = self.gen_cache_id()
            #print(new_cache_id)
            with open(self.cache_filename, "w") as cache_fd:
                cache_fd.write(new_cache_id)
            #print("Stack success: Created cache file: " + self.cache_filename + ": " + new_cache_id)

            # Save stack outputs to yaml
            self.output_config_dict = self.template.process_stack_output_config(self)
            with open(self.output_filename, "w") as output_fd:
                yaml.dump(data=self.output_config_dict,
                        stream=output_fd)

    def create_stack(self):
        # Create Stack
        self.action = "create"
        account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+":", self.max_account_name_size)
        action_name = self.aim_ctx.str_spc("Create:", self.max_action_name_size)
        self.aim_ctx.log("{0} {1} {2}".format(account_name, action_name, self.get_name()))
        try:
            stack_parameters = self.template.generate_stack_parameters()
        except StackException as e:
            if e.code == AimErrorCode.StackDoesNotExist:
                print("Stack: %s: Error: Depends on StackOutputs from a stack that does not yet exist." % (self.get_name()))
            raise e
        self.hooks.run("create", "pre", self)
        response = self.cf_client.create_stack(
            StackName=self.get_name(),
            TemplateBody=self.template.body,
            Parameters=stack_parameters,
            DisableRollback=True,
            Capabilities=self.template.capabilities,
            Tags=self.tags.cf_list()
            # EnableTerminationProtection=False
        )
        self.stack_id = response['StackId']

    def update_stack(self):
        # Update Stack
        self.action = "update"
        action_name = self.aim_ctx.str_spc("Update:", self.max_action_name_size)
        account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+":", self.max_account_name_size)
        print("{0} {1} {2}".format(account_name, action_name, self.get_name()))
        stack_parameters = self.template.generate_stack_parameters()
        self.hooks.run("update", "pre", self)
        try:
            self.cf_client.update_stack(
                StackName=self.get_name(),
                TemplateBody=self.template.body,
                Parameters=stack_parameters,
                Capabilities=self.template.capabilities,
                UsePreviousTemplate=False,
                Tags=self.tags.cf_list()
            )
            #pprint(repr(response))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                success = False
                if e.response['Error']['Message'].endswith("No updates are to be performed."):
                    success = True
                elif e.response['Error']['Message'].endswith("is in UPDATE_COMPLETE_CLEANUP_IN_PROGRESS state and can not be updated."):
                    success = True

                if success == True:
                    msg = self.aim_ctx.str_spc("", self.max_account_name_size+1)
                    #print("msg: |{0}|".format(msg))
                    msg += self.aim_ctx.str_spc("Done:", self.max_action_name_size)
                    print("{0} {1}".format(msg, self.get_name()))
                    self.stack_success()
                else:
                    print(e.response['Error']['Message'])
                    raise StackException(AimErrorCode.Unknown)
            else:
                print(e.response['Error']['Message'])
                raise StackException(AimErrorCode.Unknown)

        self.cf_client.update_termination_protection(
            EnableTerminationProtection=self.termination_protection,
            StackName=self.get_name()
        )

    def delete_stack(self):
        # Delete Stack
        self.action = "delete"
        account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+":", self.max_account_name_size)
        action_name = self.aim_ctx.str_spc("Delete:", self.max_action_name_size)
        self.aim_ctx.log("{0} {1} {2}".format(account_name, action_name, self.get_name()))
        self.hooks.run("delete", "pre", self)
        self.cf_client.delete_stack( StackName=self.get_name() )

    def provision(self):
        #self.aim_ctx.log("StackGroup.provision")
        # TODO:
        #  1. If stack does not exist
        #     1.1 Create stack
        #  2. Else
        #     2.1 If stack is failed
        #         2.1.1 Delete stack if configured
        #     2.1 Else
        #         2.1.1 Update stack
        #print("Provision: "+ self.get_name())
        self.template.provision()

        # If last md5 is equal, then we no changes are required
        if self.is_stack_cached() == True:
            account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+':', self.max_account_name_size)
            action_name = self.aim_ctx.str_spc("Cached:", self.max_action_name_size)
            print("{0} {1} {2}".format(account_name, action_name, self.get_name()))
            return

        self.get_status()
        if self.status == StackStatus.DOES_NOT_EXIST:
            self.create_stack()
        elif self.is_complete():
            self.update_stack()
        elif self.is_creating() or self.is_updating() or self.is_deleting():
            account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+':', self.max_account_name_size)
            if self.is_creating():
                action_name = self.aim_ctx.str_spc("Create:", self.max_action_name_size)
                self.action = "create"
            elif self.is_deleting():
                action_name = self.aim_ctx.str_spc("Delete:", self.max_action_name_size)
                self.action = "delete"
            else:
                action_name = self.aim_ctx.str_spc("Update:", self.max_action_name_size)
                self.action = "update"
            print("{0} {1} {2}".format(account_name, action_name, self.get_name()))
#        elif self.has_failure_status():
            # Delete stack here if in error state
#            pass
        elif self.is_creating() == False and self.is_updating() == False:
            account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+':', self.max_account_name_size)
            action_name = self.aim_ctx.str_spc("Error:", self.max_action_name_size)
            print("{0} {1} {2}".format(account_name, action_name, self.get_name()))
            print(self.status)
            raise StackException(AimErrorCode.Unknown)

        #instance-profile/NE-aimdemo-dev-App-app-usw2-Profile-instance-iam-role
        #instance-profile/NE-aimdemo-dev-App-app-usw2-Role-site-webapp-instance-iam-role


    def delete(self):

        self.template.delete()
        self.delete_stack()
        try:
            os.remove(self.cache_filename)
        except FileNotFoundError:
            pass
        try:
            os.remove(self.output_filename)
        except FileNotFoundError:
            pass


    def wait_for_complete(self, verbose=False):
        if self.action == None:
            return
        self.get_status()
        waiter = None
        account_name = self.aim_ctx.str_spc(self.account_ctx.get_name()+":", self.max_account_name_size)
        action_name = self.aim_ctx.str_spc(self.action.capitalize()+":", self.max_action_name_size)
        detail_log = "{0} {1} {2}".format(account_name, action_name, self.get_name())
        #print("Wait For Complete??: " + detail_log)
        if self.is_updating():
            #self.aim_ctx.log("Waiting for stack update complete")
            if verbose:
                print(detail_log)
            waiter = self.cf_client.get_waiter('stack_update_complete')
        elif self.is_creating():
            #self.aim_ctx.log("Waiting for stack create complete")
            if verbose:
                print(detail_log)
            waiter = self.cf_client.get_waiter('stack_create_complete')
        elif self.is_deleting():
            #self.aim_ctx.log("Waiting for stack create complete")
            if verbose:
                print(detail_log)
            waiter = self.cf_client.get_waiter('stack_delete_complete')
        elif self.is_complete():
            pass
            #self.aim_ctx.log("Stack status is already complete")
#            self.stack_success()
        elif not self.is_exists():
            pass
        else:
            print("Unknown status: ")
            print(self.status)
            raise StackException(AimErrorCode.Unknown)

        if waiter != None:
            msg = self.aim_ctx.str_spc("", self.max_account_name_size+1)
            msg += self.aim_ctx.str_spc("Waiting:", self.max_action_name_size)
            print("{0} {1}".format(msg, self.get_name()))
            waiter.wait(StackName=self.get_name())
            msg = self.aim_ctx.str_spc("", self.max_account_name_size+1)
            msg += self.aim_ctx.str_spc("Done:", self.max_action_name_size)
            print("{0} {1}".format(msg, self.get_name()))

        if self.is_exists():
            self.stack_success()

        if self.action == "create":
            self.hooks.run("create", "post", self)
        elif self.action == "update":
            self.hooks.run("update", "post", self)
        elif self.action == "delete":
            self.hooks.run("delete", "post", self)
        #self.aim_ctx.log("Waiting complete: " + self.get_name())



class StackGroup():
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 group_name,
                 aws_name,
                 controller):
        #aim_ctx.log("stack group init")
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
        self.state_filename = '-'.join([self.get_aws_name(), group_name, "StackGroup-State.yaml"])
        self.state_filepath = os.path.join(self.aim_ctx.build_folder, self.state_filename)

    def delete_stack(self, account_name, region, stack_name):
        # Delete Stack
        account_ctx = self.aim_ctx.get_account_context(account_name=account_name)
        cf_client = account_ctx.get_aws_client('cloudformation', region)
        cf_client.delete_stack( StackName=stack_name )

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
            answer = self.aim_ctx.input("\nDelete them from your AWS environment?", default="Y", yes_no_prompt=True)
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
        #deleted_stack.wait_for_complete(verbose=False)



    def validate(self):
        #self.aim_ctx.log("Stack group validate")
        # Loop through stacks and validate each
        for order_item in self.stack_orders:
            if order_item.order == StackOrder.PROVISION:
                order_item.stack.validate()

    def provision(self):
        # Loop through stacks and provision each one
        for order_item in self.stack_orders:
            #print("StackGroup: Provision: %s: %d" % (order_item.stack.get_name(), order_item.order.value))
            if order_item.order == StackOrder.PROVISION:
                order_item.stack.provision()
            elif order_item.order == StackOrder.WAIT:
                if order_item.stack.cached == False:
                    #print("StackGroup: Provision: Wait: %s: %d" % (order_item.stack.get_name(), order_item.order.value))
                    order_item.stack.wait_for_complete(verbose=False)
                #else:
                    #print("StackGroup: Provision: Cached: %s: %d" % (order_item.stack.get_name(), order_item.order.value))
        self.update_state()

    def delete(self):
        # Loop through stacks and deletes each one
        for order_item in reversed(self.stack_orders):
            if order_item.order == StackOrder.PROVISION:
                order_item.stack.delete()

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
            #print("Stack Order: append: %s: %d" % (stack.get_name(), order.value))
            self.stack_orders.append(stack_order)
        if not stack in self.stacks:
            self.stacks.append(stack)


    def get_aws_name(self):
        name = '-'.join([self.controller.get_aws_name(),
                         self.aws_name])
        return name