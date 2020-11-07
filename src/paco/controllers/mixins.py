from paco.aws_api.awslambda.code import update_lambda_code
from paco.core.exception import PacoUnsupportedFeature, LambdaInvocationError
from paco.models import schemas
from botocore.exceptions import ClientError
from base64 import b64decode
import pprint
import json


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

    def lambda_invoke_command(self, resource, event):
        "Invoke Lambda funciton(s)"
        if schemas.ILambda.providedBy(resource):
            account_name = resource.get_account().name
            account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
            function_name = resource.stack.get_outputs_value('FunctionName')
            client = account_ctx.get_aws_client('lambda', resource.stack.aws_region)
            print(f"Invoking Lambda {resource.paco_ref_parts}")
            print(f"Waiting for Lamdba response ...")
            try:
                if event == None:
                    response = client.invoke(
                        FunctionName=function_name,
                        InvocationType='RequestResponse',
                        LogType='Tail',
                    )
                else:
                    response = client.invoke(
                        FunctionName=function_name,
                        InvocationType='RequestResponse',
                        LogType='Tail',
                        Payload=event.encode(),
                        # ClientContext='string', ToDo: identify Paco CLI as context
                        # Qualifier='string' ToDo: specify version/alias
                    )
            except ClientError as error:
                raise LambdaInvocationError(error)

            print("... response recieved.\n")
            if 'FunctionError' in response:
                print(f"Lamdba returned an error of type '{response['FunctionError']}':\n")
                json_error = json.loads(
                    response['Payload'].read().decode()
                )
                pprint.pprint(json_error)
                print("\nLog Result:\n")
                print(b64decode(response['LogResult']).decode())
            else:
                print("Lambda invoked and returned the response:\n")
                json_response = json.loads(
                    response['Payload'].read().decode()
                )
                pprint.pprint(json_response)
                print("\nLog Result:\n")
                print(b64decode(response['LogResult']).decode())

        else:
            # ToDo: support netenv/env_region/app scopes
            raise PacoUnsupportedFeature("Scope not a Lambda")
