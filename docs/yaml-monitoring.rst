

Monitoring
==========

The ``monitor`` directory can contain two files: ``monitor/alarmsets.yaml`` and ``monitor/logging.yaml``. These files
contain CloudWatch Alarm and CloudWatch Agent Log Source configuration. These alarms and log sources
are grouped into named sets, and sets of alarms and logs can be applied to resources.

Currently only CloudWatch is supported, but it is intended in the future to support other monitoring and logging services
in the future.


AlarmSets
----------


Alarm Sets are defined in the file ``monitor/alarmsets.yaml``.

AlarmSets are named to match a Paco Resource type, then a unique AlarmSet name.


.. code-block:: yaml
    :caption: Structure of an alarmets.yaml file

    # AutoScalingGroup alarms
    ASG:
        launch-health:
            GroupPendingInstances-Low:
                # alarm config here ...
            GroupPendingInstances-Critical:
                # alarm config here ...

    # Application LoadBalancer alarms
    LBApplication:
        instance-health:
            HealthyHostCount-Critical:
                # alarm config here ...
        response-latency:
            TargetResponseTimeP95-Low:
                # alarm config here ...
            HTTPCode_Target_4XX_Count-Low:
                # alarm config here ...


The base `Alarm`_ schema contains fields to add additional metadata to alarms. For CloudWatchAlarms, this
metadata set in the AlarmDescription field as JSON:

Alarms can have different contexts, which increases the number of metadata that is populated in the AlarmDescription field:

 * Global context. Only has base context. e.g. a CloudTrail log alarm.

 * NetworkEnvironmnet context. Base and NetworkEnvironment context. e.g. a VPC flow log alarm.

 * Application context alarm. Base, NetworkEnvironment and Application contexts. e,g, an external HTTP health check alarm

 * Resource context alarm. Base, NetworkEnvironment, Application and Resource contexts. e.g. an AutoScalingGroup CPU alarm

.. code-block:: yaml

    Base context for all alarms
    ----------------------------

    "project_name": Project name
    "project_title": Project title
    "account_name": Account name
    "alarm_name": Alarm name
    "classification": Classification
    "severity": Severity
    "topic_arns": SNS Topic ARN subscriptions
    "description": Description (only if supplied)
    "runbook_url": Runbook URL (only if supplied)

    NetworkEnvironment context alarms
    ---------------------------------

    "netenv_name": NetworkEnvironment name
    "netenv_title": NetworkEnvironment title
    "env_name": Environment name
    "env_title": Environment title
    "envreg_name": EnvironmentRegion name
    "envreg_title": EnvironmentRegion title

    Application context alarms
    --------------------------

    "app_name": Application name
    "app_title": Application title

     Resource context alarms
     -----------------------

    "resource_group_name": Resource Group name
    "resource_group_title": Resource Group title
    "resource_name": Resource name
    "resource_title": Resource title

Alarms can be set in the ``monitoring:`` field for `Application`_ and `Resource`_ objects. The name of
each `AlarmSet` should be listed in the ``alarm_sets:`` field. It is possible to override the individual fields of
an Alarm in a netenv file.

.. code-block:: yaml
    :caption: Examples of adding AlarmSets to Environmnets

    environments:
      prod:
        title: "Production"
        default:
          enabled: true
          applications:
            app:
              monitoring:
                enabled: true
                alarm_sets:
                  special-app-alarms:
              groups:
                site:
                  resources:
                    alb:
                      monitoring:
                        enabled: true
                        alarm_sets:
                          core:
                          performance:
                            # Override the SlowTargetResponseTime Alarm threshold field
                            SlowTargetResponseTime:
                              threshold: 2.0

Stylistically, ``monitoring`` and ``alarm_sets`` can be specified in the base ``applications:`` section in a netenv file,
and set to ``enabled: false``. Then only the production environment can override the enabled field to true. This makes it
easy to enable a dev or test environment if you want to test alarms before using in a production environment.

Alternatively, you may wish to only specify the monitoring in the ``environments:`` section of your netenv file only
for production, and keep the base ``applications:`` configuration shorter.


Alarm notifications tell alarms which SNS Topics to notify. Alarm notifications are set with the ``notifications:`` field
at the `Application`_, `Resource`_, `AlarmSet`_ and `Alarm`_ level.

.. code-block:: yaml
    :caption: Examples of Alarm notifications

    applications:
      app:
        enabled: true
        # Application level notifications
        notifications:
          ops_team:
            groups:
            - cloud_ops
        groups:
          site:
            resources:
              web:
                monitoring:
                  # Resource level notifications
                  notifications:
                    web_team:
                      groups:
                      - web
                  alarm_sets:
                    instance-health-cwagent:
                      notifications:
                        # AlarmSet notifications
                        alarmsetnotif:
                          groups:
                          - misterteam
                      SwapPercent-Low:
                        # Alarm level notifications
                        notifications:
                          singlealarm:
                            groups:
                            - oneguygetsthis

Notifications can be filtered for specific ``severity`` and ``classification`` levels. This allows you to direct
critical severity to one group and low severity to another, or to send only performance classification alarms to one
group and security classification alarms to another.

.. code-block:: yaml
    :caption: Examples of severity and classification filters

    notifications:
      severe_security:
        groups:
        - security_group
        severity: 'critical'
        classification: 'security'

Note that although you can configure multiple SNS Topics to subscribe to a single alarm, CloudWatch has a maximum
limit of five SNS Topics that a given alarm may be subscribed to.

It is also possible to write a Paco add-on that overrides the default CloudWatch notifications and instead notifies
a single SNS Topic. This is intended to allow you to write an add-on that directs all alarms through a single Lambda
(regardless or account or region) which is then responsible for delivering or taking action on alarms.

Currently Global and NetworkEnvironment alarms are only supported through Paco add-ons.


.. code-block:: yaml
    :caption: Example alarmsets.yaml for Application, ALB, ASG, RDSMySQL and LogAlarms

    App:
      special-app-alarms:
        CustomMetric:
          description: "Custom metric has been triggered."
          classification: health
          severity: low
          metric_name: "custom_metric"
          period: 86400 # 1 day
          evaluation_periods: 1
          threshold: 1
          comparison_operator: LessThanThreshold
          statistic: Average
          treat_missing_data: breaching
          namespace: 'CustomMetric'

    LBApplication:
      core:
        HealthyHostCount-Critical:
          classification: health
          severity: critical
          description: "Alert if fewer than X number of backend hosts are passing health checks"
          metric_name: "HealthyHostCount"
          dimensions:
            - name: LoadBalancer
              value: paco.ref netenv.wa.applications.ap.groups.site.resources.alb.fullname
            - name: TargetGroup
              value: paco.ref netenv.wa.applications.ap.groups.site.resources.alb.target_groups.ap.fullname
          period: 60
          evaluation_periods: 5
          statistic: Minimum
          threshold: 1
          comparison_operator: LessThanThreshold
          treat_missing_data: breaching
      performance:
        SlowTargetResponseTime:
          severity: low
          classification: performance
          description: "Average HTTP response time is unusually slow"
          metric_name: "TargetResponseTime"
          period: 60
          evaluation_periods: 5
          statistic: Average
          threshold: 1.5
          comparison_operator: GreaterThanOrEqualToThreshold
          treat_missing_data: missing
          dimensions:
            - name: LoadBalancer
              value: paco.ref netenv.wa.applications.ap.groups.site.resources.alb.fullname
            - name: TargetGroup
              value: paco.ref netenv.wa.applications.ap.groups.site.resources.alb.target_groups.ap.fullname
        HTTPCode4XXCount:
          classification: performance
          severity: low
          description: "Large number of 4xx HTTP error codes"
          metric_name: "HTTPCode_Target_4XX_Count"
          period: 60
          evaluation_periods: 5
          statistic: Sum
          threshold: 100
          comparison_operator: GreaterThanOrEqualToThreshold
          treat_missing_data: notBreaching
        HTTPCode5XXCount:
          classification: performance
          severity: low
          description: "Large number of 5xx HTTP error codes"
          metric_name: "HTTPCode_Target_5XX_Count"
          period: 60
          evaluation_periods: 5
          statistic: Sum
          threshold: 100
          comparison_operator: GreaterThanOrEqualToThreshold
          treat_missing_data: notBreaching

    ASG:
      core:
        StatusCheck:
          classification: health
          severity: critical
          metric_name: "StatusCheckFailed"
          namespace: AWS/EC2
          period: 60
          evaluation_periods: 5
          statistic: Maximum
          threshold: 0
          comparison_operator: GreaterThanThreshold
          treat_missing_data: breaching
        CPUTotal:
          classification: performance
          severity: critical
          metric_name: "CPUUtilization"
          namespace: AWS/EC2
          period: 60
          evaluation_periods: 30
          threshold: 90
          statistic: Average
          treat_missing_data: breaching
          comparison_operator: GreaterThanThreshold
      cwagent:
        SwapPercentLow:
          classification: performance
          severity: low
          metric_name: "swap_used_percent"
          namespace: "CWAgent"
          period: 60
          evaluation_periods: 5
          statistic: Maximum
          threshold: 80
          comparison_operator: GreaterThanThreshold
          treat_missing_data: breaching
        DiskSpaceLow:
          classification: health
          severity: low
          metric_name: "disk_used_percent"
          namespace: "CWAgent"
          period: 300
          evaluation_periods: 1
          statistic: Minimum
          threshold: 60
          comparison_operator: GreaterThanThreshold
          treat_missing_data: breaching
        DiskSpaceCritical:
          classification: health
          severity: low
          metric_name: "disk_used_percent"
          namespace: "CWAgent"
          period: 300
          evaluation_periods: 1
          statistic: Minimum
          threshold: 80
          comparison_operator: GreaterThanThreshold
          treat_missing_data: breaching

      # CloudWatch Log Alarms
      log-alarms:
        CfnInitError:
          type: LogAlarm
          description: "CloudFormation Init Errors"
          classification: health
          severity: critical
          log_set_name: 'cloud'
          log_group_name: 'cfn_init'
          metric_name: "CfnInitErrorMetric"
          period: 300
          evaluation_periods: 1
          threshold: 1.0
          treat_missing_data: notBreaching
          comparison_operator: GreaterThanOrEqualToThreshold
          statistic: Sum
        CodeDeployError:
          type: LogAlarm
          description: "CodeDeploy Errors"
          classification: health
          severity: critical
          log_set_name: 'cloud'
          log_group_name: 'codedeploy'
          metric_name: "CodeDeployErrorMetric"
          period: 300
          evaluation_periods: 1
          threshold: 1.0
          treat_missing_data: notBreaching
          comparison_operator: GreaterThanOrEqualToThreshold
          statistic: Sum
        WsgiError:
          type: LogAlarm
          description: "HTTP WSGI Errors"
          classification: health
          severity: critical
          log_set_name: 'ap'
          log_group_name: 'httpd_error'
          metric_name: "WsgiErrorMetric"
          period: 300
          evaluation_periods: 1
          threshold: 1.0
          treat_missing_data: notBreaching
          comparison_operator: GreaterThanOrEqualToThreshold
          statistic: Sum
        HighHTTPTraffic:
          type: LogAlarm
          description: "High number of http access logs"
          classification: performance
          severity: low
          log_set_name: 'ap'
          log_group_name: 'httpd_access'
          metric_name: "HttpdLogCountMetric"
          period: 300
          evaluation_periods: 1
          threshold: 1000
          treat_missing_data: ignore
          comparison_operator: GreaterThanOrEqualToThreshold
          statistic: Sum

    RDSMysql:
      basic-database:
        CPUTotal-Low:
          classification: performance
          severity: low
          metric_name: "CPUUtilization"
          namespace: AWS/RDS
          period: 300
          evaluation_periods: 6
          threshold: 90
          comparison_operator: GreaterThanOrEqualToThreshold
          statistic: Average
          treat_missing_data: breaching

        FreeableMemoryAlarm:
          classification: performance
          severity: low
          metric_name: "FreeableMemory"
          namespace: AWS/RDS
          period: 300
          evaluation_periods: 1
          threshold: 100000000
          comparison_operator: LessThanOrEqualToThreshold
          statistic: Minimum
          treat_missing_data: breaching

        FreeStorageSpaceAlarm:
          classification: performance
          severity: low
          metric_name: "FreeStorageSpace"
          namespace: AWS/RDS
          period: 300
          evaluation_periods: 1
          threshold: 5000000000
          comparison_operator: LessThanOrEqualToThreshold
          statistic: Minimum
          treat_missing_data: breaching


    

.. _AlarmSets:

.. list-table:: :guilabel:`AlarmSets` |bars| Container<`AlarmSet`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


AlarmSet
^^^^^^^^^


A container of Alarm objects.
    

.. _AlarmSet:

.. list-table:: :guilabel:`AlarmSet`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - resource_type
      - String
      - Resource type
      - Must be a valid AWS resource type
      - 

*Base Schemas* `Named`_, `Notifiable`_, `Title`_


Alarm
^^^^^^


A Paco Alarm.

This is a base schema which defines metadata useful to categorize an alarm.
    

.. _Alarm:

.. list-table:: :guilabel:`Alarm`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - classification
      - String |star|
      - Classification
      - Must be one of: 'performance', 'security' or 'health'
      - unset
    * - description
      - String
      - Description
      - 
      - 
    * - notification_groups
      - List<String>
      - List of notificationn groups the alarm is subscribed to.
      - 
      - 
    * - runbook_url
      - String
      - Runbook URL
      - 
      - 
    * - severity
      - String
      - Severity
      - Must be one of: 'low', 'critical'
      - low

*Base Schemas* `Deployable`_, `Named`_, `Notifiable`_, `Title`_


Dimension
^^^^^^^^^^


A dimension of a metric
    

.. _Dimension:

.. list-table:: :guilabel:`Dimension`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Dimension name
      - 
      - 
    * - value
      - PacoReference|String
      - String or a Paco Reference to resource output.
      - Paco Reference to `Interface`_. String Ok.
      - 



AlarmNotifications
^^^^^^^^^^^^^^^^^^^


Container for `AlarmNotification`_ objects.
    

.. _AlarmNotifications:

.. list-table:: :guilabel:`AlarmNotifications` |bars| Container<`AlarmNotification`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


AlarmNotification
^^^^^^^^^^^^^^^^^^


Alarm Notification
    

.. _AlarmNotification:

.. list-table:: :guilabel:`AlarmNotification`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - classification
      - String
      - Classification filter
      - Must be one of: 'performance', 'security', 'health' or ''.
      - 
    * - groups
      - List<String> |star|
      - List of groups
      - 
      - 
    * - severity
      - String
      - Severity filter
      - Must be one of: 'low', 'critical'
      - 

*Base Schemas* `Named`_, `Title`_


SimpleCloudWatchAlarm
^^^^^^^^^^^^^^^^^^^^^^


A Simple CloudWatch Alarm
    

.. _SimpleCloudWatchAlarm:

.. list-table:: :guilabel:`SimpleCloudWatchAlarm`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - actions_enabled
      - Boolean
      - Actions Enabled
      - 
      - 
    * - alarm_description
      - String
      - Alarm Description
      - Valid JSON document with Paco fields.
      - 
    * - comparison_operator
      - String
      - Comparison operator
      - Must be one of: 'GreaterThanThreshold','GreaterThanOrEqualToThreshold', 'LessThanThreshold', 'LessThanOrEqualToThreshold'
      - 
    * - dimensions
      - List<Dimension_>
      - Dimensions
      - 
      - 
    * - evaluation_periods
      - Int
      - Evaluation periods
      - 
      - 
    * - metric_name
      - String |star|
      - Metric name
      - 
      - 
    * - namespace
      - String
      - Namespace
      - 
      - 
    * - period
      - Int
      - Period in seconds
      - 
      - 
    * - statistic
      - String
      - Statistic
      - 
      - 
    * - threshold
      - Float
      - Threshold
      - 
      - 



MetricFilters
^^^^^^^^^^^^^^


Container for `Metric`Filter` objects.
    

.. _MetricFilters:

.. list-table:: :guilabel:`MetricFilters` |bars| Container<`MetricFilter`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


MetricFilter
^^^^^^^^^^^^^


    Metric filter
    

.. _MetricFilter:

.. list-table:: :guilabel:`MetricFilter`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - filter_pattern
      - String
      - Filter pattern
      - 
      - 
    * - metric_transformations
      - List<MetricTransformation_>
      - Metric transformations
      - 
      - 

*Base Schemas* `Named`_, `Title`_


MetricTransformation
^^^^^^^^^^^^^^^^^^^^^


Metric Transformation
    

.. _MetricTransformation:

.. list-table:: :guilabel:`MetricTransformation`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - default_value
      - Float
      - The value to emit when a filter pattern does not match a log event.
      - 
      - 
    * - metric_name
      - String |star|
      - The name of the CloudWatch Metric.
      - 
      - 
    * - metric_namespace
      - String
      - The namespace of the CloudWatch metric. If not set, the namespace used will be 'AIM/{log-group-name}'.
      - 
      - 
    * - metric_value
      - String |star|
      - The value that is published to the CloudWatch metric.
      - 
      - 



Metric
^^^^^^^


A set of metrics to collect and an optional collection interval:

- name: disk
    measurements:
    - free
    collection_interval: 900
    

.. _Metric:

.. list-table:: :guilabel:`Metric`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - collection_interval
      - Int
      - Collection interval
      - 
      - 
    * - drop_device
      - Boolean
      - Drops the device name from disk metrics
      - 
      - True
    * - measurements
      - List<String>
      - Measurements
      - 
      - 
    * - name
      - String
      - Metric(s) group name
      - 
      - 
    * - resources
      - List<String>
      - List of resources for this metric
      - 
      - 




CloudWatchLogging
------------------


CloudWatch Logging configuration
    

.. _CloudWatchLogging:

.. list-table:: :guilabel:`CloudWatchLogging`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - log_sets
      - Container<CloudWatchLogSets_>
      - A CloudWatchLogSets container
      - 
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


CloudWatchLogRetention
^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudWatchLogRetention:

.. list-table:: :guilabel:`CloudWatchLogRetention`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - expire_events_after_days
      - String
      - Expire Events After. Retention period of logs in this group
      - 
      - 



CloudWatchLogSets
^^^^^^^^^^^^^^^^^^


Container for `CloudWatchLogSet`_ objects.
    

.. _CloudWatchLogSets:

.. list-table:: :guilabel:`CloudWatchLogSets` |bars| Container<`CloudWatchLogSet`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


CloudWatchLogSet
^^^^^^^^^^^^^^^^^


A set of Log Group objects
    

.. _CloudWatchLogSet:

.. list-table:: :guilabel:`CloudWatchLogSet`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - log_groups
      - Container<CloudWatchLogGroups_>
      - A CloudWatchLogGroups container
      - 
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


CloudWatchLogGroups
^^^^^^^^^^^^^^^^^^^^


Container for `CloudWatchLogGroup`_ objects.
    

.. _CloudWatchLogGroups:

.. list-table:: :guilabel:`CloudWatchLogGroups` |bars| Container<`CloudWatchLogGroup`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


CloudWatchLogGroup
^^^^^^^^^^^^^^^^^^^


A CloudWatchLogGroup is responsible for retention, access control and metric filters
    

.. _CloudWatchLogGroup:

.. list-table:: :guilabel:`CloudWatchLogGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - log_group_name
      - String
      - Log group name. Can override the LogGroup name used from the name field.
      - 
      - 
    * - metric_filters
      - Container<MetricFilters_>
      - Metric Filters
      - 
      - 
    * - sources
      - Container<CloudWatchLogSources_>
      - A CloudWatchLogSources container
      - 
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


CloudWatchLogSources
^^^^^^^^^^^^^^^^^^^^^


A container of `CloudWatchLogSource`_ objects.
    

.. _CloudWatchLogSources:

.. list-table:: :guilabel:`CloudWatchLogSources` |bars| Container<`CloudWatchLogSource`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_


CloudWatchLogSource
^^^^^^^^^^^^^^^^^^^^


Log source for a CloudWatch agent.
    

.. _CloudWatchLogSource:

.. list-table:: :guilabel:`CloudWatchLogSource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - encoding
      - String
      - Encoding
      - 
      - utf-8
    * - log_stream_name
      - String |star|
      - Log stream name
      - CloudWatch Log Stream name
      - 
    * - multi_line_start_pattern
      - String
      - Multi-line start pattern
      - 
      - 
    * - path
      - String |star|
      - Path
      - Must be a valid filesystem path expression. Wildcard * is allowed.
      - 
    * - timestamp_format
      - String
      - Timestamp format
      - 
      - 
    * - timezone
      - String
      - Timezone
      - Must be one of: 'Local', 'UTC'
      - Local

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_



HealthChecks
-------------

Container for `Route53HealthCheck`_ objects.

.. _HealthChecks:

.. list-table:: :guilabel:`HealthChecks` |bars| Container<`Route53HealthCheck`_>
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * -
      -
      -
      -
      -

*Base Schemas* `Named`_, `Title`_

.. _application: yaml-netenv.html#application

.. _route53healthcheck: yaml-app-resources.html#route53healthcheck



.. _Named: yaml-base.html#Named

.. _Name: yaml-base.html#Name

.. _Title: yaml-base.html#Title

.. _Deployable: yaml-base.html#Deployable

.. _SecurityGroupRule: yaml-base.html#SecurityGroupRule

.. _ApplicationEngine: yaml-base.html#ApplicationEngine

.. _DnsEnablable: yaml-base.html#ApplicationEngine

.. _monitorable: yaml-base.html#monitorable

.. _notifiable: yaml-base.html#notifiable

.. _resource: yaml-base.html#resource

.. _type: yaml-base.html#type

.. _interface: yaml-base.html#interface

.. _regioncontainer: yaml-base.html#regioncontainer

.. _function: yaml-base.html#function



.. _account: yaml-accounts.html#account

