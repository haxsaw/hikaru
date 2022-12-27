# Copyright (c) 2021 Incisive Technology Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
from hikaru.model.rel_1_22 import Namespace
from kubernetes import config


config_env = "KUBECONFIG"


def kill_namespace(nsname: str):
    ns: Namespace = Namespace.readNamespace(nsname).obj
    del ns.spec.finalizers[:]
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
