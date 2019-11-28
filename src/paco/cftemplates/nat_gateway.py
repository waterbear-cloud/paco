import os
from paco.cftemplates.cftemplates import CFTemplate

from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference
from io import StringIO
from enum import Enum


class NATGateway(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 stack_order,
                 nat_config):

        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=nat_config.is_enabled(),
            config_ref=nat_config.paco_ref_parts,
            iam_capabilities=["CAPABILITY_NAMED_IAM"],
            stack_group=stack_group,
            stack_tags=stack_tags,
            stack_order=stack_order
        )
        self.set_aws_name('NGW', nat_config.name)

        network_config = get_parent_by_interface(nat_config, schemas.INetworkEnvironment)

        self.set_parameter('NATGatewayEnabled', nat_config.is_enabled())

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'NAT Gateways'

Parameters:

  NATGatewayEnabled:
    Type: String
    Default: False
    AllowedValues:
      - true
      - false

{0[parameters_yaml]:s}

Conditions:

  NATGatewayIsEnabled: !Equals [!Ref NATGatewayEnabled, "true"]

Resources:
{0[resources_yaml]:s}

Outputs:
{0[outputs_yaml]:s}
"""

        net_eip_params_fmt = """
  SubnetId{0[id]:s}:
    Description: The Subnet Id where the NAT Gateway for {0[id]:s} will be attached.
    Type: AWS::EC2::Subnet::Id
"""

        nat_eip_fmt = """
  EIP{0[id]:s}:
    Type: AWS::EC2::EIP
    Properties:
      Domain: vpc

  NATGateway{0[id]:s}:
    Type: AWS::EC2::NatGateway
    Condition: NATGatewayIsEnabled
    Properties:
      AllocationId: !GetAtt [EIP{0[id]:s}, AllocationId]
      SubnetId: !Ref SubnetId{0[id]:s}
"""

        outputs_fmt = """
  NATGatewayPublicIp{0[id]:s}:
    Value: !Ref EIP{0[id]:s}
"""

        default_route_params_fmt = """
  RouteTable{0[segment]:s}{0[az_id]:s}:
    Description: The Route Table Id for Segment {0[segment]:s} in {0[az_id]:s} to place a default route in.
    Type: String
"""

        default_route_fmt = """
  SegmentDefaultRoute{0[segment]:s}{0[az_id]:s}:
    Type: AWS::EC2::Route
    Condition: NATGatewayIsEnabled
    Properties:
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NATGateway{0[gateway_id]:s}
      RouteTableId: !Ref RouteTable{0[segment]:s}{0[az_id]:s}
"""

        default_route_table = {
            'az_id': None,
            'segment': None,
            'gateway_id': None
        }

        template_table = {
            'parameters_yaml': "",
            'resources_yaml': "",
            'outputs_yaml': ""
        }

        cf_table = {
            'id': None,
        }

        num_vpc_azs = network_config.availability_zones
        segment_ref = nat_config.segment
        if nat_config.availability_zone == 'all':
            cur_az = 1
        else:
            cur_az = nat_config.availability_zone

        while True:
            unique_id = "AZ{0}".format(cur_az)
            cf_table['id'] = unique_id
            subnet_id_ref = '{}.az{}.subnet_id'.format(segment_ref, cur_az)
            self.set_parameter('SubnetId'+unique_id, subnet_id_ref)
            template_table['parameters_yaml'] += net_eip_params_fmt.format(cf_table)
            template_table['resources_yaml'] += nat_eip_fmt.format(cf_table)
            template_table['outputs_yaml'] += outputs_fmt.format(cf_table)

            if nat_config.availability_zone == 'all' and cur_az == num_vpc_azs:
                break
            elif nat_config.availability_zone != 'all':
                break
            cur_az += 1

        while True:
            gateway_id = "AZ{0}".format(nat_config.availability_zone)
            for cur_az in range(1, num_vpc_azs+1):
                az_id = "AZ{0}".format(cur_az)
                if nat_config.availability_zone == 'all':
                    gateway_id = az_id
                # Default Routes
                for segment_ref in nat_config.default_route_segments:
                    paco_ref = Reference(segment_ref)
                    segment_id = paco_ref.last_part
                    default_route_table['segment'] = segment_id
                    default_route_table['az_id'] = az_id
                    default_route_table['gateway_id'] = gateway_id
                    self.set_parameter('RouteTable'+segment_id+az_id, segment_ref+".az{0}.route_table.id".format(cur_az))
                    template_table['parameters_yaml'] += default_route_params_fmt.format(default_route_table)
                    template_table['resources_yaml'] += default_route_fmt.format(default_route_table)

            if nat_config.availability_zone == 'all' and cur_az == num_vpc_azs:
                break
            elif nat_config.availability_zone != 'all':
                break

        self.set_template(template_fmt.format(template_table))

