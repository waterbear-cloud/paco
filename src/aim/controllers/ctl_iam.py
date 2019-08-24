import click
import os
import time
import aim
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.stack_group import IAMStackGroup
from aim.cftemplates import IAMRoles, IAMManagedPolicies
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class PolicyContext():
    def __init__(self, aim_ctx, account_ctx, region, group_id, policy_id, policy_ref, policy_config_yaml, parent_config, stack_group, template_params, stack_tags):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.region = region

        self.group_id = group_id
        self.name = None
        self.arn = None
        self.policy_id = policy_id
        self.policy_ref = policy_ref
        self.policy_config_yaml = policy_config_yaml
        self.stack_group = stack_group
        self.stack_tags = stack_tags
        self.policy_template = None
        self.policy_stack = None
        self.template_params = template_params
        self.policy_context = {}

        self.policy_context = {}

        policy_config_dict = yaml.load(self.policy_config_yaml)
        self.policy_config = aim.models.iam.ManagedPolicy(policy_id, parent_config)
        aim.models.loader.apply_attributes_from_config(self.policy_config, policy_config_dict)

        self.init_policy()

    def init_policy(self):
        self.policy_config.resolve_ref_obj = self
        policy_context = {
            'id': self.policy_id,
            'config': self.policy_config,
            'ref': self.policy_ref,
            'template_params': self.template_params
        }

        policy_stack_tags = StackTags(self.stack_tags)
        policy_stack_tags.add_tag('AIM-IAM-Resource-Type', 'ManagedPolicy')
        template_name = '-'.join([self.group_id, self.policy_id])
        policy_context['template'] = IAMManagedPolicies(self.aim_ctx,
                                                        self.account_ctx,
                                                        self.region,
                                                        self.stack_group,
                                                        policy_stack_tags,
                                                        policy_context,
                                                        template_name)

        policy_context['stack'] = policy_context['template'].stack

        self.name = policy_context['template'].gen_policy_name(self.policy_id)
        self.arn = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.name)

        self.policy_context[self.policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])


class RoleContext():
    def __init__(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params, stack_tags):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.region = region

        self.group_id = group_id
        self.role_name = None
        self.role_id = role_id
        self.role_ref = role_ref
        self.role_config = role_config
        self.stack_group = stack_group
        self.stack_tags = stack_tags
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

        policy_stack_tags = StackTags(self.stack_tags)
        policy_stack_tags.add_tag('AIM-IAM-Resource-Type', 'ManagedPolicy')
        template_name = '-'.join([self.group_id, policy_id])
        policy_context['template'] = IAMManagedPolicies(self.aim_ctx,
                                                        self.account_ctx,
                                                        self.region,
                                                        self.stack_group,
                                                        policy_stack_tags,
                                                        policy_context,
                                                        template_name)

        policy_context['stack'] = policy_context['template'].stack

        self.policy_context['name'] = policy_context['template'].gen_policy_name(policy_id)
        self.policy_context['arn'] = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.policy_context['name'])

        self.policy_context[policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])

    def init_role(self):
        role_stack_tags = StackTags(self.stack_tags)
        role_stack_tags.add_tag('AIM-IAM-Resource-Type', 'Role')
        self.role_config.resolve_ref_obj = self
        template_name = '-'.join([self.group_id, self.role_id])
        self.role_template = IAMRoles(self.aim_ctx,
                                      self.account_ctx,
                                      self.region,
                                      self.stack_group,
                                      role_stack_tags,
                                      template_name,
                                      self.role_ref,
                                      self.role_id,
                                      self.role_config,
                                      self.template_params)

        self.role_stack = self.role_template.stack
        self.role_name = self.role_template.gen_iam_role_name("Role", self.role_id)
        self.role_arn = "arn:aws:iam::{0}:role/{1}".format(self.account_ctx.get_id(), self.role_name)
        role_profile_name = self.role_template.gen_iam_role_name("Profile", self.role_id)
        self.role_profile_arn = "arn:aws:iam::{0}:instance-profile/{1}".format(self.account_ctx.get_id(), role_profile_name)
        self.stack_group.add_stack_order(self.role_stack)

    def get_role_arn(self):
        return self.role_arn

    def resolve_ref(self, ref):
        if ref.ref.startswith(self.role_ref):
            if ref.resource_ref == 'profile.arn':
                return self.role_profile_arn
            elif ref.resource_ref == 'arn':
                return self.role_arn
            elif ref.resource_ref == 'name':
                return self.role_name
        else:
            for policy_ref in self.policy_context.keys():
                if ref.ref.startswith(policy_ref) == False:
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
        self.policy_context = {}
        self.iam_config = self.aim_ctx.project['iam']
        #self.aim_ctx.log("IAM Service: Configuration: %s" % (name))

    def init_users(self):
        for user_name in self.iam_config.users.keys():
            user_config = self.iam_config.users[user_name]
            # Create IAMUser
            #   - Access Key
            #   - Console Access: Enough to be able to login and set MFA
            #   - user_config.accounts: Create cross account access roles
            #   - Prompt for and set password
            #
            # Iterate through permissions
            #   - CodeCommit
            #     - Get repository account and create a policy and attach
            #       it to the user's account delegatge role
            #     - Manage SSH keys

    def init(self, controller_args):
        if controller_args == None:
            return
        if controller_args['arg_1'] == 'users':
            self.init_users()

    def create_managed_policy(self, aim_ctx, account_ctx, region, group_id, policy_id, policy_ref, policy_config_yaml, parent_config, stack_group, template_params, stack_tags):
        if policy_ref not in self.policy_context.keys():
            self.policy_context[policy_ref] = PolicyContext(aim_ctx=self.aim_ctx,
                                                            account_ctx=account_ctx,
                                                            region=region,
                                                            group_id=group_id,
                                                            policy_id=policy_id,
                                                            policy_ref=policy_ref,
                                                            policy_config_yaml=policy_config_yaml,
                                                            parent_config=parent_config,
                                                            stack_group=stack_group,
                                                            template_params=template_params,
                                                            stack_tags=stack_tags)
        else:
            print("Managed Policy already exists: %s" % (policy_ref))
            raise StackException(AimErrorCode.Unknown)

    def add_managed_policy(self, role_ref, *args, **kwargs):
        return self.role_context[role_ref].add_managed_policy(*args, **kwargs)

    def add_role(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params, stack_tags):
        if role_ref not in self.role_context.keys():
            self.role_context[role_ref] = RoleContext(aim_ctx=self.aim_ctx,
                                                      account_ctx=account_ctx,
                                                      region=region,
                                                      group_id=group_id,
                                                      role_id=role_id,
                                                      role_ref=role_ref,
                                                      role_config=role_config,
                                                      stack_group=stack_group,
                                                      template_params=template_params,
                                                      stack_tags=stack_tags)

        else:
            print("Role already exists: %s" % (role_ref))
            raise StackException(AimErrorCode.Unknown)

    def role_arn(self, role_ref):
        role_ref = role_ref.replace('aim.ref ', '')
        return self.role_context[role_ref].role_arn

    def role_profile_arn(self, role_ref):
        role_ref = role_ref.replace('aim.ref ', '')
        return self.role_context[role_ref].role_profile_arn

    def validate(self):
        pass

