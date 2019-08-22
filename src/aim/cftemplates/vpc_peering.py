import os
import troposphere
import troposphere.ec2
import troposphere.route53
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from io import StringIO
from enum import Enum


class VPCPeering(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 netenv_name,
                 network_config,
                 vpc_config_ref):
        #aim_ctx.log("VPC CF Template init")

        super().__init__(aim_ctx=aim_ctx,
                         account_ctx=account_ctx,
                         aws_region=aws_region,
                         config_ref=vpc_config_ref,
                         aws_name='-'.join(["VPCPeering"]))

        vpc_config = network_config.vpc
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('VPC Peering')


        #---------------------------------------------------------------------
        # VPC Peering
        vpc_id_param = self.gen_parameter(
            name='VpcId',
            param_type='AWS::EC2::VPC::Id',
            description='The VPC Id',
            value='aim.ref netenv.{}.<account>.<region>.network.vpc.id'.format(netenv_name),
            use_troposphere=True
        )
        template.add_parameter(vpc_id_param)

        # Peer
        for peer in vpc_config.peering.keys():
            peer_config = vpc_config.peering[peer]

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
                    route_table_param = self.gen_parameter(
                        name='PeerRouteTableId' + resource_name_suffix,
                        param_type='String',
                        description='The route table ID for AZ {}.'.format(az_str),
                        value='{}.az{}.route_table.id'.format(route.segment, az_str),
                        use_troposphere=True
                    )
                    peer_route_res = troposphere.ec2.Route(
                        'PeeringRoute' + resource_name_suffix,
                        DestinationCidrBlock = route.cidr,
                        VpcPeeringConnectionId = troposphere.Ref(vpc_peering_connection_res),
                        RouteTableId = troposphere.Ref(route_table_param)
                    )
                    template.add_parameter(route_table_param)
                    template.add_resource(peer_route_res)

        # Define the Template
        self.set_template(template.to_yaml())

