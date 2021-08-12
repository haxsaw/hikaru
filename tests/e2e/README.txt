The tests in this file assume an running Kubernetes system to succeed.

They were developed using K3s, a lightweight Kubernetes system good for
developers. You may need to adjust them if you wish them to run on other
K8s systems, most notably setting the path to the config file for the
Kubernetes configuration.

There are no assumptions of any resources being deployed on the system for
the tests to operate; they create their own resources. Bear in mind that
this may entail downloading some containers for pods.
