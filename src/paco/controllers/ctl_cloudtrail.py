import paco.cftemplates
import paco.models.applications
import os
from paco.controllers.controllers import Controller
from paco.stack_group import Stack, StackGroup
from paco.models.loader import apply_attributes_from_config
from paco.core.exception import PacoBucketExists
from paco.models.references import get_model_obj_from_ref


class CloudTrailStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, cloudtrail, controller, accounts, account_default_region):
        aws_name = account_ctx.get_name()
        super().__init__(
            paco_ctx,
            account_ctx,
            'CloudTrail',
            aws_name,
            controller
        )
        project = self.paco_ctx.project
        self.cloudtrail = cloudtrail
        self.account_default_region = account_default_region
        self.stack_list = []
        for trail in cloudtrail.trails.values():
            if trail.region:
                region = trail.region
            else:
                region = self.account_default_region

            # Create an S3 bucket to store the CloudTrail in
            s3_ctl = self.paco_ctx.get_controller('S3')
            s3_config_ref = trail.paco_ref + '.s3bucket'
            # ToDo: StackTags is None
            s3_ctl.init_context(account_ctx, region, s3_config_ref, self, None)
            put_suffixes = []
            for account in accounts:
                if trail.s3_key_prefix:
                    put_suffixes.append("/{}/AWSLogs/{}/*".format(trail.s3_key_prefix, account.account_id))
                else:
                    put_suffixes.append("/AWSLogs/{}/*".format(account.account_id))
            bucket_config_dict = {
                'region': region,
                'account': account_ctx.gen_ref(),
                'bucket_name': 'cloudtrail',
                'enabled': True,
                'deletion_policy': 'delete',
                'policy': [ {
                    'principal': {"Service": "cloudtrail.amazonaws.com"},
                    'effect': 'Allow',
                    'action': ['s3:GetBucketAcl'],
                    'resource_suffix': ['']
                },
                {
                    'principal': {"Service": "cloudtrail.amazonaws.com"},
                    'effect': 'Allow',
                    'action': ['s3:PutObject'],
                    'resource_suffix': put_suffixes,
                    'condition': {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
                } ],
            }
            global_buckets = project['resource']['s3']
            s3bucket = paco.models.applications.S3Bucket(trail.name, global_buckets)
            apply_attributes_from_config(s3bucket, bucket_config_dict, read_file_path = 'dynamically generated in code paco.controllers.ctl_cloudtrail')
            global_buckets.buckets[trail.name] = s3bucket
            s3bucket.resolve_ref_object = self
            s3bucket.enabled = trail.is_enabled()
            try:
                s3_ctl.add_bucket(
                    s3bucket,
                    config_ref = s3_config_ref,
                )
            except PacoBucketExists:
                # for multiple accounts there is only one bucket needed
                pass
            # Create the CloudTrail stack and prepare it
            cloudtrail_template = paco.cftemplates.CloudTrail(
                self.paco_ctx,
                self.account_ctx,
                region,
                self,
                None, #stack_tags
                trail,
                s3bucket.get_bucket_name()
            )
            self.stack_list.append(cloudtrail_template.stack)


class CloudTrailController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "Resource",
            "CloudTrail"
        )
        if not 'cloudtrail' in self.paco_ctx.project['resource']:
            self.init_done = True
            return
        self.init_done = False
        self.cloudtrail = self.paco_ctx.project['resource']['cloudtrail']
        self.stack_grps = []

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_done = True
        self.init_stack_groups()

    def init_stack_groups(self):
        for trail in self.cloudtrail.trails.values():
            accounts = trail.get_accounts()
            # re-organize the list so that the s3_bucket_account is the first on the list
            # as the first account gets the S3 bucket
            s3_bucket_account = get_model_obj_from_ref(trail.s3_bucket_account, self.paco_ctx.project)
            ordered_accounts = []
            for account in accounts:
                if s3_bucket_account.name == account.name:
                    ordered_accounts.append(account)
            for account in accounts:
                if s3_bucket_account.name != account.name:
                    ordered_accounts.append(account)

            for account in ordered_accounts:
                account_ctx = self.paco_ctx.get_account_context(account_name=account.name)
                cloudtrail_stack_grp = CloudTrailStackGroup(
                    self.paco_ctx,
                    account_ctx,
                    self.cloudtrail,
                    self,
                    accounts,
                    account_default_region=account.region,
                )
                self.stack_grps.append(cloudtrail_stack_grp)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def delete(self):
        for stack_grp in self.stack_grps:
            stack_grp.delete()
