.. _quickstart:

Quickstart Lab 101
==================

This quickstart will walk you through creating an AIM project. An AIM project is a directory
of YAML files that semantically describes an Infrastructure as code (IaC) project. It consists of
data for concepts such as networks, applications and environments.

This Quickstart 101 will walk you through creating an AIM project that hosts a simple
web application. You will copy a starting AIM project template, and provision the resources
it defines to an AWS account. This will give you simple but working application.
Later Quickstarts will demonstrate how to add a bastion, monitoring,
alerting and a CI/CD.

The architecture of the starting template in this quickstart will be create a simple network divided into
two subnets: one public and the other private. A load balancer will be hosted in the public subnet, and
will be configured to send requests to an AutoScalingGroup of web server(s) in the private subnet. The
application will have separate ``development`` and ``production`` environments, with a single t2.nano
in the development environment and a minimum of two t2.medium's in the production environment. The starting
configuration will have the production environment disabled, so that you will learn
how to provision each environment separately.

    .. image:: ./images/simple-dev-env.png

    .. image:: ./images/simple-prod-env.png

Install AIM
-----------

The AIM application is installable as a Python package. This will give you the ``aim`` command on
your CLI. The AIM CLI will read AIM Projects and provision AWS Resources from it.

You can install AIM with pip:

``pip install aim``

For more details, see the Installation_ page. After you have installed
AIM you should have ``aim`` available on your comand-line.
Try running ``aim --help`` to confirm that's it's properly installed.

.. _Installation: ./install.html

Create an AIM Administration User
---------------------------------

Maybe create an AWS Account?

Install a CloudFormation template.

Create access keys.

Create an AIM Project
---------------------

An AIM Project is a directory of specially named sub-directories
containing YAML files each requiring speccific formats.
These configuration sub-directories and files are documented
on the `AIM Configuration`_ page.

.. _`AIM Configuration`: ./aim-config.html

.. Attention:: Names are used extensively in AIM projects. Every object has a name.
    All Accounts, NetworkEnvironments, Applications, Environments and more will be named.
    These AIM names are concatened together to create unique AWS Resource Names.

    Some AWS Resource Names have character name limits, so you should
    try to always keep your names as short as possible. This will also make it
    easier to see what workload each resource is supporting in the AWS Console.
    About no more than 10 characters is a rule of thumb.

    If your names are too long for a resource, your CloudFormation stack will fail to create.
    If you  have already create resources, you can't rename them without
    destroying them, changing the name, and creating new resources.
    As it's not easy to rename resources after they are provisioned,
    think carefully as after you launch prod, you will be stuck
    with them for a long time ...

    .. image:: ./images/aim-name-parts.png

The ``aim init`` command will create a skeleton directory structure
to help you get started quickly.

.. code-block:: text

    $ aim init

    AIM Project initialization
    --------------------------

    About to create a new AIM Project directory at /Users/kteague/water/temparoo

    Select starting_template:
    1 - empty
    2 - simple-web-app
    Choose from 1, 2 (1, 2) [1]: 2

You will be asked questions about your project. First, choose ``2`` to use the
``simple-web-app`` template. This will give you basic network, with a simple
application that is deployed into two environments.

You will be asked for a ``project_title`` and ``project_name``. The title is a
human-readable string, so you can use space and other characters. The name will
be used not only as the directory name of your project, but will also be a key
which is used in the name of AWS resources. The name should be short, only
contain alphanumeric, underscore or hyphen characters.

.. code-block:: text

    project_title [My AIM Project]: First Project
    project_name [first_project]: first_project

Next you will be asked for network and application titles and names. In this simple
walkthrough, you will create one network and one application. In more complex
AIM uses, you can create a single network and deploy mulitple applications into it.

.. code-block:: text

    network_environment_title [My AIM NetworkEnvironment]: Basic Network
    network_environment_name [basic_network]: basic_network
    application_title [My AIM Application]: Apache Web Server
    application_name [apache_web_server]: apache_web_server


You will be asked for a default AWS Region name, if you don't know
the AWS Region names, you can use ``us-west-2``:

.. code-block:: text

    aws_default_region [Administrator Default AWS Region]: us-west-2

Finally, you will supply the AWS Account and Administrator credentials.
You can leave this blank if you don't have them handy, and edit the file at
``<my-aim-project>/Accounts/.credentials`` to add them later.

.. code-block:: text

    master_account_id [Master AWS Account Id]: 1234567890
    master_admin_iam_username [Master Admin IAM Username]: Administrator
    aws_access_key_id [Administrator AWS Access Key ID]: ********
    aws_secret_access_key [Administrator AWS Secret Access Key]: ********

At this point you should have a working AIM Project. You can run the
``aim describe`` command to get a summary of your project. This will
also ensure that your files are in the correct format.

.. code-block:: text

    $ aim --home ./first_project/ describe
    Project: first_project - First Project
    Location: /Users/kteague/water/temparoo/first_project

    Accounts
    - .credentials -

    Network Environments
    - basic_network - Basic Network


Create an EC2 keypair
---------------------

You will need to generate an EC2 SSH keypair and an SSH PEM file. This
keypair will be used when you initiallize an AIM project with
the starting template.

Run ``aim init keypair <keypair-name>`` to generate a keypair.

.. code-block:: text

    $ aim init keypair <keypair-name>


Review the AIM project configuration
------------------------------------

Your format of your AIM project directory is documented
on the `AIM Configuration`_ page. If you look in this directory,
you will see a file at ``./NetworkEnvironments/mynet.yaml``.

This YAML file contains all of your main configuration. It will
describe your network, applications and environments. The start of
this file will describe your network and looks like this:

.. code-block:: yaml

    network:

        title: "My AIM Network"
        availability_zones: 2
        enabled: true
        region: eu-central-1
        vpc:
            enable_dns_hostnames: true
            enable_dns_support: true
            enable_internet_gateway: true
            nat_gateway:
                myapp:
                    enabled: true
                    availability_zone: 1
                    segment: public
                    default_route_segments:
                    - webserver
            vpn_gateway:
            myapp:
                enabled: false
            private_hosted_zone:
            enabled: false
            name: example.internal
            security_groups:
                myapp:
                    alb:
                        egress:
                            - cidr_ip: 0.0.0.0/0
                            name: ANY
                            protocol: "-1"
                        ingress:
                            - cidr_ip: 70.68.173.245/32
                            from_port: 443
                            name: HTTPS
                            protocol: tcp
                            to_port: 443
                            - cidr_ip: 70.68.173.245/32
                            from_port: 80
                            name: HTTP
                            protocol: tcp
                            to_port: 80
                    webserver:
                        egress:
                            - cidr_ip: 0.0.0.0/0
                            name: ANY
                            protocol: "-1"
                        ingress:
                            - from_port: 80
                            name: HTTP
                            protocol: tcp
                            source_security_group_id: netenv.ref mynet.network.vpc.security_groups.myapp.alb.id
                            to_port: 80
            segments:
                public:
                    enabled: true
                webserver:
                    enabled: true

This tree of configuration will be the base template for configuring networks. The above network
will never be directly provisioned in AWS, but will be created by environments to contain
applications.

The next section will contain applications, and these applications are also base templates like the network
section. There is only one application in this quickstart and it is named ``myapp``:

.. code-block:: yaml

    applications:

        myapp:
            title: My AIM Application
            enabled: true
            managed_updates: true
            groups:
            site:
                type: Application
                order: 1
                resources:
                alb:
                    type: LBApplication
                    enabled: true
                    order: 1
                    target_groups:
                        myapp:
                            health_check_interval: 30
                            health_check_timeout: 10
                            healthy_threshold: 2
                            unhealthy_threshold: 2
                            port: 80
                            protocol: HTTP
                            health_check_http_code: 200
                            health_check_path: /
                            connection_drain_timeout: 300
                    listeners:
                        - port: 80
                        protocol: HTTP
                        target_group: myapp
                    scheme: internet-facing
                    security_groups:
                        - netenv.ref mynet.network.vpc.security_groups.myapp.alb.id
                    segment: public
                webserver:
                    type: ASG
                    order: 2
                    enabled: true
                    associate_public_ip_address: false
                    cooldown_secs: 300
                    ebs_optimized: false
                    health_check_grace_period_secs: 300
                    health_check_type: ELB
                    instance_iam_role:
                    enabled: true
                    instance_ami: 'ami-0cc293023f983ed53' # latest Amazon Linux 2, June 2019
                    instance_key_pair: mykeypair
                    instance_monitoring: false
                    instance_type: t2.nano
                    max_instances: 2
                    min_instances: 1
                    desired_capacity: 1
                    target_groups:
                        - netenv.ref mynet.applications.myapp.groups.site.resources.alb.target_groups.myapp.arn
                    security_groups:
                        - netenv.ref mynet.network.vpc.security_groups.myapp.webserver.id
                    segment: webserver
                    termination_policies:
                        - Default
                    update_policy_max_batch_size: 1
                    update_policy_min_instances_in_service: 0
                    user_data_script: |
                        #!/bin/bash

                        yum update -y
                        yum install httpd -y

                        # Restart apache
                        apachectl restart

Finally the environments section will deploy AWS Resources to create networks and applications to
support each environment. In this quickstart, there will be two environments, one named ``dev``
and the other named ``prod``. Every environment builds it's network based on the ``network:`` section
defined at the top of the file, then the environent names the applications it will contain.

At any point in the environment configuration, the default network and applications configuration
can be overridden. In this quickstart, the ``prod`` environment has an AutoScalingGroup with
a larger instance size, a minimum of two web server instances.

The ``prod`` environment is also set to ``enabled: false`` which means that it will not be
provisioned.

.. code-block:: yaml

    environments:

        dev:
            title: "Development Environment"
            default:
            applications:
                myapp:
                    enabled: true
            network:
                aws_account: config.ref accounts.master
                vpc:
                    cidr: 10.20.0.0/16
                    segments:
                        public:
                            az1_cidr: 10.20.1.0/24
                            az2_cidr: 10.20.2.0/24
                            internet_access: true
                        webserver:
                            az1_cidr: 10.20.3.0/24
                            az2_cidr: 10.20.4.0/24
                    nat_gateway:
                        myapp:
                            enabled: false
            eu-central-1:
                enabled: true

        prod:
            title: "Production Environment"
            default:
                applications:
                    myapp:
                        enabled: true
                        groups:
                            site:
                                web:
                                    instance_type: t2.medium
                                    max_instances: 4
                                    min_instances: 2
                                    desired_capacity: 2
                network:
                    aws_account: config.ref accounts.master
                    vpc:
                        cidr: 10.20.0.0/16
                        segments:
                            public:
                                az1_cidr: 10.20.1.0/24
                                az2_cidr: 10.20.2.0/24
                                internet_access: true
                            webserver:
                                az1_cidr: 10.20.3.0/24
                                az2_cidr: 10.20.4.0/24
                        nat_gateway:
                            myapp:
                                enabled: false
            eu-central-1:
                enabled: false


.. _`AIM Configuration`: ./aim-config.html


Provision an environment
------------------------

The aim provision command creates all the AWS resources needed for an environments.


Clean-up and next steps
-----------------------

If you are finished, you can use the ``aim delete`` command to
delete your environments and networks.

.. Attention:: If you want to continue with Quickstart 102, you will
    need to leave the ``dev`` environment you created up and running.
    To save on AWS costs (the dev env costs about $1 per day to run),
    you can use the delete command to completely remove all your AWS
    resources, then save your aim project directory for later use
    and run ``aim provision NetEnv dev`` to recreate your envrionment.
    However, it does take about 20 minutes to spin up a new environment.

You can delete the NetworkEnvironment named ``mynet`` that you created
with:

.. code-block:: bash

    $ aim delete NetEnv mynet

The next walkthrough, `Quickstart 102`_, will show you how to
add an SSH bastion server and launch it in the public subnet,
then use it as an SSH gateway to connect to
your web server on a private subnet.

.. _`Quickstart 102`: ./quickstart102.html

