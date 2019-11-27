The Paco CLI
============

The ``paco`` CLI is used to create, update and delete your cloud resources.

The CLI is divided into sub-commands. Run ``paco --help`` to see them:

.. code-block:: text

    $ paco --help
    Usage: paco [OPTIONS] COMMAND [ARGS]...

    Paco: Application Infrastructure Manager

    Options:
    --version  Show the version and exit.
    --help     Show this message and exit.

    Commands:
    delete     Delete Paco managed resources
    init       Commands for initializing Paco projects.
    provision  Provision resources to the cloud.
    validate   Validate an Paco project


For most commands, you will need to tell ``paco`` where your Paco config directory is located.
You can do this with the ``--home`` argument, or you can set an ``PACO_HOME``
environment variable.

Init
----

The ``paco init`` is divided into sub-commands:

* ``paco init project <project-name>``: Creates a new directory with a boilerplate Paco project in it.

* ``paco init credentials``: Initializes the .credentials file for an Paco project.

*  ``paco init accounts``: Initializes the accounts for an Paco project.

Cloud commands
--------------

There are three cloud commands to interact with the cloud:

* ``paco validate <CONFIG_SCOPE>``: Generates CloudFormation and validates it with AWS.

* ``paco provision <CONFIG_SCOPE>``: Creates or updates cloud resources.

* ``paco delete <CONFIG_SCOPE>``: Deletes cloud resources.

The CONFIG_SCOPE argument is a reference to a location with the Paco project configuration.

CONFIG_SCOPE must be an Paco reference to an Paco object. These are
constructed by matching a top-level directory name, then a filename in that directory
then optionally walking through keys within that file. Each part is
separated by the . character. The ``netenv`` files are all automatically scoped within
the top-level ``environments`` key.

.. code-block:: text

    account. objects : AWS Accounts
      Location: files in the `Accounts` directory.
      Examples:
        accounts.dev
        accounts.master

    resource. objects : Global Resources
      Location: files in the `Resources` directory.
      examples:
        resource.ec2.keypairs.mykeypair
        resource.cloudtrail
        resource.codecommit
        resource.iam

    netenv. objects : NetworkEnvironments
      Location: files in the `NetworkEnvironments` directory.
      examlpes:
        netenv.mynet.dev
        netenv.mynet.dev.us-west-2
        netenv.mynet.dev.us-west-2.applications.myapp.groups.somegroup.resources.webserver

    service. objects : AIM Pluggable Extensions
      Location: files in the `Services` directory.
      examples:
        service.notification
        service.security