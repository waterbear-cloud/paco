import click
import pkg_resources
from aim.commands.cmd_provision import provision_command
from aim.commands.cmd_init import init_command
from aim.commands.cmd_delete import delete_command
from aim.commands.cmd_describe import describe_command
from aim.commands.cmd_validate import validate_command
from aim.commands.cmd_shell import shell_command
from aim.commands.cmd_ftest import ftest_command
from aim.commands.helpers import pass_aim_context

@click.group()
@click.version_option( version=pkg_resources.require("aim")[0].version, prog_name="aim")
@click.option(
    '-v', '--verbose',
    is_flag=True,
    default=False,
    help='Enables verbose mode.'
)
@click.option(
    '-n', '--nocache',
    is_flag=True,
    default=False,
    help='Disables the AIM CloudFormation stack cache.'
)
@click.option(
    '-y', '--yes',
    is_flag=True,
    default=False,
    help='Responds "yes" to any Yes/No prompts.'
)
@click.option(
    '-d', '--disable-validation',
    is_flag=True,
    default=False,
    help='Supresses validation differences.'
)
@click.option(
    '-c', '--quiet-changes-only',
    is_flag=True,
    default=False,
    help='Supresses Cache, Protected, and Disabled messages.'
)

@pass_aim_context
def cli(ctx, verbose, nocache, yes, disable_validation, quiet_changes_only):
    """AIM: Application Infrastructure Manager"""
    ctx.verbose = verbose
    ctx.nocache = nocache
    ctx.yes = yes
    ctx.disable_validation = disable_validation
    ctx.quiet_changes_only = quiet_changes_only

cli.add_command(provision_command)
cli.add_command(init_command)
cli.add_command(delete_command)
cli.add_command(describe_command)
cli.add_command(validate_command)
cli.add_command(shell_command)
cli.add_command(ftest_command)