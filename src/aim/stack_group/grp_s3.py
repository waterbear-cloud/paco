import aim.cftemplates
import botocore
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks
from aim.config import S3Config
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode


class S3StackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 config,
                 config_name,
                 app_id,
                 group_id,
                 controller,
                 s3_context_id,
                 stack_hooks=None):
        aws_name = config_name
        super().__init__(aim_ctx,
                         account_ctx,
                         config_name,
                         aws_name,
                         controller)

        # Initialize config with a deepcopy of the project defaults
        self.config = config
        self.stack_list = []
        self.app_id = app_id
        self.group_id = group_id
        self.s3_context_id = s3_context_id
        self.stack_hooks = stack_hooks
        s3_template = aim.cftemplates.S3(self.aim_ctx,
                                         self.account_ctx,
                                         config,
                                         self.app_id,
                                         self.group_id,
                                         self.s3_context_id,
                                         self.config.config_ref)
        s3_template.set_template_file_id(self.aim_ctx.md5sum(str_data=self.controller.context_id))

        # S3 Delete on Stack Delete hook
        if self.stack_hooks == None:
            self.stack_hooks = StackHooks(self.aim_ctx)

        self.stack_hooks.add('S3StackGroup', 'delete', 'post',
                             self.stack_hook_post_delete, None, config)
        s3_stack = Stack(self.aim_ctx,
                         self.account_ctx,
                         self,
                         config,
                         s3_template,
                         aws_region=self.config.region,
                         hooks=self.stack_hooks)

        self.stack_list.append(s3_stack)

        self.add_stack_order(s3_stack)

    def stack_hook_post_delete(self, hook, hook_arg):
        # Empty the S3 Bucket if enabled
        s3_config = hook_arg
        s3_resource = self.account_ctx.get_aws_resource('s3', s3_config.region)
        for bucket_id in s3_config.get_bucket_ids(self.app_id, self.group_id):
            deletion_policy = s3_config.get_bucket_deletion_policy(self.app_id, self.group_id, bucket_id)
            bucket_name = s3_config.get_bucket_name(self.app_id, self.group_id, bucket_id)
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
        # self.validate()
        super().provision()

        return None
