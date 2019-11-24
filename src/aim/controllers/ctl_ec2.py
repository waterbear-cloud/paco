import os, sys
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode, InvalidAIMScope
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError, BotoCoreError
from aim.core.yaml import YAML
from aim.models import schemas


yaml=YAML()
yaml.default_flow_sytle = False

class EC2Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(
            aim_ctx,
            "Resource",
            "EC2"
        )
        self.init_done = False

    def print_keypair(self, keypair, message, sub_entry=False):
        service_name = "keypairs: "
        header = "EC2 Service: "
        if sub_entry == True:
            header = "             "
            service_name_space = ""
            for _ in range(len(service_name)):
                service_name_space += " "
            service_name = service_name_space
        print("%s%s%s: %s" % (header, service_name, keypair.name, message))

    def init(self, command=None, model_obj=None):
        if self.init_done:
            return
        self.init_done = True
        if command == 'init':
            return

        # currently EC2.yaml only holds keypairs
        # ToDo: enable resource.ec2.keypairs
        if schemas.IEC2Resource.providedBy(model_obj):
            self.keypairs = model_obj.keypairs.values()
        elif schemas.IEC2KeyPair.providedBy(model_obj):
            self.keypairs = [ model_obj ]
        elif model_obj != None:
            raise InvalidAIMScope("Scope of {} not operable.".format(model_obj.aim_ref_parts))

        for keypair in self.keypairs:
            aws_account_ref = keypair.account
            keypair._account_ctx = self.aim_ctx.get_account_context(account_ref=aws_account_ref)
            keypair._ec2_client = keypair._account_ctx.get_aws_client(
                'ec2',
                aws_region=keypair.region
            )
            try:
                keypair._aws_info = keypair._ec2_client.describe_key_pairs(
                    KeyNames=[keypair.name]
                )['KeyPairs'][0]
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
                    pass
                else:
                    # TOOD: Make this more verbose
                    raise StackException(AimErrorCode.Unknown)

    def validate(self):
        for keypair in self.keypairs:
            if hasattr(keypair, '_aws_info'):
                self.print_keypair(keypair, "Key pair has been previously provisioned.")
                self.print_keypair(keypair, "Fingerprint: %s" % (keypair._aws_info['KeyFingerprint']), sub_entry=True)
            else:
                self.print_keypair(keypair, "Key pair has NOT been provisioned.")

    def provision(self):
        for keypair in self.keypairs:
            if hasattr(keypair, '_aws_info'):
                self.print_keypair(keypair, "Key pair already provisioned.")
            keypair._aws_info = keypair._ec2_client.create_key_pair(KeyName=keypair.name)
            self.print_keypair(keypair, "Key pair created successfully.")
            self.print_keypair(keypair, "Account: %s" % (keypair._account_ctx.get_name()), sub_entry=True)
            self.print_keypair(keypair, "Region:  %s" % (keypair.region), sub_entry=True)
            self.print_keypair(keypair, "Fingerprint: %s" % (keypair._aws_info['KeyFingerprint']), sub_entry=True)
            self.print_keypair(keypair, "Key: \n%s" % (keypair._aws_info['KeyMaterial']), sub_entry=True)

    def delete(self):
        for keypair in self.keypairs:
            if hasattr(keypair, '_aws_info'):
                self.print_keypair(keypair,"Deleting key pair.")
                keypair._ec2_client.delete_key_pair(KeyName=keypair.name)
                self.print_keypair(keypair, "Delete successful.", sub_entry=True)
            else:
                self.print_keypair(keypair, "Key pair does not exist.")
