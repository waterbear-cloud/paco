.. _workflow:

Paco Workflows
==============

Workflows describe the processes around how Paco is used to change cloud resources.


Enforce Git Branches for Environments
-------------------------------------

If you want to make changes to Paco configuration that is not yet ready to be applied
to other environments then it is recommended to use a Git branch for each environment.

For example, if you have a ``test`` environment and a ``prod`` environment, you can override changes
between the test and prod environments directly in the NetworkEnvironment file and provision both
environments from the same Git branch. But what happens if you are making bigger changes between
environments? What if you want to be less rigorous about changes to your ``test`` environment, but
don't want a mistake to inadvertently be carried into your ``prod`` environment?

You can create a Git branch for each environment, then apply changes to one environment and test
them before merging from one environment branch to the next and applying them there. The Paco default
for naming your branches is:

.. code-block:: text

    ENV-<environment-name>

For example, with ``dev``, ``test`` and ``prod`` environments you would create these Git branches:

.. code-block:: text

    master
    ENV-dev
    ENV-test
    ENV-prod

Then you would only run ``paco provision netenv.mynet.test`` from within the ``ENV-test`` branch, after tests
pass you would merge those changes into the ``ENV-prod`` branch and then from that branch run
``paco provision netenv.mynet.prod``.

For provisioning global resources you can additionally designate those changes can happen from a designated branch.
The suggested default for global resources is ``prod``.

The Paco project's ``project.yaml`` configuration lets you enforce this Git branch workflow, and will
prevent you from accidentally applying changes in an ``ENV-test`` branch to a prod environment.

The configuration to enable this beviour is in a Paco project's ``project.yaml`` file and is:

.. code-block:: yaml

    version_control:
      enforce_branch_environments: true

You can supply additional configuration if you don't want to use Paco's default conventions:

.. code-block:: yaml

    version_control:
      enforce_branch_environments: true
      environment_branch_prefix: "AWS_ENV_"
      git_branch_environment_mappings:
        - production:master
      global_environment_name: production

That additional configuration options allows you to configure different Git branch prefix names, map to branch
names that don't have a prefix or follow a convention, and change the environment that can provision global resources.
