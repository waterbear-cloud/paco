from enum import Enum

PacoErrorCode = Enum(
    'PacoErrorCode',
    '\
Unknown TemplateValidationError InvalidNumberOfArguments StackInProgress \
BadConfigFiles StackDoesNotExist StackOutputMissing InvalidStackName \
WaiterError')

class PacoException(Exception):
    def __init__(self, code, message=None):
        super().__init__()
        self.code = code
        if message != None:
            self.message = message
        else:
            self.set_message(code)

    def set_message(self, code):
        if code == PacoErrorCode.Unknown:
            self.message = "Unknown error"
        elif code == PacoErrorCode.TemplateValidationError:
            self.message = "A CloudFormation template failed to validate"
        elif code == PacoErrorCode.InvalidNumberOfArguments:
            self.message = "Invalid number of arguments"
        elif code == PacoErrorCode.StackInProgress:
            self.message = "The stack is already in progress"
        elif code == PacoErrorCode.BadConfigFiles:
            self.message = "Config files can not be understood."
        elif code == PacoErrorCode.StackDoesNotExist:
            self.message = "Stack does not exist."


class StackException(PacoException):
    def __init__(self, code, message=None):
        super().__init__(code, message)

    def get_error_str(self):
        error_str =  "StackException: " + self.code.name + ": " + self.message
        return error_str

class PacoBucketExists(Exception):
    "S3 Bucket already exists"

class UnsupportedCloudFormationParameterType(Exception):
    "Unsupported Parameter Type"

class InvalidLogSetConfiguration(Exception):
    "Invalid Log Set configuration"

class PacoUnsupportedFeature(Exception):
    "Feature does not yet exist"

class InvalidPacoScope(Exception):
    "Paco Reference not valid in this context."
