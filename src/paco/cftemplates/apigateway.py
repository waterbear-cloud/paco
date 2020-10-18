"""
CloudFormation template for API Gateway
"""

from awacs.aws import Allow, Statement, Policy, Principal
from paco.cftemplates.cftemplates import StackTemplate
from paco.models.references import get_model_obj_from_ref
from paco.utils import md5sum
import awacs.sts
import awacs.awslambda
import troposphere
import troposphere.apigateway
import troposphere.awslambda
import troposphere.iam


class ApiGatewayRestApi(StackTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx, iam_capabilities=["CAPABILITY_IAM"])
        self.apigatewayrestapi = apigatewayrestapi = stack.resource
        self.set_aws_name('ApiGatewayRestApi', self.resource_group_name, self.resource.name)

        self.init_template('ApiGateway: {}'.format(apigatewayrestapi.title))
        template = self.template
        if not self.apigatewayrestapi.is_enabled():
            return

        # Parameters
        lambda_params = {}
        for method in self.apigatewayrestapi.methods.values():
            if method.integration.integration_lambda != None:
                param_name = 'MethodArn' + self.create_cfn_logical_id(method.name)
                if method.integration.integration_lambda not in lambda_params:
                    lambda_params[method.integration.integration_lambda] = self.create_cfn_parameter(
                        name=param_name,
                        param_type='String',
                        description='Lambda ARN parameter.',
                        value=method.integration.integration_lambda + '.arn',
                    )
                method.parameter_arn_ref = troposphere.Ref(lambda_params[method.integration.integration_lambda])

        # Resources
        restapi_logical_id = 'ApiGatewayRestApi'
        restapi_resource = troposphere.apigateway.RestApi.from_dict(
            restapi_logical_id,
            self.apigatewayrestapi.cfn_export_dict
        )
        template.add_resource(restapi_resource)
        self.create_output(
            title='ApiGatewayRestApiId',
            value=troposphere.Ref(restapi_resource),
            ref=self.apigatewayrestapi.paco_ref_parts + '.id',
        )
        self.create_output(
            title='ApiGatewayRestApiRootResourceId',
            value=troposphere.GetAtt(restapi_resource, "RootResourceId"),
            ref=self.apigatewayrestapi.paco_ref_parts + '.root_resource_id',
        )

        # Authorizers
        if self.apigatewayrestapi.cognito_authorizers != None:
            # monkey patch for Troposphere ... ToDo: file a PR
            troposphere.apigateway.Authorizer.props['AuthorizerUri'] = (str, False)
            self.user_pool_params = {}
            for cog_auth in self.apigatewayrestapi.cognito_authorizers.values():
                provider_arns = []
                for user_pool_ref in cog_auth.user_pools:
                    if user_pool_ref not in self.user_pool_params:
                        self.user_pool_params[user_pool_ref] = self.create_cfn_parameter(
                        name='CognitoUserPool' + md5sum(str_data=user_pool_ref),
                        param_type='String',
                        description='Cognito User Pool ARN',
                        value=user_pool_ref + '.arn',
                    )
                    provider_arns.append(troposphere.Ref(self.user_pool_params[user_pool_ref]))
                cog_auth_resource = troposphere.apigateway.Authorizer(
                    title=self.create_cfn_logical_id(f'CognitoAuthorizer{cog_auth.name}'),
                    Name=cog_auth.name,
                    RestApiId=troposphere.Ref(restapi_resource),
                    IdentitySource='method.request.header.' + cog_auth.identity_source,
                    Type='COGNITO_USER_POOLS',
                    ProviderARNs=provider_arns,
                )
                self.template.add_resource(cog_auth_resource)
                cog_auth.resource = cog_auth_resource

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
            resource_logical_id = 'ApiGatewayResource' + self.create_cfn_logical_id(resource.name)
            cfn_export_dict = resource.cfn_export_dict
            if resource.parent_id == "RootResourceId":
                cfn_export_dict["ParentId"] = troposphere.GetAtt(restapi_resource, "RootResourceId")
                cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            else:
                raise NotImplemented("ToDo: handle nested resources")
            resource_resource = troposphere.apigateway.Resource.from_dict(resource_logical_id, cfn_export_dict)
            resource.resource = resource_resource
            resource_resource.DependsOn = restapi_logical_id
            template.add_resource(resource_resource)
            self.create_output(
                title=self.create_cfn_logical_id(f'ApiGatewayRestApiResource{resource.name}'),
                value=troposphere.Ref(resource_resource),
                ref=resource.paco_ref_parts + '.id',
            )

        # Method
        api_account_name = self.apigatewayrestapi.get_account().name
        for method in self.apigatewayrestapi.methods.values():
            method_id = 'ApiGatewayMethod' + self.create_cfn_logical_id(method.name)
            method.logical_id = method_id
            cfn_export_dict = method.cfn_export_dict
            if method.authorizer != None:
                # ToDo: only Cognito Authorizers
                auth_type, auth_name = method.authorizer.split('.')
                auth_cont = getattr(self.apigatewayrestapi, auth_type)
                auth_obj = auth_cont[auth_name]
                cfn_export_dict["AuthorizerId"] = troposphere.Ref(auth_obj.resource)
                if auth_type == 'cognito_authorizers':
                    cfn_export_dict["AuthorizationType"] = 'COGNITO_USER_POOLS'
            if method.resource_name:
                resource = self.apigatewayrestapi.resources[method.resource_name]
                cfn_export_dict["ResourceId"] = troposphere.Ref(resource.resource)
            else:
                cfn_export_dict["ResourceId"] = troposphere.GetAtt(restapi_resource, 'RootResourceId')
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)

            # Lambad Integration
            if method.integration.integration_lambda != None:
                awslambda = get_model_obj_from_ref(method.integration.integration_lambda, self.project)
                uri = troposphere.Join('', [
                    "arn:aws:apigateway:",
                    awslambda.region_name,
                    ":lambda:path/2015-03-31/functions/",
                    method.parameter_arn_ref,
                    "/invocations"]
                )
                cfn_export_dict["Integration"]["Uri"] = uri

                if method.integration.integration_type == 'AWS_PROXY':
                    # Cross-account Lambda can not have a Role or gets a permission error
                    if api_account_name == awslambda.get_account().name:
                        # IAM Role - allows API Gateway to invoke Lambda
                        # ToDo: enable Api Gateway to invoke things other than Lambda ...
                        # ToDo: share Roles between methods!
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
                if method_response.response_parameters:
                    response_dict["ResponseParameters"] = method_response.response_parameters
                responses.append(response_dict)
            cfn_export_dict["MethodResponses"] = responses

            method_resource = troposphere.apigateway.Method.from_dict(method_id, cfn_export_dict)
            method_resource.DependsOn = restapi_logical_id
            template.add_resource(method_resource)
            self.create_output(
                title=self.create_cfn_logical_id(f'ApiGatewayRestApiMethod{method.name}'),
                value=troposphere.Ref(method_resource),
                ref=method.paco_ref_parts + '.id',
            )

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
        self.create_output(
            title=self.create_cfn_logical_id(f'ApiGatewayRestApiDeployment'),
            value=troposphere.Ref(deployment_resource),
            ref=self.apigatewayrestapi.paco_ref_parts + '.deploymnt_id',
        )

        # Stage
        for stage in self.apigatewayrestapi.stages.values():
            stage_id = self.create_cfn_logical_id('ApiGatewayStage' + stage.name)
            cfn_export_dict = stage.cfn_export_dict
            cfn_export_dict["RestApiId"] = troposphere.Ref(restapi_resource)
            cfn_export_dict["DeploymentId"] = troposphere.Ref(deployment_resource)
            stage_resource = troposphere.apigateway.Stage.from_dict(stage_id, cfn_export_dict)
            template.add_resource(stage_resource)
            self.create_output(
                title=self.create_cfn_logical_id(f'ApiGatewayRestApiStag{stage.name}'),
                value=troposphere.Ref(stage_resource),
                ref=stage.paco_ref_parts + '.id',
            )

class ApiGatewayLamdaPermissions(StackTemplate):
    def __init__(self, stack, paco_ctx, awslambda):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('ApiGatewayLamdaPermission', self.resource_group_name, self.resource_name)
        self.init_template('Cross-account Api Gateway Lambda Permission')
        apigateway = self.resource

        api_gateway_id_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('ApiGatewayRestApiId'),
            param_type='String',
            description='API Gateway Rest API Id',
            value=apigateway.paco_ref + '.id',
        )
        lambda_arn_param = self.create_cfn_parameter(
            name=self.create_cfn_logical_id('LambdaArn'),
            param_type='String',
            description='Lambda Arn',
            value=awslambda.paco_ref + '.arn',
        )

        # Lambda Permission for cross-account API Gateway invocation
        for method in apigateway.methods.values():
            if method.integration != None and method.integration.integration_lambda != None:
                if awslambda.paco_ref == method.integration.integration_lambda:
                    if apigateway.get_account().name != awslambda.get_account().name:
                        # Grant Cross-Account API Gateway permission
                        path_part = ''
                        # ToDo: nested resource support!
                        if method.resource_name:
                            path_part = apigateway.resources[method.resource_name].path_part
                        lambda_permission_resource = troposphere.awslambda.Permission(
                            title='ApiGatewayRestApiMethod' + md5sum(str_data=method.paco_ref),
                            Action="lambda:InvokeFunction",
                            FunctionName=troposphere.Ref(lambda_arn_param),
                            Principal='apigateway.amazonaws.com',
                            SourceArn=troposphere.Join('', [
                                "arn:aws:execute-api:",
                                awslambda.region_name, # lambda region
                                ":",
                                apigateway.get_account().account_id, # account id
                                ":",
                                troposphere.Ref(api_gateway_id_param),
                                f"/*/{method.http_method}/{path_part}",
                            ])
                        )
                        self.template.add_resource(lambda_permission_resource)
