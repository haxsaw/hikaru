
.. |travis| image:: https://travis-ci.com/haxsaw/hikaru.svg?branch=dev
    :target: https://travis-ci.com/haxsaw/hikaru

.. |license| image:: https://img.shields.io/github/license/haxsaw/hikaru
   :alt: GitHub license   :target: https://github.com/haxsaw/hikaru/blob/main/LICENSE

.. |versions| image:: https://img.shields.io/pypi/pyversions/hikaru
   :alt: PyPI - Python Version

.. |coverage| image:: https://codecov.io/gh/haxsaw/hikaru/branch/main/graph/badge.svg?token=QOFGNVHGNP
   :target: https://codecov.io/gh/haxsaw/hikaru

======
Hikaru
======

|travis|   |license|   |versions|   |coverage|

**Full documentation at: https://hikaru.readthedocs.io/en/latest/index.html**

Hikaru is a tool that provides you the ability to easily shift between
YAML, Python objects/source, and JSON representations of your Kubernetes config
files, provides assistance in authoring these files in Python,
opens up options in how you can assemble and customise the files, and even
provides some programmatic tools for inspecting large, complex files to
enable automation of policy and security compliance.

From Python
~~~~~~~~~~~

Hikaru uses type-annotated Python dataclasses to represent each of the
kinds of objects defined in the Kubernetes API, so when used with an
IDE that understands Python type annotations, Hikaru enables the IDE to
provide the user direct assistance as to what parameters are available,
what type each parameter must be, and which parameters are optional. Assembled
Hikaru object can be rendered into YAML that can be processed by regular
Kubernetes tools.

From YAML
~~~~~~~~~

But you don’t have to start with authoring Python: you can use Hikaru to
parse Kubernetes YAML into these same Python objects, at which point you
can inspect the created objects, modify them and re-generate new YAML,
or even have Hikaru emit Python source
code that will re-create the same structure but from the Python
interface.

From JSON
~~~~~~~~~

You can also process JSON or Python dict representations of Kubernetes configs
into the corresponding Python objects

To YAML, Python, or JSON
~~~~~~~~~~~~~~~~~~~~~~~~

Hikaru can output a Python Kubernetes object as Python source code,
YAML, JSON, or a Python dict, and go back to any of these representations, allowing you
to shift easily between representational formats for various purposes.

Alternative to templating for customisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using Hikaru, you can assemble Kubernetes objects using previously
defined libraries of objects in Python, craft replacements procedurally, or
even tweak the values of an existing object and turn it back into YAML.

Build models for uses other than controlling systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use Hikaru in the process of issuing instructions to Kubernetes,
but the same Hikaru models can be used as high-fidelity replicas of the
YAML for other processes as well.

Type checking, diffing, and inspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hikaru supports a number of other operations on the Python objects it defines. For
example, you can check the types of all attributes in a config against the defined
types for each attribute, you can diff two configs to see where they aren't the same,
and you can search through a config for specific values and contained objects.

API Coverage
~~~~~~~~~~~~

Currently, Hikaru supports all objects in the OpenAPI swagger spec for
the Kubernetes API except those in the ‘apiextensions’ group. There are
recusively defined objects in that group which can neither be
topologically sorted or represented by Python dataclasses, so an
alternative for those objects is being investigated. But all other
objects in the swagger file are available, as well as version v1 through
v2beta2 of the API’s objects.

Additionally, the Kubernetes Python client includes a test that assumes
the availability of support for a ‘List’ kind, however the swagger file
contains no support for a List object.

Usage
-----

To create Python objects from a Kubernetes YAML source, use
``load_full_yaml()``:

.. code:: python

   from hikaru import load_full_yaml  # or just 'from hikaru import *'

   docs = load_full_yaml(stream=open("test.yaml", "r"))
   p = docs[0]

``load_full_yaml()`` loads every Kubernetes YAML document in a YAML file and returns
a list of the resulting Hikaru objects found. You can then use the YAML
property names to navigate the resulting object. If you assert that an
object is of a known object type, your IDE can provide you assistance in
navigation:

.. code:: python

   from hikaru import Pod
   assert isinstance(p, Pod)
   print(p.metadata.labels["lab2"])
   print(p.spec.containers[0].ports[0].containerPort)
   for k, v in p.metadata.labels.items():
       print(f"key:{k} value:{v}")
       

You can create Kubernetes objects in Python:

.. code:: python

   from hikaru import Pod, PodSpec, Container, ObjectMeta
   x = Pod(apiVersion='v1', kind='Pod',
           metadata=ObjectMeta(name='hello-kiamol-3'),
           spec=PodSpec(
               containers=[Container(name='web', image='kiamol/ch02-hello-kiamol') ]
                )
       )
       

…and then render it in YAML:

.. code:: python

   from hikaru import get_yaml
   print(get_yaml(x))

…which yields:

.. code:: yaml

   ---
   apiVersion: v1
   kind: Pod
   metadata:
     name: hello-kiamol-3
   spec:
     containers:
       - name: web
         image: kiamol/ch02-hello-kiamol

If you use Hikaru to parse this back in as Python objects, you can then
ask Hikaru to output Python source code that will re-create it (thus
providing a migration path):

.. code:: python

   from hikaru import get_python_source, load_full_yaml
   docs = load_full_yaml(path="to/the/above.yaml")
   print(get_python_source(docs[0], assign_to='x', style="black"))

...which results in:

.. code:: python

    x = Pod(
        apiVersion="v1",
        kind="Pod",
        metadata=ObjectMeta(name="hello-kiamol-3"),
        spec=PodSpec(containers=[Container(name="web", image="kiamol/ch02-hello-kiamol")]),
    )

It is entirely possible to load YAML into Python, tailor it, and then
send it back to YAML; Hikaru can round-trip YAML through Python and
then back to the equivalent YAML.

The pieces of complex objects can be created separately and even stored
in a standard components library module for assembly later, or returned as the
value of a factory function, as opposed to using a templating system to piece
text files together:

.. code:: python

   from component_lib import web_container, lb_container
   from hikaru.model import Pod, ObjectMeta, PodSpec
   # make an ObjectMeta instance here called "om"
   p = Pod(apiVersion="v1", kind="Pod",
           metadata=om,
           spec=PodSpec(containers=[web_container, lb_container])
           )

You can also transform Hikaru objects into Python dicts:

.. code:: python

    from pprint import pprint
    pprint(get_clean_dict(x))

...which yields:

.. code:: python

    {'apiVersion': 'v1',
     'kind': 'Pod',
     'metadata': {'name': 'hello-kiamol-3'},
     'spec': {'containers': [{'image': 'kiamol/ch02-hello-kiamol', 'name': 'web'}]}}

...and go back into Hikaru objects. You can also render Hikaru objects as
JSON:

.. code:: python

    from hikaru import *
    print(get_json(x))

...which outputs the similar:

.. code:: json

    {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "hello-kiamol-3"}, "spec": {"containers": [{"name": "web", "image": "kiamol/ch02-hello-kiamol"}]}}

Hikaru lets you go from JSON back to Hikaru objects as well.

Hikaru objects can be tested for equivalence with ‘==’, and you can also
easily create deep copies of entire object structures with dup(). This
latter is useful in cases where you have a component that you want to
use multiple times in a model but need it slightly tweaked in each use;
a shared instance can’t have different values at each use, so it’s easy
to make a copy that can be customised in isolation.

Finally, every Hikaru object that holds other properties and objects
have methods that allow you to search the entire collection of objects.
This lets you find various objects of interest for review and checking
against policies and conventions. For example, if we had a Pod ‘p’ that was
pulled in with load_full_yaml(), we could examine all of the Container objects
with:

.. code:: python

   containers = p.find_by_name("containers")
   for c in containers:
       # check what you want...
       

Or you can get all of the ExecAction object (the value of ‘exec’
properties) that are part the second container’s lifecycle’s httpGet
property like so:

.. code:: python

   execs = p.find_by_name("exec", following='containers.1.lifecycle.httpGet')

These queries result in a list of ``CatalogEntry`` objects, which are
named tuples that provide the path to the found element. You can acquire
the actual element for inspection with the ``object_at_path()`` method:

.. code:: python

   o = p.object_at_path(execs[0].path)

This makes it easy to scan for specific items in a config under
automated control.

Future work
~~~~~~~~~~~

Since both the classes of Hikaru and those in the official
Python Kubernetes client are generated from the same swagger file, if a
means to determine a mapping between the two can be established it
should be possible to integrate these Python classes directly into the
Kubernetes client for actioning on a Kubernetes cluster.

About
~~~~~

Hikaru is Mr. Sulu’s first name, a famed fictional helmsman.
