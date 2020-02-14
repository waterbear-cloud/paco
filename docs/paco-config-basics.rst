.. _paco-config-basics:

********************
Configuration Basics
********************

Paco configuration overview
===========================

Paco configuration is a complete declarative description of a cloud project.
These files semantically describe cloud resources and logical groupings of those
resources. The contents of these files describe accounts, networks, environments, applications,
resources, services, and monitoring configuration.

The Paco configuration files are parsed into a Python object model by the library
``paco.models``. This object model is used by Paco to provision
AWS resources using CloudFormation. However, the object model is a standalone
Python package and can be used to work with cloud infrastructure semantically
with other tooling.


File format overview
--------------------

Paco configuration is a directory of files and sub-directories that
make up an Paco project. All of the files are in YAML_ format.

In the top-level directory are sub-directories that contain YAML
files each with a different format. This directories are:

  * ``accounts/``: Each file in this directory is an AWS account.

  * ``netenv/``: Each file in this directory defines a complete set of networks, applications and environments.
    Environments are provisioned into your accounts.

  * ``monitor/``: These contain alarm and logging configuration.

  * ``resource/``: For global resources, such as S3 Buckets, IAM Users, EC2 Keypairs.

  * ``service/``: For extension plug-ins.

Also at the top level are ``project.yaml`` and ``paco-project-version.txt`` files.

The ``paco-project-version.txt`` is a simple one line file with the version of the Paco project
file format, e.g. ``2.1``. The Paco project file format version contains a major and a medium
version. The major version indicates backwards incompatable changes, while the medium
version indicates additions of new object types and fields.

The ``project.yaml`` contains gloabl information about the Paco project. It also contains
an ``paco_project_version`` field that is loaded from ``paco-project-version.txt``.

The YAML files are organized as nested key-value dictionaries. In each sub-directory,
key names map to relevant Paco schemas. An Paco schema is a set of fields that describe
the field name, type and constraints.

An example of how this hierarchy looks, in a NetworksEnvironent file, a key name ``network:``
must have attributes that match the Network schema. Within the Network schema there must be
an attribute named ``vpc:`` which contains attributes for the VPC schema. That looks like this:

.. code-block:: yaml

    network:
        enabled: true
        region: us-west-2
        availability_zones: 2
        vpc:
            enable_dns_hostnames: true
            enable_dns_support: true
            enable_internet_gateway: true

Some key names map to Paco schemas that are containers. For containers, every key must contain
a set of key/value pairs that map to the Paco schema that container is for.
Every Paco schema in a container has a special ``name`` attribute, this attribute is derived
from the key name used in the container.

For example, the NetworkEnvironments has a key name ``environments:`` that maps
to an Environments container object. Environments containers contain Environment objects.

.. code-block:: yaml

    environments:
        dev:
            title: Development
        staging:
            title: Staging
        prod:
            title: Production

When this is parsed, there would be three Environment objects:

.. code-block:: text

    Environment:
        name: dev
        title: Development
    Environment:
        name: staging
        title: Staging
    Environment:
        name: prod
        title: Production

.. Attention:: Key naming warning: As the key names you choose will be used in the names of
    resources provisioned in AWS, they should be as short and simple as possible. If you wanted
    rename keys, you need to first delete all of your AWS resources under their old key names,
    then recreate them with their new name. Try to give everything short, reasonable names.

Key names have the following restrictions:

  * Can contain only letters, numbers, hyphens and underscores.

  * First character must be a letter.

  * Cannot end with a hyphen or contain two consecutive hyphens.

Certain AWS resources have additional naming limitations, namely S3 bucket names
can not contain uppercase letters and certain resources have a name length of 64 characters.

The ``title`` field is available in almost all Paco schemas. This is intended to be
a human readable name. This field can contain any character except newline.
The ``title`` field can also be added as a Tag to resources, so any characters
beyond 255 characters would be truncated.

.. _YAML: https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html

Enabled/Disabled
================

Many Paco schemas have an ``enabled:`` field. If an Environment, Application or Resource field
have ``enabled: True``, that indicates it should be provisioned. If ``enabled: False`` is set,
then the resource won't be provisioned.

To determine if a resource should be provisioned or not, if **any** field higher in the tree
is set to ``enabled: False`` the resource will not be provisioned.

In the following example, the network is enabled by default. The dev environment is enabled,
and there are two applications, but only one of them is enabled. The production environment
has two applications enabled, but they will not be provisioned as enabled is off for the
entire environment.

.. code-block:: yaml

    network:
        enabled: true

    environments:
        dev:
            enabled: true
            default:
                applications:
                    my-paco-example:
                        enabled: false
                    reporting-app:
                        enabled: true
        prod:
            enabled: false
            default:
                applications:
                    my-paco-example:
                        enabled: true
                    reporting-app:
                        enabled: true

.. Attention:: Note that currently, this field is only applied during the ``paco provision`` command.
    If you want delete an environment or application, you need to do so explicitly with the ``paco delete`` command.

References and Substitutions
============================

Some values can be special references. These will allow you to reference other values in
your Paco Configuration.

 * ``paco.ref netenv``: NetworkEnvironment reference

 * ``paco.ref resource``: Resource reference

 * ``paco.ref accounts``: Account reference

 * ``paco.ref function``: Function reference

 * ``paco.ref service``: Service reference

References are in the format:

``type.ref name.seperated.by.dots``

In addition, the ``paco.sub`` string indicates a substitution.

paco.ref netenv
---------------

To refer to a value in a NetworkEnvironment use an ``paco.ref netenv`` reference. For example:

``paco.ref netenv.my-paco-example.network.vpc.security_groups.app.lb``

After ``paco.ref netenv`` should be a part which matches the filename of a file (without the .yaml or .yml extension)
in the NetworkEnvironments directory.

The next part will start to walk down the YAML tree in the specified file. You can
either refer to a part in the ``applications`` or ``network`` section.

Keep walking down the tree, until you reach the name of a field. This final part is sometimes
a field name that you don't supply in your configuration, and is instead can be generated
by the Paco Engine after it has provisioned the resource in AWS.

An example where a ``paco.ref netenv`` refers to the id of a SecurityGroup:

.. code-block:: yaml

    network:
        vpc:
            security_groups:
                app:
                    lb:
                        egress
                    webapp:
                        ingress:
                            - from_port: 80
                            name: HTTP
                            protocol: tcp
                            source_security_group: paco.ref netenv.my-paco-example.network.vpc.security_groups.app.lb

You can refer to an S3 Bucket and it will return the ARN of the bucket:

.. code-block:: yaml

    artifacts_bucket: paco.ref netenv.my-paco-example.applications.app.groups.cicd.resources.cpbd_s3

SSL Certificates can be added to a load balancer. If a reference needs to look-up the name or id of an AWS
Resource, it needs to first be provisioned, the ``order`` field controls the order in which resources
are created. In the example below, the ACM cert is first created, then an Applicatin Load Balancer is provisioned
and configured with the ACM cert:

.. code-block:: yaml

    applications:
        app:
            groups:
                site:
                    cert:
                        type: ACM
                        order: 1
                        domain_name: example.com
                        subject_alternative_names:
                        - '*.example.com'
                    alb:
                        type: LBApplication
                        order: 2
                        listeners:
                            - port: 80
                                protocol: HTTP
                                redirect:
                                port: 443
                                protocol: HTTPS
                            - port: 443
                                protocol: HTTPS
                                ssl_certificates:
                                - paco.ref netenv.my-paco-example.applications.app.groups.site.resources.cert


paco.ref resource
-----------------

To refer to a global resource created in the Resources directory, use an ``paco.ref resource``. For example:

``paco.ref resource.route53.example``

After the ``paco.ref resource`` the next part should matche the filename of a file
(without the .yaml or .yml extension)  in the Resources directory.
Subsequent parts will walk down the YAML in that file.

In the example below, the ``hosted_zone`` of a Route53 record is looked up.

.. code-block:: yaml

    # netenv/my-paco-example.yaml

    applications:
        app:
            groups:
                site:
                    alb:
                        dns:
                        - hosted_zone: paco.ref resource.route53.example

    # resource/Route53.yaml

    hosted_zones:
    example:
        enabled: true
        domain_name: example.com
        account: paco.ref accounts.prod


paco.ref accounts
-----------------

To refer to an AWS Account in the Accounts directory, use ``paco.ref``. For example:

``paco.ref accounts.dev``

Account references should matches the filename of a file (without the .yaml or .yml extension)
in the Accounts directory.

These are useful to override in the environments section in a NetworkEnvironment file
to control which account an environment should be deployed to:

.. code-block:: yaml

    environments:
        dev:
            network:
                aws_account: paco.ref accounts.dev

paco.ref function
-----------------

A reference to an imperatively generated value that is dynamically resolved at runtime. For example:

``paco.ref function.mypackage.mymodule.myfunction``

This must be an importable Python function that accepts three arguements: reference, project, account_ctx.

This function must return a value that is compatable with the fields data type (e.g. typically a string).

There is one built-in function:

``paco.ref function.aws.ec2.ami.latest.amazon-linux-2``

Currently can only look-up AMI IDs. Can be either ``aws.ec2.ami.latest.amazon-linux-2``
or ``aws.ec2.ami.latest.amazon-linux``.

.. code-block:: yaml

    web:
        type: ASG
        instance_ami: paco.ref function.aws.ec2.ami.latest.amazon-linux-2

paco.ref service
----------------

To refer to a service created in the Services directory, use an ``paco.ref service``. For example:

``paco.ref service.notification.<account>.<region>.applications.notification.groups.lambda.resources.snstopic``

Services are plug-ins that extend Paco with additional functionality. For example, custom notification, patching, back-ups
and cost optimization services could be developed and installed into an Paco application to provide custom business
functionality.

paco.sub
--------

Can be used to look-up a value and substitute the results into a templated string.
