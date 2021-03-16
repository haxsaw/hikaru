******************
API Model Versions
******************

Hikaru uses the same swagger file that defines the Kubernetes API as does the Python
Kubernetes client. This file contains a variety of different versions of the API. Hikaru
provides support for using each of these models as you wish.

By default, when you write:

.. code:: python

    from hikaru import *

...you automatically import all model classes from the v1 version of the API spec. An
explicit way of doing this is to import directly from the v1 version model in the model
subpackage:

.. code:: python

    from hikaru.model.v1 import *

Hikaru's model package contains support for the following Kubernetes versions in separate modules:

  - v1alpha1
  - v1beta1
  - v1
  - v2beta1
  - v2beta2

To work explicitly with a particular version, import that version into your program.

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
