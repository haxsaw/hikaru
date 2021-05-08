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
import importlib
from pathlib import Path
import sys
from typing import List, Dict, Optional, Union, Tuple, Any, Set
import json
import re
import warnings
from black import format_file_contents, FileMode, NothingChanged
from hikaru.naming import (process_swagger_name, full_swagger_name,
                           dprefix, camel_to_pep8)
from hikaru.meta import HikaruBase, HikaruDocumentBase


NoneType = type(None)


remaining_ops_module = "misc.py"


def _clean_directory(dirpath: str, including_dirpath=False):
    path = Path(dirpath)
    for p in path.iterdir():
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            _clean_directory(str(p), including_dirpath=True)
            if including_dirpath:
                p.rmdir()


_package_init_code = \
"""
try:
    from .v1 import *
except ImportError:  # pragma: no cover
    pass"""


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


def make_root_init(directory: str, default_rel: str):
    path = Path(directory)
    init = path / "__init__.py"
    if init.exists():
        init.unlink()
    f = init.open('w')
    f.write(_module_docstring)
    f.write(f"from .{default_rel} import *\n")
    f.write(f"default_release = '{default_rel}'\n")
    f.close()


def prep_rel_package(directory: str) -> Path:
    """
    This function empties the directory named 'directory', creating it if needed
    :param directory: string; name of an empty directory to create. Creates it
        if needed, and removes any existing content if it's already there.
    """
    path = _setup_dir(directory)
    # once here, the directory exists and is a directory; clean it out
    # _clean_directory(str(path))
    init = path / "__init__.py"
    init.touch()
    f = init.open('w')
    print(_module_docstring, file=f)
    print(_package_init_code, file=f)
    print(file=f)
    output_footer(stream=f)
    return path


_package_version_init_code = \
"""
try:
    from .{} import *
except ImportError:  # pragma: no cover
    pass"""


def prep_version_package(directory: str, version: str) -> Path:
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
    f = init.open('w')
    print(_module_docstring, file=f)
    print(_package_version_init_code.format(version), file=f)
    print(file=f)
    output_footer(stream=f)
    return path


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


def output_boilerplate(stream=sys.stdout, other_imports=None):
    """
    Write out the standard module header imports
    :param stream: where to write; sys.stdout default
    :param other_imports: None, or a list of strings to generate import
        statements for
    """
    print(_module_docstring, file=stream)
    print(file=stream)
    print(f"from hikaru.meta import {HikaruBase.__name__}, {HikaruDocumentBase.__name__}",
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


_module_footer = '''globs = dict(globals())
__all__ = [c.__name__ for c in globs.values()
           if type(c) == type]
del globs'''


def output_footer(stream=sys.stdout):
    """
    Write out the footer that defines '__all__'
    :param stream: file to write the footer to
    """
    print(_module_footer, file=stream)


def write_classes(class_list, for_version: str, stream=sys.stdout):
    for cd in class_list:
        assert isinstance(cd, ClassDescriptor)
        if not cd.has_properties():
            print(f'Skipping code generation for attribute-less class {cd.short_name}, '
                  f'v {cd.version} for version {for_version}')
            continue
        print(cd.as_python_class(for_version), file=stream)
        print(file=stream)


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


def write_documents_module(path: Path, version: str):
    path.touch()
    f = path.open('w')
    print(_module_docstring, file=f)
    print(_documents_init_code.format(version), file=f)
    print(file=f)
    f.close()


def write_misc_module(path: Path, version: str):
    if version is None:
        return
    misc_file = path.open('w+')
    print(_module_docstring, file=misc_file)
    print("from typing import *", file=misc_file)
    print("from hikaru import HikaruOpsBase", file=misc_file)
    print("from hikaru.utils import Response", file=misc_file)
    print("from kubernetes.client import CoreV1Api, ApiClient", file=misc_file)

    print("\n", file=misc_file)
    vops = ops_by_version.get(version)
    if vops is not None:
        for domain, qops in vops.query_ops.items():
            if qops.operations:
                class_content = []
                for op in qops.operations.values():
                    op.is_staticmethod = True
                    if op.op_id is None:
                        print(f"still can't render {op.op_path}; no op_id")
                        continue
                    kube_client = _search_for_free_method(op.op_id)
                    if kube_client is None:
                        print(f"Can't find the K8S method for {op.op_id}")
                        continue
                    op.set_k8s_access(kube_client)
                    lines = op.as_python_method()
                    if lines:
                        if not class_content:
                            class_content.append(
                                f"class {domain.capitalize()}Ops(HikaruOpsBase):")
                            class_content.append("")
                        class_content.extend([f"    {line}" for line in lines])
                        class_content.append("")
                code = "\n".join(class_content)
                try:
                    code = format_file_contents(code, fast=False, mode=FileMode())
                except NothingChanged:
                    pass
                print(code, file=misc_file)


def write_modules(pkgpath: str):
    pkg = Path(pkgpath)
    d = module_defs()
    mod_names = []
    base = d.get(None)
    # first, create the module with un-versioned object defs
    if base:
        unversioned = pkg / f'{unversioned_module_name}.py'
        assert isinstance(base, ModuleDef)
        f = unversioned.open('w')
        base.as_python_module(stream=f)
        f.close()

    # next, write out all the version-specific object defs
    for k, md in d.items():
        if k is not None:
            assert isinstance(md, ModuleDef)
            version_path = pkg / md.version
            prep_version_package(str(version_path), md.version)
            mod_names.append(md.version)
            mod = version_path / f'{md.version}.py'
            f = mod.open('w')
            md.as_python_module(stream=f)
            f.close()
            documents_path = version_path / "documents.py"
            write_documents_module(documents_path, md.version)
            # misc_path = version_path / remaining_ops_module
            # misc_path.touch()
            # write_misc_module(misc_path, md.version)

    # finally, capture the names of all the version modules in version module
    versions = pkg / 'versions.py'
    f = versions.open('w')
    print(f"versions = {str(mod_names)}", file=f)
    f.close()


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
    raise RuntimeError("Unable to locate method {k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
body = get_clean_dict(self)
all_args['{body_key}'] = body
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
return Response(result, codes_returning_objects)
"""

_static_method_body_template = \
"""client_to_use = client
inst = {k8s_class_name}(api_client=client_to_use)
the_method = getattr(inst, '{k8s_method_name}_with_http_info')
if the_method is None:  # pragma: no cover
    raise RuntimeError("Unable to locate method {k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
if body is not None:
    body = get_clean_dict(body) if isinstance(body, HikaruBase) else body
all_args['{body_key}'] = body
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
return Response(result, codes_returning_objects)
"""

_static_method_nobody_template = \
"""client_to_use = client
inst = {k8s_class_name}(api_client=client_to_use)
the_method = getattr(inst, '{k8s_method_name}_with_http_info')
if the_method is None:  # pragma: no cover
    raise RuntimeError("Unable to locate method {k8s_method_name}_with_http_info "
                       "on {k8s_class_name}; possible release mismatch?")
all_args = dict()
{arg_assignment_lines}
all_args['async_req'] = async_req
result = the_method(**all_args)
codes_returning_objects = {codes_returning_objects}
return Response(result, codes_returning_objects)
"""


class Operation(object):
    """
    A single operation from paths; associated with a verb such as 'get' or 'post'

    The same path may have multiple operations with different verbs, and hence
    may also involve different input params/outputs
    """

    regexp = re.compile(r'{(?P<pname>[a-z]+)}')

    def __init__(self, verb: str, op_path: str, op_id: str, description: str,
                 gvk_dict: dict):
        self.should_render = True
        self.verb = verb
        self.op_path = op_path
        self.version = get_path_version(self.op_path)
        self.gvk_version = gvk_dict.get('version')
        self.group = gvk_dict.get('group', 'custom_objects')
        self.kind = gvk_dict.get('kind')
        self.op_id = op_id
        self.description = description
        self.is_staticmethod = False
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
            self.add_parameter(pname, "str", "part of the URL path", required=True)

    def depends_on(self) -> list:
        deps = [p.ptype for p in self.parameters if isinstance(p.ptype, ClassDescriptor)]
        if self.self_param and isinstance(self.self_param.ptype, ClassDescriptor):
            deps.append(self.self_param.ptype)
        return deps

    def add_parameter(self, name: str, ptype: Any, description: str,
                      required: bool = False) -> 'OpParameter':
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
                                                          codes_returning_objects)
            else:
                rez = _static_method_nobody_template.format(k8s_class_name=
                                                            k8s_class_name,
                                                            k8s_method_name=
                                                            k8s_method_name,
                                                            arg_assignment_lines=
                                                            "\n".join(
                                                               arg_assignment_lines),
                                                            codes_returning_objects=
                                                            codes_returning_objects)
        else:
            rez = _method_body_template.format(k8s_class_name=k8s_class_name,
                                               k8s_method_name=k8s_method_name,
                                               body_key=body_key,
                                               arg_assignment_lines="\n".join(
                                                    arg_assignment_lines),
                                               codes_returning_objects=
                                               codes_returning_objects)
        return rez.split("\n")

    # this prefix is used to detect methods in rel_1_15 for DeleteOptions
    # where the instead of the object being the 'body' parameter it is the
    # (UNSPECIFIED!) 'v1_delete_options' parameter. Horrifying...
    del_collection_prefix = "delete_collection"

    def make_docstring(self) -> List[str]:
        docstring_parts = ['    r"""', f'    {self.description}']
        docstring_parts.append("")
        docstring_parts.append(f'    operationID: {self.op_id}')
        docstring_parts.append(f'    path: {self.op_path}')
        if self.parameters:
            docstring_parts.append("")
            for p in self.parameters:
                docstring_parts.append(f'   {p.docstring()}')
        docstring_parts.append("    :param client: optional; instance of "
                               "kubernetes.client.api_client.ApiClient")
        docstring_parts.append("    :param async_req: bool; if True, call is "
                               "async and the caller must invoke ")
        docstring_parts.append("        .get() on the returned Response object. Default "
                               "is False,  which ")
        docstring_parts.append("        makes the call blocking.")
        if self.returns:
            docstring_parts.append("")
            docstring_parts.append("    :return: hikaru.utils.Response instance with "
                                   "the following codes and ")
            docstring_parts.append("        obj value types:")
            docstring_parts.append('      Code  ObjType    Description')
            docstring_parts.append('      -----------------------------')
            for ret in self.returns.values():
                rettype = (ret.ref.short_name if isinstance(ret.ref, ClassDescriptor)
                           else ret.ref)
                docstring_parts.append(f"      {ret.code}   {rettype}  "
                                       f"  {ret.description}")
        docstring_parts.append('   """')
        return docstring_parts

    def as_python_method(self, cd=None) -> List[str]:
        written_methods.add((self.version, self.op_id))
        if self.op_id is None:
            return []
        if cd is not None:
            assert isinstance(cd, ClassDescriptor)
        version = get_path_version(self.op_path)
        if version is None:
            version = ""
        else:
            version = version.replace('v', 'V')
        stmt_name = self.op_id.replace(version, '')
        parts = []
        params = []
        parts.append(f"def {stmt_name}(")
        required = [p for p in self.parameters if p.required]
        optional = [p for p in self.parameters if not p.required]

        if not self.is_staticmethod:
            params.append('self')
        else:
            if self.self_param:
                optional.append(self.self_param)
        params.extend([p.as_python()
                       for p in chain(required, optional)])
        # here, we add any standard parmeter(s) that all should have:
        params.append('client: ApiClient = None')
        params.append('async_req: bool = False')
        # end standards
        parts.append(", ".join(params))
        parts.append(") -> Response:")

        docstring_parts = self.make_docstring()
        docstring = '\n'.join(docstring_parts)
        defline = "".join(parts)
        # do the work to create the method body; we need a list of assignment
        # statements that captures the data in each parameter that came into
        # the method to be passed to the k8s method. These are to be assigned
        # to keys in the 'all_args' dict
        assignment_list = []
        body_seen = False
        for p in chain(required, optional):
            assert isinstance(p, OpParameter)
            if not body_seen and p.name in ('v1_delete_options', 'body'):
                body_seen = True
            if p.name in python_reserved:
                assignment_list.append(f"all_args['_{p.name}'] = {p.name}_")
            else:
                assignment_list.append(f"all_args['{camel_to_pep8(p.name)}'] = "
                                       f"{camel_to_pep8(p.name)}")
        if (cd and cd.short_name == "DeleteOptions"
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
        final = []
        if self.is_staticmethod:
            final.append("@staticmethod")
        final.extend([defline, docstring] if docstring else [defline])
        final.extend(body)
        return final

# maybe later...
# class ListCreateOperation(Operation):
#     def __init__(self, contained_class: 'ClassDescriptor'):
#         super(ListCreateOperation, self).__init__(self, "put", "-created, no path-"
#                                                   'deferred', 'deferred',
#                                                   {'version': contained_class.version,
#                                                    'group': contained_class.group,
#                                                    'kind': f'{contained_class.kind}List'})
#         self.is_staticmethod = False
#         self.contained_class = contained_class
#         for k in self.contained_class.operations:
#             if k.startswith('create'):
#                 self._op_id = f'{k}List'
#                 break
#         else:
#             self._op_id = f'{self.contained_class.short_name}List'
#
#     @property
#     def op_id(self):
#         for k in self.contained_class.operations:
#             if k.startswith('create'):
#                 self._op_id = f'{k}List'
#                 break
#         else:
#             self._op_id = f'{self.contained_class.short_name}List'
#         return self._op_id
#
#     @op_id.setter
#     def op_id(self, name):
#         self._op_id = name


class ObjectOperations(object):
    """
    This object captures all of the operations that a doc is input for
    """
    def __init__(self, full_k8s_name: str):
        self.full_k8s_name = full_k8s_name
        self.operations: Dict[str, Operation] = {}

    def add_operation(self, op_id: str, operation: Operation):
        self.operations[op_id] = operation


class ClassDescriptor(object):
    def __init__(self, key, d):
        self.full_name = full_swagger_name(key)
        group, version, name = process_swagger_name(self.full_name)
        self.short_name = name
        self.group = None
        self.kind = None
        self.version = version
        self.description = "None"
        self.all_properties = {}
        self.required = []
        self.type = None
        self.is_subclass_of = None
        self.is_document = False
        self.operations: Dict[str, Operation] = {}

        self.required_props = []
        self.optional_props = []
        self.update(d)
        # OK, now a hack for Kubernetes:
        # Although K8s defines top-level objects that are collections
        # of other objects, and there are API calls that fetch these collection
        # objects, there are not API calls in the swagger that accept these
        # objects as input for the purposes of creation. The K8s client, nonetheless,
        # provides support for creation of these things directly from YAML (only)
        # by iterating over them in the local client and just doing repeated calls
        # to the singleton creation method. Since there's no spec'd version of this,
        # we have to detect such when we have one of these an generate a special
        # Operation ourselves that does the same iteration and calls the underlying
        # operation on another class. I'll refrain from saying what I think about
        # having to do this...
        if self.short_name.endswith('List'):
            # OK, invent an operation for these that can create a list
            contained_class_name = self.short_name.replace('List', '')
            mod = get_module_def(self.version)
            cd = mod.get_class_desc_from_full_name(contained_class_name)
            if cd is None:
                raise NotImplementedError(f"Need to make a list create for "
                                          f"{self.short_name} but can't find "
                                          f"the contained class {contained_class_name}")
            # maybe later...
            # create_op = ListCreateOperation(cd)

    def add_operation(self, op: Operation):
        self.operations[op.op_id] = op

    def has_properties(self) -> bool:
        return len(self.all_properties) > 0

    def update(self, d: dict):
        x_k8s = d.get("x-kubernetes-group-version-kind")
        if x_k8s is not None:
            x_k8s = x_k8s[0]
            self.group = x_k8s["group"]
            if self.group == "":
                self.group = "core"
            self.kind = x_k8s["kind"]
            self.version = x_k8s['version']
            self.is_document = True
        self.description = d.get("description")
        self.all_properties = d.get("properties", {})
        self.required = d.get("required", [])
        self.type = d.get('type', None)
        if self.type in types_map:
            self.is_subclass_of = types_map[self.type]

    _doc_markers = ("apiVersion", "kind")

    def adjust_special_props(self, fd):
        assert isinstance(fd, PropertyDescriptor)
        if fd.name == 'apiVersion':
            first_bit = f'{self.group}/' if self.group not in ('core', None) else ""
            fd.default_value = f'"{first_bit}{self.version}"'
        elif fd.name == 'kind':
            fd.default_value = f'"{self.kind}"'

    def process_properties(self):
        self.required_props = []
        self.optional_props = []
        if self.is_subclass_of is None:  # then there are properties
            for k, v in self.all_properties.items():
                fd = PropertyDescriptor(self, k, v)
                if fd.name in self._doc_markers:
                    self.adjust_special_props(fd)
                if k in self.required:
                    self.required_props.append(fd)
                else:
                    self.optional_props.append(fd)
            self.required_props.sort(key=lambda x: x.name)
            self.optional_props.sort(key=lambda x: x.name)

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

    def as_python_class(self, for_version: str) -> str:
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
        lines.append(f"class {self.short_name}({base}):")
        # now the docstring
        ds_parts = ['    r"""']
        ds_parts.extend(self.split_line(self.description))
        ds_parts.append("")
        ds_parts.append(f'    Full name: {self.full_name.split("/")[-1]}')
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

        code = "\n".join(lines)
        try:
            code = format_file_contents(code, fast=False, mode=FileMode())
        except NothingChanged:
            pass
        return code

    def depends_on(self, include_external=False) -> list:
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
        return [d for d in deps if d != self or d.short_name == "JSONSchemaProps"]


class ModuleDef(object):
    def __init__(self, version):
        self.version = version
        self.all_classes: Dict[str, ClassDescriptor] = {}

    def get_class_desc(self, sname: str) -> Optional[
            ClassDescriptor]:
        """
        Use a short name to find the ClassDescriptor

        :param sname: the shortname of a K8s class after processing away the swagger
            stuff
        :return: either a ClassDescriptor or None if it can't be found.
        """
        return self.all_classes.get(sname)

    def get_class_desc_from_full_name(self, fullname: str,
                                      create_if_missing: bool = True) -> Optional[
            ClassDescriptor]:
        """
        Find a class descriptor from the full swagger name of a class, create if missing

        :param fullname: full swagger name from which you can get a group and version.
            will work if you supply just a short name though.
        :param create_if_missing: if True, then an empty ClassDescriptor is made
            to serve as a placeholder for when a real one is needed later, and then all
            can share a single definition
        :return: if create_if_missing is True, then always a ClassDescriptor, but if
            False, either a ClassDescriptor or None if the name can't be found.
        """
        _, _, shortname = process_swagger_name(fullname)
        cd = self.get_class_desc(shortname)
        if cd is None and create_if_missing:
            cd = ClassDescriptor(fullname, {})
            self.save_class_desc(cd)
        return cd

    def save_class_desc(self, class_def: ClassDescriptor):
        assert isinstance(class_def, ClassDescriptor)
        self.all_classes[class_def.short_name] = class_def

    def external_versions_used(self) -> List[str]:
        ext_ver = set()
        for cd in self.all_classes.values():
            for dep in cd.depends_on(include_external=True):
                assert isinstance(dep, ClassDescriptor)
                if dep.version != self.version:
                    ext_ver.add(dep.version)
        return list(ext_ver)

    def as_python_module(self, stream=sys.stdout):
        externals = self.external_versions_used()
        other_imports = []
        if None in externals:
            other_imports.append(f'from ..{unversioned_module_name} import *')
            try:
                externals.remove(None)
            except ValueError:
                pass
        externals.sort()
        all_classes = {}
        for ext in externals:
            emod = _all_module_defs[ext]
            assert isinstance(emod, ModuleDef)
            all_classes.update(emod.all_classes)
        all_classes.update(self.all_classes)
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
        print("\n", file=stream)
        write_classes(list(all_classes.values()), self.version, stream=stream)
        output_footer(stream=stream)


def get_module_def(version) -> ModuleDef:
    md = _all_module_defs.get(version)
    if md is None:
        md = _all_module_defs[version] = ModuleDef(version)
    return md


def module_defs() -> dict:
    return dict(_all_module_defs)


class PropertyDescriptor(object):

    def __init__(self, containing_class: ClassDescriptor, name: str,
                 d: dict):
        """
        capture the information
        :param containing_class:
        :param d:
        """
        # another odd-man-out issue with the swagger spec; the only
        # property that starts with an upper case letter,
        # Port of DaemonEndpoint. Force it lower...
        if containing_class.short_name == 'DaemonEndpoint' and name == 'Port':
            name = 'port'
        name = name.replace('-', '_')
        if name in python_reserved:
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
                    group, version, short_name = process_swagger_name(ref)
                    fullname = full_swagger_name(ref)
                    mod_def = get_module_def(version)
                    item_ref = mod_def.get_class_desc(short_name)
                    if item_ref is None:
                        item_ref = ClassDescriptor(fullname, {})  # make a placeholder
                        mod_def.save_class_desc(item_ref)
                else:
                    itype = items.get("type")
                    if itype:
                        if itype == "object":
                            item_ref = "Any"
                        else:
                            item_ref = itype
                    else:
                        raise RuntimeError(f"Don't know how to process type of "
                                           f"{name} in {self.containing_class.full_name}")
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
                group, version, short_name = process_swagger_name(d["$ref"])
                fullname = full_swagger_name(d["$ref"])
                mod_def = get_module_def(version)
                ref_class = mod_def.get_class_desc(short_name)
                if ref_class is None:
                    ref_class = ClassDescriptor(fullname, {})
                    mod_def.save_class_desc(ref_class)
                self.prop_type = ref_class

    @staticmethod
    def as_required(anno: str, as_required: bool) -> str:
        return anno if as_required else f"Optional[{anno}]"

    def depends_on(self) -> Union[ClassDescriptor, NoneType]:
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
                parts.append(self.as_required(f"'{self.prop_type.short_name}'",
                                              as_required))
        elif self.container_type is list:
            if isinstance(self.item_type, ClassDescriptor):
                parts.append(self.as_required(f"List['{self.item_type.short_name}']",
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
                            f"{self.containing_class.short_name}, "
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


class OpParameter(object):
    def __init__(self, name: str, ptype: Any, description: str, required: bool):
        self.name = name
        self.ptype = ptype
        self.description = description
        self.required = required
        self.is_bodyany: bool = True if name == 'body' and ptype == 'Any' else False

    def docstring(self):
        name = camel_to_pep8(self.name)
        name = f"{name}_" if name in python_reserved else name
        line = f':param {name}: {self.description}'
        final_lines = ClassDescriptor.split_line(line, prefix="",
                                                 hanging_indent="      ",
                                                 linelen=70)
        return "\n".join(final_lines)

    def as_python(self) -> str:
        if type(self.ptype) == type:
            ptype = self.ptype.__name__
        elif isinstance(self.ptype, ClassDescriptor):
            ptype = f"'{self.ptype.short_name}'"
        else:
            ptype = self.ptype
        ptype = (ptype
                 if self.required
                 else f"Optional[{ptype}] = None")
        name = camel_to_pep8(self.name)
        name = f"{name}_" if name in python_reserved else name
        return f"{name}: {ptype}"


class OpResponse(object):
    def __init__(self, code: int, description: str, ref: Optional[str] = None):
        self.code = code
        self.description = description
        self.ref = ref

    def is_object(self) -> bool:
        return isinstance(self.ref, ClassDescriptor)


class QueryDomainOperations(object):
    """
    This object collects query operations for a single query domain

    Instances of this class organize operations for which a Hikaru object is
    not needed for input, but may result in one upon output. Given this, there
    is no Hikaru class to make these operations methods on, and hence we gather
    them together in this class. All operations in a single instance of this
    class share the same element that comes right after the version element
    in the path for the operation; so all operations with a path that looks like:

    /mumble/v1/watch/moremumble

    will be gathered in the 'watch' domain.
    """
    def __init__(self, domain):
        self.domain = domain
        self.operations: Dict[str, Operation] = {}

    def add_operation(self, op_id: str, operation: Operation):
        self.operations[op_id] = operation


class APIVersionOperations(object):
    def __init__(self, version):
        self.version = version
        # key is the input object's swagger name
        self.object_ops: Dict[str, ObjectOperations] = {}
        # key is the domain of the operation
        self.query_ops: Dict[str, QueryDomainOperations] = {}

    def add_obj_operation(self, full_k8s_name: str, op: Operation):
        obops = self.object_ops.get(full_k8s_name)
        if obops is None:
            obops = ObjectOperations(full_k8s_name)
            self.object_ops[full_k8s_name] = obops
        obops.add_operation(op.op_id, op)

    def add_query_operation(self, domain: str, op: Operation):
        qops = self.query_ops.get(domain)
        if qops is None:
            qops = QueryDomainOperations(domain)
            self.query_ops[domain] = qops
        qops.add_operation(op.op_id, op)


def get_version_ops(version: str) -> APIVersionOperations:
    vops = ops_by_version.get(version)
    if vops is None:
        vops = APIVersionOperations(version)
        ops_by_version[version] = vops
    return vops


def get_path_version(path: str) -> str:
    version = None
    parts = path.split('/')
    for part in parts:
        if part.startswith('v1') or part.startswith('v2'):
            version = part
            break
    return version


def get_path_domain(path: str):
    version = get_path_version(path)
    path_parts = path.split(f"/{version}/")
    if len(path_parts) > 1:
        parts = path_parts[1].split("/")
        domain = parts[0]
    else:
        domain = None
    return domain


def _best_guess(op: Operation) -> Optional[ClassDescriptor]:
    # look for a good class for this op based on the op name
    md = get_module_def(op.version)
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
    # first, look for just each part of the name as a class
    # only take the first match
    for part in parts:
        test_name = part.capitalize() if part != 'API' else part
        if guess is None and test_name in md.all_classes:
            guess = md.all_classes[test_name]
    # next, look for a longer name by concat'ing from the end forward, taking
    # any longer matches
    for part in parts:
        new_parts.insert(0,
                         part.capitalize() if part != 'API' else part)
        test_name = "".join(new_parts)
        if test_name in md.all_classes:
            if not guess or len(guess.short_name) < len(test_name):
                guess = md.all_classes[test_name]
    # final check: if a longer name is possible, then look for a permuation
    if not guess or len(guess.short_name) < len(''.join(new_parts)):
        # then a better guess might exist via some permutation of the name parts
        for perm in permutations(new_parts):
            test_name = "".join(perm)
            if test_name in md.all_classes:
                guess = md.all_classes[test_name]
                break
    return guess


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


def process_params_and_responses(path: str, verb: str, op_id: str,
                                 params: list, responses: dict, description: str,
                                 gvk_dict: dict,
                                 reuse_op: Operation = None) -> Operation:
    version = get_path_version(path)
    vops = get_version_ops(version)
    domain = get_path_domain(path)
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
                k8s_name = full_swagger_name(pref)
                _, sver, ptype = process_swagger_name(k8s_name)
                if version and sver != version:
                    has_mismatch = True
                mod_def = get_module_def(sver)
                ptype = mod_def.get_class_desc(ptype)  # you need cd later...
                if ptype is None:
                    raise RuntimeError(f"Couldn't find a ClassDescriptor for "
                                       f"parameter {k8s_name} in {op_id}")

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
                _, sver, ptype = process_swagger_name(ref)
                if version and sver != version:
                    has_mismatch = True
                mod_def = get_module_def(sver)
                ptype = mod_def.get_class_desc(ptype)
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
            if cd_in_params.short_name == "DeleteOptions":
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
                whose_method.short_name != guess.short_name):
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
            vops.add_query_operation(domain, new_op)
    return new_op


_dont_remove_groups = {"storage", "policy"}


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


def _search_for_method(group: str, version: str, kind: str,
                       methname: str) -> Union[NoneType,
                                               Tuple[str, str, str, str]]:
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


def _search_for_free_method(swagger_name: str) -> Optional[Tuple[str, str, str, str]]:
    result = None
    package_name = 'kubernetes.client.api'
    module_name = '.core_v1_api'
    class_name = 'CoreV1Api'
    try:
        mod = importlib.import_module(module_name, package_name)
    except ModuleNotFoundError:
        pass
    else:
        cls = getattr(mod, class_name, None)
        if cls is not None:
            k8s_name = camel_to_pep8(swagger_name)
            meth = getattr(cls, k8s_name, None)
            if meth is not None:
                result = package_name, module_name, class_name, k8s_name
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


def load_stable(swagger_file_path: str) -> str:
    f = open(swagger_file_path, 'r')
    d = json.load(f)
    for k, v in d["definitions"].items():
        group, version, name = process_swagger_name(k)
        mod_def = get_module_def(version)
        cd = mod_def.get_class_desc(name)
        if cd is None:
            cd = ClassDescriptor(k, v)
            mod_def.save_class_desc(cd)
        else:
            cd.update(v)
        cd.process_properties()

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

    for mod in _all_module_defs.values():
        assert isinstance(mod, ModuleDef)
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
                        print(f">>>Can't find the method for {cd.short_name} {op.op_id} "
                              f"{op.op_path}")

    info = d.get('info')
    rel_version = info.get("version")
    relnum = rel_version.split("-")[-1].replace(".", "_")
    release_name = f"rel_{relnum}"
    return release_name


python_reserved = {"except", "continue", "from", "not", "or"}


types_map = {"boolean": "bool",
             "integer": "int",
             "string": "str",
             "float": "float",
             "number": "float"}


unversioned_module_name = "unversioned"


objop_param_mismatches: Dict[str, Operation] = {}


response_mismatches: Dict[str, Operation] = {}


_all_module_defs = {}


model_package = "hikaru/model"


ops_by_version: Dict[str, APIVersionOperations] = {}


# version, opid
written_methods: Set[Tuple[str, str]] = set()


def reset_all():
    objop_param_mismatches.clear()
    response_mismatches.clear()
    _all_module_defs.clear()
    ops_by_version.clear()
    written_methods.clear()


_release_in_process = None


def check_for_stragglers():
    total = 0
    print("LOOKING FOR STRAGGLERS")
    for k, vops in ops_by_version.items():
        for domain, qops in vops.query_ops.items():
            for op in qops.operations.values():
                if (op.version, op.op_id) not in written_methods:
                    print(f"version {k}, dom {domain}, verb {op.verb}, opid {op.op_id},"
                          f" path {op.op_path}")
                    total += 1
    print(f"END LOOKING FOR STRAGGLERS; found {total}")


def build_it(swagger_file: str, main_rel: str):
    """
    Initiate the swagger-file-driven model package build

    :param swagger_file: string; path to the swagger file to process
    :param main_rel: the name of a release to treat as default; if this swagger
        file is that release, then make it the default release for Hikaru
    """
    global _release_in_process
    reset_all()
    relname = load_stable(swagger_file)
    _release_in_process = relname
    path = prep_model_root(model_package)
    relpath = path / relname
    prep_rel_package(str(relpath))
    write_modules(str(relpath))
    if main_rel == relname:
        # this is the main release; make the root package default to it
        make_root_init(model_package, main_rel)
    # check_for_stragglers()
    _release_in_process = None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <main-rel-name> <swagger-json-file>+")
        sys.exit(1)
    main_rel = sys.argv[1]
    for swagger_file in sys.argv[2:]:
        print(f">>>Processing {swagger_file}")
        build_it(swagger_file, main_rel)
    sys.exit(0)
