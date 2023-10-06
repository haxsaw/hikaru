# Copyright (c) 2023 Incisive Technology Ltd
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

from hikaru.model.rel_1_26.v1 import *
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release
from hikaru.crd import (register_crd_class, HikaruCRDDocumentMixin,
                        get_crd_schema)
from hikaru.meta import FieldMetadata as fm
from typing import Optional
from dataclasses import dataclass, field
from kubernetes import config
import pytest


namespace = "rel-1-26-crd"


def beginning():
    set_default_release("rel_1_26")
    ns: Namespace = Namespace(metadata=ObjectMeta(name=namespace))
    return ns.create()


def ending():
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
    os: Optional[str] = field(default=None, metadata=fm(enum=["windows",
                                                              "linux"]))
    instanceSize: Optional[str] = field(default=None,
                                        metadata=fm(enum=["small",
                                                          "medium",
                                                          "large"]))
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

    # now make the CRD object with the schema
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
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
        new_crd: CustomResourceDefinition = crd.create()
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

    # now make the CRD object with the schema
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
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
