Changelog for aim
=================

1.0.1 (unreleased)
------------------

### Added

- Added --nocache to cli to force updates to stacks.

- CLI reports human readable validation errors from AIM project configuration files

- "aim ftest" command added to run functional tests on the "aim init project"
  templates. This command will be expanded in the future so you can test your
  own aim projects.

- Resources/S3.yaml is now functional: eg. aim validate S3


1.0.0 (2019-07-06)
------------------

### Added

- Initial documentation with AIM project site at https://aim.waterbear.cloud/en/latest/

- Added init command with ability to create starting templates for AIM projects
  with the cookiecutter project under the hood.

- Added redirect to Listner rules in the ALB

### Changed

- Document and refactor AIM CLI.

- Moved yaml.py to aim.core

- Refactored S3 Controller

- Ported Route53 config to the model

- Ported CodeCommit config to the model

- Refactored S3 to use Application StackGroup

- CPBD artifacts s3 bucket now uses S3 Resource in NetEnv yaml instead

- Converted the ALB's listener and listener rules to dicts from lists

### Removed

- Removed deprecated configuration


0.6.0 (2019-06-21)
-----------------------

- Document and clean-up AIM CLI

- Validate and Provision functioning after cleanup


0.5.0 (2019-06-21)
------------------

- First open source release
