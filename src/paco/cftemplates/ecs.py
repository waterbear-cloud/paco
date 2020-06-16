from paco.cftemplates.cftemplates import StackTemplate
from paco.utils import prefixed_name
import troposphere
import troposphere.ecs


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
    def __init__(self, stack, paco_ctx):
        ecs_config = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ECS Services', self.resource_group_name, self.resource.name)

        self.init_template('Elastic Container Service (ECS) Services and TaskDefinitions')
        if not ecs_config.is_enabled(): return

        # TaskDefinitions
        for task in ecs_config.task_definitions.values():
            task_dict = task.cfn_export_dict
            index = 0
            task._depends_on = []
            for container_definition in task.container_definitions.values():
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
        cluster_param = self.create_cfn_parameter(
            name='Cluster',
            param_type='String',
            description='Cluster Name',
            value=ecs_config.cluster + '.name',
        )

        #  Services
        for service in ecs_config.services.values():
            service_dict = service.cfn_export_dict
            # convert TargetGroup ref to a Parameter
            lb_idx = 0
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

            # ECS Service Role
            # service_role_arn_param = self.create_cfn_parameter(
            #     param_type='String',
            #     name='ServiceRoleArn',
            #     description='ECS service Role',
            #     value=role.get_arn()
            # )
            # service_dict['Role'] = troposphere.Ref(service_role_arn_param)

            service_dict['Cluster'] = troposphere.Ref(cluster_param)
            service_res = troposphere.ecs.Service.from_dict(
                self.create_cfn_logical_id('Service' + service.name),
                service_dict
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
