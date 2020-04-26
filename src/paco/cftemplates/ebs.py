from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import vocabulary
import troposphere
import troposphere.ec2


class EBS(StackTemplate):
    def __init__(self, stack, paco_ctx):
        ebs_config = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('EBS', self.resource_group_name, self.resource.name)

        # Troposphere Template Initialization
        self.init_template('Elastic Block Store Volume')

        # EBS Resource
        ebs_dict = {
            'VolumeType': ebs_config.volume_type,
            'AvailabilityZone': vocabulary.aws_regions[self.aws_region]['zones'][ebs_config.availability_zone-1]
        }
        # Snapshot overrides Size
        if ebs_config.snapshot_id != None and ebs_config.snapshot_id != '':
            ebs_dict['SnapshotId'] = ebs_config.snapshot_id
        else:
            ebs_dict['Size'] = ebs_config.size_gib

        ebs_res = troposphere.ec2.Volume.from_dict(
            'EBS',
            ebs_dict
        )
        self.template.add_resource(ebs_res)

        # Outputs
        self.create_output(
            title='EBSVolumeId',
            description="The EBS Volume Id.",
            value=troposphere.Ref(ebs_res),
            ref=ebs_config.paco_ref_parts + ".id",
        )
