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
Exercising CRUD methods
"""
from os import getcwd
from pathlib import Path
from typing import cast
from unittest import SkipTest
from hikaru import *
from hikaru.model.rel_1_16.v1 import *
from kubernetes import config
import pytest

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd
crud_namespace = 'crud-test-ns'


def beginning():
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    ns = Namespace(metadata=ObjectMeta(name=crud_namespace))
    res = ns.createNamespace()
    return res


def ending():
    Namespace.deleteNamespace(crud_namespace)


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res.obj
    ending()


def test01():
    """
    Create a deployment via CRUD
    """
    path = base_path / 'apps-deployment.yaml'
    d: Deployment = cast(Deployment, load_full_yaml(path=str(path))[0])
    d.metadata.namespace = crud_namespace
    d.create()
    try:
        d.read()
        d.metadata.labels['a'] = 'b'
        d.update()
    finally:
        d.delete()


def test01a():
    """
    Create same deployment via CRUD, but do so via args
    """
    path = base_path / 'apps-deployment.yaml'
    d: Deployment = cast(Deployment, load_full_yaml(path=str(path))[0])
    d.metadata.name = f"{d.metadata.name}new"
    d.metadata.namespace = None
    d.create(namespace=crud_namespace)
    try:
        d.read()
        d.metadata.labels['test'] = 'test01a'
        d.update()
    finally:
        d.delete()


def test02():
    """
    Create a pod via CRUD
    """
    path = base_path / "core-pod.yaml"
    p: Pod = cast(Pod, load_full_yaml(path=str(path))[0])
    p.metadata.namespace = crud_namespace
    p.create()
    try:
        p.read()
        p.metadata.labels['test'] = 'test02'
        p.update()
    finally:
        p.delete()


def test03():
    """
    Create a service via CRUD
    """
    path = base_path / "core-service.yaml"
    s: Service = cast(Service, load_full_yaml(path=str(path))[0])
    s.metadata.namespace = crud_namespace
    s.create()
    try:
        s.read()
        s.metadata.labels['test'] = 'test03'
        s.update()
    finally:
        s.delete()


def test04():
    """
    Create a namespace via CRUD
    """
    path = base_path / "core-namespace.yaml"
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path))[0])
    ns.metadata.name = f"{crud_namespace}test04"
    ns.create()
    try:
        ns.read()
        ns.metadata.labels['test'] = 'test04'
        ns.update()
    finally:
        ns.delete()


def test05():
    """
    Create an RBAC role via CRUD
    """
    path = base_path / "rbac-role.yaml"
    r: Role = cast(Role, load_full_yaml(path=str(path))[0])
    r.metadata.namespace = crud_namespace
    r.create()
    try:
        r.read()
        r.metadata.labels['test'] = 'test05'
        r.update()
    finally:
        r.delete()


def test06():
    """
    Try creating a pod and then reading it via another pod
    """
    path = base_path / "core-pod.yaml"
    p: Pod = cast(Pod, load_full_yaml(path=str(path))[0])
    p.metadata.namespace = crud_namespace
    p.metadata.name = f"{p.metadata.name}06"
    p.create()
    try:
        p.read()
        np: Pod = Pod()
        np.read(name=p.metadata.name, namespace=p.metadata.namespace)
        assert p == np
    finally:
        p.read()
        p.delete()


def test07():
    """
    Manipulate an RBAC via CRUD
    """
    path = base_path / "rbac-role.yaml"
    r: Role = cast(Role, load_full_yaml(path=str(path))[0])
    r.metadata.namespace = crud_namespace
    r.create()
    try:
        r.read()
        r.metadata.labels['test'] = 'test07'
        r.update()
    finally:
        r.delete()


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
            raise
    ending()
