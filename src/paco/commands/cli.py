import click
import pkg_resources
from paco.commands.cmd_provision import provision_command
from paco.commands.cmd_init import init_group
from paco.commands.cmd_delete import delete_command
from paco.commands.cmd_describe import describe_command
from paco.commands.cmd_validate import validate_command
from paco.commands.cmd_shell import shell_command
from paco.commands.cmd_set import set_command
from paco.commands.cmd_lambda import lambda_group
from paco.commands.helpers import pass_paco_context


@click.group()
@click.version_option(
    version=pkg_resources.require("paco-cloud")[0].version,
    prog_name="Paco: Prescribed automation for cloud orchestration"
)
@pass_paco_context
def cli(ctx):
    """Paco: Prescribed automation for cloud orchestration"""
    pass

cli.add_command(init_group)
cli.add_command(validate_command)
cli.add_command(provision_command)
cli.add_command(delete_command)
cli.add_command(set_command)
cli.add_command(lambda_group)
cli.add_command(describe_command)
#cli.add_command(shell_command)
