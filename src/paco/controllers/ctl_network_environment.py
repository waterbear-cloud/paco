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
from paco.stack_group import StackTags, stack_group, StackGroup

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
        self.config_ref_prefix = '.'.join([
            self.netenv_ctl.config_ref_prefix,
            self.netenv_id,
            self.env_id,
            self.region
        ])
        # Network Stack Group
        self.init_done = False
        self.resource_yaml_filename = "{}-{}-{}.yaml".format(
            self.netenv_id,
            self.env_id,
            self.region
        )
        self.resource_yaml_path = os.path.join(
            self.paco_ctx.project_folder,
            'Outputs',
            'NetworkEnvironments'
        )
        self.resource_yaml = os.path.join(self.resource_yaml_path, self.resource_yaml_filename)
        self.stack_tags = StackTags()
        self.stack_tags.add_tag('paco.netenv.name', self.netenv_id)
        self.stack_tags.add_tag('paco.env.name', self.env_id)

    def init(self):
        if self.init_done:
            return
        self.init_done = True
        self.paco_ctx.log_action_col('Init', 'Environment', self.env_id+' '+self.region)
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

        # IAM Stack
        # XXX: This may come back later.
        #for iam_group_id in self.iam_ids():
        #    iam_roles_dict = self.iam_roles_dict(iam_group_id)
        #    iam_stack_grp = IAMStackGroup(self.paco_ctx,
        #                                  self.account_ctx,
        #                                  self.get_aws_name(),
        #                                  iam_roles_dict,
        #                                  iam_group_id,
        #                                  self.config_ref_prefix,
        #                                  self)
        #    self.iam_stack_grps[iam_group_id] = iam_stack_grp
        #    self.stack_grps.append(iam_stack_grp)
        #    iam_stack_grp.init()

        # Application Engine Stacks
        for app_id in self.application_ids():
            application_stack_grp = ApplicationStackGroup(
                self.paco_ctx,
                self.account_ctx,
                self,
                app_id,
                StackTags(self.stack_tags)
            )
            self.application_stack_grps[app_id] = application_stack_grp
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

    def security_groups(self):
        return self.config.network.vpc.security_groups

    def nat_gateway_ids(self):
        return self.config.network.vpc.nat_gateway.keys()

    def nat_gateway_enabled(self, nat_id):
        return self.config.network.vpc.nat_gateway[nat_id].enabled

    def nat_gateway_az(self, nat_id):
        return self.config.network.vpc.nat_gateway[nat_id].availability_zone

    def nat_gateway_segment(self, nat_id):
        return self.config.network.vpc.nat_gateway[nat_id].segment

    def nat_gateway_default_route_segments(self, nat_id):
        return self.config.network.vpc.nat_gateway[nat_id].default_route_segments

    def vpc_config(self):
        return self.config.network.vpc

    def peering_config(self):
        return self.config.network.vpc.peering

    def segment_ids(self):
        if self.config.network.vpc.segments != None:
            return self.config.network.vpc.segments.keys()
        return []

    def segment_config(self, segment_id):
        return self.config.network.vpc.segments[segment_id]

    def availability_zones(self):
        return self.config.network.availability_zones

    def iam_ids(self):
        return sorted(self.config['iam'].keys())

    def iam_roles_dict(self, iam_roles_id):
        return self.config['iam'][iam_roles_id].roles

    def application_ids(self):
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

    def deployment_ids(self, app_id):
        self.config.applications[app_id].resources.deployments()
        #for resource in self.config.applications[app_id].resources:
        #    if resource.is_deployment():

        return sorted(self.config.applications[app_id].keys())

    def app_services_config(self, app_id):
        return self.config.applications[app_id].services

    def app_group_items(self, app_id):
        return self.config.applications[app_id].groups_ordered()

    def app_resource_instance_iam_profile(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].instance_iam_profile

    def app_deployment_type(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].type

    def app_deployment_config(self, app_id, resource_id):
        return self.config.applications[app_id].deployments[resource_id]

    def app_deployment_artifacts_bucket_config(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].artifacts_bucket

    def app_deployment_codecommit_repository(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].codecommit_repository

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
            pathlib.Path(self.resource_yaml_path).mkdir(parents=True, exist_ok=True)
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

    def backup(self, resource_path):
        # Get resource config
        # applications.groups.compute.resources.cloud
        res_ref = self.gen_ref() + '.' + resource_path
        resource_config = self.paco_ctx.get_ref(res_ref)

        # TODO
        # Lookup ASG, if more than once instance error
        # Get instance ID from ASG
        # Generate image name
        # Add permissions
        # Return AMI ID and image name
        ec2_client = self.account_ctx.get_aws_client('ec2')
        ec2_client.create_image(InstanceId=instance_id,
                                Name=image_name)



    def env_ref_prefix(
        self,
        app_id=None,
        grp_id=None,
        res_id=None,
        iam_id=None,
        role_id=None,
        segment_id=None,
        attribute=None,
        seperator='.'
    ):
        netenv_ref = 'paco.ref netenv.{0}.{1}.{2}'.format(self.netenv_id, self.env_id, self.region)
        if app_id != None:
            netenv_ref = seperator.join([netenv_ref, 'applications', app_id])
        if iam_id != None:
            netenv_ref = seperator.join([netenv_ref, 'iam', app_id])
        if role_id != None:
            netenv_ref = seperator.join([netenv_ref, 'roles', app_id])
        if grp_id != None:
            netenv_ref = seperator.join([netenv_ref, 'groups', grp_id])
        if res_id != None:
            netenv_ref = seperator.join([netenv_ref, 'resources', res_id])
        if segment_id != None:
            netenv_ref = seperator.join([netenv_ref, 'network', 'vpc', 'segments', segment_id])
        if attribute != None:
            netenv_ref = seperator.join([netenv_ref, attribute])
        return netenv_ref


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
        self.config_ref_prefix = "netenv"

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
        if netenv_arg == None:
            message = "Command: paco {} {}\n".format(paco_command, netenv_arg)
            message += "Error:   Missing NetEnv argument:  netenv.<netenv>.<environment>[.<region>.<option>.<resource>.<path>]"
            raise StackException(
                PacoErrorCode.Unknown,
                message = message
            )

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

    def backup(self, config_arg):
        env_ctx = self.sub_envs[config_arg['env_id']][config_arg['region']]
        env_ctx.backup(config_arg['resource'])

    def delete(self):
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                self.sub_envs[env_id][region].delete()

    def get_aws_name(self):
        return '-'.join([super().get_aws_name(), self.netenv_id])
