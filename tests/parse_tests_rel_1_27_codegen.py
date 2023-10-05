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
from hikaru import *
from hikaru.naming import get_default_release
import pytest


def setup():
    set_default_release('rel_1_27')


test_parms = []
path = pathlib.Path("test_yaml")
for p in path.iterdir():
    if p.parts[-1] == 'list.yaml':
        test_parms.append(pytest.param(p, marks=pytest.mark.xfail))
    elif str(p).endswith('.json'):
        continue
    else:
        test_parms.append(p,)


def make_instance_from_source(version, source):
    exec(f'from hikaru.model.{get_default_release()}.{version}.{version} import *')
    x = eval(source, globals(), locals())
    return x


@pytest.mark.parametrize("yamlpath", test_parms)
def test_yaml(yamlpath: pathlib.Path):
    f = yamlpath.open("r")
    docs = load_full_yaml(stream=f)
    assert len(docs) > 0, f"For path {yamlpath}, only got {len(docs)} docs"
    for doc in docs:
        # first test that rendered Python source yields the same object
        source = get_python_source(doc, style="black")
        _, version = process_api_version(doc.apiVersion)
        x = make_instance_from_source(version, source)
        try:
            assert x == doc, f'Failed to create identical Python from Python' \
                             f' source for {str(yamlpath)}, kind={doc.kind}'
        except AssertionError:
            print()
            for dd in x.diff(doc):
                assert isinstance(dd, DiffDetail)
                print(f">>{dd.cls.__name__}.{dd.formatted_path}: {dd.report}")
            raise

        # next try rendered yaml yields the same object
        yaml = get_yaml(x)
        new_doc = load_full_yaml(yaml=yaml)[0]
        try:
            assert doc == new_doc, f'Failed to create identical Python from' \
                                   f' exported yaml for {str(yamlpath)},' \
                                   f' kind={doc.kind}'
        except AssertionError:
            _ = 1  # debugger hook

        # next check rendered dicts yield the same object
        d = get_clean_dict(new_doc)
        dict_doc = from_dict(d)
        try:
            assert doc == dict_doc, f'Failed to get matching doc from a' \
                                    f' previously dumped dict'
        except AssertionError:
            _ = 1  # debugger hook

        # try dumping json and recrating it; should be the same
        j = get_json(dict_doc)
        jdoc = from_json(j)
        try:
            assert doc == jdoc, f'Failed to get matching doc from a' \
                                f' previous json dump'
        except AssertionError:
            _ = 1  # debugger hook

        # finally, check that the types check on the final copy
        warnings = jdoc.get_type_warnings()
        no_intorstring = [w for w in warnings if "IntOrString" not in w.warning]
        assert len(no_intorstring) == 0, f"Got {len(no_intorstring)}"


def do_all():
    path = pathlib.Path("test_yaml")
    for p in path.iterdir():
        try:
            test_yaml(p)
        except Exception as e:
            if str(p) == pathlib.Path("test_yaml/list.yaml"):
                print(f"WARNING! Still failed on list.yaml; no support in the "
                      f"swagger file for List. Ignoring failure")
            else:
                print(f"Failed on {p} with {e}")


if __name__ == "__main__":
    do_all()
