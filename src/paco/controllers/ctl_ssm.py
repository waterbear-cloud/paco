import json
from paco.aws_api.ssm.document import SSMDocumentClient
from paco.core.exception import StackException
from paco.controllers.controllers import Controller
from paco.models.resources import SSMDocument
from paco.utils import md5sum, prefixed_name


SSM_DOCUMENT_UPDATE_WINDOWS_CLOUDWATCH_AGENT = {
    "schemaVersion": "2.2",
    "description": "Windows CloudWatch Agent Configuration and Start",
    "parameters": {
        "ConfigParamStoreName": {
            "type": "String",
            "description": "CloudWatch Configuration Parameter Store Name"
        },
    },
    "mainSteps": [
        {
            "action": "aws:runPowerShellScript",
            "name": "WindowsCloudWatchConfigAndStart",
            "inputs": {
                "runCommand": [
                    '& "C:\Program Files\Amazon\AmazonCloudWatchAgent\\amazon-cloudwatch-agent-ctl.ps1" -a fetch-config -m ec2 -s -c ssm:{{ConfigParamStoreName}}',
                ]
            }
        }
    ]
}

class SSMController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "Resource", "SSM")

    def init(self, command=None, model_obj=None):
        self.command = command
        self.model_obj = model_obj

    def paco_ec2lm_update_instance(self, resource, account_ctx, region, cache_id):
        ssm_client = account_ctx.get_aws_client('ssm', aws_region=region)
        ssm_log_group_name = prefixed_name(resource, 'paco_ssm', self.paco_ctx.legacy_flag)
        ssm_client.send_command(
            Targets=[{
                'Key': 'tag:aws:cloudformation:stack-name',
                'Values': [resource.stack.get_name()]
            },],
            DocumentName='paco_ec2lm_update_instance',
            Parameters={ 'CacheId': [cache_id] },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': ssm_log_group_name,
                'CloudWatchOutputEnabled': True,
            },
        )

    def command_update_ssm_agent(self, resource, account_ctx, region):
        ssm_client = account_ctx.get_aws_client('ssm', aws_region=region)
        ssm_log_group_name = prefixed_name(resource, 'paco_ssm', self.paco_ctx.legacy_flag)
        response = ssm_client.send_command(
            Targets=[{
                'Key': 'tag:aws:cloudformation:stack-name',
                'Values': [resource.stack.get_name()]
            },],
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': ssm_log_group_name,
                'CloudWatchOutputEnabled': True,
            },
            DocumentName='AWS-UpdateSSMAgent',
        )

    def wait_for_command(self, ssm_client, account_ctx, region, resource, command_id):
        ec2_client = account_ctx.get_aws_client('ec2', aws_region=region)
        ec2_response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Paco-Stack-Name',
                    'Values': [resource.stack.get_name()]
                }

            ]
        )
        for instance in ec2_response['Reservations'][0]['Instances']:
            instance_id = instance['InstanceId']
            while True:
                # TODO: Needs a try for InvocationDoesNotExist Exception
                try:
                    command_response = ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=instance_id,
                    )
                except Exception as e:
                    # An instance may need more time if we get here, try again.
                    # breakpoint()
                    print(f"{e}")
                    break
                if command_response['Status'] not in ('Pending', 'InProgress', 'Delayed'):
                    if command_response['Status'] == 'Success':
                        print(f"ssm command: {command_id}: success on {instance_id}")
                    else:
                        print(f"Command status: {instance_id}: {command_response['Status']}: {command_response['StatusDetails']}")
                        if 'StandardOutputContent' in command_response.keys():
                            print(f"Command stdout: {instance_id}: {command_response['StandardOutputContent']}")
                        if 'StandardErrorContent' in command_response.keys():
                            print(f"Command stderr: {instance_id}: {command_response['StandardErrorContent']}")
                    break

# Install the Agent
    def send_command(self, account_ctx, region, resource, parameters, targets, document_name):
        ssm_client = account_ctx.get_aws_client('ssm', aws_region=region)
        ssm_log_group_name = prefixed_name(resource, 'paco_ssm', self.paco_ctx.legacy_flag)
        response = ssm_client.send_command(
            Parameters=parameters,
            Targets=targets,
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': ssm_log_group_name,
                'CloudWatchOutputEnabled': True,
            },
            DocumentName=document_name
        )

        self.wait_for_command(ssm_client, account_ctx, region, resource, response['Command']['CommandId'])

    def command_update_cloudwatch_agent(self, resource, account_ctx, region, cloudwatch_config_json):
        ssm_documents = self.paco_ctx.project['resource']['ssm'].ssm_documents
        if 'paco_windows_cloudwatch_agent_update' not in ssm_documents:
            ssm_doc = SSMDocument('paco_windows_cloudwatch_agent_update', ssm_documents)
            ssm_doc.add_location(account_ctx.paco_ref, region)
            ssm_doc.content = json.dumps(SSM_DOCUMENT_UPDATE_WINDOWS_CLOUDWATCH_AGENT)
            ssm_doc.document_type = 'Command'
            ssm_doc.enabled = True
            ssm_documents['paco_windows_cloudwatch_agent_update'] = ssm_doc
        else:
            ssm_documents['paco_windows_cloudwatch_agent_update'].add_location(
                account_ctx.paco_ref,
                region
            )

        self.provision_ssm_document(ssm_doc, account_ctx, region)
        ssm_client = account_ctx.get_aws_client('ssm', aws_region=region)

        # Create Config Parameter Store
        cloudwatch_config_param_store_name = f'Paco-CloudWatch-Config-{resource.stack.get_name()}'
        response = ssm_client.put_parameter(
            Name=cloudwatch_config_param_store_name,
            Description='CloudWatch Configuration',
            Value=cloudwatch_config_json,
            Type='String',
            Overwrite=True,
            Tier='Advanced'
        )

        # Configure Amazon CloudWatch Agent
        parameters = {
            'action': ['Install'],
            'name': ["AmazonCloudWatchAgent"],
            'version': ["latest"],
        }
        targets=[{
            'Key': 'tag:aws:cloudformation:stack-name',
            'Values': [resource.stack.get_name()]
        }]

        self.send_command(account_ctx, region, resource, parameters, targets, 'AWS-ConfigureAWSPackage')

        # Update the Agent
        parameters = {
            'ConfigParamStoreName': [cloudwatch_config_param_store_name],
        }
        targets=[{
            'Key': 'tag:aws:cloudformation:stack-name',
            'Values': [resource.stack.get_name()]
        }]
        self.send_command(account_ctx, region, resource, parameters, targets, 'paco_windows_cloudwatch_agent_update')



    def validate(self):
        pass

    def provision(self, scope=None):
        if scope != None:
            scope_parts = scope.split('.')
            if scope.startswith('resource.ssm.ssm_documents.') and len(scope_parts) == 6:
                name, account_name, aws_region = scope_parts[3:]
                # TODO: EC2LM and Windows: name can == paco_ec2lm_update_instance
                if name in self.paco_ctx.project['resource']['ssm'].ssm_documents.keys():
                    account_ctx = self.paco_ctx.get_account_context(account_name=account_name)
                    ssm_doc = self.paco_ctx.project['resource']['ssm'].ssm_documents[name]
                    self.provision_ssm_document(ssm_doc, account_ctx, aws_region)
        else:
            # ToDo: provisions everything in resource/ssm.yaml - add scopes
            for ssm_doc in self.paco_ctx.project['resource']['ssm'].ssm_documents.values():
                for location in ssm_doc.locations:
                    account_ctx = self.paco_ctx.get_account_context(account_ref=location.account)
                    for aws_region in location.regions:
                        self.provision_ssm_document(ssm_doc, account_ctx, aws_region)

    def provision_ssm_document(self, ssm_doc, account_ctx, aws_region):
        "Create or Update an SSM Document"
        ssmclient = SSMDocumentClient(self.paco_ctx.project, account_ctx, aws_region)
        if not ssmclient.document_exists(ssm_doc):
            self.paco_ctx.log_action_col(
                'Provision',
                'Create',
                account_ctx.name + '.' + aws_region,
                'boto3: ' + ssm_doc.name,
                enabled=True,
                col_2_size=9
            )
            ssmclient.create_ssm_document(ssm_doc)
        else:
            if ssmclient.is_document_identical(ssm_doc):
                self.paco_ctx.log_action_col(
                    'Provision',
                    'Cache',
                    account_ctx.name + '.' + aws_region,
                    'boto3: ' + ssm_doc.name,
                    enabled=True,
                    col_2_size=9
                )
            else:
                self.paco_ctx.log_action_col(
                    'Provision',
                    'Update',
                    account_ctx.name + '.' + aws_region,
                    'boto3: ' + ssm_doc.name,
                    enabled=True,
                    col_2_size=9
                )
                ssmclient.update_ssm_document(ssm_doc)
