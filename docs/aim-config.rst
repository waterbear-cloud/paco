
.. _aim-config:

AIM Configuration Overview
==========================

AIM configuration is intended to be a complete declarative description of an Infrastructure-as-Code
cloud project. These files semantically describe cloud resources and logical groupings of those
resources. The contents of these files describe accounts, networks, environments, applications,
services, and monitoring configuration.

The AIM configuration files are parsed into a Python object model by the library
``aim.models``. This object model is used by AIM Orchestration to provision
AWS resources using CloudFormation. However, the object model is a standalone
Python package and can be used to work with cloud infrastructure semantically
with other tooling.


File format overview
--------------------

AIM configuration is a directory of files and sub-directories that
make up an AIM project. All of the files are in YAML_ format.

In the top-level directory are sub-directories that contain YAML
files each with a different format. This directories are:

  * ``Accounts/``: Each file in this directory is an AWS account.

  * ``NetworkEnvironments/``: This is the main show. Each file in this
    directory defines a complete set of networks, applications and environments.
    These can be provisioned into any of the accounts.

  * ``MonitorConfig/``: These contain alarm and log source information.

  * ``Services/``: These contain global or shared resources, such as
    S3 Buckets, IAM Users, EC2 Keypairs.

Also at the top level is a ``project.yaml`` file. Currently this file just
contains ``name:`` and ``title:`` attributes, but may be later extended to
contain useful global project configuration.

The YAML files are organized as nested key-value dictionaries. In each sub-directory,
key names map to relevant AIM schemas. An AIM schema is a set of fields that describe
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

Some key names map to AIM schemas that are containers. For containers, every key must contain
a set of key/value pairs that map to the AIM schema that container is for.
Every AIM schema in a container has a special ``name`` attribute, this attribute is derived
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

The ``title`` field is available in almost all AIM schemas. This is intended to be
a human readable name. This field can contain any character except newline.
The ``title`` field can also be added as a Tag to resources, so any characters
beyond 255 characters would be truncated.

References
----------

Some values can be special references. These will allow you to reference other values in
your AIM Configuration.

 * ``netenv.ref``: NetworkEnvironment reference

 * ``service.ref``: Service reference

 * ``config.ref``: Config reference


YAML Gotchas
------------

YAML allows unquoted scalar values. For the account_id field you could write:


.. code-block:: yaml

    account_id: 00223456789

However, when this field is read by the YAML parser, it will attempt to convert this to an integer.
Instead of the string '00223456789', the field will be an integer of 223456789.

You can quote scalar values in YAML with single quotes or double quotes:

.. code-block:: yaml

    account_id: '00223456789' # single quotes can contain double quote characters
    account_id: "00223456789" # double quotes can contain single quote characters

.. _YAML: https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html

Accounts
========

AWS account information is kept in the ``Accounts/`` directory.
Each file in this directory will define one AWS account, the filename
will be the ``name`` of the account, with a .yml or .yaml extension.


Account
--------

.. _Account:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - account_id
      - String
      - .. fa:: check
      - None
      - Can only contain digits.
      - Account ID
    * - account_type
      - String
      - .. fa:: check
      - AWS
      - Supported account types: AWS
      - Account Type
    * - admin_delegate_role_name
      - String
      - .. fa:: check
      - 
      - 
      - Administrator delegate IAM Role name for the account
    * - admin_iam_users
      - Container of AdminIAMUser_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Admin IAM Users
    * - is_master
      - Boolean
      - .. fa:: check
      - False
      - 
      - Boolean indicating if this a Master account
    * - organization_account_ids
      - List of Strings
      - .. fa:: times
      - []
      - 
      - A list of account ids to add to the Master account's AWS Organization
    * - region
      - String
      - .. fa:: check
      - us-west-2
      - 
      - Region to install AWS Account specific resources
    * - root_email
      - String
      - .. fa:: check
      - None
      - 
      - The email address for the root user of this account
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AdminIAMUser
-------------

.. _AdminIAMUser:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - username
      - String
      - .. fa:: check
      - 
      - 
      - IAM Username


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
The ``network:`` must contain a key/value pairs that match a NetworkEnvironment AIM schema.
The ``applications:`` and ``environments:`` are containers that hold Application
and Environment AIM schemas.

.. code-block:: yaml

    network:
        availability_zones: 2
        enabled: true
        region: us-west-2
        # more network YAML here ...

    applications:
        my-aim-app:
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
                                  source_security_group_id: netenv.ref aimdemo.network.vpc.security_groups.app.lb.id
                                  to_port: 80


Network
--------

.. _Network:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - availability_zones
      - Int
      - .. fa:: check
      - 0
      - Number of Availability Zones
      - Availability Zones
    * - aws_account
      - TextReference
      - .. fa:: check
      - None
      - 
      - AWS Account Reference
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - vpc
      - VPC_ AIM schema
      - .. fa:: times
      - None
      - 
      - VPC



VPC
----

.. _VPC:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cidr
      - String
      - .. fa:: check
      - 
      - 
      - CIDR
    * - enable_dns_hostnames
      - Boolean
      - .. fa:: check
      - False
      - 
      - Enable DNS Hostnames
    * - enable_dns_support
      - Boolean
      - .. fa:: check
      - False
      - 
      - Enable DNS Support
    * - enable_internet_gateway
      - Boolean
      - .. fa:: check
      - False
      - 
      - Internet Gateway
    * - nat_gateway
      - Container of NATGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - NAT Gateway
    * - private_hosted_zone
      - PrivateHostedZone_ AIM schema
      - .. fa:: check
      - None
      - 
      - Private hosted zone
    * - security_groups
      - Dict
      - .. fa:: check
      - {}
      - 
      - Security groups
    * - segments
      - Container of Segment_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Segments
    * - vpn_gateway
      - Container of VPNGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - VPN Gateway



NATGateway
-----------

.. _NATGateway:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - availability_zone
      - Int
      - .. fa:: check
      - None
      - 
      - Availability Zone
    * - default_route_segments
      - List of Strings
      - .. fa:: check
      - []
      - 
      - Default Route Segments
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - segment
      - String
      - .. fa:: check
      - public
      - 
      - Segment



VPNGateway
-----------

.. _VPNGateway:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled



PrivateHostedZone
------------------

.. _PrivateHostedZone:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - name
      - String
      - .. fa:: check
      - None
      - 
      - Hosted zone name



Segment
--------

.. _Segment:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - az1_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 1 CIDR
    * - az2_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 2 CIDR
    * - az3_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 3 CIDR
    * - az4_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 4 CIDR
    * - az5_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 5 CIDR
    * - az6_cidr
      - String
      - .. fa:: check
      - 
      - 
      - Availability Zone 6 CIDR
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - internet_access
      - Boolean
      - .. fa:: check
      - False
      - 
      - Internet Access



SecurityGroup
--------------

.. _SecurityGroup:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - egress
      - List of EgressRule_ AIM schemas
      - .. fa:: check
      - []
      - 
      - Egress
    * - group_description
      - String
      - .. fa:: check
      - 
      - 
      - Group description
    * - group_name
      - String
      - .. fa:: check
      - 
      - 
      - Group name
    * - ingress
      - List of IngressRule_ AIM schemas
      - .. fa:: check
      - []
      - 
      - Ingress



EgressRule
-----------

.. _EgressRule:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cidr_ip
      - String
      - .. fa:: check
      - 
      - 
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: check
      - 
      - 
      - CIDR IP v6
    * - description
      - String
      - .. fa:: check
      - 
      - 
      - Description
    * - from_port
      - Int
      - .. fa:: check
      - -1
      - 
      - From port
    * - name
      - String
      - .. fa:: check
      - 
      - 
      - Name
    * - protocol
      - String
      - .. fa:: check
      - None
      - 
      - IP Protocol
    * - source_security_group_id
      - TextReference
      - .. fa:: times
      - None
      - 
      - Source Security Group
    * - to_port
      - Int
      - .. fa:: check
      - -1
      - 
      - To port



IngressRule
------------

.. _IngressRule:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cidr_ip
      - String
      - .. fa:: check
      - 
      - 
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: check
      - 
      - 
      - CIDR IP v6
    * - description
      - String
      - .. fa:: check
      - 
      - 
      - Description
    * - from_port
      - Int
      - .. fa:: check
      - -1
      - 
      - From port
    * - name
      - String
      - .. fa:: check
      - 
      - 
      - Name
    * - protocol
      - String
      - .. fa:: check
      - None
      - 
      - IP Protocol
    * - source_security_group_id
      - TextReference
      - .. fa:: times
      - None
      - 
      - Source Security Group
    * - to_port
      - Int
      - .. fa:: check
      - -1
      - 
      - To port


Applications
============

Applications define a collection of AWS resources that work together to support a workload.

Applications specify the sets of AWS resources needed for an application workload.
Applications contain a mandatory ``groups:`` field which is container of ResrouceGroup objects.
Every AWS resource for an application must be contained in a ResrouceGroup with a unique name, and every
ResourceGroup has a Resources container where each Resource is given a unique name.

In the example below, the ``groups:`` contain keys named ``cicd``, ``website`` and ``bastion``.
In turn, each ResourceGroup contains ``resources:`` with names such as ``cpbd``, ``cert`` and ``alb``.

.. code-block:: yaml

    applications:
        my-aim-app:
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



ApplicationEngines
-------------------

.. _ApplicationEngines:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



Application
------------

.. _Application:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - groups
      - ResourceGroups_ AIM schema
      - .. fa:: check
      - None
      - 
      - 
    * - managed_updates
      - Boolean
      - .. fa:: check
      - False
      - 
      - Managed Updates
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



ResourceGroups
---------------

.. _ResourceGroups:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



ResourceGroup
--------------

.. _ResourceGroup:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - order
      - Int
      - .. fa:: check
      - None
      - The order in which the group will be deployed.
      - Group Dependency
    * - resources
      - Resources_ AIM schema
      - .. fa:: check
      - None
      - 
      - 
    * - title
      - String
      - .. fa:: check
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: check
      - None
      - 
      - Type



Resources
----------

.. _Resources:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



Resource
---------

.. _Resource:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: check
      - None
      - The order in which the resource will be deployed.
      - Resource Dependency
    * - resource_name
      - String
      - .. fa:: check
      - None
      - 
      - AWS Resource Name
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: check
      - None
      - 
      - Type of Resources



Environments
============

Environments define how the real AWS resources will be provisioned.
As environments copy the defaults from ``network`` and ``applications`` config,
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
a valid AWS region name, or the special ``default`` name, which is used to override
network and application config for a whole environment, regardless of region.

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


NetworkEnvironments
--------------------

.. _NetworkEnvironments:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



Environment
------------

.. _Environment:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



EnvironmentRegion
------------------

.. _EnvironmentRegion:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title


Services
========

Services need to be documented.

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


CloudWatchAlarm
----------------

.. _CloudWatchAlarm:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - classification
      - String
      - .. fa:: check
      - None
      - Class of Alarm: performance, security or health
      - Classification
    * - comparison_operator
      - String
      - .. fa:: check
      - None
      - 
      - Comparison operator
    * - enabled
      - Boolean
      - .. fa:: check
      - False
      - Could be deployed to AWS
      - Enabled
    * - evaluate_low_sample_count_percentile
      - String
      - .. fa:: check
      - None
      - 
      - Evaluate low sample count percentile
    * - evaluation_periods
      - Int
      - .. fa:: check
      - None
      - 
      - Evaluation periods
    * - extended_statistic
      - String
      - .. fa:: check
      - None
      - 
      - Extended statistic
    * - metric_name
      - String
      - .. fa:: check
      - None
      - 
      - Metric name
    * - name
      - String
      - .. fa:: check
      - 
      - 
      - Name
    * - period
      - Int
      - .. fa:: check
      - None
      - 
      - Period
    * - severity
      - String
      - .. fa:: check
      - low
      - 
      - Severity
    * - statistic
      - String
      - .. fa:: check
      - None
      - 
      - Statistic
    * - threshold
      - Float
      - .. fa:: check
      - None
      - 
      - Threshold
    * - treat_missing_data
      - String
      - .. fa:: check
      - None
      - 
      - Treat missing data



CWAgentLogSource
-----------------

.. _CWAgentLogSource:

.. list-table::
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - encoding
      - String
      - .. fa:: check
      - utf-8
      - 
      - Encoding
    * - log_group_name
      - String
      - .. fa:: check
      - 
      - CloudWatch Log Group name
      - Log group name
    * - log_stream_name
      - String
      - .. fa:: check
      - 
      - CloudWatch Log Stream name
      - Log stream name
    * - multi_line_start_pattern
      - String
      - .. fa:: check
      - 
      - 
      - Multi-line start pattern
    * - name
      - String
      - .. fa:: check
      - 
      - 
      - Name
    * - path
      - String
      - .. fa:: check
      - 
      - 
      - Path
    * - timestamp_format
      - String
      - .. fa:: check
      - 
      - 
      - Timestamp format
    * - timezone
      - String
      - .. fa:: check
      - Local
      - 
      - Timezone


