from paco.aws_api.awslambda.code import update_lambda_code
from paco.core.exception import PacoUnsupportedFeature
from paco.models import schemas


class LambdaDeploy():

    def lambda_deploy_command(self, resource):
        "Deploy Lambda funciton(s) to AWS"
        if schemas.ILambda.providedBy(resource):
            account_name = resource.get_account().name
            account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
            # ToDo: support -s, --src option and validate
            src = resource.code.zipfile
            function_name = resource.stack.get_outputs_value('FunctionName')
            print(f"Uploading code for Lambda '{resource.name}' ({function_name})")
            update_lambda_code(resource, function_name, src, account_ctx, resource.region_name)
            print(f"Lambda {resource.name} has been updated.")
        else:
            # ToDo: support netenv/env_region/app scopes
            raise PacoUnsupportedFeature("Scope not a Lambda")
