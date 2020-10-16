import click
from paco.commands.helpers import paco_home_option, pass_paco_context, handle_exceptions, \
    cloud_options, init_cloud_command, cloud_args, config_types


@click.command(name='provision', short_help='Provision resources to the cloud.')
@click.option(
    '-a', '--auto-publish-code',
    default=False,
    is_flag=True,
    help="""
Automatically update Lambda Code assets. Lambda resources that use the `zipfile:` to a local filesystem path will automatically publish new code if it differs from the currently published code asset.
"""
)
@paco_home_option
@cloud_args
@cloud_options
@pass_paco_context
@handle_exceptions
def provision_command(
    paco_ctx,
    verbose,
    nocache,
    yes,
    warn,
    disable_validation,
    quiet_changes_only,
    config_scope,
    home='.',
    auto_publish_code=False,
):
    """Provision Cloud Resources"""
    paco_ctx.auto_publish_code = auto_publish_code
    command = 'provision'
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
    controller = paco_ctx.get_controller(controller_type, command, obj)
    controller.provision()

provision_command.help = """
Provision Cloud Resources.

""" + config_types