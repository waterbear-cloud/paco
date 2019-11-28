import paco.cftemplates
import copy
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.cftemplates import IAMRoles, IAMManagedPolicies
from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup

class IAMStackGroup(StackGroup):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 aws_name,
                 iam_context_id,
                 roles_by_order,
                 policies_by_order,
                 config_ref_prefix,
                 controller):

        super().__init__(paco_ctx,
                         account_ctx,
                         'IAM',
                         'IAM',
                         controller)

        self.paco_ctx = paco_ctx
        self.stack_list = []
        self.aws_name = aws_name
        self.account_ctx = account_ctx
        self.config_ref_prefix = config_ref_prefix
        self.roles_by_order = roles_by_order
        self.policies_by_order = policies_by_order
        self.aws_region = aws_region
        self.roles_template = None
        self.roles_stack = None
        self.iam_context_id = iam_context_id

        # Set Reference resolution object
        for resource in self.roles_by_order:
            resource['config'].resolve_ref_obj = self
        for resource in self.policies_by_order:
            resource['config'].resolve_ref_obj = self


    def init(self):
        # Roles
        if len(self.roles_by_order) > 0:
            #iam_config_ref = '.'.join([self.config_ref_prefix, 'iam', self.iam_group_id, 'roles'])
            self.roles_template = IAMRoles(self.paco_ctx,
                                            self.account_ctx,
                                            self.aws_region,
                                            self,
                                            None, # stack_tags
                                            self.iam_context_id,
                                            self.roles_by_order)

            self.roles_stack = self.roles_templates.stack

            self.stack_list.append(self.roles_stack)

        # Managed Policies
        if len(self.policies_by_order) > 0:
            self.managed_policies_template = IAMManagedPolicies(self.paco_ctx,
                                                                self.account_ctx,
                                                                self.aws_region,
                                                                self,
                                                                None, # stack_tags
                                                                self.iam_context_id,
                                                                self.policies_by_order)

            self.managed_policies_stack = self.managed_policies_template.stack

            self.stack_list.append(self.managed_policies_stack)

    def role_arn(self, role_id):
        role_name = self.roles_template.gen_iam_role_name("Role", role_id)
        role_arn = "arn:aws:iam::{0}:role/{1}".format(self.account_ctx.get_id(), role_name)
        return role_arn

    def role_profile_arn(self, role_id):
        role_name = self.roles_template.gen_iam_role_name("Profile", role_id)
        profile_arn = "arn:aws:iam::{0}:instance-profile/{1}".format(self.account_ctx.get_id(), role_name)
        return profile_arn

    def move_stack_orders(self, new_stack_group):
        new_stack_group.add_stack_order(self.roles_stack)

    def validate(self):
        # Generate Stacks
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()

    def get_role_id_from_ref(self, ref, role_id):
        id_parts = []
        if 'applications' in ref.parts:
            grp_idx = ref.parts.index('groups')
            res_idx = ref.parts.index('resources')
            id_parts.append(ref.parts[grp_idx+1])
            id_parts.append(ref.parts[res_idx+1])

        id_parts.append(role_id)

        return '-'.join(id_parts)

    def resolve_ref(self, ref):
        if ref.resource_ref == 'profile.arn':
            role_id = self.get_role_id_from_ref(ref, ref.parts[-3])
            return self.role_profile_arn(role_id)
        elif ref.resource_ref == 'arn':
            role_id = self.get_role_id_from_ref(ref, ref.parts[-2])
            return self.role_arn(role_id)
        elif ref.resource_ref == 'name':
            role_id = self.get_role_id_from_ref(ref, ref.parts[-2])
            return self.roles_template.gen_iam_role_name("Role", role_id)
        return None

