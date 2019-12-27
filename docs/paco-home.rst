.. _paco-home:

Using PACO_HOME
===============

With the exception of creating a new Paco project with ``paco init project`` all of the
Paco commands operate on a Paco project. This is a directory of YAML files that conform to
Paco project schemas.

These commands can all be run with a ``--home`` option to specify the path to this project.
For example:

.. code-block:: bash

    paco provision netenv.mynet.dev --home=/Users/username/projects/my-paco-project

However, it's tedious to need to type the full path to the Paco project for every command.
You can change the current working directory to a Paco project and use ``--home=.`` but
then you can't change directories.

The PACO_HOME environment variable can also be used to specify the Paco project home directory.
You can export this environment variable on a BASH shell with the command:

.. code-block:: bash

    export PACO_HOME=/Users/username/projects/my-paco-project

If you will only be working on a single Paco project, you could export this environment variable
in your ``~/.bash_profile``. However, if you are using more than one Paco project, we recommend
putting a file named ``profile.sh`` in your Paco project's root directory that looks like this:

.. code-block:: bash

    export PACO_HOME=/Users/username/projects/my-paco-project
    export PS1="(my-paco-project) \h \W$ "

Then you can simply change directory to your Paco project and source the profile.sh file:

.. code-block:: bash

    $ cd ~/projects/my-paco-project
    $ source profile.sh
    (my-paco-project) hostname my-paco-project$

Exporting the PS1 environment variable will remind you which Paco project is currently active
in the PACO_HOME environment variable.

If you keep your Paco project in a git repo (which we highly recommend) and this is
shared with other users, they will have different paths to their PACO_HOME. In this case,
you can create a new ``profile.sh`` file after each time you clone a Paco project repo and
put ``profile.sh`` in your ``.gitignore`` file to keep yourself from committing it to the repo.

Finally, if you have a project installation tool that is used to ensure that you are using
the same fixed version of Paco and it's dependencies, it may also be able to use it dynamically create
a ``profile.sh`` for your convenience.



