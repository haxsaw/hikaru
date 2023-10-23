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
import time
from os import getcwd
from pathlib import Path
from typing import cast
from unittest import SkipTest
from hikaru import *
from hikaru.model.rel_1_23.v1 import *
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
crud_namespace = 'crud-test-ns-rel-1-23'


def beginning():
    set_default_release('rel_1_23')
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    ns = Namespace(metadata=ObjectMeta(name=crud_namespace))
    try:
        res = ns.read()
    except:
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
        d.read()
        time.sleep(0.15)
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
        time.sleep(0.1)
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
        time.sleep(0.2)
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
        s.read()
        s.metadata.labels['test'] = 'test03'
        s.update()
    finally:
        s.delete()


def test04():
    """
    Create a namespace via CRUD
    """
    path = base_path / "core-namespace-23.yaml"
    ns: Namespace = cast(Namespace, load_full_yaml(path=str(path))[0])
    ns.metadata.name = f"{crud_namespace}test04"
    ns.create()
    try:
        ns.read()
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
        r.read()
        r.metadata.labels['test'] = 'test07'
        r.update()
    finally:
        r.delete()


def test08():
    """
    create an api service via crud
    """
    path = base_path / "api-service-1_23.yaml"
    api: APIService = cast(APIService, load_full_yaml(path=str(path))[0])
    api.metadata.namespace = crud_namespace
    api.create()
    try:
        api.read()
        api.read()
        api.metadata.labels['test'] = 'test08'
        api.update()
    finally:
        api.delete()


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
    create/manage a service via crud
    """
    svcname = 'crud-test09'
    svc: Service = make_svc(svcname)
    svc.metadata.namespace = crud_namespace
    svc.create()
    try:
        svc.read()
        svc.read()
        svc.metadata.labels['test'] = 'test09'
        svc.update()
    finally:
        svc.delete()


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
    make a replication controller via crud
    """
    name = 'rc-test10'
    rc = make_rc(name)
    rc.metadata.namespace = crud_namespace
    rc.create()
    try:
        rc.read()
        time.sleep(0.1)
        rc.read()
        rc.metadata.labels['test'] = 'test10'
        rc.update()
    finally:
        rc.delete()


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
    make a config map via crud
    """
    name = 'cm-test11'
    cm: ConfigMap = make_cm(name)
    cm.metadata.namespace = crud_namespace
    cm.create()
    try:
        cm.read()
        cm.read()
        cm.metadata.labels['testt'] = 'test11'
        cm.update()
    finally:
        cm.delete()


job_base = Job(metadata=ObjectMeta(name=''),
               spec=JobSpec(template=
                            PodTemplateSpec(metadata=ObjectMeta(name=''),
                                            spec=PodSpec(
                                                containers=[Container(
                                                    image='busybox',
                                                    name='',
                                                    command=['sh', '-c',
                                                             'sleep 5']
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


def test12():
    """
    make a job via crud
    """
    name = 'job-test12'
    job: Job = make_job(name)
    job.metadata.namespace = crud_namespace
    job.create()
    try:
        job.read()
        job.read()
        time.sleep(0.2)
        job.read()
        job.metadata.labels['test'] = 'test12'
        job.update()
    finally:
        job.delete()


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


def test13():
    """
    make a daemon set via crud
    """
    name = 'ds-test15'
    ds = make_daemonset(name)
    ds.metadata.namespace = crud_namespace
    ds.create()
    try:
        ds.read()
        ds.read()
        time.sleep(0.1)
        ds.read()
        ds.metadata.labels['test'] = 'test13'
        ds.update()
    finally:
        ds.delete()


def test14():
    """
    make a persistent volume claim via crud
    """
    pvc = PersistentVolumeClaim(
        metadata=ObjectMeta(
            name='postgres-pvc-kiamol',
            namespace=crud_namespace
        ),
        spec=PersistentVolumeClaimSpec(
            accessModes=['ReadWriteOnce'],
            storageClassName='kiamol',
            resources=ResourceRequirements(
                requests={'storage': '100Mi'}
            )
        )
    )
    pvc.create()
    try:
        pvc.read()
        pvc.read()
        pvc.metadata.labels['test'] = 'test14'
        pvc.update()
    finally:
        pvc.delete()


def test15():
    """
    make a service account via crud
    """
    sa = ServiceAccount(
        metadata=ObjectMeta(
            name='user-cert-generator',
            namespace=crud_namespace,
            labels={'kiamol': 'ch17'}
        )
    )
    sa.create()
    try:
        sa.read()
        sa.read()  # seems that there may be an update to the resource after 1st read
        sa.metadata.labels['test'] = 'test15'
        sa.update()
    finally:
        sa.delete()


def test16():
    """
    create a cluster role via crud
    """
    cr = ClusterRole(
        metadata=ObjectMeta(
            name='create-approve-csr',
            namespace=crud_namespace,
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
    cr.create()
    try:
        cr.read()
        cr.read()
        cr.metadata.labels['test'] = 'test116'
        cr.update()
    finally:
        cr.delete()


def test17():
    """
    component status via crud
    :return:
    """
    cs = ComponentStatus()
    cs.read(name='controller-manager')
    assert len(cs.conditions) > 0


def test18():
    """
    horizontal pod autoscaler via crud
    """
    hpa = HorizontalPodAutoscaler(
        metadata=ObjectMeta(name='pi-cpu',
                            namespace=crud_namespace),
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
    hpa.create()
    try:
        hpa.read()
        hpa.read()
        hpa.metadata.labels['test'] = 'test18'
        hpa.update()
    finally:
        hpa.delete()


def test19():
    """
    create network policy via crud
    """
    np = NetworkPolicy(
        metadata=ObjectMeta(name='apod-api',
                            namespace=crud_namespace),
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
    np.create()
    try:
        np.read()
        np.read()
        np.metadata.labels['test'] = 'test21'
        np.update()
    finally:
        np.delete()


def test20():
    """
    priority class via crud
    """
    pc = PriorityClass(
        metadata=ObjectMeta(name='test66-low'),
        value=100,
        globalDefault=True,
        description='test low priority class'
    )
    pc.create()
    try:
        pc.read()
        pc.read()
        pc.metadata.labels['test'] = 'test20'
        pc.update()
    finally:
        pc.delete()


def test21():
    """
    replica set via crud
    """
    rs = ReplicaSet(
        metadata=ObjectMeta(name='whoami-web',
                            namespace=crud_namespace),
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
    rs.create()
    try:
        rs.read()
        rs.read()
        rs.metadata.labels['test'] = 'test21'
        rs.update()
    finally:
        rs.delete()


def test22():
    """
    resource quota via crud
    """
    rq = ResourceQuota(
        metadata=ObjectMeta(name='memory-quota',
                            namespace=crud_namespace),
        spec=ResourceQuotaSpec(
            hard={'limits.memory': '150Mi'}
        )
    )
    rq.create()
    try:
        rq.read()
        rq.read()
        rq.metadata.labels['test'] = 'test22'
        rq.update()
    finally:
        rq.delete()


def test23():
    """
    role binding via crud
    """
    rb = RoleBinding(
        metadata=ObjectMeta(name='reader-view',
                            namespace=crud_namespace),
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
    rb.create()
    try:
        rb.read()
        rb.read()
        rb.metadata.labels['test'] = 'test23'
        rb.update()
    finally:
        rb.delete()


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
