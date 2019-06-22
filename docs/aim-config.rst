
.. _aim-config:

AIM Configuration
=================

AIM configuration is a directory of files that make up an AIM project.
These files can describe networks, environments, applications, services,
accounts, and monitoring and logging configuration.


Accounts
--------

AWS account information is kept in the ``Accounts`` directory.
Each file in this directory will define one AWS account, the filename
will be the name of the account, with a .yml or .yaml extension.

<InterfaceClass aim.models.schemas.IAccount>
