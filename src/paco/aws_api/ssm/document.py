from botocore.config import Config
from botocore.exceptions import ClientError
from paco.models import references
from paco.stack.stack import Stack
import re


class SSMDocumentClient():

    def __init__(self, project, account_ctx, aws_region):
        self.project = project
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.aws_ssm_docs = {}

    @property
    def ssm_client(self):
        if hasattr(self, '_ssm_client') == False:
            self._ssm_client = self.account_ctx.get_aws_client('ssm', self.aws_region)
        return self._ssm_client

    def document_exists(self, ssm_doc):
        try:
            response = self.ssm_client.get_document(
                Name=ssm_doc.name
            )
            if response["Status"] != "Active":
                raise InvalidSSMDocument(f"The SSM Document named {ssm_doc.name} has unexpected Status '{response['Status']}'")
            self.aws_ssm_docs[ssm_doc.name] = response
        except ClientError as error:
            if error.response['Error']['Code'] != 'InvalidDocument':
                raise error
            else:
                return False
        return True

    def is_document_identical(self, ssm_doc):
        "Is the model SSM doc the same as SSM doc in AWS?"
        aws_ssm_doc = self.aws_ssm_docs[ssm_doc.name]
        if aws_ssm_doc["Content"] == ssm_doc.content:
            return True

    def create_ssm_document(self, ssm_doc):
        "Create a new SSM Document"
        response = self.ssm_client.create_document(
            Name=ssm_doc.name,
            DocumentType=ssm_doc.document_type,
            Content=ssm_doc.content,
            DocumentFormat='JSON',
        )

    def update_ssm_document(self, ssm_doc):
        "Update SSM Document"
        try:
            response = self.ssm_client.update_document(
                Name=ssm_doc.name,
                Content=ssm_doc.content,
                DocumentVersion='$LATEST',
                DocumentFormat='JSON',
            )
        except ClientError as error:
            if error.response['Error']['Code'] != 'DuplicateDocumentContent':
                raise error
            else:
                # document is already identical
                return
        document_version = response['DocumentDescription']['DocumentVersion']
        response = self.ssm_client.update_document_default_version(
            Name=ssm_doc.name,
            DocumentVersion=document_version,
        )
