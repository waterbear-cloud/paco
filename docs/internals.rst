.. _internals:

Paco Internals
===============

Discussions on what Paco does under the hood.

The .paco-work directory
------------------------

Paco creates a directory in every Paco project named ``.paco-work``. This directory
contains several sub-directories that Paco will read/write to while it's working.

``.paco-work/applied``:
    Paco starts a provision command by showing you a diff of the configuration from the last provision.
    It does this by keeping a cache of YAML configuration files after it applies them here.

    Paco will also show you changes between previously CloudFormation stacks and Parameters and the
    new ones it wants to apply. Paco creates a cache of stacks here when after they have been applied.

    If this directory gets out-of-sync then Paco can skip updates to Resrouces believing that they
    haven't changed. You can remedy this by using the ``-n`` ``--nocahce`` flag with the Paco CLI.

    Alternatively, you could run ``rm -rf .paco-work/applied/cloudformation`` to remove this cache
    and Paco will simply run slower on it's next run as it fetches state from CloudFormation.

``.paco-work/build``:
    This is a scratch space that Paco can use. For example, the EC2LaunchManager creates a
    zip file bundles of files used to configure EC2 instances. These zip files are created in here.

``.paco-work/outputs``:
    Stack outputs are cached here. These outputs are organized according to the structure of the Paco
    model as opposed to the structure of the CloudFormation stacks.
