import aim.models
import click
import sys
from aim.commands.helpers import (
    aim_home_option, init_aim_home_option, pass_aim_context,
    handle_exceptions, cloud_options, init_cloud_command, cloud_args, config_types
)
from aim.core.exception import StackException


@click.command('delete', short_help='Delete Paco managed resources')
@aim_home_option
@cloud_args
@cloud_options
@pass_aim_context
@handle_exceptions
def delete_command(
    aim_ctx,
    verbose,
    nocache,
    yes,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.'
):
    """Deletes provisioned AWS Resources"""
    command = 'delete'
    controller_type, obj = init_cloud_command(
        command,
        aim_ctx,
        verbose,
        nocache,
        yes,
        disable_validation,
        quiet_changes_only,
        config_scope,
        home
    )
    answer = aim_ctx.input_confirm_action("Proceed with deletion of {}?".format(config_scope))
    if answer == False:
        print("Aborted delete operation.")
        return

    controller = aim_ctx.get_controller(controller_type, 'delete', obj)
    controller.delete()

delete_command.help = """
Delete cloud resources.

""" + config_types
