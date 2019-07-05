import os
from aim.stack_group import Route53StackGroup
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError, BotoCoreError

class EC2Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Service",
                         "EC2")

        self.config = self.aim_ctx.project['ec2']

        #self.aim_ctx.log("EC2 Service: Configuration")

        self.init_done = False
        self.ec2_client = None
        self.ec2_service_name = None
        self.keypair_id = None
        self.keypair_config = None
        self.keypair_info = None
        self.keypair_account_ctx = None

    def print_ec2(self, message, sub_entry=False):
        service_name = self.ec2_service_name + ": "
        if self.ec2_service_name == 'keypair':
            component_name = self.keypair_config.name
        else:
            component_name = 'unknown'
        header = "EC2 Service: "
        if sub_entry == True:
            header = "             "
            service_name_space = ""
            for _ in range(len(service_name)):
                service_name_space += " "
            service_name = service_name_space

        print("%s%s%s: %s" % (header, service_name, component_name, message))

    def init(self, init_config):
        if self.init_done:
            return
        self.init_done = True
        self.ec2_service_name = init_config['service']
        if self.ec2_service_name == 'keypair':
            self.keypair_id = init_config['id']
            self.keypair_config = self.config.keypairs[self.keypair_id]
            aws_account_ref = self.keypair_config.account
            self.keypair_account_ctx = self.aim_ctx.get_account_context(account_ref=aws_account_ref)
            self.ec2_client = self.keypair_account_ctx.get_aws_client('ec2')
            try:
                self.keypair_info = self.ec2_client.describe_key_pairs(
                    KeyNames=[self.keypair_config.name]
                )['KeyPairs'][0]
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
                    pass
                else:
                    # TOOD: Make this more verbose
                    raise StackException(AimErrorCode.Unknown)
        else:
            print("EC2 Service: Unknown EC2 service name: %s" % self.ec2_service_name)

    def validate(self):
        if self.ec2_service_name == 'keypair':
            if self.keypair_info == None:
                self.print_ec2("Key pair has NOT been provisioned.")
            else:
                self.print_ec2("Key pair has been provisioned.")
                self.print_ec2("Fingerprint: %s" % (self.keypair_info['KeyFingerprint']), sub_entry=True)


    def provision(self):
        if self.ec2_service_name == 'keypair':
            if self.keypair_info != None:
                self.print_ec2("Key pair has already been provisioned.")
                return

            self.keypair_info = self.ec2_client.create_key_pair(KeyName=self.keypair_config.name)
            self.print_ec2("Key pair created successfully.")
            self.print_ec2("Account: %s" % (self.keypair_account_ctx.get_name()), sub_entry=True)
            self.print_ec2("Region:  %s" % (self.keypair_config.region), sub_entry=True)
            self.print_ec2("Fingerprint: %s" % (self.keypair_info['KeyFingerprint']), sub_entry=True)
            self.print_ec2("Key: \n%s" % (self.keypair_info['KeyMaterial']), sub_entry=True)

    def delete(self):
        if self.ec2_service_name == 'keypair':
            if self.keypair_info != None:
                self.print_ec2("Deleting key pair.")
                self.ec2_client.delete_key_pair(KeyName=self.keypair_config.name)
                self.print_ec2("Delete successful.", sub_entry=True)
            else:
                self.print_ec2("Key pair does not exist and may have already been deleted.")