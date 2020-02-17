import os
import troposphere
import troposphere.ec2
import troposphere.route53
from paco.cftemplates.cftemplates import CFTemplate

from io import StringIO
from enum import Enum


class VPCPeering(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        netenv_name,
        env_name,
        network_config,
        vpc_config_ref
    ):
        super().__init__(
            paco_ctx=paco_ctx,
            account_ctx=account_ctx,
            aws_region=aws_region,
            config_ref=vpc_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            environment_name = env_name
        )
        self.set_aws_name('VPCPeering')

        vpc_config = network_config.vpc
        self.init_template('VPC Peering')
        template = self.template

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
            if peer_config.is_enabled():
                any_peering_enabled = True
            else:
                continue
            vpc_peering_connection_res = troposphere.ec2.VPCPeeringConnection(
                'VPCPeeringConnection' + peer.title(),
                PeerOwnerId = peer_config.peer_account_id,
                PeerRegion = peer_config.peer_region,
                PeerVpcId = peer_config.peer_vpcid,
                PeerRoleArn = 'arn:aws:iam::{}:role/{}'.format(
                    peer_config.peer_account_id, peer_config.peer_role_name
                ),
                VpcId = troposphere.Ref(vpc_id_param)
            )

            template.add_resource(vpc_peering_connection_res)
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
                    template.add_resource(peer_route_res)

        self.enabled = any_peering_enabled

        # Define the Template
        self.set_template()

