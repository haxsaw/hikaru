"""
Use this tool to kill off a namespace stuck in 'terminating'

This program assumes the availability of kubectl to do its thing,
and requires that the KUBECONFIG envvar be set to the path of the K8s
configuration file (or whatever K8s-compliant system you're using).

Run it like:

python kns.py <namespace to kill>

It assumes that the current status is 'Terminating'; unclear what happens if
you run it in any other status.
"""
import sys
import os
import subprocess
import tempfile
from hikaru import get_json
from hikaru.model import Namespace
from kubernetes import config


config_env = "KUBECONFIG"


def kill_namespace(nsname: str):
    ns: Namespace = Namespace.readNamespace(nsname).obj
    del ns.spec.finalizers[:]
    res = ns.replaceNamespace(ns.metadata.name)
    tf = tempfile.NamedTemporaryFile(mode="w")
    name = tf.name
    tf.write(get_json(ns))
    tf.flush()
    sp = subprocess.run(["kubectl", "replace", '--raw',
                         f'/api/v1/namespaces/{nsname}/finalize',
                         '-f', name])
    tf.close()


if __name__ == "__main__":
    if config_env not in os.environ:
        sys.stderr.write(f"You must set the {config_env} environment var before "
                         f"running {sys.argv[0]}\n")
        sys.exit(1)
    if len(sys.argv) < 2:
        sys.stderr.write(f"Usage: python {sys.argv[0]} <namespace name>\n")
        sys.exit(1)
    config.load_kube_config(config_file=os.environ[config_env])
    kill_namespace(sys.argv[1])
