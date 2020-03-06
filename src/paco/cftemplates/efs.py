from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.efs


class EFS(StackTemplate):
    def __init__(self, stack, paco_ctx, network):
        efs_config = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('EFS', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Filesystem')
        if not efs_config.is_enabled(): return

        # Parameters
        sg_list_param = self.create_cfn_ref_list_param(
            param_type='List<AWS::EC2::SecurityGroup::Id>',
            name='TargetSecurityGroupList',
            description='EFS mount target security group list.',
            value=efs_config.security_groups,
            ref_attribute='id',
        )
        encrypted_param = self.create_cfn_parameter(
            name='EncryptedAtRest',
            param_type='String',
            description='Boolean indicating whether the data will be encrypted at rest.',
            value=efs_config.encrypted,
        )

        # Elastic File System
        efs_res = troposphere.efs.FileSystem(
            title = 'EFS',
            template = self.template,
            Encrypted=troposphere.Ref(encrypted_param)
        )
        self.create_output(
            title=efs_res.title + 'Id',
            description="Elastic File System ID.",
            value=troposphere.Ref(efs_res),
            ref=efs_config.paco_ref_parts + ".id"
        )

        # Mount Targets
        for az_idx in range(1, network.availability_zones + 1):
            subnet_id_ref = network.vpc.segments[efs_config.segment].paco_ref_parts + '.az{}.subnet_id'.format(az_idx)
            subnet_param = self.create_cfn_parameter(
                name='SubnetIdAZ{}'.format(az_idx),
                param_type='String',
                description='The SubnetId for AZ{}.'.format(az_idx),
                value='paco.ref ' + subnet_id_ref,
            )
            efs_mount_logical_id = self.create_cfn_logical_id('EFSMountTargetAZ{}'.format(az_idx))
            troposphere.efs.MountTarget(
                title=efs_mount_logical_id,
                template=self.template,
                FileSystemId=troposphere.Ref(efs_res),
                SecurityGroups=troposphere.Ref(sg_list_param),
                SubnetId=troposphere.Ref(subnet_param)
            )
