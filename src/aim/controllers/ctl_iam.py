import click
import os
import time
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.stack_group import IAMStackGroup
import aim.models


class IAMContext():
    def __init__(self, aim_ctx, account_ctx, aws_region, controller, context_id, config_ref_prefix):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.controller = controller
        self.context_id = context_id
        self.managed_policies = {}
        self.roles = {}
        self.roles_by_order = []
        self.policies_by_order = []
        self.config_ref_prefix = config_ref_prefix
        self.stack_group = None

    def aws_name(self):
        return self.context_id

    def get_aws_name(self):
        return self.aws_name()

    def update_stack_group(self):
        self.stack_group = IAMStackGroup(self.aim_ctx,
                                        self.account_ctx,
                                        self.aws_region,
                                        "IAM",
                                        self.context_id,
                                        self.roles_by_order,
                                        self.policies_by_order,
                                        self.config_ref_prefix,
                                        self)
        self.stack_group.init()

    def get_role(self, role_id=None, role_ref=None):
        role_by_id = None
        role_by_ref = None
        if role_id !=  None:
            for role in self.roles:
                if role.id == role_id:
                    role_by_id = role
                    break
        if role_ref != None:
            role_by_ref = role[role_ref]

        if role_by_id != None and role_by_ref != None:
            if role_by_id.id == role_by_ref.id:
                return role_by_id
            else:
                # You specified both role_id and role_ref
                # but they each returned different results.
                raise StackException(AimErrorCode)
        elif role_by_id != None:
            return role_by_id

        return role_by_ref

    def add_managed_policy(self,
                           resolve_ref_obj,
                           parent_config,
                           policy_id,
                           policy_config_dict,
                           policy_ref,
                           template_params=None):

        policy_config = aim.models.iam.ManagedPolicy(policy_id, parent_config)
        aim.models.loader.apply_attributes_from_config(policy_config, policy_config_dict)
        policy_config.resolve_ref_obj = resolve_ref_obj
        managed_policy = {
            'id': policy_id,
            'config': policy_config,
            'ref': policy_ref,
            'template_params': template_params
        }
        self.policies_by_order.append(managed_policy)
        self.update_stack_group()


    def add_role(self, resolve_ref_obj, role_id, role_ref, role_config, template_params=None):
        if role_ref in self.roles.keys():
            # Role ID already exists
            raise StackException(AimErrorCode.Unknown)

        role = {
            'id': role_id,
            'config': role_config,
            'ref': role_ref,
            'template_params': template_params
        }
        self.roles[role_ref] = role
        self.roles_by_order.append(role)
        role_config.resolve_ref_obj = resolve_ref_obj
        self.update_stack_group()

    def role_arn(self, role_id):
        return self.stack_group.role_arn(role_id)

    def role_profile_arn(self, role_id):
        return self.stack_group.role_profile_arn(role_id)

    def move_stack_orders(self, new_stack_group):
        self.stack_group.move_stack_orders(new_stack_group)

    def validate(self):
        self.stack_group.validate()

    def provision(self):
        self.stack_group.provision()

    def delete(self):
        self.stack_group.delete()


class IAMController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "IAM")

        self.contexts = {}
        self.contexts_by_order = []
        #self.aim_ctx.log("IAM Service: Configuration: %s" % (name))

    def init(self, init_config):
        pass

    def init_context(self, account_ctx, aws_region, context_id, config_ref_prefix):
        if context_id not in self.contexts.keys():
            self.contexts[context_id] = IAMContext(self.aim_ctx,
                                                   account_ctx,
                                                   aws_region,
                                                   self,
                                                   context_id,
                                                   config_ref_prefix)
            self.contexts_by_order.append(self.contexts[context_id])

    def add_managed_policy(self, context_id, *args, **kwargs):
        return self.contexts[context_id].add_managed_policy(*args, **kwargs)

    def add_role(self, context_id, *args, **kwargs):
        return self.contexts[context_id].add_role(*args, **kwargs)

    def role_arn(self, context_id, *args, **kwargs):
        return self.contexts[context_id].role_arn(*args, **kwargs)

    def role_profile_arn(self, context_id, *args, **kwargs):
        return self.contexts[context_id].role_profile_arn(*args, **kwargs)

    def move_stack_orders(self, context_id, *args, **kwargs):
        return self.contexts[context_id].move_stack_orders(*args, **kwargs)

    def validate(self, context_id):
        return self.contexts[context_id].validate()

    def provision(self, context_id):
        return self.contexts[context_id].provision()

    def delete(self, context_id):
        return self.contexts[context_id].delete()

    def get_config(self, config_id):
        for config in self.config_list:
            if config.name == config_id:
                return config
        return None

    def get_value_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.parse_ref(aim_ref)
        ref_parts = ref_dict['ref_parts']
        config_ref = ref_dict['ref']

        raise StackException(AimErrorCode.Unknown)
