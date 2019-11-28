"""
CloudFormation templates for API Gateway
"""

import awacs.sts
import awacs.awslambda
import troposphere
import troposphere.apigateway
import troposphere.awslambda
import troposphere.iam
from paco.cftemplates.cftemplates import CFTemplate
from paco.models import references
from paco.models.references import Reference
from awacs.aws import Allow, Statement, Policy, Principal


class ApiGatewayRestApi(CFTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        app_id,
        grp_id,
        res_id,
        apigatewayrestapi,
        config_ref=None,
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            iam_capabilities=["CAPABILITY_IAM"],
            enabled=apigatewayrestapi.is_enabled(),
        )
        self.apigatewayrestapi = apigatewayrestapi
        self.set_aws_name('ApiGatewayRestApi', grp_id, res_id)

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization

        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description(apigatewayrestapi.title)


        # ---------------------------------------------------------------------------
        # Parameters

        method_params = []
        for method in self.apigatewayrestapi.methods.values():
            param_name = 'MethodArn' + self.create_cfn_logical_id(method.name)
            lambda_arn_param = self.create_cfn_parameter(
                name=param_name,
                param_type='String',
                description='Lambda ARN parameter.',
                value=method.integration.integration_lambda + '.arn',
                use_troposphere=True
            )
            method.parameter_arn_ref = troposphere.Ref(param_name)
            template.add_parameter(lambda_arn_param)

        # ---------------------------------------------------------------------------
        # Resources

        restapi_logical_id = 'ApiGatewayRestApi'
        restapi_resource = troposphere.apigateway.RestApi.from_dict(
            restapi_logical_id,
            self.apigatewayrestapi.cfn_export_dict
        )
        template.add_resource(restapi_resource)

        # Model
        for model in self.apigatewayrestapi.models.values():
            model.logical_id = self.create_cfn_logical_id('ApiGatewayModel' + model.name)
            cfn_export_dict = model.cfn_export_dict
            cfn_export_dict['RestApiId'] = troposphere.Ref(restapi_resource)
            if 'Schema' not in cfn_export_dict:
                cfn_export_dict['Schema'] = {}
            model_resource = troposphere.apigateway.Model.from_dict(model.logical_id, cfn_export_dict)
            model.resource = model_resource
            template.add_resource(model_resource)

        # Resource
        for resource in self.apigatewayrestapi.resources.values():
            resource_id = 'ApiGatewayResource' + self.create_cfn_logical_id(resource.name)
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
            method_id = 'ApiGatewayMethod' + self.create_cfn_logical_id(method.name)
            method.logical_id = method_id
            cfn_export_dict = method.cfn_export_dict
            for resource in self.apigatewayrestapi.resources.values():
                if resource.name == method.resource_id:
                    cfn_export_dict["ResourceId"] = troposphere.Ref(resource.resource)
            if 'ResourceId' not in cfn_export_dict:
                cfn_export_dict["ResourceId"] = troposphere.GetAtt(restapi_resource, 'RootResourceId')
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            uri = troposphere.Join('', ["arn:aws:apigateway:", method.region_name, ":lambda:path/2015-03-31/functions/", method.parameter_arn_ref, "/invocations"])
            cfn_export_dict["Integration"]["Uri"] = uri

            if method.integration.integration_type == 'AWS_PROXY':
                # IAM Role - allows API Gateway to invoke Lambda
                # ToDo: enable Api Gateway to invoke things other than Lambda ...
                iam_role_resource = troposphere.iam.Role(
                    self.create_cfn_logical_id('ApiGatewayIamRole' + self.apigatewayrestapi.name + method.name),
                    Path='/',
                    AssumeRolePolicyDocument=Policy(
                        Version='2012-10-17',
                        Statement=[
                            Statement(
                                Effect=Allow,
                                Action=[awacs.sts.AssumeRole],
                                Principal=Principal('Service',['apigateway.amazonaws.com'])
                            )
                        ],
                    ),
                    Policies=[
                        troposphere.iam.Policy(
                            PolicyName=self.create_cfn_logical_id('LambdaAccessApiGateway' + self.apigatewayrestapi.name + method.name),
                            PolicyDocument=Policy(
                                Version='2012-10-17',
                                Statement=[
                                    Statement(
                                        Effect=Allow,
                                        Action=[awacs.awslambda.InvokeFunction],
                                        Resource=[method.parameter_arn_ref],
                                    )
                                ]
                            )
                        )
                    ]
                )
                template.add_resource(iam_role_resource)
                cfn_export_dict["Integration"]["Credentials"] = troposphere.GetAtt(iam_role_resource, "Arn")

            elif method.integration.integration_type == 'AWS':
                # Enable Lambda (custom) integration
                # When send to a Lambda (Custom) the HTTP Method must always be POST regardless of
                # the HttpMethod
                cfn_export_dict["Integration"]["IntegrationHttpMethod"] = "POST"
                lambda_permission_resource = troposphere.awslambda.Permission(
                    self.create_cfn_logical_id('LambdaPermissionApiGateway' + method.name),
                    Action = 'lambda:InvokeFunction',
                    FunctionName = method.parameter_arn_ref,
                    Principal = 'apigateway.amazonaws.com',
                    SourceArn = troposphere.Sub(
                        "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${%s}/*/%s/" % (
                            restapi_logical_id, method.http_method
                        )
                    )
                )
                template.add_resource(lambda_permission_resource)

            # look-up the method_names and assign a Ref to the model resource
            # ToDo: validate model_names in the model
            responses = []
            for method_response in method.method_responses:
                response_dict = {"StatusCode": method_response.status_code}
                if method_response.response_models:
                    response_dict["ResponseModels"] = {}
                    for response_model in method_response.response_models:
                        for model in self.apigatewayrestapi.models.values():
                            if model.name == response_model.model_name:
                                response_dict["ResponseModels"][response_model.content_type] = troposphere.Ref(model.resource)
                responses.append(response_dict)
            cfn_export_dict["MethodResponses"] = responses

            method_resource = troposphere.apigateway.Method.from_dict(method_id, cfn_export_dict)
            method_resource.DependsOn = restapi_logical_id
            template.add_resource(method_resource)

        # Deployment
        deployment_resource = troposphere.apigateway.Deployment.from_dict(
            'ApiGatewayDeployment',
            {'Description': 'Deployment',
             'RestApiId': troposphere.Ref(restapi_resource) }
        )
        # ToDo: Deployment depends upon all Methods
        for method in self.apigatewayrestapi.methods.values():
            deployment_resource.DependsOn = method.logical_id
        template.add_resource(deployment_resource)

        # Stage
        for stage in self.apigatewayrestapi.stages.values():
            stage_id = self.create_cfn_logical_id('ApiGatewayStage' + stage.name)
            cfn_export_dict = stage.cfn_export_dict
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            cfn_export_dict["DeploymentId"] = troposphere.Ref(deployment_resource)
            stage_resource = troposphere.apigateway.Stage.from_dict(stage_id, cfn_export_dict)
            template.add_resource(stage_resource)

        # Generate the Template
        self.set_template(template.to_yaml())