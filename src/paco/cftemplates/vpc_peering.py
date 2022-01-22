from paco.cftemplates.cftemplates import StackTemplate
from paco.models.locations import get_parent_by_interface
from paco.models import schemas, references
import troposphere
import troposphere.ec2
import troposphere.route53


class VPCPeering(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        vpc_config = stack.resource
        network_config = get_parent_by_interface(vpc_config, schemas.INetwork)
        env_name = get_parent_by_interface(vpc_config, schemas.IEnvironment).name
        netenv_name = get_parent_by_interface(vpc_config, schemas.INetworkEnvironment).name
        super().__init__(
            stack,
            paco_ctx,
        )
        self.set_aws_name('VPCPeering')
        self.init_template('VPC Peering')

        # VPC Peering
        vpc_id_param = self.create_cfn_parameter(
            name='VpcId',
            param_type='AWS::EC2::VPC::Id',
            description='The VPC Id',
            value='paco.ref netenv.{}.<environment>.<region>.network.vpc.id'.format(netenv_name),
        )

        # Peer
        any_peering_enabled = False
        for peer in vpc_config.peering.keys():
            peer_config = vpc_config.peering[peer]
            if peer_config.is_enabled() and peer_config.peer_type == 'requester':
                any_peering_enabled = True
            else:
                continue

            if peer_config.network_environment != None:
                peer_config = self.get_peer_config(peer_config)

            vpc_peering_connection_res = troposphere.ec2.VPCPeeringConnection(
                'VPCPeeringConnection' + peer.title(),
                PeerOwnerId = peer_config.peer_account_id,
                PeerRegion = peer_config.peer_region,
                PeerVpcId = peer_config.peer_vpcid,
                PeerRoleArn = f'arn:aws:iam::{peer_config.peer_account_id}:role/{peer_config.peer_role_name}',
                VpcId = troposphere.Ref(vpc_id_param)
            )

            self.template.add_resource(vpc_peering_connection_res)
            # Routes
            for route in peer_config.routing:
                for az in range(0, network_config.availability_zones):
                    az_str = str(az+1)
                    resource_name_suffix = peer.title() + 'AZ' + az_str
                    route_table_param = self.create_cfn_parameter(
                        name='PeerRouteTableId' + resource_name_suffix,
                        param_type='String',
                        description='The route table ID for AZ {}.'.format(az_str),
                        value='{}.az{}.route_table.id'.format(route.segment, az_str),
                    )
                    peer_route_res = troposphere.ec2.Route(
                        'PeeringRoute' + resource_name_suffix,
                        DestinationCidrBlock = route.cidr,
                        VpcPeeringConnectionId = troposphere.Ref(vpc_peering_connection_res),
                        RouteTableId = troposphere.Ref(route_table_param)
                    )
                    self.template.add_resource(peer_route_res)

        self.set_enabled(any_peering_enabled)

    def get_peer_config(self, peer_config):
        # Get Config
        netenv_ref = references.Reference(peer_config.network_environment + '.network')
        netenv_config = netenv_ref.resolve(self.paco_ctx.project)

        # Peer Account ID
        peer_config.peer_account_id = self.paco_ctx.get_ref(netenv_config.aws_account + '.id')

        # Peer Region
        peer_config.peer_region = netenv_ref.region

        # Peer VPC Id
        peer_config.peer_vpcid = self.paco_ctx.get_ref(netenv_config.vpc.paco_ref + '.id')

        # Peer Role name is not yet automated and needs manual configuration

        return peer_config

