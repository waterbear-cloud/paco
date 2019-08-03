
.. _aim-config:

AIM Configuration Overview
==========================

AIM configuration is intended to be a complete declarative description of an Infrastructure-as-Code
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

 * ``aim.ref``: Config reference

 * ``aim.ref function``: Function reference

References are in the format:

``type.ref name.seperated.by.dots``

In addition, the ``aim.sub`` will indicate a substitution.

aim.ref netenv
----------

NetworkEnvironment references refer to values in a NetworkEnvironment.

The first part of the reference will be a filename of a file in the NetworkEnvironments directory.

The second part can be either ``applications`` or ``network``.

The following parts will then continue to walk down the tree by key name. The final part will
be the name of a field. This final part can sometimes be a field name that you don't supply
in your configuration, and is instead can be generated by the AIM Engine after it has provisioned
the resource in AWS.

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
                            source_security_group_id: aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb.id

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
                                - aim.ref netenv.my-aim-example.applications.app.groups.site.resources.cert.arn


aim.ref resource
-----------

If you need to refer to a global resource created in the Resources directory, use a ``aim.ref resource``.

In the example below, the ``hosted_zone_id`` of a Route53 record is looked up.

.. code-block:: yaml

    # NetworkEnvironments/my-aim-example.yaml

    applications:
        app:
            groups:
                site:
                    alb:
                        dns:
                        - hosted_zone_id: aim.ref resource.route53.example.id

    # Resources/Route53.yaml

    hosted_zones:
    example:
        enabled: true
        domain_name: example.com
        account: aim.ref accounts.prod


aim.ref
----------

If you want to refer to an AWS Account in the Accounts directory, use ``aim.ref``.

These are useful to override in the environments section in a NetworkEnvironment file
to control which account and environment should be deployed to:

.. code-block:: yaml

    environments:
        dev:
            network:
                aws_account: aim.ref accounts.dev

aim.ref function
------------

A reference dynamically resolved at runtime. Currently can only look-up AMI IDs.
Can be either ``aws.ec2.ami.latest.amazon-linux-2`` or ``aws.ec2.ami.latest.amazon-linux``.

.. code-block:: yaml

    web:
        type: ASG
        instance_ami: aim.ref function.aws.ec2.ami.latest.amazon-linux-2

aim.sub
-------

Can be used to look-up a value and substitute the results into a templated string.


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
      - Supported types: 'AWS'
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
      - Each string in the list must contain only digits.
      - A list of account ids to add to the Master account's AWS Organization
    * - region
      - String
      - .. fa:: check
      - us-west-2
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
                                  source_security_group_id: aim.ref netenv.my-aim-example.network.vpc.security_groups.app.lb.id
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
      - .. fa:: check
      - 0
      -
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
      - Two level deep dictionary: first key is Application name, second key is Resource name.
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
      - Every list item must be an EgressRule
      - Egress
    * - group_description
      - String
      - .. fa:: check
      -
      - Up to 255 characters in length
      - Group description
    * - group_name
      - String
      - .. fa:: check
      -
      - Up to 255 characters in length. Cannot start with sg-.
      - Group name
    * - ingress
      - List of IngressRule_ AIM schemas
      - .. fa:: check
      - []
      - Every list item must be an IngressRule
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
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: check
      -
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
    * - description
      - String
      - .. fa:: check
      -
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
    * - from_port
      - Int
      - .. fa:: check
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
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
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
    * - source_security_group_id
      - TextReference
      - .. fa:: times
      - None
      - An AIM Reference to a SecurityGroup
      - Source Security Group
    * - to_port
      - Int
      - .. fa:: check
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
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
      - A valid CIDR v4 block or an empty string
      - CIDR IP
    * - cidr_ip_v6
      - String
      - .. fa:: check
      -
      - A valid CIDR v6 block or an empty string
      - CIDR IP v6
    * - description
      - String
      - .. fa:: check
      -
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - Description
    * - from_port
      - Int
      - .. fa:: check
      - -1
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
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
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - IP Protocol
    * - source_security_group_id
      - TextReference
      - .. fa:: times
      - None
      - An AIM Reference to a SecurityGroup
      - Source Security Group
    * - to_port
      - Int
      - .. fa:: check
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
      - Container of ResourceGroups_ AIM schemas
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
      - .. fa:: times
      - 0
      -
      - The order in which the resource will be deployed
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
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - Type of Resources



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
    * - title
      - String
      - .. fa:: times
      -
      -
      - Title



EnvironmentRegion
------------------



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
      - Must be one of: 'performance', 'security' or 'health'
      - Classification
    * - comparison_operator
      - String
      - .. fa:: check
      - None
      - Must be one of: 'GreaterThanThreshold','GreaterThanOrEqualToThreshold', 'LessThanThreshold', 'LessThanOrEqualToThreshold'
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
      - Must be one of: 10, 30, 60, 300, 900, 3600, 21600, 90000
      - Period in seconds
    * - severity
      - String
      - .. fa:: check
      - low
      - Must be one of: 'low', 'critical'
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
      - Must be a valid filesystem path expression. Wildcard * is allowed.
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
      - Must be one of: 'Local', 'UTC'
      - Timezone


