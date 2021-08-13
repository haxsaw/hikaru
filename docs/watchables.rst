*******************************************
Watchables: Monitoring Kubernetes Activity
*******************************************

=======
Intro
=======

The K8s API includes a set of interfaces that allow you receive events
describing the activities that K8s is undertaking. The general term for these
are **watches**, and there are a variety of ways you can tune watch activities.

Hikaru provides a simplifying interface on top of these basic facilities, reducing the 
knowledge you must have of watchable classes, group API objects, and watch interface
semantics required to successfully set up watches on a K8s infrastructure.

====================
The `watch` module
====================

You access these capabilities through the `hikaru.watch` module. Besides knowing the objects
you want to watch, there are only three classes in the `watch` module that you need to interact
with:

- The ``Watcher`` class provides a way to set up a stream of events on single kinds of K8s
  objects such as Pods or Nodes. Once created, instances can be used to stream updates on the
  watched resource kinds.
- The ``MultiplexingWatcher`` class provides a container for Watcher classes that produces a
  single stream of events for multiple kinds of resources.
- The ``WatchEvent`` class is the container object in which watch events are delivered; it
  contains an indication of the type of event (ADDED, MODIFIED, DELETED) and a Hikaru model
  instance of the type indicated during the Watcher's creation.

======================
A simple example
======================

Here's a minimal example that prints out some Pod metadata for Pod events across all
namespaces:

.. code:: python

    from kubernetes import config
    from hikaru.model.rel_1_17 import Pod
    from hikaru.watch import Watcher
    
    def pod_watcher():
        # config file location on my dev system:
        config.load_kube_config(config_file='/etc/rancher/k3s/k3s.yaml')
        watcher = Watcher(Pod)
        for we in watcher.stream():
            p: Pod = we.obj
            print(f"{we.etype}, {p.metadata.namespace}, {p.metadata.name}")
    
    if __name__ == "__main__":
        pod_watcher()

The line ``watcher = Watcher(Pod)`` creates a watcher for `Pod` events across all namespaces,
and ``watcher.stream()`` creates a generator that you can iterate over as it yields up
``WatcherEvent`` instances, here the ``we`` variable in the for loop. The ``obj`` attribute is a
reference to the Hikaru model object that was sent from K8s, and the ``etype`` attribute
contains one of the strings ADDED, MODIFIED, or DELETED to indicate what action was taken
relative to the resource in obj.

On my dev system, I get repeated sets of three lines for the currently existing Pods in the
K3s system I work on; these look like the following:

.. code::

    ADDED, kube-system, local-path-provisioner-5ff76fc89d-n5mr9
    ADDED, kube-system, coredns-854c77959c-mdw6w
    ADDED, kube-system, metrics-server-86cbb8457f-lgmgq
    ADDED, kube-system, local-path-provisioner-5ff76fc89d-n5mr9
    ADDED, kube-system, coredns-854c77959c-mdw6w
    ADDED, kube-system, metrics-server-86cbb8457f-lgmgq

I get the same three lines repeatedly because of the default values of the keyword arguments
to ``Watcher`` and the initiation of the `stream()`. We'll go into
these details below, but we can change this to stop this behaviour by providing the
Watcher a ``timeout_seconds`` argument with a value of ``None``:

.. code::

        watcher = Watcher(Pod, timeout_seconds=None)

This results in getting these initial lines only once, and then lines for any new events that occur.

======================
Working with Watchers
======================

In Hikaru, a ``Watcher`` provides a control abstraction over top of the watch facilities in
the underlying K8s Python client. It not only wraps and exposes the underlying semantics, it
implements some other common patterns on top of the underying watchers that allows your code
to be a bit simpler.

A K8s `watch` also produces a generator which may block until an event arrives. Hikaru's
``Watcher`` manages this generator, and may restart it on timeouts or tell it to pick up with the most recent version of a resource, depending on how you configure it.

Key arguments when creating a ``Watcher``
---------------------------------------

The main documentation for the ``Watcher`` class goes into each optional creation argument
in detail, but two are worth going into more detail here as their interpretation can have
some subtleties.

- The ``timeout_seconds`` parameter instructs what timeout to set up for the underlying K8s
  watch object. The default value of 1 means that after a second of being idle the underlying
  generator will terminate. What the ``Watcher`` instance does if the underlying watch timesout
  depends on how you instructed the streaming operation to behave. If you supply a value of None
  for this argument then the underlying watch generator never times out. It can be good
  to have a timeout of 1 second as that gives the ``Watcher`` instance the opportunity to kill
  the underlying watch, otherwise you have to wait until it delivers an event in order to stop
  it.
- The ``resource_version`` parameter tells the underlying watch what version of the resource is
  *older* than the versions you want to consider. In otherwords, setting this to an integer or
  numeric string tells the watch that you don't want any events for the resource whose version is
  the same or less than the version provided. If you don't set any resource, how the `Watcher`
  behaves while streaming depends on the parameters to the ``stream()`` call.

So, in above example, when we created the `Watcher` with just the ``Pod`` argument, the
``timeout_seconds`` value was 1 and we didn't specify any resource_version. This causes K8s to send
us events for the currently operating Pods. After a second of no further events, the underlying
watch times out and stops, but because of the default arguments to ``stream()`` (more on these below),
the watch is restarted and the same events are sent again. This is why there is the repeated listing
of the same three pods. When we provide the value None for ``timeout_seconds``, the underlying watch
never times out and hence we see only the three Pod events one time.

Streaming events
----------------

Once you have created a ``Watcher``, you're ready to start streaming events with the ``stream()``
method. This method has two arguments that govern its operation:

- The ``manage_resource_version`` argument is a bool that tells the Watcher if you want it to
  manage the underlying watch in terms of what values to set for resource_version as the ``Watcher``
  operates the watch. This defaults to False, so a ``Watcher`` normally does nothing about managing
  the resourceVersion of events, and just takes whatever is sent from K8s.
- The ``quit_on_timeout`` argument is a bool that tells the ``Watcher`` how to behave if the
  underlying watch times out. The default, False, tells the ``Watcher`` to restart the watch if
  it times out. This is what contributed to our initial example from above repeatedly restarting
  the underlying watch: the watch had a default timeout of 1 second, and after a second of
  inactivity the watch exited. But since quit_on_timeout defaults to False, the `Watcher`
  instance restarts the underlying watch which runs again as if it was the first time.

The interaction of the ``resource_version`` argument to the ``Watcher`` constructor and the
``manage_resource_version`` argument to the `stream()` instance method
can be subtle; you sometimes have to think about what's happening underneath to be
comfortable with the results you see, or to know what combination of argument values you need to get
the behaviour you want. The table below explains what happens with each combination when streaming
so you can get the results you want (the argument 'manage_resource_version' is rendered as
'manage resource version' so that the first column isn't too wide):

.. csv-table:: **Resource Version Impacting Arguments**
   :file: managed-resource-version-matrix.csv
   :header-rows: 1
   :stub-columns: 1
   :widths: 20,40,40
   :class: longtable

Stopping a ``Watcher``
-----------------------

Once ``stream()`` is activated, it will continue to emit events subject it how its timeouts and
resourceVersion management have been configured as discussed above. To stop the stream, you should
invoke the `Watcher`'s ``stop()`` method. This method can be invoked while processing an event received from the ``stream()`` generator, or may be invoked from another thread.

.. note::

    If invoked from another thread, the ``stop()`` won't be acted upon until the underlying watch
    produces a new event and the ``Watcher`` can regain control.

If run in a ``for`` loop, a ``stream()`` can of course also be stopped by simply ``break`` ing out
of the loop. However, if you can bother to have a ``break``, it is just as easy to invoke ``stop()``.

A stopped ``Watcher`` can be started again with a new call to ``stream()``.

Namespaced and unnamespaced; what can be watched?
-------------------------------------------------

The underlying K8s APIs have different endpoints for narrowing a watch down to resources in a specifi
namspace. So for example, there are different endpoints to call if you want to watch Pod events
across all of K8s vs Pod events from a specific namespace.

Additionally, there are some K8s resources that don't have namespaces associated with them (such
as Nodes), hence they only have a single API endpoint available for watches.

Hikaru provides some assistance in creating code in these spaces through a few different means:

- First, if a Hikaru model class doesn't support any watches, a ``TypeError`` is raised when you try
  to create a ``Watcher`` on that class.
- Second, you can indicate you want to use a namespaced ``Watcher`` simply by supplying the ``namespace`` keyword argument a value when creating a new ``Watcher``. If the model class you
  supply doesn't support namespaced watches, a ``TypeError`` is raised.
- Third, you can get some help in remembering what classes support namespaced and unnamespaced
  watches by using the objects in the ``watchables`` module that accompanies each model version
  module in a version package.
- Finally, from the perspective of creating a ``Watcher``, both the singlular item and item list
  version of Hikaru model objects can be used when building a ``Watcher``. So for example, you
  can interchangeably use ``Pod`` and ``PodList`` to get a list of Pod ``WatchEvents`` from
  a ``Watcher``.

Let's look at these in turn.

Since only ``HikaruDocumentBase`` subclasses can potentially be watched, using anything else
will result in a ``TypeError``:

.. code:: python

    >>> from hikaru.watch import Watcher
    >>> from hikaru.model.rel_1_17.v1 import ObjectMeta
    >>> w = Watcher(ObjectMeta)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/haxsaw/hikaru/hikaru/watch.py", line 207, in __init__
        raise TypeError("cls must be a subclass of HikaruDocumentBase")

Additionally, the class must support watches:

.. code:: python

    >>> from hikaru.model.rel_1_17.v1 import SelfSubjectRulesReview
    >>> w = Watcher(SelfSubjectRulesReview)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/haxsaw/hikaru/hikaru/watch.py", line 220, in __init__
        raise TypeError(f"{cls.__name__} has no watcher support")
    TypeError: SelfSubjectRulesReview has no watcher support

The Hikaru won't let you try to create a namespaced ``Watcher`` on classes that only support
unnamespaced watches:

.. code:: python

    >>> from hikaru.model.rel_1_17.v1 import Node
    >>> w = Watcher(Node, namespace='will-it-blend')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/haxsaw/hikaru/hikaru/watch.py", line 216, in __init__
        raise TypeError(f"{cls.__name__} has no namespaced watcher support")
    TypeError: Node has no namespaced watcher support

So in general, you can check pretty quickly whether or not the class you want to watch supports
the operations you have in mind.

Second, you can easily select namespace-bound ``Watcher``s simply by providing a value for the
``namespace`` argument:

.. code:: python

    >>> from hikaru.model.rel_1_17.v1 import Pod
    >>> w = Watcher(Pod, namespace='some-business-unit')
    >>>

All events streamed from such a `Watcher` will only be from the indicated namespace.

Third, you can get some hints as to which classes can be watched with/without namespaces by
using the `watchables` module:

.. code:: python

    >>> from hikaru.watch import Watcher
    >>> from hikaru.model.rel_1_17.v1 import watchables
    >>> w = Watcher(watchables.Watchables.Pod)
    >>> # or, for a namespaced Watcher
    >>> w = Watcher(watchables.NamespacedWatchables.Pod,
                    namespace='some-business-unit')
    >>>

Each version package (v1, v1beta1, etc) will contain a `watchables` module if there are any model
objects in that version that can be watched. This module contains two classes:

- **Watchables**, which contains attributes that are model classes that can be watched `without` a
  namespace.
- **NamespacedWatchables**, which contains attributes that are model classes that can be watched
  `with` a namespace.

The attributes on these classes are simply references to the actual model classes in the model
class module. `Watcher` allows you to use either, as they refer to the same object. The
`watchables` module solely exists to provide some handy documentation that you can use in your
IDE to know that classes and be watched and which can support namespaced watching.

Finally, `Watcher` allows you to use either the listing model class or the list's item class when
creating a watcher; either one will result in a stream of events of the list item's class:

.. code:: python

    # these are the same:
    w = Watcher(Pod)
    w = Watcher(PodList)

When streaming such a `Watcher`, both will emit a series of events for `Pod` resources.

==============================================
Mixing Event Types: the `MultiplexingWatcher`
==============================================


