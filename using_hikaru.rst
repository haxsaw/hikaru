############
Using hikaru
############

1. Installation
2. Quickstart
3. Key Functions
4. Models
5. The HikaruBase class
6. Querying
7. Issues, Changes, and Limitations
8. Recipes
9. Reference

************
Installation
************

From PyPI, you can just use the normal ``pip install`` dance:

    ``pip install hikaru``

Or if installing from source, you can install dependencies with:

    ``pip install -r requirements.txt``

...and then install from setup.py:

    ``python setup.py install``

**THIS NEEDS REVIEWING**

************
Quickstart
************

The following are the 'bread and butter' functions of hikaru.

To read Kubernetes YAML documents into hikaru Python objects:
=============================================================

For loading Kubernetes YAML documents into live hikaru Python objects, use the
``load_full_yaml()`` function:

.. code:: python

    from hikaru import load_full_yaml
    docs = load_full_yaml(path="<path to yaml file>")
    # docs is a list of different doc 'kinds' such as Pod, Deployment, etc

The objects in the resultant list will always have *kind* and *apiVersion*
attributes populat4ed. If any of the input YAML doesn't have these attributes for their
documents, hikaru can't tell what classes to build. You can then use Kubernetes YAML
property names to navigate through the Python objects.

To write Kubernetes YAML documents from hikaru Python objects:
==============================================================

You can print out the equivalent Kubernetes YAML from hikaru Python objects with the
``get_yaml()`` function:

.. code:: python

    from hikaru import get_yaml
    # assume that 'p' below is an instance of the Pod class
    print(get_yaml(p))

The output YAML will start with a 'start of document' marker (---) and then the
YAML for the hikaru objects will be printed.

To generate hikaru Python source from hikaru Python objects:
============================================================

If you want to convert your Kubernetes YAML to actual hikaru Python source code, use
the ``get_python_source()`` function:

.. code:: python

    from hikaru import get_python_source, load_full_yaml
    docs = load_full_yaml(path="<path to yaml>")
    p = docs[0]
    # when rendering the Python source, you can indicate a variable to assign
    # the created object to:
    print(get_python_source(p, assign_to='x'))

This will output a PEP8-compliant set of Python. Generation may take a short while
depending on how many deeply nested Python objects are involved.

Key Functions
*************

A good deal of the manipulations you'll perform on hikaru objects will be facilitated
by a short list of functions. These are covered in detail in the Reference section, but they will be quickly reviewed here. All of these can be imported from the 'hikaru' package.


load_full_yaml()
----------------

``load_full_yaml()`` is the main way to load Kubernetes YAML files, and the documents they
contain, into hikaru objects. ``load_full_yaml()`` returns a list of hikaru objects, each of
which represents a document in the YAML file. Each document **must** be a top-level Kubernetes object, such as Deployment, Pod, DaemonSet, etc, and each must have valid
`kind` and `apiVersion` properties-- this is how hikaru tells what root object to
instantiate.

``load_full_yaml()`` can be called three different ways to process YAML content:

.. code:: python

    # to load from a file at a known path:
    load_full_yaml(path="<path to yaml file>")
    # to load from a file-like object already opened:
    load_full_yaml(stream=f)
    # to load from a string that contains the YAML:
    load_full_yaml(yaml=x)

get_yaml()
----------

This function returns a string containing YAML that can re-create the object it is called
with. The YAML that is output is preceeded by a start of document marker (---), and the top
level object in the YAML file will be the hikaru object that is passed in. The hikaru object can be a Kubernetes document object such as Pod, Deployment, etc, but it can also be any hikaru modeling object; all will be rendered as YAML.

``load_full_yaml()`` and ``get_yaml()`` can be used to round-trip YAML through Python; it
may be a handy way to customize a Kubernetes YAML file by loading into Python, modifying it
programmatically, and then rendering it back to YAML.

get_json()
----------

This function works like ``get_yaml()`` but returns JSON that represents the object instead.
This is currently a one-way operation; there is no current ability to load a hikaru object
from JSON, but this is may change in the future.

A JSON form of a Kubernetes document may be a useful form to employ for creating a record of 
executed Kubernetes commands in a document database.

get_python_source()
-------------------

This function returns a PEP8-compliant string containing Python source code that will
re-create the object that was passed to it. By default, this code simply calls a model
class with all necessary arguments, but as there's no assignment running this code will
cause an object to be created and then immediately destroyed. If you wish to have code
that will assign the created object to a variable, use the `assign_to` keyword argument:

.. code:: python

    # assume we have a Deployment object called 'd'
    from hikaru import get_python_source
    code = get_python_source(d, assign_to="the_deployment")

This will result in code that looks something like the following:

.. code:: python

    >>> print(code)
    the_deployment = Deployment(apiVerision='v1', kind='Deployment',
                                metadata=ObjectMeta(<etc>),
                                spec=<etc>)

Code is formatted to a line length of 90 chars. This function may take a second or two
to run, depending on how many nested objects are involved in the argument to
``get_python_source()``. The code can be saved to another Python module and re-run to
recreate the original object.

get_clean_dict()
----------------

All hikaru model classes are Python dataclasses, which can automatically be rendered to 
a dict. However, the resultant dict will contain every attribute of every object, even
optional ones that weren't provided values (they will have None). The ``get_clean_dict()``
function takes that dict and prunes out all None values it contains, returning a minimal
dict that represents the state of the object. This also is currently a one-way trip, but
future releases will enable round-trips back to hikaru objects.

Models
******

Hikaru uses the same swagger file that defines the Kubernetes API as does the Python
Kubernetes client. This file contains a variety of different versions of the API. Hikaru
provides support for using each of these models as you wish.

By default, when you write:

.. code:: python

    from hikaru import *

...you automatically import all model classes from the v1 version of the API spec. An explicit way of doing this is to import directly from the v1 version model in the model subpackage:

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
hikaru model class can be used with the tools in the dataclasses module to inspect and
process both classes and class instances.

The HikaruBase class
********************

All hikaru model objects are based on the HikaruBase class, and the model objects
only add data; there are no additional behaviours. All operations that you can do
on hikaru objects are defined on the HikaruBase class.

Full documentation for the class can be found in the `Reference` section, but some of the 
key methods are discussed here.

from_yaml() (classmethod)
-------------------------

The class method ``from_yaml()`` allows you to create a populated instance instance from a supplied `ruamel.yaml.YAML` instance (this is what is used internally for loading and parsing Kubernetes YAML). So you can use ``from_yaml()`` to manually load a specific hikaru class:

.. code:: python

    from ruamel.yaml import YAML
    from hikaru import Pod
    yaml = YAML()
    f = open("<path to yaml containing a pod>", "r")
    doc = yaml.load(f)
    p = Pod.from_yaml(doc)
    assert isinstance(p, Pod)

While ``load_full_yaml()`` relies on `apiVersion` and `kind` properties in the YAML to
determine what class to instantiate and populate, ``from_yaml()`` assumes you are invoking
it on a class that matches the kind of thing you want to load from the YAML. This allows
you to actually load any hikaru object from YAML, even ones that are fragments of
larger Kubernetes documents. For instance, if you had a YAML file that only contained
the definition of a container (no `apiVersion` or `kind`), ``from_yaml()`` would still
allow you to load it:

.. code:: python

    from ruamel.yaml import YAML
    from hikaru import Container
    yaml = YAML()
    f = open("<path to yaml containing a container>", "r")
    doc = yaml.load(f)
    c = Container.from_yaml(doc)
    assert isinstance(c, Container)

Note that loading fragments in this way requires the fragment to appear to be the
top-level YAML object in the file; there can be no indentation of the initial lines.

as_python_source()
------------------

HikaruBase can render itself as Python source with ``as_python_source()`` that will
re-create the state of the object. The source is unformatted with respect to PEP8, and may
in fact be quite difficult to read. However, it is legal Python and will execute properly.
It is better to use the ``get_python_source()`` function for this, as it will also run the
PEP8 formatter to make the code more readable.

Support for ==
--------------

Instances of models can be checked for equality using '=='. HikaruBase understands how to
inspect subclasses and recursivly ensure that all field values, dict keys, list entries, etc
are the same.

dup()
-----

Any HikaruBase instance can generate a duplicate of itself, a deep copy. This is especially
useful in cases where pre-made components are loaded from a library and a particular
component is used mutliple times within the same containing object, but where you may wish
to tweak the values in each use. Since these are all object references, tweaking the values
in one place will be seen in another unless a full copy is used in each location so the same group of objects are all being operated on from different places.

find_by_name()
--------------

As HikaruBase objects are populated via processing YAML or by being created with Python
code, an internal search catalog is created on each object that provides assistance in
searching through the object hierarchy for specific fields or nested objects. This provides
significant assistance in constructing automated reviewing tools that can locate and
highlight specific objects to ensure consistency of usage and compliance to standards.

This catalog is used by the ``find_by_name()`` method, which returns a list of CatalogEntry
objects (named tuples) that describe all attributes and their location in the model that satisfy the query arguments to the method.

The simplest use of this method is to supply a name to find; in this case, ``find_by_name()``
will return every attribute called name wherever it is in the model. For example, here is
the result when querying for 'name' against a Pod (p) in one of hikaru's test cases:

.. code:: python

    >>> for ce in p.find_by_name("name"):
    ...     print(ce)
    ... 
    CatalogEntry(cls='str', attrname='name', path=['metadata', 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'lifecycle', 'postStart', 'httpGet', 'httpHeaders', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'env', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'env', 1, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'envFrom', 0, 'configMapRef', 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'envFrom', 0, 'secretRef', 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'volumeDevices', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'containers', 1, 'volumeMounts', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'imagePullSecrets', 0, 'name'])
    CatalogEntry(cls='str', attrname='name', path=['spec', 'imagePullSecrets', 1, 'name'])

As you can see, the field occurs in quite a lot of places at different depths of the object
hierarchy, and this is only a Pod with two containers, so the result could be a lot more
voluminous. We can establish a search scope with ``find_by_name()`` by using the ``following``
keyword argument. This argument tells the function to return CatalogEntries for each instance
of the named attribute **if** that attribute comes after one or more other attributes in
the path to attribute we want. For example, we can narrow the search down to only ones where
'name' comes somewhere within the containers:

.. code:: python

    >>> for ce in p.find_by_name("name", following="containers"):
    ...     print(ce)
    ... 
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 0, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'lifecycle', 'postStart', 'httpGet', 'httpHeaders', 0, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'env', 0, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'env', 1, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'envFrom', 0, 'configMapRef', 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'envFrom', 0, 'secretRef', 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'volumeDevices', 0, 'name'])
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'volumeMounts', 0, 'name'])

That gets rid of metadata and imagePullSecrets, but that's still too much. Say we only care about
the second container, and under that we just want the postStart:

.. code:: python

    >>> for ce in p.find_by_name("name", following="containers.1.postStart"):
    ...     print(ce)
    ... 
    CatalogEntry(cls=<class 'str'>, attrname='name', path=['spec', 'containers', 1, 'lifecycle', 'postStart', 'httpGet', 'httpHeaders', 0, 'name'])

Now we only have one entry in the result. In this case, although we could have used just used 'lifecycle', we
want to illustrate a couple of things:

  - First, notice that we can use a series of attributes in the ``following`` expression, separated by '.'.
  - Second, notice that the attributes don't have to be directly sequential as you tunnel into an object.
  - Third, note that we can use integers as indexes into a list of objects; we will only search under that index.

The attributes of a CatalogEntry are:

  - cls: the class object for the value of the item that was named
  - attrname: the name of the attribute found
  - path: a list of strings that will take you from object where you did the search to the located item

Finally, it's worth noting that the ``following`` expression can either be a '.' separated string,
or a list of strings and ints.

object_at_path()
----------------

The ``object_at_path()`` method works with the ``path`` attribute of the returned 
CatalogEntry object. By passing the the path into ``object_at_path()``, you can access
the actual value of the object stored there. This gives you the means to inspect the 
object that you've located.

repopulate_catalog()
--------------------

Normally, the catalogs are created automatically when you create an object in Python or when
you load an instance from YAML. However, once you've loaded the instance, you are free to
modify the existing entries, add additional ones, or even delete existing pieces. Such
operations will make the catalog inaccurate if you intend to use ``find_by_name()`` again.
To bring the catalog up to date, invoke ``repopulate_catalog()``, and all catalogs from
the object where you invoked the method on down with have their catalogs recomputed and
made up to date.

Issues, Changes and Limitations
*******************************

Python reserved words
---------------------

In the Kubernetes swagger file, there are some property names that are Python reserved words:
**except**, **continue**, and **from**. Since Python won't allow these words as attribute names,
they have had an '_' appended to them for use within Python, but get translated back to their
original versions when going back to YAML. So within Python, you'll use **except_**, **continue_**, and **from_**.

Skipped API groups
------------------

To make type annotations on Python dataclasses, the type needs to be defined before the annotation
can be created. However, the **apiextensions** group in the API file contains a reference cycle
in terms of the defined types, and hence a topological sort to determine the order of writing
classes for these objects isn't possible. Therefore, there is currently no support for the 
objects defined in the ``apiextensions`` group in hikaru. Solutions for this problem are being
considered.

Long run times for getting formatted Python code
------------------------------------------------

Hikaru uses the ``autopep`` package to reformat generated code to be PEP8 compliant. However,
this package apparently runs into some issues with the kinds of deeply nested object instantiation
that is typical in making Python source for hikaru objects from YAML, and can take a second or
two to return the formatted code. Nothing is wrong, just know that this operation can take longer
than you may expect.


Reference
*********
