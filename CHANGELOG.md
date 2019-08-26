Changelog for aim
=================

1.4.1 (unreleased)
------------------

### Fixed

- snstopic output ref and lambda alarm ref fixes.

- Added IAM Users feature for creating IAM Users and configuring console access
  assigning permissions, and access keys.

### Added

- Moved aim reference generation into the Model. Model objects now have .aim_ref and
  .aim_ref_parts properties which contain their aim.ref reference.

- Added StackOutputsManger(). This now creates and maintains $AIM_HOME/ResourceMap.yaml
  which will include a complete list of all stack outputs that are referenced using the
  yaml dictionary path of the resource.

### Changed

- Automated CloudFront Parameter lists for things like security group and target arn lists.

- Consolidated CFTemplates and Stack's and other Stack cleanups.


1.4.0 (2019-08-21)
------------------

### Added

- CloudTrail resource adds basic CloudTrail provisioning.

- LogGroups are created for all groups that the CloudWatch Agent will require.
  Uses the new Logging schema in aim.models.

- Added CloudFront application Resource

- Added VPC Peering application resource.

- Automated the glue of passing outputs from a stack to the parameter of another stack.

1.3.1 (2019-08-07)
------------------

### Fixed

- Python packaging, also include version.txt.


1.3.0 (2019-08-07)
------------------

### Changed

- CloudWatchAlarms now check for namespace and dimesions fields, that
  can be used to override the default of one primary dimension and the resource_name.

### Fixed

- Python dist did not include README.md and CHANGELOG.md

1.2.0 (2019-08-06)
------------------

### Added

- Deleting resources can leave dangling CloudFormation templates in your
  account. Controllers for NetworkEnvironments now keep track of templates
  they've provisioned and warn you about unused templates.

- NotificationGroups can be provisioned as SNS Topics and subscriptions.
  Use ``aim provision notificationgroups``.

- CloudWatch Alarm descriptions are JSON with metadata about the environment,
  region, application, resource group and resource that the alarm is for.

- CloudWatch Alarms will not notify the SNS Topics that they are subscribed to.

- Rewrote commands with consistent way of passing arguments to controllers.
  Controllers args can now be all lower case.

- Added Account initialization to 'aim init project'.

### Changed

 - AIM references have a new format! It's simpler and more consistent.
   Every ref now starts with ``aim.ref ``.

 - Created ``aim.utils`` to clean up AimContext object.

1.1.0 (2019-07-24)
------------------

### Added

- Logging functionality added to monitoring. Logs will be ingested by a configured
  CloudWatch Agent and sent to a CloudWatch Log Group.

- Added --nocache to cli to force updates to stacks.

- CLI reports human readable validation errors from AIM project configuration files

- "aim ftest" command added to run functional tests on the "aim init project"
  templates. This command will be expanded in the future so you can test your
  own aim projects.

- Resources/S3.yaml is now functional: eg. aim validate S3

- Added Region to cftemplates so we can do inline replace of <account> and <region>.

- Added LambdaPermission and CWEventRule cftemplates.

- Added CloudWatchController and LambdaController.

### Fixed

 - cookiecutter generated .credentials file was not in git repo as, the cookiecutter
   .gitignore file was causing it to be ignored.


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
