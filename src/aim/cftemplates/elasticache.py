import os
import troposphere
import troposphere.elasticache
from aim.cftemplates.cftemplates import CFTemplate
from aim.cftemplates.cftemplates import Parameter
from aim.cftemplates.cftemplates import StackOutputParam
from aim.models.references import Reference
from io import StringIO
from enum import Enum
import base64
from aim.models import vocabulary, schemas


class ElastiCache(CFTemplate):
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 stack_group,
                 stack_tags,

                 aws_name,
                 app_id,
                 grp_id,
                 elasticache_config,
                 config_ref=None):

        aws_name = '-'.join([aws_name, 'ElastiCache', elasticache_config.engine])
        super().__init__(aim_ctx,
                         account_ctx,
                         aws_region,
                         enabled=elasticache_config.is_enabled(),
                         config_ref=config_ref,
                         aws_name=aws_name,
                         stack_group=stack_group,
                         stack_tags=stack_tags)

        if elasticache_config.is_enabled() == True:
            # ---------------------------------------------------------------------------
            # Parameters

            # Security Groups
            sg_params = []
            vpc_sg_list = []
            for sg_ref in elasticache_config.security_groups:
                ref = Reference(sg_ref)
                sg_param_name = 'SecurityGroupId'+ref.parts[-2]+ref.parts[-1]
                sg_param = self.gen_parameter(
                    name=sg_param_name,
                    param_type='String',
                    description='VPC Security Group Id',
                    value=sg_ref + '.id',
                    use_troposphere=True
                )
                sg_params.append(sg_param)
                vpc_sg_list.append(troposphere.Ref(sg_param))

            # Subnet Ids
            subnet_ids_param = self.gen_parameter(
                name='SubnetIdList',
                param_type='List<String>',
                description='List of Subnet Ids to provision ElastiCache nodes',
                value=elasticache_config.segment+'.subnet_id_list',
                use_troposphere=True
            )

            # ---------------------------------------------------------------------------
            # ElastiCache Subnet Group
            subnet_group_dict = {
                'Description': troposphere.Ref('AWS::StackName'),
                'SubnetIds' : troposphere.Ref(subnet_ids_param)
            }
            subnet_group_res = troposphere.elasticache.SubnetGroup.from_dict(
                'SubnetGroup',
                subnet_group_dict
            )

            # ---------------------------------------------------------------------------
            # ElastiCache Parameter Group Resource
            #param_group_dict = {
            #    'CacheParameterGroupFamily': elasticache_config.cache_parameter_group_family,
            #    'Description': troposphere.Ref('AWS::StackName'),
            #    'Properties': None
            #}

            #param_group_res = troposphere.elasticache.ParameterGroup.from_dict(
            #    'ParameterGroup',
            #    param_group_dict
            #)

            # ---------------------------------------------------------------------------
            # Elasticache Resource
            elasticache_dict = {
                'Engine': elasticache_config.engine,
                'EngineVersion': elasticache_config.engine_version,
                'Port': elasticache_config.port,
                'AtRestEncryptionEnabled': elasticache_config.at_rest_encryption,
                'AutomaticFailoverEnabled': elasticache_config.automatic_failover_enabled,
                'ReplicasPerNodeGroup': elasticache_config.number_of_read_replicas,
                'ReplicationGroupDescription': troposphere.Ref('AWS::StackName'),
                'AutoMinorVersionUpgrade': elasticache_config.auto_minor_version_upgrade,
                'CacheNodeType': elasticache_config.cache_node_type,
                'PreferredMaintenanceWindow': elasticache_config.maintenance_preferred_window,
                'SecurityGroupIds': vpc_sg_list,
                #'CacheParameterGroupName': troposphere.Ref(param_group_res),
                'CacheSubnetGroupName': troposphere.Ref(subnet_group_res)
            }

            # Redis Cache Cluster
            cfn_cache_cluster_name = 'ReplicationGroup'

            cache_cluster_res = troposphere.elasticache.ReplicationGroup.from_dict(
                cfn_cache_cluster_name,
                elasticache_dict
            )

        # Troposphere Template Generation
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description('ElastiCache: {} - {}'.format(
            elasticache_config.engine,
            elasticache_config.engine_version
        ))
        if elasticache_config.is_enabled() == True:

            for sg_param in sg_params:
                template.add_parameter(sg_param)
            template.add_parameter( subnet_ids_param)
            #template.add_resource( param_group_res )
            template.add_resource( subnet_group_res )
            template.add_resource( cache_cluster_res )
        else:
            # There is no way to stop a cluster, it must be removed.
            # Leave a dummy resource to allow the stack to delete
            # the resources.
            template.add_resource(
                troposphere.cloudformation.WaitConditionHandle(title="DummyResource")
            )

        self.set_template(template.to_yaml())

