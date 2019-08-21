import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from io import StringIO
from enum import Enum


class NATGateway(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 env_ctx,
                 nat_id,
                 config_ref):
        #aim_ctx.log("NATGateway CF Template init")
        self.env_ctx = env_ctx
        aws_name = '-'.join(["NGW",nat_id])

        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         config_ref=config_ref,
                         aws_name=aws_name,
                         iam_capabilities=["CAPABILITY_NAMED_IAM"])

        self.set_parameter('NATGatewayEnabled', self.env_ctx.nat_gateway_enabled(nat_id))

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

        parameters_yaml = ""
        resources_yaml = ""
        outputs_yaml = ""

        nat_az = self.env_ctx.nat_gateway_az(nat_id)
        num_vpc_azs = self.env_ctx.availability_zones()
        nat_segment = self.env_ctx.nat_gateway_segment(nat_id)
        segment_ref = self.env_ctx.gen_ref(segment_id=nat_segment)
        if nat_az == 'all':
            cur_az = 1
        else:
            cur_az = nat_az

        while True:
            unique_id = "AZ{0}".format(cur_az)
            cf_table['id'] = unique_id
            self.set_parameter('SubnetId'+unique_id, segment_ref+".az{0}.subnet_id".format(cur_az))
            template_table['parameters_yaml'] += net_eip_params_fmt.format(cf_table)
            template_table['resources_yaml'] += nat_eip_fmt.format(cf_table)
            template_table['outputs_yaml'] += outputs_fmt.format(cf_table)

            if nat_az == 'all' and cur_az == num_vpc_azs:
                break
            elif nat_az != 'all':
                break
            cur_az += 1

        while True:
            gateway_id = "AZ{0}".format(nat_az)
            for cur_az in range(1, num_vpc_azs+1):
                az_id = "AZ{0}".format(cur_az)
                if nat_az == 'all':
                    gateway_id = az_id
                # Default Routes
                dgw_segments = self.env_ctx.nat_gateway_default_route_segments(nat_id)
                for segment_id in dgw_segments:
                    segment_ref = self.env_ctx.gen_ref(segment_id=segment_id)
                    default_route_table['segment'] = segment_id
                    default_route_table['az_id'] = az_id
                    default_route_table['gateway_id'] = gateway_id
                    self.set_parameter('RouteTable'+segment_id+az_id, segment_ref+".az{0}.route_table.id".format(cur_az))
                    template_table['parameters_yaml'] += default_route_params_fmt.format(default_route_table)
                    template_table['resources_yaml'] += default_route_fmt.format(default_route_table)

            if nat_az == 'all' and cur_az == num_vpc_azs:
                break
            elif nat_az != 'all':
                break

        self.set_template(template_fmt.format(template_table))

