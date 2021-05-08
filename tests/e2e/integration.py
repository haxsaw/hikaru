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
import base64
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
    res = Endpoints.listEndpointsForAllNamespaces()
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
    res = Event.listEventForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, EventList)
    assert len(res.obj.items) > 0


def test26():
    """
    test listing events via event list
    """
    res = EventList.listNamespacedEvent('default')
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
    res = Lease.listLeaseForAllNamespaces()
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
    res = LimitRangeList.listNamespacedLimitRange('default')
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
    res = SecretList.listNamespacedSecret('default')
    before_len = len(res.obj.items)
    secret = Secret(metadata=ObjectMeta(name='seekrit'),
                    data={'pw1': base64.b64encode(b'bibble').decode(),
                          'pw2': base64.b64encode(b'bobble').decode()})
    res = secret.createNamespacedSecret('default')
    assert res.obj
    res = SecretList.listNamespacedSecret('default')
    assert before_len < len(res.obj.items)
    rres = Secret.readNamespacedSecret(name=secret.metadata.name,
                                       namespace='default')
    assert rres.obj
    assert secret.metadata.name == rres.obj.metadata.name
    dres = Secret.deleteNamespacedSecret(secret.metadata.name,
                                         'default')
    assert dres.obj


def test53():
    """
    test crud ops on pod templates
    """
    res = PodTemplateList.listNamespacedPodTemplate('default')
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
    res = pt.createNamespacedPodTemplate('default')
    assert res.obj
    res = PodTemplateList.listNamespacedPodTemplate('default')
    assert before_len < len(res.obj.items)
    rres = PodTemplate.readNamespacedPodTemplate(pt.metadata.name, 'default')
    assert rres.obj
    assert rres.obj.metadata.name == pt.metadata.name
    dres = PodTemplate.deleteNamespacedPodTemplate(pt.metadata.name, 'default')
    assert dres.obj


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
    res = pvc.createNamespacedPersistentVolumeClaim('default')
    assert res.obj
    assert isinstance(res.obj, PersistentVolumeClaim)
    assert res.obj.metadata.name == pvc.metadata.name
    rres = PersistentVolumeClaim.readNamespacedPersistentVolumeClaim(
        pvc.metadata.name, 'default')
    assert rres.obj
    assert isinstance(rres.obj, PersistentVolumeClaim)
    assert rres.obj.metadata.name == pvc.metadata.name
    dres = PersistentVolumeClaim.deleteNamespacedPersistentVolumeClaim(pvc.metadata.name,
                                                                       'default')


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
    assert res.obj
    rres = PersistentVolume.readPersistentVolume(pv.metadata.name)
    assert rres.obj
    assert isinstance(rres.obj, PersistentVolume)
    assert rres.obj.metadata.name == pv.metadata.name
    dres = PersistentVolume.deletePersistentVolume(pv.metadata.name)
    assert dres.obj


def make_sa57() -> ServiceAccount:
    sa = ServiceAccount(
        metadata=ObjectMeta(
            name='user-cert-generator',
            labels={'kiamol': 'ch17'}
        )
    )
    return sa


def test57():
    """
    test service account crud operations
    """
    sa = make_sa57()
    res = sa.createNamespacedServiceAccount('default')
    assert res.obj
    assert isinstance(res.obj, ServiceAccount)
    assert res.obj.metadata.name == sa.metadata.name
    rres = ServiceAccount.readNamespacedServiceAccount(sa.metadata.name,
                                                       'default')
    assert rres.obj
    assert isinstance(rres.obj, ServiceAccount)
    assert rres.obj.metadata.name == sa.metadata.name
    dsa = sa.dup()
    dsa.metadata.labels['extra-label'] = 'value'
    pres = dsa.patchNamespacedServiceAccount(sa.metadata.name,
                                             'default')
    assert pres.obj
    assert isinstance(pres.obj, ServiceAccount)
    assert pres.obj.metadata.name == sa.metadata.name
    dres = ServiceAccount.deleteNamespacedServiceAccount(sa.metadata.name,
                                                         'default')
    assert dres.obj


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
    dres = ClusterRole.deleteClusterRole(cr.metadata.name)
    assert dres.obj


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
                          namespace='default')],
        roleRef=RoleRef(
            apiGroup='rbac.authorization.k8s.io',
            kind='ClusterRole',
            name=cr.metadata.name
        )
    )
    sa_res = sa.createNamespacedServiceAccount('default')
    assert sa_res.obj
    cr_res = cr.createClusterRole()
    assert cr_res.obj
    crb_res = crb.createClusterRoleBinding()
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
    dres = ClusterRoleBinding.deleteClusterRoleBinding(crb.metadata.name)
    assert dres.obj
    _ = ClusterRole.deleteClusterRole(cr.metadata.name)
    _ = ServiceAccount.deleteNamespacedServiceAccount(sa.metadata.name,
                                                      'default')


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
    res = Endpoints.listEndpointsForAllNamespaces()
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
    res = hpa.createNamespacedHorizontalPodAutoscaler(namespace='default')
    assert res.obj
    assert isinstance(res.obj, HorizontalPodAutoscaler)
    assert res.obj.metadata.name == hpa.metadata.name
    rres = HorizontalPodAutoscaler.readNamespacedHorizontalPodAutoscaler(
        name=hpa.metadata.name, namespace='default'
    )
    assert rres.obj
    assert isinstance(rres.obj, HorizontalPodAutoscaler)
    assert rres.obj.metadata.name == hpa.metadata.name
    dhpa = hpa.dup()
    dhpa.metadata.labels = {'new-label': 'see'}
    dhpa.patchNamespacedHorizontalPodAutoscaler(dhpa.metadata.name,
                                                'default')
    dres = HorizontalPodAutoscaler.deleteNamespacedHorizontalPodAutoscaler(
        name=hpa.metadata.name, namespace='default'
    )
    assert dres.obj


def test63():
    """
    test crud ops on Lease
    """
    l = Lease(
        metadata=ObjectMeta(name='test63-lease'),
        spec=LeaseSpec()
    )
    res = Lease.listLeaseForAllNamespaces()
    assert res.obj
    assert isinstance(res.obj, LeaseList)
    before_len = len(res.obj.items)
    res = l.createNamespacedLease('default')
    assert res.obj
    assert isinstance(res.obj, Lease)
    assert res.obj.metadata.name == l.metadata.name
    res = Lease.listLeaseForAllNamespaces()
    assert isinstance(res.obj, LeaseList)
    assert before_len < len(res.obj.items)
    rres = Lease.readNamespacedLease(l.metadata.name,
                                     'default')
    assert rres.obj
    assert rres.obj.metadata.name == l.metadata.name
    dres = Lease.deleteNamespacedLease(l.metadata.name, 'default')
    assert dres.obj


def test64():
    """
    test crud ops on LimitRanges
    """
    res = LimitRangeList.listNamespacedLimitRange('default')
    before_len = len(res.obj.items)
    lr = LimitRange(
        metadata=ObjectMeta(name='test65-limitrange'),
        spec=LimitRangeSpec(
            limits=[LimitRangeItem(type="Pod")]
        )
    )
    res = lr.createNamespacedLimitRange('default')
    assert res.obj
    assert isinstance(res.obj, LimitRange)
    assert res.obj.metadata.name == lr.metadata.name
    res = LimitRangeList.listNamespacedLimitRange('default')
    assert before_len < len(res.obj.items)
    rres = LimitRange.readNamespacedLimitRange(lr.metadata.name,
                                               'default')
    assert rres.obj
    assert rres.obj.metadata.name == lr.metadata.name
    dlr = lr.dup()
    dlr.metadata.labels = {'new_label': 'now'}
    pres = dlr.patchNamespacedLimitRange(dlr.metadata.name,
                                         'default')
    assert pres.obj
    assert pres.obj.metadata.name == dlr.metadata.name
    dres = LimitRange.deleteNamespacedLimitRange(lr.metadata.name,
                                                 'default')
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
