import os
from aim.models import loader
from aim.core.exception import StackException, AimErrorCode

class Controller():

    def __init__(self, aim_ctx, controller_type, controller_name):
        self.aim_ctx = aim_ctx
        self.controller = None
        self.controller_type = controller_type
        self.aws_name = controller_type
        self.init_done = False
        self.model_obj = None
        self.stack_group_filter = None
        if controller_name:
            self.aws_name = self.aws_name + '-' + controller_name

    def get_aws_name(self):
        return self.aws_name

    def init(self, controller_args):
        if self.init_done:
            return
        self.init_done = True

    def validate_model_obj(self, model_obj):
        self.model_obj = model_obj
        if self.model_obj != None:
            loader.validate_model_obj(
                self.model_obj,
                self.aim_ctx.home,
                self.aim_ctx.build_folder,
                self.aim_ctx.yes
            )

    def apply_model_obj(self):
        if self.model_obj != None:
            loader.apply_model_obj(
                self.model_obj,
                self.aim_ctx.home,
                self.aim_ctx.build_folder
            )
        else:
            raise StackException(
                AimErrorCode.unknown,
                message = 'No model object to apply.'
            )