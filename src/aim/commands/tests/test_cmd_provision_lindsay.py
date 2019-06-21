import aim.commands.cmd_provision

def test_cmd():
    """
    Funcitonal test just to help debug MatchaLatte deployment
    """
    project_folder = '/Users/klindsay/bitbucket/waterbear/aim/fixtures/waterbear-networks/'
    aim_ctx = aim.config.aim_context.AimContext(config_folder=project_folder)
    aim_ctx.init_project(project_folder)
    config_arg = {
        'netenv_id': 'aimdemo',
        'subenv_id': 'dev',
        'region' : 'us-west-2'
    }
    controller = aim_ctx.get_controller('NetEnv', config_arg)
    controller.validate()
