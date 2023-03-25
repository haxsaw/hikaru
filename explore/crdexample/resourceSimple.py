from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release, get_yaml
from hikaru.crd import register_crd_class, HikaruCRDDocumentMixin, get_crd_schema
from hikaru.meta import FieldMetadata as fm
from typing import Optional
from dataclasses import dataclass, field

set_default_release("rel_1_23")


@dataclass
class MyPlatformSpec(HikaruBase):
    appId: str
    language: str
    environmentType: str
    os: Optional[str] = None
    instanceSize: Optional[str] = None
    replicas: Optional[int] = 1


@dataclass
class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    spec: Optional[MyPlatformSpec] = None
    apiVersion: str = "example.com/v1"
    kind: str = "MyPlatform"


register_crd_class(MyPlatform, plural_name="myplatforms", is_namespaced=False)


if __name__ == "__main__":
    print(get_yaml(get_crd_schema(MyPlatform)))
