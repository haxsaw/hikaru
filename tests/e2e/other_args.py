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
import pytest
from typing import cast
from unittest import SkipTest
from hikaru import *
from hikaru.model import *
from kubernetes import config


tests_namespace = 'other-args-tests'


def beginning():
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    ns = Namespace(metadata=ObjectMeta(name=tests_namespace))
    res = ns.createNamespace()
    return res


def ending():
    Namespace.deleteNamespace(name=tests_namespace)
    res: Response = Pod.listPodForAllNamespaces()
    plist: PodList = cast(PodList, res.obj)
    for pod in plist.items:
        if pod.metadata.namespace == tests_namespace:
            Pod.deleteNamespacedPod(pod.metadata.name, pod.metadata.namespace)


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res.obj
    ending()


def test01():
    """
    Check async pod creation
    """
    base_pod = Pod(metadata=ObjectMeta(name='pod-test01'),
                   spec=PodSpec(
                       containers=[Container(image='busybox',
                                             name='sleep',
                                             args=["/bin/sh",
                                                   "-c"])]
                   ))
    res = base_pod.createNamespacedPod(namespace=tests_namespace, async_req=True)
    assert not res.obj
    val = res.get(20)
    assert type(val) is tuple
    assert res.obj
    dres = Pod.deleteNamespacedPod(base_pod.metadata.name,
                                   tests_namespace, async_req=True)
    assert not dres.obj
    val = dres.get(20)
    assert type(val) is tuple
    assert dres.obj


def test02():
    """
    Check doing a dry run on Pod creation
    """
    p = Pod(metadata=ObjectMeta(name='pod-test02'),
            spec=PodSpec(
                containers=[Container(image='busybox',
                                      name='sleep',
                                      args=["/bin/sh",
                                            "-c"])]
            ))
    res = p.createNamespacedPod(namespace=tests_namespace,
                                dry_run='All')
    assert res.obj
    assert isinstance(res.obj, Pod)
    assert res.obj.metadata.name == p.metadata.name
    try:
        rres = Pod.readNamespacedPod(p.metadata.name,
                                     tests_namespace)
    except:
        pass  # we were supposed to get an exception
    else:
        assert False, 'we were able to read a pod that was created with dry_run'


def test03():
    """
    Test doing both async and dry run
    """
    p = Pod(metadata=ObjectMeta(name='pod-test03'),
            spec=PodSpec(
                containers=[Container(image='busybox',
                                      name='sleep',
                                      args=["/bin/sh",
                                            "-c"])]
            ))
    res = p.createNamespacedPod(namespace=tests_namespace,
                                async_req=True,
                                dry_run='All')
    assert not res.obj
    val = res.get()
    assert type(val) is tuple
    assert res.obj
    assert isinstance(res.obj, Pod)
    try:
        rres = Pod.readNamespacedPod(p.metadata.name,
                                     tests_namespace)
    except:
        pass
    else:
        assert False, 'we were able to read a dryrun pod'


def test04():
    """
    test the other async methods on the returned Response
    """
    base_pod = Pod(metadata=ObjectMeta(name='pod-test04'),
                   spec=PodSpec(
                       containers=[Container(image='busybox',
                                             name='sleep',
                                             args=["/bin/sh",
                                                   "-c"])]
                   ))
    res = base_pod.createNamespacedPod(namespace=tests_namespace, async_req=True)
    assert not res.obj
    res.wait(20)
    try:
        assert res.ready()
        val = res.get()
        assert type(val) is tuple
        assert res.obj
        assert res.successful()
    finally:
        dres = Pod.deleteNamespacedPod(base_pod.metadata.name,
                                       tests_namespace, async_req=True)
        assert not dres.obj
        val = dres.get(20)
        assert type(val) is tuple
        assert dres.obj


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
