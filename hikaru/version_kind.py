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
import importlib
from typing import Dict, Optional
from hikaru.meta import HikaruDocumentBase
# try:
#     from hikaru.model.versions import versions
# except ImportError:
#     versions = []

_version_kind_class_cache: Dict[str, Dict[str, HikaruDocumentBase]] = {}


def get_version_kind_class(version: str, kind: str) -> Optional[type]:
    """
    Return a class for a subclasses of HikaruDocumentBase for a specific K8s version

    :param version: string; name of the version in which to look for the object
    :param kind: string; value of the 'kind' parameter for a document; same as
        the name of the class that models the document
    :return: a class object that is a subclass of HikaruDocumentBase

    NOTE: this function does lazy loading of modules in order to avoid
        dependency loops and speed startup. Hence the first time a kind is
        requested from a version the function may run a bit longer as it loads
        up the needed modules and processes its symbols
    """
    kind_dict = _version_kind_class_cache.get(version)
    if kind_dict is None:
        kind_dict: Dict[str, HikaruDocumentBase] = {}
        _version_kind_class_cache[version] = kind_dict
        try:
            mod = importlib.import_module(f".{version}", "hikaru.model")
        except ImportError:
            pass
        else:
            for o in vars(mod).values():
                if (type(o) == type and issubclass(o, HikaruDocumentBase) and
                        o is not HikaruDocumentBase):
                    kind_dict[o.__name__] = o
    return kind_dict.get(kind)
