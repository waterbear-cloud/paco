"""
EC2 Launch Manager supports applications by creating a launch bundle that
is a zip file of configuration and scripts to initialize them,
storing the launch bundle in S3 and ensuring that the configuration is
applied in the user_data when instances launch.

For example, if an ASG of instances has monitoring configuration,
the CloudWatch Agent will be installed and configured to collect
the metrics needed to support that monitoring.

EC2 Launch Mangaer is currently linux-centric and does not yet work with Windows instances.
"""


import base64
import paco.cftemplates
import json
import os
import pathlib
import shutil
import tarfile
from paco.stack import StackHooks, Stack, StackTags
from paco import models
from paco import utils
from paco.application import ec2lm_commands
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference, is_ref, resolve_ref, get_model_obj_from_ref
from paco.models.base import Named
from paco.models.resources import SSMDocument
from paco.utils import md5sum, prefixed_name
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.application.reseng_deploymentpipeline import RELEASE_PHASE_SCRIPT, RELEASE_PHASE_SCRIPT_SSM_DOCUMENT_CONTENT, \
        ECR_DEPLOY_SCRIPT_HEAD, ECR_DEPLOY_SCRIPT_BODY, ECR_DEPLOY_SCRIPT_CONFIG

class LaunchBundle():
    """
    A zip file sent to an S3 Bucket to support initializing a new EC2 instance.
    """

    def __init__(self, resource, manager, name):
        self.name = name
        self.manager = manager
        self.resource = resource
        self.build_path = os.path.join(
            self.manager.build_path,
            self.resource.group_name,
            self.resource.name,
        )
        self.bundle_files = []
        self.cache_id = ""
        self.bucket_ref = resource.paco_ref_parts + '.ec2lm'
        self.bundles_path = os.path.join(self.build_path, 'LaunchBundles')
        self.bundle_folder = self.name
        self.package_filename = str.join('.', [self.bundle_folder, 'tgz'])
        self.package_path = os.path.join(self.bundles_path, self.package_filename)

    def set_launch_script(self, launch_script, enabled=True):
        """Set the script run to launch the bundle. By convention, this file
        is named 'launch.sh', and is a reserved filename in a launch bundle.
        """
        if enabled == True:
            launch_bundle_enabled="true"
        else:
           launch_bundle_enabled="false"
        enabled_script = f"""
# This script is auto-generated. Do not edit.
LAUNCH_BUNDLE_ENABLED={launch_bundle_enabled}
if [ "$LAUNCH_BUNDLE_ENABLED" == "true" ] ; then
    run_launch_bundle
else
    disable_launch_bundle
fi
"""
        self.add_file("launch.sh", launch_script + enabled_script)

    def add_file(self, name, contents):
        """Add a file to the launch bundle"""
        file_config = {
            'name': name,
            'contents': contents
        }
        self.bundle_files.append(file_config)

    def build(self):
        """Builds the launch bundle. Puts the files for the bundle in a bundles tmp dir
        and then creates a gzip archive.
        Updates the bundle cache id based on the contents of the bundle.
        """
        orig_cwd = os.getcwd()
        pathlib.Path(self.bundles_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.bundles_path)
        pathlib.Path(self.bundle_folder).mkdir(parents=True, exist_ok=True)
        contents_md5 = ""
        for bundle_file in self.bundle_files:
            utils.write_to_file(self.bundle_folder, bundle_file['name'], bundle_file['contents'])
            contents_md5 += md5sum(str_data=bundle_file['contents'])
        lb_tar = tarfile.open(self.package_filename, "w:gz")
        lb_tar.add(self.bundle_folder, recursive=True)
        lb_tar.close()
        os.chdir(orig_cwd)
        self.cache_id = md5sum(str_data=contents_md5)


class EC2LaunchManager():
    """
    Creates and stores a launch bundle in S3 and ensures that the bundle
    will be installed when an EC2 instance launches in an ASG via user_data.
    """
    def __init__(
        self,
        paco_ctx,
        app_engine,
        application,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags
    ):
        self.paco_ctx = paco_ctx
        self.app_engine = app_engine
        self.application = application
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.stack_group = stack_group
        self.cloudwatch_agent = False
        self.cloudwatch_agent_config = None
        self.id = 'ec2lm'
        self.launch_bundles = {}
        self.cache_id = {}
        self.stack_tags = stack_tags
        self.ec2lm_functions_script = {}
        self.ec2lm_buckets = {}
        self.launch_bundle_names = [
            'SSM', 'EIP', 'CloudWatchAgent', 'EFS', 'EBS', 'cfn-init', 'SSHAccess', 'ECS', 'CodeDeploy', 'ScriptManager'#, 'DNS'
        ]
        self.build_path = os.path.join(
            self.paco_ctx.build_path,
            'EC2LaunchManager',
            self.application.paco_ref_parts,
            self.account_ctx.get_name(),
            self.aws_region,
            self.application.name,
        )
        self.paco_base_path = '/opt/paco'
        # legacy_flag: aim_name_2019_11_28 - Use AIM name
        if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
            self.paco_base_path = '/opt/aim'

    def get_cache_id(self, resource):
        """Return a cache id unique to an ASG resource.
        Cache id is an aggregate of all bundle cache ids and the ec2lm functions script cache id.
        """
        cache_context = '.'.join([resource.app_name, resource.group_name, resource.name])
        bucket_name = self.get_ec2lm_bucket_name(resource)
        ec2lm_functions_cache_id = ''
        if bucket_name in self.ec2lm_functions_script.keys():
            ec2lm_functions_cache_id = utils.md5sum(str_data=self.ec2lm_functions_script[bucket_name])
        if cache_context not in self.cache_id:
            return ec2lm_functions_cache_id
        return self.cache_id[cache_context] + ec2lm_functions_cache_id

    def upload_bundle_stack_hook(self, hook, bundle):
        "Uploads the launch bundle to an S3 bucket"
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(bundle.bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        bundle_s3_key = os.path.join("LaunchBundles", bundle.package_filename)
        s3_client.upload_file(bundle.package_path, bucket_name, bundle_s3_key)

    def stack_hook_cache_id(self, hook, bundle):
        "Cache method to return a bundle's cache id"
        return bundle.cache_id

    def add_bundle_to_s3_bucket(self, bundle):
        """Adds stack hook which will upload launch bundle to an S3 bucket when
        the stack is created or updated."""
        cache_context = '.'.join([bundle.resource.app_name, bundle.resource.group_name, bundle.resource.name])
        if cache_context not in self.cache_id:
            self.cache_id[cache_context] = ''
        self.cache_id[cache_context] += bundle.cache_id
        stack_hooks = StackHooks()
        stack_hooks.add(
            name='UploadBundle.'+bundle.name,
            stack_action='create',
            stack_timing='post',
            hook_method=self.upload_bundle_stack_hook,
            cache_method=self.stack_hook_cache_id,
            hook_arg=bundle
        )
        stack_hooks.add(
            'UploadBundle.'+bundle.name, 'update', 'post',
            self.upload_bundle_stack_hook, self.stack_hook_cache_id, bundle
        )
        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_ctl.add_stack_hooks(resource_ref=bundle.bucket_ref, stack_hooks=stack_hooks)

    def ec2lm_functions_hook_cache_id(self, hook, s3_bucket_ref):
        "Cache method for EC2LM functions cache id"
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(s3_bucket_ref)
        return utils.md5sum(str_data=self.ec2lm_functions_script[bucket_name])

    def ec2lm_functions_hook(self, hook, s3_bucket_ref):
        "Hook to upload ec2lm_functions.bash to S3"
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(s3_bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        s3_client.put_object(
            Bucket=bucket_name,
            Body=self.ec2lm_functions_script[bucket_name],
            Key="ec2lm_functions.bash"
        )

    def ec2lm_update_instances_hook(self, hook, bucket_resource):
        "Hook to upload ec2lm_cache_id.md5 to S3 and invoke SSM Run Command on paco_ec2lm_update_instance"
        s3_bucket_ref, resource = bucket_resource
        cache_id = self.get_cache_id(resource)
        # update ec2lm_cache_id.md5 file
        s3_ctl = self.paco_ctx.get_controller('S3')
        bucket_name = s3_ctl.get_bucket_name(s3_bucket_ref)
        s3_client = self.account_ctx.get_aws_client('s3')
        s3_client.put_object(
            Bucket=bucket_name,
            Body=cache_id,
            Key="ec2lm_cache_id.md5"
        )
        # send SSM command to update existing instances
        ssm_client = self.account_ctx.get_aws_client('ssm', aws_region=self.aws_region)
        ssm_log_group_name = prefixed_name(resource, 'paco_ssm', self.paco_ctx.legacy_flag)
        ssm_client.send_command(
            Targets=[{
                'Key': 'tag:aws:cloudformation:stack-name',
                'Values': [resource.stack.get_name()]
            },],
            DocumentName='paco_ec2lm_update_instance',
            Parameters={ 'CacheId': [cache_id] },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': ssm_log_group_name,
                'CloudWatchOutputEnabled': True,
            },
        )

    def ec2lm_update_instances_cache(self, hook, bucket_resource):
        "Cache method for EC2LM resource"
        s3_bucket_ref, resource = bucket_resource
        return self.get_cache_id(resource)

    def init_ec2lm_s3_bucket(self, resource):
        "Initialize the EC2LM S3 Bucket stack if it does not already exist"
        bucket_config_dict = {
            'enabled': True,
            'bucket_name': 'lb',
            'deletion_policy': 'delete',
            'policy': [ {
                'aws': [ "%s" % (resource._instance_iam_role_arn) ],
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
        bucket = models.applications.S3Bucket('ec2lm', resource)
        bucket.update(bucket_config_dict)
        bucket.resolve_ref_obj = self
        bucket.enabled = resource.is_enabled()

        s3_bucket_ref = bucket.paco_ref_parts
        if s3_bucket_ref in self.ec2lm_buckets.keys():
            return

        s3_ctl = self.paco_ctx.get_controller('S3')
        s3_ctl.init_context(
            self.account_ctx,
            self.aws_region,
            s3_bucket_ref,
            self.stack_group,
            StackTags(self.stack_tags)
        )

        # EC2LM Common Functions StackHooks
        stack_hooks = StackHooks()
        stack_hooks.add(
            name='UploadEC2LMFunctions',
            stack_action='create',
            stack_timing='post',
            hook_method=self.ec2lm_functions_hook,
            cache_method=self.ec2lm_functions_hook_cache_id,
            hook_arg=s3_bucket_ref
        )
        stack_hooks.add(
            name='UploadEC2LMFunctions',
            stack_action='update',
            stack_timing='post',
            hook_method=self.ec2lm_functions_hook,
            cache_method=self.ec2lm_functions_hook_cache_id,
            hook_arg=s3_bucket_ref
        )
        s3_ctl.add_bucket(
            bucket,
            config_ref=s3_bucket_ref,
            stack_hooks=stack_hooks,
            change_protected=resource.change_protected
        )

        # save the bucket to the EC2LaunchManager
        self.ec2lm_buckets[s3_bucket_ref] = bucket
        return bucket

    def get_ec2lm_bucket_name(self, resource):
        "Paco reference to the ec2lm bucket for a resource"
        s3_ctl = self.paco_ctx.get_controller('S3')
        return s3_ctl.get_bucket_name(resource.paco_ref_parts + '.ec2lm')

    def init_ec2lm_function(self, ec2lm_bucket_name, resource, stack_name):
        """Init ec2lm_functions.bash script and add managed policies"""
        oldest_health_check_timeout = 0
        if resource.target_groups != None and len(resource.target_groups) > 0:
            for target_group in resource.target_groups:
                if is_ref(target_group):
                    target_group_obj = self.paco_ctx.get_ref(target_group)
                    health_check_timeout = (target_group_obj.healthy_threshold * target_group_obj.health_check_interval)
                    if oldest_health_check_timeout < health_check_timeout:
                        oldest_health_check_timeout = health_check_timeout

        launch_bundle_names = ' '.join(self.launch_bundle_names)
        if self.paco_ctx.legacy_flag('aim_name_2019_11_28') == True:
            tool_name = 'AIM'
        else:
            tool_name = 'PACO'
        self.ec2lm_functions_script[ec2lm_bucket_name] = f"""INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AVAIL_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
REGION="$(echo \"$AVAIL_ZONE\" | sed 's/[a-z]$//')"
export AWS_DEFAULT_REGION=$REGION
EC2LM_AWS_ACCOUNT_ID="{self.account_ctx.id}"
EC2LM_STACK_NAME=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=aws:cloudformation:stack-name" --query 'Tags[0].Value' |tr -d '"')
EC2LM_FOLDER='{self.paco_base_path}/EC2Manager/'
EC2LM_{tool_name}_NETWORK_ENVIRONMENT="{resource.netenv_name}"
EC2LM_{tool_name}_ENVIRONMENT="{resource.env_name}"
EC2LM_{tool_name}_ENVIRONMENT_REF={resource.env_region_obj.paco_ref_parts}

# Escape a string for sed replacements
function sed_escape() {{
    RES="${{1//$'\\n'/\\\\n}}"
    RES="${{RES//./\\\\.}}"
    RES="${{RES//\\//\\\\/}}"
    RES="${{RES// /\\\\ }}"
    RES="${{RES//!/\\\\!}}"
    RES="${{RES//-/\\\\-}}"
    RES="${{RES//,/\\\\,}}"
    RES="${{RES//&/\\\\&}}"
    echo "${{RES}}"
}}

# Runs another function in a timeout loop.
# ec2lm_timeout <function> <timeout_secs>
#   <function> returns: 0 == success
#                       1 == keep waiting
#                     > 1 == error code and abort
#
# ec2lm_timeout returns: 0 == success
#                        1 == timed out
#                      > 1 == error
function ec2lm_timeout() {{
    TIMEOUT_SECS=$1
    shift
    FUNCTION=$1
    shift

    COUNT=0
    while :
    do
        OUTPUT=$($FUNCTION $@)
        RES=$?
        if [ $RES -eq 0 ] ; then
            echo $OUTPUT
            return $RES
        fi
        if [ $RES -gt 1 ] ; then
            echo "EC2LM: ec2lm_timeout: Function '$FUNCTION' returned an error: $RES: $OUTPUT"
            return $RES
        fi
        if [ $COUNT -eq $TIMEOUT_SECS ] ; then
            echo "EC2LM: ec2lm_timeout: Function '$FUNCTION' timed out after $TIMEOUT_SECS seconds"
            return 1
        fi
        COUNT=$(($COUNT + 1))
        sleep 1
    done

}}

# Launch Bundles
function ec2lm_launch_bundles() {{
    CACHE_ID=$1

    export EC2LM_IGNORE_CACHE=false
    if [ "$CACHE_ID" == "on_launch" ] ; then
        export EC2LM_IGNORE_CACHE=true
    fi

    # Compare new EC2LM contents cache id with existing
    OLD_CACHE_ID=$(<$EC2LM_FOLDER/ec2lm_cache_id.md5)

    if [ "$EC2LM_IGNORE_CACHE" == "false" ] ; then
        if [ "$CACHE_ID" == "$OLD_CACHE_ID" ] ; then
            echo "Cache Id unchanged. Skipping ec2lm_launch_bundles."
            return
        fi
    fi

    # EC2LM Lock file
    EC2LM_LOCK_FILE='/var/lock/paco_ec2lm.lock'
    if [ ! -f $EC2LM_LOCK_FILE ]; then
        :>$EC2LM_LOCK_FILE
    fi
    exec 100>$EC2LM_LOCK_FILE
    echo "EC2LM: LaunchBundles: Obtaining lock."
    flock -n 100
    if [ $? -ne 0 ]  ; then
        echo “[ERROR] EC2LM LaunchBundles: Unable to obtain EC2LM lock.”
        return 1
    fi

    # Synchronize latest bundle contents
    aws s3 sync s3://{ec2lm_bucket_name}/ --region=$REGION $EC2LM_FOLDER

    # Run launch bundles
    mkdir -p $EC2LM_FOLDER/LaunchBundles/
    cd $EC2LM_FOLDER/LaunchBundles/

    echo "EC2LM: LaunchBundles: Loading"
    for BUNDLE_NAME in {launch_bundle_names}
    do
        BUNDLE_FOLDER=$BUNDLE_NAME
        BUNDLE_PACKAGE=$BUNDLE_NAME".tgz"
        BUNDLE_PACKAGE_CACHE_ID=$BUNDLE_PACKAGE".cache"
        if [ ! -f "$BUNDLE_PACKAGE" ] ; then
            echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Skipping missing package: $BUNDLE_PACKAGE"
            continue
        fi
        # Check if this bundle has changed
        NEW_BUNDLE_CACHE_ID=$(md5sum $BUNDLE_PACKAGE | awk '{{print $1}}')
        if [ "$EC2LM_IGNORE_CACHE" == "false" ] ; then
            if [ -f $BUNDLE_PACKAGE_CACHE_ID ] ; then
                OLD_BUNDLE_CACHE_ID=$(cat $BUNDLE_PACKAGE_CACHE_ID)
                if [ "$NEW_BUNDLE_CACHE_ID" == "$OLD_BUNDLE_CACHE_ID" ] ; then
                    echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Skipping unchanged bundle: $BUNDLE_PACKAGE: $NEW_BUNDLE_CACHE_ID == $OLD_BUNDLE_CACHE_ID"
                    continue
                fi
            fi
        fi
        echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Unpacking $BUNDLE_PACKAGE"
        tar xvfz $BUNDLE_PACKAGE
        chown -R root.root $BUNDLE_FOLDER
        echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Launching bundle"
        cd $BUNDLE_FOLDER
        chmod u+x ./launch.sh
        ./launch.sh
        # Save the Bundle Cache ID after launch completion
        echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Saving new cache id: $NEW_BUNDLE_CACHE_ID"
        cd ..
        echo -n "$NEW_BUNDLE_CACHE_ID" >$BUNDLE_PACKAGE_CACHE_ID
        echo "EC2LM: LaunchBundles: $BUNDLE_NAME: Done"
    done
}}

# Instance Tags
function ec2lm_instance_tag_value() {{
    TAG_NAME="$1"
    aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=$TAG_NAME" --query 'Tags[0].Value' |tr -d '"'
}}

# Signal the ASG resource
function ec2lm_signal_asg_resource() {{
    STATUS=$1
    if [ "$STATUS" != "SUCCESS" -a "$STATUS" != "FAILURE" ] ; then
        echo "EC2LM: Signal ASG Resource: Error: Invalid status: $STATUS: Valid values: SUCCESS | FAILURE"
        return 1
    fi
    STACK_STATUS=$(aws cloudformation describe-stacks --stack $EC2LM_STACK_NAME --region $REGION --query "Stacks[0].StackStatus" | tr -d '"')
    echo "EC2LM: Signal ASG Resource: Stack status: $STACK_STATUS"
    if [[ "$STACK_STATUS" == *"PROGRESS" ]]; then
        # ASG Rolling Update
        ASG_LOGICAL_ID=$(ec2lm_instance_tag_value 'aws:cloudformation:logical-id')
        # Sleep to allow ALB healthcheck to succeed otherwise older instances will begin to shutdown
        echo "EC2LM: Signal ASG Resource: Sleeping for {oldest_health_check_timeout} seconds to allow target healthcheck to succeed."
        sleep {oldest_health_check_timeout}
        echo "EC2LM: Signal ASG Resource: Signaling ASG Resource: $EC2LM_STACK_NAME: $ASG_LOGICAL_ID: $INSTANCE_ID: $STATUS"
        aws cloudformation signal-resource --region $REGION --stack $EC2LM_STACK_NAME --logical-resource-id $ASG_LOGICAL_ID --unique-id $INSTANCE_ID --status $STATUS
    else
        echo "EC2LM: Resource Signaling: Not a rolling update: skipping"
    fi
}}

# Swap
function swap_on() {{
    SWAP_SIZE_GB=$1
    if [ -e /swapfile ] ; then
        CUR_SWAP_FILE_SIZE=$(stat -c '%s' /swapfile)
        if [ $CUR_SWAP_FILE_SIZE -eq $(($SWAP_SIZE_GB*1073741824)) ] ; then
            set +e
            OUTPUT=$(swapon /swapfile 2>&1)
            RES=$?
            if [ $RES -eq 0 ] ; then
                echo "EC2LM: Swap: Enabling existing ${{SWAP_SIZE_GB}}GB Swapfile: /swapfile"
            else
                if [[ $OUTPUT == *"Device or resource busy"* ]] ; then
                    echo  "EC2LM: Swap: $OUTPUT"
                elif [[ $RES -ne 0 ]] ; then
                    echo "EC2LM: Swap: Error: $OUTPUT"
                    return 255
                fi
            fi
            set -e
        fi
    fi
    if [ "$(swapon -s|grep -v Filename|wc -c)" == "0" ]; then
        echo "EC2LM: Swap: Enabling a ${{SWAP_SIZE_GB}}GB Swapfile: /swapfile"
        dd if=/dev/zero of=/swapfile bs=1024 count=$(($SWAP_SIZE_GB*1024))k
        chmod 0600 /swapfile
        mkswap /swapfile
        swapon /swapfile
    else
        echo "EC2LM: Swap: Swap already enabled"
    fi
    swapon -s
    free
    echo "EC2LM: Swap: Done"
}}

# Install Wget
function ec2lm_install_wget() {{
    CLIENT_PATH=$(which wget)
    if [ $? -eq 1 ] ; then
        {ec2lm_commands.user_data_script['install_wget'][resource.instance_ami_type_generic]}
    fi
}}

# Install Wget
function ec2lm_install_package() {{
    {ec2lm_commands.user_data_script['install_package'][resource.instance_ami_type_generic]} $1
}}

"""
        if resource.secrets != None and len(resource.secrets) > 0:
            self.ec2lm_functions_script[ec2lm_bucket_name] += self.add_secrets_function_policy(resource)

        # Add a base IAM Managed Policy to allow access to EC2 Tags
        iam_policy_name = '-'.join([resource.name, 'ec2lm'])
        policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:DescribeTags"
    resource:
      - '*'
"""
        # allow cloudformation SignalResource and DescribeStacks if needed
        if resource.rolling_update_policy.wait_on_resource_signals == True:
            policy_config_yaml += f"""

  - effect: Allow
    action:
      - "cloudformation:SignalResource"
      - "cloudformation:DescribeStacks"
    resource:
      - 'arn:aws:cloudformation:{self.aws_region}:{self.account_ctx.id}:stack/{stack_name}/*'
"""
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role=resource.instance_iam_role,
            resource=resource,
            policy_name='policy',
            policy_config_yaml=policy_config_yaml,
            extra_ref_names=['ec2lm','ec2lm'],
        )

    def user_data_script(self, resource, stack_name):
        """BASH script that will load the launch bundle from user_data"""
        if resource.change_protected == True:
            return "#!/bin/bash\n"
        self.init_ec2lm_s3_bucket(resource)
        ec2lm_bucket_name = self.get_ec2lm_bucket_name(resource)

        # EC2LM Functions and Managed Policies
        self.init_ec2lm_function(ec2lm_bucket_name, resource, stack_name)

        # Checks and warnings
        update_packages =''
        if resource.launch_options.update_packages == True:
            update_packages = ec2lm_commands.user_data_script['update_packages'][resource.instance_ami_type_generic]
        if self.paco_ctx.warn:
            if resource.rolling_update_policy != None and \
                resource.rolling_update_policy.wait_on_resource_signals == True and \
                    resource.user_data_script.find('ec2lm_signal_asg_resource') == -1:
                print("WARNING: {}.rolling_update_policy.wait_on_resource_signals == True".format(resource.paco_ref_parts))
                print("'ec2lm_signal_asg_resource <SUCCESS|FAILURE>' was not detected in your user_data_script for this resource.")

        # Newer Ubuntu (>20) does not have Python 2
        if resource.instance_ami_type in ('ubuntu_20', 'amazon_ecs'):
            install_aws_cli = ec2lm_commands.user_data_script['install_aws_cli'][resource.instance_ami_type]
        else:
            install_aws_cli = ec2lm_commands.user_data_script['install_aws_cli'][resource.instance_ami_type_generic]

        # Return UserData script
        return f"""#!/bin/bash
echo "Paco EC2LM: Script: $0"

# Runs pip
function ec2lm_pip() {{
    for PIP_CMD in pip3 pip2 pip
    do
        which $PIP_CMD >/dev/null 2>&1
        if [ $? -eq 0 ] ; then
            $PIP_CMD $@
            return
        fi
    done
}}

{resource.user_data_pre_script}
{update_packages}
{install_aws_cli}

EC2LM_FOLDER='{self.paco_base_path}/EC2Manager/'
EC2LM_FUNCTIONS=ec2lm_functions.bash
mkdir -p $EC2LM_FOLDER/
aws s3 sync s3://{ec2lm_bucket_name}/ --region={resource.region_name} $EC2LM_FOLDER

. $EC2LM_FOLDER/$EC2LM_FUNCTIONS

# Run every Paco EC2LM launch bundle on launch
mkdir -p /var/log/paco
ec2lm_launch_bundles on_launch

"""

    def add_secrets_function_policy(self, resource):
        "Add ec2lm_functions.bash function for Secrets and managed policy to allow access to secrets"
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
        iam_policy_name = '-'.join([resource.name, 'secrets'])
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

        policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    action:
      - secretsmanager:GetSecretValue
    resource:
{secret_arn_list_yaml}
"""
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_managed_policy(
            role=resource.instance_iam_role,
            resource=resource,
            policy_name='policy',
            policy_config_yaml=policy_config_yaml,
            template_params=template_params,
            extra_ref_names=['ec2lm','secrets'],
        )
        return secrets_script

    def add_bundle(self, bundle):
        "Build and add a bundle to the ec2lm S3 Bucket"
        bundle.build()
        if bundle.bucket_ref not in self.launch_bundles:
            self.init_ec2lm_s3_bucket(bundle.resource)
            self.launch_bundles[bundle.bucket_ref] = []
        # Add the bundle to the S3 Context ID bucket
        self.add_bundle_to_s3_bucket(bundle)
        self.launch_bundles[bundle.bucket_ref].append(bundle)

    def lb_add_cfn_init(self, bundle_name, resource):
        """Launch bundle to install and run cfn-init configsets"""
        cfn_init_lb = LaunchBundle(resource, self, bundle_name)

        cfn_init_enabled = True
        if resource.cfn_init == None or len(resource.launch_options.cfn_init_config_sets) == 0:
            cfn_init_enabled = False

        # cfn-init base path
        if resource.instance_ami_type_generic in ['amazon', 'centos']:
            # Amazon Linux and CentOS have cfn-init pre-installed at /opt/aws/
            cfn_base_path = '/opt/aws'
        else:
            # other OS types will install cfn-init into the Paco directory
            cfn_base_path = self.paco_base_path

        if resource.instance_ami_type in ec2lm_commands.user_data_script['install_cfn_init']:
            install_cfn_init_command = ec2lm_commands.user_data_script['install_cfn_init'][resource.instance_ami_type]
        else:
            install_cfn_init_command = ec2lm_commands.user_data_script['install_cfn_init'][resource.instance_ami_type_generic]
        install_cfn_init_command = install_cfn_init_command.format(cfn_base_path=cfn_base_path)

        config_sets_str = ','.join(resource.launch_options.cfn_init_config_sets)
        launch_script = f"""#!/bin/bash
. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

function run_launch_configuration() {{
    {cfn_base_path}/bin/cfn-init --stack=$EC2LM_STACK_NAME --resource=LaunchConfiguration --region=$REGION --configsets={config_sets_str}
}}

function run_launch_bundle() {{
    # cfn-init configsets are only run by Paco during initial launch
    if [[ ! -f ./initialized-configsets.txt  || "$EC2LM_IGNORE_CACHE" == "true" ]]; then
        {install_cfn_init_command}
        echo "{config_sets_str}" >> ./initialized-configsets.txt
        run_launch_configuration
        {cfn_base_path}/bin/cfn-signal -e $? --stack $EC2LM_STACK_NAME --resource=LaunchConfiguration --region=$REGION
    fi
}}

function disable_launch_bundle() {{
    # touch the initialized-configsets.txt file to prevent a later addition
    # of a cfn-init ConfigSet from running unexpectedly
    touch ./initialized-configsets.txt
}}

# enable local running of launch configset with:
# $EC2LM_FOLDER/LaunchBundles/cfn-init/launch.sh run
RUN_LAUNCH_CFN=$1
if [ "$RUN_LAUNCH_CFN" == "run" ] ; then
    run_launch_configuration
fi

"""
        cfn_init_lb.set_launch_script(launch_script, cfn_init_enabled)
        self.add_bundle(cfn_init_lb)

    def lb_add_efs(self, bundle_name, resource):
        """Launch bundle to configure and mount EFS"""
        efs_lb = LaunchBundle(resource, self, bundle_name)

        efs_enabled = False
        if len(resource.efs_mounts) >= 0:
            process_mount_targets = ""
            for efs_mount in resource.efs_mounts:
                if efs_mount.enabled == False:
                    continue
                efs_enabled = True
                if is_ref(efs_mount.target) == True:
                    stack = resolve_ref(efs_mount.target, self.paco_ctx.project, self.account_ctx)
                    efs_stack_name = stack.get_name()
                else:
                    # ToDo: Paco EC2LM does not yet support string EFS Ids
                    raise AttributeError('String EFS Id values not yet supported by EC2LM')
                process_mount_targets += "process_mount_target {} {}\n".format(efs_mount.folder, efs_stack_name)

        # ToDo: add other unsupported OSes here (Suse? CentOS 6)
        if resource.instance_ami_type in ['ubuntu_14',]:
            raise AttributeError(f"OS type {resource.instance_ami_type} does not support EFS")
        install_efs_utils = ec2lm_commands.user_data_script['install_efs_utils'][resource.instance_ami_type_generic]
        mount_efs = ec2lm_commands.user_data_script['mount_efs'][resource.instance_ami_type_generic]
        if resource.instance_ami_type in ['ubuntu_16', 'ubuntu_20']:
            install_efs_utils = ec2lm_commands.user_data_script['install_efs_utils'][resource.instance_ami_type]
            mount_efs = ec2lm_commands.user_data_script['mount_efs'][resource.instance_ami_type]

        launch_script = f"""#!/bin/bash

. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash
EFS_MOUNT_FOLDER_LIST=./efs_mount_folder_list
EFS_ID_LIST=./efs_id_list

function process_mount_target()
{{
    MOUNT_FOLDER=$1
    EFS_STACK_NAME=$2

    # Get EFS ID from Tag
    EFS_ID=$(aws efs describe-file-systems --region $REGION --no-paginate --query "FileSystems[].{{Tags: Tags[?Key=='Paco-Stack-Name'].Value, FileSystemId: FileSystemId}} | [].{{stack: Tags[0], fs: FileSystemId}} | [?stack=='$EFS_STACK_NAME'].fs | [0]" | tr -d '"')

    # Setup the mount folder
    if [ -e $MOUNT_FOLDER ] ; then
        mv $MOUNT_FOLDER ${{MOUNT_FOLDER%%/}}.old
    fi
    mkdir -p $MOUNT_FOLDER

    # Setup fstab
    grep -v -E "^$EFS_ID:/" /etc/fstab >/tmp/fstab.efs_new
    echo "$EFS_ID:/ $MOUNT_FOLDER efs defaults,_netdev,fsc 0 0" >>/tmp/fstab.efs_new
    mv /tmp/fstab.efs_new /etc/fstab
    chmod 0664 /etc/fstab
    echo "$MOUNT_FOLDER" >>$EFS_MOUNT_FOLDER_LIST".new"
    echo "$EFS_ID" >>$EFS_ID_LIST".new"
}}

function run_launch_bundle() {{
    # Install EFS Utils
    {install_efs_utils}
    # Enable EFS Utils
    {ec2lm_commands.user_data_script['enable_efs_utils'][resource.instance_ami_type_generic]}

    # Process Mounts
    :>$EFS_MOUNT_FOLDER_LIST".new"
    :>$EFS_ID_LIST".new"
    {process_mount_targets}
    mv $EFS_MOUNT_FOLDER_LIST".new" $EFS_MOUNT_FOLDER_LIST
    mv $EFS_ID_LIST".new" $EFS_ID_LIST

    # Mount EFS folders
    {mount_efs}
}}

function disable_launch_bundle() {{
    # Remove them if they exist
    if [ -e "$EFS_MOUNT_FOLDER_LIST" ] ; then
        for MOUNT_FOLDER in $(cat $EFS_MOUNT_FOLDER_LIST)
        do
            umount $MOUNT_FOLDER
        done
        rm $EFS_MOUNT_FOLDER_LIST
    fi
    if [ -e "$EFS_ID_LSIT" ] ; then
        for EFS_ID in $(cat $EFS_ID_LIST)
        do
            grep -v -E "^$EFS_ID:/" /etc/fstab >/tmp/fstab.efs_new
            mv /tmp/fstab.efs_new /etc/fstab
            chmod 0664 /etc/fstab
        done
        rm $EFS_ID_LIST
    fi
}}
"""
        efs_lb.set_launch_script(launch_script, efs_enabled)
        self.add_bundle(efs_lb)

        # IAM Managed Policy to allow EFS
        if efs_enabled:
            iam_policy_name = '-'.join([resource.name, 'efs'])
            policy_config_yaml = """
policy_name: '{}'
enabled: true
statement:
  - effect: Allow
    action:
      - 'elasticfilesystem:DescribeFileSystems'
    resource:
      - '*'
""".format(iam_policy_name)
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','efs'],
            )

    def lb_add_ebs(self, bundle_name, resource):
        """Launch bundle to configure and mount EBS Volumes"""
        ebs_lb = LaunchBundle(resource, self, bundle_name)

        # is EBS enabled? if yes, create process_volume_mount commands
        ebs_enabled = False
        process_mount_volumes = ""
        for ebs_volume_mount in resource.ebs_volume_mounts:
            if ebs_volume_mount.enabled == False:
                continue
            ebs_enabled = True
            ebs_stack = resolve_ref(ebs_volume_mount.volume, self.paco_ctx.project, self.account_ctx)
            ebs_stack_name = ebs_stack.get_name()
            process_mount_volumes += "process_volume_mount {} {} {} {}\n".format(
                ebs_volume_mount.folder,
                ebs_stack_name,
                ebs_volume_mount.filesystem,
                ebs_volume_mount.device
            )

        launch_script = f"""#!/bin/bash

. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

EBS_MOUNT_FOLDER_LIST=ebs_mount_folder_list
EBS_VOLUME_UUID_LIST=ebs_volume_uuid_list

# Attach EBS Volume
function ec2lm_attach_ebs_volume() {{
    EBS_VOLUME_ID=$1
    EBS_DEVICE=$2

    aws ec2 attach-volume --region $REGION --volume-id $EBS_VOLUME_ID --instance-id $INSTANCE_ID --device $EBS_DEVICE 2>/tmp/ec2lm_attach.output
    RES=$?
    if [ $? -eq 0 ] ; then
        echo "EC2LM: EBS: Successfully attached $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE"
        return 0
    fi
    return 1
}}

# Checks if a volume has been attached
# ec2lm_volume_is_attached <device>
# Return: 0 == True
#         1 == False
function ec2lm_volume_is_attached() {{
    DEVICE=$1
    OUTPUT=$(file -s $DEVICE)
    if [[ $OUTPUT == *"No such file or directory"* ]] ; then
        return 1
    fi
    return 0
}}

# Checks if a volume has been attached
# ec2lm_volume_is_attached <device>
# Return: 0 == True
#         1 == False
function ec2lm_get_volume_uuid() {{
    EBS_DEVICE=$1
    VOLUME_UUID=$(/sbin/blkid $EBS_DEVICE |grep UUID |cut -d'"' -f 2)
    if [ "${{VOLUME_UUID}}" != "" ] ; then
        echo $VOLUME_UUID
        return 0
    fi
    return 1
}}

# Attach and Mount an EBS Volume
function process_volume_mount()
{{
    MOUNT_FOLDER=$1
    EBS_STACK_NAME=$2
    FILESYSTEM=$3
    EBS_DEVICE=$4

    echo "EC2LM: EBS: Process Volume Mount: Begin"

    # Get EBS Volume Id
    EBS_VOLUME_ID=$(aws ec2 describe-volumes --filters Name=tag:aws:cloudformation:stack-name,Values=$EBS_STACK_NAME --query "Volumes[*].VolumeId | [0]" --region $REGION | tr -d '"')

    # Setup the mount folder
    if [ -e $MOUNT_FOLDER ] ; then
        mv $MOUNT_FOLDER ${{MOUNT_FOLDER%%/}}.old
    fi
    mkdir -p $MOUNT_FOLDER

    TIMEOUT_SECS=300
    echo "EC2LM: EBS: Attaching $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE: Timeout = $TIMEOUT_SECS"
    OUTPUT=$(ec2lm_timeout $TIMEOUT_SECS ec2lm_attach_ebs_volume $EBS_VOLUME_ID $EBS_DEVICE)
    if [ $? -eq 1 ] ; then
        echo "[ERROR] EC2LM: EBS: Unable to attach $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE"
        echo "[ERROR] EC2LM: EBS: $OUTPUT"
        cat /tmp/ec2lm_attach.output
        exit 1
    fi

    # Initialize filesystem if blank
    echo "EC2LM: EBS: Waiting for volume to become available: $EBS_DEVICE"
    TIMEOUT_SECS=30
    OUTPUT=$(ec2lm_timeout $TIMEOUT_SECS ec2lm_volume_is_attached $EBS_DEVICE)
    if [ $? -eq 1 ] ; then
        echo "EC2LM: EBS: Error: Unable to detect the attached volume $EBS_VOLUME_ID to $INSTANCE_ID as $EBS_DEVICE."
        echo "[ERROR] EC2LM: EBS: $OUTPUT"
        exit 1
    fi

    # Format: Make a filesystem if the device
    FILE_FMT=$(file -s $EBS_DEVICE)
    BLANK_FMT="$EBS_DEVICE: data"
    if [ "$FILE_FMT" == "$BLANK_FMT" ] ; then
        echo "EC2LM: EBS: Initializing EBS Volume with FS type $FILESYSTEM"
        /sbin/mkfs -t $FILESYSTEM $EBS_DEVICE
    fi

    # Setup fstab
    echo "EC2LM: EBS: Getting Volume UUID for $EBS_DEVICE"
    TIMEOUT_SECS=30
    VOLUME_UUID=$(ec2lm_timeout $TIMEOUT_SECS ec2lm_get_volume_uuid $EBS_DEVICE)
    if [ $? -eq 1 ] ; then
        echo "[ERROR] EC2LM: EBS: Unable to get volume UUID for $EBS_DEVICE"
        echo "[ERROR] EC2LM: EBS: Error: $OUTPUT"
        /sbin/blkid
        exit 1
    fi

    # /etc/fstab entry
    echo "EC2LM: EBS: $EBS_DEVICE UUID: $VOLUME_UUID"
    FSTAB_ENTRY="UUID=$VOLUME_UUID $MOUNT_FOLDER $FILESYSTEM defaults,nofail 0 2"
    echo "EC2LM: EBS: Configuring /etc/fstab: $FSTAB_ENTRY"
    grep -v -E "^UUID=$VOLUME_UUID" /etc/fstab >/tmp/fstab.ebs_new
    echo $FSTAB_ENTRY >>/tmp/fstab.ebs_new
    mv /tmp/fstab.ebs_new /etc/fstab
    chmod 0664 /etc/fstab

    # Mount Volume
    echo "EC2LM: EBS: Mounting $MOUNT_FOLDER"
    mount $MOUNT_FOLDER
    echo "$MOUNT_FOLDER" >>$EBS_MOUNT_FOLDER_LIST".new"
    echo "$VOLUME_UUID" >>$EBS_VOLUME_UUID_LIST".new"
    echo "EC2LM: EBS: Process Volume Mount: Done"

    return 0
}}

function run_launch_bundle()
{{
    # Process Mounts
    :>$EBS_MOUNT_FOLDER_LIST".new"
    :>$EBS_VOLUME_UUID_LIST".new"
    {process_mount_volumes}
    mv $EBS_MOUNT_FOLDER_LIST".new" $EBS_MOUNT_FOLDER_LIST
    mv $EBS_VOLUME_UUID_LIST".new" $EBS_VOLUME_UUID_LIST
}}

# Remove any previous mounts that existed
function disable_launch_bundle()
{{
    if [ "$EFS_MOUNT_FOLDER_LIST" != "" ] ; then
        for MOUNT_FOLDER in $(cat $EBS_MOUNT_FOLDER_LIST)
        do
            umount $MOUNT_FOLDER
        done

        for VOLUME_UUID in $(cat $EBS_VOLUME_UUID_LIST)
        do
            grep -v -E "^UUID=$VOLUME_UUID" /etc/fstab >/tmp/fstab.ebs_new
            mv /tmp/fstab.ebs_new /etc/fstab
        done
    fi
}}
"""
        ebs_lb.set_launch_script(launch_script, ebs_enabled)
        self.add_bundle(ebs_lb)

        # IAM Managed Policy to allow attaching volumes
        if ebs_enabled:
            iam_policy_name = '-'.join([resource.name, 'ebs'])
            policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    action:
      - "ec2:AttachVolume"
    resource:
      - 'arn:aws:ec2:*:*:volume/*'
      - 'arn:aws:ec2:*:*:instance/*'
  - effect: Allow
    action:
      - "ec2:DescribeVolumes"
    resource:
      - "*"
"""
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','ebs'],
            )

    def lb_add_eip(self, bundle_name, resource):
        """Creates a launch bundle to configure Elastic IPs"""
        # Create the Launch Bundle and configure it
        eip_lb = LaunchBundle(resource, self, bundle_name)

        enabled = True
        if resource.eip == None:
            enabled = False

        # get the EIP Stack Name
        eip_alloc_id = ''
        eip_stack_name = ''
        if is_ref(resource.eip) == True:
            eip_stack = resolve_ref(resource.eip, self.paco_ctx.project, self.account_ctx)
            eip_stack_name = eip_stack.get_name()
        elif resource.eip != None:
            eip_alloc_id = resource.eip

        launch_script = f"""#!/bin/bash

. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

EIP_STATE_FILE=$EC2LM_FOLDER/LaunchBundles/EIP/eip-association-id.txt

function ec2lm_eip_is_associated() {{
    EIP_IP=$1
    EIP_ALLOC_ID=$2
    PUBLIC_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4/)
    if [ "$PUBLIC_IP" == "$EIP_IP" ] ; then
        echo "EC2LM: EIP: Association Successful"
        # save association id to allow later disassociation
        EIP_ASSOCIATION_ID=$(aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID --query 'Addresses[0].AssociationId' --region $REGION | tr -d '"')
        echo "$EIP_ASSOCIATION_ID" > $EIP_STATE_FILE
        return 0
    fi
    return 1
}}

function run_launch_bundle()
{{
    # Allocation ID
    EIP_ALLOCATION_EC2_TAG_KEY_NAME="Paco-EIP-Allocation-Id"
    echo "EC2LM: EIP: Getting Allocation ID from EIP matching stack: {eip_stack_name}"
    EIP_ALLOC_ID=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-type,Values=elastic-ip" "Name=tag:aws:cloudformation:stack-name,Values={eip_stack_name}" --query 'Tags[0].ResourceId' |tr -d '"')
    if [ "$EIP_ALLOC_ID" == "null" ] ; then
        EIP_ALLOC_ID=$(aws ec2 describe-tags --region $REGION --filter "Name=resource-type,Values=elastic-ip" "Name=tag:Paco-Stack-Name,Values={eip_stack_name}" --query 'Tags[0].ResourceId' |tr -d '"')
        if [ "$EIP_ALLOC_ID" == "null" ] ; then
            echo "EC2LM: EIP: ERROR: Unable to get EIP Allocation ID"
            exit 1
        fi
    fi

    # IP Address
    echo "EC2LM: EIP: Getting IP Address for $EIP_ALLOC_ID"
    EIP_IP=$(aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID --query 'Addresses[0].PublicIp' --region $REGION | tr -d '"')

    # Association
    echo "EC2LM: EIP: Assocating $EIP_ALLOC_ID - $EIP_IP"
    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $EIP_ALLOC_ID --region $REGION

    # Wait for Association
    TIMEOUT_SECS=300
    OUTPUT=$(ec2lm_timeout $TIMEOUT_SECS ec2lm_eip_is_associated $EIP_IP $EIP_ALLOC_ID)
    RES=$?
    if [ $RES -lt 2 ] ; then
        echo "$OUTPUT"
    else
        echo "EC2LM: EIP: Error: $OUTPUT"
    fi
}}

function disable_launch_bundle()
{{
    if [ -e $EIP_STATE_FILE ] ; then
        EIP_ASSOCIATION_ID=$(<$EIP_STATE_FILE)
        aws ec2 disassociate-address --association-id $EIP_ASSOCIATION_ID --region $REGION
    fi
}}
"""
        eip_lb.set_launch_script(launch_script, enabled)
        self.add_bundle(eip_lb)

        # IAM Managed Policy to allow EIP
        if enabled:
            iam_policy_name = '-'.join([resource.name, 'eip'])
            policy_config_yaml = """
policy_name: '{}'
enabled: true
statement:
  - effect: Allow
    action:
      - 'ec2:AssociateAddress'
      - 'ec2:DisassociateAddress'
      - 'ec2:DescribeAddresses'
    resource:
      - '*'
""".format(iam_policy_name)
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','eip'],
            )

    def lb_add_cloudwatchagent(self, bundle_name, resource):
        """Creates a launch bundle to install and configure a CloudWatch Agent:

         - Adds a launch script to install the agent

         - Adds a CW Agent JSON configuration file for the agent

         - Adds an IAM Policy to the instance IAM role that will allow the agent
           to do what it needs to do (e.g. send metrics and logs to CloudWatch)
        """
        cw_lb = LaunchBundle(resource, self, bundle_name)

        # is the cloudwatchagent bundle enabled?
        monitoring = resource.monitoring
        cw_enabled = True
        if monitoring == None or monitoring.enabled == False:
            cw_enabled = False

        # Launch script
        agent_path = ec2lm_commands.cloudwatch_agent[resource.instance_ami_type_generic]['path']
        if resource.instance_ami_type_family == 'redhat':
            agent_object = 'amazon-cloudwatch-agent.rpm'
            install_command = f'rpm -U {agent_object}'
            installed_command = 'rpm -q amazon-cloudwatch-agent'
            uninstall_command = 'rpm -e amazon-cloudwatch-agent'
        elif resource.instance_ami_type_family == 'debian':
            agent_object = 'amazon-cloudwatch-agent.deb'
            install_command = f'dpkg -i -E {agent_object}'
            installed_command = 'dpkg --status amazon-cloudwatch-agent'
            uninstall_command = 'dpkg -P amazon-cloudwatch-agent'
        launch_script = f"""#!/bin/bash
echo "EC2LM: CloudWatch: Begin"
. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

function run_launch_bundle() {{
    LB_DIR=$(pwd)
    $({installed_command} &> /dev/null)
    RES=$?
    if [[ $RES -ne 0 ]]; then
        # Download the agent
        mkdir /tmp/paco/
        cd /tmp/paco/
        ec2lm_install_wget # built in function

        echo "EC2LM: CloudWatch: Downloading agent"
        wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent{agent_path}/{agent_object}
        wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent{agent_path}/{agent_object}.sig

        # Verify the agent
        echo "EC2LM: CloudWatch: Downloading and importing agent GPG key"
        TRUSTED_FINGERPRINT=$(echo "9376 16F3 450B 7D80 6CBD 9725 D581 6730 3B78 9C72" | tr -d ' ')
        wget -nv https://s3.amazonaws.com/amazoncloudwatch-agent/assets/amazon-cloudwatch-agent.gpg
        gpg --import amazon-cloudwatch-agent.gpg

        echo "EC2LM: CloudWatch: Verify agent signature"
        KEY_ID="$(gpg --list-packets amazon-cloudwatch-agent.gpg 2>&1 | awk '/keyid:/{{ print $2 }}' | tr -d ' ')"
        FINGERPRINT="$(gpg --fingerprint ${{KEY_ID}} 2>&1 | tr -d ' ')"
        OBJECT_FINGERPRINT="$(gpg --verify {agent_object}.sig {agent_object} 2>&1 | tr -d ' ')"
        if [[ ${{FINGERPRINT}} != *${{TRUSTED_FINGERPRINT}}* || ${{OBJECT_FINGERPRINT}} != *${{TRUSTED_FINGERPRINT}}* ]]; then
            # Log error here
            echo "[ERROR] CloudWatch Agent signature invalid: ${{KEY_ID}}: ${{OBJECT_FINGERPRINT}}"
            exit 1
        fi

        # Install the agent
        echo "EC2LM: CloudWatch: Installing agent: {install_command}"
        {install_command}
    fi

    cd ${{LB_DIR}}
    echo "EC2LM: CloudWatch: Updating configuration"
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:amazon-cloudwatch-agent.json -s
    echo "EC2LM: CloudWatch: Done"
}}

function disable_launch_bundle() {{
    $({installed_command} &> /dev/null)
    if [[ $? -eq 0 ]]; then
        {uninstall_command}
    fi
}}
"""
        if cw_enabled:
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
                        #"ImageId": "${aws:ImageId}",
                        #"InstanceId": "${aws:InstanceId}",
                        #"InstanceType": "${aws:InstanceType}",
                        "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
                    },
                    "aggregation_dimensions" : [["AutoScalingGroupName"]]
                }
                collected = agent_config['metrics']['metrics_collected']
                for metric in monitoring.metrics:
                    if metric.collection_interval:
                        interval = metric.collection_interval
                    else:
                        interval = monitoring.collection_interval
                    collected[metric.name] = {
                        "measurement": metric.measurements,
                        "collection_interval": interval,
                    }
                    if metric.resources and len(metric.resources) > 0:
                        collected[metric.name]['resources'] = metric.resources
                    if metric.name == 'disk':
                        collected[metric.name]['drop_device'] = metric.drop_device

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
                    prefixed_log_group_name = prefixed_name(resource, log_group.get_full_log_group_name(), self.paco_ctx.legacy_flag)
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
            cw_lb.add_file('amazon-cloudwatch-agent.json', agent_config)

            # Create instance managed policy for the agent
            iam_policy_name = '-'.join([resource.name, 'cloudwatchagent'])
            policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
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
                # allow a logs:CreateLogGroup action
                policy_config_yaml += """      - "logs:CreateLogGroup"\n"""
                log_group_resources = ""
                log_stream_resources = ""
                for log_group in monitoring.log_sets.get_all_log_groups():
                    lg_name = prefixed_name(resource, log_group.get_full_log_group_name(), self.paco_ctx.legacy_flag)
                    log_group_resources += "      - arn:aws:logs:{}:{}:log-group:{}:*\n".format(
                        self.aws_region,
                        self.account_ctx.id,
                        lg_name,
                    )
                    log_stream_resources += "      - arn:aws:logs:{}:{}:log-group:{}:log-stream:*\n".format(
                        self.aws_region,
                        self.account_ctx.id,
                        lg_name,
                    )
                policy_config_yaml += f"""
  - effect: Allow
    action:
      - "logs:DescribeLogStreams"
      - "logs:DescribeLogGroups"
      - "logs:CreateLogStream"
    resource:
{log_group_resources}
  - effect: Allow
    action:
      - "logs:PutLogEvents"
    resource:
{log_stream_resources}
"""
            policy_name = 'policy_ec2lm_cloudwatchagent'
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','cloudwatchagent'],
            )

        # Set the launch script
        cw_lb.set_launch_script(launch_script, cw_enabled)
        self.add_bundle(cw_lb)

    def add_update_instance_ssm_document(self):
        "Add paco_ec2lm_update_instance SSM Document to the model"
        ssm_documents = self.paco_ctx.project['resource']['ssm'].ssm_documents
        if 'paco_ec2lm_update_instance' not in ssm_documents:
            ssm_doc = SSMDocument('paco_ec2lm_update_instance', ssm_documents)
            ssm_doc.add_location(self.account_ctx.paco_ref, self.aws_region)
            content = {
                "schemaVersion": "2.2",
                "description": "Paco EC2 LaunchManager update instance state",
                "parameters": {
                    "CacheId": {
                        "type": "String",
                        "description": "EC2LM Cache Id"
                    }
                },
                "mainSteps": [
                    {
                        "action": "aws:runShellScript",
                        "name": "updateEC2LMInstance",
                        "inputs": {
                            "runCommand": [
                                '#!/bin/bash',
                                f'. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash',
                                'ec2lm_launch_bundles ' + '{{CacheId}}',
                            ]
                        }
                    }
                ]
            }
            ssm_doc.content = json.dumps(content)
            ssm_doc.document_type = 'Command'
            ssm_doc.enabled = True
            ssm_documents['paco_ec2lm_update_instance'] = ssm_doc
        else:
            ssm_documents['paco_ec2lm_update_instance'].add_location(
                self.account_ctx.paco_ref,
                self.aws_region,
            )

    def lb_add_sshaccess(self, bundle_name, resource):
        "SSH Access Bundle"
        ssh_lb = LaunchBundle(resource, self, bundle_name)
        ssh_access = resource.ssh_access
        launch_script = f"""#!/bin/bash
echo "EC2LM: SSHAccess: Begin"
. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash
"""
        ssh_enabled = False
        auth_key_file = ec2lm_commands.default_user[resource.instance_ami_type_generic] + '/.ssh/authorized_keys'
        auth_key_contents=''
        if len(ssh_access.users) > 0 or len(ssh_access.groups) > 0:
            ssh_enabled = True
            public_keys = {}
            public_keys_user = {}
            project = get_parent_by_interface(resource)
            ec2_users = project.resource['ec2'].users
            ec2_groups = project.resource['ec2'].groups
            for username in ssh_access.users:
                public_keys[ec2_users[username].public_ssh_key] = True
                public_keys_user[ec2_users[username].public_ssh_key] = username
            for groupname in ssh_access.groups:
                group = ec2_groups[groupname]
                for username in group.members:
                    public_keys[ec2_users[username].public_ssh_key] = True
                    public_keys_user[ec2_users[username].public_ssh_key] = username

            key_lines = ['# Autogenerated by Paco - do not edit after this line',]
            idx = 0
            for public_key in public_keys.keys():
                key_lines.append(f'{public_key} {public_keys_user[public_key]}')
                idx += 1
            auth_key_contents = "\n".join(key_lines)

        launch_script += f"""
AUTH_KEY_FILE={auth_key_file}
AUTH_CONTENTS='{auth_key_contents}'

function run_launch_bundle() {{
    # Remove everything after '# Autogenerated by Paco'
    sed -i '/# Autogenerated by Paco - do not edit after this line/Q' $AUTH_KEY_FILE
    # append Paco public keys
    echo -e "$AUTH_CONTENTS" >> $AUTH_KEY_FILE
}}

function disable_launch_bundle() {{
    # Remove everything after '# Autogenerated by Paco'
    sed -i '/# Autogenerated by Paco - do not edit after this line/Q' $AUTH_KEY_FILE
}}
"""
        ssh_lb.set_launch_script(launch_script, ssh_enabled)
        self.add_bundle(ssh_lb)

    def lb_add_ecs(self, bundle_name, resource):
        "ECS Launch Bundle"
        ecs_lb = LaunchBundle(resource, self, bundle_name)
        ecs = resource.ecs
        launch_script = ""

        # is the ECS bundle enabled?
        ecs_enabled = False
        if ecs != None:
            ecs_enabled = True
            # ECS Policy
            iam_policy_name = '-'.join([resource.name, 'ecs'])
            policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
path: /
statement:
  - effect: Allow
    action:
      - 'ecs:CreateCluster'
      - 'ecs:DeregisterContainerInstance'
      - 'ecs:DiscoverPollEndpoint'
      - 'ecs:Poll'
      - 'ecs:RegisterContainerInstance'
      - 'ecs:StartTelemetrySession'
      - 'ecs:Submit*'
      - 'logs:CreateLogStream'
      - 'logs:PutLogEvents'
      - 'ecr:GetAuthorizationToken'
      - 'ecr:BatchCheckLayerAvailability'
      - 'ecr:GetDownloadUrlForLayer'
      - 'ecr:GetRepositoryPolicy'
      - 'ecr:DescribeRepositories'
      - 'ecr:ListImages'
      - 'ecr:DescribeImages'
      - 'ecr:BatchGetImage'
      - 'ecr:GetLifecyclePolicy'
      - 'ecr:GetLifecyclePolicyPreview'
      - 'ecr:ListTagsForResource'
      - 'ecr:DescribeImageScanFindings'
    resource:
      - '*'
"""
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','ecs'],
            )

            launch_script = f"""#!/bin/bash
echo "EC2LM: ECS: Begin"
. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

function run_launch_bundle() {{
    mkdir -p /etc/ecs/
    CLUSTER_NAME=$(ec2lm_instance_tag_value 'Paco-ECSCluster-Name')
    echo ECS_CLUSTER=$CLUSTER_NAME > /etc/ecs/ecs.config
    echo ECS_LOGLEVEL={ecs.log_level} >> /etc/ecs/ecs.config

    # restart the ecs service to reload the new config
    # do not do this on initial launch or ecs just hangs
    if [ "$EC2LM_IGNORE_CACHE" != "true" ] ; then
        systemctl restart ecs.service
    fi
}}

function disable_launch_bundle() {{
    rm -f /etc/ecs/ecs.config
}}
"""
        ecs_lb.set_launch_script(launch_script, ecs_enabled)
        self.add_bundle(ecs_lb)

    def lb_add_ssm(self, bundle_name, resource):
        """Creates a launch bundle to install and configure the SSM agent"""
        # Create the Launch Bundle
        ssm_lb = LaunchBundle(resource, self, bundle_name)
        ssm_enabled = True
        if not resource.launch_options.ssm_agent:
            ssm_enabled = False

        # Install SSM Agent - except where it is pre-baked in the image
        download_url = ''
        agent_install = ''
        agent_object = ''
        download_command = 'wget -nv'
        if resource.instance_ami_type_family == 'redhat':
            installed_command = 'rpm -q amazon-ssm-agent'
        elif resource.instance_ami_type_family == 'debian':
            installed_command = 'dpkg --status amazon-ssm-agent'
        if resource.instance_ami_type_generic != 'amazon':
            agent_config = ec2lm_commands.ssm_agent[resource.instance_ami_type]
            agent_install = agent_config["install"]
            agent_object = agent_config["object"]
            if resource.instance_ami_type not in ('ubuntu_16_snap', 'ubuntu_18', 'ubuntu_20'):            # use regional URL for faster download
                if self.aws_region in ec2lm_commands.ssm_regions:
                    download_url = f'https://s3.{self.aws_region}.amazonaws.com/amazon-ssm-{self.aws_region}/latest'
                else:
                    download_url = f'https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest'
                download_url += f'{agent_config["path"]}/{agent_config["object"]}'
            else:
                installed_command = 'snap list amazon-ssm-agent'
                download_command = ""
                download_url = ""

        launch_script = f"""#!/bin/bash

echo "EC2LM: SSM Agent: Begin"

$({installed_command} &> /dev/null)
if [[ $? -eq 0 ]]; then
    SSM_INSTALLED=true
else
    SSM_INSTALLED=false
fi

echo "EC2LM: SSM Agent: End"

function run_launch_bundle() {{
    if [ "$SSM_INSTALLED" == "false" ] ; then
        # Load EC2 Launch Manager helper functions
        . {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

        # Download the agent
        LB_DIR=$(pwd)
        mkdir /tmp/paco/
        cd /tmp/paco/
        # ensure wget is installed
        ec2lm_install_wget

        echo "EC2LM: SSM: Downloading agent"
        {download_command} {download_url}

        # Install the agent
        echo "EC2LM: SSM: Installing agent: {agent_install} {agent_object}"
        {agent_install} {agent_object}
    fi
}}

function disable_launch_bundle() {{
    # No-op: Paco will not remove SSM agent
    :
}}
"""
        ssm_lb.set_launch_script(launch_script, ssm_enabled)
        self.add_bundle(ssm_lb)

        if ssm_enabled:
            # Create instance managed policy for the agent
            iam_policy_name = '-'.join([resource.name, 'ssmagent-policy'])
            ssm_prefixed_name = prefixed_name(resource, 'paco_ssm', self.paco_ctx.legacy_flag)
            # allows instance to create a LogGroup with any name - this is a requirement of the SSM Agent
            # if you limit the resource to just the LogGroups names you want SSM to use, the agent will not work
            ssm_log_group_arn = f"arn:aws:logs:{self.aws_region}:{self.account_ctx.id}:log-group:*"
            ssm_log_stream_arn = f"arn:aws:logs:{self.aws_region}:{self.account_ctx.id}:log-group:{ssm_prefixed_name}:log-stream:*"
            policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
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
      - ssm:DescribeInstanceProperties
      - ssm:DescribeDocumentParameters
    resource:
      - '*'
  - effect: Allow
    action:
      - s3:GetEncryptionConfiguration
    resource:
      - '*'
  - effect: Allow
    action:
      - logs:CreateLogGroup
      - logs:CreateLogStream
      - logs:DescribeLogGroups
      - logs:DescribeLogStreams
    resource:
      - {ssm_log_group_arn}
  - effect: Allow
    action:
      - logs:PutLogEvents
    resource:
      - {ssm_log_stream_arn}
"""
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','ssmagent'],
            )

    def lb_add_scriptmanager(self, bundle_name, resource):
        "EC2 Script Manager Launch Bundle"
        script_lb = LaunchBundle(resource, self, bundle_name)
        launch_script = ""
        scripts = {}
        script_manager_enabled = False
        # ECS Release Phase Script
        if resource.script_manager and resource.script_manager.ecr_deploy and len(resource.script_manager.ecr_deploy) > 0:
            ecr_deploy_script = ECR_DEPLOY_SCRIPT_HEAD.format(
                paco_base_path=self.paco_base_path,
                ecr_deploy_list=' '.join(resource.script_manager.ecr_deploy.keys())
            )
            ecr_deploy_idx = 0
            for ecr_deploy_name in resource.script_manager.ecr_deploy.keys():
                ecr_deploy = resource.script_manager.ecr_deploy[ecr_deploy_name]
                repo_idx = 0
                for repository in ecr_deploy.repositories:
                    # ECR Deploy Script
                    # ECS Relase Phase Script
                    source_ecr_obj = get_model_obj_from_ref(repository.source_repo, self.paco_ctx.project)
                    source_env = get_parent_by_interface(source_ecr_obj, schemas.IEnvironmentRegion)
                    source_account_id = self.paco_ctx.get_ref(source_env.network.aws_account+".id")

                    dest_ecr_obj = get_model_obj_from_ref(repository.dest_repo, self.paco_ctx.project)
                    dest_env = get_parent_by_interface(dest_ecr_obj, schemas.IEnvironmentRegion)
                    dest_account_id = self.paco_ctx.get_ref(dest_env.network.aws_account+".id")

                    dest_ecr_obj = get_model_obj_from_ref(repository.dest_repo, self.paco_ctx.project)
                    ecr_deploy_script += ECR_DEPLOY_SCRIPT_CONFIG.format(
                        ecr_deploy_name=ecr_deploy_name,
                        source_repo_name=source_ecr_obj.repository_name,
                        source_repo_domain=f'{source_account_id}.dkr.ecr.{source_env.region}.amazonaws.com',
                        idx=repo_idx,
                        source_tag=repository.source_tag,
                        dest_repo_name=dest_ecr_obj.repository_name,
                        dest_repo_domain=f'{dest_account_id}.dkr.ecr.{dest_env.region}.amazonaws.com',
                        dest_tag=repository.dest_tag,
                        release_phase=repository.release_phase
                    )
                    repo_idx += 1

                if repo_idx > 0:
                    ecr_deploy_script += f'\n{ecr_deploy_name}_ECR_DEPLOY_LEN={repo_idx}\n'

                if ecr_deploy.release_phase and len(ecr_deploy.release_phase.ecs) > 0:
                    # Genreate script
                    release_phase_script = RELEASE_PHASE_SCRIPT
                    idx = 0
                    release_phase_script += ". /opt/aim/EC2Manager/ec2lm_functions.bash\n\n"
                    for command in ecr_deploy.release_phase.ecs:
                        release_phase_name = command.service.split(' ')[1]
                        release_phase_script += f"""
CLUSTER_ID_{idx}=$(ec2lm_instance_tag_value PACO_CB_RP_ECS_CLUSTER_ID_{idx})
SERVICE_ID_{idx}=$(ec2lm_instance_tag_value PACO_CB_RP_ECS_SERVICE_ID_{idx})
RELEASE_PHASE_NAME_{idx}={release_phase_name}
RELEASE_PHASE_COMMAND_{idx}="{command.command}"
run_release_phase "${{CLUSTER_ID_{idx}}}" "${{SERVICE_ID_{idx}}}" "${{RELEASE_PHASE_NAME_{idx}}}" "${{RELEASE_PHASE_COMMAND_{idx}}}"
"""
                        idx += 1
                    scripts['release_phase'] = {
                        'path': f'/usr/local/bin/paco-ecs-release-phase-{ecr_deploy_name}',
                        'mode': '0755',
                        'data': base64.b64encode(release_phase_script.encode('ascii')).decode('ascii')
                    }

                    # Create the SSM Document if it does not exist
                    ssm_documents = self.paco_ctx.project['resource']['ssm'].ssm_documents
                    if 'paco_ecs_docker_exec' not in ssm_documents:
                        ssm_doc = SSMDocument('paco_ecs_docker_exec', ssm_documents)
                        ssm_doc.add_location(self.account_ctx.paco_ref, self.aws_region)
                        ssm_doc.content = json.dumps(RELEASE_PHASE_SCRIPT_SSM_DOCUMENT_CONTENT)
                        ssm_doc.document_type = 'Command'
                        ssm_doc.enabled = True
                        ssm_documents['paco_ecs_docker_exec'] = ssm_doc
                    else:
                        ssm_documents['paco_ecs_docker_exec'].add_location(
                            self.account_ctx.paco_ref,
                            self.aws_region,
                        )
                ecr_deploy_idx += 1

                ecr_deploy_script += ECR_DEPLOY_SCRIPT_BODY
                scripts['ecr_deploy'] = {
                    'path': f'/usr/local/bin/paco-ecr-deploy-{ecr_deploy_name}',
                    'mode': '0755',
                    'data': base64.b64encode(ecr_deploy_script.encode('ascii')).decode('ascii')
                }


        # Script Manager
        launch_script = f"""#!/bin/bash
echo "EC2LM: Script Manager: Begin"

. {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

declare -a SCRIPTS
"""
        idx = 0
        for script_name in scripts.keys():
            launch_script += f"""
SCRIPTS[{idx}]="{script_name}"
{script_name}_DATA="{scripts[script_name]['data']}"
{script_name}_PATH="{scripts[script_name]['path']}"
{script_name}_MODE="{scripts[script_name]['mode']}"
"""
            idx += 1

        launch_script += f"""
function run_launch_bundle() {{
    ec2lm_install_package jq
    for NAME in ${{SCRIPTS[@]}}
    do
        SCRIPT_PATH_VAR=${{NAME}}_PATH
        SCRIPT_DATA_VAR=${{NAME}}_DATA
        SCRIPT_MODE_VAR=${{NAME}}_MODE

        SCRIPT_PATH=${{!SCRIPT_PATH_VAR}}
        SCRIPT_DATA=${{!SCRIPT_DATA_VAR}}
        SCRIPT_MODE=${{!SCRIPT_MODE_VAR}}
        if [ -e "${{SCRIPT_PATH}}" ] ; then
            echo "Updating script: ${{SCRIPT_PATH}}"
        else
            echo "Creating script: ${{SCRIPT_PATH}}"
        fi
        echo ${{SCRIPT_DATA}} | base64 -d >${{SCRIPT_PATH}}
        chmod ${{SCRIPT_MODE}} ${{SCRIPT_PATH}}
    done
}}

function disable_launch_bundle() {{
    :
}}

echo "EC2LM: Script Manager: End"
"""

        if len(scripts.keys()) > 0:
            script_manager_enabled = True
        script_lb.set_launch_script(launch_script, script_manager_enabled)
        self.add_bundle(script_lb)

    # TODO: Blocked until cftemplates/iam_managed_policies.py supports toposphere
    # and paco.ref Parameters!
    def lb_add_dns(self, bundle_name, resource):
        """Creates a launch bundle to install and configure the DNS agent"""
        # Create the Launch Bundle
        dns_lb = LaunchBundle(resource, self, bundle_name)
        dns_enabled = True
        if len(resource.dns) == 0:
            dns_enabled = False

        ec2_dns_domain = resource.dns[0].domain_name
        ec2_dns_hosted_zone = resource.dns[0].domain_name


        launch_script = f"""#!/bin/bash

function set_dns() {{
    INSTANCE_HOSTNAME="$(curl http://169.254.169.254/latest/meta-data/hostname)"
    RECORD_SET_FILE=/tmp/internal_record_set.json
    HOSTED_ZONE_ID=$1
    DOMAIN=$2
    cat << EOF >$RECORD_SET_FILE
    {{
        "Comment": "API Server",
        "Changes": [ {{
            "Action": "UPSERT",
            "ResourceRecordSet": {{
                "Name": "$DOMAIN",
                "Type": "CNAME",
                "TTL": 60,
                "ResourceRecords": [ {{
                    "Value": "$INSTANCE_HOSTNAME"
                }} ]
            }}
        }} ]
    }}
    EOF
    aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch file://$RECORD_SET_FILE
    echo "EC2LM: DNS: $HOSTED_ZONE_ID: $DOMAIN -> $INSTANCE_HOSTNAME"
}}

function run_launch_bundle() {{
    echo "EC2LM: DNS: Begin"
    # Load EC2 Launch Manager helper functions
    . {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

    for IDX in {{0..{len(resource.dns)}}}
    do
        HOSTED_ZONE_ID=$(ec2lm_instance_tag_value Paco-DNS-Hosted-Zone-$IDX)
        DOMAIN=$(ec2lm_instance_tag_value Paco-DNS-Domain-$IDX)

        set_dns $HOSTED_ZONE_ID $DOMAIN
    done
    echo "EC2LM: DNS: End"
}}

function disable_launch_bundle() {{
    :
}}
"""
        dns_lb.set_launch_script(launch_script, dns_enabled)
        self.add_bundle(dns_lb)

        if dns_enabled:
            # Create instance managed policy for the agent
            iam_policy_name = '-'.join([resource.name, 'dns-policy'])
            param = {
                'description': 'DNS Hosted Zone ID',
                'type': 'String',
                'key': 'DNSHostedZoneId' + hostedzone_hash,
                'value': ec2_dns_hosted_zone + '.id'
            }
            template_params.append(param)

            policy_config_yaml = f"""
policy_name: '{iam_policy_name}'
enabled: true
statement:
  - effect: Allow
    action:
      - route53:ChangeResourceRecordSets
    resource:
      - paco.sub '${{paco.ref {get_parent_by_interface(resource, schemas.IEnvironmentRegion).paco_ref}.network.vpc.private_hosted_zone.arn'}}
"""
            iam_ctl = self.paco_ctx.get_controller('IAM')
            iam_ctl.add_managed_policy(
                role=resource.instance_iam_role,
                resource=resource,
                policy_name='policy',
                policy_config_yaml=policy_config_yaml,
                extra_ref_names=['ec2lm','dns'],
            )

    def lb_add_codedeploy(self, bundle_name, resource):
        """Creates a launch bundle to install and configure the CodeDeploy agent"""
        # Create the Launch Bundle
        codedeploy_lb = LaunchBundle(resource, self, bundle_name)
        if resource.instance_ami_type_generic in ['amazon', 'centos']:
            uninstall_command='yum erase codedeploy-agent -y'
        else:
            uninstall_command='dpkg --purge codedeploy-agent -y'
        launch_script = f"""#!/bin/bash

function stop_agent() {{
    CODEDEPLOY_BIN="/opt/codedeploy-agent/bin/codedeploy-agent"
    if [ ! -e $CODEDEPLOY_BIN ] ; then
        return 0
    fi
    set +e
    TIMEOUT=60
    SLEEP_SECS=10
    T_COUNT=0
    echo "EC2LM: CodeDeploy: Attempting to stop Agent"
    while :
    do
        OUTPUT=$($CODEDEPLOY_BIN stop 2>/dev/null)
        if [ $? -eq 0 ] ; then
            break
        fi
        echo "EC2LM: CodeDeploy: A deployment is in progress, waiting for deployment to complete."
        sleep $SLEEP_SECS
        T_COUNT=$(($T_COUNT+1))
        if [ $T_COUNT -eq $TIMEOUT ] ; then
            echo "EC2LM: CodeDeploy: ERROR: Timeout after $(($TIMEOUT*$SLEEP_SECS)) seconds waiting for deployment to complete."
            exit 1
        fi
    done
    echo "EC2LM: Agent has been stopped."
    set -e
}}

function run_launch_bundle() {{
    echo "EC2LM: CodeDeploy: Agent Install: Begin"
    # Load EC2 Launch Manager helper functions
    . {self.paco_base_path}/EC2Manager/ec2lm_functions.bash

    cd /tmp/
    ec2lm_install_wget
    ec2lm_install_package ruby
    echo "EC2LM: CodeDeploy: Downloading Agent"
    rm -f install
    wget https://aws-codedeploy-ca-central-1.s3.amazonaws.com/latest/install
    chmod u+x ./install
    # Stopping the current agent
    stop_agent

    echo "EC2LM: CodeDeploy: Installing Agent"
    ./install auto
    CODEDEPLOY_AGENT_CONF="/etc/codedeploy-agent/conf/codedeployagent.yml"
    grep -v max_revisions $CODEDEPLOY_AGENT_CONF >$CODEDEPLOY_AGENT_CONF.new
    echo ":max_revisions: 1" >>$CODEDEPLOY_AGENT_CONF.new
    mv $CODEDEPLOY_AGENT_CONF.new $CODEDEPLOY_AGENT_CONF
    service codedeploy-agent start
    echo
    echo "EC2LM: CodeDeploy: Agent install complete."

    echo "EC2LM: CodeDeploy: End"
}}

function disable_launch_bundle() {{
    stop_agent
    {uninstall_command}
}}
"""
        codedeploy_lb.set_launch_script(launch_script, resource.launch_options.codedeploy_agent)
        self.add_bundle(codedeploy_lb)

    def process_bundles(self, resource, instance_iam_role_ref):
        "Initialize launch bundle S3 bucket and iterate through all launch bundles and add every applicable bundle"
        self.add_update_instance_ssm_document()
        resource._instance_iam_role_arn_ref = 'paco.ref ' + instance_iam_role_ref + '.arn'
        resource._instance_iam_role_arn = self.paco_ctx.get_ref(resource._instance_iam_role_arn_ref)
        if resource._instance_iam_role_arn == None:
            raise StackException(
                    PacoErrorCode.Unknown,
                    message="ec2_launch_manager: user_data_script: Unable to locate value for ref: " + instance_iam_role_arn_ref
                )
        bucket = self.init_ec2lm_s3_bucket(resource)
        for bundle_name in self.launch_bundle_names:
            bundle_method = getattr(self, 'lb_add_' + bundle_name.replace('-', '_').lower())
            bundle_method(bundle_name, resource)

        # Create CloudWatch Log Groups for SSM and CloudWatch Agent
        if resource.launch_options.ssm_agent or (resource.monitoring != None and resource.monitoring.log_sets):
            self.stack_group.add_new_stack(
                self.aws_region,
                resource,
                paco.cftemplates.LogGroups,
                stack_tags=self.stack_tags,
                support_resource_ref_ext='log_groups',
            )
        return bucket
