import click
import sys
from aim.commands.cli import pass_context
from aim.core.exception import StackException


@click.command('validate', short_help='Validate an AIM project')
@click.argument('controller_type', required=True, type=click.STRING)
@click.argument('component_name', required=False, type=click.STRING)
@click.argument('config_name', required=False, type=click.STRING)
@click.argument('config_region', required=False, type=click.STRING)
@pass_context
def cli(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None):
    """Validates a Config CloudFormation"""
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    aim_ctx.init_project(aim_ctx.home)
    config_arg = None
    if controller_type == "NetEnv":
        config_arg = {
            'netenv_id': component_name,
            'subenv_id': config_name,
            'region' : config_region
        }
    else:
        config_arg = {
            'name': component_name
        }

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.validate()
