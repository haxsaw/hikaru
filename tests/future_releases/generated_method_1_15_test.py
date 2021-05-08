import importlib
from types import MethodType, FunctionType
from typing import List
from random import choice
from inspect import signature
from hikaru.meta import HikaruDocumentBase
from hikaru.model.rel_1_15.versions import versions
from hikaru import set_default_release
import pytest


set_default_release('rel_1_15')


special_classes_to_test = {'Patch'}


class MockApiClient(object):
    def __init__(self):
        self.body = None
        self.client_side_validation = 1

    def select_header_accept(self, accepts):
        """Returns `Accept` based on an array of accepts provided.

        :param accepts: List of headers.
        :return: Accept (e.g. application/json).
        """
        if not accepts:
            return

        accepts = [x.lower() for x in accepts]

        if 'application/json' in accepts:
            return 'application/json'
        else:
            return ', '.join(accepts)

    def call_api(self, path, verb, path_params, query_params, header_params,
                 body=None, **kwargs):
        self.body = body


all_params = []
for version in versions:
    test_classes = []
    mod = importlib.import_module(f".{version}", 'hikaru.model.rel_1_15')
    for c in vars(mod).values():
        if (type(c) is type and ((issubclass(c, HikaruDocumentBase) and
                c is not HikaruDocumentBase) or
                c.__name__ in special_classes_to_test)):
            test_classes.append(c)
    for cls in test_classes:
        for name, attr in vars(cls).items():
            if not name.startswith("__"):
                if isinstance(attr, MethodType) or isinstance(attr, FunctionType):
                    sig = signature(attr)
                    # first do it with the client provided at instance creation;
                    # we aren't actually doing that, we just set it after the
                    # the instances is made
                    inst = cls.get_empty_instance()
                    mock_client = MockApiClient()
                    inst.client = mock_client
                    params = {'self': inst}
                    for p in sig.parameters.values():
                        if p.name == 'client' or p.name == 'self':
                            continue
                        if p.name == "namespace":
                            params[p.name] = "the_namespace"
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, params))
                    # now do it again, but his time adding the client to the params
                    # that are passed into the method
                    inst = cls.get_empty_instance()
                    mock_client = MockApiClient()
                    params = {'self': inst}
                    for p in sig.parameters.values():
                        if p.name == 'self':
                            continue
                        if p.name == "client":
                            params["client"] = mock_client
                        elif p.name == "namespace":
                            params[p.name] = "the_namespace"
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, params))


@pytest.mark.parametrize('func, kwargs', all_params)
def test_methods(func, kwargs):
    func(**kwargs)


if __name__ == "__main__":
    for func, params in all_params:
        test_methods(func, params)
        print('.', end="")
    print()

