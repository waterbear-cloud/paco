import click
import os
import time
import aim
from aim.cftemplates import IAMRoles, IAMManagedPolicies,IAMUsers, IAMUserAccountDelegates
from aim.controllers.controllers import Controller
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.core.yaml import YAML
from aim.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags, StackHooks
from aim.utils import md5sum

yaml=YAML()
yaml.default_flow_sytle = False

class IAMUserStackGroup(StackGroup):
    def __init__(self, aim_ctx, account_ctx, group_name, controller):
        super().__init__(
            aim_ctx,
            account_ctx,
            group_name,
            'User',
            controller
        )

class PolicyContext():
    def __init__(self, aim_ctx, account_ctx, region, group_id, policy_id, policy_ref, policy_config_yaml, parent_config, stack_group, template_params, stack_tags):
        self.aim_ctx = aim_ctx
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
        self.policy_context = {}

        self.policy_context = {}

        policy_config_dict = yaml.load(self.policy_config_yaml)
        self.policy_config = aim.models.iam.ManagedPolicy(policy_id, parent_config)
        aim.models.loader.apply_attributes_from_config(self.policy_config, policy_config_dict)

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
        policy_stack_tags.add_tag('AIM-IAM-Resource-Type', 'ManagedPolicy')
        template_name = '-'.join([self.group_id, self.policy_id])
        policy_context['template'] = IAMManagedPolicies(self.aim_ctx,
                                                        self.account_ctx,
                                                        self.region,
                                                        self.stack_group,
                                                        policy_stack_tags,
                                                        policy_context,
                                                        template_name)

        policy_context['stack'] = policy_context['template'].stack

        self.name = policy_context['template'].gen_policy_name(self.policy_id)
        self.arn = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.name)

        self.policy_context[self.policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])


class RoleContext():
    def __init__(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params, stack_tags):
        self.aim_ctx = aim_ctx
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
                raise StackException(AimErrorCode)
        elif role_by_id != None:
            return role_by_id

        return role_by_ref

    def add_managed_policy(self,
                           parent_config,
                           group_id,
                           policy_id,
                           policy_ref,
                           policy_config_yaml=None,
                           template_params=None):

        if policy_ref in self.policy_context.keys():
            print("Managed policy already exists: %s" % (policy_ref) )
            raise StackException(AimErrorCode.Unknown)

        policy_config_dict = yaml.load(policy_config_yaml)
        policy_config_dict['roles'] = [self.role_name]
        policy_config = aim.models.iam.ManagedPolicy(policy_id, parent_config)
        aim.models.loader.apply_attributes_from_config(policy_config, policy_config_dict)
        policy_config.resolve_ref_obj = self
        policy_context = {
            'id': policy_id,
            'config': policy_config,
            'ref': policy_ref,
            'template_params': template_params
        }

        policy_stack_tags = StackTags(self.stack_tags)
        policy_stack_tags.add_tag('AIM-IAM-Resource-Type', 'ManagedPolicy')
        template_name = '-'.join([self.group_id, policy_id])
        policy_context['template'] = IAMManagedPolicies(self.aim_ctx,
                                                        self.account_ctx,
                                                        self.region,
                                                        self.stack_group,
                                                        policy_stack_tags,
                                                        policy_context,
                                                        template_name)

        policy_context['stack'] = policy_context['template'].stack

        self.policy_context['name'] = policy_context['template'].gen_policy_name(policy_id)
        self.policy_context['arn'] = "arn:aws:iam::{0}:policy/{1}".format(self.account_ctx.get_id(), self.policy_context['name'])

        self.policy_context[policy_ref] = policy_context
        self.stack_group.add_stack_order(policy_context['stack'])

    def init_role(self):
        role_stack_tags = StackTags(self.stack_tags)
        role_stack_tags.add_tag('AIM-IAM-Resource-Type', 'Role')
        self.role_config.resolve_ref_obj = self
        template_name = '-'.join([self.group_id, self.role_id])
        self.role_template = IAMRoles(self.aim_ctx,
                                      self.account_ctx,
                                      self.region,
                                      self.stack_group,
                                      role_stack_tags,
                                      template_name,
                                      self.role_ref,
                                      self.role_id,
                                      self.role_config,
                                      self.template_params)

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
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Resource",
                         "IAM")

        self.role_context = {}
        self.policy_context = {}
        self.iam_config = self.aim_ctx.project['iam']
        self.iam_user_stack_groups = {}
        self.iam_user_access_keys_sdb_domain = 'AIM-IAM-Users-Access-Keys-Meta'
        #self.aim_ctx.log("IAM Service: Configuration: %s" % (name))

    # CodeCommit
    def init_codecommit_permission(self, permission_config, permissions_by_account):
        for repo_config in permission_config.repositories:
            # Account Delegate Role
            if repo_config.console_access_enabled == True:
                codecommit_config = self.aim_ctx.get_ref(repo_config.codecommit)
                if codecommit_config.enabled:
                    account_ref = codecommit_config.account
                    account_name = self.aim_ctx.get_ref(account_ref+'.name')
                    permissions_by_account[account_name].append(permission_config)

    # Administrator
    def init_administrator_permission(self, permission_config, permissions_by_account):
        accounts = permission_config.accounts
        if 'all' in accounts:
            accounts = self.aim_ctx.project['accounts'].keys()

        for account_name in accounts:
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
        master_account_ctx = self.aim_ctx.get_account_context(account_ref='aim.ref accounts.master')
        iam_client = master_account_ctx.get_aws_client('iam')
        access_key_config = user_config.programmatic_access
        if access_key_config and access_key_config.enabled == True:
            self.iam_user_enable_access_keys(iam_client, user_config)
            # Create SDB Domain for Account wide access keys
            sdb_client = master_account_ctx.get_aws_client('sdb')
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
                    print("Error: Unable to locate Access Key Num for key: {}".format(key_meta['AccessKeyId']+'KeyNum'))
                key_version = self.get_sdb_attribute_value(sdb_client, sdb_domain, sdb_item_name, key_meta['AccessKeyId']+'Version')
                if key_version == None:
                    print("Error: Unable to locate Access Key Version for key: {}".format(key_meta['AccessKeyId']+'Version'))
                if key_num == None or key_version == None:
                    continue
                key_config = {
                    'access_key_id': key_meta['AccessKeyId'],
                    'version': int(key_version),
                    'key_num': key_num
                }
                if old_keys[key_num] != None:
                    print("Error: Cur keys have already been set.")
                    raise StackException(AimErrorCode.Unknown, message='Cur keys have already been set')
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

    def init_users(self):
        master_account_ctx = self.aim_ctx.get_account_context(account_ref='aim.ref accounts.master')
        for user_name in self.iam_config.users.keys():
            user_config = self.iam_config.users[user_name]

            # Build a list of permissions for each account
            permissions_by_account = {}
            # Initialize permission_by_account for all accounts
            for account_name in self.aim_ctx.project['accounts'].keys():
                permissions_by_account[account_name] = []

            for permission_name in user_config.permissions.keys():
                permission_config = user_config.permissions[permission_name]
                init_method = getattr(self, "init_{}_permission".format(permission_config.type.lower()))
                init_method(permission_config, permissions_by_account)

            # Give access to accounts the user has explicitly access to
            for account_name in self.aim_ctx.project['accounts'].keys():
                account_ctx = self.aim_ctx.get_account_context('aim.ref accounts.'+account_name)
                config_ref = 'resource.iam.users.'+user_name
                # StackGroup
                self.iam_user_stack_groups[account_name] = IAMUserStackGroup(self.aim_ctx, account_ctx, account_name, self)
                # Template and stack
                IAMUserAccountDelegates(
                    self.aim_ctx,
                    account_ctx,
                    master_account_ctx.config.region,
                    self.iam_user_stack_groups[account_name],
                    None, # stack_tags
                    user_config,
                    permissions_by_account[account_name],
                    config_ref
                )


        # Stack hooks for managing access keys
        stack_hooks = StackHooks(self.aim_ctx)
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
            self.aim_ctx,
            master_account_ctx,
            master_account_ctx.config.region,
            self.iam_user_stack_groups['master'],
            None, # stack_tags,
            stack_hooks,
            self.iam_config.users,
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




    def init(self, controller_args):
        if controller_args == None:
            return
        if controller_args['arg_1'] == 'users':
            self.init_users()

    def create_managed_policy(self, aim_ctx, account_ctx, region, group_id, policy_id, policy_ref, policy_config_yaml, parent_config, stack_group, template_params, stack_tags):
        if policy_ref not in self.policy_context.keys():
            self.policy_context[policy_ref] = PolicyContext(aim_ctx=self.aim_ctx,
                                                            account_ctx=account_ctx,
                                                            region=region,
                                                            group_id=group_id,
                                                            policy_id=policy_id,
                                                            policy_ref=policy_ref,
                                                            policy_config_yaml=policy_config_yaml,
                                                            parent_config=parent_config,
                                                            stack_group=stack_group,
                                                            template_params=template_params,
                                                            stack_tags=stack_tags)
        else:
            print("Managed Policy already exists: %s" % (policy_ref))
            raise StackException(AimErrorCode.Unknown)

    def add_managed_policy(self, role_ref, *args, **kwargs):
        return self.role_context[role_ref].add_managed_policy(*args, **kwargs)

    def add_role(self, aim_ctx, account_ctx, region, group_id, role_id, role_ref, role_config, stack_group, template_params, stack_tags):
        if role_ref not in self.role_context.keys():
            self.role_context[role_ref] = RoleContext(aim_ctx=self.aim_ctx,
                                                      account_ctx=account_ctx,
                                                      region=region,
                                                      group_id=group_id,
                                                      role_id=role_id,
                                                      role_ref=role_ref,
                                                      role_config=role_config,
                                                      stack_group=stack_group,
                                                      template_params=template_params,
                                                      stack_tags=stack_tags)

        else:
            print("Role already exists: %s" % (role_ref))
            raise StackException(AimErrorCode.Unknown)

    def role_arn(self, role_ref):
        role_ref = role_ref.replace('aim.ref ', '')
        return self.role_context[role_ref].role_arn

    def role_profile_arn(self, role_ref):
        role_ref = role_ref.replace('aim.ref ', '')
        return self.role_context[role_ref].role_profile_arn

    def validate(self):
        for account_name in self.iam_user_stack_groups.keys():
            stack_group = self.iam_user_stack_groups[account_name]
            stack_group.validate()

    def provision(self):
        for account_name in self.iam_user_stack_groups.keys():
            stack_group = self.iam_user_stack_groups[account_name]
            stack_group.provision()

    def delete(self):
        for account_name in self.iam_user_stack_groups.keys():
            stack_group = self.iam_user_stack_groups[account_name]
            stack_group.delete()


