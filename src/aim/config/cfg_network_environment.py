from aim.config.config import Config
import os
import copy
from pprint import pprint
import aim.core.log
from aim.core.exception import AimException, AimErrorCode


logger = aim.core.log.get_aim_logger()


class NetEnvConfig(Config):

    def __init__(self, aim_ctx, name):
        # config/NetworkEnvironments/<name>/
        config_folder = os.path.join(
            aim_ctx.config_folder, "NetworkEnvironments")

        super().__init__(aim_ctx, config_folder, name)
        self.name = name
        self.subenv_config = {}
        self.netenv = self.project['ne'][name]
        logger.debug("NetEnvConfig Loaded: %s, Yaml: %s" %
                     (name, self.yaml_path))
        self.load()

        for subenv_id in self.subenv_ids():
            self.subenv_config[subenv_id] = {}
            default_config = self.config_override(self.config_dict, self.config_dict['environments'][subenv_id]['default'])
            for region in self.config_dict['environments'][subenv_id].keys():
                if region in ('default','title'):
                    continue
                subenv_config_dict = self.merged_config_for_subenv_copy(subenv_id, region, default_config)
                self.subenv_config[subenv_id][region] = subenv_config_dict

    @property
    def title(self):
        return self.config_dict['network']['title']

    def subenv_regions(self, subenv_id):
        return self.netenv[subenv_id].env_regions

    def default_subenv_dict(self, subenv_id, region):
        return self.config_dict['environments'][subenv_id][region]

    def subenv_config_dict(self, subenv_id, region):
        return self.merged_subenv_dict(subenv_id, region)

    def merged_subenv_dict(self, subenv_id, region):
        return self.subenv_config[subenv_id][region]

    def subenv_ids(self):
        return sorted(self.config_dict['environments'].keys())

    def vpc_dict(self, subenv_id):
        return self.subenv_config[subenv_id]['network']['vpc']

    def segment_ids(self, subenv_id):
        return self.subenv_config[subenv_id]['network']['vpc']['segments']

    def segment_dict(self, subenv_id, segment_id):
        return self.subenv_config[subenv_id]['network']['vpc']['segments'][segment_id]

    def security_groups_dict(self, subenv_id):
        if 'security_groups' in self.subenv_config[subenv_id]['network']['vpc'].keys():
            return self.subenv_config[subenv_id]['network']['vpc']['security_groups']
        else:
            return []

    # AWS
    def aws_account(self, subenv_id):
        #return self.subenv_config[subenv_id]['network']['aws_account']
        # load from aim.model
        # XXX reference loading not yet implemented, need to be able to do ['network'].aws_account directly
        return self.project['ne'][self.name][subenv_id]['default']['network']._ref_aws_account

#    def gen_new_netenv_ref(self, netenv_ref_raw, sub_ref_len, subenv_id):
#        return new_ref

    def insert_subenv_ref_aim_sub(self, str_value, subenv_id, region):
        # Isolate string between quotes: aim.sub ''
        sub_idx = str_value.find('aim.sub')
        if sub_idx == -1:
            return str_value
        end_idx = str_value.find('\n', sub_idx)
        if end_idx == -1:
            end_idx = len(str_value)
        str_idx = str_value.find("'", sub_idx, end_idx)
        if str_idx == -1:
            raise StackException(AimErrorCode.Unknown)
        str_idx += 1
        end_str_idx = str_value.find("'", str_idx, end_idx)
        if end_str_idx == -1:
            raise StackException(AimErrorCode.Unknown)
        #print("Aim SUB: %s" % (str_value[str_idx:str_idx+(end_str_idx-str_idx)]))
        # Isolate any ${} replacements
        first_pass = True
        while True:
            dollar_idx = str_value.find("${", str_idx, end_str_idx)
            if dollar_idx == -1:
                if first_pass == True:
                    raise StackException(AimErrorCode.Unknown)
                else:
                    break
            rep_1_idx = dollar_idx
            rep_2_idx = str_value.find("}", rep_1_idx, end_str_idx)+1
            netenv_ref_idx = str_value.find(
                "netenv.ref ", rep_1_idx, rep_2_idx)
            if netenv_ref_idx != -1:
                #sub_ref_idx = netenv_ref_idx + len("netenv.ref ")
                sub_ref_idx = netenv_ref_idx
                sub_ref_end_idx = sub_ref_idx+(rep_2_idx-sub_ref_idx-1)
                sub_ref = str_value[sub_ref_idx:sub_ref_end_idx]
                #print("Sub ref: " + sub_ref)

                new_ref = self.insert_subenv_ref_str(sub_ref, subenv_id, region)
                #print("Sub Value: %s" % (sub_value))
                # if sub_value.startswith("service.ref"):
                #    sub_value = self.aim_ctx.get_service_ref_value(sub_value)
                sub_var = str_value[sub_ref_idx:sub_ref_end_idx]
                #print("Sub var: %s" % (sub_var))
                str_value = str_value.replace(sub_var, new_ref)
            else:
                break
            first_pass = False
        # print(str_value)
        return str_value

    def insert_subenv_ref_str(self, str_value, subenv_id, region):
        netenv_ref_idx = str_value.find("netenv.ref ")
        if netenv_ref_idx == -1:
            return str_value

        if str_value.startswith("aim.sub "):
            return self.insert_subenv_ref_aim_sub(str_value, subenv_id, region)

        netenv_ref_raw = str_value
        sub_ref_len = len(netenv_ref_raw)

        netenv_ref = netenv_ref_raw[0:sub_ref_len]
        ref_dict = self.aim_ctx.parse_ref(netenv_ref)
        if ref_dict['netenv_component'] == 'subenv':
            return str_value

        ref_dict['ref_parts'][0] = '.'.join([ref_dict['netenv_id'],
                                             'subenv',
                                             subenv_id,
                                             region])

        new_ref_parts = '.'.join(ref_dict['ref_parts'])
        new_ref = ' '.join([ref_dict['type'], new_ref_parts])

        #print("Modified ref: " + str_value + " to " + new_ref)

        return new_ref

    def insert_subenv_ref_list(self, config_list, subenv_id, region):
        for list_idx in range(0, len(config_list)):
            if type(config_list[list_idx]) == list:
                self.insert_subenv_ref_list(config_list[list_idx], subenv_id, region)
            elif type(config_list[list_idx]) == dict:
                self.insert_subenv_ref_dict(config_list[list_idx], subenv_id, region)
            elif type(config_list[list_idx]) == str:
                if config_list[list_idx].find('netenv.ref ') != -1:
                    config_list[list_idx] = self.insert_subenv_ref_str(
                                              config_list[list_idx],
                                              subenv_id,
                                              region
                                            )

    # Modify default netenv.ref referecnes to include the Sub Environment ID
    def insert_subenv_ref_dict(self, config_dict, subenv_id, region):
        for key in config_dict.keys():
            #            print("Key: ", key)
            if type(config_dict[key]) == dict:
                self.insert_subenv_ref_dict(config_dict[key], subenv_id, region)
            elif type(config_dict[key]) == list:
                self.insert_subenv_ref_list(config_dict[key], subenv_id, region)
            elif type(config_dict[key]) == str:
                if config_dict[key].find('netenv.ref ') != -1:
                    config_dict[key] = self.insert_subenv_ref_str(
                                        config_dict[key],
                                        subenv_id,
                                        region)

    def merged_config_for_subenv_copy(self, subenv_id, region, default_config_dict):
        new_subenv_config = copy.deepcopy(self.default_subenv_dict(subenv_id, region))
        for config_key in default_config_dict.keys():
            if config_key == 'environments':
                continue
            if config_key == 'enabled':
                continue
            #print("merged_config_for_subenv_copy: Config key: " + config_key)
            default_key_config = copy.deepcopy(default_config_dict[config_key])
            subenv_key_config = {}
            if config_key in self.default_subenv_dict(subenv_id, region).keys():
                subenv_key_config = self.default_subenv_dict(subenv_id, region)[config_key]
            merged_config = self.config_override(default_key_config, subenv_key_config)
            #print("merged_config_for_subenv_copy: Modifying " + config_key)
            self.insert_subenv_ref_dict(merged_config, subenv_id, region)
            new_subenv_config[config_key] = merged_config

        #print("merged_config_for_subenv_copy: Done")
        # print(new_subenv_config)
        return new_subenv_config

    def dict_path_value(self, subenv_id, region, value_path):
        subenv_dict = self.merged_subenv_dict(subenv_id, region)
        dict_ptr = subenv_dict
        # print("dict_path_value:")
        for key in value_path:
            # print(key)
            # print(dict_ptr[key])
            dict_ptr = dict_ptr[key]

        # print("dict_ptr: " + dict_ptr)
        return dict_ptr
