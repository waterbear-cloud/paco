.. _installation:

Installation
============

Paco requires Python 3.6 or higher. As Paco requires newer release of Python, you may need to
download and install a Python_ interpreter.

Ideally you will want to install Paco in a self-contained Python environment. For some guidance
on managing Python applications check out `Python on macos`_ or `Python on Windows`_.

Install the `paco-cloud` Python package. If you are using `pip3` then you would run:

.. code-block:: bash

  $ pip3 install paco-cloud

You should now have a CLI application named `paco`.

.. code-block:: bash

  $ paco --help
  Usage: paco [OPTIONS] COMMAND [ARGS]...

    Paco: Prescribed Automation for Cloud Orchestration
  ...

It is recommended for production usage to pin the version Paco that you are running with to the
project that contains the Paco configuration files.


.. _Python: https://www.python.org/downloads/

.. _Python on macos: https://medium.com/@briantorresgil/definitive-guide-to-python-on-mac-osx-65acd8d969d0

.. _Python on Windows: https://docs.microsoft.com/en-us/windows/python/beginners
