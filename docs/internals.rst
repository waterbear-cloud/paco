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

Paco has several Classes which it uses to model stacks and templates and control how they interact with the
AWS CloudFormation service.

Controller
^^^^^^^^^^

Controller objects initialize and set-up other objects. They create StackGroups and add Stacks to them.
The can also interact with commands from the CLI.

Controllers also inject a ``resolve_ref_obj`` into model objects, to allow model objects to use Paco
References to refer to Stack outputs.

PacoContext
^^^^^^^^^^^

The ``paco.config.paco_context.PacoContext`` class contains the arguments and options parsed from the CLI.
PacoContext also makes a call to load a Paco project into a model and make the project root node available
as a ``.project`` attribute.

The ``.get_controller(<controller-name>)`` method on PacoContext is used to fetch a controller. This ensures
that controllers are initialized once and only once.

StackGroup
^^^^^^^^^^

The ``paco.stack.stack_group.StackGroup`` class implements a StackGroup. A StackGroup is a logical collection
of stacks that support a single concept. StackGroups apply the same operation against all Stacks that it
contains and ensure that they are executed in the correct order and if necessary wait for stacks to be
created if one stack depends upon the output of another stack.

StackGroups are often subclassed and the subclass adds logic to related to that subclasses purpose.
For example, a BackupVault needs an IAM Role to assume. If you have a BackupVault Stack, you also need
an IAM Role Stack with a Role. The BackupVaultsStackGroup adds the ability to create a Stack for that IAM Role.

Stack
^^^^^

The ``paco.stack.Stack`` class defines a Paco Stack. A Stack is connected to an account and region, and
can fetch the state of the Stack as well as create, update and delete a stack in AWS.

Every Stack expects a StackTemplate object to be set on the ``.template`` attribute. This happens by calling
``add_new_stack()`` on a StackGroup. This method ensures that the Stack is created first, then the StackTemplate
is created with the stack object passed in the constructor, after the new StackTemplate object is set on the
``.template`` attribute any commands that need to happen after are applied and the stack is given orders
to the StackGroup.

Every Stack is created with a ``.resource`` attribute. This is the model object which contains the configuration
for that Stacks template. The ``IResource`` interface in the models provides an ``is_enabled()`` method, and
a ``.order`` and ``.change_protected`` attributes. This helps inform the stack if it should be modified,
and in which order, or if it shouldn't be touched at all.

Every Stack as a ``stack_ref`` property. This is normally the paco.ref for the ``.resource`` but it can also
be extended with a ``support_resource_ref_ext`` when the Stack is created. For example, an ASG resource needs
a LogGroup stack where it will log to. This is a supporting resource that isn't explicitly declared in the
configuration. The same happens for Alarms, which add a '.alarms' extension to the ref.


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

StackHooks
^^^^^^^^^^

StackHooks are programatic actions that happen before or after a create, update or delete stack operation.

Paco uses them to upload files to an S3 Bucket after it's created in the EC2LaunchManager, to delete all files
in an S3 Bucket before it's deleted, and to create and manage access keys for IAM Users.

The ``paco.stack.stack.StackHooks`` class should be created and have one or more hooks added to it, then passed to
``StackGroup.add_new_stack`` to have the hooks added to a stack, or ``Stack.add_hooks`` can be called after creation
to have hooks after stack creation. The ``Stack.add_hooks`` will merge new hooks with existing ones, so several places
can contribute StackHooks.

To create a hook, call ``StackHooks.add()`` method with:

 - ``name``: This will be displayed on the command-line interface.

 - ``stack_action``: Must be one of ``create``, ``update`` or ``delete``. The ``update`` action is called every time
   an existing stack is in scope, if the hook's ``cache_method`` returns a different cache id or the cache does not exist.
   ``update`` hooks should be designed to be idempotent and able to be re-run multiple times.

 - ``stack_timing``: Must be one of ``pre`` or ``post``.

 - ``hook_method``: A method that will perform the work of the hook. It is called with two arguments: the ``hook``
   iteslf and the ``hook_arg`` value.

 - ``cache_method``: Optional. A method that will return a cache id. If this value does not change between provisions,
   then the hook will be skipped. This only applies to hooks on the ``update`` stack action.

 - ``hook_arg``: Optional. A value which is supplied as an argument to the ``hook_method`` with it is invoked.

.. code-block:: python
    :caption: example usage of StackHooks

      stack_hooks = StackHooks()
      stack_hooks.add(
         name='UploadZipFile',
         stack_action='create',
         stack_timing='post',
         hook_method=self.upload_bundle_stack_hook,
         cache_method=self.stack_hook_cache_id,
         hook_arg=bundle
      )


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
