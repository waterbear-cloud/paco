.. _quickstart:

Quickstart Lab 101
==================

This quickstart will walk you through creating the AWS resources for a basic network that
hosts a simple application. The application will have separate ``development`` and ``production``
environments.

This quickstart will walk you through:

  1. Installing AIM.

  #. Create an AIM Administration IAM User in AWS.

  #. Create an AIM project.

  #. Add configuration for the network.

  #. Add configuration for the application.

  #. Add configuration for the development and production environments.

  #. Provision a complete working application.

  #. Clean-up. Delete your AWS Resources when you are finished.


Install AIM
-----------

AIM is installable as a Python package. You can install it with pip:

``pip install aim``

For more details, see the Installation_ page. After you have installed
AIM you should have ``aim`` available on your comand-line.
Try running ``aim --help`` to confirm that's it's properly installed.

.. _Installation: ./install.html

Create an AIM Administration User
---------------------------------

Maybe create an AWS Account?

Install a CloudFormation template.

Create access keys.

Create an AIM Project
---------------------

An AIM Project is a directory of specially named sub-directories
containing YAML files each requiring speccific formats.
These configuration sub-directories and files are documented
on the `AIM Configuration`_ page.

.. _`AIM Configuration`: ./aim-config.html

The ``aim init`` command will create a skeleton directory structure
to help you get started quickly.

.. code-block:: text

    $ aim init

    AIM Project initialization
    --------------------------

    About to create a new AIM Project directory at /Users/kteague/water/temparoo

    Select starting_template:
    1 - empty
    2 - simple-web-app
    Choose from 1, 2 (1, 2) [1]: 2

You will be asked questions about your project. First, choose ``2`` to use the
``simple-web-app`` template. This will give you basic network, with a simple
application that is deployed into two environments.

You will be asked for a ``project_title`` and ``project_name``. The title is a
human-readable string, so you can use space and other characters. The name will
be used not only as the directory name of your project, but will also be a key
which is used in the name of AWS resources. The name should be short, only
contain alphanumeric, underscore or hyphen characters.

.. code-block:: text

    project_title [My AIM Project]: First Project
    project_name [first_project]: first_project

Next you will be asked for network and application titles and names. In this simple
walkthrough, you will create one network and one application. In more complex
AIM uses, you can create a single network and deploy mulitple applications into it.

.. code-block:: text

    network_environment_title [My AIM NetworkEnvironment]: Basic Network
    network_environment_name [basic_network]: basic_network
    application_title [My AIM Application]: Apache Web Server
    application_name [apache_web_server]: apache_web_server


You will be asked for a default AWS Region name, if you don't know
the AWS Region names, you can use ``us-west-2``:

.. code-block:: text

    aws_default_region [Administrator Default AWS Region]: us-west-2

Finally, you will supply the AWS Account and Administrator credentials.
You can leave this blank if you don't have them handy, and edit the file at
``<my-aim-project>/Accounts/.credentials`` to add them later.

.. code-block:: text

    master_account_id [Master AWS Account Id]: 1234567890
    master_admin_iam_username [Master Admin IAM Username]: Administrator
    aws_access_key_id [Administrator AWS Access Key ID]: ********
    aws_secret_access_key [Administrator AWS Secret Access Key]: ********

At this point you should have a working AIM Project. You can run the
``aim describe`` command to get a summary of your project. This will
also ensure that your files are in the correct format.

.. code-block:: text

    $ aim --home ./first_project/ describe
    Project: first_project - First Project
    Location: /Users/kteague/water/temparoo/first_project

    Accounts
    - .credentials -

    Network Environments
    - basic_network - Basic Network









Add network configuration
-------------------------

Intro to Networks and the config.

Add application configuration
-----------------------------

Intro to applications and the config.

Add environment configuration
-----------------------------

Into to environments and the config.

Provision your environments
---------------------------

Run "aim provision"

Clean-up and next steps
-----------------------

Run "aim delete".

Look at Quickstart 201.

Look at the AIM Configuration docs.

