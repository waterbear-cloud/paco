import base64
import os
import troposphere
import troposphere.autoscaling
import troposphere.policies
from io import StringIO
from enum import Enum
from paco import utils
from paco.models import references, schemas
from paco.cftemplates.cftemplates import CFTemplate
from paco.core.exception import UnsupportedCloudFormationParameterType
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference


class ASG(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        env_ctx,
        app_id,
        grp_id,
        asg_id,
        asg_config,
        asg_config_ref,
        role_profile_arn,
        ec2_manager_user_data_script,
        ec2_manager_cache_id
    ):
        self.env_ctx = env_ctx
        self.ec2_manager_cache_id = ec2_manager_cache_id
        segment_stack = self.env_ctx.get_segment_stack(asg_config.segment)

        # Super Init:
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=asg_config.is_enabled(),
            config_ref=asg_config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=asg_config.change_protected
        )
        self.set_aws_name('ASG', grp_id, asg_id)
        self.asg_config = asg_config

        # Troposphere
        self.init_template('AutoScalingGroup: ' + self.ec2_manager_cache_id)
        template = self.template

        # if the network for the ASG is disabled, only use an empty placeholder
        env_region = get_parent_by_interface(asg_config, schemas.IEnvironmentRegion)
        if not env_region.network.is_enabled():
            self.set_template(template.to_yaml())
            return

        security_group_list_param = self.create_cfn_ref_list_param(
            param_type='List<AWS::EC2::SecurityGroup::Id>',
            name='SecurityGroupList',
            description='List of security group ids to attach to the ASG instances.',
            value=asg_config.security_groups,
            ref_attribute='id',
            use_troposphere=True,
            troposphere_template=template
        )
        instance_key_pair_param = self.create_cfn_parameter(
            param_type='String',
            name='InstanceKeyPair',
            description='The EC2 SSH KeyPair to assign each ASG instance.',
            value=asg_config.instance_key_pair+'.keypair_name',
            use_troposphere=True,
            troposphere_template=template
        )
        instance_ami_param = self.create_cfn_parameter(
            param_type='String',
            name='InstanceAMI',
            description='The Amazon Machine Image Id to launch instances with.',
            value=asg_config.instance_ami,
            use_troposphere=True,
            troposphere_template=template
        )
        launch_config_dict = {
            'AssociatePublicIpAddress': asg_config.associate_public_ip_address,
            'EbsOptimized': asg_config.ebs_optimized,
            'ImageId': troposphere.Ref(instance_ami_param),
            'InstanceMonitoring': asg_config.instance_monitoring,
            'InstanceType': asg_config.instance_type,
            'KeyName': troposphere.Ref(instance_key_pair_param),
            'SecurityGroups': troposphere.Ref(security_group_list_param),
        }

        # BlockDeviceMappings
        if len(asg_config.block_device_mappings) > 0:
            mappings = []
            for bdm in asg_config.block_device_mappings:
                mappings.append(
                    bdm.cfn_export_dict
                )
            launch_config_dict["BlockDeviceMappings"] = mappings

        user_data_script = ''
        if ec2_manager_user_data_script != None:
            user_data_script += ec2_manager_user_data_script
        if asg_config.user_data_script != '':
            user_data_script += asg_config.user_data_script.replace('#!/bin/bash', '')
        if user_data_script != '':
            user_data_64 = base64.b64encode(user_data_script.encode('ascii'))
            user_data_script_param = self.create_cfn_parameter(
                param_type='String',
                name='UserDataScript',
                description='User data script to run at instance launch.',
                value=user_data_64.decode('ascii'),
                use_troposphere=True,
                troposphere_template=template)
            launch_config_dict['UserData'] = troposphere.Ref(user_data_script_param)

        if role_profile_arn != None:
            launch_config_dict['IamInstanceProfile'] = role_profile_arn

        # CloudFormation Init
        if asg_config.cfn_init and asg_config.is_enabled():
            launch_config_dict['Metadata'] = troposphere.autoscaling.Metadata(
                asg_config.cfn_init.export_as_troposphere()
            )
            for key, value in asg_config.cfn_init.parameters.items():
                if type(value) == type(str()):
                    param_type = 'String'
                elif type(value) == type(int()) or type(value) == type(float()):
                    param_type = 'Number'
                else:
                    raise UnsupportedCloudFormationParameterType(
                        "Can not cast {} of type {} to a CloudFormation Parameter type.".format(
                            value, type(value)
                        )
                    )
                cfn_init_param = self.create_cfn_parameter(
                    param_type=param_type,
                    name=key,
                    description='CloudFormation Init Parameter {} for ASG {}'.format(key, asg_config.name),
                    value=value,
                    use_troposphere=True
                )
                template.add_parameter(cfn_init_param)

        # Launch Configuration resource
        launch_config_res = troposphere.autoscaling.LaunchConfiguration.from_dict(
            'LaunchConfiguration',
            launch_config_dict
        )
        template.add_resource(launch_config_res)

        subnet_list_ref = 'paco.ref {}'.format(segment_stack.template.config_ref)
        if asg_config.availability_zone == 'all':
            subnet_list_ref += '.subnet_id_list'
        else:
            subnet_list_ref += '.az{}.subnet_id'.format(asg_config.availability_zone)


        asg_subnet_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='ASGSubnetList',
            description='A list of subnets where the ASG will launch instances',
            value=subnet_list_ref,
            use_troposphere=True,
            troposphere_template=template
        )

        min_instances = asg_config.min_instances if asg_config.is_enabled() else 0
        desired_capacity = asg_config.desired_capacity if asg_config.is_enabled() else 0
        asg_dict = {
            'AutoScalingGroupName': asg_config.get_aws_name(),
            'DesiredCapacity': desired_capacity,
            'HealthCheckGracePeriod': asg_config.health_check_grace_period_secs,
            'LaunchConfigurationName': troposphere.Ref(launch_config_res),
            'MaxSize': asg_config.max_instances,
            'MinSize': min_instances,
            'Cooldown': asg_config.cooldown_secs,
            'HealthCheckType': asg_config.health_check_type,
            'TerminationPolicies': asg_config.termination_policies,
            'VPCZoneIdentifier': troposphere.Ref(asg_subnet_list_param),
        }

        if asg_config.load_balancers != None and len(asg_config.load_balancers) > 0:
            load_balancer_names_param = self.create_cfn_ref_list_param(
                param_type='List<String>',
                name='LoadBalancerNames',
                description='A list of load balancer names to attach to the ASG',
                value=asg_config.load_balancers,
                use_troposphere=True,
                troposphere_template=template
            )
            asg_dict['LoadBalancerNames'] = troposphere.Ref(load_balancer_names_param)

        if asg_config.is_enabled():
            if asg_config.target_groups != None and len(asg_config.target_groups) > 0:
                asg_dict['TargetGroupARNs'] = []
                for target_group_arn in asg_config.target_groups:
                    target_group_arn_param = self.create_cfn_parameter(
                        param_type='String',
                        name='TargetGroupARNs'+utils.md5sum(str_data=target_group_arn),
                        description='A Target Group ARNs to attach to the ASG',
                        value=target_group_arn+'.arn',
                        use_troposphere=True,
                        troposphere_template=template
                    )
                    asg_dict['TargetGroupARNs'].append(troposphere.Ref(target_group_arn_param))


        if asg_config.monitoring != None and \
                asg_config.monitoring.is_enabled() == True and \
                len(asg_config.monitoring.asg_metrics) > 0:
            asg_dict['MetricsCollection'] = [{
                'Granularity': '1Minute',
                'Metrics': asg_config.monitoring.asg_metrics
            }]

        # ASG Tags
        asg_dict['Tags'] = [
            troposphere.autoscaling.Tag('Name', asg_dict['AutoScalingGroupName'], True)
        ]

        # EIP
        if asg_config.eip != None and asg_config.is_enabled():
            if references.is_ref(asg_config.eip) == True:
                eip_value = asg_config.eip + '.allocation_id'
            else:
                eip_value = asg_config.eip
            eip_id_param = self.create_cfn_parameter(
                param_type='String',
                name='EIPAllocationId',
                description='The allocation Id of the EIP to attach to the instance.',
                value=eip_value,
                use_troposphere=True,
                troposphere_template=template)
            asg_dict['Tags'].append(
                troposphere.autoscaling.Tag('Paco-EIP-Allocation-Id', troposphere.Ref(eip_id_param), True)
            )

        # EFS FileSystemId Tags
        if asg_config.is_enabled():
            for efs_mount in asg_config.efs_mounts:
                target_hash = utils.md5sum(str_data=efs_mount.target)
                if references.is_ref(efs_mount.target) == True:
                    efs_value = efs_mount.target + '.id'
                else:
                    efs_value = efs_mount.target
                efs_id_param = self.create_cfn_parameter(
                    param_type='String',
                    name='EFSId'+target_hash,
                    description='EFS Id',
                    value=efs_value,
                    use_troposphere=True,
                    troposphere_template=template)
                asg_tag = troposphere.autoscaling.Tag(
                    'efs-id-' + target_hash,
                    troposphere.Ref(efs_id_param),
                    True
                )
                asg_dict['Tags'].append(asg_tag)

            # EBS Volume Id and Device name Tags
            for ebs_volume_mount in asg_config.ebs_volume_mounts:
                if ebs_volume_mount.is_enabled() == False:
                    continue
                volume_hash = utils.md5sum(str_data=ebs_volume_mount.volume)
                if references.is_ref(ebs_volume_mount.volume) == True:
                    ebs_volume_id_value = ebs_volume_mount.volume + '.id'
                else:
                    ebs_volume_id_value = ebs_volume_mount.volume
                # Volume Id
                ebs_volume_id_param = self.create_cfn_parameter(
                    param_type='String',
                    name='EBSVolumeId'+volume_hash,
                    description='EBS Volume Id',
                    value=ebs_volume_id_value,
                    use_troposphere=True,
                    troposphere_template=template)
                ebs_volume_id_tag = troposphere.autoscaling.Tag(
                    'ebs-volume-id-' + volume_hash,
                    troposphere.Ref(ebs_volume_id_param),
                    True
                )
                asg_dict['Tags'].append(ebs_volume_id_tag)
                #ebs_device_param = self.create_cfn_parameter(
                #    param_type='String',
                #    name='EBSDevice'+volume_hash,
                #   description='EBS Device Name',
                #    value=ebs_volume_mount.device,
                #    use_troposphere=True,
                #    troposphere_template=template)
                #ebs_device_tag = troposphere.autoscaling.Tag(
                #    'ebs-device-' + volume_hash,
                #    troposphere.Ref(ebs_device_param),
                #    True
                #)
                #asg_dict['Tags'].append(ebs_device_tag)

        asg_res = troposphere.autoscaling.AutoScalingGroup.from_dict(
            'ASG',
            asg_dict
        )
        template.add_resource(asg_res)
        asg_res.DependsOn = launch_config_res
        max_batch_size = 1
        min_instances_in_service = 0
        pause_time = 'PT0S'
        wait_on_resource_signals = False
        if asg_config.is_enabled() == True:
            if asg_config.rolling_update_policy != None:
                if asg_config.rolling_update_policy.is_enabled():
                    max_batch_size = asg_config.rolling_update_policy.max_batch_size
                    min_instances_in_service = asg_config.rolling_update_policy.min_instances_in_service
                    pause_time = asg_config.rolling_update_policy.pause_time
                    wait_on_resource_signals = asg_config.rolling_update_policy.wait_on_resource_signals
            else:
                max_batch_size = asg_config.update_policy_max_batch_size
                min_instances_in_service = asg_config.update_policy_min_instances_in_service

        asg_res.UpdatePolicy = troposphere.policies.UpdatePolicy(
            AutoScalingRollingUpdate=troposphere.policies.AutoScalingRollingUpdate(
                MaxBatchSize=max_batch_size,
                MinInstancesInService=min_instances_in_service,
                PauseTime=pause_time,
                WaitOnResourceSignals=wait_on_resource_signals
            )
        )

        troposphere.Output(
            title='ASGName',
            template=template,
            Value=troposphere.Ref(asg_res),
            Description='Auto Scaling Group Name'
        )

        self.register_stack_output_config(asg_config_ref, 'ASGName')
        self.register_stack_output_config(asg_config_ref+'.name', 'ASGName')

        # CPU Scaling Policy
        if asg_config.scaling_policy_cpu_average > 0:
            troposphere.autoscaling.ScalingPolicy(
                title='CPUAverageScalingPolicy',
                template=template,
                AutoScalingGroupName=troposphere.Ref(asg_res),
                PolicyType='TargetTrackingScaling',
                TargetTrackingConfiguration=troposphere.autoscaling.TargetTrackingConfiguration(
                    PredefinedMetricSpecification=troposphere.autoscaling.PredefinedMetricSpecification(
                        PredefinedMetricType='ASGAverageCPUUtilization'
                    ),
                    TargetValue=float(asg_config.scaling_policy_cpu_average)
                )
            )

        if asg_config.scaling_policies != None:
            for scaling_policy_name in asg_config.scaling_policies.keys():
                scaling_policy = asg_config.scaling_policies[scaling_policy_name]
                if scaling_policy.is_enabled() == False:
                    continue
                scaling_policy_res = troposphere.autoscaling.ScalingPolicy(
                    title=self.create_cfn_logical_id_join(
                        ['ScalingPolicy', scaling_policy_name],
                        camel_case=True
                    ),
                    template=template,
                    AdjustmentType=scaling_policy.adjustment_type,
                    AutoScalingGroupName=troposphere.Ref(asg_res),
                    PolicyType=scaling_policy.policy_type,
                    ScalingAdjustment=scaling_policy.scaling_adjustment,
                    Cooldown=scaling_policy.cooldown
                )
                alarm_idx = 0
                for alarm in scaling_policy.alarms:
                    dimension_list = []
                    for dimension in alarm.dimensions:
                        dimension_value = dimension.value
                        if dimension.name == 'AutoScalingGroupName' and references.is_ref(dimension.value):
                            # Reference the local ASG if the ref points here
                            dimension_ref = Reference(dimension.value)
                            if dimension_ref.ref == self.config_ref:
                                dimension_value = troposphere.Ref(asg_res)
                        dimension_res = troposphere.cloudwatch.MetricDimension(
                            Name=dimension.name,
                            Value=dimension_value
                        )
                        dimension_list.append(dimension_res)

                    if len(dimension_list) == 0:
                        dimension_list = troposphere.Ref('AWS::NoValue')

                    # Alarm Resource
                    troposphere.cloudwatch.Alarm(
                        title=self.create_cfn_logical_id_join(
                            ['ScalingPolicyAlarm', scaling_policy_name, str(alarm_idx)],
                            camel_case=True
                        ),
                        template=template,
                        ActionsEnabled=True,
                        AlarmActions=[troposphere.Ref(scaling_policy_res)],
                        AlarmDescription=alarm.alarm_description,
                        ComparisonOperator=alarm.comparison_operator,
                        MetricName=alarm.metric_name,
                        Namespace=alarm.namespace,
                        Period=alarm.period,
                        Threshold=alarm.threshold,
                        EvaluationPeriods=alarm.evaluation_periods,
                        Statistic=alarm.statistic,
                        Dimensions=dimension_list
                    )
                    alarm_idx += 1

        if asg_config.lifecycle_hooks != None:
            for lifecycle_hook_name in asg_config.lifecycle_hooks:
                lifecycle_hook = asg_config.lifecycle_hooks[lifecycle_hook_name]
                if lifecycle_hook.is_enabled() == False:
                    continue
                troposphere.autoscaling.LifecycleHook(
                    title = self.create_cfn_logical_id_join(
                        ['LifecycleHook', lifecycle_hook_name],
                        camel_case=True
                    ),
                    template=template,
                    AutoScalingGroupName=troposphere.Ref(asg_res),
                    DefaultResult=lifecycle_hook.default_result,
                    LifecycleTransition=lifecycle_hook.lifecycle_transition,
                    RoleARN=lifecycle_hook.role_arn,
                    NotificationTargetARN=lifecycle_hook.notification_target_arn
                )

        self.set_template(template.to_yaml())
