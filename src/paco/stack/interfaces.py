from zope.interface import Interface


class IStack(Interface):
    "A set of related cloud resources"

class ICloudFormationStack(IStack):
    "A set of related AWS resources provisioned as CloudFormation Stack(s)"

class IBotoStack(IStack):
    "A set of related AWS resoruces provisioned with AWS API class"
