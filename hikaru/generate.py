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
import json
import keyword
from dataclasses import asdict
from io import StringIO
from typing import List, TextIO, Optional, Tuple

from ruamel.yaml import YAML

from hikaru.meta import HikaruBase, HikaruDocumentBase
from hikaru.naming import process_api_version, dprefix, get_default_release
from hikaru.version_kind import get_version_kind_class


def get_python_source(obj: HikaruBase, assign_to: str = None,
                      style: Optional[str] = None) -> str:
    """
    returns Python source that will re-create the supplied object

    NOTE: this function can be slow, as formatting the code to be PEP8 compliant
    can take some time for complex code.

    :param obj: an instance of HikaruBase
    :param assign_to: if supplied, must be a legal Python identifier name,
        as the returned expression will be assigned to that as a variable.
    :param style: optional string, default None, may also be one of 'black'
        or 'autopep8'. This argument indicates what code formatter, if any,
        to apply. The default value of None says not to format the code; this
        will return syntactically correct Python, but it will be an eyesore.
        However, if you just plan to dynamically execute it how it looks
        may be of no consequence. The other two formatters return PEP8-compliant
        formatted Python based on different formatting 'opinions'. The 'black'
        style produces somewhat more vertically spread-out code that is a bit
        clearer to read. The 'autopep8' formatter is a bit more aggressive in
        putting more arguments on a single line, so it's a bit more compact,
        but can be a little harder to see what's going on. The 'black' formatter
        is a bit faster than 'autopep8', and no formatting is the fastest.
    :return: Python source code that will re-create the supplied object
    :raises RuntimeError: if an unrecognized style is supplied
    """
    from autopep8 import fix_code
    from black import format_str, Mode, NothingChanged

    if style not in ('black', 'autopep8', None):
        raise RuntimeError(f'Unrecognized style: {style}')
    code = obj.as_python_source(assign_to=assign_to)
    if style is None:
        result = code
    elif style == "autopep8":
        result = fix_code(code, options={"max_line_length": 88,
                                         "experimental": 1})
    else:  # then it's black
        try:
            result = format_str(code, mode=Mode())
        except NothingChanged:
            result = code
    return result


def _clean_dict(d: dict) -> dict:
    # returns a new dict missing any keys in d that have None for its value
    clean = {}
    for k, v in d.items():
        if k.startswith(dprefix):
            k = f'${k.replace(dprefix, "")}'
        if k.endswith("_") and keyword.iskeyword(k[:-1]):
            k = k[:-1]
        if v is None:
            continue
        if isinstance(v, (list, dict)) and not v:  # this is an empty container
            continue
        if isinstance(v, dict):
            clean[k] = _clean_dict(v)
        elif isinstance(v, list):
            new_list = list()
            for i in v:
                if isinstance(i, dict):
                    new_list.append(_clean_dict(i))
                else:
                    new_list.append(i)
            clean[k] = new_list
        else:
            clean[k] = v
    return clean


def get_clean_dict(obj: HikaruBase) -> dict:
    """
    Turns an instance of a HikaruBase into a dict without values of None

    This function returns a Python dict object that represents the hierarchy
    of objects starting at ``obj`` and recusing into any nested objects.
    The returned dict **does not** include any key/value pairs where the value
    of the key is None or empty.

    If you wish to instead have a dict with all key/value pairs even when
    there is no useful value then you should use the dataclasses module's
    ``asdict()`` function on obj.

    :param obj: some api_version_group of subclass of HikaruBase
    :return: a dict representation of the obj instance, but if any value
        in the dict was originally None, that key:value is removed from the
        returned dict, hence it is a minimal representation
    :raises TypeError: if the supplied obj is not a HikaruBase (dataclass),
        or if obj is not an instance of a HikaruBase subclass
    """
    if not isinstance(obj, HikaruBase):
        raise TypeError("obj must be a kind of HikaruBase")
    initial_dict = asdict(obj)
    clean_dict = _clean_dict(initial_dict)
    return clean_dict


def get_yaml(obj: HikaruBase) -> str:
    """
    Creates a YAML representation of a HikaruBase model

    :param obj: instance of some HikaruBase subclass
    :return: big ol' string of YAML that represents the model
    :raises TypeError: if the supplied obj is not an instance of a HikaruBase
        subclass
    """
    if not isinstance(obj, HikaruBase):
        raise TypeError("obj must be a kind of HikaruBase")
    d: dict = get_clean_dict(obj)
    yaml = YAML(typ="safe")
    yaml.indent(offset=2, sequence=4)
    sio = StringIO()
    yaml.dump(d, sio)
    return "\n".join(["---", sio.getvalue()])


def get_json(obj: HikaruBase) -> str:
    """
    Creates a JSON representation of a HikaruBase model

    NOTE: current there is no way to go from JSON back to YAML or Python. This
        function is must useful for storing a model's representation in a
        document database.

    :param obj: instance of a HikaruBase model
    :return: string containing JSON that represents the information in the model
    :raises TypeError: if obj is not an instance of a HikaruBase subclass
    """
    if not isinstance(obj, HikaruBase):
        raise TypeError("obj must be an instance of a HikaruBase subclass")
    d = get_clean_dict(obj)
    s = json.dumps(d)
    return s


def from_json(json_data: str, cls: Optional[type] = None) -> HikaruBase:
    """
    Create Hikaru objects from a string of JSON from ``get_json()``

    This function can re-create a hierachy of HikaruBase objects from a string
    of JSON previous returned by a call to ``get_json()``.

    If the JSON was created from a full Kubernetes document object, such as Pod
    or Deployment, only the json_data argument is required.

    If the JSON was created from an arbitrary HikaruBase subclass, this function
    needs to know what kind of thing it is loading; in this case, you must provide
    the ``cls`` parameter so that Hikaru knows what kind of instance you wish
    to create.

    :param json_data: string; the value previously returned by ``get_json()`` on
        some HikaruBase subclass instance.
    :param cls: optional; a HikaruBase subclass (*not* the string name
        of the class). This should match the kind of object that was dumped into
        the dict.
    :return: an instance of a HikaruBase subclass with all attributes and contained
        objects recreated.
    """
    d = json.loads(json_data)
    return from_dict(d, cls=cls)


def from_dict(adict: dict, cls: Optional[type] = None,
              translate: bool = False) -> HikaruBase:
    """
    Create Hikaru objects from a ``get_clean_dict()`` dict

    This function can re-create a hierarchy of HikaruBase objects from a
    dict that was created with ``get_clean_dict()``.

    If the dict was created from a full Kubernetes document object, such as Pod
    or Deployment, only the dict argument is required.

    If the dict was created from an arbitrary HikaruBase subclass, this function
    needs to know what kind of thing it is loading; in this case, you must provide
    the ``cls`` parameter so that Hikaru knows what kind of instance you wish
    to create.

    :param adict: a Python dict that was previously created with ``get_clean_dict()``
    :param cls: optional; a HikaruBase subclass (*not* the string name
        of the class). This should match the kind of object that was dumped into
        the dict.
    :param translate: optional bool, default False. If True, then all attributes
        that are fetched from the dict are first run through camel_to_pep8 to
        use the underscore-embedded versions of the attribute names.
    :return: an instance of a HikaruBase subclass with all attributes and contained
        objects recreated.
    :raises RuntimeError: if no cls was specified and Hikaru was unable to determine
        what class to make from the data
    :raises TypeError: if adict isn't actually a dict, or if cls isn't a subclass
        (not an instance) of HikaruBase
    """
    if not isinstance(adict, dict):
        raise TypeError("The 'adict' parameter is not a dict")
    if cls is not None and not issubclass(cls, HikaruBase):
        raise TypeError("cls is not a subclass of HikaruBase")
    parser = YAML(typ="safe")
    sio = StringIO()
    parser.dump(adict, stream=sio)

    if cls is None:
        docs = load_full_yaml(yaml=sio.getvalue(), translate=translate)
        doc = docs[0]
    else:
        parser = YAML(typ="safe")
        sio.seek(0)
        yaml = parser.load(sio)
        doc = cls.from_yaml(yaml, translate=translate)
    return doc


def get_processors(path: str = None, stream: TextIO = None,
                   yaml: str = None) -> List[dict]:
    """
    Takes a path, stream, or string for a YAML file and returns a list of processors.

    This function can accept a number of different parameters that can provide
    the contents of a YAML file; from this, a YAML parser is created and a processed
    list of YAML dicts is created and returned. The main use case for this function is to
    provide input to the from_yaml() method of a HikaruBase subclass.

    Only one of path, stream or yaml should be supplied. If yaml is supplied in addition
    to path or stream, only the yaml parameter is used. If stream and path are supplied,
    then only stream is used.

    :param path: string; path to a Kubernetes YAML file containing one or more docs
    :param stream: file-like object; opened on a Kubernetes YAML file containing one
        or more documents
    :param yaml: string; contains Kubernetes YAML, one or more documents
    :return: List of dicts (or dictionary-like objects) that contain the parsed-
        out content of the input YAML files.
    :raises RuntimeError: if none of path, stream or yaml are provided.
    """
    if path is None and stream is None and yaml is None:
        raise RuntimeError("One of path, stream, or yaml must be specified")
    if path:
        f = open(path, "r")
    if stream:
        f = stream
    if yaml:
        to_parse = yaml
    else:
        to_parse = f.read()
    parser = YAML(typ="safe")
    docs = list(parser.load_all(to_parse))
    return docs


def load_full_yaml(path: str = None, stream: TextIO = None,
                   yaml: str = None,
                   release: Optional[str] = None,
                   translate: bool = False) -> List[HikaruDocumentBase]:
    """
    Parse/process the indicated Kubernetes yaml file and return a list of Hikaru objects

    This function takes one of the supplied sources of Kubernetes YAML, parses it
    into separate YAML documents, and then processes those into a list of Hikaru
    objects, one per document.

    **NOTE**: this function only works on complete Kubernetes message documents,
    and relies on the presence of both 'apiVersion' and 'kind' being in the top-level
    object. Other Kubernetes objects represented in ruamel.yaml can be parsed using either
    the appropriate class's from_yaml() class method, or from an instance's process()
    method, both of which can only accept a ruamel.yaml instance to process.

    Only one of path, stream or yaml should be supplied. If yaml is supplied in addition
    to path or stream, only the yaml parameter is used. If stream and path are supplied,
    then only stream is used.

    :param path: string; path to a yaml file that will be opened, read, and processed
    :param stream: return of the open() function, or any file-like (TextIO) object
    :param yaml: string; the actual YAML to process
    :param release: optional string; if supplied, indicates which release to load classes
        from. Must be one of the subpackage of hikaru.model, such as rel_1_16 or
        rel_unversioned. If unspecified, the release specified from
        hikaru.naming.set_default_release() is used; if that hasn't been called,
        then the default from when hikaru was built will be used.
        NOTE: rel_unversioned is for pre-release models from the github repo of the K8s
        Python client; use appropriately.
    :param translate: option bool, default False. Generally not needed by users of
        Hikaru, it instructs whether or not camel case identifiers should be turned
        into PEP8 identifiers (this only happens when True). If you're doing some
        odd tests and getting complaints that PEP8-style attributes are missing,
        you might want to set this to True.
    :return: list of HikaruDocumentBase subclasses, one for each document in the YAML file
    :raises RuntimeError: if one of the documents in the input YAML has an unrecognized
        api_version/kind pair; Hikaru can't determine what class to instantiate, or
        if none of the YAML input sources have been specified.
    """
    docs = get_processors(path=path, stream=stream, yaml=yaml)
    objs = []
    for i, doc in enumerate(docs):
        initial_api_version = doc.get('apiVersion', '--NOPE--')
        if initial_api_version == '--NOPE--':
            initial_api_version = doc.get('api_version', '')
        _, api_version = process_api_version(initial_api_version)
        kind = doc.get('kind', "")
        api_version, kind = _vk_mapper(initial_api_version
                                       if api_version != initial_api_version
                                       else api_version,
                                       kind, release)
        klass = get_version_kind_class(api_version, kind, release)
        if klass is None:
            raise RuntimeError(f"Doc number {i} in the supplied YAML has an"
                               f" unrecognized api_version ({api_version}) and"
                               f" kind ({kind}) pair; can't determine the class"
                               f" to instantiate")
        inst = klass.from_yaml(doc, translate=translate)
        objs.append(inst)

    return objs

#
# this helps get around problems when classes from different groups
# have the same name
_deprecation_helper = {
    'rel_1_23': {
        ('v1', 'Event'): ('v1', 'Event_core'),
    },
    'rel_1_24': {
        ('v1', 'Event'): ('v1', 'Event_core'),
    },
    'rel_1_25': {
        ('v1', 'Event'): ('v1', 'Event_core'),
    },
    'rel_1_26': {
        ('v1', 'Event'): ('v1', 'Event_core'),
    },
}


def _vk_mapper(api_version: str, kind: str, release: str=None) -> Tuple[str, str]:
    """
    May map a version/kind pair to different values to cover some of the deprecation cases

    Not really meant of users at large to access
    :param api_version: string; an api version string such as 'v1'
    :param kind: string; value of 'kind' to determine what sort of object to
        make
    :param release: optional string; if supplied, indicates which release to load classes
        from. Must be one of the subpackage of hikaru.model, such as rel_1_16 or
        rel_unversioned. If unspecified, the release specified from
        hikaru.naming.set_default_release() is used; if that hasn't been called,
        then the default from when hikaru was built will be used.
    :return: 2 tuple of strings: (version, kind) to be used in subsequent lookups
    """
    use_release = release if release is not None else get_default_release()
    mdict = _deprecation_helper.get(use_release)
    if mdict is None:
        return api_version, kind
    api_version, kind = mdict.get((api_version, kind), (api_version, kind))
    return api_version, kind
