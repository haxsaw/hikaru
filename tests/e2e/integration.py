#
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
This module seeks to implement equivalent tests as in the official Kubernetes
client's e2e_test/test_utils.py module.

It is based on having access to a Linux install of k3s.
"""
from os import getcwd
from pathlib import Path
from unittest import SkipTest
import pytest
from hikaru import *
from hikaru.model.rel_1_16.v1 import *
from kubernetes import config

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd
e2e_namespace = 'e2e-tests'


setup_calls = 0


def beginning():
    global setup_calls
    setup_calls += 1
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    ns = Namespace(metadata=ObjectMeta(name=e2e_namespace))
    res = ns.createNamespace()
    return res


def ending():
    Namespace.deleteNamespace(name=e2e_namespace)


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res.obj
    ending()


def test01():
    """
    Create a deployment, read it, and delete it
    """
    path = base_path / 'apps-deployment.yaml'
    d: Deployment = load_full_yaml(path=path)[0]
    res = d.createNamespacedDeployment(e2e_namespace)
    assert res.obj and isinstance(res.obj, Deployment)
    res = Deployment.readNamespacedDeployment(d.metadata.name, e2e_namespace)
    assert res.obj and isinstance(res.obj, Deployment)
    res = Deployment.deleteNamespacedDeployment(d.metadata.name,
                                                e2e_namespace)
    assert res.obj and isinstance(res.obj, Status)


def test02():
    """
    Create, read, and delete a Pod
    """
    path = base_path / "core-pod.yaml"
    p: Pod = load_full_yaml(path=path)[0]
    res = p.createNamespacedPod(e2e_namespace)
    assert res.obj and isinstance(res.obj, Pod)
    res = Pod.readNamespacedPod(p.metadata.name, e2e_namespace)
    assert res.obj and isinstance(res.obj, Pod)
    res = Pod.deleteNamespacedPod(p.metadata.name, e2e_namespace)
    assert res.obj and isinstance(res.obj, Pod)


def test03():
    """
    Create, read, and delete a Service
    """
    path = base_path / "core-service.yaml"
    s: Service = load_full_yaml(path=path)[0]
    res = s.createNamespacedService(e2e_namespace)
    assert res.obj and isinstance(res.obj, Service), f"actually got a {type(res.obj)}"
    res = Service.readNamespacedService(s.metadata.name, e2e_namespace)
    assert res.obj and isinstance(res.obj, Service)
    res = Service.deleteNamespacedService(s.metadata.name, e2e_namespace)
    assert res.obj


def test04():
    """
    Create, read, and delete a Namespace
    """
    path = base_path / "core-namespace.yaml"
    ns: Namespace = load_full_yaml(path=path)[0]
    res = ns.createNamespace()
    assert res.obj and isinstance(res.obj, Namespace)
    res = Namespace.readNamespace(ns.metadata.name)
    assert res.obj and isinstance(res.obj, Namespace)
    res = Namespace.deleteNamespace(ns.metadata.name)
    assert res.obj


def test05():
    """
    Create, read, and delete an RBAC role
    """
    path = base_path / "rbac-role.yaml"
    r: Role = load_full_yaml(path=path)[0]
    # this has its own namespace specified in the request so we need
    # to make sure they agree
    res = r.createNamespacedRole(r.metadata.namespace)
    assert res.obj and isinstance(res.obj, Role)
    res = Role.readNamespacedRole(r.metadata.name, r.metadata.namespace)
    assert res.obj and isinstance(res.obj, Role)
    res = Role.deleteNamespacedRole(r.metadata.name, r.metadata.namespace)
    assert res.obj


def test06():
    """
    Create a namespace and then a deployment in just that namespace, delete both
    """
    path_ns = base_path / "dep-namespace.yaml"
    path_dep = base_path / "dep-deployment.yaml"
    # namespace: create and read
    ns: Namespace = load_full_yaml(path=path_ns)[0]
    res = ns.createNamespace()
    assert res.obj and isinstance(res.obj, Namespace)
    res = Namespace.readNamespace(ns.metadata.name)
    assert res.obj and isinstance(res.obj, Namespace)
    # deployment: create and read
    dep: Deployment = load_full_yaml(path=path_dep)[0]
    res = dep.createNamespacedDeployment(ns.metadata.name)
    assert res.obj and isinstance(res.obj, Deployment)
    res = Deployment.readNamespacedDeployment(dep.metadata.name,
                                              ns.metadata.name)
    assert res.obj and isinstance(res.obj, Deployment)
    res = Deployment.deleteNamespacedDeployment(dep.metadata.name,
                                                dep.metadata.namespace)
    assert res.obj
    res = Namespace.deleteNamespace(ns.metadata.name)
    assert res.obj


def test07():
    """
    Create API service, read, fail creating dup, delete
    """
    path = base_path / "api-service.yaml"
    api: APIService = load_full_yaml(path=path)[0]
    res = api.createAPIService()
    assert res.obj and res.code < 400
    res = APIService.readAPIService(api.metadata.name)
    assert res.obj
    api2: APIService = load_full_yaml(path=path)[0]
    try:
        _ = api2.createAPIService()
        assert False, "second registration should have raised an exception"
    except:
        pass
    res = APIService.deleteAPIService(api.metadata.name)
    assert res.obj


def test08():
    """
    Create a list of namespaces, read them, delete them

    Original test: test_create_namespace_list_from_yaml
    """
    assert True, "Support yet to be implemented to namespace list create"


if __name__ == "__main__":
    beginning()
    the_tests = {k: v for k, v in globals().items()
                 if k.startswith('test') and callable(v)}
    for k, v in the_tests.items():
        try:
            v()
        except SkipTest:
            pass
        except Exception as e:
            print(f'{k} failed with {str(e)}, {e.__class__}')
    ending()
