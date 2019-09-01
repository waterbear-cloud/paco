"""
Initializes and configures the resources for applications by creating
CloudFormation templates, organizing the stacks into groups and configuring supporting resources.
"""

import aim.cftemplates
import os
from aim import models
from aim.application.ec2_launch_manager import EC2LaunchManager
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.core.yaml import YAML
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks, StackTags

yaml=YAML()
yaml.default_flow_sytle = False

class ApplicationEngine():
    """This class initializes and configures applications.
    Applications are logical groupings of AWS Resources designed
    to suport a single workload.

    """

    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        app_id,
        config,
        parent_config_ref,
        stack_group,
        ref_type,
        stack_tags=StackTags(),
        env_ctx=None
    ):
        self.aim_ctx = aim_ctx
        self.config = config
        self.app_id = app_id
        self.parent_config_ref = parent_config_ref
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.stack_group = stack_group
        self.ref_type = ref_type
        self.env_ctx = env_ctx
        self.iam_contexts = []
        self.cpbd_codepipebuild_template = None
        self.cpbd_codecommit_role_template = None
        self.cpbd_kms_template = None
        self.cpbd_codedeploy_template = None
        self.stack_tags = stack_tags
        self.stack_tags.add_tag( 'AIM-Application-Name', self.app_id )

    def get_aws_name(self):
        return self.stack_group.get_aws_name()

    def init(self):
        print("Init: Application: %s" % (self.app_id) )
        self.ec2_launch_manager = EC2LaunchManager(
            self.aim_ctx,
            self,
            self.app_id,
            self.account_ctx,
            self.aws_region,
            self.parent_config_ref,
            self.stack_group,
            self.stack_tags
        )

        # Resource Groups
        for grp_id, grp_config in self.config.groups_ordered():
            for res_id, res_config in grp_config.resources_ordered():
                res_stack_tags = StackTags(self.stack_tags)
                res_stack_tags.add_tag('AIM-Application-Group-Name', grp_id)
                res_stack_tags.add_tag('AIM-Application-Resource-Name', res_id)
                res_config.resolve_ref_obj = self
                init_method = getattr(self, "init_{}_resource".format(res_config.type.lower()), None)
                self.log_resource_init_status(res_config)
                if init_method == None:
                    reseng_class = getattr(aim.application, res_config.type+'ResourceEngine', None)(self)
                    reseng_class.init_resource(grp_id, res_id, res_config, StackTags(res_stack_tags))
                else:
                    init_method(grp_id, res_id, res_config, StackTags(res_stack_tags))

        print("Init: Application: %s: Completed" % (self.app_id))


    def gen_iam_role_id(self, res_id, role_id):
        return '-'.join([res_id, role_id])

    def log_resource_init_status(self, res_config):
        "Logs the init status of a resource"
        if res_config.is_enabled() == False:
            print("! Disabled: Init: Application: Resource: {}: {}".format(res_config.title_or_name, res_config.name))
        else:
            print("Init: Application: Resource: {}: {}".format(res_config.title_or_name, res_config.name))

    def init_alarms(self, aws_name, res_config, res_stack_tags):
        aim.cftemplates.CWAlarms(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,

            res_config.monitoring.alarm_sets,
            res_config.type,
            res_config.aim_ref_parts,
            res_config,
            aws_name
        )

    def init_apigatewayrestapi_resource(self, grp_id, res_id, res_config, res_stack_tags):
        aws_name = "-".join([grp_id, res_id])
        aim.cftemplates.ApiGatewayRestApi(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            aws_name,
            self.app_id,
            grp_id,
            res_config,
            res_config.aim_ref_parts
        )

    def init_rdsmysql_resource(self, grp_id, res_id, res_config, res_stack_tags):
        # RDS Mysql CloudFormation
        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.RDS(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            aws_name,
            self.app_id,
            grp_id,
            res_config,
            res_config.aim_ref_parts
        )

    def init_cloudfront_resource(self, grp_id, res_id, res_config, res_stack_tags):
        for factory_name, factory_config in res_config.factory.items():
            cloudfront_config_ref = res_config.aim_ref_parts + '.factory.' + factory_name
            res_config.domain_aliases = factory_config.domain_aliases
            res_config.viewer_certificate.certificate = factory_config.viewer_certificate.certificate

            # Create Certificate in us-east-1 because that is where CloudFront lives.
            acm_ctl = self.aim_ctx.get_controller('ACM')
            cert_group_id = cloudfront_config_ref+'.viewer_certificate'
            cert_group_id = cert_group_id.replace(self.aws_region, 'us-east-1')
            cert_config = self.aim_ctx.get_ref(res_config.viewer_certificate.certificate)
            acm_ctl.add_certificate_config(
                self.account_ctx,
                'us-east-1',
                cert_group_id,
                'viewer_certificate',
                cert_config
            )
            res_config.viewer_certificate.resolve_ref_obj = self
            factory_config.viewer_certificate.resolve_ref_obj = self
            # CloudFront CloudFormation
            aws_name = '-'.join([grp_id, res_id, factory_name])
            aim.cftemplates.CloudFront(
                self.aim_ctx,
                self.account_ctx,
                self.aws_region,
                self.stack_group,
                res_stack_tags,
                aws_name,
                self.app_id,
                grp_id,
                res_config,
                cloudfront_config_ref,
                [StackOrder.PROVISION, StackOrder.WAITLAST]
            )

    def init_snstopic_resource(self, grp_id, res_id, res_config, res_stack_tags):
        aws_name = '-'.join([grp_id, res_id])
        sns_topics_config = [res_config]
        # Strip the last part as SNSTopics loops thorugh a list and will
        # append the name to ref when it needs.
        res_config_ref = '.'.join(res_config.aim_ref_parts.split('.')[:-1])
        aim.cftemplates.SNSTopics(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            aws_name,
            sns_topics_config,
            res_config_ref
        )

    def init_lambda_resource(self, grp_id, res_id, res_config, res_stack_tags):
        # Create function execution role
        if res_config.iam_role.enabled == False:
            role_config_yaml = """
instance_profile: false
path: /
role_name: %s""" % ("LambdaFunction")
            role_config_dict = yaml.load(role_config_yaml)
            role_config = models.iam.Role()
            role_config.apply_config(role_config_dict)
        else:
            role_config = res_config.iam_role

        # Add CloudWatch Logs permissions
        cw_logs_policy = """
name: CloudWatchLogs
statement:
  - effect: Allow
    action:
      - logs:CreateLogGroup
      - logs:CreateLogStream
      - logs:PutLogEvents
    resource:
      - '*'
"""
        role_config.add_policy(yaml.load(cw_logs_policy))

        # The ID to give this role is: group.resource.iam_role
        iam_role_ref = res_config.aim_ref_parts + '.iam_role'
        iam_role_id = self.gen_iam_role_id(res_id, 'iam_role')
        # If no assume policy has been added, force one here since we know its
        # a Lambda function using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'aws': ["aim.sub 'arn:aws:iam::${aim.ref accounts.%s}:root'" % (self.account_ctx.get_name())],
                            'service': ['lambda.amazonaws.com'] }
            role_config.set_assume_role_policy(policy_dict)
        # Always turn off instance profiles for Lambda functions
        role_config.instance_profile = False
        role_config.enabled = res_config.is_enabled()
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_role(
            aim_ctx=self.aim_ctx,
            account_ctx=self.account_ctx,
            region=self.aws_region,
            group_id=grp_id,
            role_id=iam_role_id,
            role_ref=iam_role_ref,
            role_config=role_config,
            stack_group=self.stack_group,
            template_params=None,
            stack_tags=res_stack_tags
        )

        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.Lambda(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            aws_name,
            res_config,
            res_config.aim_ref_parts
        )
        # add alarms if there is monitoring configuration
        if getattr(res_config, 'monitoring', None) != None and \
            getattr(res_config.monitoring, 'alarm_sets', None) != None and \
                len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['Lambda', grp_id, res_id])
            self.init_alarms(aws_name, res_config, StackTags(res_stack_tags))

    def init_acm_resource(self, grp_id, res_id, res_config, res_stack_tags):

        acm_ctl = self.aim_ctx.get_controller('ACM')
        cert_group_id = res_config.aim_ref_parts
        acm_ctl.add_certificate_config(
            self.account_ctx,
            self.aws_region,
            cert_group_id,
            res_id,
            res_config
        )

    def init_s3bucket_resource(self, grp_id, res_id, res_config, res_stack_tags):
        # Generate s3 bucket name for application deployment
        bucket_name_prefix = '-'.join([self.get_aws_name(), grp_id])
        #print("Application depoloyment bucket name: %s" % new_name)
        s3_ctl = self.aim_ctx.get_controller('S3')
        # If an account was nto set, use the network default
        if res_config.account == None:
            res_config.account = self.aim_ctx.get_ref('aim.ref '+self.parent_config_ref+'.network.aws_account')
        account_ctx = self.aim_ctx.get_account_context(account_ref=res_config.account)
        s3_ctl.init_context(account_ctx, self.aws_region, res_config.aim_ref_parts, self.stack_group, res_stack_tags)
        s3_ctl.add_bucket(
            resource_ref=res_config.aim_ref_parts,
            region=self.aws_region,
            bucket_id=res_id,
            bucket_group_id=grp_id,
            bucket_name_prefix=bucket_name_prefix,
            bucket_name_suffix=None,
            bucket_config=res_config
        )

    def init_lbclassic_resource(self, grp_id, res_id, res_config, res_stack_tags):
        elb_config = res_config[res_id]
        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.ELB(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            self.env_ctx,
            self.app_id,
            res_id,
            aws_name,
            elb_config,
            res_config.aim_ref_parts
        )

    def init_lbapplication_resource(self, grp_id, res_id, res_config, res_stack_tags):

        # resolve_ref object for TargetGroups
        for target_group in res_config.target_groups.values():
            target_group.resolve_ref_obj = self
        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.ALB(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            self.env_ctx,
            aws_name,
            self.app_id,
            res_id,
            res_config,
            res_config.aim_ref_parts
        )
        # add alarms if there is monitoring configuration
        if hasattr(res_config, 'monitoring') and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ALB', grp_id, res_id])
            self.init_alarms(aws_name, res_config, StackTags(res_stack_tags))

    def init_asg_resource(self, grp_id, res_id, res_config, res_stack_tags):

        # Create instance role
        role_profile_arn = None
        if res_config.instance_iam_role.enabled == False:
            role_config_yaml = """
instance_profile: false
path: /
role_name: %s""" % ("ASGInstance")
            role_config_dict = yaml.load(role_config_yaml)
            role_config = models.iam.Role()
            role_config.apply_config(role_config_dict)

        else:
            role_config = res_config.instance_iam_role

        # The ID to give this role is: group.resource.instance_iam_role
        instance_iam_role_ref = res_config.aim_ref_parts + '.instance_iam_role'
        instance_iam_role_id = self.gen_iam_role_id(res_id, 'instance_iam_role')
        # If no assume policy has been added, force one here since we know its
        # an EC2 instance using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'service': ['ec2.amazonaws.com'] }
            role_config.set_assume_role_policy(policy_dict)
        # Always turn on instance profiles for ASG instances
        role_config.instance_profile = True
        role_config.enabled = res_config.is_enabled()
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_role(
            aim_ctx=self.aim_ctx,
            account_ctx=self.account_ctx,
            region=self.aws_region,
            group_id=grp_id,
            role_id=instance_iam_role_id,
            role_ref=instance_iam_role_ref,
            role_config=role_config,
            stack_group=self.stack_group,
            template_params=None,
            stack_tags=res_stack_tags
        )
        role_profile_arn = iam_ctl.role_profile_arn(instance_iam_role_ref)
        if res_config.monitoring != None and res_config.monitoring.enabled != False:
            self.ec2_launch_manager.lb_add_cloudwatch_agent(instance_iam_role_ref, res_config)
        # SSM Agent
        # if when_ssm_is_need():
        #    self.ec2_launch_manager.lb_add_ssm_agent(
        #        instance_iam_role_ref,
        #        self.app_id,
        #        grp_id,
        #        res_id,
        #        res_config
        #    )
        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.ASG(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,

            self.env_ctx,
            aws_name,
            self.app_id,
            grp_id,
            res_id,
            res_config,
            res_config.aim_ref_parts,
            role_profile_arn,
            self.ec2_launch_manager.user_data_script(self.app_id, grp_id, res_id),
            self.ec2_launch_manager.get_cache_id(self.app_id, grp_id, res_id)
        )

        if res_config.monitoring and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ASG', grp_id, res_id])
            self.init_alarms(aws_name, res_config, StackTags(res_stack_tags))

    def init_ec2_resource(self, grp_id, res_id, res_config, res_stack_tags):

        aws_name = '-'.join([grp_id, res_id])
        aim.cftemplates.EC2(
            self.aim_ctx,
            self.account_ctx,
            self.aws_region,
            self.stack_group,
            res_stack_tags,
            self.env_id,
            aws_name,
            self.app_id,
            res_id,
            res_config,
            res_config.aim_ref_parts
        )

    def get_stack_from_ref(self, ref):
        for stack in self.stack_group.stacks:
            #if ref.ref == 'netenv.aimdemo.dev.us-west-2.applications.app.groups.site.resources.webdemo.name':
            #    print("grp_application: get stack : " + ref.raw + " contains " + stack.template.config_ref)
            if stack.template.config_ref and stack.template.config_ref != '' and ref.raw.find(stack.template.config_ref) != -1:
                return stack
        return None

    def resolve_ref(self, ref):
        if isinstance(ref.resource, models.applications.SNSTopic):
            return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.TargetGroup):
            return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.ASG):
            if ref.resource_ref.startswith('instance_id'):
                asg_stack = self.get_stack_from_ref(ref)
                asg_outputs_key = asg_stack.template.get_outputs_key_from_ref(ref)
                if asg_outputs_key == None:
                    raise StackException(
                        AimErrorCode.Unknown,
                        message="Unable to find outputkey for ref: %s" % ref.raw)
                asg_name = asg_stack.get_outputs_value(asg_outputs_key)
                asg_client = self.account_ctx.get_aws_client('autoscaling')
                asg_response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                instance_id = asg_response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
                ssm_client = self.account_ctx.get_aws_client('ssm')
                ssm_client.start_session(Target=instance_id)
            else:
                return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.Lambda):
            lambda_stack = self.get_stack_from_ref(ref)
            return lambda_stack
        elif isinstance(ref.resource, models.applications.CloudFrontViewerCertificate):
            acm_ctl = self.aim_ctx.get_controller('ACM')
            # Force the region to us-east-1 because CloudFront lives there
            ref.sub_part(ref.region, 'us-east-1')
            ref.region = 'us-east-1'
            return acm_ctl.resolve_ref(ref)
        elif isinstance(ref.resource, models.applications.LBApplication):
            return self.get_stack_from_ref(ref)

        return None
