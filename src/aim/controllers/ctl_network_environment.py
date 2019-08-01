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


class SubNetEnvContext():
    def __init__(self, aim_ctx, netenv_ctx, subenv_id, region, config):
        self.aim_ctx = aim_ctx
        self.netenv_ctx = netenv_ctx
        self.netenv_id = netenv_ctx.netenv_id
        self.subenv_id = subenv_id
        self.region = region
        self.config = config
        self.network_stack_grp = None
        self.application_stack_grps = {}
        self.iam_stack_grps = {}
        self.stack_grps = []
        subenv_account_ref = self.config.network.aws_account
        self.account_ctx = aim_ctx.get_account_context(account_ref=subenv_account_ref)
        self.config_ref_prefix = '.'.join([self.netenv_id, 'subenv', self.subenv_id, self.region])

        # Network Stack Group
        self.aim_ctx.log("Environment: %s" % (self.subenv_id))
        self.init_done = False
        self.resource_yaml_filename = "{}-{}-{}.yaml".format(self.netenv_id,
                                                             self.subenv_id,
                                                             self.region)
        self.resource_yaml_path = os.path.join(self.aim_ctx.project_folder,
                                               'Resources',
                                               'NetworkEnvironments')
        self.resource_yaml = os.path.join(self.resource_yaml_path, self.resource_yaml_filename)
        self.stack_tags = StackTags()
        self.stack_tags.add_tag('aim.netenv.name', self.netenv_id)
        self.stack_tags.add_tag('aim.env.name', self.subenv_id)

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
        aws_name = '-'.join([self.netenv_ctx.get_aws_name(),
                             self.subenv_id])
        return aws_name

    def get_segment_stack(self, segment_id):
        return self.network_stack_grp.get_segment_stack(segment_id)

    def get_vpc_stack(self):
        return self.network_stack_grp.get_vpc_stack()

    def get_security_group_stack(self, s3_id):
        return self.network_stack_grp.get_security_group_stack(s3_id)

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

    #def app_resources_config(self, app_id):
    #    return self.config.applications[app_id].resources()

    def app_resource_instance_iam_profile(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].instance_iam_profile

    def app_deployment_type(self, app_id, resource_id):
        return self.config.applications[app_id].resources[resource_id].type

    def app_deployment_config(self, app_id, dresource_id):
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
            yaml.dump(data=merged_config[self.netenv_id]['subenv'][self.subenv_id][self.region],
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
        netenv_ref = 'netenv.ref {0}.subenv.{1}.{2}'.format(self.netenv_id, self.subenv_id, self.region)
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



class NetEnvContext():

    def __init__(self, aim_ctx, netenv_ctl, netenv_id):
        self.aim_ctx = aim_ctx
        self.netenv_id = netenv_id
        self.sub_envs = {}
        self.netenv_ctl = netenv_ctl

        self.config = self.aim_ctx.project['ne'][netenv_id]

    def init_sub_env(self, subenv_id, region):
        if subenv_id in self.sub_envs.keys():
            if region in self.sub_envs[subenv_id]:
                return self.sub_envs[subenv_id][region]

        #subenv_config = self.config.subenv_config_dict(subenv_id, region)
        subenv_config = self.config[subenv_id][region]
        subenv_ctx = SubNetEnvContext(self.aim_ctx, self, subenv_id, region, subenv_config)
        self.sub_envs[subenv_id] = { region: subenv_ctx }
        subenv_ctx.init()

    def init_all_sub_envs(self):
        for subenv_id in self.config.keys():
            for region in self.config[subenv_id].env_regions:
                self.init_sub_env(subenv_id, region)

    def get_subenv_ctx(self, subenv_id, region):
        return self.sub_envs[subenv_id][region]

    def get_aws_name(self, subenv_id=None):
        aws_name = '-'.join([self.netenv_ctl.get_aws_name(), self.netenv_id])
        if subenv_id != None:
            aws_name = '-'.join([aws_name, subenv_id])
        return aws_name


    def get_security_group_stack(self, subenv_id, s3_id):
        subenv_ctx = self.sub_envs[subenv_id]
        return subenv_ctx.get_security_group_stack(s3_id)

    def validate(self):
        for subenv_id in self.sub_envs.keys():
            for region in self.sub_envs[subenv_id].keys():
                print("Validating Environment: %s.%s" % (subenv_id, region))
                self.sub_envs[subenv_id][region].validate()

    def provision(self):
        for subenv_id in self.sub_envs.keys():
            for region in self.sub_envs[subenv_id].keys():
                env_region = self.aim_ctx.project['ne'][self.netenv_id][subenv_id][region]
                if env_region.is_enabled():
                    self.sub_envs[subenv_id][region].provision()

    def delete(self):
        for subenv_id in self.sub_envs.keys():
            for region in self.sub_envs[subenv_id].keys():
                self.sub_envs[subenv_id][region].delete()

class NetEnvController(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "NE",
                         None)

        self.aim_ctx.log("Network Environment")
        self.net_envs = {}
        self.net_envs_list = []
        # this_netenv_id: Store the name of the current NetEnv being initialized.
        #                 Used in configuration to reference the current environment
        self.this_netenv_id = None

    def load_env(self, netenv_id, subenv_id=None, region=None):
        if netenv_id in self.net_envs.keys():
            return netenv_ctx
        else:
            netenv_ctx = NetEnvContext(self.aim_ctx, self, netenv_id)

        self.net_envs[netenv_id] = netenv_ctx
        self.net_envs_list.append(netenv_ctx)

        self.this_netenv_id = netenv_id
        if subenv_id != None:
            if region == None:
                raise StackException(AimErrorCode.Unknown)
            netenv_ctx.init_sub_env(subenv_id, region)
            return netenv_ctx
        else:
            netenv_ctx.init_all_sub_envs()
        # If something accesses 'this_net_env_id' after this point, we need to
        # we have a design issue
        self.this_net_env_id = None

        return netenv_ctx

    def init(self, controller_args):
        if self.init_done == True or controller_args == None:
            return
        self.init_done = True

        netenv_id = controller_args['arg_1']
        subenv_id = controller_args['arg_2']
        region = controller_args['arg_3']

        print("NetEnv: {}: Init: Starting".format(netenv_id))
        self.load_env(netenv_id, subenv_id, region)
        print("NetEnv: {}: Init: Complete".format(netenv_id))

    def validate(self):
        for netenv_ctx in self.net_envs_list:
            netenv_ctx.validate()

    def provision(self):
        for netenv_ctx in self.net_envs_list:
            netenv_ctx.provision()

    def backup(self, config_arg):
        subenv_ctx = self.get_subenv_ctx(config_arg['netenv_id'], config_arg['subenv_id'], config_arg['region'])
        subenv_ctx.backup(config_arg['resource'])

    def delete(self):
        for netenv_ctx in self.net_envs_list:
            netenv_ctx.delete()

    def get_subenv_ctx(self, netenv_id, subenv_id, region):
        netenv_ctx = self.net_envs[netenv_id]
        return netenv_ctx.get_subenv_ctx(subenv_id, region)

    def get_network_stack_grp(self, netenv_id, subenv_id, region):
        netenv_ctx = self.net_envs[netenv_id]
        subenv_ctx =  self.get_subenv_ctx(netenv_id, subenv_id, region)
        return subenv_ctx.network_stack_grp

    def get_application_stack_grp(self, netenv_id, subenv_id, region, app_id):
        subenv_ctx = self.get_subenv_ctx(netenv_id, subenv_id, region)
        return subenv_ctx.application_stack_grps[app_id]

    def get_iam_stack_grp(self, netenv_id, subenv_id, region, iam_id):
        subenv_ctx = self.get_subenv_ctx(netenv_id, subenv_id, region)
        return subenv_ctx.iam_stack_grps[iam_id]

    def get_stack_from_ref(self, ref_dict):
        ref_parts = ref_dict['ref_parts']
        netenv_id = ref_dict['netenv_id']
        subenv_id = ref_dict['subenv_id']
        subenv_region = ref_dict['subenv_region']
        netenv_component = ref_dict['netenv_component']
        stack=None
        if netenv_component == 'network':
            network_grp = self.get_network_stack_grp(netenv_id, subenv_id, subenv_region)
            if network_grp == None:
                raise StackException(AimErrorCode.Unknown)
            stack = network_grp.get_stack_from_ref(ref_dict['raw'])
        elif netenv_component == 'applications':
            # Get application Group
            app_id = ref_parts[5]
            app_grp = self.get_application_stack_grp(netenv_id, subenv_id, subenv_region, app_id)
            # If none, we are probably referencing ourselves when we are not yet finished initializing
            if app_grp == None:
                raise StackException(AimErrorCode.Unknown)
            # Get the stack for the resource in the app grp
            stack = app_grp.get_stack_from_ref(ref_dict['raw'])
        elif netenv_component == 'iam':
            # 0      1      2         3   4
            # netenv.subenv.subenv_id.region.iam.iam_id.roles.role_id
            iam_id = ref_parts[5]
            iam_grp = self.get_iam_stack_grp(netenv_id, subenv_id, subenv_region, iam_id)
            return iam_grp.get_stack_from_ref(ref_dict['raw'])
        if stack == None:
            print("Unable to find stack for ref: " + ref_dict['raw'])
            raise StackException(AimErrorCode.Unknown)

        return stack

    def get_value_from_ref(self, ref_dict): #, app_stack_grp=None):
        # "applications.app1.deployments.cpbd.s3.buckets.deployment_artifacts.arn"
        ref_parts = ref_dict['ref_parts']
        last_ref_part = ref_parts[len(ref_parts)-1]
        netenv_component = ref_dict['netenv_component']
        netenv_id = ref_dict['netenv_id']
        subenv_id = ref_dict['subenv_id']
        subenv_region = ref_dict['subenv_region']

        # netenv.ref wbsites.subenv.prod.applications.sites.resources.alb.dns.ssl_certificate.arn
        netenv_ctx = self.net_envs[netenv_id]

        if netenv_component == 'network':
            network_grp = self.get_network_stack_grp(netenv_id, subenv_id, subenv_region)
            if network_grp == None:
                raise StackException(AimErrorCode.Unknown)
            return network_grp.get_value_from_ref(ref_dict)
        elif netenv_component == 'iam':
            iam_group_id = ref_parts[5]
            iam_stack_grp = self.get_iam_stack_grp(netenv_id, subenv_id, subenv_region, iam_group_id)
            if iam_stack_grp == None:
                print("ERROR: Not Found: ctl_network_environment: get_value_from_ref: IAM Stack group: " + ref_dict['raw'])
                raise StackException(AimErrorCode.Unknown)
            return iam_stack_grp.get_value_from_ref(ref_dict)
        elif netenv_component == "applications":
            app_id = ref_parts[5]
            app_stack_grp = self.get_application_stack_grp(netenv_id, subenv_id, subenv_region, app_id)
            if app_stack_grp == None:
                raise StackException(AimErrorCode.Unknown)
            return app_stack_grp.get_value_from_ref(ref_dict)

        print("ERROR: Unhandled ref: ctl_network_environment: get_value_from_ref: " + ref_dict['raw'])
        raise StackException(AimErrorCode.Unknown)
