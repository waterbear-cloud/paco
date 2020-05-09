import shutil
import os


def patched_make_zipfile(base_name, base_dir, verbose=0, dry_run=0, logger=None):
    """Modified from the original to include symlinks, and also to filter
    out files which don't make sense in Python zip files, e.g. __pycache__

    Create a zip file from all the files under 'base_dir'.

    The output zip file will be named 'base_name' + ".zip".  Returns the
    name of the output zip file.
    """
    import zipfile  # late import for breaking circular dependency

    zip_filename = base_name
    archive_dir = os.path.dirname(base_name)

    if archive_dir and not os.path.exists(archive_dir):
        if logger is not None:
            logger.info("creating %s", archive_dir)
        if not dry_run:
            os.makedirs(archive_dir)

    if logger is not None:
        logger.info("creating '%s' and adding '%s' to it",
                    zip_filename, base_dir)
    if not dry_run:
        with zipfile.ZipFile(zip_filename, "w",
                             compression=zipfile.ZIP_DEFLATED) as zf:
            path = os.path.normpath(base_dir)
            if path != os.curdir:
                zf.write(path, path)
                if logger is not None:
                    logger.info("adding '%s'", path)
            # Here be a monkey patch: added followlinks=True
            for dirpath, dirnames, filenames in os.walk(base_dir, followlinks=True):
                for name in sorted(dirnames):
                    if name == '__pycache__':
                        continue
                    path = os.path.normpath(os.path.join(dirpath, name))
                    zf.write(path, path)
                    if logger is not None:
                        logger.info("adding '%s'", path)
                for name in filenames:
                    if name.endswith('.pyc'):
                        continue
                    path = os.path.normpath(os.path.join(dirpath, name))
                    if os.path.isfile(path):
                        zf.write(path, path)
                        if logger is not None:
                            logger.info("adding '%s'", path)

    return zip_filename

