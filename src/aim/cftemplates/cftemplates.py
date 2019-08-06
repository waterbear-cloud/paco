import boto3
import os
import pathlib
import random
import string
from enum import Enum
from aim.core.exception import StackException
from aim.core.exception import AimErrorCode
from aim.stack_group import Stack
from aim.models import references
from aim.models.references import Reference
from aim.utils import dict_of_dicts_merge
from aim.utils import md5sum
from botocore.exceptions import ClientError
from pprint import pprint


# StackOutputParam
#    Holds a list of dicts describing a stack and the outputs that are required
#    to populate another stacks input parameter.
#    A list of outputs can be provided which will allow the generation of a list
#    for to pass into a stack parameter.
#    (ie, Security Group lists)
class StackOutputParam():
    def __init__(self, param_key, stack=None, stack_output_key=None):
        self.key = param_key
        # entry:
        #   'stack': stack,
        #   'output_keys': []
        self.entry_list = []
        self.use_previous_value = False
        self.resolved_value = ""
        #print(param_key)
        if stack !=None and stack_output_key !=None:
            #print("Adding stackoutput key: " + stack_output_key)
            self.add_stack_output( stack, stack_output_key)

    def add_stack_output(self, stack, stack_output_key):
        if stack_output_key == None:
            raise AimErrorException(AimErrorCode.Unknown)
        #print(stack.template.aws_name + ": add_stack_output: output_key: " + stack_output_key)
        for entry in self.entry_list:
            if entry['stack'] == stack:
                entry['output_keys'].append(stack_output_key)

        if len(self.entry_list) == 0:
            entry = {'stack': stack,
                     'output_keys': [stack_output_key]}
            self.entry_list.append(entry)


    def gen_parameter_value(self):
        param_value = ""
        comma = ''
        #print("cftemplates: StackOutputParam: gen_parameter_value: ")
        #pprint(repr(self.entry_list))
        for entry in self.entry_list:
            for output_key in entry['output_keys']:
                #print(entry['stack'].template.aws_name + ": gen_parameter: output_key: " + output_key)
                output_value = entry['stack'].get_outputs_value(output_key)
                #print("Value: " + output_value)
                param_value += comma + output_value
                comma = ','

        return param_value

    # Generates a parameter entry
    #  - All stacks are queried, their output values gathered and are placed
    #    in a single comma delimited list to be passed to the next stacks
    #    parameter as a single value
    def gen_parameter(self):
        param_value = self.gen_parameter_value()
        return Parameter(self.key, param_value, self.use_previous_value, self.resolved_value)

class StackOutputConfig():
    def __init__(self, config_ref, key):
        self.key = key
        self.config_ref = config_ref

    def get_config_dict(self, stack):
        conf_dict = current = {}
        ref_part_list = self.config_ref.split('.')
        for ref_part in ref_part_list:
            current[ref_part] = {}
            last_dict = current
            current = current[ref_part]

        last_dict[ref_part]['__name__'] = stack.get_outputs_value(self.key)

        return conf_dict


class Parameter():
    def __init__(self,
                 key,
                 value,
                 use_previous_value=False,
                 resolved_value=""):
        self.key = key
        # Normalize param_value to a string
        if type(value) == bool:
            if value:
                normalized_value = "true"
            else:
                normalized_value = "false"
        elif type(value) == int:
            normalized_value = str(value)
        elif type(value) == str:
            normalized_value = value
        else:
            print("Error: Parameter: Type Error")
            print(type(value))
            raise AimErrorException(AimErrorCode.Unknown)

        self.value = normalized_value
        self.use_previous_value = use_previous_value
        self.resolved_value = resolved_value

    def gen_parameter_value(self):
        #print("Key: " + self.key + ": Value: " + self.value)
        return self.value

    def gen_parameter(self):
        return self

class CFTemplate():
    def __init__(self,
                 aim_ctx,
                 account_ctx,
                 aws_region,
                 config_ref,
                 aws_name,
                 iam_capabilities=[] ):
        self.aim_ctx = aim_ctx
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.build_folder = os.path.join(aim_ctx.build_folder, "templates")
        self.yaml_path = None
        self.parameters = []
        self.capabilities = iam_capabilities
        self.body = None
        self.cf_client = self.account_ctx.get_aws_client('cloudformation')
        self.aws_name = aws_name.replace('_', '-')
        self.config_ref = config_ref
        self.stack = None
        self.template_file_id = None
        self.stack_output_config_list = []

    def set_template_file_id(self, file_id):
        self.template_file_id = file_id
        self.yaml_path = None

    def get_yaml_path(self):
        if self.yaml_path == None:
            yaml_filename = self.stack.get_name()
            if self.template_file_id != None:
                yaml_filename += "-" + self.template_file_id
            yaml_filename += ".yaml"
            #print("BF: " + self.build_folder)
            #print("YF: " + yaml_filename)
            self.yaml_path = os.path.join(self.build_folder, self.account_ctx.get_name())
            #print("YP: " + self.yaml_path)
            if self.stack.aws_region != None:
                self.yaml_path = os.path.join(self.yaml_path, self.stack.aws_region)
            else:
                raise StackException(AimErrorCode.Unknown)
                #print("YP: " + self.yaml_path)

            pathlib.Path(self.yaml_path).mkdir(parents=True, exist_ok=True)
            self.yaml_path = os.path.join(self.yaml_path, yaml_filename)
            #print("YP: " + self.yaml_path)
        return self.yaml_path

    # Move this somewhere else?
    def aim_sub(self):
        #print("Start sub")
        while True:
            # Isolate string between quotes: aim.sub ''
            sub_idx = self.body.find('aim.sub')
            if sub_idx == -1:
                #print("break 1")
                break
            #print("Found a sub: " + self.body[sub_idx:sub_idx+128])
            # print(self.body)
            end_idx = self.body.find('\n', sub_idx)
            if end_idx == -1:
                end_idx = len(self.body)
            str_idx = self.body.find("'", sub_idx, end_idx)
            if str_idx == -1:
                raise StackException(AimErrorCode.Unknown)
            str_idx += 1
            end_str_idx = self.body.find("'", str_idx, end_idx)
            if end_str_idx == -1:
                raise StackException(AimErrorCode.Unknown)
            #print("Aim SUB: %s" % (self.body[str_idx:str_idx+(end_str_idx-str_idx)]))
            # Isolate any ${} replacements
            first_pass = True
            while True:
                dollar_idx = self.body.find("${", str_idx, end_str_idx)
                if dollar_idx == -1:
                    if first_pass == True:
                        raise StackException(AimErrorCode.Unknown)
                    else:
                        #print("break 2")
                        break
                rep_1_idx = dollar_idx
                rep_2_idx = self.body.find("}", rep_1_idx, end_str_idx)+1
                next_ref_idx = self.body.find("aim.ref ", rep_1_idx, rep_2_idx)
                if next_ref_idx != -1:
                    sub_ref_idx = next_ref_idx
                    sub_ref = self.body[sub_ref_idx:sub_ref_idx+(rep_2_idx-sub_ref_idx-1)]
                    #print("Sub ref: " + sub_ref)
                    if sub_ref.find('<account>') != -1:
                        sub_ref = sub_ref.replace('<account>', self.account_ctx.get_name())
                    if sub_ref.find('<region>') != -1:
                        sub_ref = sub_ref.replace('<region>', self.aws_region)

                    sub_value = self.aim_ctx.get_ref(sub_ref)
                    if sub_value == None:
                        raise StackException(
                            AimErrorCode.Unknown,
                            message="cftemplate: aim_sub: Unable to locate value for ref: " + sub_ref
                        )
                    #print("Sub Value: %s" % (sub_value))
                    # Replace the ${}
                    sub_var = self.body[rep_1_idx:rep_1_idx+(rep_2_idx-rep_1_idx)]
                    #print("Sub var: %s" % (sub_var))
                    self.body = self.body.replace(sub_var, sub_value, 1)
                else:
                    #print("break 3")
                    break
                first_pass = False

            # Remote aim.sub '' scaffolding
            self.body = self.body[:sub_idx] + self.body[str_idx:]
            end_idx = self.body.find('\n', sub_idx)
            end_str_idx = self.body.find("'", sub_idx, end_idx)
            self.body = self.body[:end_str_idx] + self.body[end_str_idx+1:]
            #print("break 4")
            #break
        #print("End sub")

    def validate(self):
        self.generate_template()
        self.aim_ctx.log("Validate template: " + self.get_yaml_path())
        try:
            response = self.cf_client.validate_template(TemplateBody=self.body)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                self.aim_ctx.log("Validation error: " + e.response['Error']['Message'])
                raise StackException(AimErrorCode.TemplateValidationError)
        #self.aim_ctx.log("Validation successful")

    def provision(self):
        #print("cftemplate: provision: " + self.get_yaml_path())
        self.generate_template()

    def delete(self):
        pass

    def generate_template(self):
        #print("Generating template: " + self.get_yaml_path())
        self.aim_sub()
        # Create folder and write template body to file
        pathlib.Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        stream = open(self.get_yaml_path(), 'w')
        stream.write(self.body)
        stream.close()

    # Sets Scheduled output parameters to be collected from one stacks Outputs
    #   - This is called after a stacks status has been polled
    def generate_stack_parameters(self):
        #print("Generating Stack Parameters")
        parameter_list = []
        for param_entry in self.parameters:
            parameter = param_entry.gen_parameter()
            stack_param_entry = {
                'ParameterKey': parameter.key,
                'ParameterValue': parameter.value,
                'UsePreviousValue': parameter.use_previous_value,
                'ResolvedValue': parameter.resolved_value  # For resolving SSM Parameters
            }

            parameter_list.append(stack_param_entry)

        #pprint(repr(parameter_list))
        return parameter_list

    # Adds a parameter to the template's stack
    #   output_param_key:  If string: Grabs the value of the key from the stacks oututs
    #                      If list: Grabs the values of each key in the list and forms a single comma delimited string as the value
    def set_parameter( self,
                       param_key,
                       param_value=None,
                       use_previous_param_value=False,
                       resolved_ssm_value=""):

        param_entry = None
        if type(param_key) == StackOutputParam:
            #print("Type: StackOutput")
            param_entry = param_key
        elif type(param_key) == Parameter:
            #print("Type: Parameter")
            param_entry = param_key
        elif isinstance(param_value, list):
            param_entry = Parameter(param_key, self.list_to_string(param_value))
        elif isinstance(param_value, str) and references.is_ref(param_value):
            param_value = param_value.replace("<account>", self.account_ctx.get_name())
            param_value = param_value.replace("<region>", self.aws_region)
            ref = Reference(param_value)
            ref_value = ref.resolve(self.aim_ctx.project, account_ctx=self.account_ctx)
            if ref_value == None:
                raise StackException(
                    AimErrorCode.Unknown,
                    message="cftemplate: set_parameter: Unable to locate value for ref: " + param_value
                )
            if isinstance(ref_value, Stack):
                stack_output_key = self.get_stack_outputs_key_from_ref(ref, ref_value)
                param_entry = StackOutputParam(param_key, ref_value, stack_output_key)
            else:
                param_entry = Parameter(param_key, ref_value)

        if param_entry == None:
            param_entry = Parameter(param_key, param_value)
            if param_entry == None:
                #print("NOOOOOOOOOOOOOOOO")
                raise StackException(AimErrorCode.Unknown)
        # Append the parameter to our list
        self.parameters.append(param_entry)

    def gen_cache_id(self):
        template_md5 = md5sum(self.get_yaml_path())
        outputs_str = ""
        for param_entry in self.parameters:
            param_value = param_entry.gen_parameter_value()
            outputs_str += param_value

        outputs_md5 = md5sum(str_data=outputs_str)

        return template_md5+outputs_md5


    def set_template(self, template_body):
        self.body = template_body

    # Gets the output key of a project reference
    def get_stack_outputs_key_from_ref(self, ref, stack=None):
        if isinstance(ref, Reference) == False:
            raise StackException(
                AimErrorCode.Unknown,
                message="Invalid Reference object")


        if stack == None:
            stack = ref.resolve(self.aim_ctx.project)
        output_key = stack.get_outputs_key_from_ref(ref)
        if output_key == None:
            raise StackException(
                AimErrorCode.Unknown,
                message="Unable to find outputkey for ref: %s" % ref.raw)
        return output_key


    # TODO: Put in a common place
    def list_to_string(self, list_to_convert):
        comma=''
        str_list = ""
        for item in list_to_convert:
            str_list += comma + item
            comma = ','
        return str_list

    def gen_cf_logical_name(self, name, sep=None):
        sep_list = ['_','-','@','.']
        if sep != None:
            sep_list = [sep]
        for sep in sep_list:
            cf_name = ""
            for name_item in name.split(sep):
                if len(name_item) > 1:
                    cf_name += name_item[0].upper() + name_item[1:]
                else:
                    cf_name += name_item.upper()
            name = cf_name
        cf_name = cf_name.replace('-','')

        return cf_name

    def register_stack_output_config(self,
                                     config_ref,
                                     stack_output_key):
        stack_output_config = StackOutputConfig(config_ref, stack_output_key)
        self.stack_output_config_list.append(stack_output_config)




    def process_stack_output_config(self, stack):
        merged_config = {}
        for output_config in self.stack_output_config_list:
            config_dict = output_config.get_config_dict(stack)
            merged_config = dict_of_dicts_merge(merged_config, config_dict)

        return merged_config

    def lb_hosted_zone_id(self, lb_type, lb_region):
        nlb_zone_id = {
            'us-east-2': 'ZLMOA37VPKANP',
            'us-east-1': 'Z26RNL4JYFTOTI',
            'us-west-1': 'Z24FKFUX50B4VW',
            'us-west-2': 'Z18D5FSROUN65G',
            'ap-south-1': 'ZVDDRBQ08TROA',
            'ap-northeast-3': 'Z1GWIQ4HH19I5X',
            'ap-northeast-2': 'ZIBE1TIR4HY56',
            'ap-southeast-1': 'ZKVM4W9LS7TM',
            'ap-southeast-2': 'ZCT6FZBF4DROD',
            'ap-northeast-1': 'Z31USIVHYNEOWT',
            'ca-central-1': 'Z2EPGBW3API2WT',
            'cn-north-1': 'Z3QFB96KMJ7ED6',
            'cn-northwest-1': 'ZQEIKTCZ8352D',
            'eu-central-1': 'Z3F0SRJ5LGBH90',
            'eu-west-1': 'Z2IFOLAFXWLO4F',
            'eu-west-2': 'ZD4D7Y8KGAS4G',
            'eu-west-3': 'Z1CMS0P5QUZ6D5',
            'eu-north-1': 'Z1UDT6IFJ4EJM',
            'sa-east-1': 'ZTK26PT1VY4CU'
        }
        lb_zone_id = {
          'us-east-2': 'Z3AADJGX6KTTL2',
          'us-east-1': 'Z35SXDOTRQ7X7K',
          'us-west-1': 'Z368ELLRRE2KJ0',
          'us-west-2': 'Z1H1FL5HABSF5',
          'ap-south-1': 'ZP97RAFLXTNZK',
          'ap-northeast-3': 'Z5LXEXXYW11ES',
          'ap-northeast-2': 'ZWKZPGTI48KDX',
          'ap-southeast-1': 'Z1LMS91P8CMLE5',
          'ap-southeast-2': 'Z1GM3OXH4ZPM65',
          'ap-northeast-1': 'Z14GRHDCWA56QT',
          'ca-central-1': 'ZQSVJUPU6J1EY',
          'cn-north-1': 'Z3BX2TMKNYI13Y',
          'cn-northwest-1': 'Z3BX2TMKNYI13Y',
          'eu-central-1': 'Z215JYRZR1TBD5',
          'eu-west-1': 'Z32O12XQLNTSW2',
          'eu-west-2': 'ZHURV8PSTC4K8',
          'eu-west-3': 'Z3Q77PNBQS71R4',
          'eu-north-1': 'Z23TAZ6LKFMNIO',
          'sa-east-1': 'Z2P70J7HTTTPLU'
        }

        if lb_type == 'elb' or lb_type == 'alb':
            return lb_zone_id[lb_region]
        elif lb_type == 'nlb':
            return nlb_zone_id[lb_region]
        else:
            raise AimErrorException(AimErrorCode.Unknown)

    def normalize_resource_name(self, name):
        name = name.replace('-', '')
        name = name.replace('_', '')
        name = name.replace('.', '')
        name = name.replace('@', '')
        return name

    def gen_parameter(self, param_type, name, description):
        return """
  {}:
    Description: {}
    Type: {}
""".format(name, description, param_type)
