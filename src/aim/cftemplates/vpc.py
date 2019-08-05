import os
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from io import StringIO
from enum import Enum


class VPC(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 vpc_config,
                 vpc_config_ref):
        #aim_ctx.log("VPC CF Template init")

        super().__init__(aim_ctx=aim_ctx,
                         account_ctx=account_ctx,
                         aws_region=aws_region,
                         config_ref=vpc_config_ref,
                         aws_name='-'.join(["VPC"]))

        # Initialize Parameters
        self.set_parameter('CIDR', vpc_config.cidr)
        self.set_parameter('EnableInternetGatewayCondition', vpc_config.enable_internet_gateway)
#        self.set_parameter('EnableVGWCondition', vpc_config['vpn_gateway']['enabled'])
        self.set_parameter('EnablePrivateHostedZoneCondition', vpc_config.private_hosted_zone.enabled)
        self.set_parameter('EnableDnsHostnames', vpc_config.enable_dns_hostnames)
        self.set_parameter('EnableDnsSupport', vpc_config.enable_dns_support)
        self.set_parameter('InternalDomainName', vpc_config.private_hosted_zone.name)

        # Define the Template
        self.set_template("""
AWSTemplateFormatVersion: '2010-09-09'

Description: 'VPC, Optional Internet Gateway, Optional Virtual Gateway'

#------------------------------------------------------------------------------
Parameters:
  CIDR:
    Description: CIDR for the VPC
    Type: String
    MinLength: '9'
    MaxLength: '18'
    ConstraintDescription: must be a valid CIDR range of the form x.x.x.x/x

  EnableInternetGatewayCondition:
    Type: String
    AllowedValues:
      - true
      - false

#  EnableVGWCondition:
#    Type: String
#    AllowedValues:
#      - true
#      - false

  EnablePrivateHostedZoneCondition:
    Type: String
    AllowedValues:
      - true
      - false

  EnableDnsHostnames:
    Type: String
    Default: true
    AllowedValues:
      - true
      - false

  EnableDnsSupport:
    Type: String
    Default: true
    AllowedValues:
      - true
      - false

  InternalDomainName:
    Type: String

  EnableNATGateway:
    Type: String
    Default: false
    AllowedValues:
      - true
      - false

#------------------------------------------------------------------------------
Conditions:
  EnableInternetGateway: !Equals [ !Ref EnableInternetGatewayCondition, 'true' ]
#  EnableVGW: !Equals [ !Ref EnableVGWCondition, 'true' ]
  EnablePrivateHostedZone: !Equals [ !Ref EnablePrivateHostedZoneCondition, 'true' ]

#------------------------------------------------------------------------------
Resources:

# VPC: Virtual Private Cloud
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref CIDR
      EnableDnsSupport: !Ref EnableDnsSupport
      EnableDnsHostnames: !Ref EnableDnsHostnames

#------------------------------------------------------------------------------
# Gateway to the Internet
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Condition: EnableInternetGateway
    DependsOn:
      - VPC

# Attach the Internet Gateway to the VPC
  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    DependsOn:
      - VPC
      - InternetGateway
    Condition: EnableInternetGateway
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

#------------------------------------------------------------------------------
#  VGW:
#    Type: "AWS::EC2::VPNGateway"
#    Condition: EnableVGW
#    Properties:
#      Type: ipsec.1

#  VPCGatewayAttachment:
#    Type: "AWS::EC2::VPCGatewayAttachment"
#    Condition: EnableVGW
#    Properties:
#      VpcId: !Ref VPC
#      VpnGatewayId: !Ref VGW

#------------------------------------------------------------------------------
  PrivateHostedZone:
    Type: "AWS::Route53::HostedZone"
    Condition: EnablePrivateHostedZone
    Properties:
      Name: !Ref InternalDomainName
      VPCs:
        - VPCId: !Ref VPC
          VPCRegion: !Ref AWS::Region

#------------------------------------------------------------------------------
Outputs:
  VPC:
    Value: !Ref VPC

  InternetGateway:
    Condition: EnableInternetGateway
    Value: !Ref InternetGateway
#------------------------------------------------------------------------------
""")
        # Config Model AWS resource Ids
        # vpc_ref: <netenv>.network.vpc
        self.register_stack_output_config(vpc_config_ref, 'VPC')
        self.register_stack_output_config(vpc_config_ref + ".internet_gateway", 'InternetGateway')

    def validate(self):
        #self.aim_ctx.log("Validating VPC Template")
        super().validate()
