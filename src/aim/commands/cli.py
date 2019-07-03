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
    '--config_folder',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help='Path to an AIM Project configuration folder. Can also be set with the environment variable AIM_CONFIG_FOLDER.'
)
@click.option(
    '--project',
    type=click.Path(exists=True, file_okay=False, resolve_path=False),
    help='The name of the project folder in the config_folder or AIM_CONFIG_FOLDER Env variable.'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enables verbose mode.'
)
@pass_context
def cli(ctx, verbose, config_folder, project):
    """AIM: Application Infrastructure Manager"""
    ctx.verbose = verbose
    # --config_folder overrides the AIM_CONFIG_FOLDER Env var
    # --project overrides the AIM_PROJECT Env var
    if not config_folder:
        config_folder = os.environ.get('AIM_CONFIG_FOLDER')
    if not project:
        project_relative_folder = os.environ.get('AIM_PROJECT')
    if config_folder is not None:
        ctx.config_folder = config_folder
    if project_relative_folder is not None:
        ctx.project_relative_folder = project_relative_folder

