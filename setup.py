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
    name='aim',
    version=version,
    author='Waterbear Cloud',
    author_email='hello@waterbear.cloud',
    description='AIM: Application Infrastructure Manager',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/waterbear-cloud/aim',
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    ],
    keywords=['AWS','Waterbear','Cloud','Infrastructure-as-Code'],
    install_requires=[
        'aim.models',
        'boto3',
        'click',
        'cookiecutter',
        'Setuptools',
        'tldextract',
        'pexpect',
        'troposphere',
        'awacs',
        'deepdiff'
    ],
    packages=[
        'aim.adapters',
        'aim.api',
        'aim.aws_api',
        'aim.cftemplates',
        'aim.commands',
        'aim.config',
        'aim.controllers',
        'aim.core',
        'aim.stack_group',
        'aim.tests',
        'aim.doc',
        'aim.application',
        'aim.utils'
    ],
    include_package_data=True,
    zip_safe=False,
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'aim = aim.commands.cli:cli',
            'aim_doc = aim.doc.docschema:aim_schema_generate',
        ]
    },
    extras_require={
        'docs': docs_extras,
    },
)
