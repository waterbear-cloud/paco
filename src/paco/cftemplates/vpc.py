from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.ec2
import troposphere.route53


class VPC(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
    ):
        super().__init__(
            stack,
            paco_ctx,
        )
        self.set_aws_name('VPC')
        self.init_template('Virtual Private Cloud')
        template = self.template
        vpc_config = stack.resource
        vpc_config_ref = vpc_config.paco_ref_parts

        # VPC
        cidr_block_param = self.create_cfn_parameter(
            name='CidrBlock',
            param_type='String',
            description='The VPC CIDR block',
            value=vpc_config.cidr
        )
        enable_dns_support_param = self.create_cfn_parameter(
            name='EnableDnsSupport',
            param_type='String',
            description='Indicates whether the DNS resolution is supported for the VPC.',
            value=vpc_config.enable_dns_support,
        )
        enable_dns_hostname_param = self.create_cfn_parameter(
            name='EnableDnsHostnames',
            param_type='String',
            description='Indicates whether the instances launched in the VPC get DNS hostnames.',
            value=vpc_config.enable_dns_hostnames,
        )
        vpc_dict = {
            'CidrBlock': troposphere.Ref(cidr_block_param),
            'EnableDnsSupport': troposphere.Ref(enable_dns_support_param),
            'EnableDnsHostnames': troposphere.Ref(enable_dns_hostname_param)
        }
        vpc_resource = troposphere.ec2.VPC.from_dict('VPC', vpc_dict)
        template.add_resource(vpc_resource)

        # Output
        self.create_output(
            title=vpc_resource.title,
            value=troposphere.Ref(vpc_resource),
            ref=[vpc_config_ref, vpc_config_ref + '.id']
        )

        # Internet gateway
        if vpc_config.enable_internet_gateway == True:
            # Gateway
            igw_resource = troposphere.ec2.InternetGateway('InternetGateway')
            # Attachment
            igw_attachment_dict = {
                'VpcId': troposphere.Ref(vpc_resource),
                'InternetGatewayId': troposphere.Ref(igw_resource)
            }
            igw_attachment_resource = troposphere.ec2.VPCGatewayAttachment.from_dict(
                'InternetGatewayAttachment',
                igw_attachment_dict
            )
            template.add_resource(igw_resource)
            template.add_resource(igw_attachment_resource)

            # Output
            self.create_output(
                title='InternetGateway',
                value=troposphere.Ref(igw_resource),
                ref=vpc_config_ref + ".internet_gateway"
            )

        # Private Hosted Zone
        if vpc_config.private_hosted_zone.enabled == True:
            internal_domain_name_param = self.create_cfn_parameter(
                name='PrivateZoneDomainName',
                param_type='String',
                description='The name of the private hosted zone domain.',
                value=vpc_config.private_hosted_zone.name,
            )
            private_zone_vpcs = []
            private_zone_vpcs.append(troposphere.route53.HostedZoneVPCs(
                VPCId=troposphere.Ref(vpc_resource),
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
            template.add_resource(private_zone_res)
            self.create_output(
                title='PrivateHostedZoneId',
                description="Private Hosted Zone Id",
                value=troposphere.Ref(private_zone_res),
                ref=vpc_config_ref + ".private_hosted_zone.id"
            )
