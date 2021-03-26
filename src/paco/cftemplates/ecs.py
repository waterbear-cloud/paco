from paco.models.references import get_model_obj_from_ref
from paco.models.schemas import ILoadBalancer, get_parent_by_interface
from troposphere.ecs import AwsvpcConfiguration
from troposphere.events import AwsVpcConfiguration
from paco.cftemplates.cftemplates import StackTemplate
from paco.utils import prefixed_name, md5sum
from paco.core.exception import UnsupportedCloudFormationParameterType
from paco.models import references
import troposphere
import troposphere.applicationautoscaling
import troposphere.ecs
import troposphere.servicediscovery

ECS_SCRIPT_HEAD = """#!/bin/bash
. {paco_base_path}/EC2Manager/ec2lm_functions.bash

declare -a ECS_LIST=({ecs_list})

function usage() {{
    echo "$0 <cluster name> <command> [args]"
    echo "    ECS Cluster Names:"
    for ECS_NAME in $ECS_LIST
    do
        echo "        $ECS_NAME"
    done
    echo
    echo "    Commands:"
    echo "        list-services"
    echo "        list-tasks"
    echo "        ssh [service name]"
    exit 0
}}

if [ $# -lt 2 ] ; then
    usage
fi

ECS_NAME=$1
shift
COMMAND=$1

case $ECS_NAME in
"""

ECS_SCRIPT_CONFIG = """
    {ecs_name})
        CLUSTER_ARN=$(ec2lm_instance_tag_value 'paco:script_manager:ecs:{ecs_name}:cluster:arn')
        ;;
    *)
        usage
        ;;
"""

ECS_SCRIPT_BODY = """
esac

CLUSTER=$(echo $CLUSTER_ARN | awk -F '/' '{print $2}')
ARN_PREFIX=$(echo ${CLUSTER_ARN} | awk -F ':' '{print "arn:aws:ecs:"$4":"$5}')

SERVICE_LIST_CACHE=$(mktemp)

function list_services() {
    LIST_TYPE="$1"
    LIST_CACHE=${SERVICE_LIST_CACHE}".data"
    if [ ! -e ${LIST_CACHE} ] ; then
	aws ecs list-services --cluster ${CLUSTER_ARN} --query 'serviceArns[]' --output text >${LIST_CACHE}
    fi
    for SERVICE_ARN in $(cat ${LIST_CACHE})
    do
        if [ "$LIST_TYPE" == ""  ] ; then
            SERVICE=$(echo "$SERVICE_ARN" | awk -F '/' '{print $3}' | awk -F '-' '{print $10}' | awk -F 'Service' '{print $2}' | tr '[:upper:]' '[:lower:]')
        elif [ "$LIST_TYPE" == "full" ] ; then
            SERVICE=$(echo "$SERVICE_ARN" | awk -F '/' '{print $3}')
        elif [ "$LIST_TYPE" == "arns" ] ; then
            SERVICE="${SERVICE_ARN}"
	elif [ "$LIST_TYPE" == "lookup" ] ; then
	    SERVICE=$(echo "$SERVICE_ARN" | awk -F '/' '{print $3}' | awk -F '-' '{print $10}' | awk -F 'Service' '{print $2}' | tr '[:upper:]' '[:lower:]')
	    if [ "$SERVICE" == "$2" ] ; then
		echo "$SERVICE_ARN" | awk -F '/' '{print $3}'
		return
	    fi
        else
            echo "error: unknown list type: ${LIST_TYPE}"
            exit 1
        fi
        echo "${SERVICE}"
    done
}

function list_tasks() {
    SERVICE_NAME_ARG=$(echo $1 | tr '[:upper:]' '[:lower:]')
    LIST_TYPE="$2"

    for SERVICE in $(list_services full)
    do
        #echo "aws ecs list-tasks --cluster ${CLUSTER_ARN} --service-name ${SERVICE} --query 'taskArns[]' --output text"
        for TASK_ARN in $(aws ecs list-tasks --cluster ${CLUSTER_ARN} --service-name ${SERVICE} --query 'taskArns[]' --output text)
        do
            if [ "$LIST_TYPE" == "arns" ] ; then
                echo "$TASK_ARN"
            else
                TASK=$(echo $TASK_ARN | awk -F'/' '{print $3}')
                CONTAINER_INSTANCE_ARN=$(aws ecs describe-tasks --cluster ${CLUSTER_ARN} --tasks ${TASK} --query 'tasks[0].containerInstanceArn' --output text)
                INSTANCE_ID=$(aws ecs describe-container-instances --cluster ${CLUSTER} --container-instances ${CONTAINER_INSTANCE_ARN} --query 'containerInstances[0].ec2InstanceId' --output text)
                IP_ADDRESS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
                DOCKER_TASK=$(aws ecs describe-tasks --cluster ${CLUSTER} --tasks ${TASK} --query 'tasks[0].containers[0].runtimeId' --output text)
                SHORT_SERVICE_NAME=$(echo $SERVICE | awk -F '-' '{print $10}' | awk -F 'Service' '{print $2}' | tr '[:upper:]' '[:lower:]')
                echo -e "${SHORT_SERVICE_NAME}	${IP_ADDRESS}	${DOCKER_TASK}"
            fi
        done
    done

}

function restart_service() {
    SERVICE=$1
    aws ecs update-service --cluster ${CLUSTER} --force-new-deployment --service ${SERVICE}
    # TODO: Add waiter to detect restart completion
}

function restart_services() {
    SERVICE=$1
    if [ "$SERVICE" == "all" ] ; then
	for SERVICE in $(list_services full)
	do
	    restart_service $SERVICE
	done
    else
        restart_service $(list_services lookup $SERVICE)
    fi
}

#function usage() {
#    echo "$0 <service_name> [task_id]"
#    echo
#    echo "Service names:"
#    list_services
#    echo
#    exit 1
#}

COMMAND=$1
shift


case ${COMMAND} in
    list-services)
	    list_services $1
	    exit 0
	    ;;
    restart-services)
        restart_services $1
        exit 0
        ;;
    list-tasks)
        list_tasks $1
        exit 0
        ;;
    ssh)
        ;;
    *)
        usage
        ;;
esac

TASK_ARG="NULL"
if [ $# -eq 2 ] ; then
    TASK_ARG=$2
fi

SERVICE_NAME_ARG=$(echo $1 | tr '[:upper:]' '[:lower:]')

SERVICE_OPTION=""
SERVICE=""
for SERVICE_ARN in $(list_services arns)
do
    SERVICE=$(echo "$SERVICE_ARN" |  awk -F '/' '{print $3}')
    SERVICE_OPTION=$(echo "$SERVICE" | awk -F '-' '{print $10}' | awk -F 'Service' '{print $2}' | tr '[:upper:]' '[:lower:]')
    if [ "$SERVICE_OPTION" == "$SERVICE_NAME_ARG" ] ; then
        break
    fi
    SERVICE_OPTION=""
done

if [ "$SERVICE_OPTION" == "" ] ; then
    echo "error: '${SERVICE_NAME_ARG}' was not found."
    echo
    usage
fi

SERVICE_ARN="${ARN_PREFIX}:service/${CLUSTER}/${SERVICE}"

TASK_IDX=0
NUM_TASKS=$(aws ecs list-tasks --cluster ${CLUSTER_ARN} --service-name ${SERVICE} --query 'length(taskArns)')
if [ $NUM_TASKS -gt 1 ] ; then
    if [ "$TASK_ARG" == "NULL" ] ; then
        echo "More than one task is running for '${SERVICE_NAME_ARG}'. Please specify a Task Id."
        echo "       Task Id                         ""     Start Time"
    fi
    IDX=0
    for TASK_ARN in $(list-tasks ${SERVICE} arns) #$(aws ecs list-tasks --cluster ${CLUSTER_ARN} --service-name ${SERVICE} --query 'taskArns[]' --output text)
    do
        IDX=$(($IDX+1))
        TASK=$(echo $TASK_ARN | awk -F'/' '{print $3}')
        if [ "$TASK_ARG" == "$TASK" ] ; then
            break
        fi
        if [ "$TASK_ARG" == "NULL" ] ; then
            TASK_STARTED_AT=$(aws ecs describe-tasks --cluster ${CLUSTER} --tasks ${TASK} --query 'tasks[0].startedAt' --output text)
            echo "    ${IDX}) ${TASK}     "$(date -d @${TASK_STARTED_AT})
        fi
    done
    while :
    do
        if [ "$TASK_ARG" == "$TASK" ] ; then
            # break if the users Task argument was found
            break
        elif [ "$TASK_ARG" != "NULL" ] ; then
            # Unable to find the users Task
            echo "error: '${TASK_ARG}' task is not running"
            exit 1
        fi
        read -p "Select a task: [1-$IDX]: " TASK_IDX
        if [ $TASK_IDX -ge 1 -a $TASK_IDX -le $NUM_TASKS ] ; then
            # Array is 0 based so decrement by 1
            TASK_IDX=$(($TASK_IDX-1))
            break
        fi
        echo "error: '$TASK_IDX' must be an integer between 1 and $NUM_TASKS"
        echo
    done
fi

TASK=$(aws ecs list-tasks --cluster ${CLUSTER_ARN} --service-name ${SERVICE} --query "taskArns[$TASK_IDX]" --output text | awk -F'/' '{print $3}')
CONTAINER_INSTANCE_ARN=$(aws ecs describe-tasks --cluster ${CLUSTER_ARN} --tasks ${TASK} --query 'tasks[0].containerInstanceArn' --output text)
INSTANCE_ID=$(aws ecs describe-container-instances --cluster ${CLUSTER} --container-instances ${CONTAINER_INSTANCE_ARN} --query 'containerInstances[0].ec2InstanceId' --output text)
IP_ADDRESS=$(aws ec2 describe-instances --instance-ids ${INSTANCE_ID} --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
DOCKER_TASK=$(aws ecs describe-tasks --cluster ${CLUSTER} --tasks ${TASK} --query 'tasks[0].containers[0].runtimeId' --output text)
echo
echo "ecs-ssh: ${SERVICE_NAME_ARG}: SSH to ${IP_ADDRESS} for docker task id ${DOCKER_TASK}"
ssh ${IP_ADDRESS}
"""

class ECSCluster(StackTemplate):
    def __init__(self, stack, paco_ctx):
        ecs_cluster = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ECSCluster', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Container Service (ECS) Cluster')
        if not ecs_cluster.is_enabled(): return

        # Cluster
        cluster_res = troposphere.ecs.Cluster(
            title='Cluster',
            template=self.template,
        )

        # Outputs
        self.create_output(
            title=cluster_res.title + 'Name',
            description="Cluster Name",
            value=troposphere.Ref(cluster_res),
            ref=ecs_cluster.paco_ref_parts + ".name"
        )
        self.create_output(
            title=cluster_res.title + 'Arn',
            description="Cluster Arn",
            value=troposphere.GetAtt(cluster_res, "Arn"),
            ref=ecs_cluster.paco_ref_parts + ".arn"
        )


class ECSServices(StackTemplate):
    def __init__(self, stack, paco_ctx, task_execution_role):
        ecs_config = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ECS Services', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Container Service (ECS) Services and TaskDefinitions')
        if not ecs_config.is_enabled(): return

        cluster_obj = get_model_obj_from_ref(ecs_config.cluster, self.project)
        self.secret_params = {}
        self.environment_params = {}

        # Task Execution Role
        task_execution_role_param = self.create_cfn_parameter(
            name='TaskExecutionRole',
            param_type='String',
            description='Task Execution Role',
            value=task_execution_role.get_arn(),
        )

        # TaskDefinitions
        for task in ecs_config.task_definitions.values():
            task_dict = task.cfn_export_dict
            task_dict['ExecutionRoleArn'] = troposphere.Ref(task_execution_role_param)

            index = 0
            task._depends_on = []
            for container_definition in task.container_definitions.values():
                # Environment variables
                # Merge setting_groups env vars with container_definition specific env vars
                merged_environment = {}
                for group_name in container_definition.setting_groups:
                    for env_pair in ecs_config.setting_groups[group_name].environment:
                        merged_environment[env_pair.name] = env_pair.value
                for env_pair in container_definition.environment:
                    merged_environment[env_pair.name] = env_pair.value

                for key, value in merged_environment.items():
                    # only paco refs are passed as Parameters to avoid tripping the 60 Parameter CloudFormation limit
                    if references.is_ref(value):
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
                        if value not in self.environment_params:
                            self.environment_params[value] = self.create_cfn_parameter(
                                name=self.create_cfn_logical_id('EnvironmentValue' + md5sum(str_data=value)),
                                description=f'Environment variable for container definition {container_definition.name} for task definition {task.name}',
                                param_type=param_type,
                                value=value,
                            )
                        value = troposphere.Ref(self.environment_params[value])
                    if 'Environment' not in task_dict['ContainerDefinitions'][index]:
                        task_dict['ContainerDefinitions'][index]['Environment'] = []
                    task_dict['ContainerDefinitions'][index]['Environment'].append({'Name': key, 'Value': value})

                # Secrets
                # merge shared setting_groups secrets with container definition specific secrets
                merged_secrets = {}
                for group_name in container_definition.setting_groups:
                    for secret_pair in ecs_config.setting_groups[group_name].secrets:
                        merged_secrets[secret_pair.name] = secret_pair.value_from
                for secret_pair in container_definition.secrets:
                    merged_secrets[secret_pair.name] = secret_pair.value_from

                for key, value_from in merged_secrets.items():
                    # To use the full value of the secret
                    #   paco.ref netenv.mynet.dev.ca-central-1.secrets_manager.myco.myapp.mysecret
                    # To use the field of JSON doc in the the secret
                    #   paco.ref netenv.mynet.dev.ca-central-1.secrets_manager.myco.myapp.mysecret.myjsonfield
                    value_from_ref_obj = references.Reference(value_from)
                    base_ref_obj = value_from_ref_obj.secret_base_ref()

                    if base_ref_obj.ref not in self.secret_params:
                        self.secret_params[base_ref_obj.ref] = self.create_cfn_parameter(
                            name=self.create_cfn_logical_id('SecretArn' + md5sum(str_data=base_ref_obj.ref)),
                            description=f'Arn of a Secrets Manger Secret for {base_ref_obj.ref}',
                            param_type='String',
                            value=base_ref_obj.raw + '.arn'
                        )
                    if 'Secrets' not in task_dict['ContainerDefinitions'][index]:
                        task_dict['ContainerDefinitions'][index]['Secrets'] = []

                    value_from_final = troposphere.Ref(self.secret_params[base_ref_obj.ref])
                    if base_ref_obj.raw != value_from_ref_obj.raw:
                        jsonfield_name = value_from_ref_obj.parts[8]
                        value_from_final = troposphere.Join(':', [
                            troposphere.Ref(self.secret_params[base_ref_obj.ref]), f'{jsonfield_name}::'
                        ])
                    task_dict['ContainerDefinitions'][index]['Secrets'].append({
                        'Name': key,
                        'ValueFrom': value_from_final
                    })

                # Image can be a paco.ref to an ECR Repository
                if references.is_ref(container_definition.image):
                    param_name = self.create_cfn_logical_id(f'{task.name}{container_definition.name}Image')
                    image_arn_param = self.create_cfn_parameter(
                        param_type='String',
                        name=param_name,
                        description=f'Image used to start the container.',
                        value=container_definition.image + '.arn',
                    )
                    # The ECR URL needs to break apart the ARN and re-assemble it as the URL is no provided as a Stack Output :(
                    task_dict['ContainerDefinitions'][index]['Image'] = troposphere.Join(
                        ':', [
                            troposphere.Join(
                                '/', [
                                    # domain portion: aws_account_id.dkr.ecr.region.amazonaws.com
                                    troposphere.Join(
                                        '.', [
                                            troposphere.Select(4, troposphere.Split(':', troposphere.Ref(image_arn_param))), # account id
                                            'dkr',
                                            'ecr',
                                            troposphere.Select(3, troposphere.Split(':', troposphere.Ref(image_arn_param))), # region
                                            'amazonaws',
                                            'com',
                                        ]
                                    ),
                                    troposphere.Select(1, troposphere.Split('/', troposphere.Ref(image_arn_param))) # ecr-repo-name
                                ]
                            ),
                            container_definition.image_tag # image tag
                        ]
                    )
                else:
                    task_dict['ContainerDefinitions'][index]['Image'] = container_definition.image

                if getattr(container_definition, 'logging') != None:
                    task_dict['ContainerDefinitions'][index]['LogConfiguration'] = {}
                    log_dict = task_dict['ContainerDefinitions'][index]['LogConfiguration']
                    log_dict['LogDriver'] = container_definition.logging.driver
                    # Only awslogs supported for now
                    if container_definition.logging.driver == 'awslogs':
                        log_dict['Options'] = {}
                        log_dict['Options']['awslogs-region'] = troposphere.Ref('AWS::Region')
                        prefixed_log_group_name = prefixed_name(container_definition, task.name)
                        log_group_resource = self.add_log_group(prefixed_log_group_name, container_definition.logging.expire_events_after_days)
                        log_dict['Options']['awslogs-group'] = troposphere.Ref(log_group_resource)
                        task._depends_on.append(log_group_resource)
                        log_dict['Options']['awslogs-stream-prefix'] = container_definition.name
                index += 1

            task_res = troposphere.ecs.TaskDefinition.from_dict(
                self.create_cfn_logical_id('TaskDefinition' + task.name),
                task_dict,
            )
            task_res.DependsOn = task._depends_on
            self.template.add_resource(task_res)
            task._troposphere_res = task_res

        # Cluster Param
        cluster_name_param = self.create_cfn_parameter(
            name='Cluster',
            param_type='String',
            description='Cluster Name',
            value=ecs_config.cluster + '.name',
        )
        target_group_params = {}
        alb_params = {}

        # ToDo: allow multiple PrivateDnsNamespaces?
        # e.g. if multiple ECSServices want to particpate in the same PrivateDnsNamespace?
        private_dns_namespace_res = None
        if ecs_config.service_discovery_namespace_name != '':
            private_dns_vpc_param = self.create_cfn_parameter(
                param_type='String',
                name='PrivateDnsNamespaceVpc',
                description='The Vpc for the Service Discovery Private DNS Namespace.',
                value='paco.ref ' + '.'.join(ecs_config.paco_ref_parts.split('.')[:4]) + '.network.vpc.id'
            )
            private_dns_namespace_res = troposphere.servicediscovery.PrivateDnsNamespace(
                title=self.create_cfn_logical_id(f'DiscoveryService{ecs_config.service_discovery_namespace_name}'),
                Name=ecs_config.service_discovery_namespace_name,
                Vpc=troposphere.Ref(private_dns_vpc_param),
            )
            self.template.add_resource(private_dns_namespace_res)

        #  Services
        for service in ecs_config.services.values():
            service_dict = service.cfn_export_dict
            service_dict['EnableECSManagedTags'] = True
            service_dict['Cluster'] = troposphere.Ref(cluster_name_param)
            cfn_service_name = self.create_cfn_logical_id('Service' + service.name)

            # does this service use any enabled scaling?
            uses_scaling = False
            uses_target_tracking_scaling = False
            for target_tracking_scaling_policy in service.target_tracking_scaling_policies.values():
                if target_tracking_scaling_policy.enabled == True:
                    uses_scaling = True
                    uses_target_tracking_scaling = True
                    continue

            desired_tasks_param = self.create_cfn_parameter(
                param_type='String',
                name=f'{cfn_service_name}DesiredTasks',
                description='The desired number of tasks for the Service.',
                value=service.desired_count,
                ignore_changes=uses_scaling,
            )
            service_dict['DesiredCount'] = troposphere.Ref(desired_tasks_param)
            minimum_tasks_param = None
            maximum_tasks_param = None
            if uses_scaling:
                minimum_tasks_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'{cfn_service_name}MinimumTasks',
                    description='The minimum number of tasks for the Service.',
                    value=service.minimum_tasks,
                )
                maximum_tasks = service.maximum_tasks
                if maximum_tasks == 0 and service.desired_count > 0:
                    maximum_tasks = service.desired_count
                maximum_tasks_param = self.create_cfn_parameter(
                    param_type='String',
                    name=f'{cfn_service_name}MaximumTasks',
                    description='The maximum number of tasks for the Service.',
                    value=maximum_tasks,
                )

            # awsvpc NetworkConfiguration
            if service.vpc_config != None:
                sg_name = self.create_cfn_logical_id(f'SecurityGroups{service.name}')
                security_groups_param = self.create_cfn_ref_list_param(
                    name=sg_name,
                    param_type='List<AWS::EC2::SecurityGroup::Id>',
                    description=f'Security Group List for Service {service.name}',
                    value=service.vpc_config.security_groups,
                    ref_attribute='id',
                )
                segment_ref = service.vpc_config.segments[0] + '.subnet_id_list'
                segment_name = self.create_cfn_logical_id(f'Segments{service.name}')
                segment_param = self.create_cfn_parameter(
                    name=segment_name,
                    param_type='List<AWS::EC2::Subnet::Id>',
                    description=f'VPC Subnet Id List for Service {service.name}',
                    value=segment_ref
                )
                cfn_assign_public_ip = 'DISABLED'
                if service.vpc_config.assign_public_ip:
                    cfn_assign_public_ip = 'ENABLED'
                service_dict['NetworkConfiguration'] = {
                    'AwsvpcConfiguration': {
                        'AssignPublicIp': cfn_assign_public_ip,
                        'SecurityGroups': troposphere.Ref(security_groups_param),
                        'Subnets': troposphere.Ref(segment_param),
                    }
                }

            # Service Discovery
            if service.hostname != None:
                service_discovery_res = troposphere.servicediscovery.Service(
                    title=self.create_cfn_logical_id(f'DiscoveryService{service.name}'),
                    DnsConfig=troposphere.servicediscovery.DnsConfig(
                        DnsRecords=[
                            # troposphere.servicediscovery.DnsRecord(
                            #     TTL='60',
                            #     Type='A'
                            # ),
                            troposphere.servicediscovery.DnsRecord(
                                TTL='60',
                                Type='SRV'
                            )
                        ]
                    ),
                    HealthCheckCustomConfig=troposphere.servicediscovery.HealthCheckCustomConfig(FailureThreshold=float(1)),
                    NamespaceId=troposphere.Ref(private_dns_namespace_res),
                    Name=service.name,
                )
                service_discovery_res.DependsOn = [private_dns_namespace_res]
                self.template.add_resource(service_discovery_res)
                service_dict['ServiceRegistries'] = []
                for load_balancer in service.load_balancers:
                    service_registry_dict = {
                        'RegistryArn': troposphere.GetAtt(service_discovery_res, 'Arn'),
                        'ContainerName': load_balancer.container_name,
                        'ContainerPort': load_balancer.container_port,
                    }
                    # ToDo: add Port when needed ... 'Port': ?,
                    service_dict['ServiceRegistries'].append(service_registry_dict)

            # convert TargetGroup ref to a Parameter
            lb_idx = 0
            if 'LoadBalancers' in service_dict:
                for lb in service_dict['LoadBalancers']:
                    target_group_ref = lb['TargetGroupArn']
                    tg_param = self.create_cfn_parameter(
                        name=self.create_cfn_logical_id(f'TargetGroup{service.name}{lb_idx}'),
                        param_type='String',
                        description='Target Group ARN',
                        value=target_group_ref + '.arn',
                    )
                    lb['TargetGroupArn'] = troposphere.Ref(tg_param)
                    lb_idx += 1

            # Health check grace period is only valid for services configured to use load balancers
            if lb_idx == 0:
                del service_dict['HealthCheckGracePeriodSeconds']

            # Replace TaskDefinition name with a TaskDefinition ARN
            if 'TaskDefinition' in service_dict:
                service_dict['TaskDefinition'] = troposphere.Ref(
                    ecs_config.task_definitions[service_dict['TaskDefinition']]._troposphere_res
                )

            # Capacity Providers
            # Service-specific Capacity Provider
            if len(service.capacity_providers) > 0:
                # ToDo: adjust cfn_export not to set LaunchType
                del service_dict['LaunchType']
                provider_cfn = []
                for provider in service.capacity_providers:
                    # ToDo: validate that ASG is configured as a Capacity Provider
                    asg = get_model_obj_from_ref(provider.provider, self.project)
                    provide_dict = {'CapacityProvider': asg.ecs.capacity_provider.get_aws_name()}
                    if provider.base != None:
                        provide_dict['Base'] = provider.base
                    if provider.weight != None:
                        provide_dict['Weight'] = provider.weight
                    provider_cfn.append(provide_dict)
                service_dict['CapacityProviderStrategy'] = provider_cfn
            # Default to ECSCluster Capacity Provider
            # Only use this default if there is no launch_type specified
            elif len(cluster_obj.capacity_providers) > 0:
                if service.launch_type == None:
                    # ToDo: adjust cfn_export not to set LaunchType
                    del service_dict['LaunchType']
                    provider_cfn = []
                    for provider in cluster_obj.capacity_providers:
                        # ToDo: validate that ASG is configured as a Capacity Provider
                        asg = get_model_obj_from_ref(provider.provider, self.project)
                        provide_dict = {'CapacityProvider': asg.ecs.capacity_provider.get_aws_name()}
                        if provider.base != None:
                            provide_dict['Base'] = provider.base
                        if provider.weight != None:
                            provide_dict['Weight'] = provider.weight
                        provider_cfn.append(provide_dict)
                    service_dict['CapacityProviderStrategy'] = provider_cfn

            # ECS Service Resource
            service_res = troposphere.ecs.Service.from_dict(
                cfn_service_name,
                service_dict
            )
            self.template.add_resource(service_res)

            # ECS Scaling: TargetTracking Scaling
            scalable_target_res = None
            if uses_target_tracking_scaling:
                # ScalableTarget
                scalable_target_dict = {}
                scalable_target_dict['ServiceNamespace'] = 'ecs'
                scalable_target_dict['MinCapacity'] = troposphere.Ref(minimum_tasks_param)
                scalable_target_dict['MaxCapacity'] = troposphere.Ref(maximum_tasks_param)
                scalable_target_dict['ResourceId'] = troposphere.Join('/', [
                    'service', troposphere.Ref(cluster_name_param), troposphere.GetAtt(service_res, 'Name')
                ])
                # CloudFormation will automatically generate this service-linked Role if it doesn't already exist
                scalable_target_dict['RoleARN'] = f'arn:aws:iam::{self.account_ctx.id}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService'
                scalable_target_dict['ScalableDimension'] = 'ecs:service:DesiredCount'
                scalable_target_dict['SuspendedState'] = {
                    "DynamicScalingInSuspended" : service.suspend_scaling,
                    "DynamicScalingOutSuspended" : service.suspend_scaling,
                    "ScheduledScalingSuspended" : service.suspend_scaling,
                }
                scalable_target_res = troposphere.applicationautoscaling.ScalableTarget.from_dict(
                    cfn_service_name + 'ScalableTarget',
                    scalable_target_dict
                )
                self.template.add_resource(scalable_target_res)

            for target_tracking_policy in service.target_tracking_scaling_policies.values():
                if target_tracking_policy.enabled == False:
                    continue

                # ScalingPolicies
                scaling_policy_dict = {}
                scaling_policy_dict['PolicyName'] = self.create_cfn_logical_id(f"{service.name}{target_tracking_policy.name}Policy")
                scaling_policy_dict['PolicyType'] = 'TargetTrackingScaling'
                scaling_policy_dict['ScalingTargetId'] = troposphere.Ref(scalable_target_res)
                scaling_policy_dict['TargetTrackingScalingPolicyConfiguration'] = {
                    "DisableScaleIn": target_tracking_policy.disable_scale_in,
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": target_tracking_policy.predefined_metric,
                    },
                    "ScaleInCooldown": target_tracking_policy.scale_in_cooldown,
                    "ScaleOutCooldown": target_tracking_policy.scale_out_cooldown,
                    "TargetValue": target_tracking_policy.target,
                }
                if target_tracking_policy.predefined_metric == 'ALBRequestCountPerTarget':
                    target_group = get_model_obj_from_ref(target_tracking_policy.target_group, self.project)
                    load_balancer = get_parent_by_interface(target_group, ILoadBalancer)
                    lb_name = self.create_cfn_logical_id('ALBFullName' + md5sum(str_data=load_balancer.paco_ref_parts))
                    tg_name = self.create_cfn_logical_id('TargetGroupFullName' + md5sum(str_data=target_group.paco_ref_parts))
                    if lb_name not in alb_params:
                        alb_params[lb_name] = self.create_cfn_parameter(
                            name=lb_name,
                            param_type='String',
                            description='ALBFullName',
                            value=load_balancer.paco_ref + '.fullname',
                        )
                    if tg_name not in target_group_params:
                        target_group_params[tg_name] = self.create_cfn_parameter(
                            name=tg_name,
                            param_type='String',
                            description='TargetGroupFullName',
                            value=target_group.paco_ref + '.fullname',
                        )
                    resource_label = troposphere.Join('/', [
                        troposphere.Ref(alb_params[lb_name]),
                        troposphere.Ref(target_group_params[tg_name]),
                    ])
                    scaling_policy_dict['TargetTrackingScalingPolicyConfiguration']['PredefinedMetricSpecification']['ResourceLabel'] = resource_label

                scaling_policy_res = troposphere.applicationautoscaling.ScalingPolicy.from_dict(
                    self.create_cfn_logical_id(f"{cfn_service_name}{target_tracking_policy.name}ScalingPolicy"),
                    scaling_policy_dict
                )
                self.template.add_resource(scaling_policy_res)

            # Outputs
            self.create_output(
                title=service_res.title + 'ARN',
                description="Service ARN",
                value=troposphere.Ref(service_res),
                ref=service.paco_ref_parts + ".arn"
            )
            self.create_output(
                title=service_res.title + 'Name',
                description="Service Name",
                value=troposphere.GetAtt(service_res, 'Name'),
                ref=service.paco_ref_parts + ".name"
            )

    def add_log_group(self, loggroup_name, expire_events_after_days):
        "Add a LogGroup resource to the template"
        cfn_export_dict = {
            'LogGroupName': loggroup_name,
        }
        if expire_events_after_days != 'Never' and expire_events_after_days != '':
            cfn_export_dict['RetentionInDays'] = int(expire_events_after_days)
        loggroup_logical_id = self.create_cfn_logical_id('LogGroup' + loggroup_name)
        loggroup_resource = troposphere.logs.LogGroup.from_dict(
            loggroup_logical_id,
            cfn_export_dict
        )
        self.template.add_resource(loggroup_resource)
        return loggroup_resource
