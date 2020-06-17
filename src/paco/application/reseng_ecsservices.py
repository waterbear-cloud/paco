from paco import cftemplates
from paco.application.res_engine import ResourceEngine
from paco.models.locations import get_parent_by_interface
from paco.models import schemas
import paco.models.iam


class ECSServicesResourceEngine(ResourceEngine):
    def init_resource(self):
        # Service Role
        # This Role is no longer needed AFAIK - kteague
        # role=None
        # if self.resource.is_enabled():
        #     role = self.create_service_role()

        # Task Execution Role
        if self.resource.is_enabled():
            task_execution_role = self.create_task_execution_role()

        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            cftemplates.ECSServices,
            stack_tags=self.stack_tags,
            extra_context={'task_execution_role': task_execution_role},
        )

    def create_task_execution_role(self):
        "ECS Task Execution IAM Role"
        netenv = get_parent_by_interface(self.resource, schemas.INetworkEnvironment)
        iam_role_id = self.gen_iam_role_id(netenv.name, 'ECSTaskExecution')
        role = paco.models.iam.Role(iam_role_id, self.resource)
        statements = [{
            'effect': 'Allow',
            'action': [
                'ecr:GetAuthorizationToken',
                'ecr:BatchCheckLayerAvailability',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'logs:CreateLogStream',
                'logs:PutLogEvent'
            ],
            'resource': ['*'],
        },]
        role.apply_config({
            'enabled': True,
            'path': '/',
            'role_name': iam_role_id,
            'assume_role_policy': {'effect': 'Allow', 'service': ['ecs-tasks.amazonaws.com']},
            'policies': [{'name': 'ECS-TaskExecution', 'statement': statements}],
        })
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=role,
            iam_role_id=iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
        )
        return role

    def create_service_role(self):
        "Service role for ECS to assume"
        netenv = get_parent_by_interface(self.resource, schemas.INetworkEnvironment)
        iam_role_id = self.gen_iam_role_id(netenv.name, 'ECSService')
        role = paco.models.iam.Role(iam_role_id, self.resource)
        statements = [{
            'effect': 'Allow',
            'action': [
                'elasticloadbalancing:DeregisterInstancesFromLoadBalancer',
                'elasticloadbalancing:DeregisterTargets',
                'elasticloadbalancing:Describe*',
                'elasticloadbalancing:RegisterInstancesWithLoadBalancer',
                'elasticloadbalancing:RegisterTargets',
                'ec2:Describe*',
                'ec2:AuthorizeSecurityGroupIngress',
            ],
            'resource': ['*'],
        },]
        role.apply_config({
            'enabled': True,
            'path': '/',
            'role_name': iam_role_id,
            'assume_role_policy': {'effect': 'Allow', 'service': ['ecs.amazonaws.com']},
            'policies': [{'name': 'ECS-Service', 'statement': statements}],
        })
        iam_ctl = self.paco_ctx.get_controller('IAM')
        iam_ctl.add_role(
            region=self.aws_region,
            resource=self.resource,
            role=role,
            iam_role_id=iam_role_id,
            stack_group=self.stack_group,
            stack_tags=self.stack_tags,
        )
        return role
