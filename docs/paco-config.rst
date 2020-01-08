
.. _paco-config:

*****************
YAML File Schemas
*****************

Base Schemas
============

Base Schemas are never configured by themselves, they are schemas that are inherited by other schemas.

Interface
---------

A generic placeholder for any schema.


Named
------


A name given to a cloud resource. Names identify resources and changing them
can break configuration.


.. _Named:

.. list-table:: :guilabel:`Named`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Name
      - 
      - 

*Base Schemas* `Title`_


Title
------


A title is a human-readable name. It can be as long as you want, and can change without
breaking any configuration.
    

.. _Title:

.. list-table:: :guilabel:`Title`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - title
      - String
      - Title
      - 
      - 



Name
-----


A name that can be changed or duplicated with other similar cloud resources without breaking anything.
    

.. _Name:

.. list-table:: :guilabel:`Name`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Name
      - 
      - 



Resource
---------


AWS Resource to support an Application
    

.. _Resource:

.. list-table:: :guilabel:`Resource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - change_protected
      - Boolean
      - Boolean indicating whether this resource can be modified or not.
      - 
      - False
    * - order
      - Int
      - The order in which the resource will be deployed
      - 
      - 0

*Base Schemas* `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


Deployable
-----------


Indicates if this configuration tree should be enabled or not.
    

.. _Deployable:

.. list-table:: :guilabel:`Deployable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - enabled
      - Boolean
      - Enabled
      - Could be deployed to AWS
      - False



Type
-----



.. _Type:

.. list-table:: :guilabel:`Type`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - type
      - String
      - Type of Resources
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - 



DNSEnablable
-------------

Provides a parent with an inheritable DNS enabled field

.. _DNSEnablable:

.. list-table:: :guilabel:`DNSEnablable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dns_enabled
      - Boolean
      - Boolean indicating whether DNS record sets will be created.
      - 
      - True



Monitorable
------------


A monitorable resource
    

.. _Monitorable:

.. list-table:: :guilabel:`Monitorable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - monitoring
      - Object<MonitorConfig_>
      - 
      - 
      - 



MonitorConfig
--------------


A set of metrics and a default collection interval
    

.. _MonitorConfig:

.. list-table:: :guilabel:`MonitorConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alarm_sets
      - Container<AlarmSets_>
      - Sets of Alarm Sets
      - 
      - 
    * - asg_metrics
      - List<String>
      - ASG Metrics
      - Must be one of: 'GroupMinSize', 'GroupMaxSize', 'GroupDesiredCapacity', 'GroupInServiceInstances', 'GroupPendingInstances', 'GroupStandbyInstances', 'GroupTerminatingInstances', 'GroupTotalInstances'
      - 
    * - collection_interval
      - Int
      - Collection interval
      - 
      - 60
    * - health_checks
      - Container<HealthChecks_>
      - Set of Health Checks
      - 
      - 
    * - log_sets
      - Container<CloudWatchLogSets_>
      - Sets of Log Sets
      - 
      - 
    * - metrics
      - List<Metric_>
      - Metrics
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Notifiable`_, `Title`_


RegionContainer
----------------

Container for objects which do not belong to a specific Environment.

.. _RegionContainer:

.. list-table:: :guilabel:`RegionContainer`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alarm_sets
      - Container<AlarmSets_>
      - Alarm Sets
      - 
      - 

*Base Schemas* `Named`_, `Title`_


Notifiable
-----------


A notifiable object
    

.. _Notifiable:

.. list-table:: :guilabel:`Notifiable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - notifications
      - Container<AlarmNotifications_>
      - Alarm Notifications
      - 
      - 



SecurityGroupRule
------------------



.. _SecurityGroupRule:

.. list-table:: :guilabel:`SecurityGroupRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cidr_ip
      - String
      - CIDR IP
      - A valid CIDR v4 block or an empty string
      - 
    * - cidr_ip_v6
      - String
      - CIDR IP v6
      - A valid CIDR v6 block or an empty string
      - 
    * - description
      - String
      - Description
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - 
    * - from_port
      - Int
      - From port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1
    * - port
      - Int
      - Port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1
    * - protocol
      - String
      - IP Protocol
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - 
    * - to_port
      - Int
      - To port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1

*Base Schemas* `Name`_


ApplicationEngine
------------------


Application Engine : A template describing an application
    

.. _ApplicationEngine:

.. list-table:: :guilabel:`ApplicationEngine`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - groups
      - Container<ResourceGroups_> |star|
      - 
      - 
      - 
    * - order
      - Int
      - The order in which the application will be processed
      - 
      - 0

*Base Schemas* `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Notifiable`_, `Title`_

Function
--------

A callable function that returns a value.


Accounts: accounts/\*.yaml
==========================

AWS account information is kept in the ``accounts/`` directory.
Each file in this directory will define one AWS account, the filename
will be the ``name`` of the account, with a .yml or .yaml extension.


Account
--------

Cloud account information

.. _Account:

.. list-table:: :guilabel:`Account`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account_id
      - String
      - Account ID
      - Can only contain digits.
      - 
    * - account_type
      - String
      - Account Type
      - Supported types: 'AWS'
      - AWS
    * - admin_delegate_role_name
      - String
      - Administrator delegate IAM Role name for the account
      - 
      - 
    * - admin_iam_users
      - Container<AdminIAMUser_>
      - Admin IAM Users
      - 
      - 
    * - is_master
      - Boolean
      - Boolean indicating if this a Master account
      - 
      - False
    * - organization_account_ids
      - List<String>
      - A list of account ids to add to the Master account's AWS Organization
      - Each string in the list must contain only digits.
      - 
    * - region
      - String |star|
      - Region to install AWS Account specific resources
      - Must be a valid AWS Region name
      - no-region-set
    * - root_email
      - String |star|
      - The email address for the root user of this account
      - Must be a valid email address.
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


AdminIAMUser
-------------

An AWS Account Administerator IAM User

.. _AdminIAMUser:

.. list-table:: :guilabel:`AdminIAMUser`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - username
      - String
      - IAM Username
      - 
      - 

*Base Schemas* `Deployable`_

Global Resources: resource/\*.yaml
==================================

CloudTrail: resource/cloudtrail.yaml
------------------------------------

The ``resource/cloudtrail.yaml`` file contains CloudTrails.

.. code-block:: bash

    paco provision resource.cloudtrail


.. code-block:: yaml
    :caption: Example resource/cloudtrail.yaml file

    trails:
      cloudtrail:
        region: ''
        enabled: true
        cloudwatchlogs_log_group:
          expire_events_after_days: '14'
          log_group_name: 'CloudTrail'
        enable_log_file_validation: true
        include_global_service_events: true
        is_multi_region_trail: true
        enable_kms_encryption: true
        s3_bucket_account: 'paco.ref accounts.security'
        s3_key_prefix: 'cloudtrails'

CodeCommit: resource/codecommit.yaml
-------------------------------------

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



CodeCommit
^^^^^^^^^^^


CodeCommit Service Configuration
    

.. _CodeCommit:

.. list-table:: :guilabel:`CodeCommit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - repository_groups
      - Container<CodeCommitRepositoryGroups_> |star|
      - Container of CodeCommitRepositoryGroup objects
      - 
      - 



CodeCommitRepositoryGroups
^^^^^^^^^^^^^^^^^^^^^^^^^^^


Container for `CodeCommitRepositoryGroup`_ objects.
    

.. _CodeCommitRepositoryGroups:

.. list-table:: :guilabel:`CodeCommitRepositoryGroups` |bars| Container<`CodeCommitRepositoryGroup`_>
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


CodeCommitRepositoryGroup
^^^^^^^^^^^^^^^^^^^^^^^^^^


Container for `CodeCommitRepository`_ objects.
    

.. _CodeCommitRepositoryGroup:

.. list-table:: :guilabel:`CodeCommitRepositoryGroup` |bars| Container<`CodeCommitRepository`_>
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


CodeCommitRepository
^^^^^^^^^^^^^^^^^^^^^


CodeCommit Repository
    

.. _CodeCommitRepository:

.. list-table:: :guilabel:`CodeCommitRepository`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference |star|
      - Account this repo belongs to.
      - Paco Reference to `Account`_.
      - 
    * - description
      - String
      - Repository Description
      - 
      - 
    * - region
      - String
      - AWS Region
      - 
      - 
    * - repository_name
      - String
      - Repository Name
      - 
      - 
    * - users
      - Container<CodeCommitUser_>
      - CodeCommit Users
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


CodeCommitUser
^^^^^^^^^^^^^^^


CodeCommit User
    

.. _CodeCommitUser:

.. list-table:: :guilabel:`CodeCommitUser`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - public_ssh_key
      - String
      - CodeCommit User Public SSH Key
      - 
      - 
    * - username
      - String
      - CodeCommit Username
      - 
      - 


EC2 Keypairs: resource/ec2.yaml
--------------------------------

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


EC2KeyPair
^^^^^^^^^^^


EC2 SSH Key Pair
    

.. _EC2KeyPair:

.. list-table:: :guilabel:`EC2KeyPair`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - AWS Account the key pair belongs to
      - Paco Reference to `Account`_.
      - 
    * - keypair_name
      - String |star|
      - The name of the EC2 KeyPair
      - 
      - 
    * - region
      - String |star|
      - AWS Region
      - Must be a valid AWS Region name
      - no-region-set

*Base Schemas* `Named`_, `Title`_

IAM: resource/iam.yaml
----------------------

The ``resource/iam.yaml`` file contains IAM Users. Each user account can be given
different levels of access a set of AWS accounts. For more information on how
IAM Users can be managed, see `Managing IAM Users with Paco`_.

.. code-block:: bash

    paco provision resource.iam.users


.. _Managing IAM Users with Paco: ./paco-users.html


IAMResource
^^^^^^^^^^^^


IAM Resource contains IAM Users who can login and have different levels of access to the AWS Console and API.
    

.. _IAMResource:

.. list-table:: :guilabel:`IAMResource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - users
      - Container<IAMUsers_>
      - IAM Users
      - 
      - 

*Base Schemas* `Named`_, `Title`_


IAMUsers
^^^^^^^^^


Container for `IAMUser`_ objects.
    

.. _IAMUsers:

.. list-table:: :guilabel:`IAMUsers` |bars| Container<`IAMUser`_>
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


IAMUser
^^^^^^^^


IAM User
    

.. _IAMUser:

.. list-table:: :guilabel:`IAMUser`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference |star|
      - Paco account reference to install this user
      - Paco Reference to `Account`_.
      - 
    * - account_whitelist
      - CommaList
      - Comma separated list of Paco AWS account names this user has access to
      - 
      - 
    * - console_access_enabled
      - Boolean |star|
      - Console Access Boolean
      - 
      - 
    * - description
      - String
      - IAM User Description
      - 
      - 
    * - permissions
      - Container<IAMUserPermissions_>
      - Paco IAM User Permissions
      - 
      - 
    * - programmatic_access
      - Object<IAMUserProgrammaticAccess_>
      - Programmatic Access
      - 
      - 
    * - username
      - String
      - IAM Username
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


IAMUserProgrammaticAccess
^^^^^^^^^^^^^^^^^^^^^^^^^^


IAM User Programmatic Access Configuration
    

.. _IAMUserProgrammaticAccess:

.. list-table:: :guilabel:`IAMUserProgrammaticAccess`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - access_key_1_version
      - Int
      - Access key version id
      - 
      - 0
    * - access_key_2_version
      - Int
      - Access key version id
      - 
      - 0

*Base Schemas* `Deployable`_


IAMUserPermissions
^^^^^^^^^^^^^^^^^^^


Container for IAM User Permission objects.
    

.. _IAMUserPermissions:

.. list-table:: :guilabel:`IAMUserPermissions`
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


Role
^^^^^



.. _Role:

.. list-table:: :guilabel:`Role`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - assume_role_policy
      - Object<AssumeRolePolicy_>
      - Assume role policy
      - 
      - 
    * - global_role_name
      - Boolean
      - Role name is globally unique and will not be hashed
      - 
      - False
    * - instance_profile
      - Boolean
      - Instance profile
      - 
      - False
    * - managed_policy_arns
      - List<String>
      - Managed policy ARNs
      - 
      - 
    * - max_session_duration
      - Int
      - Maximum session duration
      - The maximum session duration (in seconds)
      - 3600
    * - path
      - String
      - Path
      - 
      - /
    * - permissions_boundary
      - String
      - Permissions boundary ARN
      - Must be valid ARN
      - 
    * - policies
      - List<Policy_>
      - Policies
      - 
      - 
    * - role_name
      - String
      - Role name
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


AssumeRolePolicy
^^^^^^^^^^^^^^^^^



.. _AssumeRolePolicy:

.. list-table:: :guilabel:`AssumeRolePolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - aws
      - List<String>
      - List of AWS Principles
      - 
      - 
    * - effect
      - String
      - Effect
      - 
      - 
    * - service
      - List<String>
      - Service
      - 
      - 



Policy
^^^^^^^



.. _Policy:

.. list-table:: :guilabel:`Policy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Policy name
      - 
      - 
    * - statement
      - List<Statement_>
      - Statements
      - 
      - 



Statement
^^^^^^^^^^



.. _Statement:

.. list-table:: :guilabel:`Statement`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - action
      - List<String>
      - Action(s)
      - 
      - 
    * - effect
      - String
      - Effect
      - Must be one of: 'Allow', 'Deny'
      - 
    * - resource
      - List<String>
      - Resrource(s)
      - 
      - 

*Base Schemas* `Named`_, `Title`_

Route 53: resource/route53.yaml
-------------------------------

The ``resource/route53.yaml`` file manages AWS Route 53.


Route53Resource
^^^^^^^^^^^^^^^^


Route53 Service Configuration
    

.. _Route53Resource:

.. list-table:: :guilabel:`Route53Resource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - hosted_zones
      - Container<Route53HostedZone_>
      - Hosted Zones
      - 
      - 

*Base Schemas* `Named`_, `Title`_


Route53HostedZone
^^^^^^^^^^^^^^^^^^


Route53 Hosted Zone
    

.. _Route53HostedZone:

.. list-table:: :guilabel:`Route53HostedZone`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference |star|
      - Account this Hosted Zone belongs to
      - Paco Reference to `Account`_.
      - 
    * - domain_name
      - String |star|
      - Domain Name
      - 
      - 
    * - external_resource
      - Object<Route53HostedZoneExternalResource_>
      - External HostedZone Id Configuration
      - 
      - 
    * - parent_zone
      - String
      - Parent Hozed Zone name
      - 
      - 
    * - record_sets
      - List<Route53RecordSet_> |star|
      - List of Record Sets
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


Route53HostedZoneExternalResource
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Existing Hosted Zone configuration
    

.. _Route53HostedZoneExternalResource:

.. list-table:: :guilabel:`Route53HostedZoneExternalResource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - hosted_zone_id
      - String |star|
      - ID of an existing Hosted Zone
      - 
      - 
    * - nameservers
      - List<String> |star|
      - List of the Hosted Zones Nameservers
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


Route53RecordSet
^^^^^^^^^^^^^^^^^


Route53 Record Set
    

.. _Route53RecordSet:

.. list-table:: :guilabel:`Route53RecordSet`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - record_name
      - String |star|
      - Record Set Full Name
      - 
      - 
    * - resource_records
      - List<String> |star|
      - Record Set Values
      - 
      - 
    * - ttl
      - Int
      - Record TTL
      - 
      - 300
    * - type
      - String |star|
      - Record Set Type
      - 
      - 



SNS Topics: resource/snstopics.yaml
-----------------------------------

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


NetworkEnvironments: netenv/\*.yaml
====================================

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

NetEnv - network:
=================

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


NetworkEnvironment
-------------------


NetworkEnvironment : A template for a network.
    

.. _NetworkEnvironment:

.. list-table:: :guilabel:`NetworkEnvironment`
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
    * - vpc
      - Object<VPC_>
      - VPC
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


Network
--------



.. _Network:

.. list-table:: :guilabel:`Network`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - aws_account
      - PacoReference
      - Account this Network belongs to
      - Paco Reference to `Account`_.
      - 

*Base Schemas* `NetworkEnvironment`_, `Deployable`_, `Named`_, `Title`_


VPC
----


AWS Resource: VPC
    

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
      - Container<NATGateway_> |star|
      - NAT Gateway
      - 
      - {}
    * - peering
      - Container<VPCPeering_>
      - VPC Peering
      - 
      - 
    * - private_hosted_zone
      - Object<PrivateHostedZone_>
      - Private hosted zone
      - 
      - 
    * - security_groups
      - Dict
      - Security groups
      - Two level deep dictionary: first key is Application name, second key is Resource name.
      - {}
    * - segments
      - Container<Segment_>
      - Segments
      - 
      - 
    * - vpn_gateway
      - Container<VPNGateway_> |star|
      - VPN Gateway
      - 
      - {}

*Base Schemas* `Deployable`_, `Named`_, `Title`_


VPCPeering
-----------


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
----------------


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



NATGateway
-----------


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


VPNGateway
-----------


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

*Base Schemas* `Deployable`_


PrivateHostedZone
------------------


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


Segment
--------


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


SecurityGroup
--------------


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
-----------

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
------------

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

NetEnv - applications:
======================

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


ApplicationEngines
-------------------

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
------------


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
---------------

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
--------------

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
----------

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


NetEnv - resources:
===================

At it's heart, an Application is a collection of Resources. These are the Resources available for
applications.


ApiGatewayRestApi
------------------

An Api Gateway Rest API resource

.. _ApiGatewayRestApi:

.. list-table:: :guilabel:`ApiGatewayRestApi`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - api_key_source_type
      - String
      - API Key Source Type
      - Must be one of 'HEADER' to read the API key from the X-API-Key header of a request or 'AUTHORIZER' to read the API key from the UsageIdentifierKey from a Lambda authorizer.
      - 
    * - binary_media_types
      - List<String>
      - Binary Media Types. The list of binary media types that are supported by the RestApi resource, such as image/png or application/octet-stream. By default, RestApi supports only UTF-8-encoded text payloads.
      - Duplicates are not allowed. Slashes must be escaped with ~1. For example, image/png would be image~1png in the BinaryMediaTypes list.
      - 
    * - body
      - String
      - Body. An OpenAPI specification that defines a set of RESTful APIs in JSON or YAML format. For YAML templates, you can also provide the specification in YAML format.
      - Must be valid JSON.
      - 
    * - body_file_location
      - StringFileReference
      - Path to a file containing the Body.
      - Must be valid path to a valid JSON document.
      - 
    * - body_s3_location
      - String
      - The Amazon Simple Storage Service (Amazon S3) location that points to an OpenAPI file, which defines a set of RESTful APIs in JSON or YAML format.
      - Valid S3Location string to a valid JSON or YAML document.
      - 
    * - clone_from
      - String
      - CloneFrom. The ID of the RestApi resource that you want to clone.
      - 
      - 
    * - description
      - String
      - Description of the RestApi resource.
      - 
      - 
    * - endpoint_configuration
      - List<String>
      - Endpoint configuration. A list of the endpoint types of the API. Use this field when creating an API. When importing an existing API, specify the endpoint configuration types using the `parameters` field.
      - List of strings, each must be one of 'EDGE', 'REGIONAL', 'PRIVATE'
      - 
    * - fail_on_warnings
      - Boolean
      - Indicates whether to roll back the resource if a warning occurs while API Gateway is creating the RestApi resource.
      - 
      - False
    * - methods
      - Container<ApiGatewayMethods_>
      - 
      - 
      - 
    * - minimum_compression_size
      - Int
      - An integer that is used to enable compression on an API. When compression is enabled, compression or decompression is not applied on the payload if the payload size is smaller than this value. Setting it to zero allows compression for any payload size.
      - A non-negative integer between 0 and 10485760 (10M) bytes, inclusive.
      - 
    * - models
      - Container<ApiGatewayModels_>
      - 
      - 
      - 
    * - parameters
      - Dict
      - Parameters. Custom header parameters for the request.
      - Dictionary of key/value pairs that are strings.
      - {}
    * - policy
      - String
      - A policy document that contains the permissions for the RestApi resource, in JSON format. To set the ARN for the policy, use the !Join intrinsic function with "" as delimiter and values of "execute-api:/" and "*".
      - Valid JSON document
      - 
    * - resources
      - Container<ApiGatewayResources_>
      - 
      - 
      - 
    * - stages
      - Container<ApiGatewayStages_>
      - 
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayMethods
^^^^^^^^^^^^^^^^^^

Container for `ApiGatewayMethod`_ objects.

.. _ApiGatewayMethods:

.. list-table:: :guilabel:`ApiGatewayMethods` |bars| Container<`ApiGatewayMethod`_>
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


ApiGatewayMethod
^^^^^^^^^^^^^^^^^

API Gateway Method

.. _ApiGatewayMethod:

.. list-table:: :guilabel:`ApiGatewayMethod`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - authorization_type
      - String |star|
      - Authorization Type
      - Must be one of NONE, AWS_IAM, CUSTOM or COGNITO_USER_POOLS
      - 
    * - http_method
      - String
      - HTTP Method
      - Must be one of ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST or PUT.
      - 
    * - integration
      - Object<ApiGatewayMethodIntegration_>
      - Integration
      - 
      - 
    * - method_responses
      - List<ApiGatewayMethodMethodResponse_>
      - Method Responses
      - List of ApiGatewayMethod MethodResponses
      - 
    * - request_parameters
      - Dict
      - Request Parameters
      - Specify request parameters as key-value pairs (string-to-Boolean mapping),
                with a source as the key and a Boolean as the value. The Boolean specifies whether
                a parameter is required. A source must match the format method.request.location.name,
                where the location is query string, path, or header, and name is a valid, unique parameter name.
      - {}
    * - resource_id
      - String
      - Resource Id
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayModels
^^^^^^^^^^^^^^^^^

Container for `ApiGatewayModel`_ objects.

.. _ApiGatewayModels:

.. list-table:: :guilabel:`ApiGatewayModels` |bars| Container<`ApiGatewayModel`_>
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


ApiGatewayModel
^^^^^^^^^^^^^^^^



.. _ApiGatewayModel:

.. list-table:: :guilabel:`ApiGatewayModel`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_type
      - String
      - Content Type
      - 
      - 
    * - description
      - String
      - Description
      - 
      - 
    * - schema
      - Dict
      - Schema
      - JSON format. Will use null({}) if left empty.
      - {}

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayResources
^^^^^^^^^^^^^^^^^^^^

Container for `ApiGatewayResource`_ objects.

.. _ApiGatewayResources:

.. list-table:: :guilabel:`ApiGatewayResources` |bars| Container<`ApiGatewayResource`_>
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


ApiGatewayResource
^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayResource:

.. list-table:: :guilabel:`ApiGatewayResource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - parent_id
      - String
      - Id of the parent resource. Default is 'RootResourceId' for a resource without a parent.
      - 
      - RootResourceId
    * - path_part
      - String |star|
      - Path Part
      - 
      - 
    * - rest_api_id
      - String |star|
      - Name of the API Gateway REST API this resource belongs to.
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayStages
^^^^^^^^^^^^^^^^^

Container for `ApiGatewayStage`_ objects

.. _ApiGatewayStages:

.. list-table:: :guilabel:`ApiGatewayStages` |bars| Container<`ApiGatewayStages`_>
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


ApiGatewayStage
^^^^^^^^^^^^^^^^

API Gateway Stage

.. _ApiGatewayStage:

.. list-table:: :guilabel:`ApiGatewayStage`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - deployment_id
      - String
      - Deployment ID
      - 
      - 
    * - description
      - String
      - Description
      - 
      - 
    * - stage_name
      - String
      - Stage name
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayMethodIntegration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodIntegration:

.. list-table:: :guilabel:`ApiGatewayMethodIntegration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - integration_http_method
      - String
      - Integration HTTP Method
      - Must be one of ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST or PUT.
      - POST
    * - integration_lambda
      - PacoReference
      - Integration Lambda
      - Paco Reference to `Lambda`_.
      - 
    * - integration_responses
      - List<ApiGatewayMethodIntegrationResponse_>
      - Integration Responses
      - 
      - 
    * - integration_type
      - String |star|
      - Integration Type
      - Must be one of AWS, AWS_PROXY, HTTP, HTTP_PROXY or MOCK.
      - AWS
    * - request_parameters
      - Dict
      - The request parameters that API Gateway sends with the backend request.
      - Specify request parameters as key-value pairs (string-to-string mappings),
        with a destination as the key and a source as the value. Specify the destination by using the
        following pattern `integration.request.location.name`, where `location` is query string, path,
        or header, and `name` is a valid, unique parameter name.
        
        The source must be an existing method request parameter or a static value. You must
        enclose static values in single quotation marks and pre-encode these values based on
        their destination in the request.
                
      - {}
    * - uri
      - String
      - Integration URI
      - 
      - 



ApiGatewayMethodIntegrationResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodIntegrationResponse:

.. list-table:: :guilabel:`ApiGatewayMethodIntegrationResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_handling
      - String
      - Specifies how to handle request payload content type conversions.
      - Valid values are:
        
        CONVERT_TO_BINARY: Converts a request payload from a base64-encoded string to a binary blob.
        
        CONVERT_TO_TEXT: Converts a request payload from a binary blob to a base64-encoded string.
        
        If this property isn't defined, the request payload is passed through from the method request
        to the integration request without modification.

      - 
    * - response_parameters
      - Dict
      - Response Parameters
      - 
      - {}
    * - response_templates
      - Dict
      - Response Templates
      - 
      - {}
    * - selection_pattern
      - String
      - A regular expression that specifies which error strings or status codes from the backend map to the integration response.
      - 
      - 
    * - status_code
      - String |star|
      - The status code that API Gateway uses to map the integration response to a MethodResponse status code.
      - Must match a status code in the method_respones for this API Gateway REST API.
      - 



ApiGatewayMethodMethodResponse
-------------------------------



.. _ApiGatewayMethodMethodResponse:

.. list-table:: :guilabel:`ApiGatewayMethodMethodResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - response_models
      - List<ApiGatewayMethodMethodResponseModel_>
      - The resources used for the response's content type.
      - Specify response models as key-value pairs (string-to-string maps),
        with a content type as the key and a Model Paco name as the value.
      - 
    * - status_code
      - String |star|
      - HTTP Status code
      - 
      - 



ApiGatewayMethodMethodResponseModel
------------------------------------



.. _ApiGatewayMethodMethodResponseModel:

.. list-table:: :guilabel:`ApiGatewayMethodMethodResponseModel`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_type
      - String
      - Content Type
      - 
      - 
    * - model_name
      - String
      - Model name
      - 
      - 



LBApplication
--------------


The ``LBApplication`` resource type creates an Application Load Balancer. Use load balancers to route traffic from
the internet to your web servers.

Load balancers have ``listeners`` which will accept requrests on specified ports and protocols. If a listener
uses the HTTPS protocol, it can have a Paco reference to an SSL Certificate. A listener can then either
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
                - paco.ref netenv.app.applications.app.groups.certs.resources.root
            target_group: api
    dns:
        - hosted_zone: paco.ref resource.route53.mynetenv
          domain_name: api.example.com
    scheme: internet-facing
    security_groups:
        - paco.ref netenv.app.network.vpc.security_groups.app.alb
    segment: public



.. _LBApplication:

.. list-table:: :guilabel:`LBApplication`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - access_logs_bucket
      - PacoReference
      - Bucket to store access logs in
      - Paco Reference to `S3Bucket`_.
      - 
    * - access_logs_prefix
      - String
      - Access Logs S3 Bucket prefix
      - 
      - 
    * - dns
      - List<DNS_>
      - List of DNS for the ALB
      - 
      - 
    * - enable_access_logs
      - Boolean
      - Write access logs to an S3 Bucket
      - 
      - 
    * - idle_timeout_secs
      - Int
      - Idle timeout in seconds
      - The idle timeout value, in seconds.
      - 60
    * - listeners
      - Container<Listeners_>
      - Listeners
      - 
      - 
    * - scheme
      - Choice
      - Scheme
      - 
      - 
    * - security_groups
      - List<PacoReference>
      - Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Id of the segment stack
      - 
      - 
    * - target_groups
      - Container<TargetGroups_>
      - Target Groups
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


DNS
^^^^



.. _DNS:

.. list-table:: :guilabel:`DNS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - PacoReference|String
      - Domain name
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - hosted_zone
      - PacoReference|String
      - Hosted Zone Id
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - ssl_certificate
      - PacoReference
      - SSL certificate Reference
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - ttl
      - Int
      - TTL
      - 
      - 300



Listeners
^^^^^^^^^^


Container for `Listener`_ objects.
    

.. _Listeners:

.. list-table:: :guilabel:`Listeners` |bars| Container<`Listener`_>
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


Listener
^^^^^^^^^



.. _Listener:

.. list-table:: :guilabel:`Listener`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - redirect
      - Object<PortProtocol_>
      - Redirect
      - 
      - 
    * - rules
      - Container<ListenerRule_>
      - Container of listener rules
      - 
      - 
    * - ssl_certificates
      - List<PacoReference>
      - List of SSL certificate References
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - target_group
      - String
      - Target group
      - 
      - 

*Base Schemas* `PortProtocol`_


ListenerRule
^^^^^^^^^^^^^



.. _ListenerRule:

.. list-table:: :guilabel:`ListenerRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - host
      - String
      - Host header value
      - 
      - 
    * - priority
      - Int
      - Forward condition priority
      - 
      - 1
    * - redirect_host
      - String
      - The host to redirect to
      - 
      - 
    * - rule_type
      - String
      - Type of Rule
      - 
      - 
    * - target_group
      - String
      - Target group name
      - 
      - 

*Base Schemas* `Deployable`_


PortProtocol
^^^^^^^^^^^^^

Port and Protocol

.. _PortProtocol:

.. list-table:: :guilabel:`PortProtocol`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - port
      - Int
      - Port
      - 
      - 
    * - protocol
      - Choice
      - Protocol
      - 
      - 



TargetGroups
^^^^^^^^^^^^^


Container for `TargetGroup`_ objects.
    

.. _TargetGroups:

.. list-table:: :guilabel:`TargetGroups` |bars| Container<`TargetGroup`_>
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


TargetGroup
^^^^^^^^^^^^

Target Group

.. _TargetGroup:

.. list-table:: :guilabel:`TargetGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - connection_drain_timeout
      - Int
      - Connection drain timeout
      - 
      - 
    * - health_check_http_code
      - String
      - Health check HTTP codes
      - 
      - 
    * - health_check_interval
      - Int
      - Health check interval
      - 
      - 
    * - health_check_path
      - String
      - Health check path
      - 
      - /
    * - health_check_timeout
      - Int
      - Health check timeout
      - 
      - 
    * - healthy_threshold
      - Int
      - Healthy threshold
      - 
      - 
    * - unhealthy_threshold
      - Int
      - Unhealthy threshold
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `PortProtocol`_, `Title`_, `Type`_


ASG
----


Auto Scaling Group
    

.. _ASG:

.. list-table:: :guilabel:`ASG`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - associate_public_ip_address
      - Boolean
      - Associate Public IP Address
      - 
      - False
    * - availability_zone
      - String
      - Availability Zones to launch instances in.
      - 
      - all
    * - block_device_mappings
      - List<BlockDeviceMapping_>
      - Block Device Mappings
      - 
      - 
    * - cfn_init
      - Object<CloudFormationInit_>
      - CloudFormation Init
      - 
      - 
    * - cooldown_secs
      - Int
      - Cooldown seconds
      - 
      - 300
    * - desired_capacity
      - Int
      - Desired capacity
      - 
      - 1
    * - ebs_optimized
      - Boolean
      - EBS Optimized
      - 
      - False
    * - ebs_volume_mounts
      - List<EBSVolumeMount_>
      - Elastic Block Store Volume Mounts
      - 
      - 
    * - efs_mounts
      - List<EFSMount_>
      - Elastic Filesystem Configuration
      - 
      - 
    * - eip
      - PacoReference|String
      - Elastic IP or AllocationId to attach to instance at launch
      - Paco Reference to `EIP`_. String Ok.
      - 
    * - health_check_grace_period_secs
      - Int
      - Health check grace period in seconds
      - 
      - 300
    * - health_check_type
      - String
      - Health check type
      - Must be one of: 'EC2', 'ELB'
      - EC2
    * - instance_ami
      - PacoReference|String
      - Instance AMI
      - Paco Reference to `Function`_. String Ok.
      - 
    * - instance_ami_type
      - String
      - The AMI Operating System family
      - Must be one of amazon, centos, suse, debian, ubuntu, microsoft or redhat.
      - amazon
    * - instance_iam_role
      - Object<Role_> |star|
      - 
      - 
      - 
    * - instance_key_pair
      - PacoReference
      - Key pair to connect to launched instances
      - Paco Reference to `EC2KeyPair`_.
      - 
    * - instance_monitoring
      - Boolean
      - Instance monitoring
      - 
      - False
    * - instance_type
      - String
      - Instance type
      - 
      - 
    * - launch_options
      - Object<EC2LaunchOptions_>
      - EC2 Launch Options
      - 
      - 
    * - lifecycle_hooks
      - Container<ASGLifecycleHooks_>
      - Lifecycle Hooks
      - 
      - 
    * - load_balancers
      - List<PacoReference>
      - Target groups
      - Paco Reference to `TargetGroup`_.
      - 
    * - max_instances
      - Int
      - Maximum instances
      - 
      - 2
    * - min_instances
      - Int
      - Minimum instances
      - 
      - 1
    * - scaling_policies
      - Container<ASGScalingPolicies_>
      - Scaling Policies
      - 
      - 
    * - scaling_policy_cpu_average
      - Int
      - Average CPU Scaling Polciy
      - 
      - 0
    * - secrets
      - List<PacoReference>
      - List of Secrets Manager References
      - Paco Reference to `SecretsManagerSecret`_.
      - 
    * - security_groups
      - List<PacoReference>
      - Security groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 
    * - target_groups
      - List<PacoReference>
      - Target groups
      - Paco Reference to `TargetGroup`_.
      - 
    * - termination_policies
      - List<String>
      - Terminiation policies
      - 
      - 
    * - update_policy_max_batch_size
      - Int
      - Update policy maximum batch size
      - 
      - 1
    * - update_policy_min_instances_in_service
      - Int
      - Update policy minimum instances in service
      - 
      - 1
    * - user_data_pre_script
      - String
      - User data pre-script
      - 
      - 
    * - user_data_script
      - String
      - User data script
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


ASGLifecycleHooks
^^^^^^^^^^^^^^^^^^


Container for `ASGLifecycleHook` objects.
    

.. _ASGLifecycleHooks:

.. list-table:: :guilabel:`ASGLifecycleHooks` |bars| Container<`ASGLifecycleHook`_>
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


ASGLifecycleHook
^^^^^^^^^^^^^^^^^


ASG Lifecycle Hook
    

.. _ASGLifecycleHook:

.. list-table:: :guilabel:`ASGLifecycleHook`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - default_result
      - String
      - Default Result
      - 
      - 
    * - lifecycle_transition
      - String |star|
      - ASG Lifecycle Transition
      - 
      - 
    * - notification_target_arn
      - String |star|
      - Lifecycle Notification Target Arn
      - 
      - 
    * - role_arn
      - String |star|
      - Licecycel Publish Role ARN
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


ASGScalingPolicies
^^^^^^^^^^^^^^^^^^^


Container for `ASGScalingPolicy`_ objects.
    

.. _ASGScalingPolicies:

.. list-table:: :guilabel:`ASGScalingPolicies` |bars| Container<`ASGScalingPolicy`_>
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


ASGScalingPolicy
^^^^^^^^^^^^^^^^^


Auto Scaling Group Scaling Policy
    

.. _ASGScalingPolicy:

.. list-table:: :guilabel:`ASGScalingPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - adjustment_type
      - String |star|
      - Adjustment Type
      - 
      - ChangeInCapacity
    * - alarms
      - List<SimpleCloudWatchAlarm_> |star|
      - Alarms
      - 
      - 
    * - cooldown
      - Int
      - Scaling Cooldown in Seconds
      - 
      - 300
    * - policy_type
      - String |star|
      - Policy Type
      - 
      - SimpleScaling
    * - scaling_adjustment
      - Int |star|
      - Scaling Adjustment
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


BlockDeviceMapping
^^^^^^^^^^^^^^^^^^^



.. _BlockDeviceMapping:

.. list-table:: :guilabel:`BlockDeviceMapping`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - device_name
      - String |star|
      - The device name exposed to the EC2 instance
      - 
      - 
    * - ebs
      - Object<BlockDevice_>
      - Amazon Ebs volume
      - 
      - 
    * - virtual_name
      - String
      - The name of the virtual device.
      - The name must be in the form ephemeralX where X is a number starting from zero (0), for example, ephemeral0.
      - 



BlockDevice
^^^^^^^^^^^^



.. _BlockDevice:

.. list-table:: :guilabel:`BlockDevice`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - delete_on_termination
      - Boolean
      - Indicates whether to delete the volume when the instance is terminated.
      - 
      - True
    * - encrypted
      - Boolean
      - Specifies whether the EBS volume is encrypted.
      - 
      - 
    * - iops
      - Int
      - The number of I/O operations per second (IOPS) to provision for the volume.
      - The maximum ratio of IOPS to volume size (in GiB) is 50:1, so for 5,000 provisioned IOPS, you need at least 100 GiB storage on the volume.
      - 
    * - size_gib
      - Int
      - The volume size, in Gibibytes (GiB).
      - This can be a number from 1-1,024 for standard, 4-16,384 for io1, 1-16,384 for gp2, and 500-16,384 for st1 and sc1.
      - 
    * - snapshot_id
      - String
      - The snapshot ID of the volume to use.
      - 
      - 
    * - volume_type
      - String |star|
      - The volume type, which can be standard for Magnetic, io1 for Provisioned IOPS SSD, gp2 for General Purpose SSD, st1 for Throughput Optimized HDD, or sc1 for Cold HDD.
      - Must be one of standard, io1, gp2, st1 or sc1.
      - 



EBSVolumeMount
^^^^^^^^^^^^^^^


EBS Volume Mount Configuration
    

.. _EBSVolumeMount:

.. list-table:: :guilabel:`EBSVolumeMount`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - device
      - String |star|
      - Device to mount the EBS Volume with.
      - 
      - 
    * - filesystem
      - String |star|
      - Filesystem to mount the EBS Volume with.
      - 
      - 
    * - folder
      - String |star|
      - Folder to mount the EBS Volume
      - 
      - 
    * - volume
      - PacoReference|String |star|
      - EBS Volume Resource Reference
      - Paco Reference to `EBS`_. String Ok.
      - 

*Base Schemas* `Deployable`_


EFSMount
^^^^^^^^^


EFS Mount Folder and Target Configuration
    

.. _EFSMount:

.. list-table:: :guilabel:`EFSMount`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - folder
      - String |star|
      - Folder to mount the EFS target
      - 
      - 
    * - target
      - PacoReference|String |star|
      - EFS Target Resource Reference
      - Paco Reference to `EFS`_. String Ok.
      - 

*Base Schemas* `Deployable`_


EC2LaunchOptions
^^^^^^^^^^^^^^^^^


EC2 Launch Options
    

.. _EC2LaunchOptions:

.. list-table:: :guilabel:`EC2LaunchOptions`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cfn_init_config_sets
      - List<String>
      - List of cfn-init config sets
      - 
      - []
    * - update_packages
      - Boolean
      - Update Distribution Packages
      - 
      - False

*Base Schemas* `Named`_, `Title`_


CloudFormationInit
-------------------


`CloudFormation Init`_ is a method to configure an EC2 instance after it is launched.
CloudFormation Init is a much more complete and robust method to install configuration files and
pakcages than using a UserData script.

It stores information about packages, files, commands and more in CloudFormation metadata. It is accompanied
by a ``cfn-init`` script which will run on the instance to fetch this configuration metadata and apply
it. The whole system is often referred to simply as cfn-init after this script.

The ``cfn_init`` field of for an ASG contains all of the cfn-init configuration. After an instance
is launched, it needs to run a local cfn-init script to pull the configuration from the CloudFromation
stack and apply it. After cfn-init has applied configuration, you will run cfn-signal to tell CloudFormation
the configuration was successfully applied. Use the ``launch_options`` field for an ASG to let Paco take care of all this
for you.

.. sidebar:: Prescribed Automation

    ``launch_options``: The ``cfn_init_config_sets:`` field is a list of cfn-init configurations to
    apply at launch. This list will be applied in order. On Amazon Linux the cfn-init script is pre-installed
    in /opt/aws/bin. If you enable a cfn-init launch option, Paco will install cfn-init in /opt/paco/bin for you.

Refer to the `CloudFormation Init`_ docs for a complete description of all the configuration options
available.

.. code-block:: yaml
    :caption: cfn_init with launch_options

    launch_options:
        cfn_init_config_sets:
        - "Install"
    cfn_init:
      parameters:
        BasicKey: static-string
        DatabasePasswordarn: paco.ref netenv.mynet.secrets_manager.app.site.database.arn
      config_sets:
        Install:
          - "Install"
      configurations:
        Install:
          packages:
            rpm:
              epel: "http://download.fedoraproject.org/pub/epel/5/i386/epel-release-5-4.noarch.rpm"
            yum:
              jq: []
              python3: []
          files:
            "/tmp/get_rds_dsn.sh":
              content_cfn_file: ./webapp/get_rds_dsn.sh
              mode: '000700'
              owner: root
              group: root
            "/etc/httpd/conf.d/saas_wsgi.conf":
              content_file: ./webapp/saas_wsgi.conf
              mode: '000600'
              owner: root
              group: root
            "/etc/httpd/conf.d/wsgi.conf":
              content: "LoadModule wsgi_module modules/mod_wsgi.so"
              mode: '000600'
              owner: root
              group: root
            "/tmp/install_codedeploy.sh":
              source: https://aws-codedeploy-us-west-2.s3.us-west-2.amazonaws.com/latest/install
              mode: '000700'
              owner: root
              group: root
          commands:
            10_install_codedeploy:
              command: "/tmp/install_codedeploy.sh auto > /var/log/cfn-init-codedeploy.log 2>&1"
          services:
            sysvinit:
              codedeploy-agent:
                enabled: true
                ensure_running: true

The ``parameters`` field is a set of Parameters that will be passed to the CloudFormation stack. This
can be static strings or ``paco.ref`` that are looked up from already provisioned cloud resources.

CloudFormation Init can be organized into Configsets. With raw cfn-init using Configsets is optional,
but is required with Paco.

In a Configset, the ``files`` field has four fields for specifying the file contents.

 * ``content_file:`` A path to a file on the local filesystem. A convenient practice is to make a
   sub-directory in the ``netenv`` directory for keeping cfn-init files.

 * ``content_cfn_file:`` A path to a file on the local filesystem. This file will have FnSub and FnJoin
   CloudFormation applied to it.

 * ``content:`` For small files, the content can be in-lined directly in this field.

 * ``source:`` Fetches the file from a URL.

If you are using ``content_cfn_file`` to interpolate Parameters, the file might look like:

.. code-block:: bash

    !Sub |
        #!/bin/bash

        echo "Database ARN is " ${DatabasePasswordarn}
        echo "AWS Region is " ${AWS::Region}

If you want to include a raw ``${SomeValue}`` string in your file, use the ! character to escape it like this:
``${!SomeValue}``. cfn-init also supports interpolation with Mustache templates, but Paco support for this is
not yet implemented.

.. _CloudFormation Init: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-init.html

    

.. _CloudFormationInit:

.. list-table:: :guilabel:`CloudFormationInit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - config_sets
      - Container<CloudFormationConfigSets_> |star|
      - CloudFormation Init configSets
      - 
      - 
    * - configurations
      - Container<CloudFormationConfigurations_> |star|
      - CloudFormation Init configurations
      - 
      - 
    * - parameters
      - Dict
      - Parameters
      - 
      - {}

*Base Schemas* `Named`_, `Title`_


CloudFormationConfigSets
^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigSets:

.. list-table:: :guilabel:`CloudFormationConfigSets`
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


CloudFormationConfigurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigurations:

.. list-table:: :guilabel:`CloudFormationConfigurations` |bars| Container<`CloudFormationConfiguration`_>
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


CloudFormationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfiguration:

.. list-table:: :guilabel:`CloudFormationConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - commands
      - Container<CloudFormationInitCommands_>
      - Commands
      - 
      - 
    * - files
      - Container<CloudFormationInitFiles_>
      - Files
      - 
      - 
    * - groups
      - Object<CloudFormationInitGroups_>
      - Groups
      - 
      - 
    * - packages
      - Object<CloudFormationInitPackages_>
      - Packages
      - 
      - 
    * - services
      - Object<CloudFormationInitServices_>
      - Services
      - 
      - 
    * - sources
      - Container<CloudFormationInitSources_>
      - Sources
      - 
      - 
    * - users
      - Object<CloudFormationInitUsers_>
      - Users
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitCommands
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitCommands:

.. list-table:: :guilabel:`CloudFormationInitCommands`
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


CloudFormationInitCommand
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitCommand:

.. list-table:: :guilabel:`CloudFormationInitCommand`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - command
      - String |star|
      - Command
      - 
      - 
    * - cwd
      - String
      - Cwd. The working directory
      - 
      - 
    * - env
      - Dict
      - Environment Variables. This property overwrites, rather than appends, the existing environment.
      - 
      - {}
    * - ignore_errors
      - Boolean
      - Ingore errors - determines whether cfn-init continues to run if the command in contained in the command key fails (returns a non-zero value). Set to true if you want cfn-init to continue running even if the command fails.
      - 
      - False
    * - test
      - String
      - A test command that determines whether cfn-init runs commands that are specified in the command key. If the test passes, cfn-init runs the commands.
      - 
      - 



CloudFormationInitFiles
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitFiles:

.. list-table:: :guilabel:`CloudFormationInitFiles`
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


CloudFormationInitFile
^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitFile:

.. list-table:: :guilabel:`CloudFormationInitFile`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - authentication
      - String
      - The name of an authentication method to use.
      - 
      - 
    * - content
      - Object<Interface_>
      - Either a string or a properly formatted YAML object.
      - 
      - 
    * - content_cfn_file
      - YAMLFileReference
      - File path to a properly formatted CloudFormation Functions YAML object.
      - 
      - 
    * - content_file
      - StringFileReference
      - File path to a string.
      - 
      - 
    * - context
      - String
      - Specifies a context for files that are to be processed as Mustache templates.
      - 
      - 
    * - encoding
      - String
      - The encoding format.
      - 
      - 
    * - group
      - String
      - The name of the owning group for this file. Not supported for Windows systems.
      - 
      - 
    * - mode
      - String
      - A six-digit octal value representing the mode for this file.
      - 
      - 
    * - owner
      - String
      - The name of the owning user for this file. Not supported for Windows systems.
      - 
      - 
    * - source
      - String
      - A URL to load the file from.
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitGroups
^^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CloudFormationInitPackages
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitPackages:

.. list-table:: :guilabel:`CloudFormationInitPackages`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - apt
      - Container<CloudFormationInitVersionedPackageSet_>
      - Apt packages
      - 
      - 
    * - msi
      - Container<CloudFormationInitPathOrUrlPackageSet_>
      - MSI packages
      - 
      - 
    * - python
      - Container<CloudFormationInitVersionedPackageSet_>
      - Apt packages
      - 
      - 
    * - rpm
      - Container<CloudFormationInitPathOrUrlPackageSet_>
      - RPM packages
      - 
      - 
    * - rubygems
      - Container<CloudFormationInitVersionedPackageSet_>
      - Rubygems packages
      - 
      - 
    * - yum
      - Container<CloudFormationInitVersionedPackageSet_>
      - Yum packages
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitVersionedPackageSet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CloudFormationInitPathOrUrlPackageSet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CloudFormationInitServiceCollection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitServiceCollection:

.. list-table:: :guilabel:`CloudFormationInitServiceCollection`
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


CloudFormationInitServices
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitServices:

.. list-table:: :guilabel:`CloudFormationInitServices`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - sysvinit
      - Container<CloudFormationInitServiceCollection_>
      - SysVInit Services for Linux OS
      - 
      - 
    * - windows
      - Container<CloudFormationInitServiceCollection_>
      - Windows Services for Windows OS
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitService
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitService:

.. list-table:: :guilabel:`CloudFormationInitService`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - commands
      - List<String>
      - A list of command names. If cfn-init runs the specified command, this service will be restarted.
      - 
      - 
    * - enabled
      - Boolean
      - Ensure that the service will be started or not started upon boot.
      - 
      - 
    * - ensure_running
      - Boolean
      - Ensure that the service is running or stopped after cfn-init finishes.
      - 
      - 
    * - files
      - List<String>
      - A list of files. If cfn-init changes one directly via the files block, this service will be restarted
      - 
      - 
    * - packages
      - Dict
      - A map of package manager to list of package names. If cfn-init installs or updates one of these packages, this service will be restarted.
      - 
      - {}
    * - sources
      - List<String>
      - A list of directories. If cfn-init expands an archive into one of these directories, this service will be restarted.
      - 
      - 



CloudFormationInitSources
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitSources:

.. list-table:: :guilabel:`CloudFormationInitSources`
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


CloudFormationInitUsers
^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CodePipeBuildDeploy
--------------------


Code Pipeline: Build and Deploy
    

.. _CodePipeBuildDeploy:

.. list-table:: :guilabel:`CodePipeBuildDeploy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alb_target_group
      - PacoReference
      - ALB Target Group to deploy to
      - Paco Reference to `TargetGroup`_.
      - 
    * - artifacts_bucket
      - PacoReference
      - S3 Bucket for Artifacts
      - Paco Reference to `S3Bucket`_.
      - 
    * - asg
      - PacoReference
      - ASG Reference
      - Paco Reference to `ASG`_.
      - 
    * - auto_rollback_enabled
      - Boolean
      - Automatic rollback enabled
      - 
      - True
    * - codebuild_compute_type
      - String
      - CodeBuild Compute Type
      - 
      - 
    * - codebuild_image
      - String
      - CodeBuild Docker Image
      - 
      - 
    * - codecommit_repository
      - PacoReference
      - CodeCommit Respository
      - Paco Reference to `CodeCommitRepository`_.
      - 
    * - cross_account_support
      - Boolean
      - Cross Account Support
      - 
      - False
    * - deploy_config_type
      - String
      - Deploy Config Type
      - 
      - HOST_COUNT
    * - deploy_config_value
      - Int
      - Deploy Config Value
      - 
      - 0
    * - deploy_instance_role
      - PacoReference
      - Deploy Instance Role Reference
      - Paco Reference to `Role`_.
      - 
    * - deploy_style_option
      - String
      - Deploy Style Option
      - 
      - WITH_TRAFFIC_CONTROL
    * - deployment_branch_name
      - String
      - Deployment Branch Name
      - 
      - 
    * - deployment_environment
      - String
      - Deployment Environment
      - 
      - 
    * - elb_name
      - String
      - ELB Name
      - 
      - 
    * - manual_approval_enabled
      - Boolean
      - Manual approval enabled
      - 
      - False
    * - manual_approval_notification_email
      - String
      - Manual approval notification email
      - 
      - 
    * - timeout_mins
      - Int
      - Timeout in Minutes
      - 
      - 60
    * - tools_account
      - PacoReference
      - Account where CodePipeline runs
      - Paco Reference to `Account`_.
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


AWSCertificateManager
----------------------



.. _AWSCertificateManager:

.. list-table:: :guilabel:`AWSCertificateManager`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - String
      - Domain Name
      - 
      - 
    * - external_resource
      - Boolean
      - Marks this resource as external to avoid creating and validating it.
      - 
      - False
    * - subject_alternative_names
      - List<String>
      - Subject alternative names
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


CodeDeployApplication
----------------------


CodeDeploy Application

.. code-block:: yaml
    :caption: Example CodeDeployApplication resource YAML

    type: CodeDeployApplication
    order: 40
    compute_platform: "Server"
    deployment_groups:
      deployment:
        title: "My Deployment Group description"
        ignore_application_stop_failures: true
        revision_location_s3: paco.ref netenv.mynet.applications.app.groups.deploybucket
        autoscalinggroups:
          - paco.ref netenv.mynet.applications.app.groups.web



.. _CodeDeployApplication:

.. list-table:: :guilabel:`CodeDeployApplication`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - compute_platform
      - String |star|
      - Compute Platform
      - Must be one of Lambda, Server or ECS
      - 
    * - deployment_groups
      - Container<CodeDeployDeploymentGroups_> |star|
      - CodeDeploy Deployment Groups
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


CodeDeployDeploymentGroups
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CodeDeployDeploymentGroups:

.. list-table:: :guilabel:`CodeDeployDeploymentGroups`
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


CodeDeployDeploymentGroup
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CodeDeployDeploymentGroup:

.. list-table:: :guilabel:`CodeDeployDeploymentGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - autoscalinggroups
      - List<PacoReference>
      - AutoScalingGroups that CodeDeploy automatically deploys revisions to when new instances are created
      - Paco Reference to `ASG`_.
      - 
    * - ignore_application_stop_failures
      - Boolean
      - Ignore Application Stop Failures
      - 
      - 
    * - revision_location_s3
      - Object<DeploymentGroupS3Location_>
      - S3 Bucket revision location
      - 
      - 
    * - role_policies
      - List<Policy_>
      - Policies to grant the deployment group role
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_

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
    - paco.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: paco.ref netenv.mynet.network.vpc.segments.private
  primary_domain_name: database.example.internal
  primary_hosted_zone: paco.ref netenv.mynet.network.vpc.private_hosted_zone
  parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance




RDSOptionConfiguration
^^^^^^^^^^^^^^^^^^^^^^^


Option groups enable and configure features that are specific to a particular DB engine.
    

.. _RDSOptionConfiguration:

.. list-table:: :guilabel:`RDSOptionConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - option_name
      - String
      - Option Name
      - 
      - 
    * - option_settings
      - List<NameValuePair_>
      - List of option name value pairs.
      - 
      - 
    * - option_version
      - String
      - Option Version
      - 
      - 
    * - port
      - String
      - Port
      - 
      - 



NameValuePair
^^^^^^^^^^^^^^

A Name/Value pair to use for RDS Option Group configuration

.. _NameValuePair:

.. list-table:: :guilabel:`NameValuePair`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Name
      - 
      - 
    * - value
      - String
      - Value
      - 
      - 



RDSMysql
^^^^^^^^^


The RDSMysql type extends the base RDS schema with a ``multi_az`` field. When you provision a Multi-AZ DB Instance,
Amazon RDS automatically creates a primary DB Instance and synchronously replicates the data to a standby instance
in a different Availability Zone (AZ).
    

.. _RDSMysql:

.. list-table:: :guilabel:`RDSMysql`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - multi_az
      - Boolean
      - Multiple Availability Zone deployment
      - 
      - False

*Base Schemas* `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSAurora
^^^^^^^^^^


RDS Aurora
    

.. _RDSAurora:

.. list-table:: :guilabel:`RDSAurora`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - secondary_domain_name
      - PacoReference|String
      - Secondary Domain Name
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - secondary_hosted_zone
      - PacoReference
      - Secondary Hosted Zone
      - Paco Reference to `Route53HostedZone`_.
      - 

*Base Schemas* `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


DBParameterGroup
-----------------


DBParameterGroup
    

.. _DBParameterGroup:

.. list-table:: :guilabel:`DBParameterGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - description
      - String
      - Description
      - 
      - 
    * - family
      - String |star|
      - Database Family
      - 
      - 
    * - parameters
      - Container<DBParameters_> |star|
      - Database Parameter set
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_

DBParameters
------------

A unconstrainted set of key-value pairs.


EC2
----


EC2 Instance
    

.. _EC2:

.. list-table:: :guilabel:`EC2`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - associate_public_ip_address
      - Boolean
      - Associate Public IP Address
      - 
      - False
    * - disable_api_termination
      - Boolean
      - Disable API Termination
      - 
      - False
    * - instance_ami
      - String
      - Instance AMI
      - 
      - 
    * - instance_key_pair
      - PacoReference
      - key pair for connections to instance
      - Paco Reference to `EC2KeyPair`_.
      - 
    * - instance_type
      - String
      - Instance type
      - 
      - 
    * - private_ip_address
      - String
      - Private IP Address
      - 
      - 
    * - root_volume_size_gb
      - Int
      - Root volume size GB
      - 
      - 8
    * - security_groups
      - List<PacoReference>
      - Security groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 
    * - user_data_script
      - String
      - User data script
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


Lambda
-------


Lambda Functions allow you to run code without provisioning servers and only
pay for the compute time when the code is running.

For the code that the Lambda function will run, use the ``code:`` block and specify
``s3_bucket`` and ``s3_key`` to deploy the code from an S3 Bucket or use ``zipfile`` to read a local file from disk.

.. sidebar:: Prescribed Automation

    ``sdb_cache``: Create a SimpleDB Domain and IAM Policy that grants full access to that domain. Will
    also make the domain available to the Lambda function as an environment variable named ``SDB_CACHE_DOMAIN``.

    ``sns_topics``: Subscribes the Lambda to SNS Topics. For each Paco reference to an SNS Topic,
    Paco will create an SNS Topic Subscription so that the Lambda function will recieve all messages sent to that SNS Topic.
    It will also create a Lambda Permission granting that SNS Topic the ability to publish to the Lambda.

    **S3 Bucket Notification permission** Paco will check all resources in the Application for any S3 Buckets configured
    to notify this Lambda. Lambda Permissions will be created to allow those S3 Buckets to invoke the Lambda.

    **Events Rule permission** Paco will check all resources in the Application for CloudWatch Events Rule that are configured
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
      - paco.ref netenv.app.applications.app.groups.web.resources.snstopic
    vpc_config:
        segments:
          - paco.ref netenv.app.network.vpc.segments.public
        security_groups:
          - paco.ref netenv.app.network.vpc.security_groups.app.function



.. _Lambda:

.. list-table:: :guilabel:`Lambda`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - code
      - Object<LambdaFunctionCode_> |star|
      - The function deployment package.
      - 
      - 
    * - description
      - String |star|
      - A description of the function.
      - 
      - 
    * - environment
      - Object<LambdaEnvironment_>
      - Lambda Function Environment
      - 
      - 
    * - handler
      - String |star|
      - Function Handler
      - 
      - 
    * - iam_role
      - Object<Role_> |star|
      - The IAM Role this Lambda will execute as.
      - 
      - 
    * - layers
      - List<String> |star|
      - Layers
      - Up to 5 Layer ARNs
      - 
    * - memory_size
      - Int
      - Function memory size (MB)
      - 
      - 128
    * - reserved_concurrent_executions
      - Int
      - Reserved Concurrent Executions
      - 
      - 0
    * - runtime
      - String |star|
      - Runtime environment
      - 
      - python3.7
    * - sdb_cache
      - Boolean
      - SDB Cache Domain
      - 
      - False
    * - sns_topics
      - List<PacoReference>
      - List of SNS Topic Paco references or SNS Topic ARNs to subscribe the Lambda to.
      - Paco Reference to `SNSTopic`_. String Ok.
      - 
    * - timeout
      - Int
      - Max function execution time in seconds.
      - Must be between 0 and 900 seconds.
      - 
    * - vpc_config
      - Object<LambdaVpcConfig_>
      - Vpc Configuration
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


LambdaFunctionCode
^^^^^^^^^^^^^^^^^^^

The deployment package for a Lambda function.

.. _LambdaFunctionCode:

.. list-table:: :guilabel:`LambdaFunctionCode`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - s3_bucket
      - PacoReference|String
      - An Amazon S3 bucket in the same AWS Region as your function
      - Paco Reference to `S3Bucket`_. String Ok.
      - 
    * - s3_key
      - String
      - The Amazon S3 key of the deployment package.
      - 
      - 
    * - zipfile
      - StringFileReference
      - The function as an external file.
      - Maximum of 4096 characters.
      - 



LambdaEnvironment
^^^^^^^^^^^^^^^^^^


Lambda Environment
    

.. _LambdaEnvironment:

.. list-table:: :guilabel:`LambdaEnvironment`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - variables
      - List<LambdaVariable_>
      - Lambda Function Variables
      - 
      - 



LambdaVpcConfig
^^^^^^^^^^^^^^^^


Lambda Environment
    

.. _LambdaVpcConfig:

.. list-table:: :guilabel:`LambdaVpcConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - security_groups
      - List<PacoReference>
      - List of VPC Security Group Ids
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segments
      - List<PacoReference>
      - VPC Segments to attach the function
      - Paco Reference to `Segment`_.
      - 

*Base Schemas* `Named`_, `Title`_


LambdaVariable
^^^^^^^^^^^^^^^


    Lambda Environment Variable
    

.. _LambdaVariable:

.. list-table:: :guilabel:`LambdaVariable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - key
      - String |star|
      - Variable Name
      - 
      - 
    * - value
      - PacoReference|String |star|
      - String Value or a Paco Reference to a resource output
      - Paco Reference to `Interface`_. String Ok.
      - 



ManagedPolicy
--------------


IAM Managed Policy
    

.. _ManagedPolicy:

.. list-table:: :guilabel:`ManagedPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - path
      - String
      - Path
      - 
      - /
    * - roles
      - List<String>
      - List of Role Names
      - 
      - 
    * - statement
      - List<Statement_>
      - Statements
      - 
      - 
    * - users
      - List<String>
      - List of IAM Users
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


S3Bucket
---------


S3 Bucket
    

.. _S3Bucket:

.. list-table:: :guilabel:`S3Bucket`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - Account that S3 Bucket belongs to.
      - Paco Reference to `Account`_.
      - 
    * - bucket_name
      - String |star|
      - Bucket Name
      - A short unique name to assign the bucket.
      - bucket
    * - cloudfront_origin
      - Boolean
      - Creates and listens for a CloudFront Access Origin Identity
      - 
      - False
    * - deletion_policy
      - String
      - Bucket Deletion Policy
      - 
      - delete
    * - external_resource
      - Boolean
      - Boolean indicating whether the S3 Bucket already exists or not
      - 
      - False
    * - notifications
      - Object<S3NotificationConfiguration_>
      - Notification configuration
      - 
      - 
    * - policy
      - List<S3BucketPolicy_>
      - List of S3 Bucket Policies
      - 
      - 
    * - region
      - String
      - Bucket region
      - 
      - 
    * - static_website_hosting
      - Object<S3StaticWebsiteHosting_>
      - Static website hosting configuration.
      - 
      - 
    * - versioning
      - Boolean
      - Enable Versioning on the bucket.
      - 
      - False

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


S3BucketPolicy
^^^^^^^^^^^^^^^


S3 Bucket Policy
    

.. _S3BucketPolicy:

.. list-table:: :guilabel:`S3BucketPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - action
      - List<String> |star|
      - List of Actions
      - 
      - 
    * - aws
      - List<String>
      - List of AWS Principles.
      - Either this field or the principal field must be set.
      - 
    * - condition
      - Dict
      - Condition
      - Each Key is the Condition name and the Value must be a dictionary of request filters. e.g. { "StringEquals" : { "aws:username" : "johndoe" }}
      - {}
    * - effect
      - String |star|
      - Effect
      - Must be one of: 'Allow', 'Deny'
      - Deny
    * - principal
      - Dict
      - Prinicpals
      - Either this field or the aws field must be set. Key should be one of: AWS, Federated, Service or CanonicalUser. Value can be either a String or a List.
      - {}
    * - resource_suffix
      - List<String> |star|
      - List of AWS Resources Suffixes
      - 
      - 



S3StaticWebsiteHosting
^^^^^^^^^^^^^^^^^^^^^^^



.. _S3StaticWebsiteHosting:

.. list-table:: :guilabel:`S3StaticWebsiteHosting`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - redirect_requests
      - Object<S3StaticWebsiteHostingRedirectRequests_>
      - Redirect requests configuration.
      - 
      - 

*Base Schemas* `Deployable`_


S3StaticWebsiteHostingRedirectRequests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3StaticWebsiteHostingRedirectRequests:

.. list-table:: :guilabel:`S3StaticWebsiteHostingRedirectRequests`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - protocol
      - String |star|
      - Protocol
      - 
      - 
    * - target
      - PacoReference|String |star|
      - Target S3 Bucket or domain.
      - Paco Reference to `S3Bucket`_. String Ok.
      - 



S3LambdaConfiguration
^^^^^^^^^^^^^^^^^^^^^^



.. _S3LambdaConfiguration:

.. list-table:: :guilabel:`S3LambdaConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - event
      - String
      - S3 bucket event for which to invoke the AWS Lambda function
      - Must be a supported event type: https://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
      - 
    * - function
      - PacoReference
      - Lambda function to notify
      - Paco Reference to `Lambda`_.
      - 



S3NotificationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3NotificationConfiguration:

.. list-table:: :guilabel:`S3NotificationConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - lambdas
      - List<S3LambdaConfiguration_>
      - Lambda configurations
      - 
      - 



SNSTopic
---------


Simple Notification Service (SNS) Topic resource.

.. sidebar:: Prescribed Automation

    ``cross_account_access``: Creates an SNS Topic Policy which will grant all of the AWS Accounts in this
    Paco Project access to the ``sns.Publish`` permission for this SNS Topic.

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
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cross_account_access
      - Boolean
      - Cross-account access from all other accounts in this project.
      - 
      - False
    * - display_name
      - String
      - Display name for SMS Messages
      - 
      - 
    * - subscriptions
      - List<SNSTopicSubscription_>
      - List of SNS Topic Subscriptions
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


SNSTopicSubscription
^^^^^^^^^^^^^^^^^^^^^



.. _SNSTopicSubscription:

.. list-table:: :guilabel:`SNSTopicSubscription`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - endpoint
      - PacoReference|String
      - SNS Topic ARN or Paco Reference
      - Paco Reference to `SNSTopic`_. String Ok.
      - 
    * - protocol
      - String
      - Notification protocol
      - Must be a valid SNS Topic subscription protocol: 'http', 'https', 'email', 'email-json', 'sms', 'sqs', 'application', 'lambda'.
      - email



CloudFront
-----------


CloudFront CDN Configuration
    

.. _CloudFront:

.. list-table:: :guilabel:`CloudFront`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cache_behaviors
      - List<CloudFrontCacheBehavior_>
      - List of Cache Behaviors
      - 
      - 
    * - custom_error_responses
      - List<CloudFrontCustomErrorResponse_>
      - List of Custom Error Responses
      - 
      - 
    * - default_cache_behavior
      - Object<CloudFrontDefaultCacheBehavior_>
      - Default Cache Behavior
      - 
      - 
    * - default_root_object
      - String
      - The default path to load from the origin.
      - 
      - index.html
    * - domain_aliases
      - List<DNS_>
      - List of DNS for the Distribution
      - 
      - 
    * - factory
      - Container<CloudFrontFactory_>
      - CloudFront Factory
      - 
      - 
    * - origins
      - Container<CloudFrontOrigin_>
      - Map of Origins
      - 
      - 
    * - price_class
      - String
      - Price Class
      - 
      - All
    * - viewer_certificate
      - Object<CloudFrontViewerCertificate_>
      - Viewer Certificate
      - 
      - 
    * - webacl_id
      - String
      - WAF WebACLId
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


CloudFrontDefaultCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontDefaultCacheBehavior:

.. list-table:: :guilabel:`CloudFrontDefaultCacheBehavior`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - allowed_methods
      - List<String>
      - List of Allowed HTTP Methods
      - 
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
    * - cached_methods
      - List<String>
      - List of HTTP Methods to cache
      - 
      - ['GET', 'HEAD', 'OPTIONS']
    * - compress
      - Boolean
      - Compress certain files automatically
      - 
      - False
    * - default_ttl
      - Int |star|
      - Default TTTL
      - 
      - 0
    * - forwarded_values
      - Object<CloudFrontForwardedValues_>
      - Forwarded Values
      - 
      - 
    * - target_origin
      - PacoReference |star|
      - Target Origin
      - Paco Reference to `CloudFrontOrigin`_.
      - 
    * - viewer_protocol_policy
      - String |star|
      - Viewer Protocol Policy
      - 
      - redirect-to-https

*Base Schemas* `Named`_, `Title`_


CloudFrontCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCacheBehavior:

.. list-table:: :guilabel:`CloudFrontCacheBehavior`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - path_pattern
      - String |star|
      - Path Pattern
      - 
      - 

*Base Schemas* `CloudFrontDefaultCacheBehavior`_, `Named`_, `Title`_


CloudFrontFactory
^^^^^^^^^^^^^^^^^^


CloudFront Factory
    

.. _CloudFrontFactory:

.. list-table:: :guilabel:`CloudFrontFactory`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_aliases
      - List<DNS_>
      - List of DNS for the Distribution
      - 
      - 
    * - viewer_certificate
      - Object<CloudFrontViewerCertificate_>
      - Viewer Certificate
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontOrigin
^^^^^^^^^^^^^^^^^


CloudFront Origin Configuration
    

.. _CloudFrontOrigin:

.. list-table:: :guilabel:`CloudFrontOrigin`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - custom_origin_config
      - Object<CloudFrontCustomOriginConfig_>
      - Custom Origin Configuration
      - 
      - 
    * - domain_name
      - PacoReference|String
      - Origin Resource Reference
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - s3_bucket
      - PacoReference
      - Origin S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontCustomOriginConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomOriginConfig:

.. list-table:: :guilabel:`CloudFrontCustomOriginConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - http_port
      - Int
      - HTTP Port
      - 
      - 
    * - https_port
      - Int
      - HTTPS Port
      - 
      - 
    * - keepalive_timeout
      - Int
      - HTTP Keepalive Timeout
      - 
      - 5
    * - protocol_policy
      - String
      - Protocol Policy
      - 
      - 
    * - read_timeout
      - Int
      - Read timeout
      - 
      - 30
    * - ssl_protocols
      - List<String>
      - List of SSL Protocols
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontCustomErrorResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomErrorResponse:

.. list-table:: :guilabel:`CloudFrontCustomErrorResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - error_caching_min_ttl
      - Int
      - Error Caching Min TTL
      - 
      - 
    * - error_code
      - Int
      - HTTP Error Code
      - 
      - 
    * - response_code
      - Int
      - HTTP Response Code
      - 
      - 
    * - response_page_path
      - String
      - Response Page Path
      - 
      - 



CloudFrontViewerCertificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontViewerCertificate:

.. list-table:: :guilabel:`CloudFrontViewerCertificate`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - certificate
      - PacoReference
      - Certificate Reference
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - minimum_protocol_version
      - String
      - Minimum SSL Protocol Version
      - 
      - TLSv1.1_2016
    * - ssl_supported_method
      - String
      - SSL Supported Method
      - 
      - sni-only

*Base Schemas* `Named`_, `Title`_


CloudFrontForwardedValues
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontForwardedValues:

.. list-table:: :guilabel:`CloudFrontForwardedValues`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cookies
      - Object<CloudFrontCookies_>
      - Forward Cookies
      - 
      - 
    * - headers
      - List<String>
      - Forward Headers
      - 
      - ['*']
    * - query_string
      - Boolean
      - Forward Query Strings
      - 
      - True

*Base Schemas* `Named`_, `Title`_


CloudFrontCookies
^^^^^^^^^^^^^^^^^^



.. _CloudFrontCookies:

.. list-table:: :guilabel:`CloudFrontCookies`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - forward
      - String
      - Cookies Forward Action
      - 
      - all
    * - whitelisted_names
      - List<String>
      - White Listed Names
      - 
      - 

*Base Schemas* `Named`_, `Title`_


ElastiCache
------------


Base ElastiCache Interface
    

.. _ElastiCache:

.. list-table:: :guilabel:`ElastiCache`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - at_rest_encryption
      - Boolean
      - Enable encryption at rest
      - 
      - 
    * - auto_minor_version_upgrade
      - Boolean
      - Enable automatic minor version upgrades
      - 
      - 
    * - automatic_failover_enabled
      - Boolean
      - Specifies whether a read-only replica is automatically promoted to read/write primary if the existing primary fails
      - 
      - 
    * - az_mode
      - String
      - AZ mode
      - 
      - 
    * - cache_clusters
      - Int
      - Number of Cache Clusters
      - 
      - 
    * - cache_node_type
      - String
      - Cache Node Instance type
      - 
      - 
    * - description
      - String
      - Replication Description
      - 
      - 
    * - engine
      - String
      - ElastiCache Engine
      - 
      - 
    * - engine_version
      - String
      - ElastiCache Engine Version
      - 
      - 
    * - maintenance_preferred_window
      - String
      - Preferred maintenance window
      - 
      - 
    * - number_of_read_replicas
      - Int
      - Number of read replicas
      - 
      - 
    * - parameter_group
      - PacoReference|String
      - Parameter Group name
      - Paco Reference to `Interface`_. String Ok.
      - 
    * - port
      - Int
      - Port
      - 
      - 
    * - security_groups
      - List<PacoReference>
      - List of Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - PacoReference
      - Segment
      - Paco Reference to `Segment`_.
      - 



ElastiCacheRedis
^^^^^^^^^^^^^^^^^


Redis ElastiCache Interface
    

.. _ElastiCacheRedis:

.. list-table:: :guilabel:`ElastiCacheRedis`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cache_parameter_group_family
      - String
      - Cache Parameter Group Family
      - 
      - 
    * - snapshot_retention_limit_days
      - Int
      - Snapshot Retention Limit in Days
      - 
      - 
    * - snapshot_window
      - String
      - The daily time range (in UTC) during which ElastiCache begins taking a daily snapshot of your node group (shard).
      - 
      - 

*Base Schemas* `ElastiCache`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


DeploymentPipeline
-------------------


Code Pipeline: Build and Deploy
    

.. _DeploymentPipeline:

.. list-table:: :guilabel:`DeploymentPipeline`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - build
      - Container<DeploymentPipelineBuildStage_>
      - Deployment Pipeline Build Stage
      - 
      - 
    * - configuration
      - Object<DeploymentPipelineConfiguration_>
      - Deployment Pipeline General Configuration
      - 
      - 
    * - deploy
      - Container<DeploymentPipelineDeployStage_>
      - Deployment Pipeline Deploy Stage
      - 
      - 
    * - source
      - Container<DeploymentPipelineSourceStage_>
      - Deployment Pipeline Source Stage
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


DeploymentPipelineSourceStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline source stage actions
    

.. _DeploymentPipelineSourceStage:

.. list-table:: :guilabel:`DeploymentPipelineSourceStage`
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


DeploymentPipelineDeployStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline deploy stage actions
    

.. _DeploymentPipelineDeployStage:

.. list-table:: :guilabel:`DeploymentPipelineDeployStage`
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


DeploymentPipelineBuildStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline build stage actions
    

.. _DeploymentPipelineBuildStage:

.. list-table:: :guilabel:`DeploymentPipelineBuildStage`
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


DeploymentPipelineDeployCodeDeploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeDeploy DeploymentPipeline Deploy Stage
    

.. _DeploymentPipelineDeployCodeDeploy:

.. list-table:: :guilabel:`DeploymentPipelineDeployCodeDeploy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alb_target_group
      - PacoReference
      - ALB Target Group Reference
      - Paco Reference to `TargetGroup`_.
      - 
    * - auto_rollback_enabled
      - Boolean |star|
      - Automatic rollback enabled
      - 
      - True
    * - auto_scaling_group
      - PacoReference
      - ASG Reference
      - Paco Reference to `ASG`_.
      - 
    * - deploy_instance_role
      - PacoReference
      - Deploy Instance Role Reference
      - Paco Reference to `Role`_.
      - 
    * - deploy_style_option
      - String
      - Deploy Style Option
      - 
      - WITH_TRAFFIC_CONTROL
    * - elb_name
      - String
      - ELB Name
      - 
      - 
    * - minimum_healthy_hosts
      - Object<CodeDeployMinimumHealthyHosts_>
      - The minimum number of healthy instances that should be available at any time during the deployment.
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


CodeDeployMinimumHealthyHosts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeDeploy Minimum Healthy Hosts
    

.. _CodeDeployMinimumHealthyHosts:

.. list-table:: :guilabel:`CodeDeployMinimumHealthyHosts`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - type
      - String
      - Deploy Config Type
      - 
      - HOST_COUNT
    * - value
      - Int
      - Deploy Config Value
      - 
      - 0

*Base Schemas* `Named`_, `Title`_


DeploymentPipelineManualApproval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


ManualApproval DeploymentPipeline
    

.. _DeploymentPipelineManualApproval:

.. list-table:: :guilabel:`DeploymentPipelineManualApproval`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - manual_approval_notification_email
      - List<String>
      - Manual Approval Notification Email List
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineDeployS3
^^^^^^^^^^^^^^^^^^^^^^^^^^^


Amazon S3 Deployment Provider
    

.. _DeploymentPipelineDeployS3:

.. list-table:: :guilabel:`DeploymentPipelineDeployS3`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference
      - S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 
    * - extract
      - Boolean
      - Boolean indicating whether the deployment artifact will be unarchived.
      - 
      - True
    * - object_key
      - String
      - S3 object key to store the deployment artifact as.
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineBuildCodeBuild
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeBuild DeploymentPipeline Build Stage
    

.. _DeploymentPipelineBuildCodeBuild:

.. list-table:: :guilabel:`DeploymentPipelineBuildCodeBuild`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - codebuild_compute_type
      - String
      - CodeBuild Compute Type
      - 
      - 
    * - codebuild_image
      - String
      - CodeBuild Docker Image
      - 
      - 
    * - deployment_environment
      - String
      - Deployment Environment
      - 
      - 
    * - role_policies
      - List<Policy_>
      - Project IAM Role Policies
      - 
      - 
    * - timeout_mins
      - Int
      - Timeout in Minutes
      - 
      - 60

*Base Schemas* `Deployable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineSourceCodeCommit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeCommit DeploymentPipeline Source Stage
    

.. _DeploymentPipelineSourceCodeCommit:

.. list-table:: :guilabel:`DeploymentPipelineSourceCodeCommit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - codecommit_repository
      - PacoReference
      - CodeCommit Respository
      - Paco Reference to `CodeCommitRepository`_.
      - 
    * - deployment_branch_name
      - String
      - Deployment Branch Name
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineStageAction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Deployment Pipeline Source Stage
    

.. _DeploymentPipelineStageAction:

.. list-table:: :guilabel:`DeploymentPipelineStageAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - run_order
      - Int
      - The order in which to run this stage
      - 
      - 1
    * - type
      - String
      - The type of DeploymentPipeline Source Stage
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


DeploymentPipelineConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Deployment Pipeline General Configuration
    

.. _DeploymentPipelineConfiguration:

.. list-table:: :guilabel:`DeploymentPipelineConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - The account where Pipeline tools will be provisioned.
      - Paco Reference to `Account`_.
      - 
    * - artifacts_bucket
      - PacoReference
      - Artifacts S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 

*Base Schemas* `Named`_, `Title`_


DeploymentGroupS3Location
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _DeploymentGroupS3Location:

.. list-table:: :guilabel:`DeploymentGroupS3Location`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference
      - S3 Bucket revision location
      - Paco Reference to `S3Bucket`_.
      - 
    * - bundle_type
      - String
      - Bundle Type
      - Must be one of JSON, tar, tgz, YAML or zip.
      - 
    * - key
      - String |star|
      - The name of the Amazon S3 object that represents the bundled artifacts for the application revision.
      - 
      - 



EFS
----


AWS Elastic File System (EFS) resource.

.. code-block:: yaml
    :caption: Example EFS resource YAML

    type: EFS
    order: 20
    enabled: true
    encrypted: false
    segment: private
    security_groups:
      - paco.ref netenv.mynet.network.vpc.security_groups.cloud.content

    

.. _EFS:

.. list-table:: :guilabel:`EFS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - encrypted
      - Boolean |star|
      - Encryption at Rest
      - 
      - False
    * - security_groups
      - List<PacoReference> |star|
      - Security groups
      - `SecurityGroup`_ the EFS belongs to Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


EIP
----


Elastic IP
    

.. _EIP:

.. list-table:: :guilabel:`EIP`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dns
      - List<DNS_>
      - List of DNS for the EIP
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


Route53HealthCheck
-------------------

Route53 Health Check

.. _Route53HealthCheck:

.. list-table:: :guilabel:`Route53HealthCheck`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - String
      - Fully Qualified Domain Name
      - Either this or the load_balancer field can be set but not both.
      - 
    * - enable_sni
      - Boolean
      - Enable SNI
      - 
      - False
    * - failure_threshold
      - Int
      - Number of consecutive health checks that an endpoint must pass or fail for Amazon Route 53 to change the current status of the endpoint from unhealthy to healthy or vice versa.
      - 
      - 3
    * - health_check_type
      - String |star|
      - Health Check Type
      - Must be one of HTTP, HTTPS or TCP
      - 
    * - health_checker_regions
      - List<String>
      - Health checker regions
      - List of AWS Region names (e.g. us-west-2) from which to make health checks.
      - 
    * - ip_address
      - PacoReference|String
      - IP Address
      - Paco Reference to `EIP`_. String Ok.
      - 
    * - latency_graphs
      - Boolean
      - Measure latency and display CloudWatch graph in the AWS Console
      - 
      - False
    * - load_balancer
      - PacoReference|String
      - Load Balancer Endpoint
      - Paco Reference to `LBApplication`_. String Ok.
      - 
    * - match_string
      - String
      - String to match in the first 5120 bytes of the response
      - 
      - 
    * - port
      - Int
      - Port
      - 
      - 80
    * - request_interval_fast
      - Boolean
      - Fast request interval will only wait 10 seconds between each health check response instead of the standard 30
      - 
      - False
    * - resource_path
      - String
      - Resource Path
      - String such as '/health.html'. Path should return a 2xx or 3xx. Query string parameters are allowed: '/search?query=health'
      - /

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


EventsRule
-----------


Events Rule
    

.. _EventsRule:

.. list-table:: :guilabel:`EventsRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - description
      - String
      - Description
      - 
      - 
    * - schedule_expression
      - String |star|
      - Schedule Expression
      - 
      - 
    * - targets
      - List<PacoReference> |star|
      - The AWS Resources that are invoked when the Rule is triggered.
      - Paco Reference to `Interface`_.
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


EBS
----


Elastic Block Store Volume
    

.. _EBS:

.. list-table:: :guilabel:`EBS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - availability_zone
      - Int |star|
      - Availability Zone to create Volume in.
      - 
      - 
    * - size_gib
      - Int |star|
      - Volume Size in GiB
      - 
      - 10
    * - volume_type
      - String
      - Volume Type
      - Must be one of: gp2 | io1 | sc1 | st1 | standard
      - gp2

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


NetEnv - secrets_manager:
=========================


SecretsManager
---------------

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
    * - generate_string_key
      - String
      - The JSON key name that's used to add the generated password to the JSON structure.
      - 
      - 
    * - password_length
      - Int
      - The desired length of the generated password.
      - 
      - 32
    * - secret_string_template
      - String
      - A properly structured JSON string that the generated password can be added to.
      - 
      - 

*Base Schemas* `Deployable`_


NetEnv - backup_vaults:
=======================

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
-------------


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


NetEnv - environments:
======================

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
------------


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
-------------------


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
------------------


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

Monitoring: monitor/\*.yaml
============================

The ``monitor`` directory can contain two files: ``monitor/alarmsets.yaml`` and ``monitor/logging.yaml``. These files
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
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - classification
      - String |star|
      - Classification
      - Must be one of: 'performance', 'security' or 'health'
      - unset
    * - description
      - String
      - Description
      - 
      - 
    * - notification_groups
      - List<String>
      - List of notificationn groups the alarm is subscribed to.
      - 
      - 
    * - runbook_url
      - String
      - Runbook URL
      - 
      - 
    * - severity
      - String
      - Severity
      - Must be one of: 'low', 'critical'
      - low

*Base Schemas* `Deployable`_, `Named`_, `Notifiable`_, `Title`_


AlarmSet
---------


A container of Alarm objects.
    

.. _AlarmSet:

.. list-table:: :guilabel:`AlarmSet`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - resource_type
      - String
      - Resource type
      - Must be a valid AWS resource type
      - 

*Base Schemas* `Named`_, `Notifiable`_, `Title`_


AlarmSets
----------


A container of `AlarmSet`_ objects.
    

.. _AlarmSets:

.. list-table:: :guilabel:`AlarmSets` |bars| Container<`AlarmSet`_>
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


Dimension
----------


A dimension of a metric
    

.. _Dimension:

.. list-table:: :guilabel:`Dimension`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Dimension name
      - 
      - 
    * - value
      - PacoReference|String
      - String or a Paco Reference to resource output.
      - Paco Reference to `Interface`_. String Ok.
      - 



AlarmNotifications
-------------------


Container for `AlarmNotification`_ objects.
    

.. _AlarmNotifications:

.. list-table:: :guilabel:`AlarmNotifications` |bars| Container<`AlarmNotification`_>
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


AlarmNotification
------------------


Alarm Notification
    

.. _AlarmNotification:

.. list-table:: :guilabel:`AlarmNotification`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - classification
      - String
      - Classification filter
      - Must be one of: 'performance', 'security', 'health' or ''.
      - 
    * - groups
      - List<String> |star|
      - List of groups
      - 
      - 
    * - severity
      - String
      - Severity filter
      - Must be one of: 'low', 'critical'
      - 

*Base Schemas* `Named`_, `Title`_


HealthChecks
-------------

Container for `Route53HealthCheck`_ objects.

.. _HealthChecks:

.. list-table:: :guilabel:`HealthChecks` |bars| Container<`Route53HealthCheck`_>
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


SimpleCloudWatchAlarm
^^^^^^^^^^^^^^^^^^^^^^


A Simple CloudWatch Alarm
    

.. _SimpleCloudWatchAlarm:

.. list-table:: :guilabel:`SimpleCloudWatchAlarm`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - actions_enabled
      - Boolean
      - Actions Enabled
      - 
      - 
    * - alarm_description
      - String
      - Alarm Description
      - Valid JSON document with Paco fields.
      - 
    * - comparison_operator
      - String
      - Comparison operator
      - Must be one of: 'GreaterThanThreshold','GreaterThanOrEqualToThreshold', 'LessThanThreshold', 'LessThanOrEqualToThreshold'
      - 
    * - dimensions
      - List<Dimension_>
      - Dimensions
      - 
      - 
    * - evaluation_periods
      - Int
      - Evaluation periods
      - 
      - 
    * - metric_name
      - String |star|
      - Metric name
      - 
      - 
    * - namespace
      - String
      - Namespace
      - 
      - 
    * - period
      - Int
      - Period in seconds
      - 
      - 
    * - statistic
      - String
      - Statistic
      - 
      - 
    * - threshold
      - Float
      - Threshold
      - 
      - 



CloudWatchLogRetention
^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudWatchLogRetention:

.. list-table:: :guilabel:`CloudWatchLogRetention`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - expire_events_after_days
      - String
      - Expire Events After. Retention period of logs in this group
      - 
      - 



CloudWatchLogSets
------------------


Container for `CloudWatchLogSet`_ objects.
    

.. _CloudWatchLogSets:

.. list-table:: :guilabel:`CloudWatchLogSets` |bars| Container<`CloudWatchLogSet`_>
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


CloudWatchLogSet
-----------------


A set of Log Group objects
    

.. _CloudWatchLogSet:

.. list-table:: :guilabel:`CloudWatchLogSet`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - log_groups
      - Container<CloudWatchLogGroups_>
      - A CloudWatchLogGroups container
      - 
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


CloudWatchLogGroups
^^^^^^^^^^^^^^^^^^^^


Container for `CloudWatchLogGroup`_ objects.
    

.. _CloudWatchLogGroups:

.. list-table:: :guilabel:`CloudWatchLogGroups` |bars| Container<`CloudWatchLogGroup`_>
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


CloudWatchLogGroup
^^^^^^^^^^^^^^^^^^^


A CloudWatchLogGroup is responsible for retention, access control and metric filters
    

.. _CloudWatchLogGroup:

.. list-table:: :guilabel:`CloudWatchLogGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - log_group_name
      - String
      - Log group name. Can override the LogGroup name used from the name field.
      - 
      - 
    * - metric_filters
      - Container<MetricFilters_>
      - Metric Filters
      - 
      - 
    * - sources
      - Container<CloudWatchLogSources_>
      - A CloudWatchLogSources container
      - 
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


CloudWatchLogSources
^^^^^^^^^^^^^^^^^^^^^


A container of `CloudWatchLogSource`_ objects.
    

.. _CloudWatchLogSources:

.. list-table:: :guilabel:`CloudWatchLogSources` |bars| Container<`CloudWatchLogSource`_>
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


CloudWatchLogSource
^^^^^^^^^^^^^^^^^^^^


Log source for a CloudWatch agent.
    

.. _CloudWatchLogSource:

.. list-table:: :guilabel:`CloudWatchLogSource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - encoding
      - String
      - Encoding
      - 
      - utf-8
    * - log_stream_name
      - String |star|
      - Log stream name
      - CloudWatch Log Stream name
      - 
    * - multi_line_start_pattern
      - String
      - Multi-line start pattern
      - 
      - 
    * - path
      - String |star|
      - Path
      - Must be a valid filesystem path expression. Wildcard * is allowed.
      - 
    * - timestamp_format
      - String
      - Timestamp format
      - 
      - 
    * - timezone
      - String
      - Timezone
      - Must be one of: 'Local', 'UTC'
      - Local

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


MetricFilters
^^^^^^^^^^^^^^


Container for `Metric`Filter` objects.
    

.. _MetricFilters:

.. list-table:: :guilabel:`MetricFilters` |bars| Container<`MetricFilter`_>
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


MetricFilter
^^^^^^^^^^^^^


    Metric filter
    

.. _MetricFilter:

.. list-table:: :guilabel:`MetricFilter`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - filter_pattern
      - String
      - Filter pattern
      - 
      - 
    * - metric_transformations
      - List<MetricTransformation_>
      - Metric transformations
      - 
      - 

*Base Schemas* `Named`_, `Title`_


MetricTransformation
^^^^^^^^^^^^^^^^^^^^^


Metric Transformation
    

.. _MetricTransformation:

.. list-table:: :guilabel:`MetricTransformation`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - default_value
      - Float
      - The value to emit when a filter pattern does not match a log event.
      - 
      - 
    * - metric_name
      - String |star|
      - The name of the CloudWatch Metric.
      - 
      - 
    * - metric_namespace
      - String
      - The namespace of the CloudWatch metric. If not set, the namespace used will be 'AIM/{log-group-name}'.
      - 
      - 
    * - metric_value
      - String |star|
      - The value that is published to the CloudWatch metric.
      - 
      - 



Metric
-------


A set of metrics to collect and an optional collection interval:

- name: disk
    measurements:
    - free
    collection_interval: 900
    

.. _Metric:

.. list-table:: :guilabel:`Metric`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - collection_interval
      - Int
      - Collection interval
      - 
      - 
    * - drop_device
      - Boolean
      - Drops the device name from disk metrics
      - 
      - True
    * - measurements
      - List<String>
      - Measurements
      - 
      - 
    * - name
      - String
      - Metric(s) group name
      - 
      - 
    * - resources
      - List<String>
      - List of resources for this metric
      - 
      - 


