********************
Patterns and Recipes
********************

Tweaking an existing Kubernetes config
--------------------------------------

One of the use cases for Hikaru is to provide a way to tweak some values in YAML
based on criteria such as environment (dev, test, prod, dr). Hikaru provides the
tooling for a broad set of such use cases, so we'll just look at one such use
here.

The metadata object's `labels` are used in a variety of different ways, from matching
up resources to providing the keys and values that can be used to query across an
entire Kubernetes estate to find objects linked in some way, for instance for monitoring
purposes, business alignment, or operational management.

Indeed, breaking down labels into discrete domains provides a way to structure the label
space in an operationally useful fashion, and can also segment responsibility for management
of the labels. However, if writing the full YAML for any given component, the YAML author
would normally be required to understand the all domains and ensure all labels for each
domain are correct. Worse, if something were to change, then all YAML documents would need
to be modified to reflect the change.

YAML templating systems often help with this; below we'll look at an approach that could be
used with Hikaru to segregate management concerns over the label space.

First, let's suppose we segregate the label space into three domains: application, environment,
and business unit:

  - The application domain is used to indicate how the components of the application find
    and interact with each other. These would be managed by the dev or devops teams.
  - The environment domain is used to indicate where the application is running, such as
    dev, test, prod, etc. This may entail different monitoring labels or provide different
    names for finding common services used by the application. These would be managed by
    the infrastructure teams.
  - The business unit domain is used to identify components of a business unit function.
    There may be a number of applications that go into a function, and hence this is an
    additional dimension to provide a function-centric view of resources, one that show
    what functions are impacted if specific components fail. These would be managed by
    business-aligned operations teams.

Each team that manages these domains creates separate YAML labels files that contain the
appropriate labels for the different aspects of their domain; these are kept in a directory
hierarchy like so:

.. code::

    domains
        |-- application
        |        |-- app1
        |        |-- app2
        |        |-- app3
        |-- environment
        |        |-- dev
        |        |-- test
        |        |-- prod
        |        |-- dr
        |-- business_unit
        |        |-- equities
        |        |        |-- trading
        |        |        |-- stock_loan
        |        |-- operations
        |        |        |-- settlement
        |        |        |-- asset_servicing
        |        |-- (and so on)

Each of those leaves indicates a file full of YAML labels, managed by a different group.
A single file would just have a labels mapping like so:

.. code:: yaml

    key1: value1
    key2: value2
    key_n: value_n

We could then easily build a pipeline app that augments the metadata's labels of a base
YAML file, writing the result to stdout, either for further processing or creating the
final YAML file to submit to Kubernetes. A simple version of that processing app,
`label_updater.py` could look like this:

.. code:: python

    import sys
    from hikaru import *

    def add_labels(label_file_paths, inyaml_file, outyaml_file):
        # get_processors() returns a list of processed YAML
        # we get the first since there's only one ([0] on the end)
        labels = []
        for p in label_file_paths:
            labels.append(get_processors(path=p)[0])
        tweaked_yaml = []
        for doc in get_full_yaml(stream=inyaml_file):
            for l in labels:
                doc.metadata.labels.update(l)
            tweaked_yaml.append(get_yaml(doc))
        outyaml_file.write("\n".join(tweaked_yaml))

    
    if __name__ == __main__:
        add_labels(sys.argv[1:], sys.stdin, sys.stdout)
        sys.exit(0)

Usage would just involve a list of the labels to apply in order:

.. code:: shell

    cat original.yaml | python label_updater.py domains/application/app2 domains/environment/prod domains/business_unit/operations/settlement > final.yaml

The output, `final.yaml`, is the one submitted to Kubernetes. This kind of approach can be
used with either YAML or Hikaru Python sources to augment or piece together larger configs
from separately managed and standardized parts.

Finding out the version of a loaded document
--------------------------------------------

Hikaru's `load_full_yaml()` can determine which model version of a document and
its objects to create while parsing, but you may want to be able to determine this
yourself if you want to customize processing for different versions. Often, you
can simply look to `object.apiVersion`, but sometimes this is addtionally coded with
the Kubernetes API group that the object is part of, which means you need to know
which group any object belongs to.

Hikaru provides the `process_api_version()` function to tease these apart, providing
the caller with a 2-tuple result, consisting of the group string followed by the the
version string:

.. code:: python

    docs = load_full_yaml(path='<path to some Kubernetes yaml>')
    for doc in docs:
        group, version = proces_api_version(doc.apiVersion)
        print(group, version)

Finding the version can be important in some of the other patterns discussed below.

Shutting up the linter
----------------------

Your IDE or linter may complain about the types of objects coming from ``load_full_yaml()``
when you assign them to a variable, especially if you use type annotations on the variable
so that you get the benefits of Hikaru's dataclasses. If you have a some code like the
following:

.. code:: python

    from hikaru import load_full_yaml
    from hikaru.model.rel_1_16 import Pod
    p: Pod = load_full_yaml(path='file-with-a-pod.yaml')[0]

You can get complaints for the last line as the types in the list returned by
``load_full_yaml()`` don't match the type annotation on ``p``.

To silence these complaints, you can use the ``cast()`` function from the ``typing`` module
to assure the type checker that these types are to match:

.. code:: python

    from typing import cast
    from hikaru import load_full_yaml
    from hikaru.model.rel_1_16 import Pod
    p: Pod = cast(Pod, load_full_yaml(path='file-with-a-pod.yaml')[0])

This will silence such complaints so that you are left with only meaningful type warnings.

Avoiding the version change trap
--------------------------------

So this is a cautionary tale that comes from Hikaru's own testing. It has to do
with the *default* version of Hikaru Kubernetes objects that you use versus
specifically named versions, and where you need to pay attention to what you create.

Suppose you had some Kubernetes YAML that starts like so:

.. code:: yaml

    apiVersion: apps/v1beta1
    kind: Deployment
    metadata:
      name: nginx-app-2
      labels:
        app: nginx

...and goes on from there. It's the only document in the YAML file. You want
to get your hands on it in Python, and so you load its file,
`deployment.yaml`, with `load_full_yaml()`:

.. code:: python

    from hikaru import *
    from hikaru.model.rel_1_16 import *
    doc = load_full_yaml(path="deployment.yaml")[0]

...and you want to get the equivalent Python source for this. So you use
`get_python_source()` to get the source that will recreate `doc`:

.. code:: python

    s = get_python_source(doc)

Being a cautious user, you decide to check to make sure that these two are
the same. So you add:

.. code:: python

    new_doc = eval(s, globals(), locals())  # eval the python in s
    if new_doc != doc:
        print("Not the same!")

When you run this, it does **indeed** print "Not the same!". You dump it into
the debugger and it seems all the fields are the same; you can't spot the
difference in the data that != says is there.

You then remember there's a ``diff()`` method on HikaruBase objects, so you
quickly type in:

.. code:: python

    print(doc.diff(new_doc))

which yields something like:

.. code:: 

    [DiffDetail(diff_type=<DiffType.ATTRIBUTE_ADDED: 0>, cls=<class 'hikaru.model.rel_1_16.v1.v1.ObjectMeta'>, formatted_path="ObjectMeta.labels['b']", path=['labels', 'b'], report="Key added: self.ObjectMeta.labels['b'] is 2 but does not exist in other", value='2', other_value=None)]

The report says 'Incompatible:self is a Deployment while other is a Deployment'? Wait, are they the same or not?

But the fact that diff says the classes are different gets you to thinking, and so you decide
to look at the class objects:

.. code:: python

    doc.__class__, new_doc.__class__

..and there, you finally see it:

.. code:: 

    (<class 'hikaru.model.v1beta1.Deployment'>, <class 'hikaru.model.v1.Deployment'>)

The Deployment class is being loaded from two different version modules. How is that
happening?

When you use `load_full_yaml()`, it looks at the kind/apiVersion information in the document and
loads the proper module and class from what it finds in those properties. However, the import
statement `from hikaru.model.rel_1_16 import *` loads the v1 model objects *by default* into whatever
scope the statement is in, in this case the global scope. So when you use `eval()` to execute
the Python, it looks first to the local and then the global scope for the definition of
`Deployment`, and what it finds is the one from the wild import, **not** the one named in the
document and used by `load_full_yaml()`.

So how to get around this? Happily, there are a lot of approaches. One way is to not
dynamically execute strings containing Python and instead write them to a file that has
the proper import statement; in this case it would be:

.. code:: python

    from hikaru.model.rel_1_16.v1beta1 import *
    # and don't do an 'from hikaru.rel_1_16 import *' here; if you want other
    # names import them specifically
    # ...and then the generated code goes here

That's one way. If you want to use dynamic code, perhaps in testing scenarios,
here's a succinct approach. You use the symbols in the specific module as a
way to provide the local namespace. So first you import all the model modules
*without wild imports*:

.. code:: python

    from hikaru import load_full_yaml, process_api_version, get_python_source
    from hikaru.model.rel_1_16 import v1
    from hikaru.model.rel_1_16 import v1beta1
    # and the same for the rest of the model version modules

Then make a mapping of version numbers to modules:

.. code:: python

    version_modules = {'v1': v1,
                       'v1beta1': v1beta1,
                       # and so on
                      }

And the rest of the code then depends on getting the version number out of the
document and using that to select the proper module from `version_modules`:

.. code:: python

    doc = load_full_yaml(path="deployment.yaml")[0]
    _, version = process_api_version(doc.apiVersion)
    s = get_python_source(doc)
    new_doc = eval(s, globals(), vars(version_modules[version]))
    if doc == new_doc:
        print("okey dokey")

This approach only works when loading full Kubernetes documents, those with both
the `kind` and `apiVersion` properties at the top level. If you are loading document
fragments, you'll already be using the specific class's `from_yaml()` method, so you
just need to be sure of which version of that class to use.

Regardless of the approach, the important point to remember here is that
if you use the `from hikaru.model.rel_1_16 import *` form, you will default to all `v1` objects,
so you should be mindful of when you might actually want to make instances of 
a different version.

Mass migrating YAML to Hikaru
-----------------------------------

If you have a large body of Kubernetes YAML that you'd like to convert to Hikaru, perhaps
to run an analysis on it or to migrate away from YAML, it's a pretty simple matter use
Python's pathlib to iterate over a directory of YAML and turn it into Hikaru Python source
(this example ignores different apiVersions):

.. code:: python

    from pathlib import Path
    from hikaru import load_full_yaml, get_python_source
    
    yaml_dir_path = "<some directory path>"
    for i, p in enumerate(Path(yaml_dir_path).iterdir()):
        if not (p.is_file() and str(p).endswith('.yaml')):
            continue
        docs = load_full_yaml(path=str(p))
        name = f"{p.parts[-1].split('.')[:-1][0]}.py"
        fname = Path(yaml_dir_path) / name
        f = fname.open('w')
        print("from hikaru.model.rel_1_16 import *\n\n", file=f)
        for j, doc in enumerate(docs):
            s = get_python_source(doc, assign_to=f"obj{j}",
                                  style="black")
            print(s, file=f)
            print("\n\n", file=f)
        f.close()

This creates Python files with the same name as their YAML source files, and sequentially assigns each YAML document to 'obj1', 'obj2', etc. Once verified, you can easily separate
out the Python from YAML.

Checking types on a Hikaru model
--------------------------------

If you want to be sure that you've filled out a config model properly, at least from the types
perspective, you can use `get_type_warnings()` to look for issues:

.. code:: python

    # assume the object we want to check is 'm'
    warnings = m.get_type_warnings()
    for w in warnings:
        print(f"Class:{w.cls.__name__}, attr:{w.attrname}, warning:{w.warning}")

In general, you can ignore warnings regarding a type known as IntOrString, as long as
the value you are providing is an int or string. This is a current limitation.

Checking resource limits on a config
------------------------------------

While this example focuses on resources, this style can be used for any sort of automated
checks you'd care to perform.

Suppose you wanted to ensure that resource limitss were always running within certain bands or
followed certain standard configuration. You could use pre-defined objects for resources that
are just plugged into a Hikaru config model, but you can also use the `find_by_name()`
method to locate resources in any model print them out:

.. code:: python

    from dataclasses import as dict
    from pprint import pprint
    from hikaru import *

    def check_model_resources(model):
        matches = model.find_by_name('resources', following="containers")
        for m in matches:
            print(f">>>Found resources at {m.path}")
            pprint(asdict(model.object_at_path(m.path)))
            print()

You would then just pass in whatever Hikaru object you wished into `check_model_resources()`
and would get a report of any resources inside containers.
