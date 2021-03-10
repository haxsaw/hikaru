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
from typing import List

from autopep8 import fix_code
from ruamel.yaml import YAML

from hikaru.model import *
from hikaru.meta import num_positional, HikaruBase
from hikaru.naming import process_api_version
from hikaru.version_kind import version_kind_map


def get_python_source(obj: HikaruBase, assign_to: str = None) -> str:
    """
    returns formatted Python source that will re-create the supplied object

    :param obj: an instance of HikaruBase
    :param assign_to: if supplied, must be a legal Python identifier name,
        as the returned expression will be assigned to that variable.
    :return: fully formatted Python code that will re-create the supplied
        object
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


def load_full_yaml(path=None, stream=None, yaml=None) -> List[HikaruBase]:
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
    for doc in docs:
        # api_version = doc.get('apiVersion').split('/')[-1]
        _, api_version = process_api_version(doc.get('apiVersion', ""))
        kind = doc.get('kind', "")
        klass = version_kind_map.get((api_version, kind))
        if klass is None:
            raise RuntimeError(f"No model class for {(api_version, kind)}")
        np = num_positional(klass.__init__) - 1
        inst = klass(*([None] * np), **{})
        inst.parse(doc)
        objs.append(inst)

    return objs
