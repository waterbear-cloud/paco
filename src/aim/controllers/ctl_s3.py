import os
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.stack_group import S3StackGroup
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError
from aim.models import vocabulary

class S3Context():
    def __init__(self, aim_ctx, account_ctx, controller, context_id, region, group_name):
        self.aim_ctx = aim_ctx
        self.stack_group = None
        self.controller = controller
        self.buckets = []
        self.region = region
        self.account_ctx = account_ctx
        self.context_id = context_id
        self.group_name = group_name

    def bucket_context(self, app_id, group_id, bucket_id):
        return '.'.join([app_id, group_id, bucket_id])

    def add_bucket( self,
                    region,
                    bucket_id,
                    bucket_name_prefix,
                    bucket_name_suffix,
                    bucket_ref,
                    bucket_config,
                    stack_hooks=None):

        if bucket_name_suffix == None:
            bucket_name_suffix = vocabulary.aws_regions[region]['short_name']
        else:
            bucket_name_suffix += '-'+vocabulary.aws_regions[region]['short_name']

        bucket_context = {
            'id': bucket_id,
            'config': bucket_config,
            'ref': bucket_ref,
            'bucket_name_prefix': bucket_name_prefix,
            'bucket_name_suffix': bucket_name_suffix
        }
        self.buckets.append(bucket_context)

        self.stack_group = S3StackGroup(self.aim_ctx,
                                        self.account_ctx,
                                        self.region,
                                        self.group_name,
                                        self.buckets,
                                        self.controller,
                                        self.context_id,
                                        stack_hooks)

    def get_bucket_context(self, bucket_ref):
        for bucket_context in self.buckets:
            if bucket_context['ref'] == bucket_ref:
                return bucket_context
        return None

    def get_bucket_arn(self, bucket_ref):
        return 'arn:aws:s3:::'+self.get_bucket_name(bucket_ref)

    def get_bucket_name(self, bucket_ref):
        bucket_context = self.get_bucket_context(bucket_ref)
        bucket_name = '-'.join([bucket_context['bucket_name_prefix'],
                                bucket_context['config'].name,
                                bucket_context['bucket_name_suffix']])
        return bucket_name.replace('_', '').lower()

    def get_region(self):
        return self.region

    def validate(self):
        if self.stack_group:
            self.stack_group.validate()

    def provision(self):
        if self.stack_group:
            self.stack_group.provision()

    def delete(self):
        if self.stack_group:
            self.stack_group.delete()

    def empty_bucket(self, bucket_ref):
        for bucket_context in self.buckets:
            if bucket_context['ref'] == bucket_ref:
                break

        if bucket_context == None:
            print("ctl_s3: empty_bucket: ERROR: Unable to locate stack group for group: " + group_id)
            raise StackException(AimErrorCode.Unknown)


        s3_client = self.account_ctx.get_aws_client('s3')
        bucket_name = self.get_bucket_name(bucket_ref)
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                return
            else:
                raise e

        if 'Contents' in response:
            for item in response['Contents']:
                s3_client.delete_object(Bucket=bucket_name, Key=item['Key'])
                while response['KeyCount'] == 1000:
                    response = s3_client.list_objects_v2(
                        Bucket=bucket_name,
                        StartAfter=response['Contents'][0]['Key'],
                    )
                    for item in response['Contents']:
                        s3_client.delete_object(Bucket=bucket_name, Key=item['Key'])

class S3Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "S3")

        #self.aim_ctx.log("S3 Service: Configuration: %s" % (name))
        self.contexts = {}

    def init(self, init_config):
        pass

    def init_context(self, account_ctx, context_id, region, group_name):
        if context_id not in self.contexts.keys():
            self.contexts[context_id] = S3Context(self.aim_ctx, account_ctx, self, context_id, region, group_name)

    def add_bucket(self, context_id, *args, **kwargs):
        return self.contexts[context_id].add_bucket(*args, **kwargs)

    def get_bucket_arn(self, context_id, *args, **kwargs):
        return self.contexts[context_id].get_bucket_arn(*args, **kwargs)

    def get_bucket_name(self, context_id, *args, **kwargs):
        return self.contexts[context_id].get_bucket_name(*args, **kwargs)

    def empty_bucket(self, context_id, *args, **kwargs):
        return self.contexts[context_id].empty_bucket(*args, **kwargs)

    def get_region(self, context_id, *args, **kwargs):
        return self.contexts[context_id].empty_bucket(*args, **kwargs)

    def validate(self, context_id):
        if context_id in self.contexts:
            return self.contexts[context_id].validate()

    def provision(self, context_id):
        if context_id in self.contexts:
            return self.contexts[context_id].provision()

    def delete(self, context_id):
        if context_id in self.contexts:
            return self.contexts[context_id].delete()

    def get_stack_from_ref(self, context_id, *args, **kwargs):
        return self.contexts[context_id].get_stack_from_ref(*args, **kwargs)

    def get_value_from_ref(self, context_id, *args, **kwargs):
        return self.contexts[context_id].get_value_from_ref(*args, **kwargs)
