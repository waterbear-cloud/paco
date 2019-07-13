import os
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
import aim.cftemplates
from aim.application.ec2_launch_manager import EC2LaunchManager
from aim import models

from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class ApplicationEngine():

    def __init__(self, aim_ctx, account_ctx, aws_region, app_id, config, config_ref_prefix, stack_group, ref_type, subenv_ctx=None):
        self.aim_ctx = aim_ctx
        self.config = config
        self.app_id = app_id
        self.config_ref_prefix = config_ref_prefix
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.stack_group = stack_group
        self.ref_type = ref_type

        self.subenv_ctx = subenv_ctx
        self.iam_contexts = []

        self.cpbd_codepipebuild_stack = None
        self.cpbd_codecommit_role_template = None
        self.cpbd_kms_stack = None
        self.cpbd_codedeploy_stack = None
        #self.controller = None
        #self.controller_type = controller_type
        #self.aws_name = controller_type
        #self.init_done = False
        #if controller_name:
        #    self.aws_name = self.aws_name + '-' + controller_name

    def gen_ref(self,
                grp_id=None,
                res_id=None,
                segment_id=None,
                attribute=None,
                seperator='.'):
        #netenv_ref = 'netenv.ref {0}.subenv.{1}.{2}'.format(self.netenv_id, self.subenv_id, self.region)
        ref_str = '{0} {1}.applications.{2}'.format(self.ref_type, self.config_ref_prefix, self.app_id)
        if grp_id != None:
            ref_str = seperator.join([ref_str, 'groups', grp_id])
        if res_id != None:
            ref_str = seperator.join([ref_str, 'resources', res_id])
        if segment_id != None:
            ref_str = seperator.join([ref_str, 'network', 'vpc', 'segments', segment_id])
        if attribute != None:
            ref_str = seperator.join([ref_str, attribute])
        return ref_str

    def get_aws_name(self):
        return self.stack_group.get_aws_name()

    def init(self):
        print("ApplicationEngine: Init: %s" % (self.app_id) )
        self.ec2_launch_manager = EC2LaunchManager(self.aim_ctx,
                                                    self,
                                                    self.app_id,
                                                    self.account_ctx,
                                                    self.aws_region,
                                                    self.config_ref_prefix,
                                                    self.stack_group)
        # Resource Groups
        for grp_id, grp_config in self.config.groups_ordered():
            for res_id, res_config in grp_config.resources_ordered():
                res_config.resolve_ref_obj = self
                if res_config.type == 'ACM':
                    self.init_acm_resource(grp_id, res_id, res_config)
                elif res_config.type == 'S3Bucket':
                    self.init_s3bucket_resource(grp_id, res_id, res_config)
                elif res_config.type == 'LBClassic':
                    self.init_lbclassic_resource(grp_id, res_id, res_config)
                elif res_config.type == 'LBApplication':
                    self.init_lbapplication_resource(grp_id, res_id, res_config)
                elif res_config.type == 'ASG':
                    self.init_asg_resource(grp_id, res_id, res_config)
                elif res_config.type == 'EC2':
                    self.init_ec2_resource(grp_id, res_id, res_config)
                elif res_config.type == 'CodePipeBuildDeploy':
                    self.init_cpbd_resource(grp_id, res_id, res_config)
                elif res_config.type == 'Lambda':
                    self.init_lambda_resource(grp_id, res_id, res_config)
        print("ApplicationEngine: Init: %s: Completed" % (self.app_id))

    def gen_resource_ref(self, grp_id, res_id, attribute=None):
        ref ='.'.join([self.config_ref_prefix, "applications", self.app_id, "groups", grp_id, "resources", res_id])
        if attribute != None:
            ref = '.'.join([ref, attribute])
        return ref

    def gen_iam_context_id(self, aws_region, iam_id=None):
        iam_context_id = '-'.join([self.get_aws_name(), vocabulary.aws_regions[aws_region]['short_name']])
        if iam_id != None:
            iam_context_id += '-' + iam_id
        if iam_context_id not in self.iam_contexts:
            self.iam_contexts.append(iam_context_id)
        return iam_context_id


    def gen_iam_role_id(self, res_id, role_id):
        return '-'.join([res_id, role_id])

    def init_alarms(self, aws_name, res_config_ref, res_config):
        alarms_template = aim.cftemplates.CWAlarms(self.aim_ctx,
                                                   self.account_ctx,
                                                   res_config.monitoring.alarm_sets,
                                                   res_config.type,
                                                   res_config_ref,
                                                   aws_name)
        alarms_stack = Stack(self.aim_ctx,
                            self.account_ctx,
                            self.stack_group,
                            res_config,
                            alarms_template,
                            aws_region=self.aws_region)
        self.stack_group.add_stack_order(alarms_stack)

    def init_lambda_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: Lambda: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: Lambda: %s" % (res_id))

        lambda_config_ref = self.gen_resource_ref(grp_id, res_id)
        # Create instance role
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

        # The ID to give this role is: group.resource.iam_role
        iam_role_ref = self.gen_ref(grp_id=grp_id,
                                             res_id=res_id,
                                             attribute='iam_role')
        iam_role_id = self.gen_iam_role_id(res_id, 'iam_role')
        # If no assume policy has been added, force one here since we know its
        # a Lambda function using it.
        # Set defaults if assume role policy was not explicitly configured
        if not hasattr(role_config, 'assume_role_policy') or role_config.assume_role_policy == None:
            policy_dict = { 'effect': 'Allow',
                            'aws': ["aim.sub 'arn:aws:iam::${config.ref accounts.%s}:root'" % (self.account_ctx.get_name())],
                            'service': ['lambda.amazonaws.com'] }

            role_config.set_assume_role_policy(policy_dict)
        # Always turn off instance profiles for Lambda functions
        role_config.instance_profile = False
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_role(   aim_ctx=self.aim_ctx,
                            account_ctx=self.account_ctx,
                            region=self.aws_region,
                            group_id=grp_id,
                            role_id=iam_role_id,
                            role_ref=iam_role_ref,
                            role_config=role_config,
                            stack_group=self.stack_group,
                            template_params=None)

        aws_name = '-'.join([grp_id, res_id])
        asg_template = aim.cftemplates.Lambda(self.aim_ctx,
                                            self.account_ctx,
                                            aws_name,
                                            res_config,
                                            lambda_config_ref)
        asg_stack = Stack(self.aim_ctx,
                            self.account_ctx,
                            self.stack_group,
                            res_config,
                            asg_template,
                            aws_region=self.aws_region)
        self.stack_group.add_stack_order(asg_stack)

    def init_acm_resource(self, grp_id, res_id, res_config):
        # print(cert_config)
        if res_config.enabled == False:
            print("ApplicationEngine: Init: ACM: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: ACM: %s" % (res_id))
            # print("Adding cert?????")
            acm_ctl = self.aim_ctx.get_controller('ACM')
            self.gen_resource_ref(grp_id, res_id)
            cert_group_id = self.gen_resource_ref(grp_id, res_id)
            acm_ctl.add_certificate_config(self.account_ctx,
                                            cert_group_id,
                                            res_id,
                                            res_config)

    def init_s3bucket_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: S3: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: S3: %s" % (res_id))
            s3_config_ref = "netenv.ref "+self.gen_resource_ref(grp_id, res_id)
            # Generate s3 bucket name for application deployment
            bucket_name_prefix = '-'.join([self.get_aws_name(), grp_id])
            #print("Application depoloyment bucket name: %s" % new_name)
            s3_ctl = self.aim_ctx.get_controller('S3')
            account_ctx = self.aim_ctx.get_account_context(account_ref=res_config.account)
            s3_ctl.init_context(account_ctx, self.aws_region, s3_config_ref, self.stack_group)
            s3_ctl.add_bucket(  resource_ref=s3_config_ref,
                                region=self.aws_region,
                                bucket_id=res_id,
                                bucket_group_id=grp_id,
                                bucket_name_prefix=bucket_name_prefix,
                                bucket_name_suffix=None,
                                bucket_config=res_config)

    def init_lbclassic_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: LBClassic: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: LBClassic: %s" % (res_id))
            elb_config = res_config[res_id]
            elb_config_ref = self.gen_resource_ref(grp_id, res_id)
            aws_name = '-'.join([grp_id, res_id])
            elb_template = aim.cftemplates.ELB(self.aim_ctx,
                                                self.account_ctx,
                                                self.subenv_ctx,
                                                self.app_id,
                                                res_id,
                                                aws_name,
                                                elb_config,
                                                elb_config_ref)

            elb_stack = Stack(self.aim_ctx, self.account_ctx, self.stack_group,
                                res_config[res_id],
                                elb_template,
                                aws_region=self.aws_region)

            self.stack_group.add_stack_order(elb_stack)


    def init_lbapplication_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: LBApplication: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: LBApplication: %s" % (res_id))
        alb_config_ref = self.gen_resource_ref(grp_id, res_id)
        # resolve_ref object for TargetGroups
        for target_group in res_config.target_groups.values():
            target_group.resolve_ref_obj = self
        aws_name = '-'.join([grp_id, res_id])
        alb_template = aim.cftemplates.ALB(self.aim_ctx,
                                            self.account_ctx,
                                            self.subenv_ctx,
                                            aws_name,
                                            self.app_id,
                                            res_id,
                                            res_config,
                                            alb_config_ref)

        alb_stack = Stack(  self.aim_ctx,
                            self.account_ctx,
                            self.stack_group,
                            res_config,
                            alb_template,
                            aws_region=self.aws_region)

        self.stack_group.add_stack_order(alb_stack)

        if hasattr(res_config, 'monitoring') and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ALB', grp_id, res_id])
            self.init_alarms(aws_name, alb_config_ref, res_config)

    def init_asg_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: ASG: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: ASG: " + res_id)
        asg_config_ref = self.gen_resource_ref(grp_id, res_id)
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
        instance_iam_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                        grp_id=grp_id,
                                                        res_id=res_id,
                                                        attribute='instance_iam_role')
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
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_role(   aim_ctx=self.aim_ctx,
                            account_ctx=self.account_ctx,
                            region=self.aws_region,
                            group_id=grp_id,
                            role_id=instance_iam_role_id,
                            role_ref=instance_iam_role_ref,
                            role_config=role_config,
                            stack_group=self.stack_group,
                            template_params=None)

        role_profile_arn = iam_ctl.role_profile_arn(instance_iam_role_ref)

        if res_config.monitoring != None:
            self.ec2_launch_manager.lb_add_cloudwatch_agent(instance_iam_role_ref,
                                                            res_config.monitoring,
                                                            self.app_id,
                                                            grp_id,
                                                            res_id,
                                                            res_config)
        if res_id == 'webapptest':
            self.ec2_launch_manager.lb_add_ssm_agent(instance_iam_role_ref,
                                                     self.app_id,
                                                     grp_id,
                                                     res_id,
                                                     res_config)
        aws_name = '-'.join([grp_id, res_id])
        asg_template = aim.cftemplates.ASG(self.aim_ctx,
                                            self.account_ctx,
                                            self.subenv_ctx,
                                            aws_name,
                                            self.app_id,
                                            res_id,
                                            res_config,
                                            asg_config_ref,
                                            role_profile_arn,
                                            self.ec2_launch_manager.user_data_script(self.app_id, grp_id, res_id),
                                            self.ec2_launch_manager.get_cache_id(self.app_id, grp_id, res_id))
        asg_stack = Stack(self.aim_ctx,
                            self.account_ctx,
                            self.stack_group,
                            res_config,
                            asg_template,
                            aws_region=self.aws_region)
        self.stack_group.add_stack_order(asg_stack)

        if res_config.monitoring and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ASG', grp_id, res_id])
            self.init_alarms(aws_name, asg_config_ref, res_config)

    def init_ec2_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: EC2: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: EC2 Instance")
            #print("TODO: Refactor with new design.")
            #raise StackException(AimErrorCode.Unknown)
            ec2_config_ref = self.gen_resource_ref(grp_id, res_id)
            aws_name = '-'.join([grp_id, res_id])
            ec2_template = aim.cftemplates.EC2(self.aim_ctx,
                                                self.account_ctx,
                                                self.subenv_id,
                                                aws_name,
                                                self.app_id,
                                                res_id,
                                                res_config,
                                                ec2_config_ref)
            ec2_stack = Stack(self.aim_ctx,
                                self.account_ctx,
                                self.stack_group,
                                resources_config[res_id],
                                ec2_template,
                                aws_region=self.aws_region)

            self.stack_group.add_stack_order(ec2_stack)

    def init_cpbd_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationEngine: Init: CodePipeBuildDeploy: %s *disabled*" % (res_id))
        else:
            print("ApplicationEngine: Init: CodePipeBuildDeploy: %s" % (res_id))
            tools_account_ctx = self.aim_ctx.get_account_context(res_config.tools_account)
            # XXX: Fix Hardcoded!!!
            data_account_ctx = self.aim_ctx.get_account_context("config.ref accounts.data")

            # -----------------
            # S3 Artifacts Bucket:
            s3_ctl = self.aim_ctx.get_controller('S3')

            s3_artifacts_bucket_ref = res_config.artifacts_bucket
            s3_artifacts_bucket_arn = s3_ctl.get_bucket_arn(s3_artifacts_bucket_ref)
            s3_artifacts_bucket_name = s3_ctl.get_bucket_name(s3_artifacts_bucket_ref)

            # S3 Artifacts Bucket:  POST
            codebuild_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                         grp_id=grp_id,
                                                         res_id=res_id,
                                                         attribute='codebuild_role.arn')
            codepipeline_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                            grp_id=grp_id,
                                                            res_id=res_id,
                                                            attribute='codepipeline_role.arn')
            codedeploy_tools_delegate_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                                         grp_id=grp_id,
                                                                         res_id=res_id,
                                                                         attribute='codedeploy_tools_delegate_role.arn')
            codecommit_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                          grp_id=grp_id,
                                                          res_id=res_id,
                                                          attribute='codecommit_role.arn')

            # ----------------
            # KMS Key
            #
            aws_account_ref = self.subenv_ctx.gen_ref(attribute='network.aws_account')
            kms_config_dict = {
                'admin_principal': {
                    'aws': [ "!Sub 'arn:aws:iam::${{AWS::AccountId}}:root'" ]
                },
                'crypto_principal': {
                    'aws': [
                        # Sub-Environment account
                        "aim.sub 'arn:aws:iam::${%s}:root'" % (self.aim_ctx.get_ref(aws_account_ref)),
                        # CodeCommit Account
                        "aim.sub 'arn:aws:iam::${config.ref accounts.data}:root'",
                        # Tools Account
                    ]
                }
            }
            kms_conf_ref = '.'.join(["applications", self.app_id, "groups", grp_id, "resources", res_id, "kms"])
            aws_name = '-'.join([grp_id, res_id])
            kms_template = aim.cftemplates.KMS(self.aim_ctx,
                                                tools_account_ctx,
                                                aws_name,
                                                kms_conf_ref,
                                                kms_config_dict)

            kms_stack_pre = Stack(self.aim_ctx,
                                    tools_account_ctx,
                                    self.stack_group,
                                    None,
                                    kms_template,
                                    aws_region=self.aws_region)

            self.cpbd_kms_stack = kms_stack_pre

            self.stack_group.add_stack_order(kms_stack_pre)


            # -------------------------------------------
            # CodeCommit Delegate Role
            role_yaml = """
assume_role_policy:
  effect: Allow
  aws:
    - '{0[tools_account_id]:s}'
instance_profile: false
path: /
role_name: CodeCommit
policies:
  - name: CPBD
    statement:
      - effect: Allow
        action:
          - codecommit:BatchGetRepositories
          - codecommit:Get*
          - codecommit:GitPull
          - codecommit:List*
          - codecommit:CancelUploadArchive
          - codecommit:UploadArchive
        resource:
          - {0[codecommit_ref]:s}
      - effect: Allow
        action:
          - 's3:*'
        resource:
          - {0[artifact_bucket_arn]:s}
          - {0[artifact_bucket_arn]:s}/*
      - effect: Allow
        action:
          - 'kms:*'
        resource:
          - "!Ref CMKArn"
"""
            kms_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                              grp_id=grp_id,
                                              res_id=res_id,
                                              attribute='kms')

            #codecommit_ref = self.subenv_ctx.app_deployment_codecommit_repository(self.app_id,
            #                                                                        res_id)
            codecommit_ref = res_config.codecommit_repository
            role_table = {
                'codecommit_account_id': "aim.sub '${{{0}.account_id}}'".format(codecommit_ref),
                'tools_account_id': tools_account_ctx.get_id(),
                'codecommit_ref': "aim.sub '${{{0}.arn}}'".format(codecommit_ref),
                'artifact_bucket_arn': s3_artifacts_bucket_arn,
                'kms_ref': kms_ref
            }
            role_config_dict = yaml.load(role_yaml.format(role_table))
            codecommit_iam_role_config = models.iam.Role()
            codecommit_iam_role_config.apply_config(role_config_dict)

            iam_ctl = self.aim_ctx.get_controller('IAM')
            # The ID to give this role is: group.resource.instance_iam_role
            codecommit_iam_role_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                              grp_id=grp_id,
                                                              res_id=res_id,
                                                              attribute='codecommit_role')
            codecommit_iam_role_id = self.gen_iam_role_id(res_id, 'codecommit_role')
            # IAM Roles Parameters
            iam_role_params = [
                {
                    'key': 'CMKArn',
                    'value': kms_ref,
                    'type': 'String',
                    'description': 'CPBD KMS Key Arn'
                }
            ]
            iam_ctl.add_role(aim_ctx=self.aim_ctx,
                             account_ctx=data_account_ctx,
                             region=self.aws_region,
                             group_id=grp_id,
                             role_id=codecommit_iam_role_id,
                             role_ref=codecommit_iam_role_ref,
                             role_config=codecommit_iam_role_config,
                             stack_group=self.stack_group,
                             template_params=iam_role_params)



            # ----------------------------------------------------------
            # Code Deploy
            codedeploy_conf_ref = '.'.join(["applications", self.app_id, "groups", grp_id, "resources", res_id, "deploy"])
            aws_name = '-'.join([grp_id, res_id])
            codedeploy_template = aim.cftemplates.CodeDeploy(self.aim_ctx,
                                                             self.account_ctx,
                                                             self.subenv_ctx,
                                                             aws_name,
                                                             self.app_id,
                                                             grp_id,
                                                             res_id,
                                                             res_config,
                                                             s3_artifacts_bucket_name,
                                                             codedeploy_conf_ref)

            codedeploy_stack = Stack(self.aim_ctx,
                                        self.account_ctx,
                                        self.stack_group,
                                        None,
                                        codedeploy_template,
                                        aws_region=self.aws_region)

            self.cpbd_codedeploy_stack = codedeploy_stack
            self.stack_group.add_stack_order(codedeploy_stack)

            # PipeBuild
            codepipebuild_conf_ref = '.'.join(["applications", self.app_id, "resources", res_id, "pipebuild"])
            aws_name = '-'.join([grp_id, res_id])
            codepipebuild_template = aim.cftemplates.CodePipeBuild(self.aim_ctx,
                                                                    tools_account_ctx,
                                                                    self.subenv_ctx,
                                                                    aws_name,
                                                                    self.app_id,
                                                                    grp_id,
                                                                    res_id,
                                                                    res_config,
                                                                    s3_artifacts_bucket_name,
                                                                    codedeploy_template.get_tools_delegate_role_arn(),
                                                                    codepipebuild_conf_ref)

            self.cpbd_codepipebuild_stack = Stack(self.aim_ctx,
                                                tools_account_ctx,
                                                self.stack_group,
                                                None,
                                                codepipebuild_template,
                                                aws_region=self.aws_region)
            self.stack_group.add_stack_order(self.cpbd_codepipebuild_stack)



            # Add CodeBuild Role ARN to KMS Key principal now that the role is created
            codebuild_arn_ref = self.subenv_ctx.gen_ref(app_id=self.app_id,
                                                        grp_id=grp_id,
                                                        res_id=res_id,
                                                        attribute="codebuild_role.arn")
            kms_config_dict['crypto_principal']['aws'].append("aim.sub '${{{0}}}'".format(codebuild_arn_ref))
            kms_conf_ref = '.'.join(["applications", self.app_id, "resources", res_id, "kms"])
            aws_name = '-'.join([grp_id, res_id])
            kms_template = aim.cftemplates.KMS(self.aim_ctx,
                                                tools_account_ctx,
                                                aws_name,
                                                kms_conf_ref,
                                                kms_config_dict)
            # Addinga  file id allows us to generate a second template without overwritting
            # the first one. This is needed as we need to update the KMS policy with the
            # Codebuild Arn after the Codebuild has been created.
            kms_template.set_template_file_id("codebuild")
            kms_stack_post = Stack(self.aim_ctx,
                                tools_account_ctx,
                                self.stack_group,
                                None,
                                kms_template,
                                aws_region=self.aws_region)

            self.stack_group.add_stack_order(kms_stack_post)

            # Get the ASG Instance Role ARN
            if res_config.asg_name[-5:] != '.name':
                print("Invalid ASG Name reference: %s" % (res_config.asg_name))
                raise StackException(AimErrorCode.Unknown)

            asg_instance_role_ref = res_config.asg_name[:-5]+'.instance_iam_role.arn'
            cpbd_s3_bucket_policy = {
                'aws': [
                    "aim.sub '${{{0}}}'".format(codebuild_role_ref),
                    "aim.sub '${{{0}}}'".format(codepipeline_role_ref),
                    "aim.sub '${{{0}}}'".format(codedeploy_tools_delegate_role_ref),
                    "aim.sub '${{{0}}}'".format(codecommit_role_ref),
                    "aim.sub '${{{0}}}'".format(asg_instance_role_ref)
                ],
                'action': [ 's3:*' ],
                'effect': 'Allow',
                'resource_suffix': [ '/*', '' ]
            }
            s3_ctl.add_bucket_policy(s3_artifacts_bucket_ref, cpbd_s3_bucket_policy)


    def get_stack_from_ref(self, ref):
        for stack in self.stack_group.stacks:
            #print("grp_application: get stack : " + ref.raw + " contains " + stack.template.config_ref)
            if stack.template.config_ref and stack.template.config_ref != '' and ref.raw.find(stack.template.config_ref) != -1:
                return stack
        return None


    def OLD_get_value_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.aim_ref.parse_ref(aim_ref)
        ref_parts = ref_dict['ref_parts']
        config_ref = ref_dict['ref']

        raise StackException(AimErrorCode.Unknown)

    def resolve_ref(self, ref):
        if isinstance(ref.resource, models.applications.CodePipeBuildDeploy):
            if ref.resource_ref == 'codecommit_role.arn':
                iam_ctl = self.aim_ctx.get_controller("IAM")
                return iam_ctl.role_arn(ref.raw[:-4])
            elif ref.resource_ref == 'codecommit.arn':
                codecommit_ref = ref.resource.codecommit_repository
                return self.aim_ctx.get_ref(codecommit_ref+".arn")
            elif ref.resource_ref == 'codebuild_role.arn':
                # self.cpbd_codepipebuild_stack will fail if there are two deployments
                # this application... corner case, but might happen?
                return self.cpbd_codepipebuild_stack.template.get_codebuild_role_arn()
            elif ref.resource_ref == 'codepipeline_role.arn':
                return self.cpbd_codepipebuild_stack.template.get_codepipeline_role_arn()
            elif ref.resource_ref == 'codedeploy_tools_delegate_role.arn':
                return self.cpbd_codedeploy_stack.template.get_tools_delegate_role_arn()
            elif ref.resource_ref == 'kms':
                return self.cpbd_kms_stack
            elif ref.resource_ref == 'codedeploy_application_name':
                return self.cpbd_codedeploy_stack.template.get_application_name()
            elif ref.resource_ref == 'deploy.deployment_group_name':
                return self.cpbd_codedeploy_stack
        elif isinstance(ref.resource, models.applications.TargetGroup):
            return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.ASG):
            if ref.resource_ref.startswith('instance_id'):
                asg_stack = self.get_stack_from_ref(ref)
                asg_outputs_key = asg_stack.template.get_outputs_key_from_ref(ref)
                asg_name = asg_stack.get_outputs_value(asg_outputs_key)
                asg_client = self.account_ctx.get_aws_client('autoscaling')
                asg_response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                instance_id = asg_response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
                ssm_client = self.account_ctx.get_aws_client('ssm')
                response = ssm_client.start_session(Target=instance_id)
                breakpoint()
            else:
                return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.applications.Lambda):
            pass
        breakpoint()
        return None