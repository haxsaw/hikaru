
.. |travis| image:: https://travis-ci.com/haxsaw/hikaru.svg?branch=dev
    :target: https://travis-ci.com/haxsaw/hikaru

.. |license| image:: https://img.shields.io/github/license/haxsaw/hikaru
   :alt: GitHub license   :target: https://github.com/haxsaw/hikaru/blob/main/LICENSE

.. |versions| image:: https://img.shields.io/pypi/pyversions/hikaru
   :alt: PyPI - Python Version

.. |coverage| image:: https://codecov.io/gh/haxsaw/hikaru/branch/dev/graph/badge.svg?token=QOFGNVHGNP
   :target: https://codecov.io/gh/haxsaw/hikaru
   
.. |logo| image:: hikaru-logo.png
   :alt: Hikaru

|logo|


Version 0.8.1b

|travis|   |license|   |versions|   |coverage|

`Try it: see Hikaru convert your K8s YAML <http://www.incisivetech.co.uk/try-hikaru.html>`_

`Release notes <https://github.com/haxsaw/hikaru/blob/main/release_notes.rst>`_

`Full documentation at Read the Docs <https://hikaru.readthedocs.io/en/latest/index.html>`_

Hikaru is a tool that provides you the ability to easily shift between
YAML, Python objects/source, and JSON representations of your Kubernetes config
files. It provides assistance in authoring these files in Python,
opens up options in how you can assemble and customise the files, and 
provides some programmatic tools for inspecting large, complex files to
enable automation of policy and security compliance.

Additionally, Hikaru allows you to use its K8s model objects to interact with Kubernetes,
directing it to create, modify, and delete resources.

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

Supports multiple versions of Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hikaru allows you to use multiple releases of the Kubernetes client, providing
appropriate bindings/methods/attributes for every object in each version of a
release.

Direct Kubernetes via CRUD or low-level methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use Hikaru objects to interact with a Kubernetes system. Hikaru wraps the Kubernetes
Python client and maps API operations on to the Hikaru model they involve. For example, you
can now create a Pod directly from a Pod object. Hikaru supports a higher-level CRUD-style
set of methods as well as all the operations defined in the Swagger API specification.

Hikaru can work with any Kubernetes-compliant system such as `K3s <https://k3s.io/>`_
and `minikube <https://minikube.sigs.k8s.io/docs/>`_.

Monitor Kubernetes activities with watches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hikaru provides an abstraction on over the K8s `watch` APIs, which allow you to easily
create code that receives events for all activites carried out in your K8s cluster on
a per-kind basis. Or, you can create a watch container that multiplexes the output
from individual watches into a single stream.

Integrate your own subclasses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can not only in create your own subclasses of Hikaru document classes for your own
use, but you can also register these classes with Hikaru and it will make instances
of your classes when Hikaru encounters the relevant ``apiVersion`` and ``kind``
values. So for example, you can create your own ``MyPod`` subclass of ``Pod``, and
Hikaru will instantiate your subclass when reading Pod YAML.

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

Type checking, diffing, merging, and inspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hikaru supports a number of other operations on the Python objects it defines. For
example, you can check the types of all attributes in a config against the defined
types for each attribute, you can diff two configs to see where they aren't the same,
and you can search through a config for specific values and contained objects.

API coverage
~~~~~~~~~~~~

Hikaru supports all objects in the OpenAPI swagger spec for
the Kubernetes API **v 1.16**, and has initial support for methods on those objects
from the same swagger spec. Additionally, it defines some higher-level CRUD-style
methods on top of these foundation methods.

Usage examples
~~~~~~~~~~~~~~

To create Python objects from a Kubernetes YAML source, use ``load_full_yaml()``:

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

   from hikaru.model.rel_1_16 import Pod
   assert isinstance(p, Pod)
   print(p.metadata.labels["lab2"])
   print(p.spec.containers[0].ports[0].containerPort)
   for k, v in p.metadata.labels.items():
       print(f"key:{k} value:{v}")
       

You can create Hikaru representations of Kubernetes objects in Python:

.. code:: python

   from hikaru.model.rel_1_16 import Pod, PodSpec, Container, ObjectMeta
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
    
...and then turn it into real Kubernetes resources using the CRUD methods:

.. code:: python

	x.create(namespace='my-namespace')
	
...or read an existing object back in:

.. code:: python

	p = Pod().read(name='hello-kiamol-3', namespace='my-namespace')
	
...or use a Hikaru object as a context manager to automatically perform updates:

.. code:: python

	with Pod().read(name='hello-kiamol-3', namespace='my-namespace') as p:
		p.metadata.labels["new-label"] = 'some-value'
		# and other changes
		
	# when the 'with' ends, the context manager sends an update()

It is entirely possible to load YAML into Python, tailor it, and then
send it back to YAML; Hikaru can round-trip YAML through Python and
then back to the equivalent YAML.

The pieces of complex objects can be created separately and even stored
in a standard components library module for assembly later, or returned as the
value of a factory function, as opposed to using a templating system to piece
text files together:

.. code:: python

   from component_lib import web_container, lb_container
   from hikaru.model.rel_1_16 import Pod, ObjectMeta, PodSpec
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

With basic support of managing Kubernetes resources in place, other directions
are being considered such as event/watch support and bringing in support for
additional releases of Kubernetes.

About
~~~~~

Hikaru is Mr. Sulu’s first name, a famed fictional helmsman.
