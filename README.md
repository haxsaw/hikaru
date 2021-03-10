# hikaru

hikaru is a tool that provides you the ability to easily shift between YAML and
Python representations of your Kubernetes config files, as well as providing some
assistance in authoring these files in Python, opens up options in how you can assemble and
customise the files, and even provides some programmatic tools for inspecting
large, complex files to enable automation of policy and security compliance.

### From Python

hikaru uses type-annotated Python dataclasses to represent each of the kinds of
objects defined in the Kubernetes API, so when used with and IDE that understands
Python type annotations, hikaru enables the IDE to provide the user direct assistance as
to what parameters are available, what types each parameter must be, and which
are optional. Assembled Kubernetes object can be rendered into YAML that can be
processed by regular Kubernetes tools.

### From YAML

But you don't have to start with authoring Python: you can use hikaru to parse
Kubernetes YAML into these same Python objects, at which point you can inspect
the created objects, or even have hikaru emit Python source code that will re-
create the same structure but from the Python interface.

### To YAML, Python, or JSON

hikaru can output a Python Kubernetes object as Python source code, YAML, or JSON
(going to the other two from JSON is coming), allowing you to shift easily
between representational formats for various purposes.

### Alternative to templating for customisation

Using hikaru, you can assemble Kubernetes objects using previously defined library
objects in Python, craft replacements procedurally, or even tweak the values of
an existing object and turn it back into YAML.

### API Coverage

Currently, hikaru supports all objects in the OpenAPI Swagger spec for the
Kubernetes API except those in the 'apiextensions' group. There are recusively
defined objects in that group which can neither be topologically sorted or
represented by Python dataclasses, so an alternative for those objects is being
investigated. But all other objects in the swagger file are available, as well
as version v1 through v2beta2 of the API's objects.

Additionally, the Kubernetes Python client includes a test that assumes the
availability of support for a 'List' kind, however the swagger file contains
no support for a List object.

## Usage

To create Python objects from a Kubernetes YAML source, use ``load_full_yaml()``:


    from hikaru import load_full_yaml
    
    docs = load_full_yaml(stream=open("test.yaml", "r"))
    p = docs[0]

``load_full_yaml`` loads every YAML document in a YAML file and returns a list
of the resulting hikaru objects found. You can then use the YAML property
names to navigate the resulting object. If you assert that an object is of a
known object type, your IDE can provide you assistance in navigation:


    from hikaru.model import Pod
    assert isinstance(p, Pod)
    print(p.metadata.labels["lab2"])
    print(p.spec.containers[0].ports[0].containerPort)
    for k, v in p.metadata.labels.items():
        print(f"key:{k} value:{v}")
        
You can create Kubernetes objects in Python:

    from hikaru.model import Pod, PodSpec, Container, ObjectMeta
    x = Pod(apiVersion='v1', kind='Pod',
            metadata=ObjectMeta(name='hello-kiamol-3'),
            spec=PodSpec(
                containers=[Container(name='web', image='kiamol/ch02-hello-kiamol') ]
                 )
        )
        
...and then render it in YAML:

    from hikaru import get_yaml
    print(get_yaml(x))

...which yields:

    ---
    apiVersion: v1
    kind: Pod
    metadata:
      name: hello-kiamol-3
    spec:
      containers:
        - name: web
          image: kiamol/ch02-hello-kiamol
