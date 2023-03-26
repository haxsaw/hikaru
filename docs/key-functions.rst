*************
Key Functions
*************

A good deal of the manipulations you'll perform on Hikaru objects will be facilitated
by a short list of functions. These are covered in detail in the :ref:`Reference`
section, but they will be quickly reviewed here. All of these can be imported from the
'hikaru' package.


load_full_yaml()
****************

:ref:`Documentation<load_full_yaml doc>`

``load_full_yaml()`` is the main way to load Kubernetes YAML files and the documents they
contain into Hikaru objects. ``load_full_yaml()`` returns a list of Hikaru objects, each
of which represents a document in the YAML file. Each document **must** be a top-level
Kubernetes object, such as Deployment, Pod, DaemonSet, etc, and each must have valid
`kind` and `apiVersion` properties-- this is how Hikaru tells what root object to
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
**********

:ref:`Documentation<get_yaml doc>`

This function returns a string containing YAML that can re-create the object it is called
with. The YAML that is output is preceded by a start of document marker (---), and the top
level object in the YAML file will be the Hikaru object that is passed in. The
Hikaru object can be a Kubernetes document object such as Pod, Deployment, etc,
but it can also be any Hikaru modeling object; all will be rendered as YAML.

``load_full_yaml()`` and ``get_yaml()`` can be used to round-trip YAML through Python; it
may be a handy way to customize a Kubernetes YAML file by loading into Python, modifying it
programmatically, and then rendering it back to YAML.

get_json()
**********

:ref:`Documentation<get_json doc>`

This function works like ``get_yaml()`` but returns JSON that represents the object instead.

A JSON form of a Kubernetes document may be a useful form to employ for creating a record of 
executed Kubernetes commands in a document database.

from_json()
***********

:ref:`Documentation<from_json doc>`

This function is the inverse of ``get_json()``; it takes a string of JSON that was output
by ``get_json()`` and returns a HikaruBase subclass that has been filled with the JSON's
content.

If processing JSON that represents a top-level Kubernetes object (that is, there are `apiVersion`
and `kind` keys), then ``from_json()`` is able to work out which class needs to be
instantiated and populated. If this is any other Kubernetes object in JSON, then you must
supply the optional ``cls`` argument informing ``from_json()`` which class to instantiate
and fill.

get_clean_dict()
****************

:ref:`Documentation<get_clean_dict doc>`

All Hikaru model classes are Python dataclasses, which can automatically be rendered to
a dict. However, the resultant dict will contain every attribute of every object, even
optional ones that weren't provided values (they will have None). The ``get_clean_dict()``
function takes that dict and prunes out all None values it contains, returning a minimal
dict that represents the state of the object.

from_dict()
***********

:ref:`Documentation<from_dict doc>`

This function is the inverse of ``get_clean_dict()``; it takes a Python dict produced by
``get_clean_dict()`` and returns a HikaruBase subclass that has been
filled with the dict's content.

If processing a top-level Kubernetes document (that is, there are `apiVersion` and `kind` keys),
``from_dict()`` is able to work out the proper class to instantiate and fill. If the dict
is of another Kubernetes object that doesn't have these keys, you can supply
the ``cls`` keyword argument to indicate what class should be instantiated and filled.

get_python_source()
*******************

:ref:`Documentation<get_python_source doc>`

This function returns a PEP8-compliant string containing Python source code that will
re-create the object that was passed to it. By default, the resultant code simply calls a model
class with all necessary arguments, but as there's no assignment in the generated code running it will
cause an object to be created and then immediately destroyed. If you wish to have code
that will assign the created object to a variable, use the `assign_to` keyword argument:

.. code:: python

    # assume we have a Deployment object called 'd'
    from hikaru import get_python_source
    code = get_python_source(d, assign_to="the_deployment")

This will result in code that looks something like the following:

.. code:: python

    >>> print(code)
    the_deployment = Deployment(apiVersion='v1', kind='Deployment', metadata=ObjectMeta(
        name='wibble'), spec=DeploymentSpec(selector=LabelSelector(), template=PodTemplateSpec()))

The above code is formatted to the default style, ``autopep8``. If you would rather have a more vertically oriented style, use ``black`` for the value of the style argument:

.. code:: python

    >>> print(get_python_source(d, assign_to="the_deployment", style='black'))
    the_deployment = Deployment(
        apiVersion="v1",
        kind="Deployment",
        metadata=ObjectMeta(
            name="wibble",
            annotations={},
            finalizers=[],
            labels={},
            managedFields=[],
            ownerReferences=[],
        ),
        spec=DeploymentSpec(
            selector=LabelSelector(matchExpressions=[], matchLabels={}),
            template=PodTemplateSpec(),
        ),
    )

In general, ``autopep8`` will work harder to fill lines, while ``black`` will generally
write things on different lines unless it can put all parameters on a single line.

Code is formatted to a line length of 88 chars. This function may take a second or two
to run, depending on how many nested objects are involved in the argument to
``get_python_source()``. The code can be saved to another Python module and re-run to
recreate the original object.

**NOTE:** There are no import statements output as part of the generated code; you have
to supply these yourself. This is because it's not clear if this will be added to another
string of generated code. You can satisfy all function import requirements by
prepending the line:

.. code:: python

    from hikaru import *

...and the release model classes by prepending a line that imports everything from your
desired release:

.. code:: python

    from hikaru.model.release_1_22 import *

...before the generated code as appropriate.

process_api_version()
*********************

:ref:`Documentation<process_api_version doc>`

The ``apiVersion`` attribute of any top-level Kubernetes object may have encoded
both the object group and the version of the API that the object is to respect.
This function takes the value of this attribute and splits it out into its parts,
the API object group and the version. This is returned as a 2-tuple of strings,
(group, version).

get_processors()
****************

:ref:`Documentation<get_processors doc>`

This function takes the same arguments as ``load_full_yaml()`` but instead of
returning a list of HikaruBase subclasses, it returns a list of dict-like objects containing
the parsed out YAML. This would then normally be processed by the machinery in
HikaruBase to create objects, and individual elements can be used with the
``from_yaml()`` method of HikaruBase subclasses to populate individual document
hierarchies, but you are free to use these as you wish.

get_default_release()
*********************

:ref:`Documentation<get_default_release doc>`

Returns a string that is the name of the default release that Hikaru will use when creating
objects from YAML, JSON, or a dict. The release name returned will be the release **set for the calling thread**
(if there is one), or else it will be the global default release for
the entire process. A more thorough discussion of using this function can be found
:ref:`here<Kubernetes API Releases and Versions>`.

set_default_release()
*********************

:ref:`Documentation<set_default_release doc>`

Sets the default string name of the release for Hikaru to use when creating objects from YAML, JSON or a dict.
This value is set only for the calling thread, hence each thread can have its own default
release. The supplied string must be the name of one of the release packages under ``hikaru.model``.
A more thorough discussion of using this function can be found
:ref:`here<Kubernetes API Releases and Versions>`.

set_global_default_release()
****************************

:ref:`Documentation<set_global_default_release doc>`

Sets the default string name of the release to use for the entire program; this supplies a fallback
release name to use in case an individual thread doesn't set a release name for itself. The supplied
string must be the name of a release package under ``hikaru.model``.
A more thorough discussion of using this function can be found
:ref:`here<Kubernetes API Releases and Versions>`.

get_version_kind_class()
************************

:ref:`Documentation<get_version_kind_class doc>`

Returns the class object that will be used by Hikaru when it encounters the specified version and
kind values.

register_version_kind_class()
*****************************

:ref:`Documentation<register_version_kind_class doc>`

Registers the class to create when Hikaru encounters the specified version and kind
values.
Use of this function is part of advanced Hikaru usage, which is documented
:ref:`here<Advanced Hikaru: Defining Your Own Classes>`.

rollback_cm()
*************

:ref:`Documentation<rollback_cm doc>`

When using an instance of a HikaruDocumentBase subclass as a context manager,
wrapping it with this function in the ``with`` statement sets the object so that it
can roll back to its original state if an error occurs in the ``with`` block.

register_crd_class()
********************

:ref:`Documentation<register_crd_class doc>`

Registers a new user-created custom resource definition class with Hikaru. This is similar to 
``registers_version_kind_class()``, but captures additional data needed for supporting user
created resources. This function registers the class with Hikaru's runtime system, which allows
Hikaru to create instances of the class when Kubernetes sends a message for this resource,
as well as establishing the appropriate watch mechanisms for supporting Watchers on CRDs.

get_crd_schema()
****************

:ref:`Documentaton<get_crd_schema doc>`

Inspects a ``HikaruDocumentBase`` subclass and generates a ``JSONSchemaProps`` object that contains
the OpenAPI schema for the supplied subclass. This can then be viewed if desired, but the primary
use for the returned schema is to supply it to a ``CustomResourceDefinition`` object to define
the subclass as a CRD to Kubernetes. You can read more about creating CRDs 
:ref:`here<Hikaru CRD Support>`.

