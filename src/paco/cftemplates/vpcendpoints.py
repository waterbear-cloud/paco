from paco.cftemplates.cftemplates import StackTemplate
from paco.models import schemas
from paco.models.locations import get_parent_by_interface
from paco.utils import md5sum
import troposphere.ec2


class VPCEndpoints(StackTemplate):
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('Endpoints', self.resource_group_name, self.resource.name)

        # Troposphere Template Initialization
        self.init_template('VPC Endpoints')

        if self.resource.endpoints == None:
            return
        # Resource
        network_config = get_parent_by_interface(self.resource, schemas.INetwork)
        segment_cache = []
        route_table_id_list = []
        subnet_id_list = []
        security_group_cache = {}
        vpc_id_param = self.create_cfn_parameter(
            name='VpcId',
            param_type='AWS::EC2::VPC::Id',
            description='The VPC Id',
            value=f'{network_config.paco_ref}.vpc.id'
        )
        for (endpoint_name, endpoint) in self.resource.endpoints.items():
            if endpoint.is_enabled() == False:
                continue
            # Generate a RouteTable Ids
            for segment_id in endpoint.segments:
                for az_idx in range(1, network_config.availability_zones+1):
                    if endpoint.availability_zone != 'all' and str(az_idx) != endpoint.availability_zone:
                        continue
                    # Route Table: TODO: Not needed until we support GATEWAY endpoint types
                    # route_table_id_param_name = self.create_cfn_logical_id_join(
                    #     str_list=['RouteTable', segment_id, 'AZ', str(az_idx)],
                    #     camel_case=True
                    # )
                    # if route_table_id_param_name in segment_cache:
                    #     continue
                    # segment_cache.append(route_table_id_param_name)
                    # route_table_id_param = self.create_cfn_parameter(
                    #     name=route_table_id_param_name,
                    #     param_type='String',
                    #     description=f'RouteTable ID for {segment_id} AZ{az_idx}',
                    #     value=f'{network_config.paco_ref}.vpc.segments.{segment_id}.az{az_idx}.route_table.id',
                    # )
                    # route_table_id_list.append(troposphere.Ref(route_table_id_param))
                    # Subnet Id
                    subnet_id_param_name = self.create_cfn_logical_id_join(
                        str_list=['SubnetId', segment_id, 'AZ', str(az_idx)],
                        camel_case=True
                    )
                    if subnet_id_param_name in segment_cache:
                        continue
                    segment_cache.append(subnet_id_param_name)
                    subnet_id_param = self.create_cfn_parameter(
                        name=subnet_id_param_name,
                        param_type='String',
                        description=f'Subnet ID for {segment_id} AZ{az_idx}',
                        value=f'{network_config.paco_ref}.vpc.segments.{segment_id}.az{az_idx}.subnet_id',
                    )
                    subnet_id_list.append(troposphere.Ref(subnet_id_param))


            name_hash = md5sum(str_data=endpoint.security_group)
            security_group_param_name = self.create_cfn_logical_id_join(
                str_list=['SecurityGroupId', name_hash]
            )
            if security_group_param_name not in security_group_cache:
                security_group_param = self.create_cfn_parameter(
                    name=security_group_param_name,
                    param_type='String',
                    description=f'SecurityGroupId for endpoint service {endpoint_name}',
                    value=endpoint.security_group+'.id'
                )
                security_group_cache[security_group_param_name] = troposphere.Ref(security_group_param)

            security_group_id_list = [security_group_cache[security_group_param_name]]
            endpoint_dict = {
                'ServiceName': f'com.amazonaws.{self.aws_region}.{endpoint.service}',
                #'RouteTableIds': route_table_id_list,
                'SubnetIds': subnet_id_list,
                'SecurityGroupIds': security_group_id_list,
                'PrivateDnsEnabled': True,
                'VpcId': troposphere.Ref(vpc_id_param),
                'VpcEndpointType': 'Interface'
            }

            if endpoint.service in ['s3', 'ec2']:
                endpoint_dict['PrivateDnsEnabled'] = False

            endpoint_res = troposphere.ec2.VPCEndpoint.from_dict(
                self.create_cfn_logical_id(endpoint_name),
                endpoint_dict
            )
            self.template.add_resource( endpoint_res )


        # Outputs
        # self.create_output(
        #     title='ExampleResourceId',
        #     description="Example resource Id.",
        #     value=troposphere.Ref(example_res),
        #     ref=self.resource.paco_ref_parts + ".id"
        # )
