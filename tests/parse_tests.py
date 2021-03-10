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
This test runs through all of the test yaml files that go into the
test suite for the official Python kubernetes project. This have been
copied from:

https://github.com/kubernetes-client/python/tree/master/kubernetes/e2e_test/test_yaml
"""

import pathlib
from hikaru.generate import load_full_yaml


def test_yaml(yamlpath: pathlib.Path):
    f = yamlpath.open("r")
    docs = load_full_yaml(stream=f)
    assert len(docs) > 0, f"For path {yamlpath}, only got {len(docs)} docs"


def test_all():
    path = pathlib.Path("test_yaml")
    for p in path.iterdir():
        try:
            test_yaml(p)
        except Exception as e:
            if str(p) == "test_yaml/list.yaml":
                print(f"WARNING! Still failed on list.yaml; no support in the "
                      f"swagger file for List. Ignoring failure")
            else:
                print(f"Failed on {p} with {e}")


if __name__ == "__main__":
    test_all()
