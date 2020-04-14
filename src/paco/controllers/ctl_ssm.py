from paco.core.exception import StackException
from paco.controllers.controllers import Controller
from paco.aws_api.ssm.document import SSMDocumentClient

class SSMController(Controller):
    def __init__(self, paco_ctx):
        super().__init__(paco_ctx, "Resource", "SSM")

    def init(self, command=None, model_obj=None):
        pass

    def validate(self):
        pass

    def provision(self, account=None, region=None):
        for ssm_doc in self.paco_ctx.project['resource']['ssm'].ssm_documents.values():
            for location in ssm_doc.locations:
                account_ctx = self.paco_ctx.get_account_context(account_ref=location.account)
                for aws_region in location.regions:
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

