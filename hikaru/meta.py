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
from typing import Union, List, Dict
from dataclasses import fields, dataclass, is_dataclass
from inspect import signature, Parameter
from collections import defaultdict, namedtuple

try:
    from typing import get_args, get_origin
except ImportError:
    def get_args(tp):
        return tp.__args__ if hasattr(tp, "__args__") else ()

    def get_origin(tp):
        return tp.__origin__ if hasattr(tp, "__origin__") else None

NoneType = type(None)


def num_positional(acallable) -> int:
    sig = signature(acallable)
    num_pos = len([p for p in sig.parameters.values()
                  if p.kind in (Parameter.POSITIONAL_ONLY,
                                Parameter.POSITIONAL_OR_KEYWORD)])
    return num_pos


CatalogEntry = namedtuple('CatalogEntry', ['cls', 'attrname', 'path'])


@dataclass
class HikaruBase(object):
    def __post_init__(self):
        self._type_catalog = defaultdict(list)
        self._field_catalog = defaultdict(list)
        self._capture_catalog()

    @staticmethod
    def _process_other_catalog(src_cat, dst_cat, idx, name):
        for k, ce_list in src_cat.items():
            for ce in ce_list:
                assert isinstance(ce, CatalogEntry)
                new_ce = CatalogEntry(ce.cls, ce.attrname, ce.path[:])
                if idx is not None:
                    new_ce.path.insert(0, idx)
                new_ce.path.insert(0, name)
                dst_cat[k].append(new_ce)

    def _merge_catalog_of(self, other, name: str, idx: int = None):
        # other: a HikaruBase subclass instance that self owns
        # name: a string that is the attribute name for this instance
        # idx: optional integer index within name if name is a list
        #
        # catalog entries are of the form:
        # (cls, attrname, path-list)
        # _type_catalog is keyed by the cls
        # _field_catalog is keyed by the attribute name
        # first, add an entry for this item
        if idx is None:
            ce = CatalogEntry(other.__class__, name, [name])
        else:
            ce = CatalogEntry(other.__class__, name, [name, idx])
        self._type_catalog[other.__class__].append(ce)
        self._field_catalog[name].append(ce)

        # now merge in the catalog of other if it has one
        if isinstance(other, HikaruBase):
            assert isinstance(other, HikaruBase)
            self._process_other_catalog(other._type_catalog, self._type_catalog, idx, name)
            self._process_other_catalog(other._field_catalog, self._field_catalog,
                                        idx, name)

    def _capture_catalog(self):
        for f in fields(self):
            initial_type = get_origin(f.type)
            if initial_type is Union:
                assignment_type = get_args(f.type)[0]
            else:
                assignment_type = f.type
            del initial_type
            # now we have the type without a Union
            obj = getattr(self, f.name, None)
            if obj is None:  # nothing to catalog
                continue
            if (type(assignment_type) == type and
                    issubclass(assignment_type, (int, str, bool, float, dict))):
                ce = CatalogEntry(assignment_type, f.name, [f.name])
                self._field_catalog[f.name].append(ce)
                self._type_catalog[assignment_type].append(ce)
            elif is_dataclass(assignment_type) and issubclass(assignment_type,
                                                              HikaruBase):
                if obj:
                    self._merge_catalog_of(obj, f.name)
            else:
                origin = get_origin(assignment_type)
                if origin in (list, List):
                    item_type = get_args(assignment_type)[0]
                    if is_dataclass(item_type) and issubclass(item_type, HikaruBase):
                        for i, item in enumerate(obj):
                            self._merge_catalog_of(item, f.name, i)
                    elif (type(item_type) == type and
                            issubclass(item_type, (int, str, bool, float, dict))):
                        ce = CatalogEntry(item_type, f.name, [f.name])
                        self._field_catalog[f.name].append(ce)
                        self._type_catalog[item_type].append(ce)

    def _clear_catalog(self):
        # clear the catalogs from this object down into any contained
        # catalog-holding objects
        self._field_catalog.clear()
        self._type_catalog.clear()
        for f in fields(self):
            a = getattr(self, f.name)
            if a is None:
                continue
            if is_dataclass(a) and isinstance(a, HikaruBase):
                a._clear_catalog()
            elif type(a) == list and len(a) > 0:
                for i in a:
                    if is_dataclass(i) and isinstance(i, HikaruBase):
                        i._clear_catalog()

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        else:
            flist = fields(self)
            for f in flist:
                left = getattr(self, f.name)
                right = getattr(other, f.name)
                if left.__class__ != right.__class__:
                    return False
                elif isinstance(left, HikaruBase):
                    result = left.__eq__(right)
                    if not result:
                        return False
                elif left != right:
                    # this covers list, dict and the scalars
                    # tuples aren't interchangeable with lists!
                    return False
        return True

    def repopulate_catalog(self):
        """
        re-creates the catalog for this object (and any contained objects) from scratch

        If a HikaruBase model gets changed after it was populated from YAML or
        by Python source code, it may be desirable to re-create the catalogs
        to inspect the new model. This method causes the old catalogs to be
        dropped and new catalogs to be loaded with the data currently in the
        model.
        """
        self._clear_catalog()
        self._capture_catalog()
        return self

    def dup(self):
        """
        Create a deep copy of self
        :return: identical instance of self plus any contained instances
        """
        klass = self.__class__
        np = num_positional(klass.__init__) - 1
        copy = klass(*([None] * np), **{})
        for f in fields(self):
            a = getattr(self, f.name)
            if isinstance(a, HikaruBase):
                setattr(copy, f.name, a.dup())
            elif type(a) == dict:
                setattr(copy, f.name, dict(a))
            elif type(a) == list:
                new_list = []
                setattr(copy, f.name, new_list)
                for i in a:
                    if isinstance(i, HikaruBase):
                        new_list.append(i.dup())
                    elif type(i) == dict:
                        new_list.append(dict(i))
                    else:
                        new_list.append(i)
            else:
                setattr(copy, f.name, a)
        return copy

    def find_by_name(self, name: str, following: Union[str, List] = None) -> \
            List[CatalogEntry]:
        """
        Returns a list of catalog entries for the named field wherever they occur
        in the model.

        This method returns a list of CatalogEntry instances that match the criteria
        of the input parameters. At very least, the list will contain all entries
        for an attribute named 'name'.

        The list of returned items can be further reduced by supplying a value for the
        'following' argument, which names one or more attributes that must come before
        the named attribute in order for the entry to be included in the returned list.
        The 'following' argument may be specified as a '.' separated string of
        attribute names or as a list of strings. These describe the prerequisite
        attributes that must be on the path to the named attribute, but not necessarily
        consecutively. By specifying 'following' you can essentially establish a
        context in which you find the named attribute. The attributes named in
        'following' will be considered in order, but they don't have to be directly
        sequential in the model.

        :param name: string containing a name for an attribute somewhere in the model,
            the search for with starts at 'self'. This must be a legal Python identifier,
            not an integer.
        :param following: Sequence of strings or a single string with elements
            separated by '.'. These elements must appear somewhere along the path to
            'name' in order, but not necessarily consecutively. These will serve as a
            way to specify 'signposts' along the way to the desired field. Each element
            is either an attribute name or an integer for lists to identify which
            element in the list must be seen before 'name'. For example, say you had a
            model of a Pod and wanted all the attributes called 'name', but only within
            a container's volumeMounts objects. You can get these with the following
            invocation::

                p.find_by_name('name',
                               following="containers.volumeMounts")

            Or suppose you wanted 'exec' from from anywhere in the lifecycle object
            of of the first container in a pod::

                p.find_by_name('exec',
                               following=['containers', 0, 'lifecycle'])

            or::

                p.find_by_name('exec',
                               following="containers.0.lifecycle")

            Or suppose you wanted to find all the httpHeaders 'name' from in the
            lifecycle in any container in a pod::

                p.find_by_name('name',
                               following="containers.lifecycle.httpGet")

            In the last example, 'lifecycle' is an direct attribute of a single
            container, but 'httpGet' is several objects beneath the lifecycle.
        :return: list of CatalogEntry objects that match the query criteria.
        """
        result = list()
        field_list = self._field_catalog.get(name)
        if field_list is not None:
            result.extend(field_list)

        if following:
            if isinstance(following, str):
                signposts = following.split('.')
            elif isinstance(following, (list, tuple)):
                signposts = following
            else:
                raise TypeError("following is an unsupported type")
            candidates = result
            result = []
            for ce in candidates:
                assert isinstance(ce, CatalogEntry)
                start = 0
                for sp in signposts:
                    try:
                        sp = int(sp)
                    except ValueError:
                        pass
                    try:
                        start = ce.path.index(sp, start)
                    except ValueError:
                        break
                else:
                    result.append(ce)

        return result

    def object_at_path(self, path: list):
        """
        returns the value named by path starting at self

        Returns an object or base value by navigating the supplied path starting
        at 'self'. The elements of path are either strings representing attribute
        names or else integers in the case where an attribute name reaches a list
        (the int is used as an index into the list). Generally, the thing to do is
        to use the 'path' value of a returned CatalogEntry from find_by_name()

        :param path: A list of strings or ints.
        :return: Whatever value is found at the end of the path; this could be
            another HikaruBase instance or a plain Python object (str, bool, dict,
            etc).

        :raises RuntimeError: since there should only be actual values along the
            path, if None is ever encountered a RuntimeError exception is raised.
        """
        obj = self
        for p in path:
            try:
                p = int(p)
                obj = obj[p]
                if obj is None:
                    raise RuntimeError(f"Path {path} leads to None at {p}")
            except ValueError:
                obj = getattr(obj, p, None)
                if obj is None:
                    raise RuntimeError(f"Path {path} leads to None at {p}")
        return obj

    @classmethod
    def from_yaml(cls, yaml):
        """
        Create an instance of this HikaruBase subclass from the provided yaml.

        This factory method creates a new instance of the class upon which it is
        invoked and fills the instance with data from supplied yaml object. It is
        a short-cut to creating an empty instance yourself and then invoking
        process(yaml) on that instance (this method hides the details of making
        an empty instance).

        This method can fill an instance with suitable YAML object, whether a
        full document or a fragment of one, as long as the type of the YAML
        object being processed and the subclass of HikaruBase agree. If a fragment
        of a object that would otherwise be part of a larger object, the fragment
        should not have the same indentation as it would as part of the larger
        document, but instead should be fully "outdented" to the left as if it
        was the standalone document itself.

        :param yaml: a ruamel.yaml YAML instance
        :return: an instance of a subclass of HikaruBase
        """
        np = num_positional(cls.__init__) - 1
        inst = cls(*([None] * np), **{})
        inst.process(yaml)
        return inst

    def process(self, yaml) -> None:
        """
        extract self's data items from the supplied yaml object.

        :param yaml: a populated dict-like object that contains keys and values
            that  represent the constructs of a Kubernetes YAML file. Supplied by
            pyyaml or ruamel.yaml. Results in the construction of a set of Hikaru
            class instances that mirror the structure and contents of the YAML,
            as well as the population of the type/field catalogs. To ensure proper
            catalogues, invoke repopulate_catalog() after modifying data or doing
            multiple sequential parse() calls.

        NOTE: it is possible to call parse again, but this will result in
            additional fields added to the existing fields, not a replacement
            of what was previously there. Always parse with an empty instance
            of the object.
        """

        for f in fields(self.__class__):
            k8s_name = f.name.strip("_")
            is_required = True
            initial_type = f.type
            origin = get_origin(initial_type)
            if origin is Union:  # this is optional; grab what's inside
                type_args = get_args(f.type)
                if NoneType in type_args:
                    is_required = False
                    initial_type = type_args[0]
                else:
                    raise NotImplementedError("we aren't ready for this case")
            # ok, we've peeled away a Union left by Optional
            # let's see what we're really working with
            val = yaml.get(k8s_name, None)
            if val is None and is_required:
                raise TypeError(f"{self.__class__.__name__} is missing {k8s_name}")
            if val is None:
                continue
            if type(initial_type) == type and issubclass(initial_type, (int, str,
                                                                        bool, float)):
                # take as is
                setattr(self, f.name, val)
            elif is_dataclass(initial_type) and issubclass(initial_type, HikaruBase):
                np = num_positional(initial_type.__init__) - 1
                obj = initial_type(*([None] * np), **{})
                obj.process(val)
                setattr(self, f.name, obj)
            else:
                origin = get_origin(initial_type)
                if origin in (list, List):
                    target_type = get_args(initial_type)[0]
                    if type(target_type) == type and issubclass(target_type, (int, str,
                                                                              bool,
                                                                              float)):
                        l = [i for i in val]
                        setattr(self, f.name, l)
                    elif is_dataclass(target_type) and issubclass(target_type,
                                                                  HikaruBase):
                        np = num_positional(target_type.__init__) - 1
                        l = []
                        for o in val:
                            obj = target_type(*([None] * np), **{})
                            obj.process(o)
                            l.append(obj)
                        setattr(self, f.name, l)
                    else:
                        raise TypeError("Can only do list of scalars and k8s objs")
                elif origin in (dict, Dict):
                    d = {k: v for k, v in val.items()}
                    setattr(self, f.name, d)
                else:
                    raise ImportError(f"Unknown type inside of list: {initial_type}")
        self._capture_catalog()

    def __repr__(self):
        return self.as_python_source()

    def as_python_source(self, assign_to: str = None) -> str:
        """
        generate a string of Python code that will re-create the object and all
        contained objects

        :param assign_to: string. If supplied, must be a legal Python variable
            name. The generated code will be assigned to this variable in the
            returned string.
        :return: single string of formatted python code that if run will re-
            create self.

        NOTE: the returned code string will not include any
            necessary imports that may be needed to allow the code to actually execute;
            the caller is expected to supply that boilerplate.
        """
        code = []
        if assign_to is not None:
            code.append(f'{assign_to} = ')
        all_fields = fields(self)
        sig = signature(self.__init__)
        if len(all_fields) != len(sig.parameters):  # ignore self
            raise NotImplementedError(f"uneven number of params for "
                                      f"{self.__class__.__name__}")
        # open the call to the 'constructor'
        code.append(f'{self.__class__.__name__}(')
        # now process all attributes of the class
        parameters = []
        for f, p in zip(all_fields, tuple(sig.parameters.values())):
            one_param = []
            is_required = get_origin(f.type) is not Union
            val = getattr(self, f.name)
            if val is None and not is_required:  # should only be for optional args
                continue
            if p.kind in (Parameter.KEYWORD_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
                one_param.append(f'{f.name}=')
            if isinstance(val, HikaruBase):
                # then this attr is a nested object; get its code and set the
                # value of the attribute to it
                inner_code = val.as_python_source()
                one_param.append(inner_code)
            elif isinstance(val, list):
                one_param.append("[")
                list_values = []
                for item in val:
                    if isinstance(item, HikaruBase):
                        inner_code = item.as_python_source()
                        list_values.append(inner_code)
                    elif isinstance(item, str):
                        list_values.append(f"'{item}'")
                    elif isinstance(item, dict):
                        list_values.append("{")
                        dict_pairs = []
                        for k, v in item.items():
                            dict_pairs.append(f"'{k}': '{v}'")
                        list_values.append(",".join(dict_pairs))
                        list_values.append("}")
                    else:
                        list_values.append(str(val))
                one_param.append(",".join(list_values))
                one_param.append("]")
            elif isinstance(val, str):
                one_param.append(f"'{val}'")
            elif isinstance(val, dict):
                one_param.append("{")
                dict_pairs = []
                for k, v in val.items():
                    dict_pairs.append(f"'{k}': '{v}'")
                one_param.append(",".join(dict_pairs))
                one_param.append("}")
            else:
                one_param.append(str(val))
            parameters.append("".join(one_param))
        code.append(",".join(parameters))
        code.append(")")
        return " ".join(code)


@dataclass
class HikaruDocumentBase(HikaruBase):
    _version = 'UNKNOWN'
