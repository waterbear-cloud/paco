Running AIM CLI
---------------

The ``aim`` CLI will be used to create CloudFormation stacks in your AWS
accounts. You can run this command and it will give you usage help:

.. code-block:: text

    $ aim
    Usage: aim [OPTIONS] COMMAND [ARGS]...

    AIM: Application Infrastructure Manager

    Options:
    --version      Show the version and exit.
    -v, --verbose  Enables verbose mode.
    --help         Show this message and exit.

    Commands:
    delete     Delete AIM managed resources
    init       Initializes AIM Project files
    provision  Provision an AIM project or a specific environment.
    validate   Validate an AIM project

For most commands, you will need to tell ``aim`` where your AIM config directory is located.
You can do this with the ``--home`` argument, or you can set an ``AIM_HOME``
environment variable.
