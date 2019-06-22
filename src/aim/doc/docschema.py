"""
Loads aim.models.schemas and generates the doc file at ./doc/aim-config.rst
from the schema definition.
"""

import os.path
from aim.models import schemas

aim_config_template = """
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

{account}
"""

def aim_schema_generate():
    aim_doc = os.path.abspath(os.path.dirname(__file__)).split(os.sep)[:-3]
    aim_doc.append('docs')
    aim_doc.append('aim-config.rst')
    aim_config_doc = os.sep.join(aim_doc)

    with open(aim_config_doc, 'w') as f:
        f.write(
            aim_config_template.format(account=schemas.IAccount)
        )
    print('Wrote to {}'.format(aim_config_doc))
