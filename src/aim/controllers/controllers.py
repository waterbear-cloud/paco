import os

class Controller():

    def __init__(self, aim_ctx, controller_type, controller_name):
        self.aim_ctx = aim_ctx
        self.controller = None
        self.controller_type = controller_type
        self.aws_name = controller_type
        self.init_done = False
        if controller_name:
            self.aws_name = self.aws_name + '-' + controller_name

    def get_aws_name(self):
        return self.aws_name
