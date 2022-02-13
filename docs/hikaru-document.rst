*****************************
The HikaruDocumentBase class
*****************************

:ref:`HikaruDocumentBase<HikaruDocumentBase doc>` is a subclass of
:ref:`HikaruBase<HikaruBase doc>` that is used as the
base class for any K8s
object that appears as a top-level object in the K8s API. By *top-level* we mean any object which is 
provided as an argument to a Kubernetes API call, or any object that is returned by a Kubernetes API call.
These objects are special in that they all contain both the ``apiVersion`` and ``kind`` attributes, and
Hikaru uses the presence of the attributes to determine what classes to make into subclasses of
HikaruDocumentBase rather than just HikaruBase.

By and large, Hikaru adds only a small amount of functionality to HikaruDocumentBase, most notably in
the form of support for associating a Kubernetes Python API client object with its instances so that 
subclasses then have everything needed to make calls into the Kubernetes Python client to perform
operations involving its subclasses.

It's the subclasses of HikaruDocumentBase that are more interesting. During the Hikaru build process,
Hikaru seeks to identify actions defined in the Kubernetes Swagger spec file as being in relation to
a particular HikaruDocumentBase subclass, and creates methods on such subclasses that invoke the the
appropriate Kubernetes Python API methods to implement the action. This provides an alternate
organization of Kubernetes actions-- instead of being centered on the group that the action is a
member of, the action is associated with the object on which the action applies. The intent is to
provide a more intuitive association of actions with the objects the actions involve.

Methods are associated with a class based on one of three criteria:

- The class is an input parameter to the underlying API call; these become instance methods.
- The class is a result value from the underlying API call; these become ``staticmethods``.
- The method name seems to indicate that it would be better suited to be associated with a different
  class than the one used in either the input parameters or the responses; these also become ``staticmethods``.

So for example, the ``createNamespacedPod()`` method requires a Pod as an input parameter, so this is
treated as an instance method on the Pod class. The Pod object itself provides the values for the input
parameter.

In another example, ``deleteNamespacedPod()`` doesn't require a Pod as input, only a few select fields
from a Pod object. The the Swagger spec indicates that a Status object is the result of this call, but
Hikaru determines that Pod is a better home for this method, and so it attaches this as a ``staticmethod``
to the Pod class rather than a method on the Status class.

In this fashion, Hikaru associates all actions that impact a particular object to the object itself,
which can make it easier to find the action that you are looking for, especially since it ignores the
boundaries of groups. Additionally, all descriptive text in the Swagger file for the action (method)
and its arguments included in the docstring for the method, so you have the relevant reference
material to hand. Finally, all arguments to the method use type annotations so that IDEs are able to
provide additional assistance in using the methods.

.. note::

    In terms of generated method names, it was decided that an approach that eased
    transition best for someone familiar with the REST API would be chosen, and hence method names
    are kept in their original camel case rather than  transformed to a PEP8-compliant
    name with embedded underscores.

Method responses and the Response object
----------------------------------------

Every method returns a Hikaru :ref:`Response<Response doc>` object, which wraps up the response code, any text message,
and any returned objects. If the call was made non-blocking, then the Reponse object serves as a proxy
for the underlying thread-like object which is responsible for completing the call. By calling ``get()``
on the Response object, the caller will block until the call completes, at which time
a three-tuple will be returned that contains the returned object, code, and headers
from the response.

An example of how to use these objects and their methods when interacting with Kubernetes is shown
in the section :ref:`Using Hikaru with Kubernetes<Using Hikaru with Kubernetes>`.

The Response class uses Python type annotations to designate it as a generic type. The type parameter
is used to establish a type on the ``obj`` attribute of instances of Response, which then allows this
to be assigned to a type-annotated variable without casting. All methods that return Response objects
now add in the expected type for ``obj`` as part of theirs signature.

