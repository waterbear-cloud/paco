import os
import troposphere
import troposphere.ec2
#import troposphere.<resource>

from paco import utils
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import vocabulary


class EBS(CFTemplate):
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
        ebs_config,
        config_ref):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=ebs_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=ebs_config.change_protected
        )
        self.set_aws_name('EBS', grp_id, res_id)

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization
        self.init_template('Elastic Block Store Volume')

        ebs_dict = {
            'Size': ebs_config.size_gib,
            'VolumeType': ebs_config.volume_type,
            'AvailabilityZone': vocabulary.aws_regions[aws_region]['zones'][ebs_config.availability_zone-1]
        }

        ebs_res = troposphere.ec2.Volume.from_dict(
            'EBS',
            ebs_dict
        )
        self.template.add_resource(ebs_res)

        # ---------------------------------------------------------------------------
        # Outputs
        ebs_volume_id_output = troposphere.Output(
            title='EBSVolumeId',
            Description="The EBS Volume Id.",
            Value=troposphere.Ref(ebs_res)
        )
        self.template.add_output(ebs_volume_id_output)

        # Paco Stack Output Registration
        self.register_stack_output_config(config_ref + ".id", ebs_volume_id_output.title)

        # Generate the Template
        self.set_template(self.template.to_yaml())

