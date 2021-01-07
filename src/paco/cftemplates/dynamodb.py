from paco.cftemplates.cftemplates import StackTemplate
import troposphere
import troposphere.dynamodb


class DynamoDB(StackTemplate):
    def __init__(self, stack, paco_ctx):
        dynamodb = stack.resource
        super().__init__(stack, paco_ctx)
        self.set_aws_name('DynamoDB', self.resource_group_name, self.resource.name)

        self.init_template('DynamoDB Table(s)')
        if not dynamodb.is_enabled(): return

        # Parameters

        # DynamoDB Tables
        for table in dynamodb.tables.values():
            cfn_export_dict = table.cfn_export_dict
            table_logical_id = self.create_cfn_logical_id(table.name + 'DynamoDBTable')
            dynamodb_table_resource = troposphere.dynamodb.Table.from_dict(
                table_logical_id,
                cfn_export_dict,
            )
            self.template.add_resource(dynamodb_table_resource)
            self.create_output(
                title=dynamodb_table_resource.title + 'Name',
                description="DynamoDB Table Name",
                value=troposphere.Ref(dynamodb_table_resource),
                ref=f"{table.paco_ref_parts}.name"
            )
            self.create_output(
                title=dynamodb_table_resource.title + 'Arn',
                description="DynamoDB Table Arn",
                value=troposphere.GetAtt(dynamodb_table_resource, "Arn"),
                ref=f"{table.paco_ref_parts}.arn"
            )
