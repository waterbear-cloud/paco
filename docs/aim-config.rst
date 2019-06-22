
.. _aim-config:

AIM Configuration
=================

AIM configuration is a directory of files that make up an AIM project.
These files can describe networks, environments, applications, services,
accounts, and monitoring and logging configuration.


Accounts
--------

AWS account information is kept in the ``Accounts`` directory.
Each file in this directory will define one AWS account, the filename
will be the name of the account, with a .yml or .yaml extension.


.. list-table::
    :widths: 15 8 6 12 30
    :header-rows: 1

    * - Field name
      - Type
      - Required?
      - Default
      - Purpose
    * - account_id
      - TextLine
      - True
      - None
      - Account ID: Can only contain digits.
    * - account_type
      - TextLine
      - True
      - AWS
      - Account Type: Supported account types: AWS
    * - admin_delegate_role_name
      - TextLine
      - True
      - 
      - Administrator delegate IAM Role name for the account
    * - admin_iam_users
      - Dict
      - False
      - None
      - Admin IAM Users
    * - is_master
      - Bool
      - True
      - False
      - Boolean indicating if this a Master account
    * - name
      - TextLine
      - True
      - 
      - Name
    * - organization_account_ids
      - List
      - False
      - []
      - A list of account ids to add to the Master account's AWS Organization
    * - region
      - TextLine
      - True
      - us-west-2
      - Region to install AWS Account specific resources
    * - root_email
      - TextLine
      - True
      - None
      - The email address for the root user of this account
    * - title
      - TextLine
      - False
      - 
      - Title


NetworkEnvironments
-------------------

This is the show.

