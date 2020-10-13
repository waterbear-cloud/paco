from botocore.config import Config
from botocore.exceptions import ClientError
from paco.models import references
from paco.stack.stack import Stack
import re


class IoTPolicyClient():

    def __init__(self, project, account_ctx, aws_region, iotpolicy):
        self.project = project
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.iotpolicy = iotpolicy
        self._document = None

    @property
    def iot_client(self):
        if hasattr(self, '_iot_client') == False:
            self._iot_client = self.account_ctx.get_aws_client('iot', self.aws_region)
        return self._iot_client


    @property
    def processed_document(self):
        if self._document != None:
            return self._document

        # resolve variable references and replace with resolved value
        # ToDo: only looks up Stack output values?
        for key, var in self.iotpolicy.variables.items():
            if references.is_ref(var):
                ref_value = references.resolve_ref(var, self.project)
                if isinstance(ref_value, Stack):
                    output_key = ref_value.get_outputs_key_from_ref(references.Reference(var))
                    ref_value = ref_value.get_outputs_value(output_key)
            self.iotpolicy.variables[key] = ref_value

        # replace ${variable} strings
        def var_replace(match):
            value = match.groups()[0]
            if value.lower() == 'AWS::Region'.lower():
                return self.aws_region
            elif value.lower() == 'AWS::AccountId'.lower():
                return self.account_ctx.id
            elif value.find(':') != -1:
                return "${" + value + "}"
            else:
                return self.iotpolicy.variables[value]

        self._document = re.sub('\${(.+?)}', var_replace, self.iotpolicy.policy_json)
        return self._document

    def policy_exists(self):
        "Return the Arn of the IoT Policy or None"
        try:
            response = self.iot_client.get_policy(
                policyName=self.iotpolicy.get_aws_name()
            )
            self.aws_state = response
            return response['policyArn']
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise e
            else:
                return None

    def is_policy_document_same(self):
        if self.processed_document == self.aws_state['policyDocument']:
            return True
        else:
            return False

    def create_policy(self):
        "Create a new IoT Policy resource"
        response = self.iot_client.create_policy(
            policyName=self.iotpolicy.get_aws_name(),
            policyDocument=self.processed_document
        )

    def update_policy_document(self):
        "Update Policy document"
        # basic replace of existing document version
        # get existing versionId
        # create new version
        # delete old version
        response = self.iot_client.list_policy_versions(
            policyName=self.iotpolicy.get_aws_name(),
        )
        for version in response['policyVersions']:
            if version['isDefaultVersion'] == True:
                old_version_id = version['versionId']
        response = self.iot_client.create_policy_version(
            policyName=self.iotpolicy.get_aws_name(),
            policyDocument=self.processed_document,
            setAsDefault=True
        )
        response = self.iot_client.delete_policy_version(
            policyName=self.iotpolicy.get_aws_name(),
            policyVersionId=old_version_id,
        )
