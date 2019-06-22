import click
import aim.models
from aim.commands.cli import pass_context


@click.command('init', short_help='Initializes a Waterbear Cloud component.')
@click.argument('controller_type', required=True, type=click.STRING)
@click.argument('component_name', required=True, type=click.STRING)
@click.argument('init_arg_1', required=False, type=click.STRING)
@click.argument('init_arg_2', required=False, type=click.STRING)
@pass_context
def cli(aim_ctx, controller_type, component_name, init_arg_1=None, init_arg_2=None):
    """Initializes a Waterbear Cloud component."""

    config_arg = None
    config_arg = {
        'name': component_name
    }

    if controller_type != 'Project':
        aim_ctx.init_project(aim_ctx.home)
    else:
        if init_arg_1 == None:
            print("Error: missing project path argument: aim init Project <project name> <project_relative_path>")
        config_arg['folder'] = init_arg_1

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.init_command(config_arg)
