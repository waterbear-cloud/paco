from aim.config import aim_context

def test_create_aim_context():
    aim_ctx = aim.config.aim_context.AimContext()
    assert isinstance(aim_ctx, aim.config.aim_context.AimContext)

