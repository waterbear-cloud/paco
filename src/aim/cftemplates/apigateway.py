"""
CloudFormation templates for API Gateway
"""

import troposphere
import troposphere.apigateway
from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references
from aim.models.references import Reference


class ApiGatewayRestApi(CFTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        aws_name,
        app_id,
        grp_id,
        apigatewayrestapi,
        config_ref=None
    ):
        aws_name='-'.join([aws_name, 'ApiGatewayRestApi'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name,
            stack_group=stack_group,
            stack_tags=stack_tags
        )
        self.apigatewayrestapi = apigatewayrestapi

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description(apigatewayrestapi.title)


        # ---------------------------------------------------------------------------
        # Parameters

        method_params = []
        for method in self.apigatewayrestapi.methods.values():
            param_name = 'MethodArn' + self.normalize_resource_name(method.name)
            lambda_arn_param = self.gen_parameter(
                name=param_name,
                param_type='String',
                description='Lambda ARN parameter.',
                value=method.integration_lambda,
                use_troposphere=True
            )
            method.parameter_ref = troposphere.Ref(param_name)
            template.add_parameter(lambda_arn_param)

        # ---------------------------------------------------------------------------
        # Resources
        restapi_logical_id = 'ApiGatewayRestApi'
        restapi_resource = troposphere.apigateway.RestApi.from_dict(
            restapi_logical_id,
            self.apigatewayrestapi.cfn_export_dict
        )
        template.add_resource(restapi_resource)

        # Resource
        for resource in self.apigatewayrestapi.resources.values():
            resource_id = 'ApiGatewayResource' + self.normalize_resource_name(resource.name)
            cfn_export_dict = resource.cfn_export_dict
            if resource.parent_id == "RootResourceId":
                cfn_export_dict["ParentId"] = troposphere.GetAtt(restapi_resource, "RootResourceId")
                cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            else:
                raise NotImplemented("ToDo: handle nested resources")
            resource_resource = troposphere.apigateway.Resource.from_dict(resource_id, cfn_export_dict)
            resource.resource = resource_resource
            resource_resource.DependsOn = restapi_logical_id
            template.add_resource(resource_resource)

        # Method
        for method in self.apigatewayrestapi.methods.values():
            method_id = 'ApiGatewayMethod' + self.normalize_resource_name(method.name)
            cfn_export_dict = method.cfn_export_dict
            for resource in self.apigatewayrestapi.resources.values():
                if resource.name == method.resource_id:
                    cfn_export_dict["ResourceId"] = troposphere.Ref(resource.resource)
                    cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
                    uri = troposphere.Join('', ["arn:aws:apigateway:", method.region_name, ":lambda:path/2015-03-31/functions/", method.parameter_ref, "/invocations"])
                    cfn_export_dict["Integration"]["Uri"] = uri
            method_resource = troposphere.apigateway.Method.from_dict(method_id, cfn_export_dict)
            method_resource.DependsOn = restapi_logical_id
            template.add_resource(method_resource)

        # Model
        # Stage
        # Deployment
        breakpoint()
        # Generate the Template
        self.set_template(template.to_yaml())