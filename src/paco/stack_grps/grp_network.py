from paco.stack_group import StackEnum, StackOrder, Stack, StackGroup, StackTags
from paco.models import schemas
from pprint import pprint
import paco.cftemplates
import paco.models.networks
import paco.models.loader
from paco.models.locations import get_parent_by_interface
from paco import utils

class NetworkStackGroup(StackGroup):
    def __init__(self, paco_ctx, account_ctx, env_ctx, stack_tags):
        super().__init__(
            paco_ctx,
            account_ctx,
            env_ctx.netenv_id,
            "Net",
            env_ctx
        )
        self.env_ctx = env_ctx
        self.config_ref_prefix = self.env_ctx.config_ref_prefix
        self.region = self.env_ctx.region
        self.stack_tags = stack_tags

    def log_init_status(self, name, description, is_enabled):
        "Logs the init status of a network component"
        self.paco_ctx.log_action_col('Init', 'Network', name, description, enabled=is_enabled)

    def init(self):
        # Network Stack Templates
        # VPC Stack
        vpc_config = self.env_ctx.vpc_config()
        if vpc_config == None:
            # NetworkEnvironment with no network - serverless
            return
        network_config = get_parent_by_interface(vpc_config, schemas.INetworkEnvironment)
        self.log_init_status('VPC', '', vpc_config.is_enabled())
        vpc_config_ref = '.'.join([self.config_ref_prefix, "network.vpc"])
        vpc_config.resolve_ref_obj = self
        vpc_config.private_hosted_zone.resolve_ref_obj = self
        vpc_template = paco.cftemplates.VPC(
            self.paco_ctx,
            self.account_ctx,
            self.region,
            self, # stack_group
            StackTags(self.stack_tags),
            vpc_config,
            vpc_config_ref
        )
        self.vpc_stack = vpc_template.stack

        # Segments
        self.segment_list = []
        self.segment_dict = {}
        for segment_id in self.env_ctx.segment_ids():
            segment_config = self.env_ctx.segment_config(segment_id)
            self.log_init_status('Segment', '{}'.format(segment_id), segment_config.is_enabled())
            segment_config.resolve_ref_obj = self
            segment_config_ref = '.'.join([self.config_ref_prefix, "network.vpc.segments", segment_id])
            segment_template = paco.cftemplates.Segment(
                self.paco_ctx,
                self.account_ctx,
                self.region,
                self, # stack_group
                StackTags(self.stack_tags),
                [StackOrder.PROVISION], # stack_order
                self.env_ctx,
                segment_id,
                segment_config,
                segment_config_ref
            )
            segment_stack = segment_template.stack
            self.segment_dict[segment_id] = segment_stack
            self.segment_list.append(segment_stack)

        # Security Groups
        sg_config = self.env_ctx.security_groups()
        self.sg_list = []
        self.sg_dict = {}
        # EC2 NATGateway Groups
        # Creates a security group for each Availability Zone in the segment
        sg_nat_id = 'bastion_nat_'+utils.md5sum(str_data='gateway')[:8]
        sg_nat_config_ref = '.'.join([self.config_ref_prefix, 'network.vpc.security_groups', sg_nat_id])
        for nat_id in vpc_config.nat_gateway.keys():
            nat_config = vpc_config.nat_gateway[nat_id]
            if nat_config.is_enabled() == False:
                continue
            if nat_config.type == 'EC2':
                sg_nat_config_dict = {}
                if sg_nat_id not in sg_config.keys():
                    sg_config[sg_nat_id] = {}
                for az_idx in range(1,network_config.availability_zones+1):
                    sg_nat_config_dict['enabled'] = True
                    sg_nat_config_dict['ingress'] = []
                    for route_segment in nat_config.default_route_segments:
                        route_segment_id = route_segment.split('.')[-1]
                        az_cidr = getattr(vpc_config.segments[route_segment_id], 'az'+str(az_idx)+'_cidr')
                        sg_nat_config_dict['ingress'].append(
                            {
                                'name': 'SubnetAZ',
                                'cidr_ip': az_cidr,
                                'protocol': '-1'
                            }
                        )

                    sg_nat_config_dict['egress'] = [
                        {
                            'name': 'ANY',
                            'cidr_ip': '0.0.0.0/0',
                            'protocol': '-1'
                        }
                    ]

                    sg_nat_rule_id = nat_id +'_az'+ str(az_idx)
                    sg_config[sg_nat_id][sg_nat_rule_id] = paco.models.networks.SecurityGroup(sg_nat_rule_id, vpc_config)
                    paco.models.loader.apply_attributes_from_config(
                        sg_config[sg_nat_id][sg_nat_rule_id],
                        sg_nat_config_dict)
        # The Groups Only
        for sg_id in sg_config:
            # Set resolve_ref_obj
            for sg_obj_id in sg_config[sg_id]:
                sg_config[sg_id][sg_obj_id].resolve_ref_obj = self
                self.log_init_status(
                    'SecurityGroup', 'group: {}.{}'.format(sg_id, sg_obj_id),
                    sg_config[sg_id][sg_obj_id].is_enabled()
                )
            sg_groups_config_ref = '.'.join([self.config_ref_prefix, 'network.vpc.security_groups', sg_id])
            sg_template = paco.cftemplates.SecurityGroups(
                paco_ctx=self.paco_ctx,
                account_ctx=self.account_ctx,
                aws_region=self.region,
                stack_group=self,
                stack_tags=StackTags(self.stack_tags),
                env_ctx=self.env_ctx,
                security_groups_config=sg_config[sg_id],
                sg_group_id=sg_id,
                sg_groups_config_ref=sg_groups_config_ref,
                template_type = 'Groups' )
            sg_stack = sg_template.stack
            self.sg_list.append(sg_stack)
            self.sg_dict[sg_id] = sg_stack

        # Ingress/Egress Stacks
        for sg_id in sg_config:
            # Set resolve_ref_obj
            for sg_obj_id in sg_config[sg_id]:
                self.log_init_status(
                    'SecurityGroup', 'rules: {}.{}'.format(sg_id, sg_obj_id),
                    sg_config[sg_id][sg_obj_id].is_enabled()
                )

            sg_groups_config_ref = '.'.join([self.config_ref_prefix, 'network.vpc.security_groups', sg_id])
            paco.cftemplates.SecurityGroups(
                paco_ctx=self.paco_ctx,
                account_ctx=self.account_ctx,
                aws_region=self.region,
                stack_group=self,
                stack_tags=StackTags(self.stack_tags),
                env_ctx=self.env_ctx,
                security_groups_config=sg_config[sg_id],
                sg_group_id=sg_id,
                sg_groups_config_ref=sg_groups_config_ref,
                template_type='Rules'
            )

        # Wait for Segment Stacks
        for segment_stack in self.segment_list:
            self.add_stack_order(segment_stack, [StackOrder.WAIT])

        # VPC Peering Stack
        if vpc_config.peering != None:
            peering_config = self.env_ctx.peering_config()
            peering_config_ref = '.'.join([self.config_ref_prefix, "network.vpc.peering"])
            for peer_id in peering_config.keys():
                peer_config = vpc_config.peering[peer_id]
                peer_config.resolve_ref_obj = self
                self.log_init_status('VPCPeer', '{}'.format(peer_id), peer_config.is_enabled())

            peering_template = paco.cftemplates.VPCPeering(
                self.paco_ctx,
                self.account_ctx,
                self.region,
                self, # stack_order
                StackTags(self.stack_tags),
                self.env_ctx.netenv_id,
                self.env_ctx.env_id,
                self.env_ctx.config.network,
                peering_config_ref
            )
            self.peering_stack = peering_template.stack

        # NAT Gateway
        self.nat_list = []
        for nat_id in vpc_config.nat_gateway.keys():
            nat_config = vpc_config.nat_gateway[nat_id]
            self.log_init_status('NAT Gateway', '{}'.format(nat_id), nat_config.is_enabled())
            if sg_nat_id in sg_config.keys():
                nat_sg_config = sg_config[sg_nat_id]
            else:
                nat_sg_config = None
            # We now disable the NAT Gatewy in the template so that we can delete it and recreate
            # it when disabled.
            nat_template = paco.cftemplates.NATGateway(
                paco_ctx=self.paco_ctx,
                account_ctx=self.account_ctx,
                aws_region=self.region,
                stack_group=self,
                stack_tags=StackTags(self.stack_tags),
                stack_order=[StackOrder.PROVISION],
                network_config=network_config,
                nat_sg_config=nat_sg_config,
                nat_sg_config_ref=sg_nat_config_ref,
                nat_config=nat_config
            )
            nat_stack = nat_template.stack
            self.nat_list.append(nat_stack)

        for nat_stack in self.nat_list:
            self.add_stack_order(nat_stack, [StackOrder.WAIT])

        self.paco_ctx.log_action_col('Init', 'Network', 'Completed', enabled=self.env_ctx.config.network.is_enabled())

    def get_vpc_stack(self):
        return self.vpc_stack


    def get_security_group_stack(self, sg_id):
        return self.sg_dict[sg_id]

    def get_segment_stack(self, segment_id):
        return self.segment_dict[segment_id]

    def resolve_ref(self, ref):
        if ref.raw.endswith('network.vpc.id'):
            return self.vpc_stack
        if schemas.IPrivateHostedZone.providedBy(ref.resource):
            return self.vpc_stack
        if ref.raw.find('network.vpc.segments') != -1:
            segment_id = ref.next_part('network.vpc.segments')
            return self.get_segment_stack(segment_id)
        if schemas.ISecurityGroup.providedBy(ref.resource):
            if ref.resource_ref == 'id':
                sg_id = ref.parts[-3]
                return self.get_security_group_stack(sg_id)

    def validate(self):
        # Generate Stacks
        # VPC Stack
        super().validate()

    def provision(self):
        # self.validate()
        super().provision()
