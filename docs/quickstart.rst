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

Run "aim init project".

Run "aim describe".

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

