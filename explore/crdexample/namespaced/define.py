from kubernetes import config
from hikaru.model.rel_1_23.v1 import *
from hikaru.crd import get_crd_schema
from resource import MyPlatform, plural, group, namespace

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

    schema: JSONSchemaProps = get_crd_schema(MyPlatform)  # get the schema for the new class

    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group=group,
            names=CustomResourceDefinitionNames(
                shortNames=["myp"],
                plural=plural,
                singular="myplatform",
                kind=MyPlatform.kind
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
            metadata=ObjectMeta(name=f"{plural}.{group}")
        )

    create_result = crd.create()

    ns: Namespace = Namespace(metadata=ObjectMeta(name=namespace))
    ns.create()

