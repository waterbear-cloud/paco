import os
import troposphere
import troposphere.ec2
#import troposphere.<resource>

from aim import utils
from aim.cftemplates.cftemplates import CFTemplate


class EIP(CFTemplate):
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,

        app_id,
        grp_id,
        res_id,
        eip_config,
        config_ref):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            enabled=eip_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=eip_config.change_protected
        )
        self.set_aws_name('EIP', grp_id, res_id)

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        template = troposphere.Template(
            Description = 'Elastic IP',
        )
        template.set_version()
        template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="EmptyTemplatePlaceholder")
        )


        if eip_config.is_enabled() == True:
            eip_res = troposphere.ec2.EIP(
                title='ElasticIP',
                template=template,
                Domain='vpc'
            )

            # ---------------------------------------------------------------------------
            # Outputs
            eip_alloc_id_output = troposphere.Output(
                title='ElasticIPAllocationId',
                Description="The Elastic IPs allocation id.",
                Value=troposphere.GetAtt(eip_res, 'AllocationId')
            )
            template.add_output(eip_alloc_id_output)

            # AIM Stack Output Registration
            self.register_stack_output_config(config_ref + ".allocation_id", eip_alloc_id_output.title)

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

