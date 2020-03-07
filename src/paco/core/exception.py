from enum import Enum

PacoErrorCode = Enum(
    'PacoErrorCode',
    '\
Unknown TemplateValidationError InvalidNumberOfArguments StackInProgress \
BadConfigFiles StackDoesNotExist StackOutputMissing InvalidStackName \
WaiterError')

class PacoException(Exception):
    "Deprecated PacoExceptions. New exceptions act like stanaard Python Exceptions"
    def __init__(self, code, message=None):
        super().__init__()
        self.code = code
        if message != None:
            self.message = message
            self.title = message
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


class PacoBaseException(Exception):
    title = "Generic Paco Error"

class PacoBucketExists(PacoBaseException):
    title = "S3 Bucket already exists"

class UnsupportedCloudFormationParameterType(PacoBaseException):
    title = "Unsupported CloudFormation Parameter Type"

class InvalidLogSetConfiguration(PacoBaseException):
    title = "Invalid Log Set configuration in YAML"

class PacoUnsupportedFeature(PacoBaseException):
    title = "Feature does not yet exist"

class InvalidPacoHome(PacoBaseException):
    title = "Paco did not get a valid PACO_HOME path to a Paco project"

class InvalidPacoScope(PacoBaseException):
    title = "Invalid CONFIG_SCOPE argument"

class MissingAccountId(PacoBaseException):
    title = "No AWS account id"

class InvalidAccountName(PacoBaseException):
    title = "Invalid AWS account name"

class InvalidVersionControl(PacoBaseException):
    title = "Invalid version control"
