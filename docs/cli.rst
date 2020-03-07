.. _cli:

The Paco CLI
============

The ``paco`` CLI is used to create, update and delete your cloud resources.

The CLI is divided into sub-commands. Run ``paco --help`` to see them:

.. code-block:: text

    $ paco --help
    Usage: paco [OPTIONS] COMMAND [ARGS]...

    Paco: Prescribed Automation for Cloud Orchestration

    Options:
    --version  Show the version and exit.
    --help     Show this message and exit.

    Commands:
    delete     Delete cloud resources
    init       Create a new Paco project.
    provision  Create and configure cloud resources.
    validate   Validate cloud resources.


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

The CONFIG_SCOPE argument is a reference to an object in the Paco project configuration.

Config Scope
------------

A CONFIG_SCOPE is a valid Paco reference to a Paco object. Paco references start
at the top of the Paco project tree and walk their way down. Consider the following
Paco project:

.. code-block:: text

    paco-project/
      accounts/
        master.yaml
        prod.yaml
        dev.yaml
      monitor/
        Logging.yaml
        AlarmSets.yaml
      project.yaml
      netenv/
        saas.yaml
        intra.yaml
      resource/
        CloudTrail.yaml
        CodeCommit.yaml
        EC2.yaml
        IAM.yaml
        SNSTopics.yaml
        Route53.yaml
        S3.yaml
      service/
        CustomAddOn.yaml

The top-level directory named ``paco-project`` is the start of the scope and project configuration
is contained in the ``project.yaml`` file. You can not express this root scope with CONFIG_SCOPE.

CONFIG_SCOPE will start by expressing a directory in the Paco project. This can be one of four directories:
accounts, netenv, resource or service. We will look at how scope works in each directory.

.. Note:: **Case insensitive filenames**

    The YAML filenames are case-insensitive. The scope ``resource.cloudTRAIL`` will match
    the filename ``resource/CloudTrail.yaml``.

accounts scope
^^^^^^^^^^^^^^

The accounts directory only has a single scope: ``accounts``.

This will apply account actions on all accounts listed in the ``organization_account_ids:`` field
in the ``accounts/master.yaml`` file. Typically you will create new accounts by giving them names
in the ``organization_account_ids:`` list and then running ``paco provision accounts`` to create them.

There are no validate or delete commands for the accounts scope. If you need to delete an account, you should
`follow the AWS steps to close an account`_ and then delete the appropriate ``accounts/<account-name>.yaml`` file.

.. _follow the AWS steps to close an account: https://aws.amazon.com/premiumsupport/knowledge-center/close-aws-account/

netenv scope
^^^^^^^^^^^^

The netenv scope is used to select environments, regions and applications for a single NetworkEnvironment.

At a minimum, you must specify a NetworkEnvironment and Environment with this scope:

.. code-block:: text

    netenv.saas.dev

The NetworkEnvironment is the name of a YAML file in the netenv directory, e.g. ``netenv/saas.yaml``.

The Environment is the name of an environment in the ``environment:`` section of a netenv file.
For example, consider this netenv file:

.. code-block:: yaml

    network:
      title: "My SaaS network"
      enabled: true
      availability_zones: 2
      ...

    applications:
      saas:
        title: "My SaaS application"
        enabled: false
        ...

    environments:
      dev:
        title: "Development Environment"
        us-west-2:
          applications:
            saas:
              enabled: true
          network:
            aws_account: paco.ref accounts.dev
      prod:
        title: "Production Environment"
        default:
          applications:
            saas:
              enabled: true
          network:
            aws_account: paco.ref accounts.prod
        us-west-2:
          enabled: true
        eu-central-1:
          enabeld: true

The scopes available for this NetworkEnvironment are:

.. code-block:: text

     netenv.saas.dev
     netenv.saas.dev.us-west-2
     netenv.saas.prod
     netenv.saas.prod.us-west-2
     netenv.saas.prod.eu-central-1

After the NetworkEnvironment and Environment, the next component in the scope is the Region. If you
do not specify a Region and you can have configured your Environments to belong to more than one region,
Paco will apply the scope to all regions in that Environment.

You can drill down deeper than a Region. You may just want to update a single Application, which you can
select with the ``applications`` name and the name of the application:

.. code-block:: text

     netenv.saas.prod.us-west-2.applications.saas

Within an Application you can scope even deeper and select only a ResourceGroup or a single Resource:

.. code-block:: text

     netenv.saas.prod.us-west-2.applications.saas.groups.cicd
     netenv.saas.prod.us-west-2.applications.saas.groups.web.resources.server

Going this deep in the netenv scope is possible, but if you are trying to update some resources but not others,
consider using the ``change_protected: true`` configuration. This field can be applied to any Resource and if set
then Paco will never attempt to make any modifications to it:

.. code-block:: yaml

    saas:
      title: "My Saas App"
      enabled: false
      groups:
        web:
          type: Application
          enabled: true
          order: 10
          resources:
            servers:
              type: ASG
              # Tell Paco to never touch this resource
              change_protected: true


resource scope
^^^^^^^^^^^^^^

The resource scope is used to select global resources.

You must specify a minimum of a global Resource type and you must have a YAML file for that type:

.. code-block:: text

    resource.codecommit
    resource.ec2

These would scope to ``resource/codecommit.yaml`` and ``resource/ec2.yaml`` respectively. For most use cases,
you will want to apply changes to all configuration in a global resource and you can not specify deeper scopes.

A few resources allow for deeper scoping - however, unless you have a very large Resource file, it's encouraged
to simply scope the entire file:

CloudTrail resources in ``resource/cloudtrail.yaml``:

.. code-block:: text

    resource.cloudtrail # applies to all CloudTrails
    resource.cloudtrail.trails # also applies to all CloudTrails
    resource.cloudtrail.trails.<trail-name> # select a single CloudTrail

EC2 resources in ``resource/ec2.yaml``:

.. code-block:: text

    resource.ec2 # applies to all EC2 Keypairs
    resource.ec2.keypairs # also applies to all EC2 Keypairs
    resource.ec2.keypairs.<my-keypair> # select a single Keypair

IAM resources in ``resource/iam.yaml``:

.. code-block:: text

    resource.iam # applies to all IAM Users
    resource.iam.users # also applies to all IAM Users
    resource.iam.users.<my-user> # select a single IAM User

service scope
^^^^^^^^^^^^^

The service scope is used to select Paco extension resources.

You must specify a minimum of a global Resource type and you must have a YAML file for that type:

.. code-block:: text

    service.patch
    service.security

Typically you will only scope a complete add-on, but it is possible for an add-on to implement
deeper scopes. Consult the add-on documentation directly.
