import aim.cftemplates
import os
import pathlib
import tarfile
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.models import loader, vocabulary
from aim import models
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class LaunchBundle():
    def __init__(self,
                 aim_ctx,
                 name,
                 manager,
                 app_id,
                 group_id,
                 resource_id,
                 bucket_id):
        self.aim_ctx = aim_ctx
        self.name = name
        self.app_id = app_id
        self.group_id = group_id
        self.resource_id = resource_id
        self.manager = manager
        self.bucket_id = bucket_id
        self.manager_path = os.path.join(self.aim_ctx.build_folder,
                                         'EC2LaunchManager',
                                         self.manager.subenv_ctx.netenv_id,
                                         self.manager.account_ctx.get_name(),
                                         self.manager.subenv_ctx.region,
                                         self.app_id,
                                         self.group_id,
                                         self.resource_id)
        self.s3_bucket_ref = None
        self.bundle_files = []
        self.package_path = None
        self.cache_id = ""
        self.s3_key = None

    def set_launch_script(self, launch_script):
        self.add_file("launch.sh", launch_script)

    def add_file(self, name, contents):
        file_config = {
            'name': name,
            'contents': contents
        }
        self.bundle_files.append(file_config)

    def build(self):
        orig_cwd = os.getcwd()
        bundles_path = os.path.join(self.manager_path, 'LaunchBundles')
        pathlib.Path(bundles_path).mkdir(parents=True, exist_ok=True)
        os.chdir(bundles_path)

        # mkdir Bundle/
        bundle_folder = self.name
        pathlib.Path(bundle_folder).mkdir(parents=True, exist_ok=True)

        # Launch script
        contents_md5 = ""
        for bundle_file in self.bundle_files:
            file_path = os.path.join(bundle_folder, bundle_file['name'])
            with open(file_path, "w") as output_fd:
                output_fd.write(bundle_file['contents'])
            contents_md5 += self.aim_ctx.md5sum(str_data=bundle_file['contents'])

        self.cache_id = self.aim_ctx.md5sum(str_data=contents_md5)

        lb_tar_filename = str.join('.', [bundle_folder, 'tgz'])
        lb_tar = tarfile.open(lb_tar_filename, "w:gz")
        lb_tar.add(bundle_folder, recursive=True)
        lb_tar.close()
        os.chdir(orig_cwd)
        self.package_filename = lb_tar_filename
        self.package_path = os.path.join(bundles_path, lb_tar_filename)

        # EC2 Manager Bucket Reference
        self.s3_bucket_ref = '.'.join([self.manager.config_ref, 'groups', self.group_id,
                               'resources', self.resource_id, self.manager.id, 'bucket'])

        instance_iam_role_arn_ref = self.manager.subenv_ctx.gen_ref(app_id=self.app_id,
                                                            grp_id=self.group_id,
                                                            res_id=self.resource_id,
                                                            attribute='instance_iam_role.arn')
        self.instance_iam_role_arn = self.aim_ctx.get_ref(instance_iam_role_arn_ref)


    def get_cache_id(self):
        return self.cache_id

class EC2LaunchManager():
    def __init__(self,
                 aim_ctx,
                 parent,
                 app_id,
                 account_ctx,
                 subenv_ctx):
        self.aim_ctx = aim_ctx
        self.parent = parent
        self.account_ctx = account_ctx
        self.subenv_ctx = subenv_ctx
        self.subenv_id = self.subenv_ctx.subenv_id
        self.cloudwatch_agent = False
        self.cloudwatch_agent_config = None
        self.app_id = app_id
        self.id = 'ec2lm'
        self.config_ref = str.join('.',[self.subenv_ctx.netenv_id,
                                        self.subenv_id,
                                        'applications',
                                         self.app_id])
        self.launch_bundles = {}
        # cache_id['.'.join[app_id, grp_id, res_id]
        self.cache_id = {}

    def get_cache_id(self, app_id, grp_id, res_id):
        cache_context = '.'.join([app_id, grp_id, res_id])
        if cache_context not in self.cache_id:
            return ''
        return self.cache_id[cache_context]

    def bucket_id(self, resource_id):
        return '-'.join([resource_id, self.id])

    def stack_hook(self, hook, bundle):
        # Upload bundle to the S3 bucket
        s3_ctl = self.aim_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(bundle.s3_bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        bundle_s3_key = os.path.join("LaunchBundles", bundle.package_filename)
        s3_client.upload_file(bundle.package_path, bucket_name, bundle_s3_key)

    def stack_hook_cache_id(self, hook, bundle):
        return bundle.get_cache_id()

    def add_bundle_to_s3_bucket(self, bundle):
        cache_context = '.'.join([bundle.app_id, bundle.group_id, bundle.resource_id])
        if cache_context not in self.cache_id:
            self.cache_id[cache_context] = ''
        self.cache_id[cache_context] += bundle.cache_id

        stack_hooks = StackHooks(self.aim_ctx)
        stack_hooks.add(name='EC2LaunchManager',
                        stack_action='create',
                        stack_timing='post',
                        hook_method=self.stack_hook,
                        cache_method=self.stack_hook_cache_id,
                        hook_arg=bundle)
        stack_hooks.add('EC2LaunchManager', 'update', 'post',
                        self.stack_hook, self.stack_hook_cache_id, bundle)

        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.add_stack_hooks( resource_ref=bundle.s3_bucket_ref,
                                stack_hooks=stack_hooks )

    def init_bundle_s3_bucket(self, bundle):
        bucket_config_dict = {
            'bucket_name': 'lb',
            'deletion_policy': 'delete',
            'policy': [ {
                'aws': [ "%s" % (bundle.instance_iam_role_arn) ],
                'effect': 'Allow',
                'action': [
                    's3:Get*',
                    's3:List*'
                ],
                'resource_suffix': [
                    '/*',
                    ''
                ]
            } ]
        }
        bucket_config = models.resources.S3Bucket(bundle.resource_id, None)
        bucket_config.update(bucket_config_dict)
        bucket_config.resolve_ref_obj = self
        bucket_name_prefix = '-'.join([self.parent.get_aws_name(), bundle.group_id])
        bucket_name_suffix = self.id
        bucket_region = self.subenv_ctx.region

        s3_ctl = self.aim_ctx.get_controller('S3')
        #bucket_group_name = '-'.join([self.subenv_ctx.netenv_id, self.subenv_id, bundle.app_id, bundle.group_id, bundle.resource_id, self.id])
        s3_ctl.init_context(self.account_ctx,
                            self.subenv_ctx.region,
                            bundle.s3_bucket_ref,
                            self.parent)

        s3_ctl.add_bucket(  bundle.s3_bucket_ref,
                            region=bucket_region,
                            bucket_id=bundle.bucket_id,
                            bucket_group_id=bundle.group_id,
                            bucket_name_prefix=bucket_name_prefix,
                            bucket_name_suffix=bucket_name_suffix,
                            bucket_config=bucket_config,
                            stack_hooks=None)


    def get_s3_bucket_name(self, app_id, grp_id, bucket_id):
        for bundle_key in self.launch_bundles.keys():
            bundle = self.launch_bundles[bundle_key][0]
            if bundle.app_id == app_id and bundle.group_id == grp_id and bundle.bucket_id == bucket_id:
                s3_ctl = self.aim_ctx.get_controller('S3')
                return s3_ctl.get_bucket_name(bundle.s3_bucket_ref)
        return None

    def user_data_script(self, app_id, grp_id, resource_id):
        script = """#!/bin/bash

# EC2 Launch Manager: %s
""" % (self.get_cache_id(app_id, grp_id, resource_id))
        s3_bucket = self.get_s3_bucket_name(app_id, grp_id, self.bucket_id(resource_id))
        if s3_bucket != None:
            script += """
# Update System
yum update -y
# Launch Bundles
EC2_MANAGER_FOLDER='/opt/aim/EC2Manager/'
mkdir -p ${EC2_MANAGER_FOLDER}
aws s3 sync s3://%s/ ${EC2_MANAGER_FOLDER}

cd ${EC2_MANAGER_FOLDER}/LaunchBundles/

echo "Loading Launch Bundles"
for BUNDLE_PACKAGE in "$(ls *.tgz)"
do
    BUNDLE_FOLDER=${BUNDLE_PACKAGE//'.tgz'/}
    echo "${BUNDLE_FOLDER}: Unpacking:"
    tar xvfz ${BUNDLE_PACKAGE}
    chown -R root.root ${BUNDLE_FOLDER}
    echo "${BUNDLE_FOLDER}: Launching bundle"
    cd ${BUNDLE_FOLDER}
    chmod u+x ./launch.sh
    ./launch.sh
    cd ..
    echo "${BUNDLE_FOLDER}: Done"
done
            """ % (s3_bucket)
        else:
            script += """
# Launch Bundles
echo "No Launch bundles to load"
            """

        return script

    def add_bundle(self, bundle):
        bundle.build()
        if bundle.s3_bucket_ref not in self.launch_bundles:
            self.init_bundle_s3_bucket(bundle)
            self.launch_bundles[bundle.s3_bucket_ref] = []
            # Initializes the CloudFormation for this S3 Context ID
        # Add the bundle to the S3 Context ID bucket
        self.add_bundle_to_s3_bucket(bundle)
        self.launch_bundles[bundle.s3_bucket_ref].append(bundle)

    def lb_add_cloudwatch_agent(self,
                                instance_iam_role_ref,
                                monitoring_config,
                                app_id,
                                group_id,
                                resource_id,
                                res_config):

        if monitoring_config == None or monitoring_config.enabled == False:
            return

        # Create the CloudWatch agent launch scripts and configuration
        cw_agent_object = {
            "Amazon": { "path": "/amazon_linux/amd64/latest",
                         "object": "amazon-cloudwatch-agent.rpm"},
            "Centos":  { "path": "/centos/amd64/latest",
                         "object": "amazon-cloudwatch-agent.rpm" },
            "SUSE":    { "path": "/suse/amd64/latest",
			             "object": "amazon-cloudwatch-agent.rpm" },
            "Debian":  { "path": "/debian/amd64/latest",
			             "object": "amazon-cloudwatch-agent.deb" },
            "Ubuntu":  { "path": "/ubuntu/amd64/latest",
			             "object": "amazon-cloudwatch-agent.deb" },
            "Windows": { "path": "/windows/amd64/latest",
			             "object": "amazon-cloudwatch-agent.msi" },
            "Redhat":  { "path": "/redhat/arm64/latest",
			             "object": "amazon-cloudwatch-agent.rpm" },
            }
        cw_install_command = {
            "Amazon": "rpm -U" ,
            "Centos":  "rpm -U",
            "SUSE":    "rpm -U",
            "Debian":  "dpkg -i -E",
            "Ubuntu":  "dpkg -i -E",
            "Windows": "msiexec /i",
            "Redhat":  "rpm -U"
            }
        # Launch script
        launch_script_template = """#!/bin/bash

# Download the agent
LB_DIR=$(pwd)
mkdir /tmp/aim/
cd /tmp/aim/
wget https://s3.amazonaws.com/amazoncloudwatch-agent{0[agent_path]:s}/{0[agent_object]:s}
wget https://s3.amazonaws.com/amazoncloudwatch-agent{0[agent_path]:s}/{0[agent_object]:s}.sig

# Verify the agent
TRUSTED_FINGERPRINT=$(echo "9376 16F3 450B 7D80 6CBD 9725 D581 6730 3B78 9C72" | tr -d ' ')
wget https://s3.amazonaws.com/amazoncloudwatch-agent/assets/amazon-cloudwatch-agent.gpg
gpg --import amazon-cloudwatch-agent.gpg

KEY_ID="$(gpg --list-packets amazon-cloudwatch-agent.gpg 2>&1 | awk '/keyid:/{{ print $2 }}' | tr -d ' ')"
FINGERPRINT="$(gpg --fingerprint ${{KEY_ID}} 2>&1 | grep 'Key fingerprint =' | awk -F'= ' '{{print $2}}' | tr -d ' ')"
OBJECT_FINGERPRINT="$(gpg --verify {0[agent_object]:s}.sig {0[agent_object]:s} 2>&1| grep 'Primary key fingerprint: ' | awk -F 't: ' '{{print $2}}' | tr -d ' ')"
if [ "${{FINGERPRINT}}" != "${{TRUSTED_FINGERPRINT}}" -o "${{OBJECT_FINGERPRINT}}" != "${{TRUSTED_FINGERPRINT}}" ] ; then
    # Log error here
    echo "ERROR: CloudWatch Agent signature invalid: ${{KEY_ID}}: ${{FINGERPRINT}}"
    exit 1
fi

# Install the agent
{0[install_command]:s} {0[agent_object]}

cd ${{LB_DIR}}
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:amazon-cloudwatch-agent.json -s
"""
        launch_script_table = {
            'agent_path': cw_agent_object['Amazon']['path'],
            'agent_object': cw_agent_object['Amazon']['object'],
            'install_command': cw_install_command['Amazon']
        }

        launch_script = launch_script_template.format(launch_script_table)

        # Agent Configuration file
        # /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
        agent_config_template = """
{{
"agent": {{
    "metrics_collection_interval": {0[collection_interval]:d},
    "region": "{0[aws_region]:s}",
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
}},

"metrics": {{
    "metrics_collected": {{
{0[metrics_json]:s}
    }},
    "append_dimensions": {{
        "ImageId": "${{aws:ImageId}}",
        "InstanceId": "${{aws:InstanceId}}",
        "InstanceType": "${{aws:InstanceType}}",
        "AutoScalingGroupName": "${{aws:AutoScalingGroupName}}"
        }},
        "aggregation_dimensions" : [["AutoScalingGroupName"], ["InstanceId", "InstanceType"],[]]
    }}
}}
"""
        agent_config_table ={
            'collection_interval': 60,
            'aws_region': self.subenv_ctx.region,
            'metrics_json': ""
        }

        metrics_json_template = """
        "{0[name]:s}": {{
            "measurement": {0[measurement_array_json]:s},
            "collection_interval": {0[collection_interval]:d}
        }}"""

        metrics_json_table = {
            'name': None,
            'measurement_array_json': "[]",
            'collection_interval': None
        }

        # Metrics config
        metrics_json = ""
        for metric_config in monitoring_config.metrics:
            metrics_json_table['name'] = metric_config.name
            if metric_config.collection_interval:
                metrics_json_table['collection_interval'] = metric_config.collection_interval
            else:
                metrics_json_table['collection_interval'] = monitoring_config.collection_interval
            metrics_json_table['measurement_array_json'] = "["
            for measurement in metric_config.measurements:
                if measurement != metric_config.measurements[0]:
                    metrics_json_table['measurement_array_json'] += ', '
                metrics_json_table['measurement_array_json'] += '"{0}"'.format(measurement)
            metrics_json_table['measurement_array_json'] += "]"
            if metric_config != monitoring_config.metrics[0]:
                metrics_json += ', '
            metrics_json += metrics_json_template.format(metrics_json_table)

        # Agent Config
        if monitoring_config.collection_interval:
            agent_config_table['collection_interval'] = monitoring_config.collection_interval
        agent_config_table['metrics_json'] = metrics_json

        agent_config = agent_config_template.format(agent_config_table)

        # Create instance managed policy for the agent
        policy_config_yaml = """
name: 'CloudWatchAgent'
statement:
  - effect: Allow
    action:
      - cloudwatch:PutMetricData
      - ec2:DescribeTags
      - "autoscaling:Describe*"
      - "cloudwatch:*"
      - "logs:*"
      - "sns:*"
      - "iam:GetPolicy"
      - "iam:GetPolicyVersion"
      - "iam:GetRole"
      - "ec2:DescribeTags"
    resource:
      - '*'
"""


        policy_ref = self.parent.gen_resource_ref(grp_id=group_id,
                                                  res_id=resource_id,
                                                  attribute=self.id+".cloudwatchagent.policy")
        policy_id = '-'.join([resource_id, 'cloudwatchagent'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy( role_ref=instance_iam_role_ref,
                                    parent_config=res_config,
                                    group_id=group_id,
                                    policy_id=policy_id,
                                    policy_ref=policy_ref,
                                    policy_config_yaml=policy_config_yaml )

        # Create the Launch Bundle and configure it
        cw_lb = LaunchBundle(self.aim_ctx, "CloudWatchAgent", self, app_id, group_id, resource_id, self.bucket_id(resource_id))
        cw_lb.set_launch_script(launch_script)
        cw_lb.add_file('amazon-cloudwatch-agent.json', agent_config)

        # Save Configuration
        self.add_bundle(cw_lb)

    def lb_add_ssm_agent(self,
                        instance_iam_role_ref,
                        app_id,
                        group_id,
                        resource_id,
                        res_config):

        # Create the SSM agent launch scripts and configuration
        # Only Amazon Linux is supported
        # Launch script
        launch_script = """#!/bin/bash
# Install the agent
yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
"""

        # Create instance managed policy for the agent
        policy_config_yaml = """
name: 'SSMAgent'
statement:
  - effect: Allow
    action:
      - ssmmessages:CreateControlChannel
      - ssmmessages:CreateDataChannel
      - ssmmessages:OpenControlChannel
      - ssmmessages:OpenDataChannel
      - ec2messages:AcknowledgeMessage
      - ec2messages:DeleteMessage
      - ec2messages:FailMessage
      - ec2messages:GetEndpoint
      - ec2messages:GetMessages
      - ec2messages:SendReply
      - ssm:UpdateInstanceInformation
      - ssm:ListInstanceAssociations
    resource:
      - '*'
  - effect: Allow
    action:
      - s3:GetEncryptionConfiguration
    resource:
      - '*'
"""
        policy_ref = self.parent.gen_resource_ref(grp_id=group_id,
                                                  res_id=resource_id,
                                                  attribute=self.id+".ssmagent.policy")
        policy_id = '-'.join([resource_id, 'ssmagent-policy'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy( role_ref=instance_iam_role_ref,
                                    parent_config=res_config,
                                    group_id=group_id,
                                    policy_id=policy_id,
                                    policy_ref=policy_ref,
                                    policy_config_yaml=policy_config_yaml )

        # Create the Launch Bundle and configure it
        ssm_lb = LaunchBundle(self.aim_ctx, "SSMAgent", self, app_id, group_id, resource_id, self.bucket_id(resource_id))
        ssm_lb.set_launch_script(launch_script)

        # Save Configuration
        self.add_bundle(ssm_lb)

    def validate(self):
        pass

    def provision(self):
        pass

    def delete(self):
        pass


class ApplicationStackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 subenv_ctx,
                 app_id):
        aws_name = '-'.join(['App', app_id])
        super().__init__(aim_ctx,
                         account_ctx,
                         app_id,
                         aws_name,
                         subenv_ctx)

        self.subenv_ctx = subenv_ctx
        self.app_id = app_id
        #self.netenv_config = netenv_ctx.config
        self.config_ref_prefix = self.subenv_ctx.config_ref_prefix
        self.aws_region = self.subenv_ctx.region
        self.subenv_id = self.subenv_ctx.subenv_id
        self.cpbd_codepipebuild_stack = None
        self.cpbd_codecommit_role_template = None
        self.cpbd_kms_stack = None
        self.cpbd_codedeploy_stack = None
        self.ec2_launch_manager = EC2LaunchManager(self.aim_ctx,
                                                   self,
                                                   self.app_id,
                                                   self.account_ctx,
                                                   self.subenv_ctx)
        self.iam_contexts = []
        self.iam_context_id = self.gen_iam_context_id(self.aws_region)
        self.cpbd_iam_context_id = self.gen_iam_context_id(self.aws_region, iam_id='cpbd')

        # Initialize config with a deepcopy of the project defaults
        #self.config = ApplicationStackGroupConfig(aim_ctx, self, self.netenv_config, self.app_id, self.subenv_id)
        self.stack_list = []

    def gen_iam_role_id(self, res_id, role_id):
        return '-'.join([res_id, role_id])

    def gen_iam_context_id(self, aws_region, iam_id=None):
        iam_context_id = '-'.join([self.get_aws_name(), vocabulary.aws_regions[aws_region]['short_name']])
        if iam_id != None:
            iam_context_id += '-' + iam_id
        if iam_context_id not in self.iam_contexts:
            self.iam_contexts.append(iam_context_id)
        return iam_context_id

    def gen_resource_ref(self, grp_id, res_id, attribute=None):
        ref ='.'.join([self.config_ref_prefix, "applications", self.app_id, "groups", grp_id, "resources", res_id])
        if attribute != None:
            ref = '.'.join([ref, attribute])
        return ref

    def init_alarms(self, aws_name, res_config_ref, res_config):
        alarms_template = aim.cftemplates.CWAlarms(self.aim_ctx,
                                                   self.account_ctx,
                                                   res_config.monitoring.alarm_sets,
                                                   res_config.type,
                                                   res_config_ref,
                                                   aws_name)
        alarms_stack = Stack(self.aim_ctx,
                            self.account_ctx,
                            self,
                            res_config,
                            alarms_template,
                            aws_region=self.aws_region)
        self.stack_list.append(alarms_stack)
        self.add_stack_order(alarms_stack)

    def init_acm_resource(self, grp_id, res_id, res_config):
        # print(cert_config)
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: ACM: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: ACM: %s" % (res_id))
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
            print("ApplicationStackGroup: Init: S3: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: S3: %s" % (res_id))
            s3_config_ref = "netenv.ref "+self.gen_resource_ref(grp_id, res_id)
            # Generate s3 bucket name for application deployment
            bucket_name_prefix = '-'.join([self.get_aws_name(), grp_id])
            #print("Application depoloyment bucket name: %s" % new_name)
            s3_ctl = self.aim_ctx.get_controller('S3')
            account_ctx = self.aim_ctx.get_account_context(account_ref=res_config.account)
            s3_ctl.init_context(account_ctx, self.aws_region, s3_config_ref, self)
            s3_ctl.add_bucket(  resource_ref=s3_config_ref,
                                region=self.aws_region,
                                bucket_id=res_id,
                                bucket_group_id=grp_id,
                                bucket_name_prefix=bucket_name_prefix,
                                bucket_name_suffix=None,
                                bucket_config=res_config)

    def init_lbclassic_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: LBClassic: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: LBClassic: %s" % (res_id))
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

            elb_stack = Stack(self.aim_ctx, self.account_ctx, self,
                                res_config[res_id],
                                elb_template,
                                aws_region=self.aws_region)

            self.stack_list.append(elb_stack)
            self.add_stack_order(elb_stack)


    def init_lbapplication_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: LBApplication: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: LBApplication: %s" % (res_id))
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

        alb_stack = Stack(self.aim_ctx, self.account_ctx, self,
                            res_config,
                            alb_template,
                            aws_region=self.aws_region)

        self.stack_list.append(alb_stack)
        self.add_stack_order(alb_stack)

        if hasattr(res_config, 'monitoring') and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ALB', grp_id, res_id])
            self.init_alarms(aws_name, alb_config_ref, res_config)

    def init_asg_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: ASG: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: ASG: " + res_id)
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
                            stack_group=self,
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
                            self,
                            res_config,
                            asg_template,
                            aws_region=self.aws_region)
        self.stack_list.append(asg_stack)
        self.add_stack_order(asg_stack)

        if res_config.monitoring and len(res_config.monitoring.alarm_sets.values()) > 0:
            aws_name = '-'.join(['ASG', grp_id, res_id])
            self.init_alarms(aws_name, asg_config_ref, res_config)

    def init_ec2_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: EC2: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: EC2 Instance")
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
                                self,
                                resources_config[res_id],
                                ec2_template,
                                aws_region=self.aws_region)

            self.stack_list.append(ec2_stack)
            self.add_stack_order(ec2_stack)

    def init_cpbd_resource(self, grp_id, res_id, res_config):
        if res_config.enabled == False:
            print("ApplicationStackGroup: Init: CodePipeBuildDeploy: %s *disabled*" % (res_id))
        else:
            print("ApplicationStackGroup: Init: CodePipeBuildDeploy: %s" % (res_id))
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
                                    self,
                                    None,
                                    kms_template,
                                    aws_region=self.aws_region)

            self.cpbd_kms_stack = kms_stack_pre
            self.stack_list.append(kms_stack_pre)
            self.add_stack_order(kms_stack_pre)


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
                             stack_group=self,
                             template_params=iam_role_params)


            #self.stack_list.append(role_stack)
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
                                        self,
                                        None,
                                        codedeploy_template,
                                        aws_region=self.aws_region)

            self.stack_list.append(codedeploy_stack)
            self.cpbd_codedeploy_stack = codedeploy_stack
            self.add_stack_order(codedeploy_stack)

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
                                                self,
                                                None,
                                                codepipebuild_template,
                                                aws_region=self.aws_region)
            self.stack_list.append(self.cpbd_codepipebuild_stack)
            self.add_stack_order(self.cpbd_codepipebuild_stack)



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
                                self,
                                None,
                                kms_template,
                                aws_region=self.aws_region)

            self.stack_list.append(kms_stack_post)
            self.add_stack_order(kms_stack_post)

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


    def init(self):
        print("ApplicationStackGroup: Init")
        # Resource Groups
        for grp_id, grp_config in self.subenv_ctx.app_group_items(self.app_id):
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
        print("ApplicationStackGroup: Init: Completed")

    def validate(self):
        super().validate()


    def provision(self):
        # Provision any SSL Cerificates
        acm_ctl = self.aim_ctx.get_controller('ACM')
        acm_ctl.provision()

        # Provison Application Group
        super().provision()


    def delete(self):
        super().delete()

    def get_stack_from_ref(self, ref):
        for stack in self.stack_list:
            #print("grp_application: get stack : " + ref.raw + " contains " + stack.template.config_ref)
            if stack.template.config_ref and stack.template.config_ref != '' and ref.raw.find(stack.template.config_ref) != -1:
                return stack
        return None

    def get_app_grp_res(self, ref):
        app_idx = ref.parts.index('applications')
        grp_idx = ref.parts.index('groups')
        res_idx = ref.parts.index('resources')

        app_id = ref.parts[app_idx+1]
        grp_id = ref.parts[grp_idx+1]
        res_id = ref.parts[res_idx+1]
        return [app_id, grp_id, res_id]

    def resolve_ref(self, ref):
        if isinstance(ref.resource, models.resources.CodePipeBuildDeploy):
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
        elif isinstance(ref.resource, models.resources.TargetGroup):
            return self.get_stack_from_ref(ref)
        elif isinstance(ref.resource, models.resources.ASG):
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
        return None