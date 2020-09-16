.. _extend:

Extending Paco with Services
============================

Paco has an add-on framework called **Services**.

Every installed Paco Service is loaded during initialization and is capable of
extending or changing Paco in any way, before the rest of normal initialization and actions happen.

The `paco.services` module provides a set of APIs to help Services do common
add-on tasks consistently and without conflicts.

Overview of Paco Initialization
-------------------------------

Every time Paco loads a Paco Project, it will first read all the YAML files in a Paco Project and create
an object model of that Paco Project. Every Paco Service has a chance to declare it's own specific
YAML configuration file in a Paco Project at ``services/<my-service-name>.yaml``. This is a purely
optional step for any Paco Service that wants to define it's own customizable YAML.

Next Paco will initialize some Paco Controllers. Controllers are high level APIs for managing Paco
commands that apply to the paco model. For example, the Route53 Controller will generate StackTemplates
from the Route53 paco model during initialization, and during a provision command, the controller
will create/update those stacks to AWS.

Controller initialization happens in a specific order:

  1. Controllers for Global Resources declared in the ``resource/`` directory are initialized first. This allows other
     Controllers to depend upon global resources being already initialized and available.

  2. Service Controllers declared in the ``service/`` are initialized second. They are initialized in an ``initialization_order``
     that each Service add-on may declare. Controllers with a low `initialization_order` have a chance to
     make changes that effect the initialization of later Controllers.

  3. The Controller specific to the current PACO_SCOPE is initialized last. For example, if the command
     `paco provision netenv.mynet.staging` was run, the scope is a NetworkEnvironment and a
     NetworkEnvironment Controller will be initialized.


Creating a minimal Paco Service
-------------------------------

The minimal requirments to create a Paco Service is to create a Python project and a ``service/<my-name>.yaml`` file
in a Paco Project that will use that service.

Let's take a look at what's involved in a Paco Service that prints "Hello World" during Paco initialization.

First, create a ``mypacoaddon`` directory for your Paco Service and make it a Python project by creating a ``setup.py`` file.
This file describes the layout of your Python project.

.. code-block:: python

    from setuptools import setup

    setup(
        name='helloworld-service',
        version='0.1.dev',
        install_requires=['paco-cloud'],
        entry_points = {
            'paco.services': [
                'helloworld = mypacoaddon.helloworld',
            ],
        },
        packages=['mypacoaddon',],
        package_dir={'': 'src'},
    )

The ``setup.py`` is described in `standard Python packaging`_. The important parts to note are that the
Paco Service should declare it depends on the ``paco-cloud`` Python project in the ``install_requires`` field.

The ``entry_points`` field will register ``paco.services`` entry points. You can register more than one Paco
Service here.

Each Paco Service declared is in the format ``<service-name> = <python-dotted-name-of-module>``.

The Paco Service service name must be unique within the Services your Paco has installed.

A Python module declared to contain a Paco Service needs to have two functions in it:

.. code-block:: python

    def instantiate_model(config, project, monitor_config, read_file_path):
        "Return a Python object with configuration for this Service"
        pass

    def instantiate_class(paco_ctx, config):
        "Return a Controller for this Service"
        pass


The ``instantiate_model`` function is called during model loading. It could return any empty Python
object, it could use ``paco.mdoel`` laoding APIs to read and validate custom YAML configuration or
do any other kind of custom configuration initialization and loading you need.

The ``instantiate_class`` function is called during Controller initialization and it needs to return
a Paco Controller specific to your Paco Service.

In your ``mypacoaddon`` project, create the following directory structure:

.. code-block:: text

    mypacoaddon/
      setup.py
      src/
        mypacoaddon/
          __init__.py
          helloworld.py

Then put this code into ``helloworld.py``:

.. code-block:: python

    """
    Hello World Paco Service
    """

    # Hook into the Paco Service loading

    initialization_order = 1000

    def instantiate_model(config, project, monitor_config, read_file_path):
        return HelloWorldModel()

    def instantiate_class(paco_ctx, config):
        "Return a HelloWorld controller for the HelloWorld Service"
        return HelloWorldController(config)

    # Model and Controller

    class HelloWorldModel:
        speak = "Hello World!"

    class HelloWorldController:

        def __init__(self, config):
            self.config = config

        def init(self, command=None, model_obj=None):
            print(self.config.speak)

Next you can install your Python project from the ``mypacoaddon`` directory with the
command ``pip install -e .``. This will register your Paco Service entry point in your
for your Python environment.

By default, if you run Paco commands on a Paco Project, if there is no file for your Paco Service
in the ``services/`` directory, then Paco will not load that Paco Service. This is by design
to allow you to install a Paco Service but only use it in Paco Projects that you explicitly declare.

In a Paco Project, create a file ``services/helloworld.yaml``. This can be an empty file or valid
YAML that will be read into a Python data structure and passed as the argument ``config`` to your
``instantiate_model`` function.

Now run any Paco command and you should see "Hello World!" printed on your terminal.

.. code-block:: bash

    $ paco validate netenv.mynet.staging
    Loading Paco project: /Users/example/my-paco-project
    Hello World!
    ...


Paco Service APIs
-----------------

service module implementaion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every Paco Service Python module **must** implement ``instantiate_model`` and ``instantiate_class`` functions:

.. code-block:: python

    def instantiate_model(config, project, monitor_config, read_file_path):
        pass

    def instantiate_class(paco_ctx, config):
        pass

The module can declare an optional ``initialization_order`` attribute:

.. code-block:: python

    initialization_order = 1000

If this order is not declared the initialization order of multiple Services will be randomly assigned
starting from 1000. If your Service needs to be initialized before other "normal" Services, it should
declare a number below 1000 in this attribute.

The module can declare an optional ``override_alarm_actions`` function:

.. code-block:: python

    def override_alarm_actions(snstopics, alarm):
        "Override normal alarm actions with the SNS Topic ARN for the custom Notification Lambda"
        return ["paco.ref service.notify...snstopic.arn"]

This function must return a List of paco.refs to SNS Topic ARNs. This will change Paco's CloudWatch
AlarmActions to your own custom list of SNS Topic ARNs. This can be used to send AlarmActions to
notify your own custom Lambda function instead of sending Alarm messages directly to the
SNS Topics that Alarms are subscribed too.

Paco Service APIs
^^^^^^^^^^^^^^^^^

The ``paco.extend`` module contains convenience APIs to make it easier to extend Paco consistently.
These APIs are typically invoked from your custom Paco Service Controllers.

The ``paco.extend.extend_cw_alarm_description_hook`` allows you add extra metadata to the
CloudWatch AlarmDescription field. This takes a function that is expected to call the
``add_to_alarm_description`` method and supply a dict of extra metadata.

.. code-block:: python

    def my_service_alarm_description_function(cw_alarm):
        extra_metadata = {'SlackChannel': 'http://my-slack-webhook.url'}
        cw_alarm.add_to_alarm_description(extra_metadata)

    paco.service.extend_cw_alarm_description_hook(my_service_alarm_description_function)



.. _standard Python packaging: https://packaging.python.org/tutorials/packaging-projects/
