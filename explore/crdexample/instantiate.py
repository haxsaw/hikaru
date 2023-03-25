from hikaru.model.rel_1_23.v1 import ObjectMeta
from hikaru import get_yaml
from resource import MyCluster, MyClusterSpec
from kubernetes import config

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    # create
    result = mc.create()
    print(get_yaml(result))

    # read
    result = mc.read()
    print(get_yaml(result))

    # delete
    result = result.delete()
    print(get_yaml(result))
