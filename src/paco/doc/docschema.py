"""
Loads paco.models.schemas and generates the doc file at ./doc/paco-config.rst
from the schema definition.
"""

import os.path
import re
import zope.schema
from paco.models import schemas
from zope.interface.common.mapping import IMapping

yaml_base = """
.. _yaml-base:

*****************
YAML File Schemas
*****************

Base Schemas
============

Base Schemas are never configured by themselves, they are schemas that are inherited by other schemas.

Interface
---------

A generic placeholder for any schema.

{INamed}

{ITitle}

{IName}

{IResource}

{IDeployable}

{IEnablable}

{IType}

{IDNSEnablable}

{IMonitorable}

{IMonitorConfig}

{IRegionContainer}

{IAccountRegions}

{INotifiable}

{ISecurityGroupRule}

{IApplicationEngine}

{IVPCConfiguration}

{IHostedZone}

Function
--------

A callable function that returns a value.

.. _alarmsets: yaml-monitoring.html#alarmsets

.. _healthchecks: yaml-monitoring.html#healthchecks

.. _cloudwatchlogsets: yaml-monitoring.html#cloudwatchlogsets

.. _resourcegroups: yaml-netenv.html#resourcegroups

.. _securitygroup: yaml-netenv.html#securitygroup

.. _segment: yaml-netenv.html#segment

.. _metric: yaml-monitoring.html#metric

.. _alarmnotifications: yaml-monitoring.html#alarmnotifications

"""

yaml_accounts = """
.. _yaml-accounts:

Accounts
========

AWS account information is kept in the ``accounts/`` directory. Each file in this directory
defines one AWS account, the filename is the ``name`` of the account, with a .yml or .yaml extension.

.. code-block:: yaml
    :caption: Typical accounts directory

    accounts/
      dev.yaml
      master.yaml
      prod.yaml
      tools.yaml


{IAccount}

{IAdminIAMUsers}

{IAdminIAMUser}

"""

yaml_global_resources = """
.. _yaml-global-resources:

Global Resources
================

Global Resources are defined in the top-level ``resource/`` directory. They define cloud resources
which do not belong to an environment or other logical grouping.

{ICloudTrail}


CodeCommit
----------

The ``resource/codecommit.yaml`` file manages CodeCommit repositories and users.
The top-level of the file is CodeCommitRepositoryGroups, and each group contains a set
of CodeCommit Repositories.

.. code-block:: yaml
    :caption: Example resource/codecommit.yaml file

    # Application CodeCommitRepositoryGroup
    application:
      # SaaS API CodeCommitRepository
      saas-api:
        enabled: true
        account: paco.ref accounts.tools
        region: us-west-2
        description: "SaaS API"
        repository_name: "saas-api"
        users:
          bobsnail:
            username: bobsnail@example.com
            public_ssh_key: 'ssh-rsa AAAAB3Nza.........6OzEFxCbJ'

      # SaaS UI CodeCommitRepository
      saas-ui:
        enabled: true
        account: paco.ref accounts.tools
        region: us-west-2
        description: "Saas UI"
        repository_name: "saas-ui"
        users:
          bobsnail:
            username: bobsnail@example.com
            public_ssh_key: 'ssh-rsa AAAAB3Nza.........6OzEFxCbJ'
          external_dev_team:
            username: external_dev_team
            public_ssh_key: 'ssh-rsa AAZA5RNza.........6OzEGHb7'

    # Docs CodeCommitRepositoryGroups
    docs:
      saas-book:
        enabled: true
        account: paco.ref accounts.prod
        region: eu-central-1
        description: "The SaaS Book (PDF)"
        repository_name: "saas-book"
        users:
          bobsnail:
            username: bobsnail@example.com
            public_ssh_key: 'ssh-rsa AAAAB3Nza.........6OzEFxCbJ'

Provision CodeCommit repos and users with:

.. code-block:: bash

    paco provision resource.codecommit

Be sure to save the AWS SSH key ID for each user after your provision their key. You can also see the SSH keys
in the AWS Console in the IAM Users if you lose them.

Visit the CodeCommit service in the AWS Console to see the SSH Url for a Git repo.

To authenticate, if you are using your default public SSH key, you can embed the AWS SSH key ID as the user in SSH Url:

.. code-block:: bash

    git clone ssh://APKAV........63ICK@server/project.git

Or add the AWS SSH key Id to your `~/.ssh/config` file. This is the easiest way, especially if you have
to deal with multiple SSH keys on your workstation:

.. code-block:: bash

    Host git-codecommit.*.amazonaws.com
      User APKAV........63ICK
      IdentityFile ~/.ssh/my_pubilc_key_rsa


{ICodeCommit}

{ICodeCommitRepositoryGroup}

{ICodeCommitRepository}

{ICodeCommitUser}

EC2 Keypairs
------------

The ``resource/ec2.yaml`` file manages AWS EC2 Keypairs.

.. code-block:: bash

    paco provision resource.ec2.keypairs # all keypairs
    paco provision resource.ec2.keypairs.devnet_usw2 # single keypair

.. code-block:: yaml
    :caption: Example resource/ec2.yaml file

    keypairs:
      devnet_usw2:
        keypair_name: "dev-us-west-2"
        region: "us-west-2"
        account: paco.ref accounts.dev
      staging_cac1:
        keypair_name: "staging-us-west-2"
        region: "ca-central-1"
        account: paco.ref accounts.stage
      prod_usw2:
        keypair_name: "prod-us-west-2"
        region: "us-west-2"
        account: paco.ref accounts.prod

{IEC2KeyPair}

IAM
---

The ``resource/iam.yaml`` file contains IAM Users. Each user account can be given
different levels of access a set of AWS accounts. For more information on how
IAM Users can be managed, see `Managing IAM Users with Paco`_.

.. code-block:: bash

    paco provision resource.iam.users


.. _Managing IAM Users with Paco: ./paco-users.html

{IIAMResource}

{IIAMUsers}

{IIAMUser}

{IIAMUserProgrammaticAccess}

{IIAMUserPermissions}

{IBaseRole}

{IRole}

{IRoleDefaultEnabled}

{IAssumeRolePolicy}

{IPolicy}

{IStatement}

{IPrincipal}

Route 53
--------

{IRoute53Resource}

{IRoute53HostedZone}

{IRoute53HostedZoneExternalResource}

{IRoute53RecordSet}


SNS Topics
----------

The ``resource/snstopics.yaml`` file manages AWS Simple Notification Service (SNS) resources.
SNS has only two resources: SNS Topics and SNS Subscriptions.

.. code-block:: bash

    paco provision resource.snstopics

.. code-block:: yaml
    :caption: Example resource/snstopics.yaml file

    account: paco.ref accounts.prod
    regions:
      - 'us-west-2'
      - 'us-east-1'
    groups:
      admin:
        title: "Administrator Group"
        enabled: true
        cross_account_access: true
        subscriptions:
          - endpoint: http://example.com/yes
            protocol: http
          - endpoint: https://example.com/orno
            protocol: https
          - endpoint: bob@example.com
            protocol: email
          - endpoint: bob@example.com
            protocol: email-json
          - endpoint: '555-555-5555'
            protocol: sms
          - endpoint: arn:aws:sqs:us-east-2:444455556666:queue1
            protocol: sqs
          - endpoint: arn:aws:sqs:us-east-2:444455556666:queue1
            protocol: application
          - endpoint: arn:aws:lambda:us-east-1:123456789012:function:my-function
            protocol: lambda

.. sidebar:: Prescribed Automation

    ``cross_account_access``: Creates an SNS Topic Policy which will grant all of the AWS Accounts in this
    Paco Project access to the ``sns.Publish`` permission for this SNS Topic.

    You will need this if you want to send CloudWatch Alarms from multiple accounts to the same
    SNS Topic(s) in one account.

.. _s3bucket: yaml-app-resources.html#s3bucket

.. _cloudwatchloggroup: yaml-app-resources.html#cloudwatchloggroup

.. _vpc: yaml-netenv-resources.html#vpc

"""

yaml_netenv = """
.. _yaml-netenv:

NetworkEnvironments
===================

NetworkEnvironments are files in the top-level ``netenv/`` directory.

NetworkEnvironments are the core of any Paco project. Every .yaml file in the
``netenv`` directory contains information about networks, applications and environments.
These files define how environments are provisioned and which networks and applications
will be provisioned in each one.

NetworkEnvironment files are hierarchical. They are nested many levels deep. At each
node in the hierarchy a different field schema is used. The top level has several key names:
``network:``, ``secrets_manager:``, ``backup_vaults:``, ``applications:`` and ``environments:``.
The ``network:`` must contain a key/value pairs that matches a NetworkEnvironment schema.
The ``applications:`` and ``environments:`` are containers that hold Application
and Environment schemas.

.. code-block:: yaml

    network:
        availability_zones: 2
        enabled: true
        region: us-west-2
        # more network YAML here ...

    applications:
        my-paco-app:
            # more application YAML here ...
        reporting-app:
            # more application YAML here ...

    environments:
        dev:
            title: Development Environment
            # more environment YAML here ...
        prod:
            title: Production Environment
            # more environment YAML here ...

The network, applications, backup_vaults and secrets_manager configuration sections hold logical configuration - this configuration
does not get direclty provisioned to the cloud - it doesn't reference any environments or regions.
Think of it as default configuration.

Environments are where actual cloud resources are declared to be provisioned. Environments reference the default
configuration from networks, applications, backups and secrets and declare which account(s) and region(s) to provision them in.

In environments, any field from the default configuration being referenced can be overridden.
This could be used for running a smaller instance size in the dev environment, enabling monitoring only in a production environment,
or specifying a different git branch name for a CI/CD for each environment.

Network
-------

The network config type defines a complete logical network: VPCs, Subnets, Route Tables, Network Gateways. The applications
defined later in this file will be deployed into networks that are built from this network template.

Networks have the following hierarchy:

.. code-block:: yaml

    network:
        # general config here ...
        vpc:
            # VPC config here ...
            nat_gateway:
                # NAT gateways container
            vpn_gateway:
                # VPN gateways container
            private_hosted_zone:
                # private hosted zone config here ...
            security_groups:
                # security groups here ...

SecurityGroups have two level nested names. These can be any names, but typically the first name is the name
of an application and the second name is for a resource in that application. However, other name schemes are possible to
support workloads sharing the same Security Groups.

.. code-block:: yaml
  :caption: Example security_groups configuration

    network:
      vpc:
        security_groups:
          myapp:
            lb:
              egress:
                - cidr_ip: 0.0.0.0/0
                  name: ANY
                  protocol: "-1"
              ingress:
                - cidr_ip: 128.128.255.255/32
                  from_port: 443
                  name: HTTPS
                  protocol: tcp
                  to_port: 443
                - cidr_ip: 128.128.255.255/32
                  from_port: 80
                  name: HTTP
                  protocol: tcp
                  to_port: 80
            web:
              egress:
                - cidr_ip: 0.0.0.0/0
                  name: ANY
                  protocol: "-1"
              ingress:
                - from_port: 80
                  name: HTTP
                  protocol: tcp
                  source_security_group: paco.ref netenv.my-paco-example.network.vpc.security_groups.app.lb
                  to_port: 80

{INetworkEnvironment}

{INetwork}

{IVPC}

{IVPCPeerings}

{IVPCPeering}

{IVPCPeeringRoute}

{INATGateways}

{INATGateway}

{IVPNGateways}

{IVPNGateway}

{IPrivateHostedZone}

{ISegments}

{ISegment}

{ISecurityGroupSets}

{ISecurityGroups}

{ISecurityGroup}

{IEgressRule}

{IIngressRule}

Applications
------------

Applications define a collection of AWS resources that work together to support a workload.

Applications specify the sets of AWS resources needed for an application workload.
Applications contain a mandatory ``groups:`` field which is container of ResrouceGroup objects.
Every AWS resource for an application must be contained in a ResourceGroup with a unique name, and every
ResourceGroup has a Resources container where each Resource is given a unique name.

.. Attention:: ResourceGroups and individual Resources both have an ``order`` field. When resources are
    created, they will be created based on the value of these ``order`` fields. First, the ResrouceGroup
    order is followed. The lowest order for a ResourceGroup will indicate that all those resources
    need to be created first, and then each Resource within a group will be created based on the order
    it is given.

In the example below, the ``groups:`` contain keys named ``cicd``, ``website`` and ``bastion``.
In turn, each ResourceGroup contains ``resources:`` with names such as ``cpbd``, ``cert`` and ``alb``.

.. code-block:: yaml

    applications:
        my-paco-app:
            enabled: true
            groups:
                cicd:
                    type: Deployment
                    resources:
                        cpbd:
                            # CodePipeline CI/CD
                            type: DeploymentPipeline
                            # configuration goes here ...
                website:
                    type: Application
                    resources:
                        cert:
                            type: ACM
                            # configuration goes here ...
                        alb:
                            # Application Load Balancer (ALB)
                            type: LBApplication
                            # configuration goes here ...
                        webapp:
                            # AutoScalingGroup (ASG) of web server instances
                            type: ASG
                            # configuration goes here ...
                bastion:
                    type: Bastion
                    resources:
                        instance:
                            # AutoScalingGroup (ASG) with only 1 instance (self-healing ASG)
                            type: ASG
                            # configuration goes here ...

{IApplicationEngines}

{IApplication}

{IResourceGroups}

{IResourceGroup}

{IResources}

Environments
------------

Environments define where actual cloud resources are to be provisioned.
As Environments copy all of the defaults from ``network``, ``applications``, ``backups`` and ``secrets_manager`` config
in the same NetworkEnvironment file.

The top level ``environments:`` container is simply a name and a title. This defines logical
names for each environment.

.. code-block:: yaml

    environments:

        dev:
            title: Development

        staging:
            title: Staging and QA

        prod:
            title: Production


Environments contain EnvironmentRegions. The name of an EnvironmentRegion must match
a valid AWS region name. The special ``default`` name is also available, which can be used to
override config for a whole environment, regardless of region.

The following example enables the applications named ``marketing-app`` and
``sales-app`` into all dev environments by default. In ``us-west-2`` this is
overridden and only the ``sales-app`` would be deployed there.

.. code-block:: yaml

    environments:

        dev:
            title: Development
            default:
                applications:
                    marketing-app:
                        enabled: true
                    sales-app:
                        enabled: true
            us-west-2:
                applications:
                    marketing-app:
                        enabled: false
            ca-central-1:
                enabled: true

{IEnvironment}

{IEnvironmentDefault}

{IEnvironmentRegion}

Secrets
-------

{ISecretsManager}

{ISecretsManagerApplication}

{ISecretsManagerGroup}

{ISecretsManagerSecret}

{IGenerateSecretString}


Backups
-------

`AWS Backup`_ can be provisioned with the ``backup_vaults:``. This is a container of BackupVaults.
Each BackupVault can contain BackupPlans which are further composed of a BackupRules and BackupSelections.

.. code-block:: yaml

    backup_vaults:
      accounting:
        enabled: false
        plans:
          ebs_daily:
            title: EBS Daily Backups
            enabled: true
            plan_rules:
              - title: Backup EBS volumes once a day
                schedule_expression: cron(0 8 ? * * *)
                lifecycle_delete_after_days: 14
            selections:
              - title: EBS volumes tagged with "backup-accounting: daily"
                tags:
                  - condition_type: STRINGEQUALS
                    condition_key: backup-accounting
                    condition_value: daily
          database_weekly:
            title: Weekly MySQL Backups
            enabled: true
            plan_rules:
              - title: Rule for Weekly MySQL Backups
                schedule_expression: cron(0 10 ? * 1 *)
                lifecycle_delete_after_days: 150
            selections:
              - title: Database resource selection
                resources:
                  - paco.ref netenv.mynet.applications.accounting.groups.app.resources.database

BackupVaults must be explicity referenced in an environment for them to be provisioned.

.. code-block:: yaml

    environmnets:
      prod:
        ca-central-1:
          backup_vaults:
            accounting:
              enabled: true


.. _AWS Backup: https://aws.amazon.com/backup/

{IBackupVaults}

{IBackupVault}

{IBackupPlans}

{IBackupPlan}

{IBackupPlanRule}

{IBackupPlanSelection}

{IBackupSelectionConditionResourceType}

.. _ec2keypair: yaml-global-resources.html#ec2keypair


"""

yaml_app_resources = """
.. _yaml-resources:

Application Resources
=====================

An Application is a collection of Resources. These are the Resources which can exist
as part of an Application.

{IApiGatewayRestApi}

{IApiGatewayMethods}

{IApiGatewayMethod}

{IApiGatewayModels}

{IApiGatewayModel}

{IApiGatewayResources}

{IApiGatewayResource}

{IApiGatewayStages}

{IApiGatewayStage}

{IApiGatewayMethodIntegration}

{IApiGatewayMethodIntegrationResponse}

{IApiGatewayMethodMethodResponse}

{IApiGatewayMethodMethodResponseModel}

{IApiGatewayCognitoAuthorizers}

{IApiGatewayDNS}


{IASG}

{IASGLifecycleHooks}

{IASGLifecycleHook}

{IASGScalingPolicies}

{IASGScalingPolicy}

{IASGRollingUpdatePolicy}

{IECSASGConfiguration}

{IECSCapacityProvider}

{ISSHAccess}

{IBlockDeviceMapping}

{IBlockDevice}

{IEBSVolumeMount}

{IEFSMount}

{IEC2LaunchOptions}

{ICloudFormationInit}

{ICloudFormationConfigSets}

{ICloudFormationConfigurations}

{ICloudFormationConfiguration}

{ICloudFormationInitCommands}

{ICloudFormationInitCommand}

{ICloudFormationInitFiles}

{ICloudFormationInitFile}

{ICloudFormationInitGroups}

{ICloudFormationInitPackages}

{ICloudFormationInitVersionedPackageSet}

{ICloudFormationInitPathOrUrlPackageSet}

{ICloudFormationInitServiceCollection}

{ICloudFormationInitServices}

{ICloudFormationInitService}

{ICloudFormationInitSources}

{ICloudFormationInitUsers}


{IACM}


{ICloudFront}

{ICloudFrontDefaultCacheBehavior}

{ICloudFrontCacheBehavior}

{ICloudFrontFactory}

{ICloudFrontOrigin}

{ICloudFrontCustomOriginConfig}

{ICloudFrontCustomErrorResponse}

{ICloudFrontViewerCertificate}

{ICloudFrontForwardedValues}

{ICloudFrontCookies}

{ICloudFrontLambdaFunctionAssocation}

{ICognitoLambdaTriggers}


{ICodeDeployApplication}

{ICodeDeployDeploymentGroups}

{ICodeDeployDeploymentGroup}


{ICognitoUserPool}

{ICognitoInviteMessageTemplates}

{ICognitoUserPoolClients}

{ICognitoUserPoolClient}

{ICognitoEmailConfiguration}

{ICognitoUserPoolPasswordPolicy}

{ICognitoUserPoolSchemaAttribute}

{ICognitoUICustomizations}

{ICognitoUserCreation}


{ICognitoIdentityPool}

{ICognitoIdentityProvider}


{IDeploymentPipeline}

{ICodePipelineStages}

{ICodePipelineStage}

{IDeploymentPipelineSourceStage}

{IDeploymentPipelineDeployStage}

{IDeploymentPipelineBuildStage}

{IDeploymentPipelineDeployCodeDeploy}

{IDeploymentPipelineSourceECR}

{ICodeDeployMinimumHealthyHosts}

{IDeploymentPipelineManualApproval}

{IDeploymentPipelineDeployS3}

{IDeploymentPipelineBuildCodeBuild}

{IDeploymentPipelineSourceCodeCommit}

{IDeploymentPipelineStageAction}

{IDeploymentPipelineConfiguration}

{IDeploymentGroupS3Location}


{IEBS}


{IEC2}


{IECRRepository}

{IECRRepositoryPermission}

{IECSCluster}


{IECSServices}

{IECSServicesContainer}

{IECSService}

{IECSTaskDefinitions}

{IECSTaskDefinition}

{IECSContainerDefinitions}

{IECSContainerDefinition}

{IECSLoadBalancer}

{IECSVolume}

{IECSUlimit}

{IECSHealthCheck}

{IECSHostEntry}

{IDockerLabels}

{IECSContainerDependency}

{IECSTaskDefinitionSecret}

{IECSLogging}

{IECSVolumesFrom}

{IECSTargetTrackingScalingPolicies}

{IECSTargetTrackingScalingPolicy}

{IServiceVPCConfiguration}

{IECSMountPoint}

{IPortMapping}


{IEIP}


{IEFS}


{IElastiCache}

{IElastiCacheRedis}


{IElasticsearchDomain}

{IElasticsearchCluster}

{IEBSOptions}

ESAdvancedOptions
^^^^^^^^^^^^^^^^^

An unconstrainted set of key-value pairs used to set advanced options for Elasticsearch.


{IEventsRule}

{IEventTarget}

{ILambda}

{ILambdaFunctionCode}

{ILambdaEnvironment}

{ILambdaVpcConfig}

{ILambdaVariable}

{ILambdaAtEdgeConfiguration}


{ILoadBalancer}

{IApplicationLoadBalancer}

{INetworkLoadBalancer}

{IDNS}

{IListeners}

{IListener}

{IListenerRule}

{IPortProtocol}

{ITargetGroups}

{ITargetGroup}


{IPinpointApplication}

{IPinpointSMSChannel}

{IPinpointEmailChannel}


{IIoTTopicRule}

{IIoTTopicRuleAction}

{IIoTTopicRuleIoTAnalyticsAction}

{IIoTTopicRuleLambdaAction}


{IIoTAnalyticsPipeline}

{IIoTDatasets}

{IIoTDataset}

{IDatasetTrigger}

{IDatasetContentDeliveryRules}

{IDatasetContentDeliveryRule}

{IDatasetS3Destination}

{IDatasetQueryAction}

{IDatasetContainerAction}

{IDatasetVariables}

{IDatasetVariable}

{IIoTPipelineActivities}

{IIoTPipelineActivity}

{IAttributes}

{IIotAnalyticsStorage}

{IStorageRetention}



{IManagedPolicy}

RDS
---

Relational Database Service (RDS) allows you to set up, operate, and scale a relational database in AWS.

You can create a single DB Instance or an Aurora DB Cluster.

DB Instance
^^^^^^^^^^^

Currently Paco supports ``RDSMysql`` and ``RDSPostgresql`` for single database instances.

.. sidebar:: Prescribed Automation

  **Using Secrets Manager with RDS**

  You can set the initial password with ``master_user_password``, however this requires storing a password
  in plain-text on disk. This is fine if you have a process for changing the password after creating a database,
  however, the Paco Secrets Manager support allows you to use a ``secrets_password`` instead of the
  ``master_user_password`` field:

  .. code-block:: yaml

      type: RDSMysql
      secrets_password: paco.ref netenv.mynet.secrets_manager.app.grp.mysql

  Then in your NetworkEnvironments ``secrets_manager`` configuration you would write:

  .. code-block:: yaml

      secrets_manager:
        app: # application name
          grp: # group name
              mysql: # secret name
                enabled: true
                generate_secret_string:
                  enabled: true
                  # secret_string_template and generate_string_key must
                  # have the following values for RDS secrets
                  secret_string_template: '{{"username": "admin"}}'
                  generate_string_key: "password"

  This would generate a new, random password in the AWS Secrets Manager service when the database is provisioned
  and connect that password with RDS.

.. code-block:: yaml
  :caption: RDSMysql resource example

  type: RDSMysql
  order: 1
  title: "Joe's MySQL Database server"
  enabled: true
  engine_version: 5.7.26
  db_instance_type: db.t3.micro
  port: 3306
  storage_type: gp2
  storage_size_gb: 20
  storage_encrypted: true
  multi_az: true
  allow_major_version_upgrade: false
  auto_minor_version_upgrade: true
  publically_accessible: false
  master_username: root
  master_user_password: "change-me"
  backup_preferred_window: 08:00-08:30
  backup_retention_period: 7
  maintenance_preferred_window: 'sat:10:00-sat:10:30'
  license_model: "general-public-license"
  cloudwatch_logs_exports:
    - error
    - slowquery
  security_groups:
    - paco.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: paco.ref netenv.mynet.network.vpc.segments.private
  primary_domain_name: database.example.internal
  primary_hosted_zone: paco.ref netenv.mynet.network.vpc.private_hosted_zone
  parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance

Aurora DB Cluster
^^^^^^^^^^^^^^^^^

AWS Aurora is relational databases built for the cloud. Aurora features a distributed, fault-tolerant,
self-healing storage system and can easily scale from a single database instance to a cluster of multiple
database instances.

When creating an Aurora RDS resource, you must specify your ``db_instances``. If you specify more than
one database instance, then Aurora will automatically designate one instance as a Writer and all other
instances will be Readers.

Each ``db_instance`` can specify it's own complete set of configuration or you can use the ``default_instance``
field to shared default configuration between instances. If a ``db_instance`` doesn't specify a value but it is
specified by ``default_instance`` it will fall back to using that value.

A simple Aurora with only a single database instance could be:

.. code-block:: yaml
  :caption: Simple Aurora single instance

  type: RDSMysqlAurora
  default_instance:
    db_instance_type: db.t3.medium
  db_instances:
    single:

A more complex Aurora with a cluster of three database instances could be:

.. code-block:: yaml
  :caption: Three instance Aurora cluster

  type: RDSMysqlAurora
  default_instance:
    db_instance_type: db.t3.medium
    enhanced_monitoring_interval_in_seconds: 30
  db_instances:
    first:
      availability_zone: 1
      db_instance_type: db.t3.large
      enhanced_monitoring_interval_in_seconds: 5
    second:
      availability_zone: 2
    third:
      availability_zone: 3

.. sidebar:: Prescribed Automation

  ``secrets_password``: Uses a Secrets Manager secret for the database master password.

  ``enable_kms_encryption``: Encrypts the database storage. Paco will creates a KMS-CMK dedicated to the
  DB Cluster. This key can only be accessed by the AWS RDS service.

  ``enhanced_monitoring_interval_in_seconds``: Paco will create an IAM Role to allow the RDS monitoring service
  access to perform enhanced monitoring.

  ``cluster_event_notifications`` and ``event_notifications`` must reference a group specified in ``resource/sns.yaml``.
  This group (SNS Topic) must already be provisioned in the same account and region as the database.

  ``monitoring`` applies to ``db_instances`` and will apply CloudWatch Alarms that are specific to each database instance
  in the Aurora cluster.

.. code-block:: yaml
  :caption: RDSPostgresqlAurora db cluster example

  type: RDSPostgresqlAurora
  order: 10
  enabled: true
  availability_zones: all
  engine_version: '11.7'
  port: 5432
  master_username: master
  secrets_password: paco.ref netenv.anet.secrets_manager.anet.app.database
  backup_preferred_window: 04:00-05:00
  backup_retention_period: 7
  maintenance_preferred_window: 'Sat:07:00-Sat:08:00'
  cluster_parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.clusterparams
  cloudwatch_logs_exports:
    - error
  security_groups:
    - paco.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: paco.ref netenv.anet.network.vpc.segments.private
  dns:
    - domain_name: database.test.internal
      hosted_zone: paco.ref netenv.mynet.network.vpc.private_hosted_zone
  enable_kms_encryption: true
  cluster_event_notifications:
    groups:
      - wb_low
    event_categories:
      - failover
      - failure
      - notification
  default_instance:
    parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance
    enable_performance_insights: true
    publicly_accessible: false
    db_instance_type: db.t3.medium
    allow_major_version_upgrade: true
    auto_minor_version_upgrade: true
    event_notifications:
      groups:
        - admin
      event_categories:
        - availability
        - configuration change
        - deletion
        - failover
        - failure
        - maintenance
        - notification
        - recovery
    monitoring:
      enabled: true
      alarm_sets:
        basic_dbinstance:
  db_instances:
    first:
      db_instance_type: db.t3.medium
      enhanced_monitoring_interval_in_seconds: 30
      availability_zone: 1
      monitoring:
        enabled: true
        alarm_sets:
          complex_dbinstance:
    second:
      enable_performance_insights: false
      event_notifications:
        groups:
          - admin
        event_categories:
          - maintenance


{IRDSMysql}

{IRDSPostgresql}

{IRDSPostgresqlAurora}

{IRDSMysqlAurora}

{IRDSOptionConfiguration}

{INameValuePair}

{IRDSMultiAZ}

{IRDSInstance}

{IRDSAurora}

{IRDSDBInstanceEventNotifications}

{IRDSClusterDefaultInstance}

{IRDSClusterInstance}

{IRDSClusterInstances}

{IRDSDBClusterEventNotifications}

DBParameters
^^^^^^^^^^^^

If you want to use DB Parameter Groups with your RDS, then use the ``parameter_group`` field to
reference a DBParameterGroup_ resource. Keeping DB Parameter Groups as separate resources allows
having multiple Paramater Groups provisioned at the same time. For example, you might have both
resources for ``dbparams_performance`` and ``dbparams_debug``, allowing you to use the AWS
Console to switch between performance and debug configuration quickl in an emergency.

{IDBParameterGroup}

{IDBClusterParameterGroup}


{IRoute53HealthCheck}


{IS3Bucket}

{IS3BucketPolicy}

{IS3LambdaConfiguration}

{IS3NotificationConfiguration}

{IS3StaticWebsiteHosting}

{IS3StaticWebsiteHostingRedirectRequests}

{ISNSTopic}

{ISNSTopicSubscription}


.. _role: yaml-global-resources.html#role

.. _roledefaultenabled: yaml-global-resources.html#roledefaultenabled

.. _ec2keypair: yaml-global-resources.html#ec2keypair

.. _secretsmanagersecret: yaml-netenv#secretsmanagersecret

.. _securitygroup: yaml-netenv#securitygroup

.. _simplecloudwatchalarm: yaml-monitoring.html#simplecloudwatchalarm

.. _route53hostedzone: yaml-global-resources.html#route53hostedzone

.. _policy: yaml-global-resources.html#policy

.. _codecommitrepository: yaml-global-resources.html#codecommitrepository

.. _codecommituser: yaml-global-resources.html#codecommituser

.. _segment: yaml-netenv.html#segment

.. _cloudwatchlogretention: yaml-monitoring.html#cloudwatchlogretention

.. _statement: yaml-global-resources.html#statement

.. _vpcconfiguration: yaml-base.html#vpcconfiguration

.. _hostedzone: yaml-base.html#hostedzone


"""


yaml_monitoring = """

Monitoring
==========

The ``monitor`` directory can contain two files: ``monitor/alarmsets.yaml`` and ``monitor/logging.yaml``. These files
contain CloudWatch Alarm and CloudWatch Agent Log Source configuration. These alarms and log sources
are grouped into named sets, and sets of alarms and logs can be applied to resources.

Currently only CloudWatch is supported, but it is intended in the future to support other monitoring and logging services
in the future.

{IAlarmSets}

{IAlarmSet}

{IAlarm}

{IDimension}

{IAlarmNotifications}

{IAlarmNotification}

{ISimpleCloudWatchAlarm}

{IMetricFilters}

{IMetricFilter}

{IMetricTransformation}

{IMetric}


{ICloudWatchLogging}

{ICloudWatchLogRetention}

{ICloudWatchLogSets}

{ICloudWatchLogSet}

{ICloudWatchLogGroups}

{ICloudWatchLogGroup}

{ICloudWatchLogSources}

{ICloudWatchLogSource}


{IHealthChecks}

.. _application: yaml-netenv.html#application

.. _route53healthcheck: yaml-app-resources.html#route53healthcheck


"""

def strip_interface_char(name):
    """
    Takes an Interface name and strips the leading I character
    """
    if name not in  ('Interface'):
        return name[1:]
    return name

def convert_schema_to_list_table(schema, level='-', header=True):
    """
    Introspects a Schema-based Interface and returns
    a ReStructured Text representation of it.
    """
    table_row_template = ''
    if schema.__name__ in ('IFunction', 'IDBParameters'):
        return ''
    schema_name = strip_interface_char(schema.__name__)
    output = []

    # Header
    output = [
"""
{name}
{divider}

""".format(**{
        'name': schema_name,
        'divider': (len(schema_name) + 1) * level
        })
    ]

    # Documentation
    output.append(schema.__doc__)
    output.append('\n')

    # No table for schemas with no fields, e.g. IDBParameters
    if len(zope.schema.getFields(schema).keys()) > 0:

        # Indicate if object is a container
        if schema.extends(IMapping):
            try:
                contained_schema = schema.getTaggedValue('contains')
            except KeyError:
                print('IMapping tagged value for contains not set for {}'.format(schema.__name__))
                contained_schema = ' unknown'
            caption = ":guilabel:`{}`".format(schema_name)
            if contained_schema != 'mixed':
                caption += " |bars| Container<`{}`_>".format(
                    strip_interface_char(contained_schema)
                )
        else:
            caption = ':guilabel:`{}`'.format(schema_name)

        output.append(
"""
.. _{}:

.. list-table:: {}
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
""".format(schema_name, caption)
        )
        table_row_template = \
            '    * - {name}\n' + \
            '      - {type}\n' + \
            '      - {purpose}\n' + \
            '      - {constraints}\n' + \
            '      - {default}\n'

    base_fields = []
    base_schemas = {}
    specific_fields = []
    for fieldname, field in sorted(zope.schema.getFields(schema).items()):
        if field.interface.__name__ != schema.__name__:
            base_fields.append(field)
            if field.interface.__name__ not in base_schemas:
                base_schemas[
                    strip_interface_char(field.interface.__name__)
                ] = None
        else:
            specific_fields.append(field)

    #base_fields = sorted(base_fields, key=lambda field: field.getName())
    #base_fields = sorted(base_fields, key=lambda field: field.interface.__name__)

    #for field in base_fields:
    #    output.append(convert_field_to_table_row(schema, field, table_row_template))
    for field in specific_fields:
        output.append(convert_field_to_table_row(schema, field, table_row_template))
    if len(specific_fields) == 0:
        output.append("""    * -
      -
      -
      -
      -
""")

    if len(base_schemas.keys()) > 0:
        base_schema_str = '\n*Base Schemas* '
        for base_schema in base_schemas.keys():
            base_schema_str += "`{}`_, ".format(base_schema)
        base_schema_str = base_schema_str[:-2]
        output.append(base_schema_str)

    return ''.join(output)

def indent_text(text):
    "Replace newlines with indented lines that are formatted for a ReST table row"
    return re.sub('\n(?<!$)', '\n        ', text)

def convert_field_to_table_row(schema, field, table_row_template):
    """Schema field converted to string that represents a ReST table row"""
    # add Required star
    if field.required:
        required = ' |star|'
    else:
        required = ''

    paco_ref = False
    if schemas.IPacoReference.providedBy(field):
        paco_ref = True

    # Type field
    data_type = field.__class__.__name__
    if data_type == 'PacoReference':
        if field.str_ok:
            data_type += '|String'
    if data_type in ('TextLine', 'Text'):
        data_type = 'String'
    elif data_type == 'Bool':
        data_type = 'Boolean'
    elif data_type == 'Object':
        if field.schema.extends(IMapping):
            data_type = 'Container<{}_>'.format(
                strip_interface_char(field.schema.__name__)
            )
        else:
            data_type = 'Object<{}_>'.format(
                strip_interface_char(field.schema.__name__)
            )
    elif data_type == 'Dict':
        if field.value_type and hasattr(field.value_type, 'schema'):
            data_type = 'Container<{}_>'.format(
                strip_interface_char(field.value_type.schema.__name__)
            )
        else:
            data_type = 'Dict'
    elif data_type == 'List':
        if field.value_type and zope.schema.interfaces.IChoice.providedBy(field.value_type):
            data_type = 'Choice'
        elif field.value_type and not zope.schema.interfaces.IText.providedBy(field.value_type):
            data_type = 'List<{}_>'.format(
                strip_interface_char(field.value_type.schema.__name__)
            )
        else:
            if schemas.IPacoReference.providedBy(field.value_type):
                paco_ref = True
                data_type = 'List<PacoReference>'
            else:
                data_type = 'List<String>'
    data_type = data_type + required

    # don't display the name field, it is derived from the key
    name = field.getName()

    # Change None to '' for default
    if field.default == None:
        default = ''
    else:
        default = field.default

    # Constraints field
    constraints = field.description
    if paco_ref:
        if hasattr(field, 'value_type'):
            schema_constraint = field.value_type.schema_constraint
            str_ok = field.value_type.str_ok
        else:
            schema_constraint = field.schema_constraint
            str_ok = field.str_ok
        if schema_constraint != '':
            if len(constraints) > 0:
                constraints += ' '
            constraints += 'Paco Reference to `{}`_.'.format(strip_interface_char(schema_constraint))
        else:
            print("Warning: Paco Reference field {}.{} does not specify schema constraint.".format(
                schema.__name__, field.__name__)
            )
        if str_ok == True:
            if len(constraints) > 0:
                constraints += ' '
            constraints += 'String Ok.'
    constraints = indent_text(constraints)

    if name != 'name' or not schema.extends(schemas.INamed):
        return table_row_template.format(
            **{
                'name': name,
                'type': data_type,
                'default': default,
                'purpose': field.title,
                'constraints': constraints
            }
        )
    else:
        return ''


DOCLESS_SCHEMAS = {
  'INameValuePair': None,
  'IS3BucketPolicy': None,
  'IS3LambdaConfiguration': None,
  'IS3NotificationConfiguration': None,
}

MINOR_SCHEMAS = {
    'IApiGatewayMethods': None,
    'IApiGatewayMethod': None,
    'IApiGatewayModels': None,
    'IApiGatewayModel': None,
    'IApiGatewayResources': None,
    'IApiGatewayResource': None,
    'IApiGatewayStages': None,
    'IApiGatewayStage': None,
    'IApiGatewayMethodMethodResponse': None,
    'IApiGatewayMethodMethodResponseModel': None,
    'IApiGatewayMethodIntegration': None,
    'IApiGatewayMethodIntegrationResponse': None,
    'IApiGatewayCognitoAuthorizers': None,
    'IApiGatewayDNS': None,
    'IDNS': None,
    'IASGLifecycleHook': None,
    'IASGScalingPolicy': None,
    'IASGRollingUpdatePolicy': None,
    'IECSASGConfiguration': None,
    'IECSCapacityProvider': None,
    'IECSTargetTrackingScalingPolicies': None,
    'IECSTargetTrackingScalingPolicy': None,
    'ISSHAccess': None,
    'IListener': None,
    'ITargetGroup': None,
    'IListeners': None,
    'ITargetGroups': None,
    'IPortProtocol': None,
    'IListenerRule': None,
    'IBlockDeviceMapping': None,
    'IEBSVolumeMount': None,
    'IEFSMount': None,
    'IEC2LaunchOptions': None,
    'IASGLifecycleHooks': None,
    'IASGScalingPolicies': None,
    'ICloudFormationConfigSets': None,
    'ICloudFormationConfigurations': None,
    'IBlockDevice': None,
    'IAssumeRolePolicy': None,
    'IPolicy': None,
    'IStatement': None,
    'IPrincipal': None,
    'IIAMUser': None,
    'IIAMUserProgrammaticAccess': None,
    'IIAMUserPermissions': None,
    'IRDSOptionConfiguration': None,
    'INameValuePair': None,
    'IDBParameters': None,
    'IDBParameterGroup': None,
    'IEventTarget': None,
    'ILambdaFunctionCode': None,
    'ILambdaEnvironment': None,
    'ILambdaVpcConfig': None,
    'ILambdaVariable': None,
    'ILambdaAtEdgeConfiguration': None,
    'IS3BucketPolicy': None,
    'IS3StaticWebsiteHosting': None,
    'IS3StaticWebsiteHostingRedirectRequests': None,
    'IS3LambdaConfiguration': None,
    'IS3NotificationConfiguration': None,
    'IS3StaticWebsiteHosting': None,
    'IS3StaticWebsiteHostingRedirectRequests': None,
    'ISNSTopicSubscription': None,
    'ICloudFrontCacheBehavior': None,
    'ICloudFrontFactory': None,
    'ICloudFrontOrigin': None,
    'ICloudFrontCustomOriginConfig': None,
    'ICloudFrontCustomErrorResponse': None,
    'ICloudFrontViewerCertificate': None,
    'ICloudFrontCacheBehavior': None,
    'ICloudFrontDefaultCacheBehavior': None,
    'ICloudFrontForwardedValues': None,
    'ICloudFrontCookies': None,
    'ICloudFrontLambdaFunctionAssocation': None,
    'ICloudFrontDefaultCacheBehavior': None,
    'ICognitoLambdaTriggers': None,
    'ICloudFrontOrigins': None,
    'ICloudFrontFactories': None,
    'ICodePipelineStages': None,
    'ICodePipelineStage': None,
    'IDeploymentPipelineStageAction': None,
    'IDeploymentPipelineSourceStage': None,
    'IDeploymentPipelineDeployStage': None,
    'IDeploymentPipelineBuildStage': None,
    'IDeploymentPipelineSourceECR': None,
    'IDeploymentPipelineDeployCodeDeploy': None,
    'ICodeDeployMinimumHealthyHosts': None,
    'IDeploymentPipelineManualApproval': None,
    'IDeploymentPipelineDeployS3': None,
    'IDeploymentPipelineBuildCodeBuild': None,
    'IDeploymentPipelineSourceCodeCommit': None,
    'IDeploymentPipelineConfiguration': None,
    'IDeploymentGroupS3Location': None,
    'IRDSMysql': None,
    'IRDSMultiAZ': None,
    'IRDSInstance': None,
    'IRDSDBInstanceEventNotifications': None,
    'IRDSClusterDefaultInstance': None,
    'IRDSClusterInstance': None,
    'IRDSClusterInstances': None,
    'IRDSDBClusterEventNotifications': None,
    'IDBClusterParameterGroup': None,
    'IRDSMysqlAurora': None,
    'IRDSPostgresql': None,
    'IRDSPostgresqlAurora': None,
    'IRDSAurora': None,
    'IElastiCacheRedis': None,
    'IElasticsearchCluster': None,
    'IECSServicesContainer': None,
    'IECSService': None,
    'IECSTaskDefinitions': None,
    'IECSTaskDefinition': None,
    'IECSContainerDefinitions': None,
    'IECSContainerDefinition': None,
    'IECSLoadBalancer': None,
    'IECSVolume': None,
    'IECSUlimit': None,
    'IECSHealthCheck': None,
    'IECSHostEntry': None,
    'IDockerLabels': None,
    'IECSContainerDependency': None,
    'IECSTaskDefinitionSecret': None,
    'IECSLogging': None,
    'IECSVolumesFrom': None,
    'IECSMountPoint': None,
    'IServiceVPCConfiguration': None,
    'IPortMapping': None,
    'IEBSOptions': None,
    'IESAdvancedOptions': None,
    'ICodeDeployDeploymentGroups': None,
    'ICodeDeployDeploymentGroup': None,
    'IIAMResource': None,
    'IIAMUsers': None,
    'IIAMUser': None,
    'IIAMUserProgrammaticAccess': None,
    'IIAMUserPermissions': None,
    'IBaseRole': None,
    'IRole': None,
    'IRoleDefaultEnabled': None,
    'IAssumeRolePolicy': None,
    'IPolicy': None,
    'IStatement': None,
    'ICodeCommit': None,
    'ICodeCommitRepository': None,
    'ICodeCommitRepositoryGroup': None,
    'ICodeCommitUser': None,
    'ICloudFormationInit': None,
    'ICloudFormationConfiguration': None,
    'ICloudFormationInitCommands': None,
    'ICloudFormationInitCommand': None,
    'ICloudFormationInitFiles': None,
    'ICloudFormationInitFile': None,
    'ICloudFormationInitGroups': None,
    'ICloudFormationInitPackages': None,
    'ICloudFormationInitServices': None,
    'ICloudFormationInitService': None,
    'ICloudFormationInitSources': None,
    'ICloudFormationInitUsers': None,
    'ICloudFormationInitVersionedPackageSet': None,
    'ICloudFormationInitPathOrUrlPackageSet': None,
    'ICloudFormationInitServiceCollection': None,
    'ISimpleCloudWatchAlarm': None,
    'ICloudWatchLogGroups': None,
    'ICloudWatchLogGroup': None,
    'ICloudWatchLogSources': None,
    'ICloudWatchLogSource': None,
    'ICloudWatchLogRetention': None,
    'IMetricFilters': None,
    'IMetricFilter': None,
    'IMetricTransformation': None,
    'ISecretsManagerApplication': None,
    'ISecretsManagerGroup': None,
    'ISecretsManagerSecret': None,
    'IGenerateSecretString': None,
    'IBackupVault': None,
    'IBackupPlans': None,
    'IBackupPlan': None,
    'IBackupPlanRule': None,
    'IBackupPlanSelection': None,
    'IBackupSelectionConditionResourceType': None,
    'IBackupSelectionConditionResourceType': None,
    'IRoute53Resource': None,
    'IRoute53HostedZone': None,
    'IRoute53HostedZoneExternalResource': None,
    'IRoute53RecordSet': None,
    'IEC2KeyPair': None,
    'IAlarm': None,
    'IAlarmSet': None,
    'IDimension': None,
    'IAlarmNotifications': None,
    'IAlarmNotification': None,
    'ISimpleCloudWatchAlarm': None,
    'IMetricFilters': None,
    'IMetricFilter': None,
    'IMetricTransformation': None,
    'IMetric': None,
    'ICloudWatchLogRetention': None,
    'ICloudWatchLogSets': None,
    'ICloudWatchLogSet': None,
    'ICloudWatchLogGroups': None,
    'ICloudWatchLogGroup': None,
    'ICloudWatchLogSources': None,
    'ICloudWatchLogSource': None,
    'INetworkEnvironment': None,
    'INetwork': None,
    'IVPC': None,
    'IVPCPeering': None,
    'IVPCPeerings': None,
    'IVPCPeeringRoute': None,
    'INATGateways': None,
    'INATGateway': None,
    'IVPNGateways': None,
    'IVPNGateway': None,
    'IPrivateHostedZone': None,
    'ISegments': None,
    'ISegment': None,
    'ISecurityGroupSets': None,
    'ISecurityGroups': None,
    'ISecurityGroup': None,
    'IEgressRule': None,
    'IIngressRule': None,
    'IApplicationEngines': None,
    'IApplication': None,
    'IResourceGroups': None,
    'IResourceGroup': None,
    'IResources': None,
    'IEnvironment': None,
    'IEnvironmentDefault': None,
    'IEnvironmentRegion': None,
    'ISecretsManager': None,
    'ISecretsManagerApplication': None,
    'ISecretsManagerGroup': None,
    'ISecretsManagerSecret': None,
    'IGenerateSecretString': None,
    'IBackupVaults': None,
    'IBackupVault': None,
    'IBackupPlans': None,
    'IBackupPlan': None,
    'IBackupPlanRule': None,
    'IBackupPlanSelection': None,
    'IBackupSelectionConditionResourceType': None,
    'IIoTTopicRuleAction': None,
    'IIoTTopicRuleIoTAnalyticsAction': None,
    'IIoTTopicRuleLambdaAction': None,
    'IIoTDatasets': None,
    'IIoTDataset': None,
    'IDatasetTrigger': None,
    'IDatasetContentDeliveryRules': None,
    'IDatasetContentDeliveryRule': None,
    'IDatasetS3Destination': None,
    'IDatasetQueryAction': None,
    'IDatasetContainerAction': None,
    'IDatasetVariables': None,
    'IDatasetVariable': None,
    'IIoTPipelineActivities': None,
    'IIoTPipelineActivity': None,
    'IAttributes': None,
    'IIotAnalyticsStorage': None,
    'IStorageRetention': None,
    'IPinpointSMSChannel': None,
    'IPinpointEmailChannel': None,
    'ICognitoUserPoolClients': None,
    'ICognitoInviteMessageTemplates': None,
    'ICognitoUserPoolClient': None,
    'ICognitoEmailConfiguration': None,
    'ICognitoUserPoolPasswordPolicy': None,
    'ICognitoUserPoolSchemaAttribute': None,
    'ICognitoUICustomizations': None,
    'ICognitoUserCreation': None,
    'ICognitoIdentityProvider': None,
    'IECRRepositoryPermission': None,
}

def create_tables_from_schema():
    result = {}
    import zope.interface.interface
    for name, obj in schemas.__dict__.items():
        if isinstance(obj, zope.interface.interface.InterfaceClass):
            level = '-'
            header = True
            if obj.__name__ in MINOR_SCHEMAS:
                level = '^'
            if obj.__name__ in DOCLESS_SCHEMAS:
                header=False
            result[obj.__name__] = convert_schema_to_list_table(obj, level=level, header=header)
    return result

doc_files = {
    'yaml_base': ('yaml-base.rst', yaml_base),
    'yaml_accounts': ('yaml-accounts.rst', yaml_accounts),
    'yaml_netenv': ('yaml-netenv.rst', yaml_netenv),
    'yaml_global_resources': ('yaml-global-resources.rst', yaml_global_resources),
    'yaml_app_resources': ('yaml-app-resources.rst', yaml_app_resources),
    'yaml_monitoring': ('yaml-monitoring.rst', yaml_monitoring),
}

yaml_base_links = """
.. _Named: yaml-base.html#Named

.. _Name: yaml-base.html#Name

.. _Title: yaml-base.html#Title

.. _Deployable: yaml-base.html#Deployable

.. _Enablable: yaml-base.html#Enablable

.. _SecurityGroupRule: yaml-base.html#SecurityGroupRule

.. _ApplicationEngine: yaml-base.html#ApplicationEngine

.. _DnsEnablable: yaml-base.html#ApplicationEngine

.. _monitorable: yaml-base.html#monitorable

.. _notifiable: yaml-base.html#notifiable

.. _resource: yaml-base.html#resource

.. _accountregions: yaml-base#accountregions

.. _type: yaml-base.html#type

.. _interface: yaml-base.html#interface

.. _regioncontainer: yaml-base.html#regioncontainer

.. _function: yaml-base.html#function

"""

yaml_account_links = """

.. _account: yaml-accounts.html#account

"""

def paco_schema_generate():
    tables_dict = create_tables_from_schema()
    for filename, docstring in doc_files.values():
        doc = os.path.abspath(os.path.dirname(__file__)).split(os.sep)[:-3]
        doc.append('docs')
        doc.append(filename)
        doc_file = os.sep.join(doc)
        if filename != 'yaml-base.rst':
            docstring += yaml_base_links
        if filename != 'yaml-accounts.rst':
            docstring += yaml_account_links
        with open(doc_file, 'w') as f:
            f.write(docstring.format(**tables_dict))

        print('Wrote to {}'.format(doc_file))
