import os
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.stack_group import S3StackGroup
from aim.config import S3Config
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError


class S3Context():
    def __init__(self, aim_ctx, controller):
        self.aim_ctx = aim_ctx
        self.stack_grps = []
        self.controller = controller

    def add_bucket_config(self,
                          account_ctx,
                          region,
                          app_id,
                          group_id,
                          bucket_id,
                          bucket_name_prefix,
                          bucket_name_suffix,
                          config_ref,
                          config_name,
                          config_dict,
                          stack_hooks=None):
        s3_config_dict = {
            app_id: {
                group_id: {
                    bucket_id: config_dict
                }
            }
        }

        s3_config = S3Config(self.aim_ctx,
                             region=region,
                             config_ref=config_ref,
                             config_name=config_name,
                             config_dict=s3_config_dict,
                             bucket_name_prefix=bucket_name_prefix,
                             bucket_name_suffix=bucket_name_suffix)
        s3_stack_grp = S3StackGroup(self.aim_ctx,
                                    account_ctx,
                                    s3_config,
                                    config_name,
                                    app_id,
                                    group_id,
                                    self.controller,
                                    self.controller.context_id,
                                    stack_hooks)
        self.stack_grps.append(s3_stack_grp)

    def get_bucket_arn(self, app_id, group_id, bucket_id):
        for stack_grp in self.stack_grps:
            if stack_grp.app_id == app_id and stack_grp.group_id == group_id:
                return stack_grp.config.get_bucket_arn(app_id, group_id, bucket_id)

    def get_bucket_name(self, app_id, group_id, bucket_id):
        for stack_grp in self.stack_grps:
            if stack_grp.app_id == app_id and stack_grp.group_id == group_id:
                return stack_grp.config.get_bucket_name(app_id, group_id, bucket_id)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

    def delete(self):
        for stack_grp in reversed(self.stack_grps):
            stack_grp.delete()

    def empty_bucket(self, app_id, group_id, bucket_id):
        for stack_grp in self.stack_grps:
            if stack_grp.group_id == group_id:
                break
        if stack_grp == None:
            print("ctl_s3: empty_bucket: ERROR: Unable to locate stack group for group: " + group_id)
            raise StackException(AimErrorCode.Unknown)

        s3_client = stack_grp.account_ctx.get_aws_client('s3')
        bucket_name = self.get_bucket_name(app_id, group_id, bucket_id)
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                return

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

    def OLD_get_stack_from_ref(self, aim_ref):
        stack = None
        for stack_grp in self.stack_grps:
            stack = stack_grp.get_stack_from_ref(aim_ref)
            if stack:
                break

        return stack

    def OLD_get_value_from_ref(self, aim_ref):
        ref_dict = self.aim_ctx.parse_ref(aim_ref)
        ref_parts = ref_dict['ref_parts']
        # applications', 'app1', 'services', 's3', 'cpbd', 'buckets', 'deployment_artifacts', 'name'
        last_idx = len(ref_parts)-1

        stack = self.get_stack_from_ref(aim_ref)
        if stack:
            if ref_parts[last_idx] == 'name':
                bucket_id = ref_parts[last_idx-1]
                return stack.config.get_bucket_name(bucket_id)
        return None

class S3Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "S3")

        #self.aim_ctx.log("S3 Service: Configuration: %s" % (name))
        self.s3_context = {}
        self.context_id = None

    def init(self, init_config):
        pass

    def init_context(self, context_id):
        self.context_id = context_id
        if context_id not in self.s3_context.keys():
            self.s3_context[context_id] = S3Context(self.aim_ctx, self)

    def add_config(self, *args, **kwargs):
        return self.s3_context[self.context_id].add_config(*args, **kwargs)

    def add_bucket_config(self, *args, **kwargs):
        return self.s3_context[self.context_id].add_bucket_config(*args, **kwargs)

    def get_bucket_arn(self, *args, **kwargs):
        return self.s3_context[self.context_id].get_bucket_arn(*args, **kwargs)

    def get_bucket_name(self, *args, **kwargs):
        return self.s3_context[self.context_id].get_bucket_name(*args, **kwargs)

    def empty_bucket(self, *args, **kwargs):
        return self.s3_context[self.context_id].empty_bucket(*args, **kwargs)

    def validate(self):
        return self.s3_context[self.context_id].validate()

    def provision(self):
        return self.s3_context[self.context_id].provision()

    def delete(self):
        return self.s3_context[self.context_id].delete()

    def get_stack_from_ref(self, *args, **kwargs):
        return self.s3_context[self.context_id].get_stack_from_ref(*args, **kwargs)

    def get_value_from_ref(self, *args, **kwargs):
        return self.s3_context[self.context_id].get_value_from_ref(*args, **kwargs)
