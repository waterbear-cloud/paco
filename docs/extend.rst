.. _extend:

Extending Paco with Services
============================

Paco has an add-on feature called **Services**.

A **Paco Service** is a Python module that is loaded during Paco initialization and is capable of
extending or changing Paco in any way.

Services commonly provision cloud resources. For example, if you wanted to send CloudWatch Alarm
notifications to a Slack Channel, you would need to send your Alarm messages to a custom Lambda.
A Slack Service could provision this custom Lambda and customize your AlarmActions to send to
messages this Lambda.

Services that provision resources have the PACO_SCOPE ``service.<servicename>``:

.. code-block:: bash

    $ paco validate service.slack
    $ paco provision service.slack
    $ paco delete service.slack

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
Service here. Each Paco Service declared is in the format ``<service-name> = <python-dotted-name-of-module>``.

The Paco Service service name must be unique within the Services your Paco has installed.

A Python module that is a Paco Service **must** provide two functions:

.. code-block:: python

    def instantiate_model(config, project, monitor_config, read_file_path):
        "Return a Python object with configuration for this Service"
        pass

    def instantiate_class(paco_ctx, config):
        "Return a Controller for this Service"
        pass


The ``load_service_model`` function is called during model loading. It could return any empty Python
object, it could use ``paco.mdoel`` laoding APIs to read and validate custom YAML configuration or
do any other kind of custom configuration initialization and loading you need.

The ``get_service_controller`` function is called during Controller initialization and it needs to return
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

    def load_service_model(config, project, monitor_config, read_file_path):
        return HelloWorldModel()

    def get_service_controller(paco_ctx, config):
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
``load_service_model`` function.

Now run any Paco command and you should see "Hello World!" printed on your terminal.

.. code-block:: bash

    $ paco validate netenv.mynet.staging
    Loading Paco project: /Users/example/my-paco-project
    Hello World!
    ...


Service module specification
----------------------------

Every Paco Service Python module **must** have ``load_service_model`` and ``get_service_controller`` functions.
These will be called when the Service is initialized. In addition, the module may optionally provide a
``SERVICE_INITIALIZATION_ORDER`` attribute.

.. code-block:: python

    """
    Example barebones Paco Service module
    """

    # Every Paco Service *must*  provide these two functions
    def load_service_model(config, project, monitor_config, read_file_path):
        pass

    def get_service_controller(paco_ctx, config):
        pass

    # Optional attribute
    SERVICE_INITIALIZATION_ORDER = 1000


load_service_model
^^^^^^^^^^^^^^^^^^

This required function loads the configuration YAML into model objects for your Service.
However, it isn't required for a Service to have any model and this method can simply return None.

If a Paco Project doesn't have a ``service/<servicename>.yaml`` file,
then that service is not considered active in that Paco Project and will **NOT** be enabled.
The configuration file for a Service must be valid YAML or an empty file.

The ``load_service_model`` must accept four arguments:

 - ``config``: A Python dict of the Services ``service/<servicename>.yaml`` file.

 - ``project``: The root Paco Project model object.

 - ``monitor_config``: A Python dict of the YAML loaded from config in the``monitor/`` directory.

 - ``read_file_path``: The location of the file path of the Service's YAML file.

.. code-block:: python

    class Notification:
        pass

    def load_service_model(config, project, monitor_config, read_file_path):
        "Loads services/notification.yaml and returns a Notification model object"
        return Notification()

get_service_controller
^^^^^^^^^^^^^^^^^^^^^^

This required function must return a Controller object for your Service.

The ``get_service_controller`` must accept two arguments:

 - ``paco_ctx``: The PacoContext object contains the CLI arguments used to call Paco as well as other global information.

 - ``service_model``: The model object returned from this Service's ``load_service_model`` function.

A Controller **must** provide an ``init(self, command=None, model_obj=None)`` method. If the Service can be
provisioned, it must also implement ``validate(self)``, ``provision(self)`` and ``delete(self)`` methods.

.. code-block:: python

    class NotificationServiceController:
        def init(self, command=None, model_obj=None):
            pass

    def get_service_controller(paco_ctx, service_model):
        "Return a Paco controller"
        return NotificationServiceController()


SERVICE_INITIALIZATION_ORDER
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``SERVICE_INITIALIZATION_ORDER`` attribute determines the initialization order of Services.
This is useful for Services that need to do special initialization before other Services are initialized.

If this order is not declared the initialization order will be randomly assigned an order
starting from 1000.

Overview of Paco Initialization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every time Paco loads a Paco Project, it starts by determing which Services are installed and
actived. Configuration for Services is in the ``service/`` directory of a Paco Project. If a file exists
at ``service/<service-name>.yaml`` than that Service will be active in that Paco Project. If a Service
is installed with Paco but there is no service file, it is ignored.

All of the active Services are imported and given the chance to apply configuration that extends Paco.

Next, Paco reads all of the YAML files in the Paco Project and creates a Python object model from that
YAML configuration.

Then Paco will initialize the Controllers that it needs. Controllers are high level APIs that implement
 Paco commands. Controllers can govern the creating, updating and deletion of cloud resources, typically
 by acting on the contents of the Paco model.

Controller initialization happens in a specific order:

  1. Controllers for Global Resources declared in the ``resource/`` directory are initialized first. This allows other
     Controllers to depend upon global resources being already initialized and available.

  2. Service Controllers declared in the ``service/`` are initialized second. They are initialized in an ``initialization_order``
     that each Service add-on may declare. Controllers with a low `initialization_order` have a chance to
     make changes that effect the initialization of later Controllers.

  3. The Controller specific to the current PACO_SCOPE is initialized last. For example, if the command
     `paco provision netenv.mynet.staging` was run, the scope is a NetworkEnvironment and a
     NetworkEnvironment Controller will be initialized.


Paco Extend API
---------------

.. automodule:: paco.extend
    :members:


.. _standard Python packaging: https://packaging.python.org/tutorials/packaging-projects/
