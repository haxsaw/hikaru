from hikaru.model.rel_1_23.v1 import ObjectMeta
from resource import MyPlatform, MyPlatformSpec
from kubernetes import config

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go"),
        spec=MyPlatformSpec(
            appId="123-45-6789",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    result = mc.create()
