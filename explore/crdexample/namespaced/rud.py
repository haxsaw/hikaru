from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import get_yaml
from resource import MyPlatform, namespace
from kubernetes import config

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go", namespace=namespace)
    )

    # read
    result = mc.read()
    print(get_yaml(result))

    # update
    result.spec.instanceSize = "medium"
    result = result.update()

    # delete
    result = result.delete()
