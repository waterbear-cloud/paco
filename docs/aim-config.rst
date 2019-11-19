
.. _aim-config:

********************
Configuration Basics
********************

AIM Configuration Overview
==========================

AIM configuration is a complete declarative description of an Infrastructure-as-Code
cloud project. These files semantically describe cloud resources and logical groupings of those
resources. The contents of these files describe accounts, networks, environments, applications,
resources, services, and monitoring configuration.

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

  * ``Resources/``: These contain global or shared resources, such as
    S3 Buckets, IAM Users, EC2 Keypairs.

Also at the top level are ``project.yaml`` and ``aim-project-version.txt`` files.

The ``aim-project-version.txt`` is a simple one line file with the version of the AIM Project
file format, e.g. ``2.1``. The AIM Project file format version contains a major and a medium
version. The major version indicates backwards incompatable changes, while the medium
version indicates additions of new object types and fields.

The ``project.yaml`` contains gloabl information about the AIM Project. It also contains
an ``aim_project_version`` field that is loaded from ``aim-project-version.txt``.

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


Enabled/Disabled
================

Many AIM schemas have an ``enabled:`` field. If an Environment, Application or Resource field
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
                    my-aim-example:
                        enabled: false
                    reporting-app:
                        enabled: true
        prod:
            enabled: false
            default:
                applications:
                    my-aim-example:
                        enabled: true
                    reporting-app:
                        enabled: true

.. Attention:: Note that currently, this field is only applied during the ``aim provision`` command.
    If you want delete an environment or application, you need to do so explicitly with the ``aim delete`` command.

References and Substitutions
============================

Some values can be special references. These will allow you to reference other values in
your AIM Configuration.

 * ``aim.ref netenv``: NetworkEnvironment reference

 * ``aim.ref resource``: Resource reference

 * ``aim.ref accounts``: Account reference

 * ``aim.ref function``: Function reference

 * ``aim.ref service``: Service reference

References are in the format:

``type.ref name.seperated.by.dots``

In addition, the ``aim.sub`` string indicates a substitution.

aim.ref netenv
--------------

To refer to a value in a NetworkEnvironment use an ``aim.ref netenv`` reference. For example:

``aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb``

After ``aim.ref netenv`` should be a part which matches the filename of a file (without the .yaml or .yml extension)
in the NetworkEnvironments directory.

The next part will start to walk down the YAML tree in the specified file. You can
either refer to a part in the ``applications`` or ``network`` section.

Keep walking down the tree, until you reach the name of a field. This final part is sometimes
a field name that you don't supply in your configuration, and is instead can be generated
by the AIM Engine after it has provisioned the resource in AWS.

An example where a ``aim.ref netenv`` refers to the id of a SecurityGroup:

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
                            source_security_group: aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb

You can refer to an S3 Bucket and it will return the ARN of the bucket:

.. code-block:: yaml

    artifacts_bucket: aim.ref netenv.my-aim-example.applications.app.groups.cicd.resources.cpbd_s3

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
                                - aim.ref netenv.my-aim-example.applications.app.groups.site.resources.cert


aim.ref resource
----------------

To refer to a global resource created in the Resources directory, use an ``aim.ref resource``. For example:

``aim.ref resource.route53.example``

After the ``aim.ref resource`` the next part should matche the filename of a file
(without the .yaml or .yml extension)  in the Resources directory.
Subsequent parts will walk down the YAML in that file.

In the example below, the ``hosted_zone`` of a Route53 record is looked up.

.. code-block:: yaml

    # NetworkEnvironments/my-aim-example.yaml

    applications:
        app:
            groups:
                site:
                    alb:
                        dns:
                        - hosted_zone: aim.ref resource.route53.example

    # Resources/Route53.yaml

    hosted_zones:
    example:
        enabled: true
        domain_name: example.com
        account: aim.ref accounts.prod


aim.ref accounts
----------------

To refer to an AWS Account in the Accounts directory, use ``aim.ref``. For example:

``aim.ref accounts.dev``

Account references should matches the filename of a file (without the .yaml or .yml extension)
in the Accounts directory.

These are useful to override in the environments section in a NetworkEnvironment file
to control which account an environment should be deployed to:

.. code-block:: yaml

    environments:
        dev:
            network:
                aws_account: aim.ref accounts.dev

aim.ref function
----------------

A reference dynamically resolved at runtime. For example:

``aim.ref function.aws.ec2.ami.latest.amazon-linux-2``

Currently can only look-up AMI IDs. Can be either ``aws.ec2.ami.latest.amazon-linux-2``
or ``aws.ec2.ami.latest.amazon-linux``.

.. code-block:: yaml

    web:
        type: ASG
        instance_ami: aim.ref function.aws.ec2.ami.latest.amazon-linux-2

aim.ref service
---------------

To refer to a service created in the Services directory, use an ``aim.ref service``. For example:

``aim.ref service.notification.<account>.<region>.applications.notification.groups.lambda.resources.snstopic``

Services are plug-ins that extend AIM with additional functionality. For example, custom notification, patching, back-ups
and cost optimization services could be developed and installed into an AIM application to provide custom business
functionality.

aim.sub
-------

Can be used to look-up a value and substitute the results into a templated string.


***********************
YAML Schemas and Fields
***********************

Accounts
========

AWS account information is kept in the ``Accounts/`` directory.
Each file in this directory will define one AWS account, the filename
will be the ``name`` of the account, with a .yml or .yaml extension.


Account
--------

Cloud account information

.. _Account:

.. list-table:: :guilabel:`Account`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - account_id
      - String
      - .. fa:: times
      - 
      - Can only contain digits.
      - Account ID
      - Account
    * - account_type
      - String
      - .. fa:: times
      - AWS
      - Supported types: 'AWS'
      - Account Type
      - Account
    * - admin_delegate_role_name
      - String
      - .. fa:: times
      - 
      - 
      - Administrator delegate IAM Role name for the account
      - Account
    * - admin_iam_users
      - Container of AdminIAMUser_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Admin IAM Users
      - Account
    * - is_master
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating if this a Master account
      - Account
    * - organization_account_ids
      - List of Strings
      - .. fa:: times
      - 
      - Each string in the list must contain only digits.
      - A list of account ids to add to the Master account's AWS Organization
      - Account
    * - region
      - String
      - .. fa:: check
      - no-region-set
      - Must be a valid AWS Region name
      - Region to install AWS Account specific resources
      - Account
    * - root_email
      - String
      - .. fa:: check
      - 
      - Must be a valid email address.
      - The email address for the root user of this account
      - Account



AdminIAMUser
-------------

An AWS Account Administerator IAM User

.. _AdminIAMUser:

.. list-table:: :guilabel:`AdminIAMUser`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - username
      - String
      - .. fa:: times
      - 
      - 
      - IAM Username
      - AdminIAMUser


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
                                  source_security_group: aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb
                                  to_port: 80


Network
--------



.. _Network:

.. list-table:: :guilabel:`Network` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - availability_zones
      - Int
      - .. fa:: times
      - 0
      - 
      - Availability Zones
      - NetworkEnvironment
    * - vpc
      - VPC_ AIM schema
      - .. fa:: times
      - 
      - 
      - VPC
      - NetworkEnvironment
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - aws_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - AWS Account Reference
      - Network



VPC
----


    AWS Resource: VPC
    

.. _VPC:

.. list-table:: :guilabel:`VPC`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - cidr
      - String
      - .. fa:: times
      - 
      - 
      - CIDR
      - VPC
    * - enable_dns_hostnames
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable DNS Hostnames
      - VPC
    * - enable_dns_support
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable DNS Support
      - VPC
    * - enable_internet_gateway
      - Boolean
      - .. fa:: times
      - False
      - 
      - Internet Gateway
      - VPC
    * - nat_gateway
      - Container of NATGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - NAT Gateway
      - VPC
    * - peering
      - Container of VPCPeering_ AIM schemas
      - .. fa:: times
      - 
      - 
      - VPC Peering
      - VPC
    * - private_hosted_zone
      - PrivateHostedZone_ AIM schema
      - .. fa:: times
      - 
      - 
      - Private hosted zone
      - VPC
    * - security_groups
      - Dict
      - .. fa:: times
      - {}
      - Two level deep dictionary: first key is Application name, second key is Resource name.
      - Security groups
      - VPC
    * - segments
      - Container of Segment_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Segments
      - VPC
    * - vpn_gateway
      - Container of VPNGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - VPN Gateway
      - VPC



VPCPeering
-----------


    VPC Peering
    

.. _VPCPeering:

.. list-table:: :guilabel:`VPCPeering`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - network_environment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Network Environment Reference
      - VPCPeering
    * - peer_account_id
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer AWS account Id
      - VPCPeering
    * - peer_region
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer AWS region
      - VPCPeering
    * - peer_role_name
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer role name
      - VPCPeering
    * - peer_vpcid
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer VPC Id
      - VPCPeering
    * - routing
      - List of VPCPeeringRoute_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Peering routes
      - VPCPeering



VPCPeeringRoute
----------------


    VPC Peering Route
    

.. _VPCPeeringRoute:

.. list-table:: :guilabel:`VPCPeeringRoute`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - cidr
      - String
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
      - VPCPeeringRoute
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment reference
      - VPCPeeringRoute



NATGateway
-----------


    AWS Resource: NAT Gateway
    

.. _NATGateway:

.. list-table:: :guilabel:`NATGateway` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - availability_zone
      - String
      - .. fa:: times
      - all
      - 
      - Availability Zones to launch instances in.
      - NATGateway
    * - default_route_segments
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Default Route Segments
      - NATGateway
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
      - NATGateway



VPNGateway
-----------


    AWS Resource: VPN Gateway
    

.. _VPNGateway:

.. list-table:: :guilabel:`VPNGateway` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable



PrivateHostedZone
------------------


    AWS Resource: Private Hosted Zone
    

.. _PrivateHostedZone:

.. list-table:: :guilabel:`PrivateHostedZone`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Hosted zone name
      - PrivateHostedZone
    * - vpc_associations
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Ids
      - PrivateHostedZone



Segment
--------


    AWS Resource: Segment
    

.. _Segment:

.. list-table:: :guilabel:`Segment`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - az1_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 1 CIDR
      - Segment
    * - az2_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 2 CIDR
      - Segment
    * - az3_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 3 CIDR
      - Segment
    * - az4_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 4 CIDR
      - Segment
    * - az5_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 5 CIDR
      - Segment
    * - az6_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 6 CIDR
      - Segment
    * - internet_access
      - Boolean
      - .. fa:: times
      - False
      - 
      - Internet Access
      - Segment



SecurityGroup
--------------


    AWS Resource: Security Group
    

.. _SecurityGroup:

.. list-table:: :guilabel:`SecurityGroup`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - egress
      - List of EgressRule_ AIM schemas
      - .. fa:: times
      - 
      - Every list item must be an EgressRule
      - Egress
      - SecurityGroup
    * - group_description
      - String
      - .. fa:: times
      - 
      - Up to 255 characters in length
      - Group description
      - SecurityGroup
    * - group_name
      - String
      - .. fa:: times
      - 
      - Up to 255 characters in length. Cannot start with sg-.
      - Group name
      - SecurityGroup
    * - ingress
      - List of IngressRule_ AIM schemas
      - .. fa:: times
      - 
      - Every list item must be an IngressRule
      - Ingress
      - SecurityGroup



EgressRule
-----------

Security group egress

.. _EgressRule:

.. list-table:: :guilabel:`EgressRule`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
      - Name
    * - cidr_ip
      - String
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
      - SecurityGroupRule
    * - cidr_ip_v6
      - String
      - .. fa:: times
      - 
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
      - SecurityGroupRule
    * - description
      - String
      - .. fa:: times
      - 
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
      - SecurityGroupRule
    * - from_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - From port
      - SecurityGroupRule
    * - port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - Port
      - SecurityGroupRule
    * - protocol
      - String
      - .. fa:: times
      - 
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
      - SecurityGroupRule
    * - to_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - To port
      - SecurityGroupRule
    * - destination_security_group
      - TextReference
      - .. fa:: times
      - 
      - An AIM Reference to a SecurityGroup
      - Destination Security Group Reference
      - EgressRule



IngressRule
------------

Security group ingress

.. _IngressRule:

.. list-table:: :guilabel:`IngressRule`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
      - Name
    * - cidr_ip
      - String
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
      - SecurityGroupRule
    * - cidr_ip_v6
      - String
      - .. fa:: times
      - 
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
      - SecurityGroupRule
    * - description
      - String
      - .. fa:: times
      - 
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
      - SecurityGroupRule
    * - from_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - From port
      - SecurityGroupRule
    * - port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - Port
      - SecurityGroupRule
    * - protocol
      - String
      - .. fa:: times
      - 
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
      - SecurityGroupRule
    * - to_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - To port
      - SecurityGroupRule
    * - source_security_group
      - TextReference
      - .. fa:: times
      - 
      - An AIM Reference to a SecurityGroup
      - Source Security Group Reference
      - IngressRule


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


Environment
------------


    Environment
    

.. _Environment:

.. list-table:: :guilabel:`Environment` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



EnvironmentDefault
-------------------


    Default values for an Environment's configuration
    

.. _EnvironmentDefault:

.. list-table:: :guilabel:`EnvironmentDefault` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - alarm_sets
      - Container of AlarmSets_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Sets
      - RegionContainer
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Application container
      - EnvironmentDefault
    * - network
      - Container of Network_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Network
      - EnvironmentDefault
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Secrets Manager
      - EnvironmentDefault



EnvironmentRegion
------------------


    An actual provisioned Environment in a specific region.
    May contains overrides of the IEnvironmentDefault where needed.
    

.. _EnvironmentRegion:

.. list-table:: :guilabel:`EnvironmentRegion` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Application container
      - EnvironmentDefault
    * - network
      - Container of Network_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Network
      - EnvironmentDefault
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Secrets Manager
      - EnvironmentDefault
    * - alarm_sets
      - Container of AlarmSets_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Sets
      - RegionContainer
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title


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

A collection of Application Engines

.. _ApplicationEngines:

.. list-table:: :guilabel:`ApplicationEngines` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



Application
------------


    Application : An Application Engine configuration to run in a specific Environment
    

.. _Application:

.. list-table:: :guilabel:`Application` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - groups
      - Container of ResourceGroups_ AIM schemas
      - .. fa:: check
      - 
      - 
      - 
      - ApplicationEngine
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the application will be processed
      - ApplicationEngine
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
      - Notifiable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ResourceGroups
---------------

A collection of Application Resource Groups

.. _ResourceGroups:

.. list-table:: :guilabel:`ResourceGroups` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ResourceGroup
--------------

A collection of Application Resources

.. _ResourceGroup:

.. list-table:: :guilabel:`ResourceGroup` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - 
      - 
      - 
      - ResourceGroup
    * - order
      - Int
      - .. fa:: check
      - 
      - 
      - The order in which the group will be deployed
      - ResourceGroup
    * - resources
      - Container of Resources_ AIM schemas
      - .. fa:: check
      - 
      - 
      - 
      - ResourceGroup
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - ResourceGroup
    * - type
      - String
      - .. fa:: check
      - 
      - 
      - Type
      - ResourceGroup



Resources
----------

A collection of Application Resources

.. _Resources:

.. list-table:: :guilabel:`Resources` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



Resource
---------


    AWS Resource to support an Application
    

.. _Resource:

.. list-table:: :guilabel:`Resource`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource


Application Resources
=====================

At it's heart, an Application is a collection of Resources. These are the Resources available for
applications.


ApiGatewayRestApi
------------------

An Api Gateway Rest API resource

.. _ApiGatewayRestApi:

.. list-table:: :guilabel:`ApiGatewayRestApi`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - api_key_source_type
      - String
      - .. fa:: times
      - 
      - Must be one of 'HEADER' to read the API key from the X-API-Key header of a request or 'AUTHORIZER' to read the API key from the UsageIdentifierKey from a Lambda authorizer.
      - API Key Source Type
      - ApiGatewayRestApi
    * - binary_media_types
      - List of Strings
      - .. fa:: times
      - 
      - Duplicates are not allowed. Slashes must be escaped with ~1. For example, image/png would be image~1png in the BinaryMediaTypes list.
      - Binary Media Types. The list of binary media types that are supported by the RestApi resource, such as image/png or application/octet-stream. By default, RestApi supports only UTF-8-encoded text payloads.
      - ApiGatewayRestApi
    * - body
      - String
      - .. fa:: times
      - 
      - Must be valid JSON.
      - Body. An OpenAPI specification that defines a set of RESTful APIs in JSON or YAML format. For YAML templates, you can also provide the specification in YAML format.
      - ApiGatewayRestApi
    * - body_file_location
      - StringFileReference
      - .. fa:: times
      - 
      - Must be valid path to a valid JSON document.
      - Path to a file containing the Body.
      - ApiGatewayRestApi
    * - body_s3_location
      - String
      - .. fa:: times
      - 
      - Valid S3Location string to a valid JSON or YAML document.
      - The Amazon Simple Storage Service (Amazon S3) location that points to an OpenAPI file, which defines a set of RESTful APIs in JSON or YAML format.
      - ApiGatewayRestApi
    * - clone_from
      - String
      - .. fa:: times
      - 
      - 
      - CloneFrom. The ID of the RestApi resource that you want to clone.
      - ApiGatewayRestApi
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description of the RestApi resource.
      - ApiGatewayRestApi
    * - endpoint_configuration
      - List of Strings
      - .. fa:: times
      - 
      - List of strings, each must be one of 'EDGE', 'REGIONAL', 'PRIVATE'
      - Endpoint configuration. A list of the endpoint types of the API. Use this field when creating an API. When importing an existing API, specify the endpoint configuration types using the `parameters` field.
      - ApiGatewayRestApi
    * - fail_on_warnings
      - Boolean
      - .. fa:: times
      - False
      - 
      - Indicates whether to roll back the resource if a warning occurs while API Gateway is creating the RestApi resource.
      - ApiGatewayRestApi
    * - methods
      - Container of ApiGatewayMethods_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
      - ApiGatewayRestApi
    * - minimum_compression_size
      - Int
      - .. fa:: times
      - 
      - A non-negative integer between 0 and 10485760 (10M) bytes, inclusive.
      - An integer that is used to enable compression on an API. When compression is enabled, compression or decompression is not applied on the payload if the payload size is smaller than this value. Setting it to zero allows compression for any payload size.
      - ApiGatewayRestApi
    * - models
      - Container of ApiGatewayModels_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
      - ApiGatewayRestApi
    * - parameters
      - Dict
      - .. fa:: times
      - {}
      - Dictionary of key/value pairs that are strings.
      - Parameters. Custom header parameters for the request.
      - ApiGatewayRestApi
    * - policy
      - String
      - .. fa:: times
      - 
      - Valid JSON document
      - A policy document that contains the permissions for the RestApi resource, in JSON format. To set the ARN for the policy, use the !Join intrinsic function with "" as delimiter and values of "execute-api:/" and "*".
      - ApiGatewayRestApi
    * - resources
      - Container of ApiGatewayResources_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
      - ApiGatewayRestApi
    * - stages
      - Container of ApiGatewayStages_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
      - ApiGatewayRestApi



ApiGatewayMethods
^^^^^^^^^^^^^^^^^^

Container for API Gateway Method objects

.. _ApiGatewayMethods:

.. list-table:: :guilabel:`ApiGatewayMethods` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ApiGatewayModels
^^^^^^^^^^^^^^^^^

Container for API Gateway Model objects

.. _ApiGatewayModels:

.. list-table:: :guilabel:`ApiGatewayModels` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ApiGatewayResources
^^^^^^^^^^^^^^^^^^^^

Container for API Gateway Resource objects

.. _ApiGatewayResources:

.. list-table:: :guilabel:`ApiGatewayResources` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ApiGatewayStages
^^^^^^^^^^^^^^^^^

Container for API Gateway Stage objects

.. _ApiGatewayStages:

.. list-table:: :guilabel:`ApiGatewayStages` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



LBApplication
--------------


The ``LBApplication`` resource type creates an Application Load Balancer. Use load balancers to route traffic from
the internet to your web servers.

Load balancers have ``listeners`` which will accept requrests on specified ports and protocols. If a listener
uses the HTTPS protocol, it can have an aim reference to an SSL Certificate. A listener can then either
redirect the traffic to another port/protcol or send it one of it's named ``target_groups``.

Each target group will specify it's health check configuration. To specify which resources will belong
to a target group, use the ``target_groups`` field on an ASG resource.

.. sidebar:: Prescribed Automation

    ``dns``: Creates Route 53 Record Sets that will resolve DNS records to the domain name of the load balancer.

    ``enable_access_logs``: Set to True to turn on access logs for the load balancer, and will automatically create
    an S3 Bucket with permissions for AWS to write to that bucket.

    ``access_logs_bucket``: Name an existing S3 Bucket (in the same region) instead of automatically creating a new one.
    Remember that if you supply your own S3 Bucket, you are responsible for ensuring that the bucket policy for
    it grants AWS the `s3:PutObject` permission.

.. code-block:: yaml
    :caption: Example LBApplication load balancer resource YAML

    type: LBApplication
    enabled: true
    enable_access_logs: true
    target_groups:
        api:
            health_check_interval: 30
            health_check_timeout: 10
            healthy_threshold: 2
            unhealthy_threshold: 2
            port: 3000
            protocol: HTTP
            health_check_http_code: 200
            health_check_path: /
            connection_drain_timeout: 30
    listeners:
        http:
            port: 80
            protocol: HTTP
            redirect:
                port: 443
                protocol: HTTPS
        https:
            port: 443
            protocol: HTTPS
            ssl_certificates:
                - aim.ref netenv.app.applications.app.groups.certs.resources.root
            target_group: api
    dns:
        - hosted_zone: aim.ref resource.route53.mynetenv
          domain_name: api.example.com
    scheme: internet-facing
    security_groups:
        - aim.ref netenv.app.network.vpc.security_groups.app.alb
    segment: public



.. _LBApplication:

.. list-table:: :guilabel:`LBApplication` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - access_logs_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Bucket to store access logs in
      - LBApplication
    * - access_logs_prefix
      - String
      - .. fa:: times
      - 
      - 
      - Access Logs S3 Bucket prefix
      - LBApplication
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the ALB
      - LBApplication
    * - enable_access_logs
      - Boolean
      - .. fa:: times
      - 
      - 
      - Write access logs to an S3 Bucket
      - LBApplication
    * - idle_timeout_secs
      - Int
      - .. fa:: times
      - 60
      - The idle timeout value, in seconds.
      - Idle timeout in seconds
      - LBApplication
    * - listeners
      - Container of Listener_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Listeners
      - LBApplication
    * - scheme
      - Choice
      - .. fa:: times
      - 
      - 
      - Scheme
      - LBApplication
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security Groups
      - LBApplication
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Id of the segment stack
      - LBApplication
    * - target_groups
      - Container of TargetGroup_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Target Groups
      - LBApplication



DNS
^^^^



.. _DNS:

.. list-table:: :guilabel:`DNS`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Domain name
      - DNS
    * - hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Hosted Zone Id
      - DNS
    * - ssl_certificate
      - TextReference
      - .. fa:: times
      - 
      - 
      - SSL certificate Reference
      - DNS
    * - ttl
      - Int
      - .. fa:: times
      - 300
      - 
      - TTL
      - DNS



Listener
^^^^^^^^^



.. _Listener:

.. list-table:: :guilabel:`Listener`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
      - PortProtocol
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol
      - PortProtocol
    * - redirect
      - PortProtocol_ AIM schema
      - .. fa:: times
      - 
      - 
      - Redirect
      - Listener
    * - rules
      - Container of ListenerRule_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Container of listener rules
      - Listener
    * - ssl_certificates
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SSL certificate References
      - Listener
    * - target_group
      - String
      - .. fa:: times
      - 
      - 
      - Target group
      - Listener



ListenerRule
^^^^^^^^^^^^^



.. _ListenerRule:

.. list-table:: :guilabel:`ListenerRule`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - host
      - String
      - .. fa:: times
      - 
      - 
      - Host header value
      - ListenerRule
    * - priority
      - Int
      - .. fa:: times
      - 1
      - 
      - Forward condition priority
      - ListenerRule
    * - redirect_host
      - String
      - .. fa:: times
      - 
      - 
      - The host to redirect to
      - ListenerRule
    * - rule_type
      - String
      - .. fa:: times
      - 
      - 
      - Type of Rule
      - ListenerRule
    * - target_group
      - String
      - .. fa:: times
      - 
      - 
      - Target group name
      - ListenerRule



PortProtocol
^^^^^^^^^^^^^

Port and Protocol

.. _PortProtocol:

.. list-table:: :guilabel:`PortProtocol`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
      - PortProtocol
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol
      - PortProtocol



TargetGroup
^^^^^^^^^^^^

Target Group

.. _TargetGroup:

.. list-table:: :guilabel:`TargetGroup`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
      - PortProtocol
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol
      - PortProtocol
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - connection_drain_timeout
      - Int
      - .. fa:: times
      - 
      - 
      - Connection drain timeout
      - TargetGroup
    * - health_check_http_code
      - String
      - .. fa:: times
      - 
      - 
      - Health check HTTP codes
      - TargetGroup
    * - health_check_interval
      - Int
      - .. fa:: times
      - 
      - 
      - Health check interval
      - TargetGroup
    * - health_check_path
      - String
      - .. fa:: times
      - /
      - 
      - Health check path
      - TargetGroup
    * - health_check_timeout
      - Int
      - .. fa:: times
      - 
      - 
      - Health check timeout
      - TargetGroup
    * - healthy_threshold
      - Int
      - .. fa:: times
      - 
      - 
      - Healthy threshold
      - TargetGroup
    * - unhealthy_threshold
      - Int
      - .. fa:: times
      - 
      - 
      - Unhealthy threshold
      - TargetGroup



ASG
----


    Auto Scaling Group
    

.. _ASG:

.. list-table:: :guilabel:`ASG`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - associate_public_ip_address
      - Boolean
      - .. fa:: times
      - False
      - 
      - Associate Public IP Address
      - ASG
    * - availability_zone
      - String
      - .. fa:: times
      - all
      - 
      - Availability Zones to launch instances in.
      - ASG
    * - block_device_mappings
      - List of BlockDeviceMapping_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Block Device Mappings
      - ASG
    * - cfn_init
      - CloudFormationInit_ AIM schema
      - .. fa:: times
      - 
      - 
      - CloudFormation Init
      - ASG
    * - cooldown_secs
      - Int
      - .. fa:: times
      - 300
      - 
      - Cooldown seconds
      - ASG
    * - desired_capacity
      - Int
      - .. fa:: times
      - 1
      - 
      - Desired capacity
      - ASG
    * - ebs_optimized
      - Boolean
      - .. fa:: times
      - False
      - 
      - EBS Optimized
      - ASG
    * - ebs_volume_mounts
      - List of EBSVolumeMount_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Elastic Block Store Volume Mounts
      - ASG
    * - efs_mounts
      - List of EFSMount_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Elastic Filesystem Configuration
      - ASG
    * - eip
      - TextReference
      - .. fa:: times
      - 
      - 
      - Elastic IP Reference or AllocationId
      - ASG
    * - health_check_grace_period_secs
      - Int
      - .. fa:: times
      - 300
      - 
      - Health check grace period in seconds
      - ASG
    * - health_check_type
      - String
      - .. fa:: times
      - EC2
      - Must be one of: 'EC2', 'ELB'
      - Health check type
      - ASG
    * - instance_ami
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance AMI
      - ASG
    * - instance_ami_type
      - String
      - .. fa:: times
      - amazon
      - Must be one of amazon, centos, suse, debian, ubuntu, microsoft or redhat.
      - The AMI Operating System family
      - ASG
    * - instance_iam_role
      - Role_ AIM schema
      - .. fa:: check
      - 
      - 
      - 
      - ASG
    * - instance_key_pair
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance key pair reference
      - ASG
    * - instance_monitoring
      - Boolean
      - .. fa:: times
      - False
      - 
      - Instance monitoring
      - ASG
    * - instance_type
      - String
      - .. fa:: times
      - 
      - 
      - Instance type
      - ASG
    * - launch_options
      - EC2LaunchOptions_ AIM schema
      - .. fa:: times
      - 
      - 
      - EC2 Launch Options
      - ASG
    * - lifecycle_hooks
      - Container of ASGLifecycleHooks_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lifecycle Hooks
      - ASG
    * - load_balancers
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Target groups
      - ASG
    * - max_instances
      - Int
      - .. fa:: times
      - 2
      - 
      - Maximum instances
      - ASG
    * - min_instances
      - Int
      - .. fa:: times
      - 1
      - 
      - Minimum instances
      - ASG
    * - scaling_policies
      - Container of ASGScalingPolicies_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Scaling Policies
      - ASG
    * - scaling_policy_cpu_average
      - Int
      - .. fa:: times
      - 0
      - 
      - Average CPU Scaling Polciy
      - ASG
    * - secrets
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Secrets Manager References
      - ASG
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security groups
      - ASG
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
      - ASG
    * - target_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Target groups
      - ASG
    * - termination_policies
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Terminiation policies
      - ASG
    * - update_policy_max_batch_size
      - Int
      - .. fa:: times
      - 1
      - 
      - Update policy maximum batch size
      - ASG
    * - update_policy_min_instances_in_service
      - Int
      - .. fa:: times
      - 1
      - 
      - Update policy minimum instances in service
      - ASG
    * - user_data_pre_script
      - String
      - .. fa:: times
      - 
      - 
      - User data pre-script
      - ASG
    * - user_data_script
      - String
      - .. fa:: times
      - 
      - 
      - User data script
      - ASG



ASGLifecycleHooks
^^^^^^^^^^^^^^^^^^


    Container of ASG LifecycleHOoks
    

.. _ASGLifecycleHooks:

.. list-table:: :guilabel:`ASGLifecycleHooks` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



ASGScalingPolicies
^^^^^^^^^^^^^^^^^^^


    Container of Auto Scaling Group Scaling Policies
    

.. _ASGScalingPolicies:

.. list-table:: :guilabel:`ASGScalingPolicies` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



BlockDeviceMapping
^^^^^^^^^^^^^^^^^^^



.. _BlockDeviceMapping:

.. list-table:: :guilabel:`BlockDeviceMapping`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - device_name
      - String
      - .. fa:: check
      - 
      - 
      - The device name exposed to the EC2 instance
      - BlockDeviceMapping
    * - ebs
      - BlockDevice_ AIM schema
      - .. fa:: times
      - 
      - 
      - Amazon Ebs volume
      - BlockDeviceMapping
    * - virtual_name
      - String
      - .. fa:: times
      - 
      - The name must be in the form ephemeralX where X is a number starting from zero (0), for example, ephemeral0.
      - The name of the virtual device.
      - BlockDeviceMapping



BlockDevice
^^^^^^^^^^^^



.. _BlockDevice:

.. list-table:: :guilabel:`BlockDevice`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - delete_on_termination
      - Boolean
      - .. fa:: times
      - True
      - 
      - Indicates whether to delete the volume when the instance is terminated.
      - BlockDevice
    * - encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Specifies whether the EBS volume is encrypted.
      - BlockDevice
    * - iops
      - Int
      - .. fa:: times
      - 
      - The maximum ratio of IOPS to volume size (in GiB) is 50:1, so for 5,000 provisioned IOPS, you need at least 100 GiB storage on the volume.
      - The number of I/O operations per second (IOPS) to provision for the volume.
      - BlockDevice
    * - size_gib
      - Int
      - .. fa:: times
      - 
      - This can be a number from 1-1,024 for standard, 4-16,384 for io1, 1-16,384 for gp2, and 500-16,384 for st1 and sc1.
      - The volume size, in Gibibytes (GiB).
      - BlockDevice
    * - snapshot_id
      - String
      - .. fa:: times
      - 
      - 
      - The snapshot ID of the volume to use.
      - BlockDevice
    * - volume_type
      - String
      - .. fa:: check
      - 
      - Must be one of standard, io1, gp2, st1 or sc1.
      - The volume type, which can be standard for Magnetic, io1 for Provisioned IOPS SSD, gp2 for General Purpose SSD, st1 for Throughput Optimized HDD, or sc1 for Cold HDD.
      - BlockDevice



EBSVolumeMount
^^^^^^^^^^^^^^^


    EBS Volume Mount Configuration
    

.. _EBSVolumeMount:

.. list-table:: :guilabel:`EBSVolumeMount`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - device
      - String
      - .. fa:: check
      - 
      - 
      - Device to mount the EBS Volume with.
      - EBSVolumeMount
    * - filesystem
      - String
      - .. fa:: check
      - 
      - 
      - Filesystem to mount the EBS Volume with.
      - EBSVolumeMount
    * - folder
      - String
      - .. fa:: check
      - 
      - 
      - Folder to mount the EBS Volume
      - EBSVolumeMount
    * - volume
      - TextReference
      - .. fa:: check
      - 
      - 
      - EBS Volume Resource Reference
      - EBSVolumeMount



EFSMount
^^^^^^^^^


    EFS Mount Folder and Target Configuration
    

.. _EFSMount:

.. list-table:: :guilabel:`EFSMount`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - folder
      - String
      - .. fa:: check
      - 
      - 
      - Folder to mount the EFS target
      - EFSMount
    * - target
      - TextReference
      - .. fa:: check
      - 
      - 
      - EFS Target Resource Reference
      - EFSMount



EC2LaunchOptions
^^^^^^^^^^^^^^^^^


    EC2 Launch Options
    

.. _EC2LaunchOptions:

.. list-table:: :guilabel:`EC2LaunchOptions`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - cfn_init_config_sets
      - List of Strings
      - .. fa:: times
      - []
      - 
      - List of cfn-init config sets
      - EC2LaunchOptions
    * - update_packages
      - Boolean
      - .. fa:: times
      - False
      - 
      - Update Distribution Packages
      - EC2LaunchOptions



CloudFormationInit
^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInit:

.. list-table:: :guilabel:`CloudFormationInit`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - config_sets
      - Container of CloudFormationConfigSets_ AIM schemas
      - .. fa:: check
      - 
      - 
      - CloudFormation Init configSets
      - CloudFormationInit
    * - configurations
      - Container of CloudFormationConfigurations_ AIM schemas
      - .. fa:: check
      - 
      - 
      - CloudFormation Init configurations
      - CloudFormationInit
    * - parameters
      - Dict
      - .. fa:: times
      - {}
      - 
      - Parameters
      - CloudFormationInit



CloudFormationConfigSets
^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigSets:

.. list-table:: :guilabel:`CloudFormationConfigSets` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



CloudFormationConfigurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigurations:

.. list-table:: :guilabel:`CloudFormationConfigurations` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



CodePipeBuildDeploy
--------------------


    Code Pipeline: Build and Deploy
    

.. _CodePipeBuildDeploy:

.. list-table:: :guilabel:`CodePipeBuildDeploy`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - alb_target_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ALB Target Group Reference
      - CodePipeBuildDeploy
    * - artifacts_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Artifacts S3 Bucket Reference
      - CodePipeBuildDeploy
    * - asg
      - TextReference
      - .. fa:: times
      - 
      - 
      - ASG Reference
      - CodePipeBuildDeploy
    * - auto_rollback_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Automatic rollback enabled
      - CodePipeBuildDeploy
    * - codebuild_compute_type
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Compute Type
      - CodePipeBuildDeploy
    * - codebuild_image
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Docker Image
      - CodePipeBuildDeploy
    * - codecommit_repository
      - TextReference
      - .. fa:: times
      - 
      - 
      - CodeCommit Respository
      - CodePipeBuildDeploy
    * - cross_account_support
      - Boolean
      - .. fa:: times
      - False
      - 
      - Cross Account Support
      - CodePipeBuildDeploy
    * - data_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Data Account Reference
      - CodePipeBuildDeploy
    * - deploy_config_type
      - String
      - .. fa:: times
      - HOST_COUNT
      - 
      - Deploy Config Type
      - CodePipeBuildDeploy
    * - deploy_config_value
      - Int
      - .. fa:: times
      - 0
      - 
      - Deploy Config Value
      - CodePipeBuildDeploy
    * - deploy_instance_role
      - TextReference
      - .. fa:: times
      - 
      - 
      - Deploy Instance Role Reference
      - CodePipeBuildDeploy
    * - deploy_style_option
      - String
      - .. fa:: times
      - WITH_TRAFFIC_CONTROL
      - 
      - Deploy Style Option
      - CodePipeBuildDeploy
    * - deployment_branch_name
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Branch Name
      - CodePipeBuildDeploy
    * - deployment_environment
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Environment
      - CodePipeBuildDeploy
    * - elb_name
      - String
      - .. fa:: times
      - 
      - 
      - ELB Name
      - CodePipeBuildDeploy
    * - manual_approval_enabled
      - Boolean
      - .. fa:: times
      - False
      - 
      - Manual approval enabled
      - CodePipeBuildDeploy
    * - manual_approval_notification_email
      - String
      - .. fa:: times
      - 
      - 
      - Manual approval notification email
      - CodePipeBuildDeploy
    * - timeout_mins
      - Int
      - .. fa:: times
      - 60
      - 
      - Timeout in Minutes
      - CodePipeBuildDeploy
    * - tools_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Tools Account Reference
      - CodePipeBuildDeploy



AWSCertificateManager
----------------------



.. _AWSCertificateManager:

.. list-table:: :guilabel:`AWSCertificateManager`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - domain_name
      - String
      - .. fa:: times
      - 
      - 
      - Domain Name
      - AWSCertificateManager
    * - external_resource
      - Boolean
      - .. fa:: times
      - False
      - 
      - Marks this resource as external to avoid creating and validating it.
      - AWSCertificateManager
    * - subject_alternative_names
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Subject alternative names
      - AWSCertificateManager


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
  however, the AIM Secrets Manager support allows you to use a ``secrets_password`` instead of the
  ``master_user_password`` field:

  .. code-block:: yaml

      type: RDSMysql
      secrets_password: aim.ref netenv.mynet.secrets_manager.app.grp.mysql

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
                  secret_string_template: '{"username": "admin"}'
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
    - aim.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: aim.ref netenv.mynet.network.vpc.segments.private
  primary_domain_name: database.example.internal
  primary_hosted_zone: aim.ref netenv.mynet.network.vpc.private_hosted_zone
  parameter_group: aim.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance




RDSOptionConfiguration
^^^^^^^^^^^^^^^^^^^^^^^


Option groups enable and configure features that are specific to a particular DB engine.
    

.. _RDSOptionConfiguration:

.. list-table:: :guilabel:`RDSOptionConfiguration`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - option_name
      - String
      - .. fa:: times
      - 
      - 
      - Option Name
      - RDSOptionConfiguration
    * - option_settings
      - List of NameValuePair_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of option name value pairs.
      - RDSOptionConfiguration
    * - option_version
      - String
      - .. fa:: times
      - 
      - 
      - Option Version
      - RDSOptionConfiguration
    * - port
      - String
      - .. fa:: times
      - 
      - 
      - Port
      - RDSOptionConfiguration



NameValuePair
^^^^^^^^^^^^^^

A Name/Value pair to use for RDS Option Group configuration

.. _NameValuePair:

.. list-table:: :guilabel:`NameValuePair`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
      - NameValuePair
    * - value
      - String
      - .. fa:: times
      - 
      - 
      - Value
      - NameValuePair



RDSMysql
^^^^^^^^^


The RDSMysql type extends the base RDS schema with a ``multi_az`` field. When you provision a Multi-AZ DB Instance,
Amazon RDS automatically creates a primary DB Instance and synchronously replicates the data to a standby instance
in a different Availability Zone (AZ).
    

.. _RDSMysql:

.. list-table:: :guilabel:`RDSMysql`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - allow_major_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Allow major version upgrades
      - RDS
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Automatic minor version upgrades
      - RDS
    * - backup_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Backup Preferred Window
      - RDS
    * - backup_retention_period
      - Int
      - .. fa:: times
      - 
      - 
      - Backup Retention Period in days
      - RDS
    * - cloudwatch_logs_exports
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of CloudWatch Logs Exports
      - RDS
    * - db_instance_type
      - String
      - .. fa:: times
      - 
      - 
      - RDS Instance Type
      - RDS
    * - db_snapshot_identifier
      - String
      - .. fa:: times
      - 
      - 
      - DB Snapshot Identifier to restore from
      - RDS
    * - deletion_protection
      - Boolean
      - .. fa:: times
      - False
      - 
      - Deletion Protection
      - RDS
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the RDS
      - RDS
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine
      - RDS
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine Version
      - RDS
    * - kms_key_id
      - TextReference
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
      - RDS
    * - license_model
      - String
      - .. fa:: times
      - 
      - 
      - License Model
      - RDS
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Maintenance Preferred Window
      - RDS
    * - master_user_password
      - String
      - .. fa:: times
      - 
      - 
      - Master User Password
      - RDS
    * - master_username
      - String
      - .. fa:: times
      - 
      - 
      - Master Username
      - RDS
    * - option_configurations
      - List of RDSOptionConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Option Configurations
      - RDS
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - RDS Parameter Group
      - RDS
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - DB Port
      - RDS
    * - primary_domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Domain Name
      - RDS
    * - primary_hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Hosted Zone
      - RDS
    * - publically_accessible
      - Boolean
      - .. fa:: times
      - 
      - 
      - Assign a Public IP address
      - RDS
    * - secrets_password
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secrets Manager password
      - RDS
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
      - RDS
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
      - RDS
    * - storage_encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
      - RDS
    * - storage_size_gb
      - Int
      - .. fa:: times
      - 
      - 
      - DB Storage Size in Gigabytes
      - RDS
    * - storage_type
      - String
      - .. fa:: times
      - 
      - 
      - DB Storage Type
      - RDS
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - multi_az
      - Boolean
      - .. fa:: times
      - False
      - 
      - Multiple Availability Zone deployment
      - RDSMysql



RDSAurora
^^^^^^^^^^


    RDS Aurora
    

.. _RDSAurora:

.. list-table:: :guilabel:`RDSAurora`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - allow_major_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Allow major version upgrades
      - RDS
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Automatic minor version upgrades
      - RDS
    * - backup_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Backup Preferred Window
      - RDS
    * - backup_retention_period
      - Int
      - .. fa:: times
      - 
      - 
      - Backup Retention Period in days
      - RDS
    * - cloudwatch_logs_exports
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of CloudWatch Logs Exports
      - RDS
    * - db_instance_type
      - String
      - .. fa:: times
      - 
      - 
      - RDS Instance Type
      - RDS
    * - db_snapshot_identifier
      - String
      - .. fa:: times
      - 
      - 
      - DB Snapshot Identifier to restore from
      - RDS
    * - deletion_protection
      - Boolean
      - .. fa:: times
      - False
      - 
      - Deletion Protection
      - RDS
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the RDS
      - RDS
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine
      - RDS
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine Version
      - RDS
    * - kms_key_id
      - TextReference
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
      - RDS
    * - license_model
      - String
      - .. fa:: times
      - 
      - 
      - License Model
      - RDS
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Maintenance Preferred Window
      - RDS
    * - master_user_password
      - String
      - .. fa:: times
      - 
      - 
      - Master User Password
      - RDS
    * - master_username
      - String
      - .. fa:: times
      - 
      - 
      - Master Username
      - RDS
    * - option_configurations
      - List of RDSOptionConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Option Configurations
      - RDS
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - RDS Parameter Group
      - RDS
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - DB Port
      - RDS
    * - primary_domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Domain Name
      - RDS
    * - primary_hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Hosted Zone
      - RDS
    * - publically_accessible
      - Boolean
      - .. fa:: times
      - 
      - 
      - Assign a Public IP address
      - RDS
    * - secrets_password
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secrets Manager password
      - RDS
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
      - RDS
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
      - RDS
    * - storage_encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
      - RDS
    * - storage_size_gb
      - Int
      - .. fa:: times
      - 
      - 
      - DB Storage Size in Gigabytes
      - RDS
    * - storage_type
      - String
      - .. fa:: times
      - 
      - 
      - DB Storage Type
      - RDS
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - secondary_domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secondary Domain Name
      - RDSAurora
    * - secondary_hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secondary Hosted Zone
      - RDSAurora



DBParameterGroup
-----------------


    AWS::RDS::DBParameterGroup
    

.. _DBParameterGroup:

.. list-table:: :guilabel:`DBParameterGroup`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
      - DBParameterGroup
    * - family
      - String
      - .. fa:: check
      - 
      - 
      - Database Family
      - DBParameterGroup
    * - parameters
      - Container of DBParameters_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Database Parameter set
      - DBParameterGroup



DBParameters
^^^^^^^^^^^^^

A dict of database parameters



EC2
----


    EC2 Instance
    

.. _EC2:

.. list-table:: :guilabel:`EC2`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - associate_public_ip_address
      - Boolean
      - .. fa:: times
      - False
      - 
      - Associate Public IP Address
      - EC2
    * - disable_api_termination
      - Boolean
      - .. fa:: times
      - False
      - 
      - Disable API Termination
      - EC2
    * - instance_ami
      - String
      - .. fa:: times
      - 
      - 
      - Instance AMI
      - EC2
    * - instance_key_pair
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance key pair reference
      - EC2
    * - instance_type
      - String
      - .. fa:: times
      - 
      - 
      - Instance type
      - EC2
    * - private_ip_address
      - String
      - .. fa:: times
      - 
      - 
      - Private IP Address
      - EC2
    * - root_volume_size_gb
      - Int
      - .. fa:: times
      - 8
      - 
      - Root volume size GB
      - EC2
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security groups
      - EC2
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
      - EC2
    * - user_data_script
      - String
      - .. fa:: times
      - 
      - 
      - User data script
      - EC2



Lambda
-------


Lambda Functions allow you to run code without provisioning servers and only
pay for the compute time when the code is running.

For the code that the Lambda function will run, use the ``code:`` block and specify
``s3_bucket`` and ``s3_key`` to deploy the code from an S3 Bucket or use ``zipfile`` to read a local file from disk.

.. sidebar:: Prescribed Automation

    ``sdb_cache``: Create a SimpleDB Domain and IAM Policy that grants full access to that domain. Will
    also make the domain available to the Lambda function as an environment variable named ``SDB_CACHE_DOMAIN``.

    ``sns_topics``: Subscribes the Lambda to SNS Topics. For each AIM reference to an SNS Topic,
    AIM will create an SNS Topic Subscription so that the Lambda function will recieve all messages sent to that SNS Topic.
    It will also create a Lambda Permission granting that SNS Topic the ability to publish to the Lambda.

    **S3 Bucket Notification permission** AIM will check all resources in the Application for any S3 Buckets configured
    to notify this Lambda. Lambda Permissions will be created to allow those S3 Buckets to invoke the Lambda.

    **Events Rule permission** AIM will check all resources in the Application for CloudWatch Events Rule that are configured
    to notify this Lambda and create a Lambda permission to allow that Event Rule to invoke the Lambda.

.. code-block:: yaml
    :caption: Lambda function resource YAML

    type: Lambda
    enabled: true
    order: 1
    title: 'My Lambda Application'
    description: 'Checks the Widgets Service and applies updates to a Route 53 Record Set.'
    code:
        s3_bucket: my-bucket-name
        s3_key: 'myapp-1.0.zip'
    environment:
        variables:
        - key: 'VAR_ONE'
          value: 'hey now!'
        - key: 'VAR_TWO'
          value: 'Hank Kingsley'
    iam_role:
        enabled: true
        policies:
          - name: DNSRecordSet
            statement:
              - effect: Allow
                action:
                  - route53:ChangeResourceRecordSets
                resource:
                  - 'arn:aws:route53:::hostedzone/AJKDU9834DUY934'
    handler: 'myapp.lambda_handler'
    memory_size: 128
    runtime: 'python3.7'
    timeout: 900
    sns_topics:
      - aim.ref netenv.app.applications.app.groups.web.resources.snstopic
    vpc_config:
        segments:
          - aim.ref netenv.app.network.vpc.segments.public
        security_groups:
          - aim.ref netenv.app.network.vpc.security_groups.app.function



.. _Lambda:

.. list-table:: :guilabel:`Lambda`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - code
      - LambdaFunctionCode_ AIM schema
      - .. fa:: check
      - 
      - 
      - The function deployment package.
      - Lambda
    * - description
      - String
      - .. fa:: check
      - 
      - 
      - A description of the function.
      - Lambda
    * - environment
      - Container of LambdaEnvironment_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda Function Environment
      - Lambda
    * - handler
      - String
      - .. fa:: check
      - 
      - 
      - Function Handler
      - Lambda
    * - iam_role
      - Role_ AIM schema
      - .. fa:: check
      - 
      - 
      - The IAM Role this Lambda will execute as.
      - Lambda
    * - layers
      - List of Strings
      - .. fa:: check
      - 
      - Up to 5 Layer ARNs
      - Layers
      - Lambda
    * - memory_size
      - Int
      - .. fa:: times
      - 128
      - 
      - Function memory size (MB)
      - Lambda
    * - reserved_concurrent_executions
      - Int
      - .. fa:: times
      - 0
      - 
      - Reserved Concurrent Executions
      - Lambda
    * - runtime
      - String
      - .. fa:: check
      - python3.7
      - 
      - Runtime environment
      - Lambda
    * - sdb_cache
      - Boolean
      - .. fa:: times
      - False
      - 
      - SDB Cache Domain
      - Lambda
    * - sns_topics
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SNS Topic AIM References
      - Lambda
    * - timeout
      - Int
      - .. fa:: times
      - 
      - Must be between 0 and 900 seconds.
      - Max function execution time in seconds.
      - Lambda
    * - vpc_config
      - LambdaVpcConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - Vpc Configuration
      - Lambda



LambdaFunctionCode
^^^^^^^^^^^^^^^^^^^

The deployment package for a Lambda function.

.. _LambdaFunctionCode:

.. list-table:: :guilabel:`LambdaFunctionCode`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - s3_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - An Amazon S3 bucket in the same AWS Region as your function
      - LambdaFunctionCode
    * - s3_key
      - String
      - .. fa:: times
      - 
      - 
      - The Amazon S3 key of the deployment package.
      - LambdaFunctionCode
    * - zipfile
      - StringFileReference
      - .. fa:: times
      - 
      - Maximum of 4096 characters.
      - The function as an external file.
      - LambdaFunctionCode



LambdaEnvironment
^^^^^^^^^^^^^^^^^^


    Lambda Environment
    

.. _LambdaEnvironment:

.. list-table:: :guilabel:`LambdaEnvironment` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - variables
      - List of LambdaVariable_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda Function Variables
      - LambdaEnvironment



LambdaVpcConfig
^^^^^^^^^^^^^^^^


    Lambda Environment
    

.. _LambdaVpcConfig:

.. list-table:: :guilabel:`LambdaVpcConfig`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
      - LambdaVpcConfig
    * - segments
      - List of Strings
      - .. fa:: times
      - 
      - 
      - VPC Segments to attach the function
      - LambdaVpcConfig



LambdaVariable
^^^^^^^^^^^^^^^


    Lambda Environment Variable
    

.. _LambdaVariable:

.. list-table:: :guilabel:`LambdaVariable`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - key
      - String
      - .. fa:: check
      - 
      - 
      - Variable Name
      - LambdaVariable
    * - value
      - TextReference
      - .. fa:: check
      - 
      - 
      - Variable Value
      - LambdaVariable



ManagedPolicy
--------------


    IAM Managed Policy
    

.. _ManagedPolicy:

.. list-table:: :guilabel:`ManagedPolicy` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - path
      - String
      - .. fa:: times
      - /
      - 
      - Path
      - ManagedPolicy
    * - roles
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Role Names
      - ManagedPolicy
    * - statement
      - List of Statement_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Statements
      - ManagedPolicy
    * - users
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of IAM Users
      - ManagedPolicy



S3Bucket
---------


    S3 Bucket : A template describing an S3 Bbucket
    

.. _S3Bucket:

.. list-table:: :guilabel:`S3Bucket`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Account Reference
      - S3Bucket
    * - bucket_name
      - String
      - .. fa:: check
      - bucket
      - A short unique name to assign the bucket.
      - Bucket Name
      - S3Bucket
    * - cloudfront_origin
      - Boolean
      - .. fa:: times
      - False
      - 
      - Creates and listens for a CloudFront Access Origin Identity
      - S3Bucket
    * - deletion_policy
      - String
      - .. fa:: times
      - delete
      - 
      - Bucket Deletion Policy
      - S3Bucket
    * - external_resource
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether the S3 Bucket already exists or not
      - S3Bucket
    * - notifications
      - S3NotificationConfiguration_ AIM schema
      - .. fa:: times
      - 
      - 
      - Notification configuration
      - S3Bucket
    * - policy
      - List of S3BucketPolicy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of S3 Bucket Policies
      - S3Bucket
    * - region
      - String
      - .. fa:: times
      - 
      - 
      - Bucket region
      - S3Bucket
    * - versioning
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable Versioning on the bucket.
      - S3Bucket



S3BucketPolicy
^^^^^^^^^^^^^^^


    S3 Bucket Policy
    

.. _S3BucketPolicy:

.. list-table:: :guilabel:`S3BucketPolicy`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - action
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of Actions
      - S3BucketPolicy
    * - aws
      - List of Strings
      - .. fa:: times
      - 
      - Either this field or the principal field must be set.
      - List of AWS Principles.
      - S3BucketPolicy
    * - condition
      - Dict
      - .. fa:: times
      - {}
      - Each Key is the Condition name and the Value must be a dictionary of request filters. e.g. { "StringEquals" : { "aws:username" : "johndoe" }}
      - Condition
      - S3BucketPolicy
    * - effect
      - String
      - .. fa:: check
      - Deny
      - Must be one of: 'Allow', 'Deny'
      - Effect
      - S3BucketPolicy
    * - principal
      - Dict
      - .. fa:: times
      - {}
      - Either this field or the aws field must be set. Key should be one of: AWS, Federated, Service or CanonicalUser. Value can be either a String or a List.
      - Prinicpals
      - S3BucketPolicy
    * - resource_suffix
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of AWS Resources Suffixes
      - S3BucketPolicy



S3LambdaConfiguration
^^^^^^^^^^^^^^^^^^^^^^



.. _S3LambdaConfiguration:

.. list-table:: :guilabel:`S3LambdaConfiguration`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - event
      - String
      - .. fa:: times
      - 
      - Must be a supported event type: https://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
      - S3 bucket event for which to invoke the AWS Lambda function
      - S3LambdaConfiguration
    * - function
      - TextReference
      - .. fa:: times
      - 
      - 
      - Reference to a Lambda
      - S3LambdaConfiguration



S3NotificationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3NotificationConfiguration:

.. list-table:: :guilabel:`S3NotificationConfiguration`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - lambdas
      - List of S3LambdaConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda configurations
      - S3NotificationConfiguration



SNSTopic
---------


Simple Notification Service (SNS) Topic resource.

.. sidebar:: Prescribed Automation

    ``cross_account_access``: Creates an SNS Topic Policy which will grant all of the AWS Accounts in this
    AIM Project access to the ``sns.Publish`` permission for this SNS Topic.

.. code-block:: yaml
    :caption: Example SNSTopic resource YAML

    type: SNSTopic
    order: 1
    enabled: true
    display_name: "Waterbear Cloud AWS"
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



.. _SNSTopic:

.. list-table:: :guilabel:`SNSTopic`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - cross_account_access
      - Boolean
      - .. fa:: times
      - False
      - 
      - Cross-account access from all other accounts in this project.
      - SNSTopic
    * - display_name
      - String
      - .. fa:: times
      - 
      - 
      - Display name for SMS Messages
      - SNSTopic
    * - subscriptions
      - List of SNSTopicSubscription_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of SNS Topic Subscriptions
      - SNSTopic



SNSTopicSubscription
^^^^^^^^^^^^^^^^^^^^^



.. _SNSTopicSubscription:

.. list-table:: :guilabel:`SNSTopicSubscription`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - endpoint
      - TextReference
      - .. fa:: times
      - 
      - 
      - SNS Topic Endpoint
      - SNSTopicSubscription
    * - protocol
      - String
      - .. fa:: times
      - email
      - Must be a valid SNS Topic subscription protocol: 'http', 'https', 'email', 'email-json', 'sms', 'sqs', 'application', 'lambda'.
      - Notification protocol
      - SNSTopicSubscription



CloudFront
-----------


    CloudFront CDN Configuration
    

.. _CloudFront:

.. list-table:: :guilabel:`CloudFront`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - cache_behaviors
      - List of CloudFrontCacheBehavior_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of Cache Behaviors
      - CloudFront
    * - custom_error_responses
      - List of CloudFrontCustomErrorResponse_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of Custom Error Responses
      - CloudFront
    * - default_cache_behavior
      - CloudFrontDefaultCacheBehavior_ AIM schema
      - .. fa:: times
      - 
      - 
      - Default Cache Behavior
      - CloudFront
    * - default_root_object
      - String
      - .. fa:: times
      - index.html
      - 
      - The default path to load from the origin.
      - CloudFront
    * - domain_aliases
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the Distribution
      - CloudFront
    * - factory
      - Container of CloudFrontFactory_ AIM schemas
      - .. fa:: times
      - 
      - 
      - CloudFront Factory
      - CloudFront
    * - origins
      - Container of CloudFrontOrigin_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Map of Origins
      - CloudFront
    * - price_class
      - String
      - .. fa:: times
      - All
      - 
      - Price Class
      - CloudFront
    * - viewer_certificate
      - CloudFrontViewerCertificate_ AIM schema
      - .. fa:: times
      - 
      - 
      - Viewer Certificate
      - CloudFront
    * - webacl_id
      - String
      - .. fa:: times
      - 
      - 
      - WAF WebACLId
      - CloudFront



CloudFrontDefaultCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontDefaultCacheBehavior:

.. list-table:: :guilabel:`CloudFrontDefaultCacheBehavior`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - allowed_methods
      - List of Strings
      - .. fa:: times
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
      - 
      - List of Allowed HTTP Methods
      - CloudFrontDefaultCacheBehavior
    * - cached_methods
      - List of Strings
      - .. fa:: times
      - ['GET', 'HEAD', 'OPTIONS']
      - 
      - List of HTTP Methods to cache
      - CloudFrontDefaultCacheBehavior
    * - compress
      - Boolean
      - .. fa:: times
      - False
      - 
      - Compress certain files automatically
      - CloudFrontDefaultCacheBehavior
    * - default_ttl
      - Int
      - .. fa:: check
      - 0
      - 
      - Default TTTL
      - CloudFrontDefaultCacheBehavior
    * - forwarded_values
      - CloudFrontForwardedValues_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forwarded Values
      - CloudFrontDefaultCacheBehavior
    * - target_origin
      - TextReference
      - .. fa:: check
      - 
      - 
      - Target Origin
      - CloudFrontDefaultCacheBehavior
    * - viewer_protocol_policy
      - String
      - .. fa:: check
      - redirect-to-https
      - 
      - Viewer Protocol Policy
      - CloudFrontDefaultCacheBehavior



CloudFrontCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCacheBehavior:

.. list-table:: :guilabel:`CloudFrontCacheBehavior`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - allowed_methods
      - List of Strings
      - .. fa:: times
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
      - 
      - List of Allowed HTTP Methods
      - CloudFrontDefaultCacheBehavior
    * - cached_methods
      - List of Strings
      - .. fa:: times
      - ['GET', 'HEAD', 'OPTIONS']
      - 
      - List of HTTP Methods to cache
      - CloudFrontDefaultCacheBehavior
    * - compress
      - Boolean
      - .. fa:: times
      - False
      - 
      - Compress certain files automatically
      - CloudFrontDefaultCacheBehavior
    * - default_ttl
      - Int
      - .. fa:: check
      - 0
      - 
      - Default TTTL
      - CloudFrontDefaultCacheBehavior
    * - forwarded_values
      - CloudFrontForwardedValues_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forwarded Values
      - CloudFrontDefaultCacheBehavior
    * - target_origin
      - TextReference
      - .. fa:: check
      - 
      - 
      - Target Origin
      - CloudFrontDefaultCacheBehavior
    * - viewer_protocol_policy
      - String
      - .. fa:: check
      - redirect-to-https
      - 
      - Viewer Protocol Policy
      - CloudFrontDefaultCacheBehavior
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - path_pattern
      - String
      - .. fa:: check
      - 
      - 
      - Path Pattern
      - CloudFrontCacheBehavior



CloudFrontFactory
^^^^^^^^^^^^^^^^^^


    CloudFront Factory
    

.. _CloudFrontFactory:

.. list-table:: :guilabel:`CloudFrontFactory`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - domain_aliases
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the Distribution
      - CloudFrontFactory
    * - viewer_certificate
      - CloudFrontViewerCertificate_ AIM schema
      - .. fa:: times
      - 
      - 
      - Viewer Certificate
      - CloudFrontFactory



CloudFrontOrigin
^^^^^^^^^^^^^^^^^


    CloudFront Origin Configuration
    

.. _CloudFrontOrigin:

.. list-table:: :guilabel:`CloudFrontOrigin`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - custom_origin_config
      - CloudFrontCustomOriginConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - Custom Origin Configuration
      - CloudFrontOrigin
    * - domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Origin Resource Reference
      - CloudFrontOrigin
    * - s3_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Origin S3 Bucket Reference
      - CloudFrontOrigin



CloudFrontCustomOriginConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomOriginConfig:

.. list-table:: :guilabel:`CloudFrontCustomOriginConfig`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - http_port
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Port
      - CloudFrontCustomOriginConfig
    * - https_port
      - Int
      - .. fa:: times
      - 
      - 
      - HTTPS Port
      - CloudFrontCustomOriginConfig
    * - keepalive_timeout
      - Int
      - .. fa:: times
      - 5
      - 
      - HTTP Keepalive Timeout
      - CloudFrontCustomOriginConfig
    * - protocol_policy
      - String
      - .. fa:: times
      - 
      - 
      - Protocol Policy
      - CloudFrontCustomOriginConfig
    * - read_timeout
      - Int
      - .. fa:: times
      - 30
      - 
      - Read timeout
      - CloudFrontCustomOriginConfig
    * - ssl_protocols
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SSL Protocols
      - CloudFrontCustomOriginConfig



CloudFrontCustomErrorResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomErrorResponse:

.. list-table:: :guilabel:`CloudFrontCustomErrorResponse`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - error_caching_min_ttl
      - Int
      - .. fa:: times
      - 
      - 
      - Error Caching Min TTL
      - CloudFrontCustomErrorResponse
    * - error_code
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Error Code
      - CloudFrontCustomErrorResponse
    * - response_code
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Response Code
      - CloudFrontCustomErrorResponse
    * - response_page_path
      - String
      - .. fa:: times
      - 
      - 
      - Response Page Path
      - CloudFrontCustomErrorResponse



CloudFrontViewerCertificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontViewerCertificate:

.. list-table:: :guilabel:`CloudFrontViewerCertificate`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - certificate
      - TextReference
      - .. fa:: times
      - 
      - 
      - Certificate Reference
      - CloudFrontViewerCertificate
    * - minimum_protocol_version
      - String
      - .. fa:: times
      - TLSv1.1_2016
      - 
      - Minimum SSL Protocol Version
      - CloudFrontViewerCertificate
    * - ssl_supported_method
      - String
      - .. fa:: times
      - sni-only
      - 
      - SSL Supported Method
      - CloudFrontViewerCertificate



CloudFrontForwardedValues
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontForwardedValues:

.. list-table:: :guilabel:`CloudFrontForwardedValues`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - cookies
      - CloudFrontCookies_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forward Cookies
      - CloudFrontForwardedValues
    * - headers
      - List of Strings
      - .. fa:: times
      - ['*']
      - 
      - Forward Headers
      - CloudFrontForwardedValues
    * - query_string
      - Boolean
      - .. fa:: times
      - True
      - 
      - Forward Query Strings
      - CloudFrontForwardedValues



CloudFrontCookies
^^^^^^^^^^^^^^^^^^



.. _CloudFrontCookies:

.. list-table:: :guilabel:`CloudFrontCookies`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - forward
      - String
      - .. fa:: times
      - all
      - 
      - Cookies Forward Action
      - CloudFrontCookies
    * - whitelisted_names
      - List of Strings
      - .. fa:: times
      - 
      - 
      - White Listed Names
      - CloudFrontCookies



ElastiCacheRedis
-----------------


    Redis ElastiCache Interface
    

.. _ElastiCacheRedis:

.. list-table:: :guilabel:`ElastiCacheRedis`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - at_rest_encryption
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable encryption at rest
      - ElastiCache
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable automatic minor version upgrades
      - ElastiCache
    * - automatic_failover_enabled
      - Boolean
      - .. fa:: times
      - 
      - 
      - Specifies whether a read-only replica is automatically promoted to read/write primary if the existing primary fails
      - ElastiCache
    * - az_mode
      - String
      - .. fa:: times
      - 
      - 
      - AZ mode
      - ElastiCache
    * - cache_clusters
      - Int
      - .. fa:: times
      - 
      - 
      - Number of Cache Clusters
      - ElastiCache
    * - cache_node_type
      - String
      - .. fa:: times
      - 
      - 
      - Cache Node Instance type
      - ElastiCache
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Replication Description
      - ElastiCache
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - ElastiCache Engine
      - ElastiCache
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - ElastiCache Engine Version
      - ElastiCache
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Preferred maintenance window
      - ElastiCache
    * - number_of_read_replicas
      - Int
      - .. fa:: times
      - 
      - 
      - Number of read replicas
      - ElastiCache
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - Parameter Group name or reference
      - ElastiCache
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
      - ElastiCache
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Security Groups
      - ElastiCache
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
      - ElastiCache
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
      - Monitorable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - cache_parameter_group_family
      - String
      - .. fa:: times
      - 
      - 
      - Cache Parameter Group Family
      - ElastiCacheRedis
    * - snapshot_retention_limit_days
      - Int
      - .. fa:: times
      - 
      - 
      - Snapshot Retention Limit in Days
      - ElastiCacheRedis
    * - snapshot_window
      - String
      - .. fa:: times
      - 
      - 
      - The daily time range (in UTC) during which ElastiCache begins taking a daily snapshot of your node group (shard).
      - ElastiCacheRedis



DeploymentPipeline
-------------------


    Code Pipeline: Build and Deploy
    

.. _DeploymentPipeline:

.. list-table:: :guilabel:`DeploymentPipeline`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - build
      - Container of DeploymentPipelineBuildStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Build Stage
      - DeploymentPipeline
    * - configuration
      - DeploymentPipelineConfiguration_ AIM schema
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline General Configuration
      - DeploymentPipeline
    * - deploy
      - Container of DeploymentPipelineDeployStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Deploy Stage
      - DeploymentPipeline
    * - source
      - Container of DeploymentPipelineSourceStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Source Stage
      - DeploymentPipeline



DeploymentPipelineSourceStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline source stage actions
    

.. _DeploymentPipelineSourceStage:

.. list-table:: :guilabel:`DeploymentPipelineSourceStage` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



DeploymentPipelineDeployStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline deploy stage actions
    

.. _DeploymentPipelineDeployStage:

.. list-table:: :guilabel:`DeploymentPipelineDeployStage` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



DeploymentPipelineBuildStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline build stage actions
    

.. _DeploymentPipelineBuildStage:

.. list-table:: :guilabel:`DeploymentPipelineBuildStage` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



DeploymentPipelineDeployCodeDeploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeDeploy DeploymentPipeline Deploy Stage
    

.. _DeploymentPipelineDeployCodeDeploy:

.. list-table:: :guilabel:`DeploymentPipelineDeployCodeDeploy` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - alb_target_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ALB Target Group Reference
      - DeploymentPipelineDeployCodeDeploy
    * - auto_rollback_enabled
      - Boolean
      - .. fa:: check
      - True
      - 
      - Automatic rollback enabled
      - DeploymentPipelineDeployCodeDeploy
    * - auto_scaling_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ASG Reference
      - DeploymentPipelineDeployCodeDeploy
    * - deploy_instance_role
      - TextReference
      - .. fa:: times
      - 
      - 
      - Deploy Instance Role Reference
      - DeploymentPipelineDeployCodeDeploy
    * - deploy_style_option
      - String
      - .. fa:: times
      - WITH_TRAFFIC_CONTROL
      - 
      - Deploy Style Option
      - DeploymentPipelineDeployCodeDeploy
    * - elb_name
      - String
      - .. fa:: times
      - 
      - 
      - ELB Name
      - DeploymentPipelineDeployCodeDeploy
    * - minimum_healthy_hosts
      - CodeDeployMinimumHealthyHosts_ AIM schema
      - .. fa:: times
      - 
      - 
      - The minimum number of healthy instances that should be available at any time during the deployment.
      - DeploymentPipelineDeployCodeDeploy



CodeDeployMinimumHealthyHosts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeDeploy Minimum Healthy Hosts
    

.. _CodeDeployMinimumHealthyHosts:

.. list-table:: :guilabel:`CodeDeployMinimumHealthyHosts`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - HOST_COUNT
      - 
      - Deploy Config Type
      - CodeDeployMinimumHealthyHosts
    * - value
      - Int
      - .. fa:: times
      - 0
      - 
      - Deploy Config Value
      - CodeDeployMinimumHealthyHosts



DeploymentPipelineManualApproval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    ManualApproval DeploymentPipeline
    

.. _DeploymentPipelineManualApproval:

.. list-table:: :guilabel:`DeploymentPipelineManualApproval` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - manual_approval_notification_email
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Manual Approval Notification Email List
      - DeploymentPipelineManualApproval



DeploymentPipelineDeployS3
^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Amazon S3 Deployment Provider
    

.. _DeploymentPipelineDeployS3:

.. list-table:: :guilabel:`DeploymentPipelineDeployS3` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - S3 Bucket Reference
      - DeploymentPipelineDeployS3
    * - extract
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether the deployment artifact will be unarchived.
      - DeploymentPipelineDeployS3
    * - object_key
      - String
      - .. fa:: times
      - 
      - 
      - S3 object key to store the deployment artifact as.
      - DeploymentPipelineDeployS3



DeploymentPipelineBuildCodeBuild
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeBuild DeploymentPipeline Build Stage
    

.. _DeploymentPipelineBuildCodeBuild:

.. list-table:: :guilabel:`DeploymentPipelineBuildCodeBuild` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - codebuild_compute_type
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Compute Type
      - DeploymentPipelineBuildCodeBuild
    * - codebuild_image
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Docker Image
      - DeploymentPipelineBuildCodeBuild
    * - deployment_environment
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Environment
      - DeploymentPipelineBuildCodeBuild
    * - role_policies
      - List of Policy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Project IAM Role Policies
      - DeploymentPipelineBuildCodeBuild
    * - timeout_mins
      - Int
      - .. fa:: times
      - 60
      - 
      - Timeout in Minutes
      - DeploymentPipelineBuildCodeBuild



DeploymentPipelineSourceCodeCommit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeCommit DeploymentPipeline Source Stage
    

.. _DeploymentPipelineSourceCodeCommit:

.. list-table:: :guilabel:`DeploymentPipelineSourceCodeCommit` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - codecommit_repository
      - TextReference
      - .. fa:: times
      - 
      - 
      - CodeCommit Respository
      - DeploymentPipelineSourceCodeCommit
    * - deployment_branch_name
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Branch Name
      - DeploymentPipelineSourceCodeCommit



DeploymentPipelineStageAction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Deployment Pipeline Source Stage
    

.. _DeploymentPipelineStageAction:

.. list-table:: :guilabel:`DeploymentPipelineStageAction` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
      - DeploymentPipelineStageAction
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage
      - DeploymentPipelineStageAction



DeploymentPipelineConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Deployment Pipeline General Configuration
    

.. _DeploymentPipelineConfiguration:

.. list-table:: :guilabel:`DeploymentPipelineConfiguration`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - account
      - TextReference
      - .. fa:: times
      - 
      - 
      - The account where Pipeline tools will be provisioned.
      - DeploymentPipelineConfiguration
    * - artifacts_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Artifacts S3 Bucket Reference
      - DeploymentPipelineConfiguration



EFS
----


    Elastic File System Resource
    

.. _EFS:

.. list-table:: :guilabel:`EFS`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - encrypted
      - Boolean
      - .. fa:: check
      - False
      - 
      - Encryption at Rest
      - EFS
    * - security_groups
      - List of Strings
      - .. fa:: check
      - 
      - 
      - Security groups
      - EFS
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
      - EFS



EIP
----


    Elastic IP
    

.. _EIP:

.. list-table:: :guilabel:`EIP`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the EIP
      - EIP



Route53HealthCheck
-------------------

Route53 Health Check

.. _Route53HealthCheck:

.. list-table:: :guilabel:`Route53HealthCheck`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - failure_threshold
      - Int
      - .. fa:: times
      - 3
      - 
      - Number of consecutive health checks that an endpoint must pass or fail for Amazon Route 53 to change the current status of the endpoint from unhealthy to healthy or vice versa.
      - Route53HealthCheck
    * - health_check_type
      - String
      - .. fa:: check
      - 
      - Must be one of HTTP, HTTPS or TCP
      - Health Check Type
      - Route53HealthCheck
    * - health_checker_regions
      - List of Strings
      - .. fa:: times
      - 
      - List of AWS Region names (e.g. us-west-2) from which to make health checks.
      - Health checker regions
      - Route53HealthCheck
    * - latency_graphs
      - Boolean
      - .. fa:: times
      - False
      - 
      - Measure latency and display CloudWatch graph in the AWS Console
      - Route53HealthCheck
    * - load_balancer
      - TextReference
      - .. fa:: times
      - 
      - 
      - Load Balancer Endpoint
      - Route53HealthCheck
    * - match_string
      - String
      - .. fa:: times
      - 
      - 
      - String to match in the first 5120 bytes of the response
      - Route53HealthCheck
    * - port
      - Int
      - .. fa:: times
      - 80
      - 
      - Port
      - Route53HealthCheck
    * - request_interval_fast
      - Boolean
      - .. fa:: times
      - False
      - 
      - Fast request interval will only wait 10 seconds between each health check response instead of the standard 30
      - Route53HealthCheck
    * - resource_path
      - String
      - .. fa:: times
      - /
      - String such as '/health.html'. Path should return a 2xx or 3xx. Query string parameters are allowed: '/search?query=health'
      - Resource Path
      - Route53HealthCheck



EventsRule
-----------


    Events Rule
    

.. _EventsRule:

.. list-table:: :guilabel:`EventsRule`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
      - EventsRule
    * - schedule_expression
      - String
      - .. fa:: check
      - 
      - 
      - Schedule Expression
      - EventsRule
    * - targets
      - List of Strings
      - .. fa:: check
      - 
      - 
      - The AWS Resources that are invoked when the Rule is triggered.
      - EventsRule



EBS
----


    Elastic Block Store Volume
    

.. _EBS:

.. list-table:: :guilabel:`EBS`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
      - DNSEnablable
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
      - Resource
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
      - Resource
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
      - Type
    * - availability_zone
      - Int
      - .. fa:: check
      - 
      - 
      - Availability Zone to create Volume in.
      - EBS
    * - size_gib
      - Int
      - .. fa:: check
      - 10
      - 
      - Volume Size in GiB
      - EBS
    * - volume_type
      - String
      - .. fa:: times
      - gp2
      - Must be one of: gp2 | io1 | sc1 | st1 | standard
      - Volume Type
      - EBS



Secrets
=======


SecretsManager
---------------

Secrets Manager

.. _SecretsManager:

.. list-table:: :guilabel:`SecretsManager` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title


Global Resources
================

IAM
---

The ``Resources/IAM.yaml`` file contains IAM Users. Each user account can be given
different levels of access a set of AWS accounts.


IAMResource
------------


IAM Resource contains IAM Users who can login and have different levels of access to the AWS Console and API.
    

.. _IAMResource:

.. list-table:: :guilabel:`IAMResource`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - users
      - Container of IAMUser_ AIM schemas
      - .. fa:: times
      - 
      - 
      - IAM Users
      - IAMResource



IAMUser
^^^^^^^^


    IAM User
    

.. _IAMUser:

.. list-table:: :guilabel:`IAMUser`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - account
      - TextReference
      - .. fa:: check
      - 
      - 
      - AIM account reference to install this user
      - IAMUser
    * - account_whitelist
      - CommaList
      - .. fa:: times
      - 
      - 
      - Comma separated list of AIM AWS account names this user has access to
      - IAMUser
    * - console_access_enabled
      - Boolean
      - .. fa:: check
      - 
      - 
      - Console Access Boolean
      - IAMUser
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - IAM User Description
      - IAMUser
    * - permissions
      - Container of IAMUserPermissions_ AIM schemas
      - .. fa:: times
      - 
      - 
      - AIM IAM User Permissions
      - IAMUser
    * - programmatic_access
      - IAMUserProgrammaticAccess_ AIM schema
      - .. fa:: times
      - 
      - 
      - Programmatic Access
      - IAMUser
    * - username
      - String
      - .. fa:: times
      - 
      - 
      - IAM Username
      - IAMUser



IAMUserProgrammaticAccess
^^^^^^^^^^^^^^^^^^^^^^^^^^


    IAM User Programmatic Access Configuration
    

.. _IAMUserProgrammaticAccess:

.. list-table:: :guilabel:`IAMUserProgrammaticAccess`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - access_key_1_version
      - Int
      - .. fa:: times
      - 0
      - 
      - Access key version id
      - IAMUserProgrammaticAccess
    * - access_key_2_version
      - Int
      - .. fa:: times
      - 0
      - 
      - Access key version id
      - IAMUserProgrammaticAccess



IAMUserPermissions
^^^^^^^^^^^^^^^^^^^


    Group of IAM User Permissions
    

.. _IAMUserPermissions:

.. list-table:: :guilabel:`IAMUserPermissions` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



Role
-----



.. _Role:

.. list-table:: :guilabel:`Role`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - assume_role_policy
      - AssumeRolePolicy_ AIM schema
      - .. fa:: times
      - 
      - 
      - Assume role policy
      - Role
    * - global_role_name
      - Boolean
      - .. fa:: times
      - False
      - 
      - Role name is globally unique and will not be hashed
      - Role
    * - instance_profile
      - Boolean
      - .. fa:: times
      - False
      - 
      - Instance profile
      - Role
    * - managed_policy_arns
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Managed policy ARNs
      - Role
    * - max_session_duration
      - Int
      - .. fa:: times
      - 3600
      - The maximum session duration (in seconds)
      - Maximum session duration
      - Role
    * - path
      - String
      - .. fa:: times
      - /
      - 
      - Path
      - Role
    * - permissions_boundary
      - String
      - .. fa:: times
      - 
      - Must be valid ARN
      - Permissions boundary ARN
      - Role
    * - policies
      - List of Policy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Policies
      - Role
    * - role_name
      - String
      - .. fa:: times
      - 
      - 
      - Role name
      - Role



AssumeRolePolicy
^^^^^^^^^^^^^^^^^



.. _AssumeRolePolicy:

.. list-table:: :guilabel:`AssumeRolePolicy`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - aws
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of AWS Principles
      - AssumeRolePolicy
    * - effect
      - String
      - .. fa:: times
      - 
      - 
      - Effect
      - AssumeRolePolicy
    * - service
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Service
      - AssumeRolePolicy



Policy
^^^^^^^



.. _Policy:

.. list-table:: :guilabel:`Policy`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Policy name
      - Policy
    * - statement
      - List of Statement_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Statements
      - Policy



Statement
^^^^^^^^^^



.. _Statement:

.. list-table:: :guilabel:`Statement`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - action
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Action(s)
      - Statement
    * - effect
      - String
      - .. fa:: times
      - 
      - Must be one of: 'Allow', 'Deny'
      - Effect
      - Statement
    * - resource
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Resrource(s)
      - Statement



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


Alarm
------


    An Alarm
    

.. _Alarm:

.. list-table:: :guilabel:`Alarm`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
      - Deployable
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
      - Notifiable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - classification
      - String
      - .. fa:: check
      - unset
      - Must be one of: 'performance', 'security' or 'health'
      - Classification
      - Alarm
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
      - Alarm
    * - notification_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of notificationn groups the alarm is subscribed to.
      - Alarm
    * - runbook_url
      - String
      - .. fa:: times
      - 
      - 
      - Runbook URL
      - Alarm
    * - severity
      - String
      - .. fa:: times
      - low
      - Must be one of: 'low', 'critical'
      - Severity
      - Alarm



AlarmSet
---------


    A collection of Alarms
    

.. _AlarmSet:

.. list-table:: :guilabel:`AlarmSet` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
      - Notifiable
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - resource_type
      - String
      - .. fa:: times
      - 
      - Must be a valid AWS resource type
      - Resource type
      - AlarmSet



AlarmSets
----------


    A collection of AlarmSets
    

.. _AlarmSets:

.. list-table:: :guilabel:`AlarmSets` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



Dimension
----------


    A dimension of a metric
    

.. _Dimension:

.. list-table:: :guilabel:`Dimension`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Dimension name
      - Dimension
    * - value
      - TextReference
      - .. fa:: times
      - 
      - 
      - Value to look-up dimension
      - Dimension



CloudWatchLogSource
--------------------


    Log source for a CloudWatch agent
    

.. _CloudWatchLogSource:

.. list-table:: :guilabel:`CloudWatchLogSource`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - expire_events_after_days
      - String
      - .. fa:: times
      - 
      - 
      - Expire Events After. Retention period of logs in this group
      - CloudWatchLogRetention
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - encoding
      - String
      - .. fa:: times
      - utf-8
      - 
      - Encoding
      - CloudWatchLogSource
    * - log_stream_name
      - String
      - .. fa:: times
      - 
      - CloudWatch Log Stream name
      - Log stream name
      - CloudWatchLogSource
    * - multi_line_start_pattern
      - String
      - .. fa:: times
      - 
      - 
      - Multi-line start pattern
      - CloudWatchLogSource
    * - path
      - String
      - .. fa:: check
      - 
      - Must be a valid filesystem path expression. Wildcard * is allowed.
      - Path
      - CloudWatchLogSource
    * - timestamp_format
      - String
      - .. fa:: times
      - 
      - 
      - Timestamp format
      - CloudWatchLogSource
    * - timezone
      - String
      - .. fa:: times
      - Local
      - Must be one of: 'Local', 'UTC'
      - Timezone
      - CloudWatchLogSource



AlarmNotifications
-------------------


    Alarm Notifications
    

.. _AlarmNotifications:

.. list-table:: :guilabel:`AlarmNotifications` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title



AlarmNotification
------------------


    Alarm Notification
    

.. _AlarmNotification:

.. list-table:: :guilabel:`AlarmNotification`
    :widths: 15 8 4 12 15 30 10
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
      - Base Schema
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
      - Title
    * - classification
      - String
      - .. fa:: times
      - 
      - Must be one of: 'performance', 'security', 'health' or ''.
      - Classification filter
      - AlarmNotification
    * - groups
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of groups
      - AlarmNotification
    * - severity
      - String
      - .. fa:: times
      - 
      - Must be one of: 'low', 'critical'
      - Severity filter
      - AlarmNotification


