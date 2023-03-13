#
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

from inspect import isclass, signature, Signature, Parameter
from dataclasses import dataclass, is_dataclass, Field, fields, InitVar
from functools import partial
from typing import Optional, Dict, Union, List, get_type_hints
from .meta import HikaruDocumentBase, HikaruBase
from .utils import get_origin, get_args, HikaruCallableTyper, ParamSpec, get_hct, FieldMetadata as fm
from hikaru.version_kind import register_version_kind_class

ignorable = {'apiVersion', 'kind', 'metadata', 'group'}
type_map = {str: "string", int: "integer", float: "float", bool: "boolean"}


def get_crd_schema(cls, jsp_class: type):
    """
    Return a JSONSchemaProps instance suitable for describing this class in a CustomResourceDefinition msg

    Only works with a dataclass!

    Limitations:

    - Cannot handle recursively defined classes (yet), neither direct nor indirect

    """
    if jsp_class.__name__ != "JSONSchemaProps":
        raise TypeError("The jsp_class parameter must be one of the JSONSchemaProps classes for "
                        "one of the supported releases under hikaru.model")
    schema = _process_cls(cls)
    jsp = jsp_class(**schema)
    return jsp


def _process_cls(cls) -> dict:
    if not is_dataclass(cls):
        raise TypeError(f"The class {cls.__name__} is not a dataclass; Hikaru can't generate "
                        f"a schema for it.")
    props = {}
    jsp_args = {"type": "object", "properties": props}
    required = []
    hct: HikaruCallableTyper = get_hct(cls)
    p: ParamSpec
    for p in hct.values():
        if p.name in ignorable:
            continue
        if isinstance(p.hint_type, InitVar):
            continue
        if p.default is Parameter.empty:
            required.append(p.name)
        prop = props[p.name] = {}
        metadata = p.metadata
        description = metadata.get(fm.DESCRIPTION_KEY)
        if description is not None:
            prop['description'] = description
        enums = metadata.get(fm.ENUM_KEY)
        if enums is not None:
            prop['enum'] = enums
        if isclass(p.annotation) and issubclass(p.annotation, HikaruBase):
            if not is_dataclass(p.annotation):
                raise TypeError(f"The class {p.annotation.__name__} is not a dataclass; Hikaru can't generate "
                                f"a schema for it.")
            prop.update(_process_cls(p.annotation))
        elif p.annotation in type_map:
            prop.update({"type": type_map[p.annotation]})
        else:
            initial_type = p.annotation
            origin = get_origin(initial_type)
            if origin is Union:
                type_args = get_args(p.annotation)
                initial_type = type_args[0]
                if initial_type in type_map:
                    prop["type"] = type_map[initial_type]
                    continue
            origin = get_origin(initial_type)
            if origin in (list, List):
                prop["type"] = "array"
                list_of_type = get_args(initial_type)[0]
                if list_of_type in type_map:
                    prop["items"] = {"type": type_map[list_of_type]}
                elif isclass(list_of_type) and issubclass(list_of_type, HikaruBase):
                    if not is_dataclass(list_of_type):
                        raise TypeError(f"The list item type of attribute {p.name} is a subclass "
                                        f"of HikaruBase but is not a dataclass")
                    prop["items"] = _process_cls(list_of_type)
                else:
                    raise TypeError(f"Don't know how to process {p.name}'s type {p.annotation}; "
                                    f"origin: {get_origin(p.annotation)}, args: {get_args(p.annotation)}")
            elif isclass(initial_type) and issubclass(initial_type, HikaruBase):
                if not is_dataclass(initial_type):
                    raise TypeError(f"The type of {p.name} is a subclass of HikaruBase "
                                    f"but is not a dataclass")
                prop.update(_process_cls(initial_type))
            elif origin in (dict, Dict) or initial_type is object:
                prop["type"] = "object"
                # @TODO we currently don't have enough data to exactly how to output
                # this; we've lost some info if it came from K8s swagger. While this is
                # certainly an object, it's rendering can either involve key/value
                # pairs or a single string in a particular format. This is something
                # we can eventually clarify, but for now we'll just treat it as a k/v
                # pairs collection
                prop["additionalProperties"] = {"type": "string"}
            else:
                raise TypeError(f"Don't know how to process type {p.name}'s {p.annotation}; "
                                f"origin: {get_origin(p.annotation)}, args: {get_args(p.annotation)}")
    if required:
        jsp_args["required"] = required

    return jsp_args


class _RegisterCRD(object):
    def __init__(self, is_namespaced: bool = True):
        self.is_namespaced = is_namespaced


_crd_registration_details: Dict[type(HikaruDocumentBase), _RegisterCRD] = {}


def register_crd_schema(crd_cls, is_namespaced: bool = True):
    if not issubclass(crd_cls, HikaruDocumentBase):
        raise TypeError("The decorated class must be a subclass of HikaruCRDDocumentBase")
    if not hasattr(crd_cls, 'apiVersion') or not hasattr(crd_cls, 'kind'):
        raise TypeError("The decorated class must have both an apiVersion and kind attribute")
    if not is_dataclass(crd_cls):
        raise TypeError(f"The class {crd_cls.__name__} must be a dataclass")
    register_version_kind_class(crd_cls, crd_cls.apiVersion, crd_cls.kind)
    crdr = _RegisterCRD(is_namespaced=is_namespaced)
    _crd_registration_details[crd_cls] = crdr
    return crd_cls


class APICallProp(object):
    def __init__(self, o: object, m):
        self.o = o
        self.m = m

    def __call__(self, *args, **kwargs):
        # this is probably where all the work to call the K8s API will happen
        pass


class APICall(object):
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    OP = 'op'

    def __init__(self, method, url: str):
        self.method = method
        self.url = url
        self.prop: Optional[APICallProp] = None

    def __call__(self, m):
        self.prop = APICallProp(self, m)
        return self.prop


_method_map = {APICall.CREATE: 'put',
               APICall.READ: 'get',
               APICall.UPDATE: 'post',
               APICall.DELETE: 'delete'}


def crd_create(f):
    return partial(APICall, APICall.CREATE)


def crd_read(f):
    return partial(APICall, APICall.READ)


def crd_update(f):
    return partial(APICall, APICall.UPDATE)


def crd_delete(f):
    return partial(APICall, APICall.DELETE)


def op_operation(f):
    return partial(APICall, APICall.OP)
