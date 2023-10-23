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
official Kubernetes client's e2e_test sub-package, as well as other methods
on various objects.

It is based on having access to a Linux install of k3s.
"""
import base64
import datetime
from os import getcwd
from pathlib import Path
import re
import time
from typing import cast, Optional
from unittest import SkipTest
import pytest
from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from kubernetes import config

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd
e2e_namespace = 'e2e-tests-v1-rel1-23'


setup_calls = 0

conf: Optional[config.kube_config.Configuration] = None


def beginning():
    global setup_calls, conf
    set_default_release('rel_1_23')
    setup_calls += 1
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    conf = config.kube_config.Configuration.get_default_copy()
    conf.client_side_validation = False
    config.kube_config.Configuration.set_default(conf)
    ns = Namespace(metadata=ObjectMeta(name=e2e_namespace))
    res = ns.createNamespace()
    return res


def ending():
    Namespace.deleteNamespace(name=e2e_namespace)
    res: Response = PodList.listPodForAllNamespaces()
    plist: PodList = cast(PodList, res.obj)
    for pod in plist.items:
        if (pod.metadata.namespace in ('default', e2e_namespace) and
            (pod.metadata.name.startswith('rc-test') or
             pod.metadata.name.startswith('job-test'))):
            try:
                Pod.deleteNamespacedPod(pod.metadata.name, pod.metadata.namespace)
            except:
                pass


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
    try:
        assert res.obj and isinstance(res.obj, Deployment)
        d: Deployment = res.obj
        assert not isinstance(d.metadata.creationTimestamp, datetime.datetime), "creationTimestamp is still a datetime"
        assert isinstance(d.metadata.creationTimestamp, str)
        res = Deployment.readNamespacedDeployment(d.metadata.name, e2e_namespace)
        assert res.obj and isinstance(res.obj, Deployment)
    finally:
        _ = Deployment.deleteNamespacedDeployment(d.metadata.name,
                                                  e2e_namespace)


def test01a():
    """
    Test patching a Deployment but do so with returned object; issue #10 in github
    """
    name = 'test01adep'
    path = base_path / 'apps-deployment.yaml'
    d: Deployment = cast(Deployment, load_full_yaml(path=str(path))[0])
    d.metadata.name = name
    rd: Deployment = d.createNamespacedDeployment(e2e_namespace).obj
    try:
        assert rd
        rd = Deployment.readNamespacedDeployment(name, e2e_namespace).obj
        time.sleep(0.1)
        rd = Deployment.readNamespacedDeployment(name, e2e_namespace).obj
        rd.spec.replicas += 1
        res = rd.patchNamespacedDeployment(name, e2e_namespace)
        assert res.obj
    finally:
        _ = Deployment.deleteNamespacedDeployment(name, e2e_namespace)


def test02():
    """
    Create, read, and delete a Pod
    """
    path = base_path / "core-pod.yaml"
    p: Pod = cast(Pod, load_full_yaml(path=str(path))[0])
    res = p.createNamespacedPod(e2e_namespace)
    try:
        assert res.obj and isinstance(res.obj, Pod)
        res = Pod.readNamespacedPod(p.metadata.name, e2e_namespace)
        assert res.obj and isinstance(res.obj, Pod)
    finally:
        _ = Pod.deleteNamespacedPod(p.metadata.name, e2e_namespace)


ip_regex = r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"


def test02a():
    """
    Create a pod and check for hostIP and podIP; must arrive w/in a minute
    """
    path = base_path / "core-pod.yaml"
    p: Pod = cast(Pod, load_full_yaml(path=str(path))[0])
    p.metadata.name += '-2a'
    res = p.createNamespacedPod(e2e_namespace)
    try:
        assert res.obj and isinstance(res.obj, Pod)
        found_podIP: bool = False
        found_hostIP: bool = False
        for i in range(60):
            time.sleep(1)
            res = Pod.readNamespacedPod(p.metadata.name, e2e_namespace)
            assert res.obj and isinstance(res.obj, Pod)
            if not found_podIP and res.obj.status.podIP:
                assert re.match(ip_regex, res.obj.status.podIP)
                found_podIP = True
            if not found_hostIP and res.obj.status.hostIP:
                assert re.match(ip_regex, res.obj.status.hostIP)
                found_hostIP = True
            if found_hostIP and found_podIP:
                break
        else:
            assert False, f"Found hostIP: {found_hostIP}, found podIP: {found_podIP}"
    finally:
        _ = Pod.deleteNamespacedPod(p.metadata.name, e2e_namespace)


def test03():
    """
    Create, read, and delete a Service
    """
    path = base_path / "core-service.yaml"
    s: Service = cast(Service, load_full_yaml(path=str(path))[0])
    res = s.createNamespacedService(e2e_namespace)
    try:
        assert res.obj and isinstance(res.obj, Service), f"actually got a {type(res.obj)}"
        res = Service.readNamespacedService(s.metadata.name, e2e_namespace)
        assert res.obj and isinstance(res.obj, Service)
    finally:
        _ = Service.deleteNamespacedService(s.metadata.name, e2e_namespace)


def test04():
    """
    Create, read, and delete a Namespace
    """
    path = base_path / "core-namespace-23.yaml"
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path))[0])
    res = ns.createNamespace()
    try:
        assert res.obj and isinstance(res.obj, Namespace)
        res = Namespace.readNamespace(ns.metadata.name)
        assert res.obj and isinstance(res.obj, Namespace)
    finally:
        _ = Namespace.deleteNamespace(ns.metadata.name)


def test05():
    """
    Create, read, and delete an RBAC role
    """
    path = base_path / "rbac-role-rel-1-23.yaml"
    r: Role = cast(Role, load_full_yaml(path=str(path))[0])
    # this has its own namespace specified in the request so we need
    # to make sure they agree
    res = r.createNamespacedRole(r.metadata.namespace)
    try:
        assert res.obj and isinstance(res.obj, Role)
        res = Role.readNamespacedRole(r.metadata.name, r.metadata.namespace)
        assert res.obj and isinstance(res.obj, Role)
    finally:
        _ = Role.deleteNamespacedRole(r.metadata.name, r.metadata.namespace)


def test06():
    """
    Create a namespace and then a deployment in just that namespace, delete both
    """
    path_ns = base_path / "dep-namespace-23.yaml"
    path_dep = base_path / "dep-deployment-23.yaml"
    # namespace: create and read
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path_ns))[0])
    res = ns.createNamespace()
    try:
        assert res.obj and isinstance(res.obj, Namespace)
        res = Namespace.readNamespace(ns.metadata.name)
        assert res.obj and isinstance(res.obj, Namespace)
        # deployment: create and read
        dep: Deployment = cast(Deployment, load_full_yaml(path=str(path_dep))[0])
        res = dep.createNamespacedDeployment(ns.metadata.name)
        try:
            assert res.obj and isinstance(res.obj, Deployment)
            res = Deployment.readNamespacedDeployment(dep.metadata.name,
                                                      ns.metadata.name)
            assert res.obj and isinstance(res.obj, Deployment)
        finally:
            _ = Deployment.deleteNamespacedDeployment(dep.metadata.name,
                                                      dep.metadata.namespace)
    finally:
        _ = Namespace.deleteNamespace(ns.metadata.name)


def test07():
    """
    Create API service, read, fail creating dup, delete
    """
    path = base_path / "api-service-1_23.yaml"
    api: APIService = cast(APIService, load_full_yaml(path=str(path))[0])
    res = api.createAPIService()
    try:
        assert res.obj and res.code < 400
        res = APIService.readAPIService(api.metadata.name)
        assert res.obj
        api2: APIService = cast(APIService, load_full_yaml(path=str(path))[0])
        try:
            _ = api2.createAPIService()
            assert False, "second registration should have raised an exception"
        except:
            pass
    finally:
        _ = APIService.deleteAPIService(api.metadata.name)


@pytest.mark.xfail
def test07a():
    """
    Currently fails on returned underlying system data
    """
    lres = APIServiceList.listAPIService()
    assert lres.obj
    assert isinstance(lres.obj, APIServiceList)
    assert 0 > len(lres.obj.items)


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
    res = test_pod.createNamespacedPod(namespace=e2e_namespace)
    try:
        assert res.obj
        assert test_pod.metadata.name == res.obj.metadata.name
        assert res.obj.status.phase
        while True:
            read_res = Pod.readNamespacedPod(test_pod.metadata.name, e2e_namespace)
            assert read_res.obj
            assert read_res.obj.metadata.name == test_pod.metadata.name
            assert read_res.obj.status.phase
            if read_res.obj.status.phase != 'Pending':
                break
            time.sleep(0.5)
        # skipping the stream() bit for now; have to look into it further
        np_res = PodList.listPodForAllNamespaces()
        assert np_res.obj
        assert isinstance(np_res.obj, PodList)
        assert len(np_res.obj.items) > 0
    finally:
        _ = Pod.deleteNamespacedPod(test_pod.metadata.name, e2e_namespace)


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
    cres = svc.createNamespacedService(namespace=e2e_namespace)
    try:
        assert cres.obj
        assert cres.obj.metadata.name == svcname
        rres = Service.readNamespacedService(name=svcname, namespace=e2e_namespace)
        assert rres.obj
        assert rres.obj.metadata.name == svcname
        assert rres.obj.status
        svc.spec.ports[0].name = 'new'
        svc.spec.ports[0].port = 8080
        svc.spec.ports[0].targetPort = 8080
        # must update our resourceVersion so we show we're changing the right one
        svc.metadata.resourceVersion = rres.obj.metadata.resourceVersion

        pres = svc.patchNamespacedService(name=svc.metadata.name,
                                          namespace=e2e_namespace)
        assert 2 == len(pres.obj.spec.ports)
    finally:
        _ = Service.deleteNamespacedService(svc.metadata.name,
                                            e2e_namespace)


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
    cres = rc.createNamespacedReplicationController(e2e_namespace)
    try:
        assert cres.obj
        assert name == cres.obj.metadata.name
        rres = ReplicationController.readNamespacedReplicationController(name,
                                                                         namespace=e2e_namespace)
        assert rres.obj
        assert rres.obj.metadata.name == name
        assert 2 == rres.obj.spec.replicas
        drc = rc.dup()
        drc.spec.replicas = rc.spec.replicas + 1
        pres = drc.patchNamespacedReplicationController(drc.metadata.name, e2e_namespace)
        assert pres.obj
        assert isinstance(pres.obj, ReplicationController)
        assert pres.obj.spec.replicas == rc.spec.replicas + 1
    finally:
        _ = ReplicationController.deleteNamespacedReplicationController(name,
                                                                        namespace=e2e_namespace)


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
    cres = cm.createNamespacedConfigMap(namespace=e2e_namespace)
    try:
        assert cres.obj
        assert name == cres.obj.metadata.name

        rres = ConfigMap.readNamespacedConfigMap(name, namespace=e2e_namespace)
        assert rres.obj
        assert name == rres.obj.metadata.name

        cm.data['config.json'] = '{}'
        assert isinstance(rres.obj, ConfigMap)
        cm.metadata.resourceVersion = rres.obj.metadata.resourceVersion

        pres = cm.patchNamespacedConfigMap(name=cm.metadata.name,
                                           namespace=e2e_namespace)
        assert pres.obj
    finally:
        _ = cm.deleteNamespacedConfigMap(name, e2e_namespace)


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
    cres = job.createNamespacedJob(e2e_namespace)
    try:
        assert cres.obj
        assert name == cres.obj.metadata.name
        rres = Job.readNamespacedJob(name, e2e_namespace)
        assert rres.obj
        assert name == rres.obj.metadata.name
    finally:
        _ = Job.deleteNamespacedJob(name, e2e_namespace)


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
    cres: Response = dep.createNamespacedDeployment(e2e_namespace)
    try:
        assert cres.obj
        assert name == cres.obj.metadata.name
        rres: Response = Deployment.readNamespacedDeployment(name, e2e_namespace)
        assert rres.obj
        assert name == rres.obj.metadata.name
    finally:
        _ = Deployment.deleteNamespacedDeployment(name, e2e_namespace)


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
    cres = ds.createNamespacedDaemonSet(namespace=e2e_namespace)
    try:
        assert cres.obj
        assert cres.obj.metadata.name == name
        rres = DaemonSet.readNamespacedDaemonSet(name, e2e_namespace)
        assert rres.obj
        assert name == rres.obj.metadata.name
    finally:
        _ = DaemonSet.deleteNamespacedDaemonSet(name, e2e_namespace)


# others

def test16():
    """
    test fetching a list of clusterRoleBindings
    """
    rres = ClusterRoleBindingList.listClusterRoleBinding()
    assert rres.obj
    assert isinstance(rres.obj, ClusterRoleBindingList)
    assert len(rres.obj.items) > 0


def test17():
    """
    test fetching a list of ClusterRoles
    """
    rres = ClusterRoleList.listClusterRole()
    assert rres.obj
    assert isinstance(rres.obj, ClusterRoleList)
    assert len(rres.obj.items) > 0


def test18():
    """
    test fetching a list of ConfigMaps
    """
    rres = ConfigMapList.listConfigMapForAllNamespaces()
    assert rres.obj
    assert isinstance(rres.obj, ConfigMapList)
    assert len(rres.obj.items) > 0
    nsres = ConfigMapList.listNamespacedConfigMap(namespace='kube-system')
    assert nsres.obj
    assert isinstance(nsres.obj, ConfigMapList)
    assert len(rres.obj.items) > 0


def test19():
    """
    test fetching a list of ControllerRevisions
    """
    rres = ControllerRevisionList.listNamespacedControllerRevision('default')
    assert rres.obj
    assert isinstance(rres.obj, ControllerRevisionList)
    rres = ControllerRevisionList.listControllerRevisionForAllNamespaces()
    assert rres.obj
    assert isinstance(rres.obj, ControllerRevisionList)


def test20():
    """
    test listing custom resources
    """
    res = CustomResourceDefinitionList.listCustomResourceDefinition()
    assert res.obj
    assert isinstance(res.obj, CustomResourceDefinitionList)
    assert len(res.obj.items) > 0


def test21():
    """
    test listing daemon sets
    """
    res = DaemonSetList.listNamespacedDaemonSet('default')
    assert res.obj
    assert isinstance(res.obj, DaemonSetList)
    res = DaemonSetList.listDaemonSetForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, DaemonSetList)


def test22():
    """
    test listing deployments
    """
    res = DeploymentList.listNamespacedDeployment('kube-system')
    assert res.obj
    assert isinstance(res.obj, DeploymentList)
    assert len(res.obj.items) > 0


def test23():
    """
    test listing endpoints
    """
    res = EndpointsList.listEndpointsForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, EndpointsList)
    assert len(res.obj.items) > 0


def test24():
    """
    test fetching endpoints list
    """
    res = EndpointsList.listNamespacedEndpoints('kube-system')
    assert res.obj
    assert isinstance(res.obj, EndpointsList)
    assert len(res.obj.items) > 0


def test25():
    """
    test listing events via event
    """
    raise SkipTest("Doesn't work in 1.22")
    conf.client_side_validation = False
    client = ApiClient(configuration=conf)
    res = EventList.listEventForAllNamespaces(client=client)
    assert res.obj
    assert isinstance(res.obj, EventList)
    assert len(res.obj.items) > 0


def test26():
    """
    test listing events via event list
    """
    raise SkipTest("Doesn't wok in 1.22")
    res = EventList.listNamespacedEvent(e2e_namespace)
    assert res.obj
    assert isinstance(res.obj, EventList)
    assert len(res.obj.items) > 0


def test27():
    """
    test getting a horizontal pod autoscaler list
    """
    res = HorizontalPodAutoscalerList.listNamespacedHorizontalPodAutoscaler('default')
    assert res.obj
    assert isinstance(res.obj, HorizontalPodAutoscalerList)


def test28():
    """
    test getting the joblist
    """
    res = JobList.listNamespacedJob('default')
    assert res.obj
    assert isinstance(res.obj, JobList)


def test29():
    """
    test getting the list of Leases via Lease
    """
    res = LeaseList.listLeaseForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, LeaseList)
    assert len(res.obj.items) > 0


def test30():
    """
    test getting the lease list via LeaseList
    """
    res = LeaseList.listNamespacedLease('kube-node-lease')
    assert res.obj
    assert isinstance(res.obj, LeaseList)
    assert len(res.obj.items) > 0


def test31():
    """
    test getting a limit range list via LimiteRangeList
    """
    res = LimitRangeList.listNamespacedLimitRange(e2e_namespace)
    assert res.obj
    assert isinstance(res.obj, LimitRangeList)
    res = LimitRangeList.listLimitRangeForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, LimitRangeList)


def test32():
    """
    test getting a list of mutating webhook configs
    """
    res = MutatingWebhookConfigurationList.listMutatingWebhookConfiguration()
    assert res.obj
    assert isinstance(res.obj, MutatingWebhookConfigurationList)


def test33():
    """
    test listing namespaces
    """
    res = NamespaceList.listNamespace()
    assert res.obj
    assert isinstance(res.obj, NamespaceList)
    assert len(res.obj.items) > 0


def test34():
    """
    test listing network policies various ways
    """
    res = NetworkPolicyList.listNamespacedNetworkPolicy('default')
    assert res.obj
    assert isinstance(res.obj, NetworkPolicyList)
    res = NetworkPolicyList.listNetworkPolicyForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, NetworkPolicyList)


def test35():
    """
    test listing persistent vol
    """
    res = PersistentVolumeList.listPersistentVolume()
    assert res.obj
    assert isinstance(res.obj, PersistentVolumeList)


def test36():
    """
    test listing persistent vol claims
    """
    res = PersistentVolumeClaimList.listNamespacedPersistentVolumeClaim('default')
    assert res.obj
    assert isinstance(res.obj, PersistentVolumeClaimList)


def test37():
    """
    test fetching pod list via PodList
    """
    res = PodList.listNamespacedPod('kube-system')
    assert res.obj
    assert isinstance(res.obj, PodList)
    assert len(res.obj.items) > 0


def test38():
    """
    test fetching pod template list
    """
    res = PodTemplateList.listNamespacedPodTemplate('default')
    assert res.obj
    assert isinstance(res.obj, PodTemplateList)


def test39():
    """
    test fetching a priority class list
    """
    res = PriorityClassList.listPriorityClass()
    assert res.obj
    assert isinstance(res.obj, PriorityClassList)
    assert len(res.obj.items) > 0


def test40():
    """
    list replica sets
    """
    res = ReplicaSetList.listNamespacedReplicaSet('kube-system')
    assert res.obj
    assert isinstance(res.obj, ReplicaSetList)
    assert len(res.obj.items) > 0
    res = ReplicaSetList.listReplicaSetForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, ReplicaSetList)
    assert len(res.obj.items) > 0


def test41():
    """
    list replication controllers
    """
    res = ReplicationControllerList.listNamespacedReplicationController('default')
    assert res.obj
    assert isinstance(res.obj, ReplicationControllerList)
    res = ReplicationControllerList.listReplicationControllerForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, ReplicationControllerList)


def test42():
    """
    list resource quotas
    """
    res = ResourceQuotaList.listNamespacedResourceQuota('default')
    assert res.obj
    assert isinstance(res.obj, ResourceQuotaList)
    res = ResourceQuotaList.listResourceQuotaForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, ResourceQuotaList)


def test43():
    """
    list role bindings
    """
    res = RoleBindingList.listNamespacedRoleBinding('kube-system')
    assert res.obj
    assert isinstance(res.obj, RoleBindingList)
    assert len(res.obj.items) > 0


def test44():
    """
    list Roles
    """
    res = RoleList.listNamespacedRole('kube-system')
    assert res.obj
    assert isinstance(res.obj, RoleList)
    assert len(res.obj.items) > 0


def test45():
    """
    list secrets
    """
    res = SecretList.listNamespacedSecret('kube-system')
    assert res.obj
    assert isinstance(res.obj, SecretList)
    assert len(res.obj.items) > 0


def test46():
    """
    list service accounts
    """
    res = ServiceAccountList.listNamespacedServiceAccount('kube-system')
    assert res.obj
    assert isinstance(res.obj, ServiceAccountList)
    assert len(res.obj.items) > 0


def test47():
    """
    list services
    """
    res = ServiceList.listNamespacedService('kube-system')
    assert res.obj
    assert isinstance(res.obj, ServiceList)
    assert len(res.obj.items) > 0


def test48():
    """
    list stateful sets
    """
    res = StatefulSetList.listNamespacedStatefulSet('default')
    assert res.obj
    assert isinstance(res.obj, StatefulSetList)
    res = StatefulSetList.listStatefulSetForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, StatefulSetList)


def test49():
    """
    List storage classes
    """
    res = StorageClassList.listStorageClass()
    assert res.obj
    assert isinstance(res.obj, StorageClassList)
    assert len(res.obj.items) > 0


def test50():
    """
    list validating webhook configurations
    """
    res = ValidatingWebhookConfigurationList.listValidatingWebhookConfiguration()
    assert res.obj
    assert isinstance(res.obj, ValidatingWebhookConfigurationList)


def test51():
    """
    list volume attachments
    """
    res = VolumeAttachmentList.listVolumeAttachment()
    assert res.obj
    assert isinstance(res.obj, VolumeAttachmentList)


def test52():
    """
    test crud ops on secrets
    """
    res = SecretList.listNamespacedSecret(e2e_namespace)
    before_len = len(res.obj.items)
    secret = Secret(metadata=ObjectMeta(name='seekrit'),
                    data={'pw1': base64.b64encode(b'bibble').decode(),
                          'pw2': base64.b64encode(b'bobble').decode()})
    res = secret.createNamespacedSecret(e2e_namespace)
    try:
        assert res.obj
        res = SecretList.listNamespacedSecret(e2e_namespace)
        assert before_len < len(res.obj.items)
        rres = Secret.readNamespacedSecret(name=secret.metadata.name,
                                           namespace=e2e_namespace)
        assert rres.obj
        assert secret.metadata.name == rres.obj.metadata.name
    finally:
        _ = Secret.deleteNamespacedSecret(secret.metadata.name,
                                          e2e_namespace)


def test53():
    """
    test crud ops on pod templates
    """
    res = PodTemplateList.listNamespacedPodTemplate(e2e_namespace)
    before_len = len(res.obj.items)
    pt = PodTemplate(
        metadata=ObjectMeta(name='test-53'),
        template=PodTemplateSpec(
            metadata=ObjectMeta(labels={'name': ''}),
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
    res = pt.createNamespacedPodTemplate(e2e_namespace)
    try:
        assert res.obj
        res = PodTemplateList.listNamespacedPodTemplate(e2e_namespace)
        assert before_len < len(res.obj.items)
        rres = PodTemplate.readNamespacedPodTemplate(pt.metadata.name, e2e_namespace)
        assert rres.obj
        assert rres.obj.metadata.name == pt.metadata.name
    finally:
        _ = PodTemplate.deleteNamespacedPodTemplate(pt.metadata.name, e2e_namespace)


def test54():
    """
    test persistent volume claims
    """
    pvc = PersistentVolumeClaim(
        metadata=ObjectMeta(
            name='postgres-pvc-kiamol'
        ),
        spec=PersistentVolumeClaimSpec(
            accessModes=['ReadWriteOnce'],
            storageClassName='kiamol',
            resources=ResourceRequirements(
                requests={'storage': '100Mi'}
            )
        )
    )
    res = pvc.createNamespacedPersistentVolumeClaim(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, PersistentVolumeClaim)
        assert res.obj.metadata.name == pvc.metadata.name
        rres = PersistentVolumeClaim.readNamespacedPersistentVolumeClaim(
            pvc.metadata.name, e2e_namespace)
        assert rres.obj
        assert isinstance(rres.obj, PersistentVolumeClaim)
        assert rres.obj.metadata.name == pvc.metadata.name
    finally:
        _ = PersistentVolumeClaim.deleteNamespacedPersistentVolumeClaim(pvc.metadata.name,
                                                                        e2e_namespace)


def test55():
    """
    test listing component status
    """
    res = ComponentStatusList.listComponentStatus()
    assert res.obj
    assert isinstance(res.obj, ComponentStatusList)
    assert len(res.obj.items) > 0


def test56():
    """
    test persistent volume crud ops
    """
    pv = PersistentVolume(
        metadata=ObjectMeta(
            name='pv01'
        ),
        spec=PersistentVolumeSpec(
            capacity={'storage': '50Mi'},
            accessModes=['ReadWriteOnce'],
            nfs=NFSVolumeSource(
                server='nsf.my.network',
                path='/kubernetes-volumes'
            )
        )
    )
    res = pv.createPersistentVolume()
    try:
        assert res.obj
        rres = PersistentVolume.readPersistentVolume(pv.metadata.name)
        assert rres.obj
        assert isinstance(rres.obj, PersistentVolume)
        assert rres.obj.metadata.name == pv.metadata.name
    finally:
        _ = PersistentVolume.deletePersistentVolume(pv.metadata.name)


def make_sa57(ns: str = None) -> ServiceAccount:
    sa = ServiceAccount(
        metadata=ObjectMeta(
            name='user-cert-generator',
            labels={'kiamol': 'ch17'},
            namespace=ns
        )
    )
    return sa


def test57():
    """
    test service account crud operations
    """
    sa = make_sa57()
    res = sa.createNamespacedServiceAccount(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, ServiceAccount)
        assert res.obj.metadata.name == sa.metadata.name
        rres = ServiceAccount.readNamespacedServiceAccount(sa.metadata.name,
                                                           e2e_namespace)
        assert rres.obj
        assert isinstance(rres.obj, ServiceAccount)
        assert rres.obj.metadata.name == sa.metadata.name
        dsa = sa.dup()
        dsa.metadata.labels['extra-label'] = 'value'
        pres = dsa.patchNamespacedServiceAccount(sa.metadata.name,
                                                 e2e_namespace)
        assert pres.obj
        assert isinstance(pres.obj, ServiceAccount)
        assert pres.obj.metadata.name == sa.metadata.name
    finally:
        _ = ServiceAccount.deleteNamespacedServiceAccount(sa.metadata.name,
                                                          e2e_namespace)


def make_cr58() -> ClusterRole:
    cr = ClusterRole(
        metadata=ObjectMeta(
            name='create-approve-csr',
            labels={'kiamol': 'ch17'}
        ),
        rules=[
            PolicyRule(apiGroups=["certificates.k8s.io"],
                       resources=["certificatesigningrequests"],
                       verbs=["create", "get", "list", "watch"],
                       ),
            PolicyRule(apiGroups=["certificates.k8s.io"],
                       resources=["certificatesigningrequests/approval"],
                       verbs=["update"]),
            PolicyRule(apiGroups=["certificates.k8s.io"],
                       resources=["signers"],
                       resourceNames=["kubernetes.io/kube-apiserver-client",
                                      "kubernetes.io/legacy-unknown"],
                       verbs=['approve'])
        ]
    )
    return cr


def test58():
    """
    test crud ops on cluster roles
    """
    cr = make_cr58()
    res = cr.createClusterRole()
    try:
        assert res.obj
        assert isinstance(res.obj, ClusterRole)
        assert cr.metadata.name == res.obj.metadata.name
        rres = ClusterRole.readClusterRole(cr.metadata.name)
        assert rres.obj
        assert isinstance(rres.obj, ClusterRole)
        assert rres.obj.metadata.name == cr.metadata.name
        dcr = cr.dup()
        dcr.metadata.labels['new-label'] = 'new-value'
        pres = dcr.patchClusterRole(dcr.metadata.name)
        assert pres.obj
        assert isinstance(pres.obj, ClusterRole)
        assert pres.obj.metadata.name == cr.metadata.name
    finally:
        _ = ClusterRole.deleteClusterRole(cr.metadata.name)


def test59():
    """
    test binding a cluster role to a service account
    """
    sa = make_sa57()
    cr = make_cr58()
    crb = ClusterRoleBinding(
        metadata=ObjectMeta(
            name='user-cert-generator',
            labels={'kiamol': 'ch17'}
        ),
        subjects=[Subject(kind='ServiceAccount',
                          name=sa.metadata.name,
                          namespace=e2e_namespace)],
        roleRef=RoleRef(
            apiGroup='rbac.authorization.k8s.io',
            kind='ClusterRole',
            name=cr.metadata.name
        )
    )
    sa_res = sa.createNamespacedServiceAccount(e2e_namespace)
    try:
        assert sa_res.obj
        cr_res = cr.createClusterRole()
        try:
            assert cr_res.obj
            crb_res = crb.createClusterRoleBinding()
            try:
                assert crb_res.obj
                assert isinstance(crb_res.obj, ClusterRoleBinding)
                assert crb_res.obj.metadata.name == crb.metadata.name
                rres = ClusterRoleBinding.readClusterRoleBinding(crb.metadata.name)
                assert rres.obj
                assert isinstance(rres.obj, ClusterRoleBinding)
                assert rres.obj.metadata.name == crb.metadata.name
                dcr = cr.dup()
                dcr.rules[1].verbs.append('watch')
                pres = dcr.patchClusterRole(dcr.metadata.name)
                assert pres.obj
            finally:
                _ = ClusterRoleBinding.deleteClusterRoleBinding(crb.metadata.name)
        finally:
            _ = ClusterRole.deleteClusterRole(cr.metadata.name)
    finally:
        _ = ServiceAccount.deleteNamespacedServiceAccount(sa.metadata.name,
                                                          e2e_namespace)


def test60():
    """
    trying reading component status
    """
    cs = ComponentStatus(metadata=ObjectMeta(name='test60'))
    res = cs.readComponentStatus('controller-manager')
    assert res.obj
    assert isinstance(res.obj, ComponentStatus)
    assert len(res.obj.conditions) > 0


def test61():
    """
    test listing endpoints
    """
    res = EndpointsList.listEndpointsForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, EndpointsList)
    assert len(res.obj.items) > 0


def test62():
    """
    test horizontal pod autoscaling
    """
    hpa = HorizontalPodAutoscaler(
        metadata=ObjectMeta(name='pi-cpu'),
        spec=HorizontalPodAutoscalerSpec(
            scaleTargetRef=CrossVersionObjectReference(
                kind='Deployment',
                apiVersion='apps/v1',
                name='pi-web'
            ),
            minReplicas=1,
            maxReplicas=5,
            targetCPUUtilizationPercentage=75
        )
    )
    res = hpa.createNamespacedHorizontalPodAutoscaler(namespace=e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, HorizontalPodAutoscaler)
        assert res.obj.metadata.name == hpa.metadata.name
        rres = HorizontalPodAutoscaler.readNamespacedHorizontalPodAutoscaler(
            name=hpa.metadata.name, namespace=e2e_namespace
        )
        assert rres.obj
        assert isinstance(rres.obj, HorizontalPodAutoscaler)
        assert rres.obj.metadata.name == hpa.metadata.name
        dhpa = hpa.dup()
        dhpa.metadata.labels = {'new-label': 'see'}
        dhpa.patchNamespacedHorizontalPodAutoscaler(dhpa.metadata.name,
                                                    e2e_namespace)
    finally:
        _ = HorizontalPodAutoscaler.deleteNamespacedHorizontalPodAutoscaler(
            name=hpa.metadata.name, namespace=e2e_namespace
        )


def test63():
    """
    test crud ops on Lease
    """
    l = Lease(
        metadata=ObjectMeta(name='test63-lease'),
        spec=LeaseSpec()
    )
    res = LeaseList.listLeaseForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, LeaseList)
    before_len = len(res.obj.items)
    res = l.createNamespacedLease(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, Lease)
        assert res.obj.metadata.name == l.metadata.name
        res = LeaseList.listLeaseForAllNamespaces()
        assert isinstance(res.obj, LeaseList)
        assert before_len < len(res.obj.items)
        rres = Lease.readNamespacedLease(l.metadata.name,
                                         e2e_namespace)
        assert rres.obj
        assert rres.obj.metadata.name == l.metadata.name
    finally:
        _ = Lease.deleteNamespacedLease(l.metadata.name, e2e_namespace)


def test64():
    """
    test crud ops on LimitRanges
    """
    res = LimitRangeList.listNamespacedLimitRange(e2e_namespace)
    before_len = len(res.obj.items)
    lr = LimitRange(
        metadata=ObjectMeta(name='test65-limitrange'),
        spec=LimitRangeSpec(
            limits=[LimitRangeItem(type="Pod")]
        )
    )
    res = lr.createNamespacedLimitRange(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, LimitRange)
        assert res.obj.metadata.name == lr.metadata.name
        res = LimitRangeList.listNamespacedLimitRange(e2e_namespace)
        assert before_len < len(res.obj.items)
        rres = LimitRange.readNamespacedLimitRange(lr.metadata.name,
                                                   e2e_namespace)
        assert rres.obj
        assert rres.obj.metadata.name == lr.metadata.name
        dlr = lr.dup()
        dlr.metadata.labels = {'new_label': 'now'}
        pres = dlr.patchNamespacedLimitRange(dlr.metadata.name,
                                             e2e_namespace)
        assert pres.obj
        assert pres.obj.metadata.name == dlr.metadata.name
    finally:
        _ = LimitRange.deleteNamespacedLimitRange(lr.metadata.name, e2e_namespace)


def test65():
    """
    test network policy crud ops
    """
    np = NetworkPolicy(
        metadata=ObjectMeta(name='apod-api'),
        spec=NetworkPolicySpec(
            podSelector=LabelSelector(
                matchLabels={'app': 'apod-api'}
            ),
            ingress=[NetworkPolicyIngressRule(
                from_=[NetworkPolicyPeer(
                    podSelector=LabelSelector(
                        matchLabels={'app': 'apod-web'}
                    )
                )],
                ports=[NetworkPolicyPort(port='api')]
            )]
        )
    )
    res = np.createNamespacedNetworkPolicy(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, NetworkPolicy)
        assert res.obj.metadata.name == np.metadata.name
        rres = NetworkPolicy.readNamespacedNetworkPolicy(np.metadata.name,
                                                         e2e_namespace)
        assert rres.obj
        assert isinstance(rres.obj, NetworkPolicy)
        assert np.metadata.name == rres.obj.metadata.name
        dnp = np.dup()
        dnp.metadata.labels = {'new_labels': 'are_here'}
        pres = dnp.patchNamespacedNetworkPolicy(dnp.metadata.name,
                                                e2e_namespace)
        assert pres.obj
        assert isinstance(pres.obj, NetworkPolicy)
        assert pres.obj.metadata.name == np.metadata.name
    finally:
        _ = NetworkPolicy.deleteNamespacedNetworkPolicy(np.metadata.name,
                                                        e2e_namespace)


def test66():
    """
    test priority class crud ops
    """
    pc = PriorityClass(
        metadata=ObjectMeta(name='test66-low'),
        value=100,
        globalDefault=True,
        description='test low priority class'
    )
    res = pc.createPriorityClass()
    try:
        assert res.obj
        assert isinstance(res.obj, PriorityClass)
        assert res.obj.metadata.name == pc.metadata.name
        rres = PriorityClass.readPriorityClass(pc.metadata.name)
        assert rres.obj
        assert isinstance(rres.obj, PriorityClass)
        assert rres.obj.metadata.name == pc.metadata.name
        dpc = pc.dup()
        dpc.metadata.labels = {'new_labels': 'here'}
        pres = dpc.patchPriorityClass(dpc.metadata.name)
        assert pres.obj
    finally:
        _ = PriorityClass.deletePriorityClass(pc.metadata.name)


def test67():
    """
    test replica set crud operations
    """
    rs = ReplicaSet(
        metadata=ObjectMeta(name='whoami-web'),
        spec=ReplicaSetSpec(
            replicas=1,
            selector=LabelSelector(
                matchLabels={'app': 'whoami-web'}
            ),
            template=PodTemplateSpec(
                metadata=ObjectMeta(labels={'app': 'whoami-web'},
                                    name='whoami-web'),
                spec=PodSpec(
                    containers=[Container(image='nginx',
                                          name='nginx',
                                          ports=[ContainerPort(
                                              containerPort=80,
                                              protocol='TCP'
                                          )]
                                          )
                                ]
                )
            )
        )
    )
    res = rs.createNamespacedReplicaSet(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, ReplicaSet)
        assert res.obj.metadata.name == rs.metadata.name
        rres = ReplicaSet.readNamespacedReplicaSet(rs.metadata.name, e2e_namespace)
        assert rres.obj
        drs = rs.dup()
        drs.metadata.labels = {'newLabel': 'here'}
        pres = drs.patchNamespacedReplicaSet(drs.metadata.name, e2e_namespace)
        assert pres.obj
    finally:
        _ = ReplicaSet.deleteNamespacedReplicaSet(rs.metadata.name,
                                                  e2e_namespace)


def test68():
    """
    test resource quota crud ops
    """
    rq = ResourceQuota(
        metadata=ObjectMeta(name='memory-quota'),
        spec=ResourceQuotaSpec(
            hard={'limits.memory': '150Mi'}
        )
    )
    res = rq.createNamespacedResourceQuota(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, ResourceQuota)
        assert res.obj.metadata.name == rq.metadata.name
        rres = ResourceQuota.readNamespacedResourceQuota(rq.metadata.name, e2e_namespace)
        assert rres.obj
        drq = rq.dup()
        drq.metadata.labels = {'newLabel': 'here'}
        pres = drq.patchNamespacedResourceQuota(drq.metadata.name, e2e_namespace)
        assert pres.obj
    finally:
        _ = ResourceQuota.deleteNamespacedResourceQuota(rq.metadata.name,
                                                        e2e_namespace)


def test69():
    """
    test role binding crud ops
    """
    rb = RoleBinding(
        metadata=ObjectMeta(name='reader-view'),
        subjects=[Subject(
            kind='User',
            name='reader@kiamol.net',
            apiGroup='rbac.authorization.k8s.io'
        )],
        roleRef=RoleRef(
            kind='ClusterRole',
            name='view',
            apiGroup='rbac.authorization.k8s.io'
        )
    )
    res = rb.createNamespacedRoleBinding(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, RoleBinding)
        assert res.obj.metadata.name == rb.metadata.name
        rres = RoleBinding.readNamespacedRoleBinding(rb.metadata.name, e2e_namespace)
        assert rres.obj
        drb = rb.dup()
        drb.metadata.labels = {'whowantsalabel': 'me'}
        pres = drb.patchNamespacedRoleBinding(drb.metadata.name, e2e_namespace)
        assert pres.obj
    finally:
        _ = RoleBinding.deleteNamespacedRoleBinding(rb.metadata.name, e2e_namespace)


base_ss = StatefulSet(
    apiVersion="apps/v1",
    kind="StatefulSet",
    metadata=ObjectMeta(name="todo-db", labels={"kiamol": "ch08"}),
    spec=StatefulSetSpec(
        selector=LabelSelector(matchLabels={"app": "todo-db"}),
        serviceName="todo-db",
        template=PodTemplateSpec(
            metadata=ObjectMeta(labels={"app": "todo-db"}),
            spec=PodSpec(
                containers=[
                    Container(
                        name="db",
                        image="postgres:11.6-alpine",
                        command=["/scripts/startup.sh"],
                        env=[
                            EnvVar(
                                name="POSTGRES_PASSWORD_FILE",
                                value="/secrets/postgres_password",
                            ),
                            EnvVar(
                                name="PGPASSWORD",
                                valueFrom=EnvVarSource(
                                    secretKeyRef=SecretKeySelector(
                                        key="POSTGRES_PASSWORD", name="todo-db-secret"
                                    )
                                ),
                            ),
                        ],
                        envFrom=[
                            EnvFromSource(
                                configMapRef=ConfigMapEnvSource(name="todo-db-env")
                            )
                        ],
                        volumeMounts=[
                            VolumeMount(mountPath="/secrets", name="secret"),
                            VolumeMount(mountPath="/scripts", name="scripts"),
                            VolumeMount(mountPath="/conf", name="config"),
                            VolumeMount(
                                mountPath="/docker-entrypoint-initdb.d", name="initdb"
                            ),
                        ],
                    )
                ],
                initContainers=[
                    Container(
                        name="wait-service",
                        image="kiamol/ch03-sleep",
                        command=["/scripts/wait-service.sh"],
                        envFrom=[
                            EnvFromSource(
                                configMapRef=ConfigMapEnvSource(name="todo-db-env")
                            )
                        ],
                        volumeMounts=[
                            VolumeMount(mountPath="/scripts", name="scripts")
                        ],
                    ),
                    Container(
                        name="initialize-replication",
                        image="postgres:11.6-alpine",
                        command=["/scripts/initialize-replication.sh"],
                        env=[
                            EnvVar(
                                name="PGPASSWORD",
                                valueFrom=EnvVarSource(
                                    secretKeyRef=SecretKeySelector(
                                        key="POSTGRES_PASSWORD", name="todo-db-secret"
                                    )
                                ),
                            )
                        ],
                        envFrom=[
                            EnvFromSource(
                                configMapRef=ConfigMapEnvSource(name="todo-db-env")
                            )
                        ],
                        volumeMounts=[
                            VolumeMount(mountPath="/scripts", name="scripts"),
                            VolumeMount(
                                mountPath="/docker-entrypoint-initdb.d", name="initdb"
                            ),
                        ],
                    ),
                ],
                volumes=[
                    Volume(
                        name="secret",
                        secret=SecretVolumeSource(
                            defaultMode=400,
                            secretName="todo-db-secret",
                            items=[
                                KeyToPath(
                                    key="POSTGRES_PASSWORD", path="postgres_password"
                                )
                            ],
                        ),
                    ),
                    Volume(
                        name="scripts",
                        configMap=ConfigMapVolumeSource(
                            defaultMode=555, name="todo-db-scripts"
                        ),
                    ),
                    Volume(
                        name="config",
                        configMap=ConfigMapVolumeSource(
                            defaultMode=444, name="todo-db-config"
                        ),
                    ),
                    Volume(name="initdb", emptyDir=EmptyDirVolumeSource()),
                ],
            ),
        ),
        replicas=2,
    ),
)


def test70():
    """
    test stateful set crud ops
    """
    ss = base_ss.dup()
    res = ss.createNamespacedStatefulSet(e2e_namespace)
    try:
        assert res.obj
        assert isinstance(res.obj, StatefulSet)
        assert res.obj.metadata.name == ss.metadata.name
        rres = StatefulSet.readNamespacedStatefulSet(ss.metadata.name,
                                                     e2e_namespace)
        assert rres.obj
        dss = ss.dup()
        dss.metadata.labels['newkey'] = 'value'
        pres = dss.patchNamespacedStatefulSet(dss.metadata.name,
                                              e2e_namespace)
        assert pres.obj
    finally:
        _ = StatefulSet.deleteNamespacedStatefulSet(ss.metadata.name,
                                                    e2e_namespace)


def test71():
    """
    test token request
    """
    ns = 'test71-tokenrequest-23'
    sa = make_sa57(ns=e2e_namespace)
    tr = TokenRequest(
        metadata=ObjectMeta(namespace=e2e_namespace),
        spec=TokenRequestSpec(
            audiences=[sa.metadata.name],
            expirationSeconds=60*10
        )
    )
    res = sa.createNamespacedServiceAccount(e2e_namespace)
    try:
        assert res.obj
        res = tr.createNamespacedServiceAccountToken(sa.metadata.name,
                                                     e2e_namespace)
        assert res.obj
        assert isinstance(res.obj, TokenRequest)
        assert res.obj.status.token
    finally:
        _ = ServiceAccount.deleteNamespacedServiceAccount(sa.metadata.name,
                                                          e2e_namespace)


def test72():
    """
    test validating webhook configuration crud ops
    """
    name = "servicetokenpolicy"
    vwc = ValidatingWebhookConfiguration(
        metadata=ObjectMeta(
            name=name,
            labels={'kiamol': 'ch16'}
        ),
        webhooks=[ValidatingWebhook(
            name='servicetokenpolicy.kiamol.net',
            sideEffects='None',
            admissionReviewVersions=['v1'],
            rules=[RuleWithOperations(
                operations=['CREATE', 'UPDATE'],
                apiGroups=[""],
                apiVersions=["v1"],
                resources=["pods"]
            )],
            clientConfig=WebhookClientConfig(
                service=ServiceReference(
                    name='admission-webhook',
                    namespace=e2e_namespace,
                    path="/validate"
                ),
            )
        )]
    )
    res = vwc.createValidatingWebhookConfiguration()
    try:
        assert res.obj
        assert isinstance(res.obj, ValidatingWebhookConfiguration)
        assert res.obj.metadata.name == vwc.metadata.name
        rres = ValidatingWebhookConfiguration.readValidatingWebhookConfiguration(name)
        assert rres.obj
        assert isinstance(rres.obj, ValidatingWebhookConfiguration)
        assert rres.obj.metadata.name == name
        vwc.metadata.labels['new_label'] = 'value'
        pres = vwc.patchValidatingWebhookConfiguration(name)
        assert pres.obj
    finally:
        _ = ValidatingWebhookConfiguration.deleteValidatingWebhookConfiguration(name)


if __name__ == "__main__":
    beginning()
    the_tests = {k: v for k, v in globals().items()
                 if k.startswith('test') and callable(v)}
    for k, v in the_tests.items():
        if k == 'test07a':
            continue  # fails way down in kubernetes
        try:
            v()
        except SkipTest:
            pass
        except Exception as e:
            print(f'{k} failed with {str(e)}, {e.__class__}')
            ending()
            raise
    ending()
