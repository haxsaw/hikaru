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
from hikaru import HikaruDocumentBase, set_global_default_release
from hikaru.watch import Watcher
from hikaru.model.rel_1_27.versions import versions
set_global_default_release('rel_1_27')


namespaced_classes = []

unnamespaced_classes = []

for version in versions:
    try:
        mod = importlib.import_module(".watchables",
                                      f"hikaru.model.rel_1_27.{version}")
    except ModuleNotFoundError:
        continue
    namespaced_classes.extend([c for c in vars(mod.NamespacedWatchables).values()
                               if type(c) is type and issubclass(c, HikaruDocumentBase)])
    unnamespaced_classes.extend([c for c in vars(mod.Watchables).values()
                                 if type(c) is type and issubclass(c, HikaruDocumentBase)])


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
