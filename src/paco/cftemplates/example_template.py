from paco.cftemplates.cftemplates import StackTemplate
import troposphere


class Example(StackTemplate):
    def __init__(self, stack, paco_ctx)
        super().__init__(stack, paco_ctx)
        self.set_aws_name('Example', self.resource_group_name, self.resource.name)

        # Troposphere Template Initialization
        self.init_template('Example Template')
        if not self.resource.is_enabled():
            return

        # Parameters
        example_param = self.create_cfn_parameter(
            name='ExampleParameterName',
            param_type='String',
            description='Example parameter.',
            value=self.resource.example_variable,
        )

        # Resource
        example_dict = {
            'some_property' : troposphere.Ref(example_param)
        }
        example_res = troposphere.resource.Example.from_dict(
            'ExampleResource',
            example_dict
        )
        self.template.add_resource( example_res )

        # Outputs
        self.create_output(
            title='ExampleResourceId',
            description="Example resource Id.",
            value=troposphere.Ref(example_res),
            ref=self.resource.paco_ref_parts + ".id"
        )
