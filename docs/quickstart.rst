.. _quickstart:

Quickstart
==========

AIM Configuration Directory
---------------------------

You will need a directory of YAML that describes
your cloud infrastructure.

ToDo: How to create a starting directory template?

.. code-block:: text

    aim-project
        ├── Accounts
        │   └── dev.yaml
        │   └── prod.yaml
        ├── MonitorSets
        │   └── AlarmSets.yaml
        │   └── LogSets.yaml
        ├── NetworkEnvironments
        │   └── my-app.yaml
        ├── Services
        │   └── S3.yaml
        ├── project.yaml

Account Set-up
--------------

You will need to give AIM access to an AWS account. AIM is intended to be
used with AWS Organizations to be multi-account.

ToDo: How to set this up?

Running AIM CLI
---------------

The `aim` CLI will be used to create CloudFormation stacks in your AWS
accounts.




