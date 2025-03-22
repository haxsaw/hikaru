from hikaru.model.rel_1_29.v1 import *
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release
from hikaru.crd import (register_crd_class, HikaruCRDDocumentMixin,
                        get_crd_schema)
from hikaru.meta import FieldMetadata as fm
import time
from typing import Optional
from dataclasses import dataclass, field
from kubernetes import config
import pytest

namespace = "rel-1-29-crd"


def beginning():
    set_default_release("rel_1_29")
    ns: Namespace = Namespace(metadata=ObjectMeta(name=namespace))
    ns_response = ns.create()

    # Create a Role granting permissions on the "myplatforms" resource in this namespace.
    role = Role(
        metadata=ObjectMeta(name="crd-ns-role", namespace=namespace),
        rules=[
            PolicyRule(
                apiGroups=["example.com"],
                resources=["myplatforms"],
                verbs=["create", "get", "list", "update", "patch", "delete"]
            )
        ]
    )
    try:
        role.createNamespacedRole(namespace)
    except Exception as e:
        if "already exists" in str(e):
            pass
        else:
            raise

    # Create a RoleBinding binding the default service account in this namespace to the Role.
    rb = RoleBinding(
        metadata=ObjectMeta(name="crd-ns-rolebinding", namespace=namespace),
        subjects=[Subject(kind="ServiceAccount", name="default", namespace=namespace)],
        roleRef=RoleRef(apiGroup="rbac.authorization.k8s.io", kind="Role", name="crd-ns-role")
    )
    try:
        rb.createNamespacedRoleBinding(namespace)
    except Exception as e:
        if "already exists" in str(e):
            pass
        else:
            raise

    return ns_response


def ending():
    time.sleep(0.3)
    Namespace.deleteNamespace(namespace)


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res
    ending()


@dataclass
class MyPlatformSpec(HikaruBase):
    appId: str
    language: str = field(metadata=fm(enum=["csharp", "python", "go"]))
    environmentType: str = field(metadata=fm(enum=["dev", "test", "prod"]))
    os: Optional[str] = field(default=None, metadata=fm(enum=["windows", "linux"]))
    instanceSize: Optional[str] = field(default=None,
                                        metadata=fm(enum=["small", "medium", "large"]))
    replicas: Optional[int] = field(default=1,
                                    metadata=fm(minimum=1))


@dataclass
class MyPlatform(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    spec: Optional[MyPlatformSpec] = None
    apiVersion: str = "example.com/v1"
    kind: str = "MyPlatform"


register_crd_class(MyPlatform, plural_name="myplatforms", is_namespaced=True)
config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

crd_defined: bool = False
crd_instance_created: bool = False


def test01():
    """
    Create the CRD definition
    """
    global crd_defined
    schema: JSONSchemaProps = get_crd_schema(MyPlatform)

    crd: CustomResourceDefinition = CustomResourceDefinition(
        spec=CustomResourceDefinitionSpec(
            group="example.com",
            names=CustomResourceDefinitionNames(
                shortNames=["myp"],
                plural="myplatforms",
                singular="myplatform",
                kind="MyPlatform"
            ),
            scope="Namespaced",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema
                )
            )]
        ),
        metadata=ObjectMeta(name="myplatforms.example.com")
    )

    new_crd: CustomResourceDefinition
    try:
        new_crd = crd.read()
    except:
        new_crd = crd.create()
    assert new_crd
    crd_defined = True


def test02():
    """
    Create an instance of the CRD
    """
    global crd_instance_created

    if not crd_defined:
        raise Exception("Can't create instance; crd not defined")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go", namespace=namespace),
        spec=MyPlatformSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    new: MyPlatform = mc.create()
    assert new
    time.sleep(0.2)
    crd_instance_created = True


def test03():
    """
    Read the CRD instance
    """
    if not crd_instance_created:
        raise Exception("Can't read the instance; not defined")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go", namespace=namespace),
    )

    existing: MyPlatform = mc.read()
    assert existing


def test04():
    """
    Update the CRD instance
    """
    if not crd_instance_created:
        raise Exception("Can't update the instance; not defined")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go", namespace=namespace),
    )

    existing: MyPlatform = mc.read()
    existing.spec.language = "go"
    updated: MyPlatform = existing.update()
    assert updated and updated.spec.language == "go"


def test05():
    """
    Delete the instance
    """
    global crd_instance_created

    if not crd_instance_created:
        raise Exception("Can't delete the instance; not created")

    mc: MyPlatform = MyPlatform(
        metadata=ObjectMeta(name="first-go", namespace=namespace),
    )

    result = mc.delete()
    crd_instance_created = False
    assert result


def test06():
    """
    Delete the namespaced CRD definition
    """
    global crd_defined

    if not crd_defined:
        raise Exception("Can't delete; crd not defined")

    schema: JSONSchemaProps = get_crd_schema(MyPlatform)
    crd: CustomResourceDefinition = CustomResourceDefinition(
        spec=CustomResourceDefinitionSpec(
            group="example.com",
            names=CustomResourceDefinitionNames(
                shortNames=["myp"],
                plural="myplatforms",
                singular="myplatform",
                kind="MyPlatform"
            ),
            scope="Namespaced",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema
                )
            )]
        ),
        metadata=ObjectMeta(name="myplatforms.example.com")
    )
    result = crd.delete()
    crd_defined = False
    assert result
