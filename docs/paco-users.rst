.. _paco-users:

Managing IAM Users with Paco
============================

The `Getting Started with Paco` showed you how to create an IAM User and Role that
was able to allow a Paco project access to your AWS account. However, what if you
have several people working in your AWS accounts and you want each one to
have thier own dedicated account?

Paco can create IAM Users for you. It will also help you to configure permissions
allowing a user cross-account access if you have a multi-account set-up. Each
multi-account user can be granted access to all accounts, or restricted just to
certain accounts. In addition, each user can have full admin access or have
limited access.

For example, you could allow one user access to update a dev account
but restrict them from accessing a production account. Or you could allow
other users only access to CodeCommit and CodePipeline to only do
application deployments.


IAM Users with resource/iam.yaml
--------------------------------

A Paco project can have a ``resource/iam.yaml`` file that defines IAM Users.

.. code-block:: yaml

    users:
      yourusername:
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

Each user can be given access to all accounts or just certain ones. Use the ``account_whitelist``
with a comma-seperated list for this:

.. code-block:: yaml

    account_whitelist: dev,staging,tools # limit to only the dev, staging and tools accounts

    account_whitelist: all # special keyword for all accounts

Each user can be given full administrator access or limited to custom policies that only allow specific
access. Use the ``permissions`` field for this:

.. code-block:: yaml

    permissions:
      # grants full access to all accounts that are defined in the account_whitelist field
      administrator:
        type: Administrator
        accounts: all

      # grants custom access to only a test account
      custom:
        type: CustomPolicy
        accounts: test
        policies:
          - name: CloudWatchLogs
            statement:
              - effect: Allow
                action:
                  - logs:Describe*
                  - logs:Get*
                  - logs:List*
                resource:
                  - '*'

After you have added user(s) to ``resource/iam.yaml`` run:

.. code-block:: bash

    paco provision resource.iam.users


This will generate a starting password for each user as well as an API key if ``programmatic_access``
was enabled for them.


Setting up a new User
---------------------

A new user will first need to `sign-in to the AWS Console`_ with the AWS account id (with the master account
id in a multi-account set-up), their username and starting password.

After signing in, they will be prompted to set a new password. After they are signed in, the only permission they
will have is to set an MFA device for their User account. They will need to go to the IAM service, click on Users,
then click on their User account. Then under the **Security Credentials** tab they need to click on the link **Manage**
beside "Assign MFA Device". For more information, see AWS docs on `Enabling MFA Devices`_.

Assuming a Role
---------------

Paco will only grants a User the ability to view and set their password and MFA device and the ability to
**assume a role**. All permissions that a User will typically use must be gained by first assuming a Role
that contains those permissions. This is done for security, as when a Role is assumed, it can enfore that
the user has logged in with MFA.

Note that the first time a User logs in and sets MFA, they must then log out and log in again with their
new MFA credentials. Only then will they be able to assume a Role.

In the AWS Console, assuming a Role is called switching roles, see the AWS docs on `Switching to a Role`_.
Each Role created by Paco will have a roleName in the format ``IAM-User-Account-Delegate-Role-<username>``.

A user signed in to the console can switch roles by visiting a link in the format:

.. code-block:: bash

    https://signin.aws.amazon.com/switchrole?account=123456789012&roleName=IAM-User-Account-Delegate-Role-<username>

If you visit the CloudFormation service you can also see this in the ``Resource-IAM-*`` stacks on the Outputs
tab with the Key ``SigninUrl``.

AWS Extend Switch Roles
-----------------------

In a multi-account set-up, the AWS Console will only remember the five most recently used Roles. If you
access more than five Roles, you will need to either manage Bookmarks with the SigninUrl for every Role
or consider using the **AWS Extend Switch Roles** browser extension for `Chrome`_ or `Firefox`_.

After you've installed this extension, you will see a green key in the top right of your browser.
Click on **Configuration** and enter your configuration. You can use the example configuration
below and replace ``<username>`` with your own username and refer to your Paco project ``accounts``
directory for the account id for your child accounts. Suggested colors are also provided ;P


.. code-block:: bash

        [profile AwsOrgName Master]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = 000000

        [profile AwsOrgName Prod]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = 800000

        [profile AwsOrgName Stage]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = 4f901a

        [profile AwsOrgName Dev]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = 008080

        [profile AwsOrgName Tools]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = 8000ff

        [profile AwsOrgName Security]
        aws_account_id = 123456789012
        role_name = IAM-User-Account-Delegate-Role-<username>
        color = e26453


.. _Getting Started with Paco: ./started.html

.. _sign-in to the AWS Console: https://signin.aws.amazon.com/

.. _Enabling MFA Devices: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable.html

.. _Switching to a Role: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html

.. _Chrome: https://chrome.google.com/webstore/detail/aws-extend-switch-roles/jpmkfafbacpgapdghgdpembnojdlgkdl?hl=en

.. _Firefox: https://addons.mozilla.org/en-US/firefox/addon/aws-extend-switch-roles3/
