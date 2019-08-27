"""
Here be utils.

.%%..%%..%%%%%%..%%%%%%..%%.......%%%%..
.%%..%%....%%......%%....%%......%%.....
.%%..%%....%%......%%....%%.......%%%%..
.%%..%%....%%......%%....%%..........%%.
..%%%%.....%%....%%%%%%..%%%%%%...%%%%..
........................................

"""

import hashlib
from aim.core.exception import StackException, AimErrorCode
from aim.models import schemas
from aim.models.locations import get_parent_by_interface
from copy import deepcopy
from functools import partial


def md5sum(filename=None, str_data=None):
    """Computes and returns an MD5 sum in hexdigest format on a file or string"""
    d = hashlib.md5()
    if filename != None:
        with open(filename, mode='rb') as f:
            for buf in iter(partial(f.read, 128), b''):
                d.update(buf)
    elif str_data != None:
        d.update(bytearray(str_data, 'utf-8'))
    else:
        raise StackException(AimErrorCode.Unknown, message="cli: md5sum: Filename or String data expected")

    return d.hexdigest()

def dict_of_dicts_merge(x, y):
    """Merge to dictionaries of dictionaries"""
    z = {}
    if hasattr(x, 'keys') == False or hasattr(y, 'keys') == False:
        return y
    overlapping_keys = x.keys() & y.keys()
    for key in overlapping_keys:
        z[key] = dict_of_dicts_merge(x[key], y[key])
    for key in x.keys() - overlapping_keys:
        z[key] = deepcopy(x[key])
    for key in y.keys() - overlapping_keys:
        z[key] = deepcopy(y[key])
    return z

def str_spc(str_data, size):
    "Add space padding to a string"
    new_str = str_data
    str_len = len(str_data)
    if str_len > size:
        message = "ERROR: cli: str_spc: string size is larger than space size: {0} > {1}".format(
            str_len, size
        )
        raise StackException(AimErrorCode.Unknown, message = message)

    for idx in range(size - str_len):
        new_str += " "
    return new_str

def normalize_name(name, replace_sep, camel_case):
    normalized_name = ""
    name_list = name.split("_")
    first = True
    for name_item in name_list:
        if camel_case == True:
            name_item = name_item.title()
        if first == False:
            normalized_name += replace_sep
        first = False
        normalized_name += name_item

    return normalized_name

def normalized_join(str_list, replace_sep, camel_case):
    new_str = replace_sep.join(str_list)
    normalized_str = ""
    first = True
    for str_item in str_list:
        str_item = normalize_name(str_item, replace_sep, camel_case)
        if first == False:
            normalized_str += replace_sep
        first = False
        normalized_str += str_item

    return normalized_str

def prefixed_name(resource, name):
    """Returns a name prefixed to be unique:
    e.g. env_name-app_name-group_name-resource_name-name"""
    # currently ony works for resources in an environment
    env_name = get_parent_by_interface(resource, schemas.IEnvironment).name
    app_name = get_parent_by_interface(resource, schemas.IApplication).name
    group_name = get_parent_by_interface(resource, schemas.IResourceGroup).name

    return '-'.join([env_name, app_name, group_name, resource.name, name])

def log_action(action, message, return_it=False):
    log_message = action+": "+message
    if return_it == False:
        print(log_message)
    else:
        return log_message
