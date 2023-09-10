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
This program generates all the 'model' package & api version modules

This program works off a specified Kubernetes swagger file and from there
builds out the model sub-package of hikaru. It first removes all existing
content of this package and then re-creates it from scratch. If the swagger
file hasn't changed, then these generated modules will be identical, otherwise
they will contain the new contents from the swagger file.

Usage is:

    python build.py <path to swagger file>

The assumption is to create the 'build' package in the cwd.

Just some notes to remember how this all works:

For the collection types, you must parameterize the
types from typing (List, Dict, etc).

If you want an optional type, you can use typing.Optional,
which turns into Union[T, NoneType].

You can use dataclasses.field(default_factory=list) to indicate
where optional args should be defaulted to new empty lists.

You can acquire the fields of class X with
dataclasses.fields(X). The type annotation for the field is
stored in the 'type' attribute.

You now want to understand Union and List types. There are two
different ways to do this; the change comes at Py3.8. This
are both performed on the type object found in the above
mentioned attribute:

Operation           Pre-3.8         3.8 and later
========================================================
get origin          __origin__      typing.get_origin()
get args            __args__        typing.get_args()

inspect.signature() can give the argument signature for a
method; can find how many required positional args there are.
"""
from itertools import chain, permutations
from functools import lru_cache
import importlib
from pathlib import Path
import keyword
import sys
from typing import List, Dict, Optional, Union, Tuple, Any, Set
import json
from collections import defaultdict
import re
from warnings import warn
from black import NothingChanged, format_str, Mode
from hikaru.naming import (process_swagger_name, full_swagger_name,
                           dprefix, camel_to_pep8)
from hikaru.meta import (HikaruBase, HikaruDocumentBase, KubernetesException,
                         WatcherDescriptor)


class VersionStr(str):
    """
    Special string for holding version values;
    """
    major_stage_minor = re.compile("v(?P<major>[0-9]+)(?P<stage>[a-z]*)(?P<minor>[0-9]*)")

    @lru_cache
    def get_msm(self) -> list:
        parts = []
        m = VersionStr.major_stage_minor.match(self)
        if m is not None:
            parts.append(int(m.group('major')))
            stage = m.group('stage')
            if stage:
                parts.append(stage)
                minor = m.group('minor')
                if minor:
                    parts.append(int(minor))
        return parts

    def is_ga(self, msm: Optional[List] = None):
        if msm is None:
            msm = self.get_msm()
        return len(msm) == 1

    @lru_cache
    def __lt__(self, other):
        sparts = self.get_msm()
        oparts = other.get_msm()

        # OK, first check if either/both are GA; GA is never less than non-GA,
        # and if both are GA then just compare the release numbers
        s_is_ga = len(sparts) == 1
        o_is_ga = len(oparts) == 1
        if s_is_ga ^ o_is_ga:
            # only one is GA; is self is then it is not less than since it is GA
            return False if s_is_ga else True
        if s_is_ga and o_is_ga:
            return sparts[0] < oparts[0]

        # if we get here then neither is GA; then compare stages (which must be there)
        if sparts[1] != oparts[1]:
            return sparts[1] < oparts[1]
        # next compare releases
        if sparts[0] != oparts[0]:
            return sparts[0] < oparts[0]

        # OK, the stages are the same, so check the minor version
        s_has_minor = len(sparts) == 3
        o_has_minor = len(oparts) == 3
        if s_has_minor and o_has_minor:
            return sparts[2] < oparts[2]
        if s_has_minor ^ o_has_minor:
            return False if s_has_minor else True
        return False

    @lru_cache
    def __gt__(self, other):
        return self != other and not (self < other)

    @lru_cache
    def __le__(self, other):
        return self == other or self < other

    @lru_cache
    def __ge__(self, other):
        return self == other or self > other


# version, opid
written_methods: Set[Tuple[VersionStr, str]] = set()


NoneType = type(None)


types_map = {"boolean": "bool",
             "integer": "int",
             "string": "str",
             "float": "float",
             "number": "float"}

model_package = "hikaru/model"

unversioned_module_name = "unversioned"

_copyright_string = \
"""#
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
# SOFTWARE."""

_module_docstring = f'''{_copyright_string}
"""
DO NOT EDIT THIS FILE!

This module is automatically generated using the Hikaru build program that turns
a Kubernetes swagger spec into the code for the hikaru.model package.
"""
'''


_package_init_code = \
"""
try:
    from .v1 import *
except ImportError:  # pragma: no cover
    pass"""


_deprecation_warning = \
"""
warnings.filterwarnings('default', category=PendingDeprecationWarning)
warnings.warn("Consider migrating from release %s of K8s; this is the last "
              "Hikaru release that will support it",
              category=PendingDeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)"""


_module_footer = '''globs = dict(globals())
__all__ = [c.__name__ for c in globs.values()
           if type(c) == type]
del globs'''


_package_version_init_code = \
"""
try:
    from .{} import *
except ImportError:  # pragma: no cover
    pass"""


class PropertyDescriptor(object):

    def __init__(self, containing_class: 'ClassDescriptor', name: str, d: dict):
        """
        capture the information
        :param containing_class:
        :param d:
        """
        name = name.replace('-', '_')
        if keyword.iskeyword(name):
            python_name = f'{name}_'
        elif name.startswith("$"):
            python_name = f'{dprefix}{name.strip("$")}'
        else:
            python_name = name
        self.name = python_name
        self.default_value = None
        self.containing_class = containing_class
        self.description = d.get('description', "")
        # all possible attributes that could be populated
        self.container_type = self.item_type = self.prop_type = None
        ctype = d.get("type")
        if ctype == "array":
            self.container_type = list
            items = d["items"]
            self.item_type = items.get('type')
            if self.item_type is None or self.item_type == "object":
                # then it is a list of objects; possibly of one of the defs
                ref = items.get("$ref")
                if ref:
                    item_ref = find_cd_by_property_ref(ref)
                else:
                    itype = items.get("type")
                    if itype:
                        if itype == "object":
                            item_ref = "object"
                        else:
                            item_ref = itype
                    else:
                        raise RuntimeError(f"Don't know how to process type of {name} "
                                           f"in {self.containing_class.hikaru_name}")
                self.item_type = item_ref
            elif self.item_type in types_map:
                self.item_type = types_map[self.item_type]
            else:
                raise TypeError(f"Unknown type: {self.item_type} in property {self.name}")
        elif ctype == "object":
            # This can be a couple of things, depending on the release
            # of the spec. Sometimes it's just used to allow any content,
            # and sometimes it's for a untyped key/value object
            # We'll look for the presence of 'additionalProperties' and if
            # found, we'll treat it as a dict, otherwise an object
            if 'additionalProperties' in d:
                self.container_type = dict
            else:
                self.container_type = object
        else:
            self.container_type = None

        if self.container_type is None:
            if ctype in types_map:
                self.prop_type = types_map[ctype]
            else:
                ref_class = find_cd_by_property_ref(d["$ref"])
                self.prop_type = ref_class

    @staticmethod
    def as_required(anno: str, as_required: bool) -> str:
        return anno if as_required else f"Optional[{anno}]"

    def depends_on(self) -> Optional['ClassDescriptor']:
        result = None
        if isinstance(self.item_type, ClassDescriptor):
            result = self.item_type
        elif isinstance(self.prop_type, ClassDescriptor):
            result = self.prop_type
        return result

    def change_dep(self, new_dep):
        if isinstance(self.item_type, ClassDescriptor):
            self.item_type = new_dep
        elif isinstance(self.prop_type, ClassDescriptor):
            self.prop_type = new_dep

    def as_python_typeanno(self, as_required: bool) -> str:
        parts = ["    ", self.name, ": "]
        if self.container_type is None:
            # then a straight-up type, either scalar or another object
            if isinstance(self.prop_type, str):
                parts.append(self.as_required(self.prop_type, as_required))
            elif isinstance(self.prop_type, ClassDescriptor):
                parts.append(self.as_required(f"'{self.prop_type.hikaru_name}'",
                                              as_required))
        elif self.container_type is list:
            if isinstance(self.item_type, ClassDescriptor):
                parts.append(self.as_required(f"List['{self.item_type.hikaru_name}']",
                                              as_required))
            else:
                parts.append(self.as_required(f"List[{self.item_type}]",
                                              as_required))
        elif self.container_type is dict:
            parts.append(self.as_required("Dict[str, str]", as_required))
        elif self.container_type is object:
            parts.append(self.as_required("object", as_required))
        else:
            raise TypeError(f"Unknown attribute {self.name} in "
                            f"{self.containing_class.hikaru_name}, "
                            f"prop_type:{self.prop_type}, "
                            f"container:{self.container_type}")
        # now check if we should add a field default
        if not as_required:
            # then we need to add a default value so we don't have to
            # supply this argument when creating it programmatically
            if self.container_type is not None:
                # then we need a field
                factory = "list" if self.container_type is list else "dict"
                parts.append(f" = field(default_factory={factory})")
            else:
                # just default it to None
                parts.append(f" = {self.default_value}")
        return "".join(parts)


def process_gvk_dict(gvk: dict) -> Tuple[str, VersionStr, str]:
    version = VersionStr(gvk['version'])
    group = gvk['group']
    kind = gvk['kind']
    if not group:
        group = ''
    else:
        group = group.split('.')[0]
    return group, version, kind


class OpParameter(object):
    def __init__(self, name: str, ptype: Any, description: str, required: bool):
        self.name = name
        self.ptype = ptype
        self.description = description
        self.required = required
        self.is_bodyany: bool = True if name == 'body' and ptype == 'Any' else False

    def docstring(self, prefix="", hanging_indent="      ", linelen=70):
        name = camel_to_pep8(self.name)
        name = f"{name}_" if keyword.iskeyword(name) else name
        line = f':param {name}: {self.description}'
        final_lines = ClassDescriptor.split_line(line, prefix=prefix,
                                                 hanging_indent=hanging_indent,
                                                 linelen=linelen)
        return "\n".join(final_lines)

    def as_python(self) -> str:
        if type(self.ptype) == type:
            ptype = self.ptype.__name__
        elif isinstance(self.ptype, ClassDescriptor):
            ptype = f"'{self.ptype.hikaru_name}'"
        else:
            ptype = self.ptype
        ptype = (ptype
                 if self.required
                 else f"Optional[{ptype}] = None")
        name = camel_to_pep8(self.name)
        name = f"{name}_" if keyword.iskeyword(name) else name
        return f"{name}: {ptype}"


class OpResponse(object):
    def __init__(self, code: int, description: str, ref: Optional[str] = None):
        self.code = code
        self.description = description
        self.ref = ref

    def is_object(self) -> bool:
        return isinstance(self.ref, ClassDescriptor)


def get_path_version(path: str) -> VersionStr:
    version = None
    parts = path.split('/')
    for part in parts:
        if part.startswith('v1') or part.startswith('v2'):
            version = VersionStr(part)
            break
    return version


# the following strings are used to format an Operation's method body
_method_body_template = \
"""if client is not None:
    client_to_use = client
else:
    # noinspection PyDataclass
    client_to_use = self.client
inst = {k8s_class_name}(api_client=client_to_use)
the_method = getattr(inst, '{k8s_method_name}_with_http_info')
if the_method is None:  # pragma: no cover
    raise RuntimeError("Unable to locate method "
                       "{k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
body = get_clean_dict(self)
all_args['{body_key}'] = body
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
resp: Response['{returned_type}'] = Response['{returned_type}'](result,
                                                                codes_returning_objects)
return resp
"""

_static_method_body_template = \
"""client_to_use = client
inst = {k8s_class_name}(api_client=client_to_use)
the_method = getattr(inst, '{k8s_method_name}_with_http_info')
if the_method is None:  # pragma: no cover
    raise RuntimeError("Unable to locate method "
                       "{k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
if body is not None:
    body = get_clean_dict(body) if isinstance(body, HikaruBase) else body
all_args['{body_key}'] = body
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
resp: Response['{returned_type}'] = Response['{returned_type}'](result,
                                                                codes_returning_objects)
return resp
"""

_static_method_nobody_template = \
"""client_to_use = client
inst = {k8s_class_name}(api_client=client_to_use)
the_method = getattr(inst, '{k8s_method_name}_with_http_info')
if the_method is None:  # pragma: no cover
    raise RuntimeError("Unable to locate method "
                       "{k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
resp: Response['{returned_type}'] = Response['{returned_type}'](result,
                                                                codes_returning_objects)
return resp
"""


class Operation(object):
    """
    A single operation from paths; associated with a verb such as 'get' or 'post'

    The same path may have multiple operations with different verbs, and hence
    may also involve different input params/outputs
    """

    regexp = re.compile(r'{(?P<pname>[a-z]+)}')
    # the crud_registry allows derived classes to register with Operation
    # as to their support for specific crud verbs (create, read, etc).
    # keys are one of the verbs, all lower case, and values are a class object
    # that is derived from SyntheticOperation
    crud_registry: Dict[str, type] = {}

    def __init__(self, verb: str, op_path: str, op_id: str, description: str,
                 gvk_dict: dict):
        self.owning_cd: Optional['ClassDescriptor'] = None
        self.should_render = True
        self.verb = verb
        self.op_path = op_path
        self.version: VersionStr = get_path_version(self.op_path)
        self.gvk_version: VersionStr = VersionStr(gvk_dict.get('version'))
        self.group = gvk_dict.get('group', 'custom_objects')
        self.kind = gvk_dict.get('kind')
        self.op_id = op_id
        self.description = description
        self.is_staticmethod = False
        # flag if this can be 'watched'
        self.supports_watch = False
        # support for 1.16; some 'body' inputs don't have a type beside
        # 'object' which we treat as Any,
        # but in every case it appears they should be 'self' and treated
        # as the type of the receiving object. this captures those as
        # they come in, and if we need to update the type to a ClassDescriptor
        # then we can find the correct OpParameter quickly
        self.bodyany: Optional[OpParameter] = None
        self.parameters: List[OpParameter] = list()
        # self_param is a special parameter, usually named 'body',
        # that is passed as an argument to another method and which
        # refers to 'self' of the owning object
        self.self_param: Optional[OpParameter] = None
        self.returns: Dict[int, OpResponse] = {}
        self.k8s_access_tuple = None
        # OK, now we need to check for implicit params in the path
        # itself; we'll record these as OpParam objects
        search_str = self.op_path
        match = self.regexp.search(search_str)
        url_params = []
        while match is not None:
            url_params.append(match.group('pname'))
            search_str = search_str[match.end():]
            match = self.regexp.search(search_str)
        url_params.sort()
        for pname in url_params:
            self.add_parameter(pname, "str", f"{pname} for the resource", required=True)
        # determine the method name for this operation
        version: VersionStr = get_path_version(self.op_path)
        if version is None:
            version = VersionStr("")
        else:
            version = version.replace('v', 'V')
        self.meth_name = self.op_id.replace(version, '') if self.op_id else None

    def set_owning_class_descriptor(self, cd: 'ClassDescriptor'):
        self.owning_cd = cd

    def depends_on(self) -> list:
        deps = [p.ptype for p in self.parameters if isinstance(p.ptype, ClassDescriptor)]
        if self.self_param and isinstance(self.self_param.ptype, ClassDescriptor):
            deps.append(self.self_param.ptype)
        return deps

    def add_parameter(self, name: str, ptype: Any, description: str,
                      required: bool = False) -> 'OpParameter':
        if name == 'watch':
            self.supports_watch = True
        ptype = types_map.get(ptype, ptype)
        new_param = OpParameter(name, ptype, description, required)
        if self.self_param is None and (isinstance(ptype, ClassDescriptor) or
                                        ptype == 'Any'):
            self.self_param = new_param
        elif not any([name == p.name for p in self.parameters]):
            self.parameters.append(new_param)
        if new_param.is_bodyany:
            self.bodyany = new_param
        return new_param

    def set_k8s_access(self, t):
        """
        Stores the names that tie this operation to the k8s client method
        :param t: a 4-tuple of strings consisting of:
            pkg, mod, cls, meth
            pkg: the package name to use in importlib.import_module
            mod: the module name to use in the above function
            cls: the class name to get out of the module
            meth: the method name to access in the class for the operation
        """
        self.k8s_access_tuple = t

    def add_return(self, code: str, ptype: Optional[str], description: str):
        ptype = types_map.get(ptype, ptype)
        code = int(code)
        self.returns[code] = OpResponse(code, description, ref=ptype)

    def response_codes_returning_object(self) -> List[int]:
        return [r.code for r in self.returns.values()
                if r.is_object()]

    def _get_method_body(self, k8s_class_name: str, k8s_method_name: str,
                         arg_assignment_lines: List[str],
                         codes_returning_objects: str,
                         body_key: str = 'body',
                         use_body: bool = True) -> List[str]:
        if self.is_staticmethod:
            if use_body:
                rez = _static_method_body_template.format(k8s_class_name=k8s_class_name,
                                                          k8s_method_name=k8s_method_name,
                                                          body_key=body_key,
                                                          arg_assignment_lines="\n".join(
                                                             arg_assignment_lines),
                                                          codes_returning_objects=
                                                          codes_returning_objects,
                                                          returned_type=
                                                          self.owning_cd.hikaru_name)
            else:
                rez = _static_method_nobody_template.format(k8s_class_name=
                                                            k8s_class_name,
                                                            k8s_method_name=
                                                            k8s_method_name,
                                                            arg_assignment_lines=
                                                            "\n".join(
                                                               arg_assignment_lines),
                                                            codes_returning_objects=
                                                            codes_returning_objects,
                                                            returned_type=
                                                            self.owning_cd.hikaru_name)
        else:
            rez = _method_body_template.format(k8s_class_name=k8s_class_name,
                                               k8s_method_name=k8s_method_name,
                                               body_key=body_key,
                                               arg_assignment_lines="\n".join(
                                                    arg_assignment_lines),
                                               codes_returning_objects=
                                               codes_returning_objects,
                                               returned_type=self.owning_cd.hikaru_name)
        return rez.split("\n")

    # this prefix is used to detect methods in rel_1_15 for DeleteOptions
    # where the instead of the object being the 'body' parameter it is the
    # (UNSPECIFIED!) 'v1_delete_options' parameter. Horrifying...
    del_collection_prefix = "delete_collection"

    def make_docstring(self, parameters: List['OpParameter']) -> List[str]:
        docstring_parts = ['    r"""', f'    {self.description}']
        docstring_parts.append("")
        docstring_parts.append(f'    operationID: {self.get_effective_op_id()}')
        docstring_parts.append(f'    path: {self.op_path}')
        if parameters:
            docstring_parts.append("")
            for p in parameters:
                ds = p.docstring(hanging_indent="          ", linelen=80)
                docstring_parts.append(f'   {ds}')
        docstring_parts.append("    :param client: optional; instance of "
                               "kubernetes.client.api_client.ApiClient")
        docstring_parts.extend(self.get_async_doc())
        docstring_parts.extend(self.make_return_doc())
        docstring_parts.append('   """')
        return docstring_parts

    def get_async_doc(self) -> List[str]:
        return ["    :param async_req: bool; if True, call is "
                "async and the caller must invoke ",
                "        .get() on the returned Response object. Default "
                "is False, which makes ",
                "        the call blocking."]

    def make_return_doc(self) -> List[str]:
        docstring_parts = []
        if self.returns:
            docstring_parts.append("")
            docstring_parts.append("    :return: hikaru.utils.Response[T] instance with "
                                   "the following codes and ")
            docstring_parts.append("        obj value types:")
            docstring_parts.append('      Code  ObjType    Description')
            docstring_parts.append('      -----------------------------')
            for ret in self.returns.values():
                rettype = (ret.ref.hikaru_name if isinstance(ret.ref, ClassDescriptor)
                           else ret.ref)
                docstring_parts.append(f"      {ret.code}   {rettype}  "
                                       f"  {ret.description}")
        return docstring_parts

    def get_effective_op_id(self) -> str:
        return self.op_id

    def crud_counterpart_name(self) -> Optional[str]:
        """
        If self is a kind of CRUD method, return the associated CRUD verb name

        Checks self.op_id and decides if the id could be a synonym for a CRUD verb.

        :return: str  which is the name of the CRUD verb to use or None if no
            CRUD verb maps to this operation
        """
        if self.op_id.startswith('create') and self.op_id != 'create':
            return 'create'
        if (self.op_id.startswith('read') and self.op_id != 'read' and
            not self.op_id.endswith('Log')):
            return 'read'
        if self.op_id.startswith('patch') and self.op_id != 'patch':
            return 'update'
        if (self.op_id.startswith('delete') and
                not self.op_id.startswith('deleteCollection') and
                self.op_id != 'delete'):
            return 'delete'
        return None

    def as_crud_python_method(self, cd: Optional['ClassDescriptor'] = None) -> List[str]:
        crud_lines = []
        # Scale is full of read methods! skip it entirely
        if cd and cd.name == 'Scale':
            return crud_lines
        crud_name = self.crud_counterpart_name()
        if crud_name is None:
            return crud_lines
        crud_class = self.crud_registry.get(crud_name)
        if crud_class is None:
            return crud_lines
        assert issubclass(crud_class, SyntheticOperation)
        if crud_class.op_name in cd.crud_ops_created:
            return crud_lines
        cd.crud_ops_created.add(crud_class.op_name)
        crud_lines.extend(["", ""])
        crud_op: Operation = crud_class(self)
        crud_lines.extend(crud_op.as_python_method(cd))
        return crud_lines

    def get_meth_decorators(self) -> List[str]:
        return ["@staticmethod"] if self.is_staticmethod else []

    def get_meth_defline(self, parameters: Optional[List['OpParameter']] = None) -> str:
        def_parts = []
        if parameters is None:
            parameters = self.parameters
        def_parts.append(f"def {self.meth_name}(")
        required = [p for p in parameters if p.required]
        optional = [p for p in parameters if not p.required]
        params = []
        if not self.is_staticmethod:
            params.append('self')
        params.extend([p.as_python()
                       for p in chain(required, optional)])
        # here, we add any standard parameter(s) that all should have:
        params.append('client: ApiClient = None')
        params.extend(self.get_async_param())
        # end standards
        def_parts.append(", ".join(params))
        def_parts.append(f") -> {self.get_meth_return()}:")
        return "".join(def_parts)

    def get_async_param(self) -> List[str]:
        return ['async_req: bool = False']

    def get_meth_return(self) -> str:
        return f"Response['{self.owning_cd.hikaru_name}']"

    def get_meth_body(self, parameters: Optional[List['OpParameter']] = None,
                      cd: Optional['ClassDescriptor'] = None) -> List[str]:
        assignment_list = []
        body_seen = False
        if parameters is None:
            parameters = self.parameters
        required = [p for p in parameters if p.required]
        optional = [p for p in parameters if not p.required]
        for p in chain(required, optional):
            assert isinstance(p, OpParameter)
            if not body_seen and p.name in ('v1_delete_options', 'body'):
                body_seen = True
            if keyword.iskeyword(p.name):
                assignment_list.append(f"all_args['_{p.name}'] = {p.name}_")
            else:
                assignment_list.append(f"all_args['{camel_to_pep8(p.name)}'] = "
                                       f"{camel_to_pep8(p.name)}")
        # ok, now cover a weird case where if we have a body param that
        # is not the same type as the current class we're building, and the
        # method is static, we need to include this in the set of params we
        # set
        if (self.self_param and self.self_param.name == 'body' and
                self.self_param.ptype != cd and self.op_id.startswith('delete')):
            assignment_list.append(f"all_args['body'] = body")

        if (cd and cd.name == "DeleteOptions"
                and _release_in_process == 'rel_1_15' and
                self.k8s_access_tuple[3].startswith(self.del_collection_prefix)):
            body_key = 'v1_delete_options'
        else:
            body_key = 'body'
        object_response_codes = str(tuple(self.response_codes_returning_object()))
        body_lines = self._get_method_body(self.k8s_access_tuple[2],
                                           self.k8s_access_tuple[3],
                                           assignment_list,
                                           object_response_codes,
                                           body_key=body_key,
                                           use_body=body_seen)
        body = [f"    {bl}" for bl in body_lines]
        return body

    def prep_inbound_params(self) -> List['OpParameter']:
        return list(self.parameters)

    def prep_outbound_params(self) -> List['OpParameter']:
        return self.prep_inbound_params()

    def as_python_method(self, cd: Optional['ClassDescriptor'] = None) -> List[str]:
        if self.op_id is None:
            return []
        written_methods.add((self.version, self.op_id))
        parameters = self.prep_inbound_params()
        if self.is_staticmethod and self.self_param:
            parameters.append(self.self_param)
        lines = []
        lines.extend(self.get_meth_decorators())
        lines.append(self.get_meth_defline(parameters=parameters))
        ds = self.make_docstring(parameters=parameters)
        if ds:
            lines.extend(ds)
        lines.extend(self.get_meth_body(parameters=self.prep_outbound_params(),
                                        cd=cd))
        lines.extend(self.as_crud_python_method(cd))
        return lines


def register_crud_class(verb: str):
    def rcc(cls):
        Operation.crud_registry[verb] = cls
        return cls
    return rcc


class SyntheticOperation(Operation):
    op_name = 'noop'  # must be overridden by derived classes for the real op name

    def __init__(self, base_op: Operation):
        gvk = {'group': base_op.group,
               'version': base_op.gvk_version,
               'kind': base_op.kind}
        super(SyntheticOperation, self).__init__(base_op.verb, base_op.op_path,
                                                 self.op_name,
                                                 base_op.description,
                                                 gvk)
        for p in base_op.parameters:
            self.add_parameter(p.name, p.ptype, p.description, p.required)
        for r in base_op.returns.values():
            assert isinstance(r, OpResponse)
            self.add_return(str(r.code), r.ref, r.description)
        self.base_op = base_op

    def get_effective_op_id(self) -> str:
        return self.base_op.op_id

    def make_return_doc(self) -> List[str]:
        doc = list()
        doc.append('    :return: returns self; the state of self may be '
                   'permuted with a returned')
        doc.append('        HikaruDocumentBase object, whose values will be '
                   'merged into self ')
        doc.append('(if of the same type).')
        doc.append('    :raises: KubernetesException. Raised only by the CRUD '
                   'methods to signal ')
        doc.append('        that a return code of 400 or higher was returned by the '
                   'underlying ')
        doc.append('        Kubernetes library.')
        return doc

    def get_meth_return(self) -> str:
        return f"'{self.base_op.owning_cd.hikaru_name}'"

    def get_async_param(self) -> List[str]:
        return []

    def get_async_doc(self) -> List[str]:
        return []

    def as_python_method(self, cd: Optional['ClassDescriptor'] = None) -> List[str]:
        code = super(SyntheticOperation, self).as_python_method(cd=cd)
        code.extend(self.post_method_code(cd=cd))
        return code

    def post_method_code(self, cd: Optional['ClassDescriptor'] = None) -> List[str]:
        return []


_create_body_with_namespace = \
"""
    # noinspection PyDataclass
    client = client or self.client

    if namespace is not None:
        effective_namespace = namespace
    elif not self.metadata or not self.metadata.namespace:
        raise RuntimeError("There must be a namespace supplied in either "
                           "the arguments to {op_name}() or in a "
                           "{classname}'s metadata")
    else:
        effective_namespace = self.metadata.namespace
    res = self.{methname}({paramlist})
    if not 200 <= res.code <= 299:
        raise KubernetesException("Kubernetes returned error " + str(res.code))
    if self.__class__.__name__ == res.obj.__class__.__name__:
        self.merge(res.obj, overwrite=True)
    return self
"""

_create_body_no_namespace = \
"""
    # noinspection PyDataclass
    client = client or self.client

    res = self.{methname}({paramlist})
    if not 200 <= res.code <= 299:
        raise KubernetesException("Kubernetes returned error " + str(res.code))
    if self.__class__.__name__ == res.obj.__class__.__name__:
        self.merge(res.obj, overwrite=True)
    return self
"""


@register_crud_class('create')
class CreateOperation(SyntheticOperation):
    """
    A synthetic operation; making a synonym named 'create()' for whatever the
    actual create method is
    """
    op_name = 'create'

    def get_meth_decorators(self) -> List[str]:
        return []

    def prep_inbound_params(self) -> List['OpParameter']:
        params = [p for p in self.prep_outbound_params()
                  if p.name not in ('name', 'async_req')]
        return params

    def prep_outbound_params(self) -> List['OpParameter']:
        params = []
        for p in self.parameters:
            if p.name == 'namespace':
                p.required = False
                p.description = f"{p.description}. NOTE: if you leave out the " \
                                f"namespace from the arguments you *must* have " \
                                f"filled in the namespace attribute in the metadata " \
                                f"for the resource!"
            if p.name == "async_req":
                continue
            params.append(p)
        return params

    def _with_namespace_template(self):
        return _create_body_with_namespace

    def _without_namespace_template(self):
        return _create_body_no_namespace

    def namespace_name(self):
        return 'effective_namespace'

    def name_name(self):
        return 'self.metadata.name'

    def get_meth_body(self, parameters: Optional[List['OpParameter']] = None,
                      cd: Optional['ClassDescriptor'] = None) -> List[str]:
        required = [p for p in parameters if p.required]
        optional = [p for p in parameters if not p.required]
        param_assignments = []
        seen_namespace = False
        for p in chain(required, optional):
            assert isinstance(p, OpParameter)
            if p.name == "namespace":
                seen_namespace = True
                local_name = self.namespace_name()
                param_name = camel_to_pep8(p.name)
            elif p.name == 'name':
                local_name = self.name_name()
                param_name = camel_to_pep8(p.name)
            else:
                local_name = param_name = camel_to_pep8(p.name)
            param_assignments.append(f"{param_name}={local_name}")
        param_assignments.append("client=client")
        body_str = (self._with_namespace_template()
                    if seen_namespace else
                    self._without_namespace_template())
        fdict = {"classname": cd.hikaru_name if cd else 'UNKNOWN',
                 "methname": self.base_op.meth_name,
                 'paramlist': ", ".join(param_assignments),
                 'op_name': self.op_name}
        body = body_str.format(**fdict)
        return body.split("\n")


_update_context_manager = \
"""

def __enter__(self):
    return self

def __exit__(self, ex_type, ex_value, ex_traceback):
    passed = ex_type is None and ex_value is None and ex_traceback is None
    has_rollback = hasattr(self, "__rollback")
    if passed:
        try:
            self.update()
        except Exception:
            if has_rollback:
                self.merge(getattr(self, "__rollback"), overwrite=True)
                delattr(self, "__rollback")
            raise
    if has_rollback:
        if not passed:
            self.merge(getattr(self, "__rollback"), overwrite=True)
        delattr(self, "__rollback")
    return False
    """


@register_crud_class('update')
class UpdateOperation(CreateOperation):
    """
    A synthetic operation to make an 'update()' crud method to provide a synonym
    to the patch method
    """
    op_name = 'update'

    def post_method_code(self, cd: Optional['ClassDescriptor'] = None) -> List[str]:
        return _update_context_manager.split("\n")


_delete_body_with_namespace = \
"""
    # noinspection PyDataclass
    client = client or self.client

    if namespace is not None:
        effective_namespace = namespace
    elif not self.metadata or not self.metadata.namespace:
        raise RuntimeError("There must be a namespace supplied in either "
                           "the arguments to {op_name}() or in a "
                           "{classname}'s metadata")
    else:
        effective_namespace = self.metadata.namespace

    if name is not None:
        effective_name = name
    elif not self.metadata or not self.metadata.name:
        raise RuntimeError("There must be a name supplied in either "
                           "the arguments to {op_name}() or in a "
                           "{classname}'s metadata")
    else:
        effective_name = self.metadata.name
    res = self.{methname}({paramlist})
    if not 200 <= res.code <= 299:
        raise KubernetesException("Kubernetes returned error " + str(res.code))
    if self.__class__.__name__ == res.obj.__class__.__name__:
        self.merge(res.obj, overwrite=True)
    elif isinstance(res.obj, Status):
        self._status = res.obj
    return self
"""

_delete_body_without_namespace = \
"""
    # noinspection PyDataclass
    client = client or self.client

    if name is not None:
        effective_name = name
    elif not self.metadata or not self.metadata.name:
        raise RuntimeError("There must be a name supplied in either "
                           "the arguments to {op_name}() or in a "
                           "{classname}'s metadata")
    else:
        effective_name = self.metadata.name
    res = self.{methname}({paramlist})
    if not 200 <= res.code <= 299:
        raise KubernetesException("Kubernetes returned error " + str(res.code))
    if self.__class__.__name__ == res.obj.__class__.__name__:
        self.merge(res.obj, overwrite=True)
    elif isinstance(res.obj, Status):
        self._status = res.obj
    return self
"""


@register_crud_class('delete')
class DeleteOperation(CreateOperation):
    op_name = 'delete'

    def get_meth_decorators(self) -> List[str]:
        return []

    def prep_inbound_params(self) -> List['OpParameter']:
        return self.prep_outbound_params()

    def prep_outbound_params(self) -> List['OpParameter']:
        params = []
        for p in self.parameters:
            if p.name in ('namespace', 'name'):
                p.required = False
                p.description = f"{p.description}. NOTE: if you leave out the " \
                                f"{p.name} from the arguments you *must* have " \
                                f"filled in the {p.name} attribute in the metadata " \
                                f"for the resource!"
            if p.name == 'async_req':
                continue
            params.append(p)
        return params

    def name_name(self):
        return 'effective_name'

    def _with_namespace_template(self):
        return _delete_body_with_namespace

    def _without_namespace_template(self):
        return _delete_body_without_namespace


@register_crud_class('read')
class ReadOperation(DeleteOperation):
    """
    A synthetic operation; simple read() method for a more complex class
    """
    op_name = 'read'


objop_param_mismatches: Dict[str, Operation] = {}
response_mismatches: Dict[str, Operation] = {}


class ClassDescriptor(object):
    _doc_markers = ('apiVersion', 'kind')

    def __init__(self, swagger_name: str, swagger: dict):
        self.has_doc_markers = False
        self.has_gvk_dict = "x-kubernetes-group-version-kind" in swagger
        group, version, name = process_swagger_name(swagger_name)
        if version is not None:
            version: VersionStr = VersionStr(version)
        self.group = group if group is not None else ''
        if self.has_gvk_dict:
            gvk = swagger["x-kubernetes-group-version-kind"][0]
            self.api_version_group = gvk["group"]
            if self.api_version_group == "":
                self.api_version_group = "core"
        else:
            self.api_version_group = self.group
        self.name = self.kind = name
        self.version: VersionStr = version
        self.swagger = swagger
        self.operations: Dict[str, Operation] = {}
        self.description = self.swagger.get('description', '')
        self.type = swagger.get('type', None)
        self.is_subclass_of = (types_map[self.type]
                               if self.type in types_map
                               else None)
        self.required_props = []
        self.optional_props = []
        self.watchable = False
        self._hikaru_name = None
        self.crud_ops_created = set()
        self.properties_processed: bool = False

    @property
    def is_document(self):
        return self.has_doc_markers and self.has_gvk_dict

    def supports_namespaced_watch(self):
        if self.watchable:
            retval = any([True for op in self.operations.values()
                          if op.supports_watch and 'Namespaced' in op.op_id])
        else:
            retval = False
        return retval

    @property
    def hikaru_name(self) -> str:
        if self._hikaru_name is None:
            if PreferredVersions.is_preferred_for_swagger_gvk(self.group, self.version,
                                                              self.name):
                self._hikaru_name = self.name
            else:
                group = self.group if self.group is not None else ''
                group = group.split('.')[0]
                if not group and self.api_version_group:
                    group = self.api_version_group.split('.')[0]
                self._hikaru_name = f"{self.name}_{group}"
        return self._hikaru_name

    def add_operation(self, op: Operation):
        if op.supports_watch:
            self.watchable = True
        self.operations[op.op_id] = op
        op.set_owning_class_descriptor(self)

    def adjust_special_props(self, fd: PropertyDescriptor):
        if fd.name == 'apiVersion':
            first_bit = (f'{self.api_version_group}/'
                         if self.api_version_group not in ('core', '')
                         else "")
            fd.default_value = f'"{first_bit}{self.version}"'
        elif fd.name == 'kind':
            fd.default_value = f'"{self.name}"'

    def process_properties(self):
        if self.properties_processed:
            return
        self.properties_processed = True
        doc_markers = set(self._doc_markers)
        required = self.swagger.get('required', [])
        for pname, pdict in self.swagger['properties'].items():
            prop = PropertyDescriptor(self, pname, pdict)
            if pname in self._doc_markers:
                self.adjust_special_props(prop)
                try:
                    doc_markers.remove(pname)
                except KeyError:
                    pass
                if not doc_markers:
                    self.has_doc_markers = True
            if prop.name in required:
                self.required_props.append(prop)
            else:
                self.optional_props.append(prop)

    @staticmethod
    def split_line(line, prefix: str = "   ", hanging_indent: str = "",
                   linelen: int = 90) -> List[str]:
        parts = []
        if line is not None:
            words = line.split()
            current_line = [prefix]
            for w in words:
                w = w.strip()
                if not w:
                    continue
                if (sum(len(s) for s in current_line) + len(current_line) + len(w) >
                        linelen):
                    parts.append(" ".join(current_line))
                    current_line = [prefix]
                    if hanging_indent:
                        current_line.append(hanging_indent)
                current_line.append(w)
            else:
                if current_line:
                    parts.append(" ".join(current_line))
        return parts

    def as_python_class(self, for_version: VersionStr) -> str:
        lines = list()
        # start of class statement
        if self.is_subclass_of is not None:
            base = self.is_subclass_of
        else:
            # then it is to be a dataclass
            lines.append("@dataclass")
            base = (HikaruDocumentBase.__name__
                    if self.is_document else
                    HikaruBase.__name__)
        lines.append(f"class {self.hikaru_name}({base}):")
        # now the docstring
        ds_parts = ['    r"""']
        ds_parts.extend(self.split_line(self.description))
        ds_parts.append("")
        ds_parts.append(f'    Full name: {self.name.split("/")[-1]}')
        if self.is_subclass_of is None:
            ds_parts.append("")
            ds_parts.append("    Attributes:")
            for p in self.required_props:
                ds_parts.extend(self.split_line(f'{p.name}: {p.description}',
                                                hanging_indent="   "))
            for p in (x for x in self.optional_props if x.container_type is None):
                ds_parts.extend(self.split_line(f'{p.name}: {p.description}',
                                                hanging_indent="   "))
            for p in (x for x in self.optional_props if x.container_type is not None):
                ds_parts.extend(self.split_line(f'{p.name}: {p.description}',
                                                hanging_indent="   "))
        ds_parts.append('    """')
        lines.extend(ds_parts)
        if self.is_subclass_of is None:
            if self.required_props or self.optional_props:
                lines.append("")
            if self.is_document:
                lines.append(f"    _version = '{self.version}'")
            for p in self.required_props:
                lines.append(p.as_python_typeanno(True))
            for p in (x for x in self.optional_props if x.container_type is None):
                lines.append(p.as_python_typeanno(False))
            for p in (x for x in self.optional_props if x.container_type is not None):
                lines.append(p.as_python_typeanno(False))
            if self.is_document:
                lines.append("    # noinspection PyDataclass")
                lines.append("    client: InitVar[Optional[ApiClient]] = None")
        lines.append("")
        # now the operations
        for op in (o for o in self.operations.values() if o.version == for_version and
                   o.should_render and
                   self.is_document):
            assert isinstance(op, Operation)
            method_lines = [f"    {line}" for line in op.as_python_method(self)
                            if op.should_render]
            method_lines.append("")
            lines.extend(method_lines)
            if op.supports_watch:
                if 'Namespaced' in op.meth_name:
                    target = '_namespaced_watcher'
                else:
                    target = '_watcher'
                pkgname, modname, clsname, methname = \
                    determine_k8s_mod_class(self, op)
                lines.append(f"    {target} = WatcherDescriptor('{pkgname}', "
                             f"'{modname}', '{clsname}', "
                             f"'{methname}')")
                lines.append("")

        code = "\n".join(lines)
        try:
            code = format_str(code, mode=Mode())
        except NothingChanged:
            pass
        return code

    def depends_on(self, include_external=False) -> list:
        """
        returns a list of ClassDescriptors this ClassDescriptor depends on
        :param include_external:
        :return:
        """
        r = [p.depends_on() for p in self.required_props]
        deps = [p for p in r
                if p is not None]
        o = [p.depends_on() for p in self.optional_props]
        deps.extend(p for p in o
                    if p is not None and (True
                                          if include_external else
                                          self.version == p.version))

        for op in self.operations.values():
            assert isinstance(op, Operation)
            deps.extend(op.depends_on())
        return [d for d in deps if d != self or d.name == "JSONSchemaProps"]

    def has_properties(self) -> bool:
        return len(self.required_props) > 0 or len(self.optional_props) > 0


# class map
# the outer map's keys are version, value is an inner map whose keys
# are group, and whose value is the innermost dict whose keys are
# the swagger
_all_classes: Dict[VersionStr, Dict[str, Dict[str, ClassDescriptor]]] = {}


def store_swagger_object(k: str, v: dict):
    cd = ClassDescriptor(k, v)
    group, version, name = cd.group, cd.version, cd.name
    ver_dict = _all_classes.get(version)
    if ver_dict is None:
        _all_classes[version] = ver_dict = {}
    group_dict = ver_dict.get(group)
    if group_dict is None:
        ver_dict[group] = group_dict = {}
    group_dict[name] = cd
    # put in an aliased entry for this if cd.group != cd.api_version_group
    if cd.group != cd.api_version_group:
        group_dict = ver_dict.get(cd.api_version_group)
        if group_dict is None:
            ver_dict[cd.api_version_group] = group_dict = {}
        group_dict[name] = cd
    # put in an aliased entry for this if there are dots in the group name
    group_no_dots = group.split('.')[0]
    if group_no_dots != group:
        group_dict = ver_dict.get(group_no_dots)
        if group_dict is None:
            ver_dict[group_no_dots] = group_dict = {}
        group_dict[group_no_dots] = cd
    if cd.group != cd.api_version_group:
        group_no_dots = cd.api_version_group.split('.')[0]
        group_dict = ver_dict.get(group_no_dots)
        if group_dict is None:
            ver_dict[group_no_dots] = group_dict = {}
        group_dict[group_no_dots] = cd


_mod_classes: Dict[VersionStr, Dict[str, List[ClassDescriptor]]] = {}


def get_module_def(ver: Optional[VersionStr]) -> Dict[str, List[ClassDescriptor]]:
    """
    Should only be called when all class defs have been loaded as results are cached
    :param ver:
    :return:
    """
    ver_classes = _mod_classes.get(ver)
    if ver_classes is not None:
        return ver_classes

    ver_classes: Dict[str, List[ClassDescriptor]] = defaultdict(list)
    vdict = _all_classes.get(ver)
    if vdict is None:
        raise RuntimeError(f"no version dict named {ver}")
    for gdict in vdict.values():
        for k, v in gdict.items():
            ver_classes[k].append(v)
    _mod_classes[ver] = ver_classes
    return ver_classes


def find_cd_by_gvk(group: str, version: VersionStr, name: str,
                   recurse: bool = True) -> Optional[ClassDescriptor]:
    group = '' if group is None else group
    vdict = _all_classes.get(version)
    if vdict is None:
        warn(f"Can't find a version dict named {version} for ref "
             f"{group}.{version}.{name}")
        return None
    gdict = vdict.get(group)
    if gdict is None:
        warn(f"Can't find a group dict named {group} for ref "
             f"{group}.{version}.{name}")
        return None
    cd = gdict.get(name)
    if cd is None:
        # OK, there are a couple of edge cases to consider. First, we want to
        # consider looking into group 'core' if the current group is ''. Next,
        # sometimes a group has a value but instead the cd winds up being in
        # group '', so we look there before we finally throw up our hands.
        if group == '' and recurse:
            cd = find_cd_by_gvk('core', version, name, recurse=False)
        if cd is None and group != '' and recurse:
            cd = find_cd_by_gvk('', version, name, recurse=False)
        if cd is None:
            warn(f"Can't find a class descriptor named {name} for ref "
                 f"{group}.{version}.{name}")
        return cd
    return cd


def find_cd_by_property_ref(initial_property_ref: str) -> Optional[ClassDescriptor]:
    """
    Look up a ClassDescriptor using the properties swagger ref
    :param initial_property_ref: str; value of $ref in the swagger for a property
    :return:
    """
    property_ref = initial_property_ref.replace('#/definitions/', '')
    group, version, name = process_swagger_name(property_ref)
    return find_cd_by_gvk(group, VersionStr(version) if version is not None else version, name)


def stop_when_true(test_expr, result_expr, seq):
    """
    feed elements into expr until it returns True, returning that element (None otherwise)

    :param test_expr: callable of 1 arg that returns True/False
    :param result_expr: callable of 1 arg; takes found element from test_expr
        and maps it to a final value to return
    :param seq: iterable of elements that can be passed to expr; when expr returns
        True then return that element, None otherwise
    :return: an element from seq or None
    """
    result = None
    for e in seq:
        if test_expr(e):
            result = result_expr(e)
            break
    return result


_dont_remove_groups = {"storage", "policy", "resource"}


def make_method_name(op: Operation, cd: ClassDescriptor=None) -> str:
    under_name = camel_to_pep8(op.op_id)
    parts = under_name.split("_")
    group = op.group.replace(".k8s.io", "") if op.group else ""
    try:
        parts.remove(cd.version if cd else op.version)
    except ValueError:
        pass
    try:
        if group not in _dont_remove_groups:
            parts.remove(group)
    except ValueError:
        pass
    result = "_".join(parts)
    return result


def _select_from_candidates(candidates: List[ClassDescriptor],
                            op: Operation) -> Optional[ClassDescriptor]:
    for op_response in op.returns.values():
        if 200 <= op_response.code < 300:
            if op_response.ref in candidates:
                return op_response.ref
    return None


def _best_guess(op: Operation) -> Optional[ClassDescriptor]:
    # look for a good class for this op based on the op name
    md: Dict[str, List[ClassDescriptor]] = get_module_def(op.version)
    meth_name = make_method_name(op)
    parts = meth_name.split('_')
    parts.reverse()
    try:
        parts.remove("namespaced")  # this never shows up in a class name
    except ValueError:
        pass
    if 'api' in parts:
        parts[parts.index('api')] = 'API'
    new_parts = []
    guess: Optional[ClassDescriptor] = None
    candidates: Optional[List[ClassDescriptor]] = None
    # first, look for just each part of the name as a class
    # only take the first match
    for part in parts:
        test_name = part.capitalize() if part != 'API' else part
        if guess is None and test_name in md:
            candidates = md[test_name]
            if len(candidates) > 1:
                guess = _select_from_candidates(candidates, op)
            else:
                guess = candidates[0]
    # next, look for a longer name by concat'ing from the end forward, taking
    # any longer matches
    for part in parts:
        new_parts.insert(0,
                         part.capitalize() if part != 'API' else part)
        test_name = "".join(new_parts)
        if test_name in md:
            if not guess or len(guess.name) < len(test_name):
                candidates = md[test_name]
                if len(candidates) > 1:
                    guess = _select_from_candidates(candidates, op)
                else:
                    guess = candidates[0]
    # next check: if a longer name is possible, then look for a permutation
    if not guess or len(guess.name) < len(''.join(new_parts)):
        # then a better guess might exist via some permutation of the name parts
        for perm in permutations(new_parts):
            test_name = "".join(perm)
            if test_name in md:
                candidates = md[test_name]
                guess = _select_from_candidates(candidates, op)
                break
    # GVK check; turn to the gvk entry (if populated) to find an ClassDescriptor
    # that might have a better name
    group, version, kind = op.group, op.gvk_version, op.kind
    if group is None:
        group = ''
    group = group.split('.')[0]
    gvk_guess = find_cd_by_gvk(group, version, kind)
    if not guess or (gvk_guess is not None and len(guess.name) < len(gvk_guess.name)):
        guess = gvk_guess
    # returns check; look to the returns and if you find any that have a status
    # code in the 200s and have a ref to a ClassDescriptor that has a longer
    # name than the one we matched, pick that one instead
    for op_response in op.returns.values():
        if 200 <= op_response.code < 300:
            if isinstance(op_response.ref, ClassDescriptor):
                if not guess or (len(guess.name) < len(op_response.ref.name) and
                                op_response.ref.name != 'Status'):
                    guess = op_response.ref
                    break
    return guess


def process_params_and_responses(path: str, verb: str, op_id: str,
                                 params: list, responses: dict, description: str,
                                 gvk_dict: dict,
                                 reuse_op: Operation = None) -> Operation:
    version = get_path_version(path)
    if reuse_op is None:
        new_op = Operation(verb, path, op_id, description, gvk_dict)
    else:
        new_op = reuse_op
    for param in params:
        has_mismatch = False
        name = param["name"]
        required = True if ('required' in param) and param['required'] else False
        description = param.get('description', '')
        if "type" in param:
            ptype = param["type"]
        elif "schema" in param:
            schema = param["schema"]
            pref = schema.get("$ref")
            if pref:
                ptype = find_cd_by_property_ref(pref)
                if ptype is None:
                    raise RuntimeError(f"Couldn't find a ClassDescriptor for "
                                       f"parameter {name} in {op_id}")

            else:
                ptype = schema.get("type")
                if not ptype:
                    raise RuntimeError(f"Can't determine type of param '{name}' "
                                       f"in path {path}, verb {verb}")
                elif ptype == "object":
                    ptype = "Any"
                # otherwise, leave it alone
        else:
            raise RuntimeError(f"Don't know what to do with param"
                               f" {path}.{verb}.{name}")
        new_op.add_parameter(name, ptype, description, required)
        if has_mismatch:
            objop_param_mismatches[f"{name}:{new_op.op_id}"] = new_op

    cd_in_params: Optional[ClassDescriptor] = \
        stop_when_true(lambda x: x is not None and
                       (isinstance(x.ptype, ClassDescriptor) or
                        x.is_bodyany),
                       lambda x: x.ptype,
                       [new_op.self_param] + new_op.parameters)

    for code, response in responses.items():
        has_mismatch = False
        description = response.get('description', '')
        if 'schema' in response:
            if '$ref' in response['schema']:
                ref = full_swagger_name(response['schema']['$ref'])
                ptype = find_cd_by_property_ref(ref)
                if ptype is None:
                    raise RuntimeError(f"Couldn't find a ClassDescriptor for "
                                       f"response {code} in {op_id}")
            elif 'type' in response['schema']:
                ptype = response['schema']['type']
                ptype = types_map.get(ptype, ptype)
            else:
                raise RuntimeError(f"Don't know how to deal with this"
                                   f" schema: {response['schema']}")
        else:
            ptype = None
        new_op.add_return(code, ptype, description)
        if has_mismatch:
            response_mismatches[f"{code}:{new_op.op_id}"] = new_op

    cd_in_responses: Optional[ClassDescriptor] = \
                                stop_when_true(lambda x:
                                               isinstance(x.ref,
                                                          ClassDescriptor),
                                               lambda x: x.ref,
                                               new_op.returns.values())

    whose_method: Optional[ClassDescriptor] = None
    if cd_in_params:
        if cd_in_params != 'Any':
            if cd_in_params.name == "DeleteOptions":
                if cd_in_responses:
                    whose_method = cd_in_responses
                    new_op.is_staticmethod = True
                else:
                    whose_method = cd_in_params
            else:
                whose_method = cd_in_params
    elif cd_in_responses:
        whose_method = cd_in_responses
        new_op.is_staticmethod = True
    else:
        # then no objects in the params or responses; consider further below
        pass

    guess: Optional[ClassDescriptor] = None
    if whose_method:
        guess = _best_guess(new_op)
        if (guess and whose_method is cd_in_responses and
                whose_method is not cd_in_params and
                whose_method.name != guess.name and
                not new_op.op_id.startswith('list')):
            guess.add_operation(new_op)
        else:
            whose_method.add_operation(new_op)
    else:
        new_op.is_staticmethod = True if new_op.bodyany is None else False
        if new_op.op_id:
            guess = _best_guess(new_op)
        if guess:
            guess.add_operation(new_op)
        else:
            if new_op.op_id is not None:
                print(f'Wanted to add a query op: {new_op.op_id}')
    return new_op


class PreferredVersions(object):
    # preferred is keyed by the swagger class name, and values are lists
    # of two-tuples, the first element being the version that contains the
    # preferred variation, and the second being the group name of the preferred
    # variation
    preferred: Dict[str, Set[Tuple[VersionStr, str]]] = {}

    @classmethod
    def load_preferreds(cls, jdict: Dict[str, List[dict]]):
        # top level key is 'preferred_versions', value is a list of dicts
        prefs = jdict.get('preferred_versions', [])
        for pref in prefs:
            clsname = pref['class_name']
            cls.preferred[clsname] = {(VersionStr(entry['colliding_version']),
                                       entry['preferred_group'])
                                      for entry in pref['preferred_group_by_version']}

    @classmethod
    def is_preferred_for_swagger_gvk(cls, group: str, ver: str, kind: str) -> bool:
        """
        Determines if the supplied GVK values should be preferred over similar ones

        For a given kind value, there may be multiple version/group combinations
        that are preferred. This method returns True under two conditions: first,
        if there is no entry for the supplied kind at all, which means that any
        value supplied is preferred, and second, if there is a kind entry in the
        class AND entries for the supplied group/ver. The method returns False
        otherwise. It's up to the caller to figure out what to do in that case.

        :param group: str; value for the GVK group
        :param ver: str; value for the GVK version
        :param kind: str; value for the GVK kind
        :return: bool; True if the supplied values should be preferred over any other
            combination of group/ver for a given kind, False otherwise
        """
        ver = VersionStr(ver) if ver is not None else ver
        pref_set = cls.preferred.get(kind)
        if pref_set is None:
            return True
        else:
            return (ver, group) in pref_set


def _search_for_method(group: str, version: str, kind: str,
                       methname: str) -> Union[NoneType,
                                               Tuple[str, str, str, str]]:
    version: VersionStr = VersionStr(version) if version is not None else version
    package_name = 'kubernetes.client.api'
    mgroup = group if group else 'core'
    mgroup = mgroup.replace(".k8s.io", "").replace(".", "_")
    module_name = f'.{mgroup}_{version}_api' if version else f'.{mgroup}_api'
    try:
        mod = importlib.import_module(module_name, package_name)
    except ModuleNotFoundError:
        result = None
    else:
        class_group = group if group else 'core'
        class_group = class_group.replace(".k8s.io", "")
        class_group = "".join(f.capitalize() for f in class_group.split("_"))
        if "." in class_group:
            class_group = "".join([w.capitalize() for w in class_group.split('.')])
        class_name = (f'{class_group}{version.capitalize()}Api'
                      if version else
                      f'{class_group}Api')
        cls = getattr(mod, class_name, None)
        if cls is None:
            result = None
        else:
            meth = getattr(cls, methname, None)
            if meth is not None:
                result = package_name, module_name, class_name, methname
            else:
                result = None
    return result


def determine_k8s_mod_class(cd: ClassDescriptor, op: Operation = None) -> \
        Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    from a reference path determine the Kubernetes Python client's module and class
    :param cd: a ClassDescriptor instance for which to find the API class
    :param op: Operation, optional. provides extra info to find the required
        method.
    :return: 4 tuple:
        - string: import path before the name of the module where the class lives
        - string: name of the module where the class lives
        - string: name of the class
        - string: method name
        If the method can't be resolved, a tuple of Nones is returned
    """
    method_name = make_method_name(op, cd)
    search_args = [(cd.group, cd.version, cd.kind),
                   (op.group, op.version, op.kind),
                   ('core', op.version, op.kind),
                   ('apps', op.version, op.kind)]
    pkg = mod = cls = meth = None
    for group, version, kind in search_args:
        details = _search_for_method(group, version, kind, method_name)
        if details is not None:
            pkg, mod, cls, meth = details
            break
    else:
        print(f"Can't find p/m/c/m for {method_name} in {cd.group} or {op.group}")
    return pkg, mod, cls, meth


def load_swagger(swagger_file_path: str):
    global _release_in_process, _release_hints
    f = open(swagger_file_path, 'r')
    d = json.load(f)
    info = d.get('info')
    rel_version = info.get("version")
    relnum = rel_version.split("-")[-1].replace(".", "_")
    release_name = f"rel_{relnum}"
    _release_in_process = release_name
    try:
        hint_text = open("build_helper.json", 'rt').read()
        h = json.loads(hint_text)
        _release_hints = h.get(_release_in_process)
        PreferredVersions.load_preferreds(_release_hints)
    except FileNotFoundError:
        print("NO HINTS LOADED")

    # this first pass shreds the definitions into separate dicts that are
    # keyed first by version, then by group, and finally by kind
    for k, v in d["definitions"].items():
        store_swagger_object(k, v)
    # This pass ensures that we can resolve every parameter reference in
    # every object, so that we can be sure that we can create the correct
    # init methods for each object and create refs to the right classes
    for vdict in _all_classes.values():
        for gdict in vdict.values():
            for cd in gdict.values():
                try:
                    cd.process_properties()
                except RuntimeError as e:
                    raise RuntimeError(f"failed on {cd.version}/{cd.group}/"
                                       f"{cd.name} with {e}")
    # next, we process the operations on all the objects, tying them to the
    # proper class
    for k, v in d["paths"].items():
        last_verb = None
        last_opid = None
        last_op = None
        for verb, details in v.items():
            if verb == "parameters" and type(details) == list:
                process_params_and_responses(k, last_verb, last_opid, details,
                                             {}, '', {}, reuse_op=last_op)
                last_op = None
                continue
            gvk = details.get("x-kubernetes-group-version-kind", {})
            description = details.get('description', '')
            op_id = details["operationId"]
            last_op = process_params_and_responses(k, verb, op_id,
                                                   details.get("parameters", []),
                                                   details.get("responses", {}),
                                                   description, gvk)
            last_verb = verb
            last_opid = op_id

    # finally, we sort out the definitions into modules, taking into account
    # dependencies between versions of classes.
    for ver in _all_classes.keys():
        mod = ModuleDef(ver)
        for cd in mod.all_classes.values():
            assert isinstance(cd, ClassDescriptor)
            if cd.operations:
                for op in cd.operations.values():
                    pkg, mod, cls, meth = determine_k8s_mod_class(cd, op)
                    if pkg is not None:
                        op.set_k8s_access((pkg, mod, cls, meth))
                    else:
                        # we can't find the underlying k8s client func;
                        # mark this as something we shouldn't render
                        op.should_render = False
                        print(f">>>Can't find the method for {cd.name} {op.op_id} "
                              f"{op.op_path}")


def _setup_dir(directory: str) -> Path:
    path = Path(directory)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if not path.is_dir():
            path.unlink()
            path.mkdir(parents=True)
    return path


def prep_model_root(directory: str) -> Path:
    path = _setup_dir(directory)
    return path


def output_footer(stream=sys.stdout):
    """
    Write out the footer that defines '__all__'
    :param stream: file to write the footer to
    """
    print(_module_footer, file=stream)


def _clean_directory(dirpath: str, including_dirpath=False):
    path = Path(dirpath)
    for p in path.iterdir():
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            _clean_directory(str(p), including_dirpath=True)
            if including_dirpath:
                p.rmdir()


def prep_rel_package(directory: str, deprecated: bool = False) -> Path:
    """
    This function empties the directory named 'directory', creating it if needed
    :param directory: string; name of an empty directory to create. Creates it
        if needed, and removes any existing content if it's already there.
    """
    path = _setup_dir(directory)
    # once here, the directory exists and is a directory; clean it out
    init = path / "__init__.py"
    init.touch()
    f = init.open('w', encoding='utf-8')
    print(_module_docstring, file=f)
    if deprecated:
        print("import warnings", file=f)
    print(_package_init_code, file=f)
    if deprecated:
        print(_deprecation_warning % path.name, file=f)
    print(file=f)
    output_footer(stream=f)
    return path


class ModuleDef(object):
    _cache: Dict[VersionStr, 'ModuleDef'] = {}

    def __new__(cls, version: Optional[VersionStr]):
        inst = cls._cache.get(version)
        if inst is None:
            inst = super(ModuleDef, cls).__new__(cls)
            inst.initialzed = False
            cls._cache[version] = inst
        return inst

    def __init__(self, version: Optional[VersionStr]):
        if not self.initialzed:
            self.initialzed = True
            self.version: VersionStr = VersionStr(version) if version is not None else version
            mod_classes: Dict[str, List[ClassDescriptor]] = get_module_def(version)
            self.all_classes: Dict[str, ClassDescriptor] = {}
            for cd_list in mod_classes.values():
                for cd in cd_list:
                    self.all_classes[cd.hikaru_name] = cd

    def external_versions_used(self) -> List[str]:
        ext_ver = set()
        for cd in self.all_classes.values():
            for dep in cd.depends_on(include_external=True):
                assert isinstance(dep, ClassDescriptor)
                if dep.version != self.version:
                    ext_ver.add(dep.version)
        return list(ext_ver)

    def as_python_module(self, stream=sys.stdout, import_unversioned=True):
        # first, determine if the unversioned classes module should be imported
        other_imports = []
        if import_unversioned:
            other_imports.append(f'from ..{unversioned_module_name} import *')

        # now look for the classes that need to be imported, but only if module is versioned
        classes_to_import: Dict[str, ClassDescriptor] = {}
        if self.version is not None:
            my_msm = self.version.get_msm()
            ga = self.version.is_ga(my_msm)
            for hikaru_name, cd in self.all_classes.items():
                for dep in cd.depends_on(include_external=True):
                    assert isinstance(dep, ClassDescriptor)
                    if self.version != dep.version:
                        dep_msm = dep.version.get_msm()
                        dep_ga = dep.version.is_ga(dep_msm)
                        if dep_ga:
                            if dep_msm[0] <= my_msm[0]:
                                classes_to_import[dep.hikaru_name] = dep
                            else:
                                raise Exception(f"Processing classes for module "
                                                f"{self.version}, class {hikaru_name} "
                                                f"has a dependency {dep.hikaru_name} on version "
                                                f"{dep.version} which is later")
                        else:
                            raise Exception(f"Processing classes for module {self.version}, "
                                            f"class {hikaru_name}, has a dependency on version "
                                            f"{dep.version} which is not GA")

        all_classes: Dict[str, ClassDescriptor] = dict(self.all_classes)
        # compute all pairs of objects involved in implementing 'watch' semantics
        watcher_pairs = {}
        for v in all_classes.values():
            if 'List' in v.hikaru_name and v.watchable:
                item_name = v.hikaru_name.replace('List', '')
                if item_name in all_classes:
                    watcher_pairs[item_name] = v.name
                else:
                    print(f"!!!!Can't find an item class for {v.name}")
        # compute & output all the imports needed from Kubernetes

        k8s_imports = {"ApiClient"}
        for cd in self.all_classes.values():
            for op in cd.operations.values():
                assert isinstance(op, Operation)
                if not op.should_render or not cd.is_document:
                    continue
                k8s_imports.add(op.k8s_access_tuple[2])
        k8s_imports = list(k8s_imports)
        k8s_imports.sort()

        output_boilerplate(stream=stream, other_imports=other_imports)
        for k8s_class in k8s_imports:
            print(f"from kubernetes.client import {k8s_class}", file=stream)
        # print import classes from other Hikaru sister modules
        # first, if not v1, the import Status from v1 as we'll be writing code
        # in methods that depend on it
        if self.version not in ("v1", None):
            print("from ..v1 import Status", file=stream)
        for cd in classes_to_import.values():
            print(f"from ..{cd.version} import {cd.hikaru_name}", file=stream)
        print("\n", file=stream)
        write_classes(list(all_classes.values()), self.version, stream=stream)
        if watcher_pairs:
            for k, v in watcher_pairs.items():
                print(f"{k}._watcher_cls = {v}", file=stream)
            print("\n", file=stream)
        output_footer(stream=stream)


def write_classes(class_list: List[ClassDescriptor], for_version: VersionStr,
                  stream=sys.stdout):
    for cd in class_list:
        if not cd.has_properties():
            print(f'Skipping code generation for attribute-less class {cd.name}, '
                  f'v {cd.version} for version {for_version}')
            continue
        print(cd.as_python_class(for_version), file=stream)
        print(file=stream)


def output_boilerplate(stream=sys.stdout, other_imports=None):
    """
    Write out the standard module header imports
    :param stream: where to write; sys.stdout default
    :param other_imports: None, or a list of strings to generate import
        statements for
    """
    print(_module_docstring, file=stream)
    print(file=stream)
    print(f"from hikaru.meta import {HikaruBase.__name__}, "
          f"{HikaruDocumentBase.__name__}, {KubernetesException.__name__}, "
          f"{WatcherDescriptor.__name__}",
          file=stream)
    print("from hikaru.generate import get_clean_dict", file=stream)
    print("from hikaru.utils import Response", file=stream)
    print("from typing import Dict, List, Optional, Any", file=stream)
    print("from dataclasses import dataclass, field, InitVar", file=stream)
    print("from kubernetes.client import CoreV1Api", file=stream)
    if other_imports is not None:
        for line in other_imports:
            print(line, file=stream)
    print(file=stream)


def prep_version_package(directory: str, version: VersionStr) -> Path:
    """
    This function creates an initializes the supplied version directory, creating if
    needed

    :param directory: string; name of a directory to create to hold the files for a
        single version in a release
    :param version: string; name of the version package to prep within directory
    :return: the Path object created for the version package
    """
    path = _setup_dir(directory)
    _clean_directory(str(path))
    init = path / "__init__.py"
    init.touch()
    f = init.open('w', encoding='utf-8')
    print(_module_docstring, file=f)
    print(_package_version_init_code.format(version), file=f)
    print(file=f)
    output_footer(stream=f)
    return path


watchables_doc = \
'''    """
    Attributes of this class are classes that support watches without the namespace
    keyword argument
    """'''


namespaced_watchables_doc = \
'''    """
    Attributes of this class are classes that support watches with the namespace
    keyword argument
    """'''


def write_watchables_module(path: Path, md: ModuleDef):
    watchables = {}
    for cd in md.all_classes.values():
        if cd.watchable and cd.is_document:
            watchables[cd.hikaru_name] = cd
            if 'List' in cd.hikaru_name:
                item = md.all_classes.get(cd.hikaru_name.replace('List', ''))
                if item is not None:
                    watchables[item.hikaru_name] = item

    namespaced = {k: v for k, v in watchables.items()
                  if v.supports_namespaced_watch() and 'List' in v.hikaru_name}
    for cd in list(namespaced.values()):
        if 'List' in cd.hikaru_name:
            item = md.all_classes.get(cd.hikaru_name.replace('List', ''))
            if item is not None and item.is_document:
                namespaced[item.hikaru_name] = item

    if watchables:
        path.touch()
        f = path.open('w', encoding='utf-8')
        print(_module_docstring, file=f)
        print(f'from .{md.version} import *', file=f)
        print("\n", file=f)
        print("class Watchables(object):  # pragma: no cover", file=f)
        print(watchables_doc, file=f)
        for cd in watchables.values():
            print(f'    {cd.hikaru_name} = {cd.hikaru_name}', file=f)
        print("\n\nwatchables = Watchables", file=f)

        # now the support for namespaced watchables, whether there are
        # any or not
        print('\n', file=f)
        print("class NamespacedWatchables(object):  # pragma: no cover", file=f)
        print(namespaced_watchables_doc, file=f)
        if namespaced:
            for cd in namespaced.values():
                print(f'    {cd.hikaru_name} = {cd.hikaru_name}', file=f)
        else:  # put an empty class in here just to keep the module API consistent
            print('    pass', file=f)
        print("\n\nnamespaced_watchables = NamespacedWatchables", file=f)


_documents_init_code = \
"""
try:
    from .{} import *
except ImportError:  # pragma: no cover
    pass
from hikaru import HikaruDocumentBase

__all__ = [o.__name__ for o in globals().values()
           if type(o) is type and issubclass(o, HikaruDocumentBase)]
"""


def write_documents_module(path: Path, version: VersionStr):
    path.touch()
    f = path.open('w', encoding='utf-8')
    print(_module_docstring, file=f)
    print(_documents_init_code.format(version), file=f)
    print(file=f)
    f.close()


def write_modules(pkgpath: str):
    pkg = Path(pkgpath)
    mod_names = []
    # first, create the module with un-versioned object defs
    if None in _all_classes:
        md = ModuleDef(None)
        unversioned = pkg / f'{unversioned_module_name}.py'
        f = unversioned.open('w', encoding='utf-8')
        md.as_python_module(stream=f, import_unversioned=False)
        f.close()

    # next, write out all the version-specific object defs
    for k, v in _all_classes.items():
        if k is not None:
            md: ModuleDef = ModuleDef(k)
            version_path = pkg / md.version
            prep_version_package(str(version_path), md.version)
            mod_names.append(md.version)
            mod = version_path / f'{md.version}.py'
            f = mod.open('w', encoding='utf-8')
            md.as_python_module(stream=f)
            f.close()
            documents_path = version_path / "documents.py"
            write_documents_module(documents_path, md.version)
            watchables_path = version_path / "watchables.py"
            write_watchables_module(watchables_path, md)

    # finally, capture the names of all the version modules in version module
    versions = pkg / 'versions.py'
    f = versions.open('w', encoding='utf-8')
    print(f"versions = {str(mod_names)}", file=f)
    f.close()


def make_namespace_root(directory: str):
    """
    ensures the model namespace package has the most recent defrel.py file
    """
    path = Path(directory)
    defrel_file = path / "defrel.py"
    if defrel_file.exists():
        defrel_file.unlink()
    dfile = defrel_file.open("w", encoding="utf-8")
    sfile = Path("defrel_master.py").open("r")
    dfile.write(sfile.read())
    dfile.close()


_deprecations_skeleton = """from hikaru.generate add_deprecations_for_release

add_deprecations_for_release("%s", {})
"""


def make_deprecations(directory: str):
    path = Path(directory)
    depmod_path = path


def build_it(swagger_file: str):
    load_swagger(swagger_file)
    path = prep_model_root(model_package)
    relpath = path / _release_in_process
    prep_rel_package(str(relpath), deprecated=False)
    write_modules(str(relpath))
    make_namespace_root(model_package)


_release_in_process = None
_release_hints = {}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <swagger-json-file>")
        sys.exit(1)
    if len(sys.argv) > 2:
        print("no arguments besides the swagger file")
        sys.exit(1)
    print(f">>>Processing {sys.argv[1]}")
    build_it(sys.argv[1])
