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
import pytest
from hikaru import (HikaruBase, HikaruDocumentBase, get_clean_dict, from_dict,
                    set_default_release)
from hikaru.model.rel_1_20.versions import versions
set_default_release('rel_1_20')
from hikaru.model.rel_1_20 import NamespaceList


all_classes = []
for version in versions:
    mod = importlib.import_module(f".{version}", f"hikaru.model.rel_1_20.{version}")
    for o in vars(mod).values():
        if (type(o) is type and issubclass(o, HikaruBase) and
                o not in (HikaruBase, HikaruDocumentBase)):
            all_classes.append(o)


@pytest.mark.parametrize('cls', all_classes)
def test_instantiation(cls):
    assert issubclass(cls, HikaruBase)
    inst = cls.get_empty_instance()
    if issubclass(cls, HikaruDocumentBase):
        d = get_clean_dict(inst)
        _ = from_dict(d)
    else:
        d = get_clean_dict(inst)
        _ = from_dict(d, cls=cls)


if __name__ == "__main__":
    test_instantiation(NamespaceList)
    for cls in all_classes:
        test_instantiation(cls)
        print('.', end="")
    print()
