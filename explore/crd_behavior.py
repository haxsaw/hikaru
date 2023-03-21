from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from hikaru.watch import Watcher
from hikaru.crd import (register_crd_class, HikaruCRDDocumentMixin,
                        get_crd_schema)
from dataclasses import dataclass
from typing import Optional
from kubernetes.watch import Watch

set_default_release("rel_1_23")


@dataclass
class MyResourceSpec(HikaruBase):
    pass


@dataclass
class MyResource(HikaruDocumentBase, HikaruCRDDocumentMixin):
    kind = "myresource"
    apiVersion = "v1"
    group = "incisivetech.co.uk"

    meta: ObjectMeta
    spec: Optional[MyResourceSpec]


register_crd_class(MyResource, "myresources")


m = ObjectMeta(name='me')

mr = MyResource(ObjectMeta(name='wibble'), spec=None)
mr.create()

# defining the CRD to Kubernetes

schema: CustomResourceValidation = get_crd_schema(MyResource)


# watching for messages for the defined CRD
watcher: Watcher = Watcher(MyResource)
watcher.stream(manage_resource_version=True, quit_on_timeout=True)

# API Issues
#
# - Registration will need to be changed  DONE
#   So registering a class can be done in the decorator, but what's needed here is a superset
#   of the data needed to allow users to register their own versions of thing like Pod with
#   Hikaru. Probably we need to inject some differences in the back end to default away the
#   deets used for the currently exposed method and allow the collection of more deets for the
#   CRD classes
#
#   REMEMBER: in the CRD message, the name MUST be:
#       spec-names-plural.spec-group
#   ...and in instances of the CRD class, apiVersion MUST be:
#       group/version
#
# - Defining URLs for methods
#
#   URL forms--

#   Namespaced:
#   POST
#   https://<host>:<port>/apis/<group-name>/<version>/namespaces/<namespace>/<crd-plural-name>
#   GET (DEL/PATCH/UPDATE too?)
#   https://<host>:<port>/apis/<group-name>/<version>/namespaces/<namespace>/<crd-plural-name>/<instance-name>
#
#   Notes: <group-name> must be DNS compatible?
#          if <namespace> isn't specified, it defaults to the value "default"
#          <rsrc-name> comes from the ObjectMeta for the resource
#
#   Unnamespaced (Cluster scope):
#   POST
#   https://<host>:<port>/apis/<group-name>/<version>/<plural-crd-name>
#   GET (DEL/PATCH/UPDATE too?)
#   https://<host>:<port>/apis/<group-name>/<version>/<plural-crd-name>/<instance-name>
#
#
#
# - Primary vs List operations
#   It seems best to follow the example of K8s and encourage the separate creation of a
#   singular and list models instead of trying to automatically support getting lists. But
#   there should be no create, update, or delete methods, but perhaps two reads, one for
#   unnamespaced and the other for namespaced resources.
#
#
# - Operations outside of CRUD
#   maybe a decorator...but what does it do? and what does the function do? I suppose it does
#   provide a callable that can be invoked, but really all it needs is a signature to keep
#   IDEs happy-- there's nothing that the method need to do. Would it be better to assign
#   a callable object to a class attribute? The __call__ method would have the correct signature,
#   and the object's constructor would be where the signature would be specified along with
#   any other data needed to invoke the operation.
#
# - WatcherDescription class needs to change for CRDs
#   So it seems that WatcherDescriptor is really just a struct whose data is used by code
#   in watch.py. We probably need to migrate the functionality of watch._get_api_class() into
#   a method on WatcherDesccriptor, but add a protocol class that implements _get_api_class()
#   so that it can provide multiple ways to yield a watch class. We can then make a CRD watcher
#   that can implement the class fetch differently, and let the descriptor also direct processing
#   to a standard method for CRDs (if that's possible).
#
# - Going to need to review watcher classes in K8s code
#   So there's a Watch object and we pass the method name of the particular watch K8s method
#   to use when streaming events. We'll need to provde our own version of this, hopefully a
#   generic one that can be shared by all classes.
#
#
# from:
# https://www.techtarget.com/searchitoperations/tip/Learn-to-use-Kubernetes-CRDs-in-this-tutorial-example
#
#
# Metadata on the field() call; include:
# - enum
# - format
# - description
# - additionalProperties @TODO this renders differently depending on the kind of thing that this describes
#   - if an object, then you add {"type": <typename>} as the value of additionalProperties
#   - if an array, then you add {"items": {"type": <typename>}} as the value of additionalProperties
#   also, additionalProperties and format flag how to render; is it an object or not. Check the swagger
#   for examples

# - consider adding the key "x-kubernetes-group-version-kind" with group/version/kind data
# - consider adding x-kubernetes-patch-strategy
# - consider adding x-kubernetes-patch-merge-key
#
# elif origin in (dict, Dict) or initial_type is object TODO crd.py
# We need to use metadata in the field() to determine how to resolve the issue
# indentified at this TODO ; we may wan to consider modifying the newest build
# to include the use of field() metadata too, just so we can process all the classes
# we generate from the build.
#
# To create a CRD, the opid is createCustomResourceDefinition. you can find the path in the swagger
CustomResourceDefinition(
    spec=CustomResourceDefinitionSpec(
        group="contoso.com",
        names=CustomResourceDefinitionNames(
            kind="MyPlatform",
            plural="myplatforms",
            singular="myplatform",
            shortNames=["myp"],
        ),
        scope="Namespaced",
        versions=[
            CustomResourceDefinitionVersion(
                name="v1alpha1",
                served=True,
                storage=True,
                schema=schema,
            )
        ],
    ),
    apiVersion="apiextensions.k8s.io/v1",
    kind="CustomResourceDefinition",
    metadata=ObjectMeta(name="myplatforms.contoso.com"),
)
