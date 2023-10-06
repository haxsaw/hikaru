
.. |travis| image:: https://travis-ci.com/haxsaw/hikaru.svg?branch=dev
    :target: https://app.travis-ci.com/github/haxsaw/hikaru

.. |license| image:: https://img.shields.io/github/license/haxsaw/hikaru
   :alt: GitHub license   :target: https://github.com/haxsaw/hikaru/blob/main/LICENSE

.. |versions| image:: https://img.shields.io/pypi/pyversions/hikaru
   :alt: PyPI - Python Version

.. |coverage| image:: https://codecov.io/gh/haxsaw/hikaru/branch/dev/graph/badge.svg?token=QOFGNVHGNP
   :target: https://codecov.io/gh/haxsaw/hikaru
   
.. |logo| image:: hikaru-model-24-logo.png
   :alt: Hikaru

|logo|


Version 1.1.1

|travis|   |license|   |versions|   |coverage|

`Try it: see Hikaru convert your K8s YAML <http://www.incisivetech.co.uk/try-hikaru.html>`_

`Release notes <https://github.com/haxsaw/hikaru/blob/main/release_notes.rst>`_

`Full documentation at Read the Docs <https://hikaru.readthedocs.io/en/latest/index.html>`_

Hikaru is a collection of tools that allow you to work with Kubernetes resources from within Python in
a variety of ways:

- Hikaru provides type-annotated classes that model all of the Kubernetes resources in Python
  and supports CRUD operations on those classes to manage their lifecycle in your Kubernetes cluster.
- Hikaru also provides tooling to shift formats for these objects, allowing you to turn K8s YAML
  into Python objects, JSON, or Python dicts, and vice-versa. It can also generate Python source code for K8s
  objects loaded from non-Python sources.
- Hikaru also supports a number of features that aid in the management of
  your objects such as searching for specific fields or diffing two instances of a K8s resource.
- Hikaru includes support for creating 'watches' on your objects, providing a means to monitor events
  on your provisioned K8s resources.
- Hikaru provides support for creation of CRDs which support all the above features such as CRUD operations
  and watches.
- Finally, Hikaru includes a facility to specify a collection of
  resources as an 'application', similar in spirit to a Helm chart, and provides the same CRUD,
  watch, and management capabilities on the entire application as it does on single resource objects
  (full format shifting support to come).

**This package provides model classes to create resources through the Kubernetes Python client version 24.x**.
It depends on the
``hikaru-core`` package which will be installed automatically when this packages is installed. This package
will work with any version of the Kubernetes Python client >= 24.x; if you need to constrain which release
is installed then you should establish your own requirement limts on the Kubernetes Python client package.

See README-core.rst for the main README and links to overall documentation.

About
~~~~~

Hikaru is Mr. Sulu’s first name, a famed fictional helmsman.
