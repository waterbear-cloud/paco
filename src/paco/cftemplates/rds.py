import base64
import os
import troposphere
import troposphere.rds
import troposphere.secretsmanager
from paco import utils
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import vocabulary, schemas
from enum import Enum
from io import StringIO

class DBParameterGroup(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        grp_id,
        resource,
        config_ref=None
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=resource.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('DBParameterGroup', grp_id, resource.name)
        self.init_template('DB Parameter Group')

        # Resources
        cfn_export_dict = {
            'Family': resource.family,
            'Parameters': {}
        }
        if resource.description != None:
            cfn_export_dict['Description'] = resource.description
        else:
            cfn_export_dict['Description'] = troposphere.Ref('AWS::StackName')

        for key, value in resource.parameters.items():
            cfn_export_dict['Parameters'][key] = value

        dbparametergroup_resource = troposphere.rds.DBParameterGroup.from_dict(
            'DBParameterGroup',
            cfn_export_dict
        )
        self.template.add_resource(dbparametergroup_resource)

        # Outputs
        dbparametergroup_name_output = troposphere.Output(
            title='DBParameterGroupName',
            Description='DB Parameter Group Name',
            Value=troposphere.Ref(dbparametergroup_resource)
        )
        self.template.add_output(dbparametergroup_name_output)
        self.register_stack_output_config(config_ref, 'DBParameterGroupName')
        self.register_stack_output_config(config_ref + '.name', 'DBParameterGroupName')

        # All done, let's go home!
        self.set_template(self.template.to_yaml())


class RDS(CFTemplate):
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
        rds_config,
        config_ref=None
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=rds_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.set_aws_name('RDS', grp_id, res_id)
        self.init_template('RDS')
        template = self.template

        if not rds_config.is_enabled():
            # Remove RDS resource and leave a dummy template is not enabled
            self.template.add_resource(
                troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
            )
            self.set_template(template.to_yaml())
            return

        rds_logical_id = 'PrimaryDBInstance'

        # DB Subnet Group
        db_subnet_id_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='DBSubnetIdList',
            description='The list of subnet IDs where this database will be provisioned.',
            value=rds_config.segment+'.subnet_id_list',
            use_troposphere=True,
            troposphere_template=template
        )

        db_subnet_group_res = troposphere.rds.DBSubnetGroup(
            title = 'DBSubnetGroup',
            template  = template,
            DBSubnetGroupDescription = troposphere.Ref('AWS::StackName'),
            SubnetIds = troposphere.Ref(db_subnet_id_list_param)
        )

        # DB Parameter Group
        if rds_config.parameter_group == None:
            # No Parameter Group supplied, create one
            engine_major_version = '.'.join(rds_config.engine_version.split('.')[0:2])
            param_group_family = vocabulary.rds_engine_versions[rds_config.engine][engine_major_version]['param_group_family']
            dbparametergroup_ref = troposphere.rds.DBParameterGroup(
                "DBParameterGroup",
                template = template,
                Family=param_group_family,
                Description=troposphere.Ref('AWS::StackName')
            )
        else:
            # Use an existing Parameter Group
            dbparametergroup_ref = self.create_cfn_parameter(
                name='DBParameterGroupName',
                param_type='String',
                description='DB Parameter Group Name',
                value=rds_config.parameter_group + '.name',
                use_troposphere=True
            )
            self.template.add_parameter(dbparametergroup_ref)

        # Option Group
        option_group_res = None
        if len(rds_config.option_configurations) > 0:
            option_group_dict = {
                'EngineName': rds_config.engine,
                'MajorEngineVersion': engine_major_version,
                'OptionGroupDescription': troposphere.Ref('AWS::StackName')
            }
            if len(rds_config.option_configurations) > 0:
                option_config_list = []
                for option_config in rds_config.option_configurations:
                    option_config_dict = {
                        'OptionName': option_config.option_name,
                    }
                    if len(option_config.option_settings) > 0:
                        option_config_dict['OptionSettings'] = []
                        for option_setting in option_config.option_settings:
                            option_setting_dict = {
                                'Name': option_setting.name,
                                'Value': option_setting.value
                            }
                            option_config_dict['OptionSettings'].append(option_setting_dict)
                    option_config_list.append(option_config_dict)
                option_group_dict['OptionConfigurations'] = option_config_list

            option_group_res = troposphere.rds.OptionGroup.from_dict(
                'OptionGroup',
                option_group_dict )
            template.add_resource(option_group_res)

        # RDS Mysql
        if schemas.IRDSMysql.providedBy(rds_config):
            sg_param_ref_list = []
            for sg_ref in rds_config.security_groups:
                sg_hash = utils.md5sum(str_data=sg_ref)
                sg_param = self.create_cfn_parameter(
                    param_type='AWS::EC2::SecurityGroup::Id',
                    name=self.create_cfn_logical_id('SecurityGroup'+sg_hash),
                    description='VPC Security Group to attach to the RDS.',
                    value=sg_ref+'.id',
                    use_troposphere=True,
                    troposphere_template=template
                )
                sg_param_ref_list.append(troposphere.Ref(sg_param))

            db_instance_dict = {
                'Engine': rds_config.engine,
                'EngineVersion': rds_config.engine_version,
                'DBInstanceIdentifier': troposphere.Ref('AWS::StackName'),
                'DBInstanceClass': rds_config.db_instance_type,
                'DBSubnetGroupName': troposphere.Ref(db_subnet_group_res),
                'DBParameterGroupName': troposphere.Ref(dbparametergroup_ref),
                'CopyTagsToSnapshot': True,
                'AllowMajorVersionUpgrade': rds_config.allow_major_version_upgrade,
                'AutoMinorVersionUpgrade': rds_config.auto_minor_version_upgrade,
                'MultiAZ': rds_config.multi_az,
                'AllocatedStorage': rds_config.storage_size_gb,
                'StorageType': rds_config.storage_type,
                'BackupRetentionPeriod': rds_config.backup_retention_period,
                'Port': rds_config.port,
                'PreferredBackupWindow': rds_config.backup_preferred_window,
                'PreferredMaintenanceWindow': rds_config.maintenance_preferred_window,
                'VPCSecurityGroups': sg_param_ref_list
            }

            # License Model
            if rds_config.license_model:
                db_instance_dict['LicenseModel'] = rds_config.license_model

            # Deletion Protection
            if rds_config.deletion_protection:
                db_instance_dict['DeletionProtection'] = rds_config.deletion_protection

            # CloudWatch Logs Exports
            if len(rds_config.cloudwatch_logs_exports) > 0:
                db_instance_dict['EnableCloudwatchLogsExports'] = rds_config.cloudwatch_logs_exports

            # Option Group
            if option_group_res != None:
                db_instance_dict['OptionGroupName'] = troposphere.Ref(option_group_res)

            # DB Snapshot Identifier
            if rds_config.db_snapshot_identifier == '' or rds_config.db_snapshot_identifier == None:
                db_snapshot_id_enabled = False
            else:
                db_snapshot_id_enabled = True
            if db_snapshot_id_enabled == True:
                db_instance_dict['DBSnapshotIdentifier'] = rds_config.db_snapshot_identifier

            # Encryption
            if rds_config.kms_key_id == '' or rds_config.kms_key_id == None:
                encryption_enabled = False
            else:
                encryption_enabled = True
            if db_snapshot_id_enabled == False:
                db_instance_dict['StorageEncrypted'] = encryption_enabled
                if encryption_enabled:
                    db_instance_dict['KmsKeyId'] = rds_config.kms_key_id

            # Username and Passsword
            if db_snapshot_id_enabled == False:
                db_instance_dict['MasterUsername'] = rds_config.master_username
                if rds_config.secrets_password:
                    # Password from Secrets Manager
                    sta_logical_id = 'SecretTargetAttachmentRDS'
                    secret_arn_param = self.create_cfn_parameter(
                        param_type='String',
                        name='RDSSecretARN',
                        description='The ARN for the secret for the RDS master password.',
                        value=rds_config.secrets_password + '.arn',
                        use_troposphere=True
                    )
                    template.add_parameter(secret_arn_param)
                    secret_target_attachment_resource = troposphere.secretsmanager.SecretTargetAttachment(
                        title=sta_logical_id,
                        SecretId=troposphere.Ref(secret_arn_param),
                        TargetId=troposphere.Ref(rds_logical_id),
                        TargetType='AWS::RDS::DBInstance'
                    )
                    template.add_resource(secret_target_attachment_resource)

                    db_instance_dict['MasterUserPassword'] = troposphere.Join(
                        '',
                        ['{{resolve:secretsmanager:', troposphere.Ref(secret_arn_param), ':SecretString:password}}' ]
                    )
                else:
                    master_password_param = self.create_cfn_parameter(
                        param_type='String',
                        name='MasterUserPassword',
                        description='The master user password.',
                        value=rds_config.master_user_password,
                        noecho=True,
                        use_troposphere=True,
                        troposphere_template=template
                    )
                    db_instance_dict['MasterUserPassword'] = troposphere.Ref(master_password_param)

            db_instance_res = troposphere.rds.DBInstance.from_dict(
                rds_logical_id,
                db_instance_dict
            )
            template.add_resource(db_instance_res)

            # Outputs
            dbname_output = troposphere.Output(
                title='DBInstanceName',
                Description='DB Instance Name',
                Value=troposphere.Ref(db_instance_res)
            )
            template.add_output(dbname_output)
            self.register_stack_output_config(config_ref + ".name", dbname_output.title)

            endpoint_address_output = troposphere.Output(
                title='RDSEndpointAddress',
                Description='RDS Endpoint URL',
                Value=troposphere.GetAtt(db_instance_res, 'Endpoint.Address')
            )
            template.add_output(endpoint_address_output)
            self.register_stack_output_config(config_ref + ".endpoint.address", endpoint_address_output.title)

            if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == True:
                if rds_config.is_dns_enabled() == True:
                    for dns_config in rds_config.dns_config:
                        dns_hash = utils.md5sum(str_data=(rds_config.hosted_zone+rds_config.domain_name))
                        primary_hosted_zone_id_param = self.create_cfn_parameter(
                            param_type='String',
                            name='DNSHostedZoneId'+dns_hash,
                            description='The hosted zone id to create the Route53 record set.',
                            value=rds_config.primary_hosted_zone+'.id',
                            use_troposphere=True,
                            troposphere_template=template
                        )
                        record_set_res = troposphere.route53.RecordSetType(
                            title = 'RecordSet'+dns_hash,
                            template = template,
                            Comment = 'RDS Primary DNS',
                            HostedZoneId = troposphere.Ref(primary_hosted_zone_id_param),
                            Name = rds_config.primary_domain_name,
                            Type = 'CNAME',
                            TTL = dns_config.ttl,
                            ResourceRecords = [ troposphere.GetAtt(db_instance_res, 'Endpoint.Address')]
                        )
                        record_set_res.DependsOn = db_instance_res

        self.set_template(template.to_yaml())

        if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == False:
            if rds_config.is_dns_enabled() == True:
                route53_ctl = self.paco_ctx.get_controller('route53')
                for dns_config in rds_config.dns:
                    route53_ctl.add_record_set(
                        self.account_ctx,
                        self.aws_region,
                        enabled=rds_config.is_enabled(),
                        dns=dns_config,
                        record_set_type='CNAME',
                        resource_records=[ 'paco.ref '+config_ref+'.endpoint.address' ],
                        stack_group = self.stack_group,
                        config_ref = rds_config.paco_ref_parts+'.dns')
