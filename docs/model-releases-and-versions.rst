********************************************
Kubernetes API Releases and Versions
********************************************

Hikaru is structured to support different releases of the Kubernetes API (as expressed through
the Kubernetes Python client) as well as different versions of the API within a single release.
If you don't care much about what release you're working to, chances are that
you won't have to do anything special to use the proper release and version of the API model
in your code, but if you are working with an older Kubernetes infrastructure or a different
release of the Python client then you may need to specify what release and/or version to use.

Hikaru supports different releases of the Kubernetes Python client via different 'model packages'
such as ``hikaru-model-24`` and ``hikaru-model--25`` for releases 24.x and 25.x of the K8s client,
respectively. Hence, when you see the term 'release' in the following, it is referring to a K8s client
and API release for which there is a corresponding Hikaru model package to support its use.

================================================================
The Common Use Cases
================================================================

Creating objects in code
------------------------

Generally, most users only need v1 objects from any Kubernetes release, and the default version
in a release is always v1, so you can just import everything from that package and get all classes
in your namespace. For instance, if you have the model package for release 25.x installed, you can
just use:

.. code:: python

    from hikaru.model.rel_1_25 import *

Or, if you want specific things, you can just import them:

.. code:: python

    from hikaru.model.rel_1_25 import Pod, ObjectMeta, PodSpec

...although the first form is probably more useful.

Creating objects from the cluster or YAML/JSON/dict
---------------------------------------------------

Creating objects from external sources involves either using methods on Hikaru's Kubernetes model objects, or
by using the included utility functions :ref:`from_dict()<from_dict doc>`, :ref:`load_full_yaml()<load_full_yaml doc>`,
or :ref:`from_json()<from_json doc>`.

If you only have a single model package installed, there's not much else to do but import the required function
and use it:

.. code:: python

    from hikaru import from_dict
    o = from_dict(d)

...although you might want to still import specific model classes to use with type annotations so your IDE can help
with attributes and methods.

If you have multiple model packages installed, you'll need to tell Hikaru which package it should use to build
objects from if you don't want the default, which is the highest numbered (most recent) model package. You do this
with a call to either :ref:`set_default_release()<set_default_release doc>` or
:ref:`set_global_default_release()<set_global_default_release doc>`:

.. code:: python

    from hikaru import set_default_release()
    set_default_release("rel_1_24")

If you don't set the default release first, Hikaru will use whatever is the highest numbered installed model package;
this may not always work, as objects sometimes move from one group to another and the underlying support is
different.

================================================================
Support for Kubernetes Releases and Versions
================================================================

General Structure
-----------------

The Kubernetes API goes through various releases where each release contains different versions
of the API. Each of these K8s releases is supported by a different Hikaru model package, so for K8s
24.x there is a ``hikaru-model-24``, for 25.x there is a ``hikaru-model-25``, and so forth.

These are installed as sub-packages into the ``hikaru.model`` namespace package. Here is what a Hikaru
install would look like if the ``hikaru-model-23``, ``hikaru-model-24``, and ``hikaru-model-25`` packages
were all installed:

.. code::

    hikaru
        |-- model
            |-- rel_1_23
                # package contents
            |-- rel_1_24
                # package contents
            |-- rel_1_25
                # package contents

Model Package Contents
-----------------------

Besides the sub-packages that describe different versions of the K8s API objects and operations, a model package contains a few
standard files. Most of these are ignorable for general cases, but maybe useful for certain specialized uses:

- __init__.py: imports all symbols from the default version sub-package (more on this below) and also ensures
  that the deprecations overrides are loaded.
- deprecations.py: defines certain deprecations that Hikaru core must watch out for when using this model package's
  objects; this provides a way for the core to dis-ambiguate certain situations. Not usually needed by anyone but the
  core.
- unversioned.py: objects defined in the K8s API that don't seem to have an accompanying version number.
- versions.py: contains a single global variable, `versions`, that is a list of strings that names the set of version
  sub-packages within this model package

Versions
---------

Within a single Kubernetes API release are different versions of the API. Each corresponding Hikaru
model package provides support for the objects and methods for all objects in the release.

For example, release 26.x (or 1.26 as it is known in the API swagger file), the following
versions are defined:

- v1
- v1alpha1
- v1beta1
- v1beta2
- v1beta3
- v2

And the structure of the corresponding Hikaru model package will look like the following:

.. code::

    hikaru
        |--model
            |--rel_1_26
                |--v1
                    |--__init__.py
                    |--documents.py
                    |--v1.py   # same name as package
                    |--watchables.py
                |--v1alpha1
                    |--__init__.py
                    |--documents.py
                    |--v1alpha1.py   # same name as package
                    |--watchables.py
                |--v1beta1
                    |--   # same structure
                |--v1beta2
                    |--   # same structure
                |--   #etc
                |--__init__.py
                |--deprecations.py
                |--unversioned.py
                |--versions.py

Most users won't have need for anything other than the classes in the ``v1`` version, but all are available in
case others are needed.

Each version is a subpackage has a standard structure:

- version module with the same name as the package.
- an ``__init__.py`` file that imports all classes from the version module so that
  they are available at the package level.
- a ``documents`` module that provides a filtered view on the contents of the version
  module, only containing top-level classes that are subclasses of ``HikaruDocumentBase``.
- a ``watchables`` module that contains two collection classes for the Hikaru classes
  whose instances support **watch** capabilities.  Watchables and watchers are covered in more detail at
  :ref:`watchers<watchers>`.

===========
Importing
===========

Creating objects in Python code
--------------------------------

Importing a model package imports the default version, which in all cases is ``v1``. That makes the following
lines equivalent:

.. code:: python

    from hikaru.model.rel_1_25 import *  # pulls in the default version's objects
    from hikaru.model.rel_1_25.v1 import *  # pulls in the v1 objects
    from hikaru.model.rel_1_25.v1.v1 import * # same as above

You want to make sure you have installed and are importing the proper Hikaru release for the version of the Kubernetes
Python client you are using. Each Hikaru model package has a dependency on the lowest numbered version of the client
that it works with, but no upper bound. Upper bounds will be established when it is determined that a change in
the client makes some aspect of Hikaru no longer compatible with the client. So far, Hikaru has shown to be pretty
compatible with newer Kubernetes client releases, but unless you control which client release you install you
should rely on decent tests for your code.


Having Hikaru Create Objects
------------------------------

Using imports to specify which model package to use works when you're creating objects directly, but
what about when Hikaru is creating the objects for you, for example as as a result of calling
``load_full_yaml()``, and you have multiple model packages installed?

By default, Hikaru dynamically computes a global **default** model release it will use when creating
objects from YAML, JSON, or Python dicts; this is the highest numbered Hikaru model package installed. So if you have
both ``hikaru-model-24`` and ``hikaru-model-25`` installed, the default model package with be 25, and functions
like ``load_full_yaml()`` will create objects from that model package.

If you have multiple model packages installed and want to control which one Hikaru will use to create objects,
Hikaru provides two functions that allow you to specify which model package to use:


- The :ref:`set_default_release()<set_default_release doc>` function sets the string name
  of the default model package to use *for the current thread*; hence different threads can
  default to different releases of Hikaru objects and hence the underlying K8s API.
- The :ref:`set_global_default_release()<set_global_default_release doc>` function sets
  the string name of the
  global default model package to use in the entire program; so if a thread doesn't have its
  own default then it will fall back to the value supplied with this call.

There are also a couple of functions you can use to look up release information:

- The :ref:`get_default_release()<get_default_release doc>` method returns a string that
  is the name of the model package set
  for the current thread, and if there isn't one then it returns the name of the
  global model package for the program, and if there isn't one of those it will return the highest-numbered (most recent)
  installed model package's name.
- The :ref:`get_default_installed_release()<get_default_installed_release doc>` returns the name of the package
  that is the highest numbered model package that is installed on the system.

.. note::

    While Hikaru supports the use of multiple K8s releases from a single program, in practice
    it can be tricky making this work. That's because while Hikaru allows you to use model
    objects from any release that it supports, there is generally only one actual Python K8s
    client package installed, and there are cases where the symbol names don't line up between
    releases. So if you have the 1.22 K8s client installed and try using model objects from
    rel_1_19, you might find that there are symbols needed by these objects that aren't
    available in the K8s 1.22 client. This effect is most pronounced when using alpha or 
    beta objects. Be sure to test your code thoroughly to ensure that the use of multiple
    releases works as you intend.
