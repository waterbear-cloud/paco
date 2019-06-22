import aim.core.log
import copy
import json
import os
from aim.core.yaml import YAML

yaml=YAML(typ="safe", pure=True)
yaml.default_flow_sytle = False

logger = aim.core.log.get_aim_logger()

class Config():

    def __init__(self, aim_ctx, yaml_folder, name):
        self.aim_ctx = aim_ctx
        self.project = aim_ctx.project

        # check for .yml otherwise load a .yaml extension
        yml_path = os.path.join(yaml_folder, name + ".yml")
        yaml_path = os.path.join(yaml_folder, name + ".yaml")

        if os.path.isfile(yml_path):
            self.yaml_path = yml_path
        elif os.path.isfile(yaml_path):
            self.yaml_path = yaml_path
        else:
            raise FileNotFoundError(
                'Could not find YAML file: in path {}/{}.*'.format(yaml_folder, name)
            )

        self.config_dict = None
        self.name = name

    def load(self):
        logger.debug("Loading YAML: %s" % (self.yaml_path))
        stream = open(self.yaml_path, 'r')
        # XXX: Security: Verify safety, yaml.load is like pickle!
        self.config_dict = yaml.load(stream)
        stream.close()

    def load_json(self, json_data):
        self.config_dict = json.loads(json_data)

    def save(self):
        stream = open(self.yaml_path, 'w')
        yaml.dump(self.config_dict, stream)
        stream.close()

    def set_config_dict(self, config_dict):
        self.config_dict = config_dict

