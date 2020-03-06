import click
import sys
from paco.core.exception import StackException
from paco.commands.helpers import (
    pass_paco_context, paco_home_option, handle_exceptions, cloud_options,
    init_cloud_command, cloud_args, config_types
)


@click.command('validate', short_help='Validate a Paco project')
@paco_home_option
@cloud_args
@cloud_options
@pass_paco_context
@handle_exceptions
def validate_command(
    paco_ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.'
):
    "Validate resources"
    command = 'validate'
    controller_type, obj = init_cloud_command(
        command,
        paco_ctx,
        verbose,
        nocache,
        yes,
        warn,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    controller = paco_ctx.get_controller(controller_type, 'validate', obj)
    controller.validate()

validate_command.help = """
Creates CloudFormation templates and validates they are well-formed.

""" + config_types
