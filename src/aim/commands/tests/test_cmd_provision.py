import aim.commands.cmd_provision

def test_cmd_provision():
    """
    Funcitonal test just to help debug MatchaLatte deployment
    """
    project_folder = '/Users/kteague/water/aim/fixtures/waterbear-kt/'
    aim_ctx = aim.config.aim_context.AimContext(config_folder=project_folder)
    aim_ctx.init_project(project_folder)
    config_arg = {
        'netenv_id': 'ml',
        'subenv_id': None,
        'region' : None
    }
    controller = aim_ctx.get_controller('NetEnv', config_arg)
    controller.provision()


