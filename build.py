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
from itertools import chain
from pathlib import Path
import sys
from typing import List, Dict, Optional, Union, Tuple
import json
import networkx
from hikaru.naming import (process_swagger_name, full_swagger_name,
                           make_swagger_name, dprefix, camel_to_pep8)
from hikaru.meta import HikaruBase, HikaruDocumentBase


python_reserved = {"except", "continue", "from", "not", "or"}


types_map = {"boolean": "bool",
             "integer": "int",
             "string": "str",
             "float": "float",
             "number": "float"}


NoneType = type(None)


unversioned_module_name = "unversioned"


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
except ImportError:
    pass"""


def prep_package(directory: str):
    """
    This function empties the directory named 'directory', creating it if needed
    :param directory: string; name of an empty directory to create. Creates it
        if needed, and removes any existing content if it's already there.
    """
    path = Path(directory)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if not path.is_dir():
            path.unlink()
            path.mkdir(parents=True)
    # once here, the directory exists and is a directory; clean it out
    _clean_directory(str(path))
    init = path / "__init__.py"
    init.touch()
    f = init.open('w')
    print(_module_docstring, file=f)
    print(_package_init_code, file=f)
    print(file=f)
    output_footer(stream=f)


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

This module is automatically generated using the hikaru.build program that turns
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
    print("from typing import List, Dict, Optional, Any", file=stream)
    print("from dataclasses import dataclass, field", file=stream)
    if other_imports is not None:
        for line in other_imports:
            print(line, file=stream)
    print(file=stream)
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


def build_digraph(all_classes: dict) -> networkx.DiGraph:
    dg = networkx.DiGraph()
    for cd in all_classes.values():
        assert isinstance(cd, ClassDescriptor)
        deps = cd.depends_on(include_external=True)
        dg.add_node(cd)
        for c in deps:
            dg.add_edge(cd, c)

    return dg


def write_classes(class_list, stream=sys.stdout):
    for dc in class_list:
        print(dc.as_python_class(), file=stream)


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
            mod_names.append(md.version)
            mod = pkg / f'{md.version}.py'
            f = mod.open('w')
            md.as_python_module(stream=f)
            f.close()

    # finally, capture the names of all the version modules in version module
    versions = pkg / 'versions.py'
    f = versions.open('w')
    print(f"versions = {str(mod_names)}", file=f)
    f.close()


class ClassDescriptor(object):
    def __init__(self, key, d):
        self.full_name = full_swagger_name(key)
        group, version, name = process_swagger_name(self.full_name)
        self.short_name = name
        self.group = group
        self.version = version
        self.description = "None"
        self.all_properties = {}
        self.required = []
        self.type = None
        self.is_subclass_of = None
        self.is_document = False
        self.alternate_base = None

        self.required_props = []
        self.optional_props = []
        self.update(d)

    def has_alternate_base(self) -> bool:
        return self.alternate_base is not None

    def update(self, d: dict):
        self.description = d.get("description")
        self.all_properties = d.get("properties", {})
        self.required = d.get("required", [])
        self.type = d.get('type', None)
        if self.type in types_map:
            self.is_subclass_of = types_map[self.type]

    _doc_markers = ("apiVersion", "kind")

    def process_properties(self):
        self.required_props = []
        self.optional_props = []
        seen_markers = set(self._doc_markers)
        if self.is_subclass_of is None:  # then there are properties
            for k, v in self.all_properties.items():
                if k in seen_markers:
                    seen_markers.remove(k)
                    if not seen_markers:
                        self.is_document = True
                fd = PropertyDescriptor(self, k, v)
                if k in self.required:
                    self.required_props.append(fd)
                else:
                    self.optional_props.append(fd)
            self.required_props.sort(key=lambda x: x.name)
            self.optional_props.sort(key=lambda x: x.name)
        make_alternate_base = False
        deps = self.depends_on()
        for dep in deps:
            assert isinstance(dep, ClassDescriptor)
            if self.ref_to_self(dep):
                # this is then recursive
                make_alternate_base = True
        if make_alternate_base:
            self.alternate_base = self.construct_alternate_base()

    def ref_to_self(self, other) -> bool:
        """
        returns True if other names the same group/version/short_name
        :param other: another ClassDescriptor
        :return: True if they refer to the same group/version/short_name
        """
        assert isinstance(other, ClassDescriptor)
        return (self.group == other.group and
                self.version == other.version and
                self.short_name == other.short_name)

    def construct_alternate_base(self):
        base_name = f"{self.short_name}HikaruBase"
        swagger_name = make_swagger_name(self.group, self.version, base_name)
        alt_base = ClassDescriptor(swagger_name, {})
        alt_base.process_properties()  # ensure all state is where it belongs
        for prop in list(self.required_props):
            assert isinstance(prop, PropertyDescriptor)
            dep = prop.depends_on()
            if dep is None or not self.ref_to_self(dep):
                # this isn't self-referential and can go into the new base
                alt_base.required_props.append(prop)
                self.required_props.remove(prop)
                self.required.remove(prop.name)
                alt_base.required.append(prop.name)
            else:
                prop.change_dep(alt_base)
        for prop in list(self.optional_props):
            assert isinstance(prop, PropertyDescriptor)
            dep = prop.depends_on()
            if dep is None or not self.ref_to_self(dep):
                # this isn't self-referential and can go into the new base
                alt_base.optional_props.append(prop)
                self.optional_props.remove(prop)
            else:
                prop.change_dep(alt_base)
        alt_base.type = "object"
        alt_base.full_name = self.full_name
        return alt_base

    @staticmethod
    def split_line(line, prefix: str = "   ", hanging_indent: str = "") -> List[str]:
        parts = []
        if line is not None:
            words = line.split()
            current_line = [prefix]
            for w in words:
                if sum(len(s) for s in current_line) + len(current_line) + len(w) > 90:
                    parts.append(" ".join(current_line))
                    current_line = [prefix]
                    if hanging_indent:
                        current_line.append(hanging_indent)
                current_line.append(w)
            else:
                if current_line:
                    parts.append(" ".join(current_line))
        return parts

    def as_python_class(self) -> str:
        lines = list()
        # start of class statement
        if self.is_subclass_of is not None:
            base = self.is_subclass_of
        else:
            # then it is to be a dataclass
            lines.append("@dataclass")
            if self.alternate_base:
                base = self.alternate_base.short_name
            else:
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
        lines.append("")
        lines.append("")

        return "\n".join(lines)

    def depends_on(self, include_external=False) -> list:
        r = [p.depends_on() for p in self.required_props]
        deps = [p for p in r
                if p is not None]
        o = [p.depends_on() for p in self.optional_props]
        deps.extend(p for p in o
                    if p is not None and (True
                                          if include_external else
                                          self.version == p.version))
        if self.alternate_base is not None:
            deps.append(self.alternate_base)
        return deps


class ModuleDef(object):
    def __init__(self, version):
        self.version = version
        self.all_classes = {}

    def get_class_desc(self, sname: str) -> Optional[ClassDescriptor]:
        return self.all_classes.get(sname)

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
            other_imports.append(f'from .{unversioned_module_name} import *')
            externals.remove(None)
        externals.sort()
        all_classes = {}
        for ext in externals:
            emod = _all_module_defs[ext]
            assert isinstance(emod, ModuleDef)
            all_classes.update(emod.all_classes)
        all_classes.update(self.all_classes)
        g = build_digraph(all_classes)
        output_boilerplate(stream=stream, other_imports=other_imports)
        traversal = list(reversed(list(networkx.topological_sort(g))))
        if not traversal:
            traversal = list(self.all_classes.values())
        write_classes(traversal, stream=stream)
        output_footer(stream=stream)


_all_module_defs = {}


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
        name = name.replace('-', '_')
        if name in python_reserved:
            python_name = f'{name}_'
        elif name.startswith("$"):
            python_name = f'{dprefix}{name.strip("$")}'
        else:
            python_name = name
        self.name = python_name
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
                    print(f"No $ref for property:{name}, class"
                          f":{self.containing_class.full_name}")
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
                parts.append(self.as_required(self.prop_type.short_name,
                                              as_required))
        elif self.container_type is list:
            if isinstance(self.item_type, ClassDescriptor):
                parts.append(self.as_required(f"List[{self.item_type.short_name}]",
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
                parts.append(" = None")
        return "".join(parts)


model_package = "hikaru/model"


class OpParameter(object):
    def __init__(self, name: str, ptype: str, description: str, required: bool):
        self.name = name
        self.ptype = ptype
        self.description = description
        self.required = required

    def as_python(self) -> str:
        if type(self.ptype) == type:
            ptype = self.ptype.__name__
        else:
            ptype = self.ptype
        ptype = (ptype
                 if self.required
                 else f"Optional[{ptype}] = None")
        return f"{camel_to_pep8(self.name)}: {ptype}"


class OpResponse(object):
    def __init__(self, code: str, description: str, ref: Optional[str] = None):
        self.code = code
        self.description = description
        self.ref = ref


class Operation(object):
    """
    A single operation from paths; associated with a verb such as 'get' or 'post'

    The same path may have multiple operations with different verbs, and hence
    may also involve different input params/outputs
    """
    def __init__(self, verb: str, op_path: str, op_id: str):
        self.verb = verb
        self.op_path = op_path
        self.op_id = op_id
        self.parameters: List[OpParameter] = list()
        self.self_param: Optional[OpParameter] = None
        self.returns = {}

    def add_parameter(self, name: str, ptype: str, description: str,
                      required: bool = False):
        ptype = types_map.get(ptype, ptype)
        if self.self_param is None:
            self.self_param = OpParameter(name, ptype, description, required)
        else:
            self.parameters.append(OpParameter(name, ptype, description, required))

    def add_return(self, code: str, ptype: Optional[str], description: str):
        ptype = types_map.get(ptype, ptype)
        self.returns[code] = OpResponse(code, description, ref=ptype)

    def as_python_method(self) -> str:
        version = get_path_version(self.op_path).replace('v', 'V')
        stmt_name = self.op_id.replace(version, '')
        parts = [f"def {stmt_name}("]
        required = [p for p in self.parameters if p.required]
        optional = [p for p in self.parameters if not p.required]
        params = ["self"]
        params.extend([p.as_python()
                       for p in chain(required, optional)])
        parts.append(", ".join(params))
        parts.append("):")
        return "".join(parts)


class ObjectOperations(object):
    """
    This object captures all of the operations that a doc is input for
    """
    def __init__(self, full_k8s_name: str):
        self.full_k8s_name = full_k8s_name
        self.operations: Dict[str, Operation] = {}

    def add_operation(self, op_id: str, operation: Operation):
        self.operations[op_id] = operation


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


ops_by_version: Dict[str, APIVersionOperations] = {}


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


# @TEMPORARY
objop_param_mismatches: Dict[str, Operation] = {}


# @TEMPORARY
response_mismatches: Dict[str, Operation] = {}


def process_params_and_responses(path: str, verb: str, op_id: str,
                                 params: list, responses: dict):
    version = get_path_version(path)
    vops = get_version_ops(version)
    domain = get_path_domain(path)
    new_op = Operation(verb, path, op_id)
    k8s_name = None  # used as a flag that an object is an input param
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
                    # print(f"Param ver mismatch on op {new_op.op_id}"
                    #       f" than the path: {path},"
                    #       f" {verb}, {name}, pathver={version}, pver={sver}")
                    has_mismatch = True  # @TEMPORARY
                    # FIXME: probably need to do something more here
            else:
                ptype = schema.get("type")
                if not ptype:
                    raise RuntimeError(f"Can't determine type of param '{name}' "
                                       f"in path {path}, verb {verb}")
                elif ptype == "object":
                    ptype = "Any"
        else:
            raise RuntimeError(f"Don't know what to do with param"
                               f" {path}.{verb}.{name}")
        new_op.add_parameter(name, ptype, description, required)
        # @TEMPORARY
        if has_mismatch:
            objop_param_mismatches[f"{name}:{new_op.op_id}"] = new_op
            _ = 1

    for code, response in responses.items():
        has_mismatch = False
        description = response.get('description', '')
        if 'schema' in response:
            if '$ref' in response['schema']:
                ref = full_swagger_name(response['schema']['$ref'])
                _, sver, ptype = process_swagger_name(ref)
                if version and sver != version:
                    # print(f"Got a return with different version"
                    #       f" than the path: {path},"
                    #       f" {verb}, {code}, pathver={version}, rver={sver}")
                    has_mismatch = True
            elif 'type' in response['schema']:
                ptype = response['schema']['type']
                ptype = types_map.get(ptype, ptype)
            else:
                raise RuntimeError(f"Don't know how to deal with this"
                                   f" schema: {response['schema']}")
        else:
            ptype = None
        new_op.add_return(code, description, ptype)
        if has_mismatch:
            response_mismatches[f"{code}:{new_op.op_id}"] = new_op

    if k8s_name is not None:
        vops.add_obj_operation(k8s_name, new_op)
    else:
        vops.add_query_operation(domain, new_op)


def load_stable(swagger_file_path: str) -> NoneType:
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
        if cd.has_alternate_base():
            mod_def.save_class_desc(cd.alternate_base)

    for k, v in d["paths"].items():
        last_verb = None
        last_opid = None
        for verb, details in v.items():
            if verb == "parameters" and type(details) == list:
                process_params_and_responses(k, last_verb, last_opid, details,
                                             {})
                continue
            op_id = details["operationId"]
            process_params_and_responses(k, verb, op_id,
                                         details.get("parameters", []),
                                         details.get("responses", {}))
            last_verb = verb
            last_opid = op_id


def analyze_obj_mismatches():
    matches: Dict[str, Tuple[str, str, Operation]] = {}
    print("\n")
    for pname, op in objop_param_mismatches.items():
        version = get_path_version(op.op_path)
        for altver in ['v1alpha1', 'v1beta1', 'v1beta2', 'v1', 'v2beta1']:
            if altver == version:
                continue
            altpath = op.op_path.replace(version, altver)
            vops = get_version_ops(altver)
            altop = vops.object_ops.get(altpath)
            if altop:
                matches[pname] = (version, altver, op)
                break
        else:
            print(f"No other version for '{pname}' in "
                  f"{op.op_path}:{op.verb}")

    print("\nOBJECT MATCHES:")
    for k, (ver, altver, op) in matches.items():
        print(f"{k}: {ver}, {altver} {op.op_id}")


def analyze_response_mismatches():
    matches: Dict[str, Tuple[str, str, Operation]] = {}
    print("\n")
    for key, op in response_mismatches.items():
        version = get_path_version(op.op_path)
        domain = get_path_domain(op.op_path)
        for altver in ['v1alpha1', 'v1beta1', 'v1beta2', 'v1', 'v2beta1']:
            if altver == version:
                continue
            altpath = op.op_path.replace(version, altver)
            vops = get_version_ops(altver)
            altdomain = vops.query_ops.get(domain)
            if altdomain is None:
                print(f"NO DOMAIN {domain} in {altver}")
                continue
            altop = altdomain.operations.get(op.op_id)
            if altop:
                matches[key] = (version, altver, op)
        else:
            print(f"No other version for {key} in "
                  f"{op.op_path}:{op.verb}")
    print("\nQUERY MATCHES")
    for k, (ver, altver, op) in matches.items():
        print(f"{k}: {ver}, {altver} {op.op_id}")


def build_it(swagger_file: str):
    """
    Initiate the swagger-file-driven model package build

    :param swagger_file: string; path to the swagger file to process
    """
    load_stable(swagger_file)
    # v1ops = get_version_ops("v1")
    # for key, objops in v1ops.object_ops.items():
    #     print(f"class {key}")
    #     for k, op in objops.operations.items():
    #         print(f"\t{k} {op.as_python_method()}")
    # analyze_obj_mismatches()
    # analyze_response_mismatches()
    prep_package(model_package)
    write_modules(model_package)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <path-to-swagger-json-file>")
        sys.exit(1)
    build_it(sys.argv[1])
    sys.exit(0)
