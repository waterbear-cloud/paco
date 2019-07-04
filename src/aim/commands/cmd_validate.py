import click
import sys
from aim.core.exception import StackException
from aim.commands.helpers import pass_aim_context, controller_args, aim_home_option, init_aim_home_option

@click.command('validate', short_help='Validate an AIM project')
@controller_args
@aim_home_option
@pass_aim_context
def validate_command(aim_ctx, controller_type, component_name=None, config_name=None, config_region=None, home='.'):
    """Validates a Config CloudFormation"""
    init_aim_home_option(aim_ctx, home)
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
    elif controller_type == "EC2":
        config_arg = {
            'service': component_name,
            'id': config_name
        }
    else:
        config_arg = {
            'name': component_name
        }

    controller = aim_ctx.get_controller(controller_type, config_arg)
    controller.validate()
