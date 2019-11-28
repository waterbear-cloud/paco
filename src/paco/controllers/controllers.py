import os
from paco.models import loader
from paco.core.exception import StackException, PacoErrorCode

class Controller():

    def __init__(self, paco_ctx, controller_type, controller_name):
        self.paco_ctx = paco_ctx
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

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_done = True

    def confirm_yaml_changes(self, model_obj):
        self.model_obj = model_obj
        if self.model_obj != None and self.paco_ctx.command != 'delete':
            self.paco_ctx.confirm_yaml_changes(self.model_obj)

    def apply_model_obj(self):
        if self.model_obj != None:
            self.paco_ctx.apply_model_obj(self.model_obj)
        else:
            raise StackException(
                PacoErrorCode.Unknown,
                message = 'No model object to apply.'
            )