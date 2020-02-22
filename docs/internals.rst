.. _internals:

Paco Internals
===============

Discussions on what Paco does under the hood.

Paco Architecture
-----------------

What happens when you run "paco provision" to create cloud resources?

Paco will go through the following steps:

  1. PacoContext: Command line arguments are read and parsed. An object of the class
     ``paco.config.paco_context.PacoContext`` is created which holds the command-line arguments.
     Most notably, this object will have a .home attribute, which is the path to the Paco project
     and a .project attribute which will contain that project loaded as a model.

  2. Load the project config: After the home directory is set on PacoContext, then ``paco_ctx.load_project()``
     will call ``paco.models.load_project_from_yaml`` with that directory. The paco.models loader will read all
     of the YAML files and construct Python objects. The Paco model is a tree of objects, the root node is a ``Project``
     object. Every object in the tree has a ``name`` and ``__parent__`` attribute. This allows any object to know
     it's paco.ref by walking up the parents to the root node and concatenating the names.

  3. AccountContext: Next and object of the class ``paco.config.paco_context.AccountContext`` is created for the master
     account. This will ask the user for their MFA credentials. AccountContext objects manage connections to the
     AWS accounts.

  4. Global Initialization: Paco has Controllers which are objects which initialize and orchestrate the CloudFormation templates
     and stacks. They are also responsible for connecting the model to the stacks they create, so that resources can
     find the outputs that they create. Global controllers that are widely depended upon are initialized (Route53, S3 and SNS Topics).
     Finally once everything is almost ready, Service controllers are loaded - these are Paco Add-Ons. These are last in the
     process to give them a chance to react/modify the final set-up without limit.

  5. Scope Initialization: Depending on the scope that is being provisioned (e.g. netenv.mynet.dev or resource.s3) a controller
     of the appropriate type will be looked up and initialized.

  6. Perform Cloud Action: The cloud action (validate, provision, delete) is called on the controller for the scope. It is up to the
     controller to determine how it goes about doing that action, but most controllers follow the common pattern of iterating
     through their StackGroups and calling the cloud action on each StackGroup.


Stacks and Templates
--------------------

AWS CloudFormation
^^^^^^^^^^^^^^^^^^

Paco uses the AWS CloudFormation service to provision AWS resources and maintain resource state. CloudFormation has two
core concepts: a template and a stack. A template is a CloudFormation document the declares resources. A stack is when
a template is uploaded to AWS to create those resources. A stack will always belong to a specific account and region.

Stack
^^^^^

The ``paco.stack.Stack`` class defines a Paco Stack. A Stack is connected to an account and region, and
can fetch the state of the Stack as well as create, update and delete a stack in AWS.

Every Stack expects a StackTemplate object to be set on the .stack attribute. Stacks must be created first
though and then a StackTemplate set on the Stack. This allows the StackTemplate to inspect and modify the Stack
it belongs to.

StackTemplate
^^^^^^^^^^^^^

The ``paco.cftemplates.StackTemplate`` class defines a Paco Template. A StackTemplate has a .body attribute which is
a string of CloudFormation in YAML format.

A StackTemplate requires a Stack object to be passed to the constructor. In Paco, a StackTemplate can provision
a CloudFormation template in several different locations and potentially look different in each of those
locations. The StackTemplate has access to the Stack. The StackTemplate typically sets Parameters on the Stack.
It can also change the behaviour of Stack updates, for example, certain Parameters can be set to use the
previously existing value of the Stack.

A ``troposphere.Template`` class defines a StackTemplate's .template attribute. Troposphere is an external
Python dependency of Paco. It's a great library with a complete and updated representation of CloudFormation objects.
However a StackTemplatecan provide any kind of return string, so simple Python strings can also be constructed and
set as the template body.

When Paco uses a StackTemplate it never instantiates it directly. It's a base class that resource specific templates
inherit from. These subclasses are responsible for creating the template.

StackTemplates are also passed a Paco Project object, which contains a complete Paco model.

ToDo: right now this is passed in through paco_ctx, but templates should only need access to the Project.


StackGroup
^^^^^^^^^^

Paco organizes Stacks into StackGroups. A StackGroup is a logical collection of stacks that support a single concept.
The ``paco.stack_group.stack_group.StackGroup`` class implements StackGroup which provides functionality to iterate
through the Stacks that belong to it and validate, provision and delete them.

StackGroups can contain logic. It is a common pattern to subclass a StackGroup and include additional functionality.
For example, a BackupVault needs an IAM Role to assume. The BackupVaultsStackGroup inherits from StackGroup,
but it also contains the ability to create a second Stack for that IAM Role.


The .paco-work directory
------------------------

Paco creates a directory in every Paco project named ``.paco-work``. This directory
contains several sub-directories that Paco will read/write to while it's working.

``.paco-work/applied``
    Paco starts a provision command by showing you a diff of the configuration from the last provision.
    It does this by keeping a cache of YAML configuration files after it applies them here.

    Paco will also show you changes between previously CloudFormation stacks and Parameters and the
    new ones it wants to apply. Paco creates a cache of stacks here when after they have been applied.

    If this directory gets out-of-sync then Paco can skip updates to Resrouces believing that they
    haven't changed. You can remedy this by using the ``-n`` ``--nocahce`` flag with the Paco CLI.

    Alternatively, you could run ``rm -rf .paco-work/applied/cloudformation`` to remove this cache
    and Paco will simply run slower on it's next run as it fetches state from CloudFormation.

``.paco-work/build``
    This is a scratch space that Paco can use. For example, the EC2LaunchManager creates a
    zip file bundles of files used to configure EC2 instances. These zip files are created in here.

``.paco-work/outputs``
    Stack outputs are cached here. These outputs are organized according to the structure of the Paco
    model as opposed to the structure of the CloudFormation stacks.
