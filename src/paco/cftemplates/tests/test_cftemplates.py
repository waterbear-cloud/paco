from paco.cftemplates import cftemplates
from paco.cftemplates.tests import BaseTestStack
from paco.core.yaml import YAML

yaml=YAML(typ='safe')

class TestStackTemplate(BaseTestStack):

    def test_fix_yaml_tagged_string_quotes(self):
        # replace single '!Ref Thing'
        body = """SomeResource:
  - '!Ref MyGoodRef'

MoreTemplate:
"""
        expected = """SomeResource:
  - !Ref MyGoodRef

MoreTemplate:
"""
        new_body = cftemplates.fix_yaml_tagged_string_quotes(body)
        assert new_body == expected

        # replace multiple '!Ref Thing's
        body = """SomeResource:
  - '!Ref MyGoodRef'
  - '!Ref MoreRef'

MoreTemplate:
  Foobs: '!Ref Foobs'
"""
        expected = """SomeResource:
  - !Ref MyGoodRef
  - !Ref MoreRef

MoreTemplate:
  Foobs: !Ref Foobs
"""
        new_body = cftemplates.fix_yaml_tagged_string_quotes(body)
        assert new_body == expected

        # Do not replace strings that start with !Ref
        body = """SomeResource:
  Title: '!Ref is a CFN Tag'
"""
        expected = """SomeResource:
  Title: '!Ref is a CFN Tag'
"""
        new_body = cftemplates.fix_yaml_tagged_string_quotes(body)
        assert new_body == expected

        # Do not replace multi-line strings that start with !Ref
        body = """SomeResource:
  Title: '!Ref isA
CFNTag'
"""
        expected = """SomeResource:
  Title: '!Ref isA
CFNTag'
"""
        new_body = cftemplates.fix_yaml_tagged_string_quotes(body)
        assert new_body == expected
