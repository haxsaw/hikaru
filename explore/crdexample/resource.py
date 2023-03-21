from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release
from hikaru.crd import register_crd_class, HikaruCRDDocumentMixin
from hikaru.meta import FieldMetadata as fm
from typing import Optional
from dataclasses import dataclass, field

set_default_release("rel_1_23")


@dataclass
class MyClusterSpec(HikaruBase):
    appId: str
    language: str = field(metadata=fm(enum=["csharp", "python", "go"]))
    environmentType: str = field(metadata=fm(enum=["dev", "test", "prod"]))
    os: Optional[str] = field(default=None, metadata=fm(enum=["windows",
                                                              "linux"]))
    instanceSize: Optional[str] = field(default=None,
                                        metadata=fm(enum=["small",
                                                          "medium",
                                                          "large"]))
    replicas: Optional[int] = field(default=1,
                                    metadata=fm(minimum=1))


@dataclass
class MyCluster(HikaruDocumentBase, HikaruCRDDocumentMixin):
    spec: MyClusterSpec
    metadata: ObjectMeta
    apiVersion: str = "example.com/v1"
    kind: str = "MyCluster"


register_crd_class(MyCluster, plural_name="myclusters", is_namespaced=False)
