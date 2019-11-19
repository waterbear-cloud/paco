.. _installation:

Installation
============

AIM requires Python 3.7 or higher. As AIM requires newer release of Python, you may need to
download and install a Python_ interpreter.

Ideally you will want to install AIM in a self-contained Python environment. For some guidance
on managing Python applications check out `Python on macos`_ or `Python on Windows`_.

Install the `aim` Python package. If you are using `pip3` then you would run:

.. code-block:: bash

  $ pip3 install aim

You should now have a CLI application named `aim`.

.. code-block:: bash

  aim --help
  Usage: aim [OPTIONS] COMMAND [ARGS]...

    AIM: Application Infrastructure Manager
  ...

It is recommended for production usage to pin the version AIM that you are running with to the
project that contains the AIM configuration files.

Create an AIM Project and connect it to your AWS Accounts
---------------------------------------------------------

Go!

.. _Python: https://www.python.org/downloads/

.. _Python on macos: https://medium.com/@briantorresgil/definitive-guide-to-python-on-mac-osx-65acd8d969d0

.. _Python on Windows: https://docs.microsoft.com/en-us/windows/python/beginners
