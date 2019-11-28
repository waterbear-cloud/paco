import os
from paco.cftemplates.cftemplates import CFTemplate

from paco.cftemplates.cftemplates import StackOutputParam
from paco.models.references import Reference
from io import StringIO
from enum import Enum


class ELB(CFTemplate):
    def __init__(self, paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 env_ctx,
                 app_id,
                 grp_id,
                 elb_id,
                 elb_config,
                 elb_config_ref):
        #paco_ctx.log("ELB CF Template init")

        self.env_ctx = env_ctx
        segment_stack = self.env_ctx.get_segment_stack(elb_config['segment'])

        super().__init__(paco_ctx=paco_ctx,
                         account_ctx=account_ctx,
                         aws_region=aws_region,
                         enabled=elb_config.is_enabled(),
                         config_ref=elb_config_ref,
                         stack_group=stack_group,
                         stack_tags=stack_tags)
        self.set_aws_name('ELB', grp_id, elb_id)

        # Initialize Parameters
        self.set_parameter('HealthyThreshold', elb_config['health_check']['healthy_threshold'])
        self.set_parameter('HealthCheckInterval', elb_config['health_check']['interval'])
        self.set_parameter('HealthyTimeout', elb_config['health_check']['timeout'])
        self.set_parameter('HealthCheckTarget', elb_config['health_check']['target'])
        self.set_parameter('UnhealthyThreshold', elb_config['health_check']['unhealthy_threshold'])
        self.set_parameter('ConnectionDrainingEnabled', elb_config['connection_draining']['enabled'])
        self.set_parameter('ConnectionDrainingTimeout', elb_config['connection_draining']['timeout'])
        self.set_parameter('ConnectionSettingsIdleSeconds', elb_config['connection_settings']['idle_timeout'])
        self.set_parameter('CrossZone', elb_config['cross_zone'])
        self.set_parameter('CustomDomainName', elb_config['dns']['domain_name'])
        self.set_parameter('HostedZoneId', elb_config['dns']['hosted_zone'])
        self.set_parameter('DNSEnabled', elb_config.is_dns_enabled())

        elb_region = self.env_ctx.region
        self.set_parameter('ELBHostedZoneId', self.lb_hosted_zone_id('elb', elb_region))

        # 32 Characters max
        # <proj>-<env>-<app>-<elb_id>
        # TODO: Limit each name item to 7 chars
        # Name collision risk:, if unique identifying characrtes are truncated
        #   - Add a hash?
        #   - Check for duplicates with validating template
        # TODO: Make a method for this
        #load_balancer_name = paco_ctx.project_ctx.name + "-" + paco_ctx.env_ctx.name + "-" + stack_group_ctx.application_name + "-" + elb_id
        load_balancer_name = self.create_resource_name_join(
            name_list=[self.env_ctx.netenv_id, self.env_ctx.env_id, app_id, elb_id],
            separator='',
            camel_case=True
        )
        self.set_parameter('LoadBalancerEnabled', elb_config.is_enabled())
        self.set_parameter('LoadBalancerName', load_balancer_name)

        self.set_parameter('Scheme', elb_config['scheme'])

        # Segment SubnetList is a Segment stack Output based on availability zones
        subnet_list_key = 'SubnetList' + str(self.env_ctx.availability_zones())
        self.set_parameter(StackOutputParam('SubnetList', segment_stack, subnet_list_key, self))

        # Security Group List
        # TODO: Use self.create_cfn_ref_list_param()
        sg_output_param = StackOutputParam('SecurityGroupList', param_template=self)
        for sg_ref in elb_config['security_groups']:
            # TODO: Better name for self.get_stack_outputs_key_from_ref?
            sg_output_key = self.get_stack_outputs_key_from_ref(Reference(sg_ref))
            sg_stack = self.paco_ctx.get_ref(sg_ref, 'stack')
            sg_output_param.add_stack_output(sg_stack, sg_output_key)
        self.set_parameter(sg_output_param)

        # Define the Template
        template_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Elastic Load Balancer'

Parameters:

  LoadBalancerEnabled:
    Description: Boolean indicating whether the load balancer is enabled or not.
    Type: String
    AllowedValues:
      - true
      - false

  HealthyThreshold:
    Description: Specifies the number of consecutive health probe successes required before moving the instance to the Healthy state.
    Type: Number

  HealthCheckInterval:
    Description: Specifies the approximate interval, in seconds, between health checks of an individual instance.
    Type: Number

  HealthyTimeout:
    Description: Specifies the amount of time, in seconds, during which no response means a failed health probe.
    Type: Number

  HealthCheckTarget:
    Description: The ELBs healtcheck target
    Type: String

  UnhealthyThreshold:
    Description: Specifies the number of consecutive health probe failures required before moving the instance to the Unhealthy state.
    Type: Number

  ConnectionDrainingEnabled:
    Description: Boolean indicating whether connections draining is enabled
    Type: String
    AllowedValues:
      - true
      - false

  ConnectionDrainingTimeout:
    Description: The time in seconds after the load balancer closes all connections to a deregistered or unhealthy instance.
    Type: Number

  ConnectionSettingsIdleSeconds:
    Description: The time in seconds that a connection to the load balancer can remain idle before being forcibly closed.
    Type: Number

  CrossZone:
    Description: Whether cross availability zone load balancing is enabled for the load balancer.
    Type: String
    MinLength: '1'
    MaxLength: '128'

  LoadBalancerName:
    Description: The name of the load balancer
    Type: String

  Scheme:
    Description: 'Specify internal to create an internal load balancer with a DNS name that resolves to private IP addresses or internet-facing to create a load balancer with a publicly resolvable DNS name, which resolves to public IP addresses.'
    Type: String
    MinLength: '1'
    MaxLength: '128'

  SubnetList:
    Description: A list of subnets where the ELBs instances will be provisioned
    Type: List<AWS::EC2::Subnet::Id>

  SecurityGroupList:
    Description: A List of security groups to attach to the ELB
    Type: List<AWS::EC2::SecurityGroup::Id>

  CustomDomainName:
    Description: Custom DNS name to assign to the ELB
    Type: String
    Default: ""

  HostedZoneId:
    Description: The Route53 Hosted Zone ID where the Custom Domain will be added
    Type: String

  ELBHostedZoneId:
    Description: The Regonal AWS Route53 Hosted Zone ID
    Type: String

  DNSEnabled:
    Description: Enables the creation of DNS Record Sets
    Type: String

{0[SSLCertificateParameters]:s}

Conditions:
  IsEnabled: !Equals [!Ref LoadBalancerEnabled, "true"]
  CustomDomainExists: !Not [!Equals [!Ref CustomDomainName, ""] ]
  DNSIsEnabled: !Equals [!Ref DNSEnabled, "true"]
  CustomDomainIsEnabled: !And
    - !Condition DNSIsEnabled
    - !Condition CustomDomainExists
    - !Condition IsEnabled

Resources:

# Elastic Load Balancer

  ClassicLoadBalancer:
    Type: AWS::ElasticLoadBalancing::LoadBalancer
    Condition: IsEnabled
    Properties:
      LoadBalancerName: !Ref LoadBalancerName
      Subnets: !Ref SubnetList
      HealthCheck:
        HealthyThreshold: !Ref HealthyThreshold
        Interval: !Ref HealthCheckInterval
        Target: !Ref HealthCheckTarget
        Timeout: !Ref HealthyTimeout
        UnhealthyThreshold: !Ref UnhealthyThreshold
      ConnectionDrainingPolicy:
        Enabled: !Ref ConnectionDrainingEnabled
        Timeout: !Ref ConnectionDrainingTimeout
      ConnectionSettings:
        IdleTimeout: !Ref ConnectionSettingsIdleSeconds
      CrossZone: !Ref CrossZone
      Scheme: !Ref Scheme
      SecurityGroups: !Ref SecurityGroupList
      Listeners: {0[Listeners]:s}

  RecordSet:
    Type: AWS::Route53::RecordSet
    Condition: CustomDomainIsEnabled
    Properties:
      HostedZoneId: !Ref HostedZoneId
      Name: !Ref CustomDomainName
      Type: A
      AliasTarget:
        DNSName: !GetAtt ClassicLoadBalancer.DNSName
        HostedZoneId: !GetAtt ClassicLoadBalancer.CanonicalHostedZoneNameID

Outputs:
  LoadBalancer:
    Value: !Ref ClassicLoadBalancer
"""
        ssl_cert_param_fmt = """
  SSLCertificateId{0[idx]:d}:
    Description: The Arn of the SSL Certificate to associate with this Load Balancer
    Type: String

"""


        listener_fmt = """
        - InstancePort: {0[instance_port]:d}
          LoadBalancerPort: {0[elb_port]:d}
          Protocol: {0[elb_protocol]:s}
          InstanceProtocol: {0[instance_protocol]:s}"""

        listener_table = {
            'idx': None,
            'instance_port': None,
            'elb_port': None,
            'elb_protocol': None,
            'instance_protocol': None
        }

        ssl_certificate_fmt = """
          SSLCertificateId: !Ref SSLCertificateId{0[idx]:d}"""

        listener_yaml = ""
        ssl_cert_param_yaml = ""
        listener_idx = 0
        for listener in elb_config['listeners']:
            listener_table['idx'] = listener_idx
            listener_table['instance_port'] = listener['instance_port']
            listener_table['elb_port'] = listener['elb_port']
            listener_table['elb_protocol'] = listener['elb_protocol']
            listener_table['instance_protocol'] = listener['instance_protocol']
            listener_yaml += listener_fmt.format(listener_table)
            if 'ssl_certificate_id' in listener:
                listener_yaml += ssl_certificate_fmt.format(listener_table)
                ssl_cert_param_yaml += ssl_cert_param_fmt.format(listener_table)
                self.set_parameter('SSLCertificateId'+str(listener_idx), self.paco_ctx.get_ref(listener['ssl_certificate_id']))
            listener_idx += 1

        template_fmt_table = {'Listeners': listener_yaml, 'SSLCertificateParameters': ssl_cert_param_yaml}


        self.set_template(template_fmt.format(template_fmt_table))
