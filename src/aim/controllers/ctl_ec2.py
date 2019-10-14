import os, sys
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.controllers.controllers import Controller
from botocore.exceptions import ClientError, BotoCoreError
from aim.core.yaml import YAML

yaml=YAML()
yaml.default_flow_sytle = False

class EC2Controller(Controller):
    def __init__(self, aim_ctx):
        super().__init__(aim_ctx,
                         "Resource",
                         "EC2")

        self.config = self.aim_ctx.project['resource']['ec2']

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
        if self.ec2_service_name == 'keypairs':
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

    def init(self, controller_args):
        if self.init_done:
            return
        self.init_done = True
        if controller_args['command'] == 'init':
            return
        self.ec2_service_name = controller_args['arg_1']
        if self.ec2_service_name == 'keypairs':
            self.keypair_id = controller_args['arg_2']
            if self.keypair_id == None:
                print("error: missing keypair id")
                print("aim provision ec2 keypairs <keypair_id>")
                sys.exit(1)
            self.keypair_config = self.config.keypairs[self.keypair_id]
            aws_account_ref = self.keypair_config.account
            self.keypair_account_ctx = self.aim_ctx.get_account_context(account_ref=aws_account_ref)
            self.ec2_client = self.keypair_account_ctx.get_aws_client('ec2', aws_region=self.keypair_config.region)
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

    def init_command(self, controller_args):
        ec2_component = controller_args['arg_1']
        if ec2_component != 'keypairs':
            print("Unknown EC2 init component: {}".format(ec2_component))
            return
        keypair_name = controller_args['arg_2']
        keypair_account = controller_args['arg_3']
        keypair_region = controller_args['arg_4']
        if keypair_name == None or keypair_region == None:
            print("aim init keypair <keypair_name> <account_name> <region>")
            return
        base_dir = os.path.join(self.aim_ctx.project_folder, 'Resources')
        ec2_config = None
        ec2_file = None
        if os.path.isfile(base_dir + os.sep + 'EC2.yaml'):
            ec2_file = base_dir + os.sep + 'EC2.yaml'
        elif os.path.isfile(base_dir + os.sep + 'EC2.yml'):
            ec2_file = base_dir + os.sep + 'EC2.yml'

        if ec2_file != None:
            with open(ec2_file, 'r') as stream:
                ec2_config = yaml.load(stream)
        else:
            ec2_file = os.path.isfile(base_dir + os.sep + 'EC2.yaml')

        if ec2_config == None:
            ec2_config = {'keypairs': {}}
        account_ctx = self.aim_ctx.get_account_context(account_name=keypair_account)
        print("\nAIM EC2 keypair initialization")
        print("------------------------------\n")
        keypair_full_name = "{}-{}-{}".format(keypair_name, keypair_account, keypair_region)
        ec2_config['keypairs'][keypair_name] = {
            'name': keypair_full_name,
            'region': keypair_region,
            'account': account_ctx.gen_ref()
        }
        with open(ec2_file, 'w') as stream:
            yaml.dump(ec2_config, stream)

        print("Added keypair {} for account {} and region {} to file at {}.".format(
            keypair_name, keypair_account, keypair_region, ec2_file
        ))


    def validate(self):
        if self.ec2_service_name == 'keypairs':
            if self.keypair_info == None:
                self.print_ec2("Key pair has NOT been provisioned.")
            else:
                self.print_ec2("Key pair has been previously provisioned.")
                self.print_ec2("Fingerprint: %s" % (self.keypair_info['KeyFingerprint']), sub_entry=True)


    def provision(self):
        if self.ec2_service_name == 'keypairs':
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
        if self.ec2_service_name == 'keypairs':
            if self.keypair_info != None:
                self.print_ec2("Deleting key pair.")
                self.ec2_client.delete_key_pair(KeyName=self.keypair_config.name)
                self.print_ec2("Delete successful.", sub_entry=True)
            else:
                self.print_ec2("Key pair does not exist and may have already been deleted.")