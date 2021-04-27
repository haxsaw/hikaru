import importlib
from types import MethodType, FunctionType
from inspect import signature
from random import choice
import pytest
from hikaru import HikaruDocumentBase, HikaruOpsBase
from hikaru.model.rel_1_16.versions import versions
from hikaru import set_default_release


set_default_release('rel_1_16')


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

    def select_header_content_type(self, content_types: list):
        if not content_types:
            return 'application/json'

        content_types = [x.lower() for x in content_types]

        if 'application/json' in content_types or '*/*' in content_types:
            return 'application/json'
        else:
            return content_types[0]

    def call_api(self, path, verb, path_params, query_params, header_params,
                 body=None, **kwargs):
        self.body = body
        coin = choice(('heads', 'tails'))
        if coin == 'heads':
            return None, 401, {}
        else:
            return 1


all_params = []
for version in versions:
    test_classes = []
    mod = importlib.import_module(f".{version}", f'hikaru.model.rel_1_16.{version}')
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
                        if p.name in {'client', 'self'}:
                            continue
                        if p.name == "namespace":
                            params[p.name] = "default"
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
                elif isinstance(attr, staticmethod):
                    # process static methods here
                    smeth = getattr(cls, name)
                    sig = signature(smeth)
                    mock_client = MockApiClient()
                    params = {"client": mock_client}
                    for p in sig.parameters.values():
                        if p.name == "client":
                            continue
                        elif p.name == "namespace":
                            params[p.name] = 'default'
                        elif p.name == 'name':
                            params[p.name] = 'the_name'
                        elif p.name == 'body':
                            params[p.name] = {}
                        else:
                            params[p.name] = None
                    all_params.append((smeth, params))
    # ok, that got the classes and instace methods; now find/test the Ops collections
    mod = importlib.import_module(".misc", f"hikaru.model.rel_1_16.{version}")
    test_classes = []
    for c in vars(mod).values():
        if (type(c) is type and issubclass(c, HikaruOpsBase) and c is not HikaruOpsBase):
            test_classes.append(c)
    for cls in test_classes:
        for name, attr in vars(cls).items():
            if not name.startswith("__"):
                if isinstance(attr, staticmethod):
                    smeth = getattr(cls, name)
                    sig = signature(smeth)
                    mock_client = MockApiClient()
                    params = {}
                    for p in sig.parameters.values():
                        if p.name == 'client':
                            params['client'] = mock_client
                        elif p.name == 'namespace':
                            params[p.name] = 'the_namespace'
                        elif p.name == 'name':
                            params[p.name] = 'the_name'
                        elif p.name == 'path':
                            params[p.name] = 'somePath'
                        else:
                            params[p.name] = None
                    all_params.append((smeth, params))


@pytest.mark.parametrize('func, kwargs', all_params)
def test_methods(func, kwargs):
    func(**kwargs)


if __name__ == "__main__":
    for func, params in all_params:
        test_methods(func, params)
        print('.', end="")
    print()

