from hikaru import *
from hikaru.model.rel_1_26.v1 import *
from hikaru.watch import Watcher
from hikaru.crd import (register_crd, HikaruCRDDocumentBase, crd_create,
                        crd_read, crd_update, crd_delete)
from hikaru.crd import HikaruCRDDocumentBase
from dataclasses import dataclass
from typing import Optional, List, Dict


# defining a CRD
@dataclass
class MyResourceSpec(HikaruBase):
    pass


@dataclass
class MyResource(HikaruCRDDocumentBase):
    kind = "myresource"
    apiVersion = "v1"
    group = "incisivetech.co.uk"

    meta: ObjectMeta
    spec: Optional[MyResourceSpec]

    @crd_create("/myresource/{namespace}/create")
    def create(self, namespace, dry_run, connection):
        pass

    # @crd_read("/myresource/{namespace}")

register_crd(MyResource)


m = ObjectMeta(name='me')

mr = MyResource(ObjectMeta(name='wibble'), spec=None)
mr.create()

# defining the CRD to Kubernetes

schema: CustomResourceValidation = MyResource.get_crd_schema()


# watching for messages for the defined CRD
watcher: Watcher = Watcher(MyResource)
watcher.stream(manage_resource_version=True, quit_on_timeout=True)

# API Issues
# - Registration will need to be changed
#   So registering a class can be done in the decorator, but what's needed here is a superset
#   of the data needed to allow users to register their own versions of thing like Pod with
#   Hikaru. Probably we need to inject some differences in the back end to default away the
#   deets used for the currently exposed method and allow the collection of more deets for the
#   CRD classes
#
# - Defining URLs for methods
#   Decorators are the most obvious choice, but what to decorate? We actually provide the
#   implementations of the CRUD methods, so the user doesn't write any methods and hence
#   there's nothing to decorate. We could establish some standard non-annotated class attrs
#   that supply URLs but that seems ugly to me. We *could* add them as kw args to the
#   _RegisterCRD class, so that when someone registers a class they can optionally supply
#   each of the URLs. That may be the best of the options.
#
#   Solution part 1: for CRUD methods, we'll use arguments to the register_crd decorator
#       to supply the CRUD urls. Anything beyond that will need to use the unique method
#       decorators (see below) that allows additional operations.
#
# - What about the verb for the method? Should there be a default one for each CRUD method?
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