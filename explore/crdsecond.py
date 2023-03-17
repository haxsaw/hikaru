from hikaru.model.rel_1_23.v1 import *
from hikaru.crd import register_crd_schema, get_crd_schema, HikaruCRDCRUDDocumentMixin
from hikaru.meta import FieldMetadata as fm
from dataclasses import dataclass, field
from typing import Optional
from hikaru import get_yaml, set_default_release
from kubernetes import config


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
class MyCluster(HikaruDocumentBase, HikaruCRDCRUDDocumentMixin):
    spec: MyClusterSpec
    metadata: ObjectMeta
    apiVersion: str = "incisivetech.co.uk/v1"
    kind: str = "MyCluster"


register_crd_schema(MyCluster, plural_name="myclusters", is_namespaced=False)


if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    schema: JSONSchemaProps = get_crd_schema(MyCluster)
    # print(get_yaml(schema))

    # now make the CRD object with the schema
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group="incisivetech.co.uk",
            names=CustomResourceDefinitionNames(
                shortNames=["myc"],
                plural="myclusters",
                singular="mycluster",
                kind="MyCluster"
            ),
            scope="Cluster",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema  # schema goes here!
                )
            )]
        ),
        metadata=ObjectMeta(name="myclusters.incisivetech.co.uk")
    )

    # print(get_yaml(crd))
    #
    # # create the crd on the cluster
    # new_crd = crd.create()
    # print("New CRD created; details:")
    # print(get_yaml(new_crd))

    # INSTANCE
    client = ApiClient()

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    ).set_client(client)
    res = mc.create()
    print(get_yaml(res.obj))
    new_mc: MyCluster = res.obj

    print("...reading...")
    new_mc.set_client(client)
    res = new_mc.read()
    print(get_yaml(res.obj))

    print("...deleting...")
    res = new_mc.delete()
    print(get_yaml(res.obj))
