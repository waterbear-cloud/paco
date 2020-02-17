import os
import troposphere
#import troposphere.<resource>

from paco.cftemplates.cftemplates import CFTemplate


class Example(CFTemplate):
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        stack_group,
        stack_tags,
        grp_id,
        res_id,
        example_config,
        config_ref
    ):
        super().__init__(
            paco_ctx,
            account_ctx,
            aws_region,
            enabled=example_config.is_enabled(),
            config_ref=config_ref,
            stack_group=stack_group,
            stack_tags=stack_tags,
            change_protected=example_config.change_protected
        )
        self.set_aws_name('Example', grp_id, res_id)

        # Troposphere Template Initialization
        self.init_template('Example Template')
        if not example_config.is_enabled():
            return self.set_template()

        # Parameters
        example_param = self.create_cfn_parameter(
            name='ExampleParameterName',
            param_type='String',
            description='Example parameter.',
            value=example_config.example_variable,
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
            ref=config_ref + ".id"
        )

        # Generate the Template
        self.set_template()

