.. _aim:

AIM: Application Infrastructure Manager
=======================================

Overview
--------

AIM is a cloud orchestration tool for AWS.

AIM works by using configuration files that semantically describe your
infrastructure, networks, environments and AWS resources. It can generate
CloudFormation stacks and provisions and manages those stacks in your AWS accounts.

Project Status
--------------

AIM is capable of reliably deploying robust AWS environments. However, there is a lot more we want to add to AIM!

As AIM is a young project, it's API and design may be subject to frequent changes.
It is used for real-world projects by the authors though, so backward breaking changes will attempt
to be minimized with reasonable migration paths.

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
   :maxdepth: 3

   install
   quickstart101
   quickstart102

AIM Engine CLI
--------------

.. toctree::
   :maxdepth: 3

   cli

AIM Project Configuration
-------------------------

.. toctree::
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
