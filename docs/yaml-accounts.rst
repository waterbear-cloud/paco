
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



Account
--------


Cloud accounts.

The specially named `master.yaml` file is for the AWS Master account. It is the only account
which can have the field `organization_account_ids` which is used to define and create the
child accounts.

.. code-block:: yaml
    :caption: Example accounts/master.yaml account file

    name: Master
    title: Master AWS Account
    is_master: true
    account_type: AWS
    account_id: '123456789012'
    region: us-west-2
    organization_account_ids:
      - prod
      - tools
      - dev
    root_email: master@example.com

.. code-block:: yaml
    :caption: Example accounts/dev.yaml account file

    name: Development
    title: Development AWS Account
    account_type: AWS
    account_id: '123456789012'
    region: us-west-2
    root_email: dev@example.com



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
      - Paco-Organization-Account-Delegate-Role
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

