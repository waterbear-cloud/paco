import os
import troposphere
import troposphere.ec2
import troposphere.route53
from paco.cftemplates.cftemplates import CFTemplate

from io import StringIO
from enum import Enum


class VPC(CFTemplate):
    def __init__(self,
                 paco_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 vpc_config,
                 vpc_config_ref):
        #paco_ctx.log("VPC CF Template init")

        super().__init__(
            paco_ctx=paco_ctx,
            account_ctx=account_ctx,
            aws_region=aws_region,
            enabled=vpc_config.is_enabled(),
            config_ref=vpc_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('VPC')
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('Virtual Private Network')

        #---------------------------------------------------------------------
        # VPC
        cidr_block_param = self.create_cfn_parameter(
            name='CidrBlock',
            param_type='String',
            description='The VPC CIDR block',
            value=vpc_config.cidr,
            use_troposphere=True
        )
        enable_dns_support_param = self.create_cfn_parameter(
            name='EnableDnsSupport',
            param_type='String',
            description='Indicates whether the DNS resolution is supported for the VPC.',
            value=vpc_config.enable_dns_support,
            use_troposphere=True
        )
        enable_dns_hostname_param = self.create_cfn_parameter(
            name='EnableDnsHostnames',
            param_type='String',
            description='Indicates whether the instances launched in the VPC get DNS hostnames.',
            value=vpc_config.enable_dns_hostnames,
            use_troposphere=True
        )
        vpc_dict = {
            'CidrBlock': troposphere.Ref(cidr_block_param),
            'EnableDnsSupport': troposphere.Ref(enable_dns_support_param),
            'EnableDnsHostnames': troposphere.Ref(enable_dns_hostname_param)
        }
        vpc_res = troposphere.ec2.VPC.from_dict('VPC', vpc_dict)
        vpc_output = troposphere.Output(
            'VPC',
            Value=troposphere.Ref(vpc_res)
        )


        template.add_parameter(cidr_block_param)
        template.add_parameter(enable_dns_support_param)
        template.add_parameter(enable_dns_hostname_param)
        template.add_resource(vpc_res)
        template.add_output(vpc_output)

        self.register_stack_output_config(vpc_config_ref, vpc_output.title)
        self.register_stack_output_config(vpc_config_ref + '.id', vpc_output.title)


        #---------------------------------------------------------------------
        # Internet gateway
        if vpc_config.enable_internet_gateway == True:
            # Gateway
            igw_res = troposphere.ec2.InternetGateway('InternetGateway')
            # Attachment
            igw_attachment_dict = {
                'VpcId': troposphere.Ref(vpc_res),
                'InternetGatewayId': troposphere.Ref(igw_res)
            }
            igw_attachment_res = troposphere.ec2.VPCGatewayAttachment.from_dict(
                'InternetGatewayAttachment',
                igw_attachment_dict
            )
            # Output
            igw_output = troposphere.Output(
                'InternetGateway',
                Value=troposphere.Ref(igw_res)
            )

            template.add_resource(igw_res)
            template.add_resource(igw_attachment_res)
            template.add_output(igw_output)
            self.register_stack_output_config(vpc_config_ref + ".internet_gateway", igw_output.title)

        #---------------------------------------------------------------------
        # Private Hosted Zone
        if vpc_config.private_hosted_zone.enabled == True:
            internal_domain_name_param = self.create_cfn_parameter(
                name='PrivateZoneDomainName',
                param_type='String',
                description='The name of the private hosted zone domain.',
                value=vpc_config.private_hosted_zone.name,
                use_troposphere=True
            )
            private_zone_vpcs = []
            private_zone_vpcs.append(troposphere.route53.HostedZoneVPCs(
                VPCId=troposphere.Ref(vpc_res),
                VPCRegion=troposphere.Ref('AWS::Region')
            ))

            for vpc_id in vpc_config.private_hosted_zone.vpc_associations:
                private_zone_vpcs.append(troposphere.route53.HostedZoneVPCs(
                    VPCId=vpc_id,
                    VPCRegion=troposphere.Ref('AWS::Region')
                ))
            private_zone_res = troposphere.route53.HostedZone(
                'PrivateHostedZone',
                Name=troposphere.Ref(internal_domain_name_param),
                VPCs=private_zone_vpcs
            )
            private_zone_id_output = troposphere.Output(
                'PrivateHostedZoneId',
                Description="Private Hosted Zone Id",
                Value=troposphere.Ref(private_zone_res)
            )

            template.add_parameter(internal_domain_name_param)
            template.add_resource(private_zone_res)
            template.add_output(private_zone_id_output)

            self.register_stack_output_config(vpc_config_ref + ".private_hosted_zone.id", private_zone_id_output.title)

        # Define the Template
        self.set_template(template.to_yaml())
