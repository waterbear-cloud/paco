import os
import troposphere
import troposphere.ec2

from enum import Enum
from io import StringIO
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference
from paco import utils

class NATGateway(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 stack_order,
                 network_config,
                 nat_sg_config,
                 nat_sg_config_ref,
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

        if nat_config.type == 'Managed':
            self.managed_nat_gateway(network_config, nat_config)
        else:
            self.init_template('EC2 NAT Gateway')
            if nat_config.is_enabled() == True:
                self.ec2_nat_gateway(network_config, nat_sg_config, nat_sg_config_ref, nat_config)
            # Generate the Template
            self.set_template(self.template.to_yaml())

    def ec2_nat_gateway(self, network_config, nat_sg_config, nat_sg_config_ref, nat_config):

        nat_az = nat_config.availability_zone
        nat_segment = nat_config.segment.split('.')[-1]
        ec2_resource = {}
        for az_idx in range(1, network_config.availability_zones+1):
            # Add security groups created for NAT Bastions
            nat_security_groups = []
            nat_security_groups.extend(nat_config.security_groups)
            if nat_az == 'all':
                nat_sg_id = nat_config.name + "_az" + str(az_idx)
                nat_security_groups.append('paco.ref ' + nat_sg_config_ref + '.' + nat_sg_id)
            elif az_idx == int(nat_config.availability_zone):
                for nat_sg_id in nat_sg_config.keys():
                    nat_security_groups.append('paco.ref ' + nat_sg_config_ref + '.' + nat_sg_id)

            if nat_az == 'all' or nat_az == str(az_idx):
                security_group_list_param = self.create_cfn_ref_list_param(
                    param_type='List<AWS::EC2::SecurityGroup::Id>',
                    name='NATSecurityGroupListAZ'+str(az_idx),
                    description='List of security group ids to attach to the instances.',
                    value=nat_security_groups,
                    ref_attribute='id',
                    use_troposphere=True,
                    troposphere_template=self.template
                )

                subnet_id_param = self.create_cfn_parameter(
                    name=self.create_cfn_logical_id_join(
                        str_list=['SubnetIdAZ', str(az_idx), nat_segment],
                        camel_case=True),
                    param_type='String',
                    description='SubnetId to launch an EC2 NAT instance',
                    value=nat_config.segment + '.az' + str(az_idx) + '.subnet_id',
                    use_troposphere=True,
                    troposphere_template=self.template,
                )
                ref_parts = nat_config.paco_ref_parts.split('.')
                instance_name = utils.big_join(
                    str_list=[ref_parts[1], ref_parts[2], 'NGW', nat_config.name, 'AZ'+str(az_idx)],
                    separator_ch='-',
                    camel_case=True
                )

                ec2_resource[az_idx] = troposphere.ec2.Instance(
                    title = self.create_cfn_logical_id_join(
                        str_list = ['EC2NATInstance', str(az_idx)],
                        camel_case=True),
                    template = self.template,
                    SubnetId = troposphere.Ref(subnet_id_param),
                    ImageId = self.paco_ctx.get_ref('paco.ref function.aws.ec2.ami.latest.amazon-linux-nat', self.account_ctx),
                    InstanceType = nat_config.ec2_instance_type,
                    KeyName = self.paco_ctx.get_ref(nat_config.ec2_key_pair+'.keypair_name'),
                    SecurityGroupIds = troposphere.Ref(security_group_list_param),
                    SourceDestCheck=False,
                    Tags=troposphere.ec2.Tags(Name=instance_name)
                )

                ec2_instance_id_output = troposphere.Output(
                    title=ec2_resource[az_idx].title+'Id',

                    Description="EC2 NAT Instance Id",
                    Value=troposphere.Ref(ec2_resource[az_idx])
                )
                self.template.add_output( ec2_instance_id_output )

                troposphere.ec2.EIP(
                    title=self.create_cfn_logical_id_join(
                        str_list = ['ElasticIP', str(az_idx)],
                        camel_case=True),
                    template=self.template,
                    Domain='vpc',
                    InstanceId=troposphere.Ref(ec2_resource[az_idx])
                )

                self.register_stack_output_config(nat_config.paco_ref_parts + ".ec2.az" + str(az_idx), ec2_instance_id_output.title)

        # Add DefaultRoute to the route tables in each AZ
        for segment_ref in nat_config.default_route_segments:
            segment_id = segment_ref.split('.')[-1]
            # Routes
            for az_idx in range(1, network_config.availability_zones+1):
                if nat_config.availability_zone == 'all':
                    instance_id_ref = troposphere.Ref(ec2_resource[az_idx])
                else:
                    instance_id_ref = troposphere.Ref(ec2_resource[int(nat_az)])

                route_table_id_param = self.create_cfn_parameter(
                    name=self.create_cfn_logical_id_join(
                        str_list=['RouteTable', segment_id, 'AZ', str(az_idx)],
                        camel_case=True),
                    param_type='String',
                    description='RouteTable ID for '+segment_id+' AZ'+str(az_idx),
                    value=segment_ref+".az{}.route_table.id".format(az_idx),
                    use_troposphere=True,
                    troposphere_template=self.template)

                troposphere.ec2.Route(
                    title="EC2NATRouteAZ"+str(az_idx),
                    template=self.template,
                    DestinationCidrBlock="0.0.0.0/0",
                    InstanceId=instance_id_ref,
                    RouteTableId=troposphere.Ref(route_table_id_param)
                )

    def managed_nat_gateway(self, network_config, nat_config):

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

