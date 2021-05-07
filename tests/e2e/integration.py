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
This module seeks to implement equivalent tests from various modules in the
official Kubernetes client's e2e_test sub-package.

It is based on having access to a Linux install of k3s.
"""
from os import getcwd
from pathlib import Path
import time
from typing import cast
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
    res: Response = Pod.listPodForAllNamespaces()
    plist: PodList = cast(PodList, res.obj)
    for pod in plist.items:
        if (pod.metadata.namespace == 'default' and
            (pod.metadata.name.startswith('rc-test') or
             pod.metadata.name.startswith('job-test'))):
            Pod.deleteNamespacedPod(pod.metadata.name, pod.metadata.namespace)


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res.obj
    ending()


####################
# from test_utils.py
####################


def test01():
    """
    Create a deployment, read it, and delete it
    """
    path = base_path / 'apps-deployment.yaml'
    d: Deployment = cast(Deployment, load_full_yaml(path=str(path))[0])
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
    p: Pod = cast(Pod, load_full_yaml(path=str(path))[0])
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
    s: Service = cast(Service, load_full_yaml(path=str(path))[0])
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
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path))[0])
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
    r: Role = cast(Role, load_full_yaml(path=str(path))[0])
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
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path_ns))[0])
    res = ns.createNamespace()
    assert res.obj and isinstance(res.obj, Namespace)
    res = Namespace.readNamespace(ns.metadata.name)
    assert res.obj and isinstance(res.obj, Namespace)
    # deployment: create and read
    dep: Deployment = cast(Deployment, load_full_yaml(path=str(path_dep))[0])
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
    api: APIService = cast(APIService, load_full_yaml(path=str(path))[0])
    res = api.createAPIService()
    assert res.obj and res.code < 400
    res = APIService.readAPIService(api.metadata.name)
    assert res.obj
    api2: APIService = cast(APIService, load_full_yaml(path=str(path))[0])
    try:
        _ = api2.createAPIService()
        assert False, "second registration should have raised an exception"
    except:
        pass
    res = APIService.deleteAPIService(api.metadata.name)
    assert res.obj


#####################
# from test_client.py
#####################


base_pod = Pod(metadata=ObjectMeta(),
               spec=PodSpec(
                   containers=[Container(image='busybox',
                                         name='sleep',
                                         args=["/bin/sh",
                                               "-c"])]
               ))


def test08():
    """
    Create/read/destroy pod

    Original test: test_pod_apis
    """
    test_pod = base_pod.dup()
    test_pod.metadata.name = 'integration-test08'
    test_pod.spec.containers[0].args.append("while true;do date;sleep 5; done")
    res = test_pod.createNamespacedPod(namespace='default')
    assert res.obj
    assert test_pod.metadata.name == res.obj.metadata.name
    assert res.obj.status.phase
    while True:
        read_res = Pod.readNamespacedPod(test_pod.metadata.name, 'default')
        assert read_res.obj
        assert read_res.obj.metadata.name == test_pod.metadata.name
        assert read_res.obj.status.phase
        if read_res.obj.status.phase != 'Pending':
            break
        time.sleep(0.5)
    # skipping the stream() bit for now; have to look into it further
    np_res = Pod.listPodForAllNamespaces()
    assert np_res.obj
    assert isinstance(np_res.obj, PodList)
    assert len(np_res.obj.items) > 0
    del_res = Pod.deleteNamespacedPod(test_pod.metadata.name, 'default')
    assert del_res.obj


base_service = Service(metadata=ObjectMeta(labels={'name': ''},
                                           name='',
                                           resourceVersion='v1'),
                       spec=ServiceSpec(ports=[ServicePort(port=80,
                                                           name='port',
                                                           protocol='TCP',
                                                           targetPort=80)],
                                        selector={'name': ''}))


def make_svc(new_name: str) -> Service:
    svc: Service = base_service.dup()
    svc.metadata.labels['name'] = new_name
    svc.metadata.name = new_name
    svc.spec.selector['name'] = new_name
    return svc


def test09():
    """
    Test service apis; from test_service_apis
    """
    svcname = 'svc-test09'
    svc: Service = make_svc(svcname)
    cres = svc.createNamespacedService(namespace='default')
    assert cres.obj
    assert cres.obj.metadata.name == svcname
    rres = Service.readNamespacedService(name=svcname, namespace='default')
    assert rres.obj
    assert rres.obj.metadata.name == svcname
    assert rres.obj.status
    svc.spec.ports[0].name = 'new'
    svc.spec.ports[0].port = 8080
    svc.spec.ports[0].targetPort = 8080
    # must update our resourceVersion so we show we're changing the right one
    svc.metadata.resourceVersion = rres.obj.metadata.resourceVersion

    pres = svc.patchNamespacedService(name=svc.metadata.name,
                                      namespace='default')
    assert 2 == len(pres.obj.spec.ports)
    dres = Service.deleteNamespacedService(svc.metadata.name,
                                           'default')
    assert dres.obj


base_rc = ReplicationController(
    metadata=ObjectMeta(labels={'name': ''},
                        name=''),
    spec=ReplicationControllerSpec(
        replicas=2,
        selector={'name': ''},
        template=PodTemplateSpec(metadata=ObjectMeta(labels={'name': ''}),
                                 spec=PodSpec(
                                     containers=[Container(image='nginx',
                                                           name='nginx',
                                                           ports=[ContainerPort(
                                                               containerPort=80,
                                                               protocol='TCP'
                                                           )]
                                                           )
                                                 ]
                                 ))
    )
)


def make_rc(name: str) -> ReplicationController:
    rc: ReplicationController = base_rc.dup()
    rc.metadata.labels['name'] = name
    rc.metadata.name = name
    rc.spec.selector['name'] = name
    rc.spec.template.metadata.labels['name'] = name
    return rc


def test10():
    """
    Echo the K8s replication controller test. from test_replication_controller_apis
    """
    name = 'rc-test10'
    rc = make_rc(name)
    cres = rc.createNamespacedReplicationController('default')
    assert cres.obj
    assert name == cres.obj.metadata.name
    rres = ReplicationController.readNamespacedReplicationController(name,
                                                                     namespace='default')
    assert rres.obj
    assert rres.obj.metadata.name == name
    assert 2 == rres.obj.spec.replicas

    _ = ReplicationController.deleteNamespacedReplicationController(name,
                                                                    namespace='default')


base_cm = ConfigMap(
    metadata=ObjectMeta(name=''),
    data={'config.json': "{\"command\":\"/usr/bin/mysqld_safe\"}",
          "frontend.cnf": "[mysqld]\nbind-address = 10.0.0.3\nport = 3306\n"}
)


def make_cm(name: str) -> ConfigMap:
    cm = base_cm.dup()
    cm.metadata.name = name
    return cm


def test11():
    """
    test ConfigMap methods. from test_configmap_apis
    """
    name = 'cm-test11'
    cm: ConfigMap = make_cm(name)
    cres = cm.createNamespacedConfigMap(namespace='default')
    assert cres.obj
    assert name == cres.obj.metadata.name

    rres = ConfigMap.readNamespacedConfigMap(name, namespace='default')
    assert rres.obj
    assert name == rres.obj.metadata.name

    cm.data['config.json'] = '{}'
    assert isinstance(rres.obj, ConfigMap)
    cm.metadata.resourceVersion = rres.obj.metadata.resourceVersion

    pres = cm.patchNamespacedConfigMap(name=cm.metadata.name,
                                       namespace='default')
    assert pres.obj
    dres = cm.deleteNamespacedConfigMap(name, 'default')
    assert dres.obj


def test12():
    """
    test node methods. from test_node_apis
    """
    rres = NodeList.listNode()
    assert rres.obj
    for item in rres.obj.items:
        nres = Node.readNode(item.metadata.name)
        node: Node = nres.obj
        assert node
        assert len(node.metadata.labels) > 0
        assert isinstance(node.metadata.labels, dict)


####################
# from test_batch.py
####################


job_base = Job(metadata=ObjectMeta(name=''),
               spec=JobSpec(template=
                            PodTemplateSpec(metadata=ObjectMeta(name=''),
                                            spec=PodSpec(
                                                containers=[Container(
                                                    image='busybox',
                                                    name='',
                                                    command=['sh', '-c', 'sleep 5']
                                                )],
                                                restartPolicy='Never'
                                            ))
                            ))


def make_job(name: str) -> Job:
    job = job_base.dup()
    job.metadata.name = name
    job.spec.template.metadata.name = name
    job.spec.template.spec.containers[0].name = name
    return job


def test13():
    """
    test batch methods; from test_job_apis
    """
    name = 'job-test13'
    job: Job = make_job(name)
    cres = job.createNamespacedJob('default')
    assert cres.obj
    assert name == cres.obj.metadata.name
    rres = Job.readNamespacedJob(name, 'default')
    assert rres.obj
    assert name == rres.obj.metadata.name
    _ = Job.deleteNamespacedJob(name, 'default')


####################
# from test_apps.py
####################


def make_deployment(name: str) -> Deployment:
    base_deployment = Deployment(
        metadata=ObjectMeta(name=name),
        spec=DeploymentSpec(
            replicas=3,
            selector=LabelSelector(matchLabels={'app': 'nginx'}),
            template=PodTemplateSpec(
                metadata=ObjectMeta(labels={'app': 'nginx'}),
                spec=PodSpec(
                    containers=[Container(
                        name='nginx',
                        image='nginx:1.15.4',
                        ports=[ContainerPort(containerPort=80)]
                    )]
                )
            )
        )
    )
    return base_deployment


def test14():
    """
    test deployment methods; from test_create_deployment
    """
    name = 'deployment-test14'
    dep = make_deployment(name)
    cres: Response = dep.createNamespacedDeployment('default')
    assert cres.obj
    assert name == cres.obj.metadata.name
    rres: Response = Deployment.readNamespacedDeployment(name, 'default')
    assert rres.obj
    assert name == rres.obj.metadata.name
    dres = Deployment.deleteNamespacedDeployment(name, 'default')
    assert dres.obj


def make_daemonset(name: str) -> DaemonSet:
    ds = DaemonSet(
        metadata=ObjectMeta(
            name=name,
            labels={'app': 'nginx'}
        ),
        spec=DaemonSetSpec(
            selector=LabelSelector(
                matchLabels={'app': 'nginx'}
            ),
            template=PodTemplateSpec(
                metadata=ObjectMeta(
                    name=name,
                    labels={'app': 'nginx'}
                ),
                spec=PodSpec(
                    containers=[Container(
                        name='nginx-app',
                        image='nginx:1.15.4'
                    )]
                )
            ),
            updateStrategy=DaemonSetUpdateStrategy(type='RollingUpdate')
        )
    )
    return ds


def test15():
    """
    test daemon set methods; from test_create_daemonset
    """
    name = 'ds-test15'
    ds = make_daemonset(name)
    cres = ds.createNamespacedDaemonSet(namespace='default')
    assert cres.obj
    assert cres.obj.metadata.name == name
    rres = DaemonSet.readNamespacedDaemonSet(name, 'default')
    assert rres.obj
    assert name == rres.obj.metadata.name
    dres = DaemonSet.deleteNamespacedDaemonSet(name, 'default')
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
