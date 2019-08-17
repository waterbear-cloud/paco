import aim.cftemplates
import aim.models.applications
import os
from aim.controllers.controllers import Controller
from aim.models import references
from aim.stack_group import Stack, StackGroup


class CloudTrailStackGroup(StackGroup):
    def __init__(self, aim_ctx, account_ctx, cloudtrail, controller, account_default_region):
        aws_name = account_ctx.get_name()
        super().__init__(
            aim_ctx,
            account_ctx,
            'CloudTrail',
            aws_name,
            controller
        )
        self.cloudtrail = cloudtrail
        self.account_default_region = account_default_region
        self.stack_list = []
        for trail in cloudtrail.trails.values():
            if trail.region:
                region = trail.region
            else:
                region = self.account_default_region

            # Create an S3 bucket to store the CloudTrail in
            s3_ctl = self.aim_ctx.get_controller('S3')
            s3_config_ref = "aim.ref resource.cloudtrail.trails.{}.s3bucket".format(trail.name)
            # ToDo: StackTags is None
            s3_ctl.init_context(account_ctx, region, s3_config_ref, self, None)
            group_id = 'CloudTrail'
            bucket_name_prefix = '-'.join([aws_name, group_id])
            if trail.s3_key_prefix:
                put_suffix = "/{}/AWSLogs/{}/*".format(trail.s3_key_prefix, account_ctx.get_id())
            else:
                put_suffix = "/AWSLogs/{}/*".format(account_ctx.get_id())
            bucket_config_dict = {
                'bucket_name': 'cloudtrail',
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
                    'resource_suffix': [ put_suffix ],
                    'condition': {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
                } ],
            }
            s3bucket = aim.models.applications.S3Bucket(trail.name, None)
            s3bucket.update(bucket_config_dict)
            s3_ctl.add_bucket(
                resource_ref=s3_config_ref,
                region=region,
                bucket_id=trail.name,
                bucket_group_id=group_id,
                bucket_name_prefix=bucket_name_prefix,
                bucket_name_suffix=trail.name,
                bucket_config=s3bucket
            )

            # Create the CloudTrail stack and prepare it
            cloudtrail_template = aim.cftemplates.CloudTrail(
                self.aim_ctx,
                self.account_ctx,
                region,
                trail,
                s3_ctl.get_bucket_name(s3_config_ref)
            )
            cloudtrail_stack = Stack(
                self.aim_ctx,
                self.account_ctx,
                self,
                trail,
                cloudtrail_template,
                aws_region=region
            )
            self.stack_list.append(cloudtrail_stack)
            self.add_stack_order(cloudtrail_stack)


class CloudTrailController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(
            aim_ctx,
            "Resource",
            "CloudTrail"
        )
        if not 'cloudtrail' in self.aim_ctx.project:
            self.init_done = True
            return
        self.init_done = False
        self.cloudtrail = self.aim_ctx.project['cloudtrail']
        self.stack_grps = []

    def init(self, controller_args):
        if self.init_done:
            return
        self.init_done = True
        self.init_stack_groups()

    def init_stack_groups(self):
        for trail in self.cloudtrail.trails.values():
            if trail.accounts == []:
                # default is to enable for all accounts
                accounts = self.aim_ctx.project['accounts'].values()
            else:
                accounts = []
                for account_ref in trail.accounts:
                    # ToDo: when accounts .get_ref returns an object, remove this workaround
                    ref = references.Reference(account_ref)
                    account = self.aim_ctx.project['accounts'][ref.last_part]
                    accounts.append(account)
            for account in accounts:
                account_ctx = self.aim_ctx.get_account_context(account_name=account.name)
                cloudtrail_stack_grp = CloudTrailStackGroup(
                    self.aim_ctx,
                    account_ctx,
                    self.cloudtrail,
                    self,
                    account_default_region=account.region
                )
                self.stack_grps.append(cloudtrail_stack_grp)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()
