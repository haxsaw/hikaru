# Copyright (c) 2022 Incisive Technology Ltd
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
from hikaru.model.rel_1_25.v1 import *
from hikaru import HikaruBase, HikaruDocumentBase, set_default_release
from hikaru.crd import (register_crd_class, HikaruCRDDocumentMixin,
                        get_crd_schema)
from hikaru.meta import FieldMetadata as fm
from typing import Optional
from dataclasses import dataclass, field
from kubernetes import config

set_default_release("rel_1_25")


@dataclass
class MyClusterSpec(HikaruBase):
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
class MyCluster(HikaruDocumentBase, HikaruCRDDocumentMixin):
    spec: MyClusterSpec
    metadata: ObjectMeta
    apiVersion: str = "example.com/v1"
    kind: str = "MyCluster"


register_crd_class(MyCluster, plural_name="myclusters", is_namespaced=False)
config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

crd_defined: bool = False
crd_instance_created: bool = False


def test01():
    """
    Create the CRD in the system if not already there
    """
    global crd_defined
    schema: JSONSchemaProps = get_crd_schema(MyCluster)
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group="example.com",
            names=CustomResourceDefinitionNames(
                shortNames=["myc"],
                plural="myclusters",
                singular="mycluster",
                kind="MyCluster"
            ),
            scope="Cluster",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema
                )
            )]
        ),
        metadata=ObjectMeta(name="myclusters.example.com")
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

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    new: MyCluster = mc.create()
    assert new
    crd_instance_created = True


def test03():
    """
    Read the CRD instance
    """
    if not crd_instance_created:
        raise Exception("Can't read the instance; not defined")

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    existing: MyCluster = mc.read()
    assert existing


def test04():
    """
    Update the CRD instance
    """
    if not crd_instance_created:
        raise Exception("Can't update the instance; not defined")

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    existing: MyCluster = mc.read()
    existing.spec.language = "go"
    updated: MyCluster = existing.update()
    assert updated and updated.spec.language == "go"


def test05():
    """
    Delete the instance
    """
    global crd_instance_created

    if not crd_instance_created:
        raise Exception("Can't delete the instance; not created")

    mc: MyCluster = MyCluster(
        metadata=ObjectMeta(name="first-go"),
        spec=MyClusterSpec(
            appId="first-go-spec",
            language="python",
            environmentType="dev",
            instanceSize="small"
        )
    )

    result = mc.delete()
    crd_instance_created = False
    assert result


def test06():
    """
    Delete the CRD definition
    """
    global crd_defined

    if crd_instance_created or not crd_defined:
        raise Exception("can't delete the definition")
    schema: JSONSchemaProps = get_crd_schema(MyCluster)
    crd: CustomResourceDefinition = \
        CustomResourceDefinition(spec=CustomResourceDefinitionSpec(
            group="example.com",
            names=CustomResourceDefinitionNames(
                shortNames=["myc"],
                plural="myclusters",
                singular="mycluster",
                kind="MyCluster"
            ),
            scope="Cluster",
            versions=[CustomResourceDefinitionVersion(
                name="v1",
                served=True,
                storage=True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema  # schema goes here!
                )
            )]
        ),
        metadata=ObjectMeta(name="myclusters.example.com")
    )
    result = crd.delete()
    crd_defined = False
    assert result
