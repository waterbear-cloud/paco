import os
import troposphere
import troposphere.ec2
#import troposphere.<resource>

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

        # ---------------------------------------------------------------------------
        # Resource
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

        # Generate the Template
        self.set_template(template.to_yaml())

