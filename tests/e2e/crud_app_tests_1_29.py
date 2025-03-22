from dataclasses import dataclass
from os import getcwd
from pathlib import Path
import time
from typing import cast, Dict, List
from kubernetes import config
from kubernetes.client.exceptions import ApiException
from hikaru import *
from hikaru.model.rel_1_29.v1 import *
from hikaru.app import Application, Reporter
import pytest

set_default_release("rel_1_29")

if getcwd().endswith('/e2e'):
    base_path = Path('../test_yaml')
else:
    base_path = Path('test_yaml')

test_ns = "crud-app-test-ns-1-29"


def beginning():
    set_default_release("rel_1_29")
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    return True


def ending():
    pass


@pytest.fixture(scope="module", autouse=True)
def setup():
    res = beginning()
    yield res
    ending()


# Now the Application model includes all the components that comprise the app.
@dataclass
class CRUD_1_29(Application):
    ns: Namespace
    dep: Deployment
    role: Role
    rb: RoleBinding

    @classmethod
    def standard_instance(cls, namespace: str):
        # Create a Namespace object. We let Application.create() handle its creation.
        ns_obj = Namespace(metadata=ObjectMeta(name=namespace))

        # Load the deployment YAML and set its namespace and ensure it uses the default service account.
        path = base_path / 'apps-deployment.yaml'
        dep = cast(Deployment, load_full_yaml(path=str(path))[0])
        dep.metadata.namespace = namespace
        if not dep.spec:
            dep.spec = PodSpec()
        if not dep.spec.template:
            dep.spec.template = PodTemplateSpec(metadata=ObjectMeta(), spec=PodSpec())
        dep.spec.template.spec.serviceAccountName = "default"

        # Create a Role object to grant necessary permissions on deployments in this namespace.
        role = Role(
            metadata=ObjectMeta(name="crud-app-role", namespace=namespace),
            rules=[
                PolicyRule(
                    apiGroups=["apps"],
                    resources=["deployments"],
                    verbs=["create", "get", "list", "update", "patch", "delete"]
                )
            ]
        )

        # Create a RoleBinding that binds the default service account in this namespace to the Role.
        rb = RoleBinding(
            metadata=ObjectMeta(name="crud-app-rolebinding", namespace=namespace),
            subjects=[Subject(kind="ServiceAccount", name="default", namespace=namespace)],
            roleRef=RoleRef(apiGroup="rbac.authorization.k8s.io", kind="Role", name="crud-app-role")
        )

        # Compose the application from its parts. When create() is called on the application,
        # Hikaru will take care of creating the Namespace, Deployment, Role, and RoleBinding.
        app = CRUD_1_29(ns=ns_obj, dep=dep, role=role, rb=rb)
        return app


def test01():
    """
    Testing delete first so we have something that can wipe out a created app
    """
    app: CRUD_1_29 = CRUD_1_29.standard_instance(test_ns + "test01")
    try:
        _ = app.delete()
    except ApiException as e:
        if e.status != 404:
            raise


def test02():
    """
    Testing create
    """
    app: CRUD_1_29 = CRUD_1_29.standard_instance(test_ns + "test02")
    assert app.create()
    assert app.delete()


def test03():
    """
    Test read for an existing app
    """
    ignore_attrs = {'resourceVersion',
                    'deployment.kubernetes.io/revision',
                    'managedFields',
                    'observedGeneration',
                    'unavailableReplicas',
                    'conditions',
                    'replicas',
                    'updatedReplicas'}
    app: CRUD_1_29 = CRUD_1_29.standard_instance(test_ns + "test03")
    assert app.create()
    try:
        # Now read the application via its instance_id.
        read_app: CRUD_1_29 = CRUD_1_29.read(app.instance_id)
        assert read_app is not None
        assert read_app.instance_id == app.instance_id
        diffs: Dict[str, List[DiffDetail]] = app.diff(read_app)
        for attr, l in diffs.items():
            assert attr == "dep", f"unexpected attribute in diff: {attr}"
            for d in l:
                assert d.attrname in ignore_attrs, f"unexpected diff attr in dep: {d.attrname}"
    finally:
        app.delete()


def test04():
    """
    Perform an update on an app's components
    """
    app: CRUD_1_29 = CRUD_1_29.standard_instance(test_ns + "test04")
    assert app.create()
    try:
        # Read the app a few times to stabilize state.
        app = CRUD_1_29.read(app.instance_id)
        app = CRUD_1_29.read(app.instance_id)
        time.sleep(0.2)
        app = CRUD_1_29.read(app.instance_id)
        # Modify annotations in both the Deployment and Namespace.
        app.dep.metadata.annotations["test04"] = "dep-change"
        app.ns.metadata.annotations["test04"] = "ns-change"
        app.update()
        new_app: CRUD_1_29 = CRUD_1_29.read(app.instance_id)
        assert new_app.dep.metadata.annotations["test04"] == 'dep-change'
        assert new_app.ns.metadata.annotations['test04'] == 'ns-change'
    finally:
        app.delete()
