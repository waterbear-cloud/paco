import os
import troposphere
import troposphere.efs
from paco.cftemplates.cftemplates import CFTemplate


class EFS(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        res_id,
        efs_config,
        config_ref
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=efs_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('EFS', grp_id, res_id)

        self.init_template('Elastic Filesystem')
        if not efs_config.is_enabled():
            self.set_template(self.template.to_yaml())
            return

        # Parameters
        sg_list_param = self.create_cfn_ref_list_param(
            param_type='List<AWS::EC2::SecurityGroup::Id>',
            name='TargetSecurityGroupList',
            description='EFS mount target security group list.',
            value=efs_config.security_groups,
            ref_attribute='id',
            use_troposphere=True,
            troposphere_template=self.template
        )
        encrypted_param = self.create_cfn_parameter(
            name='EncryptedAtRest',
            param_type='String',
            description='Boolean indicating whether the data will be encrypted at rest.',
            value=efs_config.encrypted,
            use_troposphere=True,
            troposphere_template=self.template,
        )

        # Elastic File System
        efs_res = troposphere.efs.FileSystem(
            title = 'EFS',
            template = self.template,
            Encrypted=troposphere.Ref(encrypted_param)
        )
        efs_id_output_logical_id = efs_res.title+'Id'
        troposphere.Output(
            title=efs_id_output_logical_id,
            template=self.template,
            Description="Elastic File System ID.",
            Value=troposphere.Ref(efs_res)
        )
        # Paco Stack Output Registration
        self.register_stack_output_config(config_ref + ".id", efs_id_output_logical_id)

        # Mount Targets
        availability_zones = env_ctx.config.network.availability_zones
        for az_idx in range(1, availability_zones+1):
            subnet_id_ref = env_ctx.env_ref_prefix(
                segment_id=efs_config.segment,
                attribute='az{}.subnet_id'.format(az_idx))

            subnet_param = self.create_cfn_parameter(
                name='SubnetIdAZ{}'.format(az_idx),
                param_type='String',
                description='The SubnetId for AZ{}.'.format(az_idx),
                value=subnet_id_ref,
                use_troposphere=True,
                troposphere_template=self.template,
            )
            efs_mount_logical_id = self.create_cfn_logical_id('EFSMountTargetAZ{}'.format(az_idx))
            troposphere.efs.MountTarget(
                title=efs_mount_logical_id,
                template=self.template,
                FileSystemId=troposphere.Ref(efs_res),
                SecurityGroups=troposphere.Ref(sg_list_param),
                SubnetId=troposphere.Ref(subnet_param)
            )

        # Generate the Template
        self.set_template(self.template.to_yaml())

