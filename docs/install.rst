.. _installation:

How to install Paco
===================

Install Python
--------------

Paco is written in Python and requires Python 3.6 or greater.

Paco currently works with macos and Linux. **Windows support is not yet available.**

Get the latest version of Python from python.org_ or with your operating systems
package manager. Some helpful links for specific operating systems:

- `Python on macos`_

- `Python on Ubuntu 16.04 LTS`_

Verify your Python version on your shell by typing ``python`` (or sometimes ``python3``):

.. code-block:: bash

  Python 3.x.y
  [GCC 4.x] on linux
  Type "help", "copyright", "credits" or "license" for more information.
  >>>


Install Paco
------------

Paco can be installed with any Python package manager. Pip_ is the most popular and
often comes with your Python installer. The Paco project is named ``paco-cloud`` on PyPI,
to install it simply type:

.. code-block:: bash

  $ pip install paco-cloud

You should now have the ``paco`` application installed:

.. code-block:: bash

  $ paco --help
  Usage: paco [OPTIONS] COMMAND [ARGS]...

    Paco: Prescribed Automation for Cloud Orchestration
  ...

.. _python.org: https://www.python.org/downloads/

.. _Python on macos: https://medium.com/@briantorresgil/definitive-guide-to-python-on-mac-osx-65acd8d969d0

.. _Python on Ubuntu 16.04 LTS: http://ubuntuhandbook.org/index.php/2017/07/install-python-3-6-1-in-ubuntu-16-04-lts/

.. _Pip: https://pip.pypa.io/
