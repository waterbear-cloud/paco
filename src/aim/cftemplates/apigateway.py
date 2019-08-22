"""
CloudFormation templates for API Gateway
"""

import troposphere
import troposphere.apigateway
from aim.cftemplates.cftemplates import CFTemplate
from aim.models import references
from aim.models.references import Reference


class ApiGatewayRestApi(CFTemplate):
    """
    CloudFormation template for ApiGatewayRestApi
    """
    def __init__(
        self,
        aim_ctx,
        account_ctx,
        aws_region,
        aws_name,
        app_id,
        grp_id,
        apigatewayrestapi,
        config_ref=None
    ):
        aws_name='-'.join([aws_name, 'ApiGatewayRestApi'])
        super().__init__(
            aim_ctx,
            account_ctx,
            aws_region,
            config_ref=config_ref,
            aws_name=aws_name
        )
        self.apigatewayrestapi = apigatewayrestapi
        template = troposphere.Template()
        template.add_version('2010-09-09')
        template.add_description(apigatewayrestapi.title)
        
        template.add_resource(
            troposphere.apigateway.RestApi.from_dict(
                'ApiGatewayRestApi',
                self.apigatewayrestapi.cfn_export_dict
            )
        )

        self.set_template(template.to_yaml())