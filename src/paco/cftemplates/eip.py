import os
import troposphere
import troposphere.ec2
from paco import utils
from paco.cftemplates.cftemplates import CFTemplate


class EIP(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        app_id,
        grp_id,
        res_id,
        eip_config,
        config_ref
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=eip_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=eip_config.change_protected
        )
        self.set_aws_name('EIP', grp_id, res_id)

        # Troposphere Template Initialization
        self.init_template('Elastic IP')
        if not eip_config.is_enabled():
            self.set_template(self.template.to_yaml())
            return

        template = self.template
        eip_res = troposphere.ec2.EIP(
            title='ElasticIP',
            template=template,
            Domain='vpc'
        )

        # Outputs
        eip_address_output = troposphere.Output(
            title='ElasticIPAddress',
            Description="The Elastic IP Address.",
            Value=troposphere.Ref(eip_res)
        )
        template.add_output(eip_address_output)

        eip_alloc_id_output = troposphere.Output(
            title='ElasticIPAllocationId',
            Description="The Elastic IPs allocation id.",
            Value=troposphere.GetAtt(eip_res, 'AllocationId')
        )
        template.add_output(eip_alloc_id_output)

        # Paco Stack Output Registration
        self.register_stack_output_config(config_ref + ".address", eip_address_output.title)
        self.register_stack_output_config(config_ref + ".allocation_id", eip_alloc_id_output.title)

        if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == True:
            if eip_config.is_dns_enabled():
                for dns_config in eip_config.dns:
                    dns_hash = utils.md5sum(str_data=dns_config.domain_name)
                    zone_param_name = 'DomainHostedZoneId' + dns_hash
                    dns_zone_id_param = self.create_cfn_parameter(
                        param_type='String',
                        name=zone_param_name,
                        description='Domain Alias Hosted Zone Id',
                        value=dns_config.hosted_zone+'.id',
                        use_troposphere=True,
                        troposphere_template=template
                        )
                    troposphere.route53.RecordSetType(
                        title = self.create_cfn_logical_id_join(['RecordSet', dns_hash]),
                        template = template,
                        HostedZoneId = troposphere.Ref(dns_zone_id_param),
                        Name = dns_config.domain_name,
                        Type = 'A',
                        TTL = 300,
                        ResourceRecords = [ troposphere.Ref(eip_res)]
                    )

        # Generate the Template
        self.set_template(template.to_yaml())

        if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == False:
            route53_ctl = self.paco_ctx.get_controller('route53')
            if eip_config.is_dns_enabled() == True and eip_config.is_enabled() == True:
                for dns_config in eip_config.dns:
                    route53_ctl.add_record_set(
                        self.account_ctx,
                        self.aws_region,
                        enabled=eip_config.is_enabled(),
                        dns=dns_config,
                        record_set_type='A',
                        resource_records=['paco.ref '+config_ref+'.address'],
                        stack_group = self.stack_group,
                        config_ref = eip_config.paco_ref_parts+'.dns')

