import click
import sys
from aim.core.exception import StackException
from aim.commands.helpers import pass_aim_context, controller_args, aim_home_option, init_aim_home_option

@click.command('shell', short_help='Open a shell to an instance.')
@click.argument("netenv_id", required=True, type=click.STRING)
@click.argument("env_id", required=True, type=click.STRING)
@click.argument("region", required=True, type=click.STRING)
@click.argument("instance_ref", required=True, type=click.STRING)
@aim_home_option
@pass_aim_context
def shell_command(aim_ctx, netenv_id, env_id, region, instance_ref, home='.'):
    """Open a shell to an instance"""

    init_aim_home_option(aim_ctx, home)
    if not aim_ctx.home:
        print('AIM configuration directory needs to be specified with either --home or AIM_HOME environment variable.')
        sys.exit()

    aim_ctx.init_project()
    config_arg = {
            'netenv_id': netenv_id,
            'subenv_id': env_id,
            'region' : region,
        }
    aim_ctx.get_controller('NetEnv', config_arg)
    full_ref = 'netenv.ref %s.subenv.%s.%s.%s' % (netenv_id, env_id, region, instance_ref)
    aim_ctx.get_ref(full_ref)
