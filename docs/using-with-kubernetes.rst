****************************
Using Hikaru with Kubernetes
****************************

Starting with release 0.4 of Hikaru, you can now use Hikaru objects to interact with
Kubernetes using the underlying Kubernetes Python client. Depending on your use case and
interaction method, it can be possible to not use a single Kubernetes Python call and work
entirely in Hikaru objects. Hikaru also provides a way for the user to explicitly set the
``kubernetes.client.ApiClient`` instance to use when interacting with Kubernetes.

Hikaru provides two levels of interface to the underlying Kubernetes client:

- A higher-level `CRUD`-style set of instance methods that have consistent names and
  behaviours across all top-level Hikaru objects (that is, subclasses of
  :ref:`HikaruDocumentBase<HikaruDocumentBase doc>`) but which hide some of the details of the underlying operations, and
- A lower-level (but not much lower) set of instance and class methods that are direct
  analogs of the operations defined in the K8s swagger file; the names of these methods
  follow the operationIDs in the swagger file, and expose return codes, headers, and allow
  for async operation.

The CRUD operations are simply veneers over the lower-level methods exposed by Hikaru, and
should provide the user a simplified API to work with.

Hikaru CRUD methods
********************

Hikaru implements a CRUD method when there is a suitable matching lower-level method to
base it on. If no such method exists, then a CRUD method won't be generated. For example,
the ``ComponentStatus`` object only has a ``read()`` method defined for it.

All Hikaru CRUD methods work on single objects with the exception of objects that are
inherently containers for collections of objects such as ``PodList``. Outside of these
objects, there is no CRUD support for getting lists of objects-- consult the lower-level
API for methods that support fetching lists.

All Hikaru CRUD methods share share the following characteristics:

- they are all instance methods (lower-level methods are a mix of instance and static
  methods),
- they all have ``self`` as their return value,
- they also all modify ``self`` in place if the underlying method returns an object of the
  same type as ``self``; the return's values are merged into self using the ``merge()``
  method of ``HikaruBase``,
- they can only be run in blocking mode,
- they support the other optional parameters of the underlying call,
- they duplicate the docstring of the underlying low-level call so you review the doc
  for each method.

Each of the methods are discussed below.

create()
********

The ``create()`` method provides a way to create a resource in Kubernetes. This is an independent
action from creating the Hikaru object; you must first create the Hikaru object, and then call
``create()`` on it to create it within Kubernetes.

Typically, you create the Hikaru object either using the Python model objects or by creating the
object by loading YAML, JSON, or a Python dict. You may tailor the object at any point, and then
instruct Kubernetes to create it with ``create()``. For example, if you had a ``Pod`` Hikaru
object, you can ask Kubernetes to create it with:

.. code:: python

    pod.create()

For namespaced resources, you can leave the namespace out of the object's metadata
(ObjectMeta) and instead supply it as a keyword argument to ``create()``:

.. code:: python

    pod.create(namespace='some-name')

Bear in mind that the same restrictions apply as in the underlying Kubernetes client, namely
that if you supply a namespace as an argument, the metadata for the object either must not have
a namespace value or else it must have the same value as the argument.

If Kubernetes returns the same type of resource as was used in the ``create()`` call, then the
values of those fields are merged into the original object. Note that this frequently isn't the
final state-- trying to modify the object now and then issuing an ``update()`` will often result
in an error as the returned value from ``create()`` may not be referring to the most recent state
of the object. Typically you'll need to call ``read()`` first.

read()
******

The ``read()`` method provides you a way to acquire the details of an existing resource.
You typically have a couple of ways to read: either by supplying an object that contains a
name and/or namespace (as appropriate), or by supplying these as keyword arguments. So these
two calls to read the details of a Pod are equivalent:

.. code:: python

    p = Pod(metadata=ObjectMeta(name='theName', namespace='the-namespace')).read()
    # and:
    p = Pod().read(name='theName', namespace='the-namespace')
    # or, for a Pod that already has the name/namespace in its metadata:
    p.read()

Or, you could have the name in the Pod and supply the namespace in the read line, as long as the
namespace in the Pod is None or the same value as provided in the arguments.

As mentioned above in the section on ``create()``, you generally are advised to invoke read prior
to any update operations to ensure you are only trying to make changes on the latest version of
the pod.

update()
********

Calls to ``update()`` behave like calls to ``create()`` , although you generally
don't need to specify a ``namespace`` parameter since you are usually updating with an object
in which the namespace was previously specified. However, you can supply the value if needed using
the ``namespace`` keyword argument to ``update()``:

.. code:: python

    pod.update(namespace='whatever')

patch vs replace
----------------

The Kubernetes spec identifies two different operations that could be thought of as implementing
`update` semantics, **patch** and **replace**. Since **replace** is meant to fully replace an
existing resource with another one, it was decided that the ``update()`` method would be a
wrapper around the the **patch** operation, since patching an existing resource more closely
matches the semantics of ``update()``. You can still access the replace method for the resource
by using the lower-level API.

update() and Context Managers
------------------------------

Any ``HikaruDocumentBase`` subclass that has an ``update()`` method is also a context manager.
When the ``with`` block that the object manages closes, the object automatically calls the
``update()`` method on the object. So constructions like the following can be created:

.. code:: python

	with Pod().read(name='thename', namespace='the-namespace') as p:
		p.labels['new-label'] = 'value'
		# and other actions that change the content of the Pod p
		
	# once here, the Pod p has automatically invoked update()
	
The instance that serves as the context manager can come from any usual source. So if a
previously created Pod was stored as YAML, you can load it and use that to manage the
context:

.. code:: python

	p = load_full_yaml(path="/some/path")[0]
	with p.read() as pod:  # always read before update to make sure you have the latest rev!
		# and carry on modifying pod here...
		
There is also a helper function, :ref:`rollback_cm()<rollback_cm doc>`, which sets up the context manager to roll
back to the original state of the object if an exception is raised inside the ``with`` block.
This allows you to restore your object to the original condition from when the with block
started in the case of an error. Applying this function to the example from above, we'd then
have:

.. code:: python

	p = load_full_yaml(path="/some/path")[0]
	try:
		with rollback_cm(p.read()) as pod:
			# and carry on modifying pod here...
	except:
		# pod (p) will have the same content as at the start of the with block

delete()
********

The ``delete()`` method allows you to delete the modelled resource in Kubernetes. This does
not delete the Hikaru object; it simply gets rid of the underlying Kubernetes resource.

Unlike ``update()``, ``delete()`` doesn't need the lastest version of the object to perform
its actions; in general, all is necessary are the name and namespace (if applicable) for the
resource in question. That allows issuing a ``delete()`` from an anonymous object:

.. code:: python

	Pod().delete(name='podname', namespace='podnamespace')
	
...as well as deleting from a resource that has metadata with both name and namespace filled in:

.. code:: python

	# let's assume we previously persisted a Pod that we had created with its name
	# and namespace we can then load and delete it
	p = load_full_yaml(path='/path/to/saved/pod')[0]
	p.delete()
	
...or the uselessly verbose:

.. code:: python

	p = Pod(metadata=ObjectMeta(name='podname', namespace='podnamespace'))
	p.delete()
	



Hikaru low-level methods
*************************

The lower-level Hikaru methods are all direct analogs of the operations defined in the 
Kubernetes swagger API specification file. The names of the methods are taken from the
``operationID`` property of each operation in that file, although in some cases version
information has been scrubbed out of the name. Each method supports all of the parameters
documented in that file, including the flag to indicate asynchronous operation.

All methods return a :ref:`Response<Response doc>` object. These objects contain
references to the returned result code, HTTP headers, and any object returned by
Kubernetes (as a Hikaru object).

If you requested an operation to be done asynchronously using the ``async_req=True``
argument,
then the above three attributes aren't filled out when the method returns and instead the
Response can be used
to sync with the arrival of the response data with a calling thread. Using the ``get()``
method call on the
Response object, you can block the caller (with optional timeout) until Kubernetes
responds to your request. When get() returns, the code, object, and header fields will be
filled out in the Response object. The ``get()`` call also returns a three-tuple
containing this same data.

To illustrate this, we'll start with a fully explicit verion with commented interaction and
then show how you can pare it down based on defaults. In this example,
we'll create and delete a Pod using the K3s lightweight Kubernetes package.

.. code:: python

    import time
    from hikaru import load_full_yaml, Response
    from hikaru.model import Pod
    # here are the two bits we need from K8s
    from kubernetes import config
    from kubernetes.client import ApiClient
    
    
    def do_it():
        # configure the Kubernetes client library by telling it where
        # to find the K3s configuration file
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        # create a client
        client = ApiClient()
        # load a Pod from YAML
        f = open('pod.yaml', 'r')
        pod: Pod = load_full_yaml(stream=f)[0]
        # inform the Pod object about the client
        pod.set_client(client)
        print("creating")
        # use the createNamespacedPod() instance method to create the pod
        # and get the full Pod definition back in the response
        result: Response = pod.createNamespacedPod(namespace='default')
        newpod: Pod = result.obj
        time.sleep(5)  # smoke 'em if ya got 'em...
        print("deleting")
        # use the static method deleteNamespacedPos() to delete the
        # previously created Pod, passing the API client object into
        # the call
        fres: Response = Pod.deleteNamespacedPod(newpod.metadata.name, 'default',
                                                 client=client)
        return fres
    
    
    if __name__ == "__main__":
        do_it()

Notice that for instances of :ref:`HikaruDocumentBase<HikaruDocumentBase doc>`
subclasses we can ``set_client()``
on the instance or pass the client in as a keyword parameter. For static methods on
a subclass itself you must pass the client in (if you don't use a default client).

Using a default client allows you to shorten the above. Once you've told
the Kubernetes library where the configuration file is, you no longer need to explicitly
make client objects-- if an object is needed but not supplied, one is created for you
by the underlying system. That reduces the above to:

.. code:: python

    import time
    from hikaru import load_full_yaml, Response
    from hikaru.model import Pod
    from kubernetes import config
    
    
    def do_it():
        config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
        f = open('pod.yaml', 'r')
        pod: Pod = load_full_yaml(stream=f)[0]
        print("creating")
        result: Response = pod.createNamespacedPod(namespace='default')
        newpod: Pod = result.obj
        time.sleep(5)
        print("deleting")
        fres: Response = Pod.deleteNamespacedPod(newpod.metadata.name, 'default')
        return fres
    
    
    if __name__ == "__main__":
        do_it()
    
All we need to is load the configuration file and the underlying Kubernetes system will
handle making clients.

