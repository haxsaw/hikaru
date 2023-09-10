Hikaru Application
*******************

Basic Usage
    Creating an Application Class
    CRUD operations
Digging Deeper
    Labels and Annotations
    Modeling Constraints
    Instance Customization
    Persisted Forms
    Cannonical Forms with Class Methods
Other Operations
    Type Checking
    Diffs
    Searching


The Hikaru Application facility provides a way to aggregate a set of K8s resources that support an application
into a single construct that Hikaru can model and manage together. Additionally, it provides many of the same
utility methods that HikaruDocumentBase derived model classes do. With Applications objects you can:

- Model all the components of an application in a single dataclass
- Provide different instantiation methods to configure the Application class instance in different ways
- Use CRUD methods to manage the lifecycle of configured Application class instances in a K8s cluster
- Acquire feedback on processing progress through a Reporter class
- Persist and load the details of an instance to YAML, JSON, and Python dicts
- Easily create a Watcher on all the components of the Application instance in order to monitor their status
- Use the various inspection methods to do things like check type correctness, diff instances, or search for
  instances of particular classes within the application

The Basics
==========

Creating an Application Class
-----------------------------

Like Hikaru K8s model objects, Application objects are based on Python dataclasses. Users create a subclass of
the Application class from the ``app.py`` module (decorated with ``@dataclass``), and then define fields with type
annotations that indicate which K8s model resources comprise the application. You can then make create an instance
of the class with specific instances of the component resources, and then instruct Hikaru to create all the application
resources with the ``create()`` method.

Here's a simple example that involves a Pod and its Namespace:

.. code:: python

    from dataclasses import dataclass
    from hikaru.model.rel_1_26.v1 import *
    from hikaru.app import Application

    @dataclass
    class Example(Application):
        pod: Pod
        ns: Namespace

The Application subclass can contain any top-level (``HikaruDocumentBase`` derived) resource desired. While you'll most
likely want to specify various helper methods, this is the minimum needed to use Hikaru Applications.

To create an instance you'll need to supply values for both ``pod`` and ``ns`` in the call to Example:

.. code:: python

    ex = Example(pod=Pod(metadata=ObjectMeta(name="myapp-pod", namespace="example_ns"),
                         spec=PodSpec(containers=[
                                    Container(name="myapp-container",
                                              image="busybox",
                                              command=['sh', '-c',
                                                       'echo Hello Kubernetes! '
                                                       '&& sleep 3600'])]
                                  ),
                 ns=Namespace(metadata=ObjectMeta(name="example_ns")
                 )

CRUD Operations
---------------

Once you instantiate an Application subclass, you can have Hikaru create an instance in your
Kubernetes cluster with the ``create()`` method:

.. code:: python

    ex.create()

A number of things happen here:

- Hikaru generates a UUID for the instance
- Hikaru examines the components of the app and orders their creation
- Prior to creating a resource, it attempts to ``read()`` it first to see if it already exists (so
  creation is idempotent); if the item exists it moves on to the next resource
- If it doesn't exist, Hikaru invokes ``create()`` on the resource to make the instance of it in
  the cluster

Once the ``create()`` call returns, the id of the instance in K8s can be acquired via the ``instance_id``
attribute:

.. code:: python

    print(ex.instance_id)

You can recreate an instance from the cluster using the ``read()`` class method on the subclass by supplying the
instance_id that Hikaru created when the instance was created:

.. code:: python

    ex: Example = Example.read(instance_id)

``update()`` works as you'd expect. Suppose you wanted to add some metadata to the Pod after creation and
read back the instance as shown above. Updating is just:

.. code:: python

    ex.pod.metadata.labels["new_label"] = "new value"
    ex.update()

And of course, you can free all the resources for the Application in the cluster with the ``delete()`` method:

.. code:: python

    ex.delete()

Monitoring Operations
---------------------

When performing CRUD operations, Hikaru is silent by default-- there is no output to stdout or any other channel as
work progresses.

Application instances can optionally be associated with a "reporter" object that will receive events as CRUD operations
are carried out. These are different from a Kubernetes ``watch`` in that they reflect the processing progress of individual
resources being carried out by Hikaru.

If a user wants to be able to capture these events, they can create a subclass of the `hikaru.app.Reporter` class and provide
it to the Application subclass instance. The derived class of ``Reporter`` provides an implementation of the ``report()``
method. This method will be invoked during various processing steps for each resource in an application as CRUD operations
are carried out.

The ``report()`` method is passed the following parameters:

- The ``Application`` instace doing the reporting, so that multiple instances can share the same ``Reporter``,
- A string defining what kind of action is being carried out (create, read, etc),
- A string defining the type of the event being reported; these are class attributes on the ``Reporter`` class,
- A string timestamp of when the event occured,
- An optional string containing the name of the attribute in the Application that is being processed (None if an
  Application level event),
- A ``HikaruDocumentBase`` derived resource instance that is being processed (or None if an,
- A dict of any other supplemental information.

Here's a simple example of a ``Reporter`` that prints some of the data to a specified stream:

.. code:: python

    class SimpleReporter(Reporter):
        def __init__(self, stream):
            self.stream = stream

        def report(self, app: Application, app_action: str, event_type: str, timestamp: str,
                   attribute_name: str, resource: HikaruDocumentBase, addtional_details: dict):
            self.stream.write(f"Got event {event_type} for {app_action} at {timestamp} "
                              f"for resource {attribute_name}\n")

    reporter = SimpleReporter(sys.stdout)  # send output to stdout
    # Using an ``ex`` instance from the above examples,
    ex.set_reporter(reporter)



Digging Deeper
==============


Labels and Annotations
----------------------

During the ``create()`` process, Hikaru adds some content to the metadata of each resource to help with subsequent
queries:

- In each resource's ``labels`` map in the resource's ObjectMeta object, Hikaru creates an entry
  "app.kubernetes.io/instance": <instance UUID> to indicate that
  the instance of this resource belongs to this instance of the Application. This is used later to
  re-create the instance using the ``read()`` class method. The key used in the map is noted in
  the Kubernetes documentation as the official key for such uses, so other tools may be able to also
  use this key to identify instances of the application. The <instance UUID> value is the ``instance_id`` established
  for the Application instance during creation.
- In the ``annotations`` map of ObjectMeta, Hikaru creates an entry "HIKARU_RSRC_ATTR_KEY": <attr name>, identifying
  what attribute in the Application class this resource instance belongs to. This allows Hikaru to properly
  re-assemble an Application subclass instance when ``read()`` from K8s, even if the class has
  multiple attributes of the same resource type (for example, more than one resource is of type Pod).

This label and annotation data allow Hikaru to recreate instances of Application objects with the ``read()``
class method on the Application subclass.

.. note::

    Altering either these keys or their values will make it so that Hikaru will not be able to re-create
    the instance with ``read()``. It is possible to change what key is use to stored the instance UUID in the ``labels``
    mapping with ``app.set_app_instance_label_key()``. Similarly, you can change the key used in the annotations mapping
    that stores the name of the attribute a resource instance belongs to with ``app.set_app_rsrc_attr_annotation_key()``.
    See the relevant documentation for details.

Modeling Constraints
--------------------

The current implementation of Application involves some constraints on what kinds of fields you can declare
in your Application dataclass. This is because Hikaru must be able to recreate an Application subclass instance
from data solely from a Kubernetes cluster, and non-Hikaru model data won't be available for reading from the
cluster. This constraint may be relaxed in a future release, but for now it is enforced. In practice, there are
other ways to include additional data in Application subclasses that get around this constraint.

In this release of Hikaru Applications, your dataclasses are **allowed** to:

- Have *non-type annotated* class attributes
- Have type annotated attributes whose type is a derived class of HikaruDocumentBase (such as Pod, Namespace,
  etc)
- Have Optional[] type annotated attributes whose type is a derived class of HikaruDocumentBase with a default of ``None``.

The following Application subclass illustrates these recognized conditions:

.. code:: python

    @dataclass
    class Allowed(Application):
        regular_ol_class_attr = "something"  # regular class attribute without a type annotation
        pod: Pod   # type annotated field whose type is derived from HikaruDocumentBase
        maybe_pod: Optional[Pod] = None  # Optional type annotated field with a default value

The following are **not** allowed:

- Any other type annotation
- List[], Dict[], Tuple[], etc as a type annotation
- Optional[] annotations involving any of the above
- The use of field() to supply anything other than a default value (default factories aren't currently supported)

Such classes won't fail in Hikaru immediately, but when any operation is carried out that requires examining all of
type annotations in a dataclass, illegal annotations will be found then the operation will be aborted. These
operations include:

- CRUD operations
- diff, searching, other inspection
- transformation to/from other forms (JSON, YAML, Python dict)

Persistence Forms
------------------

Like other Hikaru objects, Application subclass instances can be saved off a variety of different external forms and then
re-instantiated from those forms.

Hikaru Application subclass instances can be persisted to:

- YAML
- JSON
- Python dicts

And these persisted forms can then be reloaded back into live objects upon which subsequent operations can be performed. For
example, after an instance is created in Python and had ``create()`` invoked on it to create an instance of the Application,
the object can then be persisted to JSON and stored in a document database of running application instances. This JSON can later be
read and turned back into a Python object where it can be watched, updated, or deleted.

YAML
^^^^

Like on basic Hikaru objects, the method ``get_yaml()`` can be invoked to acquire a string containing YAML that represents the 
details of the Application instance:

.. code:: python

    # assuming that 'ex' from above contains an instance
    # of the Example class from above
    s = ex.get_yaml()
    print(s)

This string can be saved to a file or other storage. When retrieved later, this string can be used to recreate the previously
saved instance using ``from_yaml()``:

.. note::

    The YAML form is actually a container of standard Kubernetes YAML for each resource. Hence, individual resource YAML
    representations can be extracted and used with regular K8s tools.

.. code:: python

    # s contains a string retrieved from store
    ex = Example.from_yaml(yaml=s)

These two methods are the same as on other HikaruBase derived classes, and ``from_yaml()`` can work with content from a string,
a file at a path, or a TextIO object (an open file stream of some kind).

JSON
^^^^

JSON is also supported with methods that echo those of ``HikaruBase``. A JSON representation of an ``Application`` subclass instance
can be acquired with the ``get_json()`` method:

.. code:: python

    # assuming that 'ex' from above contains an instance
    # of the Example class from above
    j = ex.get_json()

When an instance is to be recreated from the JSON representation simply call the ``from_json()`` method on the class, passing
the previously saved JSON:

.. code:: python

    # j contains the retrieved JSON string
    ex = Example.from_json(j)

Factory Methods for Canonical Forms and Instance Customization
--------------------------------------------------------------

Because of constraints imposed by Python dataclasses and Hikaru Application semantics, there are some limitations in
further customizing Application instances in terms of the data instances can contain.

As previously mentioned, the definition of a Application subclass can only contain dataclass fields that are type annotated
to be some kind of ``HikaruDocumentBase`` subclasss. This is in support of the ``read()`` class method on all Application
subclasses. ``read()`` takes a single argument, the instance_id from a previous invocation, and uses that to query the K8s cluster
to find all the resources that go into the Application. The ``read()`` method uses the type annotated class attributes to determine
what kind of objects to query from the cluster, and then uses those queried objects in the creation of a new instance of the
Application subclass. Since only Kubernetes objects can be queried from the cluster, no other data can included in the Application
dataclass since there is no place to acquire it for instance creation when doing ``read()``. The ``dup()`` method has similar
constraints since it also must create a new instance of an Application subclass.

The following addresses a couple of common scenarios where additional data besides that modeled in the dataclass may be of use.

Factory Methods
^^^^^^^^^^^^^^^

In order to allow an Application subclass to be used correctly in a number of different contexts it is good practice to create a
factory classmethod that can create a standardized instance of the Application rather than expecting a user of the Application to
always provide the correctly configured resources to the instance creation call. Adding such a method provides a way of
incorporating non-dataclass data into the instance creation process without actually having to store the data in the dataclass
itself.

Recalling the example app from above:

.. code:: python

    from dataclasses import dataclass
    from hikaru.model.rel_1_26.v1 import *
    from hikaru.app import Application

    @dataclass
    class Example(Application):
        pod: Pod
        ns: Namespace

We initially showed how the ``Example`` class could be instantiated by passing in instances of each field into the ``Example()``
call:

.. code:: python

    ex = Example(pod=Pod(metadata=ObjectMeta(name="myapp-pod", namespace="example_ns"),
                         spec=PodSpec(containers=[
                                    Container(name="myapp-container",
                                              image="busybox",
                                              command=['sh', '-c',
                                                       'echo Hello Kubernetes! '
                                                       '&& sleep 3600'])]
                                  ),
                 ns=Namespace(metadata=ObjectMeta(name="example_ns")
                 )

Operationally this is fine, but puts significant responsibiltiy on the caller to ensure that the components are each configured
correctly for the purpose of the app (and possibly for other conventions and standards as well).

A simple way to ensure that a user of ``Example`` can always get a canonical form of the app is to provide a classmethod that
knows how to create and return a canonical form:

.. code:: python

    @dataclass
    class Example(Application):
        pod: Pod
        ns: Namespace

    @classmethod
    def example_factory(cls) -> "Example":
        ex = Example(pod=Pod(metadata=ObjectMeta(name="myapp-pod", namespace="example_ns"),
                         spec=PodSpec(containers=[
                                    Container(name="myapp-container",
                                              image="busybox",
                                              command=['sh', '-c',
                                                       'echo Hello Kubernetes! '
                                                       '&& sleep 3600'])]
                                  ),
                 ns=Namespace(metadata=ObjectMeta(name="example_ns")
                 )
        return ex

Now a user of ``Example`` need only invoke ``example_factory()`` to get a properly configured instance of an ``Example``:

.. code:: python

    new_example = Example.example_factory()

It's a simple matter now to build on this classmethod to provide parameters that customize the canonical form in a controlled
manner. For instance, the implementation below allows the caller to specify the name for the namespace to be created in the app:

.. code:: python

    @classmethod
    def example_factory(cls, nspace: str) -> "Example":
        ex = Example(pod=Pod(metadata=ObjectMeta(name="myapp-pod", namespace=nspace),
                         spec=PodSpec(containers=[
                                    Container(name="myapp-container",
                                              image="busybox",
                                              command=['sh', '-c',
                                                       'echo Hello Kubernetes! '
                                                       '&& sleep 3600'])]
                                  ),
                 ns=Namespace(metadata=ObjectMeta(name=nspace)
                 )
        return ex

This approach can allow for a wide variety of customization approaches, even providing a means to allow the caller to provide
whole sub-assemblies such as a specifically configured ``Container`` instance for the PodSpec.

Instance Customization
^^^^^^^^^^^^^^^^^^^^^^

If you require storing additional data in your Application subclass you have a bit more work ahead of you.

Generally, adding non-resource data to Application subclasses is discouraged due to the complexity involved in working around the
constraints of dataclasses, what can be stored/retrieved in Kubernetes, and the work needed to support persisting
reanimating such classes. Few use cases can't be addressed with either the factory method approach shown above or else storing the
additional data in an object associated with the Application instance. For the sake of completeness, the steps required are
discussed here.

*Creating instances*

Instance creation is taken over by the ``dataclass`` machinery and that imposes some restrictions. While it is possible to include
fields in a dataclass that can have type a annotation of ``InitVar`` which allows them to be



Other Operations
=================

Type Checking
-------------

Diffs
------

Searching
----------

