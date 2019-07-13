import click
import os
import time
import aim
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.stack_group import IAMStackGroup
from aim.cftemplates import IAMRoles, IAMManagedPolicies
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class RoleContext():
    def __init__(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.region = region

        self.group_id = group_id
        self.role_id = role_id
        self.role_ref = role_ref
        self.role_config = role_config
        self.stack_group = stack_group
        self.role_template = None
        self.role_stack = None
        self.template_params = template_params

        self.policy_context = {}

        self.init_role()

    def aws_name(self):
        return self.role_ref

    def get_aws_name(self):
        return self.aws_name()

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
                           parent_config,
                           group_id,
                           policy_id,
                           policy_ref,
                           policy_config_yaml=None,
                           template_params=None):

        if policy_ref in self.policy_context.keys():
            print("Managed policy already exists: %s" % (policy_ref) )
            raise StackException(AimErrorCode.Unknown)

        policy_config_dict = yaml.load(policy_config_yaml)
        policy_config_dict['roles'] = [self.role_name]
        policy_config = aim.models.iam.ManagedPolicy(policy_id, parent_config)
        aim.models.loader.apply_attributes_from_config(policy_config, policy_config_dict)
        policy_config.resolve_ref_obj = self
        policy_context = {
            'id': policy_id,
            'config': policy_config,
            'ref': policy_ref,
            'template_params': template_params
        }

        template_name = '-'.join([self.group_id, policy_id])
        policy_context['template'] = IAMManagedPolicies(self.aim_ctx,
                                                        self.account_ctx,
                                                        policy_context,
                                                        template_name)

        policy_context['stack'] = Stack(aim_ctx=self.aim_ctx,
                                        account_ctx=self.account_ctx,
                                        grp_ctx=self.stack_group,
                                        stack_config=self.policy_context,
                                        template=policy_context['template'],
                                        aws_region=self.region)

        self.policy_context['name'] = policy_context['template'].gen_policy_name(policy_id)
        self.policy_context['arn'] = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.policy_context['name'])

        self.policy_context[policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])

    def init_role(self):

        self.role_config.resolve_ref_obj = self
        template_name = '-'.join([self.group_id, self.role_id])
        self.role_template = IAMRoles(self.aim_ctx,
                                      self.account_ctx,
                                      template_name,
                                      self.role_ref,
                                      self.role_id,
                                      self.role_config,
                                      self.template_params)

        self.role_stack = Stack(aim_ctx=self.aim_ctx,
                                account_ctx=self.account_ctx,
                                grp_ctx=self.stack_group,
                                stack_config=self.role_config,
                                template=self.role_template,
                                aws_region=self.region)

        self.role_name = self.role_template.gen_iam_role_name("Role", self.role_id)
        self.role_arn = "arn:aws:iam::{0}:role/{1}".format(self.account_ctx.get_id(), self.role_name)
        role_profile_name = self.role_template.gen_iam_role_name("Profile", self.role_id)
        self.role_profile_arn = "arn:aws:iam::{0}:instance-profile/{1}".format(self.account_ctx.get_id(), role_profile_name)
        self.stack_group.add_stack_order(self.role_stack)


    def resolve_ref(self, ref):
        if ref.raw.startswith(self.role_ref):
            if ref.resource_ref == 'profile.arn':
                return self.role_profile_arn
            elif ref.resource_ref == 'arn':
                return self.role_arn
            elif ref.resource_ref == 'name':
                return self.role_name
        else:
            for policy_ref in self.policy_context.keys():
                if ref.raw.startswith(policy_ref) == False:
                    continue
                if ref.resource_ref == 'arn':
                    return self.policy_context[policy_ref]['arn']
                elif ref.resource_ref == 'name':
                    return self.policy_context[policy_ref]['name']
        return None


class IAMController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "IAM")

        self.role_context = {}
        #self.aim_ctx.log("IAM Service: Configuration: %s" % (name))

    def init(self, init_config):
        pass

    def add_managed_policy(self, role_ref, *args, **kwargs):
        return self.role_context[role_ref].add_managed_policy(*args, **kwargs)

    def add_role(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params):
        if role_ref not in self.role_context.keys():
            self.role_context[role_ref] = RoleContext(aim_ctx=self.aim_ctx,
                                                      account_ctx=account_ctx,
                                                      region=region,
                                                      group_id=group_id,
                                                      role_id=role_id,
                                                      role_ref=role_ref,
                                                      role_config=role_config,
                                                      stack_group=stack_group,
                                                      template_params=template_params)

        else:
            print("Role already exists: %s" % (role_ref))
            raise StackException(AimErrorCode.Unknown)

    def role_arn(self, role_ref):
        return self.role_context[role_ref].role_arn

    def role_profile_arn(self, role_ref):
        return self.role_context[role_ref].role_profile_arn


    def get_value_from_ref(self, aim_ref):

        raise StackException(AimErrorCode.Unknown)
