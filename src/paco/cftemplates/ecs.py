from paco.cftemplates.cftemplates import StackTemplate
from paco.utils import prefixed_name, md5sum
from paco.core.exception import UnsupportedCloudFormationParameterType
from paco.models import references
import troposphere
import troposphere.ecs
import troposphere.servicediscovery


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


class ECSServices(StackTemplate):
    def __init__(self, stack, paco_ctx, task_execution_role):
        ecs_config = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ECS Services', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Container Service (ECS) Services and TaskDefinitions')
        if not ecs_config.is_enabled(): return

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
                # ContainerDefinition Environment variables
                for env_pair in container_definition.environment:
                    key = env_pair.name
                    value = env_pair.value
                    # only paco refs are passed as Parameters to avoid tripping the 60 Parameter CloudFormation limit
                    if references.is_ref(value):
                        if type(value) == type(str()):
                            param_type = 'String'
                        elif type(value) == type(int()) or type(value) == type(float()):
                            param_type = 'Number'
                        else:
                            breakpoint()
                            raise UnsupportedCloudFormationParameterType(
                                "Can not cast {} of type {} to a CloudFormation Parameter type.".format(
                                    value, type(value)
                                )
                            )
                        param_name = self.create_cfn_logical_id(f'{task.name}{container_definition.name}{key}')
                        environment_param = self.create_cfn_parameter(
                            param_type=param_type,
                            name=param_name,
                            description=f'Environment variable for container definition {container_definition.name} for task definition {task.name}',
                            value=value,
                        )
                        value = troposphere.Ref(environment_param)
                    if 'Environment' not in task_dict['ContainerDefinitions'][index]:
                        task_dict['ContainerDefinitions'][index]['Environment'] = []
                    task_dict['ContainerDefinitions'][index]['Environment'].append({'Name': key, 'Value': value})

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

            # Setup Secrets
            for task_dict_container_def in task_dict['ContainerDefinitions']:
                if 'Secrets' in task_dict_container_def:
                    for secrets_pair in task_dict_container_def['Secrets']:
                        # Secerts Arn Parameters
                        name_hash = md5sum(str_data=secrets_pair['ValueFrom'])
                        secret_param_name = 'TaskDefinitionSecretArn'+name_hash
                        secret_param = self.create_cfn_parameter(
                            param_type='String',
                            name=secret_param_name,
                            description='The arn of the Secrets Manger Secret.',
                            value=secrets_pair['ValueFrom']+'.arn'
                        )
                        secrets_pair['ValueFrom'] = '!ManualTroposphereRef '+secret_param_name

            task_res = troposphere.ecs.TaskDefinition.from_dict(
                self.create_cfn_logical_id('TaskDefinition' + task.name),
                task_dict,
            )
            task_res.DependsOn = task._depends_on
            self.template.add_resource(task_res)
            task._troposphere_res = task_res

        # Cluster Param
        cluster_param = self.create_cfn_parameter(
            name='Cluster',
            param_type='String',
            description='Cluster Name',
            value=ecs_config.cluster + '.name',
        )

        #  Services
        # ToDo: allow multiple PrivateDnsNamespaces?
        # e.g. if multiple ECSServices want to particpate in the same PrivateDnsNamespace?
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
        for service in ecs_config.services.values():
            service_dict = service.cfn_export_dict

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

            # Replace TaskDefinition name with a TaskDefinition ARN
            if 'TaskDefinition' in service_dict:
                service_dict['TaskDefinition'] = troposphere.Ref(
                    ecs_config.task_definitions[service_dict['TaskDefinition']]._troposphere_res
                )
            service_dict['Cluster'] = troposphere.Ref(cluster_param)
            service_res = troposphere.ecs.Service.from_dict(
                self.create_cfn_logical_id('Service' + service.name),
                service_dict
            )

            # Outputs
            self.create_output(
                title=service_res.title + 'Name',
                description="Service Name",
                value=troposphere.GetAtt(service_res, 'Name'),
                ref=service.paco_ref_parts + ".name"
            )

            self.template.add_resource(service_res)
            # if 'TaskDefinition' in service_dict:
            #     service_res.DependsOn = ecs.task_definitions[service_dict['TaskDefinition']]._troposphere_res

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
