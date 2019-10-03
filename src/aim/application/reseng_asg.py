import aim.cftemplates
from aim.application.res_engine import ResourceEngine
from aim.core.yaml import YAML
from aim import models

yaml=YAML()
yaml.default_flow_sytle = False

class ASGResourceEngine(ResourceEngine):

    def init_resource(self):
        # Create instance role
        role_profile_arn = None
        if self.resource.instance_iam_role.enabled == False:
            role_config_yaml = """
instance_profile: false
path: /
role_name: %s""" % ("ASGInstance")
            role_config_dict = yaml.load(role_config_yaml)
            role_config = models.iam.Role()
            role_config.apply_config(role_config_dict)
        else:
            role_config = self.resource.instance_iam_role

        # The ID to give this role is: group.resource.instance_iam_role
        instance_iam_role_ref = self.resource.aim_ref_parts + '.instance_iam_role'
        instance_iam_role_id = self.gen_iam_role_id(self.res_id, 'instance_iam_role')
        # If no assume policy has been added, force one here since we know its
        # an EC2 instance using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'service': ['ec2.amazonaws.com'] }
            role_config.set_assume_role_policy(policy_dict)
        # Always turn on instance profiles for ASG instances
        role_config.instance_profile = True
        role_config.enabled = self.resource.is_enabled()
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_role(
            aim_ctx=self.aim_ctx,
            account_ctx=self.account_ctx,
            region=self.aws_region,
            group_id=self.grp_id,
            role_id=instance_iam_role_id,
            role_ref=instance_iam_role_ref,
            role_config=role_config,
            stack_group=self.stack_group,
            template_params=None,
            stack_tags=self.stack_tags
        )
        role_profile_arn = iam_ctl.role_profile_arn(instance_iam_role_ref)

        # Monitoring
        if self.resource.monitoring != None and self.resource.monitoring.enabled != False:
            self.app_engine.ec2_launch_manager.lb_add_cloudwatch_agent(instance_iam_role_ref, self.resource)
        if len(self.resource.efs_mounts) > 0:
            self.app_engine.ec2_launch_manager.lb_add_efs_mounts(instance_iam_role_ref, self.resource)
        # SSM Agent
        # if when_ssm_is_need():
        #    self.app_engine.ec2_launch_manager.lb_add_ssm_agent(
        #        instance_iam_role_ref,
        #        self.app_id,
        #        self.grp_id,
        #        self.res_id,
        #        self.resource
        #    )
        # Add EIP AllocationId Tag
        aim.cftemplates.ASG(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            self.stack_tags,
            self.env_ctx,
            self.app_id,
            self.grp_id,
            self.res_id,
            self.resource,
            self.resource.aim_ref_parts,
            role_profile_arn,
            self.app_engine.ec2_launch_manager.user_data_script(
                self.app_id,
                self.grp_id,
                self.res_id,
                self.resource,
                instance_iam_role_ref
            ),
            self.app_engine.ec2_launch_manager.get_cache_id(self.app_id, self.grp_id, self.res_id)
        )
