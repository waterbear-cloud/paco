The AIM CLI
------------

The ``aim`` CLI is used to create, update and delete your cloud resources.

The CLI is divided into sub-commands. Run ``aim --help`` to see them:

.. code-block:: text

    $ aim --help
    Usage: aim [OPTIONS] COMMAND [ARGS]...

    AIM: Application Infrastructure Manager

    Options:
    --version  Show the version and exit.
    --help     Show this message and exit.

    Commands:
    delete     Delete AIM managed resources
    init       Commands for initializing AIM projects.
    provision  Provision resources to the cloud.
    validate   Validate an AIM project


For most commands, you will need to tell ``aim`` where your AIM config directory is located.
You can do this with the ``--home`` argument, or you can set an ``AIM_HOME``
environment variable.
