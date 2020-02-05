import base64
import boto3
import os
import pathlib
import random, re
import string, sys
import troposphere
from enum import Enum
from paco import utils
from paco.core.yaml import YAML
from paco.core.exception import StackException, PacoErrorCode, PacoException
from paco.models import references
from paco.models.references import Reference
from paco.stack_group import Stack, StackOrder
from paco.utils import dict_of_dicts_merge, md5sum, big_join, list_to_comma_string
from botocore.exceptions import ClientError
from pprint import pprint
from shutil import copyfile

# deepdiff turns on Deprecation warnings, we need to turn them back off
# again right after import, otherwise 3rd libs spam dep warnings all over the place
from deepdiff import DeepDiff
import warnings
warnings.simplefilter("ignore")


class StackOutputParam():
    """
    Holds a list of dicts describing a stack and the outputs that are required
    to populate another stacks input parameter.
    A list of outputs can be provided which will allow the generation of a list
    to pass into a stack parameter (e.g. Security Group lists).
    """

    def __init__(
        self,
        param_key,
        stack=None,
        stack_output_key=None,
        param_template=None
    ):
        self.key = param_key
        self.entry_list = []
        self.use_previous_value = False
        self.resolved_value = ""
        self.stack = stack
        self.param_template = param_template
        if stack !=None and stack_output_key !=None:
            self.add_stack_output( stack, stack_output_key)

    def add_stack_output(self, stack, stack_output_key):
        if stack_output_key == None:
            raise PacoException(PacoErrorCode.Unknown, message="Stack Output key is unset")
        self.stack = stack
        for entry in self.entry_list:
            if entry['stack'] == stack:
                entry['output_keys'].append(stack_output_key)
                return

        entry = {
            'stack': stack,
            'output_keys': [stack_output_key]
        }
        self.entry_list.append(entry)

    def gen_parameter_value(self):
        param_value = ""
        comma = ''
        for entry in self.entry_list:
            for output_key in entry['output_keys']:
                output_value = entry['stack'].get_outputs_value(
                    output_key
                )
                param_value += comma + output_value
                comma = ','

        return param_value

    def gen_parameter(self):
        """
        Generate a parameter entry
        All stacks are queried, their output values gathered and are placed
        in a single comma delimited list to be passed to the next stacks
        parameter as a single value
        """
        param_value = self.gen_parameter_value()
        return Parameter(self.param_template, self.key, param_value, self.use_previous_value, self.resolved_value)


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


def marshal_value_to_cfn_yaml(value):
    "Cast a Python value to a string usable as a CloudFormation YAML value"
    if type(value) == bool:
        if value:
            return "true"
        else:
            return "false"
    elif type(value) == int:
        return str(value)
    elif type(value) == str:
        return value
    else:
        raise PacoException(
            PacoErrorCode.Unknown,
            message="Parameter could not be cast to a YAML value: {}".format(type(value))
        )

class Parameter():
    def __init__(
        self,
        template,
        key,
        value,
        use_previous_value=False,
        resolved_value=""
    ):
        self.key = key
        self.value = marshal_value_to_cfn_yaml(value)
        self.use_previous_value = use_previous_value
        self.resolved_value = resolved_value

    def gen_parameter_value(self):
        return self.value

    def gen_parameter(self):
        return self


class CFTemplate():
    """A CloudFormation template"""
    def __init__(
        self,
        paco_ctx,
        account_ctx,
        aws_region,
        config_ref,
        aws_name=None,
        enabled=True,
        environment_name = None,
        stack_group=None,
        stack_tags=None,
        stack_hooks=None,
        stack_order=None,
        change_protected=False,
        iam_capabilities=[]
    ):
        self.update_only = False
        self.enabled = enabled
        self.paco_ctx = paco_ctx
        self.account_ctx = account_ctx
        self.aws_region = aws_region
        self.build_folder = os.path.join(paco_ctx.build_folder, "templates")
        self.yaml_path = None
        self.applied_yaml_path = None
        self.parameters = []
        self.capabilities = iam_capabilities
        self.body = None
        self.aws_name = aws_name
        self.config_ref = config_ref
        self.template_file_id = None
        self.environment_name = environment_name
        # Stack
        self.stack = None
        self.stack_group = stack_group
        self.stack_tags = stack_tags
        self.stack_hooks = stack_hooks
        if stack_order == None:
            self.stack_order = [StackOrder.PROVISION, StackOrder.WAIT]
        else:
            self.stack_order = stack_order
        self.stack_output_config_list = []
        # Dependencies
        self.dependency_template = None
        self.dependency_group = False
        self.change_protected = change_protected

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if value == False:
            self.update_only = True
        else:
            self.update_only = False
        self._enabled = value

    @property
    def cfn_client(self):
        if hasattr(self, '_cfn_client') == False:
            self._cfn_client = self.account_ctx.get_aws_client('cloudformation', self.aws_region)
        return self._cfn_client

    def init_template(self, description):
        "Initializes a Troposphere template"
        self.template = troposphere.Template(
            Description = description,
        )
        self.template.set_version()
        self.template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="EmptyTemplatePlaceholder")
        )

    def set_template_file_id(self, file_id):
        self.template_file_id = file_id
        self.yaml_path = None
        self.applied_yaml_path = None

    def set_dependency(self, template, dependency_name):
        """
        Makes a template dependent on another.
        This is used when a template needs to be created with an initial
        configuration, and then updated later when new information becomes
        available. This is used by KMS in the DeploymentPipeline app engine.
        """
        self.dependency_template = template
        self.dependency_group = True
        if template.dependency_template == None:
            template.set_template_file_id('parent-'+dependency_name)
            template.dependency_group = True


    def get_yaml_path(self, applied=False):
        if self.yaml_path and applied == False:
            return self.yaml_path
        if self.applied_yaml_path and applied == True:
            return self.applied_yaml_path

        yaml_filename = self.stack.get_name()
        if self.template_file_id != None:
            yaml_filename += "-" + self.template_file_id
        yaml_filename += ".yaml"

        if applied == False:
            yaml_path = os.path.join(self.build_folder, self.account_ctx.get_name())
        else:
            yaml_path = os.path.join(self.paco_ctx.home, 'aimdata', 'applied', 'cloudformation', self.account_ctx.get_name())

        if self.stack.aws_region != None:
            yaml_path = os.path.join(yaml_path, self.stack.aws_region)
        else:
            raise StackException(PacoErrorCode.Unknown, message = "AWS region is unavailable: {}".format(yaml_path))

        pathlib.Path(yaml_path).mkdir(parents=True, exist_ok=True)
        yaml_path = os.path.join(yaml_path, yaml_filename)

        if applied == True:
            self.applied_yaml_path = yaml_path
        else:
            self.yaml_path = yaml_path

        return yaml_path

    # Move this somewhere else?
    def paco_sub(self):
        #print("Start sub")
        while True:
            # Isolate string between quotes: paco.sub ''
            sub_idx = self.body.find('paco.sub')
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
                raise StackException(PacoErrorCode.Unknown, message="paco.sub error")
            str_idx += 1
            end_str_idx = self.body.find("'", str_idx, end_idx)
            if end_str_idx == -1:
                raise StackException(PacoErrorCode.Unknown, message = "paco.sub error")
            #print("Paco SUB: %s" % (self.body[str_idx:str_idx+(end_str_idx-str_idx)]))
            # Isolate any ${} replacements
            first_pass = True
            while True:
                dollar_idx = self.body.find("${", str_idx, end_str_idx)
                if dollar_idx == -1:
                    if first_pass == True:
                        message = 'Unable to find paco.ref in paco.sub expression.\n'
                        message += 'Stack: {}\n'.format(self.stack.get_name())
                        message += "paco.sub '{}'\n".format(self.body[str_idx:end_str_idx])
                        raise StackException(PacoErrorCode.Unknown, message = message)
                    else:
                        #print("break 2")
                        break
                rep_1_idx = dollar_idx
                rep_2_idx = self.body.find("}", rep_1_idx, end_str_idx)+1
                next_ref_idx = self.body.find("paco.ref ", rep_1_idx, rep_2_idx)
                if next_ref_idx != -1:
                    sub_ref_idx = next_ref_idx
                    sub_ref = self.body[sub_ref_idx:sub_ref_idx+(rep_2_idx-sub_ref_idx-1)]
                    #print("Sub ref: " + sub_ref)
                    if sub_ref.find('<account>') != -1:
                        sub_ref = sub_ref.replace('<account>', self.account_ctx.get_name())
                    if sub_ref.find('<environment>') != -1:
                        sub_ref = sub_ref.replace('<environment>', self.environment_name)
                    if sub_ref.find('<region>') != -1:
                        sub_ref = sub_ref.replace('<region>', self.aws_region)

                    sub_value = self.paco_ctx.get_ref(sub_ref)
                    if sub_value == None:
                        raise StackException(
                            PacoErrorCode.Unknown,
                            message="cftemplate: paco_sub: Unable to locate value for ref: " + sub_ref
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

            # Remote paco.sub '' scaffolding
            self.body = self.body[:sub_idx] + self.body[str_idx:]
            end_idx = self.body.find('\n', sub_idx)
            end_str_idx = self.body.find("'", sub_idx, end_idx)
            self.body = self.body[:end_str_idx] + self.body[end_str_idx+1:]
            #print("break 4")
            #break
        #print("End sub")

    def validate(self):
        applied_file_path, new_file_path = self.init_template_store_paths()
        short_yaml_path = str(new_file_path).replace(self.paco_ctx.home, '')
        if short_yaml_path[0] == '/':
            short_yaml_path = short_yaml_path[1:]
        if self.enabled == False:
            if self.paco_ctx.quiet_changes_only == False:
                self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name(), "Disabled", short_yaml_path)
            return
        elif self.change_protected:
            if self.paco_ctx.quiet_changes_only == False:
                self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name(), "Protected", short_yaml_path)
            return
        self.generate_template()
        new_str = ''
        if applied_file_path.exists() == False:
            new_str = ':new'
        self.paco_ctx.log_action_col("Validate", self.account_ctx.get_name(), "Template"+new_str, short_yaml_path)
        try:
            self.cfn_client.validate_template(TemplateBody=self.body)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                message = "Validation Error: {}\nStack: {}\nTemplate: {}\n".format(
                    e.response['Error']['Message'],
                    self.stack.get_name(),
                    self.get_yaml_path()
                )
                raise StackException(PacoErrorCode.TemplateValidationError, message=message)
        #self.paco_ctx.log("Validation successful")
        self.validate_template_changes()

    def provision(self):
        #print("cftemplate: provision: " + self.get_yaml_path())
        self.generate_template()

    def delete(self):
        # Applied Template Data
        applied_template_path, _ = self.init_template_store_paths()
        applied_parameters_path = self.init_applied_parameters_path(applied_template_path)
        short_applied_template_path = str(applied_template_path).replace(self.paco_ctx.home, '')
        short_applied_parameters_path = str(applied_parameters_path).replace(self.paco_ctx.home, '')
        if self.paco_ctx.verbose == True:
            self.paco_ctx.log_action_col('Delete', 'Template', 'Applied', short_applied_template_path)
            self.paco_ctx.log_action_col('Delete', 'Parameters', 'Applied', short_applied_parameters_path)
        try:
            applied_template_path.unlink()
            applied_parameters_path.unlink()
        except FileNotFoundError:
            pass

        # The template itself
        short_yaml_path = self.get_yaml_path().replace(self.paco_ctx.home, '')
        if self.paco_ctx.verbose == True:
            self.paco_ctx.log_action_col('Delete', 'Template', 'Build', short_yaml_path)
        try:
            pathlib.Path(self.get_yaml_path()).unlink()
        except FileNotFoundError:
            pass
        pass

    def generate_template(self):
        "Write template to the filesystem"
        self.paco_sub()
        # Create folder and write template body to file
        pathlib.Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        stream = open(self.get_yaml_path(), 'w')
        stream.write(self.body)
        stream.close()

        yaml_path = pathlib.Path(self.get_yaml_path())
        # Template size limit is 51,200 bytes
        # Start warning if the template size gets close
        warning_size_limite_bytes = 41200
        if yaml_path.stat().st_size >= warning_size_limite_bytes:
            print("WARNING: Template is reaching size limit of 51,200 bytes: Current size: {} bytes ".format(yaml_path.stat().st_size))
            print("template: " + yaml_path)


    def init_applied_parameters_path(self, applied_template_path):
        return applied_template_path.with_suffix('.parameters')

    def apply_stack_parameters(self):
        parameter_list = self.generate_stack_parameters()
        applied_template_path, _ = self.init_template_store_paths()
        applied_param_file_path = self.init_applied_parameters_path(applied_template_path)
        yaml = YAML(pure=True)
        with open(applied_param_file_path, 'w') as stream:
            yaml.dump(parameter_list, stream)

    def confirm_stack_parameter_changes(self, parameter_list):
        """
        Display changes to a stack's Parameters and confirm changes
        """
        if self.paco_ctx.disable_validation == True:
            return
        applied_file_path, new_file_path = self.init_template_store_paths()
        param_applied_file_path = applied_file_path.with_suffix('.parameters')

        if param_applied_file_path.exists() == False:
            return
        yaml = YAML(pure=True)
        yaml.allow_duplicate_keys = True
        with open(param_applied_file_path, 'r') as stream:
            applied_parameter_list = yaml.load(stream)

        # No changes detected
        if parameter_list == applied_parameter_list:
            return

        print("--------------------------------------------------------")
        print("Confirm changes to Parameters for CloudFormation Stack: " + self.stack.get_name())
        print()
        print("{}".format(self.stack.get_name()))
        if self.paco_ctx.verbose:
            print()
            print("Model: {}".format(self.config_ref))
            print("Template:  {}".format(new_file_path))
            print("Applied template:  {}".format(applied_file_path))
            print("Applied parameters:  {}".format(param_applied_file_path))
        print('')

        col_3_size = 0
        for new_param in parameter_list:
            if self.paco_ctx.verbose == True or new_param not in applied_parameter_list:
                key_len = len(new_param['ParameterKey'])
                if col_3_size < key_len: col_3_size = key_len

        for new_param in parameter_list:
            col_2_size = 12
            if new_param in applied_parameter_list:
                applied_parameter_list.remove(new_param)
                if self.paco_ctx.verbose == True:
                    self.paco_ctx.log_action_col(
                        '  ',
                        col_2 = 'Unchanged',
                        col_3 = new_param['ParameterKey'],
                        col_4 = ': {}'.format(new_param['ParameterValue']),
                        col_1_size = 2,
                        col_2_size = col_2_size,
                        col_3_size = col_3_size,
                        )
            else:
                for applied_param in applied_parameter_list:
                    if new_param['ParameterKey'] == applied_param['ParameterKey']:
                        self.paco_ctx.log_action_col(
                            '  ', col_2 = 'Changed', col_3 = applied_param['ParameterKey'],
                            col_4 = 'old: {}'.format(applied_param['ParameterValue']),
                            col_1_size = 2, col_2_size = col_2_size, col_3_size = col_3_size,
                            col_4_size = 80
                            )
                        self.paco_ctx.log_action_col(
                            '  ', col_2 = 'Changed', col_3 = new_param['ParameterKey'],
                            col_4 = 'new: {}'.format(new_param['ParameterValue']),
                            col_1_size = 2, col_2_size = col_2_size, col_3_size = col_3_size,
                            col_4_size = 80
                            )
                        # Parameter Changes
                        #print("Changed Parameter: " + new_param['ParameterKey'])
                        #print("        old value: " + applied_param['ParameterValue'])
                        #print("        new value: " + new_param['ParameterValue'])
                        if new_param['ParameterKey'] == 'UserDataScript':
                            old_decoded = base64.b64decode(applied_param['ParameterValue'])
                            new_decoded = base64.b64decode(new_param['ParameterValue'])
                            self.paco_ctx.log_action_col(
                                '  ', col_2 = 'Decoded', col_3 = 'UserDataScript',
                                col_4 = 'old: {}'.format(old_decoded.decode()),
                                col_1_size = 2, col_2_size = col_2_size, col_3_size = col_3_size,
                                col_4_size = 80
                                )
                            self.paco_ctx.log_action_col(
                                '  ', col_2 = 'Decoded', col_3 = 'UserDataScript',
                                col_4 = 'new: {}'.format(new_decoded.decode()),
                                col_1_size = 2, col_2_size = col_2_size, col_3_size = col_3_size,
                                col_4_size = 80
                                )

                    else:
                        # New parameter
                        #
                        self.paco_ctx.log_action_col(
                            '  ',
                            col_2 = 'New Param',
                            col_3 = new_param['ParameterKey'],
                            col_4 = ': {}'.format(new_param['ParameterValue']),
                            col_1_size = 2,
                            col_2_size = col_2_size,
                            col_3_size = col_3_size,
                            )
                    applied_parameter_list.remove(applied_param)
                    break

        # Deleted Parameters
        for applied_param in applied_parameter_list:
            print("Removed Parameter: {} = {}".format(applied_param['ParameterKey'], applied_param['ParameterValue']))

        print("--------------------------------------------------------")
        print("Stack: " + self.stack.get_name())
        print("")
        answer = self.paco_ctx.input_confirm_action("\nAre these changes acceptable?")
        if answer == False:
            print("Aborted run.")
            sys.exit(1)
        print()

    def generate_stack_parameters(self):
        """Sets Scheduled output parameters to be collected from one stacks Outputs.
        This is called after a stacks status has been polled.
        """
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

        return parameter_list

    def set_parameter(
        self,
        param_key,
        param_value=None,
        use_previous_param_value=False,
        resolved_ssm_value=""
    ):
        """Adds a parameter to the template's stack.
        If param_key is a string, grabs the value of the key from the stack outputs,
        if a list, grabs the values of each key in the list and forms a single comma delimited string as the value.
        """
        param_entry = None
        if type(param_key) == StackOutputParam:
            param_entry = param_key
        elif type(param_key) == Parameter:
            param_entry = param_key
        elif isinstance(param_value, list):
            # Security Group List
            param_entry = Parameter(self, param_key, list_to_comma_string(param_value))
        elif isinstance(param_value, str) and references.is_ref(param_value):
            param_value = param_value.replace("<account>", self.account_ctx.get_name())
            if self.environment_name != None:
                param_value = param_value.replace("<environment>", self.environment_name)
            elif param_value.find('<environment>') != -1:
                raise StackException(
                    PacoErrorCode.Unknown,
                    message="cftemplate: set_parameter: <environment> tag exists but self.environment_name == None: " + param_value
                )
            param_value = param_value.replace("<region>", self.aws_region)
            ref = Reference(param_value)
            ref_value = ref.resolve(self.paco_ctx.project, account_ctx=self.account_ctx)
            if ref_value == None:
                message = "Error: Unable to locate value for ref: {}\n".format(param_value)
                message += "Template: {}\n".format(self.aws_name)
                message += "Parameter: {}\n".format(param_key)
                raise StackException(
                    PacoErrorCode.Unknown,
                    message=message
                )
            if isinstance(ref_value, Stack):
                # If we need to query another stack, but that stack is not
                # enabled, then avoid setting this parameter to avoid lookup
                # errors later.
                if self.enabled == False and ref_value.template.enabled == False:
                    return None
                stack_output_key = self.get_stack_outputs_key_from_ref(ref, ref_value)
                param_entry = StackOutputParam(param_key, ref_value, stack_output_key, self)
            else:
                param_entry = Parameter(self, param_key, ref_value)

        if param_entry == None:
            param_entry = Parameter(self, param_key, param_value)
            if param_entry == None:
                raise StackException(PacoErrorCode.Unknown, message = "set_parameter says NOOOOOOOOOO")
        # Append the parameter to our list
        self.parameters.append(param_entry)

    def set_list_parameter(self, param_name, param_list, ref_att=None):
        "Sets a parameter from a list as a comma-separated value"
        # If we are not enabled, do not try to
        value_list = []
        is_stack_list = False
        for param_ref in param_list:
            if ref_att:
                param_ref += '.'+ref_att
            value = Reference(param_ref).resolve(self.paco_ctx.project)
            if isinstance(value, Stack):
                is_stack_list = True
                # If we need to query another stack, but that stack is not
                # enabled, then avoid setting this parameter to avoid lookup
                # errors later.
                if self.enabled == False and value.template.enabled == False:
                    return None
                #if self.enabled == False:
                #    return
            elif is_stack_list == True:
                raise StackException(PacoErrorCode.Unknown, message = 'Cannot have mixed Stacks and non-Stacks in the list: ' + param_ref)
            if value == None:
                raise StackException(PacoErrorCode.Unknown, message = 'Unable to resolve reference: ' + param_ref)
            value_list.append([param_ref,value])

        # If this is the first time this stack has been provisioned,
        # we will need to deferr to the stack outputs
        if is_stack_list == True:
            output_param = StackOutputParam(param_name, param_template=self)
            for param_ref, stack in value_list:
                output_key = self.get_stack_outputs_key_from_ref(Reference(param_ref))
                output_param.add_stack_output(stack, output_key)
            self.set_parameter(output_param)
        else:
            param_list = []
            for param_ref, value in value_list:
                param_list.append(value)
            self.set_parameter(param_name, ','.join(param_list))

    def gen_cache_id(self):
        "Create and return an MD5 cache id of the template"
        yaml_path = pathlib.Path(self.get_yaml_path())
        if yaml_path.exists() == False:
            return None
        template_md5 = md5sum(self.get_yaml_path())
        outputs_str = ""
        for param_entry in self.parameters:
            param_value = param_entry.gen_parameter_value()
            outputs_str += param_value

        outputs_md5 = md5sum(str_data=outputs_str)

        return template_md5+outputs_md5


    def set_template(self, template_body):
        """Sets the template and if there is not already a stack_group,
        creates a Stack and adds it to the stack_group."""
        self.body = template_body
        if self.stack_group != None:
            self.stack = Stack(
                self.paco_ctx,
                self.account_ctx,
                self.stack_group,
                self, # template
                aws_region=self.aws_region,
                stack_tags=self.stack_tags,
                hooks=self.stack_hooks,
                update_only=self.update_only,
                change_protected=self.change_protected,
            )

            self.stack_group.add_stack_order(self.stack, self.stack_order)

    def get_stack_outputs_key_from_ref(self, ref, stack=None):
        "Gets the output key of a project reference"
        if isinstance(ref, Reference) == False:
            raise StackException(
                PacoErrorCode.Unknown,
                message="Invalid Reference object")
        if stack == None:
            stack = ref.resolve(self.paco_ctx.project)
        output_key = stack.get_outputs_key_from_ref(ref)
        if output_key == None:
            raise StackException(
                PacoErrorCode.Unknown,
                message="Unable to find outputkey for ref: %s" % ref.raw)
        return output_key

    def gen_cf_logical_name(self, name, sep=None):
        """
        !! DEPRECATED !! Use self.cfn_logical_id* methods
        Create a CloudFormation safe Logical name
        """

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

    def get_outputs_key_from_ref(self, ref):
        "Finds and return the Key for the ref"
        for stack_output_config in self.stack_output_config_list:
            if stack_output_config.config_ref == ref.ref:
                return stack_output_config.key

    def register_stack_output_config(
        self,
        config_ref,
        stack_output_key
    ):
        "Register stack output config"
        if config_ref.startswith('paco.ref'):
            raise PacoException(
                PacoErrorCode.Unknown,
                message='Registered stack output config reference must not start with paco.ref: ' + config_ref
            )
        stack_output_config = StackOutputConfig(config_ref, stack_output_key)
        self.stack_output_config_list.append(stack_output_config)

    def process_stack_output_config(self, stack):
        "Process stack output config"
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
            raise PacoException(PacoErrorCode.Unknown)

    def resource_name_filter(self, name, filter_id, hash_long_names):
        "Checks a name against a filter and raises a StackException if it is not a valid AWS name"
        # Duplicated in paco.models.base.Resource
        message = None
        max_name_len = None
        if filter_id in [
            'EC2.ElasticLoadBalancingV2.LoadBalancer.Name',
            'EC2.ElasticLoadBalancingV2.TargetGroup.Name']:
            if len(name) > 32:
                max_name_len = 32
                message = "Name must not be longer than 32 characters.",
            elif filter_id.find('LoadBalancer') != -1 and name.startswith('internal-'):
                message = "Name must not start with 'internal-'"
            elif name[-1] == '-' or name[0] == '-':
                message = "Name must not begin or end with a dash."
        elif filter_id in [
            'IAM.Role.RoleName',
            'IAM.ManagedPolicy.ManagedPolicyName']:
            if len(name) > 255:
                max_name_len = 255
                message = "Name must not be longer than 255 characters."
        elif filter_id == 'IAM.Policy.PolicyName':
            if len(name) > 128:
                max_name_len = 128
                message = "Name must not be longer than 128 characters."
        elif filter_id == 'ElastiCache.ReplicationGroup.ReplicationGroupId':
            if len(name) > 40:
                max_name_len = 255
                message = "ReplicationGroupId must be 40 characters or less"
        elif filter_id == 'SecurityGroup.GroupName':
            pass
        else:
            message = 'Unknown filter_id'

        if max_name_len != None and hash_long_names == True:
            message = None
            name_hash = md5sum(str_data=name)[:8].upper()
            name = name_hash + '-' + name[((max_name_len-9)*-1):]


        if message != None:
            raise StackException(
                PacoErrorCode.Unknown,
                    message="{}: {}: {}: {}".format(
                        filter_id,
                        self.config_ref,
                        message,
                        name,
                    ))
        return name


    def resource_char_filter(self, ch, filter_id, remove_invalids=False):
        # Duplicated in paco.models.base.Resource
        # Universal check
        if ch.isalnum() == True:
            return ch
        # SecurityGroup Group Name
        # Constraints for EC2-VPC: a-z, A-Z, 0-9, spaces, and ._-:/()#,@[]+=&;{}!$*
        if filter_id == 'SecurityGroup.GroupName':
            if ch in ' ._-:/()#,@[]+=&;{}!$*':
                return ch
        elif filter_id in [
            'IAM.Role.RoleName',
            'IAM.ManagedPolicy.ManagedPolicyName',
            'IAM.Policy.PolicyName']:
            if ch in '_+=,.@-.':
                return ch
        elif filter_id == 'ElastiCache.ReplicationGroup.ReplicationGroupId':
            if ch in '-':
                return ch
        elif filter_id in [
            'EC2.ElasticLoadBalancingV2.LoadBalancer.Name',
            'EC2.ElasticLoadBalancingV2.TargetGroup.Name']:
            # Only alphanum and dases are allowed
            pass
        else:
            raise StackException(PacoErrorCode.Unknown, message="Invalid filter Id: "+filter_id)

        if remove_invalids == True:
            return ''

        # By default return a '-' for invalid characters
        return '-'


    def create_resource_name(self, name, remove_invalids=False, filter_id=None, hash_long_names=False, camel_case=False):
        """
        Resource names are only alphanumberic (A-Za-z0-9) and dashes.
        Invalid characters are removed or changed into a dash.
        """
        # Duplicated in paco.models.base.Resource
        def normalize(name, remove_invalids, filter_id, camel_case):
            uppercase_next_char = False
            new_name = ''
            for ch in name:
                if filter_id != None:
                    ch = self.resource_char_filter(ch, filter_id, remove_invalids)
                    if ch == '' and camel_case == True:
                        uppercase_next_char = True
                elif ch.isalnum() == True:
                    ch = ch
                elif remove_invalids == False:
                    ch = '-'
                elif remove_invalids == True:
                    ch = ''
                    if camel_case == True:
                        uppercase_next_char = True

                if remove_invalids == True and ch != '' and uppercase_next_char == True:
                    new_name += ch.upper()
                    uppercase_next_char = False
                else:
                    new_name += ch
            return new_name

        if name.isalnum() == True:
            new_name = name
        else:
            new_name = normalize(name, remove_invalids=remove_invalids, filter_id=filter_id, camel_case=camel_case)

        if filter_id != None:
            new_name = self.resource_name_filter(new_name, filter_id, hash_long_names)

        return new_name


    def create_resource_name_join(self, name_list, separator, camel_case=False, filter_id=None, hash_long_names=False):
        # Duplicated in paco.models.base.Resource
        name = big_join(name_list, separator, camel_case)
        return self.create_resource_name(name, filter_id=filter_id, hash_long_names=hash_long_names, camel_case=camel_case)

    def create_cfn_logical_id(self, name, camel_case=False):
        "The logical ID must be alphanumeric (A-Za-z0-9) and unique within the template."
        # Duplicated in paco.models.base.Resource
        return self.create_resource_name(name, remove_invalids=True, camel_case=camel_case).replace('-', '')

    def create_cfn_logical_id_join(self, str_list, camel_case=False):
        logical_id = big_join(str_list, '', camel_case)
        return self.create_cfn_logical_id(logical_id, camel_case=camel_case)

    def create_cfn_parameter(
        self,
        param_type,
        name,
        description,
        value,
        default=None,
        noecho=False,
        use_troposphere=False,
        troposphere_template=None,
        min_length=None,
        max_length=None
    ):
        """Return a CloudFormation Parameter
        """
        if default == '':
            default = "''"
        if value == None:
            value = default
        else:
            if type(value) == StackOutputParam:
                self.set_parameter(value)
            else:
                self.set_parameter(name, value)
        other_yaml = ""
        if default != None:
            other_yaml += '\n    Default: {}'.format(default)
        if noecho == True:
            other_yaml += '\n    NoEcho: true'
            desc_value = '**********'
        elif isinstance(value, StackOutputParam):
            desc_value = 'StackOutputParam'
        elif isinstance(value, str) == False and isinstance(value, int) == False:
            desc_value = type(value)
        else:
            desc_value = value
        if use_troposphere == False:
            return """
  # {}: {}
  {}:
    Description: {}
    Type: {}{}
""".format(name, desc_value, name, description, param_type, other_yaml)
        else:
            param_dict = {
                'Description': description,
                'Type': param_type
            }
            if default != None:
                param_dict['Default'] = default
            if noecho == True:
                param_dict['NoEcho'] = True
            if min_length != None:
                param_dict['MinLength'] = min_length
            if max_length != None:
                param_dict['MaxLength'] = max_length
            param = troposphere.Parameter.from_dict(
                name,
                param_dict
            )
            if troposphere_template != None:
                troposphere_template.add_parameter(param)
            return param

    def create_cfn_ref_list_param(
        self,
        param_type,
        name,
        description,
        value,
        ref_attribute=None,
        default=None,
        noecho=False,
        use_troposphere=False,
        troposphere_template=None
    ):
        "Create a CloudFormation Parameter from a list of refs"
        stack_output_param = StackOutputParam(name, param_template=self)
        for item_ref in value:
            if ref_attribute != None:
                item_ref += '.' + ref_attribute
            stack = self.paco_ctx.get_ref(item_ref)
            if isinstance(stack, Stack) == False:
                raise PacoException(PacoErrorCode.Unknown, message="Reference must resolve to a stack")
            stack_output_key = self.get_stack_outputs_key_from_ref(Reference(item_ref))
            stack_output_param.add_stack_output(stack, stack_output_key)

        return self.create_cfn_parameter(
            param_type,
            name,
            description,
            stack_output_param,
            default,
            noecho,
            use_troposphere,
            troposphere_template
        )

    def gen_output(self, name, value):
        "Return name and value as a CFN YAML formatted string"
        return """
  {}:
    Value: {}
""".format(name, value)

    # Role and Policy names must not be longer than 64 charcters
    def create_iam_resource_name(self, name_list, filter_id=None):
        role_name = self.create_resource_name_join(
            name_list=name_list,
            separator='-',
            camel_case=True,
            filter_id=filter_id
        )
        if len(role_name) > 64:
            name_hash = md5sum(str_data=role_name)[:8].upper()
            # len('AABBCCDD-')
            name_hash_len = len(name_hash+'-')+1
            max_role_name_len = 64

            role_name = name_hash + '-' + role_name[-(max_role_name_len-name_hash_len):]

        return role_name

    def getFromSquareBrackets(self, s):
        return re.findall(r"\['?([A-Za-z0-9_]+)'?\]", s)

    def print_diff_list(self, change_t, level=1):
        print('', end='\n')
        for value in change_t:
            print("  {}-".format(' '*(level*2)), end='')
            if isinstance(value, list):
                self.print_diff_list(value, level+1)
            elif isinstance(value, dict):
                self.print_diff_dict(value, level+1)
            else:
                print("  {}".format(value))

    def print_diff_dict(self, change_t, level=1):
        print('', end='\n')
        for key, value in change_t.items():
            print("  {}{}:".format(' '*(level*2), key), end='')
            if isinstance(value, list):
                self.print_diff_list(value, level+1)
            elif isinstance(value, dict):
                self.print_diff_dict(value, level+1)
            else:
                print("  {}".format(value))

    def print_diff_object(self, diff_obj, diff_obj_key):
        if diff_obj_key not in diff_obj.keys():
            return
        last_root_node_str = None
        for root_change in diff_obj[diff_obj_key]:
            node_str = '.'.join(self.getFromSquareBrackets(root_change.path()))
            for root_node_str in ['Parameters', 'Resources', 'Outputs']:
                if node_str.startswith(root_node_str+'.'):
                    node_str = node_str[len(root_node_str+'.'):]
                    if last_root_node_str != root_node_str:
                        print(root_node_str+":")
                    last_root_node_str = root_node_str
                    break
            if diff_obj_key.endswith('_removed'):
                change_t = root_change.t1
            elif diff_obj_key.endswith('_added'):
                change_t = root_change.t2
            elif diff_obj_key == 'values_changed':
                change_t = root_change.t1
            print("  {}:".format(node_str), end='')
            if diff_obj_key == 'values_changed':
                print("\n    old: {}".format(root_change.t1))
                print("    new: {}\n".format(root_change.t2))
            elif isinstance(change_t, list) == True:
                self.print_diff_list(change_t)
            elif isinstance(change_t, dict) == True:
                self.print_diff_dict(change_t)
            else:
                print("{}".format(change_t))
            print('')

    def init_template_store_paths(self):
        new_file_path = pathlib.Path(self.get_yaml_path())
        applied_file_path = pathlib.Path(self.get_yaml_path(applied=True))
        return [applied_file_path, new_file_path]

    def apply_template_changes(self):
        applied_file_path, new_file_path = self.init_template_store_paths()
        if new_file_path.exists():
            copyfile(new_file_path, applied_file_path)

    def warn_template_changes(self, deep_diff):
        """
        Warn the user about template changes that might have unexpected consequences.
        """
        # base method: override this in the child class with the specific warning
        # this method is responsible for printing an appropriate warning. This warning
        # should include a newline above and below this warning and be prefixed with "WARNING: "
        return None


    def validate_template_changes(self):
        if self.paco_ctx.disable_validation == True:
            return
        elif self.enabled == False:
            return
        elif self.change_protected == True:
            return
        applied_file_path, new_file_path = self.init_template_store_paths()
        if applied_file_path.exists() == False:
            return

        yaml = YAML(pure=True)
        yaml.allow_duplicate_keys = True
        #yaml.default_flow_sytle = False
        with open(applied_file_path, 'r') as stream:
            applied_file_dict= yaml.load(stream)
        with open(new_file_path, 'r') as stream:
            new_file_dict= yaml.load(stream)

        deep_diff = DeepDiff(
            applied_file_dict,
            new_file_dict,
            verbose_level=1,
            view='tree'
        )
        if len(deep_diff.keys()) == 0:
            return
        print("--------------------------------------------------------")
        print("Confirm template changes to CloudFormation Stack: " + self.stack.get_name())
        print()
        print("{}".format(self.stack.get_name()))
        if self.paco_ctx.verbose:
            print()
            print("model: {}".format(self.config_ref))
            print("file: {}".format(new_file_path))
            print("applied file: {}".format(applied_file_path))

        if 'values_changed' in deep_diff.keys():
            print("\nooo Changed")
            self.print_diff_object(deep_diff, 'values_changed')
            print("ooo")

        if  'dictionary_item_removed' in deep_diff.keys() or \
            'iterable_item_removed' in deep_diff.keys() or \
            'set_item_added' in deep_diff.keys():
            print("\n--- Removed")
            self.print_diff_object(deep_diff, 'dictionary_item_removed')
            self.print_diff_object(deep_diff, 'iterable_item_removed')
            self.print_diff_object(deep_diff, 'set_item_added')
            print("---")

        if  'dictionary_item_added' in deep_diff.keys() or \
            'iterable_item_added' in deep_diff.keys() or \
            'set_item_removed' in deep_diff.keys():
            print("\n+++ Added")
            self.print_diff_object(deep_diff, 'dictionary_item_added')
            self.print_diff_object(deep_diff, 'iterable_item_added')
            self.print_diff_object(deep_diff, 'set_item_removed')
            print("+++")

        print("\n--------------------------------------------------------")
        print("Stack: " + self.stack.get_name())
        print("")
        self.warn_template_changes(deep_diff)
        answer = self.paco_ctx.input_confirm_action("\nAre these changes acceptable?")
        if answer == False:
            print("Aborted run.")
            sys.exit(1)
        print('', end='\n')

    def set_aws_name(self, template_name, first_id=None, second_id=None, third_id=None):
        if isinstance(first_id, list):
            id_list = first_id
        else:
            id_list = [first_id, second_id, third_id]

        # Exceptions: ApiGatewayRestApi | Lambda
        if self.paco_ctx.legacy_flag('cftemplate_aws_name_2019_09_17') == True and \
            template_name not in ['ApiGatewayRestApi', 'Lambda', 'SNSTopics']:
            id_list.insert(0, template_name)
            self.aws_name = utils.big_join(
                str_list=id_list,
                separator_ch='-',
                none_value_ok=True)
        else:
            id_list.append(template_name)
            self.aws_name = utils.big_join(
                str_list=id_list,
                separator_ch='-',
                none_value_ok=True)
        self.aws_name.replace('_', '-')
