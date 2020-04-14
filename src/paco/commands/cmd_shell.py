import click
import sys
from paco.core.exception import StackException
from paco.commands.helpers import pass_paco_context, paco_home_option, init_paco_home_option

@click.command('shell', short_help='Open a shell to an instance.')
@click.argument("netenv_namne", required=True, type=click.STRING)
@click.argument("env_name", required=True, type=click.STRING)
@click.argument("region", required=True, type=click.STRING)
@click.argument("instance_ref", required=True, type=click.STRING)
@paco_home_option
@pass_paco_context
def shell_command(paco_ctx, netenv_name, env_name, region, instance_ref, home='.'):
    """Open a shell to an instance"""
    paco_ctx.command = 'shell'
    init_paco_home_option(paco_ctx, home)
    if not paco_ctx.home:
        print('Paco configuration directory needs to be specified with either --home or PACO_HOME environment variable.')
        sys.exit()

    paco_ctx.load_project()
    config_arg = {
            'netenv_name': netenv_name,
            'env_id': env_id,
            'region' : region,
        }
    paco_ctx.get_controller('NetEnv', config_arg)
    full_ref = 'paco.ref netenv.%s.%s.%s.%s' % (netenv_name, env_name, region, instance_ref)
    paco_ctx.get_ref(full_ref)
