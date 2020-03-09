Changelog for Paco
==================

6.1.0 (2020-03-09)
------------------

### Added

- New Private PyPI Starter Project.


6.0.1 (2020-03-08)
------------------

### Fixed

- Removed ``{{['.gitignore']|join}}`` cookiecutter file that crept back in that breaks install on
  filesystems that do not allow the | character.

- ALB rule.target group fix was merged into wrong place in the code.

- Restored StackOrders which wasn't being respected after refactor.

6.0.0 (2020-03-06)
------------------

### Breaking

- Consolidated the Paco work directories into a single ``.paco-work`` directory.
  Documented them on a new Paco Internals doc page. To migrate an existing Paco project
  to this new structure:

      cd <my-paco-project>
      git mv aimdata .paco-work
      git mv Outputs .paco-work/outputs
      git mv build .paco-work/build

  Those commands assume you are using git to manage a Paco project. If you are, also update your ``.gitignore``
  file to ignore .paco-work/build.

- The IAM Roles for BackupVault had inconsistently named CloudFormation stacks ("BackupVaults--Backup").
  A new IAM Role will be created in a new stack. The old stack will remain but it can be safely deleted.

  There will be a stack UPDATE to the BackupVaults. Each AWS::Backup::BackupSelection resource will
  have "Selection: " prefixed on the SelectionName, this will replace the old BackupSelection resources
  with new ones using the new Role. The AWS CloudFormation documentation states that a BackupSelection's
  SelectionName is a display name only, but this is incorrect.

- Removed the ``Resource/NotificationGroups.yaml`` filename alias. This file is now only loaded using
  the filename ``resoruce/snstopics.yaml``.

- EventsRule type target field changed from a list of Targets to a list of IEventTarget objects. This allows
  the ability to specify other information with the target such as the input_json field. Old was:

    type: EventsRule
    targets:
      - paco.ref some.ref

  The new format is:

    type: EventsRule
    targets:
      - target: paco.ref some.ref
        input_json: '{"cat":"dog"}'

### Added

- DeploymentPipeline can now use GitHub.Source as a source.

- Integrated the Parliment library to lint/validate the IAM Policies used for all Roles.
  https://github.com/duo-labs/parliament


5.1.1 (2020-02-19)
------------------

### Fixed

- Fixed security_group field for ElasticsearchDomain.


5.1.0 (2020-02-19)
------------------

### Added

- Ability to enforce that you need to be on a specific git branch to change a specific environment.
  Documentation for this was added to a new Paco Workflows page.

## Fixed

- Added proper names to Elasticsearch output refs.

5.0.1 (2020-02-17)
------------------

### Added

- ASG has new field desirec_capacity_ignore_changes that can be set.

### Fixed

- If ignore_changes was set for a CloudFormation Parameter it was breaking the Confirm Changes CLI.


5.0.0 (2020-02-17)
------------------

### Breaking

- Breaking: Lamdba now creates it's Log Group in the CloudFormation. It also allows for additional
  app-specific Log Groups. Lambda's execution role now restricts Log Group permissions to just the
  Log Groups it needs.

  If you have existing Lambdas, you will need to delete the Log Group and then re-provision the
  Lambda (and ensrue the Lambda isn't invoked after the Log Group is deleted or it will re-create it).
  This will allow the Lambda Log Groups to be under CloudFormation state.

### Added

- ServiceLinkedRoles for IAM. New IAM controller method ``add_service_linked_role`` which can be
  used to add a SerivceLinkedRole.

- ElasticsearchDomain resource.

- Ability for a template Parameter to ignore_changes. If this is True then the Parameter will not
  be changed during stack updates.

- ASG has a new instance_ami_ignore_changes field which will mark the InstanceAMI Parameter with
  ignore_changes.

- EventRules can be in the State=ENABLED or State=DISABLED set by the ``enabled_state`` boolean field.

### Changed

- EventsRules are named with a random suffix instead of a prefix. This makes it easier to
  use the --name-prefix option for list-rules in the AWS CLI and API.

- New CFTemplate.create_output created that makes creating and registering outputs easier.

4.0.0 (2020-02-05)
------------------

### Breaking

- Breaking: This will change the secrets for any secret that was created by ``generate_secret_string``.
  Completed full implementation of ``secrets.generate_secret_string``, every property in the CloudFormation
  resource is represented so that expressing defaults won't trigger new secret created.

### Added

- New ``warn_template_changes`` method for CFTemplate. This is a hook that allows
  templates to print a warning about potential unintended side-effects of the change.
  The SecretsManager template is the first to implement this warning hook.

### Docs

- Improved Getting Started documentation and "paco init project" CLI messages.

3.5.5 (2020-01-29)
------------------

### Fixed

- EFS resource can be in a disabled state.

- EIP resource will be removed when disabled.

- ALB resource properly removes ALB when disabled.

- ASG resource is properly disabled.


3.5.4 (2020-01-21)
------------------

### Added

- CloudFrontCacheBehaviours have min_ttl and max_ttl field support.

### Fixed

- CodeCommit repositories policy refactor to work around maximum 10 policy per IAM User limit.


3.5.3 (2020-01-16)
------------------

### Added

- Warn if generated CloudFormation template reaches 80% or greater of the maximum stack size of 51,200 bytes.

### Fixed

- AWS Backup was missing group name in templates. Now creates a stack for every BackupVault.

3.5.2 (2020-01-08)
------------------

### Fixed

- `paco init project` creates the `.gitignore` after cookiecutter runs. This avoids having a | character
  in the filename, which certain filsystems do not like.

- Fixed bug where resource/s3.yaml buckets were being run twice on validate and provision.

3.5.1 (2020-01-06)
------------------

### Fixed

- Fix starter projects: check for aws_second_region in ``paco init project``.

### Changed

- Starter Projects paco-project-version brought up to 6.3.

3.5.0 (2020-01-03)
------------------

### Added

 - Route 53 Health Checks support ip_address field.

 - Duplicate key errors in the YAML have a proper error message.

 - Docs have multi-account set-up page.

### Changed

- NetworkEnvironment networks can now be (almost) empty. This can be used for serverless environments
  that do not need a network. The ``network:`` configuration still needs to exist, but only has to contain
  the ``aws_account`` and ``enabled`` fields.

- Removed Parameter.ending format for cfn-init parameters and Dashboard variables.
  Instead simply including the ending in the paco.ref

- cfn-init launch bundle sends cfn-signal after cfn-init finishes.

- `paco provision account` provisions the accounts.

### Fixed

- If entire VPC is disabled for an ASG, the disabled ASG is removed.

- DeploymentPipeline can be enabled/disabled without throwing errors.

- Throw error if an account is missing an account_id.

- Throw error if .credentials file is missing before asking for MFA.

- cfn-init uses proper base path for Amazon Linux which has cfn-init pre-installed in /opt/aws.

- log group expire_events_after_days can be left blank for log_set and log_group without throwing error.

- Route 53 Record Set stack for an ALB is provisioned in the same account that Route53 is in.

- DeploymentPipeline no longer hard-codes to a 'data' account for CodeCommit principle,
  and instead uses the actual account(s) that CodeCommit repo's use.

- Alarm notifications that do not come from plug-in work again.

- Clean-up for wordpress-single-tier starting template.

- Create ~/.aws/cli/cache directory if it doesn't already exist.

- LogAlarms were incorrectly getting a Resource Dimension added to them.


3.4.1 (2019-12-04)
------------------

### Fixed

- Include paco.cookiecutters data files in paco-cloud distribution.


3.4.0 (2019-12-03)
------------------

### Added

- New CloudWatch Dashboard resource.

- Route53 Health Check supports domain_name or load_balancer fields.

### Fixed

- include paco.stack_grps package!

- Route53 Health Check alarm gets Namespace again.

### Changed

- Final AIM --> Paco rename: Log metric namespace changed from `AIM/` to `Paco/`

3.3.1 (2019-11-29)
------------------

### Fixed

- Placeholder in the wordpress-single-tier template for AMI Id.

- Assorted fixes created by the AIM to paco rename.

- ALB AWS::ElasticLoadBalancingV2::ListenerCertificate are restored.

- Fixed Zone reference lookups in Route53 stack group.

### Docs

- Overview page works on mobile.

3.3.0 (2019-11-28)
------------------

### Changed

- Changed dependency from `aim.models` to `paco.models`

- Renamed all things `aim` to `paco`.


3.2.0 (2019-11-27)
------------------

- AIM has been renamed to Paco: Prescribed automation for cloud orchestration.
  The CLI is now `paco` with a PACO_HOME environment variables. The
  PyPI package is at `paco-cloud`.

- AWS Backup service is supported by paco. Create BackupVaults with BackupPlans and BackupSelections.


3.1.0 (2019-11-06)
------------------

### Added

- DBParameterGroups template.

- LogGroups template adds MetricFilters if present.

- Respect the `global_role_names` field for the IAM Role RoleName.

- Alarms can be provisioned at the Application level without being specific to a Resoure context.

- Route53HealthChecks can be provisioned. These are global resources with the application region
  suffixed to the health check name. The CloudFormation template and CLoudWatch Alarm are provisioned
  in us-east-1, as that is where the metrics are hard-coded to by AWS.

- Lambda template will grant Lambda permissions to an Events Rule in the same application that
  references it as a Target.

- New Events Rule template.

- Added change_protected support to Cloudfront, IAM Managed Policies, and IAM Role templates.

- Added a CodeBuild IAM Permission for IAM Users

- Added the EIP Application Resource and a support 'eip' field to the ASG resource for associating an EIP with a single instance ASG.

- Added `cftemplate_iam_user_delegates_2019_10_02` legacy flag to make user delegate role stack names consistent with others.

- Added support to allow ASG to launch into a single subnet.

- Added ResourceGroupid to the ElastiCache Application Resource

- Added caching to instance AMI ID function.ref lookups.

- Added swap, wget installer, and get tag value helper functions to the EC2 Launch manager and moved all of its scripts to a separate file that is copied from S3 and executed.

- Added VPC Associations to the VPC private hosted zone.

- Added VpcConfig to the Lambda function cftemplate.

- Added `secrets_manager` to Network Environments.

- Added support for !Ref and !Sub to yaml.py

- Added a 'Nested StackGroup' feature to StackGroups. This allows us to nest a StackGroup in the place of a Stack within a StackGroup. This was needed to allow Route53 RecordSets to be created in order, but to allow a different Stack name from the current StackGroup being populated.

- Added the Route53RecordSet CFTemplate and ctl_route53.add_record_set() method.

- Added the EBS Application Resources.
  Added `ebs_volume_mounts` to IASG to mount volumes to single instance groups.
  Added the EBS Launch Bundle to implement `ebs_volume_mounts`

### Changed

- Fixed bug where if a AssumeRolePolicyDocument has both `service` and `aws` fields for the Principal,
  the `aws` field was ignored.

- Improvements to the CLI. Verbose flag is now respected.
  Yes/no questions are consistent and can be answered with 'y', 'n', 'yes' or 'no'.
  Clean-up to formatting. Only prompt for provision changes when running the provision
  sub-command.

- ALB Alarms now provision with an `LBApplication` suffix and match the Resoruce.type field.

- Made IAM Users default password more complex to satisfy password contraints.

- Updated some of the cookiecutter templates for `aim init project`.

- Ported the Route53 CFTemplate to troposphere and separated zones into their own stacks.
  Added the legacy flag `route53_hosted_zone_2019_10_12` for this change.

- Cleaned up expired token handling in Stack() by consolidating duplicate code into a single method.

- Refactor of EC2 Launch Manager user data script management. Common functions are now stored in S3 to reduce user data size.

- Modifed LogGroup names to include the Network Environment name.

- Refactored how Route53 RecordSets are being created. The previous design created RecordSets right in the resource's template. The new design uses the Route53 Controller to create RecordSets in their own stack using an account global name . The reason is that CloudFormation does not allow you to modify RecordSets unless you are modifying the stack that created it. This made it impossible to move DNS between resources without first deleting the record and recreating it. With a global controller, we can simple rewrite the RecordSets to new values.
  Added `route53_record_set_2019_10_16` legacy flag to deal with pre-existing RecordSets

- Moved app_engine.get_stack_from_ref to StackGroup

### Fixed

- Fixed a couple of AWS token expiry retries from failing.

- AWS session caching was not properly caching.

- NotificationGroups controller was not setting up refs correctly, nor resolving them correctly.

3.0.0 (2019-09-27)
------------------

### Added

- New directory `aimdata` is created within an AIM Project by paco. This is used to record state
  of AIM provisioning. CloudFormation templates used to create stacks in AWS are cached as well
  as the last copy of the AIM Project YAML files. These files are used to speed up subsequent
  runs and more importantly can show you what is changed between AIM runs to make it easier to
  review new changes before they are actaully made to AWS.

- CLI: Display a diff of changes from last AIM run and new run in the AIM Project YAML configuration.
  The `-d`, `--disable-validation` flag can be used to

- CLI: Display changes and ask for verification before updating CF templates. This can be disabled
  with the `-y` flag.

- CLI: Offer to delete a stack in a CREATE FAILED state so that a new stack can be provisioned in it's place.

- AWS credentials can now be set to live for up to 12 hours. You can set the .credentials field to
 `mfa_session_expiry_secs: 43200 # 12 hours` to enable this. The default is still one hour.

- Resources with the `change_protected` flag set to true will not have their CloudFormation stacks
  updated.

- API Gateway REST API can now have models, methods and stages. It supports Lambda integration
  with either 'AWS_PROXY' via an assumed Role or 'AWS' via a Lambda Permission.

- S3Bucket has NotificationConfiguration for Lambdas. Lambda will detect if an S3Bucket within the
  same application notifies the lambda and will automatically add a Lambda permission to allow S3 to
  invoke the lambda.

- Lambda AWS::SNS::Subscription resources now have a Region property.

- CloudWatchAlarms template has a `notification_region` class attribute that can be set if
  notificationgroup subscriptions need to go to a single region.

- CloudFront has Origin ID support.

- EFS Resource support.

### Changed

- Breaking! CF Template names have been refactored so that they are more user friendly when listed in the
  AWS Console. This requires deletion and reprovisioning of AWS resources. Templates now have new
  consistent ways to create their names, so this should be the last time this change happens.

- CLI: References to NetworkEnvironments now use consistent `paco.ref` syntax, e.g.
  `aim provision netenv <ne>.<env>.<region>`

- All stacks are created with Termination Protection set.

- CF template base class `paco.cftemplates.cftemplates.CFTemplate` has new methods for creating consistent
  AWS names: `create_resource_name()`, `create_resoruce_name_join()`, `create_cfn_logical_id()`,
  and `create_cfn_logical_id_join()`.

- Console messages reworked to show relevant information in columns.

- CF template base class method `gen_parameter` renamed to `create_cfn_parameter`.

- S3 controller now relies on the bucket name to come from the S3Bucket model object.

- Lambda code.s3_bucket field can now be an paco.ref or a plain bucket name.

- You can provision without specifying the region and it will include all regions in an env.

- NotificationGroups are loaded from project['resource']['notificationgroups']

### Fixed

- CloudTrail generates it's own CloudWatch LogGroup if needed. Outputs for CloudTrail and CloudWatch LogGroup.

- APIGateway, SNSTopics and Lambda now respect the `enabled` field.

2.0.0 (2019-08-26)
------------------

### Fixed

- snstopic output ref and lambda alarm ref fixes.

- Added IAM Users feature for creating IAM Users and configuring console access
  assigning permissions, and access keys.

### Added

- Moved aim reference generation into the Model. Model objects now have .paco_ref and
  .paco_ref_parts properties which contain their paco.ref reference.

- Added StackOutputsManger(). This now creates and maintains $AIM_HOME/ResourceMap.yaml
  which will include a complete list of all stack outputs that are referenced using the
  yaml dictionary path of the resource.

- ALB Outputs includes TargetGroup Fullname.

- Minimal APIGatewayRestApi template.

- Added external_resource support to the ACM

- Added ReadOnly support to the Administrator IAMUserPermission

### Changed

- Automated CloudFront Parameter lists for things like security group and target arn lists.

- Consolidated CFTemplates and Stack's and other Stack cleanups.

- CloudWatch Alarms multi-Dimension Alarms now expect an paco.ref. CloudWatch Alarms are now Troposphere.


1.4.0 (2019-08-21)
------------------

### Added

- CloudTrail resource adds basic CloudTrail provisioning.

- LogGroups are created for all groups that the CloudWatch Agent will require.
  Uses the new Logging schema in paco.models.

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
   Every ref now starts with ``paco.ref ``.

 - Created ``paco.utils`` to clean up PacoContext object.

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

- Initial documentation with AIM project site at https://paco.waterbear.cloud/en/latest/

- Added init command with ability to create starting templates for AIM projects
  with the cookiecutter project under the hood.

- Added redirect to Listner rules in the ALB

### Changed

- Document and refactor AIM CLI.

- Moved yaml.py to paco.core

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
