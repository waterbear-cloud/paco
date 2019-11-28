import paco.cftemplates
import paco.models.iam
from paco.application.res_engine import ResourceEngine
from paco.core.exception import PacoUnsupportedFeature


class CodeDeployApplicationResourceEngine(ResourceEngine):

    def init_resource(self):

        # Create codedeploy Service Role
        # Important: This needs to be created in it's own CloudFormation template
        # If the service Role is created in the CodeDeploy template, CodeDeploy will try
        # to use the Role before it's been properly granted access and fail.
        role_name = "CodeDeployServiceRole"
        if self.resource.compute_platform == "Server":
            policy_arns = ['arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole']
        else:
            raise PacoUnsupportedFeature("Only a service role for 'Server' compute platform.")

        role_dict = {
            'enabled': self.resource.is_enabled(),
            'path': '/',
            'role_name': role_name,
            'managed_policy_arns': policy_arns,
            'assume_role_policy': {'effect': 'Allow', 'service': ['codedeploy.amazonaws.com']}
        }
        role = paco.models.iam.Role(role_name, self.resource)
        role.apply_config(role_dict)

        iam_role_ref = self.resource.paco_ref_parts + '.' + role_name
        iam_role_id = self.gen_iam_role_id(self.res_id, role_name)
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            paco_ctx=self.paco_ctx,
            account_ctx=self.account_ctx,
            region=self.aws_region,
            group_id=self.grp_id,
            role_id=iam_role_id,
            role_ref=iam_role_ref,
            role_config=role,
            stack_group=self.stack_group,
            template_params=None,
            stack_tags=self.stack_tags
        )

        # CodeDeploy Application
        paco.cftemplates.CodeDeployApplication(
            self.paco_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.resource,
            role
        )
