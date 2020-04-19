"""
Commands and configuration for EC2 Launch Manager
"""

user_data_script = {
	'update_system': {
		'amazon': [],
		'centos': [],
		'ubuntu': [],
	},
	'essential_packages': {
		'amazon': [],
		'centos': [],
		'ubuntu': [
		],
	},
	'update_packages': {
		'amazon': 'yum update -y',
		'centos': 'yum update -y',
		'ubuntu': 'apt-get update -y && apt-get upgrade -y'
	},
	'install_aws_cli': {
		'amazon': '', # AWS is installed by default on Amazon linux
		'ubuntu': """apt-get update
apt-get -y install python-pip
pip install awscli
""",
		'centos': 'ec2lm_pip install awscli'
	},
	'install_wget': {
		'amazon': 'yum install wget -y',
		'centos': 'yum install wget -y',
		'ubuntu': 'apt-get install wget -y'
	},
	'install_efs_utils': {
		'amazon': 'yum install -y amazon-efs-utils cachefilesd',
		'centos': 'yum install -y amazon-efs-utils cachefilesd',
		'ubuntu': 'apt-get install cachefilesd -y'
	},
	'install_cfn_init': {
		'amazon': '',
		'ubuntu': """
mkdir -p /opt/paco/bin
apt-get install -y python-setuptools
wget https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
easy_install --script-dir /opt/paco/bin aws-cfn-bootstrap-latest.tar.gz
""",
		'centos': """
yum install -y pystache python-daemon
pip install aws-cfn-bootstrap
rpm -Uvh https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.amzn1.noarch.rpm
"""
	},
	'enable_efs_utils': {
		'amazon': """
/sbin/service cachefilesd start
systemctl enable cachefilesd
""",
		'ubuntu': """
sed -i 's/#RUN=yes/RUN=yes/g' /etc/default/cachefilesd
/etc/init.d/cachefilesd start
""",
		'centos': """
/sbin/service cachefilesd start
systemctl enable cachefilesd
""" },
	'mount_efs': {
		'amazon': 'mount -a -t efs',
		'ubuntu': 'mount -a -t nfs',
		'centos': 'mount -a -t nfs'
	}

}

ssm_regions = {
    'us-east-2':  None,
    'us-east-1': None,
    'us-west-1': None,
    'us-west-2': None,
    'ap-east-1': None,
    'ap-south-1': None,
    'ap-northeast-2': None,
    'ap-southeast-1': None,
    'ap-southeast-2': None,
    'ap-northeast-1': None,
    'ca-central-1': None,
    'cn-north-1': None,
    'cn-northwest-1': None,
    'eu-central-1': None,
    'eu-west-1': None,
    'eu-west-2': None,
    'eu-west-3': None,
    'eu-north-1': None,
    'me-south-1': None,
    'sa-east-1': None,
    'us-gov-east-1': None,
    'us-gov-west-1': None,
}

ssm_agent = {
    "debian": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "debian_8": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "debian_9": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "ubuntu_14_386": {
        "path": "/debian_386",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "ubuntu_16_386": {
        "path": "/debian_386",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "ubuntu_16": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "ubuntu": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "centos_7": {
        "path": "/linux_amd64",
        "object": "amazon-ssm-agent.rpm",
        "install": "yum install -y"
    },
    "centos_7_386": {
        "path": "/linux_386",
        "object": "amazon-ssm-agent.rpm",
        "install": "yum install -y"
    },
    "suse": {
        "path": "/linux_amd64",
        "object": "amazon-ssm-agent.rpm",
        "install": "yum install -y"
    },
    "suse_12": {
        "path": "/linux_amd64",
        "object": "amazon-ssm-agent.rpm",
        "install": "yum install -y"
    },
}

# Create the CloudWatch agent launch scripts and configuration
# ToDo: test/finish rpm installed command
cloudwatch_agent = {
	"amazon": {
		"path": "/amazon_linux/amd64/latest",
		"object": "amazon-cloudwatch-agent.rpm",
		"install": "rpm -U",
        "installed": "rpm -q amazon-cloudwatch-agent",
        "uninstall": "rpm -e" },
	"centos": {
		"path": "/centos/amd64/latest",
		"object": "amazon-cloudwatch-agent.rpm",
		"install": "rpm -U",
        "uninstall": "rpm -e" },
	"suse": {
		"path": "/suse/amd64/latest",
		"object": "amazon-cloudwatch-agent.rpm",
		"install": "rpm -U",
        "installed": "rpm -q amazon-cloudwatch-agent",
        "uninstall": "rpm -e",
    },
	"debian": {
		"path": "/debian/amd64/latest",
		"object": "amazon-cloudwatch-agent.deb" ,
		"install": "dpkg -i -E",
        "installed": "dpkg --status amazon-cloudwatch-agent",
        "uninstall": "dpkg -P amazon-cloudwatch-agent",
    },
	"ubuntu": {
		"path": "/ubuntu/amd64/latest",
		"object": "amazon-cloudwatch-agent.deb",
		"install": "dpkg -i -E",
        "installed": "dpkg --status amazon-cloudwatch-agent",
        "uninstall": "dpkg -P amazon-cloudwatch-agent",
    },
	"microsoft": {
		"path": "/windows/amd64/latest",
		"object": "amazon-cloudwatch-agent.msi",
		"install": "msiexec /i",
        "installed": "",
        "uninstall": "",
    },
	"redhat": {
		"path": "/redhat/arm64/latest",
		"object": "amazon-cloudwatch-agent.rpm",
		"install": "rpm -U",
        "uninstall": "rpm -e" },
}