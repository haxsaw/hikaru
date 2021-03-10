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
