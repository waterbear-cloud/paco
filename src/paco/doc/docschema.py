"""
Loads paco.models.schemas and generates the doc file at ./doc/paco-config.rst
from the schema definition.
"""

import os.path
import zope.schema
from paco.models import schemas
from zope.interface.common.mapping import IMapping


paco_config_template = """
.. _paco-config:

********************
Configuration Basics
********************

Paco configuration overview
===========================

Paco configuration is a complete declarative description of a cloud project.
These files semantically describe cloud resources and logical groupings of those
resources. The contents of these files describe accounts, networks, environments, applications,
resources, services, and monitoring configuration.

The Paco configuration files are parsed into a Python object model by the library
``paco.models``. This object model is used by Paco to provision
AWS resources using CloudFormation. However, the object model is a standalone
Python package and can be used to work with cloud infrastructure semantically
with other tooling.


File format overview
--------------------

Paco configuration is a directory of files and sub-directories that
make up an Paco project. All of the files are in YAML_ format.

In the top-level directory are sub-directories that contain YAML
files each with a different format. This directories are:

  * ``accounts/``: Each file in this directory is an AWS account.

  * ``netenv/``: Each file in this directory defines a complete set of networks, applications and environments.
    Environments are provisioned into your accounts.

  * ``monitor/``: These contain alarm and logging configuration.

  * ``resource/``: For global resources, such as S3 Buckets, IAM Users, EC2 Keypairs.

  * ``service/``: For extension plug-ins.

Also at the top level are ``project.yaml`` and ``paco-project-version.txt`` files.

The ``paco-project-version.txt`` is a simple one line file with the version of the Paco project
file format, e.g. ``2.1``. The Paco project file format version contains a major and a medium
version. The major version indicates backwards incompatable changes, while the medium
version indicates additions of new object types and fields.

The ``project.yaml`` contains gloabl information about the Paco project. It also contains
an ``paco_project_version`` field that is loaded from ``paco-project-version.txt``.

The YAML files are organized as nested key-value dictionaries. In each sub-directory,
key names map to relevant Paco schemas. An Paco schema is a set of fields that describe
the field name, type and constraints.

An example of how this hierarchy looks, in a NetworksEnvironent file, a key name ``network:``
must have attributes that match the Network schema. Within the Network schema there must be
an attribute named ``vpc:`` which contains attributes for the VPC schema. That looks like this:

.. code-block:: yaml

    network:
        enabled: true
        region: us-west-2
        availability_zones: 2
        vpc:
            enable_dns_hostnames: true
            enable_dns_support: true
            enable_internet_gateway: true

Some key names map to Paco schemas that are containers. For containers, every key must contain
a set of key/value pairs that map to the Paco schema that container is for.
Every Paco schema in a container has a special ``name`` attribute, this attribute is derived
from the key name used in the container.

For example, the NetworkEnvironments has a key name ``environments:`` that maps
to an Environments container object. Environments containers contain Environment objects.

.. code-block:: yaml

    environments:
        dev:
            title: Development
        staging:
            title: Staging
        prod:
            title: Production

When this is parsed, there would be three Environment objects:

.. code-block:: text

    Environment:
        name: dev
        title: Development
    Environment:
        name: staging
        title: Staging
    Environment:
        name: prod
        title: Production

.. Attention:: Key naming warning: As the key names you choose will be used in the names of
    resources provisioned in AWS, they should be as short and simple as possible. If you wanted
    rename keys, you need to first delete all of your AWS resources under their old key names,
    then recreate them with their new name. Try to give everything short, reasonable names.

Key names have the following restrictions:

  * Can contain only letters, numbers, hyphens and underscores.

  * First character must be a letter.

  * Cannot end with a hyphen or contain two consecutive hyphens.

Certain AWS resources have additional naming limitations, namely S3 bucket names
can not contain uppercase letters and certain resources have a name length of 64 characters.

The ``title`` field is available in almost all Paco schemas. This is intended to be
a human readable name. This field can contain any character except newline.
The ``title`` field can also be added as a Tag to resources, so any characters
beyond 255 characters would be truncated.

.. _YAML: https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html

Enabled/Disabled
================

Many Paco schemas have an ``enabled:`` field. If an Environment, Application or Resource field
have ``enabled: True``, that indicates it should be provisioned. If ``enabled: False`` is set,
then the resource won't be provisioned.

To determine if a resource should be provisioned or not, if **any** field higher in the tree
is set to ``enabled: False`` the resource will not be provisioned.

In the following example, the network is enabled by default. The dev environment is enabled,
and there are two applications, but only one of them is enabled. The production environment
has two applications enabled, but they will not be provisioned as enabled is off for the
entire environment.

.. code-block:: yaml

    network:
        enabled: true

    environments:
        dev:
            enabled: true
            default:
                applications:
                    my-paco-example:
                        enabled: false
                    reporting-app:
                        enabled: true
        prod:
            enabled: false
            default:
                applications:
                    my-paco-example:
                        enabled: true
                    reporting-app:
                        enabled: true

.. Attention:: Note that currently, this field is only applied during the ``paco provision`` command.
    If you want delete an environment or application, you need to do so explicitly with the ``paco delete`` command.

References and Substitutions
============================

Some values can be special references. These will allow you to reference other values in
your Paco Configuration.

 * ``paco.ref netenv``: NetworkEnvironment reference

 * ``paco.ref resource``: Resource reference

 * ``paco.ref accounts``: Account reference

 * ``paco.ref function``: Function reference

 * ``paco.ref service``: Service reference

References are in the format:

``type.ref name.seperated.by.dots``

In addition, the ``paco.sub`` string indicates a substitution.

paco.ref netenv
---------------

To refer to a value in a NetworkEnvironment use an ``paco.ref netenv`` reference. For example:

``paco.ref netenv.my-paco-example.network.vpc.security_groups.app.lb``

After ``paco.ref netenv`` should be a part which matches the filename of a file (without the .yaml or .yml extension)
in the NetworkEnvironments directory.

The next part will start to walk down the YAML tree in the specified file. You can
either refer to a part in the ``applications`` or ``network`` section.

Keep walking down the tree, until you reach the name of a field. This final part is sometimes
a field name that you don't supply in your configuration, and is instead can be generated
by the Paco Engine after it has provisioned the resource in AWS.

An example where a ``paco.ref netenv`` refers to the id of a SecurityGroup:

.. code-block:: yaml

    network:
        vpc:
            security_groups:
                app:
                    lb:
                        egress
                    webapp:
                        ingress:
                            - from_port: 80
                            name: HTTP
                            protocol: tcp
                            source_security_group: paco.ref netenv.my-paco-example.network.vpc.security_groups.app.lb

You can refer to an S3 Bucket and it will return the ARN of the bucket:

.. code-block:: yaml

    artifacts_bucket: paco.ref netenv.my-paco-example.applications.app.groups.cicd.resources.cpbd_s3

SSL Certificates can be added to a load balancer. If a reference needs to look-up the name or id of an AWS
Resource, it needs to first be provisioned, the ``order`` field controls the order in which resources
are created. In the example below, the ACM cert is first created, then an Applicatin Load Balancer is provisioned
and configured with the ACM cert:

.. code-block:: yaml

    applications:
        app:
            groups:
                site:
                    cert:
                        type: ACM
                        order: 1
                        domain_name: example.com
                        subject_alternative_names:
                        - '*.example.com'
                    alb:
                        type: LBApplication
                        order: 2
                        listeners:
                            - port: 80
                                protocol: HTTP
                                redirect:
                                port: 443
                                protocol: HTTPS
                            - port: 443
                                protocol: HTTPS
                                ssl_certificates:
                                - paco.ref netenv.my-paco-example.applications.app.groups.site.resources.cert


paco.ref resource
-----------------

To refer to a global resource created in the Resources directory, use an ``paco.ref resource``. For example:

``paco.ref resource.route53.example``

After the ``paco.ref resource`` the next part should matche the filename of a file
(without the .yaml or .yml extension)  in the Resources directory.
Subsequent parts will walk down the YAML in that file.

In the example below, the ``hosted_zone`` of a Route53 record is looked up.

.. code-block:: yaml

    # NetworkEnvironments/my-paco-example.yaml

    applications:
        app:
            groups:
                site:
                    alb:
                        dns:
                        - hosted_zone: paco.ref resource.route53.example

    # Resources/Route53.yaml

    hosted_zones:
    example:
        enabled: true
        domain_name: example.com
        account: paco.ref accounts.prod


paco.ref accounts
-----------------

To refer to an AWS Account in the Accounts directory, use ``paco.ref``. For example:

``paco.ref accounts.dev``

Account references should matches the filename of a file (without the .yaml or .yml extension)
in the Accounts directory.

These are useful to override in the environments section in a NetworkEnvironment file
to control which account an environment should be deployed to:

.. code-block:: yaml

    environments:
        dev:
            network:
                aws_account: paco.ref accounts.dev

paco.ref function
-----------------

A reference dynamically resolved at runtime. For example:

``paco.ref function.aws.ec2.ami.latest.amazon-linux-2``

Currently can only look-up AMI IDs. Can be either ``aws.ec2.ami.latest.amazon-linux-2``
or ``aws.ec2.ami.latest.amazon-linux``.

.. code-block:: yaml

    web:
        type: ASG
        instance_ami: paco.ref function.aws.ec2.ami.latest.amazon-linux-2

paco.ref service
----------------

To refer to a service created in the Services directory, use an ``paco.ref service``. For example:

``paco.ref service.notification.<account>.<region>.applications.notification.groups.lambda.resources.snstopic``

Services are plug-ins that extend Paco with additional functionality. For example, custom notification, patching, back-ups
and cost optimization services could be developed and installed into an Paco application to provide custom business
functionality.

paco.sub
--------

Can be used to look-up a value and substitute the results into a templated string.


***********************
YAML Schemas and Fields
***********************

Accounts
========

AWS account information is kept in the ``Accounts/`` directory.
Each file in this directory will define one AWS account, the filename
will be the ``name`` of the account, with a .yml or .yaml extension.

{IAccount}

{IAdminIAMUser}

NetworkEnvironments
===================

NetworkEnvironments are the center of the show. Each file in the
``NetworkEnvironments`` directory can contain information about
networks, applications and environments. These files define how
applications are deployed into networks, what kind of monitoring
and logging the applications have, and which environments they are in.

These files are hierarchical. They can nest many levels deep. At each
node in the hierarchy a different config type is required. At the top level
there must be three key names, ``network:``, ``applications:`` and ``environments:``.
The ``network:`` must contain a key/value pairs that match a NetworkEnvironment Paco schema.
The ``applications:`` and ``environments:`` are containers that hold Application
and Environment Paco schemas.

.. code-block:: yaml

    network:
        availability_zones: 2
        enabled: true
        region: us-west-2
        # more network YAML here ...

    applications:
        my-paco-app:
            managed_updates: true
            # more application YAML here ...
        reporting-app:
            managed_updates: false
            # more application YAML here ...

    environments:
        dev:
            title: Development Environment
            # more environment YAML here ...
        prod:
            title: Production Environment
            # more environment YAML here ...

The network and applications configuration is intended to describe a complete default configuration - this configuration
does not get direclty provisioned to the cloud though - think of it as templated configuration. Environments are where
cloud resources are declared to be provisioned. Environments stamp the default network configuration and declare it should
be provisioned into specific account. Applications are then named in Environments, to indicate that the default application
configuration should be copied into that environment's network.

In environments, any of the default configuration can be overridden. This could be used for running a smaller instance size
in the dev environment than the production environment, applying detailed monitoring metrics to a production environment,
or specifying a different git branch name for a CI/CD for each environment.

Network
=======

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

.. Attention:: SecurityGroups is a special two level container. The first key will match the name of an application defined
    in the ``applications:`` section. The second key must match the name of a resource defined in the application.
    In addition, a SecurityGroup has egress and ingress rules that are a list of rules.

    The following example has two SecurityGroups for the application named ``my-web-app``: ``lb`` which will apply to the load
    balancer and ``webapp`` which will apply to the web server AutoScalingGroup.

    .. code-block:: yaml

        network:
            vpc:
                security_groups:
                    my-web-app:
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
                        webapp:
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

{INetwork}

{IVPC}

{IVPCPeering}

{IVPCPeeringRoute}

{INATGateway}

{IVPNGateway}

{IPrivateHostedZone}

{ISegment}

{ISecurityGroup}

{IEgressRule}

{IIngressRule}

Environments
============

Environments define how actual AWS resources should be provisioned.
As Environments copy all of the defaults from ``network`` and ``applications`` config,
they can define complex cloud deployments very succinctly.

The top level environments are simply a name and a title. They are logical
groups of actual environments.

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

Applications
============

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
                            # CodePipeline and CodeBuild CI/CD
                            type: CodePipeBuildDeploy
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

{IResource}

Application Resources
=====================

At it's heart, an Application is a collection of Resources. These are the Resources available for
applications.

{IApiGatewayRestApi}

{IApiGatewayMethods}

{IApiGatewayModels}

{IApiGatewayResources}

{IApiGatewayStages}

{ILBApplication}

{IDNS}

{IListener}

{IListenerRule}

{IPortProtocol}

{ITargetGroup}

{IASG}

{IASGLifecycleHooks}

{IASGScalingPolicies}

{IBlockDeviceMapping}

{IBlockDevice}

{IEBSVolumeMount}

{IEFSMount}

{IEC2LaunchOptions}

{ICloudFormationInit}

{ICloudFormationConfigSets}

{ICloudFormationConfigurations}

{ICodePipeBuildDeploy}

{IAWSCertificateManager}

{ICodeDeployApplication}

{ICodeDeployDeploymentGroups}

{ICodeDeployDeploymentGroup}

RDS
---

Relational Database Service (RDS) is a collection of relational databases.

There is no plain vanilla RDS type, but rather choose the type that specifies which kind of relational database
engine to use. For example, ``RDSMysql`` for MySQL on RDS or ``RDSAurora`` for an Amazon Aurora database.

If you want to use DB Parameter Groups with your RDS, then use the ``parameter_group`` field to
reference a DBParameterGroup_ resource. Keeping DB Parameter Group as a separate resource allows you
to have multiple Paramater Groups provisioned at the same time. For example, you might have both
resources for ``dbparams_performance`` and ``dbparams_debug``, allowing you to use the AWS
Console to switch between performance and debug configuration quickl in an emergency.

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



{IRDSOptionConfiguration}

{INameValuePair}

{IRDSMysql}

{IRDSAurora}

{IDBParameterGroup}

{IDBParameters}

{IEC2}

{ILambda}

{ILambdaFunctionCode}

{ILambdaEnvironment}

{ILambdaVpcConfig}

{ILambdaVariable}

{IManagedPolicy}

{IS3Bucket}

{IS3BucketPolicy}

{IS3LambdaConfiguration}

{IS3NotificationConfiguration}

{ISNSTopic}

{ISNSTopicSubscription}

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

{IElastiCacheRedis}

{IDeploymentPipeline}

{IDeploymentPipelineSourceStage}

{IDeploymentPipelineDeployStage}

{IDeploymentPipelineBuildStage}

{IDeploymentPipelineDeployCodeDeploy}

{ICodeDeployMinimumHealthyHosts}

{IDeploymentPipelineManualApproval}

{IDeploymentPipelineDeployS3}

{IDeploymentPipelineBuildCodeBuild}

{IDeploymentPipelineSourceCodeCommit}

{IDeploymentPipelineStageAction}

{IDeploymentPipelineConfiguration}

{IEFS}

{IEIP}

{IRoute53HealthCheck}

{IEventsRule}

{IEBS}


Secrets
=======

{ISecretsManager}

Global Resources
================

IAM
---

The ``Resources/IAM.yaml`` file contains IAM Users. Each user account can be given
different levels of access a set of AWS accounts.

{IIAMResource}

{IIAMUsers}

{IIAMUser}

{IIAMUserProgrammaticAccess}

{IIAMUserPermissions}

{IRole}

{IAssumeRolePolicy}

{IPolicy}

{IStatement}


MonitorConfig
=============

This directory can contain two files: ``alarmsets.yaml`` and ``logsets.yaml``. These files
contain CloudWatch Alarm and CloudWatch Agent Log Source configuration. These alarms and log sources
are grouped into named sets, and sets of alarms and logs can be applied to resources.

Currently only support for CloudWatch, but it is intended in the future to support other alarm and log sets.

AlarmSets are first named by AWS Resource Type, then by the name of the AlarmSet. Each name in an AlarmSet is
an Alarm.


.. code-block:: yaml

    # AutoScalingGroup alarms
    ASG:
        launch-health:
            GroupPendingInstances-Low:
                # alarm config here ...
            GroupPendingInstances-Critical:
                # alarm config here ...

    # Application LoadBalancer alarms
    LBApplication:
        instance-health:
            HealthyHostCount-Critical:
                # alarm config here ...
        response-latency:
            TargetResponseTimeP95-Low:
                # alarm config here ...
            HTTPCode_Target_4XX_Count-Low:
                # alarm config here ...

{IAlarm}

{IAlarmSet}

{IAlarmSets}

{IDimension}

{ICloudWatchLogSource}

{IAlarmNotifications}

{IAlarmNotification}

"""

def convert_schema_to_list_table(schema, level='-', header=True):
    """
    Introspects a Schema-based Interface and returns
    a ReStructured Text representation of it.
    """
    schema_name = schema.__name__[1:]
    output = []

    #if not header:
    #    level = '='

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
            caption = """:guilabel:`{}` |bars| Container where the keys are the ``name`` field.""".format(schema_name)
        else:
            caption = ':guilabel:`{}`'.format(schema_name)

        output.append(
"""
.. _{}:

.. list-table:: {}
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
""".format(schema_name, caption)
        )
        table_row_template = \
            '    * - {name}\n' + \
            '      - {type}\n' + \
            '      - {required}\n' + \
            '      - {default}\n' + \
            '      - {constraints}\n'  + \
            '      - {purpose}\n' + \
            '      - {baseschema}\n'

    base_fields = []
    specific_fields = []
    for fieldname, field in sorted(zope.schema.getFields(schema).items()):
        if field.interface.__name__ != schema.__name__:
            base_fields.append(field)
        else:
            specific_fields.append(field)

    base_fields = sorted(base_fields, key=lambda field: field.getName())
    base_fields = sorted(base_fields, key=lambda field: field.interface.__name__)

    for field in base_fields:
        output.append(convert_field_to_table_row(schema, field, table_row_template))
    for field in specific_fields:
        output.append(convert_field_to_table_row(schema, field, table_row_template))

    return ''.join(output)

def convert_field_to_table_row(schema, field, table_row_template):
    baseschema = schema.__name__[1:]
    if field.interface.__name__ != schema.__name__:
        baseschema = field.interface.__name__[1:]

    if field.required:
        req_icon = '.. fa:: check'
    else:
        req_icon = '.. fa:: times'

    data_type = field.__class__.__name__
    if data_type in ('TextLine', 'Text'):
        data_type = 'String'
    elif data_type == 'Bool':
        data_type = 'Boolean'
    elif data_type == 'Object':
        if field.schema.extends(IMapping):
            data_type = 'Container of {}_ Paco schemas'.format(field.schema.__name__[1:])
        else:
            data_type = '{}_ Paco schema'.format(field.schema.__name__[1:])
    elif data_type == 'Dict':
        if field.value_type and hasattr(field.value_type, 'schema'):
            data_type = 'Container of {}_ Paco schemas'.format(field.value_type.schema.__name__[1:])
        else:
            data_type = 'Dict'
    elif data_type == 'List':
        if field.value_type and not zope.schema.interfaces.IText.providedBy(field.value_type):
            data_type = 'List of {}_ Paco schemas'.format(field.value_type.schema.__name__[1:])
        else:
            data_type = 'List of Strings'

    # don't display the name field, it is derived from the key
    name = field.getName()

    # Change None to '' for default
    if field.default == None:
        default = ''
    else:
        default = field.default

    if name != 'name' or not schema.extends(schemas.INamed):
        return table_row_template.format(
            **{
                'name': name,
                'type': data_type,
                'required': req_icon,
                'default': default,
                'purpose': field.title,
                'constraints': field.description,
                'baseschema': baseschema
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
    'IApiGatewayMethods': None,
    'IApiGatewayModels': None,
    'IApiGatewayResources': None,
    'IApiGatewayStages': None,
    'IDNS': None,
    'IListener': None,
    'ITargetGroup': None,
    'IPortProtocol': None,
    'IListenerRule': None,
    'IBlockDeviceMapping': None,
    'IEBSVolumeMount': None,
    'IEFSMount': None,
    'IEC2LaunchOptions': None,
    'IASGLifecycleHooks': None,
    'IASGScalingPolicies': None,
    'ICloudFormationInit': None,
    'ICloudFormationConfigSets': None,
    'ICloudFormationConfigurations': None,
    'IBlockDevice': None,
    'IAssumeRolePolicy': None,
    'IPolicy': None,
    'IStatement': None,
    'IIAMUser': None,
    'IIAMUserProgrammaticAccess': None,
    'IIAMUserPermissions': None,
    'IRDSOptionConfiguration': None,
    'INameValuePair': None,
    'IDBParameters': None,
    'ILambdaFunctionCode': None,
    'ILambdaEnvironment': None,
    'ILambdaVpcConfig': None,
    'ILambdaVariable': None,
    'IS3BucketPolicy': None,
    'IS3LambdaConfiguration': None,
    'IS3NotificationConfiguration': None,
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
    'ICloudFrontDefaultCacheBehavior': None,
    'IDeploymentPipelineSourceStage': None,
    'IDeploymentPipelineDeployStage': None,
    'IDeploymentPipelineBuildStage': None,
    'IDeploymentPipelineDeployCodeDeploy': None,
    'ICodeDeployMinimumHealthyHosts': None,
    'IDeploymentPipelineManualApproval': None,
    'IDeploymentPipelineDeployS3': None,
    'IDeploymentPipelineBuildCodeBuild': None,
    'IDeploymentPipelineSourceCodeCommit': None,
    'IDeploymentPipelineStageAction': None,
    'IDeploymentPipelineConfiguration': None,
    'IRDSMysql': None,
    'IRDSAurora': None,
    'ICodeDeployDeploymentGroups': None,
    'ICodeDeployDeploymentGroup': None,
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

def paco_schema_generate():
    paco_doc = os.path.abspath(os.path.dirname(__file__)).split(os.sep)[:-3]
    paco_doc.append('docs')
    paco_doc.append('paco-config.rst')
    paco_config_doc = os.sep.join(paco_doc)
    tables_dict = create_tables_from_schema()

    with open(paco_config_doc, 'w') as f:
        f.write(paco_config_template.format(**tables_dict))

    print('Wrote to {}'.format(paco_config_doc))
