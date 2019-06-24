import aim.cftemplates
import botocore
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class S3StackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 region,
                 group_name,
                 buckets,
                 controller,
                 resource_ref,
                 stack_hooks=None):
        print("S3 Group Name: " + group_name)
        aws_name = group_name
        super().__init__(aim_ctx,
                         account_ctx,
                         group_name,
                         aws_name,
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.stack_list = []
        self.resource_ref = resource_ref
        self.stack_hooks = stack_hooks
        self.buckets = buckets
        self.region = region

        s3_template = aim.cftemplates.S3(self.aim_ctx,
                                         self.account_ctx,
                                         self.buckets,
                                         self.resource_ref,
                                         None)
        s3_template.set_template_file_id(self.aim_ctx.md5sum(str_data=resource_ref))

        # S3 Delete on Stack Delete hook
        if self.stack_hooks == None:
            self.stack_hooks = StackHooks(self.aim_ctx)

        self.stack_hooks.add('S3StackGroup', 'delete', 'post',
                             self.stack_hook_post_delete, None, self.buckets)
        s3_stack = Stack(self.aim_ctx,
                         self.account_ctx,
                         self,
                         self.buckets,
                         s3_template,
                         aws_region=self.region,
                         hooks=self.stack_hooks)

        self.stack_list.append(s3_stack)

        self.add_stack_order(s3_stack)

    def stack_hook_post_delete(self, hook, hook_arg):
        # Empty the S3 Bucket if enabled
        buckets = hook_arg
        for bucket_context in buckets:
            s3_config = bucket_context['config']
            s3_resource = self.account_ctx.get_aws_resource('s3', self.region)
            deletion_policy = s3_config.deletion_policy
            bucket_name = self.controller.get_bucket_name(bucket_context['ref'])
            if deletion_policy == "delete":
                print("Deleting S3 Bucket: %s" % (bucket_name))
                bucket = s3_resource.Bucket(bucket_name)
                try:
                    bucket.objects.all().delete()
                    bucket.delete()
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] != 'NoSuchBucket':
                        print("%s: %s" % (e.response['Error']['Code'], e.response['Error']['Message']))
                        raise StackException(AimErrorCode.Unknown)
            else:
                print("Retaining S3 Bucket: %s" % (bucket_name))

    def validate(self):
        super().validate()

    def provision(self):
        super().provision()

        return None
