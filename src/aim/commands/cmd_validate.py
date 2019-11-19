import click
import sys
from aim.core.exception import StackException
from aim.commands.helpers import (
    pass_aim_context, aim_home_option, handle_exceptions, cloud_options,
    set_cloud_options, cloud_args, config_types
)


@click.command('validate', short_help='Validate an AIM project')
@aim_home_option
@cloud_args
@cloud_options
@pass_aim_context
@handle_exceptions
def validate_command(
    aim_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_type,
    config_scope,
    home='.'
):
    "Validate resources"
    controller_type, controller_args = set_cloud_options(
        'validate',
        aim_ctx,
        verbose,
        nocache,
        yes,
        disable_validation,
        quiet_changes_only,
        config_type,
        config_scope,
        home
    )
    controller = aim_ctx.get_controller(controller_type, controller_args)
    controller.validate()

validate_command.help = """
Creates CloudFormation templates and validates they are well-formed.

""" + config_types
