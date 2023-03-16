from hikaru.model.rel_1_23.v1 import *
from hikaru.crd import register_crd_schema, get_crd_schema
from hikaru.utils import FieldMetadata as fm
from dataclasses import dataclass, field
from typing import Optional
from hikaru import get_yaml, set_default_release
from kubernetes import config


set_default_release("rel_1_23")


@dataclass
class MyPlatformSpec(HikaruBase):
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
class MyPlatform(HikaruDocumentBase):
    spec: MyPlatformSpec
    metadata: ObjectMeta
    apiVersion: str = "v1"
    kind: str = "MyPlatform"


register_crd_schema(MyPlatform)


if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    schema: JSONSchemaProps = get_crd_schema(MyPlatform)
    # print(get_yaml(schema))

    # now make the CRD object with the schema
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group="incisivetech.co.uk",
            names=CustomResourceDefinitionNames(
                shortNames=["myp"],
                plural="myplatforms",
                singular="myplatform",
                kind="MyPlatform"
            ),
            scope="Namespaced",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema  # schema goes here!
                )
            )]
        ),
        metadata=ObjectMeta(name="myplatforms.incisivetech.co.uk")
    )

    # print(get_yaml(crd))

    # create the crd on the cluster
    new_crd = crd.create()
    print("New CRD created; details:")
    print(get_yaml(new_crd))
