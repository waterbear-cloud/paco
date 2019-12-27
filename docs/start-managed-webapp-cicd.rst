.. _start-managed-webapp-cicd:

Managed WebApp with CI/CD
=========================

The **Managed WebApp with CI/CD** starting template will provision a standard web application:
ALB load balancer, AutoScalingGroup of web server(s) and an RDS MySQL database. This application
has dev, staging and prod environments with a multi-account set-up. A CodePipeline deployment
pipeline will build and deploy code to different environments based on your application's git repo branch names.
This is a managed application, with a CloudWatch agent to gather host-level metrics and central logs,
a suite of CloudWatch Alarms to alert on metrics and a CloudWatch Dashbaord to assess overall performance.

Create a "Managed WebApp with CI/CD" Project
--------------------------------------------

`Install`_ Paco and then get started by running the ``paco init project <your-project-name`` command.
Review the instructions on `Getting Started with Paco`_ to understand the importance of ``name``
fields in Paco and the difference between a name and title. Then follow the instructions on creating
credentials for your project to connect it to your AWS Account.

Take a minute to `set-up a PACO_HOME environment variable`_, this will save you lots of time typing.

This is a multi-account project template. The CI/CD will use cross-account permissions that are designed to be
used in an account that is seperate from the accounts that they deploy into, so you will need at a minimum of two
accounts. Review the `Multi-account Setup`_ instructions to understand how a multi-account set-up works with Paco.

After you've created a Paco project, connected it to your AWS master account and created child accounts,
take a look at the `Managing IAM Users with Paco`_ docs. This template will start with only a single IAM
User with Administrator access to all accounts. If you need to grant access to this Paco project to more
than one person, or need to manage fine-grained access to different abilities across multiple accounts,
then following this document is a must.

At this point you will have ran:

.. code-block:: bash

    paco provision accounts
    paco provision resource.iam.users

Finally return here to follow the instructions on customizing and provisioning the project!

Customize and Provision CloudTrail
----------------------------------

This is an optional resource. CloudTrail is an AWS service which logs all changes to an AWS
account. It is critical for securely managing accounts and can be extremely helpful in debugging why
something broke when you have more than one person managing an account.

The CloudTrail file for this project is at ``resource/cloudtrail.yaml``. It is configured to send
CloudTrail for every account into an S3 Bucket in the tools account. If you're creating a more
security conscious set-up, you will want to create a dedicated security account and change the
``s3_bucket_account`` field to direct CloudTrail there.

Also the CloudTrail will also be temporarily stored in a CloudWatch LogGroup for 14 days.
You may want to disable that or make it longer. CloudWatch LogGroups are an easier way to
search through your CloudTrail logs and you can also configure MetricFiters to alert you
when events happen that can effect your AWS account security profile.

.. code-block:: bash

    paco provision resource.cloudtrail

s3_bucket_account: 'paco.ref accounts.{{cookiecutter.tools_account}}'


Customize and Provision SNS Topics
----------------------------------

You will need to create SNS Topics if you plan on enabling and provisioning monitoring.
These SNS Topics contain SNS Subscriptions. Review the ``resrource/snstopics.yaml`` file
and note that there is an **admin** group with one email subscription.

This group is configured to recieve any alarm notifications. You can add as many subscriptions
to this group as you want. See the `SNS Topics docs`_ for examples of all protocols.

Also note that if you deployed in a region other than us-east-1 that your project will be
configured to create a second SNS Topic in that region. This is because the Route 53 Health
Check Service only works in that region. If you are not enabling HTTP health checks for your
application, you can remove this region from your snstopics.yaml file.

Customize and Provision EC2 Key Pairs
-------------------------------------

You will need to create EC2 Key pairs in your dev, staging and prod accounts before you can launch
EC2 instances in them. You can do this by running:

.. code-block:: bash

    paco provision resource.ec2.keypairs

Make sure to save these keypairs somewhere safe, you will only see them once and need them for SSH access
to your servers. If you prefer to use your own key pairs, you can create them in the AWS Console and simply
edit the ``resource/ec2.yaml`` file and change the ``keypair_name`` field to match the name you gave your
own keypair in AWS.

Customize and Provision Environments
------------------------------------




.. _Install: ./install.html

.. _Getting Started with Paco: ./started.html

.. _set-up a PACO_HOME environment variable: ./paco-home.html

.. _Multi-account Setup: ./multiaccount.html

.. _Managing IAM Users with Paco: ./paco-users.html

.. _SNS Topics docs: ./paco-config.html#sns-topics
