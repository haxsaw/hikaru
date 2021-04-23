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
from hikaru.naming import get_default_release

_release_version_kind_class_cache: Dict[str, Dict[str, Dict[str, type]]] = {}


def get_version_kind_class(version: str, kind: str,
                           release: Optional[str] = None) -> Optional[type]:
    """
    Return a class for a subclasses of HikaruDocumentBase for a specific K8s version

    :param version: string; name of the version in which to look for the object
    :param kind: string; value of the 'kind' parameter for a document; same as
        the name of the class that models the document
    :param release: optional string; if supplied, indicates which release to load classes
        from. Must be one of the subpackage of hikaru.model, such as rel_1_16.
        If unspecified, the release specified from
        hikaru.naming.set_default_release() is used; if that hasn't been called,
        then the default from when hikaru was built will be used.
    :return: a class object that is a subclass of HikaruDocumentBase

    NOTE: this function does lazy loading of modules in order to avoid
        dependency loops and speed startup. Hence the first time a kind is
        requested from a version the function may run a bit longer as it loads
        up the needed modules and processes its symbols
    """
    use_release = release if release is not None else get_default_release()
    version_kind = _release_version_kind_class_cache.get(use_release)
    if version_kind is None:
        version_kind = {}
        _release_version_kind_class_cache[use_release] = version_kind
    kind_dict = version_kind.get(version)
    if kind_dict is None:
        kind_dict = {}
        version_kind[version] = kind_dict
        try:
            mod = importlib.import_module(f".{version}",
                                          f"hikaru.model.{use_release}.{version}")
        except ImportError:
            pass
        else:
            for o in vars(mod).values():
                if (type(o) == type and issubclass(o, HikaruDocumentBase) and
                        o is not HikaruDocumentBase):
                    kind_dict[o.__name__] = o
    return kind_dict.get(kind)
