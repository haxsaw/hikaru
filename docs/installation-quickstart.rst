***************************
Installation and Quickstart
***************************

Installation
############

From PyPI, you can just use the normal ``pip install`` dance:

    ``pip install hikaru``

Or if installing from source,  cd into the project root an then you can install from setup.py:

    ``python setup.py install``

The project GitHub repository can be found at: https://github.com/haxsaw/hikaru

Quickstart
############

The following are the 'bread and butter' functions of Hikaru.

To read Kubernetes YAML documents into Hikaru Python objects:
*************************************************************

For loading Kubernetes YAML documents into live Hikaru Python objects, use the
``load_full_yaml()`` function:

.. code:: python

    from hikaru import load_full_yaml
    docs = load_full_yaml(path="<path to yaml file>")
    # 'docs' is a list of different doc 'kinds' such
    # as Pod, Deployment, etc

The objects in the resultant list will always have *kind* and *apiVersion*
attributes populat4ed. If any of the input YAML doesn't have these attributes for their
documents, Hikaru can't tell what classes to build. You can then use Kubernetes YAML
property names to navigate through the Python objects.

To write Kubernetes YAML documents from Hikaru Python objects:
==============================================================

You can print out the equivalent Kubernetes YAML from Hikaru Python objects with the
``get_yaml()`` function:

.. code:: python

    from hikaru import get_yaml
    # assume that 'p' below is an instance of the Pod class
    print(get_yaml(p))

The output YAML will start with a 'start of document' marker (---) and then the
YAML for the Hikaru objects will be printed.

To generate Hikaru Python source from Hikaru Python objects:
============================================================

If you want to convert your Kubernetes YAML to actual Hikaru Python source code, use
the ``get_python_source()`` function:

.. code:: python

    from hikaru import get_python_source, load_full_yaml
    docs = load_full_yaml(path="<path to yaml>")
    p = docs[0]
    # when rendering the Python source, you can indicate a
    # variable to assign the created object to:
    print(get_python_source(p, assign_to='x'))

This will output a PEP8-compliant set of Python. Generation may take a short while
depending on how many deeply nested Python objects are involved.

