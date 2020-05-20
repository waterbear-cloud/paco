import paco.cftemplates
import paco.models.applications
import os
from paco.controllers.controllers import Controller
from paco.stack import Stack, StackGroup
from paco.models.loader import apply_attributes_from_config
from paco.core.exception import PacoBucketExists
from paco.models.references import get_model_obj_from_ref


class CloudTrailStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        cloudtrail,
        controller,
        accounts,
        account_default_region,
        kms_key_account=False
    ):
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

            # If KMS encryption is enabled then create a KMS Key for the trail
            if kms_key_account:
                kms_crypto_principle_list = []
                for account in accounts:
                    kms_crypto_principle_list.append(
                        "paco.sub 'arn:aws:iam::${%s}:root'" % (account.paco_ref)
                    )
                kms_config_dict = {
                    'admin_principal': {
                        'aws': [ "!Sub 'arn:aws:iam::${{AWS::AccountId}}:root'" ]
                    },
                    'crypto_principal': {
                        'aws': kms_crypto_principle_list
                    }
                }
                cloudtrail.kms_stack = self.add_new_stack(
                    region,
                    trail,
                    paco.cftemplates.KMS,
                    account_ctx=account_ctx,
                    support_resource_ref_ext='kms',
                    extra_context={'cloudtrail': trail}
                )
                self.stack_list.append(cloudtrail.kms_stack)

            # Create an S3 bucket to store the CloudTrail in
            s3_ctl = self.paco_ctx.get_controller('S3')
            # ToDo: StackTags is None
            put_suffixes = []
            for account in accounts:
                if trail.s3_key_prefix:
                    put_suffixes.append("/{}/AWSLogs/{}/*".format(trail.s3_key_prefix, account.account_id))
                else:
                    put_suffixes.append("/AWSLogs/{}/*".format(account.account_id))
            bucket_config_dict = {
                'region': region,
                'account': account_ctx.paco_ref,
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
            global_buckets = project['resource']['s3'].buckets
            s3bucket = paco.models.applications.S3Bucket(trail.name, global_buckets)
            apply_attributes_from_config(s3bucket, bucket_config_dict, read_file_path = 'dynamically generated in code paco.controllers.ctl_cloudtrail')
            global_buckets[trail.name] = s3bucket
            s3bucket.resolve_ref_object = self
            s3bucket.enabled = trail.is_enabled()
            try:
                s3_config_ref = s3bucket.paco_ref_parts
                s3_ctl.init_context(account_ctx, region, s3_config_ref, self, None)
                s3_ctl.add_bucket(s3bucket, config_ref=s3_config_ref)
            except PacoBucketExists:
                # for multiple accounts there is only one bucket needed
                pass
            # Create the CloudTrail stack and prepare it
            stack = self.add_new_stack(
                region,
                trail,
                paco.cftemplates.CloudTrail,
                account_ctx=self.account_ctx,
                extra_context={'s3_bucket_name': s3bucket.get_bucket_name()}
            )
            self.stack_list.append(stack)


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
        self.cloudtrail.resolve_ref_obj = self
        self.stack_grps = []

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_stack_groups()
        self.init_done = True

    def init_stack_groups(self):
        for trail in self.cloudtrail.trails.values():
            accounts = trail.get_accounts()
            # re-organize the list so that the s3_bucket_account is the first on the list
            # as the first account gets the S3 bucket
            s3_bucket_account = get_model_obj_from_ref(trail.s3_bucket_account, self.paco_ctx.project)
            ordered_accounts = []
            for account in accounts:
                if s3_bucket_account.name == account.name:
                    # S3 Bucket account is also the KMS Key account if that's enabled
                    account._kms_key_account = False
                    if trail.enable_kms_encryption == True:
                        account._kms_key_account = True
                    ordered_accounts.append(account)
            for account in accounts:
                if s3_bucket_account.name != account.name:
                    account._kms_key_account = False
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
                    kms_key_account=account._kms_key_account,
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

    def resolve_ref(self, ref):
        "Resolve KMS CMK ARNs: resource.cloudtrail.trails.<trailname>.kms.arn"
        trailname = ref.parts[3]
        trail = self.cloudtrail.trails[trailname]
        if trail.enable_kms_encryption == True:
            return self.cloudtrail.kms_stack
        return None
