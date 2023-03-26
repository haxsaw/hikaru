from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release
from hikaru.crd import register_crd_class, HikaruCRDDocumentMixin
from hikaru.meta import FieldMetadata as fm
from typing import Optional
from dataclasses import dataclass, field

set_default_release("rel_1_23")

plural = "myplatforms"
group = "example.com"
# normally you wouldn't associate a namespace with the CRD definition,
# but for this demo this is the only common place
namespace = "ns-myplatform"


@dataclass
class MyPlatformSpec(HikaruBase):
    appId: str = field(metadata=fm(
        description="The ID of the app this platform is for",
        pattern=r'^\d{3}-\d{2}-\d{4}$'))
    language: str = field(metadata=fm(
        description="Which language the app to deploy is written",
        enum=["csharp", "python", "go"]))
    environmentType: str = field(metadata=fm(
        description="Deployment env type",
        enum=["dev", "test", "prod"]))
    os: Optional[str] = field(default=None, metadata=fm(
        description="OS required for the deployment",
        enum=["windows",
              "linux"]))
    instanceSize: Optional[str] = field(
        default='small',
        metadata=fm(
            description="Size of the instance needed; default is 'small'",
            enum=["small",
                  "medium",
                  "large"]))
    replicas: Optional[int] = field(
        default=1,
        metadata=fm(description="How many replicas should be created, min 1",
                    minimum=1))


@dataclass
class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    spec: Optional[MyPlatformSpec] = None
    apiVersion: str = f"{group}/v1"
    kind: str = "MyPlatform"


register_crd_class(MyPlatform, plural_name=plural, is_namespaced=True)


if __name__ == "__main__":
    from hikaru import get_yaml
    from hikaru.crd import get_crd_schema

    print(get_yaml(get_crd_schema(MyPlatform)))
