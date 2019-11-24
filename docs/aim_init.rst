.. _aim_init:

Getting Started with AIM
========================

Once you have the `aim` command-line installed, to get up and running you will need to:

  1. Create an AIM project.

  2. Create an IAM User and Role in your AWS account.

  3. Connect your AIM project with your IAM User and Role.


Create an AIM project
---------------------

The ``aim init`` command is there to help you get started with a new AIM project.
It will let you create a new AIM project from a template and connect that project
to your AWS account(s).

First you will use the ``aim init project`` command to create a new project. This
command takes as a single arguement the name of directory to create with your
new AIM project files. Run it with:

.. code-block:: bash

  $ aim init project <my-aim-project>

You will be presented with a series of questions about your new project.

You will be asked to supply some ``name`` and ``title`` values. AIM makes an important distinction
between a ``name`` field and a ``title`` field. The ``name`` fields are used to construct unique
resource names in AWS, while ``title`` is for human-readable descriptions.

.. Note:: **Name guidelines in AIM**

    1. AWS resources have different character set restrictions.
        We recommend using only alphanumeric charcters and the hyphen character in names (a-zA-Z-).

    2. Try to limit names to only 3 to 5 characters.
        AIM ``name`` fields are concatenated together to create unique names. Certain AWS resources names
        are limited to only 32 characters. If you use long names they may be too long for AWS.

    3. Names can not be changed after they provsion AWS resources.
        Names identify resources in AWS. Once you use AIM to create resources in AWS, if you
        change ``name`` fields AIM will no longer know where those resources are. The only way
        to change a ``name`` field is to delete the resources, change the name, and create new ones.

An example set of answers for creating an AIM project:

.. code-block:: bash

    project_title: My AIM Project
    network_environment_name: ne
    network_environment_title: My AIM Network
    application_name: app
    application_title: My Application
    aws_default_region: us-west-2
    master_account_id: 123456789012
    master_root_email: you@example.com

After this you will have a new directory of files that comprises and AIM project.

The path to this AIM Project directory is called your AIM home. The rest of the commands
you run will need this path supplied with the `--home` CLI option. For macos and linux users,
there is also a file named `profile.sh` which will export an `AIM_HOME`
environment variable to your shell. This environment variable can be used to make it easier
by avoiding the need to type out the `--home` option for every command:

.. code-block:: bash

  $ source my-aim-project/profile.sh
  (My AWS AIM Project) laptop username$


Create a User and Role in your AWS account
------------------------------------------

When you run AIM it will requrie access to your AWS account.

AIM requires access key credentials for an IAM User that has permissions to switch
to an IAM Role that delegates full Administrator access. The reason for having the Administrator
privileges in a Role and not the User is so that multi-factor authentication (MFA) can be enforced.
MFA protects you if your access key credentials are accidentaly exposed.

You can use any User and Role in your IAM account, but follow the steps below to
install a CloudFormation template that will create a dedicated User and Role to use with AIM.

  1. Download the AIMInitialization.yaml_ CloudFormation template.

  #. Login to the AWS Console, visit the CloudFormation Service and click on the
     "Create stack (with new resources (standard))" button. Choose "Upload a template file" and
     then "Choose file" and choose the AIMInitialization.yaml file. Then click "Next".

     .. image:: ./images/quickstart101-create-stack-init.png

  #. Enter "AIMAccess" as the Stack name and enter the name of a new IAM User. Then click "Next".

     .. image:: ./images/quickstart101-stack-init-details.png

  #. On the "Configure stack options" screen you can leave everything default and click "Next".
     On the "Review AIMInitialization" you can also leave all the defaults click
     "I acknowledge that AWS CloudFormation might create IAM resources with custom names."
     to confirm that this stack can create an IAM User.
     Finally click "Create stack".

.. _AIMInitialization.yaml: ./_static/templates/AIMInitialization.yaml

Next you will need to set-up the new User account with an API key:

  1. In the AWS Console, go to the Identity and Access Management (IAM) Service, click on "Users"
     and click on the User name you supplied earlier. Then click on the "Security credentials" tab.

     .. image:: ./images/quickstart101-user-start.png

  #. Set-up multi-factor authentication (MFA). Where it says, "Assigned MFA device" click on "Manage".
     Choose "Virtual MFA device" and use either Authy_ or `Google Authenticator`_ on your computer or phone
     as a virtual MFA device.

  #. Create an AWS Access Key. While still on the "Security credentials" tab, click on "Create access key".
     You will be given an "Access key ID" and "Secret access key". Copy these and you will use them
     to configure your AIM credentials next.

.. Note::

    If you no longer want to use AIM, you can go to CloudFormation and delete the stack that you created.
    However, before you delete the stack, you will need to return to this user and manually delete the
    Assigned MFA Device and Access key. If you try and delete the stack without doing this first, you will get the
    error message "DELETE_FAILED: Cannot delete entity, must delete MFA device first.".

Connect your AIM project with your AWS account
----------------------------------------------

Next use the ``aim init credentials`` command to initialize your credentials. Enter the name of your IAM User
if you used the CloudFormation template your role name will be ``AIM-Admin-Delegate-Role``.

.. code-block:: bash

    $ aim init credentials --home=/path/to/your-aim-project

    AIM Project Credentials Initialization
    --------------------------------------

    master_admin_iam_username: <your-aim-username>
    admin_iam_role_name: AIM-Admin-Delegate-Role
    aws_access_key_id: AKIA***********4MXP
    aws_secret_access_key: 56aU******************57cT

This will create a file named ``.credentials`` in your AIM project directory. Starting AIM projects also have a ``.gitignore``
file that will prevent you from committing this credentials file to a git repo. You can save this file somewhere secure,
or if it is lost use the AWS Console to create a new acccess key for your IAM User and re-run ``aim init credentials`` to
generate a new ``.credentials`` file.

Finally, use the ``aim validate`` command to verify your credentials work. The ``aim validate`` command generates CloudFormation
templates and verifies them for correctness against your AWS account, but it will never modify any AWS resources.

.. code-block:: bash

    $ aim validate netenv.ne.prod


.. _Authy: https://authy.com/

.. _`Google Authenticator`: https://en.wikipedia.org/wiki/Google_Authenticator


