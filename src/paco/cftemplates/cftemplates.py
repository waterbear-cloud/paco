from paco import utils
from paco.core.exception import StackException, PacoErrorCode, PacoException
from paco.models import schemas
from paco.models.references import Reference
from paco.models.locations import get_parent_by_interface
from paco.stack import StackOutputParam, Stack
from paco.utils import md5sum, big_join
import paco.stack.interfaces
import re
import troposphere


single_quoted_cfn_regex = re.compile(r"(.*)'(!Ref\W+\S+)'(.*)")


def fix_yaml_tagged_string_quotes(body):
    """
    Remove single-quotes around CFN Tags from the generated CloudFormation YAML.

    Works around a bug in Troposphere .to_yaml(). This uses the cfn-flip library,
    which in turn uses PyYAML to generate the YAML from Troposphere. This is a known bug
    where a desired YAML such as:

        - !Ref SecretArnOne

    Is incorrectly wrapped in single-quotes:

        - '!Ref SecretArnOne'

    The fix requries cfn-flip using another YAML library that offers better control over the output:
    https://github.com/awslabs/aws-cfn-template-flip/issues/48
    """
    new_body = single_quoted_cfn_regex.sub(r'\1\2\3', body)
    return new_body

class StackTemplate():
    """A CloudFormation template with access to a Stack object and a Project object."""
    def __init__(
        self,
        stack,
        paco_ctx,
        config_ref=None,
        aws_name=None,
        enabled=None,
        environment_name=None,
        iam_capabilities=[],
    ):
        self.stack = stack
        self.update_only = False
        # determine if enabled
        # ToDo: some global resources do not have IDeployable settings
        if enabled == None:
            if schemas.IDeployable.providedBy(stack.resource):
                enabled = stack.resource.is_enabled()
            else:
                enabled = True
        self.enabled = enabled
        # propogate to the stack as it is needed when set_parameter is called
        stack.enabled = enabled
        self.paco_ctx = paco_ctx
        self.project = paco_ctx.project
        self.account_ctx = stack.account_ctx
        self.aws_region = stack.aws_region
        self.resource = stack.resource
        self.capabilities = iam_capabilities
        self._body = None
        self.aws_name = aws_name
        if config_ref == None:
            config_ref = stack.stack_ref
        self.config_ref = config_ref
        self.template = None
        self.environment_name = environment_name
        # propogate to stack where it's used in set_parameter
        self.stack.environment_name = environment_name
        self.change_protected = stack.change_protected

    @property
    def body(self):
        if self._body == None:
            # generate YAML from Troposphere and perform replacement on '!Ref SomeParam'
            self._body = fix_yaml_tagged_string_quotes(
                self.template.to_yaml()
            )
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

    @property
    def resource_group_name(self):
        """The Resource Group name or None. Only Application resources have a Resource Group name,
        e.g. BackupVault Resource does not.
        """
        resource_group = get_parent_by_interface(self.stack.resource, schemas.IResourceGroup)
        if resource_group != None:
            return resource_group.name
        return None

    @property
    def resource_name(self):
        return self.stack.resource.name

    @property
    def cfn_client(self):
        if hasattr(self, '_cfn_client') == False:
            self._cfn_client = self.account_ctx.get_aws_client('cloudformation', self.aws_region)
        return self._cfn_client

    def set_enabled(self, value):
        "Sets the Enabled status for the Stack"
        # ToDo: this is set on both stack and template - only needs to be on the stack though?
        self.enabled = value
        self.stack.enabled = value

    def set_parameter(
        self,
        param_key,
        param_value=None,
        use_previous_param_value=False,
        resolved_ssm_value="",
        ignore_changes=False
    ):
        "Set a Parameter for this StackTemplate's Stack"
        # convenience method - delegates to stack object
        self.stack.set_parameter(
            param_key,
            param_value=param_value,
            use_previous_param_value=use_previous_param_value,
            resolved_ssm_value=resolved_ssm_value,
            ignore_changes=ignore_changes
        )

    def init_template(self, description):
        "Initializes a Troposphere template"
        self.template = troposphere.Template(
            Description = description,
        )
        self.template.set_version()
        self.template.add_resource(
            troposphere.cloudformation.WaitConditionHandle(title="EmptyTemplatePlaceholder")
        )

    # There is a case in ECS where we need to manually set ValueFrom in the
    # ContainerDefinitions Secerts KeyValuePair list with a !Ref SomeParameterName
    # value in a dict that will be used in .from_dict(). When troposphere outputs
    # the resource to yaml, it will wrap the !Ref SomeParameterName in single
    # quotes which causes CloudFormation to complain. To workaround this we are
    # using !ManualTroposphereRef (to create uniquieness) and performing the
    # following replace.
    def fix_troposphere_manual_ref(self):
        search = "'!ManualTroposphereRef "
        replace = "!Ref '"
        self.body = self.body.replace(search, replace)

    def paco_sub(self):
        "Perform paco.sub expressions with the substitution string"
        while True:
            # Isolate string between quotes: paco.sub ''
            sub_idx = self.body.find('paco.sub')
            if sub_idx == -1:
                break
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
                        break
                rep_1_idx = dollar_idx
                rep_2_idx = self.body.find("}", rep_1_idx, end_str_idx)+1
                next_ref_idx = self.body.find("paco.ref ", rep_1_idx, rep_2_idx)
                if next_ref_idx != -1:
                    sub_ref_idx = next_ref_idx
                    sub_ref = self.body[sub_ref_idx:sub_ref_idx+(rep_2_idx-sub_ref_idx-1)]
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
                    # Replace the ${}
                    sub_var = self.body[rep_1_idx:rep_1_idx+(rep_2_idx-rep_1_idx)]
                    # if a Stack is returned, then look-up the referenced Stack Output and use that
                    if paco.stack.interfaces.IStack.providedBy(sub_value):
                        sub_value = sub_value.get_outputs_value(
                            sub_value.get_outputs_key_from_ref(
                                Reference(sub_ref)
                            )
                        )
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

    def set_template(self, template_body=None):
        """Sets the template to the body attribute"""
        if template_body == None:
            self.body = self.template.to_yaml()
        else:
            self.body = template_body

    def gen_cf_logical_name(self, name, sep=None):
        """
        !! DEPRECATED !! Use self.cfn_logical_id* methods
        Create a CloudFormation safe Logical name
        """
        cf_name = ""
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
        min_length=None,
        max_length=None,
        ignore_changes=False
    ):
        "Create a Troposphere Parameter and add it to the template"
        if default == '':
            default = "''"
        if value == None:
            value = default
        else:
            if type(value) == StackOutputParam:
                self.stack.set_parameter(value, ignore_changes=ignore_changes)
            else:
                self.stack.set_parameter(name, value, ignore_changes=ignore_changes)
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
        if not self.template:
            # if init_template has not been called, it's an old school format string template
            return """
  # {}: {}
  {}:
    Description: {}
    Type: {}{}
""".format(name, desc_value, name, description, param_type, other_yaml)

        # create troposphere Parmeter and add it to the troposphere template
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
        return self.template.add_parameter(param)

    def create_cfn_ref_list_param(
        self,
        param_type,
        name,
        description,
        value,
        ref_attribute=None,
        default=None,
        noecho=False,
    ):
        "Create a CloudFormation Parameter from a list of refs"
        stack_output_param = StackOutputParam(name, param_template=self)
        for item_ref in value:
            if ref_attribute != None:
                item_ref += '.' + ref_attribute
            stack = self.paco_ctx.get_ref(item_ref)
            if isinstance(stack, Stack) == False:
                raise PacoException(PacoErrorCode.Unknown, message="Reference must resolve to a stack")
            stack_output_key = self.stack.get_stack_outputs_key_from_ref(Reference(item_ref))
            stack_output_param.add_stack_output(stack, stack_output_key)

        return self.create_cfn_parameter(
            param_type,
            name,
            description,
            stack_output_param,
            default,
            noecho,
        )

    def create_output(
        self,
        title=None,
        description=None,
        value=None,
        ref=None,
    ):
        "Create a Troposphere output, add it to the template and register the Stack Output(s)"
        if description != None:
            troposphere.Output(
                title=title,
                template=self.template,
                Value=value,
                Description=description
            )
        else:
            troposphere.Output(
                title=title,
                template=self.template,
                Value=value,
            )
        if type(ref) == list:
            for ref_item in ref:
                self.stack.register_stack_output_config(ref_item, title)
        elif type(ref) == str:
            self.stack.register_stack_output_config(ref, title)

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

    def set_aws_name(self, template_name, first_id=None, second_id=None, third_id=None, fourth_id=None):
        if isinstance(first_id, list):
            id_list = first_id
        else:
            id_list = [first_id, second_id, third_id, fourth_id]

        # Exceptions: ApiGatewayRestApi | Lambda
        if self.paco_ctx.legacy_flag('cftemplate_aws_name_2019_09_17') == True and \
            template_name not in ['ApiGatewayRestApi', 'Lambda', 'SNSTopics']:
            id_list.insert(0, template_name)
            self.aws_name = utils.big_join(
                str_list=id_list,
                separator_ch='-',
                none_value_ok=True
            )
        else:
            id_list.append(template_name)
            self.aws_name = utils.big_join(
                str_list=id_list,
                separator_ch='-',
                none_value_ok=True
            )
        self.aws_name.replace('_', '-')
