from paco.application.res_engine import ResourceEngine
from paco.aws_api.iam.user import IAMUserClient
from paco.core.yaml import YAML
from paco.core.exception import PacoStateError
from paco.models.references import Reference
from paco.utils import md5sum
import paco.cftemplates.iamuser
import copy
import json


yaml=YAML()
yaml.default_flow_sytle = False

class IAMUserResourceEngine(ResourceEngine):

    def init_resource(self):
        # IAM User
        if self.resource.account != None:
            self.account_ctx = self.paco_ctx.get_account_context(account_ref=self.resource.account)

        self.iamuser_stack = self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.iamuser.IAMUser,
            stack_tags=self.stack_tags,
            account_ctx=self.account_ctx
        )

        # Stack hooks for managing access keys
        if self.resource.is_enabled():
            for hook_action in ['create', 'update']:
                self.iamuser_stack.hooks.add(
                    name='IAMUser-AccessKey',
                    stack_action=hook_action,
                    stack_timing='post',
                    hook_method=self.iam_user_access_keys_hook,
                    cache_method=self.iam_user_access_keys_hook_cache_id,
                    hook_arg=self.resource
                )

    def iam_user_access_keys_hook(self, hook, iamuser):
        "Manage the IAM User's Access Keys"
        access = iamuser.programmatic_access
        if access == None: return

        username = self.iamuser_stack.get_outputs_value(
            self.iamuser_stack.get_outputs_key_from_ref(Reference(self.resource.paco_ref + '.username'))
        )
        iamuser_client = IAMUserClient(self.account_ctx, self.aws_region, username)

        # enable or disable existing Access Keys
        if not iamuser.is_enabled() or access.enabled == False:
            iamuser_client.disable_access_keys()
            return
        iamuser_client.enable_access_keys()

        # Get list of access keys and load their versions
        keys_meta = iamuser_client.list_access_keys()
        old_keys = {
            '1': None,
            '2': None,
        }
        statename = md5sum(str_data=username)
        s3key = f"IAMUser/{statename}"
        api_key_state = self.paco_ctx.paco_buckets.get_object(s3key, self.account_ctx, self.aws_region)
        if api_key_state == None:
            api_key_state = {}
        else:
            api_key_state = json.loads(api_key_state.decode("utf-8"))
        start_state = copy.copy(api_key_state)

        for key_meta in keys_meta['AccessKeyMetadata']:
            key_info = api_key_state.get(key_meta['AccessKeyId'], None)
            if key_info == None:
                print(f"Creating missing KeyNum AccessKeyMetadata for: {username} + {key_meta['AccessKeyId']}")
                api_key_state[key_meta['AccessKeyId']] = {}
                key_num = str(keys_meta['AccessKeyMetadata'].index(key_meta) + 1)
                api_key_state[key_meta['AccessKeyId']]['KeyNum'] = key_num
                api_key_state[key_meta['AccessKeyId']]['Version'] = getattr(access, f'access_key_{key_num}_version')
            key_num = api_key_state[key_meta['AccessKeyId']]['KeyNum']
            key_version = api_key_state[key_meta['AccessKeyId']]['Version']
            old_keys[key_num] = {
                'access_key_id': key_meta['AccessKeyId'],
                'version': int(key_version),
                'key_num': key_num,
            }

        # Loop through user configuration and update keys
        for key_num in ['1', '2']:
            new_key_version = getattr(access, f'access_key_{key_num}_version')
            if old_keys[key_num] == None and new_key_version > 0:
                access_key_id = iamuser_client.create_access_key(key_num)
                api_key_state[access_key_id] = {"KeyNum": key_num, "Version": new_key_version}
            elif old_keys[key_num] != None and new_key_version == 0:
                access_key_id = old_keys[key_num]['access_key_id']
                iamuser_client.delete_access_key(key_num, access_key_id)
                del api_key_state[access_key_id]
            elif old_keys[key_num] != None and old_keys[key_num]['version'] != new_key_version:
                old_access_key_id = old_keys[key_num]['access_key_id']
                access_key_id = iamuser_client.rotate_access_key(new_key_version, old_access_key_id)
                del api_key_state[old_access_key_id]
                api_key_state[access_key_id] = {"KeyNum": key_num, "Version": new_key_version}

        # save updated api_key_state
        if start_state != api_key_state:
            self.paco_ctx.paco_buckets.put_object(s3key, json.dumps(api_key_state), self.account_ctx, self.aws_region)

    def iam_user_access_keys_hook_cache_id(self, hook, iamuser):
        "Cache value for AWS Access Key"
        cache_data = "AccessKeysCacheId"
        if iamuser.programmatic_access != None:
            cache_data += str(iamuser.programmatic_access.enabled)
            cache_data += str(iamuser.programmatic_access.access_key_1_version)
            cache_data += str(iamuser.programmatic_access.access_key_2_version)

        cache_id = md5sum(str_data=cache_data)
        return cache_id
