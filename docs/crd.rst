Hikaru CRD Support
******************

Hikaru includes support for the specification, instantiation, and monitoring of Custom Resource
Definitions (CRDs). With a small number of additional objects and functions, Hikaru allows the user to
define their own resources and to manage them just like the core K8s resources Hikaru ships with.

Hikaru CRD support allows you to:

- Define the structure of a CRD, either from scratch or to mimic one that is already in your environment,
- Send the definition into K8s where it will be established as a CRD managed by Kubernetes,
- Define instances of the new CRD using CRUD methods,
- Establish Watches on a specific CRD to either monitor activity or implement a Python controller for the
  CRD, and
- Use CRDs as context manager, including the rollback context manager.

Hikaru provides these capabilities with a small set of additional functions and classes built on top
of the core Hikaru facilities. They are:


- :ref:`HikaruCRDDocumentMixin<HikaruCRDDocumentMixin doc>`, a mixin base class that you add to classes derived from ``HikaruDocumentBase``;
  this mixin provides the CRUD methods needed to manage the CRD instances.
- :ref:`FieldMetadata<FieldMetadata doc>`, a class used to provide additional metadata on a single attribute that will impact
  how that attribute is rendered in OpenAPI schema when the definition is sent to Kubernetes.
- :ref:`register_crd_class()<register_crd_class doc>`, a function that takes your new CRD class and registers it with Hikaru's runtime
  system, thus enabling Hikaru to create instances of the class when messages containing it are received,
  or if external YAML or Python dicts contain that data for a class instance.
- :ref:`get_crd_schema()<get_crd_schema doc>`, a function that inspects a CRD class and returns a ``JSONSchemaProps`` object; this
  object is used by the K8s API to define new CRD resources to Kubernetes.

These four additions to the core API provide all that is needed to define and work with CRDs.

.. note::

    Some of the following assumes knowledge of Kubernetes CRDs and OpenAPI. The reader is assumed
    be comfortable with these topics and can research any knowledge gaps they may have.

Quick Example
=============

To illustrate the method to create and work with CRDs in Hikaru, we'll start with a simple example. It
will be broken in to different parts to keep each concept brief.

It will be helpful to define two terms that will be be used in the example:

- When we want to convey the structure of a new CRD to Kubernetes, we will say we are **defining** the
  CRD.
- When we want to create an instance of the resource described by the new CRD, we will say we are
  **instantiating** the resource.

Hence, the *definition* is the description of the resource's structure given to K8s, but we
*instantiate* a particular occurrence of the resource.

In the example that follows, we'll create a CRD called *MyPlatform* that collects up several bits
of information that will be recorded by Kubernetes and possibly acted upon by a controller.

The resource
------------

First, let's put the class that describes the resource into a module that can be
imported into other modules and used as needed. So in a module named *resource.py*, we'll add the
following code:

.. code:: python

    from hikaru.model.rel_1_23.v1 import ObjectMeta
    from hikaru import (HikaruBase, HikaruDocumentBase,
                        set_default_release)
    from hikaru.crd import register_crd_class, HikaruCRDDocumentMixin
    from typing import Optional
    from dataclasses import dataclass

    set_default_release("rel_1_23")
    plural = "myplatforms"
    group = "example.com"


    @dataclass
    class MyPlatformSpec(HikaruBase):
        appId: str
        language: str
        environmentType: str
        os: Optional[str] = None
        instanceSize: Optional[str] = None
        replicas: Optional[int] = 1


    @dataclass
    class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
        metadata: ObjectMeta
        spec: Optional[MyPlatformSpec] = None
        apiVersion: str = f"{group}/v1"
        kind: str = "MyPlatform"


    register_crd_class(MyPlatform, plural, is_namespaced=False)

This minimal CRD will be built upon in later sections. We first import any objects
that we need from the release/version of the K8s API that we want include in the new CRD, then import
some standard classes and utility functions from hikaru, the registration function and mixin class
from hikaru.crd, and then some typing support objects and and the dataclass decorator.

We then use ``set_default_release()`` to the desired release Hikaru should use when creating objects,
and set the variable ``plural`` to an all-lowercase plural version of our resource name (this will be
important later). We also set the variable ``group`` to a DNS-abiding string, which will also become important
here and in other modules.

The CRD itself is in two parts, echoing the structure of standard Kubernetes objects:

- The 'spec' class that contains the details of the CRD that drive its semantics. This class inherits
  from ``HikaruBase``.
- The 'document' or topmost class that provides Kubernetes the identifying information required to know what kind
  of resource this is. This class contains type annotated attribute to the spec class as well as the standard
  ``metadata``, ``apiVersion``, and ``kind`` attributes. This class is derived from both ``HikaruDocumentBase``
  and ``HikaruCRDDocumentMixin``.

Usually the spec is made an ``Optional`` object so that it can be left out when you actually just want
to read an instantiated CRD from K8s. Note that ``apiVersion`` and ``kind`` need to be set to real values.

Finally, we register the CRD class with Hikaru using the ``register_crd_class()`` function. Note that this must
always be done-- Hikaru otherwise doesn't know about your new class. The function will examine the class for
required attributes and their values to make sure it knows what kind of object to instantiate when it
receives a message from K8s. In this example, we want a cluster-wide resource with no namespace, and
hence we set ``is_namespaced`` to False.

Defining the CRD
----------------

With this in hand, we can now use the ``MyPlatform`` class as the source of data needed to define our new CRD
to Kubernetes. This is the most finicky part of dealing with CRDs, but once done all other operations are
fairly simple. In a file called `define.py` we add this code:

.. code:: python

    from kubernetes import config
    from hikaru.model.rel_1_23.v1 import *
    from hikaru.crd import get_crd_schema
    from resource import MyPlatform, plural, group

    if __name__ == "__main__":
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

        schema: JSONSchemaProps = get_crd_schema(MyPlatform)  # get the schema for the new class

        crd: CustomResourceDefinition = \
            CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
                group=group,
                names=CustomResourceDefinitionNames(
                    shortNames=["myp"],
                    plural=plural,
                    singular="myplatform",
                    kind=MyPlatform.kind
                ),
                scope="Cluster",
                versions=[CustomResourceDefinitionVersion(
                    name="v1",
                    served=True,
                    storage=True,
                    schema=CustomResourceValidation(
                        openAPIV3Schema=schema  # schema goes here!
                    )
                )]
            ),
            metadata=ObjectMeta(name=f"{plural}.{group}")
        )

        create_result = crd.create()

This code will need to contact K8s, and so the first thing it does is import the ``config`` module
from ``kubernetes``. Then it imports all the classes from the release/version of Hikaru we are
going to use, the ``get_crd_schema()`` function from ``hikaru.crd``, and then the ``MyPlatform`` class and some
of the naming variables from the `resource.py` module.

After loading the K8s config, ``get_crd_schema()`` is used on ``MyPlatform``; this returns a ``JSONSchemaProps``
instance whose contents describe the schema of the ``MyPlatform`` class (you can view this schema by
printing the return from ``hikaru.get_yaml()`` function, passing the schema as an argument).

We then get into the business of creating the ``CustomResourceDefinition`` object that will define our
new resource to Kubernetes. This is a nested set of various objects from the standard Kubernetes API.
A few things to note:

- We use the imported ``group`` variable as the value of the ``group`` parameter to `CustomResourceDefinitionSpec`
  to ensure that the names are kept consistent.
- In ``CustomResourceDefintionNames``, we use the imported ``plural`` variable and ``MyPlatform.kind`` for
  values we supply to various parameters; again, we do this to ensure we use consistent names across
  various objects.
- The ``scope`` parameter is set to "Cluster" which means that the resource is cluster-wide and doesn't need
  a namespace, which matches how we registered our class with Hikaru (these must match). If the class was
  registered to use a namespace (``is_namespaced == True``), then this parameter would need to be "Namespaced".
- The ``versions`` list can contain multiple versions of our resource, but only one can be stored to persistent
  storage.
- Inside the ``CustomResourceDefinitionVersion`` object, we finally supply our schema as the value of the
  ``openAPIV3Schema`` parameter to the ``CustomResourceValidation`` object.
- When we give the name to the resource in the ``ObjectMeta`` object, we again use the ``plural`` and ``group``
  variables for the resource's name to ensure we keep names consistent.

After creating the object, we're ready to define it to Kubernetes; we do this by invoking the ``create()``
method on the ``CustomResourceDefinition`` instance. The return will be fully filled out
``CustomResourceDefinition`` object, the
contents of which can be viewed with other Hikaru tools such as ``get_yaml()``. You can also check the
presence of the new CRD in Kubernetes with the ``kubectl`` command like so:

.. code::

    kubectl get crds

You should see the new CRD listed with the value supplied to the ``ObjectMeta.name`` parameter.

Creating Instances
------------------

To now creates instances of the new CRD, we simply make a new instance of our CRD classes and invoke
its ``create()`` method. In a file called `instantiate.py` add this code:

.. code:: python

    from hikaru.model.rel_1_23.v1 import ObjectMeta
    from resource import MyPlatform, MyPlatformSpec
    from kubernetes import config

    if __name__ == "__main__":
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

        mc: MyPlatform = MyPlatform(
            metadata=ObjectMeta(name="first-go"),
            spec=MyPlatformSpec(
                appId="123-45-6789",
                language="python",
                environmentType="dev",
                instanceSize="small"
            )
        )

        result = mc.create()

We import standard K8s classes that we need, the classes from our resource module, and then the config
module from Kubernetes as we again are going to contact Kubernetes. After we provide K8s our config data,
we make an instance of the ``MyPlatform`` resource class. Note that a ``MyPlatformSpec`` is created; we need the
whole ``spec`` to create a meaningful definition of our resource. If we were to do a read we'd only need the
``metadata`` parameter. After that, we invoke ``create()`` on the instance, and receive in return a new
``MyPlatform`` instance which will have all of the ``ObjectMeta`` information filled out. You can view this in
detail with the ``get_yaml()`` function. You can also see this from kubectl with:

.. code::

    kubectl get myplatform

or, more briefly:

.. code::

    kubectl get myp

since that was established as a short name.

Watching Activity on the CRD
----------------------------

Watchers are especially easy to construct, which makes creating controllers fairly straightforward. In a file
called `watch.py` add the following code:

.. code:: python

    from resource import MyPlatform
    from hikaru import get_yaml
    from hikaru.watch import Watcher
    from kubernetes import config

    if __name__ == "__main__":
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

        w = Watcher(MyPlatform, timeout_seconds=10, should_translate=False)
        for we in w.stream(manage_resource_version=True, quit_on_timeout=True):
            print(get_yaml(we.obj))

After importing the same objects and setting up the K8s config, we create a ``Watcher`` on ``MyPlatform`` and
then wait for events to arrive from the use of the ``stream()`` method. For each event we simply print
out the received object's YAML form, but you could do whatever you liked, like allocating a fixed set
of resources, or initiating an external process.

Other CRUD methods
-------------------

Performing other CRUD operations is easier than instantiation since you only need to provide the
``ObjectMeta`` component to ``MyPlatform``:

.. code:: python

    from hikaru.model.rel_1_23.v1 import ObjectMeta
    from hikaru import get_yaml
    from resource import MyPlatform
    from kubernetes import config

    if __name__ == "__main__":
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

        mc: MyPlatform = MyPlatform(
            metadata=ObjectMeta(name="first-go")
        )

        # read
        result = mc.read()
        print(get_yaml(result))

        # update
        result.spec.instanceSize = "medium"
        result = result.update()

        # delete
        result = result.delete()

Creating a CRD
===============

Hikaru CRDs are based on new classes created by the user or reused from existing K8s classes. These
classes must have some specific characteristics in terms of base classes, common attributes of specific
types, and default values for specific attributes. The following sections go over these requirements.

Base classes
------------

Hikaru CRDs are defined by creating a topmost class with both ``HikaruDocumentBase`` and ``HikaruCRDDocumentMixin`` as
bases in the topmost class. **By 'topmost', we are referring to the class that gives the CRD its identity and
serves as the root object in a hierarchy of data and other objects**.
While a CRD may be comprised of multiple classes, only the topmost class should be inherited from these
two bases. All other classes in a CRD must inherit from ``HikaruBase``.

Each of these classes provides specific capabilities:

- ``HikaruBase`` provides all the foundation machinery to integrate a derived class into the Hikaru
  runtime, as well as providing a number of common capabilites such as duplication, merging, rendering
  into different forms, etc. See
- ``HikaruDocumentBase``, which is a subclass of ``HikaruBase``, adds some additional capability to allow
  a class to serve as a 'topmost' class for a K8s resource. So for example, a Pod is topmost class
  that describes pods, and it is derived from HikaruDocumentBase.
- ``HikaruCRDDocumentMixin`` is an adjunct class for HikaruDocumentBase that adds standard CRUD methods
  and context manager capabilities to all topmost CRD resource classes.

Required attribute: ``apiVersion: str = "<group>/<version>"``
--------------------------------------------------------------

The topmost class must contain an attribute named ``apiVersion``, annotated as a string with a default value.
The default value contains an API group name, a '/', and then a version number as used by Kubernetes:

- The API group must follow DNS naming conventions, so 'example.com' or 'businessunit.yourcompany.com'
  are allowed names. You MAY NOT use '_' (underscore) in the name, but can use '-' (dash). These don't
  actually need to resolve to anything, they just need to be in the correct form.
- The version number must follow Kubernetes conventions. The following text about legal version numbers is
  quoted from the swagger that defines the Kubernetes API; in Kubernetes: ::

    versions start with a "v", then are followed by a number (the major version), then optionally the
    string "alpha" or "beta" and another number (the minor version). These are sorted first by
    GA > beta > alpha (where GA is a version with no suffix such as beta or alpha), and then by comparing
    major version, then minor version. An example sorted list of versions: v10, v2, v1, v11beta2,
    v10beta3, v3beta1, v12alpha1, v11alpha2, foo1, foo10.

So examples of correct versions of this attribute are:

.. code:: python

    apiVersion: str = "example.com/v1"
    apiVersion: str = "some.made.up.dns/v2beta1"
    apiVersion: str = "fx.hugebank.com/v3"

...and some incorrect examples are:

.. code:: python

    apiVersion = "example.com/v1"  # missing type annotation
    apiVersion: str = "some_company.com/v2"  # underscore not allowed
    apiVersion: str = "NoCaps.com/v1"  # use of uppercase
    apiVersion: str = "ok-name.com/V1"  # version number contains caps

Some errors here will be caught by Hikaru, some by K8s, and some may not be apparent until you run into
an odd failure.

Required attribute: ``kind: str = "CRDName"``
----------------------------------------------

A topmost class must contain a ``kind`` string attribute whose default value is a name for the kind of
resource a class represents. Conventionally, this should simply be the name of the resource class: for
instance, in the initial example, our topmost class is MyPlatform, and the kind of that class is
"MyPlatform". The only constraint is that there can only be one class with a specific combination of
version and kind values; Hikaru only tracks a single class for each unique combination of these values.

Required attribute: ``metadata: ObjectMeta``
--------------------------------------------

The ``metadata`` field contains an object that K8s commonly looks to for information such as instance
name and namespace. While this may be Optional and default to None, most interactions with K8s will
fail without it, and so it is best to include it as a required attribute.

Decorated with ``dataclass``
-----------------------------

Every class in your CRD, whether the topmost class or not, must be decorated with the ``dataclasses``
module's ``dataclass`` decorator. If this is missing, Hikaru will not be able to properly inspect your
CRD's classes which will result in runtime errors. So be sure to use this decorator for all classes in
your CRD.

Other data
-----------

Once you gotten through these requirements, you are free to add any other data fields to your dataclasses
in line with dataclass restrictions (see the Python doc for these). Each attribute that you want Hikaru to
manage must have a type annotation, and attributes that don't have a default value must be listed before
those with a default.

To see how this all fits together, reconsider the example from above:

.. code:: python

    group = "example.com"

    @dataclass
    class MyPlatformSpec(HikaruBase):
        appId: str
        language: str
        environmentType: str
        os: Optional[str] = None
        instanceSize: Optional[str] = None
        replicas: Optional[int] = 1


    @dataclass
    class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
        metadata: ObjectMeta
        spec: Optional[MyPlatformSpec] = None
        apiVersion: str = f"{group}/v1"
        kind: str = "MyPlatform"

In this code, apiVersion will default to "example.com/v1", kind to "MyPlatform", and the user must supply
an ObjectMeta instance for the metadata attribute.

Other things to note here:

- ``MyPlatformSpec`` is derived from ``HikaruBase``, while the topmost class ``MyPlatform`` is derived from both
  ``HikaruDocumentBase`` and ``HikaruCRDDocumentMixin``.
- You can reuse any existing Kubernetes class within your CRD classes; here, ``MyPlatform`` uses the standard
  ``ObjectMeta`` class.
- The ``metadata`` attribute has no default and so appears before the other attributes in the dataclass.

Supported type annotations
--------------------------

Python type annotations have grown considerably, but not every construct is currently supported by Hikaru.
Hikaru support has largely been driven by the requirements of the K8s API spec. The following list
summarizes the annotations that Hikaru can process:

- int
- float
- str
- bool
- dict (str keys, str values)
- subclass of HikaruBase
- List of any of the above
- Any of the above, including List, can be placed inside Optional[]

Note that ``datetime`` isn't listed above; these come in as strings parseable into datetime objects. This is
consistent with Kubernetes use; datetimes are strings with a format value of 'date-time'.

Forward references are supported in the normal way. To make a forward reference to a HikaruBase subclass
in a type annotation, put the class name in quotes like so:

.. code:: python

    class X(HikaruBase):
        field_x: List['SomeClassToCome']   # the forward ref
        # more fields...

    class SomeClassToCome(HikaruBase):
        # and so on...

Specifying more details with field()
-------------------------------------

The standard ``dataclasses`` module includes a function named ``field()``; this factory function
provides the user a way to specify some additional details regarding the nature of a dataclass
attribute. Hikaru works with dataclasses that use ``field()`` and provides some additional tools to
use with ``field()`` to allow Hikaru to generate richer schema for defining a CRDs to Kubernetes.

The ``field()`` factory function includes an argument ``metadata``, which is a dictionary that Python leaves to
the user to employ however they wish; the ``field()`` factory captures the value but does nothing with it.
Hikaru provides another class, ``hikaru.meta.FieldMetadata``, which is a dict that can be used for the value
of the ``metadata`` parameter, but which imposes a normalized structure on the dict for storing Hikaru values
that should avoid a collision with any other uses.

Before we go into the use of ``FieldMetadata`` in detail, let's revisit the ``MyPlatform`` example from before.
We can see in YAML form the schema that Hikaru will generate when sent to YAML with the one liner:

.. code:: python

    print(get_yaml(get_crd_schema(MyPlatform)))

which produces this resultant schema:

.. code:: yaml

    properties:
      spec:
        properties:
          appId: {type: string}
          environmentType: {type: string}
          instanceSize: {type: string}
          language: {type: string}
          os: {type: string}
          replicas: {type: integer}
        required: [appId, language, environmentType]
        type: object
    type: object

This shows that the only validation data sent to K8s will be the types involved in each field.

Now let's rewrite the above CRD classes to use the ``field()`` factory and ``FieldMetadata``
for tuning how Hikaru will render the schema for the CRD.

.. code:: python

    # we'll provide FieldMetadata an alias to make code less wordy
    from hikaru.meta import FieldMetadata as fm
    group = "example.com"

    @dataclass
    class MyPlatformSpec(HikaruBase):
        appId: str = field(metadata=fm(
            description="The ID of the app this platform is for",
            pattern=r'^\d{3}-\d{2}-\d{4}$'))
        language: str = field(metadata=fm(
            description="Which language the app to deploy is written",
            enum=["csharp", "python", "go"]))
        environmentType: str = field(metadata=fm(
            description="Deployment env type",
            enum=["dev", "test", "prod"]))
        os: Optional[str] = field(default=None, metadata=fm(
            description="OS required for the deployment",
            enum=["windows",
                  "linux"]))
        instanceSize: Optional[str] = field(
            default='small',
            metadata=fm(
                description="Size of the instance needed; default is 'small'",
                enum=["small",
                      "medium",
                      "large"]))
        replicas: Optional[int] = field(
            default=1,
            metadata=fm(description="How many replicas should be created, min 1",
                        minimum=1))


    @dataclass
    class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
        metadata: ObjectMeta
        spec: Optional[MyPlatformSpec] = None
        apiVersion: str = f"{group}/v1"
        kind: str = "MyPlatform"

Using the same one-liner on this enriched definition produces the following schema:

.. code:: yaml

    properties:
      spec:
        properties:
          appId: {description: The ID of the app this platform is for, pattern: '^\d{3}-\d{2}-\d{4}$',
            type: string}
          environmentType:
            description: Deployment env type
            enum: [dev, test, prod]
            type: string
          instanceSize:
            description: Size of the instance needed; default is 'small'
            enum: [small, medium, large]
            type: string
          language:
            description: Which language the app to deploy is written
            enum: [csharp, python, go]
            type: string
          os:
            description: OS required for the deployment
            enum: [windows, linux]
            type: string
          replicas: {description: 'How many replicas should be created, min 1', minimum: 1,
            type: integer}
        required: [appId, language, environmentType]
        type: object
    type: object

You can see the differences in the generated schema: Hikaru adds validation modifiers to each property
based on metadata added with the ``field()`` factory function. These constraints will be applied by
Kubernetes whenever interactions involving the CRD occur.

Hikaru supports a number of these modifiers; the following table summarizes what they are and how to use
them:

+-------------------+-------------------------------+----------------------+-----------------------------------------+
| Modifier          |  Applies to property of type  | Modifier value type  | Action                                  |
+===================+===============================+======================+=========================================+
| description       | Any type property             | str                  | adds a text description to the property |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| enum              | - int, str, float             | sequence of:         | lists the valid valids a property may   |
|                   | - list of int, str, float     | int, str, float      | be assigned                             |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| format            | int, str, float               | str                  | describes the format of the data\*      |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| minimum           | int, float                    | int, float           | the minimum value the property accepts  |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| exclusive_minimum | int, float                    | bool                 | True if minimum isn't an allowed value  |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| maximum           | int, float                    | bool                 | True if maximum isn't an allowed value  |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| pattern           | str                           | str                  | JS regex the values must match          |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| multiple_of       | int, float                    | int, float           | value must be an even multiple          |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| min_items         | array (list, tuple)           | int                  | minimum number of items in the array    |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| max_items         | array (list, tuple)           | int                  | maximum number of items in the array    |
+-------------------+-------------------------------+----------------------+-----------------------------------------+
| unique_items      | array (list, tuple)           | bool                 | True if all array items must be unique  |
+-------------------+-------------------------------+----------------------+-----------------------------------------+

* refer to the OpenAPI spec for allowed format values

If any of the following are used with an array type, they apply to the elements in the array:
``enum, format, minimum, exclusive_minimum, maximum, exclusive_maximum, pattern, or multiple_of``. 
Modifiers used with the incorrect type of property are ignored.

.. note::

    These modifiers are transmitted to Kubernetes and it is there that any constraints they imply are enforced.
    Hikaru doesn't look at these at all except when defining a CRD to K8s. However, **default** values are
    implemented in Hikaru, not Kubernetes. So if an element is optional and has a default value, you should
    consider whether or not Python should have a default or should the default be implemented solely in the
    controller for the CRD.

Good practices
------------------

Several good practices should be observed when defining your own CRDs:

- **Split the CRD into at least two parts, the topmost object and the ``spec``, and make the spec optional**:
  virtually every existing K8s resource is organized this way, and the reason is simple: you only need the
  contents of the spec when instantiating the resource, not when reading, or deleting. So if you make the spec
  optional then when you want to read/delete you only need to provide the name via the metadata. Typically, the topmost
  object contains ``apiVersion``, ``kind``, ``metadata``, and ``spec``, while the ``spec`` object contains all the
  data relevant to the CRD itself. You don't have to do things this way, but it can be a lot simpler to follow
  this convention.
- **House the resource classes in their own module**: this way the resources can be imported into any other module
  easily for whatever purpose.
- **Add a call to ``set_default_release()`` for the release your CRD depends on in the resource module**: if you
  do this in the resource module, you won't need to do this in the main code that uses the resource.
- **If you're creating a class to mimic an existing CRD**, you may not want to bother with adding ``field()``
  calls with ``FieldMetadata`` to your CRD dataclasses. This is because the ``FieldMetadata`` elements only come
  into play when defining the CRD to Kubernetes; Hikaru does nothing with them in any other cases, so they
  represent additional work that provides no value except perhaps documentation.
- **The ``description`` modifier is a good place to mention default values**: this allows the user to query the
  API for its metadata and receive more useful information regarding its use.
- **If your class is to mimic and existing CRD, don't bother with a ``CustomResourceDefinition`` object**: there
  is no need for this work if you aren't expecting to define the resource to K8s. It is enough to create the
  CRD classes to begin working with the resource from Python.

Defining the CRD to Kubernetes
==============================

The basics
----------

If you want to now define a CRD to Kubernetes, you need to use the ``CustomResourceDefinition`` class to provide K8s
the metadata about your resource including the schema for your CRD classes.

This section only goes over the basic details to get our example CRD, MyPlatform, into Kubernetes. It's recommended
that the reader consult the Kubernetes documentation on custom resource definitions for all the details.

A key piece is to acquire a ``JSONSchemaProps`` object that contains a schema for the new CRD classes. Hikaru makes
this simple: it just requires a call to ``get_crd_schema()``, which inspects the CRD class and generates an
appropriate ``JSONSchemaProps`` object that can be used in creating the full ``CustomResourceDefinition``. The following
is a typical use:

.. code:: python

    schema: JSONSchemaProps = get_crd_schema(MyPlatform)

And now ``schema`` cis a ``JSONSchemaProps`` object containing an OpenAPI schema for ``MyPlatform`` and all the classes
it contains. You can have a look at this schema with ``get_yaml()``:

.. code:: python

    print(get_yaml(schema))

Or, if you prefer a pretty Python dict representation, you can use the schema's ``to_dict()`` method to get a dict
and then ``pprint()`` to render it:

.. code:: python

    from pprint import pprint
    pprint(crd.to_dict())

Next we have to embed this schema into the proper place inside a ``CustomResourceDefinition`` object.

A ``CustomResourceDefinition`` instance contains a number of other objects to fully describe a CRD to Kubernetes.
Various aspects of these objects must agree with how a CRD class is constructed and registered with Hikaru. The
following depicts what objects are contained by other objects, and what aspects of each must agree with
the data in the CRD class and registration: ::

    CustomResourceDefinition  # which contains:
        spec CustomResourceDefinitionSpec  # which contains:
            group  # which must match the group portion of the apiVersion attribute
            scope  # which must be Cluster or Namespaced; must agree with is_namespaced from register_crd_class()
            names CustomResourceDefinitionNames  # which contains:
                shortName  # list of strings to use as short names
                plural  # which must match the plural name used in register_crd_class()
                singular  # a lower-cased singular form of the  resource name
                kind  # which must match <resource-class>.kind, MyPlatform.kind in this case
            versions List[CustomResourceDefinitionVersion]  # each item containing:
                name  # the version number portion of the apiVersion attribute
                served  # True if to be served by the REST API
                storage  # only one CRD version can be stored; True for the version to store
                schema CustomResourceValidation  # which contains:
                    openAPIV3Schema  schema  # THIS IS WHERE THE CRD CLASS SCHEMA GOES!
        metadata ObjectMeta  # which contains:
            name  # of the form plural.group; using our vars, f"{plural}.{group}" would do it

Using this as a guide, here's once again how we create a CRD definition object for the MyPlatform class:

.. code:: python

    schema: JSONSchemaProps = get_crd_schema(MyPlatform)

    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group=group,
            names=CustomResourceDefinitionNames(
                shortNames=["myc"],
                plural=plural,
                singular="myplatform",
                kind=MyPlatform.kind
            ),
            scope="Cluster",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema  # schema goes here!
                )
            )]
        ),
        metadata=ObjectMeta(name=f"{plural}.{group}")
    )

After this, assuming that Kubernetes has been configured as previously shown, all that's needed is to invoke
``create()`` on the ``CustomResourceDefinition`` object:

.. code:: python

    result = crd.create()

The result value will be another ``CustomResourceDefinition`` object with all data filled out, in particular
the ``ObjectMeta`` data. You can now see your resource with ``kubectl``:

.. code::

    kubectl get crds

You should see the plural.group name in the returned list.

Defining namespaced CRDs
------------------------

Defining namespaced CRDs only takes a few changes, which we'll summarize here:

- **Be sure to set is_namespaced=True when registering the CRD class with register_crd_class()**: Not doing this
  will break ``Watcher`` objects and other things.
- **Be sure to set scope="Namespaced" in the CustomResourceDefinitionSpec**: This tells Kubernetes that the resource
  is a namespaced one. This is only important if you are actually defining the CRD to Kubernetes; if your class is only to access
  and existing CRD you don't need to create a ``CustomResourceDefinition`` at all.

Additionally, you have an extra step to carry out when instantiating your namespaced CRD: first, the namespace that your instance
refers to must exist! This is also true if you want to create a ``Watcher`` on your namespaced CRD: the namespace for the things
you want to watch must exist. You can always easily try reading for the existence of the namespace first with something like:

.. code:: python

    ns: Namespace = Namespace(metadata=ObjectMeta(name='the-namespace-name'))
    try:
        result = ns.read()
    except:
        result = ns.create()

This fragment will try to read the namespace first, and if it doesn't exist, will then create it. You'll then be free
to create your CRD instance.

Places you might go wrong
-------------------------

Here are some common pitfalls when working with CRDs:

- **register_crd_class()'s is_namespaced doesn't agree with scope of CustomResourceDefinitionSpec**: this
  is easy to mistake if you copy code that worked originally for a cluster CRD to a namespaced CRD. Always
  check that they agree.
- **Starting a Watcher() on a namespaced CRD before the namespace exists**: it's easy to jump the gun here,
  and we've seen some odd errors that probably need to be better processed in Hikaru. Regardless, a Watcher()
  on a namespaced CRD won't work if the namespace doesn't first exist.
- **The ObjectMeta name isn't the plural as specified in CustomResourceDefinitionNames**: when defining a CRD
  to K8s, you need to ensure that the value of the ``plural`` argument in the ``CustomResourceDefinitionNames``
  object is the same as the first part of the ``name`` given to the ObjectMeta for the ``CustomResourceDefinition``.
  We showed some techniques above to ensure tha the value is the saem for both of these in the examples above;
  it's best you adopt this or similar practices to ensure consistency.
- **Run set_default_release() BEFORE registering your CRD with register_crd_class()**: this is important if
  the release is for isn't the current default release (which is the highest numbered Kubernetes release 
  for which there is support in the Hikaru package). If you register before setting the default release, and
  your default release is lesser than the initial default, Hikaru will register your CRD according to the wrong
  release and it won't be able to find your class when it receives a message for it. In the examples above,
  the initial default release was rel_1_26, but all our CRDs were built against rel_1_23. Due to this, we needed
  to set the default release to rel_1_23 PRIOR to registering our CRD so that it would be viewed as part of the
  rel_1_23 release. You'll know if you have a problem of this type if Hikaru complains that it can't find a class
  for a specific version/kind.

Limitations
===========

This initial version of CRD support has some limitations; generally they shouldn't be a problem, but are listed
below so the user can plan accordingly.

Recursive definitions
---------------------

Though the typing hinting facility allows for the definition of directly or indirectly recursive classes,
Hikaru currently cannot process such definitions. In particular, ``get_crd_schema()`` will raise a recursion
error. This may be lifted in future releases.

dicts are str:str only
----------------------

Currently, Hikaru can only process attributes with dict type hints at ``dict`` or ``Dict[str, str]``. The value
of a key will be set up as a str. These are rendered as a property with the type ``object`` in the schema, which
is the same type as for a class. Hence, if you don't need dynamic key sets, you should consider representing
the property as a nested class instead of a dict.

Can't automatically create Hikaru classes from existing CRDs
------------------------------------------------------------

While Hikaru can read a ``CustomResourceDefinition`` from Kubernetes which will contain a schema, Hikaru is currently
unable to transform that schema back into a Python dataclass. This is a difficult problem to solve due to the
many ways that schema can be encoded in OpenAPI. This might get added as a feature at some future point, but will
almost certainly require a schema with a very specific organization.

Limits on the modifiers available to fine-tune attribute definitions
--------------------------------------------------------------------

Not every OpenAPI property modifier is currently available; this supported set will expand as this facility
matures.

No Unions
---------

OpenAPI allows a property to be of multiple types (anyOf); the corollary to this in Python type hinting is
to use ``typing.Union``. Union is currently not supported by Hikaru, but may be added at a future point.

No list operations
------------------

Some Kubernetes resource classes have a 'List' variant; for example, there are both Pod and PodList resources,
the latter of which is read-only. In many cases, these list resources are there to support Watch capabilities.
However, Watchers are already available for CRDs in Hikaru. Given this, there is currently no equivalent List
capability in Hikaru for CRDs, but this may be added as needs arise. Certainly it would be possible for a user
to create a 'List' variant of their own resource and then create a controller that returned appropriate lists
of the base resource.

No ObjectMeta-less reads
------------------------

In the CRUD methods exposed by Hikaru on core Kubernetes resources, the user is given two ways to specify the
name of the resource for read operations: they can fill in the ``name`` attribute of a resource's ``ObjectMeta``
object, or they can supply a keyword argument ``name`` to the ``read()`` call and behind the scenes the necessary
work is done to name the resource to read. Currently, Hikaru CRD support requires the use of the ``ObjectMeta``
approach for supplying the name. A later release will provide support for specifying the name via arguments to
the ``read()`` method.

No direct support for datetime attributes
-----------------------------------------

As mentioned previously, Kubernetes's API spec defines datetimes as strings with a date-time format. Due to earlier
issues with the datetime objects created by the Kubernetes Python API, Hikaru expresses datetimes as strings but
in a format easily parseable into datetime. With the addition of some of the added metadata used in CRD definition,
this restriction may change in the future.


