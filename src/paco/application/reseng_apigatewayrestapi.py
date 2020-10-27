import paco.cftemplates
from paco.application.res_engine import ResourceEngine
from paco.models.references import Reference

class ApiGatewayRestApiResourceEngine(ResourceEngine):

    def init_resource(self):
        self.stack_group.add_new_stack(
            self.aws_region,
            self.resource,
            paco.cftemplates.ApiGatewayRestApi,
            stack_tags=self.stack_tags,
        )

        # Stack for cross-account Lambda Permissions
        # (same account Lambda Permissions are granted with an IAM Role in the ApiGatwayRestApi Stack)
        # This Stack has to be made after Lambda and after API Gateway in the target acccount as it depends upon both
        apigateway = self.resource
        for awslambda in self.paco_ctx.project.get_all_resources_by_type('Lambda'):
            for method in apigateway.methods.values():
                if method.integration != None and method.integration.integration_lambda != None:
                    if awslambda.paco_ref == method.integration.integration_lambda:
                        if apigateway.get_account().name != awslambda.get_account().name:
                            # parse the account and region from the awslambda ref
                            lambda_ref = Reference(awslambda.paco_ref)
                            account = lambda_ref.get_account(self.paco_ctx.project, awslambda)
                            account_ctx = self.paco_ctx.get_account_context(account_name=account.name)

                            # XXX FixMe: if more than one Lambda in given account/region, they will have same Stack
                            # make template have permissions for all Lambdas
                            # create LambdaPermission Stack
                            self.stack_group.add_new_stack(
                                lambda_ref.region,
                                self.resource,
                                paco.cftemplates.ApiGatewayLamdaPermissions,
                                account_ctx=account_ctx,
                                stack_tags=self.stack_tags,
                                extra_context={'awslambda': awslambda},
                            )
