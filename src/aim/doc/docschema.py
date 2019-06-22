"""
Loads aim.models.schemas and generates the doc file at ./doc/aim-config.rst
from the schema definition.
"""

import os.path
import zope.schema
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

NetworkEnvironments
-------------------

This is the show.

"""

def convert_schema_to_list_table(schema):
    output = [
"""
.. list-table::
    :widths: 15 8 6 12 30
    :header-rows: 1

    * - Field name
      - Type
      - Required?
      - Default
      - Purpose
"""]
    table_row_template = '    * - {name}\n' + \
    '      - {type}\n' + \
    '      - {required}\n' + \
    '      - {default}\n' + \
    '      - {desc}\n'
    for fieldname in sorted(zope.schema.getFields(schema).keys()):
        field = schema[fieldname]
        desc = field.title
        if field.description:
            desc = desc + ': ' + field.description
        output.append(
            table_row_template.format(
                **{
                    'name': field.getName(),
                    'type': field.__class__.__name__,
                    'required': field.required,
                    'default': field.default,
                    'desc': desc
                }
            )
        )
    return ''.join(output)


def aim_schema_generate():
    aim_doc = os.path.abspath(os.path.dirname(__file__)).split(os.sep)[:-3]
    aim_doc.append('docs')
    aim_doc.append('aim-config.rst')
    aim_config_doc = os.sep.join(aim_doc)

    with open(aim_config_doc, 'w') as f:
        f.write(
            aim_config_template.format(
                account=convert_schema_to_list_table(schemas.IAccount),
            )
        )
    print('Wrote to {}'.format(aim_config_doc))
