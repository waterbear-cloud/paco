import os
from aim.cftemplates.cftemplates import CFTemplate

from io import StringIO
from enum import Enum
import base64
from aim.models import vocabulary, schemas


class RDS(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,
                 app_id,
                 grp_id,
                 res_id,
                 rds_config,
                 config_ref=None):

        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         enabled=rds_config.is_enabled(),
                         config_ref=config_ref,
                         stack_group=stack_group,
                         stack_tags=stack_tags)
        self.set_aws_name('RDS', grp_id, res_id)

        # Define the Template
        template_yaml_fmt = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'RDS: {0[engine]:s} - {0[engine_version]:s}'

Parameters:

{0[parameters]:s}

Conditions:
  RDSIsEnabled: !Equals [!Ref RDSEnabled, 'true']
  EncryptionIsEnabled: !Not [!Equals [!Ref KMSKeyId, '']]
  DBSnapshotExists: !Not [!Equals [!Ref DBSnapshotIdentifier, '']]
  EncryptionEnabledAndNotDBSnapshotExists: !And [!Condition EncryptionIsEnabled, !Not [!Condition DBSnapshotExists]]
  OptionGroupIsEnabled: !Equals [!Ref OptionGroupEnabled, 'true']

Resources:

  DBSubnetGroup:
    Type: 'AWS::RDS::DBSubnetGroup'
    Properties:
      DBSubnetGroupDescription: !Ref 'AWS::StackName'
      SubnetIds: !Ref DBSubnetIdList

  DBParameterGroup:
    Type: 'AWS::RDS::DBParameterGroup'
    Properties:
      Description: !Ref 'AWS::StackName'
      Family: !Ref ParameterGroupFamily

  OptionGroup:
    Type: AWS::RDS::OptionGroup
    Condition: OptionGroupIsEnabled
    Properties:
      EngineName: !Ref Engine
      MajorEngineVersion: !Ref EngineMajorVersion
      OptionConfigurations:{0[option_configurations]}
      OptionGroupDescription: !Ref 'AWS::StackName'

{0[resources]:s}

#Outputs:

{0[outputs]:s}

"""
        template_table = {
            'engine': None,
            'engine_version': None,
            'parameters': None,
            'resources': None,
            'option_configurations': None,
            'outputs': None
        }

        cluster_resources_fmt = """
  DBClusterParameterGroup:
    Type: 'AWS::RDS::DBClusterParameterGroup'
    Properties:
      Description: !Ref 'AWS::StackName'
      Family: !Ref ClusterParameterGroupFamily
      Parameters:
        character_set_client: utf8
        character_set_connection: utf8
        character_set_database: utf8
        character_set_filesystem: utf8
        character_set_results: utf8
        character_set_server: utf8
        collation_connection: utf8_general_ci
        collation_server: utf8_general_ci

  DBCluster:
    Type: 'AWS::RDS::DBCluster'
    Condition: RDSIsEnabled
    DeletionPolicy: Snapshot
    UpdateReplacePolicy: Snapshot
    Properties:
      {0[common_db_properties]:s}
      #DatabaseName: !If [DBSnapshotExists, !Ref 'AWS::NoValue', !Ref DatabaseName]
      DBClusterParameterGroupName: !Ref DBClusterParameterGroup
      EngineMode: provisioned
      SnapshotIdentifier: !If [DBSnapshotExists, !Ref DBSnapshotIdentifier, !Ref 'AWS::NoValue']
      VpcSecurityGroupIds: {0[security_group_ids]:s}
"""

        db_instance_fmt = """
  DBInstance{0[db_position]:s}:
    Type: 'AWS::RDS::DBInstance'
    Condition: RDSIsEnabled
    Properties:
      {0[db_cluster_properties]:s}
      {0[db_instance_properties]}
      DBInstanceIdentifier: !Ref 'AWS::StackName'
      AllowMajorVersionUpgrade: !Ref AllowMajorVersionUpgrade
      AutoMinorVersionUpgrade: !Ref AllowMinorVersionUpgrade
      CopyTagsToSnapshot: true
      DBInstanceClass: !Ref DBInstanceClass
      DBParameterGroupName: !Ref DBParameterGroup
      DBSubnetGroupName: !Ref DBSubnetGroup
      Engine: !Ref Engine
      MultiAZ: !Ref MultiAZ
"""
        db_instance_table = {
            'db_position': None,
            'db_instance_properties': None
        }

        db_instance_cluster_properties = """
      DBClusterIdentifier: !Ref DBCluster
"""
        db_instance_properties = """
      AllocatedStorage: !Ref AllocatedStorage
      DBSnapshotIdentifier: !If [DBSnapshotExists, !Ref DBSnapshotIdentifier, !Ref 'AWS::NoValue']
      StorageType: !Ref StorageType
      OptionGroupName: !If [OptionGroupIsEnabled, !Ref OptionGroup, !Ref 'AWS::NoValue']
"""

        db_common_properties_fmt = """
      Engine: !Ref Engine
      EngineVersion: !Ref EngineVersion
      BackupRetentionPeriod: !Ref BackupRetentionPeriod
      DBSubnetGroupName: !Ref DBSubnetGroup
      KmsKeyId: !If [EncryptionEnabledAndNotDBSnapshotExists, !Ref KMSKeyId, !Ref 'AWS::NoValue']
      MasterUsername: !If [DBSnapshotExists, !Ref 'AWS::NoValue', !Ref MasterUsername]
      MasterUserPassword: !If [DBSnapshotExists, !Ref 'AWS::NoValue', !Ref MasterUserPassword]
      Port: !Ref Port
      PreferredBackupWindow: !Ref PreferredBackupWindow
      PreferredMaintenanceWindow: !Ref PreferredMaintenanceWindow
      StorageEncrypted: !If [DBSnapshotExists, !Ref 'AWS::NoValue', !If [EncryptionIsEnabled, true, false]]
"""

        record_set_fmt = """
  {0[db_position]:s}RecordSet:
    Type: AWS::Route53::RecordSet
    Condition: RDSIsEnabled
    Properties:
      Comment: 'RDS Internal {0[db_position]:s} DNS'
      HostedZoneId: !Ref {0[db_position]:s}HostedZoneId
      Name: !Ref {0[db_position]:s}DomainName
      ResourceRecords:
        - !GetAtt {0[db_resource]:s}.Endpoint.Address
      TTL: 300
      Type: CNAME
"""

        db_table = {
          'db_position': None,
          'db_instance_properties': None,
          'db_resource': None,
          'db_cluster_properties': None
        }

        parameters_yaml = ""
        resources_yaml = ""

        # ---------------------------------------------------------------------
        # Parameters
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='RDSEnabled',
          description='Boolean indicating whether RDS is enabled or not. Disabled will remove existing databases.',
          value=rds_config.is_enabled()
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='Engine',
          description='RDS Engine',
          value=rds_config.engine
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='EngineVersion',
          description='RDS Engine Version',
          value=rds_config.engine_version
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='EngineMajorVersion',
          description='RDS Engine Major Version',
          value='.'.join(rds_config.engine_version.split('.')[0:2])
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='BackupRetentionPeriod',
          description='Backup retention period in days.',
          value=rds_config.backup_retention_period
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='KMSKeyId',
          description='Specify a KMS Key Id to enable encryption at rest.',
          default='',
          value=rds_config.kms_key_id
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='MasterUsername',
          description='The master username to use when creating a new database instance.',
          value=rds_config.master_username
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='MasterUserPassword',
          description='The master user password.',
          value=rds_config.master_user_password,
          noecho=True
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='Port',
          description='The database port.',
          value=rds_config.port
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='PreferredBackupWindow',
          description='The preferred backup window.',
          value=rds_config.backup_preferred_window
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='PreferredMaintenanceWindow',
          description='The preferred maintenance window.',
          value=rds_config.maintenance_preferred_window
        )

        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='PrimaryDomainName',
          description='The primary domain name of the database',
          value=rds_config.primary_domain_name
        )

        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='PrimaryHostedZoneId',
          description='The primary domain name hosted zone id.',
          value=rds_config.primary_hosted_zone+'.id'
        )

        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='DBSnapshotIdentifier',
          description='The DB Snapshot Identifier or ARN to create a database from.',
          value=rds_config.db_snapshot_identifier,
          default=''
        )

        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='DBInstanceClass',
          description='The database instance class type',
          value=rds_config.db_instance_type
        )

        major_version = '.'.join(rds_config.engine_version.split('.')[0:2])
        param_group_family = vocabulary.rds_engine_versions[rds_config.engine][major_version]['param_group_family']
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='ParameterGroupFamily',
          description='The database parameter group family.',
          value=param_group_family
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='AllowMajorVersionUpgrade',
          description='Allow automated major version upgrades.',
          value=rds_config.allow_major_version_upgrade
        )
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='AllowMinorVersionUpgrade',
          description='Allow automated minor version upgrades.',
          value=rds_config.allow_minor_version_upgrade
        )

        # Subnet IDs
        parameters_yaml += self.create_cfn_parameter(
          param_type='List<AWS::EC2::Subnet::Id>',
          name='DBSubnetIdList',
          description='The list of subnet IDs where this database will be provisioned.',
          value=rds_config.segment+'.subnet_id_list'
        )

        # Options Group
        options_group_enabled = False
        if len(rds_config.option_configurations) > 0:
            options_group_enabled = True
        parameters_yaml += self.create_cfn_parameter(
          param_type='String',
          name='OptionGroupEnabled',
          description='Boolean indicating whether to create and link to an OptionGroup.',
          value=options_group_enabled
        )

        # RDS Mysql
        if schemas.IRDSMysql.providedBy(rds_config):
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name='MultiAZ',
                description='Enabled MultiAZ boolean.',
                value=rds_config.multi_az
            )
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name='AllocatedStorage',
                description='The amount of storage to allocate on database creation in gigabytes.',
                value=rds_config.storage_size_gb
            )
            parameters_yaml += self.create_cfn_parameter(
                param_type='String',
                name='StorageType',
                description='The storage type must be one of standard, gp2, or io1.',
                value=rds_config.storage_type
            )

            db_table['db_position'] = 'Primary'
            db_table['db_instance_properties'] = db_common_properties_fmt + db_instance_properties
            db_table['db_resource'] = 'DBInstance' + db_table['db_position']
            db_table['db_cluster_properties'] = ''
            resources_yaml += db_instance_fmt.format(db_table)
            if rds_config.primary_domain_name != None and rds_config.is_dns_enabled() == True:
                resources_yaml += record_set_fmt.format(db_table)


        option_configurations_yaml = ""
        for option_config in rds_config.option_configurations:
            option_configurations_yaml += '\n        - OptionName: ' + option_config.option_name
            if len(option_config.option_settings) > 0:
                option_configurations_yaml += '\n          OptionSettings:'
            for option_setting in option_config.option_settings:
                option_configurations_yaml += "\n            - Name: " + option_setting.name
                option_configurations_yaml += "\n              Value: '" + option_setting.value + "'"

                  #self.register_stack_output_config(config_ref, 'OutoutKeyName')

        template_table['parameters'] = parameters_yaml
        template_table['resources'] = resources_yaml
        template_table['engine'] = rds_config.engine
        template_table['engine_version'] = rds_config.engine_version
        template_table['option_configurations'] = option_configurations_yaml
        template_table['outputs'] = ""

        self.set_template(template_yaml_fmt.format(template_table))

