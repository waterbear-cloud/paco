import click
import os
import sys
from aim.config.aim_context import AimContext, AccountContext

CONTEXT_SETTINGS = dict(auto_envvar_prefix='COMPLEX')

pass_context = click.make_pass_decorator(AimContext, ensure=True)
cmd_folder = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '')
)
class ComplexCLI(click.MultiCommand):

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__('aim.commands.cmd_' + name, None, None, ['cli'])
        except ImportError:
            # Click will give the user an error about command name
            # we don't need to tell them anything else
            import pdb; pdb.set_trace();
            return
        return mod.cli


@click.command(cls=ComplexCLI, context_settings=CONTEXT_SETTINGS)
@click.option(
    '--home',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help='Path to an AIM Project configuration folder. Can also be set with the environment variable AIM_HOME.'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enables verbose mode.'
)
@pass_context
def cli(ctx, verbose, home):
    """AIM: Application Infrastructure Manager"""
    ctx.verbose = verbose
    # --home overrides the AIM_HOME Env var
    if not home:
        home = os.environ.get('AIM_HOME')
    if home is not None:
        ctx.home = home
