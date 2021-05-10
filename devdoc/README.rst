***********************************
Hikaru Developers/Maintainers Notes
***********************************

---------------------------
Setting up your environment
---------------------------

Maintainers will want to add some packages to their environment to facilitate
documentation generation and testing. There's a supplemental requirements file in the
project's root, so cd there and install it with:

    ``pip install -r maintainers_requirements.txt``

--------
Testing
--------

.. note::
    To perform any testing on an uninstalled verison of Hikaru, be sure to set your
    PYTHONPATH to the project root first, or else all tests will fail as python
    won't know where to import Hikaru from.

Unit testing
-------------

To do unit testing, run the following in the ``tests`` subdirectory:

    ``pytest --cov=hikaru --cov-report=term-missing *.py``

Integration testing
-------------------

.. note::
    Integration testing requires an underlying Kubernetes system, or a compliant
    Kubernetes alternative. Hikaru was integration tested using the excellent
    lightweight `K3s <https://k3s.io/>`_ system. The integration tests are coded
    to work with that system installed on Linux or a \*nix alternative, in particular
    the location of the config file that the underlying K8s Python client library
    needs to use to connect with Kubernetes. You may have to edit this file location
    if you use a different Kubernetes system or have other requirements.

Integration tests are also run from within the ``tests`` subdirectory, but live in the
``e2e`` directory below that; this is so that unit tests can be run indpependently of
a Kubernetes installation.

To run the integration tests, run the following from with ``tests``:

    ``pytest --cov=hikaru --cov-report=term-missing e2e/*.py``

If you want to run everything to get a comprehensive coverage report, you can run
pytest so that it appends coverage data, or else just run:

        ``pytest --cov=hikaru --cov-report=term-missing *.py e2e/*.py``

from within tests.

-------------------------------
Sphinx documenation
-------------------------------

The ``docs`` subdirectory contains all the source .rst files and the Sphinx project
files; cd into ``docs`` and run:

    ``make html``

to build the doc from the .rst files. If you have the necessary Latex files, you can also build a PDF with:

    ``make latexpdf``

Consult the Sphinx documentation for your platform to see how to do this. You can clean out all built documentation first with:

    ``make clean``

from within the ``docs`` subdirectory.

--------------------
Building the models
--------------------

Notes on building the models of Kubernetes objects can be found 
in the `Notes on building the model pkg.txt <Notes%20on%20building%20the%20model%20pkg.txt>`_
file in this directory.


