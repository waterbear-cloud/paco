
.. _yaml-global-resources:

Global Resources
================

Global Resources are defined in the top-level ``resource/`` directory. They define cloud resources
which do not belong to an environment or other logical grouping.


CloudTrail
-----------


The ``resource/cloudtrail.yaml`` file specifies CloudTrail resources.

AWS CloudTrail logs all AWS API activity. Monitor and react to changes in your AWS accounts with CloudTrail.
A CloudTrail can be used to set-up a multi-account CloudTrail that sends logs from every account into a single S3 Bucket.

.. code-block:: bash

    paco provision resource.cloudtrail

.. sidebar:: Prescribed Automation

    ``enable_kms_encryption``: Encrypt the CloudTrai logs with a Customer Managed Key (CMK). Paco will create
    a CMK for the CloudTrail in the same account as the ``s3_bucket_account``.

    ``kms_users``: A list of either IAM User names or paco references to ``resource/iam.yaml`` users. These
    users will have access to the CMK to decrypt and read the CloudTrail logs.

.. code-block:: yaml
    :caption: example resource/cloudtrail.yaml configuration

    trails:
      mycloudtrail:
        enabled: true
        region: 'us-west-2'
        cloudwatchlogs_log_group:
          expire_events_after_days: '14'
          log_group_name: CloudTrail
        enable_log_file_validation: true
        include_global_service_events: true
        is_multi_region_trail: true
        enable_kms_encryption: true
        kms_users:
          - bob@example.com
          - paco.ref resource.iam.users.sallysmith
        s3_bucket_account: paco.ref accounts.security
        s3_key_prefix: cloudtrails



.. _CloudTrail:

.. list-table:: :guilabel:`CloudTrail`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - accounts
      - List<PacoReference>
      - Accounts to enable this CloudTrail in. Leave blank to assume all accounts.
      - Paco Reference to `Account`_.
      - 
    * - cloudwatchlogs_log_group
      - Object<CloudWatchLogGroup_>
      - CloudWatch Logs LogGroup to deliver this trail to.
      - 
      - 
    * - enable_kms_encryption
      - Boolean |star|
      - Enable KMS Key encryption
      - 
      - False
    * - enable_log_file_validation
      - Boolean
      - Enable log file validation
      - 
      - True
    * - include_global_service_events
      - Boolean
      - Include global service events
      - 
      - True
    * - is_multi_region_trail
      - Boolean
      - Is multi-region trail?
      - 
      - True
    * - kms_users
      - List<PacoReference> |star|
      - IAM Users with access to CloudTrail bucket
      - Paco Reference to `IAMUser`_. String Ok.
      - 
    * - region
      - String
      - Region to create the CloudTrail
      - Must be a valid AWS Region name or empty string
      - 
    * - s3_bucket_account
      - PacoReference |star|
      - Account which will contain the S3 Bucket that the CloudTrails will be stored in
      - Must be an paco.ref to an account Paco Reference to `Account`_.
      - 
    * - s3_key_prefix
      - String
      - S3 Key Prefix specifies the Amazon S3 key prefix that comes after the name of the bucket.
      - Do not include a leading or trailing / in your prefix. They are provided already.
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


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



CodeCommit
^^^^^^^^^^^


Container for `CodeCommitRepositoryGroup`_ objects.
    

.. _CodeCommit:

.. list-table:: :guilabel:`CodeCommit` |bars| Container<`CodeCommitRepositoryGroup`_>
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
    * - external_resource
      - Boolean
      - Boolean indicating whether the CodeCommit repository already exists or not
      - 
      - False
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
    * - permissions
      - Choice
      - Permissions
      - Must be one of ReadWrite or ReadOnly
      - ReadWrite
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

*Base Schemas* `Named`_, `Title`_

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

IAM
---

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


IAM User represents a user that will exist in one account, but can also
have delegate IAM Roles in other accounts that they are allowed to assume.

.. code-block:: yaml
    :caption: example IAM User

    enabled: true
    account: paco.ref accounts.master
    username: yourusername
    description: 'Your Name - Paco Administrator'
    console_access_enabled: true
    programmatic_access:
      enabled: true
      access_key_1_version: 1
      access_key_2_version: 0
    account_whitelist: all
    permissions:
      administrator:
        type: Administrator
        accounts: all
      custom:
        accounts: dev
        managed_policies:
           - 'AWSDirectConnectReadOnlyAccess'
           - 'AmazonGlacierReadOnlyAccess'
        policies:
          - name: "AWS Polly full access"
            statement:
              - effect: Allow
                action:
                  - 'polly:*'
                resource:
                  - '*'

    

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

*Base Schemas* `Enablable`_


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


BaseRole
^^^^^^^^^



.. _BaseRole:

.. list-table:: :guilabel:`BaseRole`
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

*Base Schemas* `Named`_, `Title`_


Role
^^^^^

IAM Role that is disabled by default

.. _Role:

.. list-table:: :guilabel:`Role`
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

*Base Schemas* `BaseRole`_, `Deployable`_, `Named`_, `Title`_


RoleDefaultEnabled
^^^^^^^^^^^^^^^^^^^

IAM Role that is enabled by default

.. _RoleDefaultEnabled:

.. list-table:: :guilabel:`RoleDefaultEnabled`
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

*Base Schemas* `BaseRole`_, `Enablable`_, `Named`_, `Title`_


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
      - List of AWS Principals
      - 
      - 
    * - effect
      - Choice
      - Effect
      - Must be one of 'Allow' or 'Deny'
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
    * - condition
      - Dict
      - Condition
      - Each Key is the Condition name and the Value must be a dictionary of request filters. e.g. { "StringEquals" : { "aws:username" : "johndoe" }}
      - {}
    * - effect
      - Choice
      - Effect
      - Must be one of 'Allow' or 'Deny'
      - 
    * - principal
      - Object<Principal_>
      - Principal
      - 
      - 
    * - resource
      - List<String>
      - Resrource(s)
      - 
      - 

*Base Schemas* `Named`_, `Title`_


Principal
^^^^^^^^^^



.. _Principal:

.. list-table:: :guilabel:`Principal`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - aws
      - List<String>
      - List of AWS Principals
      - 
      - 
    * - service
      - List<String>
      - List of AWS Service Principals
      - 
      - 

*Base Schemas* `Named`_, `Title`_

Route 53
--------


Route53Resource
^^^^^^^^^^^^^^^^


The ``resource/route53.yaml`` file manages AWS Route 53 hosted zones.

Provision Route 53 with:

.. code-block:: bash

    paco provision resource.route53

.. code-block:: yaml
    :caption: Example resource/route53.yaml file

    hosted_zones:
      example:
        enabled: true
        domain_name: example.com
        account: aim.ref accounts.prod

    

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
    * - private_hosted_zone
      - Boolean
      - Make this hosted zone private.
      - 
      - False
    * - record_sets
      - List<Route53RecordSet_> |star|
      - List of Record Sets
      - 
      - 
    * - vpc_associations
      - PacoReference
      - The VPC the private hosted zone will be provisioned in.
      - Paco Reference to `VPC`_.
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

