from paco.stack import StackOrder, Stack, StackGroup, StackTags
from paco.models import schemas
from pprint import pprint
import paco.cftemplates
import paco.models.networks
import paco.models.loader
from paco.models.locations import get_parent_by_interface
from paco import utils

class NetworkStackGroup(StackGroup):
    """StackGroup to manage all the stacks for a Network: VPC, NAT Gateway, VPC Peering, Security Groups, Segments"""
    def __init__(self, paco_ctx, account_ctx, env_ctx, stack_tags):
        super().__init__(
            paco_ctx,
            account_ctx,
            env_ctx.netenv.name,
            "Net",
            env_ctx
        )
        self.env_ctx = env_ctx
        self.region = self.env_ctx.region
        self.stack_tags = stack_tags

    def init(self):
        # Network Stack Templates
        # VPC Stack
        vpc_config = self.env_ctx.env_region.network.vpc
        if vpc_config == None:
            # NetworkEnvironment with no network - serverless
            return
        network_config = get_parent_by_interface(vpc_config, schemas.INetwork)
        vpc_config.resolve_ref_obj = self
        vpc_config.private_hosted_zone.resolve_ref_obj = self
        self.vpc_stack = self.add_new_stack(
            self.region,
            vpc_config,
            paco.cftemplates.VPC,
            stack_tags=StackTags(self.stack_tags),
        )

        # Segments
        self.segment_list = []
        self.segment_dict = {}
        segments = network_config.vpc.segments
        for segment in segments.values():
            segment.resolve_ref_obj = self
            segment_stack = self.add_new_stack(
                self.region,
                segment,
                paco.cftemplates.Segment,
                stack_tags=StackTags(self.stack_tags),
                stack_orders=[StackOrder.PROVISION],
                extra_context={'env_ctx': self.env_ctx},
            )
            self.segment_dict[segment.name] = segment_stack
            self.segment_list.append(segment_stack)

        # Security Groups
        sg_config = network_config.vpc.security_groups
        self.sg_list = []
        self.sg_dict = {}
        # EC2 NATGateway Security Groups
        # Creates a security group for each Availability Zone in the segment
        sg_nat_id = 'bastion_nat_' + utils.md5sum(str_data='gateway')[:8]
        for nat_config in vpc_config.nat_gateway.values():
            if nat_config.is_enabled() == False:
                continue
            if nat_config.type == 'EC2':
                sg_nat_config_dict = {}
                if sg_nat_id not in sg_config.keys():
                    sg_config[sg_nat_id] = paco.models.networks.SecurityGroups(sg_nat_id, sg_config)
                for az_idx in range(1, network_config.availability_zones + 1):
                    sg_nat_config_dict['enabled'] = True
                    sg_nat_config_dict['ingress'] = []
                    for route_segment in nat_config.default_route_segments:
                        route_segment_id = route_segment.split('.')[-1]
                        az_cidr = getattr(vpc_config.segments[route_segment_id], f"az{az_idx}_cidr")
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
                    sg_nat_rule_id = nat_config.name + '_az' + str(az_idx)
                    sg_config[sg_nat_id][sg_nat_rule_id] = paco.models.networks.SecurityGroup(sg_nat_rule_id, vpc_config)
                    paco.models.loader.apply_attributes_from_config(
                        sg_config[sg_nat_id][sg_nat_rule_id],
                        sg_nat_config_dict
                    )

        # Declared Security Groups
        for sg_id in sg_config:
            # Set resolve_ref_obj
            for sg_obj_id in sg_config[sg_id]:
                sg_config[sg_id][sg_obj_id].resolve_ref_obj = self
            sg_stack = self.add_new_stack(
                self.region,
                sg_config[sg_id],
                paco.cftemplates.SecurityGroups,
                stack_tags=StackTags(self.stack_tags),
                extra_context={'env_ctx': self.env_ctx, 'template_type': 'Groups'},
            )
            self.sg_list.append(sg_stack)
            self.sg_dict[sg_id] = sg_stack

        # Ingress/Egress Stacks
        for sg_id in sg_config:
            self.add_new_stack(
                self.region,
                sg_config[sg_id],
                paco.cftemplates.SecurityGroups,
                stack_tags=StackTags(self.stack_tags),
                extra_context={'env_ctx': self.env_ctx, 'template_type': 'Rules'}
            )

        # Wait for Segment Stacks
        for segment_stack in self.segment_list:
            self.add_stack_order(segment_stack, [StackOrder.WAIT])

        # VPC Peering Stack
        if vpc_config.peering != None:
            peering_config = self.env_ctx.env_region.network.vpc.peering
            for peer_id in peering_config.keys():
                peer_config = vpc_config.peering[peer_id]
                peer_config.resolve_ref_obj = self
            self.peering_stack = self.add_new_stack(
                self.region,
                vpc_config,
                paco.cftemplates.VPCPeering,
                stack_tags=StackTags(self.stack_tags),
            )

        # NAT Gateway
        self.nat_list = []
        for nat_config in vpc_config.nat_gateway.values():
            if sg_nat_id in sg_config.keys():
                nat_sg_config = sg_config[sg_nat_id]
            else:
                nat_sg_config = None
            # We now disable the NAT Gateway in the template so that we can delete it and recreate it when disabled.
            nat_stack = self.add_new_stack(
                self.region,
                nat_config,
                paco.cftemplates.NATGateway,
                stack_tags=StackTags(self.stack_tags),
                stack_orders=[StackOrder.PROVISION],
                extra_context={'nat_sg_config': nat_sg_config},
            )
            self.nat_list.append(nat_stack)

        for nat_stack in self.nat_list:
            self.add_stack_order(nat_stack, [StackOrder.WAIT])

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
