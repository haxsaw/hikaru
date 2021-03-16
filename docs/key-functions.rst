*************
Key Functions
*************

A good deal of the manipulations you'll perform on hikaru objects will be facilitated
by a short list of functions. These are covered in detail in the :ref:`Reference`
section, but they will be quickly reviewed here. All of these can be imported from the
'hikaru' package.


load_full_yaml()
****************

``load_full_yaml()`` is the main way to load Kubernetes YAML files and the documents they
contain into hikaru objects. ``load_full_yaml()`` returns a list of hikaru objects, each
of which represents a document in the YAML file. Each document **must** be a top-level
Kubernetes object, such as Deployment, Pod, DaemonSet, etc, and each must have valid
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

get_processors()
****************

This function takes the same arguments as ``load_full_yaml()`` but instead of
returning a list of HikaruBase subclasses, it returns a list of dicts containing
the parsed out YAML. This would then normally be processed by the machinery in
HikaruBase to create objects, and individual elements can be used with the
``from_yaml()`` method of HikaruBase subclasses to populate individual document
hierarchies, but you are free to use these as you wish.

get_yaml()
**********

This function returns a string containing YAML that can re-create the object it is called
with. The YAML that is output is preceeded by a start of document marker (---), and the top
level object in the YAML file will be the hikaru object that is passed in. The
hikaru object can be a Kubernetes document object such as Pod, Deployment, etc,
but it can also be any hikaru modeling object; all will be rendered as YAML.

``load_full_yaml()`` and ``get_yaml()`` can be used to round-trip YAML through Python; it
may be a handy way to customize a Kubernetes YAML file by loading into Python, modifying it
programmatically, and then rendering it back to YAML.

get_json()
**********

This function works like ``get_yaml()`` but returns JSON that represents the object instead.
This is currently a one-way operation; there is no current ability to load a hikaru object
from JSON, but this is may change in the future.

A JSON form of a Kubernetes document may be a useful form to employ for creating a record of 
executed Kubernetes commands in a document database.

get_python_source()
*******************

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
****************

All hikaru model classes are Python dataclasses, which can automatically be rendered to 
a dict. However, the resultant dict will contain every attribute of every object, even
optional ones that weren't provided values (they will have None). The ``get_clean_dict()``
function takes that dict and prunes out all None values it contains, returning a minimal
dict that represents the state of the object. This also is currently a one-way trip, but
future releases will enable round-trips back to hikaru objects.
