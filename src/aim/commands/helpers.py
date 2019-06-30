import click
import os
from aim.config.aim_context import AimContext, AccountContext

pass_aim_context = click.make_pass_decorator(AimContext, ensure=True)

def controller_args(func):
    """
    decorator to add controller args
    """
    func = click.argument("config_region", required=False, type=click.STRING)(func)
    func = click.argument("config_name", required=False, type=click.STRING)(func)
    func = click.argument("component_name", required=True, type=click.STRING)(func)
    func = click.argument("controller_type", required=True, type=click.STRING)(func)
    return func

def aim_home_option(func):
    """
    decorater to add AIM Home option
    """
    func = click.option(
        "--home",
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        help="Path to an AIM Project configuration folder. Can also be set with the environment variable AIM_HOME.",
    )(func)
    return func

def init_aim_home_option(ctx, home):
    # --home overrides the AIM_HOME Env var
    if not home:
        home = os.environ.get('AIM_HOME')
    if home is not None:
        ctx.home = home
