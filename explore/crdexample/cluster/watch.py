from resource import MyPlatform
from hikaru import get_yaml
from hikaru.watch import Watcher
from kubernetes import config

if __name__ == "__main__":
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

    w = Watcher(MyPlatform, timeout_seconds=10, should_translate=False)
    for we in w.stream(manage_resource_version=True, quit_on_timeout=True):
        print(get_yaml(we.obj))
