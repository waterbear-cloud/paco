from zope.interface import Interface
from paco.models.base import Stack
from zope.interface.declarations import classImplements

class IStack(Interface):
    "A set of related cloud resources"

# add this interface to the paco.models class
classImplements(Stack, IStack)

class ICloudFormationStack(IStack):
    "A set of related AWS resources provisioned as CloudFormation Stack(s)"

class IBotoStack(IStack):
    "A set of related AWS resoruces provisioned with AWS API class"
