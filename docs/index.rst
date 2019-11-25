.. _aim:

AIM: Application Infrastructure Manager
=======================================

Overview
--------

AIM is a cloud orchestration tool for AWS.

AIM uses configuration files that semantically describe your applications,
networks, environments and resources. With those it can then create complete
environments in your AWS accounts.

Applications and networks are defined as blocks of default configuration and acts
as a blueprint. You then name your applications in the environments and regions you want to
provision them in. Automatically replicate your AWS resources through development, staging
and production environments.

Get started by `installing`_ AIM and connecting it to your AWS accounts.

.. _`installing`: ./install.html

Project Status
--------------

AIM is in use for deploying production AWS environments.

However, AIM is a young project and there is much more we want to add. For example,
AIM supports about 30 AWS services (EC2, S3, RDS, Lambda, API Gateway), but there are
many services not yet supported. Supported services may also support every configuration
setting for every resource.

The AIM CLI is also loosely documented and we plan to overhaul it's UI and fully document it.

Source Code, Issues and Support
-------------------------------

`Source code for AIM`_ is on GitHub.

Send feature requests and bugs to `AIM GitHub Issues`_.

AIM is developed by Waterbear Cloud to support the `Waterbear Cloud platform`_.
Contact us for `support or consulting`_.

.. _`Waterbear Cloud platform`: https://waterbear.cloud/pricing/

.. _`Source code for AIM`: https://github.com/waterbear-cloud/aim/

.. _`AIM GitHub Issues`: https://github.com/waterbear-cloud/aim/issues

.. _`support or consulting`: https://waterbear.cloud/contact/

Quickstart Labs
---------------

.. toctree::
   :caption: Quick Start
   :maxdepth: 3

   install
   aim_init

AIM Engine CLI
--------------

.. toctree::
   :caption: Command Line Interface
   :maxdepth: 3

   cli

AIM Project Configuration
-------------------------

.. toctree::
   :caption: YAML Configuration
   :maxdepth: 3

   aim-config


Copyright, Trademarks, and Attributions
---------------------------------------

.. toctree::
   :maxdepth: 1

   copyright

Indices and tables
------------------

* :ref:`glossary`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. add glossary in a hidden toc to avoid warnings

.. toctree::
   :hidden:

   glossary
