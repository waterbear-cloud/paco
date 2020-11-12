from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.stack import Parameter
from paco.utils import md5sum
from paco.cftemplates.iam_roles import policy_to_troposphere
import troposphere
import troposphere.iam


class IAMManagedPolicies(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        policy,
        template_params=None,
    ):
        self.policy = policy
        super().__init__(
            stack,
            paco_ctx,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
        )
        # existing Policy.policy_name's have been named in the format "<resource.name>-<policy.name>"
        # however, the policy.name is actually just 'policy' and the name used was a parent container that
        # contained the actual name for the policy.
        self.set_aws_name('Policy', self.resource_group_name, policy.policy_name)

        self.init_template('IAM: Managed Policy')
        if not stack.resource.is_enabled():
            return

        # Parameters
        if template_params:
            for param_dict in template_params:
                self.create_cfn_parameter(
                    param_type=param_dict['type'],
                    name=param_dict['key'],
                    description=param_dict['description'],
                    value=param_dict['value']
                )

        # Managed Policy Resource
        policy_name = self.gen_policy_name(policy.policy_name)
        policy_logical_id = self.create_cfn_logical_id(f'{policy.policy_name}ManagedPolicy')
        cfn_export_dict = {}
        cfn_export_dict['ManagedPolicyName'] = policy_name
        cfn_export_dict['Path'] = policy.path
        cfn_export_dict['PolicyDocument'] = policy_to_troposphere(policy)
        if policy.roles and len(policy.roles) > 0:
            cfn_export_dict['Roles'] = policy.roles
        if policy.users and len(policy.users) > 0:
            cfn_export_dict['Users'] = policy.users

        managed_policy_resource = troposphere.iam.ManagedPolicy.from_dict(
            policy_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(managed_policy_resource)

        # Output
        self.create_output(
            title=policy_logical_id,
            value=troposphere.Ref(managed_policy_resource),
            ref=f"{policy.paco_ref_parts}.arn"
        )

    def gen_policy_name(self, policy_name):
        "Generate a name valid in CloudFormation"
        policy_ref_hash = md5sum(str_data=self.policy.paco_ref_parts)[:8].upper()
        policy_name = self.create_resource_name_join(
            name_list=[policy_ref_hash, policy_name],
            separator='-',
            camel_case=False,
            filter_id='IAM.ManagedPolicy.ManagedPolicyName'
        )
        return policy_name
