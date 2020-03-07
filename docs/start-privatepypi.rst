.. _start-privatepypi:

Private PyPI Server
===================

The **Private PyPI Server** creates a private PyPI server for hosting your own private Python Packages.
It's Python packages are stored on an EFS filesystem mount. The PyPI server is hosted in an AutoScalingGroup
and will automatically relaunch and remount the EFS filesystem if the server is terminated. Configuration
is included which can be enabled to do routine back-ups on the EFS filesystem and monitor the PyPI server
and alert if the server is not responding.

The PyPI server is run behind an Application Load Balancer (ALB). This ALB is run in a separate application
named "Shared". This configuration is designed to show you how a real-world AWS deployment might run a single
ALB to save on costs and direct requests to a variety of backend resources. This tutorial will also show you
how you could instead run the PyPI server in a public subnet with an ElasticIP to run a PyPI server with
minimal costs.

