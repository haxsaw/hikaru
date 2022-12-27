********************
The HikaruBase class
********************

All Hikaru model objects are based on the HikaruBase class. Most Hikaru operations that you can do
on Hikaru model objects are defined on the HikaruBase class. Derived classes will support class-specific
methods as defined by the underlying Kubernetes API.

:ref:`Full documentation for the class<HikaruBase doc>` can be found in the
:ref:`Reference` section, but some of the key methods are discussed here.

from_yaml()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.from_yaml>`

The class method ``from_yaml()`` allows you to create a populated instance
from a supplied `ruamel.yaml.YAML` instance (this is what is used internally for
loading and parsing Kubernetes YAML). So you can use ``from_yaml()`` to manually
load a specific Hikaru class:

.. code:: python

    from ruamel.yaml import YAML
    from hikaru.model.rel_1_21 import Pod
    yaml = YAML()
    f = open("<path to yaml file containing a pod>", "r")
    doc = yaml.load(f)
    p = Pod.from_yaml(doc)
    assert isinstance(p, Pod)

While ``load_full_yaml()`` relies on `apiVersion` and `kind` properties in the YAML to
determine what class to instantiate and populate, ``from_yaml()`` assumes you are invoking
it on a class that matches the kind of thing you want to load from the YAML. This allows
you to actually load any Hikaru object from YAML, even ones that are fragments of
larger Kubernetes documents. For instance, if you had a YAML file that only contained
the definition of a container (no `apiVersion` or `kind`), ``from_yaml()`` would still
allow you to load it:

.. code:: python

    from ruamel.yaml import YAML
    from hikaru.model.rel_1_21 import Container
    yaml = YAML()
    f = open("<path to yaml file containing a container>", "r")
    doc = yaml.load(f)
    c = Container.from_yaml(doc)
    assert isinstance(c, Container)

Note that loading fragments in this way requires the fragment to appear to be the
top-level YAML object in the file; there can be no indentation of the initial lines.

You can use the ``get_processors()`` function to acquire a list of input YAML dicts
to pass into ``from_yaml()``:

.. code:: python

    from hikaru import get_processors
    from hikaru.model.rel_1_21 import Container
    docs = get_processors(path="<path to Container yaml file>")
    c = Container.from_yaml(docs[0])
    assert isinstance(c, Container)

get_empty_instance()
********************

:py:meth:`Documentation<hikaru.HikaruBase.get_empty_instance>`

This classmethod provides you an empty instance of the class on which you invoke it.
Otherwise, you have to ensure that you provide the correct required number of the non-
optional parameters to the usual object creation call. This method takes care of that
for you, giving you an empty instance that you can then populate as you wish. This includes
any contained objects and their required parameters.

as_python_source()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.as_python_source>`

HikaruBase subclasses can render themselves as Python source with ``as_python_source()``.
The rendered code will
re-create the state of the original object. The source is unformatted with respect to PEP8,
and may in fact be quite difficult to read. However, it is legal Python and will execute properly.
It is better to use the ``get_python_source()`` function for this, as it will
also run a PEP8 formatter to make the code more readable.

Support for ==
*************************

Instances of models can be checked for equality using '=='. HikaruBase understands how to
inspect subclasses and recursively ensure that all field values, dict keys, list entries,
etc are the same.

dup()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.dup>`

Any HikaruBase instance can generate a duplicate of itself, a deep copy. This is especially
useful in cases where pre-made components are loaded from a library and a particular
component is used multiple times within the same containing object but where you may wish
to tweak the values in each use. Since these are all object references, tweaking the values
in one place will be seen in another unless a full copy is used in each location so the
same group of objects are all being operated on from different places.

find_by_name()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.find_by_name>`

As HikaruBase instance objects are populated via processing YAML or by being created with Python
code, an internal search catalog is created on each object that provides assistance in
searching through the object hierarchy for specific fields or nested objects. This provides
significant assistance in constructing automated reviewing tools that can locate and
highlight specific objects to ensure consistency of usage and compliance to standards.

This catalog is used by the ``find_by_name()`` method, which returns a list of
:ref:`CatalogEntry<CatalogEntry doc>` objects (named tuples) that describe all attributes
and their location in the model that satisfy the query arguments to the method.

The simplest use of this method is to supply a name to find; in this case, ``find_by_name()``
will return every attribute called 'name' wherever it is in the model. For example, here is
the result when querying for the 'name' attribute against a Pod (p) in one of Hikaru's test
cases:

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

Now we only have one entry in the result. In this case, although we could have used just
used 'lifecycle' as the value of ``following``, we want to illustrate a couple of things:

  - First, notice that we can use a series of attributes in the ``following`` expression, separated by '.'.
  - Second, notice that the attributes don't have to be directly sequential as you tunnel into an object.
  - Third, note that we can use integers as indexes into a list of objects; we will only search under that index.

The ``following`` expression can either be a '.' separated string, or a list of strings
and ints.

The attributes of the returned CatalogEntry namedtuples are:

  - cls: the class object for the value of the item that was named
  - attrname: the name of the attribute found
  - path: a list of strings (or integer indices) that will take you from object where you did the search to the located item

get_type_warnings()
*******************

:py:meth:`Documentation<hikaru.HikaruBase.get_type_warnings>`

Although Hikaru's annotations will aid you in avoiding supplying the wrong types for 
object parameter values, or from setting an attribute directly with an item of the wrong type,
it can only aid you with warnings and advisories-- Python still let's you put anything anywhere
you want, and not until run time will you find you stuck an ObjectMeta where a PodSpec belongs.
However, you can check the alignment of contained data against the type annotations of the
attributes with the ``get_type_warnings()`` method.

This method examines every field of an object hierarchy and compares the types of the values
contained there with the types in the annotations. If there are any discrepancies, they are
collected into a list of :ref:`TypeWarning<TypeWarning doc>` nametuples are returned to the
caller. TypeWarnings are similar in structure to CatalogEntries, but have a slightly different
interpretation:

  - cls: is the class that holds the attribute that is of the wrong type
  - attrname: the name of the attribute on an instance of cls
  - path: list of strings that names the attribute path from the object where get_type_warnings() was called to the incorrect attribute
  - warning: a string that contains a message describing the type error that was found

If the returned list is empty, then all types are correct. However, there may be other usage
conventions are make an object incorrect, for example supplying three different
sub-objects
when you are supposed to choose only one. ``get_type_warnings()`` doesn't find those kinds
of errors, just when types are incorrect.

diff()
******

:py:meth:`Documentation<hikaru.HikaruBase.diff>`

The ``diff()`` method provides you a way to determine where two different Hikaru objects differ.
This can be handy when two objects that are supposed to be equal (==) aren't, and it is
difficult to determine where they are different.

The ``diff()`` method takes another Hikaru object as an argument and recursively compares all
attributes of each object. If a difference it found, a :ref:`DiffDetail<DiffDetail doc>` dataclass
is created and returned in a list. The DiffDetail includes the following fields:

  - diff_type: is a :ref:`DiffDetail<DiffType doc>` enum specifying the type of change (see below)
  - cls: is the class where the difference was found
  - formatted_path: is a string like ``Pod.spec.containers[0]`` specifying what changed
  - path: a list of strings that show how to reach the attribute where the difference was found. e.g. ``['spec', 'containers', 0]``
  - report: a string that describes the difference found
  - value: the value of the changed attribute in self
  - other_value: the value of the changed attribute in the object passed to ``diff()`` as a parameter

If the list is empty, then the two objects have no differences.

The DiffType enum has the following possible values:

  - DiffType.ADDED: an attribute was changed from None to a non-None value or a dictionary key was added.
  - DiffType.REMOVED: an attribute was changed from a non-None value to None or a dictionary key was removed.
  - DiffType.VALUE_CHANGED: the value of an attribute, dictionary item, or list item changed but the type didn't change
  - DiffType.TYPE_CHANGED: the Python type of an attribute, dictionary item, or list item changed.
  - DiffType.LIST_LENGTH_CHANGED: the length of a list changed. This is the only DiffType that will be issued for the list. No DiffTypes will be issued for individual list elements.
  - DiffType.INCOMPATIBLE_DIFF: this is returned when calling ``a.diff(b)`` and ``a`` and ``b`` have different types. This is not returned when calling ``a.diff(b)`` and an attribute like ``a.c`` has a different type than ``b.c``. (In that case a DiffType.TYPE_CHANGED is used.)

object_at_path()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.object_at_path>`

The ``object_at_path()`` method works with the ``path`` attribute of the returned 
CatalogEntry object. By passing the the path into ``object_at_path()``, you can access
the actual value of the object stored there. This gives you the means to inspect the 
object that you've located.

repopulate_catalog()
*************************

:py:meth:`Documentation<hikaru.HikaruBase.repopulate_catalog>`

Normally, the catalogs are created automatically when you create an object in Python or when
you load an instance from YAML. However, once you've loaded the instance, you are free to
modify the existing entries, add additional ones, or even delete existing pieces. Such
operations will make the catalog inaccurate if you intend to use ``find_by_name()`` again.
To bring the catalog up to date, invoke ``repopulate_catalog()``, and all catalogs from
the object where you invoked the method on down with have their catalogs recomputed and
made up to date.
