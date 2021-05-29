import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.models import vocabulary


class LBApplicationResourceEngine(ResourceEngine):

    def init_resource(self):
        # Set resolve_ref object for TargetGroups
        for target_group in self.resource.target_groups.values():
            target_group.resolve_ref_obj = self.app_engine

        if self.resource.enable_access_logs == True:
            access_logs_bucket_policies = []
            access_logs_bucket_policies.append({
                'aws': [f'arn:aws:iam::{vocabulary.elb_account_id[self.aws_region]}:root'],
                'action': [ 's3:PutObject' ],
                'effect': 'Allow',
                'resource_suffix': [ f'/{self.resource.access_logs_prefix}/AWSLogs/{self.account_ctx.id}/*' ]
            })
            access_logs_bucket_policies.append({
                'principal': {
                    'Service': 'delivery.logs.amazonaws.com'
                },
                'action': [ 's3:PutObject' ],
                'effect': 'Allow',
                'condition': {
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                },
                'resource_suffix': [ f'/{self.resource.access_logs_prefix}/AWSLogs/{self.account_ctx.id}/*' ]
            })
            access_logs_bucket_policies.append({
                'principal': {
                    'Service': 'delivery.logs.amazonaws.com'
                },
                'action': [ 's3:GetBucketAcl' ],
                'effect': 'Allow',
                'resource_suffix': [ '' ]
            })
            access_logs_bucket_policies.append({
                'principal': {
                    'Service': 'logdelivery.elb.amazonaws.com'
                },
                'action': [ 's3:PutObject' ],
                'effect': 'Allow',
                'condition': {
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                },
                'resource_suffix': [ f'/{self.resource.access_logs_prefix}/AWSLogs/{self.account_ctx.id}/*' ]
            })
            # the S3 Bucket Policy can be added to by multiple DeploymentPipelines
            s3_ctl = self.paco_ctx.get_controller('S3')
            for access_log_policy in access_logs_bucket_policies:
                s3_ctl.add_bucket_policy(self.resource.access_logs_bucket, access_log_policy)
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ALB,
            stack_tags=self.stack_tags,
            extra_context={'env_ctx': self.env_ctx, 'app_id': self.app_id}
        )

class LBNetworkResourceEngine(ResourceEngine):

    def init_resource(self):
        # Set resolve_ref object for TargetGroups
        for target_group in self.resource.target_groups.values():
            target_group.resolve_ref_obj = self.app_engine
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.NLB,
            stack_tags=self.stack_tags,
            extra_context={'env_ctx': self.env_ctx, 'app_id': self.app_id}
        )