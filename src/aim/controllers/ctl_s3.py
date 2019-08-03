import os
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.stack_group import StackGroup
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError
from aim.models import vocabulary
from aim import models
import aim.cftemplates
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackHooks, StackTags
import copy
import botocore

class S3StackGroup(StackGroup):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 region,
                 group_name,
                 controller,
                 resource_ref,
                 stack_hooks=None):
        #print("S3 Group Name: " + group_name)
        aws_name = group_name
        super().__init__(aim_ctx,
                         account_ctx,
                         group_name,
                         aws_name,
                         controller)
        self.stack_hooks = stack_hooks

class S3Context():
    def __init__(self, aim_ctx, account_ctx, region, controller, stack_group, resource_ref, stack_tags):
        self.aim_ctx = aim_ctx
        self.stack_group = stack_group
        self.controller = controller
        self.region = region
        self.account_ctx = account_ctx
        self.resource_ref = resource_ref
        self.stack_tags = stack_tags
        self.bucket_context = {
            'id': None,
            'group_id': None,
            'config': None,
            'ref': resource_ref,
            'bucket_name_prefix': None,
            'bucket_name_suffix': None,
            'stack': None
        }

    def add_stack_hooks(self, stack_hooks):
        self.bucket_context['stack'].add_hooks(stack_hooks)

    def add_stack(  self,
                    bucket_policy_only=False,
                    stack_hooks=None,
                    new_stack=True,
                    stack_tags=None):

        s3_template = aim.cftemplates.S3(self.aim_ctx,
                                         self.account_ctx,
                                         self.region,
                                         self.bucket_context,
                                         bucket_policy_only,
                                         self.resource_ref)

        s3_stack = Stack(self.aim_ctx,
                        self.account_ctx,
                        self.stack_group,
                        self.bucket_context,
                        s3_template,
                        aws_region=self.region,
                        hooks=stack_hooks,
                        stack_tags=stack_tags)

        if bucket_policy_only == False:
            if self.bucket_context['stack'] != None:
                raise StackException(AimErrorCode.Unknown)
            self.bucket_context['stack'] = s3_stack

        self.stack_group.add_stack_order(s3_stack)

    def add_bucket( self,
                    region,
                    bucket_id,
                    bucket_group_id,
                    bucket_name_prefix,
                    bucket_name_suffix,
                    bucket_config,
                    stack_hooks=None):

        if self.bucket_context['id'] != None:
            print("Bucket already exists: %s" % (self.resource_ref))
            raise StackException(AimErrorCode.Unknown)

        if bucket_name_suffix == None:
            bucket_name_suffix = vocabulary.aws_regions[region]['short_name']
        else:
            bucket_name_suffix += '-'+vocabulary.aws_regions[region]['short_name']

        self.bucket_context['id'] = bucket_id
        self.bucket_context['group_id'] = bucket_group_id
        self.bucket_context['config'] = bucket_config
        self.bucket_context['ref'] = self.resource_ref
        self.bucket_context['bucket_name_prefix'] = bucket_name_prefix
        self.bucket_context['bucket_name_suffix'] = bucket_name_suffix

        bucket_config.resolve_ref_obj = self

        # S3 Delete on Stack Delete hook
        if stack_hooks == None:
            stack_hooks = StackHooks(self.aim_ctx)


        stack_hooks.add('S3StackGroup', 'delete', 'post',
                        self.stack_hook_post_delete, None, self.bucket_context)

        self.add_stack(bucket_policy_only=False,
                        stack_hooks=stack_hooks,
                        stack_tags=self.stack_tags)


    def add_bucket_policy(self, policy_dict, stack_hooks=None, new_stack=True):
        bucket_config = self.bucket_context['config']
        # If this is a new stack, mark previous policies as processed so they
        # are not written twice.
        if new_stack == True:
            for policy in bucket_config.policy:
                policy.processed = True
        bucket_config.add_policy(policy_dict)

        self.add_stack( bucket_policy_only=True,
                        stack_hooks=stack_hooks,
                        stack_tags=self.stack_tags)

    def get_bucket_arn(self):
        return 'arn:aws:s3:::'+self.get_bucket_name()

    def get_bucket_name(self):
        bucket_name = '-'.join([self.bucket_context['bucket_name_prefix'],
                                self.bucket_context['config'].name,
                                self.bucket_context['config'].bucket_name,
                                self.bucket_context['bucket_name_suffix']])
        return bucket_name.replace('_', '-').lower()

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

    def stack_hook_post_delete(self, hook, hook_arg):
        # Empty the S3 Bucket if enabled
        buckets = hook_arg
        bucket_context = hook_arg
        s3_config = bucket_context['config']
        s3_resource = self.account_ctx.get_aws_resource('s3', self.region)
        deletion_policy = s3_config.deletion_policy
        bucket_name = self.get_bucket_name()
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

    def empty_bucket(self):
        if self.bucket_context == None:
            print("ctl_s3: empty_bucket: ERROR: Unable to locate stack group for group: " + group_id)
            raise StackException(AimErrorCode.Unknown)


        s3_client = self.account_ctx.get_aws_client('s3')
        bucket_name = self.get_bucket_name()
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

    def resolve_ref(self, ref):
        if ref.last_part == 'arn':
            return self.get_bucket_arn()
        elif ref.last_part == 'name':
            return self.get_bucket_name()
        else:
            return self.bucket_context['config']

class S3Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "S3",
                         "Resource")

        #self.aim_ctx.log("S3 Service: Configuration: %s" % (name))
        self.contexts = {}
        self.init_s3_resource_done = False

    def init_bucket_environments(self, s3_env_map, stack_tags):
        for env_id, env_config in s3_env_map.items():
            # Each bucket gets its own stack
            for bucket_id, bucket_config in env_config['buckets']:
                resource_ref = 's3.buckets.{0}.{1}.{2}'.format(env_config['account_ctx'].get_name(), env_config['region'], bucket_id)
                env_stack_group = S3StackGroup( self.aim_ctx,
                                                env_config['account_ctx'],
                                                env_config['region'],
                                                'bucket',
                                                self,
                                                resource_ref,
                                                stack_hooks=None)
                self.init_context(  env_config['account_ctx'],
                                    env_config['region'],
                                    resource_ref,
                                    env_stack_group,
                                    stack_tags )
                self.add_bucket(resource_ref,
                                env_config['region'],
                                bucket_id,
                                None,
                                'aim-s3',
                                None,
                                bucket_config,
                                None)


    def init_s3_resource(self, controller_args, stack_tags):
        if self.init_s3_resource_done == True:
            return
        self.init_s3_resource_done = True
        s3_env_map = {}
        for bucket_id in self.aim_ctx.project['s3'].buckets.keys():
            bucket_config = self.aim_ctx.project['s3'].buckets[bucket_id]
            account_ctx = self.aim_ctx.get_account_context(account_ref=bucket_config.account)
            region = bucket_config.region
            s3_env_id = '-'.join([account_ctx.get_name(), region])
            if s3_env_id not in s3_env_map.keys():
                s3_env_config = {
                    'id': s3_env_id,
                    'account_ctx': account_ctx,
                    'region': region,
                    'buckets': [] # Array of [[bucket_id, bucket_config],...]
                }
                s3_env_map[s3_env_id] = s3_env_config
            s3_env_map[s3_env_id]['buckets'].append([bucket_id, bucket_config])

        self.init_bucket_environments(s3_env_map, stack_tags)

    def init(self, controller_args):
        if controller_args != None:
            self.init_s3_resource(controller_args, stack_tags=None)

    def init_context(self, account_ctx, region, resource_ref, stack_group, stack_tags):
        if resource_ref not in self.contexts.keys():
            self.contexts[resource_ref] = S3Context(self.aim_ctx, account_ctx, region, self, stack_group, resource_ref, stack_tags)

    def add_bucket(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].add_bucket(*args, **kwargs)

    def add_bucket_policy(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].add_bucket_policy(*args, **kwargs)

    def add_stack_hooks(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].add_stack_hooks(*args, **kwargs)

    def get_bucket_arn(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].get_bucket_arn(*args, **kwargs)

    def get_bucket_name(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].get_bucket_name(*args, **kwargs)

    def empty_bucket(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].empty_bucket(*args, **kwargs)

    def get_region(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].empty_bucket(*args, **kwargs)

    def validate(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].validate()
        elif resource_ref == None:
            for s3_context in self.contexts.values():
                s3_context.validate()

    def provision(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].provision()
        elif resource_ref == None:
            for s3_context in self.contexts.values():
                s3_context.provision()

    def delete(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].delete()
        elif resource_ref == None:
            for s3_context in self.contexts.values():
                s3_context.delete()

    def get_stack_from_ref(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].get_stack_from_ref(*args, **kwargs)

    def get_value_from_ref(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].get_value_from_ref(*args, **kwargs)
