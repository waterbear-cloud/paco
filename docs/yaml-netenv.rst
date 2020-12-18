
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


NetworkEnvironment
^^^^^^^^^^^^^^^^^^^

NetworkEnvironment

.. _NetworkEnvironment:

.. list-table:: :guilabel:`NetworkEnvironment`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Deployable`_, `Named`_, `Title`_


Network
^^^^^^^^



.. _Network:

.. list-table:: :guilabel:`Network`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - availability_zones
      - Int
      - Availability Zones
      - 
      - 0
    * - aws_account
      - PacoReference
      - Account this Network belongs to
      - Paco Reference to `Account`_.
      - 
    * - vpc
      - Object<VPC_>
      - VPC
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


VPC
^^^^

VPC

.. _VPC:

.. list-table:: :guilabel:`VPC`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cidr
      - String
      - CIDR
      - 
      - 
    * - enable_dns_hostnames
      - Boolean
      - Enable DNS Hostnames
      - 
      - False
    * - enable_dns_support
      - Boolean
      - Enable DNS Support
      - 
      - False
    * - enable_internet_gateway
      - Boolean
      - Internet Gateway
      - 
      - False
    * - nat_gateway
      - Container<NATGateways_> |star|
      - NAT Gateways
      - 
      - 
    * - peering
      - Container<VPCPeerings_> |star|
      - VPC Peering
      - 
      - 
    * - private_hosted_zone
      - Object<PrivateHostedZone_>
      - Private hosted zone
      - 
      - 
    * - security_groups
      - Container<SecurityGroupSets_> |star|
      - Security Group Sets
      - Security Groups Sets are containers for SecurityGroups containers.
      - 
    * - segments
      - Container<Segments_> |star|
      - Segments
      - 
      - 
    * - vpn_gateway
      - Container<VPNGateways_> |star|
      - VPN Gateways
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


VPCPeerings
^^^^^^^^^^^^

Container for `VPCPeering`_ objects.

.. _VPCPeerings:

.. list-table:: :guilabel:`VPCPeerings` |bars| Container<`VPCPeering`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


VPCPeering
^^^^^^^^^^^


VPC Peering
    

.. _VPCPeering:

.. list-table:: :guilabel:`VPCPeering`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - network_environment
      - PacoReference
      - Network Environment Reference
      - Paco Reference to `NetworkEnvironment`_.
      - 
    * - peer_account_id
      - String
      - Remote peer AWS account Id
      - 
      - 
    * - peer_region
      - String
      - Remote peer AWS region
      - 
      - 
    * - peer_role_name
      - String
      - Remote peer role name
      - 
      - 
    * - peer_vpcid
      - String
      - Remote peer VPC Id
      - 
      - 
    * - routing
      - List<VPCPeeringRoute_> |star|
      - Peering routes
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


VPCPeeringRoute
^^^^^^^^^^^^^^^^


VPC Peering Route
    

.. _VPCPeeringRoute:

.. list-table:: :guilabel:`VPCPeeringRoute`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cidr
      - String
      - CIDR IP
      - A valid CIDR v4 block or an empty string
      - 
    * - segment
      - PacoReference
      - Segment
      - Paco Reference to `Segment`_.
      - 



NATGateways
^^^^^^^^^^^^

Container for `NATGateway`_ objects.

.. _NATGateways:

.. list-table:: :guilabel:`NATGateways` |bars| Container<`NATGateway`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


NATGateway
^^^^^^^^^^^

NAT Gateway

.. _NATGateway:

.. list-table:: :guilabel:`NATGateway`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - availability_zone
      - String
      - Availability Zones to launch instances in.
      - Can be 'all' or number of AZ: 1, 2, 3, 4 ...
      - all
    * - default_route_segments
      - List<PacoReference>
      - Default Route Segments
      - Paco Reference to `Segment`_.
      - 
    * - ec2_instance_type
      - String
      - EC2 Instance Type
      - 
      - t2.nano
    * - ec2_key_pair
      - PacoReference
      - EC2 key pair
      - Paco Reference to `EC2KeyPair`_.
      - 
    * - security_groups
      - List<PacoReference>
      - Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - PacoReference
      - Segment
      - Paco Reference to `Segment`_.
      - 
    * - type
      - String
      - NAT Gateway type
      - 
      - Managed

*Base Schemas* `Deployable`_, `Named`_, `Title`_


VPNGateways
^^^^^^^^^^^^

Container for `VPNGateway`_ objects.

.. _VPNGateways:

.. list-table:: :guilabel:`VPNGateways` |bars| Container<`VPNGateway`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


VPNGateway
^^^^^^^^^^^

VPN Gateway

.. _VPNGateway:

.. list-table:: :guilabel:`VPNGateway`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Deployable`_, `Named`_, `Title`_


PrivateHostedZone
^^^^^^^^^^^^^^^^^^

Private Hosted Zone

.. _PrivateHostedZone:

.. list-table:: :guilabel:`PrivateHostedZone`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Hosted zone name
      - 
      - 
    * - vpc_associations
      - List<String>
      - List of VPC Ids
      - 
      - 

*Base Schemas* `Deployable`_


Segments
^^^^^^^^^

Container for `Segment`_ objects.

.. _Segments:

.. list-table:: :guilabel:`Segments` |bars| Container<`Segment`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


Segment
^^^^^^^^


Segment
    

.. _Segment:

.. list-table:: :guilabel:`Segment`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - az1_cidr
      - String
      - Availability Zone 1 CIDR
      - 
      - 
    * - az2_cidr
      - String
      - Availability Zone 2 CIDR
      - 
      - 
    * - az3_cidr
      - String
      - Availability Zone 3 CIDR
      - 
      - 
    * - az4_cidr
      - String
      - Availability Zone 4 CIDR
      - 
      - 
    * - az5_cidr
      - String
      - Availability Zone 5 CIDR
      - 
      - 
    * - az6_cidr
      - String
      - Availability Zone 6 CIDR
      - 
      - 
    * - internet_access
      - Boolean
      - Internet Access
      - 
      - False

*Base Schemas* `Deployable`_, `Named`_, `Title`_


SecurityGroupSets
^^^^^^^^^^^^^^^^^^

Container for `SecurityGroups`_ objects.

.. _SecurityGroupSets:

.. list-table:: :guilabel:`SecurityGroupSets` |bars| Container<`SecurityGroups`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


SecurityGroups
^^^^^^^^^^^^^^^

Container for `SecurityGroup`_ objects.

.. _SecurityGroups:

.. list-table:: :guilabel:`SecurityGroups` |bars| Container<`SecurityGroup`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


SecurityGroup
^^^^^^^^^^^^^^


AWS Resource: Security Group
    

.. _SecurityGroup:

.. list-table:: :guilabel:`SecurityGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - egress
      - List<EgressRule_>
      - Egress
      - Every list item must be an EgressRule
      - 
    * - group_description
      - String
      - Group description
      - Up to 255 characters in length
      - 
    * - group_name
      - String
      - Group name
      - Up to 255 characters in length. Cannot start with sg-.
      - 
    * - ingress
      - List<IngressRule_>
      - Ingress
      - Every list item must be an IngressRule
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


EgressRule
^^^^^^^^^^^

Security group egress

.. _EgressRule:

.. list-table:: :guilabel:`EgressRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - destination_security_group
      - PacoReference|String
      - Destination Security Group Reference
      - A Paco reference to a SecurityGroup Paco Reference to `SecurityGroup`_. String Ok.
      - 

*Base Schemas* `SecurityGroupRule`_, `Name`_


IngressRule
^^^^^^^^^^^^

Security group ingress

.. _IngressRule:

.. list-table:: :guilabel:`IngressRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - source_security_group
      - PacoReference|String
      - Source Security Group Reference
      - A Paco Reference to a SecurityGroup Paco Reference to `SecurityGroup`_. String Ok.
      - 

*Base Schemas* `SecurityGroupRule`_, `Name`_

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


ApplicationEngines
^^^^^^^^^^^^^^^^^^^

A container for Application Engines

.. _ApplicationEngines:

.. list-table:: :guilabel:`ApplicationEngines` |bars| Container<`ApplicationEngine`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


Application
^^^^^^^^^^^^


An Application is groups of cloud resources to support a workload.
    

.. _Application:

.. list-table:: :guilabel:`Application`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `DNSEnablable`_, `Deployable`_, `ApplicationEngine`_, `Monitorable`_, `Named`_, `Notifiable`_, `Title`_


ResourceGroups
^^^^^^^^^^^^^^^

A container of Application `ResourceGroup`_ objects.

.. _ResourceGroups:

.. list-table:: :guilabel:`ResourceGroups` |bars| Container<`ResourceGroup`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


ResourceGroup
^^^^^^^^^^^^^^

A group of `Resources`_ to support an `Application`_.

.. _ResourceGroup:

.. list-table:: :guilabel:`ResourceGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dns_enabled
      - Boolean
      - 
      - 
      - 
    * - order
      - Int |star|
      - The order in which the group will be deployed
      - 
      - 
    * - resources
      - Container<Resources_> |star|
      - 
      - 
      - 
    * - title
      - String
      - Title
      - 
      - 
    * - type
      - String |star|
      - Type
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_


Resources
^^^^^^^^^^

A container of Resources to support an `Application`_.

.. _Resources:

.. list-table:: :guilabel:`Resources`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_

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


Environment
^^^^^^^^^^^^


Environment
    

.. _Environment:

.. list-table:: :guilabel:`Environment`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


EnvironmentDefault
^^^^^^^^^^^^^^^^^^^


Default values for an Environment's configuration
    

.. _EnvironmentDefault:

.. list-table:: :guilabel:`EnvironmentDefault`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - applications
      - Container<ApplicationEngines_> |star|
      - Application container
      - 
      - 
    * - network
      - Container<Network_>
      - Network
      - 
      - 
    * - secrets_manager
      - Container<SecretsManager_>
      - Secrets Manager
      - 
      - 

*Base Schemas* `RegionContainer`_, `Named`_, `Title`_


EnvironmentRegion
^^^^^^^^^^^^^^^^^^


An actual provisioned Environment in a specific region.
May contains overrides of the IEnvironmentDefault where needed.
    

.. _EnvironmentRegion:

.. list-table:: :guilabel:`EnvironmentRegion`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `RegionContainer`_, `EnvironmentDefault`_, `Deployable`_, `Named`_, `Title`_

Secrets
-------


SecretsManager
^^^^^^^^^^^^^^^

Secrets Manager contains `SecretManagerApplication` objects.

.. _SecretsManager:

.. list-table:: :guilabel:`SecretsManager` |bars| Container<`SecretsManagerApplication`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


SecretsManagerApplication
^^^^^^^^^^^^^^^^^^^^^^^^^^

Container for `SecretsManagerGroup`_ objects.

.. _SecretsManagerApplication:

.. list-table:: :guilabel:`SecretsManagerApplication` |bars| Container<`SecretsManagerGroup`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


SecretsManagerGroup
^^^^^^^^^^^^^^^^^^^^

Container for `SecretsManagerSecret`_ objects.

.. _SecretsManagerGroup:

.. list-table:: :guilabel:`SecretsManagerGroup` |bars| Container<`SecretsManagerSecret`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


SecretsManagerSecret
^^^^^^^^^^^^^^^^^^^^^

Secret for the Secrets Manager.

.. _SecretsManagerSecret:

.. list-table:: :guilabel:`SecretsManagerSecret`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - Account to provision the Secret in
      - Paco Reference to `Account`_.
      - 
    * - generate_secret_string
      - Object<GenerateSecretString_>
      - Generate SecretString object
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


GenerateSecretString
^^^^^^^^^^^^^^^^^^^^^



.. _GenerateSecretString:

.. list-table:: :guilabel:`GenerateSecretString`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - exclude_characters
      - String
      - A string that includes characters that should not be included in the generated password.
      - 
      - 
    * - exclude_lowercase
      - Boolean
      - The generated password should not include lowercase letters.
      - 
      - False
    * - exclude_numbers
      - Boolean
      - The generated password should exclude digits.
      - 
      - False
    * - exclude_punctuation
      - Boolean
      - The generated password should not include punctuation characters.
      - 
      - False
    * - exclude_uppercase
      - Boolean
      - The generated password should not include uppercase letters.
      - 
      - False
    * - generate_string_key
      - String
      - The JSON key name that's used to add the generated password to the JSON structure.
      - 
      - 
    * - include_space
      - Boolean
      - The generated password can include the space character.
      - 
      - 
    * - password_length
      - Int
      - The desired length of the generated password.
      - 
      - 32
    * - require_each_included_type
      - Boolean
      - The generated password must include at least one of every allowed character type.
      - 
      - True
    * - secret_string_template
      - String
      - A properly structured JSON string that the generated password can be added to.
      - 
      - 

*Base Schemas* `Deployable`_


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


BackupVaults
^^^^^^^^^^^^^


Container for `BackupVault` objects.
    

.. _BackupVaults:

.. list-table:: :guilabel:`BackupVaults` |bars| Container<`BackupVault`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


BackupVault
^^^^^^^^^^^^


An AWS Backup Vault.
    

.. _BackupVault:

.. list-table:: :guilabel:`BackupVault`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - notification_events
      - List<String>
      - Notification Events
      - Each notification event must be one of BACKUP_JOB_STARTED, BACKUP_JOB_COMPLETED, RESTORE_JOB_STARTED, RESTORE_JOB_COMPLETED, RECOVERY_POINT_MODIFIED
      - 
    * - notification_group
      - String
      - Notification Group
      - 
      - 
    * - plans
      - Container<BackupPlans_>
      - Backup Plans
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


BackupPlans
^^^^^^^^^^^^


Container for `BackupPlan`_ objects.
    

.. _BackupPlans:

.. list-table:: :guilabel:`BackupPlans` |bars| Container<`BackupPlan`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


BackupPlan
^^^^^^^^^^^


AWS Backup Plan
    

.. _BackupPlan:

.. list-table:: :guilabel:`BackupPlan`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - plan_rules
      - List<BackupPlanRule_> |star|
      - Backup Plan Rules
      - 
      - 
    * - selections
      - List<BackupPlanSelection_>
      - Backup Plan Selections
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


BackupPlanRule
^^^^^^^^^^^^^^^



.. _BackupPlanRule:

.. list-table:: :guilabel:`BackupPlanRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - copy_actions
      - List<BackupPlanCopyActionResourceType_>
      - Copy actions
      - 
      - []
    * - lifecycle_delete_after_days
      - Int
      - Delete after days
      - 
      - 
    * - lifecycle_move_to_cold_storage_after_days
      - Int
      - Move to cold storage after days
      - If Delete after days value is set, this value must be smaller
      - 
    * - schedule_expression
      - String
      - Schedule Expression
      - Must be a valid Schedule Expression.
      - 

*Base Schemas* `Named`_, `Title`_


BackupPlanSelection
^^^^^^^^^^^^^^^^^^^^



.. _BackupPlanSelection:

.. list-table:: :guilabel:`BackupPlanSelection`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - resources
      - List<PacoReference>
      - Backup Plan Resources
      - Paco Reference to `Interface`_.
      - 
    * - tags
      - List<BackupSelectionConditionResourceType_>
      - List of condition resource types
      - 
      - 
    * - title
      - String |star|
      - Title
      - 
      - 



BackupSelectionConditionResourceType
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _BackupSelectionConditionResourceType:

.. list-table:: :guilabel:`BackupSelectionConditionResourceType`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - condition_key
      - String |star|
      - Tag Key
      - 
      - 
    * - condition_type
      - String |star|
      - Condition Type
      - String Condition operator must be one of: StringEquals, StringNotEquals, StringEqualsIgnoreCase, StringNotEqualsIgnoreCase, StringLike, StringNotLike.
      - 
    * - condition_value
      - String |star|
      - Tag Value
      - 
      - 


.. _ec2keypair: yaml-global-resources.html#ec2keypair



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



.. _account: yaml-accounts.html#account

