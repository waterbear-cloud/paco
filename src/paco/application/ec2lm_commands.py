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
    'install_package': {
        'amazon': 'yum install -y',
        'centos': 'yum install -y',
		'ubuntu': 'apt-get install -y'
    },
	'update_packages': {
		'amazon': 'yum update -y',
		'centos': 'yum update -y',
		'ubuntu': """apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::=--force-confnew -o Dpkg::Options::=--force-confdef dist-upgrade -y --allow-downgrades --allow-remove-essential --allow-change-held-packages
"""
	},
	'install_aws_cli': {
		'amazon': '', # AWS is installed by default on Amazon linux
        'amazon_ecs': """yum -y install unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install --bin-dir /usr/bin
ln -s /usr/bin/aws /usr/local/bin/aws
""",
		'ubuntu': """apt-get update
apt-get -y install python-pip
pip install awscli
""",
		'ubuntu_18': """apt-get update
apt-get -y install python-pip
pip install awscli
""",
		'ubuntu_18_cis': """apt-get update
apt-get -y install python-pip
pip install awscli
chmod a+x /usr/local/bin/aws
""",
		'ubuntu_20': """apt-get update
apt-get -y install python3-pip
apt install awscli -y
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
		'ubuntu': """
    dpkg -l amazon-efs-utils 2>/dev/null 2>&1
    if [ $? -ne 0 ] ; then
        echo "EFS: amazon-efs-utils: Installing package"
        apt-get install cachefilesd git binutils make -y
        LB_DIR=$(pwd)
        cd /tmp
        git clone https://github.com/aws/efs-utils
        cd efs-utils/
        sh ./build-deb.sh
        apt-get -y install ./build/amazon-efs-utils*deb
        cd ${LB_DIR}
    else
        echo "EFS: amazon-efs-utils package is already installed."
    fi
"""
	},
	'install_cfn_init': {
		'amazon': '',
		'ubuntu': """
mkdir -p {cfn_base_path}/bin
apt-get install -y python-setuptools
wget https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
easy_install --script-dir {cfn_base_path}/bin aws-cfn-bootstrap-latest.tar.gz
""",
		'ubuntu_20': """
mkdir -p {cfn_base_path}/bin
wget https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz
tar -xzvf aws-cfn-bootstrap-py3-latest.tar.gz
cd aws-cfn-bootstrap-2.0/
python3 setup.py install --install-scripts {cfn_base_path}/bin
cp ./init/ubuntu/cfn-hup /etc/init.d/cfn-hup
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
		'ubuntu': 'mount -a -t efs',
		'centos': 'mount -a -t nfs'
	}

}

# ToDo: add debian and centos/RHEL and test SuSE
default_user = {
    "ubuntu": "/home/ubuntu",
    "suse": "/root",
    "amazon": "/home/ec2-user",
    "centos": "/home/centos"
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
    "ubuntu_20": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent",
        "install": "snap install --classic"
    },
    "ubuntu_18": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent",
        "install": "snap install --classic"
    },
    "ubuntu_18_cis": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent",
        "install": "snap install --classic"
    },
    "ubuntu": {
        "path": "/debian_amd64",
        "object": "amazon-ssm-agent.deb",
        "install": "dpkg -i"
    },
    "centos": {
        "path": "/linux_amd64",
        "object": "amazon-ssm-agent.rpm",
        "install": "yum install -y"
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

# CloudWatch agent path
cloudwatch_agent = {
	"amazon": {
		"path": "/amazon_linux/amd64/latest",
    },
	"redhat": {
		"path": "/redhat/arm64/latest",
    },
	"centos": {
		"path": "/centos/amd64/latest",
    },
	"suse": {
		"path": "/suse/amd64/latest",
    },
	"debian": {
		"path": "/debian/amd64/latest",
    },
	"ubuntu": {
		"path": "/ubuntu/amd64/latest",
    },
	"microsoft": {
		"path": "/windows/amd64/latest",
    },
}