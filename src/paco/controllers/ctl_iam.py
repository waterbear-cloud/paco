import click
import os
import time
import paco
from paco.cftemplates import IAMRoles, IAMManagedPolicies,IAMUsers, IAMUserAccountDelegates
from paco.controllers.controllers import Controller
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.core.yaml import YAML, Ref, Sub
from paco.models.references import Reference
from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags, StackHooks
from paco.utils import md5sum

yaml=YAML(typ='safe')
#yaml.register_class(Ref)
#yaml.register_class(Sub)
#yaml.preserve_quotes = True
#yaml=YAML(typ="safe", pure=True)
#yaml.default_flow_sytle = False

class IAMUserStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, group_name, controller):
        super().__init__(
            paco_ctx,
            account_ctx,
            group_name,
            'User',
            controller
        )

class PolicyContext():
    def __init__(
        self,
        paco_ctx, account_ctx, region,
        group_id, policy_id,
        policy_ref,
        policy_config_yaml,
        parent_config,
        stack_group,
        template_params,
        stack_tags,
        change_protected = False
    ):
        self.paco_ctx = paco_ctx
        self.account_ctx = account_ctx
        self.region = region
        self.group_id = group_id
        self.name = None
        self.arn = None
        self.policy_id = policy_id
        self.policy_ref = policy_ref
        self.policy_config_yaml = policy_config_yaml
        self.stack_group = stack_group
        self.stack_tags = stack_tags
        self.policy_template = None
        self.policy_stack = None
        self.template_params = template_params
        self.change_protected = change_protected
        self.policy_context = {}
        policy_config_dict = yaml.load(self.policy_config_yaml)
        self.policy_config = paco.models.iam.ManagedPolicy(policy_id, parent_config)
        paco.models.loader.apply_attributes_from_config(self.policy_config, policy_config_dict)
        self.init_policy()

    def init_policy(self):
        self.policy_config.resolve_ref_obj = self
        policy_context = {
            'id': self.policy_id,
            'config': self.policy_config,
            'ref': self.policy_ref,
            'template_params': self.template_params
        }
        policy_stack_tags = StackTags(self.stack_tags)
        policy_stack_tags.add_tag('Paco-IAM-Resource-Type', 'ManagedPolicy')
        policy_context['template'] = IAMManagedPolicies(
            self.paco_ctx,
            self.account_ctx,
            self.region,
            self.stack_group,
            policy_stack_tags,
            policy_context,
            self.group_id,
            self.policy_id,
            change_protected=self.change_protected
        )
        policy_context['stack'] = policy_context['template'].stack
        self.name = policy_context['template'].gen_policy_name(self.policy_id)
        self.arn = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.name)
        self.policy_context[self.policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])


class RoleContext():
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        region,
        group_id,
        role_id,
        role_ref,
        role_config,
        stack_group,
        template_params,
        stack_tags,
        change_protected=False
    ):
        self.paco_ctx = paco_ctx
        self.account_ctx = account_ctx
        self.region = region
        self.group_id = group_id
        self.role_name = None
        self.role_id = role_id
        self.role_ref = role_ref
        self.role_config = role_config
        self.stack_group = stack_group
        self.stack_tags = stack_tags
        self.role_template = None
        self.role_stack = None
        self.template_params = template_params
        self.change_protected = change_protected
        self.policy_context = {}
        self.init_role()

    def aws_name(self):
        return self.role_ref

    def get_aws_name(self):
        return self.aws_name()

    def get_role(self, role_id=None, role_ref=None):
        role_by_id = None
        role_by_ref = None
        if role_id !=  None:
            for role in self.roles:
                if role.id == role_id:
                    role_by_id = role
                    break
        if role_ref != None:
            role_by_ref = role[role_ref]

        if role_by_id != None and role_by_ref != None:
            if role_by_id.id == role_by_ref.id:
                return role_by_id
            else:
                # You specified both role_id and role_ref
                # but they each returned different results.
                raise StackException(PacoErrorCode)
        elif role_by_id != None:
            return role_by_id

        return role_by_ref

    def add_managed_policy(
        self,
        parent_config,
        group_id,
        policy_id,
        policy_ref,
        policy_config_yaml=None,
        template_params=None,
        change_protected=False
    ):
        if policy_ref in self.policy_context.keys():
            print("Managed policy already exists: %s" % (policy_ref) )
            raise StackException(PacoErrorCode.Unknown)

        policy_config_dict = yaml.load(policy_config_yaml)
        policy_config_dict['roles'] = [self.role_name]
        policy_config = paco.models.iam.ManagedPolicy(policy_id, parent_config)
        paco.models.loader.apply_attributes_from_config(policy_config, policy_config_dict)
        policy_config.resolve_ref_obj = self
        policy_context = {
            'id': policy_id,
            'config': policy_config,
            'ref': policy_ref,
            'template_params': template_params
        }
        policy_stack_tags = StackTags(self.stack_tags)
        policy_stack_tags.add_tag('Paco-IAM-Resource-Type', 'ManagedPolicy')
        policy_context['template'] = IAMManagedPolicies(
            self.paco_ctx,
            self.account_ctx,
            self.region,
            self.stack_group,
            policy_stack_tags,
            policy_context,
            self.group_id,
            policy_id,
            change_protected
        )
        policy_context['stack'] = policy_context['template'].stack
        self.policy_context['name'] = policy_context['template'].gen_policy_name(policy_id)
        self.policy_context['arn'] = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.policy_context['name'])
        self.policy_context[policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])

    def init_role(self):
        role_stack_tags = StackTags(self.stack_tags)
        role_stack_tags.add_tag('Paco-IAM-Resource-Type', 'Role')
        self.role_config.resolve_ref_obj = self
        self.role_template = IAMRoles(
            self.paco_ctx,
            self.account_ctx,
            self.region,
            self.stack_group,
            role_stack_tags,
            self.role_ref,
            self.group_id,
            self.role_id,
            self.role_config,
            self.template_params,
            self.change_protected
        )
        self.role_stack = self.role_template.stack
        self.role_name = self.role_template.gen_iam_role_name("Role", self.role_id)
        self.role_arn = "arn:aws:iam::{0}:role/{1}".format(self.account_ctx.get_id(), self.role_name)
        role_profile_name = self.role_template.gen_iam_role_name("Profile", self.role_id)
        self.role_profile_arn = "arn:aws:iam::{0}:instance-profile/{1}".format(self.account_ctx.get_id(), role_profile_name)
        self.stack_group.add_stack_order(self.role_stack)

    def get_role_arn(self):
        return self.role_arn

    def resolve_ref(self, ref):
        if ref.ref.startswith(self.role_ref):
            if ref.resource_ref == 'profile.arn':
                return self.role_profile_arn
            elif ref.resource_ref == 'arn':
                return self.role_arn
            elif ref.resource_ref == 'name':
                return self.role_name
        else:
            for policy_ref in self.policy_context.keys():
                if ref.ref.startswith(policy_ref) == False:
                    continue
                if ref.resource_ref == 'arn':
                    return self.policy_context[policy_ref]['arn']
                elif ref.resource_ref == 'name':
                    return self.policy_context[policy_ref]['name']
        return None


class IAMController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx,
                         "Resource",
                         "IAM")

        self.role_context = {}
        self.policy_context = {}
        self.iam_config = self.paco_ctx.project['resource']['iam']
        self.iam_user_stack_groups = {}
        self.iam_user_access_keys_sdb_domain = 'Paco-IAM-Users-Access-Keys-Meta'
        self.init_done = False
        #self.paco_ctx.log("IAM Service: Configuration: %s" % (name))

    # Administrator
    def init_custompolicy_permission(self, permission_config, permissions_by_account):
        """
        Adds each permission config to a map of permissions by account. This map
        is used to determines the policies a user will have created in each
        account.
        """
        accounts = permission_config.accounts
        if 'all' in accounts:
            accounts = self.paco_ctx.project['accounts'].keys()

        for account_name in accounts:
            permissions_by_account[account_name].append(permission_config)

    # CodeCommit
    def init_codecommit_permission(self, permission_config, permissions_by_account):
        for repo_config in permission_config.repositories:
            # Account Delegate Role
            if repo_config.console_access_enabled == True:
                codecommit_config = self.paco_ctx.get_ref(repo_config.codecommit)
                if codecommit_config.is_enabled():
                    account_ref = codecommit_config.account
                    account_name = self.paco_ctx.get_ref(account_ref+'.name')
                    if permission_config not in permissions_by_account[account_name]:
                        permissions_by_account[account_name].append(permission_config)

    # Administrator
    def init_administrator_permission(self, permission_config, permissions_by_account):
        """
        Adds each permission config to a map of permissions by account. This map
        is used to determines the policies a user will have created in each
        account.
        """
        accounts = permission_config.accounts
        if 'all' in accounts:
            accounts = self.paco_ctx.project['accounts'].keys()

        for account_name in accounts:
            permissions_by_account[account_name].append(permission_config)

    # CodeBuild
    def init_codebuild_permission(self, permission_config, permissions_by_account):
        """
        Iterates over each codebuild reference and adds its permission config
        to the map of permissions by account.
        """
        for resource in permission_config.resources:
            codebuild_ref = Reference(resource.codebuild)
            account_ref = 'paco.ref ' + '.'.join(codebuild_ref.parts[:-2]) + '.configuration.account'
            account_ref = self.paco_ctx.get_ref(account_ref)
            account_name = self.paco_ctx.get_ref(account_ref + '.name')
            if permission_config not in permissions_by_account[account_name]:
                permissions_by_account[account_name].append(permission_config)

    def get_sdb_attribute_value(self, sdb_client, sdb_domain, item_name, attribute_name):
        attributes = sdb_client.get_attributes(
            DomainName=sdb_domain,
            ItemName=item_name,
            AttributeNames=[ attribute_name ],
            ConsistentRead=True
        )
        #print("SDB: Get: {}: {}: {}".format(sdb_domain, item_name, attribute_name))
        if attributes == None or 'Attributes' not in attributes.keys():
            return None

        for attribute in attributes['Attributes']:
            if attribute['Name'] == attribute_name:
                return attribute['Value']
        return None

    def put_sdb_attribute(self, sdb_client, sdb_domain, item_name, attribute_name, value):
        sdb_client.put_attributes(
            DomainName=sdb_domain,
            ItemName=item_name,
            Attributes=[
                {
                    'Name': attribute_name,
                    'Value': str(value),
                    'Replace': True
                }
            ]
        )
        #print("SDB: Put: {}: {}: {}: {}".format(sdb_domain, item_name, attribute_name, str(value)))

    def delete_sdb_attribute(self, sdb_client, sdb_domain, item_name, attribute_name, value):
        sdb_client.delete_attributes(
            DomainName=sdb_domain,
            ItemName=item_name,
            Attributes=[
                {
                    'Name': attribute_name,
                    'Value': str(value)
                }
            ]
        )
        #print("SDB: Delete: {}".format(attribute_name))

    def iam_user_create_access_key(self, username, key_num, key_version, iam_client, sdb_client):
        sdb_item_name = md5sum(str_data=username)
        access_key_meta = iam_client.create_access_key(
            UserName=username
        )
        access_key_id = access_key_meta['AccessKey']['AccessKeyId']
        secret_key = access_key_meta['AccessKey']['SecretAccessKey']
        version_attribute = access_key_meta['AccessKey']['AccessKeyId']+'Version'
        key_num_attribute = access_key_meta['AccessKey']['AccessKeyId']+'KeyNum'

        self.put_sdb_attribute(
            sdb_client,
            self.iam_user_access_keys_sdb_domain,
            sdb_item_name,
            version_attribute,
            key_version
        )
        self.put_sdb_attribute(
            sdb_client,
            self.iam_user_access_keys_sdb_domain,
            sdb_item_name,
            key_num_attribute,
            key_num
        )
        print("{}: Created Access Key {}: Key Id    : {}".format(username, key_num, access_key_id))
        print("{}:                    {}: Secret Key: {}".format(username, key_num, secret_key))

    def iam_user_delete_access_key(self, username, key_config, iam_client, sdb_client):
        access_key_id = key_config['access_key_id']
        sdb_item_name = md5sum(str_data=username)
        iam_client.delete_access_key(
            UserName=username,
            AccessKeyId=access_key_id,
        )
        version_attribute = [access_key_id+'Version', key_config['version']]
        key_num_attribute = [access_key_id+'KeyNum', key_config['key_num']]

        for attribute_conf in [version_attribute, key_num_attribute]:
            self.delete_sdb_attribute(
                sdb_client,
                self.iam_user_access_keys_sdb_domain,
                sdb_item_name,
                attribute_conf[0],
                attribute_conf[1],
            )

        print("{}: Deleted Access Key {}: Key Id    : {}".format(username, key_config['key_num'], access_key_id))

    def iam_user_rotate_access_key(self, username, new_key_version, old_key_config, iam_client, sdb_client):
        key_num = old_key_config['key_num']
        print("{}: Rotating Access Key {}: Begin".format(username, key_num))
        self.iam_user_delete_access_key(username, old_key_config, iam_client, sdb_client)
        self.iam_user_create_access_key(username, key_num, new_key_version, iam_client, sdb_client)
        print("{}: Rotating Access Key {}: End".format(username, key_num))

    def iam_user_enable_access_keys(self, iam_client, user_config):
        keys_meta = iam_client.list_access_keys(
            UserName=user_config.username
        )
        for key_meta in keys_meta['AccessKeyMetadata']:
            if key_meta['Status'] == 'Inactive':
                print("{}: Modifying Access Key Status to: Active: {}".format(user_config.username, key_meta['AccessKeyId']))
                iam_client.update_access_key(
                    UserName=user_config.username,
                    AccessKeyId=key_meta['AccessKeyId'],
                    Status='Active'
                )


    def iam_user_disable_access_keys(self, iam_client, user_config):
        keys_meta = iam_client.list_access_keys(
            UserName=user_config.username
        )
        for key_meta in keys_meta['AccessKeyMetadata']:
            if key_meta['Status'] == 'Active':
                print("{}: Modifying Access Key Status to: Inctive: {}".format(user_config.username, key_meta['AccessKeyId']))
                iam_client.update_access_key(
                    UserName=user_config.username,
                    AccessKeyId=key_meta['AccessKeyId'],
                    Status='Inactive'
                )

    def iam_user_access_keys_hook(self, hook, user_config):
        # Access Keys
        if user_config.is_enabled() == False:
            return
        master_account_ctx = self.paco_ctx.get_account_context(account_ref='paco.ref accounts.master')
        iam_client = master_account_ctx.get_aws_client('iam')
        access_key_config = user_config.programmatic_access
        if access_key_config and access_key_config.enabled == True:
            self.iam_user_enable_access_keys(iam_client, user_config)
            # Create SDB Domain for Account wide access keys
            # Use us-west-2 region as ca-central-1 does not support SDB yet and the
            # region does not mattter here.
            if master_account_ctx.config.region == 'ca-central-1':
                sdb_region = 'us-west-2'
            else:
                sdb_region = master_account_ctx.config.region
            sdb_client = master_account_ctx.get_aws_client('sdb', aws_region=sdb_region)
            sdb_domain = self.iam_user_access_keys_sdb_domain
            sdb_item_name = md5sum(str_data=user_config.username)
            sdb_client.create_domain(
                DomainName=sdb_domain
            )
            # Get list of access keys and load their versions
            keys_meta = iam_client.list_access_keys(
                UserName=user_config.username
            )
            old_keys = {
                '1': None,
                '2': None
            }
            for key_meta in keys_meta['AccessKeyMetadata']:
                key_num = self.get_sdb_attribute_value(sdb_client, sdb_domain, sdb_item_name, key_meta['AccessKeyId']+'KeyNum')
                if key_num == None:
                    print("Creating missing KeyNum Access Key Meta data for: {} + {}".format(user_config.username, key_meta['AccessKeyId']))
                    key_num = str(keys_meta['AccessKeyMetadata'].index(key_meta)+1)
                    self.put_sdb_attribute(
                        sdb_client,
                        sdb_domain,
                        sdb_item_name,
                        key_meta['AccessKeyId']+'KeyNum',
                        key_num
                    )
                key_version = self.get_sdb_attribute_value(sdb_client, sdb_domain, sdb_item_name, key_meta['AccessKeyId']+'Version')
                if key_version == None:
                    print("Creating missing Version Access Key Meta data for: {} + {}".format(user_config.username, key_meta['AccessKeyId']))
                    key_version = getattr(access_key_config, 'access_key_{}_version'.format(key_num))
                    self.put_sdb_attribute(
                        sdb_client,
                        sdb_domain,
                        sdb_item_name,
                        key_meta['AccessKeyId']+'Version',
                        key_version
                    )
                if key_num == None or key_version == None:
                    continue
                key_config = {
                    'access_key_id': key_meta['AccessKeyId'],
                    'version': int(key_version),
                    'key_num': key_num
                }
                if old_keys[key_num] != None:
                    print("Error: Cur keys have already been set.")
                    raise StackException(PacoErrorCode.Unknown, message='Cur keys have already been set')
                old_keys[key_num] = key_config

            # Loop through user configuration and update keys
            for key_num in ['1', '2']:
                new_key_version = getattr(access_key_config, 'access_key_{}_version'.format(key_num))
                if old_keys[key_num] == None and new_key_version > 0:
                    self.iam_user_create_access_key(
                        user_config.username,
                        key_num, new_key_version,
                        iam_client,
                        sdb_client
                    )
                elif old_keys[key_num] != None and new_key_version == 0:
                    self.iam_user_delete_access_key(
                        user_config.username,
                        old_keys[key_num],
                        iam_client,
                        sdb_client
                    )
                elif old_keys[key_num] != None and old_keys[key_num]['version'] != new_key_version:
                    self.iam_user_rotate_access_key(
                        user_config.username,
                        new_key_version,
                        old_keys[key_num],
                        iam_client,
                        sdb_client,
                    )
        else:
            self.iam_user_disable_access_keys(iam_client, user_config)

    def iam_user_access_keys_hook_cache_id(self, hook, user_config):
        cache_data = "AccessKeysCacheId"
        if user_config.programmatic_access != None:
            access_config = user_config.programmatic_access
            cache_data += str(access_config.enabled)
            cache_data += str(access_config.access_key_1_version)
            cache_data += str(access_config.access_key_2_version)

        cache_id = md5sum(str_data=cache_data)
        return cache_id

    def init_users(self, model_obj):
        self.stack_group_filter = model_obj.paco_ref_parts
        master_account_ctx = self.paco_ctx.get_account_context(account_ref='paco.ref accounts.master')
        # StackGroup
        for account_name in self.paco_ctx.project['accounts'].keys():
            account_ctx = self.paco_ctx.get_account_context('paco.ref accounts.'+account_name)
            self.iam_user_stack_groups[account_name] = IAMUserStackGroup(self.paco_ctx, account_ctx, account_name, self)

        stack_hooks = StackHooks(self.paco_ctx)
        for user_name in self.iam_config.users.keys():
            user_config = self.iam_config.users[user_name]
            # Stack hooks for managing access keys
            for hook_action in ['create', 'update']:
                stack_hooks.add(
                    name='IAMUserAccessKeys',
                    stack_action=hook_action,
                    stack_timing='post',
                    hook_method=self.iam_user_access_keys_hook,
                    cache_method=self.iam_user_access_keys_hook_cache_id,
                    hook_arg=user_config
                )

        config_ref = 'resource.iam.users'
        IAMUsers(
            self.paco_ctx,
            master_account_ctx,
            master_account_ctx.config.region,
            self.iam_user_stack_groups['master'],
            None, # stack_tags,
            stack_hooks,
            self.iam_config.users,
            config_ref
        )

        for user_name in self.iam_config.users.keys():
            user_config = self.iam_config.users[user_name]

            # Build a list of permissions for each account
            permissions_by_account = {}
            # Initialize permission_by_account for all accounts
            for account_name in self.paco_ctx.project['accounts'].keys():
                permissions_by_account[account_name] = []

            for permission_name in user_config.permissions.keys():
                permission_config = user_config.permissions[permission_name]
                init_method = getattr(self, "init_{}_permission".format(permission_config.type.lower()))
                init_method(permission_config, permissions_by_account)

            # Give access to accounts the user has explicit access to

            for account_name in self.paco_ctx.project['accounts'].keys():
                account_ctx = self.paco_ctx.get_account_context('paco.ref accounts.'+account_name)
                config_ref = 'resource.iam.users.'+user_name
                # Template and stack
                IAMUserAccountDelegates(
                    self.paco_ctx,
                    account_ctx,
                    master_account_ctx.config.region,
                    self.iam_user_stack_groups[account_name],
                    None, # stack_tags
                    [StackOrder.PROVISION ,StackOrder.WAITLAST],
                    user_config,
                    permissions_by_account[account_name],
                    config_ref
                )


        # Create the IAM Users
        #iam_user(self.iam_config.users)
            # Create IAMUser
            #   - Access Key
            #   - Console Access: Enough to be able to login and set MFA
            #   - user_config.accounts: Create cross account access roles
            #   - Prompt for and set password
            #
            # Iterate through permissions
            #   - CodeCommit
            #     - Get repository account and create a policy and attach
            #       it to the user's account delegatge role
            #     - Manage SSH keys


    def init(self, command=None, model_obj=None):
        if model_obj == None:
            return
        if self.init_done == True:
            return
        self.init_done = True
        if model_obj.paco_ref_parts.startswith('resource.iam') == False:
            return
        if len(model_obj.paco_ref_list) == 2 or model_obj.paco_ref_list[2] == 'users':
            self.stack_group_filter = model_obj.paco_ref_parts
            self.init_users(model_obj)

    def create_managed_policy(
        self,
        paco_ctx, account_ctx, region,
        group_id, policy_id,
        policy_ref,
        policy_config_yaml,
        parent_config,
        stack_group,
        template_params,
        stack_tags,
        change_protected=False
    ):
        if policy_ref not in self.policy_context.keys():
            self.policy_context[policy_ref] = PolicyContext(
                paco_ctx=self.paco_ctx,
                account_ctx=account_ctx,
                region=region,
                group_id=group_id,
                policy_id=policy_id,
                policy_ref=policy_ref,
                policy_config_yaml=policy_config_yaml,
                parent_config=parent_config,
                stack_group=stack_group,
                template_params=template_params,
                stack_tags=stack_tags,
                change_protected=change_protected
            )
        else:
            print("Managed Policy already exists: %s" % (policy_ref))
            raise StackException(PacoErrorCode.Unknown)

    def add_managed_policy(self, role_ref, *args, **kwargs):
        return self.role_context[role_ref].add_managed_policy(*args, **kwargs)

    def add_role(
        self,
        paco_ctx,
        account_ctx,
        region,
        group_id,
        role_id,
        role_ref,
        role_config,
        stack_group,
        template_params,
        stack_tags,
        change_protected=False
    ):
        if role_ref not in self.role_context.keys():
            self.role_context[role_ref] = RoleContext(
                paco_ctx=self.paco_ctx,
                account_ctx=account_ctx,
                region=region,
                group_id=group_id,
                role_id=role_id,
                role_ref=role_ref,
                role_config=role_config,
                stack_group=stack_group,
                template_params=template_params,
                stack_tags=stack_tags,
                change_protected=change_protected
            )
        else:
            print("Role already exists: %s" % (role_ref))
            raise StackException(PacoErrorCode.Unknown)

    def role_arn(self, role_ref):
        role_ref = role_ref.replace('paco.ref ', '')
        return self.role_context[role_ref].role_arn

    def role_profile_arn(self, role_ref):
        role_ref = role_ref.replace('paco.ref ', '')
        return self.role_context[role_ref].role_profile_arn

    def validate(self):
        self.iam_user_stack_groups['master'].validate()
        for account_name in self.iam_user_stack_groups.keys():
            if account_name == 'master':
                continue
            stack_group = self.iam_user_stack_groups[account_name].validate()

    def provision(self):
        # Master first due to IAM Users needing to be created first
        # before account delegate roles
        self.iam_user_stack_groups['master'].provision()
        for account_name in self.iam_user_stack_groups.keys():
            if account_name == 'master':
                continue
            self.iam_user_stack_groups[account_name].provision()

    def delete(self):
        #print("Not doing anything because this deletes all of the users.")
        #print("TODO: Implement a per user delete!")
        print("\nIAM User delete is unavailable. Please disable users to remove them.")
        return
        for account_name in self.iam_user_stack_groups.keys():
            if account_name == 'master':
                continue
            self.iam_user_stack_groups[account_name].delete()
        self.iam_user_stack_groups['master'].delete()
