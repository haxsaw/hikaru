from hikaru.model.rel_1_23.v1 import ObjectMeta, ApiClient
from hikaru import set_default_release, get_yaml
from resource import MyCluster, MyClusterSpec
from kubernetes import config

set_default_release("rel_1_23")

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
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

    # create
    result = mc.create()
    print(get_yaml(result.obj))

    # read
    result = mc.read()
    print(get_yaml(result.obj))

    # delete
    result.obj.set_client(client)
    result = result.obj.delete()
    print(result.obj)
