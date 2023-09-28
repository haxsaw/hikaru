************
Installation
************

Package Overview
================

Previously, Hikaru was a single monolithic package that contained
the core components of Hikaru, support for four different versions of the Kubernetes Python client (and hence Kubernetes API),
and the code generation capabilities that can turn live Hikaru objects into Python source.

As of version 1.1.0, Hikaru's packaging has been changed. It has been broken into a collection of smaller packages that allow
the user to only install the support tbey require. However, a meta-package still exists that mimicks the old ``hikaru`` package
and installs all the components that were present prior to version 1.1.0.

The new package structure is as follows:

- The core Hikaru functionality is provided by the ``hikaru-core`` package. This package contains:

  - The base modeling classes (and all the methods those support)
  - CRD support
  - Support for persistence to/from YAML/JSON/Python dicts
  - Watch support
  - Application support

  This package DOES NOT include support for generating Python code from Hikaru objects.

- Kubernetes modeling objects are provided by various ``hikaru-model-*`` packages; for instance ``hikaru-model-25`` provides
  modeling objects that conform with the version 25 (1_25) version of the Kubernetes API. Each of these model packages has
  an internal requirement of ``hikaru-core``, so simply running the following command will result in the both ``hikaru-core``
  and the version 25 API model classes being installed:

.. code::

    pip install hikaru-model-25

- Python code generation is now supplied via the ``hikaru-codegen`` package. This package installs the tools Hikaru needs to
  generate Python source code from Hikaru objects. So if you want to do things like convert a directory full of Kubernetes
  YAML into Python source, you'll need this package. Like the model packages, the codegen package has a dependency on
  ``hikaru-core``, so installing codegen will also install core.

This new structure gives the user the option to create smaller installations of Hikaru, only installing the pieces that are needed
for their application. The new package structure maintains the same installation structure, so existing code needs to do nothing
to use these new packages; it is an install-time-only change.

If you wish to continue with the existing monolithic package that Hikaru was delivered in prior to version 1.1.0, there is still
a ``hikaru`` package you can install. This meta-package installs the core, codegen, and the four most current model packages.

Things to keep in mind
======================

- The ``hikaru-core`` package works with the Python Kubernetes package having a version of at least 23.6.0. Each model package
  has their own minimal version of the Kubernetes client it works with, for example ``hikaru-model-24`` requires at least
  version 24.2.0 of Kubernetes. If you do nothing else, installing a model package will result in the currently highest available
  version of the Kubernetes package being installed. Hikaru is fine with this, but your cluster might not be. If your cluster
  is running a lower numbered version of the Kubernetes API, consider adding a requirement for your own project that establishes
  a suitable maximum version for the Kubernetes client package.
- The code generation functions/methods are always available, even if the ``hikaru-codegen`` package hasn't been installed. However,
  if you attempt to use them when this package hasn't been installed, then you will get an ``ImportError`` at runtime when trying
  to generate Python source.
- Hikaru allows you to install multiple model packages if you wish. Your code can always directly import the correct model classes,
  but to be sure that Hikaru creates the correct model classes, be sure to call ``set_default_release()`` to the name of the
  release classes (rel_1_23, rel_1_25, etc) you wish it to create when reading data from the cluster or from YAML/JSON/Python dicts.
- When multiple model packages are installed, the default one Hikaru will use when it needs to instantiate an object is the highest
  numbered release.
- If you install multiple model classes, make sure there are no installation complaints regarding the version of the Kubernetes
  package you have installed. You may need to upgrade it to a later version in some cases.

Deprecations
============

Prior to version 1.1.0, every release of Hikaru that added support for a new version of the Kubernetes API dropped support for
the oldest version. At version 1.1.0, Hikaru is supporting API versions 23-26, inclusive, and the release 23 models would
generate a deprecation warning message when imported. This was done to avoid Hikaru from growing without bound as it added
support for newer versions of the Kubernetes API and its objects.

With the introduction of this new packaging structure, deprecation is no longer an issue: with the core and the models independent,
there is no longer a practical need to deprecate older models. Hence Hikaru will no longer issue deprecation warnings when
any model package is imported. In general, model packages will not be deprecated unless there the package is old and there
is an incompatible change in the core.

Package versioning
==================

Starting with v 1.1.0 of Hikaru and its new package structure, versioning will be a bit different. Previously, Hikaru would acquire a new version any time that a new version of the Kubernetes Python client became available or when Hikaru itself developed a new capability. This meant that if any version of the Kubernetes client was patched Hikaru had to issue a new version as well as any time Hikaru itself changed (happily this hasn't happened yet). This made the semantics of version numbers of Hikaru a bit murkey, as new versions had to be issued in multiple circumstances.

The new structure improves on this situation: ``hikaru-core`` will only get new versions when the core itself changes, and independent model packages will only get versions when they are first introduced or when the corresponding Kubernetes Python
client is patched. The same goes for the codegen package. As the ``hikaru`` meta-pacakge will usually only floor the versions that
make it up, it will only get new versions when an incompatibility arises in one of its component packages and a new version is
required. This helps isolate version change impact better and makes testing of the Hikaru system simpler.
