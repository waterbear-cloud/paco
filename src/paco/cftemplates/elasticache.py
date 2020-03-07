from paco.cftemplates.cftemplates import StackTemplate
from paco.models.references import Reference
from paco.models import vocabulary, schemas
import troposphere
import troposphere.elasticache


class ElastiCache(StackTemplate):
    """
    Creates an Amazon ElastiCache Redis replication group (AWS::ElastiCache::ReplicationGroup).
    A replication group is a collection of cache clusters, where one of the clusters is a
    primary read-write cluster and the others are read-only replicas.
    """
    def __init__(self, stack, paco_ctx):
        elasticache_config = stack.resource
        config_ref = elasticache_config.paco_ref_parts
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ElastiCache', self.resource_group_name, self.resource.name, elasticache_config.engine )

        # Troposphere Template Generation
        self.init_template('ElastiCache: {} - {}'.format(
            elasticache_config.engine,
            elasticache_config.engine_version
        ))

        # if disabled then leave an empty placeholder and finish
        if not elasticache_config.is_enabled(): return

        # Security Groups
        sg_params = []
        vpc_sg_list = []
        for sg_ref in elasticache_config.security_groups:
            ref = Reference(sg_ref)
            sg_param_name = 'SecurityGroupId'+ref.parts[-2]+ref.parts[-1]
            sg_param = self.create_cfn_parameter(
                name=sg_param_name,
                param_type='String',
                description='VPC Security Group Id',
                value=sg_ref + '.id',
            )
            sg_params.append(sg_param)
            vpc_sg_list.append(troposphere.Ref(sg_param))

        # Subnet Ids
        subnet_ids_param = self.create_cfn_parameter(
            name='SubnetIdList',
            param_type='List<String>',
            description='List of Subnet Ids to provision ElastiCache nodes',
            value=elasticache_config.segment+'.subnet_id_list',
        )

        # ElastiCache Subnet Group
        subnet_group_dict = {
            'Description': troposphere.Ref('AWS::StackName'),
            'SubnetIds' : troposphere.Ref(subnet_ids_param)
        }
        subnet_group_res = troposphere.elasticache.SubnetGroup.from_dict(
            'SubnetGroup',
            subnet_group_dict
        )
        self.template.add_resource(subnet_group_res)

        # ElastiCache Resource
        elasticache_dict = elasticache_config.cfn_export_dict
        elasticache_dict['SecurityGroupIds'] = vpc_sg_list
        elasticache_dict['CacheSubnetGroupName'] = troposphere.Ref(subnet_group_res)
        if elasticache_config.description:
            elasticache_dict['ReplicationGroupDescription'] = elasticache_config.description
        else:
            elasticache_dict['ReplicationGroupDescription'] = troposphere.Ref('AWS::StackName')

        cfn_cache_cluster_name = 'ReplicationGroup'
        cache_cluster_res = troposphere.elasticache.ReplicationGroup.from_dict(
            cfn_cache_cluster_name,
            elasticache_dict
        )
        self.template.add_resource(cache_cluster_res)

        # Outputs
        self.create_output(
            title='PrimaryEndPointAddress',
            description='ElastiCache PrimaryEndpoint Address',
            value=troposphere.GetAtt(cache_cluster_res, 'PrimaryEndPoint.Address'),
            ref=config_ref + ".primaryendpoint.address"
        )
        self.create_output(
            title='PrimaryEndPointPort',
            description='ElastiCache PrimaryEndpoint Port',
            value=troposphere.GetAtt(cache_cluster_res, 'PrimaryEndPoint.Port'),
            ref=config_ref + ".primaryendpoint.port"
        )
        self.create_output(
            title='ReadEndPointAddresses',
            description='ElastiCache ReadEndpoint Addresses',
            value=troposphere.GetAtt(cache_cluster_res, 'ReadEndPoint.Addresses'),
            ref=config_ref + ".readendpoint.addresses"
        )
        self.create_output(
            title='ReadEndPointPorts',
            description='ElastiCache ReadEndpoint Ports',
            value=troposphere.GetAtt(cache_cluster_res, 'ReadEndPoint.Ports'),
            ref=config_ref + ".readendpoint.ports",
        )
