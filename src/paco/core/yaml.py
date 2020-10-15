import ruamel.yaml
from ruamel.yaml.compat import StringIO

class Ref:
    yaml_tag = u'!Ref:'

    def __init__(self, value, style=None):
        self.value = value
        self.style = style

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(cls.yaml_tag,
                                            u'{.value}'.format(node), node.style)

    @classmethod
    def from_yaml(cls, constructor, node):
        return cls(node.value, node.style)

    def __iadd__(self, v):
        self.value += str(v)
        return self

class Sub:
    yaml_tag = u'!Sub'
    def __init__(self, value, style=None):
        self.value = value
        self.style = style

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(cls.yaml_tag,
                                            u'{.value}'.format(node), node.style)

    @classmethod
    def from_yaml(cls, constructor, node):
        return cls(node.value, node.style)


class YAML(ruamel.yaml.YAML):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ruamel.yaml.add_constructor('!Ref', self.tag_constructor, constructor=ruamel.yaml.SafeConstructor)
        ruamel.yaml.add_constructor('!Sub', self.tag_constructor, constructor=ruamel.yaml.SafeConstructor)

    def tag_constructor(self, node, arg2):
        return arg2.tag+ ' '+arg2.value

    def dump(self, data, stream=None, **kw):
        dumps = False
        if stream is None:
            dumps = True
            stream = StringIO()
        ruamel.yaml.YAML.dump(self, data, stream, **kw)
        if dumps:
            return stream.getvalue()

def read_yaml_file(path):
    yaml = YAML(typ="safe", pure=True)
    yaml.default_flow_sytle = False
    with open(path, 'r') as stream:
        data = yaml.load(stream)
    return data
