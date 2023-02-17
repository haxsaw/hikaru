********************************************
Kubernetes API Releases and Versions
********************************************

Hikaru is structured to support different releases of the Kubernetes API (as expressed through
the Kubernetes Python client) as well as different versions of the API within a single release.
If you don't care much about what release you're working to, chances are that
you won't have to do anything special to use the proper release and version of the API model
in your code, but if you are working with an older Kubernetes infrastructure or a different
release of the Python client then you may need to specify what release and/or version to use.

========
Releases
========

Kubernetes release number are kind of a headache; numbering approaches used in the swagger
text (such as 1.22) don't agree in approach to those used with the Python client (22.x),
and so there is some confusion about how to map through all of these things to Hikaru
release numbers. However, Hikaru has moved along far enough that it's become pretty easy
to see the relationships between swagger, Python client, and Hikaru release, with the
exception of release 0.16b:

+-----------------+-------------+----------------+----------------------+
|K8s Swagger lease|Py Client Rel| Hikaru release | Currently Supported? |
+=================+=============+================+======================+
|1.22             |22.x         |  0.12b         |      **No**          |
+-----------------+-------------+----------------+----------------------+
|1.23             |23.x         |  0.13b         |      **Yes**         |
+-----------------+-------------+----------------+----------------------+
|1.24             |24.x         |  0.16b         |      **Yes**         |
+-----------------+-------------+----------------+----------------------+
|1.25             |25.x         |  0.16b         |      **Yes**         |
+-----------------+-------------+----------------+----------------------+
|1.26             |26.x         |  0.16b         |      **Yes**         |
+-----------------+-------------+----------------+----------------------+

Instead of separate releases for each of 24.x, 25.x, and 26.x of the Python K8s client,
Hikaru 0.16b rolls together support for all of these releases with support for
23.x. That means 0.16b works with 23.x-26.x of the K8s client and the associated K8s
system. This was largely done for the convenience of Hikaru's maintainer: each release
takes a fair amount of work, and due to personal circumstances and rapid arrival of Python
client releases the Python client got ahead of Hikaru, so it was easier to create a new
release that supported the remaining unsupported Python client release than to create
unique Hikaru releases for each. Hikaru allows you to specify which should be your default
release, so users my use 0.16b with any of the supported underlying K8s releases and it
will work properly (if unspecified, the default is the highest numbered supported release,
which for 0.16b is 26.x/1.26).


.. note::

    A Hikaru release only supports the last four versions of the K8s Python client;
    with each new release support for the oldest
    release is dropped and use of the oldest remaining release results in a deprecation
    warning when imported.

In Hikaru, the differences in releases are reflected in the subpackages of the ``model``
package, which follows the naming for the actual underlying K8s release.
Each K8s release has its own subpackage under ``model`` with names such as ``rel_1_22``.
Beneath this there is a standardized structure reflecting the supported versions of the
K8s API for that particular release (more on this later).

Each release of Hikaru has a default release
that it will use when it needs to create objects for processing YAML, but this can be
changed depending on what you need. When creating your own objects, they must be done
with respect to a particular release.

Every release has a default version, currently ``v1``; the objects from the v1 version
are automatically imported into the default release. That means that if you wish
to use v1 objects for the rel_1_22 release, the following statements result in the
importing of the exact same set of Hikaru objects:

.. code:: python

    from hikaru.model.rel_1_22 import *  # pulls in the default version's objects
    from hikaru.model.rel_1_22.v1 import *  # pulls in the v1 objects
    from hikaru.model.rel_1_22.v1.v1 import * # same as above

Hikaru currently supports the following releases of the Kubernetes Python client and API:

- 1.19 (package name rel_1_19)
- 1.20 (package name rel_1_20)
- 1.21 (package name rel_1_21)
- 1.22 (package name rel_1_22)

Switching Releases in Code
--------------------------

Using imports to specify which release to use works when you're creating objects directly, but
what about when Hikaru is creating the objects for you, for example as as a result of calling
``load_full_yaml()``? 

Each Hikaru release has a notion of a global **default** K8s release it will use when creating
objects from YAML, JSON, or Python dicts; this is by default the highest numbered release
of K8s that the release of Hikaru supports. So if Hikaru supports both 1.19, 20, 21 and 22 K8s clients,
then it will default to creating rel_1_22 model objects from parsed YAML.

Hikaru maintains two notions of a *default* release; one globally for a program, and one on
a per-thread basis. If a per-thread release isn't set then the global default release is used.
Hikaru supplies some functions to view and alter these values:

- The :ref:`get_default_release()<get_default_release doc>` method returns a string that
  is the name of the release set
  for the current thread, and if there isn't one then it returns the name of the
  global release for the program.
- The :ref:`set_default_release()<set_default_release doc>` function sets the string name
  of the default release to use for the current thread; hence different threads can
  default to different releases of Hikaru objects and hence the underlying K8s API. 
- The :ref:`set_global_default_release()<set_global_default_release doc>` function sets
  the string name of the
  global default release to use in the entire program; so if a thread doesn't have its
  own default then it will fall back to the value supplied with this call.

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

=========
Versions
=========

Within a given release, Hikaru provides support for all the different versions of K8s
objects that were defined for that release in the swagger API specification file.

Each supported version lives in its own subpackage of the release package; for example
here are the available version packages for release ``rel_1_22``:

  - v1
  - v1alpha1
  - v1beta1
  - v2beta1
  - v2beta2

The available alpha and beta versions can differ from release to release of the K8s
swagger
file, so you may have to adjust your imports if you use symbols from these subpackages

Each version is a subpackage has a standard structure:

- version module with the same name as the package.
- an ``__init__.py`` file that imports all classes from the version module so that
  they are available at the package level.
- a ``documents`` module that provides a filtered view on the contents of the version
  module, only containing top-level classes that are subclasses of ``HikaruDocumentBase``.
- a ``watchables`` module that contains two collection classes for the Hikaru classes
  whose instances support **watch** capabilities.
  Watchables and watchers are covered in more detail at
  :ref:`watchers<watchers>`.

So for example, the ``rel_1_22.v1`` package contains these modules:

- ``__init__.py``
- ``documents.py``
- ``v1.py``
- ``watchables.py``

Since ``__init__.py`` imports the classes from ``v1.py``, the following two are 
equivalent:

.. code:: python

    from hikaru.model.rel_1_22.v1 import *
    from hikaru.model.rel_1_22.v1.v1 import *

The ``documents`` module exposes only a subset of the classes from ``v1.py``; these are all
subclasses of :ref:`HikaruDocumentBase<HikaruDocumentBase doc>`, and are the kinds of
classes that are instantiated when
Hikaru builds K8s objects for you when it has to determine the class, for example with the
``load_full_yaml()`` or ``from_dict()`` functions. If you never need to manually create any
arbitrary object from a given version, using just the symbols in ``documents`` can keep your
namespace from becoming cluttered. Additionally, ``HikaruDocumentBase`` subclasses are where
Kubernetes API actions are defined, and so if you wish to use Hikaru to directly interact with
Kubernetes, you will find the methods on these classes. You can still access these
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
