import paco.cftemplates
import paco.models.applications
import os
from paco.controllers.controllers import Controller
from paco.stack import Stack, StackGroup, StackTags
from paco.models.loader import apply_attributes_from_config
from paco.core.exception import PacoBucketExists
from paco.models.references import get_model_obj_from_ref


class ConfigStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        config,
        controller,
        accounts,
        regions,
    ):
        aws_name = account_ctx.get_name()
        super().__init__(paco_ctx, account_ctx, 'Config', aws_name, controller)
        self.config = config
        self.stack_list = []

        # Create an S3 bucket for ConfigRecorder to write to
        bucket_name = self.create_config_bucket(account_ctx, accounts)

        # Create IAM Role for AWS Config
        role = self.create_iam_role(bucket_name, account_ctx, config.global_resources_region)

        # Create the AWS Config stacks
        for region in regions:
            stack = self.add_new_stack(
                region,
                config,
                paco.cftemplates.Config,
                account_ctx=self.account_ctx,
                extra_context={'s3_bucket_name': bucket_name, 'role': role}
            )
            self.stack_list.append(stack)

    def create_config_bucket(self, account_ctx, accounts):
        "Create an S3 Bucket for AWS Config"
        s3_ctl = self.paco_ctx.get_controller('S3')
        global_buckets = self.paco_ctx.project['resource']['s3'].buckets
        bucket_config_dict = {
            'region': self.config.global_resources_region,
            'account': self.config.s3_bucket_logs_account,
            'bucket_name': 'config',
            'enabled': True,
            'deletion_policy': 'delete',
            'policy': [
                {
                    'sid': "AWSConfigBucketPermissionsCheck",
                    'effect': "Allow",
                    'action': ["s3:GetBucketAcl"],
                    'principal': {"Service": "config.amazonaws.com"},
                },
                {
                    'sid': "AWSConfigBucketExistenceCheck",
                    'effect': "Allow",
                    'action': ["s3:ListBucket"],
                    'principal': {"Service": "config.amazonaws.com"},
                },
                {
                    'sid': "AWSConfigBucketDelivery",
                    'effect': "Allow",
                    'action': ["s3:PutObject"],
                    'principal': {"Service": "config.amazonaws.com"},
                    'resource_suffix': [
                        f"/AWSLogs/{account.account_id}/Config/*" for account in accounts
                    ],
                    'condition': {
                        "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
                    },
                }
            ]
        }
        s3bucket = paco.models.applications.S3Bucket('paco-awsconfig', global_buckets)
        apply_attributes_from_config(s3bucket, bucket_config_dict, read_file_path = 'dynamically generated in code paco.controllers.ctl_config')
        global_buckets['paco-awsconfig'] = s3bucket
        s3bucket.resolve_ref_object = self
        bucket_account_ctx = self.paco_ctx.get_account_context(account_ref=self.config.s3_bucket_logs_account)
        try:
            s3_config_ref = s3bucket.paco_ref_parts
            s3_ctl.init_context(bucket_account_ctx, self.config.global_resources_region, s3_config_ref, self, None)
            s3_ctl.add_bucket(s3bucket, config_ref=s3_config_ref)
        except PacoBucketExists:
            pass
        return s3bucket.get_bucket_name()

    def create_iam_role(self, bucket_name, account_ctx, aws_region):
        "IAM Role for AWS Config"
        iam_role_id = 'AWSConfig-{}'.format(account_ctx.name)
        statements = [{
            'effect': "Allow",
            'action': ["s3:PutObject"],
            'resource': [f"arn:aws:s3:::{bucket_name}/AWSLogs/{account_ctx.id}/*"],
            'condition': { "StringLike": {"s3:x-amz-acl": "bucket-owner-full-control"} }
        },
        {
            'effect': "Allow",
            'action': ["s3:GetBucketAcl"],
            'resource': f"arn:aws:s3:::{bucket_name}"
        }]
        role_dict = {
            'enabled': True,
            'path': '/',
            'role_name': iam_role_id,
            'assume_role_policy': {'effect': 'Allow', 'service': ['config.amazonaws.com']},
            'policies': [{'name': 'AllowS3BucketWriteAccess','statement': statements}],
            'managed_policy_arns': ['arn:aws:iam::aws:policy/service-role/AWSConfigRole'],
        }
        role = paco.models.iam.Role(iam_role_id, self.config)
        role.apply_config(role_dict)
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=aws_region,
            resource=self.config,
            role=role,
            iam_role_id=iam_role_id,
            stack_group=self,
            stack_tags=StackTags()
        )
        return role

class ConfigController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "Resource",
            "Config"
        )
        if not 'config' in self.paco_ctx.project['resource']:
            self.init_done = True
            return
        self.init_done = False
        self.config = self.paco_ctx.project['resource']['config'].config
        self.config.resolve_ref_obj = self
        self.stack_grps = []

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_stack_groups()
        self.init_done = True

    def init_stack_groups(self):
        if self.config.locations == []:
            accounts = self.paco_ctx.project['accounts'].values()
            # boto3 call for all enabled regions
            client = self.account_ctx.get_aws_client('ec2')
            region_info = client.describe_regions()
            regions = [ region['RegionName'] for region in  region_info['Regions'] ]
            for account in accounts:
                account_ctx = self.paco_ctx.get_account_context(account_name=account.name)
                config_regions_stack_group = ConfigStackGroup(
                    self.paco_ctx,
                    account_ctx,
                    self.config,
                    self,
                    accounts,
                    regions,
                )
                self.stack_grps.append(config_regions_stack_group)
        else:
            for location in self.config.locations:
                accounts = self.config.get_accounts()
                account_ctx = self.paco_ctx.get_account_context(account_ref=location.account)
                config_regions_stack_group = ConfigStackGroup(
                    self.paco_ctx,
                    account_ctx,
                    self.config,
                    self,
                    accounts,
                    location.regions,
                )
                self.stack_grps.append(config_regions_stack_group)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def delete(self):
        for stack_grp in self.stack_grps:
            stack_grp.delete()
