import re
import sys
import aim.models.vocabulary

NAME_REGEX = r'^[_a-zA-Z][\-_a-zA-Z0-9]+$'

project_name = '{{ cookiecutter.project_name }}'

if not re.match(NAME_REGEX, project_name):
    print('ERROR: %s is not a valid AIM Project name!' % project_name)
    print('Name must only contain characters, digits, hyphens and underscores.')
    sys.exit()

aws_region = '{{ cookiecutter.aws_default_region }}'

if aws_region not in aim.models.vocabulary.aws_regions:
    print('ERROR: %s is not a valid AWS Region name!' % aws_region)
    print('AWS Region name must be one of:')
    for name in aim.models.vocabulary.aws_regions.keys():
        print('  ' + name)
