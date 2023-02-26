from hikaru import *
from hikaru.model.rel_1_26.v1 import *
from hikaru.watch import Watcher
from dataclasses import dataclass
from typing import Optional, List, Dict


# defining a CRD
@dataclass
class MyResourceSpec(HikaruBase):
    pass


@register_crd
@dataclass
class MyResource(HikaruCRDDocumentBase):
    kind = "myresource"
    version = "v1"
    group = "incisivetech.co.uk"

    meta: ObjectMeta
    spec: Optional[MyResourceSpec]

    @crd_create("/the/url")
    def create(self):
        pass

    @crd_delete("/the/url")
    def delete(self):
        pass


# defining the CRD to Kubernetes
singular = 'myresource'
plural = 'myresources'
url = "/whatever"

schema: CustomResourceValidation = MyResource.get_crd_schema()


# watching for messages for the defined CRD
watcher: Watcher = Watcher(MyResource)
watcher.stream(manage_resource_version=True, quit_on_timeout=True)
