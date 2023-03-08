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

from dataclasses import dataclass, is_dataclass
from functools import partial
from typing import Optional, Dict
from .meta import HikaruDocumentBase
from hikaru.version_kind import register_version_kind_class


class CRDMixin(object):
    @classmethod
    def get_crd_schema(cls):
        # this may need to get templatized to allow for different
        # schema classes from different releases
        pass


@dataclass
class HikaruCRDDocumentBase(HikaruDocumentBase, CRDMixin):
    pass


@dataclass
class HikaruCRDListDocumentBase(HikaruDocumentBase, CRDMixin):
    pass


class _RegisterCRD(object):
    def __init__(self, is_namespaced: bool = True):
        self.is_namespaced = is_namespaced


_crd_registration_details: Dict[type(HikaruCRDListDocumentBase), _RegisterCRD] = {}


def register_crd(crd_cls, is_namespaced: bool = True):
    if not issubclass(crd_cls, HikaruCRDDocumentBase):
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

    def __init__(self, verb, url: str):
        self.verb = verb
        self.url = url
        self.prop: Optional[APICallProp] = None

    def __call__(self, m):
        self.prop = APICallProp(self, m)
        return self.prop


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
