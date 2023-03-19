from dataclasses import dataclass
from typing import Optional
from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from hikaru.crd import (register_crd_schema, HikaruCRDDocumentMixin)


set_default_release("rel_1_23")


# test01 stuff
@dataclass
class Resource01(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    kind: str = "Resource01"
    apiVersion: str = "v1"
    group: str = "incisivetech.co.uk"


register_crd_schema(Resource01, "resource01s", is_namespaced=True)


def test01():
    """
    Check that the class can generate empty instances that include existing sub-objects
    """
    i: Resource01 = Resource01.get_empty_instance()
    assert i.metadata is not None, "No meta object in the automatically generated instance"
    assert i.kind == 'Resource01', f'kind is {i.kind}'
    assert i.apiVersion == 'v1', f'apiVersion is {i.apiVersion}'


def test02():
    """
    Check out making a new object manually
    """
    i: Resource01 = Resource01(ObjectMeta(name="test02"))
    assert i.metadata is not None, "meta data turned out None somehow"
    assert i.metadata.name == 'test02', f"metadata's name is {i.metadata.name}"


def test03():
    """
    Manually make an instance and turn it into a dict
    """
    i: Resource01 = Resource01(metadata=ObjectMeta(name="test03"))
    d = i.to_dict()
    assert isinstance(d, dict), f"to_dict() resulted in a {type(d)}"


def test04():
    """
    Round-trip a crd instance to a dict and back to an object
    """
    i: Resource01 = Resource01(metadata=ObjectMeta(name="test04"))
    d = i.to_dict()
    new_i: Resource01 = from_dict(d)
    assert isinstance(new_i, Resource01), f"from_dict() yielded a {type(new_i)}"
    assert new_i.metadata is not None, "no metadata in the recreated object"
    # also check get_clean_dict()
    d = get_clean_dict(i)
    new_i2: Resource01 = from_dict(d)
    assert isinstance(new_i2, Resource01), f"from_dict() on a get_clean_dict failed"
    assert new_i2.metadata is not None, "no metadata in the recreated get_clean_dict() dict"


def test05():
    """
    Round-trip a crd instance to JSON and back
    """
    i: Resource01 = Resource01(metadata=ObjectMeta(name="test05"))
    j: str = get_json(i)
    new_i: Resource01 = from_json(j)
    assert isinstance(new_i, Resource01), f"Got the wrong type from_json(): {new_i.__class__.__name__}"
    assert new_i.metadata is not None, "No metadata when coming from JSON"


def test06():
    """
    Round-trip a crd instance through YAML
    """
    i: Resource01 = Resource01(metadata=ObjectMeta(name="test06"))
    y: str = get_yaml(i)
    new_i: Resource01 = load_full_yaml(yaml=y)[0]
    assert isinstance(new_i, Resource01), f"Got a {new_i.__class__.__name__}"
    assert new_i.metadata is not None, "got not metadata object"


# test02 stuff
@dataclass
class Subunit02(HikaruBase):
    f1: int
    f2: float
    f3: str


@dataclass
class Resource02(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    subunit: Subunit02
    kind: str = "Resource02"
    apiVersion: str = 'v1'
    group: str = "incisivetech.co.uk"


register_crd_schema(Resource02, "resource02s", is_namespaced=True)


def test07():
    """
    Check that the class can generate empty instances that include new sub-objects
    """
    i: Resource02 = Resource02.get_empty_instance()
    assert i.metadata is not None, "No metadata in the object"
    assert i.subunit is not None, "No subunit in the object"
    assert isinstance(i.subunit, Subunit02), (f"wrong type for subunit:"
                                              f"{i.subunit.__class__.__name__}")


def test08():
    """
    Roundtrip crd with custom sub-object through a dict
    """
    i: Resource02 = Resource02(metadata=ObjectMeta(name="test08"),
                               subunit=Subunit02(f1=33, f2=3.14, f3="f3-test08"))
    d = i.to_dict()
    new_i: Resource02 = from_dict(d)
    assert isinstance(new_i, Resource02), f"wrong type recreated; got" \
                                          f"{new_i.__class__.__name__}"
    assert new_i.subunit is not None, "No subunit in recreated object"
    assert new_i.subunit.f1 == 33
    assert new_i.subunit.f2 == 3.14
    assert new_i.subunit.f3 == "f3-test08"


def test09():
    """
    Round-trip a CRD with custom sub-object through YAML
    """
    i: Resource02 = Resource02(metadata=ObjectMeta(name="test09"),
                               subunit=Subunit02(f1=99, f2=0.1, f3="f3-test09"))
    y: str = get_yaml(i)
    new_i: Resource02 = load_full_yaml(yaml=y)[0]
    assert isinstance(new_i, Resource02), f"wrong type: {type(new_i)}"
    assert new_i.subunit is not None, "no subunit in recreated resource"
    assert new_i.subunit.f1 == 99
    assert new_i.subunit.f2 == 0.1
    assert new_i.subunit.f3 == "f3-test09"
