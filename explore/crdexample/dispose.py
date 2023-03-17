from hikaru.model.rel_1_23.v1 import *
from hikaru import get_yaml
from hikaru.crd import get_crd_schema
from resource import MyCluster
from kubernetes import config


if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    schema: JSONSchemaProps = get_crd_schema(MyCluster)
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group="example.com",
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
        metadata=ObjectMeta(name="myclusters.example.com")
    )

    res = crd.delete()
    print(get_yaml(res))
