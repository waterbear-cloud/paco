from awacs.aws import Allow, Action, Policy, PolicyDocument, Principal, Statement, Condition, StringEquals
from paco import utils
from paco.cftemplates.cftemplates import StackTemplate
from paco.models import schemas
from paco.models import gen_vocabulary
import awacs.kms
import troposphere
import troposphere.iam
import troposphere.kms
import troposphere.rds
import troposphere.secretsmanager


class DBParameterGroup(StackTemplate):
    def __init__(self, stack, paco_ctx):
        resource = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('DBParameterGroup', self.resource_group_name, resource.name)
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
        self.create_output(
            title='DBParameterGroupName',
            description='DB Parameter Group Name',
            value=troposphere.Ref(dbparametergroup_resource),
            ref=[self.resource.paco_ref_parts, self.resource.paco_ref_parts + ".name"]
        )


class DBClusterParameterGroup(StackTemplate):
    def __init__(self, stack, paco_ctx):
        resource = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('DBClusterParameterGroup', self.resource_group_name, resource.name)
        self.init_template('DB Cluster Parameter Group')

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

        dbparametergroup_resource = troposphere.rds.DBClusterParameterGroup.from_dict(
            'DBClusterParameterGroup',
            cfn_export_dict
        )
        self.template.add_resource(dbparametergroup_resource)

        # Outputs
        self.create_output(
            title='DBClusterParameterGroupName',
            description='DB Cluster Parameter Group Name',
            value=troposphere.Ref(dbparametergroup_resource),
            ref=[self.resource.paco_ref_parts, self.resource.paco_ref_parts + ".name"]
        )


class RDSAurora(StackTemplate):
    """
    RDS Aurora for MySQL and PostgreSQL
    """

    def __init__(self, stack, paco_ctx,):
        rds_aurora = stack.resource
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.set_aws_name('RDSAurora', self.resource_group_name, self.resource.name)
        self.init_template('RDSAurora')
        if not rds_aurora.is_enabled(): return

        rds_cluster_logical_id = 'DBCluster'
        db_cluster_dict = rds_aurora.cfn_export_dict
        self.notification_groups = {}

        # DB Subnet Group
        db_subnet_id_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='DBSubnetIdList',
            description='The list of subnet IDs where this database will be provisioned.',
            value=rds_aurora.segment + '.subnet_id_list',
        )
        db_subnet_group_resource = troposphere.rds.DBSubnetGroup(
            title='DBSubnetGroup',
            template=self.template,
            DBSubnetGroupDescription=troposphere.Ref('AWS::StackName'),
            SubnetIds=troposphere.Ref(db_subnet_id_list_param),
        )
        db_cluster_dict['DBSubnetGroupName'] = troposphere.Ref(db_subnet_group_resource)

        # DB Cluster Parameter Group
        if rds_aurora.cluster_parameter_group == None:
            # If no Cluster Parameter Group supplied then create one
            param_group_family = gen_vocabulary.rds_engine_versions[rds_aurora.engine][rds_aurora.engine_version]['param_group_family']
            cluster_parameter_group_ref = troposphere.rds.DBClusterParameterGroup(
                "DBClusterParameterGroup",
                template=self.template,
                Family=param_group_family,
                Description=troposphere.Ref('AWS::StackName')
            )
        else:
            # Use existing Parameter Group
            cluster_parameter_group_ref = self.create_cfn_parameter(
                name='DBClusterParameterGroupName',
                param_type='String',
                description='DB Cluster Parameter Group Name',
                value=rds_aurora.cluster_parameter_group + '.name',
            )
        db_cluster_dict['DBClusterParameterGroupName'] = troposphere.Ref(cluster_parameter_group_ref)

        # Default DB Parameter Group
        default_dbparametergroup_resource = None
        need_db_pg = False
        default_instance = rds_aurora.default_instance
        for db_instance in rds_aurora.db_instances.values():
            if default_instance.parameter_group == None and db_instance.parameter_group == None:
                need_db_pg = True
        if need_db_pg:
            # create default DB Parameter Group
            param_group_family = gen_vocabulary.rds_engine_versions[rds_aurora.engine][rds_aurora.engine_version]['param_group_family']
            default_dbparametergroup_resource = troposphere.rds.DBParameterGroup(
                "DBParameterGroup",
                template=self.template,
                Family=param_group_family,
                Description=troposphere.Ref('AWS::StackName')
            )

        # Enhanced Monitoring Role
        need_monitoring_role = False
        enhanced_monitoring_role_resource = None
        for db_instance in rds_aurora.db_instances.values():
            enhanced_monitoring_interval = db_instance.get_value_or_default('enhanced_monitoring_interval_in_seconds')
            if enhanced_monitoring_interval != 0:
                need_monitoring_role = True
        if need_monitoring_role:
            enhanced_monitoring_role_resource = troposphere.iam.Role(
                title='MonitoringIAMRole',
                template=self.template,
                AssumeRolePolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[Action("sts", "AssumeRole")],
                            Principal=Principal("Service", "monitoring.rds.amazonaws.com")
                        )
                    ]
                ),
                ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"],
                Path="/",
            )

        # DB Snapshot Identifier
        if rds_aurora.db_snapshot_identifier == '' or rds_aurora.db_snapshot_identifier == None:
            db_snapshot_id_enabled = False
        else:
            db_snapshot_id_enabled = True
        if db_snapshot_id_enabled == True:
            db_cluster_dict['SnapshotIdentifier'] = rds_aurora.db_snapshot_identifier

        # CloudWatch Export Logs
        if len(rds_aurora.cloudwatch_logs_exports) > 0:
            logs_export_list = []
            if 'postgresql' in rds_aurora.cloudwatch_logs_exports:
                logs_export_list.append('postgresql')
            #if 'upgrade' in rds_aurora.cloudwatch_logs_exports:
            #    logs_export_list.append('upgrade')
            db_cluster_dict['EnableCloudwatchLogsExports'] = logs_export_list

        # KMS-CMK key encryption
        if rds_aurora.enable_kms_encryption == True and db_snapshot_id_enabled == False:
            key_policy = Policy(
                Version='2012-10-17',
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[Action('kms', '*'),],
                        Principal=Principal("AWS", [f'arn:aws:iam::{self.stack.account_ctx.id}:root']),
                        Resource=['*'],
                    ),
                    Statement(
                        Effect=Allow,
                        Action=[
                            awacs.kms.Encrypt,
                            awacs.kms.Decrypt,
                            Action('kms', 'ReEncrypt*'),
                            Action('kms', 'GenerateDataKey*'),
                            awacs.kms.CreateGrant,
                            awacs.kms.ListGrants,
                            awacs.kms.DescribeKey,
                        ],
                        Principal=Principal('AWS',['*']),
                        Resource=['*'],
                        Condition=Condition([
                            StringEquals({
                                'kms:CallerAccount': f'{self.stack.account_ctx.id}',
                                'kms:ViaService': f'rds.{self.stack.aws_region}.amazonaws.com'
                            })
                        ]),
                    ),
                ],
            )
            kms_key_resource = troposphere.kms.Key(
                title='AuroraKMSCMK',
                template=self.template,
                KeyPolicy=key_policy,
            )
            db_cluster_dict['StorageEncrypted'] = True
            db_cluster_dict['KmsKeyId'] = troposphere.Ref(kms_key_resource)

            kms_key_alias_resource = troposphere.kms.Alias(
                title="AuroraKMSCMKAlias",
                template=self.template,
                AliasName=troposphere.Sub('alias/${' + rds_cluster_logical_id + '}'),
                TargetKeyId=troposphere.Ref(kms_key_resource),
            )
            kms_key_alias_resource.DependsOn = rds_cluster_logical_id

        # Username and Passsword - only if there is no DB Snapshot Identifier
        if db_snapshot_id_enabled == False:
            db_cluster_dict['MasterUsername'] = rds_aurora.master_username
            if rds_aurora.secrets_password:
                # Password from Secrets Manager
                sta_logical_id = 'SecretTargetAttachmentRDS'
                secret_arn_param = self.create_cfn_parameter(
                    param_type='String',
                    name='RDSSecretARN',
                    description='The ARN for the secret for the RDS master password.',
                    value=rds_aurora.secrets_password + '.arn',
                )
                secret_target_attachment_resource = troposphere.secretsmanager.SecretTargetAttachment(
                    title=sta_logical_id,
                    template=self.template,
                    SecretId=troposphere.Ref(secret_arn_param),
                    TargetId=troposphere.Ref(rds_cluster_logical_id),
                    TargetType='AWS::RDS::DBCluster'
                )
                secret_target_attachment_resource.DependsOn = rds_cluster_logical_id
                db_cluster_dict['MasterUserPassword'] = troposphere.Join(
                    '',
                    ['{{resolve:secretsmanager:', troposphere.Ref(secret_arn_param), ':SecretString:password}}' ]
                )
            else:
                master_password_param = self.create_cfn_parameter(
                    param_type='String',
                    name='MasterUserPassword',
                    description='The master user password.',
                    value=rds_aurora.master_user_password,
                    noecho=True,
                )
                db_cluster_dict['MasterUserPassword'] = troposphere.Ref(master_password_param)

        # VPC Security Groups Ids
        sg_param_ref_list = []
        for sg_ref in rds_aurora.security_groups:
            sg_hash = utils.md5sum(str_data=sg_ref)
            sg_param = self.create_cfn_parameter(
                param_type='AWS::EC2::SecurityGroup::Id',
                name=self.create_cfn_logical_id(f'SecurityGroup{sg_hash}'),
                description='VPC Security Group for DB Cluster',
                value=sg_ref + '.id',
            )
            sg_param_ref_list.append(troposphere.Ref(sg_param))
        if len(sg_param_ref_list) > 0:
            db_cluster_dict['VpcSecurityGroupIds'] = sg_param_ref_list

        db_cluster_res = troposphere.rds.DBCluster.from_dict(
            rds_cluster_logical_id,
            db_cluster_dict
        )
        self.template.add_resource(db_cluster_res)

        # Cluster Event Notifications
        if hasattr(rds_aurora, 'cluster_event_notifications'):
            for group in rds_aurora.cluster_event_notifications.groups:
                notif_param = self.create_notification_param(group)
                event_subscription_resource = troposphere.rds.EventSubscription(
                    title=self.create_cfn_logical_id(f"ClusterEventSubscription{group}"),
                    template=self.template,
                    EventCategories=rds_aurora.cluster_event_notifications.event_categories,
                    SourceIds=[troposphere.Ref(db_cluster_res)],
                    SnsTopicArn=troposphere.Ref(notif_param),
                    SourceType='db-cluster',
                )

        # DB Instance(s)
        for db_instance in rds_aurora.db_instances.values():
            logical_name = self.create_cfn_logical_id(db_instance.name)
            if db_instance.external_resource == True:
                # Setup event notifications
                self.set_db_instance_event_notifications(logical_name, db_instance)
                # External instance only needs to output its name
                self.create_output(
                    title=f'DBInstanceName{logical_name}',
                    description=f'DB Instance Name for {logical_name}',
                    value=db_instance.external_instance_name,
                    ref=db_instance.paco_ref_parts + ".name",
                )
                continue
            db_instance_dict = {
                'DBClusterIdentifier': troposphere.Ref(db_cluster_res),
                'DBInstanceClass': db_instance.get_value_or_default('db_instance_type'),
                'DBSubnetGroupName': troposphere.Ref(db_subnet_group_resource),
                'EnablePerformanceInsights': db_instance.get_value_or_default('enable_performance_insights'),
                'Engine': rds_aurora.engine,
                'PubliclyAccessible': db_instance.get_value_or_default('publicly_accessible'),
                'AllowMajorVersionUpgrade': db_instance.get_value_or_default('allow_major_version_upgrade'),
                'AutoMinorVersionUpgrade': db_instance.get_value_or_default('auto_minor_version_upgrade'),
            }

            # Enhanced Monitoring
            enhanced_monitoring_interval = db_instance.get_value_or_default('enhanced_monitoring_interval_in_seconds')
            if enhanced_monitoring_interval != 0:
                db_instance_dict['MonitoringInterval'] = enhanced_monitoring_interval
                db_instance_dict['MonitoringRoleArn'] = troposphere.GetAtt(enhanced_monitoring_role_resource, "Arn")
            if db_instance.availability_zone != None:
                subnet_id_ref = f'{rds_aurora.segment}.az{db_instance.availability_zone}.availability_zone'
                db_instance_subnet_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'DBInstanceAZ{logical_name}',
                    description=f'Subnet where DB Instance {logical_name} is provisioned',
                    value=subnet_id_ref,
                )
                db_instance_dict['AvailabilityZone'] = troposphere.Ref(db_instance_subnet_param)

            # DB Parameter Group
            if default_instance.parameter_group == None and db_instance.parameter_group == None:
                dbparametergroup_resource = default_dbparametergroup_resource
            elif db_instance.parameter_group != None:
                # Use instance-specific DB Parameter Group
                dbparametergroup_resource = self.create_cfn_parameter(
                    name=f'DBParameterGroupName{logical_name}',
                    param_type='String',
                    description='DB Parameter Group Name',
                    value=db_instance.parameter_group + '.name',
                )
            else:
                # Use default DB Parameter Group
                dbparametergroup_resource = self.create_cfn_parameter(
                    name=f'DBParameterGroupName{logical_name}',
                    param_type='String',
                    description='DB Parameter Group Name',
                    value=default_instance.parameter_group + '.name',
                )
            db_instance_dict['DBParameterGroupName'] = troposphere.Ref(dbparametergroup_resource)

            db_instance_resource = troposphere.rds.DBInstance.from_dict(
                f'DBInstance{logical_name}',
                db_instance_dict
            )
            self.template.add_resource(db_instance_resource)

            # DB Event Notifications
            self.set_db_instance_event_notifications(logical_name, db_instance, db_instance_resource)

            # DB Instance Outputs
            self.create_output(
                title=f'DBInstanceName{logical_name}',
                description=f'DB Instance Name for {logical_name}',
                value=troposphere.Ref(db_instance_resource),
                ref=db_instance.paco_ref_parts + ".name",
            )

        # DB Cluster Outputs
        self.create_output(
            title='DBClusterName',
            description='DB Cluster Name',
            value=troposphere.Ref(db_cluster_res),
            ref=self.resource.paco_ref_parts + ".name",
        )
        self.create_output(
            title='ClusterEndpointAddress',
            description='Cluster Endpoint Address',
            value=troposphere.GetAtt(db_cluster_res, 'Endpoint.Address'),
            ref=self.resource.paco_ref_parts + ".endpoint.address",
        )
        self.create_output(
            title='ClusterEndpointPort',
            description='Cluster Endpoint Port',
            value=troposphere.GetAtt(db_cluster_res, 'Endpoint.Port'),
            ref=self.resource.paco_ref_parts + ".endpoint.port",
        )
        self.create_output(
            title='ClusterReadEndpointAddress',
            description='Cluster ReadEndpoint Address',
            value=troposphere.GetAtt(db_cluster_res, 'ReadEndpoint.Address'),
            ref=self.resource.paco_ref_parts + ".readendpoint.address",
        )

        # DNS - Route53 Record Set
        if rds_aurora.is_dns_enabled() == True:
            route53_ctl = self.paco_ctx.get_controller('route53')
            for dns in rds_aurora.dns:
                route53_ctl.add_record_set(
                    self.account_ctx,
                    self.aws_region,
                    rds_aurora,
                    enabled=rds_aurora.is_enabled(),
                    dns=dns,
                    record_set_type='CNAME',
                    resource_records=[rds_aurora.paco_ref + '.endpoint.address'],
                    stack_group=self.stack.stack_group,
                    async_stack_provision=True
                )
            for read_dns in rds_aurora.read_dns:
                route53_ctl.add_record_set(
                    self.account_ctx,
                    self.aws_region,
                    rds_aurora,
                    enabled=rds_aurora.is_enabled(),
                    dns=read_dns,
                    record_set_type='CNAME',
                    resource_records=[rds_aurora.paco_ref + '.readendpoint.address'],
                    stack_group=self.stack.stack_group,
                    async_stack_provision=True
                )

    def create_notification_param(self, group):
        "Create a CFN Parameter for a Notification Group"
        notification_ref = self.paco_ctx.project['resource']['sns'].computed[self.account_ctx.name][self.stack.aws_region][group].paco_ref + '.arn'

        # Re-use existing Parameter or create new one
        param_name = 'Notification{}'.format(utils.md5sum(str_data=notification_ref))
        if param_name not in self.notification_groups:
            notification_param = self.create_cfn_parameter(
                param_type='String',
                name=param_name,
                description='SNS Topic to notify',
                value=notification_ref,
                min_length=1, # prevent borked empty values from breaking notification
            )
            self.notification_groups[param_name] = notification_param
        return self.notification_groups[param_name]

    def set_db_instance_event_notifications(self, logical_name, db_instance, db_instance_resource=None):
        event_notifications = db_instance.get_value_or_default('event_notifications')
        if event_notifications == None:
            return
        if db_instance.external_resource == True:
            source_ids = [db_instance.external_instance_name]
        else:
            source_ids = [troposphere.Ref(db_instance_resource)]
        for group in event_notifications.groups:
            notif_param = self.create_notification_param(group)
            event_subscription_resource = troposphere.rds.EventSubscription(
                title=self.create_cfn_logical_id(f"DBEventSubscription{logical_name}{group}"),
                template=self.template,
                EventCategories=event_notifications.event_categories,
                SourceIds=source_ids,
                SnsTopicArn=troposphere.Ref(notif_param),
                SourceType='db-instance',
            )

class RDS(StackTemplate):
    """
    RDS creates a singel AWS::RDS::DBInstance resource
    """

    def __init__(self, stack, paco_ctx,):
        rds_config = stack.resource
        config_ref = rds_config.paco_ref_parts
        super().__init__(stack, paco_ctx)
        self.set_aws_name('RDS', self.resource_group_name, self.resource.name)
        self.init_template('RDS')
        template = self.template
        if not rds_config.is_enabled(): return

        rds_logical_id = 'PrimaryDBInstance'

        # DB Subnet Group
        db_subnet_id_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='DBSubnetIdList',
            description='The list of subnet IDs where this database will be provisioned.',
            value=rds_config.segment+'.subnet_id_list',
        )
        db_subnet_group_res = troposphere.rds.DBSubnetGroup(
            title='DBSubnetGroup',
            template =template,
            DBSubnetGroupDescription=troposphere.Ref('AWS::StackName'),
            SubnetIds=troposphere.Ref(db_subnet_id_list_param),
        )

        # DB Parameter Group
        engine_major_version = None
        if rds_config.parameter_group == None:
            # No Parameter Group supplied, create one
            engine_major_version = '.'.join(rds_config.engine_version.split('.')[0:2])
            param_group_family = gen_vocabulary.rds_engine_versions[rds_config.engine][rds_config.engine_version]['param_group_family']
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
            )

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

        # RDS MultiAZ (Mysql, Postgresql)
        if schemas.IRDSMultiAZ.providedBy(rds_config):
            sg_param_ref_list = []
            for sg_ref in rds_config.security_groups:
                sg_hash = utils.md5sum(str_data=sg_ref)
                sg_param = self.create_cfn_parameter(
                    param_type='AWS::EC2::SecurityGroup::Id',
                    name=self.create_cfn_logical_id('SecurityGroup'+sg_hash),
                    description='VPC Security Group to attach to the RDS.',
                    value=sg_ref+'.id',
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
                # To restore an existing DB from a Snapshot, RDS will need to replace the RDS
                # resource, in which case the DBInstanceIdentifier name CAN NOT be set
                # del db_instance_dict['DBInstanceIdentifier']

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
                    )
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
                    )
                    db_instance_dict['MasterUserPassword'] = troposphere.Ref(master_password_param)

            db_instance_res = troposphere.rds.DBInstance.from_dict(
                rds_logical_id,
                db_instance_dict
            )
            template.add_resource(db_instance_res)

            # Outputs
            self.create_output(
                title='DBInstanceName',
                description='DB Instance Name',
                value=troposphere.Ref(db_instance_res),
                ref=config_ref + ".name",
            )
            self.create_output(
                title='RDSEndpointAddress',
                description='RDS Endpoint URL',
                value=troposphere.GetAtt(db_instance_res, 'Endpoint.Address'),
                ref=config_ref + ".endpoint.address",
            )

            # Legacy Route53 Record Set
            if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == True:
                if rds_config.is_dns_enabled() == True:
                    for dns_config in rds_config.dns_config:
                        dns_hash = utils.md5sum(str_data=(rds_config.hosted_zone+rds_config.domain_name))
                        primary_hosted_zone_id_param = self.create_cfn_parameter(
                            param_type='String',
                            name='DNSHostedZoneId'+dns_hash,
                            description='The hosted zone id to create the Route53 record set.',
                            value=rds_config.primary_hosted_zone+'.id',
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

        # DNS - Route53 Record Set
        if self.paco_ctx.legacy_flag('route53_record_set_2019_10_16') == False:
            if rds_config.is_dns_enabled() == True:
                route53_ctl = self.paco_ctx.get_controller('route53')
                for dns_config in rds_config.dns:
                    route53_ctl.add_record_set(
                        self.account_ctx,
                        self.aws_region,
                        rds_config,
                        enabled=rds_config.is_enabled(),
                        dns=dns_config,
                        record_set_type='CNAME',
                        resource_records=['paco.ref ' + config_ref + '.endpoint.address'],
                        stack_group=self.stack.stack_group,
                        async_stack_provision=True,
                        config_ref=rds_config.paco_ref_parts + '.dns'
                    )
