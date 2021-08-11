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
from hikaru import HikaruDocumentBase
from hikaru.watch import Watcher
from hikaru.model.rel_1_16.versions import versions


namespaced_classes = []

unnamespaced_classes = []

for version in versions:
    mod = importlib.import_module(".documents",
                                  f"hikaru.model.rel_1_16.{version}")
    for o in vars(mod).values():
        if (type(o) is type and issubclass(o, HikaruDocumentBase)
                and o is not HikaruDocumentBase):
            if o._watcher_cls is not None:
                target = o._watcher_cls
            elif (o._watcher is not None or o._namespaced_watcher is not None):
                target = o
            else:
                continue
        else:
            continue

        # generate inputs for unnamespaced watchables
        if target._watcher is not None:
            unnamespaced_classes.append(target)
            if o._watcher_cls is not None and o is not target:
                unnamespaced_classes.append(o)

        # generate inputs for namespaced watchables
        if target._namespaced_watcher is not None:
            namespaced_classes.append(target)
            if o._watcher_cls is not None and o is not target:
                namespaced_classes.append(o)


@pytest.mark.parametrize('cls', namespaced_classes)
def test_namespaced(cls: type):
    w = Watcher(cls, namespace=f"namespace-for-{cls.__name__}")


@pytest.mark.parametrize('cls', unnamespaced_classes)
def test_unnamespaced(cls: type):
    w = Watcher(cls)


if __name__ == "__main__":
    for cls in namespaced_classes:
        try:
            test_namespaced(cls)
        except Exception:
            print(f"Failed making watcher for {cls.__name__}")

    for cls in unnamespaced_classes:
        try:
            test_unnamespaced(cls)
        except Exception:
            print(f"Failed making watcher for {cls.__name__}")
