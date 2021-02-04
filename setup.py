from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()
    long_description += '\n\n'
with open('CHANGELOG.md') as f:
    long_description += f.read()

with open('version.txt') as f:
    version = f.read()

docs_extras = [
    'Sphinx >= 1.3.5',
    'sphinx_rtd_theme',
]

setup(
    name='paco-cloud',
    version=version,
    author='Waterbear Cloud',
    author_email='hello@waterbear.cloud',
    description='Paco: Prescribed automation for cloud orchestration',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/waterbear-cloud/paco',
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    ],
    keywords=['AWS','Waterbear','Cloud','Infrastructure as Code', 'CloudFormation'],
    install_requires=[
        'paco.models >= 7.7.6',
        'boto3 >= 1.16.48',
        'click',
        'cookiecutter',
        'Setuptools',
        'tldextract',
        'pexpect',
        'troposphere >= 2.6.3',
        'awacs',
        'deepdiff >= 4.3.2',
        'gitpython',
        'parliament',
        'Chameleon',
        "importlib_resources ; python_version<'3.7'",
    ],
    packages=[
        'paco.adapters',
        'paco.aws_api',
        'paco.cftemplates',
        'paco.commands',
        'paco.config',
        'paco.controllers',
        'paco.core',
        'paco.stack',
        'paco.stack_grps',
        'paco.tests',
        'paco.doc',
        'paco.application',
        'paco.utils',
        'paco.cookiecutters',
        'paco.extend',
    ],
    include_package_data=True,
    zip_safe=False,
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'paco = paco.commands.cli:cli',
            'paco_doc = paco.doc.docschema:paco_schema_generate',
        ]
    },
    extras_require={
        'docs': docs_extras,
    },
)
