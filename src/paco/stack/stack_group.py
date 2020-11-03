from paco.stack import Stack
from paco.stack.interfaces import ICloudFormationStack, IBotoStack
from enum import Enum
from paco.core.yaml import YAML
import os


yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

StackOrder = Enum('StackOrder', 'PROVISION WAIT WAITLAST')

class StackOrderItem():
    def __init__(self, order, stack):
        self.order = order
        self.stack = stack


class StackGroup():
    """Group of AWS CloudFormation Stacks"""
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
        self.stack_output_config = {}
        self.state = None
        self.prev_state = None
        self.state_filename = '-'.join([self.get_aws_name(), self.name, "StackGroup-State.yaml"])
        self.state_filepath = self.paco_ctx.build_path / self.state_filename

    @property
    def filter_config(self):
        # Stack group filter can change, get it from the source
        return self.controller.stack_group_filter

    def get_aws_name(self):
        "Logical Name of the StackGroup"
        name = '-'.join([self.controller.get_aws_name(), self.aws_name])
        return name

    def new_state(self):
        "Empty state"
        return {
            'stack_names': [],
            'account_names': [],
            'regions': []
        }

    def load_state(self):
        "Read state from filesystem or return an empty state"
        if os.path.isfile(self.state_filepath) == False:
            return self.new_state()
        with open(self.state_filepath, "r") as stream:
            state = yaml.load(stream)
        if state == None:
            return self.new_state()
        return state

    def validate(self):
        "Loop through stacks and validate each one"
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
        "Loop through stacks and provision each one"
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
                    order_item.stack.wait_for_complete()
            elif order_item.order == StackOrder.WAITLAST:
                wait_last_list.append(order_item)

        for order_item in wait_last_list:
            if order_item.stack.cached == False:
                order_item.stack.wait_for_complete()

    def delete(self):
        "Loop through stacks and delete each one"
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
                order_item.stack.wait_for_complete()

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
        for order in orders:
            stack_order = self.pop_stack_order(stack, order)
            self.stack_orders.append(stack_order)
        if not stack in self.stacks:
            self.stacks.append(stack)

    def get_stack_from_ref(self, ref):
        "Returns a Stack whose stack_ref matches a given ref. Recursively searches all StackGroups."
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

    def filtered_stack_action(self, stack, action_method):
        "Call a stack action only if it falls within the scope"
        if self.filter_config == None:
            return action_method()
        stack_ref = None
        if ICloudFormationStack.providedBy(stack):
            stack_ref = stack.template.config_ref
        elif IBotoStack.providedBy(stack):
            stack_ref = stack.resource.paco_ref_parts
        # Exact match or append '.' otherwise foo.bar would match with foo.bar_bad
        if stack_ref == self.filter_config or stack_ref.startswith(self.filter_config + '.'):
            action_method()
        else:
            stack.log_action(action_method.__func__.__name__.capitalize(), 'Filtered')

    # methods specific to CloudFormation Stacks
    def add_new_stack(
        self,
        aws_region,
        resource,
        template_class,
        account_ctx=None,
        stack_tags=None,
        stack_hooks=None,
        stack_orders=None,
        change_protected=None,
        extra_context={},
        support_resource_ref_ext=None,
        set_resource_stack=False,
    ):
        "Creates a Stack and adds it to the StackGroup"
        if account_ctx == None:
            account_ctx = self.account_ctx
        if stack_orders == None:
            stack_orders = [StackOrder.PROVISION, StackOrder.WAIT]
        # change_protected should come from resource.change_protected but it is
        # used by ctl_role when making new Roles - these need to be refactored so that the Resource controlling
        # the Role is available when a Role is being modified - then this code can be removed

        stack = Stack(
            self.paco_ctx,
            account_ctx,
            self,
            resource,
            aws_region=aws_region,
            stack_tags=stack_tags,
            hooks=stack_hooks,
            change_protected=change_protected,
            support_resource_ref_ext=support_resource_ref_ext,
        )
        self.add_stack_order(stack, stack_orders)

        # make the stack available in the model
        # this only happens when there is one primary stack representing the resource
        # some resources have several stacks (CloudFront) or they have secondary stacks (Alarms, LogGroups)
        if set_resource_stack or resource.__class__.__name__ == template_class.__name__:
            resource.stack = stack

        # cook the template and add it to the stack
        stack.template = template_class(stack, self.paco_ctx, **extra_context)

        # now that the template has been created, post-template actions are possible
        if not hasattr(resource, 'is_enabled'):
            enabled = True
        else:
            enabled = resource.is_enabled()
        self.paco_ctx.log_action_col(
            "Init",
            template_class.__name__,
            account_ctx.name + '.' + aws_region,
            "stack: " + stack.get_name(),
            enabled=enabled
        )

        # Add Paco-Stack-Name tag
        if hasattr(stack, 'tags'):
            stack.tags.add_tag('Paco-Stack-Name', stack.get_name())
        # Log hooks
        stack.hooks.log_hooks()

        # add StackHooks set on the model
        if hasattr(resource, '_stack_hooks') and resource._stack_hooks != None and \
            hasattr(resource, 'stack') and resource.stack != None:
            for stack_hook in resource._stack_hooks:
                stack.add_hooks(stack_hook)

        return stack

    # methods for BotoStacks
    def add_new_boto_stack(
        self,
        aws_region,
        resource,
        stack_class,
        account_ctx=None,
        stack_tags=None,
        stack_hooks=None,
        stack_orders=None,
        change_protected=None,
        extra_context={},
        set_resource_stack=False,
    ):
        "Creates an API Stack and adds it to the StackGroup"
        if account_ctx == None:
            account_ctx = self.account_ctx
        if stack_orders == None:
            stack_orders = [StackOrder.PROVISION, StackOrder.WAIT]

        stack = stack_class(
            self.paco_ctx,
            account_ctx,
            self,
            resource,
            aws_region=aws_region,
            stack_tags=stack_tags,
            hooks=stack_hooks,
            change_protected=change_protected,
            extra_context=extra_context,
        )
        self.add_stack_order(stack, stack_orders)

        # initialize the stack
        stack.init()

        # make the stack available to the model
        # this only happens when there is one primary stack representing the resource and is
        # requested explicitly or the Class name matches the YAML resource type.
        # type: ACM --> stack_class ACMBotoStack
        resource_type_name = stack_class.__name__[:-len('BotoStack')]
        if set_resource_stack or resource.__class__.__name__ == resource_type_name:
            resource.stack = stack

        if not hasattr(resource, 'is_enabled'):
            enabled = True
        else:
            enabled = resource.is_enabled()
        self.paco_ctx.log_action_col(
            "Init",
            resource_type_name,
            account_ctx.name + '.' + aws_region,
            "stack: " + stack.get_name(),
            enabled=enabled
        )

        # Add Paco-Stack-Name tag
        if hasattr(stack, 'tags'):
            stack.tags.add_tag('Paco-Stack-Name', stack.get_name())
        # Log hooks
        stack.hooks.log_hooks()

        # add StackHooks set on the model
        if hasattr(resource, '_stack_hooks') and resource._stack_hooks != None and \
            hasattr(resource, 'stack') and resource.stack != None:
            for stack_hook in resource._stack_hooks:
                stack.add_hooks(stack_hook)

        return stack

