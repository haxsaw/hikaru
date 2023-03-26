from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import (HikaruBase, HikaruDocumentBase,
                    set_default_release)
from hikaru.crd import register_crd_class, HikaruCRDDocumentMixin
from typing import Optional
from dataclasses import dataclass

set_default_release("rel_1_23")
plural = "myplatforms"
group = "example.com"
# normally you wouldn't associate a namespace with the CRD definition,
# but for this demo this is the only common place
namespace = "ns-myplatform"


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
    apiVersion: str = f"{group}/v1"
    kind: str = "MyPlatform"


register_crd_class(MyPlatform, plural, is_namespaced=False)


if __name__ == "__main__":
    from hikaru import get_yaml
    from hikaru.crd import get_crd_schema

    print(get_yaml(get_crd_schema(MyPlatform)))
