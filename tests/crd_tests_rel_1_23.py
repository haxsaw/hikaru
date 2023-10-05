#
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
from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from hikaru.crd import (register_crd_class, HikaruCRDDocumentMixin, get_crd_schema)
from hikaru.meta import FieldMetadata as FM
from dataclasses import dataclass, field
from typing import Optional, List, Union, Dict
import pytest


set_default_release("rel_1_23")


def beginning():
    Response.set_false_for_internal_tests = False
    return Response


def ending():
    Response.set_false_for_internal_tests = True


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res
    ending()


class CRDTestExp(Exception):
    pass


class MockApiClient(object):
    def __init__(self, gen_failure=False, raise_exp=False):
        self.body = None
        self.client_side_validation = 1
        self.gen_failure = gen_failure
        self.raise_exp = raise_exp

    def select_header_accept(self, accepts):
        """Returns `Accept` based on an array of accepts provided.

        :param accepts: List of headers.
        :return: Accept (e.g. application/json).
        """
        if not accepts:
            return

        accepts = [x.lower() for x in accepts]

        if 'application/json' in accepts:
            return 'application/json'
        else:
            return ', '.join(accepts)

    def select_header_content_type(self, content_types: list):
        if not content_types:
            return 'application/json'

        content_types = [x.lower() for x in content_types]

        if 'application/json' in content_types or '*/*' in content_types:
            return 'application/json'
        else:
            return content_types[0]

    def call_api(self, path, verb, path_params, query_params,
                 body=None, **kwargs):
        if self.raise_exp:
            raise CRDTestExp("Synthetic failure")
        if isinstance(body, dict) and body:
            body = from_dict(body)
        self.body = body
        return self.body, 400 if self.gen_failure else 200, {}


# test01 stuff
@dataclass
class Resource01(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    kind: str = "Resource01"
    apiVersion: str = "example.com/v1"


register_crd_class(Resource01, "resource01s", is_namespaced=True)


def test01():
    """
    Check that the class can generate empty instances that include existing sub-objects
    """
    i: Resource01 = Resource01.get_empty_instance()
    assert i.metadata is not None, "No meta object in the automatically generated instance"
    assert i.kind == 'Resource01', f'kind is {i.kind}'
    assert i.apiVersion == 'example.com/v1', f'apiVersion is {i.apiVersion}'


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
    apiVersion: str = 'example.com/v1'
    group: str = "example.com"


register_crd_class(Resource02, "resource02s", is_namespaced=True)


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


@dataclass
class IntCheck(HikaruDocumentBase, HikaruCRDDocumentMixin):
    i1: int
    i2: Optional[int]
    i4: int = field(metadata=FM(description='',
                                enum=[5, 10, 15, 20, 25, 30],
                                format="int32",
                                minimum=5,
                                exclusive_minimum=False,
                                maximum=30,
                                exclusive_maximum=False,
                                multiple_of=5,
                                pattern=r"shouldn't be in there"))
    metadata: Optional[ObjectMeta] = None
    i3: int = field(default=-1)
    i5: Optional[int] = 10
    apiVersion: str = "example.com/v1"
    kind: str = "IntCheck"


register_crd_class(IntCheck, "intchecks")


def test10():
    """
    Check processing of int fields for schema generation
    """
    js: JSONSchemaProps = get_crd_schema(IntCheck)
    d = js.to_dict()
    assert set(d['required']) == {'i1', 'i4'}
    props = d['properties']
    assert len(props.keys()) == 5
    for name in ['i1', 'i2', 'i3', 'i4', 'i5']:
        assert props[name]['type'] == 'integer'
    i4 = props['i4']
    assert 'pattern' not in i4
    assert set(i4['enum']) == {5, 10, 15, 20, 25, 30}
    assert i4['format'] == 'int32'
    assert i4['minimum'] == 5
    assert i4['exclusiveMinimum'] is False
    assert i4['maximum'] == 30
    assert i4['exclusiveMaximum'] is False
    assert i4['multipleOf'] == 5


@dataclass
class FloatCheck(HikaruDocumentBase, HikaruCRDDocumentMixin):
    f1: float
    f2: Optional[float]
    f4: float = field(metadata=FM(description='',
                                  enum=[.5, 1.0, 1.5, 2.0],
                                  format="ieee",
                                  minimum=0.0,
                                  exclusive_minimum=True,
                                  maximum=2.5,
                                  exclusive_maximum=True,
                                  multiple_of=.5,
                                  pattern=r"shouldn't be in there"))
    metadata: Optional[ObjectMeta] = None
    f3: float = field(default=-1.1)
    f5: Optional[float] = 10
    apiVersion: str = "example.com/v1"
    kind: str = "FloatCheck"


register_crd_class(FloatCheck, "floatchecks")


def test11():
    """
    Check processing of float fields for schema generation
    """
    js: JSONSchemaProps = get_crd_schema(FloatCheck)
    d = js.to_dict()
    assert set(d['required']) == {"f1", "f4"}
    props = d['properties']
    assert len(props.keys()) == 5
    for name in ['f1', 'f2', 'f3', 'f4', 'f5']:
        assert props[name]['type'] == 'number'
    f4: dict = props['f4']
    assert set(f4['enum']) == {.5, 1.0, 1.5, 2.0}
    assert 'pattern' not in f4
    assert f4['format'] == 'ieee'
    assert f4['minimum'] == 0.0
    assert f4['exclusiveMinimum'] is True
    assert f4['maximum'] == 2.5
    assert f4['exclusiveMaximum'] is True
    assert f4['multipleOf'] == .5


@dataclass
class StrCheck(HikaruDocumentBase, HikaruCRDDocumentMixin):
    s1: str
    s2: Optional[str]
    s4: str = field(metadata=FM(description="s4 in StrCheck",
                                enum=[c for c in 'abcde'],
                                pattern=r"[a-z0-9]+wibble",
                                format="ip4",
                                minimum=5))
    metadata: Optional[ObjectMeta] = None
    s3: str = field(default="wibble")
    s5: Optional[str] = 10
    apiVersion: str = "example.com/v1"
    kind: str = "StrCheck"


register_crd_class(StrCheck, "strchecks")


def test12():
    """
    Check processing of str fields for schema generation
    """
    js: JSONSchemaProps = get_crd_schema(StrCheck)
    d = js.to_dict()
    assert set(d['required']) == {'s1', 's4'}
    props = d['properties']
    assert len(props) == 5
    for name in ['s1', 's2', 's3', 's4', 's5']:
        assert props[name]['type'] == 'string'
    s4: dict = props['s4']
    assert set([c for c in 'abcde']) == set(s4['enum'])
    assert s4['description'] == "s4 in StrCheck"
    assert s4['pattern'] == r"[a-z0-9]+wibble"
    assert 'minimum' not in s4
    assert s4['format'] == 'ip4'


@dataclass
class BoolCheck(HikaruDocumentBase, HikaruCRDDocumentMixin):
    b1: bool
    b2: Optional[bool]
    b4: bool = field(metadata=FM(description="b4 in BoolCheck",
                                 enum=[True, False],
                                 format='01',
                                 minimum=5,
                                 min_items=1))
    metadata: Optional[ObjectMeta] = None
    b3: bool = field(default=True)
    b5: Optional[bool] = False
    apiVersion: str = 'example.com/v1'
    kind: str = "BoolCheck"


register_crd_class(BoolCheck, 'boolchecks')


def test13():
    """
    Check processing of bool fields for schema generation
    """
    js: JSONSchemaProps = get_crd_schema(BoolCheck)
    d: dict = js.to_dict()
    assert set(d['required']) == {'b1', 'b4'}
    props: dict = d['properties']
    assert len(props) == 5
    for name in ['b1', 'b2', 'b3', 'b4', 'b5']:
        assert props[name]['type'] == 'boolean'
    b4: dict = props['b4']
    assert 'minimum' not in b4
    assert 'enum' not in b4
    assert 'min_items' not in b4


@dataclass
class ListCheck(HikaruDocumentBase, HikaruCRDDocumentMixin):
    """
    only do ints and strs, assume we generalized based on prev tests
    """
    i1: List[int]
    s1: List[str]
    i2: Optional[List[int]]
    s2: Optional[List[str]]
    i4: List[int] = field(metadata=FM(min_items=1,
                                      max_items=5,
                                      unique_items=True,
                                      enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                                      exclusive_maximum=True,
                                      minimum=1))
    s4: List[str] = field(metadata=FM(additional_props_type=str,
                                      min_items=1,
                                      max_items=5,
                                      unique_items=True,
                                      enum=[c for c in 'abcdefghij'],
                                      pattern=r"[a-j]",
                                      exclusive_maximum=True,
                                      maximum=5))
    metadata: Optional[ObjectMeta] = None
    apiVersion: str = 'example.com/v1'
    kind: str = "ListCheck"


register_crd_class(ListCheck, 'listchecks')


def test14():
    """
    check list operations on basic types
    """
    js: JSONSchemaProps = get_crd_schema(ListCheck)
    d: dict = js.to_dict()
    assert set(d['required']) == {'i1', 's1', 'i4', 's4'}
    props: dict = d['properties']
    assert len(props) == 6
    for name in ['i1', 's1', 'i2', 's2', 'i4', 's4']:
        assert props[name]['type'] == 'array'
    for name in ['i1', 'i2', 'i4']:
        assert props[name]['items']['type'] == 'integer'
    i4: dict = props["i4"]
    assert i4['minItems'] == 1
    assert i4['maxItems'] == 5
    assert i4['uniqueItems'] is True
    assert 'exclusiveMaximum' not in i4
    assert 'minimum' not in i4
    assert set(i4['items']['enum']) == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    s4: dict = props['s4']
    assert s4['items']['pattern'] == r"[a-j]"
    assert s4['minItems'] == 1
    assert s4['maxItems'] == 5
    assert s4['uniqueItems'] is True
    assert set(s4['items']['enum']) == set([c for c in 'abcdefghij'])
    assert 'exclusiveMaximum' not in s4
    assert 'maximum' not in s4


@dataclass
class SimpleInnerSpec(HikaruBase):
    f1: int
    f2: str
    f3: float
    f4: List[str] = field(metadata=FM(description="f4 in SimpleInnerSpec",
                                      min_items=1,
                                      max_items=5))


@dataclass
class SimpleInner(HikaruDocumentBase, HikaruCRDDocumentMixin):
    spec: SimpleInnerSpec
    option: Optional[str]
    metadata: Optional[ObjectMeta] = None
    kind: str = "SimpleInner"
    apiVersion: str = "example.com/v1"


register_crd_class(SimpleInner, "simpleinners")


@dataclass
class SimpleMiddleSpec(HikaruBase):
    wibble: str
    spec: Optional[SimpleInnerSpec] = None


@dataclass
class SimpleMiddle(HikaruDocumentBase, HikaruCRDDocumentMixin):
    spec: SimpleMiddleSpec
    metadata: Optional[ObjectMeta] = None
    kind: str = "SimpleMiddle"
    apiVersion: str = 'example.com/v1'


register_crd_class(SimpleMiddle, "simplemiddles")


@dataclass
class SimpleOuterSpec(HikaruBase):
    spec: SimpleMiddleSpec
    switch: str


@dataclass
class SimpleOuter(HikaruDocumentBase, HikaruCRDDocumentMixin):
    spec: Optional[SimpleOuterSpec] = field(metadata=FM(description="spec in SimpleOuter"))
    metadata: Optional[ObjectMeta] = None
    kind: str = "SimpleOuter"
    apiVersion: str = "example.com/v1"


register_crd_class(SimpleOuter, "simpleouters")


def test15():
    """
    Check the simplest of nested classes
    """
    js: JSONSchemaProps = get_crd_schema(SimpleInner)
    d: dict = js.to_dict()
    assert set(d['required']) == {'spec'}
    oprops: dict = d['properties']
    assert oprops['spec']['type'] == 'object'
    inner_obj: dict = oprops['spec']
    assert set(inner_obj['required']) == {'f1', 'f2', 'f3', 'f4'}
    iprops: dict = inner_obj['properties']
    assert len(iprops) == 4
    assert iprops['f4']['items']['type'] == "string"
    assert iprops['f4']['minItems'] == 1
    assert iprops['f4']['maxItems'] == 5


def test16():
    """
    Check more deeply nested classes
    """
    js: JSONSchemaProps = get_crd_schema(SimpleMiddle)
    d: dict = js.to_dict()
    assert d['required'] == ['spec']
    mprops: dict = d['properties']
    assert len(mprops) == 1
    mobj: dict = mprops["spec"]
    assert mobj['type'] == 'object'
    assert len(mobj['properties']) == 2
    assert mobj['properties']['wibble']['type'] == 'string'
    assert mobj['properties']['spec']['type'] == 'object'
    assert len(mobj['properties']['spec']['properties']) == 4


@dataclass
class ListInnerSpec(HikaruBase):
    f1: int
    f2: str


@dataclass
class ListOuter(HikaruDocumentBase, HikaruCRDDocumentMixin):
    l1: List[ListInnerSpec] = field(metadata=FM(description="l1 in ListOuter",
                                                min_items=1,
                                                max_items=10,
                                                unique_items=True))
    metadata: Optional[ObjectMeta] = None
    l2: Optional[List[ListInnerSpec]] = None
    kind: str = "ListOuter"
    apiVersion: str = "example.com/v1"


register_crd_class(ListOuter, 'listouters')


def test17():
    """
    Now do lists of nested objects
    """
    js: JSONSchemaProps = get_crd_schema(ListOuter)
    d: dict = js.to_dict()
    assert d['required'] == ['l1']
    oprops: dict = d['properties']
    assert len(oprops) == 2
    l1: dict = oprops['l1']
    assert l1['type'] == 'array'
    assert l1['items']['type'] == 'object'
    assert len(l1['items']['properties']) == 2
    assert l1['maxItems'] == 10
    assert l1['minItems'] == 1
    assert l1['uniqueItems'] is True
    assert l1['items']['properties']['f1']['type'] == 'integer'
    assert l1['items']['properties']['f2']['type'] == 'string'
    l2: dict = oprops['l2']
    assert 'minItems' not in l2
    assert 'maxItems' not in l2
    assert 'uniqueItems' not in l2


def test18():
    """
    Pass in a bad choice for JSONSchemaProps
    """
    try:
        js: JSONSchemaProps = get_crd_schema(IntCheck, jsp_class=IntCheck)
    except TypeError as e:
        assert "The jsp_class parameter" in str(e)


def test19():
    """
    Test rollback context manager
    """
    o: Resource01 = Resource01(metadata=ObjectMeta(name='test19',
                                                   deletionGracePeriodSeconds=10))
    odup: Resource01 = o.dup()

    try:
        with rollback_cm(o):
            o.metadata.deletionGracePeriodSeconds = 20
            raise CRDTestExp('test19')
    except CRDTestExp:
        pass
    assert odup.metadata.deletionGracePeriodSeconds == o.metadata.deletionGracePeriodSeconds


def test19a():
    """
    Test rollback CM; rollback due to update problem
    """
    o: Resource01 = Resource01(metadata=ObjectMeta(name='test19',
                                                   deletionGracePeriodSeconds=10))
    o.client = MockApiClient(raise_exp=True)
    odup: Resource01 = o.dup()

    try:
        with rollback_cm(o):
            o.metadata.deletionGracePeriodSeconds = 20
    except CRDTestExp:
        pass
    assert odup.metadata.deletionGracePeriodSeconds == o.metadata.deletionGracePeriodSeconds


def test20():
    """
    Test context manager failure
    """
    o: Resource01 = Resource01(metadata=ObjectMeta(name='test20',
                                                   deletionGracePeriodSeconds=10))
    odup: Resource01 = o.dup()

    try:
        with o:
            o.metadata.deletionGracePeriodSeconds = 20
            raise CRDTestExp('test20')
    except CRDTestExp:
        pass
    assert o.metadata.deletionGracePeriodSeconds != odup.metadata.deletionGracePeriodSeconds


def test21():
    """
    Test context manager success
    """
    o: Resource01 = Resource01(metadata=ObjectMeta(name="test21",
                                                   deletionGracePeriodSeconds=10))
    odup: Resource01 = o.dup()
    o.client = MockApiClient()

    with o:
        o.metadata.deletionGracePeriodSeconds = 20

    assert o.metadata.deletionGracePeriodSeconds != odup.metadata.deletionGracePeriodSeconds


def test22():
    """
    Try to register a class that's not a dataclass
    """
    class NotADataClass(object):
        f1: int
        apiVersion: str = "example.com/v1"
        kind: str = "NotADataClass"

    try:
        _ = get_crd_schema(NotADataClass)
        raise CRDTestExp("Should have raised a TypeError")
    except TypeError:
        pass


def test23():
    """
    Try to register a class that contains a class that isn't a dataclass
    """
    class BadInner(object):
        f1: int

    @dataclass
    class BadOuter(HikaruDocumentBase, HikaruCRDDocumentMixin):
        ba: BadInner
        apiVersion: str = "example.com/v1"
        kind: str = "BadOuter"

    try:
        _ = get_crd_schema(BadOuter)
        raise CRDTestExp("should have raised a TypeError")
    except TypeError:
        pass


def test24():
    """
    Ensure that we don't require a field that is Optional but with no default
    """
    @dataclass
    class NoDefault(HikaruDocumentBase, HikaruCRDDocumentMixin):
        f1: Optional[int] = field(metadata=FM(description="f1 in NoDefault"))

    _ = get_crd_schema(NoDefault)  # this just covers a line in the code


def test25():
    """
    Create a field that has a pathological Union to cover a test
    """
    @dataclass
    class BadUnion(HikaruDocumentBase, HikaruCRDDocumentMixin):
        f1: Union[str, int]

    try:
        _ = get_crd_schema(BadUnion)
        raise CRDTestExp("should have raised a NotImplemented")
    except NotImplementedError as e:
        assert "Multiple types" in str(e)


def test26():
    """
    should raise if a List type isn't a dataclass
    """
    class ListType(object):
        f1: int

    @dataclass
    class BadListType(HikaruDocumentBase, HikaruCRDDocumentMixin):
        l1: List[ListType]

    try:
        _ = get_crd_schema(BadListType)
        raise CRDTestExp("Should have raised a TypeError")
    except TypeError as e:
        assert "Don't know how to" in str(e)


def test27():
    """
    Try generating a dict/object output
    """
    @dataclass
    class WithDict(HikaruDocumentBase, HikaruCRDDocumentMixin):
        d: Dict[str, str]
        apiVersion: str = "example.com/v1"
        kind: str = "WithDict"

    _ = get_crd_schema(WithDict)


@dataclass
class ExampleResource(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    f1: int
    apiVersion: str = "example.com/v1"
    kind: str = "ExampleResource"


register_crd_class(ExampleResource, "exampleresources")


def test28():
    """
    Run through the CRUD methods
    """
    r: ExampleResource = ExampleResource(metadata=ObjectMeta(name="test28"),
                                         f1=22)
    r.client = MockApiClient()
    res: ExampleResource = r.create()
    assert res
    res.client = r.client
    read_res: ExampleResource = res.read()
    assert read_res
    read_res.client = r.client
    read_res.f1 = 44
    read_res.update()
    _: ExampleResource = read_res.delete()


@dataclass
class NoRegister(HikaruDocumentBase, HikaruCRDDocumentMixin):
    f1: int = 0
    apiVersion: str = "example.com/v1"
    kind: str = "NoRegister"


def test29():
    """
    Catch an error if trying to create without a registration
    """
    o: NoRegister = NoRegister()
    o.client = MockApiClient()
    try:
        o.create()
        raise CRDTestExp("should have raised TypeError")
    except TypeError as e:
        assert "not been registered" in str(e)


@dataclass
class BadVersion(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: Optional[ObjectMeta] = None
    i1: int = 5
    apiVersion: str = 'v1'
    kind: str = "BadVersion"



def test30():
    """
    Catch an error if apiVersion is formed wrong
    """
    register_crd_class(BadVersion, "badversions")
    bv: BadVersion = BadVersion()
    try:
        bv.create()
        raise CRDTestExp("should have raised a TypeError")
    except TypeError as e:
        assert "exactly two parts" in str(e)


@dataclass
class NoNamespace(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: Optional[ObjectMeta] = None
    i1: int = 5
    apiVersion: str = "example.com/v1"
    kind: str = "NoNamespace"


register_crd_class(NoNamespace, "nonamespaces", is_namespaced=False)


def test31():
    """
    Run through the no namespace code
    """
    o: NoNamespace = NoNamespace()
    o.client = MockApiClient()
    res: NoNamespace = o.create()
    assert res


def test32():
    """
    Do an async create call
    """
    o: NoNamespace = NoNamespace()
    o.client = MockApiClient()
    r = o.create(async_req=True)
    assert isinstance(r, Response)


@dataclass
class NNWithMetadata(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta
    f1: float = 2.5
    apiVersion: str = "example.com/v1"
    kind: str = "NNWithMetadata"


register_crd_class(NNWithMetadata, "withmetadatas", is_namespaced=False)


def test33():
    """
    Do a read call on an unnamespaced resource
    """
    o: NNWithMetadata = NNWithMetadata(metadata=ObjectMeta(name="test33"))
    o.client = MockApiClient()
    r: NNWithMetadata = o.read()
    assert r


def test33a():
    """
    Do an async delete
    """
    o: NNWithMetadata = NNWithMetadata(metadata=ObjectMeta(name="test33"))
    o.client = MockApiClient()
    r = o.delete(async_req=True)
    assert r


def test34():
    """
    Async read on an un-namespaced resource
    """
    o: NNWithMetadata = NNWithMetadata(metadata=ObjectMeta(name="test33"))
    o.client = MockApiClient()
    r: Response = o.read(async_req=True)
    assert isinstance(r, Response)


def test35():
    """
    Async update on an un-namespaced resource
    """
    o: NNWithMetadata = NNWithMetadata(metadata=ObjectMeta(name="test33"))
    o.client = MockApiClient()
    r: Response = o.update(async_req=True)
    assert isinstance(r, Response)


@dataclass
class Oopsie(HikaruBase, HikaruCRDDocumentMixin):
    i1: int = 99
    apiVersion: str = "example.com/v1"
    kind: str = "Oopsie"


def test36():
    """
    Check we raise when trying to register something not a HikaruDocumentBase subclass
    """
    try:
        register_crd_class(Oopsie, 'oopsies')
        raise CRDTestExp("should have raised a type error")
    except TypeError as e:
        assert "A CRD registered" in str(e)


@dataclass
class Missing(HikaruDocumentBase, HikaruCRDDocumentMixin):
    f1: float = 2.5


def test37():
    """
    Register should raise for missing apiVersion/kind/metadata
    """
    try:
        register_crd_class(Missing, "missings")
        raise CRDTestExp("should have raised a type error")
    except TypeError as e:
        assert "must have apiVersion, kind, and metadata attributes" in str(e)


if __name__ == "__main__":
    beginning()
    the_tests = {k: v for k, v in globals().items()
                 if k.startswith('test') and callable(v)}
    try:
        for k, v in the_tests.items():
            try:
                v()
            except Exception as e:
                print(f'{k} failed with {str(e)}, {e.__class__}')
                raise
    finally:
        ending()
