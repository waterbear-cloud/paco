import click
import getpass
import os
import pathlib
from paco import utils
from paco.controllers.controllers import Controller
from paco.core.exception import StackException
from paco.core.exception import PacoErrorCode
from paco.core.yaml import YAML
from paco.stack_grps.grp_application import ApplicationStackGroup
from paco.stack_grps.grp_network import NetworkStackGroup
from paco.stack_grps.grp_secretsmanager import SecretsManagerStackGroup
from paco.stack_grps.grp_backup import BackupVaultsStackGroup
from paco.stack import StackTags, stack_group, StackGroup

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False


class EnvironmentContext():
    def __init__(self, paco_ctx, netenv_ctl, netenv_id, env_id, region, config):
        self.paco_ctx = paco_ctx
        self.stack_group_filter = netenv_ctl.stack_group_filter
        self.netenv_ctl = netenv_ctl
        self.netenv_id = netenv_id
        self.env_id = env_id
        self.region = region
        self.config = config
        self.network_stack_grp = None
        self.application_stack_grps = {}
        self.iam_stack_grps = {}
        self.stack_grps = []
        env_account_ref = self.config.network.aws_account
        self.account_ctx = paco_ctx.get_account_context(account_ref=env_account_ref)
        # Network Stack Group
        self.init_done = False
        self.resource_yaml_filename = "{}-{}-{}.yaml".format(
            self.netenv_id,
            self.env_id,
            self.region
        )
        self.resource_yaml_path = self.paco_ctx.outputs_path / 'NetworkEnvironments'
        self.resource_yaml = self.resource_yaml_path / self.resource_yaml_filename
        self.stack_tags = StackTags()
        self.stack_tags.add_tag('paco.netenv.name', self.netenv_id)
        self.stack_tags.add_tag('paco.env.name', self.env_id)

    def init(self):
        if self.init_done:
            return
        self.init_done = True
        self.paco_ctx.log_action_col('Init', 'Environment', self.env_id+' '+self.region)

        # Secrets Manager
        self.secrets_stack_grp = SecretsManagerStackGroup(
            self.paco_ctx,
            self.account_ctx,
            self,
            self.config.secrets_manager,
            StackTags(self.stack_tags)
        )
        self.secrets_stack_grp.init()
        self.stack_grps.append(self.secrets_stack_grp)

        # Network Stack: VPC, Subnets, Etc
        self.network_stack_grp = NetworkStackGroup(
            self.paco_ctx,
            self.account_ctx,
            self,
            StackTags(self.stack_tags)
        )
        self.stack_grps.append(self.network_stack_grp)
        self.network_stack_grp.init()

        # Application Engine Stacks
        for app_name in self.ordered_application_names():
            application_stack_grp = ApplicationStackGroup(
                self.paco_ctx,
                self.account_ctx,
                self,
                self.config['applications'][app_name],
                StackTags(self.stack_tags)
            )
            self.application_stack_grps[app_name] = application_stack_grp
            self.stack_grps.append(application_stack_grp)
            application_stack_grp.init()

        # Backup
        if self.config.backup_vaults:
            self.backup_stack_grp = BackupVaultsStackGroup(
                self.paco_ctx,
                self.account_ctx,
                self,
                self.config.backup_vaults,
                StackTags(self.stack_tags)
            )
            self.backup_stack_grp.init()
            self.stack_grps.append(self.backup_stack_grp)

        self.paco_ctx.log_action_col('Init', 'Environment', self.env_id+' '+self.region)

    def get_aws_name(self):
        aws_name = '-'.join([self.netenv_ctl.get_aws_name(),
                             self.env_id])
        return aws_name

    def get_segment_stack(self, segment_id):
        return self.network_stack_grp.get_segment_stack(segment_id)

    def get_vpc_stack(self):
        return self.network_stack_grp.get_vpc_stack()

    def availability_zones(self):
        return self.config.network.availability_zones

    def ordered_application_names(self):
        "List of application names sorted according to their order"
        ordered_config_list = []
        ordered_id_list = []
        for app_id, app_config in self.config['applications'].items():
            new_app_config = [app_id, app_config]
            insert_idx = 0
            for ordered_config in ordered_config_list:
                if app_config.order < ordered_config[1].order:
                    ordered_config_list.insert(insert_idx, new_app_config)
                    ordered_id_list.insert(insert_idx, app_id)
                    break
                insert_idx += 1
            else:
                ordered_config_list.append(new_app_config)
                ordered_id_list.append(app_id)

        return ordered_id_list

    def save_stack_output_config(self):
        merged_config = {}
        for stack_grp in self.stack_grps:
            for stack in stack_grp.stacks:
                if isinstance(stack, StackGroup):
                    continue
                config_dict = stack.get_stack_output_config()
                if config_dict == None:
                    continue
                merged_config = utils.dict_of_dicts_merge(merged_config, config_dict)

        # Save merged_config to yaml file
        if 'netenv' in merged_config.keys():
            self.resource_yaml_path.mkdir(parents=True, exist_ok=True)
            with open(self.resource_yaml, "w") as output_fd:
                yaml.dump(data=merged_config['netenv'][self.netenv_id][self.env_id][self.region],
                        stream=output_fd)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        self.paco_ctx.log_action_col("Provision", "Environment", self.env_id+' '+self.region)
        if len(self.stack_grps) > 0:
            for stack_grp in self.stack_grps:
                stack_grp.provision()
            self.save_stack_output_config()
        else:
            self.paco_ctx.log_action_col("Provision", "Nothing to provision.")
        self.paco_ctx.log_action_col("Provision", "Environment", self.env_id+' '+self.region, "Completed")

    def delete(self):
        for stack_grp in reversed(self.stack_grps):
            stack_grp.delete()

class NetEnvController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(
            paco_ctx,
            "NE",
            None
        )
        self.sub_envs = {}
        self.netenv_id = None
        self.config = None

    def init_sub_env(self, env_id, region):
        if env_id in self.sub_envs.keys():
            if region in self.sub_envs[env_id]:
                return self.sub_envs[env_id][region]

        env_config = self.config[env_id][region]
        env_ctx = EnvironmentContext(self.paco_ctx, self, self.netenv_id, env_id, region, env_config)
        if env_id not in self.sub_envs:
            self.sub_envs[env_id] = {}
        self.sub_envs[env_id][region] = env_ctx
        env_ctx.init()

    def secrets_manager(self, secret_name, account_ctx, region):
        print("Modifying secret: " + secret_name)
        secret_string = getpass.getpass("Enter new secret value: ")
        secrets_client = account_ctx.get_aws_client('secretsmanager')
        secrets_client.put_secret_value(
            SecretId=secret_name,
            SecretString=secret_string
        )

    def init_command(self, controller_args):
        if controller_args['arg_1'].find('.secrets_manager.'):
            parts = controller_args['arg_1'].split('.')
            environment = parts[2]
            region = parts[3]
            account_ctx = self.paco_ctx.get_account_context(account_ref=self.config[environment][region].network.aws_account)
            secret_name = controller_args['arg_1']
            self.secrets_manager(secret_name, account_ctx, region)

    def init(self, command=None, model_obj=None):
        if self.init_done == True:
            return
        self.init_done = True
        netenv_id = None
        env_id = None
        region = None
        resource_arg = None
        paco_command = command
        netenv_arg = model_obj.paco_ref_parts
        netenv_parts = netenv_arg.split('.', 4)[1:]
        netenv_id = netenv_parts[0]
        if netenv_id in self.paco_ctx.project['netenv'].keys():
            self.netenv_id = netenv_id
            if len(netenv_parts) > 1:
                env_id = netenv_parts[1]
            if len(netenv_parts) > 2:
                region = netenv_parts[2]
            if len(netenv_parts) > 3:
                resource_arg = netenv_parts[3]
        else:
            raise StackException(
                PacoErrorCode.Unknown,
                message="Network Environment does not exist: {}".format(netenv_id)
            )

        self.config = self.paco_ctx.project['netenv'][self.netenv_id]

        if env_id not in self.config.keys():
            message = "Command: paco {} {}\n".format(paco_command, netenv_arg)
            message += "Error:   Network Environment '{}' does not have an Environment named '{}'.\n".format(netenv_id, env_id)
            raise StackException(
                PacoErrorCode.Unknown,
                message = message
            )

        # if no region specified, then applies to all in the environment
        if not region:
            regions = [region for region in self.config[env_id].env_regions.keys()]
        else:
            regions = [region]
            if region not in self.config[env_id].keys():
                message = "Command: paco {} {}\n".format(paco_command, netenv_arg)
                message += "Error:   Environment '{}' does not have region '{}'.".format(env_id, region)
                raise StackException(
                    PacoErrorCode.Unknown,
                    message = message
                )

        # Validate resource_arg
        if resource_arg != None:
            res_parts = resource_arg.split('.')
            config_obj = self.config[env_id][region]
            done_parts_str = ""
            first = True
            for res_part in res_parts:
                if first == False:
                    done_parts_str += '.'
                done_parts_str += res_part
                if hasattr(config_obj, res_part) == False and res_part not in config_obj.keys():
                    message = "Command: paco {} {}\n".format(paco_command, netenv_arg)
                    message += "Error:   Unable to locate resource: {}".format(done_parts_str)
                    raise StackException(
                        PacoErrorCode.Unknown,
                        message = message
                    )
                if hasattr(config_obj, res_part):
                    config_obj = getattr(config_obj, res_part)
                else:
                    config_obj = config_obj[res_part]
                first = False

        self.paco_ctx.log_action_col("Init", "NetEnv", self.netenv_id)
        self.stack_group_filter = netenv_arg
        if regions:
            for region in regions:
                self.init_sub_env(env_id, region)
        self.paco_ctx.log_action_col("Init", "NetEnv", self.netenv_id, "Complete")

    def validate(self):
        self.paco_ctx.log_action_col("Validate", "NetEnv", self.netenv_id)
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                self.paco_ctx.log_action_col('Validate', 'Environment', env_id+' '+region)
                self.sub_envs[env_id][region].validate()
        self.paco_ctx.log_action_col("Validate", "NetEnv", self.netenv_id, 'Completed')

    def provision(self):
        self.confirm_yaml_changes(self.config)
        self.paco_ctx.log_action_col("Provision", "NetEnv", self.netenv_id)
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                self.sub_envs[env_id][region].provision()
        self.apply_model_obj()
        self.paco_ctx.log_action_col("Provision", "NetEnv", self.netenv_id, "Completed")

    def delete(self):
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                self.sub_envs[env_id][region].delete()

    def get_aws_name(self):
        return '-'.join([super().get_aws_name(), self.netenv_id])
