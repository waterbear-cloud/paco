.. _quickstart:

Quickstart Lab 101
==================

This quickstart will walk you through creating and provisioning an AIM project.
An AIM project is a directory of YAML files that semantically describes an
Infrastructure as code (IaC) project. It consists of
data for concepts such as networks, applications and environments. AIM projects
can be provisioned to AWS using the AIM CLI.

You will learn how to create an AIM project that hosts a simple web application.
You will copy a starting AIM project template, and provision the resources
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

You will create an new AWS IAM User that only has permissions to switch to a
role that can delegate administrator access to AIM. These steps will involve
installing a CloudFormation template to create the IAM User and IAM Role,
then setting up the new User account with MFA and creating an API key.

First, to create the user and role, follow the steps below to create a CloudFormation
stack from our AIMInitialization.yaml_ template. It is possible to use AIM with an existing
IAM User account, but it is highly recommended to use a dedicated user account.
By using the CloudFormation template, you can simply delete the CloudFormation stack
when you are finished and it will remove all aim access that you need for these
quickstarts.

  1. Download the AIMInitialization.yaml_ CloudFormation template.

  #. Access your AWS Console, visit the CloudFormation Service
     and click on the "Create stack" button. Choose "Upload a template file"
     and then "Choose file" and choose the AIMInitialization.yaml file.
     Then click "Next".

     .. image:: ./images/quickstart101-create-stack-init.png

  #. Enter "AIMInitialization" as the Stack name and enter
     the name of a new IAM User. Then click "Next".

     .. image:: ./images/quickstart101-stack-init-details.png

  #. On the "Configure stack options" screen you can leave everything
     default and click "Next". On the "Review AIMInitialization" you
     can also leave all the defaults click
     "I acknowledge that AWS CloudFormation might create IAM resources with custom names."
     to confirm that this stack can create an IAM User.
     Finally click "Create stack".

  #. Wait a couple minutes for the stack to finish create. Take note on the "Outputs"
     tab that there is a "SigninUrl" field. These is an optional URL you can use if
     you want to use the same user that you use the aws cli with to login to and switch
     to the AIM Administrator role. For this quickstart, it's not necessary, but is
     useful when you have a multi-account set-up and watch to easily switch between accounts.

     .. image:: ./images/quickstart101-stack-outputs.png

.. _AIMInitialization.yaml: ./_static/templates/AIMInitialization.yaml

Next you will need to set-up the new user account and create an API key. Follow these steps:

  1. In the AWS Console, go to the Identity and Access Management (IAM) Service, click on "Users"
     and click on the User name you supplied earlier. Then click on the "Security credentials" tab.

     .. image:: ./images/quickstart101-user-start.png

  #. Set-up multi-factor authentication (MFA). As this account has full administrator access, it
     is critical to keep this secure. The delegate role is configured so that it can only be
     used by users that have MFA set-up. Where it says, "Assigned MFA device" click on "Manage".
     Then setup an MFA device. If you don't know which one to use here, choose "Virtual MFA device"
     and you can use either Authy_ or `Google Authenticator`_ on your computer or phone as a virtual
     MFA device.

  #. Create an AWS Access Key. While still on the "Security credentials" tab, click on "Create access key".
     You will be given an "Access key ID" and "Secret access key". Save these somewhere safe and secure.
     You will need these credentials later when you set-up the AIM project.

Now you are ready to create an AIM project. Note that when you are finished and wish to clean-up all AWS
resources for this quickstart, you will first need to return to this user and manually delete the
Assigned MFA Device and Access key. Then you can go to the CloudFormation service and delete the
AIMInitialization stack. If you try and delete the stack without doing this first, you will get the
error message "DELETE_FAILED: Cannot delete entity, must delete MFA device first.".

.. _Authy: https://authy.com/

.. _`Google Authenticator`: https://en.wikipedia.org/wiki/Google_Authenticator


Create an AIM Project
---------------------

An AIM Project is a directory of specially named sub-directories
containing YAML files each requiring speccific formats.
These configuration sub-directories and files are documented
on the `AIM Configuration`_ page.

.. _`AIM Configuration`: ./aim-config.html

.. Attention:: Names are used extensively in AIM projects. Every object has a name.
    All Accounts, NetworkEnvironments, Applications, Environments and more will be named.
    These **names should be as short as possible** as they are concatened together
    to create unique AWS Resource Names.

    As some AWS Resource Names have character length limits, in addition to
    keeping the name short (no more than 10 characters, but 3 to 5 is ideal),
    you can only use alphanumeric, underscore and hypeh characters. Short names also make it
    easier to see what workload each resource is supporting in the AWS Console.

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

    About to create a new AIM Project directory at /Users/username/projects/myproj

    Select starting_template:
    1 - empty
    2 - simple-web-app
    Choose from 1, 2 (1, 2) [1]: 2

You will be asked questions about your project. First, choose ``2`` to use the
``simple-web-app`` template. This will give you basic network, with a simple
application that is deployed into two environments.

You will be asked for a ``project_name`` and ``project_title``. The
``project_name`` must follow the naming restrictions
(short with only alphanumeric, underscore and hyphen characters).
The title is a human-readable string, so you can use spaces and other characters,
and you don't have to worry about the length.

.. code-block:: text

    project_name [myproj]: myproj
    project_title [My AIM Project]: My AIM Project

Next you will be asked for network and application names and titles. In this simple
walkthrough, you will create one network and one application. In more complex
AIM uses, you can create a single network and deploy mulitple applications into it.

.. code-block:: text

    network_environment_name [mynet]: mynet
    network_environment_title [My AIM NetworkEnvironment]: My AIM NetworkEnvironment
    application_name [myapp]: myapp
    application_title [My AIM Application]: My AIM Application


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

    $ aim --home ./myproj/ describe
    Project: myproj - My first AIM project
    Location: /Users/username/projects/myproj

    Accounts
    - master - Master AWS Account

    Network Environments
    - basic_network - Basic Network

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
                            - cidr_ip: 0.0.0.0/32
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
                        echo "<html><body><h1>Hello world!</h1></body></html>" > /var/www/html/index.html
                        service httpd start

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
            eu-central-1:
                enabled: false


.. _`AIM Configuration`: ./aim-config.html



Provision an EC2 keypair
------------------------

Before you can provision your environment, you first need to create
an EC2 keypair. The EC2 instances you later launch will be configured
to use this keypair for SSH access.

The ``aim provision`` command is used to create AWS resources. The provision
command takes the name of a controller and a component. This combination
of controller and component will map to different sections of an AIM project
and provision AWS resources to support that configuration.

The EC2 controller and keypair component maps to the ``keypairs:`` configuration
in the file ``<aim-project>/Services/EC2.yaml``. The ``simple-web-app`` starting template
you used will has created configuration for a keypair named ``aimkeypair``. Run the
command ``aim provision EC2 keypair aimkeypair --home myproj`` to create a keypair.

.. code-block:: bash

    $ aim provision EC2 keypair aimkeypair --home myproj
    Provisioning Configuration: EC2.keypair
    Project: /Users/username/projects/myproj/
    EC2 Service: keypair: flimflam: Key pair created successfully.
                        flimflam: Account: master
                        flimflam: Region:  us-west-2
                        flimflam: Fingerprint: a6:3b:12:c6:34:ec:31:00:36:2b:e3:2c:f9:b2:11:d4:21:bb:48:6b
                        flimflam: Key:
    -----BEGIN RSA PRIVATE KEY-----
    MIIEpQIBAAACKQEAt51MPT8LE+Ba7l52ySl2s9VgPcJ4KzxO4pZYk7LcGEotuqsInha81paXJcbz
    vCsohv9LaKuABIG0abjVzlJUOatkipSaABrqVmaICVOqx3qZ1q5ebf7oSowjhOx4uJViIF5kSx5a
    rnyNPqmZzzXTDhBFWA5av7tKQHRzdWnSsWTXxl5dHr+7Ae+wf0F2dFHRxeO59/CEwrpQdp/OGugE
    LJ3QxaGVZ7FNCqEgup09KWFpbJe/oUNbGOL67s2RMn+Wcvo7CQIEXsrNfI0Zyba/6D3Tue9yx3Y/
    Qni9a199maGxOXNb4CyFqDm0c1hcIqlSBASIxsPzlpv7vGH9XcHEpQIDAQABAoIBAQCtRI5xLVCy
    zQCB+Dp30dzmDvDm1uC3TA3U3LNxjVMMyNMmV8emBybkCO9RAtF2O/PekIMEnvILTqqFKZr5O8+n
    LAmQjHJWrw97wP2Wb5G09AjAAYOyoN1rm5rZEJ1K8gzLJsfV6yr/hSF0hG9UjiJAHzKQydrxGzgS
    YtGhdt8P7dIMa5BnOYouuxDqMGpmjAkEeZue03bJaX9IZkWyAQw8TpHnGb87AriFJMAWyzG9GsgE
    pIsPGaQmf7M1xzDCQsv4WNvd7xN1ym12bFf0G99SyTzx97SPL5riGz3mxvSkC3CGQhaP4bqa6lft
    eg3d/XXnYDi1Fmd/qoBNXUZ90VLxAoGBAPDd0yveT1psm4E6BOsQTdf0d3lDA1F8dhn4TdNgvf04
    3Lt+YFi8jqmStIstxDvnQBGXPP5jZy4CCakLWf6fRDoIB11IgGsZ6Rzsllpbuh01BNNjqtz5/Q6K
    0G9GLmX6rPx+HIlusrr4QMWg91012z0IY5UgfzsnhhQjhUaK7nmrAoGBAMMmnLlDLfVJp5I28Q4a
    KF8mTcT8MfEKKRacoZBkVXLvvFJnHQxuuXLnrxmZt06/XwhkOrd9lo3AyDqoSkRVY+9WraPUvXdF
    t94os7ZFdEBaNKXRnun8rdGm7N78BoqJP4+31ar6V1uZN9L9J/C8HIAGjE3I4L3440VlxlyamIrv
    AoGAIyds86EdmcfyJjkukJQvmE4wxbz3FgSBRCcOTMR41iVfaen269yRQcSMnyeN1WRZ4HdfSo19
    eKSJfmeOue/KyGF1nBHpFDiS4krRYtyyXCLp0mRggqHlwiKWazcl/HJKnwtU5OYIJeunoHBuyebb
    WZwI1LIKf7q0AepxQCt0xMMCgYEAkcxQPO1e8ao0or2ffPy3+taANdKBcWc46WbeIiWD3ZoUpa/Z
    +QbkUF+d5097rz60vm07nQkcKQ3FymUfD0yInDCzC/qODwUsaLMaCOx8/PMn8FbbFk+sgTzoLXQ3
    YttFfJdI8DOWfp3LIjv20hmIZXH+8sJIfkXrblaqS1dI7ksChZEA2AGNLYuTyhgsrKI7fajTMpMZ
    sFW54VnZtbHSxa3xk9AjjqesbK2S6xApHbsNZG6XUEjJIeBFGHUR0DO/FXAYYlnQ6u23MfkxvkN/
    CPKnto8xA1SYWgC8Q8e1MpYeK2M69dG3KwQfLsGrPtZnDg/aj50JqnjwauA2DGw3Yk90Rcw=
    -----END RSA PRIVATE KEY-----

Copy the whole section from ``-----BEGIN RSA PRIVATE KEY-----`` to ``-----END RSA PRIVATE KEY-----``
and put this in a new file named ``aimkeypair.pem``. Run ``chmod 0400 aimkeypair.pem`` to give
this file private permissions. If this is for a real-world environent, you need to keep
a copy of this file somewhere safe, as if you lose it you will not be able to SSH to your
EC2 instances.


Provision an environment
------------------------

The ``aim provision`` command create or updates the AWS resources needed for environments.

This command needs the path to an AIM Project directory. For this command you can either
supply this argument with the ``--home`` switch, or set the environment variable ``AIM_HOME``.

The provision command can act on different AIM configuration types, such as NetEnv, S3, Route53 and IAM.
These types are called controllers and they control how CloudFormation stacks are provisioned.
The NetEnv controller will provision a complete NetworkEnvironment YAML file, which you can
run to provision the ``dev`` environment for the ``mynet`` NetworkEnvironment.

Now run ``aim provision --home myproj NetEnv mynet`` and you should provision the ``dev`` environment.
You should see the following output on the CLI:

.. code-block:: text

    $ aim provision NetEnv mynet --home myproj
    Provisioning Configuration: NetEnv.mynet
    MFA Token: master: 123456
    Network Environment
    NetEnv: mynet: Init: Starting
    Environment: dev
    Environment Init: Starting
    NetworkStackGroup Init: VPC
    NetworkStackGroup Init: Segments
    NetworkStackGroup Init: Security Groups
    NetworkStackGroup Init: NAT Gateway: myapp
    NetworkStackGroup Init: Completed
    ApplicationStackGroup: Init
    ApplicationStackGroup: Init: LBApplication: alb
    ApplicationStackGroup: Init: ASG: web
    ApplicationStackGroup: Init: Completed
    Environment Init: Complete
    Environment: prod
    Environment Init: Starting
    NetworkStackGroup Init: VPC
    NetworkStackGroup Init: Segments
    NetworkStackGroup Init: Security Groups
    NetworkStackGroup Init: NAT Gateway: myapp
    NetworkStackGroup Init: Completed
    ApplicationStackGroup: Init
    ApplicationStackGroup: Init: LBApplication: alb
    ApplicationStackGroup: Init: ASG: web
    ApplicationStackGroup: Init: Completed
    Environment Init: Complete
    NetEnv: mynet: Init: Complete
    master: Create:  NE-mynet-dev-Net-VPC
            Waiting: NE-mynet-dev-Net-VPC
            Done:    NE-mynet-dev-Net-VPC
    master: Create:  NE-mynet-dev-Net-Segments-public
    master: Create:  NE-mynet-dev-Net-Segments-web
    master: Create:  NE-mynet-dev-Net-SecurityGroups-myapp
            Waiting: NE-mynet-dev-Net-Segments-public
            Done:    NE-mynet-dev-Net-Segments-public
    master: Create:  NE-mynet-dev-Net-NGW-myapp
            Waiting: NE-mynet-dev-Net-NGW-myapp
            Done:    NE-mynet-dev-Net-NGW-myapp
    master: Create:  NE-mynet-dev-App-myapp-euc1-IAM-Roles
            Waiting: NE-mynet-dev-App-myapp-euc1-IAM-Roles
            Done:    NE-mynet-dev-App-myapp-euc1-IAM-Roles
    master: Create:  NE-mynet-dev-App-myapp-ALB-site-alb
            Waiting: NE-mynet-dev-App-myapp-ALB-site-alb
            Done:    NE-mynet-dev-App-myapp-ALB-site-alb
    master: Create:  NE-mynet-dev-App-myapp-ASG-site-web
            Waiting: NE-mynet-dev-App-myapp-ASG-site-web
            Done:    NE-mynet-dev-App-myapp-ASG-site-web

While this is running, you can visit the AWS Console and go to the CloudFormation service and watch
the stacks being launched. You will see the stack ``NE-mynet-dev-Net-VPC`` created first.

    .. image:: ./images/simple-stack-one.png

Where possible, AIM will launch multiple stacks at once, for example, the web and public subnets stacks
will both be created at the same time. It will take about 10 minutes for all of the stacks to be created
to build the ``dev`` environment. When it's done you should see eight stacks,

    .. image:: ./images/simple-stack-two.png

Notice that stack names such as ``NE-mynet-dev-App-myapp-ASG-site-web`` are built by concatenating
together the names you chose when you created the AIM project. You can use the CloudFormation search
feature to display just the stacks requried a particular aspect of your environment. For example,
search for ``dev-App`` to display the stacks that provision the application resources for the dev environment,
or ``dev-Net`` to display the stacks that provision the network resources for that environment.

    .. image:: ./images/simple-stack-three.png

Now visit the EC2 service in the AWS Console and you should see an instance running:

    .. image:: ./images/simple-ec2-one.png

Then click on **Load Balancers** in the EC2 Services and you should see an application load balancer
running:

    .. image:: ./images/simple-alb-one.png

Copy the DNS name to the clipboard and paste it into your web browser. Your application should
return a static web page:



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

    If you have completely deleted aim or your AIM project, and left
    the AWS resources provisioned, then you can login to the AWS Console
    and go to the CloudFormation service. There you can manually delete
    all of the CloudFormation stacks to remove everything from your
    AWS account.

You can delete the NetworkEnvironment named ``mynet`` that you created
with:

.. code-block:: bash

    $ aim delete NetEnv mynet

The next walkthrough, `Quickstart 102`_, will show you how to
add an SSH bastion server and launch it in the public subnet,
then use it as an SSH gateway to connect to
your web server on a private subnet.

.. _`Quickstart 102`: ./quickstart102.html

