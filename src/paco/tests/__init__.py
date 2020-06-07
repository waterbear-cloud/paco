"""
Shared helper functions used across all test suites
"""

import os
import inspect
import pathlib


def fixtures_path():
    # find the project root directory
    # this works for pytest run from VS Code
    parts = []
    for part in os.path.abspath(os.path.dirname(__file__)).split(os.sep):
        if part == 'src':
            parts.append('fixtures')
            break
        parts.append(part)
    path = os.sep.join(parts)
    return pathlib.Path(path)

    # when run from a local test script (might need later if we run tests on commit etc)
    #path = os.path.abspath(inspect.stack()[-1][1]) # the path to the test script
    #path = path.split(os.sep)[:-2] # should be Paco project root
    #path.append('fixtures')
    #path = os.sep.join(path)

def cwd_to_fixtures():
    fpath = fixtures_path()
    os.chdir(fpath)
    return fpath
