from paco.config import paco_context

def test_create_paco_context():
    paco_ctx = paco.config.paco_context.PacoContext()
    assert isinstance(paco_ctx, paco.config.paco_context.PacoContext)

