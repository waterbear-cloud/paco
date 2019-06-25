Changelog for aim
=================

0.6.1 (unreleased)
------------------

- Document and clean-up AIM CLI.
- Removed deprecated configuration
- Added cmd_init
- Moved yaml.py to aim.core
- Refactored S3 Controller
- Ported Route53 config to the model
- Ported CodeCommit config to the model
- Refactored S3 to use Application StackGroup
- CPBD artifacts s3 bucket now uses S3 Resource in NetEnv yaml instead
- Added redirect to Listner rules in the ALB
- Converted the ALB's listener and listener rules to dicts from lists

0.6.0.dev0 (2019-06-21)
-----------------------

- Document and clean-up AIM CLI.
- Validate and Provision functioning after cleanup.


0.5.0 (2019-06-21)
------------------

- First open source release
