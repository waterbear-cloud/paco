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
        config_ref):

        # ---------------------------------------------------------------------------
        # CFTemplate Initialization
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

        # ---------------------------------------------------------------------------
        # Troposphere Template Initialization
        self.init_template('Example Template')

        # ---------------------------------------------------------------------------
        # Parameters

        example_param = self.create_cfn_parameter(
            name='ExampleParameterName',
            param_type='String',
            description='Example parameter.',
            value=example_config.example_variable,
            use_troposphere=True,
            troposphere_template=self.template,
        )

        # ---------------------------------------------------------------------------
        # Resource
        example_dict = {
            'some_property' : troposphere.Ref(example_param)
        }
        example_res = troposphere.resource.Example.from_dict(
            'ExampleResource',
            example_dict
        )
        self.template.add_resource( example_res )

        # ---------------------------------------------------------------------------
        # Outputs
        example_output = troposphere.Output(
            title='ExampleResourceId',
            Description="Example resource Id.",
            Value=troposphere.Ref(example_res)
        )
        self.template.add_output(example_output)

        # Paco Stack Output Registration
        self.register_stack_output_config(config_ref + ".id", example_output.title)

        # Generate the Template
        self.set_template(self.template.to_yaml())

