from paco.stack import StackOrder, Stack, StackGroup, StackHooks
import paco.cftemplates
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.utils import md5sum

class CodeCommitStackGroup(StackGroup):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        codecommit_config,
        repo_list,
        controller
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            account_ctx.get_name(),
            'Git',
            controller
        )

        # Initialize config with a deepcopy of the project defaults
        self.config = codecommit_config
        self.stack_list = []
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.repo_list = repo_list

    def init(self):
        stack_hooks = StackHooks()
        for hook_action in ['create', 'update']:
            stack_hooks.add(
                name='CodeCommitSSHPublicKey',
                stack_action=hook_action,
                stack_timing='post',
                hook_method=self.codecommit_post_stack_hook,
                cache_method=self.codecommit_post_stack_hook_cache_id,
                hook_arg=self.config
            )
        # CodeCommit Repository
        codecommit_stack = self.add_new_stack(
            self.aws_region,
            self.config,
            paco.cftemplates.CodeCommit,
            extra_context={'repo_list':self.repo_list},
            stack_hooks=stack_hooks
        )
        codecommit_stack.set_termination_protection(True)
        self.stack_list.append(codecommit_stack)

    def manage_ssh_key(self, iam_client, user_config):
        ssh_keys = iam_client.list_ssh_public_keys(
            UserName=user_config.username
        )

        KeyExists = False
        for ssh_key_config in ssh_keys['SSHPublicKeys']:
            iam_ssh_key = iam_client.get_ssh_public_key(
                UserName=user_config.username,
                SSHPublicKeyId=ssh_key_config['SSHPublicKeyId'],
                Encoding='SSH'
            )['SSHPublicKey']
            if user_config.public_ssh_key.startswith(iam_ssh_key['SSHPublicKeyBody']):
                # Key already exists, do nothing for this key
                KeyExists = True
                print("%s:   KeyId:    SSHPublicKeyId: %s: %s" % (
                    self.account_ctx.get_name(),
                    user_config.username,
                    ssh_key_config['SSHPublicKeyId'] ))
            else:
                # Delete Keys that do not match
                # TODO: Support multiple keys
                print("%s:   Delete:  SSHPublicKeyId: %s: %s" % (
                    self.account_ctx.get_name(),
                    user_config.username,
                    ssh_key_config['SSHPublicKeyId'] ))

                iam_client.delete_ssh_public_key(
                    UserName=user_config.username,
                    SSHPublicKeyId=ssh_key_config['SSHPublicKeyId']
                )

        # If we make it here, this key does not exist
        if KeyExists == False:
            new_key_config = iam_client.upload_ssh_public_key(
                UserName=user_config.username,
                SSHPublicKeyBody=user_config.public_ssh_key
            )

            print("%s:   Upload:  SSHPublicKeyId: %s: %s" % (
                self.account_ctx.get_name(),
                user_config.username,
                new_key_config['SSHPublicKey']['SSHPublicKeyId'] ))

    def codecommit_post_stack_hook_cache_id(self, hook, config):
        cache_data = ""
        for repo_group in config.values():
            for repo_config in repo_group.values():
                if repo_config.users != None:
                    for user_config in repo_config.users.values():
                        if user_config.public_ssh_key != None:
                            cache_data += user_config.public_ssh_key

        cache_id = md5sum(str_data=cache_data)
        return cache_id

    def codecommit_post_stack_hook(self, hook, config):
        "Iterates through users and displays the SSHPublicKeyId for each user in the stack."
        iam_client = self.account_ctx.get_aws_client('iam')
        user_done = {}
        for repo_group in config.values():
            for repo_config in repo_group.values():
                if self.paco_ctx.get_ref(repo_config.account+'.name') != self.account_ctx.get_name():
                    continue
                if repo_config.users != None:
                    for user_config in repo_config.users.values():
                        if user_config.public_ssh_key != None and user_config.username not in user_done.keys():
                            user_done[user_config.username] = True
                            self.manage_ssh_key(iam_client, user_config)

    def validate(self):
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
