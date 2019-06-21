import click
import aim.models
from aim.cli import pass_context

@click.command('describe', short_help='Describe an AIM Project')
@pass_context
def cli(ctx):
    """Describe an AIM Project"""
    ctx.log('Listing projects and their environments.')
    project = aim.models.load_project_from_yaml(ctx, ctx.home)

    print('Project: {} - {}'.format(project.name, project.title))
    print('Location: {}'.format(ctx.home))
    print()
    print('Accounts')
    for ne in project['accounts'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()
    print('Network Environments')
    for ne in project['ne'].values():
        print(' - {} - {}'.format(ne.name, ne.title))
    print()
