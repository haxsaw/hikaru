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
from dataclasses import asdict
from io import StringIO
from typing import List, TextIO

from autopep8 import fix_code
from ruamel.yaml import YAML

from hikaru.model import *
from hikaru.meta import num_positional, HikaruBase
from hikaru.naming import process_api_version
from hikaru.version_kind import version_kind_map


def get_python_source(obj: HikaruBase, assign_to: str = None) -> str:
    """
    returns PEP8-formatted Python source that will re-create the supplied object

    NOTE: this function can be slow, as formatting the code to be PEP8 compliant
    can take some time for complex code.

    :param obj: an instance of HikaruBase
    :param assign_to: if supplied, must be a legal Python identifier name,
        as the returned expression will be assigned to that as a variable.
    :return: fully PEP8 formatted Python source code that will re-create the
        supplied object
    """
    code = obj.as_python_source(assign_to=assign_to)
    result = fix_code(code, options={"max_line_length": 90,
                                     "experimental": 1})
    return result


def _clean_dict(d: dict) -> dict:
    # returns a new dict missing any keys in d that have None for its value
    clean = {}
    for k, v in d.items():
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
    turns an instance of a HikaruBase into a dict with values of None

    :param obj: some api_version_group of subclass of HikaruBase
    :return: a dict representation of the obj instance, but if any value
        in the dict was originally None, that key:value is removed from the
        returned dict, hence it is a minimal representation
    """
    initial_dict = asdict(obj)
    clean_dict = _clean_dict(initial_dict)
    return clean_dict


def get_yaml(obj: HikaruBase) -> str:
    """
    Creates a YAML representation of a HikaruBase model

    :param obj: instance of some HikaruBase subclass
    :return: big ol' string of YAML that represents the model
    """
    d: dict = get_clean_dict(obj)
    yaml = YAML()
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
    """
    d = get_clean_dict(obj)
    s = json.dumps(d)
    return s


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
    """
    if path is None and stream is None and yaml is None:
        raise RuntimeError("One of path, stream, or yaml must be specified")
    objs = []
    if path:
        f = open(path, "r")
    if stream:
        f = stream
    if yaml:
        to_parse = yaml
    else:
        to_parse = f.read()
    parser = YAML()
    docs = list(parser.load_all(to_parse))
    return docs


def load_full_yaml(path: str = None, stream: TextIO = None,
                   yaml: str = None) -> List[HikaruBase]:
    """
    Parse/process the indicated Kubernetes yaml file and return a list of Hikaru objects

    This function takes one of the supplied sources of Kubernetes YAML, parses it
    into separate YAML documents, and then processes those into a list of Hikaru
    objects, one per document.

    NOTE: this function only works on complete Kubernetes message documents, and relies
    on the presence of both 'apiVersion' and 'kind' being in the top-level object.
    Other Kubernetes objects represented in ruamel.yaml can be parsed using either the
    appropriate class's from_yaml() class method, or from an instance's process() method,
    both of which can only accept a ruamel.yaml instance to process.

    Only one of path, stream or yaml should be supplied. If yaml is supplied in addition
    to path or stream, only the yaml parameter is used. If stream and path are supplied,
    then only stream is used.

    :param path: string; path to a yaml file that will be opened, read, and processed
    :param stream: return of the open() function, or any file-like (TextIO) object
    :param yaml: string; the actual YAML to process
    :return: list of HikaruBase subclasses, one for each document in the YAML file
    """
    docs = get_processors(path=path, stream=stream, yaml=yaml)
    objs = []
    for doc in docs:
        _, api_version = process_api_version(doc.get('apiVersion', ""))
        kind = doc.get('kind', "")
        klass = version_kind_map.get((api_version, kind))
        inst = klass.from_yaml(doc)
        objs.append(inst)

    return objs
