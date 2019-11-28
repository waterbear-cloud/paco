import click
import sys
import paco.models
from paco.commands.helpers import pass_paco_context, paco_home_option, init_paco_home_option, handle_exceptions
from paco.utils.cache import load_cached_project


@click.command('describe', short_help='Describe a Paco project')
@paco_home_option
@pass_paco_context
@handle_exceptions
def describe_command(ctx, home='.'):
    """Describe a Paco project"""
    ctx.command = 'describe'
    init_paco_home_option(ctx, home)
    if not ctx.home:
        print('Paco configuration directory needs to be specified with either --home or PACO_HOME environment variable.')
        sys.exit()
    project = load_cached_project(ctx.home)

    print('Project: {} - {}'.format(project.name, project.title))
    print('Location: {}'.format(ctx.home))
    print()
    print('Accounts')
    for ne in project['accounts'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()
    print('Network Environments')
    for ne in project['netenv'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()
