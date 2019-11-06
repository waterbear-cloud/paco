"""
EC2 Launch Manager supports applications by creating a launch bundle that
is a zip file of configuration and scripts to initialize them,
storing the launch bundle in S3 and ensuring that the configuration is
applied in the user_data when instances launch.

For example, if an ASG of instances has monitoring configuration,
the CloudWatch Agent will be installed and configured to collect
the metrics needed to support that monitoring.

Note that EC2 Launch Mangaer is linux-centric and won't work
on Windows instances.
"""


import aim.cftemplates
import json
import os
import pathlib
import tarfile
from aim.stack_group import StackHooks, Stack, StackTags
from aim import models, utils
from aim.models import schemas, vocabulary
from aim.models.locations import get_parent_by_interface
from aim.models.references import Reference
from aim.utils import md5sum, prefixed_name
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class LaunchBundle():
    """
    A collection of files to support initializing a new EC2 instances
    that have been zipped and stored in S3.
    """

    def __init__(
        self,
        aim_ctx,
        name,
        manager,
        app_id,
        group_id,
        resource_id,
        resource_config,
        bucket_id
    ):
        self.aim_ctx = aim_ctx
        self.name = name
        self.manager = manager
        self.app_id = app_id
        self.group_id = group_id
        self.resource_id = resource_id
        self.resource_config = resource_config
        self.bucket_id = bucket_id
        self.build_path = os.path.join(
            self.manager.build_path,
            self.group_id,
            self.resource_id
        )
        self.s3_bucket_ref = None
        self.bundle_files = []
        self.package_path = None
        self.cache_id = ""
        self.s3_key = None

    def set_launch_script(self, launch_script):
        """Set the script run to launch the bundle. By convention, this file
        is named 'launch.sh', and is a reserved filename in a launch bundle.
        """
        self.add_file("launch.sh", launch_script)

    def add_file(self, name, contents):
        """Add a file to the launch bundle"""
        file_config = {
            'name': name,
            'contents': contents
        }
        self.bundle_files.append(file_config)

    def build(self):
        """Builds the launch bundle:

         - Creates files for bundle in a bundles tmp dir

         - Tar gzips files

         - Sets ref to S3 bucket and instance IAM role arn
        """
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
            contents_md5 += md5sum(str_data=bundle_file['contents'])

        self.cache_id = md5sum(str_data=contents_md5)

        lb_tar_filename = str.join('.', [bundle_folder, 'tgz'])
        lb_tar = tarfile.open(lb_tar_filename, "w:gz")
        lb_tar.add(bundle_folder, recursive=True)
        lb_tar.close()
        os.chdir(orig_cwd)
        self.package_filename = lb_tar_filename
        self.package_path = os.path.join(bundles_path, lb_tar_filename)

        # EC2 Manager Bucket Reference
        self.s3_bucket_ref = '.'.join([
            self.resource_config.aim_ref_parts,
            self.manager.id, 'bucket'
        ])

        instance_iam_role_arn_ref = self.resource_config.aim_ref + '.instance_iam_role.arn'
        self.instance_iam_role_arn = self.aim_ctx.get_ref(instance_iam_role_arn_ref)
        if self.instance_iam_role_arn == None:
            raise StackException(
                    AimErrorCode.Unknown,
                    message="ec2_launch_manager: LaunchBundle: build: Unable to locate value for ref: " + instance_iam_role_arn_ref
                )


class EC2LaunchManager():
    """
    Creates and stores a launch bundle in S3 and ensures that the bundle
    will be installed when an EC2 instance launches in an ASG via user_data.
    """
    def __init__(
        self,
        aim_ctx,
        app_engine,
        app_id,
        account_ctx,
        aws_region,
        config_ref,
        stack_group,
        stack_tags
    ):
        self.aim_ctx = aim_ctx
        self.app_engine = app_engine
        self.app_id = app_id
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.config_ref = '.'.join([config_ref, 'applications', app_id])
        self.stack_group = stack_group
        self.cloudwatch_agent = False
        self.cloudwatch_agent_config = None
        self.id = 'ec2lm'
        self.launch_bundles = {}
        self.cache_id = {}
        self.stack_tags = stack_tags
        self.ec2lm_functions_script = {}
        self.ec2lm_buckets = {}
        self.build_path = os.path.join(
            self.aim_ctx.build_folder,
            'EC2LaunchManager',
            self.config_ref,
            self.account_ctx.get_name(),
            self.aws_region,
            self.app_id
        )

    def get_cache_id(self, resource, app_id, grp_id):
        cache_context = '.'.join([app_id, grp_id, resource.name])
        #bucket_name = self.get_s3_bucket_name(app_id, grp_id, self.bucket_id(res_id))
        bucket_name = self.get_ec2lm_bucket_name(resource)
        ec2lm_functions_cache_id = ''
        if bucket_name in self.ec2lm_functions_script.keys():
            ec2lm_functions_cache_id = utils.md5sum(str_data=self.ec2lm_functions_script[bucket_name])

        if cache_context not in self.cache_id:
            return ec2lm_functions_cache_id
        return self.cache_id[cache_context]+ec2lm_functions_cache_id

    def bucket_id(self, resource_id):
        return '-'.join([resource_id, self.id])

    def stack_hook(self, hook, bundle):
        "Uploads the launch bundle to an S3 bucket"
        s3_ctl = self.aim_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(bundle.s3_bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        bundle_s3_key = os.path.join("LaunchBundles", bundle.package_filename)
        s3_client.upload_file(bundle.package_path, bucket_name, bundle_s3_key)

    def stack_hook_cache_id(self, hook, bundle):
        return bundle.cache_id

    def add_bundle_to_s3_bucket(self, bundle):
        """Adds stack hook which will upload launch bundle to an S3 bucket when
        the stack is created or updated."""
        cache_context = '.'.join([bundle.app_id, bundle.group_id, bundle.resource_id])
        if cache_context not in self.cache_id:
            self.cache_id[cache_context] = ''
        self.cache_id[cache_context] += bundle.cache_id
        stack_hooks = StackHooks(self.aim_ctx)
        stack_hooks.add(
            name='EC2LaunchManager',
            stack_action='create',
            stack_timing='post',
            hook_method=self.stack_hook,
            cache_method=self.stack_hook_cache_id,
            hook_arg=bundle
        )
        stack_hooks.add(
            'EC2LaunchManager', 'update', 'post',
            self.stack_hook, self.stack_hook_cache_id, bundle
        )
        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.add_stack_hooks(resource_ref=bundle.s3_bucket_ref, stack_hooks=stack_hooks)

    def ec2lm_functions_hook_cache_id(self, hook, s3_bucket_ref):
        s3_ctl = self.aim_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(s3_bucket_ref)
        return utils.md5sum(str_data=self.ec2lm_functions_script[bucket_name])

    def ec2lm_functions_hook(self, hook, s3_bucket_ref):
        s3_ctl = self.aim_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(s3_bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        s3_client.put_object(
            Bucket=bucket_name,
            Body=self.ec2lm_functions_script[bucket_name],
            Key="ec2lm_functions.bash"
        )

    def init_ec2lm_s3_bucket(self, resource, instance_iam_role_arn):
        s3_bucket_ref = '.'.join([
            resource.aim_ref_parts,
            self.id, 'bucket'])
        if s3_bucket_ref in self.ec2lm_buckets.keys():
            return

        bucket_config_dict = {
            'enabled': True,
            'bucket_name': 'lb',
            'deletion_policy': 'delete',
            'policy': [ {
                'aws': [ "%s" % (instance_iam_role_arn) ],
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
        bucket_config = models.applications.S3Bucket('ec2lm', resource)
        bucket_config.update(bucket_config_dict)
        bucket_config.resolve_ref_obj = self
        bucket_config.enabled = resource.is_enabled()

        # EC2LM Common Functions StackHooks
        stack_hooks = StackHooks(self.aim_ctx)
        stack_hooks.add(
            name='EC2LMFunctions',
            stack_action='create',
            stack_timing='post',
            hook_method=self.ec2lm_functions_hook,
            cache_method=self.ec2lm_functions_hook_cache_id,
            hook_arg=s3_bucket_ref
        )
        stack_hooks.add(
            'EC2LaunchManager', 'update', 'post',
            self.ec2lm_functions_hook, self.ec2lm_functions_hook_cache_id, s3_bucket_ref
        )

        s3_ctl = self.aim_ctx.get_controller('S3')
        s3_ctl.init_context(
            self.account_ctx,
            self.aws_region,
            s3_bucket_ref,
            self.stack_group,
            StackTags(self.stack_tags)
        )
        s3_ctl.add_bucket(
            bucket_config,
            config_ref = s3_bucket_ref,
            stack_hooks=stack_hooks,
            change_protected = resource.change_protected
        )
        self.ec2lm_buckets[s3_bucket_ref] = bucket_config

    def get_ec2lm_bucket_name(self, resource):
        bucket_ref = '.'.join([resource.aim_ref_parts, self.id, 'bucket'])
        s3_ctl = self.aim_ctx.get_controller('S3')
        return s3_ctl.get_bucket_name(bucket_ref)

    def add_ec2lm_function_swap(self, ec2lm_bucket_name):
        self.ec2lm_functions_script[ec2lm_bucket_name] += """
# Swap
function swap_on() {
    SWAP_SIZE_GB=$1
    if [ -e /swapfile ] ; then
        CUR_SWAP_FILE_SIZE=$(stat -c '%s' /swapfile)
        if [ $CUR_SWAP_FILE_SIZE -eq $(($SWAP_SIZE_GB*1073741824)) ] ; then
            swapon /swapfile
            if [ $? -eq 0 ] ; then
                echo "Enabling existing ${SWAP_SIZE_GB}GB Swapfile: /swapfile"
            fi
        fi
    fi
    if [ "$(swapon -s|grep -v Filename|wc -c)" == "0" ]; then
        echo "Enabling a ${SWAP_SIZE_GB}GB Swapfile: /swapfile"
        dd if=/dev/zero of=/swapfile bs=1024 count=$(($SWAP_SIZE_GB*1024))k
        chmod 0600 /swapfile
        mkswap /swapfile
        swapon /swapfile
    else
        echo "Swap already enabled"
    fi
    swapon -s
    free
}
"""

    def add_ec2lm_function_wget(self, ec2lm_bucket_name, instance_ami_type):
        self.ec2lm_functions_script[ec2lm_bucket_name] += """
# HTTP Client Path
function install_wget() {
    CLIENT_PATH=$(which wget)
    if [ $? -eq 1 ] ; then
        %s
    fi
}
""" % vocabulary.user_data_script['install_wget'][instance_ami_type]

    def add_ec2lm_function_eip(self, ec2lm_bucket_name, resource, grp_id, instance_iam_role_ref):
        """Adds functions for associating EIPs"""
        self.ec2lm_functions_script[ec2lm_bucket_name] += self.user_data_eip(resource, grp_id, instance_iam_role_ref)

    def add_ec2lm_function_secrets(self, ec2lm_bucket_name, resource, grp_id, instance_iam_role_ref):
        """Adds functions for getting secrets from Secrets Manager"""
        self.ec2lm_functions_script[ec2lm_bucket_name] += self.user_data_secrets(resource, grp_id, instance_iam_role_ref)

    def init_ec2lm_function(self, ec2lm_bucket_name, resource, instance_iam_role_ref):
        script_table = {
            'ec2lm_bucket_name': ec2lm_bucket_name,
            'aim_environment': self.app_engine.env_ctx.env_id,
            'aim_network_environment': self.app_engine.env_ctx.netenv_id,
            'aim_environment_ref': self.app_engine.env_ctx.config.aim_ref_parts,
            'aws_account_id': self.account_ctx.id
        }

        script_template = """
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AVAIL_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
REGION="$(echo \"$AVAIL_ZONE\" | sed 's/[a-z]$//')"
export AWS_DEFAULT_REGION=$REGION
EC2LM_AWS_ACCOUNT_ID="{0[aws_account_id]:s}"
EC2LM_STACK_NAME=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=aws:cloudformation:stack-name" --query 'Tags[0].Value' |tr -d '"')
EC2LM_FOLDER='/opt/aim/EC2Manager/'
EC2LM_AIM_NETWORK_ENVIRONMENT="{0[aim_network_environment]:s}"
EC2LM_AIM_ENVIRONMENT="{0[aim_environment]:s}"
EC2LM_AIM_ENVIRONMENT_REF={0[aim_environment_ref]:s}

# Escape a string for sed replacements
function sed_escape() {{
    RES="${{1//$'\n'/\\n}}"
    RES="${{RES//./\\.}}"
    RES="${{RES//\//\\/}}"
    RES="${{RES// /\\ }}"
    RES="${{RES//!/\\!}}"
    RES="${{RES//-/\\-}}"
    RES="${{RES//,/\\,}}"
    RES="${{RES//&/\\&}}"
    echo "${{RES}}"
}}

# Launch Bundles
function ec2lm_launch_bundles() {{
    mkdir -p $EC2LM_FOLDER/LaunchBundles
    aws s3 sync s3://{0[ec2lm_bucket_name]:s}/ $EC2LM_FOLDER

    cd $EC2LM_FOLDER/LaunchBundles/

    echo "Loading Launch Bundles"
    for BUNDLE_PACKAGE in *.tgz
    do
        BUNDLE_FOLDER=${{BUNDLE_PACKAGE//'.tgz'/}}
        echo "$BUNDLE_FOLDER: Unpacking:"
        if [ ! -f "$BUNDLE_PACKAGE" ] ; then
            echo "Unable to find package: $BUNDLE_PACKAGE"
            continue
        fi
        tar xvfz $BUNDLE_PACKAGE
        chown -R root.root $BUNDLE_FOLDER
        echo "$BUNDLE_FOLDER: Launching bundle"
        cd $BUNDLE_FOLDER
        chmod u+x ./launch.sh
        ./launch.sh
        cd ..
        echo "$BUNDLE_FOLDER: Done"
    done
}}

# Instance Tags
function ec2lm_instance_tag_value() {{
    TAG_NAME="$1"
    aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=$TAG_NAME" --query 'Tags[0].Value' |tr -d '"'
}}

"""
        self.ec2lm_functions_script[ec2lm_bucket_name] = script_template.format(script_table)

        policy_config_yaml = """
name: 'DescribeTags'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:DescribeTags"
    resource:
      - '*'
"""
        group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name

        policy_ref = '{}.{}.ec2lm.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'ec2lm'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=group_name,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=resource.change_protected
        )

    def user_data_script(self, app_id, grp_id, resource_id, resource, instance_iam_role_ref):
        """BASH script that will load the launch bundle from user_data"""
        script_fmt = """#!/bin/bash
echo "EC2 Launch Manager"
echo "Script: $0"
echo "CacheId: {0[cache_id]}"
{0[pre_script]}
{0[update_packages]}
{0[install_aws_cli]}

EC2LM_FUNCTIONS=ec2lm_functions.bash
aws s3 cp s3://{0[ec2lm_bucket_name]}/$EC2LM_FUNCTIONS /tmp/$EC2LM_FUNCTIONS
. /tmp/$EC2LM_FUNCTIONS

{0[launch_bundles]}
"""
        instance_iam_role_arn_ref = 'aim.ref '+instance_iam_role_ref + '.arn'
        instance_iam_role_arn = self.aim_ctx.get_ref(instance_iam_role_arn_ref)
        if instance_iam_role_arn == None:
            raise StackException(
                    AimErrorCode.Unknown,
                    message="ec2_launch_manager: user_data_script: Unable to locate value for ref: " + instance_iam_role_arn_ref
                )
        self.init_ec2lm_s3_bucket(resource, instance_iam_role_arn)

        ec2lm_bucket_name = self.get_ec2lm_bucket_name(resource)

        script_table = {
            'cache_id': None,
            'ec2lm_bucket_name': ec2lm_bucket_name,
            'install_aws_cli': vocabulary.user_data_script['install_aws_cli'][resource.instance_ami_type],
            'launch_bundles': 'echo "No launch bundles to load."\n',
            'update_packages': '',
            'pre_script': ''
        }
        # Launch Bundles
        if len(self.launch_bundles.keys()) > 0:
            script_table['launch_bundles'] = 'ec2lm_launch_bundles\n'

        # EC2LM Functions
        self.init_ec2lm_function(ec2lm_bucket_name, resource, instance_iam_role_ref)
        self.add_ec2lm_function_swap(ec2lm_bucket_name)
        self.add_ec2lm_function_wget(ec2lm_bucket_name, resource.instance_ami_type)

        if resource.user_data_pre_script != None:
            script_table['pre_script'] = resource.user_data_pre_script

        if resource.eip != None:
            self.add_ec2lm_function_eip(ec2lm_bucket_name, resource, grp_id, instance_iam_role_ref)

        if resource.secrets != None and len(resource.secrets) > 0:
            self.add_ec2lm_function_secrets(ec2lm_bucket_name, resource, grp_id, instance_iam_role_ref)

        if resource.launch_options != None:
            if resource.launch_options.update_packages == True:
                script_table['update_packages'] = vocabulary.user_data_script['update_packages'][resource.instance_ami_type]

        script_table['cache_id'] = self.get_cache_id(resource, app_id, grp_id)
        return script_fmt.format(script_table)

    def user_data_secrets(self, resource, grp_id, instance_iam_role_ref):
        secrets_script = """
function ec2lm_get_secret() {
    aws secretsmanager get-secret-value --secret-id "$1" --query SecretString --region $REGION --output text
}

# ec2lm_replace_secret_in_file <secret id> <file> <replace pattern>
function ec2lm_replace_secret_in_file() {
    SECRET_ID=$1
    SED_PATTERN=$2
    REPLACE_FILE=$3
    SECRET=$(ec2lm_get_secret $SECRET_ID)

    sed -i -e "s/$SED_PATTERN/$SECRET/" $REPLACE_FILE
}
"""
        policy_config_yaml = """
name: 'Secrets'
enabled: true
statement:
  - effect: Allow
    action:
      - secretsmanager:GetSecretValue
    resource:
{}
"""
        template_params = []
        secret_arn_list_yaml = ""
        for secret in resource.secrets:
            secret_ref = Reference(secret)
            secret_hash = utils.md5sum(str_data='.'.join(secret_ref.parts))
            param = {
                'description': 'Secrets Manager Secret ARN',
                'type': 'String',
                'key': 'SecretArn' + secret_hash,
                'value': secret + '.arn'
            }
            template_params.append(param)
            secret_arn_list_yaml += "      - !Ref SecretArn" + secret_hash + "\n"
        policy_ref = '{}.{}.secrets.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'secrets'])
        iam_ctl = self.aim_ctx.get_controller('IAM')

        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=grp_id,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml.format(secret_arn_list_yaml),
            template_params=template_params,
            change_protected=resource.change_protected
        )

        return secrets_script

    def user_data_eip(self,resource, grp_id, instance_iam_role_ref):
        eip_script = """
EIP_ALLOC_ID=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=AIM-EIP-Allocation-Id" --query 'Tags[0].Value' |tr -d '"')
EIP_IP=$(aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID --query 'Addresses[0].PublicIp' --region $REGION | tr -d '"')
aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $EIP_ALLOC_ID --region $REGION
# Wait for the EIP to associate
COUNT=0
TIMEOUT=10
echo -n "Waiting for EIP to associate"
while :
do
  PUBLIC_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4/)
  if [ "$PUBLIC_IP" == "$EIP_IP" ] ; then
    echo
    echo "EIP Association Successful"
    break
  fi
  echo -n "."
  sleep 1
  COUNT=$(($COUNT+1))
  if [ $COUNT -eq $TIMEOUT ] ; then
    echo
    echo "ERROR: Unable to associate EIP: Timedout after $TIMEOUT seconds"
    break
  fi
done
"""
        policy_config_yaml = """
name: 'AssociateEIP'
enabled: true
statement:
  - effect: Allow
    action:
      - 'ec2:AssociateAddress'
      - 'ec2:DescribeAddresses'
    resource:
      - '*'
"""

        policy_ref = '{}.{}.eip.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'eip'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=grp_id,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=resource.change_protected
        )

        return eip_script

    def add_bundle(self, bundle):
        bundle.build()
        if bundle.s3_bucket_ref not in self.launch_bundles:
            self.init_ec2lm_s3_bucket(bundle.resource_config, bundle.instance_iam_role_arn)
            self.launch_bundles[bundle.s3_bucket_ref] = []
            # Initializes the CloudFormation for this S3 Context ID
        # Add the bundle to the S3 Context ID bucket
        self.add_bundle_to_s3_bucket(bundle)
        self.launch_bundles[bundle.s3_bucket_ref].append(bundle)

    def lb_add_cfn_init(self, resource):
        """Creates a launch bundle to download and run cfn-init"""
        if resource.launch_options.cfn_init_config_sets == None or \
            resource.launch_options == None or \
            len(resource.launch_options.cfn_init_config_sets) == 0:
            return
        # TODO: Add ubuntu and other distro support
        launch_script = """#!/bin/bash
. /opt/aim/EC2Manager/ec2lm_functions.bash
%s
/opt/aim/bin/cfn-init --stack=$EC2LM_STACK_NAME --resource=LaunchConfiguration --region=$REGION --configsets=%s
""" % (
    vocabulary.user_data_script['install_cfn_init'][resource.instance_ami_type],
    ','.join(resource.launch_options.cfn_init_config_sets)
)

        # Create the Launch Bundle and configure it
        app_name = get_parent_by_interface(resource, schemas.IApplication).name
        group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name
        cfn_init_lb = LaunchBundle(
            self.aim_ctx,
            "cfn-init",
            self,
            app_name,
            group_name,
            resource.name,
            resource,
            self.bucket_id(resource.name)
        )
        cfn_init_lb.set_launch_script(launch_script)

        # Save Configuration
        self.add_bundle(cfn_init_lb)

    def lb_add_efs_mounts(self, instance_iam_role_ref, resource):
        """Creates a launch bundle to configure EFS mounts:

         - Installs an entry in /etc/fstab
         - On launch runs mount
        """
        # TODO: Add ubuntu and other distro support
        launch_script_template = """#!/bin/bash

# CachId: 2019-09-15.01
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AVAIL_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
REGION="$(echo \"$AVAIL_ZONE\" | sed 's/[a-z]$//')"

function process_mount_target()
{
    MOUNT_FOLDER=$1
    EFS_ID_HASH=$2

    # Get EFSID from Tag
    EFS_ID=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=efs-id-$EFS_ID_HASH" --query 'Tags[0].Value' |tr -d '"')

    # Setup the mount folder
    if [ -e $MOUNT_FOLDER ] ; then
        mv $MOUNT_FOLDER ${MOUNT_FOLDER%%/}.old
    fi
    mkdir -p $MOUNT_FOLDER

    # Setup fstab
    grep -v -E "^$EFS_ID:/" /etc/fstab >/tmp/fstab.efs_new
    echo "$EFS_ID:/ $MOUNT_FOLDER efs defaults,_netdev,fsc 0 0" >>/tmp/fstab.efs_new
    mv /tmp/fstab.efs_new /etc/fstab
    chmod 0664 /etc/fstab
}

%s
%s

%s

%s
"""
        process_mount_targets = ""
        for efs_mount in resource.efs_mounts:
            if efs_mount.enabled == False:
                continue
            efs_id_hash = utils.md5sum(str_data=efs_mount.target)
            process_mount_targets += "process_mount_target {} {}\n".format(efs_mount.folder, efs_id_hash)

        launch_script = launch_script_template % (
            vocabulary.user_data_script['install_efs_utils'][resource.instance_ami_type],
            vocabulary.user_data_script['enable_efs_utils'][resource.instance_ami_type],
            process_mount_targets,
            vocabulary.user_data_script['mount_efs'][resource.instance_ami_type])

        app_name = get_parent_by_interface(resource, schemas.IApplication).name
        group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name

        policy_config_yaml = """
name: 'DescribeTags'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:DescribeTags"
    resource:
      - '*'
"""

        policy_ref = '{}.{}.efs.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'efs'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=group_name,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=resource.change_protected
        )

        # Create the Launch Bundle and configure it
        efs_lb = LaunchBundle(
            self.aim_ctx,
            "EFS",
            self,
            app_name,
            group_name,
            resource.name,
            resource,
            self.bucket_id(resource.name)
        )
        efs_lb.set_launch_script(launch_script)

        # Save Configuration
        self.add_bundle(efs_lb)

    def lb_add_ebs_volume_mounts(self, instance_iam_role_ref, resource):
        """Creates a launch bundle to configure EBS Volume mounts:

         - Installs an entry in /etc/fstab
         - On launch runs mount
        """
        # TODO: Add ubuntu and other distro support
        launch_script_template = """#!/bin/bash

. /tmp/ec2lm_functions.bash

# Attach and Mount an EBS Volume
function process_volume_mount()
{
    MOUNT_FOLDER=$1
    EBS_VOLUME_ID_HASH=$2
    FILESYSTEM=$3
    EBS_DEVICE=$4

    # Get EBS Volume Tags and Device
    EBS_VOLUME_ID=$(ec2lm_instance_tag_value "ebs-volume-id-$EBS_VOLUME_ID_HASH")

    # Setup the mount folder
    if [ -e $MOUNT_FOLDER ] ; then
        mv $MOUNT_FOLDER ${MOUNT_FOLDER%%/}.old
    fi
    mkdir -p $MOUNT_FOLDER

    COUNT=0
    TIMEOUT=300
    echo "EC2LM: EBS: Attaching $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE: Timeout = $TIMEOUT"
    while :
    do
        aws ec2 attach-volume --region $REGION --volume-id $EBS_VOLUME_ID --instance-id $INSTANCE_ID --device $EBS_DEVICE 2>/tmp/ec2lm_attach.output
        if [ $? -eq 0 ] ; then
            echo "Successfully attached  $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE"
            break
        fi
        sleep 1
        COUNT=$(($COUNT + 1))
        if [ $COUNT -eq $TIMEOUT ] ; then
            echo
            echo "Unable to attach $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE"
            cat /tmp/ec2lm_attach.output
            shutdown -H now
            exit 1
        fi
    done

    # Setup fstab
    echo "Volume UUID: blkid $EBS_DEVICE |grep UUID |cut -d '\\"' -f 2"
    COUNT=0
    VOLUME_UUID=""
    echo "Getting Volume UUID for $EBS_DEVICE"
    TIMEOUT=30
    while :
    do
        VOLUME_UUID=$(/sbin/blkid $EBS_DEVICE |grep UUID |cut -d'"' -f 2)
        if [ "${VOLUME_UUID}" != "" ] ; then
            break
        fi
        echo -e '.'
        sleep 1
        COUNT=$(($COUNT + 1))
        if [ $COUNT -eq $TIMEOUT ] ; then
            echo
            echo "Unable to get volume UUID for $EBS_DEVICE"
            /sbin/blkid
            exit 1
        fi
    done
    echo "$EBS_DEVICE UUID: $VOLUME_UUID"
    grep -v -E "^UUID=$VOLUME_UUID" /etc/fstab >/tmp/fstab.ebs_new
    echo "UUID=$VOLUME_UUID $MOUNT_FOLDER $FILESYSTEM defaults,nofail 0 2" >>/tmp/fstab.ebs_new
    mv /tmp/fstab.ebs_new /etc/fstab
    chmod 0664 /etc/fstab
    mount $MOUNT_FOLDER
}

%s

"""
        process_mount_volumes = ""
        is_enabled = False
        for ebs_volume_mount in resource.ebs_volume_mounts:
            if ebs_volume_mount.enabled == False:
                continue
            ebs_volume_id_hash = utils.md5sum(str_data=ebs_volume_mount.volume)
            process_mount_volumes += "process_volume_mount {} {} {} {}\n".format(
                ebs_volume_mount.folder,
                ebs_volume_id_hash,
                ebs_volume_mount.filesystem,
                ebs_volume_mount.device)
            is_enabled = True

        if is_enabled == False:
            return


        launch_script = launch_script_template % (
            process_mount_volumes)
            #vocabulary.user_data_script['mount_efs'][resource.instance_ami_type])

        app_name = get_parent_by_interface(resource, schemas.IApplication).name
        group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name

        policy_config_yaml = """
name: 'AssociateVolume'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:AttachVolume"
    resource:
      - 'arn:aws:ec2:*:*:volume/*'
      - 'arn:aws:ec2:*:*:instance/*'
"""

        policy_ref = '{}.{}.ebs.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'ebs'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=group_name,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=resource.change_protected
        )

        # Create the Launch Bundle and configure it
        ebs_lb = LaunchBundle(
            self.aim_ctx,
            "EBS",
            self,
            app_name,
            group_name,
            resource.name,
            resource,
            self.bucket_id(resource.name)
        )
        ebs_lb.set_launch_script(launch_script)

        # Save Configuration
        self.add_bundle(ebs_lb)

    def lb_add_cloudwatch_agent(
        self,
        instance_iam_role_ref,
        resource
    ):
        """Creates a launch bundle to install and configure a CloudWatch Agent:

         - Adds a launch script to install the agent

         - Adds a CW Agent JSON configuration file for the agent

         - Adds an IAM Policy to the instance IAM role that will allow the agent
           to do what it needs to do (e.g. send metrics and logs to CloudWatch)
        """
        monitoring = resource.monitoring
        app_name = get_parent_by_interface(resource, schemas.IApplication).name
        group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name

        # Launch script
        launch_script_template = """#!/bin/bash

# Load EC2 Launch Manager helper functions
. /tmp/ec2lm_functions.bash

# Download the agent
LB_DIR=$(pwd)
mkdir /tmp/aim/
cd /tmp/aim/
install_wget # build in function
wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent{0[agent_path]:s}/{0[agent_object]:s}
wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent{0[agent_path]:s}/{0[agent_object]:s}.sig

# Verify the agent
TRUSTED_FINGERPRINT=$(echo "9376 16F3 450B 7D80 6CBD 9725 D581 6730 3B78 9C72" | tr -d ' ')
wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent/assets/amazon-cloudwatch-agent.gpg
gpg --import amazon-cloudwatch-agent.gpg

KEY_ID="$(gpg --list-packets amazon-cloudwatch-agent.gpg 2>&1 | awk '/keyid:/{{ print $2 }}' | tr -d ' ')"
FINGERPRINT="$(gpg --fingerprint ${{KEY_ID}} 2>&1 | tr -d ' ')"
OBJECT_FINGERPRINT="$(gpg --verify {0[agent_object]:s}.sig {0[agent_object]:s} 2>&1 | tr -d ' ')"
if [[ ${{FINGERPRINT}} != *${{TRUSTED_FINGERPRINT}}* || ${{OBJECT_FINGERPRINT}} != *${{TRUSTED_FINGERPRINT}}* ]]; then
    # Log error here
    echo "ERROR: CloudWatch Agent signature invalid: ${{KEY_ID}}: ${{OBJECT_FINGERPRINT}}"
    exit 1
fi

# Install the agent
echo "Running: {0[install_command]:s} {0[agent_object]}"
{0[install_command]:s} {0[agent_object]}

cd ${{LB_DIR}}

echo "Running: /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:amazon-cloudwatch-agent.json -s"
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:amazon-cloudwatch-agent.json -s
"""


        launch_script_table = {
            'agent_path': vocabulary.cloudwatch_agent[resource.instance_ami_type]['path'],
            'agent_object': vocabulary.cloudwatch_agent[resource.instance_ami_type]['object'],
            'install_command': vocabulary.cloudwatch_agent[resource.instance_ami_type]['install']
        }
        launch_script = launch_script_template.format(launch_script_table)

        # Agent Configuration file
        # /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
        agent_config = {
            "agent": {
                "metrics_collection_interval": 60,
                "region": self.aws_region,
                "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
            }
        }

        # if there is metrics, add to the cwagent config
        if monitoring.metrics:
            agent_config["metrics"] = {
                "metrics_collected": {},
                "append_dimensions": {
                    "ImageId": "${aws:ImageId}",
                    "InstanceId": "${aws:InstanceId}",
                    "InstanceType": "${aws:InstanceType}",
                    "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
                },
                "aggregation_dimensions" : [["AutoScalingGroupName"], ["InstanceId", "InstanceType"],[]]
            }
            collected = agent_config['metrics']['metrics_collected']
            for metric in monitoring.metrics:
                if metric.collection_interval:
                    interval = metric.collection_interval
                else:
                    interval = monitoring.collection_interval
                collected[metric.name] = {
                    "measurement": metric.measurements,
                    "collection_interval": interval
                }

        # if there is logging, add it to the cwagent config
        if monitoring.log_sets:
            agent_config["logs"] = {
                "logs_collected": {
                    "files": {
                        "collect_list": []
                    }
                }
            }
            collect_list = agent_config['logs']['logs_collected']['files']['collect_list']
            for log_source in monitoring.log_sets.get_all_log_sources():
                log_group = get_parent_by_interface(log_source, schemas.ICloudWatchLogGroup)
                prefixed_log_group_name = prefixed_name(resource, log_group.get_log_group_name(), self.aim_ctx.legacy_flag)
                source_config = {
                    "file_path": log_source.path,
                    "log_group_name": prefixed_log_group_name,
                    "log_stream_name": log_source.log_stream_name,
                    "encoding": log_source.encoding,
                    "timezone": log_source.timezone
                }
                if log_source.multi_line_start_pattern:
                    source_config["multi_line_start_pattern"] = log_source.multi_line_start_pattern
                if log_source.timestamp_format:
                    source_config["timestamp_format"] = log_source.timestamp_format
                collect_list.append(source_config)

        # Convert CW Agent data structure to JSON string
        agent_config = json.dumps(agent_config)

        # Create instance managed policy for the agent
        policy_config_yaml = """
name: 'CloudWatchAgent'
enabled: true
statement:
  - effect: Allow
    resource: "*"
    action:
      - "cloudwatch:PutMetricData"
      - "autoscaling:Describe*"
      - "ec2:DescribeTags"
"""
        if monitoring.log_sets:
            # append a logs:CreateLogGroup to the AllResources sid
            policy_config_yaml += """      - "logs:CreateLogGroup"\n"""
            log_group_resources = ""
            log_stream_resources = ""
            for log_group in monitoring.log_sets.get_all_log_groups():
                log_group_resources += "      - arn:aws:logs:{}:{}:log-group:{}:*\n".format(
                    self.aws_region, self.account_ctx.id, prefixed_name(resource, log_group.get_log_group_name(), self.aim_ctx.legacy_flag)
                )
                log_stream_resources += "      - arn:aws:logs:{}:{}:log-group:{}:log-stream:*\n".format(
                    self.aws_region, self.account_ctx.id, prefixed_name(resource, log_group.get_log_group_name(), self.aim_ctx.legacy_flag)
                )
            policy_config_yaml += """
  - effect: Allow
    action:
      - "logs:DescribeLogStreams"
      - "logs:DescribeLogGroups"
      - "logs:CreateLogStream"
    resource:
{}
  - effect: Allow
    action:
     - "logs:PutLogEvents"
    resource:
{}
""".format(log_group_resources, log_stream_resources)

        policy_ref = '{}.{}.cloudwatchagent.policy'.format(resource.aim_ref_parts, self.id)
        policy_id = '-'.join([resource.name, 'cloudwatchagent'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=resource,
            group_id=group_name,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=resource.change_protected
        )

        # Create the Launch Bundle and configure it
        cw_lb = LaunchBundle(
            self.aim_ctx,
            "CloudWatchAgent",
            self,
            app_name,
            group_name,
            resource.name,
            resource,
            self.bucket_id(resource.name)
        )
        cw_lb.set_launch_script(launch_script)
        cw_lb.add_file('amazon-cloudwatch-agent.json', agent_config)

        # Create the CloudWatch Log Groups so that Retention and MetricFilters can be set
        if monitoring.log_sets:
            group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name
            log_groups_config_ref = resource.aim_ref_parts + '.log_groups'
            aim.cftemplates.LogGroups(
                self.aim_ctx,
                self.account_ctx,
                self.aws_region,
                self.stack_group,
                None, # stack_tags
                group_name,
                resource,
                log_groups_config_ref,
            )

        # Save Configuration
        self.add_bundle(cw_lb)

    def lb_add_ssm_agent(
        self,
        instance_iam_role_ref,
        app_id,
        group_id,
        resource_id,
        res_config
    ):
        """Creates a launch bundle to intall and configure an SSM agent
        ToDo: Only Amazon Linux is supported right now.
        """
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
        policy_ref = '{}.{}.ssmagent.policy'.format(res_config.aim_ref_parts, self.id)
        policy_id = '-'.join([resource_id, 'ssmagent-policy'])
        iam_ctl = self.aim_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role_ref=instance_iam_role_ref,
            parent_config=res_config,
            group_id=group_id,
            policy_id=policy_id,
            policy_ref=policy_ref,
            policy_config_yaml=policy_config_yaml,
            change_protected=res_config.change_protected
        )

        # Create the Launch Bundle and configure it
        ssm_lb = LaunchBundle(self.aim_ctx, "SSMAgent", self, app_id, group_id, resource_id, res_config, self.bucket_id(resource_id))
        ssm_lb.set_launch_script(launch_script)

        # Save Configuration
        self.add_bundle(ssm_lb)

    def validate(self):
        pass

    def provision(self):
        pass

    def delete(self):
        pass