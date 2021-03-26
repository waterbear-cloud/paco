import base64
import os
import troposphere
import troposphere.autoscaling
import troposphere.policies
from io import StringIO
from awacs.aws import Allow, Statement, Policy, PolicyDocument, Principal, Action, Condition, StringEquals, StringLike
from enum import Enum
from paco import utils
from paco.models import references, schemas
from paco.cftemplates.cftemplates import StackTemplate
from paco.core.exception import UnsupportedCloudFormationParameterType
from paco.models.locations import get_parent_by_interface
from paco.models.references import Reference, get_model_obj_from_ref


class ASG(StackTemplate):
    def __init__(
        self,
        stack,
        paco_ctx,
        role_profile_arn,
        ec2_manager_user_data_script,
        ec2_manager_cache_id
    ):
        self.asg_config = asg_config = stack.resource
        asg_config_ref = asg_config.paco_ref_parts
        self.ec2_manager_cache_id = ec2_manager_cache_id
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_NAMED_IAM"])
        self.set_aws_name('ASG', self.resource_group_name, self.resource_name)

        # Troposphere
        self.init_template('AutoScalingGroup: ' + self.ec2_manager_cache_id)
        template = self.template

        # InstanceAMI Parameter is preserved in disabled templates so it can be smoothly disabled/enabled
        if self.asg_config.instance_ami_ignore_changes:
            ignore_changes = True
        else:
            ignore_changes = False
        instance_ami_param = self.create_cfn_parameter(
            param_type='String',
            name='InstanceAMI',
            description='The Amazon Machine Image Id to launch instances with.',
            value=asg_config.instance_ami,
            ignore_changes=ignore_changes,
        )

        # if the network for the ASG is disabled, only use an empty placeholder
        if not self.asg_config.env_region_obj.network.is_enabled():
            return

        security_group_list_param = self.create_cfn_ref_list_param(
            param_type='List<AWS::EC2::SecurityGroup::Id>',
            name='SecurityGroupList',
            description='List of security group ids to attach to the ASG instances.',
            value=asg_config.security_groups,
            ref_attribute='id',
        )
        instance_key_pair_param = self.create_cfn_parameter(
            param_type='String',
            name='InstanceKeyPair',
            description='The EC2 SSH KeyPair to assign each ASG instance.',
            value=asg_config.instance_key_pair+'.keypair_name',
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
            )
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
                )

        # Launch Configuration resource
        launch_config_res = troposphere.autoscaling.LaunchConfiguration.from_dict(
            'LaunchConfiguration',
            launch_config_dict
        )
        template.add_resource(launch_config_res)

        subnet_list_ref = asg_config.env_region_obj.network.vpc.segments[asg_config.segment].paco_ref
        if asg_config.availability_zone == 'all':
            subnet_list_ref += '.subnet_id_list'
        else:
            subnet_list_ref += '.az{}.subnet_id'.format(asg_config.availability_zone)


        asg_subnet_list_param = self.create_cfn_parameter(
            param_type='List<AWS::EC2::Subnet::Id>',
            name='ASGSubnetList',
            description='A list of subnets where the ASG will launch instances',
            value=subnet_list_ref
        )

        min_instances = asg_config.min_instances if asg_config.is_enabled() else 0
        desired_capacity = asg_config.desired_capacity if asg_config.is_enabled() else 0
        desired_capacity_param = self.create_cfn_parameter(
            param_type='String',
            name='DesiredCapacity',
            description='The desired capacity of instances to run in the ASG.',
            value=desired_capacity,
            ignore_changes=self.asg_config.desired_capacity_ignore_changes,
        )
        asg_dict = {
            'AutoScalingGroupName': asg_config.get_aws_name(),
            'DesiredCapacity': troposphere.Ref(desired_capacity_param),
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

        # TODO: DNS: To be enabled once cftempaltes/iam_managed_policies.py
        #            is ported to troposphere
        # if len(asg_config.dns) > 0 and asg_config.is_enabled():
        #     idx = 0
        #     for dns_config in asg_config.dns:
        #         if references.is_ref(dns_config.hosted_zone):
        #             hosted_zone_value = dns_config.hosted_zone+'.id'
        #         else:
        #             hosted_zone_value = dns_config.hosted_zone
        #         dns_hosted_zone_param = self.create_cfn_parameter(
        #             param_type='String',
        #             name=f'DNSHostedZone{idx}',
        #             description=f'DNS Hosted Zone for index {idx}',
        #             value=dns_value
        #         )
        #         asg_dict['Tags'].append(
        #             troposphere.autoscaling.Tag(f'Paco-DNS-Hosted-Zone-{idx}', troposphere.Ref(dns_hosted_zone_param), True)
        #         )
        #         dns_domain_param = self.create_cfn_parameter(
        #             param_type='String',
        #             name=f'DNSDomain{idx}',
        #             description=f'DNS Domain name for index {idx}',
        #             value=dns_value
        #         )
        #         asg_dict['Tags'].append(
        #             troposphere.autoscaling.Tag(f'Paco-DNS-Domain-{idx}', troposphere.Ref(dns_domain_param), True)
        #         )

        #         idx += 1

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
            )
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
                )
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
                    value=ebs_volume_id_value
                )
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
                #)
                #ebs_device_tag = troposphere.autoscaling.Tag(
                #    'ebs-device-' + volume_hash,
                #    troposphere.Ref(ebs_device_param),
                #    True
                #)
                #asg_dict['Tags'].append(ebs_device_tag)

        # ECS Cluster Configuration
        if asg_config.is_enabled() and asg_config.ecs != None:
            ecs_cluster_name_param = self.create_cfn_parameter(
                param_type='String',
                name='ECSClusterName',
                description='ECS Cluster Name',
                value=asg_config.ecs.cluster + '.name'
            )
            asg_tag = troposphere.autoscaling.Tag(
                'Paco-ECSCluster-Name',
                troposphere.Ref(ecs_cluster_name_param),
                True
            )
            asg_dict['Tags'].append(asg_tag)
            # ECS Cluster Capacity Manager requries NewInstancesProtectedFromScaleIn to be eneabled if it is going to manage instance protection
            if asg_config.ecs.capacity_provider != None and asg_config.ecs.capacity_provider.is_enabled():
                if asg_config.ecs.capacity_provider.managed_instance_protection == True:
                    asg_dict['NewInstancesProtectedFromScaleIn'] = True

        # ECS Release Phase Configuration
        policy_statements = []
        if asg_config.script_manager:
            if asg_config.script_manager.ecr_deploy:
                self.script_manager_ecr_deploy(asg_config.script_manager.ecr_deploy, asg_dict, asg_config, template)
            if asg_config.script_manager.ecs:
                self.script_manager_ecs(asg_config.script_manager.ecs, asg_dict, asg_config, template)

        asg_res = troposphere.autoscaling.AutoScalingGroup.from_dict(
            'ASG',
            asg_dict
        )
        template.add_resource(asg_res)
        asg_res.DependsOn = launch_config_res

        # only create an UpdatePolicy if it is enabled
        update_policy = asg_config.rolling_update_policy
        if update_policy.enabled == True:
            if update_policy.pause_time == '' and update_policy.wait_on_resource_signals == True:
                # if wait_on_resource_signals is true the default pause time is 5 minutes
                update_policy.pause_time = 'PT5M'
            elif update_policy.pause_time == '':
                update_policy.pause_time = 'PT0S'

            min_instances_in_service_param = self.create_cfn_parameter(
            param_type='String',
            name='MinInstancesInService',
            description='Roling update minimum instances to remain in service during update.',
            value=update_policy.min_instances_in_service
            )

            # UpdatePolicy properties
            asg_res.UpdatePolicy = troposphere.policies.UpdatePolicy(
                AutoScalingRollingUpdate=troposphere.policies.AutoScalingRollingUpdate(
                    MaxBatchSize=update_policy.max_batch_size,
                    MinInstancesInService=troposphere.Ref(min_instances_in_service_param),
                    PauseTime=update_policy.pause_time,
                    WaitOnResourceSignals=update_policy.wait_on_resource_signals,
                    SuspendProcesses=[
                        'HealthCheck',
                        'ReplaceUnhealthy',
                        'AlarmNotification',
                        'ScheduledActions'
                    ]
                )
            )

        self.create_output(
            title='ASGName',
            value=troposphere.Ref(asg_res),
            description='Auto Scaling Group Name',
            ref=[asg_config_ref, asg_config_ref+'.name']
        )

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

    def script_manager_ecs(self, ecs_group, asg_dict, asg_config, template):
        idx=0
        policy_statements = []
        for ecs_name in ecs_group.keys():
            ecs = ecs_group[ecs_name]
            if ecs == None:
                continue

            ecs_script_manager_cluster_arn_param = self.create_cfn_parameter(
                param_type='String',
                name=f'ECSScriptManagerClusterArn{idx}',
                description=f'ECS Script Manager Cluster Arn {idx}',
                value=ecs.cluster + '.arn'
            )
            ecs_cluster_tag = troposphere.autoscaling.Tag(
                f'paco:script_manager:ecs:{ecs_name}:cluster:arn',
                troposphere.Ref(ecs_script_manager_cluster_arn_param),
                True
            )
            asg_dict['Tags'].append(ecs_cluster_tag)

            policy_statements.append(
                Statement(
                    Sid=f'ECSScriptManagerClusterAccess{idx}',
                    Effect=Allow,
                    Action=[
                        Action('ecs', 'UpdateService'),
                        Action('ecs', 'DescribeServices'),
                        Action('ecs', 'ListServices'),
                        Action('ecs', 'RunTask'),
                        Action('ecs', 'StopTask'),
                        Action('ecs', 'DescribeContainerInstances'),
                        Action('ecs', 'ListTasks'),
                        Action('ecs', 'DescribeTasks'),
                        Action('ec2', 'DescribeInstances'),
                    ],
                    Resource=[ '*' ],
                    Condition=Condition(
                        StringEquals({
                            'ecs:cluster': troposphere.Ref(ecs_script_manager_cluster_arn_param)
                        })
                    )
                )
            )
            policy_statements.append(
                Statement(
                    Sid=f'ECSScriptManagerClusterEC2Access{idx}',
                    Effect=Allow,
                    Action=[
                        Action('ec2', 'DescribeInstances'),
                    ],
                    Resource=[ '*' ]
                )
            )

            idx += 1

        role_name = self.paco_ctx.get_ref(asg_config.paco_ref + '.instance_iam_role.name')
        script_manager_ecs_policy_res = troposphere.iam.ManagedPolicy(
            title='ScriptManagerECS',
            PolicyDocument=PolicyDocument(
                Version="2012-10-17",
                Statement=policy_statements
            ),
            Roles=[role_name]
        )
        template.add_resource(script_manager_ecs_policy_res)

    def script_manager_ecr_deploy(self, ecr_deploy_group, asg_dict, asg_config, template):
        policy_statements = []
        for ecr_deploy_name in ecr_deploy_group.keys():
            ecr_deploy = ecr_deploy_group[ecr_deploy_name]
            if ecr_deploy == None:
                continue

            if ecr_deploy and len(ecr_deploy.release_phase.ecs) > 0:
                pull_repos = []
                push_repos = []
                for repository in ecr_deploy.repositories:
                    source_ecr_obj = get_model_obj_from_ref(repository.source_repo, self.paco_ctx.project)
                    source_env = get_parent_by_interface(source_ecr_obj, schemas.IEnvironmentRegion)
                    source_account_id = self.paco_ctx.get_ref(source_env.network.aws_account+".id")

                    dest_ecr_obj = get_model_obj_from_ref(repository.dest_repo, self.paco_ctx.project)
                    dest_env = get_parent_by_interface(dest_ecr_obj, schemas.IEnvironmentRegion)
                    dest_account_id = self.paco_ctx.get_ref(dest_env.network.aws_account+".id")

                    pull_repo_arn = f'arn:aws:ecr:{source_env.region}:{source_account_id}:repository/{source_ecr_obj.repository_name}'
                    push_repo_arn = f'arn:aws:ecr:{dest_env.region}:{dest_account_id}:repository/{dest_ecr_obj.repository_name}'
                    pull_repos.append(pull_repo_arn)
                    push_repos.append(push_repo_arn)

                policy_statements.append(
                    Statement(
                        Sid=f'ScriptManagerECRDeployPull',
                        Effect=Allow,
                        Action=[
                            Action('ecr', 'GetDownloadUrlForLayer'),
                            Action('ecr', 'BatchGetImage'),
                        ],
                        Resource=pull_repos
                    )
                )

                policy_statements.append(
                    Statement(
                        Sid=f'ScriptManagerECRDeployPush',
                        Effect=Allow,
                        Action=[
                            Action('ecr', 'GetDownloadUrlForLayer'),
                            Action('ecr', 'BatchCheckLayerAvailability'),
                            Action('ecr', 'PutImage'),
                            Action('ecr', 'InitiateLayerUpload'),
                            Action('ecr', 'UploadLayerPart'),
                            Action('ecr', 'CompleteLayerUpload'),
                        ],
                        Resource=push_repos
                    )
                )
                iam_cluster_cache = []
                idx = 0
                for command in ecr_deploy.release_phase.ecs:
                    service_obj = get_model_obj_from_ref(command.service, self.paco_ctx.project)
                    ecs_services_obj = get_parent_by_interface(service_obj, schemas.IECSServices)
                    ecs_release_phase_cluster_arn_param = self.create_cfn_parameter(
                        param_type='String',
                        name=f'ECSReleasePhaseClusterArn{idx}',
                        description=f'ECS Release Phase Cluster Arn {idx}',
                        value=ecs_services_obj.cluster + '.arn'
                    )
                    ecs_release_phase_cluster_name_param = self.create_cfn_parameter(
                        param_type='String',
                        name=f'ECSReleasePhaseClusterName{idx}',
                        description=f'ECS Release Phase Cluster Name {idx}',
                        value=ecs_services_obj.cluster + '.name'
                    )
                    ecs_release_phase_service_name_param = self.create_cfn_parameter(
                        param_type='String',
                        name=f'ECSReleasePhaseServiceName{idx}',
                        description=f'ECS Release Phase Cluster Name {idx}',
                        value=command.service + '.name'
                    )
                    ecs_cluster_asg_tag = troposphere.autoscaling.Tag(
                        f'PACO_CB_RP_ECS_CLUSTER_ID_{idx}',
                        troposphere.Ref(ecs_release_phase_cluster_name_param),
                        True
                    )
                    ecs_service_asg_tag = troposphere.autoscaling.Tag(
                        f'PACO_CB_RP_ECS_SERVICE_ID_{idx}',
                        troposphere.Ref(ecs_release_phase_service_name_param),
                        True
                    )
                    asg_dict['Tags'].append(ecs_cluster_asg_tag)
                    asg_dict['Tags'].append(ecs_service_asg_tag)


                    if ecs_services_obj.cluster not in iam_cluster_cache:
                        policy_statements.append(
                            Statement(
                                Sid=f'ECSReleasePhaseSSMSendCommand{idx}',
                                Effect=Allow,
                                Action=[
                                    Action('ssm', 'SendCommand'),
                                ],
                                Resource=[ 'arn:aws:ec2:*:*:instance/*' ],
                                Condition=Condition(
                                    StringLike({
                                        'ssm:resourceTag/Paco-ECSCluster-Name': troposphere.Ref(ecs_release_phase_cluster_name_param)
                                    })
                                )
                            )
                        )

                        policy_statements.append(
                            Statement(
                                Sid=f'ECSRelasePhaseClusterAccess{idx}',
                                Effect=Allow,
                                Action=[
                                    Action('ecs', 'DescribeServices'),
                                    Action('ecs', 'RunTask'),
                                    Action('ecs', 'StopTask'),
                                    Action('ecs', 'DescribeContainerInstances'),
                                    Action('ecs', 'ListTasks'),
                                    Action('ecs', 'DescribeTasks'),
                                ],
                                Resource=[ '*' ],
                                Condition=Condition(
                                    StringEquals({
                                        'ecs:cluster': troposphere.Ref(ecs_release_phase_cluster_arn_param)
                                    })
                                )
                            )
                        )
                        iam_cluster_cache.append(ecs_services_obj.cluster)

                    idx += 1

                policy_statements.append(
                    Statement(
                        Sid='ECSReleasePhaseSSMAutomationExecution',
                        Effect=Allow,
                            Action=[
                            Action('ssm', 'StartAutomationExecution'),
                            Action('ssm', 'StopAutomationExecution'),
                            Action('ssm', 'GetAutomationExecution'),
                        ],
                        Resource=[ 'arn:aws:ssm:::automation-definition/' ]
                    )
                )
                # ECS Policies
                policy_statements.append(
                    Statement(
                        Sid='ECSRelasePhaseECS',
                        Effect=Allow,
                        Action=[
                            Action('ecs', 'DescribeTaskDefinition'),
                            Action('ecs', 'DeregisterTaskDefinition'),
                            Action('ecs', 'RegisterTaskDefinition'),
                            Action('ecs', 'ListTagsForResource'),
                            Action('ecr', 'DescribeImages')
                        ],
                        Resource=[ '*' ]
                    )
                )

                policy_statements.append(
                    Statement(
                        Sid=f'ECSReleasePhaseSSMSendCommandDocument',
                        Effect=Allow,
                        Action=[
                            Action('ssm', 'SendCommand'),
                        ],
                        Resource=[ f'arn:aws:ssm:{self.aws_region}:{self.account_ctx.get_id()}:document/paco_ecs_docker_exec' ]
                    )
                )
                policy_statements.append(
                    Statement(
                        Sid='ECSReleasePhaseSSMCore',
                        Effect=Allow,
                        Action=[
                            Action('ssm', 'ListDocuments'),
                            Action('ssm', 'ListDocumentVersions'),
                            Action('ssm', 'DescribeDocument'),
                            Action('ssm', 'GetDocument'),
                            Action('ssm', 'DescribeInstanceInformation'),
                            Action('ssm', 'DescribeDocumentParameters'),
                            Action('ssm', 'CancelCommand'),
                            Action('ssm', 'ListCommands'),
                            Action('ssm', 'ListCommandInvocations'),
                            Action('ssm', 'DescribeAutomationExecutions'),
                            Action('ssm', 'DescribeInstanceProperties'),
                            Action('ssm', 'GetCommandInvocation'),
                            Action('ec2', 'DescribeInstanceStatus'),
                            Action('ecr', 'GetAuthorizationToken')
                        ],
                        Resource=[ '*' ]
                    )
                )

                policy_statements.append(
                    Statement(
                        Sid='IAMPassRole',
                        Effect=Allow,
                        Action=[
                            Action('iam', 'passrole')
                        ],
                        Resource=[ '*' ]
                    )
                )
                role_name = self.paco_ctx.get_ref(asg_config.paco_ref + '.instance_iam_role.name')
                ecs_release_phase_project_policy_res = troposphere.iam.ManagedPolicy(
                    title='ECSReleasePhase',
                    PolicyDocument=PolicyDocument(
                        Version="2012-10-17",
                        Statement=policy_statements
                    ),
                    Roles=[role_name]
                )
                template.add_resource(ecs_release_phase_project_policy_res)