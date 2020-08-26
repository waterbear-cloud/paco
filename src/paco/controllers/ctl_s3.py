from paco.core.exception import StackException, PacoBucketExists
from paco.core.exception import PacoErrorCode
from paco.models import schemas
from paco.models import references
from paco.models.locations import get_parent_by_interface
from paco.stack import StackGroup
from paco.controllers.controllers import Controller
from botocore.exceptions import ClientError
from paco.models import vocabulary
from paco.stack import StackOrder, Stack, StackGroup, StackHooks, StackTags
import botocore
import copy
import os
import paco.cftemplates


class S3StackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        region,
        group_name,
        controller,
        resource_ref,
        stack_hooks=None
    ):
        aws_name = group_name
        super().__init__(
            paco_ctx,
            account_ctx,
            group_name,
            aws_name,
            controller
        )
        self.stack_hooks = stack_hooks

class S3Context():
    def __init__(self, paco_ctx, account_ctx, region, controller, stack_group, resource_ref, stack_tags):
        self.paco_ctx = paco_ctx
        self.stack_group = stack_group
        self.controller = controller
        self.region = region
        self.account_ctx = account_ctx
        self.resource_ref = resource_ref
        self.stack_tags = stack_tags
        self.bucket_context = {
            'group_id': None,
            'config': None,
            'ref': resource_ref,
            'stack': None
        }

    def add_stack_hooks(self, stack_hooks):
        if self.bucket_context['stack'] == None:
            return
        self.bucket_context['stack'].add_hooks(stack_hooks)

    def add_stack(
        self,
        bucket_policy_only=False,
        stack_hooks=None,
        new_stack=True,
        stack_tags=None,
    ):
        stack = self.stack_group.add_new_stack(
            self.region,
            self.bucket_context['config'],
            paco.cftemplates.S3,
            account_ctx=self.account_ctx,
            stack_tags=stack_tags,
            stack_hooks=stack_hooks,
            extra_context={'bucket_context': self.bucket_context, 'bucket_policy_only': bucket_policy_only}
        )
        if bucket_policy_only == False:
            if self.bucket_context['stack'] != None:
                raise StackException(PacoErrorCode.Unknown)
            self.bucket_context['stack'] = stack

    def add_bucket(
        self,
        bucket,
        bucket_name_prefix=None,
        bucket_name_suffix=None,
        stack_hooks=None,
        change_protected=False
    ):
        "Add a bucket: will create a stack and stack hooks as needed"
        if self.bucket_context['config'] != None:
            raise PacoBucketExists("Bucket already exists: %s" % (self.resource_ref))

        bucket.bucket_name_prefix = bucket_name_prefix
        bucket.bucket_name_suffix = bucket_name_suffix
        res_group = get_parent_by_interface(bucket, schemas.IResourceGroup)
        if res_group != None:
            self.bucket_context['group_id'] = res_group.name
        self.bucket_context['config'] = bucket
        self.bucket_context['ref'] = self.resource_ref
        bucket.resolve_ref_obj = self

        if bucket.external_resource == True:
            # if the bucket already exists, do not create a stack for it
            pass
        else:
            if change_protected == False:
                if stack_hooks == None:
                    stack_hooks = StackHooks()
                # S3 Delete on Stack Delete hook
                stack_hooks.add(
                    'S3StackGroup', 'delete', 'pre',
                    self.stack_hook_pre_delete, None, self.bucket_context
                )
                self.add_stack(
                    bucket_policy_only=False,
                    stack_hooks=stack_hooks,
                    stack_tags=self.stack_tags,
                )

    def add_bucket_policy(self, policy_dict, stack_hooks=None, new_stack=True):
        bucket_config = self.bucket_context['config']
        # XXX: Disabled: Bucket policies are overwritten when updated with a new stack.
        #                This means we want all of the policies previously provisioned.
        # If this is a new stack, mark previous policies as processed so they
        # are not written twice.
        #if new_stack == True:
            #for policy in bucket_config.policy:
            #    policy.processed = True
        bucket_config.add_policy(policy_dict)
        self.add_stack(
            bucket_policy_only=True,
            stack_hooks=stack_hooks,
            stack_tags=self.stack_tags
        )

    def get_bucket_arn(self):
        return 'arn:aws:s3:::' + self.bucket_context['config'].get_bucket_name()

    def get_bucket_url(self):
        return self.bucket_context['config'].get_bucket_name() + '.s3.amazonaws.com'

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

    def stack_hook_pre_delete(self, hook, hook_arg):
        "Empty the S3 Bucket if enabled"
        bucket_context = hook_arg
        s3_config = bucket_context['config']
        s3_resource = self.account_ctx.get_aws_resource('s3', self.region)
        deletion_policy = s3_config.deletion_policy
        bucket_name = s3_config.get_bucket_name()
        if deletion_policy == "delete":
            self.paco_ctx.log_action_col('Run', 'Hook', 'Delete', bucket_name)
            bucket = s3_resource.Bucket(bucket_name)
            try:
                bucket.object_versions.delete()
                bucket.objects.all().delete()
                bucket.delete()
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchBucket':
                    print("%s: %s" % (e.response['Error']['Code'], e.response['Error']['Message']))
                    raise StackException(PacoErrorCode.Unknown)
        else:
            self.paco_ctx.log_action_col('Run', 'Hook', 'Retain', bucket_name)

    def empty_bucket(self):
        if self.bucket_context == None:
            print(f"ctl_s3: empty_bucket: ERROR: Unable to locate stack group for group: {self.bucket_context['group_id']}")
            raise StackException(PacoErrorCode.Unknown)
        s3_client = self.account_ctx.get_aws_client('s3')
        bucket_name = self.bucket_context['config'].get_bucket_name()
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
            return self.bucket_context['config'].get_bucket_name()
        elif ref.last_part == 'url':
            return self.get_bucket_url()
        elif ref.last_part == 'origin_id':
            return self.bucket_context['stack']
        else:
            return self.bucket_context['config']

class S3Controller(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "S3", "Resource")
        self.contexts = {}
        self.init_s3_resource_done = False

    def init_s3_resource(self, bucket_list, stack_tags):
        "Init global S3 Buckets from resource/s3.yaml"
        if self.init_s3_resource_done == True:
            return
        self.init_s3_resource_done = True
        s3_env_map = {}
        s3resource = self.paco_ctx.project['resource']['s3']
        for bucket_id in bucket_list:
            bucket_config = s3resource.buckets[bucket_id]
            account_ctx = self.paco_ctx.get_account_context(account_ref=bucket_config.account)
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

        # initialize S3 Bucket stack groups
        for env_id, env_config in s3_env_map.items():
            for bucket_id, bucket_config in env_config['buckets']:
                env_stack_group = S3StackGroup(
                    self.paco_ctx,
                    env_config['account_ctx'],
                    env_config['region'],
                    'bucket',
                    self,
                    bucket_config.paco_ref,
                    stack_hooks=None
                )
                self.init_context(
                    env_config['account_ctx'],
                    env_config['region'],
                    bucket_config.paco_ref,
                    env_stack_group,
                    stack_tags
                )
                self.add_bucket(bucket_config)

    def resolve_ref(self, ref):
        "Find the bucket then call resolve_ref on it"
        buckets = self.paco_ctx.project['resource']['s3'].buckets
        return buckets[ref.parts[3]].resolve_ref(ref)

    def init(self, command=None, model_obj=None):
        "Init S3 Buckets"
        if model_obj != None:
            bucket_list = []
            if schemas.IS3Resource.providedBy(model_obj):
                bucket_list.extend(model_obj.buckets.keys())
            else:
                bucket_list.append(model_obj.name)
            self.init_s3_resource(bucket_list, stack_tags=None)
        # Set resolve_ref_obj for global buckets
        s3resource = self.paco_ctx.project['resource']['s3']
        s3resource.resolve_ref_obj = self

    def init_context(self, account_ctx, region, resource_ref, stack_group, stack_tags):
        if resource_ref.startswith('paco.ref '):
            resource_ref = resource_ref.replace('paco.ref ', '')
        if resource_ref not in self.contexts.keys():
            self.contexts[resource_ref] = S3Context(self.paco_ctx, account_ctx, region, self, stack_group, resource_ref, stack_tags)
            # Add an 'paco.ref ' key here so that we can take paco.ref's from the yaml
            # and still do a lookup on them
            self.contexts['paco.ref ' + resource_ref] = self.contexts[resource_ref]

    def context_list(self):
        "Returns contexts that do not include the redundant 'paco.ref ' prefixed keys."
        contexts = []
        for key, value in self.contexts.items():
            if key.startswith('paco.ref '):
                continue
            contexts.append(value)
        return contexts

    def add_bucket(self, bucket, config_ref=None, **kwargs):
        if config_ref:
            return self.contexts[config_ref].add_bucket(bucket, **kwargs)
        else:
            return self.contexts[bucket.paco_ref].add_bucket(bucket, **kwargs)

    def add_bucket_policy(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].add_bucket_policy(*args, **kwargs)

    def add_stack_hooks(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].add_stack_hooks(*args, **kwargs)

    def get_bucket_arn(self, resource_ref, *args, **kwargs):
        if not resource_ref.startswith('paco.ref '):
            resource_ref = 'paco.ref ' + resource_ref
        references.resolve_ref(resource_ref, self.paco_ctx.project)
        return self.contexts[resource_ref].get_bucket_arn(*args, **kwargs)

    def get_bucket_name(self, resource_ref, *args, **kwargs):
        self.contexts[resource_ref].bucket_context['config'].get_bucket_name()
        return self.contexts[resource_ref].bucket_context['config'].get_bucket_name()

    def empty_bucket(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].empty_bucket(*args, **kwargs)

    def get_region(self, resource_ref, *args, **kwargs):
        return self.contexts[resource_ref].empty_bucket(*args, **kwargs)

    def validate(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].validate()
        elif resource_ref == None:
            for s3_context in self.context_list():
                s3_context.validate()

    def provision(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].provision()
        elif resource_ref == None:
            for s3_context in self.context_list():
                s3_context.provision()

    def delete(self, resource_ref=None):
        if resource_ref != None and resource_ref in self.contexts:
            return self.contexts[resource_ref].delete()
        elif resource_ref == None:
            for s3_context in self.context_list():
                s3_context.delete()

