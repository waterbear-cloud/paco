
.. _yaml-resources:

Application Resources
=====================

An Application is a collection of Resources. These are the Resources which can exist
as part of an Application.


ApiGatewayRestApi
------------------


An Api Gateway Rest API resource.

Intended to allow provisioning of all API Gateway REST API resources (currently only parital field support).

.. code-block:: yaml
    :caption: API Gateway REST API example

    type: ApiGatewayRestApi
    order: 10
    enabled: true
    fail_on_warnings: true
    description: "My REST API"
    endpoint_configuration:
      - 'REGIONAL'
    models:
      emptyjson:
        content_type: 'application/json'
    methods:
      get:
        http_method: GET
        integration:
          integration_type: AWS
          integration_lambda: paco.ref netenv.mynet.applications.app.groups.restapi.resources.mylambda
          integration_responses:
            - status_code: '200'
              response_templates:
                'application/json': ''
          request_parameters:
            "integration.request.querystring.my_id": "method.request.querystring.my_id"
        authorization_type: NONE
        request_parameters:
          "method.request.querystring.my_id": false
          "method.request.querystring.token": false
        method_responses:
          - status_code: '200'
            response_models:
              - content_type: 'application/json'
                model_name: 'emptyjson'
      post:
        http_method: POST
        integration:
          integration_type: AWS
          integration_lambda: paco.ref netenv.mynet.applications.app.groups.restapi.resources.mylambda
          integration_responses:
            - status_code: '200'
              response_templates:
                'application/json': ''
        authorization_type: NONE
        method_responses:
          - status_code: '200'
            response_models:
              - content_type: 'application/json'
                model_name: 'emptyjson'
    stages:
      prod:
        deployment_id: 'prod'
        description: 'Prod Stage'
        stage_name: 'prod'

    

.. _ApiGatewayRestApi:

.. list-table:: :guilabel:`ApiGatewayRestApi`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - api_key_source_type
      - String
      - API Key Source Type
      - Must be one of 'HEADER' to read the API key from the X-API-Key header of a request or 'AUTHORIZER' to read the API key from the UsageIdentifierKey from a Lambda authorizer.
      - 
    * - binary_media_types
      - List<String>
      - Binary Media Types. The list of binary media types that are supported by the RestApi resource, such as image/png or application/octet-stream. By default, RestApi supports only UTF-8-encoded text payloads.
      - Duplicates are not allowed. Slashes must be escaped with ~1. For example, image/png would be image~1png in the BinaryMediaTypes list.
      - 
    * - body
      - String
      - Body. An OpenAPI specification that defines a set of RESTful APIs in JSON or YAML format. For YAML templates, you can also provide the specification in YAML format.
      - Must be valid JSON.
      - 
    * - body_file_location
      - StringFileReference
      - Path to a file containing the Body.
      - Must be valid path to a valid JSON document.
      - 
    * - body_s3_location
      - String
      - The Amazon Simple Storage Service (Amazon S3) location that points to an OpenAPI file, which defines a set of RESTful APIs in JSON or YAML format.
      - Valid S3Location string to a valid JSON or YAML document.
      - 
    * - clone_from
      - String
      - CloneFrom. The ID of the RestApi resource that you want to clone.
      - 
      - 
    * - description
      - String
      - Description of the RestApi resource.
      - 
      - 
    * - endpoint_configuration
      - List<String>
      - Endpoint configuration. A list of the endpoint types of the API. Use this field when creating an API. When importing an existing API, specify the endpoint configuration types using the `parameters` field.
      - List of strings, each must be one of 'EDGE', 'REGIONAL', 'PRIVATE'
      - 
    * - fail_on_warnings
      - Boolean
      - Indicates whether to roll back the resource if a warning occurs while API Gateway is creating the RestApi resource.
      - 
      - False
    * - methods
      - Container<ApiGatewayMethods_>
      - 
      - 
      - 
    * - minimum_compression_size
      - Int
      - An integer that is used to enable compression on an API. When compression is enabled, compression or decompression is not applied on the payload if the payload size is smaller than this value. Setting it to zero allows compression for any payload size.
      - A non-negative integer between 0 and 10485760 (10M) bytes, inclusive.
      - 
    * - models
      - Container<ApiGatewayModels_>
      - 
      - 
      - 
    * - parameters
      - Dict
      - Parameters. Custom header parameters for the request.
      - Dictionary of key/value pairs that are strings.
      - {}
    * - policy
      - String
      - A policy document that contains the permissions for the RestApi resource, in JSON format. To set the ARN for the policy, use the !Join intrinsic function with "" as delimiter and values of "execute-api:/" and "*".
      - Valid JSON document
      - 
    * - resources
      - Container<ApiGatewayResources_>
      - 
      - 
      - 
    * - stages
      - Container<ApiGatewayStages_>
      - 
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayMethods
^^^^^^^^^^^^^^^^^^

Container for `ApiGatewayMethod`_ objects.

.. _ApiGatewayMethods:

.. list-table:: :guilabel:`ApiGatewayMethods` |bars| Container<`ApiGatewayMethod`_>
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


ApiGatewayMethod
^^^^^^^^^^^^^^^^^

API Gateway Method

.. _ApiGatewayMethod:

.. list-table:: :guilabel:`ApiGatewayMethod`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - authorization_type
      - String |star|
      - Authorization Type
      - Must be one of NONE, AWS_IAM, CUSTOM or COGNITO_USER_POOLS
      - 
    * - http_method
      - String
      - HTTP Method
      - Must be one of ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST or PUT.
      - 
    * - integration
      - Object<ApiGatewayMethodIntegration_>
      - Integration
      - 
      - 
    * - method_responses
      - List<ApiGatewayMethodMethodResponse_>
      - Method Responses
      - List of ApiGatewayMethod MethodResponses
      - 
    * - request_parameters
      - Dict
      - Request Parameters
      - Specify request parameters as key-value pairs (string-to-Boolean mapping),
                with a source as the key and a Boolean as the value. The Boolean specifies whether
                a parameter is required. A source must match the format method.request.location.name,
                where the location is query string, path, or header, and name is a valid, unique parameter name.
      - {}
    * - resource_id
      - String
      - Resource Id
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayModels
^^^^^^^^^^^^^^^^^

Container for `ApiGatewayModel`_ objects.

.. _ApiGatewayModels:

.. list-table:: :guilabel:`ApiGatewayModels` |bars| Container<`ApiGatewayModel`_>
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


ApiGatewayModel
^^^^^^^^^^^^^^^^



.. _ApiGatewayModel:

.. list-table:: :guilabel:`ApiGatewayModel`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_type
      - String
      - Content Type
      - 
      - 
    * - description
      - String
      - Description
      - 
      - 
    * - schema
      - Dict
      - Schema
      - JSON format. Will use null({}) if left empty.
      - {}

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayResources
^^^^^^^^^^^^^^^^^^^^

Container for `ApiGatewayResource`_ objects.

.. _ApiGatewayResources:

.. list-table:: :guilabel:`ApiGatewayResources` |bars| Container<`ApiGatewayResource`_>
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


ApiGatewayResource
^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayResource:

.. list-table:: :guilabel:`ApiGatewayResource`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - parent_id
      - String
      - Id of the parent resource. Default is 'RootResourceId' for a resource without a parent.
      - 
      - RootResourceId
    * - path_part
      - String |star|
      - Path Part
      - 
      - 
    * - rest_api_id
      - String |star|
      - Name of the API Gateway REST API this resource belongs to.
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayStages
^^^^^^^^^^^^^^^^^

Container for `ApiGatewayStage`_ objects

.. _ApiGatewayStages:

.. list-table:: :guilabel:`ApiGatewayStages` |bars| Container<`ApiGatewayStages`_>
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


ApiGatewayStage
^^^^^^^^^^^^^^^^

API Gateway Stage

.. _ApiGatewayStage:

.. list-table:: :guilabel:`ApiGatewayStage`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - deployment_id
      - String
      - Deployment ID
      - 
      - 
    * - description
      - String
      - Description
      - 
      - 
    * - stage_name
      - String
      - Stage name
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


ApiGatewayMethodIntegration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodIntegration:

.. list-table:: :guilabel:`ApiGatewayMethodIntegration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - integration_http_method
      - String
      - Integration HTTP Method
      - Must be one of ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST or PUT.
      - POST
    * - integration_lambda
      - PacoReference
      - Integration Lambda
      - Paco Reference to `Lambda`_.
      - 
    * - integration_responses
      - List<ApiGatewayMethodIntegrationResponse_>
      - Integration Responses
      - 
      - 
    * - integration_type
      - String |star|
      - Integration Type
      - Must be one of AWS, AWS_PROXY, HTTP, HTTP_PROXY or MOCK.
      - AWS
    * - request_parameters
      - Dict
      - The request parameters that API Gateway sends with the backend request.
      - Specify request parameters as key-value pairs (string-to-string mappings),
        with a destination as the key and a source as the value. Specify the destination by using the
        following pattern `integration.request.location.name`, where `location` is query string, path,
        or header, and `name` is a valid, unique parameter name.
        
        The source must be an existing method request parameter or a static value. You must
        enclose static values in single quotation marks and pre-encode these values based on
        their destination in the request.
                
      - {}
    * - uri
      - String
      - Integration URI
      - 
      - 



ApiGatewayMethodIntegrationResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodIntegrationResponse:

.. list-table:: :guilabel:`ApiGatewayMethodIntegrationResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_handling
      - String
      - Specifies how to handle request payload content type conversions.
      - Valid values are:
        
        CONVERT_TO_BINARY: Converts a request payload from a base64-encoded string to a binary blob.
        
        CONVERT_TO_TEXT: Converts a request payload from a binary blob to a base64-encoded string.
        
        If this property isn't defined, the request payload is passed through from the method request
        to the integration request without modification.

      - 
    * - response_parameters
      - Dict
      - Response Parameters
      - 
      - {}
    * - response_templates
      - Dict
      - Response Templates
      - 
      - {}
    * - selection_pattern
      - String
      - A regular expression that specifies which error strings or status codes from the backend map to the integration response.
      - 
      - 
    * - status_code
      - String |star|
      - The status code that API Gateway uses to map the integration response to a MethodResponse status code.
      - Must match a status code in the method_respones for this API Gateway REST API.
      - 



ApiGatewayMethodMethodResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodMethodResponse:

.. list-table:: :guilabel:`ApiGatewayMethodMethodResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - response_models
      - List<ApiGatewayMethodMethodResponseModel_>
      - The resources used for the response's content type.
      - Specify response models as key-value pairs (string-to-string maps),
        with a content type as the key and a Model Paco name as the value.
      - 
    * - status_code
      - String |star|
      - HTTP Status code
      - 
      - 



ApiGatewayMethodMethodResponseModel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _ApiGatewayMethodMethodResponseModel:

.. list-table:: :guilabel:`ApiGatewayMethodMethodResponseModel`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - content_type
      - String
      - Content Type
      - 
      - 
    * - model_name
      - String
      - Model name
      - 
      - 




ASG
----


An AutoScalingGroup (ASG) contains a collection of Amazon EC2 instances that are treated as a
logical grouping for the purposes of automatic scaling and management.

The Paco ASG resource provisions an AutoScalingGroup as well as LaunchConfiguration and TargetGroups
for that ASG.


.. sidebar:: Prescribed Automation

    ASGs use Paco's **LaunchBundles**. A LaunchBundle is a zip file of code and configuration files that is
    automatically created and stored in an S3 Bucket that the ASG has read permissions to. Paco adds BASH code
    to the UserData script for the ASG's LaunchConfiguration that will iterate through all of the LaunchBundles
    and download and run them. For example, if you specify in-host metrics for an ASG, it will have a LaunchBundle
    created with the necessary CloudWatch agent configuration and a BASH script to install and configure the agent.

    ``launch_options``: Options to add actions to newly launched instances: ``ssm_agent``, ``update_packages`` and
    ``cfn_init_config_sets``. The ``ssm_agent`` field will install the SSM Agent and is true by default.
    Paco's **LaunchBundles** feature requires the SSM Agent installed and running. The ``update_packages`` field will
    perform a operating system package update (``yum update`` or ``apt-get update``). This happens immediately after the
    ``user_data_pre_script`` commands, but before the LaunchBundle commands and ``user_data_script`` commands.
    The ``cfn_init_config_sets`` field is a list of CfnInitConfigurationSets that will be run at launch.

    ``cfn_init``: Contains CloudFormationInit (cfn-init) configuration. Paco allows reading cfn-init
    files from the filesystem, and also does additional validation checks on the configuration to ensure
    it is correct. The ``launch_options`` has a ``cfn_init_config_sets`` field to specify which
    CfnInitConfigurationSets you want to automatically call during instance launch with a LaunchBundle.

    ``ebs_volume_mounts``: Adds an EBS LaunchBundle that mounts all EBS Volumes
    to the EC2 instance launched by the ASG. If the EBS Volume is unformatted, it will be formatted to the
    specified filesystem. **This feature only works with "self-healing" ASGs**. A "self-healing" ASG is an ASG
    with ``max_instances`` set to 1. Trying to launch a second instance in the ASG will fail to mount the EBS Volume
    as it can only be mounted to one instance at a time.

    ``eip``: Adds an EIP LaunchBundle which will attach an Elastic IP to a launched instance.
    **This feature only works with "self-healing" ASGs**. A "self-healing" ASG is an ASG
    with ``max_instances`` set to 1. Trying to launch a second instance in the ASG will fail to attach the EIP
    as it can only be mounted to one instance at a time.

    ``efs_mounts``: Adds an EFS LaunchBundle that mounts all EFS locations. A SecurityGroup
    must still be manually configured to allow the ASG instances to network access to the EFS filesystem.

    ``monitoring``: Any fields specified in the ``metrics`` or ``log_sets`` fields will add a CloudWatchAgent LaunchBundle
    that will install a CloudWatch Agent and configure it to collect all specified metrics and log sources.

    ``secrets``: Adds a policy to the Instance Role which allows instances to access the specified secrets.

    ``ssh_access``:  Grants users and groups SSH access to the instances.

.. code-block:: yaml
    :caption: example ASG configuration

    type: ASG
    order: 30
    enabled: true
    associate_public_ip_address: false
    cooldown_secs: 200
    ebs_optimized: false
    health_check_grace_period_secs: 240
    health_check_type: EC2
    availability_zone: 1
    ebs_volume_mounts:
      - volume: paco.ref netenv.mynet.applications.app.groups.storage.resources.my_volume
        enabled: true
        folder: /var/www/html
        device: /dev/xvdf
        filesystem: ext4
    efs_mounts:
      - enabled: true
        folder: /mnt/wp_efs
        target: paco.ref netenv.mynet.applications.app.groups.storage.resources.my_efs
    instance_iam_role:
      enabled: true
      policies:
        - name: DNSRecordSet
          statement:
            - effect: Allow
              action:
                - route53:ChangeResourceRecordSets
              resource:
                - 'arn:aws:route53:::hostedzone/HHIHkjhdhu744'
    instance_ami: paco.ref function.aws.ec2.ami.latest.amazon-linux-2
    instance_ami_type: amazon
    instance_key_pair: paco.ref resource.ec2.keypairs.my_keypair
    instance_monitoring: true
    instance_type: t2.medium
    desired_capacity: 1
    max_instances: 3
    min_instances: 1
    rolling_update_policy:
      max_batch_size: 1
      min_instances_in_service: 1
      pause_time: PT3M
      wait_on_resource_signals: false
    target_groups:
      - paco.ref netenv.mynet.applications.app.groups.web.resources.alb.target_groups.cloud
    security_groups:
      - paco.ref netenv.mynet.network.vpc.security_groups.web.asg
    segment: private
    termination_policies:
      - Default
    scaling_policy_cpu_average: 60
    ssh_access:
      users:
        - bdobbs
      groups:
        - developers
    launch_options:
        update_packages: true
        ssm_agent: true
        cfn_init_config_sets:
        - "InstallApp"
    cfn_init:
      config_sets:
        InstallApp:
          - "InstallApp"
      configurations:
        InstallApp:
          packages:
            yum:
              python3: []
          users:
            www-data:
              uid: 2000
              home_dir: /home/www-data
          files:
            "/etc/systemd/system/pypiserver.service":
              content_file: ./pypi-config/pypiserver.service
              mode: '000755'
              owner: root
              group: root
          commands:
            00_pypiserver:
              command: "/bin/pip3 install pypiserver"
            01_passlib_dependency:
              command: "/bin/pip3 install passlib"
            02_prep_mount:
               command: "chown www-data:www-data /var/pypi"
          services:
            sysvinit:
              pypiserver:
                enabled: true
                ensure_running: true
    monitoring:
      enabled: true
      collection_interval: 60
      metrics:
        - name: swap
          measurements:
            - used_percent
        - name: disk
          measurements:
            - free
          resources:
            - '/'
            - '/var/www/html'
          collection_interval: 300
    user_data_script: |
      echo "Hello World!"


AutoScalingGroup Rolling Update Policy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When changes are applied to an AutoScalingGroup that modify the configuration of newly launched instances,
AWS can automatically launch instances with the new configuration and terminate old instances that have stale configuration.
This can be configured so that there is no interruption of service as the new instances gradually replace old ones.
This configuration is set with the ``rolling_update_policy`` field.

The rolling update policy must be able to work within the minimum/maximum number of instances in the ASG.
Consider the following ASG configuration.

.. code-block:: yaml
    :caption: example ASG configuration

    type: ASG
    max_instances: 2
    min_instances: 1
    desired_capacity: 1
    rolling_update_policy:
      max_batch_size: 1
      min_instances_in_service: 1
      pause_time: PT0S # default setting
      wait_on_resource_signals: false # default setting

This will normally run a single instance in the ASG. The ASG is never allowed to launch more than 2 instances at one time.
When an update happens, a new batch of instances is launched - in this example just one instance. There wil be only 1 instance
in service, but the capacity will be at 2 instances will the new instance is launched. After the instance
is put into service by the ASG, it will immediately terminate the old instance.

The ``wait_on_resource_signals`` can be set to tell AWS CloudFormation to wait on making changes to the AutoScalingGroup configuration
until a new instance is finished configuring and installing applications and is ready for service. If this field is enabled,
then the ``pause_time`` default is PT05 (5 minutes). If CloudFormation does not get a SUCCESS signal within the ``pause_time``
then it will mark the new instance as failed and terminate it.

If you use ``pause_time`` with the default ``wait_on_resource_signals: false`` then AWS will simply wait for the full
duration of the pause time and then consider the instance ready. ``pause_time`` is in format PT#H#M#S, where each # is the number of
hours, minutes, and seconds, respectively. The maximum ``pause_time`` is one hour. For example:

.. code-block:: yaml

    pause_time: PT0S # 0 seconds
    pause_time: PT5M # 5 minutes
    pause_time: PT2M30S # 2 minutes and 30 seconds

ASGs will use default settings for a rolling update policy. If you do not want to use an update policies at all, then
you must disable the ``rolling_update_policy`` explicitly:

.. code-block:: yaml

    type: ASG
    rolling_update_policy:
      enabled: false

With no rolling update policy, when you make configuration changes, then existing instances with old configuration will
continue to run and instances with the new configuration will not happen until the AutoScalingGroup needs to launch new
instances. You must be careful with this approach as you can not know 100% that your new configuration launches instances
proprely until some point in the future when new instances are requested by the ASG.

.. sidebar:: Prescribed Automation

    Paco can help you send signals to CloudFormation when using ``wait_on_resource_signals``.
    If you set ``wait_on_resource_signals: true`` then Paco will automatically grant the needed ``cloudformation:SignalResource`` and
    ``cloudformation:DescribeStacks`` to the IAM Role associated with the instance for you. Paco also provides an
    ``ec2lm_signal_asg_resource`` BASH function available in your ``user_data_script`` that you can run to signal the instance is
    ready: ``ec2lm_signal_asg_resource SUCCESS`` or ``ec2lm_signal_asg_resource SUCCESS``.

    If you want to wait until load balancer health checks are passing before an instance is considered healthy, then send the SUCCESS
    signal to CloudFormation, you will need to configure this yourself.

        .. code-block:: bash
            :caption: example ASG signalling using ELB health checks

            'until [ "$state" == ""InService"" ]; do state=$(aws --region ${AWS::Region} elb describe-instance-health
            --load-balancer-name ${ElasticLoadBalancer}
            --instances $(curl -s http://169.254.169.254/latest/meta-data/instance-id)
            --query InstanceStates[0].State); sleep 10; done'


See the AWS documentation for more information on how `AutoScalingRollingUpdate Policy`_ configuration is used.

.. _AutoScalingRollingUpdate Policy: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-updatepolicy.html#cfn-attributes-updatepolicy-replacingupdate

    

.. _ASG:

.. list-table:: :guilabel:`ASG`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - associate_public_ip_address
      - Boolean
      - Associate Public IP Address
      - 
      - False
    * - availability_zone
      - String
      - Availability Zones to launch instances in.
      - 
      - all
    * - block_device_mappings
      - List<BlockDeviceMapping_>
      - Block Device Mappings
      - 
      - 
    * - cfn_init
      - Object<CloudFormationInit_>
      - CloudFormation Init
      - 
      - 
    * - cooldown_secs
      - Int
      - Cooldown seconds
      - 
      - 300
    * - desired_capacity
      - Int
      - Desired capacity
      - 
      - 1
    * - desired_capacity_ignore_changes
      - Boolean
      - Ignore changes to the desired_capacity after the ASG is created.
      - 
      - False
    * - ebs_optimized
      - Boolean
      - EBS Optimized
      - 
      - False
    * - ebs_volume_mounts
      - List<EBSVolumeMount_>
      - Elastic Block Store Volume Mounts
      - 
      - 
    * - ecs
      - Object<ECSASGConfiguration_>
      - ECS Configuration
      - 
      - 
    * - efs_mounts
      - List<EFSMount_>
      - Elastic Filesystem Configuration
      - 
      - 
    * - eip
      - PacoReference|String
      - Elastic IP or AllocationId to attach to instance at launch
      - Paco Reference to `EIP`_. String Ok.
      - 
    * - health_check_grace_period_secs
      - Int
      - Health check grace period in seconds
      - 
      - 300
    * - health_check_type
      - String
      - Health check type
      - Must be one of: 'EC2', 'ELB'
      - EC2
    * - instance_ami
      - PacoReference|String
      - Instance AMI
      - Paco Reference to `Function`_. String Ok.
      - 
    * - instance_ami_ignore_changes
      - Boolean
      - Do not update the instance_ami after creation.
      - 
      - False
    * - instance_ami_type
      - String
      - The AMI Operating System family
      - Must be one of amazon, centos, suse, debian, ubuntu, microsoft or redhat.
      - amazon
    * - instance_iam_role
      - Object<Role_>
      - 
      - 
      - 
    * - instance_key_pair
      - PacoReference
      - Key pair to connect to launched instances
      - Paco Reference to `EC2KeyPair`_.
      - 
    * - instance_monitoring
      - Boolean
      - Instance monitoring
      - 
      - False
    * - instance_type
      - String
      - Instance type
      - 
      - 
    * - launch_options
      - Object<EC2LaunchOptions_> |star|
      - EC2 Launch Options
      - 
      - 
    * - lifecycle_hooks
      - Container<ASGLifecycleHooks_>
      - Lifecycle Hooks
      - 
      - 
    * - load_balancers
      - List<PacoReference>
      - Target groups
      - Paco Reference to `TargetGroup`_.
      - 
    * - max_instances
      - Int
      - Maximum instances
      - 
      - 2
    * - min_instances
      - Int
      - Minimum instances
      - 
      - 1
    * - rolling_update_policy
      - Object<ASGRollingUpdatePolicy_> |star|
      - Rolling Update Policy
      - 
      - 
    * - scaling_policies
      - Container<ASGScalingPolicies_>
      - Scaling Policies
      - 
      - 
    * - scaling_policy_cpu_average
      - Int
      - Average CPU Scaling Polciy
      - 
      - 0
    * - secrets
      - List<PacoReference>
      - List of Secrets Manager References
      - Paco Reference to `SecretsManagerSecret`_.
      - 
    * - security_groups
      - List<PacoReference>
      - Security groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 
    * - ssh_access
      - Object<SSHAccess_>
      - SSH Access
      - 
      - 
    * - target_groups
      - List<PacoReference>
      - Target groups
      - Paco Reference to `TargetGroup`_.
      - 
    * - termination_policies
      - List<String>
      - Terminiation policies
      - 
      - 
    * - user_data_pre_script
      - String
      - User data pre-script
      - 
      - 
    * - user_data_script
      - String
      - User data script
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


ASGLifecycleHooks
^^^^^^^^^^^^^^^^^^


Container for `ASGLifecycleHook` objects.
    

.. _ASGLifecycleHooks:

.. list-table:: :guilabel:`ASGLifecycleHooks` |bars| Container<`ASGLifecycleHook`_>
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


ASGLifecycleHook
^^^^^^^^^^^^^^^^^


ASG Lifecycle Hook
    

.. _ASGLifecycleHook:

.. list-table:: :guilabel:`ASGLifecycleHook`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - default_result
      - String
      - Default Result
      - 
      - 
    * - lifecycle_transition
      - String |star|
      - ASG Lifecycle Transition
      - 
      - 
    * - notification_target_arn
      - String |star|
      - Lifecycle Notification Target Arn
      - 
      - 
    * - role_arn
      - String |star|
      - Licecycel Publish Role ARN
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


ASGScalingPolicies
^^^^^^^^^^^^^^^^^^^


Container for `ASGScalingPolicy`_ objects.
    

.. _ASGScalingPolicies:

.. list-table:: :guilabel:`ASGScalingPolicies` |bars| Container<`ASGScalingPolicy`_>
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


ASGScalingPolicy
^^^^^^^^^^^^^^^^^


Auto Scaling Group Scaling Policy
    

.. _ASGScalingPolicy:

.. list-table:: :guilabel:`ASGScalingPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - adjustment_type
      - String |star|
      - Adjustment Type
      - 
      - ChangeInCapacity
    * - alarms
      - List<SimpleCloudWatchAlarm_> |star|
      - Alarms
      - 
      - 
    * - cooldown
      - Int
      - Scaling Cooldown in Seconds
      - 
      - 300
    * - policy_type
      - String |star|
      - Policy Type
      - 
      - SimpleScaling
    * - scaling_adjustment
      - Int |star|
      - Scaling Adjustment
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_


ASGRollingUpdatePolicy
^^^^^^^^^^^^^^^^^^^^^^^


AutoScalingRollingUpdate Policy
    

.. _ASGRollingUpdatePolicy:

.. list-table:: :guilabel:`ASGRollingUpdatePolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - enabled
      - Boolean
      - Enable an UpdatePolicy for the ASG
      - 
      - True
    * - max_batch_size
      - Int
      - Maximum batch size
      - 
      - 1
    * - min_instances_in_service
      - Int
      - Minimum instances in service
      - 
      - 0
    * - pause_time
      - String
      - Minimum instances in service
      - Must be in the format PT#H#M#S
      - 
    * - wait_on_resource_signals
      - Boolean |star|
      - Wait for resource signals
      - 
      - False

*Base Schemas* `Named`_, `Title`_


ECSASGConfiguration
^^^^^^^^^^^^^^^^^^^^



.. _ECSASGConfiguration:

.. list-table:: :guilabel:`ECSASGConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - capacity_provider
      - Object<ECSCapacityProvider_>
      - Capacity Provider
      - 
      - 
    * - cluster
      - PacoReference |star|
      - Cluster
      - Paco Reference to `ECSCluster`_.
      - 
    * - log_level
      - Choice
      - Log Level
      - 
      - error

*Base Schemas* `Named`_, `Title`_


ECSCapacityProvider
^^^^^^^^^^^^^^^^^^^^



.. _ECSCapacityProvider:

.. list-table:: :guilabel:`ECSCapacityProvider`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - maximum_scaling_step_size
      - Int
      - Maximum Scaling Step Size
      - 
      - 10000
    * - minimum_scaling_step_size
      - Int
      - Minimum Scaling Step Size
      - 
      - 1
    * - target_capacity
      - Int
      - Target Capacity
      - 
      - 100

*Base Schemas* `Deployable`_, `Named`_, `Title`_


SSHAccess
^^^^^^^^^^



.. _SSHAccess:

.. list-table:: :guilabel:`SSHAccess`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - groups
      - List<String>
      - Groups
      - Must match a group declared in resource/ec2.yaml
      - []
    * - users
      - List<String>
      - User
      - Must match a user declared in resource/ec2.yaml
      - []

*Base Schemas* `Named`_, `Title`_


BlockDeviceMapping
^^^^^^^^^^^^^^^^^^^



.. _BlockDeviceMapping:

.. list-table:: :guilabel:`BlockDeviceMapping`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - device_name
      - String |star|
      - The device name exposed to the EC2 instance
      - 
      - 
    * - ebs
      - Object<BlockDevice_>
      - Amazon Ebs volume
      - 
      - 
    * - virtual_name
      - String
      - The name of the virtual device.
      - The name must be in the form ephemeralX where X is a number starting from zero (0), for example, ephemeral0.
      - 



BlockDevice
^^^^^^^^^^^^



.. _BlockDevice:

.. list-table:: :guilabel:`BlockDevice`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - delete_on_termination
      - Boolean
      - Indicates whether to delete the volume when the instance is terminated.
      - 
      - True
    * - encrypted
      - Boolean
      - Specifies whether the EBS volume is encrypted.
      - 
      - 
    * - iops
      - Int
      - The number of I/O operations per second (IOPS) to provision for the volume.
      - The maximum ratio of IOPS to volume size (in GiB) is 50:1, so for 5,000 provisioned IOPS, you need at least 100 GiB storage on the volume.
      - 
    * - size_gib
      - Int
      - The volume size, in Gibibytes (GiB).
      - This can be a number from 1-1,024 for standard, 4-16,384 for io1, 1-16,384 for gp2, and 500-16,384 for st1 and sc1.
      - 
    * - snapshot_id
      - String
      - The snapshot ID of the volume to use.
      - 
      - 
    * - volume_type
      - String |star|
      - The volume type, which can be standard for Magnetic, io1 for Provisioned IOPS SSD, gp2 for General Purpose SSD, st1 for Throughput Optimized HDD, or sc1 for Cold HDD.
      - Must be one of standard, io1, gp2, st1 or sc1.
      - 



EBSVolumeMount
^^^^^^^^^^^^^^^


EBS Volume Mount Configuration
    

.. _EBSVolumeMount:

.. list-table:: :guilabel:`EBSVolumeMount`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - device
      - String |star|
      - Device to mount the EBS Volume with.
      - 
      - 
    * - filesystem
      - String |star|
      - Filesystem to mount the EBS Volume with.
      - 
      - 
    * - folder
      - String |star|
      - Folder to mount the EBS Volume
      - 
      - 
    * - volume
      - PacoReference|String |star|
      - EBS Volume Resource Reference
      - Paco Reference to `EBS`_. String Ok.
      - 

*Base Schemas* `Deployable`_


EFSMount
^^^^^^^^^


EFS Mount Folder and Target Configuration
    

.. _EFSMount:

.. list-table:: :guilabel:`EFSMount`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - folder
      - String |star|
      - Folder to mount the EFS target
      - 
      - 
    * - target
      - PacoReference|String |star|
      - EFS Target Resource Reference
      - Paco Reference to `EFS`_. String Ok.
      - 

*Base Schemas* `Deployable`_


EC2LaunchOptions
^^^^^^^^^^^^^^^^^


EC2 Launch Options
    

.. _EC2LaunchOptions:

.. list-table:: :guilabel:`EC2LaunchOptions`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cfn_init_config_sets
      - List<String>
      - List of cfn-init config sets
      - 
      - []
    * - ssm_agent
      - Boolean
      - Install SSM Agent
      - 
      - True
    * - ssm_expire_events_after_days
      - String
      - Retention period of SSM logs
      - 
      - 30
    * - update_packages
      - Boolean
      - Update Distribution Packages
      - 
      - False

*Base Schemas* `Named`_, `Title`_


CloudFormationInit
^^^^^^^^^^^^^^^^^^^


`CloudFormation Init`_ is a method to configure an EC2 instance after it is launched.
CloudFormation Init is a much more complete and robust method to install configuration files and
pakcages than using a UserData script.

It stores information about packages, files, commands and more in CloudFormation metadata. It is accompanied
by a ``cfn-init`` script which will run on the instance to fetch this configuration metadata and apply
it. The whole system is often referred to simply as cfn-init after this script.

The ``cfn_init`` field of for an ASG contains all of the cfn-init configuration. After an instance
is launched, it needs to run a local cfn-init script to pull the configuration from the CloudFromation
stack and apply it. After cfn-init has applied configuration, you will run cfn-signal to tell CloudFormation
the configuration was successfully applied. Use the ``launch_options`` field for an ASG to let Paco take care of all this
for you.

.. sidebar:: Prescribed Automation

    ``launch_options``: The ``cfn_init_config_sets:`` field is a list of cfn-init configurations to
    apply at launch. This list will be applied in order. On Amazon Linux the cfn-init script is pre-installed
    in /opt/aws/bin. If you enable a cfn-init launch option, Paco will install cfn-init in /opt/paco/bin for you.

Refer to the `CloudFormation Init`_ docs for a complete description of all the configuration options
available.

.. code-block:: yaml
    :caption: cfn_init with launch_options

    launch_options:
        cfn_init_config_sets:
        - "Install"
    cfn_init:
      parameters:
        BasicKey: static-string
        DatabasePasswordarn: paco.ref netenv.mynet.secrets_manager.app.site.database.arn
      config_sets:
        Install:
          - "Install"
      configurations:
        Install:
          packages:
            rpm:
              epel: "http://download.fedoraproject.org/pub/epel/5/i386/epel-release-5-4.noarch.rpm"
            yum:
              jq: []
              python3: []
          files:
            "/tmp/get_rds_dsn.sh":
              content_cfn_file: ./webapp/get_rds_dsn.sh
              mode: '000700'
              owner: root
              group: root
            "/etc/httpd/conf.d/saas_wsgi.conf":
              content_file: ./webapp/saas_wsgi.conf
              mode: '000600'
              owner: root
              group: root
            "/etc/httpd/conf.d/wsgi.conf":
              content: "LoadModule wsgi_module modules/mod_wsgi.so"
              mode: '000600'
              owner: root
              group: root
            "/tmp/install_codedeploy.sh":
              source: https://aws-codedeploy-us-west-2.s3.us-west-2.amazonaws.com/latest/install
              mode: '000700'
              owner: root
              group: root
          commands:
            10_install_codedeploy:
              command: "/tmp/install_codedeploy.sh auto > /var/log/cfn-init-codedeploy.log 2>&1"
          services:
            sysvinit:
              codedeploy-agent:
                enabled: true
                ensure_running: true

The ``parameters`` field is a set of Parameters that will be passed to the CloudFormation stack. This
can be static strings or ``paco.ref`` that are looked up from already provisioned cloud resources.

CloudFormation Init can be organized into Configsets. With raw cfn-init using Configsets is optional,
but is required with Paco.

In a Configset, the ``files`` field has four fields for specifying the file contents.

 * ``content_file:`` A path to a file on the local filesystem. A convenient practice is to make a
   sub-directory in the ``netenv`` directory for keeping cfn-init files.

 * ``content_cfn_file:`` A path to a file on the local filesystem. This file will have FnSub and FnJoin
   CloudFormation applied to it.

 * ``content:`` For small files, the content can be in-lined directly in this field.

 * ``source:`` Fetches the file from a URL.

If you are using ``content_cfn_file`` to interpolate Parameters, the file might look like:

.. code-block:: bash

    !Sub |
        #!/bin/bash

        echo "Database ARN is " ${DatabasePasswordarn}
        echo "AWS Region is " ${AWS::Region}

If you want to include a raw ``${SomeValue}`` string in your file, use the ! character to escape it like this:
``${!SomeValue}``. cfn-init also supports interpolation with Mustache templates, but Paco support for this is
not yet implemented.

.. _CloudFormation Init: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-init.html

    

.. _CloudFormationInit:

.. list-table:: :guilabel:`CloudFormationInit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - config_sets
      - Container<CloudFormationConfigSets_> |star|
      - CloudFormation Init configSets
      - 
      - 
    * - configurations
      - Container<CloudFormationConfigurations_> |star|
      - CloudFormation Init configurations
      - 
      - 
    * - parameters
      - Dict
      - Parameters
      - 
      - {}

*Base Schemas* `Named`_, `Title`_


CloudFormationConfigSets
^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigSets:

.. list-table:: :guilabel:`CloudFormationConfigSets`
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


CloudFormationConfigurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfigurations:

.. list-table:: :guilabel:`CloudFormationConfigurations` |bars| Container<`CloudFormationConfiguration`_>
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


CloudFormationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationConfiguration:

.. list-table:: :guilabel:`CloudFormationConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - commands
      - Container<CloudFormationInitCommands_>
      - Commands
      - 
      - 
    * - files
      - Container<CloudFormationInitFiles_>
      - Files
      - 
      - 
    * - groups
      - Object<CloudFormationInitGroups_>
      - Groups
      - 
      - 
    * - packages
      - Object<CloudFormationInitPackages_>
      - Packages
      - 
      - 
    * - services
      - Object<CloudFormationInitServices_>
      - Services
      - 
      - 
    * - sources
      - Container<CloudFormationInitSources_>
      - Sources
      - 
      - 
    * - users
      - Object<CloudFormationInitUsers_>
      - Users
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitCommands
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitCommands:

.. list-table:: :guilabel:`CloudFormationInitCommands`
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


CloudFormationInitCommand
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitCommand:

.. list-table:: :guilabel:`CloudFormationInitCommand`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - command
      - String |star|
      - Command
      - 
      - 
    * - cwd
      - String
      - Cwd. The working directory
      - 
      - 
    * - env
      - Dict
      - Environment Variables. This property overwrites, rather than appends, the existing environment.
      - 
      - {}
    * - ignore_errors
      - Boolean
      - Ingore errors - determines whether cfn-init continues to run if the command in contained in the command key fails (returns a non-zero value). Set to true if you want cfn-init to continue running even if the command fails.
      - 
      - False
    * - test
      - String
      - A test command that determines whether cfn-init runs commands that are specified in the command key. If the test passes, cfn-init runs the commands.
      - 
      - 



CloudFormationInitFiles
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitFiles:

.. list-table:: :guilabel:`CloudFormationInitFiles`
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


CloudFormationInitFile
^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitFile:

.. list-table:: :guilabel:`CloudFormationInitFile`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - authentication
      - String
      - The name of an authentication method to use.
      - 
      - 
    * - content
      - Object<Interface_>
      - Either a string or a properly formatted YAML object.
      - 
      - 
    * - content_cfn_file
      - YAMLFileReference
      - File path to a properly formatted CloudFormation Functions YAML object.
      - 
      - 
    * - content_file
      - StringFileReference
      - File path to a string.
      - 
      - 
    * - context
      - String
      - Specifies a context for files that are to be processed as Mustache templates.
      - 
      - 
    * - encoding
      - String
      - The encoding format.
      - 
      - 
    * - group
      - String
      - The name of the owning group for this file. Not supported for Windows systems.
      - 
      - 
    * - mode
      - String
      - A six-digit octal value representing the mode for this file.
      - 
      - 
    * - owner
      - String
      - The name of the owning user for this file. Not supported for Windows systems.
      - 
      - 
    * - source
      - String
      - A URL to load the file from.
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitGroups
^^^^^^^^^^^^^^^^^^^^^^^^^


Container for CloudFormationInit Groups
    
    * -
      -
      -
      -
      -



CloudFormationInitPackages
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitPackages:

.. list-table:: :guilabel:`CloudFormationInitPackages`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - apt
      - Container<CloudFormationInitVersionedPackageSet_>
      - Apt packages
      - 
      - 
    * - msi
      - Container<CloudFormationInitPathOrUrlPackageSet_>
      - MSI packages
      - 
      - 
    * - python
      - Container<CloudFormationInitVersionedPackageSet_>
      - Apt packages
      - 
      - 
    * - rpm
      - Container<CloudFormationInitPathOrUrlPackageSet_>
      - RPM packages
      - 
      - 
    * - rubygems
      - Container<CloudFormationInitVersionedPackageSet_>
      - Rubygems packages
      - 
      - 
    * - yum
      - Container<CloudFormationInitVersionedPackageSet_>
      - Yum packages
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitVersionedPackageSet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CloudFormationInitPathOrUrlPackageSet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    * -
      -
      -
      -
      -



CloudFormationInitServiceCollection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitServiceCollection:

.. list-table:: :guilabel:`CloudFormationInitServiceCollection`
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


CloudFormationInitServices
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitServices:

.. list-table:: :guilabel:`CloudFormationInitServices`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - sysvinit
      - Container<CloudFormationInitServiceCollection_>
      - SysVInit Services for Linux OS
      - 
      - 
    * - windows
      - Container<CloudFormationInitServiceCollection_>
      - Windows Services for Windows OS
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFormationInitService
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitService:

.. list-table:: :guilabel:`CloudFormationInitService`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - commands
      - List<String>
      - A list of command names. If cfn-init runs the specified command, this service will be restarted.
      - 
      - 
    * - enabled
      - Boolean
      - Ensure that the service will be started or not started upon boot.
      - 
      - 
    * - ensure_running
      - Boolean
      - Ensure that the service is running or stopped after cfn-init finishes.
      - 
      - 
    * - files
      - List<String>
      - A list of files. If cfn-init changes one directly via the files block, this service will be restarted
      - 
      - 
    * - packages
      - Dict
      - A map of package manager to list of package names. If cfn-init installs or updates one of these packages, this service will be restarted.
      - 
      - {}
    * - sources
      - List<String>
      - A list of directories. If cfn-init expands an archive into one of these directories, this service will be restarted.
      - 
      - 



CloudFormationInitSources
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFormationInitSources:

.. list-table:: :guilabel:`CloudFormationInitSources`
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


CloudFormationInitUsers
^^^^^^^^^^^^^^^^^^^^^^^^


Container for CloudFormationInit Users
    
    * -
      -
      -
      -
      -




AWSCertificateManager
----------------------



.. _AWSCertificateManager:

.. list-table:: :guilabel:`AWSCertificateManager`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - String
      - Domain Name
      - 
      - 
    * - external_resource
      - Boolean
      - Marks this resource as external to avoid creating and validating it.
      - 
      - False
    * - private_ca
      - String
      - Private Certificate Authority ARN
      - 
      - 
    * - subject_alternative_names
      - List<String>
      - Subject alternative names
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



CloudFront
-----------


CloudFront CDN Configuration
    

.. _CloudFront:

.. list-table:: :guilabel:`CloudFront`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cache_behaviors
      - List<CloudFrontCacheBehavior_>
      - List of Cache Behaviors
      - 
      - 
    * - custom_error_responses
      - List<CloudFrontCustomErrorResponse_>
      - List of Custom Error Responses
      - 
      - 
    * - default_cache_behavior
      - Object<CloudFrontDefaultCacheBehavior_>
      - Default Cache Behavior
      - 
      - 
    * - default_root_object
      - String
      - The default path to load from the origin.
      - 
      - 
    * - domain_aliases
      - List<DNS_>
      - List of DNS for the Distribution
      - 
      - 
    * - factory
      - Container<CloudFrontFactory_>
      - CloudFront Factory
      - 
      - 
    * - origins
      - Container<CloudFrontOrigin_>
      - Map of Origins
      - 
      - 
    * - price_class
      - String
      - Price Class
      - 
      - All
    * - viewer_certificate
      - Object<CloudFrontViewerCertificate_>
      - Viewer Certificate
      - 
      - 
    * - webacl_id
      - String
      - WAF WebACLId
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


CloudFrontDefaultCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontDefaultCacheBehavior:

.. list-table:: :guilabel:`CloudFrontDefaultCacheBehavior`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - allowed_methods
      - List<String>
      - List of Allowed HTTP Methods
      - 
      - ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
    * - cached_methods
      - List<String>
      - List of HTTP Methods to cache
      - 
      - ['GET', 'HEAD', 'OPTIONS']
    * - compress
      - Boolean
      - Compress certain files automatically
      - 
      - False
    * - default_ttl
      - Int |star|
      - Default TTL
      - 
      - 0
    * - forwarded_values
      - Object<CloudFrontForwardedValues_>
      - Forwarded Values
      - 
      - 
    * - max_ttl
      - Int |star|
      - Maximum TTL
      - 
      - -1
    * - min_ttl
      - Int |star|
      - Minimum TTL
      - 
      - -1
    * - target_origin
      - PacoReference |star|
      - Target Origin
      - Paco Reference to `CloudFrontOrigin`_.
      - 
    * - viewer_protocol_policy
      - String |star|
      - Viewer Protocol Policy
      - 
      - redirect-to-https

*Base Schemas* `Named`_, `Title`_


CloudFrontCacheBehavior
^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCacheBehavior:

.. list-table:: :guilabel:`CloudFrontCacheBehavior`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - path_pattern
      - String |star|
      - Path Pattern
      - 
      - 

*Base Schemas* `CloudFrontDefaultCacheBehavior`_, `Named`_, `Title`_


CloudFrontFactory
^^^^^^^^^^^^^^^^^^

CloudFront Factory

.. _CloudFrontFactory:

.. list-table:: :guilabel:`CloudFrontFactory`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_aliases
      - List<DNS_>
      - List of DNS for the Distribution
      - 
      - 
    * - viewer_certificate
      - Object<CloudFrontViewerCertificate_>
      - Viewer Certificate
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontOrigin
^^^^^^^^^^^^^^^^^


CloudFront Origin Configuration
    

.. _CloudFrontOrigin:

.. list-table:: :guilabel:`CloudFrontOrigin`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - custom_origin_config
      - Object<CloudFrontCustomOriginConfig_>
      - Custom Origin Configuration
      - 
      - 
    * - domain_name
      - PacoReference|String
      - Origin Resource Reference
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - s3_bucket
      - PacoReference
      - Origin S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontCustomOriginConfig
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomOriginConfig:

.. list-table:: :guilabel:`CloudFrontCustomOriginConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - http_port
      - Int
      - HTTP Port
      - 
      - 
    * - https_port
      - Int
      - HTTPS Port
      - 
      - 
    * - keepalive_timeout
      - Int
      - HTTP Keepalive Timeout
      - 
      - 5
    * - protocol_policy
      - String |star|
      - Protocol Policy
      - 
      - 
    * - read_timeout
      - Int
      - Read timeout
      - 
      - 30
    * - ssl_protocols
      - List<String> |star|
      - List of SSL Protocols
      - 
      - 

*Base Schemas* `Named`_, `Title`_


CloudFrontCustomErrorResponse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontCustomErrorResponse:

.. list-table:: :guilabel:`CloudFrontCustomErrorResponse`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - error_caching_min_ttl
      - Int
      - Error Caching Min TTL
      - 
      - 300
    * - error_code
      - Int
      - HTTP Error Code
      - 
      - 
    * - response_code
      - Int
      - HTTP Response Code
      - 
      - 
    * - response_page_path
      - String
      - Response Page Path
      - 
      - 



CloudFrontViewerCertificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontViewerCertificate:

.. list-table:: :guilabel:`CloudFrontViewerCertificate`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - certificate
      - PacoReference
      - Certificate Reference
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - minimum_protocol_version
      - String
      - Minimum SSL Protocol Version
      - 
      - TLSv1.1_2016
    * - ssl_supported_method
      - String
      - SSL Supported Method
      - 
      - sni-only

*Base Schemas* `Named`_, `Title`_


CloudFrontForwardedValues
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CloudFrontForwardedValues:

.. list-table:: :guilabel:`CloudFrontForwardedValues`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cookies
      - Object<CloudFrontCookies_>
      - Forward Cookies
      - 
      - 
    * - headers
      - List<String>
      - Forward Headers
      - 
      - ['*']
    * - query_string
      - Boolean
      - Forward Query Strings
      - 
      - True

*Base Schemas* `Named`_, `Title`_


CloudFrontCookies
^^^^^^^^^^^^^^^^^^



.. _CloudFrontCookies:

.. list-table:: :guilabel:`CloudFrontCookies`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - forward
      - String
      - Cookies Forward Action
      - 
      - all
    * - whitelisted_names
      - List<String>
      - White Listed Names
      - 
      - 

*Base Schemas* `Named`_, `Title`_



CodeDeployApplication
----------------------


CodeDeploy Application creates CodeDeploy Application and Deployment Groups for that application.

This resource can be used when you already have another process in-place to put deploy artifacts
into an S3 Bucket. If you also need to build artifacts, use `DeploymentPipeline`_ instead.

.. sidebar:: Prescribed Automation

    **CodeDeploy Service Role**: The AWS CodeDeploy service needs a Service Role that it is allowed to
    assume to allow the service to run in your AWS Account. Paco will automatically create such a service
    role for every CodeDeploy Application.

.. code-block:: yaml
    :caption: Example CodeDeployApplication resource YAML

    type: CodeDeployApplication
    order: 40
    compute_platform: "Server"
    deployment_groups:
      deployment:
        title: "My Deployment Group description"
        ignore_application_stop_failures: true
        revision_location_s3: paco.ref netenv.mynet.applications.app.groups.deploybucket
        autoscalinggroups:
          - paco.ref netenv.mynet.applications.app.groups.web

It can be convienent to install the CodeDeploy agent on your instances using CloudFormationInit.

.. code-block:: yaml
    :caption: Example ASG configuration for cfn_init to install CodeDeploy agent

    launch_options:
      cfn_init_config_sets:
        - "InstallCodeDeploy"
    cfn_init:
      config_sets:
        InstallCodeDeploy:
          - "InstallCodeDeploy"
      files:
        "/tmp/install_codedeploy.sh":
          source: https://aws-codedeploy-us-west-2.s3.us-west-2.amazonaws.com/latest/install
          mode: '000700'
          owner: root
          group: root
      commands:
        01_install_codedeploy:
          command: "/tmp/install_codedeploy.sh auto > /var/log/cfn-init-codedeploy.log 2>&1"
      services:
        sysvinit:
          codedeploy-agent:
            enabled: true
            ensure_running: true



.. _CodeDeployApplication:

.. list-table:: :guilabel:`CodeDeployApplication`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - compute_platform
      - String |star|
      - Compute Platform
      - Must be one of Lambda, Server or ECS
      - 
    * - deployment_groups
      - Container<CodeDeployDeploymentGroups_> |star|
      - CodeDeploy Deployment Groups
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


CodeDeployDeploymentGroups
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CodeDeployDeploymentGroups:

.. list-table:: :guilabel:`CodeDeployDeploymentGroups`
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


CodeDeployDeploymentGroup
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _CodeDeployDeploymentGroup:

.. list-table:: :guilabel:`CodeDeployDeploymentGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - autoscalinggroups
      - List<PacoReference>
      - AutoScalingGroups that CodeDeploy automatically deploys revisions to when new instances are created
      - Paco Reference to `ASG`_.
      - 
    * - ignore_application_stop_failures
      - Boolean
      - Ignore Application Stop Failures
      - 
      - 
    * - revision_location_s3
      - Object<DeploymentGroupS3Location_>
      - S3 Bucket revision location
      - 
      - 
    * - role_policies
      - List<Policy_>
      - Policies to grant the deployment group role
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_



DeploymentPipeline
-------------------


DeploymentPipeline creates AWS CodePipeline resources configured to act
as CI/CDs to deploy code and assets to application resources. DeploymentPipelines allow you
to express complex CI/CDs with minimal configuration.

A DeploymentPipeline has a number of Actions for three pre-defined Stages: source, build and deploy.
The currently supported list of actions for each stage is:

.. code-block:: yaml
    :caption: Current Actions available by Stage

    source:
      type: CodeCommit.Source
      type: ECR.Source
      type: GitHub.Source
    build:
      type: CodeBuild.Build
    deploy:
      type: CodeDeploy.Deploy
      type: ECS.Deploy
      type: ManualApproval

DeploymentPipelines can be configured to work cross-account and will automatically encrypt
the artifacts S3 Bucket with a KMS-CMK key that can only be accessed by the pipeline.
The ``configuration`` field lets you set the account that the DeploymentPipeline's CodePipeilne
resource will be created in and also specify the S3 Bucket to use for artifacts.

.. code-block:: yaml
    :caption: Configure a DeploymentPipeline to run in the tools account

    configuration:
      artifacts_bucket: paco.ref netenv.mynet.applications.myapp.groups.cicd.resources.artifacts
      account: paco.ref accounts.tools


DeploymentPipeline caveats - there are a few things to consider when creating pipelines:

  * You need to create an S3 Bucket that will be configured to for artifacts. Even pipelines
    which don't create artifacts will need this resource to hold ephemeral files created by CodePipeline.

  * A pipeline that deploys artifacts to an AutoScalingGroup will need the ``artifacts_bucket`` to
    allow the IAM Instance Role to read from the bucket.

  * A pipeline with an ``ECR.Source`` source must be in the same account as the ECR Repository.

  * A pipeline with an ``ECR.Source`` source must have at least one image alreaay created in it before
    it can be created.

  * A pipeline that is building Docker images needs to set ``privileged_mode: true``.

  * If you are using a manual approval step before deploying, pay attention to the
    ``run_order`` field. Normally you will want the approval action to happen before the deploy action.

.. code-block:: yaml
    :caption: Example S3 Bucket for a DeploymentPipeline that deploys to an AutoScalingGroup

    type: S3Bucket
    enabled: true
    order: 10
    bucket_name: "artifacts"
    deletion_policy: "delete"
    account: paco.ref accounts.tools
    versioning: true
    policy:
      - aws:
          - paco.sub '${paco.ref netenv.mynet.applications.myapp.groups.container.resources.asg.instance_iam_role.arn}'
        effect: 'Allow'
        action:
          - 's3:Get*'
          - 's3:List*'
        resource_suffix:
          - '/*'
          - ''

.. code-block:: yaml
    :caption: Example DeploymentPipeline to deploy to ECS when an ECR Repository is updated

    type: DeploymentPipeline
    order: 10
    enabled: true
    configuration:
      artifacts_bucket: paco.ref netenv.mynet.applications.myapp.groups.cicd.resources.artifacts
      account: paco.ref accounts.tools
    source:
      ecr:
        type: ECR.Source
        repository: paco.ref netenv.mynet.applications.myapp.groups.container.resources.ecr_example
        image_tag: latest
    deploy:
      ecs:
        type: ECS.Deploy
        cluster: paco.ref netenv.mynet.applications.myapp.groups.container.resources.ecs_cluster
        service: paco.ref netenv.mynet.applications.myapp.groups.container.resources.ecs_config.services.simple_app

.. code-block:: yaml
    :caption: Example DeploymentPipeline to pull from GitHub, build a Docker image and then deploy from an ECR Repo

    type: DeploymentPipeline
    order: 20
    enabled: true
    configuration:
      artifacts_bucket: paco.ref netenv.mynet.applications.myapp.groups.cicd.resources.artifacts
      account: paco.ref accounts.tools
    source:
      github:
        type: GitHub.Source
        deployment_branch_name: "prod"
        github_access_token: paco.ref netenv.mynet.secrets_manager.myapp.github.token
        github_owner: MyExample
        github_repository: MyExample-FrontEnd
        poll_for_source_changes: false
    build:
      codebuild:
        type: CodeBuild.Build
        deployment_environment: "prod"
        codebuild_image: 'aws/codebuild/standard:4.0'
        codebuild_compute_type: BUILD_GENERAL1_MEDIUM
        privileged_mode: true # To allow docker images to be built
        codecommit_repo_users:
          - paco.ref resource.codecommit.mygroup.myrepo.users.MyCodeCommitUser
        secrets:
          - paco.ref netenv.mynet.secrets_manager.myapp.github.ssh_private_key
        role_policies:
          - name: AmazonEC2ContainerRegistryPowerUser
            statement:
              - effect: Allow
                action:
                  - ecr:GetAuthorizationToken
                  - ecr:BatchCheckLayerAvailability
                  - ecr:GetDownloadUrlForLayer
                  - ecr:GetRepositoryPolicy
                  - ecr:DescribeRepositories
                  - ecr:ListImages
                  - ecr:DescribeImages
                  - ecr:BatchGetImage
                  - ecr:GetLifecyclePolicy
                  - ecr:GetLifecyclePolicyPreview
                  - ecr:ListTagsForResource
                  - ecr:DescribeImageScanFindings
                  - ecr:InitiateLayerUpload
                  - ecr:UploadLayerPart
                  - ecr:CompleteLayerUpload
                  - ecr:PutImage
                resource:
                  - '*'
    deploy:
      ecs:
        type: ECS.Deploy
        cluster: paco.ref netenv.mynet.applications.myapp.groups.container.resources.cluster
        service: paco.ref netenv.mynet.applications.myapp.groups.container.resources.services.services.frontend


.. code-block:: yaml
    :caption: Example DeploymentPipeline to pull from CodeCommit, build an app artifact and then deploy to an ASG using CodeDeploy

    type: DeploymentPipeline
    order: 30
    enabled: true
    configuration:
      artifacts_bucket: paco.ref netenv.mynet.applications.myapp.groups.cicd.resources.artifacts
      account: paco.ref accounts.tools
    source:
      codecommit:
        type: CodeCommit.Source
        codecommit_repository: paco.ref resource.codecommit.mygroup.myrepo
        deployment_branch_name: "prod"
    build:
      codebuild:
        type: CodeBuild.Build
        deployment_environment: "prod"
        codebuild_image: 'aws/codebuild/amazonlinux2-x86_64-standard:1.0'
        codebuild_compute_type: BUILD_GENERAL1_SMALL
    deploy:
      approval:
        type: ManualApproval
        run_order: 1
        manual_approval_notification_email:
          - bob@example.com
          - sally@example.com
      codedeploy:
        type: CodeDeploy.Deploy
        run_order: 2
        alb_target_group: paco.ref netenv.mynet.applications.myapp.groups.backend.resources.alb.target_groups.api
        auto_scaling_group: paco.ref netenv.mynet.applications.myapp.groups.backend.resources.api
        auto_rollback_enabled: true
        minimum_healthy_hosts:
          type: HOST_COUNT
          value: 0
        deploy_style_option: WITHOUT_TRAFFIC_CONTROL

    

.. _DeploymentPipeline:

.. list-table:: :guilabel:`DeploymentPipeline`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - build
      - Container<DeploymentPipelineBuildStage_>
      - Deployment Pipeline Build Stage
      - 
      - 
    * - configuration
      - Object<DeploymentPipelineConfiguration_>
      - Deployment Pipeline General Configuration
      - 
      - 
    * - deploy
      - Container<DeploymentPipelineDeployStage_>
      - Deployment Pipeline Deploy Stage
      - 
      - 
    * - source
      - Container<DeploymentPipelineSourceStage_>
      - Deployment Pipeline Source Stage
      - 
      - 
    * - stages
      - Container<CodePipelineStages_>
      - Stages
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


CodePipelineStages
^^^^^^^^^^^^^^^^^^^

Container for `CodePipelineStage`_ objects.

.. _CodePipelineStages:

.. list-table:: :guilabel:`CodePipelineStages` |bars| Container<`CodePipelineStage`_>
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


CodePipelineStage
^^^^^^^^^^^^^^^^^^

Container for different types of DeploymentPipelineStageAction objects.

.. _CodePipelineStage:

.. list-table:: :guilabel:`CodePipelineStage`
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


DeploymentPipelineSourceStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline source stage actions
    

.. _DeploymentPipelineSourceStage:

.. list-table:: :guilabel:`DeploymentPipelineSourceStage`
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


DeploymentPipelineDeployStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline deploy stage actions
    

.. _DeploymentPipelineDeployStage:

.. list-table:: :guilabel:`DeploymentPipelineDeployStage`
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


DeploymentPipelineBuildStage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


A map of DeploymentPipeline build stage actions
    

.. _DeploymentPipelineBuildStage:

.. list-table:: :guilabel:`DeploymentPipelineBuildStage`
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


DeploymentPipelineDeployCodeDeploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeDeploy DeploymentPipeline Deploy Stage
    

.. _DeploymentPipelineDeployCodeDeploy:

.. list-table:: :guilabel:`DeploymentPipelineDeployCodeDeploy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - alb_target_group
      - PacoReference
      - ALB Target Group Reference
      - Paco Reference to `TargetGroup`_.
      - 
    * - auto_rollback_enabled
      - Boolean |star|
      - Automatic rollback enabled
      - 
      - True
    * - auto_scaling_group
      - PacoReference
      - ASG Reference
      - Paco Reference to `ASG`_.
      - 
    * - deploy_instance_role
      - PacoReference
      - Deploy Instance Role Reference
      - Paco Reference to `Role`_.
      - 
    * - deploy_style_option
      - String
      - Deploy Style Option
      - 
      - WITH_TRAFFIC_CONTROL
    * - elb_name
      - String
      - ELB Name
      - 
      - 
    * - minimum_healthy_hosts
      - Object<CodeDeployMinimumHealthyHosts_>
      - The minimum number of healthy instances that should be available at any time during the deployment.
      - 
      - 

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineSourceECR
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Amazon ECR DeploymentPipeline Source Stage

This Action is triggered whenever a new image is pushed to an Amazon ECR repository.

.. code-block:: yaml

  pipeline:
    type: DeploymentPipeline
    stages:
      source:
        ecr:
          type: ECR.Source
          enabled: true
          repository:  paco.ref netenv.mynet.applications.myapp.groups.ecr.resources.myecr
          image_tag: "latest"

    

.. _DeploymentPipelineSourceECR:

.. list-table:: :guilabel:`DeploymentPipelineSourceECR`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - image_tag
      - String
      - The name of the tag used for the image.
      - 
      - latest
    * - repository
      - PacoReference|String |star|
      - An ECRRepository ref or the name of the an ECR repository.
      - String Ok.
      - 

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


CodeDeployMinimumHealthyHosts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeDeploy Minimum Healthy Hosts
    

.. _CodeDeployMinimumHealthyHosts:

.. list-table:: :guilabel:`CodeDeployMinimumHealthyHosts`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - type
      - String
      - Deploy Config Type
      - 
      - HOST_COUNT
    * - value
      - Int
      - Deploy Config Value
      - 
      - 0

*Base Schemas* `Named`_, `Title`_


DeploymentPipelineManualApproval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


ManualApproval DeploymentPipeline
    

.. _DeploymentPipelineManualApproval:

.. list-table:: :guilabel:`DeploymentPipelineManualApproval`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - manual_approval_notification_email
      - List<String>
      - Manual Approval Notification Email List
      - 
      - 

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineDeployS3
^^^^^^^^^^^^^^^^^^^^^^^^^^^


Amazon S3 Deployment Provider
    

.. _DeploymentPipelineDeployS3:

.. list-table:: :guilabel:`DeploymentPipelineDeployS3`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference
      - S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 
    * - extract
      - Boolean
      - Boolean indicating whether the deployment artifact will be unarchived.
      - 
      - True
    * - input_artifacts
      - List<String>
      - Input Artifacts
      - 
      - 
    * - object_key
      - String
      - S3 object key to store the deployment artifact as.
      - 
      - 

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineBuildCodeBuild
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeBuild DeploymentPipeline Build Stage
    

.. _DeploymentPipelineBuildCodeBuild:

.. list-table:: :guilabel:`DeploymentPipelineBuildCodeBuild`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - buildspec
      - String
      - buildspec.yml filename
      - 
      - 
    * - codebuild_compute_type
      - String
      - CodeBuild Compute Type
      - 
      - 
    * - codebuild_image
      - String
      - CodeBuild Docker Image
      - 
      - 
    * - codecommit_repo_users
      - List<PacoReference>
      - CodeCommit Users
      - Paco Reference to `CodeCommitUser`_.
      - 
    * - deployment_environment
      - String
      - Deployment Environment
      - 
      - 
    * - privileged_mode
      - Boolean
      - Privileged Mode
      - 
      - False
    * - role_policies
      - List<Policy_>
      - Project IAM Role Policies
      - 
      - 
    * - secrets
      - List<PacoReference>
      - List of PacoReferences to Secrets Manager secrets
      - 
      - 
    * - timeout_mins
      - Int
      - Timeout in Minutes
      - 
      - 60

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineSourceCodeCommit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


CodeCommit DeploymentPipeline Source Stage
    

.. _DeploymentPipelineSourceCodeCommit:

.. list-table:: :guilabel:`DeploymentPipelineSourceCodeCommit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - codecommit_repository
      - PacoReference
      - CodeCommit Respository
      - Paco Reference to `CodeCommitRepository`_.
      - 
    * - deployment_branch_name
      - String
      - Deployment Branch Name
      - 
      - 

*Base Schemas* `Enablable`_, `Named`_, `DeploymentPipelineStageAction`_, `Title`_


DeploymentPipelineStageAction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Deployment Pipeline Source Stage
    

.. _DeploymentPipelineStageAction:

.. list-table:: :guilabel:`DeploymentPipelineStageAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - run_order
      - Int
      - The order in which to run this stage
      - 
      - 1
    * - type
      - String
      - The type of DeploymentPipeline Source Stage
      - 
      - 

*Base Schemas* `Enablable`_, `Named`_, `Title`_


DeploymentPipelineConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Deployment Pipeline General Configuration
    

.. _DeploymentPipelineConfiguration:

.. list-table:: :guilabel:`DeploymentPipelineConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - The account where Pipeline tools will be provisioned.
      - Paco Reference to `Account`_.
      - 
    * - artifacts_bucket
      - PacoReference
      - Artifacts S3 Bucket Reference
      - Paco Reference to `S3Bucket`_.
      - 

*Base Schemas* `Named`_, `Title`_


DeploymentGroupS3Location
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _DeploymentGroupS3Location:

.. list-table:: :guilabel:`DeploymentGroupS3Location`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference
      - S3 Bucket revision location
      - Paco Reference to `S3Bucket`_.
      - 
    * - bundle_type
      - String
      - Bundle Type
      - Must be one of JSON, tar, tgz, YAML or zip.
      - 
    * - key
      - String |star|
      - The name of the Amazon S3 object that represents the bundled artifacts for the application revision.
      - 
      - 




EBS
----


Elastic Block Store (EBS) Volume.

It is required to specify the ``availability_zone`` the EBS Volume will be created in.
If the volume is going to be used by an ASG, it should launch an instance in the same
``availability_zone`` (and region).

.. code-block:: yaml
    :caption: Example EBS resource YAML

    type: EBS
    order: 5
    enabled: true
    size_gib: 4
    volume_type: gp2
    availability_zone: 1

    

.. _EBS:

.. list-table:: :guilabel:`EBS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - availability_zone
      - Int |star|
      - Availability Zone to create Volume in.
      - 
      - 
    * - size_gib
      - Int
      - Volume Size in GiB
      - 
      - 10
    * - snapshot_id
      - String
      - Snapshot ID
      - 
      - 
    * - volume_type
      - String
      - Volume Type
      - Must be one of: gp2 | io1 | sc1 | st1 | standard
      - gp2

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



EC2
----


EC2 Instance
    

.. _EC2:

.. list-table:: :guilabel:`EC2`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - associate_public_ip_address
      - Boolean
      - Associate Public IP Address
      - 
      - False
    * - disable_api_termination
      - Boolean
      - Disable API Termination
      - 
      - False
    * - instance_ami
      - String
      - Instance AMI
      - 
      - 
    * - instance_key_pair
      - PacoReference
      - key pair for connections to instance
      - Paco Reference to `EC2KeyPair`_.
      - 
    * - instance_type
      - String
      - Instance type
      - 
      - 
    * - private_ip_address
      - String
      - Private IP Address
      - 
      - 
    * - root_volume_size_gb
      - Int
      - Root volume size GB
      - 
      - 8
    * - security_groups
      - List<PacoReference>
      - Security groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 
    * - user_data_script
      - String
      - User data script
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



ECRRepository
--------------


Elastic Container Registry (ECR) Repository is a fully-managed Docker container registry.


.. sidebar:: Prescribed Automation

    ``cross_account_access``: Adds a Repository Policy that grants full access to the listed AWS Accounts.

.. code-block:: yaml
    :caption: Example ECRRepository

    type: ECRRepository
    enabled: true
    order: 10
    repository_name: 'ecr-example'
    cross_account_access:
      - paco.ref accounts.dev
      - paco.ref accounts.tools



.. _ECRRepository:

.. list-table:: :guilabel:`ECRRepository`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - Account the ECR Repository belongs to
      - Paco Reference to `Account`_.
      - 
    * - cross_account_access
      - List<PacoReference>
      - Accounts to grant access to this ECR.
      - Paco Reference to `Account`_.
      - 
    * - lifecycle_policy_registry_id
      - String
      - Lifecycle Policy Registry Id
      - 
      - 
    * - lifecycle_policy_text
      - String
      - Lifecycle Policy
      - 
      - 
    * - repository_name
      - String |star|
      - Repository Name
      - 
      - 
    * - repository_policy
      - Object<Policy_>
      - Repository Policy
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



ECSCluster
-----------


ECS Cluster
    

.. _ECSCluster:

.. list-table:: :guilabel:`ECSCluster`
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

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



ECSService
-----------

ECS Service

.. _ECSService:

.. list-table:: :guilabel:`ECSService`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - deployment_controller
      - Choice
      - Deployment Controller
      - One of ecs, code_deploy or external
      - ecs
    * - deployment_maximum_percent
      - Int
      - Deployment Maximum Percent
      - 
      - 200
    * - deployment_minimum_healthy_percent
      - Int
      - Deployment Minimum Healthy Percent
      - 
      - 100
    * - desired_count
      - Int
      - Desried Count
      - 
      - 
    * - health_check_grace_period_seconds
      - Int
      - Health Check Grace Period (seconds)
      - 
      - 0
    * - hostname
      - String
      - Container hostname
      - 
      - 
    * - load_balancers
      - List<ECSLoadBalancer_>
      - Load Balancers
      - 
      - []
    * - task_definition
      - String
      - Task Definition
      - 
      - 

*Base Schemas* `Named`_, `Title`_


ECSServicesContainer
^^^^^^^^^^^^^^^^^^^^^

Container for `ECSService`_ objects.
    * -
      -
      -
      -
      -



ECSTaskDefinitions
^^^^^^^^^^^^^^^^^^^

Container for `ECSTaskDefinition`_ objects.

.. _ECSTaskDefinitions:

.. list-table:: :guilabel:`ECSTaskDefinitions` |bars| Container<`ECSTaskDefinition`_>
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


ECSTaskDefinition
^^^^^^^^^^^^^^^^^^

ECS Task Definition

.. _ECSTaskDefinition:

.. list-table:: :guilabel:`ECSTaskDefinition`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - container_definitions
      - Container<ECSContainerDefinitions_> |star|
      - Container Definitions
      - 
      - 
    * - network_mode
      - Choice
      - Network Mode
      - Must be one of awsvpc, bridge, host or none
      - bridge
    * - volumes
      - List<ECSVolume_>
      - Volume definitions for the task
      - 
      - []

*Base Schemas* `Named`_, `Title`_


ECSContainerDefinitions
^^^^^^^^^^^^^^^^^^^^^^^^

Container for `ECSContainerDefinition`_ objects.

.. _ECSContainerDefinitions:

.. list-table:: :guilabel:`ECSContainerDefinitions` |bars| Container<`ECSContainerDefinition`_>
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


ECSContainerDefinition
^^^^^^^^^^^^^^^^^^^^^^^

ECS Container Definition

.. _ECSContainerDefinition:

.. list-table:: :guilabel:`ECSContainerDefinition`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - command
      - List<String>
      - Command (Docker CMD)
      - List of strings
      - 
    * - cpu
      - Int
      - Cpu units
      - 
      - 
    * - depends_on
      - List<ECSContainerDependency_>
      - Depends On
      - List of ECS Container Dependencies
      - []
    * - disable_networking
      - Boolean
      - Disable Networking
      - 
      - False
    * - dns_search_domains
      - List<String>
      - List of DNS search domains. Maps to 'DnsSearch' in Docker.
      - 
      - []
    * - dns_servers
      - List<String>
      - List of DNS servers. Maps to 'Dns' in Docker.
      - 
      - []
    * - docker_labels
      - Container<DockerLabels_>
      - A key/value map of labels. Maps to 'Labels' in Docker.
      - 
      - 
    * - docker_security_options
      - Choice
      - List of custom labels for SELinux and AppArmor multi-level security systems.
      - Must be a list of no-new-privileges, apparmor:PROFILE, label:value, or credentialspec:CredentialSpecFilePath
      - []
    * - entry_point
      - List<String>
      - Entry Pont (Docker ENTRYPOINT)
      - List of strings
      - 
    * - environment
      - List<NameValuePair_>
      - List of environment name value pairs.
      - 
      - 
    * - essential
      - Boolean
      - Essential
      - 
      - False
    * - extra_hosts
      - List<ECSHostEntry_>
      - List of hostnames and IP address mappings to append to the /etc/hosts file on the container.
      - 
      - []
    * - health_check
      - Object<ECSHealthCheck_>
      - The container health check command and associated configuration parameters for the container. This parameter maps to 'HealthCheck' in Docker.
      - 
      - 
    * - hostname
      - String
      - Hostname to use for your container. This parameter maps to 'Hostname' in Docker.
      - 
      - 
    * - image
      - PacoReference|String |star|
      - The image used to start a container. This string is passed directly to the Docker daemon.
      - If a paco.ref is used to ECR, then the image_tag field will provide that tag used. Paco Reference to `ECRRepository`_. String Ok.
      - 
    * - image_tag
      - String
      - Tag used for the ECR Repository Image
      - 
      - latest
    * - interactive
      - Boolean
      - When this parameter is true, this allows you to deploy containerized applications that require stdin or a tty to be allocated. This parameter maps to 'OpenStdin' in Docker.
      - 
      - 
    * - logging
      - Object<ECSLogging_>
      - Logging Configuration
      - 
      - 
    * - memory
      - Int
      - The amount (in MiB) of memory to present to the container. If your container attempts to exceed the memory specified here, the container is killed.
      - 
      - 
    * - memory_reservation
      - Int
      - The soft limit (in MiB) of memory to reserve for the container. When system memory is under heavy contention, Docker attempts to keep the container memory to this soft limit.
      - 
      - 
    * - mount_points
      - List<ECSMountPoint_>
      - The mount points for data volumes in your container.
      - 
      - 
    * - port_mappings
      - List<PortMapping_>
      - Port Mappings
      - 
      - []
    * - privileged
      - Boolean
      - Give the container elevated privileges on the host container instance (similar to the root user).
      - 
      - False
    * - pseudo_terminal
      - Boolean
      - Allocate a TTY. This parameter maps to 'Tty' in Docker.
      - 
      - 
    * - readonly_root_filesystem
      - Boolean
      - Read-only access to its root file system. This parameter maps to 'ReadonlyRootfs' in Docker.
      - 
      - 
    * - secrets
      - List<ECSTaskDefinitionSecret_>
      - List of name, value_from pairs to secret manager Paco references.
      - 
      - 
    * - start_timeout
      - Int
      - Time duration (in seconds) to wait before giving up on resolving dependencies for a container.
      - 
      - 300
    * - stop_timeout
      - Int
      - Time duration (in seconds) to wait before the container is forcefully killed if it doesn't exit normally on its own.
      - 
      - 30
    * - ulimits
      - List<ECSUlimit_>
      - List of ulimits to set in the container. This parameter maps to 'Ulimits' in Docker
      - 
      - []
    * - user
      - String
      - The user name to use inside the container. This parameter maps to 'User' in Docker.
      - 
      - 
    * - volumes_from
      - List<ECSVolumesFrom_>
      - Volumes to mount from another container (Docker VolumesFrom).
      - 
      - []
    * - working_directory
      - String
      - The working directory in which to run commands inside the container. This parameter maps to 'WorkingDir' in Docker.
      - 
      - 

*Base Schemas* `Named`_, `Title`_


ECSLoadBalancer
^^^^^^^^^^^^^^^^

ECS Load Balancer

.. _ECSLoadBalancer:

.. list-table:: :guilabel:`ECSLoadBalancer`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - container_name
      - String |star|
      - Container Name
      - 
      - 
    * - container_port
      - Int |star|
      - Container Port
      - 
      - 
    * - target_group
      - PacoReference |star|
      - Target Group
      - Paco Reference to `TargetGroup`_.
      - 

*Base Schemas* `Named`_, `Title`_


ECSVolume
^^^^^^^^^^

ECS Volume

.. _ECSVolume:

.. list-table:: :guilabel:`ECSVolume`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String |star|
      - Name
      - 
      - 



ECSUlimit
^^^^^^^^^^

ECS Ulimit

.. _ECSUlimit:

.. list-table:: :guilabel:`ECSUlimit`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - hard_limit
      - Int |star|
      - The hard limit for the ulimit type.
      - 
      - 
    * - name
      - Choice |star|
      - The type of the ulimit
      - 
      - 
    * - soft_limit
      - Int |star|
      - The soft limit for the ulimit type.
      - 
      - 



ECSHealthCheck
^^^^^^^^^^^^^^^

ECS Health Check

.. _ECSHealthCheck:

.. list-table:: :guilabel:`ECSHealthCheck`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - command
      - List<String> |star|
      - A string array representing the command that the container runs to determine if it is healthy. The string array must start with CMD to execute the command arguments directly, or CMD-SHELL to run the command with the container's default shell.
      - 
      - 
    * - interval
      - Int
      - The time period in seconds between each health check execution.
      - 
      - 30
    * - retries
      - Int
      - Retries
      - 
      - 3
    * - start_period
      - Int
      - The optional grace period within which to provide containers time to bootstrap before failed health checks count towards the maximum number of retries.
      - 
      - 
    * - timeout
      - Int
      - The time period in seconds to wait for a health check to succeed before it is considered a failure.
      - 
      - 5

*Base Schemas* `Named`_, `Title`_


ECSHostEntry
^^^^^^^^^^^^^

ECS Host Entry

.. _ECSHostEntry:

.. list-table:: :guilabel:`ECSHostEntry`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - hostname
      - String |star|
      - Hostname
      - 
      - 
    * - ip_address
      - String |star|
      - IP Address
      - 
      - 



DockerLabels
^^^^^^^^^^^^^



.. _DockerLabels:

.. list-table:: :guilabel:`DockerLabels`
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


ECSContainerDependency
^^^^^^^^^^^^^^^^^^^^^^^

ECS Container Dependency

.. _ECSContainerDependency:

.. list-table:: :guilabel:`ECSContainerDependency`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - condition
      - Choice |star|
      - Condition
      - Must be one of COMPLETE, HEALTHY, START or SUCCESS
      - 
    * - container_name
      - String |star|
      - Container Name
      - Must be an existing container name.
      - 



ECSTaskDefinitionSecret
^^^^^^^^^^^^^^^^^^^^^^^^

A Name/ValueFrom pair of Paco references to Secrets Manager secrets

.. _ECSTaskDefinitionSecret:

.. list-table:: :guilabel:`ECSTaskDefinitionSecret`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String |star|
      - Name
      - 
      - 
    * - value_from
      - PacoReference|String |star|
      - Paco reference to Secrets manager
      - String Ok.
      - 



ECSLogging
^^^^^^^^^^^

ECS Logging Configuration

.. _ECSLogging:

.. list-table:: :guilabel:`ECSLogging`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - driver
      - Choice |star|
      - Log Driver
      - One of awsfirelens, awslogs, fluentd, gelf, journald, json-file, splunk, syslog
      - 

*Base Schemas* `CloudWatchLogRetention`_, `Named`_, `Title`_


ECSVolumesFrom
^^^^^^^^^^^^^^^

VoumesFrom

.. _ECSVolumesFrom:

.. list-table:: :guilabel:`ECSVolumesFrom`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - read_only
      - Boolean
      - Read Only
      - 
      - False
    * - source_container
      - String |star|
      - The name of another container within the same task definition from which to mount volumes.
      - 
      - 



ECSMountPoint
^^^^^^^^^^^^^^

ECS TaskDefinition Mount Point

.. _ECSMountPoint:

.. list-table:: :guilabel:`ECSMountPoint`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - container_path
      - String
      - The path on the container to mount the host volume at.
      - 
      - 
    * - read_only
      - Boolean
      - Read Only
      - 
      - False
    * - source_volume
      - String
      - The name of the volume to mount.
      - Must be a volume name referenced in the name parameter of task definition volume.
      - 



PortMapping
^^^^^^^^^^^^

Port Mapping

.. _PortMapping:

.. list-table:: :guilabel:`PortMapping`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - container_port
      - Int
      - Container Port
      - 
      - 
    * - host_port
      - Int
      - Host Port
      - 
      - 
    * - protocol
      - Choice |star|
      - Protocol
      - Must be either 'tcp' or 'udp'
      - tcp




EIP
----


Elastic IP (EIP) resource.

.. sidebar:: Prescribed Automation

    ``dns``: Adds a DNS CNAME to resolve to this EIP's IP address to the Route 53 HostedZone.

.. code-block:: yaml
    :caption: Example EIP resource YAML

    type: EIP
    order: 5
    enabled: true
    dns:
      - domain_name: example.com
        hosted_zone: paco.ref resource.route53.examplecom
        ttl: 60



.. _EIP:

.. list-table:: :guilabel:`EIP`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dns
      - List<DNS_>
      - List of DNS for the EIP
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



EFS
----


AWS Elastic File System (EFS) resource.

.. code-block:: yaml
    :caption: Example EFS resource

    type: EFS
    order: 20
    enabled: true
    encrypted: false
    segment: private
    security_groups:
      - paco.ref netenv.mynet.network.vpc.security_groups.cloud.content

    

.. _EFS:

.. list-table:: :guilabel:`EFS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - encrypted
      - Boolean |star|
      - Encryption at Rest
      - 
      - False
    * - security_groups
      - List<PacoReference> |star|
      - Security groups
      - `SecurityGroup`_ the EFS belongs to Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



ElastiCache
------------


Base ElastiCache Interface
    

.. _ElastiCache:

.. list-table:: :guilabel:`ElastiCache`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - at_rest_encryption
      - Boolean
      - Enable encryption at rest
      - 
      - 
    * - auto_minor_version_upgrade
      - Boolean
      - Enable automatic minor version upgrades
      - 
      - 
    * - automatic_failover_enabled
      - Boolean
      - Specifies whether a read-only replica is automatically promoted to read/write primary if the existing primary fails
      - 
      - 
    * - az_mode
      - String
      - AZ mode
      - 
      - 
    * - cache_clusters
      - Int
      - Number of Cache Clusters
      - 
      - 
    * - cache_node_type
      - String
      - Cache Node Instance type
      - 
      - 
    * - description
      - String
      - Replication Description
      - 
      - 
    * - engine
      - String
      - ElastiCache Engine
      - 
      - 
    * - engine_version
      - String
      - ElastiCache Engine Version
      - 
      - 
    * - maintenance_preferred_window
      - String
      - Preferred maintenance window
      - 
      - 
    * - number_of_read_replicas
      - Int
      - Number of read replicas
      - 
      - 
    * - parameter_group
      - PacoReference|String
      - Parameter Group name
      - Paco Reference to `Interface`_. String Ok.
      - 
    * - port
      - Int
      - Port
      - 
      - 
    * - security_groups
      - List<PacoReference>
      - List of Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - PacoReference
      - Segment
      - Paco Reference to `Segment`_.
      - 



ElastiCacheRedis
^^^^^^^^^^^^^^^^^


Redis ElastiCache Interface
    

.. _ElastiCacheRedis:

.. list-table:: :guilabel:`ElastiCacheRedis`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cache_parameter_group_family
      - String
      - Cache Parameter Group Family
      - 
      - 
    * - snapshot_retention_limit_days
      - Int
      - Snapshot Retention Limit in Days
      - 
      - 
    * - snapshot_window
      - String
      - The daily time range (in UTC) during which ElastiCache begins taking a daily snapshot of your node group (shard).
      - 
      - 

*Base Schemas* `ElastiCache`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_



ElasticsearchDomain
--------------------


Amazon Elasticsearch Service (Amazon ES) is a managed service for Elasticsearch clusters.
An Amazon ES domain is synonymous with an Elasticsearch cluster. Domains are clusters with the
settings, instance types, instance counts, and storage resources that you specify.

.. sidebar:: Prescribed Automation

    ``segment``: Including the segment will place the Elasticsearch cluster within the Availability
    Zones for that segment. If an Elasticsearch ServiceLinkedRole is not already provisioned for that
    account and region, Paco will create it for you. This role is used by AWS to place the Elasticsearch
    cluster within the subnets that belong that segment and VPC.

    If segment is not set, then you will have a public Elasticsearch cluster with an endpoint.

.. code-block:: yaml
    :caption: example Elasticsearch configuration

    type: ElasticsearchDomain
    order: 10
    title: "Elasticsearch Domain"
    enabled: true
    access_policies_json: ./es-config/es-access.json
    advanced_options:
      indices.fielddata.cache.size: ""
      rest.action.multi.allow_explicit_index: "true"
    cluster:
      instance_count: 2
      zone_awareness_enabled: false
      instance_type: "t2.micro.elasticsearch"
      dedicated_master_enabled: true
      dedicated_master_type: "t2.micro.elasticsearch"
      dedicated_master_count: 2
    ebs_volumes:
      enabled: true
      iops: 0
      volume_size_gb: 10
      volume_type: 'gp2'
    segment: web
    security_groups:
      - paco.ref netenv.mynet.network.vpc.security_groups.app.search

    

.. _ElasticsearchDomain:

.. list-table:: :guilabel:`ElasticsearchDomain`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - access_policies_json
      - StringFileReference
      - Policy document that specifies who can access the Amazon ES domain and their permissions.
      - 
      - 
    * - advanced_options
      - Container<ESAdvancedOptions_>
      - Advanced Options
      - 
      - 
    * - cluster
      - Object<ElasticsearchCluster_>
      - Elasticsearch Cluster configuration
      - 
      - 
    * - ebs_volumes
      - Object<EBSOptions_>
      - EBS volumes that are attached to data nodes in the Amazon ES domain.
      - 
      - 
    * - elasticsearch_version
      - String
      - The version of Elasticsearch to use, such as 2.3.
      - 
      - 1.5
    * - node_to_node_encryption
      - Boolean
      - Enable node-to-node encryption
      - 
      - 
    * - security_groups
      - List<PacoReference>
      - List of Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Segment
      - 
      - 
    * - snapshot_start_hour
      - Int
      - The hour in UTC during which the service takes an automated daily snapshot of the indices in the Amazon ES domain.
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


ElasticsearchCluster
^^^^^^^^^^^^^^^^^^^^^



.. _ElasticsearchCluster:

.. list-table:: :guilabel:`ElasticsearchCluster`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - dedicated_master_count
      - Int
      - The number of instances to use for the master node.
      - If you specify this field, you must specify true for the dedicated_master_enabled field.
      - 
    * - dedicated_master_enabled
      - Boolean
      - Indicates whether to use a dedicated master node for the Amazon ES domain.
      - 
      - 
    * - dedicated_master_type
      - String
      - The hardware configuration of the computer that hosts the dedicated master node
      - Valid Elasticsearch instance type, such as m3.medium.elasticsearch. See https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/aes-supported-instance-types.html
      - 
    * - instance_count
      - Int
      - The number of data nodes (instances) to use in the Amazon ES domain.
      - 
      - 
    * - instance_type
      - String
      - The instance type for your data nodes.
      - Valid Elasticsearch instance type, such as m3.medium.elasticsearch. See https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/aes-supported-instance-types.html
      - 
    * - zone_awareness_availability_zone_count
      - Int
      - If you enabled multiple Availability Zones (AZs), the number of AZs that you want the domain to use.
      - 
      - 2
    * - zone_awareness_enabled
      - Boolean
      - Enable zone awareness for the Amazon ES domain.
      - 
      - 



EBSOptions
^^^^^^^^^^^



.. _EBSOptions:

.. list-table:: :guilabel:`EBSOptions`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - enabled
      - Boolean
      - Specifies whether Amazon EBS volumes are attached to data nodes in the Amazon ES domain.
      - 
      - 
    * - iops
      - Int
      - The number of I/O operations per second (IOPS) that the volume supports.
      - 
      - 
    * - volume_size_gb
      - Int
      - The size (in GiB) of the EBS volume for each data node.
      - The minimum and maximum size of an EBS volume depends on the EBS volume type and the instance type to which it is attached.
      - 
    * - volume_type
      - String
      - The EBS volume type to use with the Amazon ES domain.
      - Must be one of: standard, gp2, io1, st1, or sc1
      - 


ESAdvancedOptions
^^^^^^^^^^^^^^^^^

An unconstrainted set of key-value pairs used to set advanced options for Elasticsearch.



EventsRule
-----------


Events Rule resources match incoming or scheduled events and route them to target using Amazon EventBridge.

.. sidebar:: Prescribed Automation

    ``targets``: If the ``target`` is a Lambda, an IAM Role will be created that is granted permission to invoke it by this EventRule.

.. code-block:: yaml
    :caption: Lambda function resource YAML

    type: EventsRule
    enabled: true
    order: 10
    description: Invoke a Lambda every other minute
    schedule_expression: "cron(*/2 * * * ? *)"
    targets:
        - target: paco.ref netenv.mynet.applications.myapp.groups.mygroup.resources.mylambda

    

.. _EventsRule:

.. list-table:: :guilabel:`EventsRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - description
      - String
      - Description
      - 
      - 
    * - enabled_state
      - Boolean
      - Enabled State
      - 
      - True
    * - schedule_expression
      - String |star|
      - Schedule Expression
      - 
      - 
    * - targets
      - List<EventTarget_> |star|
      - The AWS Resources that are invoked when the Rule is triggered.
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


EventTarget
^^^^^^^^^^^^



.. _EventTarget:

.. list-table:: :guilabel:`EventTarget`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - input_json
      - String
      - Valid JSON passed as input to the target.
      - 
      - 
    * - target
      - PacoReference |star|
      - Paco Reference to an AWS Resource to invoke
      - Paco Reference to `Interface`_.
      - 

*Base Schemas* `Named`_, `Title`_


Lambda
-------


Lambda Functions allow you to run code without provisioning servers and only
pay for the compute time when the code is running.

The code for the Lambda function can be specified in one of three ways in the ``code:`` field:

 * S3 Bucket artifact: Supply an``s3_bucket`` and ``s3_key`` where you have an existing code artifact file.

 * Local file: Supply the ``zipfile`` as a path to a local file on disk. This will be inlined into
   CloudFormation and has a size limitation of only 4 Kb.

 * Local directory: Supply the ``zipfile`` as a path to a directory on disk. This directory will be packaged
   into a zip file and Paco will create an S3 Bucket where it will upload and manage Lambda deployment artifacts.

.. code-block:: yaml
    :caption: Lambda code from S3 Bucket or local disk

    code:
        s3_bucket: my-bucket-name
        s3_key: 'myapp-1.0.zip'

    code:
        zipfile: ./lambda-dir/my-lambda.py

    code:
        zipfile: ~/code/my-app/lambda_target/

.. sidebar:: Prescribed Automation

    ``expire_events_after_days``: Sets the Retention for the Lambda execution Log Group.

    ``log_group_names``: Creates CloudWatch Log Group(s) prefixed with '<env>-<appname>-<groupname>-<lambdaname>-'
    (or for Environment-less applications like Services it will be '<appname>-<groupname>-<lambdaname>-')
    and grants permission for the Lambda role to interact with those Log Group(s). The ``expire_events_after_days``
    field will set the Log Group retention period. Paco will also add a comma-seperated Environment Variable
    named PACO_LOG_GROUPS to the Lambda with the expanded names of the Log Groups.

    ``sdb_cache``: Create a SimpleDB Domain and IAM Policy that grants full access to that domain. Will
    also make the domain available to the Lambda function as an environment variable named ``SDB_CACHE_DOMAIN``.

    ``sns_topics``: Subscribes the Lambda to SNS Topics. For each Paco reference to an SNS Topic,
    Paco will create an SNS Topic Subscription so that the Lambda function will recieve all messages sent to that SNS Topic.
    It will also create a Lambda Permission granting that SNS Topic the ability to publish to the Lambda.

    **Lambda Permissions** Paco will check all resources in the Application for any: S3Bucket configured
    to notify this Lambda, EventsRule to invoke this Lambda, IoTAnalyticsPipeline activities to invoke this Lambda.
    These resources will automatically gain a Lambda Permission to be able to invoke the Lambda.

.. code-block:: yaml
    :caption: Lambda function resource YAML

    type: Lambda
    enabled: true
    order: 1
    title: 'My Lambda Application'
    description: 'Checks the Widgets Service and applies updates to a Route 53 Record Set.'
    code:
        s3_bucket: my-bucket-name
        s3_key: 'myapp-1.0.zip'
    environment:
        variables:
        - key: 'VAR_ONE'
          value: 'hey now!'
        - key: 'VAR_TWO'
          value: 'Hank Kingsley'
    iam_role:
        enabled: true
        policies:
          - name: DNSRecordSet
            statement:
              - effect: Allow
                action:
                  - route53:ChangeResourceRecordSets
                resource:
                  - 'arn:aws:route53:::hostedzone/AJKDU9834DUY934'
    handler: 'myapp.lambda_handler'
    memory_size: 128
    runtime: 'python3.7'
    timeout: 900
    expire_events_after_days: 90
    log_group_names:
      - AppGroupOne
    sns_topics:
      - paco.ref netenv.app.applications.app.groups.web.resources.snstopic
    vpc_config:
        segments:
          - paco.ref netenv.app.network.vpc.segments.public
        security_groups:
          - paco.ref netenv.app.network.vpc.security_groups.app.function



.. _Lambda:

.. list-table:: :guilabel:`Lambda`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - code
      - Object<LambdaFunctionCode_> |star|
      - The function deployment package.
      - 
      - 
    * - description
      - String |star|
      - A description of the function.
      - 
      - 
    * - environment
      - Object<LambdaEnvironment_>
      - Lambda Function Environment
      - 
      - 
    * - handler
      - String |star|
      - Function Handler
      - 
      - 
    * - iam_role
      - Object<Role_> |star|
      - The IAM Role this Lambda will execute as.
      - 
      - 
    * - layers
      - List<String> |star|
      - Layers
      - Up to 5 Layer ARNs
      - 
    * - log_group_names
      - List<String>
      - Log Group names
      - List of Log Group names
      - []
    * - memory_size
      - Int
      - Function memory size (MB)
      - 
      - 128
    * - reserved_concurrent_executions
      - Int
      - Reserved Concurrent Executions
      - 
      - 0
    * - runtime
      - String |star|
      - Runtime environment
      - 
      - python3.7
    * - sdb_cache
      - Boolean
      - SDB Cache Domain
      - 
      - False
    * - sns_topics
      - List<PacoReference>
      - List of SNS Topic Paco references or SNS Topic ARNs to subscribe the Lambda to.
      - Paco Reference to `SNSTopic`_. String Ok.
      - 
    * - timeout
      - Int
      - Max function execution time in seconds.
      - Must be between 0 and 900 seconds.
      - 
    * - vpc_config
      - Object<LambdaVpcConfig_>
      - Vpc Configuration
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `CloudWatchLogRetention`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


LambdaFunctionCode
^^^^^^^^^^^^^^^^^^^

The deployment package for a Lambda function.

.. _LambdaFunctionCode:

.. list-table:: :guilabel:`LambdaFunctionCode`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - s3_bucket
      - PacoReference|String
      - An Amazon S3 bucket in the same AWS Region as your function
      - Paco Reference to `S3Bucket`_. String Ok.
      - 
    * - s3_key
      - String
      - The Amazon S3 key of the deployment package.
      - 
      - 
    * - zipfile
      - LocalPath
      - The function code as a local file or directory.
      - Maximum of 4096 characters.
      - 



LambdaEnvironment
^^^^^^^^^^^^^^^^^^


Lambda Environment
    

.. _LambdaEnvironment:

.. list-table:: :guilabel:`LambdaEnvironment`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - variables
      - List<LambdaVariable_>
      - Lambda Function Variables
      - 
      - 



LambdaVpcConfig
^^^^^^^^^^^^^^^^


Lambda Environment
    

.. _LambdaVpcConfig:

.. list-table:: :guilabel:`LambdaVpcConfig`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - security_groups
      - List<PacoReference>
      - List of VPC Security Group Ids
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segments
      - List<PacoReference>
      - VPC Segments to attach the function
      - Paco Reference to `Segment`_.
      - 

*Base Schemas* `Named`_, `Title`_


LambdaVariable
^^^^^^^^^^^^^^^


    Lambda Environment Variable
    

.. _LambdaVariable:

.. list-table:: :guilabel:`LambdaVariable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - key
      - String |star|
      - Variable Name
      - 
      - 
    * - value
      - PacoReference|String |star|
      - String Value or a Paco Reference to a resource output
      - Paco Reference to `Interface`_. String Ok.
      - 




LBApplication
--------------


The ``LBApplication`` resource type creates an Application Load Balancer. Use load balancers to route traffic from
the internet to your web servers.

Load balancers have ``listeners`` which will accept requrests on specified ports and protocols. If a listener
uses the HTTPS protocol, it can have a Paco reference to an SSL Certificate. A listener can then either
redirect the traffic to another port/protcol or send it one of it's named ``target_groups``.

Each target group will specify it's health check configuration. To specify which resources will belong
to a target group, use the ``target_groups`` field on an ASG resource.

.. sidebar:: Prescribed Automation

    ``dns``: Creates Route 53 Record Sets that will resolve DNS records to the domain name of the load balancer.

    ``enable_access_logs``: Set to True to turn on access logs for the load balancer, and will automatically create
    an S3 Bucket with permissions for AWS to write to that bucket.

    ``access_logs_bucket``: Name an existing S3 Bucket (in the same region) instead of automatically creating a new one.
    Remember that if you supply your own S3 Bucket, you are responsible for ensuring that the bucket policy for
    it grants AWS the `s3:PutObject` permission.

.. code-block:: yaml
    :caption: Example LBApplication load balancer resource YAML

    type: LBApplication
    enabled: true
    enable_access_logs: true
    target_groups:
        api:
            health_check_interval: 30
            health_check_timeout: 10
            healthy_threshold: 2
            unhealthy_threshold: 2
            port: 3000
            protocol: HTTP
            health_check_http_code: 200
            health_check_path: /
            connection_drain_timeout: 30
    listeners:
        http:
            port: 80
            protocol: HTTP
            redirect:
                port: 443
                protocol: HTTPS
        https:
            port: 443
            protocol: HTTPS
            ssl_certificates:
                - paco.ref netenv.app.applications.app.groups.certs.resources.root
            target_group: api
    dns:
        - hosted_zone: paco.ref resource.route53.mynetenv
          domain_name: api.example.com
    scheme: internet-facing
    security_groups:
        - paco.ref netenv.app.network.vpc.security_groups.app.alb
    segment: public



.. _LBApplication:

.. list-table:: :guilabel:`LBApplication`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - access_logs_bucket
      - PacoReference
      - Bucket to store access logs in
      - Paco Reference to `S3Bucket`_.
      - 
    * - access_logs_prefix
      - String
      - Access Logs S3 Bucket prefix
      - 
      - 
    * - dns
      - List<DNS_>
      - List of DNS for the ALB
      - 
      - 
    * - enable_access_logs
      - Boolean
      - Write access logs to an S3 Bucket
      - 
      - 
    * - idle_timeout_secs
      - Int
      - Idle timeout in seconds
      - The idle timeout value, in seconds.
      - 60
    * - listeners
      - Container<Listeners_>
      - Listeners
      - 
      - 
    * - scheme
      - Choice
      - Scheme
      - 
      - 
    * - security_groups
      - List<PacoReference>
      - Security Groups
      - Paco Reference to `SecurityGroup`_.
      - 
    * - segment
      - String
      - Id of the segment stack
      - 
      - 
    * - target_groups
      - Container<TargetGroups_>
      - Target Groups
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


DNS
^^^^



.. _DNS:

.. list-table:: :guilabel:`DNS`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - PacoReference|String
      - Domain name
      - Paco Reference to `Route53HostedZone`_. String Ok.
      - 
    * - hosted_zone
      - PacoReference|String
      - Hosted Zone Id
      - Paco Reference to `HostedZone`_. String Ok.
      - 
    * - ssl_certificate
      - PacoReference
      - SSL certificate Reference
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - ttl
      - Int
      - TTL
      - 
      - 300



Listeners
^^^^^^^^^^


Container for `Listener`_ objects.
    

.. _Listeners:

.. list-table:: :guilabel:`Listeners` |bars| Container<`Listener`_>
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


Listener
^^^^^^^^^



.. _Listener:

.. list-table:: :guilabel:`Listener`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - redirect
      - Object<PortProtocol_>
      - Redirect
      - 
      - 
    * - rules
      - Container<ListenerRule_>
      - Container of listener rules
      - 
      - 
    * - ssl_certificates
      - List<PacoReference>
      - List of SSL certificate References
      - Paco Reference to `AWSCertificateManager`_.
      - 
    * - ssl_policy
      - Choice
      - SSL Policy
      - 
      - 
    * - target_group
      - String
      - Target group
      - 
      - 

*Base Schemas* `PortProtocol`_


ListenerRule
^^^^^^^^^^^^^



.. _ListenerRule:

.. list-table:: :guilabel:`ListenerRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - host
      - String
      - Host header value
      - 
      - 
    * - path_pattern
      - List<String>
      - List of paths to match
      - 
      - 
    * - priority
      - Int
      - Forward condition priority
      - 
      - 1
    * - redirect_host
      - String
      - The host to redirect to
      - 
      - 
    * - rule_type
      - String
      - Type of Rule
      - 
      - 
    * - target_group
      - String
      - Target group name
      - 
      - 

*Base Schemas* `Deployable`_


PortProtocol
^^^^^^^^^^^^^

Port and Protocol

.. _PortProtocol:

.. list-table:: :guilabel:`PortProtocol`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - port
      - Int
      - Port
      - 
      - 
    * - protocol
      - Choice
      - Protocol
      - 
      - 



TargetGroups
^^^^^^^^^^^^^


Container for `TargetGroup`_ objects.
    

.. _TargetGroups:

.. list-table:: :guilabel:`TargetGroups` |bars| Container<`TargetGroup`_>
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


TargetGroup
^^^^^^^^^^^^

Target Group

.. _TargetGroup:

.. list-table:: :guilabel:`TargetGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - connection_drain_timeout
      - Int
      - Connection drain timeout
      - 
      - 
    * - health_check_http_code
      - String
      - Health check HTTP codes
      - 
      - 
    * - health_check_interval
      - Int
      - Health check interval
      - 
      - 
    * - health_check_path
      - String
      - Health check path
      - 
      - /
    * - health_check_timeout
      - Int
      - Health check timeout
      - 
      - 
    * - healthy_threshold
      - Int
      - Healthy threshold
      - 
      - 
    * - unhealthy_threshold
      - Int
      - Unhealthy threshold
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `PortProtocol`_, `Title`_, `Type`_


PinpointApplication
--------------------

Amazon Pinpoint is a flexible and scalable outbound and inbound marketing communications service.
You can connect with customers over channels like email, SMS, push, or voice.

A Pinpoint Application is a collection of related settings, customer information, segments, campaigns,
and other types of Amazon Pinpoint resources.

Currently AWS Pinpoint only supports general configuration suitable for sending transactional messages.

.. sidebar:: Prescribed Automation

    ``email_channel``: Will build an ARN to a Simple Email Service Verified Email in the same account and region.

.. code-block:: yaml
    :caption: example Pinpoint Application configuration

    type: PinpointApplication
    enabled: true
    order: 20
    title: "My SaaS Transactional Message Service"
    email_channel:
        enable_email: true
        from_address: "bob@example.com"
    sms_channel:
        enable_sms: true
        sender_id: MyUniqueName



.. _PinpointApplication:

.. list-table:: :guilabel:`PinpointApplication`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - email_channel
      - Object<PinpointEmailChannel_>
      - Email Channel
      - 
      - 
    * - sms_channel
      - Object<PinpointSMSChannel_>
      - SMS Channel
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


IoTTopicRule
-------------


IoTTopicRule allows you to create a list of actions that will be triggered from a
MQTT message coming in to IoT Core.

.. sidebar:: Prescribed Automation

    **IoTTopicRule Role** Every IoTTopicRule will have a Role created that it can assume to perform any actions
    that it has. For example, it will be allowed to call a Lambda or an IoTAnalyticsPipeline.

.. code-block:: yaml
    :caption: example IoTTopicRule configuration

    type: IoTTopicRule
    title: Rule to take action for MQTT messages sent to 'sensor/example'
    order: 20
    enabled: true
    actions:
      - awslambda:
          function: paco.ref netenv.mynet.applications.app.groups.app.resources.iotlambda
      - iotanalytics:
          pipeline: paco.ref netenv.mynet.applications.app.groups.app.resources.analyticspipeline
    aws_iot_sql_version: '2016-03-23'
    rule_enabled: true
    sql: "SELECT * FROM 'sensor/example'"



.. _IoTTopicRule:

.. list-table:: :guilabel:`IoTTopicRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - actions
      - List<IoTTopicRuleAction_> |star|
      - Actions
      - An IoTTopicRule must define at least one action.
      - []
    * - aws_iot_sql_version
      - String
      - AWS IoT SQL Version
      - 
      - 2016-03-23
    * - rule_enabled
      - Boolean
      - Rule is Enabled
      - 
      - True
    * - sql
      - String |star|
      - SQL statement used to query the topic
      - Must be a valid Sql statement
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


IoTTopicRuleAction
^^^^^^^^^^^^^^^^^^^



.. _IoTTopicRuleAction:

.. list-table:: :guilabel:`IoTTopicRuleAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - awslambda
      - Object<IoTTopicRuleLambdaAction_>
      - Lambda Action
      - 
      - 
    * - iotanalytics
      - Object<IoTTopicRuleIoTAnalyticsAction_>
      - IoT Analytics Action
      - 
      - 



IoTTopicRuleIoTAnalyticsAction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _IoTTopicRuleIoTAnalyticsAction:

.. list-table:: :guilabel:`IoTTopicRuleIoTAnalyticsAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - pipeline
      - PacoReference |star|
      - IoT Analytics pipeline
      - Paco Reference to `IoTAnalyticsPipeline`_.
      - 



IoTTopicRuleLambdaAction
^^^^^^^^^^^^^^^^^^^^^^^^^



.. _IoTTopicRuleLambdaAction:

.. list-table:: :guilabel:`IoTTopicRuleLambdaAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - function
      - PacoReference |star|
      - Lambda function
      - Paco Reference to `Lambda`_.
      - 




IoTAnalyticsPipeline
---------------------


An IoTAnalyticsPipeline composes four closely related resources: IoT Analytics Channel, IoT Analytics Pipeline,
IoT Analytics Datastore and IoT Analytics Dataset.

An IoT Analytics Pipeline begins with a Channel. A Channel is an S3 Bucket of raw incoming messages.
A Channel provides an ARN that an IoTTopicRule can send MQTT messages to. These messages can later be re-processed
if the analysis pipeline changes. Use the ``channel_storage`` field to configure the Channel storage.

Next the Pipeline applies a series of ``pipeline_activities`` to the incoming Channel messages. After any message
modifications have been made, they are stored in a Datastore.

A Datastore is S3 Bucket storage of messages that are ready to be analyzed. Use the ``datastore_storage`` field to configure
the Datastore storage. The ``datastore_name`` is an optional field to give your Datastore a fixed name, this can
be useful if you use Dataset SQL Query analysis which needs to use the Datastore name in a SELECT query. However,
if you use ``datastore_name`` it doesn't vary by Environment - if you use name then it is recommended to use different
Regions and Accounts for each IoTAnalytics environment.

Lastly the Datastore can be analyzed and have the resulting output saved as a Dataset. There may be multiple Datasets
to create different analysis of the data. Datasets can be analyzed on a managed host running a Docker container or
with an SQL Query to create subsets of a Datastore suitable for analysis with tools such as AWS QuickSight.

.. sidebar:: Prescribed Automation

    **IoTAnalyticsPipeline Role** Every IoTAnalyticsPipeline has an IAM Role associated with it. This Role will
    have access to every S3 Bucket that is referenced by a Channel, Datastore or Dataset.

    ``pipeline_activities``: Every list of activities beings with an implicit Channel activity and ends with a
    Datastore activity.


.. code-block:: yaml
    :caption: example IoTAnalyticsPipeline configuration

    type: IoTAnalyticsPipeline
    title: My IoT Analytics Pipeline
    order: 100
    enabled: true
    channel_storage:
      bucket: paco.ref netenv.mynet.applications.app.groups.iot.resources.iotbucket
      key_prefix: raw_input/
    pipeline_activities:
      adddatetime:
        activity_type: lambda
        function: paco.ref netenv.mynet.applications.app.groups.iot.resources.iotfunc
        batch_size: 10
      filter:
        activity_type: filter
        filter: "temperature > 0"
    datastore_name: example
    datastore_storage:
      expire_events_after_days: 30
    datasets:
      hightemp:
        query_action:
          sql_query: "SELECT * FROM example WHERE temperature > 20"
        content_delivery_rules:
          s3temperature:
            s3_destination:
              bucket: paco.ref netenv.mynet.applications.app.groups.iot.resources.iotbucket
              key: "/HighTemp/!{iotanalytics:scheduleTime}/!{iotanalytics:versionId}.csv"
        expire_events_after_days: 3
        version_history: 5

    

.. _IoTAnalyticsPipeline:

.. list-table:: :guilabel:`IoTAnalyticsPipeline`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - channel_storage
      - Object<IotAnalyticsStorage_>
      - IoT Analytics Channel raw storage
      - 
      - 
    * - datasets
      - Container<IoTDatasets_> |star|
      - IoT Analytics Datasets
      - 
      - 
    * - datastore_name
      - String
      - Datastore name
      - 
      - 
    * - datastore_storage
      - Object<IotAnalyticsStorage_>
      - IoT Analytics Datastore storage
      - 
      - 
    * - pipeline_activities
      - Container<IoTPipelineActivities_>
      - IoT Analytics Pipeline Activies
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


IoTDatasets
^^^^^^^^^^^^

Container for `IoTDataset`_ objects.

.. _IoTDatasets:

.. list-table:: :guilabel:`IoTDatasets` |bars| Container<`IoTDataset`_>
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


IoTDataset
^^^^^^^^^^^



.. _IoTDataset:

.. list-table:: :guilabel:`IoTDataset`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - container_action
      - Object<DatasetContainerAction_>
      - Dataset Container action
      - 
      - 
    * - content_delivery_rules
      - Container<DatasetContentDeliveryRules_>
      - Content Delivery Rules
      - 
      - 
    * - query_action
      - Object<DatasetQueryAction_>
      - SQL Query action
      - 
      - 
    * - triggers
      - List<DatasetTrigger_>
      - Triggers
      - 
      - []
    * - version_history
      - Int
      - How many versions of dataset contents are kept. 0 indicates Unlimited. If not specified or set to null, only the latest version plus the latest succeeded version (if they are different) are kept for the time period specified by expire_events_after_days field.
      - 
      - 

*Base Schemas* `StorageRetention`_, `Named`_, `Title`_


DatasetTrigger
^^^^^^^^^^^^^^^



.. _DatasetTrigger:

.. list-table:: :guilabel:`DatasetTrigger`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - schedule_expression
      - String
      - Schedule Expression
      - 
      - 
    * - triggering_dataset
      - String
      - Triggering Dataset
      - 
      - 



DatasetContentDeliveryRules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Container for `DatasetContentDeliveryRule`_ objects.

.. _DatasetContentDeliveryRules:

.. list-table:: :guilabel:`DatasetContentDeliveryRules` |bars| Container<`DatasetContentDeliveryRule`_>
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


DatasetContentDeliveryRule
^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _DatasetContentDeliveryRule:

.. list-table:: :guilabel:`DatasetContentDeliveryRule`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - s3_destination
      - Object<DatasetS3Destination_>
      - S3 Destination
      - 
      - 

*Base Schemas* `Named`_, `Title`_


DatasetS3Destination
^^^^^^^^^^^^^^^^^^^^^



.. _DatasetS3Destination:

.. list-table:: :guilabel:`DatasetS3Destination`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference |star|
      - S3 Bucket
      - Paco Reference to `S3Bucket`_.
      - 
    * - key
      - String |star|
      - Key
      - 
      - 



DatasetQueryAction
^^^^^^^^^^^^^^^^^^^



.. _DatasetQueryAction:

.. list-table:: :guilabel:`DatasetQueryAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - filters
      - List<String>
      - Filters
      - 
      - []
    * - sql_query
      - String |star|
      - Sql Query Dataset Action object
      - 
      - 

*Base Schemas* `Named`_, `Title`_


DatasetContainerAction
^^^^^^^^^^^^^^^^^^^^^^^



.. _DatasetContainerAction:

.. list-table:: :guilabel:`DatasetContainerAction`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - image_arn
      - String |star|
      - Image ARN
      - 
      - 
    * - resource_compute_type
      - Choice |star|
      - Resource Compute Type
      - Either ACU_1 (vCPU=4, memory=16 GiB) or ACU_2 (vCPU=8, memory=32 GiB)
      - 
    * - resource_volume_size_gb
      - Int |star|
      - Resource Volume Size in GB
      - 
      - 
    * - variables
      - Container<DatasetVariables_> |star|
      - Variables
      - 
      - 

*Base Schemas* `Named`_, `Title`_


DatasetVariables
^^^^^^^^^^^^^^^^^

Container for `DatasetVariables`_ objects.

.. _DatasetVariables:

.. list-table:: :guilabel:`DatasetVariables` |bars| Container<`DatasetVariables`_>
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


DatasetVariable
^^^^^^^^^^^^^^^^



.. _DatasetVariable:

.. list-table:: :guilabel:`DatasetVariable`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - double_value
      - Float
      - Double Value
      - 
      - 
    * - output_file_uri_value
      - String
      - Output file URI value
      - The URI of the location where dataset contents are stored, usually the URI of a file in an S3 bucket.
      - 
    * - string_value
      - String
      - String Value
      - 
      - 

*Base Schemas* `Named`_, `Title`_


IoTPipelineActivities
^^^^^^^^^^^^^^^^^^^^^^

Container for `IoTPipelineActivity`_ objects.

.. _IoTPipelineActivities:

.. list-table:: :guilabel:`IoTPipelineActivities` |bars| Container<`IoTPipelineActivity`_>
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


IoTPipelineActivity
^^^^^^^^^^^^^^^^^^^^


Each activity must have an ``activity_type`` and supply fields specific for that type.
There is an implicit Channel activity before all other activities and an an implicit Datastore
activity after all other activities.

.. code-block:: yaml
    :caption: All example types for IoTAnalyticsPipeline pipeline_activities

    activity_type: lambda
    batch_size: 1
    function: paco.ref netenv.mynet[...]mylambda

    activity_type: add_attributes
    attributes:
      key1: hello
      key2: world

    activity_type: remove_attributes
    attribute_list:
      - key1
      - key2

    activity_type: select_attributes
    attribute_list:
      - key1
      - key2

    activity_type: filter
    filter: "attribute1 > 40 AND attribute2 < 20"

    activity_type: math
    attribute: "attribute1"
    math: "attribute1 - 10"

    activity_type: device_registry_enrich
    attribute: "attribute1"
    thing_name: "mything"

    activity_type: device_shadow_enrich
    attribute: "attribute1"
    thing_name: "mything"



.. _IoTPipelineActivity:

.. list-table:: :guilabel:`IoTPipelineActivity`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - activity_type
      - String |star|
      - Activity Type
      - 
      - 
    * - attribute
      - String
      - Attribute
      - 
      - 
    * - attribute_list
      - List<String>
      - Attribute List
      - 
      - 
    * - attributes
      - Container<Attributes_>
      - Attributes
      - 
      - 
    * - batch_size
      - Int
      - Batch Size
      - 
      - 
    * - filter
      - String
      - Filter
      - 
      - 
    * - function
      - PacoReference
      - Lambda function
      - Paco Reference to `Lambda`_.
      - 
    * - math
      - String
      - Math
      - 
      - 
    * - thing_name
      - String
      - Thing Name
      - 
      - 

*Base Schemas* `Named`_, `Title`_


Attributes
^^^^^^^^^^^


Dictionary of Attributes
    

.. _Attributes:

.. list-table:: :guilabel:`Attributes`
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


IotAnalyticsStorage
^^^^^^^^^^^^^^^^^^^^



.. _IotAnalyticsStorage:

.. list-table:: :guilabel:`IotAnalyticsStorage`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - bucket
      - PacoReference
      - S3 Bucket
      - Paco Reference to `S3Bucket`_.
      - 
    * - key_prefix
      - String
      - Key Prefix for S3 Bucket
      - 
      - 

*Base Schemas* `StorageRetention`_, `Named`_, `Title`_


StorageRetention
^^^^^^^^^^^^^^^^^



.. _StorageRetention:

.. list-table:: :guilabel:`StorageRetention`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - expire_events_after_days
      - Int
      - Expire Events After Days
      - Must be 1 or greater. If set to an explicit 0 then it is considered unlimited.
      - 0





ManagedPolicy
--------------


IAM Managed Policy
    

.. _ManagedPolicy:

.. list-table:: :guilabel:`ManagedPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - path
      - String
      - Path
      - 
      - /
    * - policy_name
      - String |star|
      - Policy Name used in AWS. This will be prefixed with an 8 character hash.
      - 
      - 
    * - roles
      - List<String>
      - List of Role Names
      - 
      - 
    * - statement
      - List<Statement_>
      - Statements
      - 
      - 
    * - users
      - List<String>
      - List of IAM Users
      - 
      - 

*Base Schemas* `Deployable`_, `Named`_, `Title`_

RDS
---

Relational Database Service (RDS) allows you to set up, operate, and scale a relational database in AWS.

You can create a single DB Instance or an Aurora DB Cluster.

DB Instance
^^^^^^^^^^^

Currently Paco supports ``RDSMysql`` and ``RDSPostgresql`` for single database instances.

.. sidebar:: Prescribed Automation

  **Using Secrets Manager with RDS**

  You can set the initial password with ``master_user_password``, however this requires storing a password
  in plain-text on disk. This is fine if you have a process for changing the password after creating a database,
  however, the Paco Secrets Manager support allows you to use a ``secrets_password`` instead of the
  ``master_user_password`` field:

  .. code-block:: yaml

      type: RDSMysql
      secrets_password: paco.ref netenv.mynet.secrets_manager.app.grp.mysql

  Then in your NetworkEnvironments ``secrets_manager`` configuration you would write:

  .. code-block:: yaml

      secrets_manager:
        app: # application name
          grp: # group name
              mysql: # secret name
                enabled: true
                generate_secret_string:
                  enabled: true
                  # secret_string_template and generate_string_key must
                  # have the following values for RDS secrets
                  secret_string_template: '{"username": "admin"}'
                  generate_string_key: "password"

  This would generate a new, random password in the AWS Secrets Manager service when the database is provisioned
  and connect that password with RDS.

.. code-block:: yaml
  :caption: RDSMysql resource example

  type: RDSMysql
  order: 1
  title: "Joe's MySQL Database server"
  enabled: true
  engine_version: 5.7.26
  db_instance_type: db.t3.micro
  port: 3306
  storage_type: gp2
  storage_size_gb: 20
  storage_encrypted: true
  multi_az: true
  allow_major_version_upgrade: false
  auto_minor_version_upgrade: true
  publically_accessible: false
  master_username: root
  master_user_password: "change-me"
  backup_preferred_window: 08:00-08:30
  backup_retention_period: 7
  maintenance_preferred_window: 'sat:10:00-sat:10:30'
  license_model: "general-public-license"
  cloudwatch_logs_exports:
    - error
    - slowquery
  security_groups:
    - paco.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: paco.ref netenv.mynet.network.vpc.segments.private
  primary_domain_name: database.example.internal
  primary_hosted_zone: paco.ref netenv.mynet.network.vpc.private_hosted_zone
  parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance

Aurora DB Cluster
^^^^^^^^^^^^^^^^^

AWS Aurora is relational databases built for the cloud. Aurora features a distributed, fault-tolerant,
self-healing storage system and can easily scale from a single database instance to a cluster of multiple
database instances.

When creating an Aurora RDS resource, you must specify your ``db_instances``. If you specify more than
one database instance, then Aurora will automatically designate one instance as a Writer and all other
instances will be Readers.

Each ``db_instance`` can specify it's own complete set of configuration or you can use the ``default_instance``
field to shared default configuration between instances. If a ``db_instance`` doesn't specify a value but it is
specified by ``default_instance`` it will fall back to using that value.

A simple Aurora with only a single database instance could be:

.. code-block:: yaml
  :caption: Simple Aurora single instance

  type: RDSMysqlAurora
  default_instance:
    db_instance_type: db.t3.medium
  db_instances:
    single:

A more complex Aurora with a cluster of three database instances could be:

.. code-block:: yaml
  :caption: Three instance Aurora cluster

  type: RDSMysqlAurora
  default_instance:
    db_instance_type: db.t3.medium
    enhanced_monitoring_interval_in_seconds: 30
  db_instances:
    first:
      availability_zone: 1
      db_instance_type: db.t3.large
      enhanced_monitoring_interval_in_seconds: 5
    second:
      availability_zone: 2
    third:
      availability_zone: 3

.. sidebar:: Prescribed Automation

  ``secrets_password``: Uses a Secrets Manager secret for the database master password.

  ``enable_kms_encryption``: Encrypts the database storage. Paco will creates a KMS-CMK dedicated to the
  DB Cluster. This key can only be accessed by the AWS RDS service.

  ``enhanced_monitoring_interval_in_seconds``: Paco will create an IAM Role to allow the RDS monitoring service
  access to perform enhanced monitoring.

  ``cluster_event_notifications`` and ``event_notifications`` must reference a group specified in ``resource/sns.yaml``.
  This group (SNS Topic) must already be provisioned in the same account and region as the database.

  ``monitoring`` applies to ``db_instances`` and will apply CloudWatch Alarms that are specific to each database instance
  in the Aurora cluster.

.. code-block:: yaml
  :caption: RDSPostgresqlAurora db cluster example

  type: RDSPostgresqlAurora
  order: 10
  enabled: true
  availability_zones: all
  engine_version: '11.7'
  port: 5432
  master_username: master
  secrets_password: paco.ref netenv.anet.secrets_manager.anet.app.database
  backup_preferred_window: 04:00-05:00
  backup_retention_period: 7
  maintenance_preferred_window: 'Sat:07:00-Sat:08:00'
  cluster_parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.clusterparams
  cloudwatch_logs_exports:
    - error
  security_groups:
    - paco.ref netenv.mynet.network.vpc.security_groups.app.database
  segment: paco.ref netenv.anet.network.vpc.segments.private
  dns:
    - domain_name: database.test.internal
      hosted_zone: paco.ref netenv.mynet.network.vpc.private_hosted_zone
  enable_kms_encryption: true
  cluster_event_notifications:
    groups:
      - wb_low
    event_categories:
      - failover
      - failure
      - notification
  default_instance:
    parameter_group: paco.ref netenv.mynet.applications.app.groups.web.resources.dbparams_performance
    enable_performance_insights: true
    publicly_accessible: false
    db_instance_type: db.t3.medium
    allow_major_version_upgrade: true
    auto_minor_version_upgrade: true
    event_notifications:
      groups:
        - admin
      event_categories:
        - availability
        - configuration change
        - deletion
        - failover
        - failure
        - maintenance
        - notification
        - recovery
    monitoring:
      enabled: true
      alarm_sets:
        basic_dbinstance:
  db_instances:
    first:
      db_instance_type: db.t3.medium
      enhanced_monitoring_interval_in_seconds: 30
      availability_zone: 1
      monitoring:
        enabled: true
        alarm_sets:
          complex_dbinstance:
    second:
      enable_performance_insights: false
      event_notifications:
        groups:
          - admin
        event_categories:
          - maintenance



RDSMysql
^^^^^^^^^

RDS for MySQL

.. _RDSMysql:

.. list-table:: :guilabel:`RDSMysql`
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

*Base Schemas* `RDSInstance`_, `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `RDSMultiAZ`_, `Named`_, `Title`_, `Type`_


RDSPostgresql
^^^^^^^^^^^^^^

RDS for Postgresql

.. _RDSPostgresql:

.. list-table:: :guilabel:`RDSPostgresql`
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

*Base Schemas* `RDSInstance`_, `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `RDSMultiAZ`_, `Named`_, `Title`_, `Type`_


RDSPostgresqlAurora
^^^^^^^^^^^^^^^^^^^^


RDS PostgreSQL Aurora Cluster
    

.. _RDSPostgresqlAurora:

.. list-table:: :guilabel:`RDSPostgresqlAurora`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - database_name
      - String
      - Database Name to create in the cluster
      - Must be a valid database name for the DB Engine. Must contain 1 to 63 letters, numbers or underscores. Must begin with a letter or an underscore. Can't be PostgreSQL reserved word.
      - 

*Base Schemas* `RDSAurora`_, `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSMysqlAurora
^^^^^^^^^^^^^^^


RDS MySQL Aurora Cluster
    

.. _RDSMysqlAurora:

.. list-table:: :guilabel:`RDSMysqlAurora`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - database_name
      - String
      - Database Name to create in the cluster
      - Must be a valid database name for the DB Engine. Must contain 1 to 64 letters or numbers. Can't be MySQL reserved word.
      - 

*Base Schemas* `RDSAurora`_, `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSOptionConfiguration
^^^^^^^^^^^^^^^^^^^^^^^


Option groups enable and configure features that are specific to a particular DB engine.
    

.. _RDSOptionConfiguration:

.. list-table:: :guilabel:`RDSOptionConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - option_name
      - String
      - Option Name
      - 
      - 
    * - option_settings
      - List<NameValuePair_>
      - List of option name value pairs.
      - 
      - 
    * - option_version
      - String
      - Option Version
      - 
      - 
    * - port
      - String
      - Port
      - 
      - 



NameValuePair
^^^^^^^^^^^^^^

A Name/Value pair to use for RDS Option Group configuration

.. _NameValuePair:

.. list-table:: :guilabel:`NameValuePair`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - name
      - String |star|
      - Name
      - 
      - 
    * - value
      - PacoReference|String |star|
      - Value
      - Paco Reference to `Interface`_. String Ok.
      - 



RDSMultiAZ
^^^^^^^^^^^


RDS with MultiAZ capabilities. When you provision a Multi-AZ DB Instance, Amazon RDS automatically creates a
primary DB Instance and synchronously replicates the data to a standby instance in a different Availability Zone (AZ).
    

.. _RDSMultiAZ:

.. list-table:: :guilabel:`RDSMultiAZ`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - multi_az
      - Boolean
      - Multiple Availability Zone deployment
      - 
      - False

*Base Schemas* `RDSInstance`_, `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSInstance
^^^^^^^^^^^^


RDS DB Instance
    

.. _RDSInstance:

.. list-table:: :guilabel:`RDSInstance`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - allow_major_version_upgrade
      - Boolean
      - Allow major version upgrades
      - 
      - 
    * - auto_minor_version_upgrade
      - Boolean
      - Automatic minor version upgrades
      - 
      - 
    * - db_instance_type
      - String
      - RDS Instance Type
      - 
      - 
    * - license_model
      - String
      - License Model
      - 
      - 
    * - option_configurations
      - List<RDSOptionConfiguration_>
      - Option Configurations
      - 
      - 
    * - parameter_group
      - PacoReference
      - RDS Parameter Group
      - Paco Reference to `DBParameterGroup`_.
      - 
    * - publically_accessible
      - Boolean
      - Assign a Public IP address
      - 
      - 
    * - storage_encrypted
      - Boolean
      - Enable Storage Encryption
      - 
      - 
    * - storage_size_gb
      - Int
      - DB Storage Size in Gigabytes
      - 
      - 
    * - storage_type
      - String
      - DB Storage Type
      - 
      - 

*Base Schemas* `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSAurora
^^^^^^^^^^


RDS Aurora DB Cluster
    

.. _RDSAurora:

.. list-table:: :guilabel:`RDSAurora`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - availability_zones
      - String
      - Availability Zones to launch instances in.
      - Must be one of all, 1, 2, 3 ...
      - all
    * - backtrack_window_in_seconds
      - Int
      - Backtrack Window in seconds. Disabled when set to 0.
      - Maximum is 72 hours (259,200 seconds).
      - 0
    * - cluster_event_notifications
      - Object<RDSDBClusterEventNotifications_>
      - Cluster Event Notifications
      - 
      - 
    * - cluster_parameter_group
      - PacoReference
      - DB Cluster Parameter Group
      - Paco Reference to `DBClusterParameterGroup`_.
      - 
    * - db_instances
      - Container<RDSClusterInstances_> |star|
      - DB Instances
      - 
      - 
    * - default_instance
      - Object<RDSClusterDefaultInstance_>
      - Default DB Instance configuration
      - 
      - 
    * - enable_http_endpoint
      - Boolean
      - Enable an HTTP endpoint to provide a connectionless web service API for running SQL queries
      - 
      - False
    * - enable_kms_encryption
      - Boolean |star|
      - Enable KMS Key encryption. Will create one KMS-CMK key dedicated to each DBCluster.
      - 
      - False
    * - engine_mode
      - Choice
      - Engine Mode
      - Must be one of provisioned, serverless, parallelquery, global, or multimaster.
      - 
    * - read_dns
      - List<DNS_>
      - DNS domains to create to resolve to the connection Read Endpoint
      - 
      - 
    * - restore_type
      - Choice
      - Restore Type
      - Must be one of full-copy or copy-on-write
      - full-copy
    * - use_latest_restorable_time
      - Boolean
      - Restore the DB cluster to the latest restorable backup time
      - 
      - False

*Base Schemas* `RDS`_, `Resource`_, `DNSEnablable`_, `Deployable`_, `Monitorable`_, `Named`_, `Title`_, `Type`_


RDSDBInstanceEventNotifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


DB Instance Event Notifications
    

.. _RDSDBInstanceEventNotifications:

.. list-table:: :guilabel:`RDSDBInstanceEventNotifications`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - event_categories
      - Choice |star|
      - Event Categories
      - 
      - 
    * - groups
      - List<String> |star|
      - Groups
      - 
      - 

*Base Schemas* `Named`_, `Title`_


RDSClusterDefaultInstance
^^^^^^^^^^^^^^^^^^^^^^^^^^


Default configuration for a DB Instance that belongs to a DB Cluster.
    

.. _RDSClusterDefaultInstance:

.. list-table:: :guilabel:`RDSClusterDefaultInstance`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - allow_major_version_upgrade
      - Boolean
      - Allow major version upgrades
      - 
      - 
    * - auto_minor_version_upgrade
      - Boolean
      - Automatic minor version upgrades
      - 
      - 
    * - availability_zone
      - Int
      - Availability Zone where the instance will be provisioned.
      - Must be one of 1, 2, 3 ...
      - 
    * - db_instance_type
      - String
      - DB Instance Type
      - 
      - 
    * - enable_performance_insights
      - Boolean
      - Enable Performance Insights
      - 
      - False
    * - enhanced_monitoring_interval_in_seconds
      - Int
      - Enhanced Monitoring interval in seconds. This will enable enhanced monitoring unless set to 0.
      - Must be one of 0, 1, 5, 10, 15, 30, 60.
      - 0
    * - event_notifications
      - Object<RDSDBInstanceEventNotifications_>
      - DB Instance Event Notifications
      - 
      - 
    * - parameter_group
      - PacoReference
      - DB Parameter Group
      - Paco Reference to `DBParameterGroup`_.
      - 
    * - publicly_accessible
      - Boolean
      - Assign a Public IP address
      - 
      - False

*Base Schemas* `Monitorable`_, `Named`_, `Title`_


RDSClusterInstance
^^^^^^^^^^^^^^^^^^^


DB Instance that belongs to a DB Cluster.
    

.. _RDSClusterInstance:

.. list-table:: :guilabel:`RDSClusterInstance`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - allow_major_version_upgrade
      - Boolean
      - Allow major version upgrades
      - 
      - 
    * - auto_minor_version_upgrade
      - Boolean
      - Automatic minor version upgrades
      - 
      - 
    * - availability_zone
      - Int
      - Availability Zone where the instance will be provisioned.
      - Must be one of 1, 2, 3 ...
      - 
    * - db_instance_type
      - String
      - DB Instance Type
      - 
      - 
    * - enable_performance_insights
      - Boolean
      - Enable Performance Insights
      - 
      - 
    * - enhanced_monitoring_interval_in_seconds
      - Int
      - Enhanced Monitoring interval in seconds. This will enable enhanced monitoring unless set to 0.
      - Must be one of 0, 1, 5, 10, 15, 30, 60.
      - 
    * - event_notifications
      - Object<RDSDBInstanceEventNotifications_>
      - DB Instance Event Notifications
      - 
      - 
    * - parameter_group
      - PacoReference
      - DB Parameter Group
      - Paco Reference to `DBParameterGroup`_.
      - 
    * - publicly_accessible
      - Boolean
      - Assign a Public IP address
      - 
      - 

*Base Schemas* `Monitorable`_, `Named`_, `Title`_


RDSClusterInstances
^^^^^^^^^^^^^^^^^^^^


Container for `RDSClusterInstance`_ objects.
    

.. _RDSClusterInstances:

.. list-table:: :guilabel:`RDSClusterInstances` |bars| Container<`RDSClusterInstances`_>
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


RDSDBClusterEventNotifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Event Notifications for a DB Cluster
    

.. _RDSDBClusterEventNotifications:

.. list-table:: :guilabel:`RDSDBClusterEventNotifications`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - event_categories
      - Choice |star|
      - Event Categories
      - 
      - 
    * - groups
      - List<String> |star|
      - Groups
      - 
      - 

*Base Schemas* `Named`_, `Title`_

DBParameters
^^^^^^^^^^^^

If you want to use DB Parameter Groups with your RDS, then use the ``parameter_group`` field to
reference a DBParameterGroup_ resource. Keeping DB Parameter Groups as separate resources allows
having multiple Paramater Groups provisioned at the same time. For example, you might have both
resources for ``dbparams_performance`` and ``dbparams_debug``, allowing you to use the AWS
Console to switch between performance and debug configuration quickl in an emergency.


DBParameterGroup
^^^^^^^^^^^^^^^^^


DBParameterGroup
    

.. _DBParameterGroup:

.. list-table:: :guilabel:`DBParameterGroup`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - description
      - String
      - Description
      - 
      - 
    * - family
      - String |star|
      - Database Family
      - 
      - 
    * - parameters
      - Container<DBParameters_> |star|
      - Database Parameter set
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


DBClusterParameterGroup
^^^^^^^^^^^^^^^^^^^^^^^^


DBCluster Parameter Group
    

.. _DBClusterParameterGroup:

.. list-table:: :guilabel:`DBClusterParameterGroup`
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

*Base Schemas* `Resource`_, `DBParameterGroup`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



Route53HealthCheck
-------------------

Route53 Health Check

.. _Route53HealthCheck:

.. list-table:: :guilabel:`Route53HealthCheck`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - domain_name
      - String
      - Fully Qualified Domain Name
      - Either this or the load_balancer field can be set but not both.
      - 
    * - enable_sni
      - Boolean
      - Enable SNI
      - 
      - False
    * - failure_threshold
      - Int
      - Number of consecutive health checks that an endpoint must pass or fail for Amazon Route 53 to change the current status of the endpoint from unhealthy to healthy or vice versa.
      - 
      - 3
    * - health_check_type
      - String |star|
      - Health Check Type
      - Must be one of HTTP, HTTPS or TCP
      - 
    * - health_checker_regions
      - List<String>
      - Health checker regions
      - List of AWS Region names (e.g. us-west-2) from which to make health checks.
      - 
    * - ip_address
      - PacoReference|String
      - IP Address
      - Paco Reference to `EIP`_. String Ok.
      - 
    * - latency_graphs
      - Boolean
      - Measure latency and display CloudWatch graph in the AWS Console
      - 
      - False
    * - load_balancer
      - PacoReference|String
      - Load Balancer Endpoint
      - Paco Reference to `LBApplication`_. String Ok.
      - 
    * - match_string
      - String
      - String to match in the first 5120 bytes of the response
      - 
      - 
    * - port
      - Int
      - Port
      - 
      - 80
    * - request_interval_fast
      - Boolean
      - Fast request interval will only wait 10 seconds between each health check response instead of the standard 30
      - 
      - False
    * - resource_path
      - String
      - Resource Path
      - String such as '/health.html'. Path should return a 2xx or 3xx. Query string parameters are allowed: '/search?query=health'
      - /

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_



S3Bucket
---------

S3Bucket is an object storage resource in the Amazon S3 service.

S3Buckets may be declared either in the global ``resource/s3.yaml`` file or in a network environment in
as an application resource.

S3Buckets in an application context will use the same ``account`` and ``region`` as the application, although
it is still possible to override this to use other accouns and regions if desired.

.. sidebar:: Prescribed Automation

    ``deletion_policy``: The ``deletion_policy:`` field supports a ``delete`` or ``keep`` values. The ``delete``
    choice will delete all objects from the S3 Bucket if a Paco delete command is applied. Otherwise AWS will not
    allow you to delete an S3 Bucket that is not empty until all objects are deleted.

    ``resource_suffix``: The ``policy`` field allows you to declare S3 Bucket policies. These policies need to be
    restricted to the S3 Bucket resource itself. The ``resource_suffix`` will be prefixed with the S3 Bucket ARN
    and you only need to declare keys within the bucket.

.. code-block:: yaml
    :caption: example S3Bucket resource

    type: S3Bucket
    title: My S3 Bucket
    enabled: true
    order: 10
    account: paco.ref accounts.data
    region: us-west-2
    deletion_policy: "delete"
    notifications:
        lambdas:
         - paco.ref netenv.mynet.applications.app.groups.serverless.resources.mylambda
    cloudfront_origin: false
    external_resource: false
    versioning: false
    policy:
      - principal:
          Service: iotanalytics.amazonaws.com
        effect: 'Allow'
        action:
          - s3:Get*
          - s3:ListBucket
          - s3:ListBucketMultipartUploads
          - s3:ListMultipartUploadParts
        resource_suffix:
          - '/*'
          - ''
      - aws:
          - paco.sub '${paco.ref netenv.mynet.applications.app.groups.site.resources.demo.instance_iam_role.arn}'
        effect: 'Allow'
        action:
          - 's3:Get*'
          - 's3:List*'
        resource_suffix:
          - '/*'
          - ''



.. _S3Bucket:

.. list-table:: :guilabel:`S3Bucket`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - account
      - PacoReference
      - Account that S3 Bucket belongs to.
      - Paco Reference to `Account`_.
      - 
    * - bucket_name
      - String |star|
      - Bucket Name
      - A short unique name to assign the bucket.
      - bucket
    * - cloudfront_origin
      - Boolean
      - Creates and listens for a CloudFront Access Origin Identity
      - 
      - False
    * - deletion_policy
      - String
      - Bucket Deletion Policy
      - 
      - delete
    * - external_resource
      - Boolean
      - Boolean indicating whether the S3 Bucket already exists or not
      - 
      - False
    * - notifications
      - Object<S3NotificationConfiguration_>
      - Notification configuration
      - 
      - 
    * - policy
      - List<S3BucketPolicy_>
      - List of S3 Bucket Policies
      - 
      - 
    * - region
      - String
      - Bucket region
      - 
      - 
    * - static_website_hosting
      - Object<S3StaticWebsiteHosting_>
      - Static website hosting configuration.
      - 
      - 
    * - versioning
      - Boolean
      - Enable Versioning on the bucket.
      - 
      - False

*Base Schemas* `Resource`_, `DNSEnablable`_, `Deployable`_, `Named`_, `Title`_, `Type`_


S3BucketPolicy
^^^^^^^^^^^^^^^


S3 Bucket Policy
    

.. _S3BucketPolicy:

.. list-table:: :guilabel:`S3BucketPolicy`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - action
      - List<String> |star|
      - List of Actions
      - 
      - 
    * - aws
      - List<String>
      - List of AWS Principals.
      - Either this field or the principal field must be set.
      - 
    * - condition
      - Dict
      - Condition
      - Each Key is the Condition name and the Value must be a dictionary of request filters. e.g. { "StringEquals" : { "aws:username" : "johndoe" }}
      - {}
    * - effect
      - Choice |star|
      - Effect
      - Must be one of 'Allow' or 'Deny'
      - 
    * - principal
      - Dict
      - Prinicpals
      - Either this field or the aws field must be set. Key should be one of: AWS, Federated, Service or CanonicalUser. Value can be either a String or a List.
      - {}
    * - resource_suffix
      - List<String> |star|
      - List of AWS Resources Suffixes
      - 
      - 
    * - sid
      - String
      - Statement Id
      - 
      - 



S3LambdaConfiguration
^^^^^^^^^^^^^^^^^^^^^^



.. _S3LambdaConfiguration:

.. list-table:: :guilabel:`S3LambdaConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - event
      - String
      - S3 bucket event for which to invoke the AWS Lambda function
      - Must be a supported event type: https://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
      - 
    * - function
      - PacoReference
      - Lambda function to notify
      - Paco Reference to `Lambda`_.
      - 



S3NotificationConfiguration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3NotificationConfiguration:

.. list-table:: :guilabel:`S3NotificationConfiguration`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - lambdas
      - List<S3LambdaConfiguration_>
      - Lambda configurations
      - 
      - 



S3StaticWebsiteHosting
^^^^^^^^^^^^^^^^^^^^^^^



.. _S3StaticWebsiteHosting:

.. list-table:: :guilabel:`S3StaticWebsiteHosting`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - redirect_requests
      - Object<S3StaticWebsiteHostingRedirectRequests_>
      - Redirect requests configuration.
      - 
      - 

*Base Schemas* `Deployable`_


S3StaticWebsiteHostingRedirectRequests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _S3StaticWebsiteHostingRedirectRequests:

.. list-table:: :guilabel:`S3StaticWebsiteHostingRedirectRequests`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - protocol
      - String |star|
      - Protocol
      - 
      - 
    * - target
      - PacoReference|String |star|
      - Target S3 Bucket or domain.
      - Paco Reference to `S3Bucket`_. String Ok.
      - 



SNSTopic
---------


Simple Notification Service (SNS) Topic resource.

.. sidebar:: Prescribed Automation

    ``cross_account_access``: Creates an SNS Topic Policy which will grant all of the AWS Accounts in this
    Paco Project access to the ``sns.Publish`` permission for this SNS Topic.

.. code-block:: yaml
    :caption: Example SNSTopic resource YAML

    type: SNSTopic
    order: 1
    enabled: true
    display_name: "Waterbear Cloud AWS"
    cross_account_access: true
    subscriptions:
      - endpoint: http://example.com/yes
        protocol: http
      - endpoint: https://example.com/orno
        protocol: https
      - endpoint: bob@example.com
        protocol: email
      - endpoint: bob@example.com
        protocol: email-json
        filter_policy: '{"State": [ { "anything-but": "COMPLETED" } ] }'
      - endpoint: '555-555-5555'
        protocol: sms
      - endpoint: arn:aws:sqs:us-east-2:444455556666:queue1
        protocol: sqs
      - endpoint: arn:aws:sqs:us-east-2:444455556666:queue1
        protocol: application
      - endpoint: arn:aws:lambda:us-east-1:123456789012:function:my-function
        protocol: lambda



.. _SNSTopic:

.. list-table:: :guilabel:`SNSTopic`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - cross_account_access
      - Boolean
      - Cross-account access from all other accounts in this project.
      - 
      - False
    * - display_name
      - String
      - Display name for SMS Messages
      - 
      - 
    * - locations
      - List<AccountRegions_>
      - Locations
      - Only applies to a global SNS Topic
      - []
    * - subscriptions
      - List<SNSTopicSubscription_>
      - List of SNS Topic Subscriptions
      - 
      - 

*Base Schemas* `Resource`_, `DNSEnablable`_, `Enablable`_, `Named`_, `Title`_, `Type`_


SNSTopicSubscription
^^^^^^^^^^^^^^^^^^^^^



.. _SNSTopicSubscription:

.. list-table:: :guilabel:`SNSTopicSubscription`
    :widths: 15 28 30 16 11
    :header-rows: 1

    * - Field name
      - Type
      - Purpose
      - Constraints
      - Default
    * - endpoint
      - PacoReference|String
      - SNS Topic ARN or Paco Reference
      - Paco Reference to `SNSTopic`_. String Ok.
      - 
    * - filter_policy
      - String
      - Filter Policy
      - Must be valid JSON
      - 
    * - protocol
      - String
      - Notification protocol
      - Must be a valid SNS Topic subscription protocol: 'http', 'https', 'email', 'email-json', 'sms', 'sqs', 'application', 'lambda'.
      - email



.. _role: yaml-global-resources.html#role

.. _ec2keypair: yaml-global-resources.html#ec2keypair

.. _secretsmanagersecret: yaml-netenv#secretsmanagersecret

.. _securitygroup: yaml-netenv#securitygroup

.. _simplecloudwatchalarm: yaml-monitoring.html#simplecloudwatchalarm

.. _route53hostedzone: yaml-global-resources.html#route53hostedzone

.. _policy: yaml-global-resources.html#policy

.. _codecommitrepository: yaml-global-resources.html#codecommitrepository

.. _codecommituser: yaml-global-resources.html#codecommituser

.. _segment: yaml-netenv.html#segment

.. _cloudwatchlogretention: yaml-monitoring.html#cloudwatchlogretention

.. _statement: yaml-global-resources.html#statement


.. _Named: yaml-base.html#Named

.. _Name: yaml-base.html#Name

.. _Title: yaml-base.html#Title

.. _Deployable: yaml-base.html#Deployable

.. _Enablable: yaml-base.html#Enablable

.. _SecurityGroupRule: yaml-base.html#SecurityGroupRule

.. _ApplicationEngine: yaml-base.html#ApplicationEngine

.. _DnsEnablable: yaml-base.html#ApplicationEngine

.. _monitorable: yaml-base.html#monitorable

.. _notifiable: yaml-base.html#notifiable

.. _resource: yaml-base.html#resource

.. _accountregions: yaml-base#accountregions

.. _type: yaml-base.html#type

.. _interface: yaml-base.html#interface

.. _regioncontainer: yaml-base.html#regioncontainer

.. _function: yaml-base.html#function



.. _account: yaml-accounts.html#account

