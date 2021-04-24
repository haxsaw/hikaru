********************************************
Kubernetes API Releases and Versions
********************************************

Hikaru is structured to support different releases of the Kubernetes API (as expressed through
the Kubernetes Python client) as well as different versions of the API within a single release.
If you don't care much about what you're release you're working to, chances are that
you won't have to do anything special to use the proper release and version of the API model
in your code, but if you are working with an older Kubernetes infrastructure or a different
release of the Python client then you may need to specify what release and/or version to use.

========
Releases
========

At the time of this writing, Kubernetes is at release 1.16, and 1.17 is in alpha. The Python Kubernetes client works on slightly different release numbers:

+-------+-------------+
|K8s Rel|Py Client Rel|
+=======+=============+
|1.15   |1.11         |
+-------+-------------+
|1.16   |1.12         |
+-------+-------------+
|1.17   |???          |
+-------+-------------+

In Hikaru, the differences in releases are reflected in the subpackages of the ``model`` package. Each K8s release has its own subpackage under ``model`` with names such as ``rel_1_16``. Beneath
this there is a standardized structure reflecting the supported verions of the K8s API for
that particular release (more on this later). Each release of Hikaru has a default release
that it works with out of the box (currently 1.16), so if you don't need anything different
than the default release then you don't need to do anything more.

Every default release has a default version, currently ``v1``; the objects from the v1 version are automatically imported into the default release, and the default release's model
objects are automatically imported into the `hikaru.model` module. That means that if you wish
to use v1 objects for the default (rel_1_16) release, the following statements result in the
importing of the exact same set of Hikaru objects:

.. code:: python

    from hikaru.model import *  # pulls in the default release's objects
    from hikaru.model.rel_1_16 import *  # pulls in the default version's objects
    from hikaru.model.rel_1_16.v1 import *  # pulls in the v1 objects
    from hikaru.model.rel_1_16.v1.v1 import * # same as above

In the future, once Hikaru ships with support for additional releases, you will be able to 
access objects from other releases by naming the release when you import:

.. code:: python

    from hikaru.model.rel_1_17 import Pod  # from the default v1 version
    from hikaru.model.rel_1_15.v2beta1 import PodSpec  # from a specific version

...and so forth.

Switching Releases in Code
--------------------------

Using imports to specify which release to use works when you're creating objects directly, but
what about when Hikaru is creating the objects for you, for example as as a result of calling ``load_full_yaml()``? 

Hikaru maintains two notions of a **default** release; one globally for a program, and one on
a per-thread basis. If a per-thread release isn't set then the global default release is used.
Hikaru supplies some functions to view and alter these values:

- The ``get_default_release()`` method returns a string that is the name of the release set for the current thread, and if there isn't one then it returns the name of the global release for the program.
- The ``set_default_release()`` function sets the string name of the default release to use for the current thread; hence different threads can default to different releases of Hikaru objects and hence the underlying K8s API. 
- The ``set_global_default_release()`` function sets the the string name of the global default release to use in the entire program; so if a thread doesn't have its own default then it will fall back to the value supplied with this call.

=========
Versions
=========

Within a given release, Hikaru provides support for all the different versions of K8s objects that were defined for that release in the Swagger API specification file.

Each supported verion lives in its own subpackage of the release package; for example here are
the available version packages for release ``rel_1_16``:

  - v1
  - v1alpha1
  - v1beta1
  - v1beta2
  - v2alpha1
  - v2beta1
  - v2beta2

The available alpha and beta releases may differ from release to release of the K8s Swagger
file.

Each version is a subpackage with a standard structure:

- version module with the same name as the package.
- an ``__init__.py`` file that imports all classes from the version module so that they are available at the package level.
- a ``documents`` module that provides a filtered view on the contents of the verion module, only containing top-level classes that are subclasses of ``HikaruDocumentBase``.
- a miscellaneous module for future use

So for example, the ``rel_1_16.v1`` package contains these modules:

- ``__init__.py``
- ``documents.py``
- ``misc.py``
- ``v1.py``

Since ``__init__.py`` imports the classes from ``v1.py``, the following two are 
equivalent:

.. code:: python

    from hikaru.model.rel_1_16.v1 import *
    from hikaru.model.rel_1_16.v1.v1 import *

The ``documents`` module exposes only a subset of the classes from ``v1.py``; these are all
subclasses of ``HikaruDocumentBase``, and are the kinds of classes that are generated when
Hikaru builds K8s objects for you when it has to determine the class, for example with the
``load_full_yaml()`` or ``from_dict()`` functions. If you never need to manually create any
arbitrary object from a given version, using just the symbols in ``documents`` can keep your
namespace from becoming cluttered. Additionally, ``HikaruDocumentBase`` subclasses are where
Kubernetes API actions are defined, and so if you wish to use Hikaru to directly interact with
Kubernetes, you will find the methods on the various classes. You can still access these
classes from the v1 version itself.

Model classes are generated automatically from the Kubernetes swagger API definition file.
They include all descriptions of the object and properties that the swagger file contains,
hence the same documentation in the Kubernetes online docs can also be found in these
generated classes.

All model classes are built as Python dataclasses with type annotations that are driven
from the swagger file. This means that in IDEs such as PyCharm and Pydev you can receive
meaningful assistance from the IDE as to the names and types of a parameters to a model
class, which provides material assistance in the authoring process. It also means that every
Hikaru model class can be used with the tools in the dataclasses module to inspect and
process both classes and class instances.
