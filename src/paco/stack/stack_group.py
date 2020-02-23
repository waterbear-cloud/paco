from paco import utils
from paco.core.exception import StackException
from paco.core.exception import PacoException, PacoErrorCode
from paco.stack import Stack
from botocore.exceptions import ClientError, WaiterError
from enum import Enum
from paco.core.yaml import YAML
from paco.utils import md5sum, dict_of_dicts_merge
import boto3
import os
import pathlib
import ruamel.yaml.parser
import sys
import time


yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

StackOrder = Enum('StackOrder', 'PROVISION WAIT WAITLAST')


class StackOrderItem():
    def __init__(self, order, stack):
        self.order = order
        self.stack = stack


class StackGroup():
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        group_name,
        aws_name,
        controller
    ):
        self.paco_ctx = paco_ctx
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
        self.state_filepath = self.paco_ctx.build_path / self.state_filename

    def add_stack_group(self, stack_group):
        self.add_stack_order(stack_group)

    def add_new_stack(
        self,
        aws_region,
        resource,
        template_class,
        stack_tags=None,
        stack_hooks=None,
        stack_orders=None,
        change_protected=None,
        extra_context={},
        support_resource_ref_ext=None,
    ):
        "Creates a Stack and adds it to the StackGroup"
        stack = Stack(
            self.paco_ctx,
            self.account_ctx,
            self,
            resource,
            aws_region=aws_region,
            stack_tags=stack_tags,
            hooks=stack_hooks,
            change_protected=change_protected,
            support_resource_ref_ext=support_resource_ref_ext,
        )
        if stack_orders == None:
            stack.orders = [StackOrder.PROVISION, StackOrder.WAIT]
        else:
            stack.orders = stack_orders
        self.add_stack_order(stack)

        # cook the template and add it to the stack
        stack.template = template_class(stack, self.paco_ctx, **extra_context)

        # Now that the template is known, the full name of the stack in AWS is known
        if hasattr(self, 'tags'):
            self.tags.add_tag('Paco-Stack-Name', self.get_name())

        # hooks can't be logged until there is a template
        stack.hooks.log_hooks()

        return stack

    def delete_stack(self, account_name, region, stack_name):
        pass
        # XXX: not used
        # Delete Stack
        #account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
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
            answer = self.paco_ctx.input_confirm_action("\nDelete them from your AWS environment?")
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
            # Exact match or append '.' otherwise we might match
            # foo.bar wtih foo.bar_bad
            if stack.template.config_ref == self.filter_config or \
                stack.template.config_ref.startswith(self.filter_config+'.') or \
                stack.singleton:
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
                if isinstance(order_item.stack, StackGroup):
                    order_item.stack.validate()
                else:
                    self.filtered_stack_action(
                        order_item.stack,
                        order_item.stack.validate
                    )

    def provision(self):
        # Loop through stacks and provision each one
        wait_last_list = []
        for order_item in self.stack_orders:
            if order_item.order == StackOrder.PROVISION:
                if isinstance(order_item.stack, StackGroup):
                    # Nested StackGroup
                    order_item.stack.provision()
                else:
                    self.filtered_stack_action(
                        order_item.stack,
                        order_item.stack.provision
                    )
            elif isinstance(order_item.stack, StackGroup):
                # Nested StackGroup
                pass
            elif order_item.order == StackOrder.WAIT:
                # Nested StackGroup
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
                if isinstance(order_item.stack, StackGroup):
                    # Nested StackGroup
                    order_item.stack.delete()
                else:
                    self.filtered_stack_action(
                        order_item.stack,
                        order_item.stack.delete
                    )

        for order_item in reversed(self.stack_orders):
            if order_item.order == StackOrder.WAIT:
                if isinstance(order_item.stack, StackGroup) == True:
                    continue
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
        "Add Stack orders to the StackGroups orders"
        for order in stack.orders:
            stack_order = self.pop_stack_order(stack, order)
            self.stack_orders.append(stack_order)
        if not stack in self.stacks:
            self.stacks.append(stack)

    def get_aws_name(self):
        name = '-'.join([self.controller.get_aws_name(), self.aws_name])
        return name

    def get_stack_from_ref(self, ref):
        "Recursively searches all StackGroups for a Stack whose resource.ref starts with the given ref"
        for stack_obj in self.stacks:
            if isinstance(stack_obj, StackGroup) == True:
                # stack_obj is a StackGroup
                stack = stack_obj.get_stack_from_ref(ref)
                if stack != None:
                    return stack
            else:
                # stack_obj is a Stack
                stack_ref = stack_obj.stack_ref
                if stack_ref and stack_ref != '' and ref.raw.find(stack_ref) != -1:
                    if stack_ref == ref.ref or ref.ref.startswith(stack_ref + '.'):
                        return stack_obj
        # Nothing found, None returned
        return None