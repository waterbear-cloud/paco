.. _installation:

Installation
============

AIM requires Python 3.7 or higher. As AIM requires newer release of Python, you may need to
download and install a Python_ interpreter.

Ideally you will want to install AIM in a self-contained Python environment. For some guidance
on managing Python applications check out `Python on macos`_ or `Python on Windows`_.

Install the `aim` Python package. If you are using `pip3` then you would run:

.. code-block:: bash

  $ pip3 install aim

You should now have a CLI application named `aim`.

.. code-block:: bash

  $ aim --help
  Usage: aim [OPTIONS] COMMAND [ARGS]...

    AIM: Application Infrastructure Manager
  ...

It is recommended for production usage to pin the version AIM that you are running with to the
project that contains the AIM configuration files.

Create an AIM Project and connect it to your AWS Accounts
---------------------------------------------------------

The AIM CLI contains a number of sub-commands. The first sub-command you will use is the `init`
sub-command. This command will get you started by creating a new AIM Project, configuring the
credentials file to connect the project to AWS and preparing your AWS accounts.

.. code-block:: bash

  $ aim init --help
  Usage: aim init [OPTIONS] COMMAND [ARGS]...

    Commands for initializing AIM Projects.

  Options:
    --help  Show this message and exit.

  Commands:
    accounts     Initializes the accounts for an AIM Project.
    credentials  Initializes the .credentials file for an AIM Project.
    project      Creates a new directory with a boilerplate AIM Project in it.

First you will use the `init` command to create a new project:

.. code-block:: bash

  $ aim init project my-aim-project

  AIM Project Initialization
  --------------------------

  About to create a new AIM Project directory at /Users/username/my-aim-project

  project_name: my-aim-project
  project_title: My AWS AIM Project
  network_environment_name: ne
  network_environment_title: My primary network
  application_name: site
  application_title: WordPress web site
  aws_default_region: us-west-2
  master_account_id: 123456789012
  master_root_email: you@example.com
  starting_template: simple-web-app

After this, you will have a new directory with AIM Project configuration files in it. The
path to this AIM Project directory is called your AIM home. The rest of the commands
you run will need this path supplied with the `--home` CLI option.

For macos and linux users, there is also a file named `profile.sh` which will export an `AIM_HOME`
environment variable to your shell. This environment variable can be used to make it easier
by avoiding the need to type out the `--home` option for every command:

.. code-block:: bash

  $ source my-aim-project/profile.sh
  (My AWS AIM Project) laptop username$

Next you will initialize your credentials:

.. code-block:: bash

  $ aim init credentials

  AIM Project Credentials Initialization
  --------------------------------------

  master_account_id: 123456789012
  aws_default_region: us-west-2
  aws_access_key_id: AKIAJJ5DR387HUYD
  aws_secret_access_key: ABeFAkEzKeyASeCr3TXF4ZcrBUFy7JrzvIhnSL
  master_admin_iam_username: aim-init
  admin_iam_role_name: AIM-Bootstrap-role



.. _Python: https://www.python.org/downloads/

.. _Python on macos: https://medium.com/@briantorresgil/definitive-guide-to-python-on-mac-osx-65acd8d969d0

.. _Python on Windows: https://docs.microsoft.com/en-us/windows/python/beginners
