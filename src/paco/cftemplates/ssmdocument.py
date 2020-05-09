from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.ssm


class SSMDocument(StackTemplate):
    def __init__(self, stack, paco_ctx):
        super().__init__(stack, paco_ctx)
        self.set_aws_name('SSMDocument', self.resource.name)
        ssmdoc = self.resource
        self.init_template('SSM Document')
        if not ssmdoc.is_enabled(): return

        # SSM Document resource
        ssmdocument = troposphere.ssm.Document(
            title = 'SSMDocument',
            template = self.template,
            Content=ssmdoc.content,
            DocumentType=ssmdoc.document_type,
            Name=ssmdoc.name,
        )

