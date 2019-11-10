
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
      - .. fa:: times
      - None
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
      - None
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
      - None
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
      - None
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




|bars| Container where the keys are the ``name`` field.


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
      - .. fa:: times
      - 0
      - 
      - Availability Zones
    * - aws_account
      - TextReference
      - .. fa:: times
      - None
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
      - None
      - 
      - VPC



VPC
----


    AWS Resource: VPC
    

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
      - None
      - 
      - VPC Peering
    * - private_hosted_zone
      - PrivateHostedZone_ AIM schema
      - .. fa:: times
      - None
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
      - None
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - network_environment
      - TextReference
      - .. fa:: times
      - None
      - 
      - Network Environment Reference
    * - peer_account_id
      - String
      - .. fa:: times
      - None
      - 
      - Remote peer AWS account Id
    * - peer_region
      - String
      - .. fa:: times
      - None
      - 
      - Remote peer AWS region
    * - peer_role_name
      - String
      - .. fa:: times
      - None
      - 
      - Remote peer role name
    * - peer_vpcid
      - String
      - .. fa:: times
      - None
      - 
      - Remote peer VPC Id
    * - routing
      - List of VPCPeeringRoute_ AIM schemas
      - .. fa:: check
      - None
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
      - .. fa:: times
      - 
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - segment
      - TextReference
      - .. fa:: times
      - None
      - 
      - Segment reference



NATGateway
-----------


    AWS Resource: NAT Gateway
    


|bars| Container where the keys are the ``name`` field.


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
      - String
      - .. fa:: times
      - all
      - 
      - Availability Zones to launch instances in.
    * - default_route_segments
      - List of Strings
      - .. fa:: times
      - None
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
      - None
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
    


|bars| Container where the keys are the ``name`` field.


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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled



PrivateHostedZone
------------------


    AWS Resource: Private Hosted Zone
    

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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - name
      - String
      - .. fa:: times
      - None
      - 
      - Hosted zone name
    * - vpc_associations
      - List of Strings
      - .. fa:: times
      - None
      - 
      - List of VPC Ids



Segment
--------


    AWS Resource: Segment
    

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
      - .. fa:: times
      - None
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
      - None
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
      - None
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
      - None
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
      - None
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
    * - source_security_group
      - TextReference
      - .. fa:: times
      - None
      - An AIM Reference to a SecurityGroup
      - Source Security Group Reference
    * - to_port
      - Int
      - .. fa:: times
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - To port


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


|bars| Container where the keys are the ``name`` field.


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


    Application : An Application Engine configuration to run in a specific Environment
    


|bars| Container where the keys are the ``name`` field.


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
      - None
      - 
      - 
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - None
      - 
      - 
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - None
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


|bars| Container where the keys are the ``name`` field.


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

A collection of Application Resources


|bars| Container where the keys are the ``name`` field.


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
    * - dns_enabled
      - Boolean
      - .. fa:: times
      - None
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
      - None
      - 
      - The order in which the group will be deployed
    * - resources
      - Container of Resources_ AIM schemas
      - .. fa:: check
      - None
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
      - None
      - 
      - Type



Resources
----------

A collection of Application Resources


|bars| Container where the keys are the ``name`` field.


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


    AWS Resource to support an Application
    

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
      - None
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

.. list-table::
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
      - None
      - Must be one of 'HEADER' to read the API key from the X-API-Key header of a request or 'AUTHORIZER' to read the API key from the UsageIdentifierKey from a Lambda authorizer.
      - API Key Source Type
    * - binary_media_types
      - List of Strings
      - .. fa:: times
      - None
      - Duplicates are not allowed. Slashes must be escaped with ~1. For example, image/png would be image~1png in the BinaryMediaTypes list.
      - Binary Media Types. The list of binary media types that are supported by the RestApi resource, such as image/png or application/octet-stream. By default, RestApi supports only UTF-8-encoded text payloads.
    * - body
      - String
      - .. fa:: times
      - None
      - Must be valid JSON.
      - Body. An OpenAPI specification that defines a set of RESTful APIs in JSON or YAML format. For YAML templates, you can also provide the specification in YAML format.
    * - body_file_location
      - StringFileReference
      - .. fa:: times
      - None
      - Must be valid path to a valid JSON document.
      - Path to a file containing the Body.
    * - body_s3_location
      - String
      - .. fa:: times
      - None
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
      - None
      - 
      - CloneFrom. The ID of the RestApi resource that you want to clone.
    * - description
      - String
      - .. fa:: times
      - None
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
      - None
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
      - None
      - 
      - 
    * - minimum_compression_size
      - Int
      - .. fa:: times
      - None
      - A non-negative integer between 0 and 10485760 (10M) bytes, inclusive.
      - An integer that is used to enable compression on an API. When compression is enabled, compression or decompression is not applied on the payload if the payload size is smaller than this value. Setting it to zero allows compression for any payload size.
    * - models
      - Container of ApiGatewayModels_ AIM schemas
      - .. fa:: times
      - None
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
      - None
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
      - None
      - 
      - 
    * - stages
      - Container of ApiGatewayStages_ AIM schemas
      - .. fa:: times
      - None
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
      - None
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



ApiGatewayMethods
^^^^^^^^^^^^^^^^^^

Container for API Gateway Method objects


|bars| Container where the keys are the ``name`` field.


.. _ApiGatewayMethods:

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



ApiGatewayModels
^^^^^^^^^^^^^^^^^

Container for API Gateway Model objects


|bars| Container where the keys are the ``name`` field.


.. _ApiGatewayModels:

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



ApiGatewayResources
^^^^^^^^^^^^^^^^^^^^

Container for API Gateway Resource objects


|bars| Container where the keys are the ``name`` field.


.. _ApiGatewayResources:

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



ApiGatewayStages
^^^^^^^^^^^^^^^^^

Container for API Gateway Stage objects


|bars| Container where the keys are the ``name`` field.


.. _ApiGatewayStages:

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



LBApplication
--------------


.. sidebar:: LBApplication Prescribed Automation

    ``enable_access_logs``: This field will turn on access logs for the load balancer, and will automatically create
    an S3 Bucket with permissions for AWS to write to that bucket.

    ``access_logs_bucket``: Use an existing S3 Bucket instead of automatically creating a new one.
    Remember that if you supply your own S3 Bucket, you are responsible for ensuring that the bucket policy for
    it grants AWS the `s3:PutObject` permission.

The ``LBApplication`` resource type creates an Application Load Balancer. Use load balancers to route traffic from
the internet to your web servers.

    


|bars| Container where the keys are the ``name`` field.


.. _LBApplication:

.. list-table::
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
      - None
      - 
      - Bucket to store access logs in
    * - access_logs_prefix
      - String
      - .. fa:: times
      - None
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
      - None
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
      - None
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
      - None
      - 
      - Listeners
    * - monitoring
      - MonitorConfig_ AIM schema
      - .. fa:: times
      - None
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
      - None
      - 
      - Scheme
    * - security_groups
      - List of Strings
      - .. fa:: times
      - None
      - 
      - Security Groups
    * - segment
      - String
      - .. fa:: times
      - None
      - 
      - Id of the segment stack
    * - target_groups
      - Container of TargetGroup_ AIM schemas
      - .. fa:: times
      - None
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
      - None
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



DNS
^^^^



.. _DNS:

.. list-table::
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
      - None
      - 
      - Domain name
    * - hosted_zone
      - TextReference
      - .. fa:: times
      - None
      - 
      - Hosted Zone Id
    * - ssl_certificate
      - TextReference
      - .. fa:: times
      - None
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

.. list-table::
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
      - None
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - None
      - 
      - Protocol
    * - redirect
      - PortProtocol_ AIM schema
      - .. fa:: times
      - None
      - 
      - Redirect
    * - rules
      - Container of ListenerRule_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Container of listener rules
    * - ssl_certificates
      - List of Strings
      - .. fa:: times
      - None
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
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - host
      - String
      - .. fa:: times
      - None
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
      - None
      - 
      - The host to redirect to
    * - rule_type
      - String
      - .. fa:: times
      - None
      - 
      - Type of Rule
    * - target_group
      - String
      - .. fa:: times
      - None
      - 
      - Target group name



PortProtocol
^^^^^^^^^^^^^

Port and Protocol

.. _PortProtocol:

.. list-table::
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
      - None
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - None
      - 
      - Protocol



TargetGroup
^^^^^^^^^^^^

Target Group

.. _TargetGroup:

.. list-table::
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
      - None
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
      - None
      - 
      - Health check HTTP codes
    * - health_check_interval
      - Int
      - .. fa:: times
      - None
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
      - None
      - 
      - Health check timeout
    * - healthy_threshold
      - Int
      - .. fa:: times
      - None
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
      - None
      - 
      - Port
    * - protocol
      - Choice
      - .. fa:: times
      - None
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
      - None
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources
    * - unhealthy_threshold
      - Int
      - .. fa:: times
      - None
      - 
      - Unhealthy threshold



Secrets
=======


SecretsManager
---------------

Secrets Manager


|bars| Container where the keys are the ``name`` field.


.. _SecretsManager:

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
    


|bars| Container where the keys are the ``name`` field.


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



EnvironmentDefault
-------------------


    Default values for an Environment's configuration
    


|bars| Container where the keys are the ``name`` field.


.. _EnvironmentDefault:

.. list-table::
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
      - None
      - 
      - Alarm Sets
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - None
      - 
      - Application container
    * - network
      - Container of Network_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Network
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - None
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
    


|bars| Container where the keys are the ``name`` field.


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
    * - alarm_sets
      - Container of AlarmSets_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Alarm Sets
    * - applications
      - Container of ApplicationEngines_ AIM schemas
      - .. fa:: check
      - None
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
      - None
      - 
      - Network
    * - secrets_manager
      - Container of SecretsManager_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Secrets Manager
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title


Resources
=========

Resources need to be documented.

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


    A CloudWatch Alarm
    

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
    * - actions_enabled
      - Boolean
      - .. fa:: times
      - None
      - 
      - Actions Enabled
    * - alarm_actions
      - List of Strings
      - .. fa:: times
      - None
      - 
      - Alarm Actions
    * - alarm_description
      - String
      - .. fa:: times
      - None
      - Valid JSON document with AIM fields.
      - Alarm Description
    * - classification
      - String
      - .. fa:: check
      - unset
      - Must be one of: 'performance', 'security' or 'health'
      - Classification
    * - comparison_operator
      - String
      - .. fa:: times
      - None
      - Must be one of: 'GreaterThanThreshold','GreaterThanOrEqualToThreshold', 'LessThanThreshold', 'LessThanOrEqualToThreshold'
      - Comparison operator
    * - description
      - String
      - .. fa:: times
      - None
      - 
      - Description
    * - dimensions
      - List of Dimension_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Dimensions
    * - enable_insufficient_data_actions
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable Actions when alarm transitions to the INSUFFICIENT_DATA state.
    * - enable_ok_actions
      - Boolean
      - .. fa:: times
      - False
      - 
      - Enable Actions when alarm transitions to the OK state.
    * - enabled
      - Boolean
      - .. fa:: times
      - False
      - Could be deployed to AWS
      - Enabled
    * - evaluate_low_sample_count_percentile
      - String
      - .. fa:: times
      - None
      - Must be one of `evaluate` or `ignore`.
      - Evaluate low sample count percentile
    * - evaluation_periods
      - Int
      - .. fa:: times
      - None
      - 
      - Evaluation periods
    * - extended_statistic
      - String
      - .. fa:: times
      - None
      - A value between p0.0 and p100.
      - Extended statistic
    * - metric_name
      - String
      - .. fa:: check
      - None
      - 
      - Metric name
    * - namespace
      - String
      - .. fa:: times
      - None
      - 
      - Namespace
    * - notification_groups
      - List of Strings
      - .. fa:: times
      - None
      - 
      - List of notificationn groups the alarm is subscribed to.
    * - notifications
      - Container of AlarmNotifications_ AIM schemas
      - .. fa:: times
      - None
      - 
      - Alarm Notifications
    * - period
      - Int
      - .. fa:: times
      - None
      - 
      - Period in seconds
    * - runbook_url
      - String
      - .. fa:: times
      - None
      - 
      - Runbook URL
    * - severity
      - String
      - .. fa:: times
      - low
      - Must be one of: 'low', 'critical'
      - Severity
    * - statistic
      - String
      - .. fa:: times
      - None
      - Must be one of `Maximum`, `SampleCount`, `Sum`, `Minimum`, `Average`.
      - Statistic
    * - threshold
      - Float
      - .. fa:: times
      - None
      - 
      - Threshold
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title
    * - treat_missing_data
      - String
      - .. fa:: times
      - None
      - Must be one of `breaching`, `notBreaching`, `ignore` or `missing`.
      - Treat missing data
    * - type
      - String
      - .. fa:: times
      - None
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



AlarmSet
---------


    A collection of Alarms
    


|bars| Container where the keys are the ``name`` field.


.. _AlarmSet:

.. list-table::
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
      - None
      - 
      - Alarm Notifications
    * - resource_type
      - String
      - .. fa:: times
      - None
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
    


|bars| Container where the keys are the ``name`` field.


.. _AlarmSets:

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



Dimension
----------


    A dimension of a metric
    

.. _Dimension:

.. list-table::
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
      - None
      - 
      - Dimension name
    * - value
      - TextReference
      - .. fa:: times
      - None
      - 
      - Value to look-up dimension



CloudWatchLogSource
--------------------


    Log source for a CloudWatch agent
    

.. _CloudWatchLogSource:

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
    


|bars| Container where the keys are the ``name`` field.


.. _AlarmNotifications:

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



AlarmNotification
------------------


    Alarm Notification
    

.. _AlarmNotification:

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
      - .. fa:: times
      - 
      - Must be one of: 'performance', 'security', 'health' or ''.
      - Classification filter
    * - groups
      - List of Strings
      - .. fa:: check
      - None
      - 
      - List of groups
    * - severity
      - String
      - .. fa:: times
      - None
      - Must be one of: 'low', 'critical'
      - Severity filter
    * - title
      - String
      - .. fa:: times
      - 
      - 
      - Title


