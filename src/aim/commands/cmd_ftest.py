"""
Functional test suite for AIM for the cookiecutter generated "aim init project" AIM projects
"""

import click
from aim.commands.helpers import pass_aim_context, handle_exceptions
from aim.config.aim_context import AimContext
from aim.commands.cookiecutter_test import test_cookiecutter_template, starting_template_mapping

@click.command('ftest', short_help='Functional testing of an AIM project', help="""
Tests an AIM project by first creating a project with 'aim init project',
provisions an environment, then does real-world functional testing on the environment,
then deletes all the AWS resources.

STARTING_TEMPLATE must be the name of a aim init starting_template, e.g. 'simple-web-app'""")
@click.argument('starting_template', default='')
@pass_aim_context
@handle_exceptions
def ftest_command(ctx, starting_template):
    """Functional testing of an AIM project"""
    print("Starting AIM functional tests")
    template_number = starting_template_mapping[starting_template]
    test_cookiecutter_template(starting_template, template_number, ctx.verbose)

