****************************
Using Hikaru with Kubernetes
****************************

Starting with release 0.4 of Hikaru, you can now use Hikaru objects to interact with
Kubernetes using the underlying Kubernetes Python client. Depending on your use case and
interaction method, it can be possible to not use a single Kubernetes Python call and work
entirely in Hikaru objects. Hikaru also provides a way for the user to explicitly set the
``kubernetes.client.ApiClient`` instance to use when interacting with Kubernetes.

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

