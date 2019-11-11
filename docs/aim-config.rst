
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
      - .. fa:: times
      - 
      - Can only contain digits.
      - Account ID
    * - account_type
      - String
      - .. fa:: times
      - AWS
      - Supported types: 'AWS'
      - Account Type
    * - admin_delegate_role_name
      - String
      - .. fa:: times
      - 
      - 
      - Administrator delegate IAM Role name for the account
    * - admin_iam_users
      - Container of AdminIAMUser_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Admin IAM Users
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - is_master
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating if this a Master account
    * - organization_account_ids
      - List of Strings
      - .. fa:: times
      - 
      - Each string in the list must contain only digits.
      - A list of account ids to add to the Master account's AWS Organization
    * - region
      - String
      - .. fa:: check
      - no-region-set
      - Must be a valid AWS Region name
      - Region to install AWS Account specific resources
    * - root_email
      - String
      - .. fa:: check
      - 
      - Must be a valid email address.
      - The email address for the root user of this account
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AdminIAMUser
-------------

An AWS Account Administerator IAM User

.. _AdminIAMUser:

.. list-table:: :guilabel:`AdminIAMUser`
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - username
      - String
      - .. fa:: times
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
                                  source_security_group: aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb
                                  to_port: 80


Network
--------



.. _Network:

.. list-table:: :guilabel:`Network` |bars| Container where the keys are the ``name`` field.
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
      - .. fa:: times
      - 0
      - 
      - Availability Zones
    * - aws_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - AWS Account Reference
    * - enabled
      - Boolean
      - .. fa:: times
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
      - 
      - 
      - VPC



VPC
----


    AWS Resource: VPC
    

.. _VPC:

.. list-table:: :guilabel:`VPC`
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
      - .. fa:: times
      - 
      - 
      - CIDR
    * - enable_dns_hostnames
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable DNS Hostnames
    * - enable_dns_support
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable DNS Support
    * - enable_internet_gateway
      - Boolean
      - .. fa:: times
      - False
      - 
      - Internet Gateway
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - nat_gateway
      - Container of NATGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - NAT Gateway
    * - peering
      - Container of VPCPeering_ AIM schemas
      - .. fa:: times
      - 
      - 
      - VPC Peering
    * - private_hosted_zone
      - PrivateHostedZone_ AIM schema
      - .. fa:: times
      - 
      - 
      - Private hosted zone
    * - security_groups
      - Dict
      - .. fa:: times
      - {}
      - Two level deep dictionary: first key is Application name, second key is Resource name.
      - Security groups
    * - segments
      - Container of Segment_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Segments
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - vpn_gateway
      - Container of VPNGateway_ AIM schemas
      - .. fa:: check
      - {}
      - 
      - VPN Gateway



VPCPeering
-----------


    VPC Peering
    

.. _VPCPeering:

.. list-table:: :guilabel:`VPCPeering`
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - network_environment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Network Environment Reference
    * - peer_account_id
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer AWS account Id
    * - peer_region
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer AWS region
    * - peer_role_name
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer role name
    * - peer_vpcid
      - String
      - .. fa:: times
      - 
      - 
      - Remote peer VPC Id
    * - routing
      - List of VPCPeeringRoute_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Peering routes
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



VPCPeeringRoute
----------------


    VPC Peering Route
    

.. _VPCPeeringRoute:

.. list-table:: :guilabel:`VPCPeeringRoute`
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
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment reference



NATGateway
-----------


    AWS Resource: NAT Gateway
    

.. _NATGateway:

.. list-table:: :guilabel:`NATGateway` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - availability_zone
      - String
      - .. fa:: times
      - all
      - 
      - Availability Zones to launch instances in.
    * - default_route_segments
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Default Route Segments
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



VPNGateway
-----------


    AWS Resource: VPN Gateway
    

.. _VPNGateway:

.. list-table:: :guilabel:`VPNGateway` |bars| Container where the keys are the ``name`` field.
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled



PrivateHostedZone
------------------


    AWS Resource: Private Hosted Zone
    

.. _PrivateHostedZone:

.. list-table:: :guilabel:`PrivateHostedZone`
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Hosted zone name
    * - vpc_associations
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Ids



Segment
--------


    AWS Resource: Segment
    

.. _Segment:

.. list-table:: :guilabel:`Segment`
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
      - .. fa:: times
      - 
      - 
      - Availability Zone 1 CIDR
    * - az2_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 2 CIDR
    * - az3_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 3 CIDR
    * - az4_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 4 CIDR
    * - az5_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 5 CIDR
    * - az6_cidr
      - String
      - .. fa:: times
      - 
      - 
      - Availability Zone 6 CIDR
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - internet_access
      - Boolean
      - .. fa:: times
      - False
      - 
      - Internet Access
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



SecurityGroup
--------------


    AWS Resource: Security Group
    

.. _SecurityGroup:

.. list-table:: :guilabel:`SecurityGroup`
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
      - .. fa:: times
      - 
      - Every list item must be an EgressRule
      - Egress
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - group_description
      - String
      - .. fa:: times
      - 
      - Up to 255 characters in length
      - Group description
    * - group_name
      - String
      - .. fa:: times
      - 
      - Up to 255 characters in length. Cannot start with sg-.
      - Group name
    * - ingress
      - List of IngressRule_ AIM schemas
      - .. fa:: times
      - 
      - Every list item must be an IngressRule
      - Ingress
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



EgressRule
-----------

Security group egress

.. _EgressRule:

.. list-table:: :guilabel:`EgressRule`
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
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: times
      - 
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
    * - description
      - String
      - .. fa:: times
      - 
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
    * - destination_security_group
      - TextReference
      - .. fa:: times
      - 
      - An AIM Reference to a SecurityGroup
      - Destination Security Group Reference
    * - from_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - From port
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
    * - port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - Port
    * - protocol
      - String
      - .. fa:: times
      - 
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
    * - to_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - To port



IngressRule
------------

Security group ingress

.. _IngressRule:

.. list-table:: :guilabel:`IngressRule`
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
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: times
      - 
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
    * - description
      - String
      - .. fa:: times
      - 
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
    * - from_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - From port
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
    * - port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - Port
    * - protocol
      - String
      - .. fa:: times
      - 
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
    * - source_security_group
      - TextReference
      - .. fa:: times
      - 
      - An AIM Reference to a SecurityGroup
      - Source Security Group Reference
    * - to_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - To port


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



EnvironmentDefault
-------------------


    Default values for an Environment's configuration
    

.. _EnvironmentDefault:

.. list-table:: :guilabel:`EnvironmentDefault` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - alarm_sets
      - Container of AlarmSets_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Sets
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Application container
    * - network
      - Container of Network_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Network
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Secrets Manager
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



EnvironmentRegion
------------------


    An actual provisioned Environment in a specific region.
    May contains overrides of the IEnvironmentDefault where needed.
    

.. _EnvironmentRegion:

.. list-table:: :guilabel:`EnvironmentRegion` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - alarm_sets
      - Container of AlarmSets_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Sets
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Application container
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - network
      - Container of Network_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Network
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Secrets Manager
    * - title
      - String
      - .. fa:: times
      - 
      - 
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


    Application : An Application Engine configuration to run in a specific Environment
    

.. _Application:

.. list-table:: :guilabel:`Application` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - groups
      - Container of ResourceGroups_ AIM schemas
      - .. fa:: check
      - 
      - 
      - 
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the application will be processed
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



ResourceGroups
---------------

A collection of Application Resource Groups

.. _ResourceGroups:

.. list-table:: :guilabel:`ResourceGroups` |bars| Container where the keys are the ``name`` field.
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

A collection of Application Resources

.. _ResourceGroup:

.. list-table:: :guilabel:`ResourceGroup` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - 
      - 
      - 
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: check
      - 
      - 
      - The order in which the group will be deployed
    * - resources
      - Container of Resources_ AIM schemas
      - .. fa:: check
      - 
      - 
      - 
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: check
      - 
      - 
      - Type



Resources
----------

A collection of Application Resources

.. _Resources:

.. list-table:: :guilabel:`Resources` |bars| Container where the keys are the ``name`` field.
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


    AWS Resource to support an Application
    

.. _Resource:

.. list-table:: :guilabel:`Resource`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources


Application Resources
=====================

At it's heart, an Application is a collection of Resources. These are the Resources available for
applications.


ApiGatewayRestApi
------------------

An Api Gateway Rest API resource

.. _ApiGatewayRestApi:

.. list-table:: :guilabel:`ApiGatewayRestApi`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - api_key_source_type
      - String
      - .. fa:: times
      - 
      - Must be one of 'HEADER' to read the API key from the X-API-Key header of a request or 'AUTHORIZER' to read the API key from the UsageIdentifierKey from a Lambda authorizer.
      - API Key Source Type
    * - binary_media_types
      - List of Strings
      - .. fa:: times
      - 
      - Duplicates are not allowed. Slashes must be escaped with ~1. For example, image/png would be image~1png in the BinaryMediaTypes list.
      - Binary Media Types. The list of binary media types that are supported by the RestApi resource, such as image/png or application/octet-stream. By default, RestApi supports only UTF-8-encoded text payloads.
    * - body
      - String
      - .. fa:: times
      - 
      - Must be valid JSON.
      - Body. An OpenAPI specification that defines a set of RESTful APIs in JSON or YAML format. For YAML templates, you can also provide the specification in YAML format.
    * - body_file_location
      - StringFileReference
      - .. fa:: times
      - 
      - Must be valid path to a valid JSON document.
      - Path to a file containing the Body.
    * - body_s3_location
      - String
      - .. fa:: times
      - 
      - Valid S3Location string to a valid JSON or YAML document.
      - The Amazon Simple Storage Service (Amazon S3) location that points to an OpenAPI file, which defines a set of RESTful APIs in JSON or YAML format.
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - clone_from
      - String
      - .. fa:: times
      - 
      - 
      - CloneFrom. The ID of the RestApi resource that you want to clone.
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description of the RestApi resource.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - endpoint_configuration
      - List of Strings
      - .. fa:: times
      - 
      - List of strings, each must be one of 'EDGE', 'REGIONAL', 'PRIVATE'
      - Endpoint configuration. A list of the endpoint types of the API. Use this field when creating an API. When importing an existing API, specify the endpoint configuration types using the `parameters` field.
    * - fail_on_warnings
      - Boolean
      - .. fa:: times
      - False
      - 
      - Indicates whether to roll back the resource if a warning occurs while API Gateway is creating the RestApi resource.
    * - methods
      - Container of ApiGatewayMethods_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
    * - minimum_compression_size
      - Int
      - .. fa:: times
      - 
      - A non-negative integer between 0 and 10485760 (10M) bytes, inclusive.
      - An integer that is used to enable compression on an API. When compression is enabled, compression or decompression is not applied on the payload if the payload size is smaller than this value. Setting it to zero allows compression for any payload size.
    * - models
      - Container of ApiGatewayModels_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - parameters
      - Dict
      - .. fa:: times
      - {}
      - Dictionary of key/value pairs that are strings.
      - Parameters. Custom header parameters for the request.
    * - policy
      - String
      - .. fa:: times
      - 
      - Valid JSON document
      - A policy document that contains the permissions for the RestApi resource, in JSON format. To set the ARN for the policy, use the !Join intrinsic function with "" as delimiter and values of "execute-api:/" and "*".
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - resources
      - Container of ApiGatewayResources_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
    * - stages
      - Container of ApiGatewayStages_ AIM schemas
      - .. fa:: times
      - 
      - 
      - 
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



ApiGatewayMethods
^^^^^^^^^^^^^^^^^^

Container for API Gateway Method objects

.. _ApiGatewayMethods:

.. list-table:: :guilabel:`ApiGatewayMethods` |bars| Container where the keys are the ``name`` field.
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



ApiGatewayModels
^^^^^^^^^^^^^^^^^

Container for API Gateway Model objects

.. _ApiGatewayModels:

.. list-table:: :guilabel:`ApiGatewayModels` |bars| Container where the keys are the ``name`` field.
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



ApiGatewayResources
^^^^^^^^^^^^^^^^^^^^

Container for API Gateway Resource objects

.. _ApiGatewayResources:

.. list-table:: :guilabel:`ApiGatewayResources` |bars| Container where the keys are the ``name`` field.
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



ApiGatewayStages
^^^^^^^^^^^^^^^^^

Container for API Gateway Stage objects

.. _ApiGatewayStages:

.. list-table:: :guilabel:`ApiGatewayStages` |bars| Container where the keys are the ``name`` field.
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



LBApplication
--------------


.. sidebar:: Prescribed Automation

    ``dns``: Creates Route 53 Record Sets that will resolve DNS records to the domain name of the load balancer.

    ``enable_access_logs``: Set to True to turn on access logs for the load balancer, and will automatically create
    an S3 Bucket with permissions for AWS to write to that bucket.

    ``access_logs_bucket``: Name an existing S3 Bucket (in the same region) instead of automatically creating a new one.
    Remember that if you supply your own S3 Bucket, you are responsible for ensuring that the bucket policy for
    it grants AWS the `s3:PutObject` permission.

The ``LBApplication`` resource type creates an Application Load Balancer. Use load balancers to route traffic from
the internet to your web servers.

Load balancers have ``listeners`` which will accept requrests on specified ports and protocols. If a listener
uses the HTTPS protocol, it can have an aim reference to an SSL Certificate. A listener can then either
redirect the traffic to another port/protcol or send it one of it's named ``target_groups``.

Each target group will specify it's health check configuration. To specify which resources will belong
to a target group, use the ``target_groups`` field on an ASG resource.

.. code-block:: yaml

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
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - access_logs_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Bucket to store access logs in
    * - access_logs_prefix
      - String
      - .. fa:: times
      - 
      - 
      - Access Logs S3 Bucket prefix
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the ALB
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enable_access_logs
      - Boolean
      - .. fa:: times
      - 
      - 
      - Write access logs to an S3 Bucket
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - idle_timeout_secs
      - Int
      - .. fa:: times
      - 60
      - The idle timeout value, in seconds.
      - Idle timeout in seconds
    * - listeners
      - Container of Listener_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Listeners
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - scheme
      - Choice
      - .. fa:: times
      - 
      - 
      - Scheme
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security Groups
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Id of the segment stack
    * - target_groups
      - Container of TargetGroup_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Target Groups
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



DNS
^^^^



.. _DNS:

.. list-table:: :guilabel:`DNS`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Domain name
    * - hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Hosted Zone Id
    * - ssl_certificate
      - TextReference
      - .. fa:: times
      - 
      - 
      - SSL certificate Reference
    * - ttl
      - Int
      - .. fa:: times
      - 300
      - 
      - TTL



Listener
^^^^^^^^^



.. _Listener:

.. list-table:: :guilabel:`Listener`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol
    * - redirect
      - PortProtocol_ AIM schema
      - .. fa:: times
      - 
      - 
      - Redirect
    * - rules
      - Container of ListenerRule_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Container of listener rules
    * - ssl_certificates
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SSL certificate References
    * - target_group
      - String
      - .. fa:: times
      - 
      - 
      - Target group



ListenerRule
^^^^^^^^^^^^^



.. _ListenerRule:

.. list-table:: :guilabel:`ListenerRule`
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - host
      - String
      - .. fa:: times
      - 
      - 
      - Host header value
    * - priority
      - Int
      - .. fa:: times
      - 1
      - 
      - Forward condition priority
    * - redirect_host
      - String
      - .. fa:: times
      - 
      - 
      - The host to redirect to
    * - rule_type
      - String
      - .. fa:: times
      - 
      - 
      - Type of Rule
    * - target_group
      - String
      - .. fa:: times
      - 
      - 
      - Target group name



PortProtocol
^^^^^^^^^^^^^

Port and Protocol

.. _PortProtocol:

.. list-table:: :guilabel:`PortProtocol`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol



TargetGroup
^^^^^^^^^^^^

Target Group

.. _TargetGroup:

.. list-table:: :guilabel:`TargetGroup`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - connection_drain_timeout
      - Int
      - .. fa:: times
      - 
      - 
      - Connection drain timeout
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - health_check_http_code
      - String
      - .. fa:: times
      - 
      - 
      - Health check HTTP codes
    * - health_check_interval
      - Int
      - .. fa:: times
      - 
      - 
      - Health check interval
    * - health_check_path
      - String
      - .. fa:: times
      - /
      - 
      - Health check path
    * - health_check_timeout
      - Int
      - .. fa:: times
      - 
      - 
      - Health check timeout
    * - healthy_threshold
      - Int
      - .. fa:: times
      - 
      - 
      - Healthy threshold
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - 
      - 
      - Protocol
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - unhealthy_threshold
      - Int
      - .. fa:: times
      - 
      - 
      - Unhealthy threshold



ASG
----


    Auto Scaling Group
    

.. _ASG:

.. list-table:: :guilabel:`ASG`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - associate_public_ip_address
      - Boolean
      - .. fa:: times
      - False
      - 
      - Associate Public IP Address
    * - availability_zone
      - String
      - .. fa:: times
      - all
      - 
      - Availability Zones to launch instances in.
    * - block_device_mappings
      - List of BlockDeviceMapping_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Block Device Mappings
    * - cfn_init
      - CloudFormationInit_ AIM schema
      - .. fa:: times
      - 
      - 
      - CloudFormation Init
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - cooldown_secs
      - Int
      - .. fa:: times
      - 300
      - 
      - Cooldown seconds
    * - desired_capacity
      - Int
      - .. fa:: times
      - 1
      - 
      - Desired capacity
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - ebs_optimized
      - Boolean
      - .. fa:: times
      - False
      - 
      - EBS Optimized
    * - ebs_volume_mounts
      - List of EBSVolumeMount_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Elastic Block Store Volume Mounts
    * - efs_mounts
      - List of EFSMount_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Elastic Filesystem Configuration
    * - eip
      - TextReference
      - .. fa:: times
      - 
      - 
      - Elastic IP Reference or AllocationId
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - health_check_grace_period_secs
      - Int
      - .. fa:: times
      - 300
      - 
      - Health check grace period in seconds
    * - health_check_type
      - String
      - .. fa:: times
      - EC2
      - Must be one of: 'EC2', 'ELB'
      - Health check type
    * - instance_ami
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance AMI
    * - instance_ami_type
      - String
      - .. fa:: times
      - amazon
      - Must be one of amazon, centos, suse, debian, ubuntu, microsoft or redhat.
      - The AMI Operating System family
    * - instance_iam_role
      - Role_ AIM schema
      - .. fa:: check
      - 
      - 
      - 
    * - instance_key_pair
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance key pair reference
    * - instance_monitoring
      - Boolean
      - .. fa:: times
      - False
      - 
      - Instance monitoring
    * - instance_type
      - String
      - .. fa:: times
      - 
      - 
      - Instance type
    * - launch_options
      - EC2LaunchOptions_ AIM schema
      - .. fa:: times
      - 
      - 
      - EC2 Launch Options
    * - lifecycle_hooks
      - Container of ASGLifecycleHooks_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lifecycle Hooks
    * - load_balancers
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Target groups
    * - max_instances
      - Int
      - .. fa:: times
      - 2
      - 
      - Maximum instances
    * - min_instances
      - Int
      - .. fa:: times
      - 1
      - 
      - Minimum instances
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - scaling_policies
      - Container of ASGScalingPolicies_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Scaling Policies
    * - scaling_policy_cpu_average
      - Int
      - .. fa:: times
      - 0
      - 
      - Average CPU Scaling Polciy
    * - secrets
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Secrets Manager References
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security groups
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
    * - target_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Target groups
    * - termination_policies
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Terminiation policies
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - update_policy_max_batch_size
      - Int
      - .. fa:: times
      - 1
      - 
      - Update policy maximum batch size
    * - update_policy_min_instances_in_service
      - Int
      - .. fa:: times
      - 1
      - 
      - Update policy minimum instances in service
    * - user_data_pre_script
      - String
      - .. fa:: times
      - 
      - 
      - User data pre-script
    * - user_data_script
      - String
      - .. fa:: times
      - 
      - 
      - User data script



ASGLifecycleHooks
^^^^^^^^^^^^^^^^^^


    Container of ASG LifecycleHOoks
    

.. _ASGLifecycleHooks:

.. list-table:: :guilabel:`ASGLifecycleHooks` |bars| Container where the keys are the ``name`` field.
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



ASGScalingPolicies
^^^^^^^^^^^^^^^^^^^


    Container of Auto Scaling Group Scaling Policies
    

.. _ASGScalingPolicies:

.. list-table:: :guilabel:`ASGScalingPolicies` |bars| Container where the keys are the ``name`` field.
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



BlockDeviceMapping
^^^^^^^^^^^^^^^^^^^



.. _BlockDeviceMapping:

.. list-table:: :guilabel:`BlockDeviceMapping`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - device_name
      - String
      - .. fa:: check
      - 
      - 
      - The device name exposed to the EC2 instance
    * - ebs
      - BlockDevice_ AIM schema
      - .. fa:: times
      - 
      - 
      - Amazon Ebs volume
    * - virtual_name
      - String
      - .. fa:: times
      - 
      - The name must be in the form ephemeralX where X is a number starting from zero (0), for example, ephemeral0.
      - The name of the virtual device.



BlockDevice
^^^^^^^^^^^^



.. _BlockDevice:

.. list-table:: :guilabel:`BlockDevice`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - delete_on_termination
      - Boolean
      - .. fa:: times
      - True
      - 
      - Indicates whether to delete the volume when the instance is terminated.
    * - encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Specifies whether the EBS volume is encrypted.
    * - iops
      - Int
      - .. fa:: times
      - 
      - The maximum ratio of IOPS to volume size (in GiB) is 50:1, so for 5,000 provisioned IOPS, you need at least 100 GiB storage on the volume.
      - The number of I/O operations per second (IOPS) to provision for the volume.
    * - size_gib
      - Int
      - .. fa:: times
      - 
      - This can be a number from 1-1,024 for standard, 4-16,384 for io1, 1-16,384 for gp2, and 500-16,384 for st1 and sc1.
      - The volume size, in Gibibytes (GiB).
    * - snapshot_id
      - String
      - .. fa:: times
      - 
      - 
      - The snapshot ID of the volume to use.
    * - volume_type
      - String
      - .. fa:: check
      - 
      - Must be one of standard, io1, gp2, st1 or sc1.
      - The volume type, which can be standard for Magnetic, io1 for Provisioned IOPS SSD, gp2 for General Purpose SSD, st1 for Throughput Optimized HDD, or sc1 for Cold HDD.



EBSVolumeMount
^^^^^^^^^^^^^^^


    EBS Volume Mount Configuration
    

.. _EBSVolumeMount:

.. list-table:: :guilabel:`EBSVolumeMount`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - device
      - String
      - .. fa:: check
      - 
      - 
      - Device to mount the EBS Volume with.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - filesystem
      - String
      - .. fa:: check
      - 
      - 
      - Filesystem to mount the EBS Volume with.
    * - folder
      - String
      - .. fa:: check
      - 
      - 
      - Folder to mount the EBS Volume
    * - volume
      - TextReference
      - .. fa:: check
      - 
      - 
      - EBS Volume Resource Reference



EFSMount
^^^^^^^^^


    EFS Mount Folder and Target Configuration
    

.. _EFSMount:

.. list-table:: :guilabel:`EFSMount`
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - folder
      - String
      - .. fa:: check
      - 
      - 
      - Folder to mount the EFS target
    * - target
      - TextReference
      - .. fa:: check
      - 
      - 
      - EFS Target Resource Reference



EC2LaunchOptions
^^^^^^^^^^^^^^^^^


    EC2 Launch Options
    

.. _EC2LaunchOptions:

.. list-table:: :guilabel:`EC2LaunchOptions`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cfn_init_config_sets
      - List of Strings
      - .. fa:: times
      - []
      - 
      - List of cfn-init config sets
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - update_packages
      - Boolean
      - .. fa:: times
      - False
      - 
      - Update Distribution Packages



CloudFormationInit
^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInit:

.. list-table:: :guilabel:`CloudFormationInit`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - config_sets
      - Container of CloudFormationConfigSets_ AIM schemas
      - .. fa:: check
      - 
      - 
      - CloudFormation Init configSets
    * - configurations
      - Container of CloudFormationConfigurations_ AIM schemas
      - .. fa:: check
      - 
      - 
      - CloudFormation Init configurations
    * - parameters
      - Dict
      - .. fa:: times
      - {}
      - 
      - Parameters
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



CloudFormationConfigSets
^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigSets:

.. list-table:: :guilabel:`CloudFormationConfigSets` |bars| Container where the keys are the ``name`` field.
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



CloudFormationConfigurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigurations:

.. list-table:: :guilabel:`CloudFormationConfigurations` |bars| Container where the keys are the ``name`` field.
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



CodePipeBuildDeploy
--------------------


    Code Pipeline: Build and Deploy
    

.. _CodePipeBuildDeploy:

.. list-table:: :guilabel:`CodePipeBuildDeploy`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - alb_target_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ALB Target Group Reference
    * - artifacts_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Artifacts S3 Bucket Reference
    * - asg
      - TextReference
      - .. fa:: times
      - 
      - 
      - ASG Reference
    * - auto_rollback_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Automatic rollback enabled
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - codebuild_compute_type
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Compute Type
    * - codebuild_image
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Docker Image
    * - codecommit_repository
      - TextReference
      - .. fa:: times
      - 
      - 
      - CodeCommit Respository
    * - cross_account_support
      - Boolean
      - .. fa:: times
      - False
      - 
      - Cross Account Support
    * - data_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Data Account Reference
    * - deploy_config_type
      - String
      - .. fa:: times
      - HOST_COUNT
      - 
      - Deploy Config Type
    * - deploy_config_value
      - Int
      - .. fa:: times
      - 0
      - 
      - Deploy Config Value
    * - deploy_instance_role
      - TextReference
      - .. fa:: times
      - 
      - 
      - Deploy Instance Role Reference
    * - deploy_style_option
      - String
      - .. fa:: times
      - WITH_TRAFFIC_CONTROL
      - 
      - Deploy Style Option
    * - deployment_branch_name
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Branch Name
    * - deployment_environment
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Environment
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - elb_name
      - String
      - .. fa:: times
      - 
      - 
      - ELB Name
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - manual_approval_enabled
      - Boolean
      - .. fa:: times
      - False
      - 
      - Manual approval enabled
    * - manual_approval_notification_email
      - String
      - .. fa:: times
      - 
      - 
      - Manual approval notification email
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - timeout_mins
      - Int
      - .. fa:: times
      - 60
      - 
      - Timeout in Minutes
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - tools_account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Tools Account Reference
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



AWSCertificateManager
----------------------



.. _AWSCertificateManager:

.. list-table:: :guilabel:`AWSCertificateManager`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - domain_name
      - String
      - .. fa:: times
      - 
      - 
      - Domain Name
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - external_resource
      - Boolean
      - .. fa:: times
      - False
      - 
      - Marks this resource as external to avoid creating and validating it.
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - subject_alternative_names
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Subject alternative names
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



RDS
----


    RDS Common Interface
    

.. _RDS:

.. list-table:: :guilabel:`RDS`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - allow_major_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Allow major version upgrades
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Automatic minor version upgrades
    * - backup_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Backup Preferred Window
    * - backup_retention_period
      - Int
      - .. fa:: times
      - 
      - 
      - Backup Retention Period in days
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - cloudwatch_logs_exports
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of CloudWatch Logs Exports
    * - db_instance_type
      - String
      - .. fa:: times
      - 
      - 
      - RDS Instance Type
    * - db_snapshot_identifier
      - String
      - .. fa:: times
      - 
      - 
      - DB Snapshot Identifier to restore from
    * - deletion_protection
      - Boolean
      - .. fa:: times
      - False
      - 
      - Deletion Protection
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the RDS
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine Version
    * - kms_key_id
      - TextReference
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
    * - license_model
      - String
      - .. fa:: times
      - 
      - 
      - License Model
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Maintenance Preferred Window
    * - master_user_password
      - String
      - .. fa:: times
      - 
      - 
      - Master User Password
    * - master_username
      - String
      - .. fa:: times
      - 
      - 
      - Master Username
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - option_configurations
      - List of RDSOptionConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Option Configurations
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - RDS Parameter Group
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - DB Port
    * - primary_domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Domain Name
    * - primary_hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Hosted Zone
    * - publically_accessible
      - Boolean
      - .. fa:: times
      - 
      - 
      - Assign a Public IP address
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - secrets_password
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secrets Manager password
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
    * - storage_encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
    * - storage_size_gb
      - Int
      - .. fa:: times
      - 
      - 
      - DB Storage Size in Gigabytes
    * - storage_type
      - String
      - .. fa:: times
      - 
      - 
      - DB Storage Type
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



RDSOptionConfiguration
^^^^^^^^^^^^^^^^^^^^^^^


    AWS::RDS::OptionGroup OptionConfiguration
    

.. _RDSOptionConfiguration:

.. list-table:: :guilabel:`RDSOptionConfiguration`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - option_name
      - String
      - .. fa:: times
      - 
      - 
      - Option Name
    * - option_settings
      - List of NameValuePair_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of option name value pairs.
    * - option_version
      - String
      - .. fa:: times
      - 
      - 
      - Option Version
    * - port
      - String
      - .. fa:: times
      - 
      - 
      - Port



NameValuePair
^^^^^^^^^^^^^^



.. _NameValuePair:

.. list-table:: :guilabel:`NameValuePair`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Name
    * - value
      - String
      - .. fa:: times
      - 
      - 
      - Value



DBParameterGroup
-----------------


    AWS::RDS::DBParameterGroup
    

.. _DBParameterGroup:

.. list-table:: :guilabel:`DBParameterGroup`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - family
      - String
      - .. fa:: check
      - 
      - 
      - Database Family
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - parameters
      - Container of DBParameters_ AIM schemas
      - .. fa:: check
      - 
      - 
      - Database Parameter set
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



DBParameters
^^^^^^^^^^^^^

A dict of database parameters



EC2
----


    EC2 Instance
    

.. _EC2:

.. list-table:: :guilabel:`EC2`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - associate_public_ip_address
      - Boolean
      - .. fa:: times
      - False
      - 
      - Associate Public IP Address
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - disable_api_termination
      - Boolean
      - .. fa:: times
      - False
      - 
      - Disable API Termination
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - instance_ami
      - String
      - .. fa:: times
      - 
      - 
      - Instance AMI
    * - instance_key_pair
      - TextReference
      - .. fa:: times
      - 
      - 
      - Instance key pair reference
    * - instance_type
      - String
      - .. fa:: times
      - 
      - 
      - Instance type
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - private_ip_address
      - String
      - .. fa:: times
      - 
      - 
      - Private IP Address
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - root_volume_size_gb
      - Int
      - .. fa:: times
      - 8
      - 
      - Root volume size GB
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Security groups
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - user_data_script
      - String
      - .. fa:: times
      - 
      - 
      - User data script



Lambda
-------


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

Lambda Functions allow you to run code without provisioning servers and only
pay for the compute time when the code is running.

For the code that the Lambda function will run, use the ``code:`` block and specify
``s3_bucket`` and ``s3_key`` to deploy the code from an S3 Bucket or use ``zipfile`` to read a local file from disk.

.. code-block:: yaml

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
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - code
      - LambdaFunctionCode_ AIM schema
      - .. fa:: check
      - 
      - 
      - The function deployment package.
    * - description
      - String
      - .. fa:: check
      - 
      - 
      - A description of the function.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - environment
      - Container of LambdaEnvironment_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda Function Environment
    * - handler
      - String
      - .. fa:: check
      - 
      - 
      - Function Handler
    * - iam_role
      - Role_ AIM schema
      - .. fa:: check
      - 
      - 
      - The IAM Role this Lambda will execute as.
    * - layers
      - List of Strings
      - .. fa:: check
      - 
      - Up to 5 Layer ARNs
      - Layers
    * - memory_size
      - Int
      - .. fa:: times
      - 128
      - 
      - Function memory size (MB)
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - reserved_concurrent_executions
      - Int
      - .. fa:: times
      - 0
      - 
      - Reserved Concurrent Executions
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - runtime
      - String
      - .. fa:: check
      - python3.7
      - 
      - Runtime environment
    * - sdb_cache
      - Boolean
      - .. fa:: times
      - False
      - 
      - SDB Cache Domain
    * - sns_topics
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SNS Topic AIM References
    * - timeout
      - Int
      - .. fa:: times
      - 
      - Must be between 0 and 900 seconds.
      - Max function execution time in seconds.
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - vpc_config
      - LambdaVpcConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - Vpc Configuration



LambdaFunctionCode
^^^^^^^^^^^^^^^^^^^

The deployment package for a Lambda function.

.. _LambdaFunctionCode:

.. list-table:: :guilabel:`LambdaFunctionCode`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - s3_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - An Amazon S3 bucket in the same AWS Region as your function
    * - s3_key
      - String
      - .. fa:: times
      - 
      - 
      - The Amazon S3 key of the deployment package.
    * - zipfile
      - StringFileReference
      - .. fa:: times
      - 
      - Maximum of 4096 characters.
      - The function as an external file.



LambdaEnvironment
^^^^^^^^^^^^^^^^^^


    Lambda Environment
    

.. _LambdaEnvironment:

.. list-table:: :guilabel:`LambdaEnvironment` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - variables
      - List of LambdaVariable_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda Function Variables



LambdaVpcConfig
^^^^^^^^^^^^^^^^


    Lambda Environment
    

.. _LambdaVpcConfig:

.. list-table:: :guilabel:`LambdaVpcConfig`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
    * - segments
      - List of Strings
      - .. fa:: times
      - 
      - 
      - VPC Segments to attach the function
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



LambdaVariable
^^^^^^^^^^^^^^^


    Lambda Environment Variable
    

.. _LambdaVariable:

.. list-table:: :guilabel:`LambdaVariable`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - key
      - String
      - .. fa:: check
      - 
      - 
      - Variable Name
    * - value
      - TextReference
      - .. fa:: check
      - 
      - 
      - Variable Value



ManagedPolicy
--------------


    IAM Managed Policy
    

.. _ManagedPolicy:

.. list-table:: :guilabel:`ManagedPolicy` |bars| Container where the keys are the ``name`` field.
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - path
      - String
      - .. fa:: times
      - /
      - 
      - Path
    * - roles
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Role Names
    * - statement
      - List of Statement_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Statements
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - users
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of IAM Users



S3Bucket
---------


    S3 Bucket : A template describing an S3 Bbucket
    

.. _S3Bucket:

.. list-table:: :guilabel:`S3Bucket`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - account
      - TextReference
      - .. fa:: times
      - 
      - 
      - Account Reference
    * - bucket_name
      - String
      - .. fa:: check
      - bucket
      - A short unique name to assign the bucket.
      - Bucket Name
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - cloudfront_origin
      - Boolean
      - .. fa:: times
      - False
      - 
      - Creates and listens for a CloudFront Access Origin Identity
    * - deletion_policy
      - String
      - .. fa:: times
      - delete
      - 
      - Bucket Deletion Policy
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - external_resource
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether the S3 Bucket already exists or not
    * - notifications
      - S3NotificationConfiguration_ AIM schema
      - .. fa:: times
      - 
      - 
      - Notification configuration
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - policy
      - List of S3BucketPolicy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of S3 Bucket Policies
    * - region
      - String
      - .. fa:: times
      - 
      - 
      - Bucket region
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - versioning
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable Versioning on the bucket.



S3BucketPolicy
^^^^^^^^^^^^^^^


    S3 Bucket Policy
    

.. _S3BucketPolicy:

.. list-table:: :guilabel:`S3BucketPolicy`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - action
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of Actions
    * - aws
      - List of Strings
      - .. fa:: times
      - 
      - Either this field or the principal field must be set.
      - List of AWS Principles.
    * - condition
      - Dict
      - .. fa:: times
      - {}
      - Each Key is the Condition name and the Value must be a dictionary of request filters. e.g. { "StringEquals" : { "aws:username" : "johndoe" }}
      - Condition
    * - effect
      - String
      - .. fa:: check
      - Deny
      - Must be one of: 'Allow', 'Deny'
      - Effect
    * - principal
      - Dict
      - .. fa:: times
      - {}
      - Either this field or the aws field must be set. Key should be one of: AWS, Federated, Service or CanonicalUser. Value can be either a String or a List.
      - Prinicpals
    * - resource_suffix
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of AWS Resources Suffixes



S3LambdaConfiguration
^^^^^^^^^^^^^^^^^^^^^^



.. _S3LambdaConfiguration:

.. list-table:: :guilabel:`S3LambdaConfiguration`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - event
      - String
      - .. fa:: times
      - 
      - Must be a supported event type: https://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
      - S3 bucket event for which to invoke the AWS Lambda function
    * - function
      - TextReference
      - .. fa:: times
      - 
      - 
      - Reference to a Lambda



S3NotificationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3NotificationConfiguration:

.. list-table:: :guilabel:`S3NotificationConfiguration`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - lambdas
      - List of S3LambdaConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Lambda configurations



SNSTopic
---------


    SNS Topic Resource Configuration
    

.. _SNSTopic:

.. list-table:: :guilabel:`SNSTopic`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - cross_account_access
      - Boolean
      - .. fa:: times
      - False
      - 
      - Cross-account access from all other accounts in this project.
    * - display_name
      - String
      - .. fa:: times
      - 
      - 
      - Display name for SMS Messages
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - subscriptions
      - List of SNSTopicSubscription_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of SNS Topic Subscriptions
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



SNSTopicSubscription
^^^^^^^^^^^^^^^^^^^^^



.. _SNSTopicSubscription:

.. list-table:: :guilabel:`SNSTopicSubscription`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - endpoint
      - TextReference
      - .. fa:: times
      - 
      - 
      - SNS Topic Endpoint
    * - protocol
      - String
      - .. fa:: times
      - email
      - Must be a valid SNS Topic subscription protocol: 'http', 'https', 'email', 'email-json', 'sms', 'sqs', 'application', 'lambda'.
      - Notification protocol



CloudFront
-----------


    CloudFront CDN Configuration
    

.. _CloudFront:

.. list-table:: :guilabel:`CloudFront`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cache_behaviors
      - List of CloudFrontCacheBehavior_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of Cache Behaviors
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - custom_error_responses
      - List of CloudFrontCustomErrorResponse_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of Custom Error Responses
    * - default_cache_behavior
      - CloudFrontDefaultCacheBehavior_ AIM schema
      - .. fa:: times
      - 
      - 
      - Default Cache Behavior
    * - default_root_object
      - String
      - .. fa:: times
      - index.html
      - 
      - The default path to load from the origin.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - domain_aliases
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the Distribution
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - factory
      - Container of CloudFrontFactory_ AIM schemas
      - .. fa:: times
      - 
      - 
      - CloudFront Factory
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - origins
      - Container of CloudFrontOrigin_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Map of Origins
    * - price_class
      - String
      - .. fa:: times
      - All
      - 
      - Price Class
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - viewer_certificate
      - CloudFrontViewerCertificate_ AIM schema
      - .. fa:: times
      - 
      - 
      - Viewer Certificate
    * - webacl_id
      - String
      - .. fa:: times
      - 
      - 
      - WAF WebACLId



CloudFrontDefaultCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontDefaultCacheBehavior:

.. list-table:: :guilabel:`CloudFrontDefaultCacheBehavior`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - allowed_methods
      - List of Strings
      - .. fa:: times
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
      - 
      - List of Allowed HTTP Methods
    * - cached_methods
      - List of Strings
      - .. fa:: times
      - ['GET', 'HEAD', 'OPTIONS']
      - 
      - List of HTTP Methods to cache
    * - compress
      - Boolean
      - .. fa:: times
      - False
      - 
      - Compress certain files automatically
    * - default_ttl
      - Int
      - .. fa:: check
      - 0
      - 
      - Default TTTL
    * - forwarded_values
      - CloudFrontForwardedValues_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forwarded Values
    * - target_origin
      - TextReference
      - .. fa:: check
      - 
      - 
      - Target Origin
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - viewer_protocol_policy
      - String
      - .. fa:: check
      - redirect-to-https
      - 
      - Viewer Protocol Policy



CloudFrontCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCacheBehavior:

.. list-table:: :guilabel:`CloudFrontCacheBehavior`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - allowed_methods
      - List of Strings
      - .. fa:: times
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
      - 
      - List of Allowed HTTP Methods
    * - cached_methods
      - List of Strings
      - .. fa:: times
      - ['GET', 'HEAD', 'OPTIONS']
      - 
      - List of HTTP Methods to cache
    * - compress
      - Boolean
      - .. fa:: times
      - False
      - 
      - Compress certain files automatically
    * - default_ttl
      - Int
      - .. fa:: check
      - 0
      - 
      - Default TTTL
    * - forwarded_values
      - CloudFrontForwardedValues_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forwarded Values
    * - path_pattern
      - String
      - .. fa:: check
      - 
      - 
      - Path Pattern
    * - target_origin
      - TextReference
      - .. fa:: check
      - 
      - 
      - Target Origin
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - viewer_protocol_policy
      - String
      - .. fa:: check
      - redirect-to-https
      - 
      - Viewer Protocol Policy



CloudFrontFactory
^^^^^^^^^^^^^^^^^^


    CloudFront Factory
    

.. _CloudFrontFactory:

.. list-table:: :guilabel:`CloudFrontFactory`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - domain_aliases
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the Distribution
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - viewer_certificate
      - CloudFrontViewerCertificate_ AIM schema
      - .. fa:: times
      - 
      - 
      - Viewer Certificate



CloudFrontOrigin
^^^^^^^^^^^^^^^^^


    CloudFront Origin Configuration
    

.. _CloudFrontOrigin:

.. list-table:: :guilabel:`CloudFrontOrigin`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - custom_origin_config
      - CloudFrontCustomOriginConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - Custom Origin Configuration
    * - domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Origin Resource Reference
    * - s3_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Origin S3 Bucket Reference
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



CloudFrontCustomOriginConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomOriginConfig:

.. list-table:: :guilabel:`CloudFrontCustomOriginConfig`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - http_port
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Port
    * - https_port
      - Int
      - .. fa:: times
      - 
      - 
      - HTTPS Port
    * - keepalive_timeout
      - Int
      - .. fa:: times
      - 5
      - 
      - HTTP Keepalive Timeout
    * - protocol_policy
      - String
      - .. fa:: times
      - 
      - 
      - Protocol Policy
    * - read_timeout
      - Int
      - .. fa:: times
      - 30
      - 
      - Read timeout
    * - ssl_protocols
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of SSL Protocols
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



CloudFrontCustomErrorResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomErrorResponse:

.. list-table:: :guilabel:`CloudFrontCustomErrorResponse`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - error_caching_min_ttl
      - Int
      - .. fa:: times
      - 
      - 
      - Error Caching Min TTL
    * - error_code
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Error Code
    * - response_code
      - Int
      - .. fa:: times
      - 
      - 
      - HTTP Response Code
    * - response_page_path
      - String
      - .. fa:: times
      - 
      - 
      - Response Page Path



CloudFrontViewerCertificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontViewerCertificate:

.. list-table:: :guilabel:`CloudFrontViewerCertificate`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - certificate
      - TextReference
      - .. fa:: times
      - 
      - 
      - Certificate Reference
    * - minimum_protocol_version
      - String
      - .. fa:: times
      - TLSv1.1_2016
      - 
      - Minimum SSL Protocol Version
    * - ssl_supported_method
      - String
      - .. fa:: times
      - sni-only
      - 
      - SSL Supported Method
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



CloudFrontForwardedValues
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontForwardedValues:

.. list-table:: :guilabel:`CloudFrontForwardedValues`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - cookies
      - CloudFrontCookies_ AIM schema
      - .. fa:: times
      - 
      - 
      - Forward Cookies
    * - headers
      - List of Strings
      - .. fa:: times
      - ['*']
      - 
      - Forward Headers
    * - query_string
      - Boolean
      - .. fa:: times
      - True
      - 
      - Forward Query Strings
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



CloudFrontCookies
^^^^^^^^^^^^^^^^^^



.. _CloudFrontCookies:

.. list-table:: :guilabel:`CloudFrontCookies`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - forward
      - String
      - .. fa:: times
      - all
      - 
      - Cookies Forward Action
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - whitelisted_names
      - List of Strings
      - .. fa:: times
      - 
      - 
      - White Listed Names



RDSMysql
---------


    RDS Mysql
    

.. _RDSMysql:

.. list-table:: :guilabel:`RDSMysql`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - allow_major_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Allow major version upgrades
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Automatic minor version upgrades
    * - backup_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Backup Preferred Window
    * - backup_retention_period
      - Int
      - .. fa:: times
      - 
      - 
      - Backup Retention Period in days
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - cloudwatch_logs_exports
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of CloudWatch Logs Exports
    * - db_instance_type
      - String
      - .. fa:: times
      - 
      - 
      - RDS Instance Type
    * - db_snapshot_identifier
      - String
      - .. fa:: times
      - 
      - 
      - DB Snapshot Identifier to restore from
    * - deletion_protection
      - Boolean
      - .. fa:: times
      - False
      - 
      - Deletion Protection
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the RDS
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - RDS Engine Version
    * - kms_key_id
      - TextReference
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
    * - license_model
      - String
      - .. fa:: times
      - 
      - 
      - License Model
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Maintenance Preferred Window
    * - master_user_password
      - String
      - .. fa:: times
      - 
      - 
      - Master User Password
    * - master_username
      - String
      - .. fa:: times
      - 
      - 
      - Master Username
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - multi_az
      - Boolean
      - .. fa:: times
      - False
      - 
      - MultiAZ Support
    * - option_configurations
      - List of RDSOptionConfiguration_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Option Configurations
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - RDS Parameter Group
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - DB Port
    * - primary_domain_name
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Domain Name
    * - primary_hosted_zone
      - TextReference
      - .. fa:: times
      - 
      - 
      - Primary Hosted Zone
    * - publically_accessible
      - Boolean
      - .. fa:: times
      - 
      - 
      - Assign a Public IP address
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - secrets_password
      - TextReference
      - .. fa:: times
      - 
      - 
      - Secrets Manager password
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of VPC Security Group Ids
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
    * - storage_encrypted
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable Storage Encryption
    * - storage_size_gb
      - Int
      - .. fa:: times
      - 
      - 
      - DB Storage Size in Gigabytes
    * - storage_type
      - String
      - .. fa:: times
      - 
      - 
      - DB Storage Type
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



ElastiCacheRedis
-----------------


    Redis ElastiCache Interface
    

.. _ElastiCacheRedis:

.. list-table:: :guilabel:`ElastiCacheRedis`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - at_rest_encryption
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable encryption at rest
    * - auto_minor_version_upgrade
      - Boolean
      - .. fa:: times
      - 
      - 
      - Enable automatic minor version upgrades
    * - automatic_failover_enabled
      - Boolean
      - .. fa:: times
      - 
      - 
      - Specifies whether a read-only replica is automatically promoted to read/write primary if the existing primary fails
    * - az_mode
      - String
      - .. fa:: times
      - 
      - 
      - AZ mode
    * - cache_clusters
      - Int
      - .. fa:: times
      - 
      - 
      - Number of Cache Clusters
    * - cache_node_type
      - String
      - .. fa:: times
      - 
      - 
      - Cache Node Instance type
    * - cache_parameter_group_family
      - String
      - .. fa:: times
      - 
      - 
      - Cache Parameter Group Family
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Replication Description
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - engine
      - String
      - .. fa:: times
      - 
      - 
      - ElastiCache Engine
    * - engine_version
      - String
      - .. fa:: times
      - 
      - 
      - ElastiCache Engine Version
    * - maintenance_preferred_window
      - String
      - .. fa:: times
      - 
      - 
      - Preferred maintenance window
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - 
      - 
      - 
    * - number_of_read_replicas
      - Int
      - .. fa:: times
      - 
      - 
      - Number of read replicas
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - parameter_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - Parameter Group name or reference
    * - port
      - Int
      - .. fa:: times
      - 
      - 
      - Port
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - security_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of Security Groups
    * - segment
      - TextReference
      - .. fa:: times
      - 
      - 
      - Segment
    * - snapshot_retention_limit_days
      - Int
      - .. fa:: times
      - 
      - 
      - Snapshot Retention Limit in Days
    * - snapshot_window
      - String
      - .. fa:: times
      - 
      - 
      - The daily time range (in UTC) during which ElastiCache begins taking a daily snapshot of your node group (shard).
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



DeploymentPipeline
-------------------


    Code Pipeline: Build and Deploy
    

.. _DeploymentPipeline:

.. list-table:: :guilabel:`DeploymentPipeline`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - build
      - Container of DeploymentPipelineBuildStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Build Stage
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - configuration
      - DeploymentPipelineConfiguration_ AIM schema
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline General Configuration
    * - deploy
      - Container of DeploymentPipelineDeployStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Deploy Stage
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - source
      - Container of DeploymentPipelineSourceStage_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Deployment Pipeline Source Stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



DeploymentPipelineSourceStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline source stage actions
    

.. _DeploymentPipelineSourceStage:

.. list-table:: :guilabel:`DeploymentPipelineSourceStage` |bars| Container where the keys are the ``name`` field.
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



DeploymentPipelineDeployStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline deploy stage actions
    

.. _DeploymentPipelineDeployStage:

.. list-table:: :guilabel:`DeploymentPipelineDeployStage` |bars| Container where the keys are the ``name`` field.
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



DeploymentPipelineBuildStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    A map of DeploymentPipeline build stage actions
    

.. _DeploymentPipelineBuildStage:

.. list-table:: :guilabel:`DeploymentPipelineBuildStage` |bars| Container where the keys are the ``name`` field.
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



DeploymentPipelineDeployCodeDeploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeDeploy DeploymentPipeline Deploy Stage
    

.. _DeploymentPipelineDeployCodeDeploy:

.. list-table:: :guilabel:`DeploymentPipelineDeployCodeDeploy` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - alb_target_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ALB Target Group Reference
    * - auto_rollback_enabled
      - Boolean
      - .. fa:: check
      - True
      - 
      - Automatic rollback enabled
    * - auto_scaling_group
      - TextReference
      - .. fa:: times
      - 
      - 
      - ASG Reference
    * - deploy_instance_role
      - TextReference
      - .. fa:: times
      - 
      - 
      - Deploy Instance Role Reference
    * - deploy_style_option
      - String
      - .. fa:: times
      - WITH_TRAFFIC_CONTROL
      - 
      - Deploy Style Option
    * - elb_name
      - String
      - .. fa:: times
      - 
      - 
      - ELB Name
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - minimum_healthy_hosts
      - CodeDeployMinimumHealthyHosts_ AIM schema
      - .. fa:: times
      - 
      - 
      - The minimum number of healthy instances that should be available at any time during the deployment.
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



CodeDeployMinimumHealthyHosts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeDeploy Minimum Healthy Hosts
    

.. _CodeDeployMinimumHealthyHosts:

.. list-table:: :guilabel:`CodeDeployMinimumHealthyHosts`
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
    * - type
      - String
      - .. fa:: times
      - HOST_COUNT
      - 
      - Deploy Config Type
    * - value
      - Int
      - .. fa:: times
      - 0
      - 
      - Deploy Config Value



DeploymentPipelineManualApproval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    ManualApproval DeploymentPipeline
    

.. _DeploymentPipelineManualApproval:

.. list-table:: :guilabel:`DeploymentPipelineManualApproval` |bars| Container where the keys are the ``name`` field.
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - manual_approval_notification_email
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Manual Approval Notification Email List
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



DeploymentPipelineDeployS3
^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Amazon S3 Deployment Provider
    

.. _DeploymentPipelineDeployS3:

.. list-table:: :guilabel:`DeploymentPipelineDeployS3` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - S3 Bucket Reference
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - extract
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether the deployment artifact will be unarchived.
    * - object_key
      - String
      - .. fa:: times
      - 
      - 
      - S3 object key to store the deployment artifact as.
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



DeploymentPipelineBuildCodeBuild
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeBuild DeploymentPipeline Build Stage
    

.. _DeploymentPipelineBuildCodeBuild:

.. list-table:: :guilabel:`DeploymentPipelineBuildCodeBuild` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - codebuild_compute_type
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Compute Type
    * - codebuild_image
      - String
      - .. fa:: times
      - 
      - 
      - CodeBuild Docker Image
    * - deployment_environment
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Environment
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - role_policies
      - List of Policy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Project IAM Role Policies
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - timeout_mins
      - Int
      - .. fa:: times
      - 60
      - 
      - Timeout in Minutes
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



DeploymentPipelineSourceCodeCommit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    CodeCommit DeploymentPipeline Source Stage
    

.. _DeploymentPipelineSourceCodeCommit:

.. list-table:: :guilabel:`DeploymentPipelineSourceCodeCommit` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - codecommit_repository
      - TextReference
      - .. fa:: times
      - 
      - 
      - CodeCommit Respository
    * - deployment_branch_name
      - String
      - .. fa:: times
      - 
      - 
      - Deployment Branch Name
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



DeploymentPipelineStageAction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Deployment Pipeline Source Stage
    

.. _DeploymentPipelineStageAction:

.. list-table:: :guilabel:`DeploymentPipelineStageAction` |bars| Container where the keys are the ``name`` field.
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - run_order
      - Int
      - .. fa:: times
      - 1
      - 
      - The order in which to run this stage
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - 
      - The type of DeploymentPipeline Source Stage



DeploymentPipelineConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    Deployment Pipeline General Configuration
    

.. _DeploymentPipelineConfiguration:

.. list-table:: :guilabel:`DeploymentPipelineConfiguration`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - account
      - TextReference
      - .. fa:: times
      - 
      - 
      - The account where Pipeline tools will be provisioned.
    * - artifacts_bucket
      - TextReference
      - .. fa:: times
      - 
      - 
      - Artifacts S3 Bucket Reference
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



EFS
----


    Elastic File System Resource
    

.. _EFS:

.. list-table:: :guilabel:`EFS`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - encrypted
      - Boolean
      - .. fa:: check
      - False
      - 
      - Encryption at Rest
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - security_groups
      - List of Strings
      - .. fa:: check
      - 
      - 
      - Security groups
    * - segment
      - String
      - .. fa:: times
      - 
      - 
      - Segment
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



EIP
----


    Elastic IP
    

.. _EIP:

.. list-table:: :guilabel:`EIP`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns
      - List of DNS_ AIM schemas
      - .. fa:: times
      - 
      - 
      - List of DNS for the EIP
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
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
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



Route53HealthCheck
-------------------

Route53 Health Check

.. _Route53HealthCheck:

.. list-table:: :guilabel:`Route53HealthCheck`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - failure_threshold
      - Int
      - .. fa:: times
      - 3
      - 
      - Number of consecutive health checks that an endpoint must pass or fail for Amazon Route 53 to change the current status of the endpoint from unhealthy to healthy or vice versa.
    * - health_check_type
      - String
      - .. fa:: check
      - 
      - Must be one of HTTP, HTTPS or TCP
      - Health Check Type
    * - health_checker_regions
      - List of Strings
      - .. fa:: times
      - 
      - List of AWS Region names (e.g. us-west-2) from which to make health checks.
      - Health checker regions
    * - latency_graphs
      - Boolean
      - .. fa:: times
      - False
      - 
      - Measure latency and display CloudWatch graph in the AWS Console
    * - load_balancer
      - TextReference
      - .. fa:: times
      - 
      - 
      - Load Balancer Endpoint
    * - match_string
      - String
      - .. fa:: times
      - 
      - 
      - String to match in the first 5120 bytes of the response
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - port
      - Int
      - .. fa:: times
      - 80
      - 
      - Port
    * - request_interval_fast
      - Boolean
      - .. fa:: times
      - False
      - 
      - Fast request interval will only wait 10 seconds between each health check response instead of the standard 30
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - resource_path
      - String
      - .. fa:: times
      - /
      - String such as '/health.html'. Path should return a 2xx or 3xx. Query string parameters are allowed: '/search?query=health'
      - Resource Path
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



EventsRule
-----------


    Events Rule
    

.. _EventsRule:

.. list-table:: :guilabel:`EventsRule`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - schedule_expression
      - String
      - .. fa:: check
      - 
      - 
      - Schedule Expression
    * - targets
      - List of Strings
      - .. fa:: check
      - 
      - 
      - The AWS Resources that are invoked when the Rule is triggered.
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



EBS
----


    Elastic Block Store Volume
    

.. _EBS:

.. list-table:: :guilabel:`EBS`
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
      - 
      - 
      - Availability Zone to create Volume in.
    * - change_protected
      - Boolean
      - .. fa:: times
      - False
      - 
      - Boolean indicating whether this resource can be modified or not.
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - True
      - 
      - Boolean indicating whether DNS record sets will be created.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - order
      - Int
      - .. fa:: times
      - 0
      - 
      - The order in which the resource will be deployed
    * - resource_fullname
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Fullname
    * - resource_name
      - String
      - .. fa:: times
      - 
      - 
      - AWS Resource Name
    * - size_gib
      - Int
      - .. fa:: check
      - 10
      - 
      - Volume Size in GiB
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - type
      - String
      - .. fa:: times
      - 
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - volume_type
      - String
      - .. fa:: times
      - gp2
      - Must be one of: gp2 | io1 | sc1 | st1 | standard
      - Volume Type



Secrets
=======


SecretsManager
---------------

Secrets Manager

.. _SecretsManager:

.. list-table:: :guilabel:`SecretsManager` |bars| Container where the keys are the ``name`` field.
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
    * - users
      - Container of IAMUser_ AIM schemas
      - .. fa:: times
      - 
      - 
      - IAM Users



IAMUser
^^^^^^^^


    IAM User
    

.. _IAMUser:

.. list-table:: :guilabel:`IAMUser`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - account
      - TextReference
      - .. fa:: check
      - 
      - 
      - AIM account reference to install this user
    * - account_whitelist
      - CommaList
      - .. fa:: times
      - 
      - 
      - Comma separated list of AIM AWS account names this user has access to
    * - console_access_enabled
      - Boolean
      - .. fa:: check
      - 
      - 
      - Console Access Boolean
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - IAM User Description
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - permissions
      - Container of IAMUserPermissions_ AIM schemas
      - .. fa:: times
      - 
      - 
      - AIM IAM User Permissions
    * - programmatic_access
      - IAMUserProgrammaticAccess_ AIM schema
      - .. fa:: times
      - 
      - 
      - Programmatic Access
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - username
      - String
      - .. fa:: times
      - 
      - 
      - IAM Username



IAMUserProgrammaticAccess
^^^^^^^^^^^^^^^^^^^^^^^^^^


    IAM User Programmatic Access Configuration
    

.. _IAMUserProgrammaticAccess:

.. list-table:: :guilabel:`IAMUserProgrammaticAccess`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - access_key_1_version
      - Int
      - .. fa:: times
      - 0
      - 
      - Access key version id
    * - access_key_2_version
      - Int
      - .. fa:: times
      - 0
      - 
      - Access key version id
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled



IAMUserPermissions
^^^^^^^^^^^^^^^^^^^


    Group of IAM User Permissions
    

.. _IAMUserPermissions:

.. list-table:: :guilabel:`IAMUserPermissions` |bars| Container where the keys are the ``name`` field.
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



Role
-----



.. _Role:

.. list-table:: :guilabel:`Role`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - assume_role_policy
      - AssumeRolePolicy_ AIM schema
      - .. fa:: times
      - 
      - 
      - Assume role policy
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - global_role_name
      - Boolean
      - .. fa:: times
      - False
      - 
      - Role name is globally unique and will not be hashed
    * - instance_profile
      - Boolean
      - .. fa:: times
      - False
      - 
      - Instance profile
    * - managed_policy_arns
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Managed policy ARNs
    * - max_session_duration
      - Int
      - .. fa:: times
      - 3600
      - The maximum session duration (in seconds)
      - Maximum session duration
    * - path
      - String
      - .. fa:: times
      - /
      - 
      - Path
    * - permissions_boundary
      - String
      - .. fa:: times
      - 
      - Must be valid ARN
      - Permissions boundary ARN
    * - policies
      - List of Policy_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Policies
    * - role_name
      - String
      - .. fa:: times
      - 
      - 
      - Role name
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AssumeRolePolicy
^^^^^^^^^^^^^^^^^



.. _AssumeRolePolicy:

.. list-table:: :guilabel:`AssumeRolePolicy`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - aws
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of AWS Principles
    * - effect
      - String
      - .. fa:: times
      - 
      - 
      - Effect
    * - service
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Service



Policy
^^^^^^^



.. _Policy:

.. list-table:: :guilabel:`Policy`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Policy name
    * - statement
      - List of Statement_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Statements



Statement
^^^^^^^^^^



.. _Statement:

.. list-table:: :guilabel:`Statement`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - action
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Action(s)
    * - effect
      - String
      - .. fa:: times
      - 
      - Must be one of: 'Allow', 'Deny'
      - Effect
    * - resource
      - List of Strings
      - .. fa:: times
      - 
      - 
      - Resrource(s)
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



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
      - unset
      - Must be one of: 'performance', 'security' or 'health'
      - Classification
    * - description
      - String
      - .. fa:: times
      - 
      - 
      - Description
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - notification_groups
      - List of Strings
      - .. fa:: times
      - 
      - 
      - List of notificationn groups the alarm is subscribed to.
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
    * - runbook_url
      - String
      - .. fa:: times
      - 
      - 
      - Runbook URL
    * - severity
      - String
      - .. fa:: times
      - low
      - Must be one of: 'low', 'critical'
      - Severity
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AlarmSet
---------


    A collection of Alarms
    

.. _AlarmSet:

.. list-table:: :guilabel:`AlarmSet` |bars| Container where the keys are the ``name`` field.
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - 
      - 
      - Alarm Notifications
    * - resource_type
      - String
      - .. fa:: times
      - 
      - Must be a valid AWS resource type
      - Resource type
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AlarmSets
----------


    A collection of AlarmSets
    

.. _AlarmSets:

.. list-table:: :guilabel:`AlarmSets` |bars| Container where the keys are the ``name`` field.
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



Dimension
----------


    A dimension of a metric
    

.. _Dimension:

.. list-table:: :guilabel:`Dimension`
    :widths: 15 8 4 12 15 30
    :header-rows: 1

    * - Field name
      - Type
      - Req?
      - Default
      - Constraints
      - Purpose
    * - name
      - String
      - .. fa:: times
      - 
      - 
      - Dimension name
    * - value
      - TextReference
      - .. fa:: times
      - 
      - 
      - Value to look-up dimension



CloudWatchLogSource
--------------------


    Log source for a CloudWatch agent
    

.. _CloudWatchLogSource:

.. list-table:: :guilabel:`CloudWatchLogSource`
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
      - .. fa:: times
      - utf-8
      - 
      - Encoding
    * - expire_events_after_days
      - String
      - .. fa:: times
      - 
      - 
      - Expire Events After. Retention period of logs in this group
    * - log_stream_name
      - String
      - .. fa:: times
      - 
      - CloudWatch Log Stream name
      - Log stream name
    * - multi_line_start_pattern
      - String
      - .. fa:: times
      - 
      - 
      - Multi-line start pattern
    * - path
      - String
      - .. fa:: check
      - 
      - Must be a valid filesystem path expression. Wildcard * is allowed.
      - Path
    * - timestamp_format
      - String
      - .. fa:: times
      - 
      - 
      - Timestamp format
    * - timezone
      - String
      - .. fa:: times
      - Local
      - Must be one of: 'Local', 'UTC'
      - Timezone
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title



AlarmNotifications
-------------------


    Alarm Notifications
    

.. _AlarmNotifications:

.. list-table:: :guilabel:`AlarmNotifications` |bars| Container where the keys are the ``name`` field.
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



AlarmNotification
------------------


    Alarm Notification
    

.. _AlarmNotification:

.. list-table:: :guilabel:`AlarmNotification`
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
      - .. fa:: times
      - 
      - Must be one of: 'performance', 'security', 'health' or ''.
      - Classification filter
    * - groups
      - List of Strings
      - .. fa:: check
      - 
      - 
      - List of groups
    * - severity
      - String
      - .. fa:: times
      - 
      - Must be one of: 'low', 'critical'
      - Severity filter
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title


