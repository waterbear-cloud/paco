"""
Cache the model after it has been parsed from YAML to speed up subsequent runs
"""

import paco.models
import os
import os.path
import pathlib
import pickle
from paco.models import load_project_from_yaml


def get_max_mtime(path, exclude):
    """
    Get the most recently modified time in a directory
    """
    mtimes = []
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude]
        mtimes.append(os.path.getmtime(root))
        for file in files:
            mtimes.append(os.path.getmtime(root + os.sep + file))
    return max(mtimes)

def load_cached_project(project_path):
    """
    Creates or updates the paco model cache if any files have been modified since
    the last cache time
    """
    last_mtime = get_max_mtime(project_path, exclude=('build'))
    cache_dir = os.path.join(project_path, "build")
    mtime_cache_file = os.path.join(cache_dir, "cache_last_mtime.txt")
    model_cache_file = os.path.join(cache_dir, "cache_model.pickle")
    pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # no last modified time cache file, so load project and cache it
    if not os.path.isfile(mtime_cache_file):
        with open(mtime_cache_file, 'w') as cache_file:
            cache_file.write(str(last_mtime))
        project = load_project_from_yaml(project_path)
        with open(model_cache_file, 'wb') as model_cache_file:
            pickle.dump(project, model_cache_file)

    # already cached, either update the cache or use it
    else:
        with open(mtime_cache_file) as cache_file:
            cache_mtime = cache_file.readlines()
        cache_mtime = float(cache_mtime[0])
        # if you CTRL-C right after running paco, you can create the mtime file but not the pickle cache
        if cache_mtime < last_mtime or not os.path.isfile(model_cache_file):
            # cache is stale
            project = load_project_from_yaml(project_path)
            with open(model_cache_file, 'wb') as model_cache_file:
                pickle.dump(project, model_cache_file)
            with open(mtime_cache_file, 'w') as cache_file:
                cache_file.write(str(last_mtime))
        else:
            # good to go - return the cache
            with open(model_cache_file, 'rb') as model_cache_file:
                project = pickle.load(model_cache_file)

    return project
