import click
import os
import os.path
from aim.commands.cli import pass_context
from cookiecutter.main import cookiecutter


@click.command('init', short_help='Initializes an AIM Project')
@click.argument('config_type', default='project', type=click.STRING)
@pass_context
def cli(aim_ctx, config_type='project'):
    """Initializes an AIM Project"""
    if config_type == 'project':
        print("\nAIM Project initialization")
        print("--------------------------\n")
        print("About to create a new AIM Project directory at {}\n".format(os.getcwd()))
        cookiecutter(os.path.dirname(__file__) + os.sep + 'aim-cookiecutter' + os.sep)
