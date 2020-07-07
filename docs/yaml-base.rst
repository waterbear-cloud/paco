
.. _yaml-base:

*****************
YAML File Schemas
*****************

Base Schemas
============

Base Schemas are never configured by themselves, they are schemas that are inherited by other schemas.

Interface
---------

A generic placeholder for any schema.


Named
------


A name given to a cloud resource. Names identify resources and changing them
can break configuration.


.. _Named:

.. list-table:: :guilabel:`Named`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Name
      - 
      - 

*Base Schemas* `Title`_


Title
------


A title is a human-readable name. It can be as long as you want, and can change without
breaking any configuration.
    

.. _Title:

.. list-table:: :guilabel:`Title`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - title
      - String
      - Title
      - 
      - 



Name
-----


A name that can be changed or duplicated with other similar cloud resources without breaking anything.
    

.. _Name:

.. list-table:: :guilabel:`Name`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String
      - Name
      - 
      - 



Resource
---------

Configuration for a cloud resource.
Resources may represent a single physical resource in the cloud,
or several closely related resources.
    

.. _Resource:

.. list-table:: :guilabel:`Resource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - change_protected
      - Boolean
      - Boolean indicating whether this resource can be modified or not.
      - 
      - False
    * - order
      - Int
      - The order in which the resource will be deployed
      - 
      - 0

*Base Schemas* `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


Deployable
-----------


Indicates if this configuration tree should be enabled or not.
    

.. _Deployable:

.. list-table:: :guilabel:`Deployable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - enabled
      - Boolean
      - Enabled
      - Could be deployed to AWS
      - False



Enablable
----------


Indicate if this configuration should be enabled.
    

.. _Enablable:

.. list-table:: :guilabel:`Enablable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - enabled
      - Boolean
      - Enabled
      - 
      - True



Type
-----



.. _Type:

.. list-table:: :guilabel:`Type`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - type
      - String
      - Type of Resources
      - A valid AWS Resource type: ASG, LBApplication, etc.
      - 



DNSEnablable
-------------

Provides a parent with an inheritable DNS enabled field

.. _DNSEnablable:

.. list-table:: :guilabel:`DNSEnablable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dns_enabled
      - Boolean
      - Boolean indicating whether DNS record sets will be created.
      - 
      - True



Monitorable
------------


A monitorable resource
    

.. _Monitorable:

.. list-table:: :guilabel:`Monitorable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - monitoring
      - Object<MonitorConfig_>
      - 
      - 
      - 



MonitorConfig
--------------


A set of metrics and a default collection interval
    

.. _MonitorConfig:

.. list-table:: :guilabel:`MonitorConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alarm_sets
      - Container<AlarmSets_>
      - Sets of Alarm Sets
      - 
      - 
    * - asg_metrics
      - List<String>
      - ASG Metrics
      - Must be one of: 'GroupMinSize', 'GroupMaxSize', 'GroupDesiredCapacity', 'GroupInServiceInstances', 'GroupPendingInstances', 'GroupStandbyInstances', 'GroupTerminatingInstances', 'GroupTotalInstances'
      - 
    * - collection_interval
      - Int
      - Collection interval
      - 
      - 60
    * - health_checks
      - Container<HealthChecks_>
      - Set of Health Checks
      - 
      - 
    * - log_sets
      - Container<CloudWatchLogSets_>
      - Sets of Log Sets
      - 
      - 
    * - metrics
      - List<Metric_>
      - Metrics
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Notifiable`_, `Title`_


RegionContainer
----------------

Container for objects which do not belong to a specific Environment.

.. _RegionContainer:

.. list-table:: :guilabel:`RegionContainer`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alarm_sets
      - Container<AlarmSets_>
      - Alarm Sets
      - 
      - 

*Base Schemas* `Named`_, `Title`_


AccountRegions
---------------

An Account and one or more Regions

.. _AccountRegions:

.. list-table:: :guilabel:`AccountRegions`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference |star|
      - AWS Account
      - Paco Reference to `Account`_.
      - 
    * - regions
      - List<String> |star|
      - Regions
      - 
      - 



Notifiable
-----------


A notifiable object
    

.. _Notifiable:

.. list-table:: :guilabel:`Notifiable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - notifications
      - Container<AlarmNotifications_>
      - Alarm Notifications
      - 
      - 



SecurityGroupRule
------------------



.. _SecurityGroupRule:

.. list-table:: :guilabel:`SecurityGroupRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cidr_ip
      - String
      - CIDR IP
      - A valid CIDR v4 block or an empty string
      - 
    * - cidr_ip_v6
      - String
      - CIDR IP v6
      - A valid CIDR v6 block or an empty string
      - 
    * - description
      - String
      - Description
      - Max 255 characters. Allowed characters are a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=;{}!$*.
      - 
    * - from_port
      - Int
      - From port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1
    * - port
      - Int
      - Port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1
    * - protocol
      - String
      - IP Protocol
      - The IP protocol name (tcp, udp, icmp, icmpv6) or number.
      - 
    * - to_port
      - Int
      - To port
      - A value of -1 indicates all ICMP/ICMPv6 types. If you specify all ICMP/ICMPv6 types, you must specify all codes.
      - -1

*Base Schemas* `Name`_


ApplicationEngine
------------------


Application Engine : A template describing an application
    

.. _ApplicationEngine:

.. list-table:: :guilabel:`ApplicationEngine`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - groups
      - Container<ResourceGroups_> |star|
      - 
      - 
      - 
    * - order
      - Int
      - The order in which the application will be processed
      - 
      - 0

*Base Schemas* `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Notifiable`_, `Title`_

Function
--------

A callable function that returns a value.

.. _alarmsets: yaml-monitoring.html#alarmsets

.. _healthchecks: yaml-monitoring.html#healthchecks

.. _cloudwatchlogsets: yaml-monitoring.html#cloudwatchlogsets

.. _resourcegroups: yaml-netenv.html#resourcegroups

.. _metric: yaml-monitoring.html#metric

.. _alarmnotifications: yaml-monitoring.html#alarmnotifications



.. _account: yaml-accounts.html#account

