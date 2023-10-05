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
import pytest
from hikaru import HikaruDocumentBase, set_default_release
from hikaru.model.rel_1_27.versions import versions
from hikaru.model.rel_1_27.v1 import JSONSchemaProps
from hikaru.crd import get_crd_schema


def beginning():
    set_default_release('rel_1_27')


def ending():
    pass


@pytest.fixture(scope='module', autouse=True)
def setup():
    beginning()
    yield 1
    ending()


test_classes = []
for version in versions:
    mod = importlib.import_module(f".{version}", f"hikaru.model.rel_1_27.{version}")
    for c in vars(mod).values():
        if (type(c) is type and issubclass(c, HikaruDocumentBase) and
                c is not HikaruDocumentBase):
            test_classes.append(c)


@pytest.mark.parametrize('cls', test_classes)
def test_docclass(cls):
    assert hasattr(cls, 'apiVersion'), f"Class {cls.__name__} doesn't have apiVersion"
    assert cls.apiVersion, f"Class {cls.__name__} has no value for apiVersion"
    assert hasattr(cls, 'kind'), f"Class {cls.__name__} doesn't have kind"
    assert cls.kind, f"Class {cls.__name__} has no value for kind"


@pytest.mark.parametrize('cls', test_classes)
def test_crd_processing(cls):
    try:
        get_crd_schema(cls)
    except RecursionError:
        # there are a couple of recursively defined classes that we can't process
        # right now, so we just ignore them
        pass


if __name__ == "__main__":
    beginning()
    try:
        for cls in test_classes:
            test_docclass(cls)
            test_crd_processing(cls)
    finally:
        ending()
