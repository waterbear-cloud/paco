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

The ``aim`` CLI will be used to create CloudFormation stacks in your AWS
accounts. You can run this command and it will give you usage help:

.. code-block:: text

    $ aim
    Usage: aim [OPTIONS] COMMAND [ARGS]...

    AIM: Application Infrastructure Manager

    Options:
    --home DIRECTORY  Path to an AIM Project configuration folder. Can also be
                        set with the environment variable AIM_HOME.
    -v, --verbose     Enables verbose mode.
    --help            Show this message and exit.

    Commands:
  delete     Delete AIM managed resources
  describe   Describe an AIM project
  provision  Provision an AIM project or a specific environment.
  validate   Validate an AIM project

You will need to tell ``aim`` where your AIM config directory is located.
You can do this with the ``--home`` argument, or you can set an ``AIM_HOME``
environment variable. If you are following along through this quickstart,
set an environment variable in your shell, all of the rest of the commands
in this quickstart assume you have an ``AIM_HOME`` environment variable set:

.. code-block:: bash

    export AIM_HOME=~/my-aim-project/config/

Lets see how the ``aim describe`` command works, it will give us a simple
overview of what's in the project. It's also a good command to run to ensure
that you have a valid AIM configuration files.

.. code-block:: text

    $ aim describe
    Project: my-aim-project - AIM Example project
    Location: /Users/username/work/my-aim-project/config/

    Accounts
    - dev - Development AWS Account
    - prod - Production AWS Account

    Network Environments
    - my-aim-project -

You will see errors if your AIM config files aren't valid. AIM will attempt to
explain why your files are invalid, but this is an area that still needs improvement,
if you get stuck on these errors messages, drop us an email at hello@waterbear.cloud or
create a GitHub issue_:

.. _issue: https://github.com/waterbear-cloud/aim/issues

Provision your first AIM environment
------------------------------------

The ``aim provision`` command is used to create and update CloudFormation stacks into
your AWS accounts. This command requires a ``CONTROLLER_TYPE`` argument and optionally takes
a ``COMPONENT_NAME`` and ``CONFIG_NAME``. Most of the time you use this command, the
``CONTROLLER_TYPE`` will be ``NetEnv``, which will create the NetworkEnvironments and Applications
defined in your configs ``NetworkEnvironments`` sub-directory.

The ``COMPONENT_NAME`` will be the filename of a file in the ``NetworkEnvironments`` sub-directory.
This parameter is required when using the ``NetEnv`` controller type.

The ``CONFIG_NAME`` is optional and for a ``NetEnv`` controller will specify an Environment within
a given NetworkEnvironment. This will typically be ``dev`` or ``prod`` and we will use this option
in the quickstart to build out only the resources for the ``dev`` environment first.

Finally the ``CONFIG_REGION`` option lets you specify an AWS Region. This is useful if you want to
update an application and environment in only a single region, if you have a multi-region deployment.

.. code-block:: bash

   $ aim provision NetEnv my-aim-project dev

Inspect your AIM environment in the AWS Console
-----------------------------------------------

Login to the AWS Console, switch to the account you have deployed into
and go to the CloudFormation service. You should see these CloudFormation stacks:

.. code-block:: text

   some-stacks

Now go to the EC2 service and you should see an EC2 instance running in an autoscaling group.

Congratulations, now you have a fully working AWS environment!

Update your AIM environment
---------------------------

Make some changes ... test it out

Delete your AIM environment
---------------------------

Done with the Quickstart. Clean-up by deleting everything.
