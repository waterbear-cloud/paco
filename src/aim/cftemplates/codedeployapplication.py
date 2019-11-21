import troposphere
import troposphere.codedeploy
from aim.cftemplates.cftemplates import CFTemplate
from aim.models.references import get_model_obj_from_ref
from aim.core.exception import AimUnsupportedFeature
from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action
from awacs.sts import AssumeRole
import awacs.autoscaling
import awacs.ec2
import awacs.tag
import awacs.sns
import awacs.cloudwatch
import awacs.elasticloadbalancing


class CodeDeployApplication(CFTemplate):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        cdapp,
        role
    ):
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            enabled=cdapp.is_enabled(),
            config_ref=cdapp.aim_ref_parts,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.env_ctx = env_ctx
        self.set_aws_name('CodeDeployApplication', grp_id, cdapp.name)
        self.init_template('CodeDeploy Application')
        self.res_name_prefix = self.create_resource_name_join(
            name_list=[self.env_ctx.get_aws_name(), app_id, grp_id, cdapp.name],
            separator='-',
            camel_case=True
        )

        # Service Role ARN parameter
        service_role_arn_param = self.create_cfn_parameter(
            param_type='String',
            name='ServiceRoleArn',
            description='The codedeploy service Role to assume.',
            value=role.get_arn(),
            use_troposphere=True,
            troposphere_template=self.template,
        )

        # CodeDeploy Application
        cdapp_resource = troposphere.codedeploy.Application(
            'CodeDeployApplication',
            ComputePlatform=cdapp.compute_platform
        )
        self.template.add_resource(cdapp_resource)

        # DeploymentGroup resources
        for deploy_group in cdapp.deployment_groups.values():
            if not deploy_group.is_enabled(): continue

            # Deployment configuration
            deploy_group_logical_id = self.create_cfn_logical_id('DeploymentGroup' + deploy_group.name)
            deployment_dict = {
                'Description': deploy_group.title_or_name,
            }
            if deploy_group.ignore_application_stop_failures:
                deployment_dict['IgnoreApplicationStopFailures'] = deploy_group.ignore_application_stop_failures
            if deploy_group.revision_location_s3:
                s3bucket = get_model_obj_from_ref(deploy_group.revision_location_s3.bucket, self.aim_ctx.project)
                deployment_dict['Revision'] = {
                    'S3Location': {
                        'Bucket': s3bucket.get_aws_name(),
                        'Key': deploy_group.revision_location_s3.key,
                    },
                    'RevisionType': 'S3'
                }
                if deploy_group.revision_location_s3.bundle_type:
                    deployment_dict['Revision']['S3Location']['BundleType'] = deploy_group.revision_location_s3.bundle_type

            cfn_export_dict = {
                'Deployment': deployment_dict,
                'ApplicationName': troposphere.Ref(cdapp_resource),
                'ServiceRoleArn': troposphere.Ref(service_role_arn_param),
            }
            if deploy_group.autoscalinggroups:
                cfn_export_dict['AutoScalingGroups'] = []
                for asg_ref in deploy_group.autoscalinggroups:
                    asg = get_model_obj_from_ref(asg_ref, self.aim_ctx.project)
                    cfn_export_dict['AutoScalingGroups'].append(asg.get_aws_name())

            deploy_group_resource = troposphere.codedeploy.DeploymentGroup.from_dict(
                deploy_group_logical_id,
                cfn_export_dict
            )
            self.template.add_resource(deploy_group_resource)
            deploy_group_resource.DependsOn = []
            deploy_group_resource.DependsOn.append(cdapp_resource.title)

            # User-defined Policies
            for policy in deploy_group.role_policies:
                policy_name = self.create_resource_name_join(
                    name_list=[self.res_name_prefix, 'CodeDeploy', deploy_group.name, policy.name],
                    separator='-',
                    filter_id='IAM.Policy.PolicyName',
                    hash_long_names=True,
                    camel_case=True
                )
                statement_list = []
                for statement in policy.statement:
                    action_list = []
                    for action in statement.action:
                        action_parts = action.split(':')
                        action_list.append(Action(action_parts[0], action_parts[1]))
                    statement_list.append(
                        Statement(
                            Effect=statement.effect,
                            Action=action_list,
                            Resource=statement.resource
                        )
                    )
                policy_resource = troposphere.iam.PolicyType(
                    title=self.create_cfn_logical_id('CodeDeployPolicy' + policy.name, camel_case=True),
                    PolicyName=policy_name,
                    PolicyDocument=PolicyDocument(
                        Statement=statement_list,
                    ),
                    Roles=[troposphere.Ref(service_role_resource)]
                )
                self.template.add_resource(policy_resource)
                deploy_group_resource.DependsOn = policy_resource

        # All done, let's go home!
        self.set_template(self.template.to_yaml())
