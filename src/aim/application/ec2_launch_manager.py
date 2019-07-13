import os
import pathlib
import tarfile
from aim.stack_group import StackHooks
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
        self.build_path = os.path.join( self.manager.build_path,
                                        self.group_id,
                                        self.resource_id )
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
        bundles_path = os.path.join(self.build_path, 'LaunchBundles')
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

        instance_iam_role_arn_ref = self.manager.app_engine.gen_ref(grp_id=self.group_id,
                                                                    res_id=self.resource_id,
                                                                    attribute='instance_iam_role.arn')
        #instance_iam_role_arn_ref = self.manager.subenv_ctx.gen_ref(app_id=self.app_id,
        #                                                            grp_id=self.group_id,
        #                                                            res_id=self.resource_id,
        #                                                            attribute='instance_iam_role.arn')
        self.instance_iam_role_arn = self.aim_ctx.get_ref(instance_iam_role_arn_ref)


    def get_cache_id(self):
        return self.cache_id

class EC2LaunchManager():
    def __init__(self,
                 aim_ctx,
                 app_engine,
                 app_id,
                 account_ctx,
                 aws_region,
                 config_ref,
                 stack_group):
        self.aim_ctx = aim_ctx
        self.app_engine = app_engine
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.cloudwatch_agent = False
        self.cloudwatch_agent_config = None
        self.app_id = app_id
        self.id = 'ec2lm'
        self.stack_group = stack_group
        self.config_ref = config_ref
        self.launch_bundles = {}
        # cache_id['.'.join[app_id, grp_id, res_id]
        self.cache_id = {}
        self.build_path = os.path.join(self.aim_ctx.build_folder,
                                        'EC2LaunchManager',
                                        self.config_ref,
                                        #self.manager.subenv_ctx.netenv_id,
                                        #self.manager.account_ctx.get_name(),
                                        #self.manager.subenv_ctx.region,
                                        self.account_ctx.get_name(),
                                        self.aws_region,
                                        self.app_id)
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
        bucket_name_prefix = '-'.join([self.app_engine.get_aws_name(), bundle.group_id])
        bucket_name_suffix = self.id
        bucket_region = self.aws_region

        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.init_context(self.account_ctx,
                            self.aws_region,
                            bundle.s3_bucket_ref,
                            self.stack_group)

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
            'aws_region': self.aws_region,
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


        policy_ref = self.app_engine.gen_resource_ref(grp_id=group_id,
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
        policy_ref = self.app_engine.gen_resource_ref(grp_id=group_id,
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