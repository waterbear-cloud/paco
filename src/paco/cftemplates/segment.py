from paco.cftemplates.cftemplates import StackTemplate
from paco.stack.stack import StackOutputParam


class Segment(StackTemplate):
    def __init__(
      self,
      stack,
      paco_ctx,
      env_ctx,
    ):
        segment_config = stack.resource
        segment_config_ref = segment_config.paco_ref_parts
        self.env_ctx = env_ctx
        super().__init__(
            stack,
            paco_ctx,
        )
        self.set_aws_name('Segments', segment_config.name)

        vpc_stack = self.env_ctx.get_vpc_stack()
        availability_zones = self.env_ctx.env_region.network.availability_zones

        # Initialize Parameters
        # VPC
        self.set_parameter(StackOutputParam('VPC', vpc_stack, 'VPC', self))

        # Internet Gateway
        self.set_parameter(StackOutputParam('InternetGateway', vpc_stack, 'InternetGateway', self))

        # Subnet CIDRS
        self.set_parameter('SubnetAZ1CIDR', segment_config.az1_cidr)
        if segment_config.az2_cidr != '' and availability_zones > 1:
            self.set_parameter('SubnetAZ2CIDR', segment_config.az2_cidr)
        if segment_config.az3_cidr != '' and availability_zones > 2:
            self.set_parameter('SubnetAZ3CIDR', segment_config.az3_cidr)

        # Public Subnet boolean
        if segment_config.internet_access != '':
            self.set_parameter('IsPublicCondition', segment_config.internet_access)
        else:
            self.set_parameter('IsPublicCondition', 'false')
        # Define the Template
        template_yaml_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Segment: NACLs, RouteTables, Subnets'

#------------------------------------------------------------------------------
Parameters:
  VPC:
    Description: 'VPC ID'
    Type: String

  InternetGateway:
    Description: 'The Internet Gateway ID'
    Type: String
    Default: 'novalue'

  SubnetAZ1CIDR:
    Description: 'AZ1 - CIDR for the Subnet'
    Type: String

  SubnetAZ2CIDR:
    Description: 'AZ2 - CIDR for the Subnet'
    Type: String
    Default: 'novalue'

  SubnetAZ3CIDR:
    Description: 'AZ3 - CIDR for the Subnet'
    Type: String
    Default: 'novalue'

  IsPublicCondition:
    Description: 'If true, adds a default route to the Internet Gateway'
    Type: String
    AllowedValues:
      - true
      - false

#------------------------------------------------------------------------------
Conditions:
  IsPublic: !Equals [ !Ref IsPublicCondition, 'true' ]

  AZ2Disabled: !Equals [ !Ref SubnetAZ2CIDR, 'novalue' ]
  AZ2Enabled: !Not [ Condition: AZ2Disabled ]
  AZ2EnabledAndIsPublic: !And
    - !Condition AZ2Enabled
    - !Condition IsPublic


  AZ3Disabled: !Equals [ !Ref SubnetAZ3CIDR, 'novalue' ]
  AZ3Enabled: !Not [ Condition: AZ3Disabled ]
  AZ3EnabledAndIsPublic: !And
    - !Condition AZ3Enabled
    - !Condition IsPublic


#------------------------------------------------------------------------------
Resources:

#------------------------------------------------------------------------------
#  NACLs

#  Network ACL
  NACLAZ3:
    Type: AWS::EC2::NetworkAcl
    Properties:
      VpcId: !Ref VPC
#      Tags:

# Inbound NACL: Allow All
  NACLAZ3EntryInboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Properties:
      CidrBlock: 0.0.0.0/0
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ3

# Outbound NACL: Allow All
  NACLAZ3EntryOutboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Properties:
      CidrBlock: 0.0.0.0/0
      Egress: 'true'
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ3

#------------------------------------------------------------------------------
# Availability Zone 1

# ---------------------------
# NACL
  NACLAZ1:
    Type: AWS::EC2::NetworkAcl
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ1'

# Inbound NACL: Allow All
  NACLAZ1EntryInboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Properties:
      CidrBlock: 0.0.0.0/0
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ1

# Outbound NACL: Allow All
  NACLAZ1EntryOutboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Properties:
      CidrBlock: 0.0.0.0/0
      Egress: 'true'
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ1

# ---------------------------
  RouteTableAZ1:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ1'

  RouteDefaultGWAZ1:
    Type: AWS::EC2::Route
    Condition: IsPublic
    Properties:
      RouteTableId: !Ref RouteTableAZ1
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

# ---------------------------
  SubnetAZ1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref SubnetAZ1CIDR
      AvailabilityZone: !Select [ 0, !GetAZs '' ]
      Tags:
        - Key: 'Name'
          Value: !Sub '${{AWS::StackName}}-AZ1'

# Association: Route Table
  SubnetAZ1RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref SubnetAZ1
      RouteTableId: !Ref RouteTableAZ1

# Association: NACL
  SubnetAZ1NACLAssociation:
    Type: AWS::EC2::SubnetNetworkAclAssociation
    Properties:
      SubnetId: !Ref SubnetAZ1
      NetworkAclId: !Ref NACLAZ1
#------------------------------------------------------------------------------
# Availability Zone 2

# ---------------------------
# NACL
  NACLAZ2:
    Type: AWS::EC2::NetworkAcl
    Condition: AZ2Enabled
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ2'

# Inbound NACL: Allow All
  NACLAZ2EntryInboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Condition: AZ2Enabled
    Properties:
      CidrBlock: 0.0.0.0/0
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ2

# Outbound NACL: Allow All
  NACLAZ2EntryOutboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Condition: AZ2Enabled
    Properties:
      CidrBlock: 0.0.0.0/0
      Egress: 'true'
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ2

# ---------------------------
  RouteTableAZ2:
    Type: AWS::EC2::RouteTable
    Condition: AZ2Enabled
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ2'

  RouteDefaultGWAZ2:
    Type: AWS::EC2::Route
    Condition: AZ2EnabledAndIsPublic
    Properties:
      RouteTableId: !Ref RouteTableAZ2
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

# ---------------------------
  SubnetAZ2:
    Type: AWS::EC2::Subnet
    Condition: AZ2Enabled
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref SubnetAZ2CIDR
      AvailabilityZone: !Select [ 1, !GetAZs '' ]
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ2'


# Association: Route Table
  SubnetAZ2RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Condition: AZ2Enabled
    Properties:
      SubnetId: !Ref SubnetAZ2
      RouteTableId: !Ref RouteTableAZ2

# Association: NACL
  SubnetAZ2NACLAssociation:
    Type: AWS::EC2::SubnetNetworkAclAssociation
    Condition: AZ2Enabled
    Properties:
      SubnetId: !Ref SubnetAZ2
      NetworkAclId: !Ref NACLAZ2

#------------------------------------------------------------------------------
# Availability Zone 3

# ---------------------------
# NACL
  NACLAZ3:
    Type: AWS::EC2::NetworkAcl
    Condition: AZ3Enabled
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ3'

# Inbound NACL: Allow All
  NACLAZ3EntryInboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Condition: AZ3Enabled
    Properties:
      CidrBlock: 0.0.0.0/0
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ3

# Outbound NACL: Allow All
  NACLAZ3EntryOutboundAll:
    Type: AWS::EC2::NetworkAclEntry
    Condition: AZ3Enabled
    Properties:
      CidrBlock: 0.0.0.0/0
      Egress: 'true'
      Protocol: '-1'
      RuleAction: allow
      RuleNumber: '100'
      NetworkAclId: !Ref NACLAZ3

# ---------------------------
  RouteTableAZ3:
    Type: AWS::EC2::RouteTable
    Condition: AZ3Enabled
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ3'

  RouteDefaultGWAZ3:
    Type: AWS::EC2::Route
    Condition: AZ3EnabledAndIsPublic
    Properties:
      RouteTableId: !Ref RouteTableAZ3
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

# ---------------------------
  SubnetAZ3:
    Type: AWS::EC2::Subnet
    Condition: AZ3Enabled
    Properties:
      VpcId: !Ref VPC
      CidrBlock: !Ref SubnetAZ3CIDR
      AvailabilityZone: !Select [ 2, !GetAZs '' ]
      Tags:
        - Key: Name
          Value: !Sub '${{AWS::StackName}}-AZ3'


# Association: Route Table
  SubnetAZ3RouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Condition: AZ3Enabled
    Properties:
      SubnetId: !Ref SubnetAZ3
      RouteTableId: !Ref RouteTableAZ3

# Association: NACL
  SubnetAZ3NACLAssociation:
    Type: AWS::EC2::SubnetNetworkAclAssociation
    Condition: AZ3Enabled
    Properties:
      SubnetId: !Ref SubnetAZ3
      NetworkAclId: !Ref NACLAZ3


#------------------------------------------------------------------------------
# Outputs
Outputs:
  SubnetList1:
    Value: !Sub '${{SubnetAZ1}}'
  SubnetList2:
    Condition: AZ2Enabled
    Value: !Sub '${{SubnetAZ1}},${{SubnetAZ2}}'
  SubnetList3:
    Condition: AZ3Enabled
    Value: !Sub '${{SubnetAZ1}},${{SubnetAZ2}},${{SubnetAZ3}}'
  SubnetIdList:
    Value: !Sub '{0[subnet_list]:s}'
  SubnetIdAZ1:
    Value: !Sub '${{SubnetAZ1}}'
  SubnetIdAZ2:
    Condition: AZ2Enabled
    Value: !Sub '${{SubnetAZ2}}'
  SubnetIdAZ3:
    Condition: AZ3Enabled
    Value: !Sub '${{SubnetAZ3}}'
  AvailabilityZone1:
    Value: !GetAtt [SubnetAZ1, AvailabilityZone]
  AvailabilityZone2:
    Condition: AZ2Enabled
    Value: !GetAtt [SubnetAZ2, AvailabilityZone]
  AvailabilityZone3:
    Condition: AZ3Enabled
    Value: !GetAtt [SubnetAZ3, AvailabilityZone]
  RouteTableIdAZ1:
    Value: !Sub '${{RouteTableAZ1}}'
  RouteTableIdAZ2:
    Condition: AZ2Enabled
    Value: !Sub '${{RouteTableAZ2}}'
  RouteTableIdAZ3:
    Condition: AZ3Enabled
    Value: !Sub '${{RouteTableAZ3}}'
"""
        template_table = {
            'subnet_list': None
        }

        # Subnet List
        subnet_list = ""
        for az_idx in range(0, availability_zones):
            if az_idx > 0:
               subnet_list += ','
            subnet_list += "${{SubnetAZ{}}}".format(az_idx+1)
        template_table['subnet_list'] = subnet_list
        self.set_template(template_yaml_fmt.format(template_table))

        self.stack.register_stack_output_config(segment_config_ref+'.subnet_id_list', 'SubnetIdList')
        self.stack.register_stack_output_config(segment_config_ref+'.az1.subnet_id', 'SubnetIdAZ1')
        self.stack.register_stack_output_config(segment_config_ref+'.az1.availability_zone', 'AvailabilityZone1')
        self.stack.register_stack_output_config(segment_config_ref+'.az1.route_table.id', 'RouteTableIdAZ1')
        if availability_zones > 1:
            self.stack.register_stack_output_config(segment_config_ref+'.az2.subnet_id', 'SubnetIdAZ2')
            self.stack.register_stack_output_config(segment_config_ref+'.az2.availability_zone', 'AvailabilityZone2')
            self.stack.register_stack_output_config(segment_config_ref+'.az2.route_table.id', 'RouteTableIdAZ2')
        if availability_zones > 2:
            self.stack.register_stack_output_config(segment_config_ref+'.az3.subnet_id', 'SubnetIdAZ3')
            self.stack.register_stack_output_config(segment_config_ref+'.az3.availability_zone', 'AvailabilityZone3')
            self.stack.register_stack_output_config(segment_config_ref+'.az3.route_table.id', 'RouteTableIdAZ3')
