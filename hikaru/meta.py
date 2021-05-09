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
The meta module contains all the support to reflectively process objects

This module provides the main runtime support for Hikaru. It defines the base
class from which all Kubernetes model version classes are derived. The base
class provides all of the machinery for working with the both Python and YAML:
it can do the YAML parsing, the Python generation, and the Python runtime
object management.
"""
from ast import literal_eval
from enum import Enum
from inspect import getmodule
from typing import Union, List, Dict, Any, Type, ForwardRef, get_type_hints
from dataclasses import fields, dataclass, is_dataclass, asdict, InitVar
from inspect import signature, Parameter
from collections import defaultdict, namedtuple
from hikaru.naming import camel_to_pep8

try:
    from typing import get_args, get_origin
except ImportError:
    def get_args(tp):
        return tp.__args__ if hasattr(tp, "__args__") else ()

    def get_origin(tp):
        return tp.__origin__ if hasattr(tp, "__origin__") else None

NoneType = type(None)


_not_there = object()


CatalogEntry = namedtuple('CatalogEntry', ['cls', 'attrname', 'path'])

TypeWarning = namedtuple('TypeWarning', ['cls', 'attrname', 'path', 'warning'])


class DiffType (Enum):
    ADDED = 0
    REMOVED = 1
    VALUE_CHANGED = 2
    TYPE_CHANGED = 3
    LIST_LENGTH_CHANGED = 4
    INCOMPATIBLE_DIFF = 5


@dataclass
class DiffDetail:
    diff_type: DiffType
    cls: Type
    formatted_path: str
    path: List[str]
    report: str
    value: Any = None
    other_value: Any = None


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

    @classmethod
    def _get_hints(cls) -> dict:
        mro = cls.mro()
        mro.reverse()
        hints = {}
        globs = vars(getmodule(cls))
        for c in mro:
            if is_dataclass(c):
                hints.update(get_type_hints(c, globs))
        return hints

    def _capture_catalog(self, catalog_depth_first=False):
        hints = self._get_hints()
        for f in fields(self):
            ftype = hints[f.name]
            initial_type = get_origin(ftype)
            if initial_type is Union:
                assignment_type = get_args(ftype)[0]
            else:
                assignment_type = ftype
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
                    if catalog_depth_first:
                        obj._capture_catalog(catalog_depth_first=catalog_depth_first)
                    self._merge_catalog_of(obj, f.name)
            else:
                origin = get_origin(assignment_type)
                if origin in (list, List):
                    item_type = get_args(assignment_type)[0]
                    if is_dataclass(item_type) and issubclass(item_type, HikaruBase):
                        for i, item in enumerate(obj):
                            if catalog_depth_first:
                                item._capture_catalog(catalog_depth_first=
                                                      catalog_depth_first)
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
        self._capture_catalog(catalog_depth_first=True)
        return self

    def to_dict(self) -> dict:
        """
        Provides a simple transfer to a dictionary representation of self

        This method does a simple transcription of self into a dict using
        hikaru.get_clean_dict().

        :return: A dict representation of self. Only keys with values are in
            the resulting dict
        """
        from hikaru.generate import get_clean_dict
        return get_clean_dict(self)

    def dup(self):
        """
        Create a deep copy of self

        :return: identical instance of self plus any contained instances
        """
        klass = self.__class__
        copy = klass.get_empty_instance()
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
        :raises TypeError: if 'name' is not a string, or if 'following' is not
            a string or list
        :raises ValueError: if 'following' is a list and one of the elements is not
            a str or an int
        """
        if not isinstance(name, str):
            raise TypeError("name must be a str")
        if following is not None and not isinstance(following, (str, list, tuple)):
            raise TypeError("following must be a string or list")
        result = list()
        field_list = self._field_catalog.get(name)
        if field_list is not None:
            result.extend(field_list)

        if following:
            signposts = []  # it isn't possible to remain this
            if isinstance(following, str):
                signposts = following.split('.')
            elif isinstance(following, (list, tuple)):
                signposts = following
            candidates = result
            result = []
            for ce in candidates:
                assert isinstance(ce, CatalogEntry)
                start = 0
                for sp in signposts:
                    try:
                        sp = int(sp)
                    except (ValueError, TypeError) as e:
                        if not isinstance(sp, str):
                            raise ValueError(str(e))
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
        to use the 'path' attribute of a returned CatalogEntry from find_by_name()

        :param path: A list of strings or ints.
        :return: Whatever value is found at the end of the path; this could be
            another HikaruBase instance or a plain Python object (str, bool, dict,
            etc).

        :raises RuntimeError: raised if None is found anywhere along the path except
            at the last element
        :raises IndexError: raised if a path index value is beyond the end of a
            list-valued attribute
        :raises ValueError: if an index for a list can't be turned into an int
        :raises AttributeError: raised if any attribute on the path isn't an
            attribute of the previous object on the path
        """
        obj = self
        for p in path:
            if isinstance(obj, (list, tuple)):
                try:
                    idx_p = int(p)
                except ValueError:
                    raise ValueError(f"Path element isn't an int for list"
                                     f" attribute; attr={p}")
                else:
                    try:
                        obj = obj[idx_p]
                    except IndexError:
                        raise IndexError(f"Index {idx_p} is beyond the end of the list")
                    else:
                        if obj is None:
                            raise RuntimeError(f"Path {path} leads to None at {p}")
            else:
                try:
                    obj = getattr(obj, p, _not_there)
                except TypeError as _:
                    raise TypeError(f'{p} is an illegal attribute')
                else:
                    if obj is _not_there:
                        raise AttributeError(f"Path {path} leads to an unknown attr at {p}")
        return obj

    @classmethod
    def from_yaml(cls, yaml, translate: bool = False):
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
        :param translate: optional bool, default False. If True, then all attributes
            that are fetched from the dict are first run through camel_to_pep8 to
            use the underscore-embedded versions of the attribute names.
        :return: an instance of a subclass of HikaruBase
        """
        inst = cls.get_empty_instance()
        inst.process(yaml, translate=translate)
        return inst

    @classmethod
    def get_empty_instance(cls):
        """
        Returns a properly initialized instance with Nones and empty collections

        :return: and instance of 'cls' with all scalar attrs set to None and
            all collection attrs set to an appropriate empty collection
        """
        kw_args = {}
        sig = signature(cls.__init__)
        init_var_hints = {k for k, v in get_type_hints(cls).items()
                          if isinstance(v, InitVar) or v is InitVar}
        hints = cls._get_hints()
        if cls.__name__ == "CrossVersionObjectReference":
            _ = 1
        for p in sig.parameters.values():
            if p.name in ('self', 'client') or p.name in init_var_hints:
                continue
            # skip these either of these next two since they are supplied by default,
            # but only if they have default values
            if p.name in ('apiVersion', 'kind'):
                if issubclass(cls, HikaruDocumentBase):
                    continue
            f = hints[p.name]
            initial_type = f
            origin = get_origin(initial_type)
            if origin is Union:
                type_args = get_args(f)
                initial_type = type_args[0]
            if ((type(initial_type) == type and issubclass(initial_type, (int, str,
                                                                          bool,
                                                                          float))) or
                    (is_dataclass(initial_type) and
                     issubclass(initial_type, HikaruBase)) or
                    initial_type is object):
                # this is a type that can default to None
                kw_args[p.name] = None
            else:
                origin = get_origin(initial_type)
                if origin in (list, List):
                    kw_args[p.name] = []
                elif origin in (dict, Dict):
                    kw_args[p.name] = {}
                else:
                    raise NotImplementedError(f"Internal error! Unknown type"
                                              f" {initial_type}"
                                              f" for parameter {p.name} in"
                                              f" {cls.__name__}. Please file a"
                                              f" bug report.")  # pragma: no cover
        new_inst = cls(**kw_args)
        return new_inst

    @classmethod
    def _diff(cls, attr: Any, other_attr: Any, containing_cls: Type, attr_path: List[str],
              formatted_attr_path: str) -> List[DiffDetail]:
        # Recursively compares attr to other_attr and returns list of differences and where they are
        # we use this classmethod instead of diff() because this is recursively called on non-hikaru classes
        # like int and float
        #
        # attr: any object, not necessarily a HikaruBase subclass.
        # other_attr: any object, not necessarily a HikaruBase subclass.
        # containing_cls: the HikaruBase subclass that contains attr and other_attr
        # attr_path: a list of the attribute names in the path to attr and other_attr
        # formatted_attr_path: a string version of attr_path like 'Pod.spec.containers[0]'
        # returns a list of DiffDetail namedtuples that describe all the discovered
        # differences. If the list is empty then the two are equal.
        if attr is not None and other_attr is None:
            return [DiffDetail(DiffType.ADDED,
                               containing_cls,
                               formatted_attr_path,
                               attr_path,
                               f"Key added: self.{formatted_attr_path} is {attr} but does not exist in other",
                               attr,
                               None)]
        elif attr is None and other_attr is not None:
            return [DiffDetail(DiffType.REMOVED,
                               containing_cls,
                               formatted_attr_path,
                               attr_path,
                               f"Key removed: self.{formatted_attr_path} does not exist but in other it is is"
                               f" {other_attr}",
                               None,
                               other_attr)]
        elif type(attr) != type(other_attr):
            return [DiffDetail(DiffType.TYPE_CHANGED,
                               containing_cls,
                               formatted_attr_path,
                               attr_path,
                               f"Type mismatch: self.{formatted_attr_path} is a {type(attr)} but other's is a"
                               f" {type(other_attr)}",
                               attr,
                               other_attr)]
        elif issubclass(type(attr), (str, int, float, bool, NoneType)):
            if attr == other_attr:
                return []
            return [DiffDetail(DiffType.VALUE_CHANGED,
                               containing_cls,
                               formatted_attr_path,
                               attr_path,
                               f"Value mismatch: self.{formatted_attr_path} is {attr} but other's is {other_attr}",
                               attr,
                               other_attr)]
        elif isinstance(attr, HikaruBase):
            diffs = []
            for f in fields(attr):
                sub_attr = getattr(attr, f.name)
                other_sub_attr = getattr(other_attr, f.name)
                diffs.extend(cls._diff(sub_attr, other_sub_attr, attr.__class__,
                                       attr_path + [f.name], f"{formatted_attr_path}.{f.name}"))
            return diffs
        elif isinstance(attr, dict):
            diffs = []
            all_keys = set(list(attr.keys()) + list(other_attr.keys()))
            for key in all_keys:
                diffs.extend(cls._diff(attr.get(key), other_attr.get(key), containing_cls,
                                       attr_path + [key], f"{formatted_attr_path}['{key}']"))
            return diffs
        elif isinstance(attr, list):
            if len(attr) != len(other_attr):
                return [DiffDetail(DiffType.LIST_LENGTH_CHANGED, containing_cls, formatted_attr_path, attr_path,
                                   f"Length mismatch: list self.{formatted_attr_path} has {len(attr)}"
                                   " elements, but other has {len(other_attr)}",
                                   attr,
                                   other_attr)]
            else:
                diffs = []
                for i, self_element in enumerate(attr):
                    diffs.extend(cls._diff(self_element, other_attr[i], containing_cls, attr_path + [i],
                                           f"{formatted_attr_path}[{i}]"))
                return diffs
        else:
            raise NotImplementedError(f"Internal error! Don't know how to compare"
                                      f" attribute {attr} with {other_attr}."
                                      f" Please file a bug "
                                      f"report")  # pragma: no cover

    def diff(self, other) -> List[DiffDetail]:
        """
        Compares self to other and returns list of differences and where they are

        The ``diff()`` method goes field-by-field between two objects looking for
        differences. Whenever any are found, a DiffDetail object is added to
        the returned list. The diff is carried out recursively across any containers
        or inner objects; the path to any differences found is recorded from
        self to any nested difference.

        Note that ``diff()`` looks at all fields in the objects, not just ones
        that have been set.

        :param other: some kind of HikaruBase subclass. If not the same class as
            self, then a single DiffDetail object is returned describing this
            and the diff stops.
        :return: a list of DiffDetail objects that describe all the discovered
            differences. If the list is empty then the two are equal.
        """
        if self.__class__ != other.__class__:
            return [DiffDetail(DiffType.INCOMPATIBLE_DIFF, self.__class__, "", [],
                               f'Incompatible: self is a {self.__class__.__name__} while'
                               f'other is a {other.__class__.__name__}')]
        return self._diff(self, other, self.__class__, [], self.__class__.__name__)

    def get_type_warnings(self) -> List[TypeWarning]:
        """
        Compares attribute type annotation to actual data; issues warning on mismatches.

        This method compares the type of each attribute based on the type annotation
        against the type of the actual data in the attribute and generates a warning
        object whenever a mismatch is discovered. The search for mismatches starts
        at ``self`` and recursively searches any HikaruBase objects contained in
        ``self``.

        Note that if ``get_type_warnings()`` finds an attribute that is a
        HikaruBase object of the incorrect type, ``get_type_warnings()``
        will NOT inspect the incorrect object's attributes for type correctness.
        The object itself will be flagged as incorrect, but checking will not
        continue inside the incorrect object. Other checks will still proceed.

        :return: a list of TypeWarning namedtuple objects. The fields should be
            interpreted as follows:

            - cls: the class object that contains the attribute that has a type mismatch
            - attrname: the name of the attribute that has the type mismatch
            - path: a list of strings that indicates from ``self`` how to reach the attr
            - warning: a string that contains the text of the warning.

            Note that the first three fields are similar to those from CatalogEntry,
            however their interpretation is slightly different.

            A return of an empty list indicates that there were no TypeWarnings.
            This DOES NOT indicate that there aren't errors in usage; for example, if
            and object may contain one of three alternative objects, this method doesn't
            check if that constraint holds true; it only checks that the types of any
            contained objects are correct.
        """
        warnings: List[TypeWarning] = list()
        hints = self._get_hints()
        for f in fields(self):
            is_required = True
            ftype = hints[f.name]
            initial_type = ftype
            origin = get_origin(initial_type)
            if origin is Union:  # this is optional; grab what's inside
                type_args = get_args(ftype)
                if NoneType in type_args:
                    is_required = False
                    initial_type = type_args[0]
                else:
                    raise NotImplementedError("Internal error! We aren't expecting this "
                                              "case. Please file a "
                                              "bug report.")  # pragma: no cover
            # current value of initial_type:
            # ok, now we have either a scaler (int, bool, str, etc),
            # a subclass of HikaruBase,
            # or a container (Dict, List),
            # or plain ol' object for older releases
            # now we want the attr's real type (scalars, dict, list, HikaruBase)
            # and if list, we want the contained type
            contained_type = None
            attr_type = initial_type
            origin = get_origin(initial_type)
            if origin is list:
                attr_type = list
                contained_type = get_args(initial_type)[0]
            elif origin is dict:
                attr_type = dict
            elif (type(initial_type) not in (type, str) and
                  not isinstance(initial_type, ForwardRef) and
                  (not issubclass(initial_type, (str, int,  float,
                                                  bool, HikaruBase)) and
                  initial_type is not object)):
                raise NotImplementedError(f"Internal error! Some other kind of type:"
                                          f" {initial_type}, attr={f.name}"
                                          f" in class {self.__class__.__name__}."
                                          f" Please file a "
                                          f"bug report.")  # pragma: no cover
            attrval = getattr(self, f.name)
            if attrval is None:
                if issubclass(attr_type, (str, int, float,
                                          bool, HikaruBase)):
                    if is_required:
                        warnings.append(TypeWarning(self.__class__,
                                                    f.name,
                                                    [f.name],
                                                    f"Attribute {f.name} is None but"
                                                    f" should have been "
                                                    f"{initial_type.__name__}"))
                elif attr_type is list:
                    warnings.append(TypeWarning(self.__class__, f.name,
                                                [f.name],
                                                f"Attribute {f.name} is None but"
                                                f" should be at least an empty list"))
                elif attr_type is dict:
                    warnings.append(TypeWarning(self.__class__, f.name,
                                                [f.name],
                                                f"Attribute {f.name} is None but"
                                                f" should be at least an empty dict"))
            elif (attr_type != type(attrval) and
                  not issubclass(attr_type, type(attrval)) and
                  attr_type is not object):
                warnings.append(TypeWarning(self.__class__, f.name,
                                            [f.name],
                                            f"Was expecting type {attr_type.__name__},"
                                            f" got {type(attrval).__name__}"))
            elif attr_type is list:
                if is_required and len(attrval) == 0:
                    warnings.append(TypeWarning(self.__class__, f.name,
                                                [f.name],
                                                f"List {f.name} has no"
                                                f" elements but is required"))
                for i, o in enumerate(attrval):
                    if contained_type != type(o):
                        warnings.append(TypeWarning(self.__class__, f.name,
                                                    [f.name, i],
                                                    f"Element {i} of list"
                                                    f" {f.name} is of type"
                                                    f" {type(o).__name__},"
                                                    f" not {contained_type.__name__}"))
                    elif issubclass(contained_type, HikaruBase):
                        # extract any warnings and amend the path
                        inner_warnings = o.get_type_warnings()
                        warnings.extend([TypeWarning(w.cls, w.attrname,
                                                     [f.name, i] + w.path,
                                                     w.warning)
                                         for w in inner_warnings])
            # FIXME; should we be looking at contents of a dict??
            elif isinstance(attrval, HikaruBase):
                inner_warnings = attrval.get_type_warnings()
                warnings.extend([TypeWarning(w.cls, w.attrname,
                                             [f.name] + w.path,
                                             w.warning)
                                 for w in inner_warnings])
        return warnings

    def process(self, yaml, translate: bool = False) -> None:
        """
        extract self's data items from the supplied yaml object.

        :param yaml: a populated dict-like object that contains keys and values
            that  represent the constructs of a Kubernetes YAML file. Supplied by
            pyyaml or ruamel.yaml. Results in the construction of a set of Hikaru
            class instances that mirror the structure and contents of the YAML,
            as well as the population of the type/field catalogs. To ensure proper
            catalogues, invoke repopulate_catalog() after modifying data or doing
            multiple sequential parse() calls.
        :param translate: optional bool, default False. If True, then all attributes
            that are fetched from the dict are first run through camel_to_pep8 to
            use the underscore-embedded versions of the attribute names.

        NOTE: it is possible to call parse again, but this will result in
            additional fields added to the existing fields, not a replacement
            of what was previously there. Always parse with an empty instance
            of the object.

        :raises TypeError: in these if the YAML is missing a required property.
        """

        # OK, there are some cases where embedded objects are actually dicts
        # encoded as a string. This isn't clear where it happens, but what we'll
        # do is the following: if the type of the 'yaml' parameter is an str, then
        # we'll eval it to hopefully get a dict, and raise a useful message if
        # we don't
        if type(yaml) == str:
            new = literal_eval(yaml)
            if type(new) != dict:
                raise RuntimeError(f"We can't process this input; type {type(yaml)}, "
                                   f"value = {yaml}")  # pragma: no cover
            yaml = new
        hints = self._get_hints()
        for f in fields(self.__class__):
            k8s_name = f.name.strip("_")
            k8s_name = camel_to_pep8(k8s_name) if translate else k8s_name
            is_required = True
            ftype = hints[f.name]
            initial_type = ftype
            origin = get_origin(initial_type)
            if origin is Union:  # this is optional; grab what's inside
                type_args = get_args(ftype)
                if NoneType in type_args:
                    is_required = False
                    initial_type = type_args[0]
                else:
                    raise NotImplementedError("Internal error! We shouldn't see this "
                                              "case! Please file a "
                                              "bug report.")  # pragma: no cover
            # ok, we've peeled away a Union left by Optional
            # let's see what we're really working with
            val = yaml.get(k8s_name, None)
            if val is None and is_required:
                raise TypeError(f"{self.__class__.__name__} is missing {k8s_name}"
                                f" (originally {f.name})")
            if val is None:
                continue
            if (type(initial_type) == type and issubclass(initial_type, (int, str,
                                                                         bool, float))
                    or initial_type == object):
                # take as is
                setattr(self, f.name, val)
            elif is_dataclass(initial_type) and issubclass(initial_type, HikaruBase):
                obj = initial_type.get_empty_instance()
                obj.process(val, translate=translate)
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
                        l = []
                        for o in val:
                            obj = target_type.get_empty_instance()
                            obj.process(o, translate=translate)
                            l.append(obj)
                        setattr(self, f.name, l)
                    else:
                        raise NotImplementedError(f"Internal error! Processing"
                                                  f" {self.__class__.__name__}.{f.name};"
                                                  f" can only do list of scalars and"
                                                  f" k8s objs. Please file a"
                                                  f" bug report.")  # pragma: no cover
                elif origin in (dict, Dict):
                    d = {k: v for k, v in val.items()}
                    setattr(self, f.name, d)
                else:
                    raise NotImplementedError(f"Internal error! Unknown type inside of"
                                              f" list: {initial_type}. Please file a bug"
                                              f" report.")  # pragma: no cover
        self._capture_catalog()

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
        if len(all_fields) != len([k for k in sig.parameters if k != 'client']):
            raise NotImplementedError(f"Internal error! Uneven number of params for"
                                      f" {self.__class__.__name__}. Please file"
                                      f" a bug report.")  # pragma: no cover
        # open the call to the 'constructor'
        code.append(f'{self.__class__.__name__}(')
        # now process all attributes of the class
        parameters = []
        for f, p in zip(all_fields, tuple(sig.parameters.values())):
            one_param = []
            keep_param = True
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
                if inner_code:
                    one_param.append(inner_code)
                # I don't think this can happen
                # else:
                #     keep_param = False
            elif isinstance(val, list):
                if len(val) > 0 or is_required:
                    one_param.append("[")
                    list_values = []
                    for item in val:
                        if isinstance(item, HikaruBase):
                            inner_code = item.as_python_source()
                            list_values.append(inner_code)
                        elif isinstance(item, str):
                            list_values.append(f"'{item}'")
                        else:
                            list_values.append(str(val))
                    if list_values:
                        one_param.append(",".join(list_values))
                    one_param.append("]")
                else:
                    keep_param = False
            elif isinstance(val, str):
                one_param.append(f"'{val}'")
            elif isinstance(val, dict):
                if len(val) > 0 or is_required:
                    one_param.append("{")
                    dict_pairs = []
                    for k, v in val.items():
                        the_val = f"'{v}'" if isinstance(v, str) else v
                        dict_pairs.append(f"'{k}': {the_val}")
                    if dict_pairs:
                        one_param.append(",".join(dict_pairs))
                    one_param.append("}")
                else:
                    keep_param = False
            else:
                one_param.append(str(val))
            if keep_param:
                parameters.append("".join(one_param))
        if parameters:
            code.append(",".join(parameters))
        code.append(")")
        return " ".join(code)


@dataclass
class HikaruDocumentBase(HikaruBase):
    _version = 'UNKNOWN'

    # noinspection PyDataclass
    def __post_init__(self, client: Any = None):
        super(HikaruDocumentBase, self).__post_init__()
        self.client = client

    def set_client(self, client: Any):
        """
        Set the k8s ApiClient on an already created Hikaru instance

        Sets the client that will be used if this object is involved in
        calls to K8s.

        :param client: instance of kubernetes.client.api_client.ApiClient
        """
        self.client = client
