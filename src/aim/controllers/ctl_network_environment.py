import click
import os
import pathlib
from aim.stack_group import NetworkStackGroup
from aim.stack_group import ApplicationStackGroup, StackTags
from aim.stack_group import IAMStackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from aim.core.yaml import YAML

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False


class EnvironmentContext():
    def __init__(self, aim_ctx, netenv_ctl, netenv_id, env_id, region, config):
        self.aim_ctx = aim_ctx
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
        self.account_ctx = aim_ctx.get_account_context(account_ref=env_account_ref)
        self.config_ref_prefix = '.'.join(
            [   self.netenv_ctl.config_ref_prefix,
                self.netenv_id,
                self.env_id,
                self.region
            ])

        # Network Stack Group
        self.aim_ctx.log("Environment: %s" % (self.env_id))
        self.init_done = False
        self.resource_yaml_filename = "{}-{}-{}.yaml".format(self.netenv_id,
                                                             self.env_id,
                                                             self.region)
        self.resource_yaml_path = os.path.join(self.aim_ctx.project_folder,
                                               'Outputs',
                                               'NetworkEnvironments')
        self.resource_yaml = os.path.join(self.resource_yaml_path, self.resource_yaml_filename)
        self.stack_tags = StackTags()
        self.stack_tags.add_tag('aim.netenv.name', self.netenv_id)
        self.stack_tags.add_tag('aim.env.name', self.env_id)

    def init(self):
        if self.init_done:
            return
        self.init_done = True
        print("Environment Init: Starting")
        # Network Stack: VPC, Subnets, Etc
        self.network_stack_grp = NetworkStackGroup(self.aim_ctx,
                                                   self.account_ctx,
                                                   self,
                                                   StackTags(self.stack_tags))
        self.stack_grps.append(self.network_stack_grp)
        self.network_stack_grp.init()

        # IAM Stack
        # XXX: This may come back later.
        #for iam_group_id in self.iam_ids():
        #    iam_roles_dict = self.iam_roles_dict(iam_group_id)
        #    iam_stack_grp = IAMStackGroup(self.aim_ctx,
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
            application_stack_grp = ApplicationStackGroup(self.aim_ctx,
                                                          self.account_ctx,
                                                          self,
                                                          app_id,
                                                          StackTags(self.stack_tags))
            self.application_stack_grps[app_id] = application_stack_grp
            self.stack_grps.append(application_stack_grp)
            application_stack_grp.init()

        print("Environment Init: Complete")

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

    def segment_ids(self):
        return self.config.network.vpc.segments.keys()

    def segment_config(self, segment_id):
        return self.config.network.vpc.segments[segment_id]

    def availability_zones(self):
        return self.config.network.availability_zones

    def iam_ids(self):
        return sorted(self.config['iam'].keys())

    def iam_roles_dict(self, iam_roles_id):
        return self.config['iam'][iam_roles_id].roles

    def application_ids(self):
        return sorted(self.config['applications'].keys())

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
                config_dict = stack.get_stack_output_config()
                merged_config = self.aim_ctx.dict_of_dicts_merge(merged_config, config_dict)


        # Save merged_config to yaml file
        pathlib.Path(self.resource_yaml_path).mkdir(parents=True, exist_ok=True)
        with open(self.resource_yaml, "w") as output_fd:
            yaml.dump(data=merged_config['netenv'][self.netenv_id][self.env_id][self.region],
                      stream=output_fd)

    def validate(self):
        for stack_grp in self.stack_grps:
            stack_grp.validate()

    def provision(self):
        for stack_grp in self.stack_grps:
            stack_grp.provision()

        self.save_stack_output_config()

    def delete(self):
        for stack_grp in reversed(self.stack_grps):
            stack_grp.delete()

    def backup(self, resource_path):
        # Get resource config
        # applications.groups.compute.resources.cloud
        res_ref = self.gen_ref() + '.' + resource_path
        resource_config = self.aim_ctx.get_ref(res_ref)

        # TODO
        # Lookup ASG, if more than once instance error
        # Get instance ID from ASG
        # Generate image name
        # Add permissions
        # Return AMI ID and image name
        ec2_client = self.account_ctx.get_aws_client('ec2')
        ec2_client.create_image(InstanceId=instance_id,
                                Name=image_name)


    def gen_ref(self,
                app_id=None,
                grp_id=None,
                res_id=None,
                iam_id=None,
                role_id=None,
                segment_id=None,
                attribute=None,
                seperator='.'):
        netenv_ref = 'aim.ref netenv.{0}.{1}.{2}'.format(self.netenv_id, self.env_id, self.region)
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
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "NE",
                         None)

        self.aim_ctx.log("Network Environment")
        self.sub_envs = {}
        self.netenv_id = None
        self.config = None
        self.config_ref_prefix = "netenv"

    def init_sub_env(self, env_id, region):
        if env_id in self.sub_envs.keys():
            if region in self.sub_envs[env_id]:
                return self.sub_envs[env_id][region]

        env_config = self.config[env_id][region]
        env_ctx = EnvironmentContext(self.aim_ctx, self, self.netenv_id, env_id, region, env_config)
        self.sub_envs[env_id] = { region: env_ctx }
        env_ctx.init()

    def init_all_sub_envs(self):
        for env_id in self.config.keys():
            for region in self.config[env_id].env_regions:
                self.init_sub_env(env_id, region)

    def init(self, controller_args):
        if self.init_done == True or controller_args == None:
            return
        self.init_done = True

        self.netenv_id = controller_args['arg_1']
        env_id = controller_args['arg_2']
        region = controller_args['arg_3']

        self.config = self.aim_ctx.project['ne'][self.netenv_id]

        print("NetEnv: {}: Init: Starting".format(self.netenv_id))
        if env_id != None:
            if region == None:
                raise StackException(
                    AimErrorCode.Unknown,
                    message="Missing region argument: aim <command> netenv %s %s <region>" % (self.netenv_id, env_id)
                )
            self.init_sub_env(env_id, region)
        else:
            self.init_all_sub_envs()
        print("NetEnv: {}: Init: Complete".format(self.netenv_id))

    def validate(self):
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                print("Validating Environment: %s.%s" % (env_id, region))
                self.sub_envs[env_id][region].validate()

    def provision(self):
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                env_region = self.aim_ctx.project['ne'][self.netenv_id][env_id][region]
                if env_region.is_enabled():
                    self.sub_envs[env_id][region].provision()

    def backup(self, config_arg):
        env_ctx = self.sub_envs[config_arg['env_id']][config_arg['region']]
        env_ctx.backup(config_arg['resource'])

    def delete(self):
        for env_id in self.sub_envs.keys():
            for region in self.sub_envs[env_id].keys():
                self.sub_envs[env_id][region].delete()

    def get_aws_name(self):
        return '-'.join([super().get_aws_name(), self.netenv_id])
