## AIM

AIM: Application Infrastructure Manager is an all-in-one AWS infrastructure orchestration tool.
It has a command-line interface for managing complete, working environments based on declarative,
semantic YAML files.

AIM has the following benefits for managing your Infrastructure as Code projects:


 - All-in-one: work at the highest levels of abstraction possible. You don't need learn how
   to cobble together a collection of tools. Replace several different languages with a single
   directory of YAML files.

 - Declarative configuration: declarative configuration gives your infrastructure
   repeatability and predictability.

 - DRY configuration: Environments are described with hiearchical YAML structures that override
   base network and application defaults. You can see at a glance exactly which configuration is
   different between your staging and production environments. You can override configuration for
   a whole environment, or for multi-region environments, have per-region overrides.

 - Time saving features: Want to alert when instances are in swap? Simply declare a swap metric
   and swap alarm for your application and AIM will ensure an agent is configured and installed
   on your instances, as well as auto-generating an IAM Policy to allow your instances to report
   metrics to CloudWatch.

 - Intelligent references remove cumbersome glue code: AIM configuration can refer to other configuration
   objects. Networks refer to just a human-readable name of the account they are provisioned in.
   When a Lambda declares a subscription to an SNS Topic, AIM can auto-generate an IAM Polciy to allow that.

 - Validate all the things: AIM configuration has a hierarchical structure with an explicit schema. Add the
   ability for configuration to reference other objects and you can validate that you have sane configuration
   before you even try to deploy anything to AWS.

 - Multi-region, multi-account: you can provision an application to multiple regions,
   but also to multiple accounts. You can even quickly provision new child accounts
   that will have delegate role access from an admin role in your parent account.

 - Metadata everywhere: When problems happen with configuration or provisioning, or when an alarm
   fires, every resource knows exactly how it fits into the system. Alarm and error messages have
   full structured information about their account, region, environment and application.

# Resources

 - [Documentation](https://aim.waterbear.cloud)

 - [PyPI Package](https://pypi.org/project/aim/)

# Credits

AIM is developed by [Waterbear Cloud](https://waterbear.cloud) and used to support their Waterbear Cloud platform.

