from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from hikaru.watch import Watcher
from hikaru.crd import (register_crd_schema, crd_create,
                        crd_read, crd_update, crd_delete)
from dataclasses import dataclass
from typing import Optional, List, Dict

set_default_release("rel_1_23")

# defining a CRD
@dataclass
class MyResourceSpec(HikaruBase):
    pass


@dataclass
class MyResource(HikaruDocumentBase):
    kind = "myresource"
    apiVersion = "v1"
    group = "incisivetech.co.uk"

    meta: ObjectMeta
    spec: Optional[MyResourceSpec]

    @crd_create("/myresource/{namespace}")
    def create(self, namespace, dry_run, connection):
        pass

    # @crd_read("/myresource/{namespace}")

register_crd_schema(MyResource)


m = ObjectMeta(name='me')

mr = MyResource(ObjectMeta(name='wibble'), spec=None)
mr.create()

# defining the CRD to Kubernetes

schema: CustomResourceValidation = MyResource.get_crd_schema()


# watching for messages for the defined CRD
watcher: Watcher = Watcher(MyResource)
watcher.stream(manage_resource_version=True, quit_on_timeout=True)

# API Issues
# - Registration will need to be changed  DONE
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
#
# - create a JSONSchemaProps object  DONE
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
                schema=CustomResourceValidation(
                    openAPIV3Schema=JSONSchemaProps(
                        type="object",
                        properties={
                            "spec": {
                                "type": "object",
                                "properties": {
                                    "appId": {"type": "string"},
                                    "language": {
                                        "type": "string",
                                        "enum": ["csharp", "python", "go"],
                                    },
                                    "os": {
                                        "type": "string",
                                        "enum": ["windows", "linux"],
                                    },
                                    "instanceSize": {
                                        "type": "string",
                                        "enum": ["small", "medium", "large"],
                                    },
                                    "environmentType": {
                                        "type": "string",
                                        "enum": ["dev", "test", "prod"],
                                    },
                                    "replicas": {"type": "integer", "minimum": 1},
                                },
                                "required": ["appId", "language", "environmentType"],
                            }
                        },
                        required=["spec"],
                    )
                ),
            )
        ],
    ),
    apiVersion="apiextensions.k8s.io/v1",
    kind="CustomResourceDefinition",
    metadata=ObjectMeta(name="myplatforms.contoso.com"),
)