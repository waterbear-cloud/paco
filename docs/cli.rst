The Paco CLI
-------------

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
