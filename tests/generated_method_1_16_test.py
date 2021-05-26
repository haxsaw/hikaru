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
from types import MethodType, FunctionType
from inspect import signature
import pytest
from hikaru import HikaruDocumentBase, Response, rollback_cm
from hikaru.model.rel_1_16.versions import versions
from hikaru import set_default_release, from_dict


class CMTestException(Exception):
    pass


set_default_release('rel_1_16')


special_classes_to_test = {'Patch'}


def beginning():
    Response.set_false_for_internal_tests = False
    return Response


def ending():
    Response.set_false_for_internal_tests = True


@pytest.fixture(scope='module', autouse=True)
def setup():
    res = beginning()
    yield res
    ending()


class MockApiClient(object):
    def __init__(self, gen_failure=False):
        self.body = None
        self.client_side_validation = 1
        self.gen_failure = gen_failure

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
        if isinstance(body, dict) and body:
            body = from_dict(body)
        self.body = body
        return self.body, 400 if self.gen_failure else 200, {}


all_params = []

cms_to_check = []

for version in versions:
    test_classes = []
    mod = importlib.import_module(f".{version}", f'hikaru.model.rel_1_16.{version}')
    om_class = getattr(mod, 'ObjectMeta')
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
                    inst.metadata = om_class(namespace='default', name='the_name')
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
                    all_params.append((attr, False, params))
                    # now do it again, but his time adding the client to the params
                    # that are passed into the method
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default', name='the_name')
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        elif p.name == "namespace":
                            params[p.name] = "the_namespace"
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, False, params))
                    # again, but this time without metadata at all; should raise
                    inst = cls.get_empty_instance()
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        elif p.name == "namespace":
                            params[p.name] = "the_namespace"
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, True, params))
                    # and again, but this time with no namespace
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(name='the_name')
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, True, params))
                    # and again, with the namespace in the metadata, not the args,
                    # BUT only for a crud method
                    if name not in {'create', 'update', 'delete', 'read'}:
                        continue
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default', name='the_name')
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        elif p.name == "name":
                            params[p.name] = "the_name"
                        else:
                            params[p.name] = None
                    all_params.append((attr, False, params))
                    # another permutation, this time ensuring that there is
                    # no name supplied in either the metadata or args
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default')
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        else:
                            params[p.name] = None
                    all_params.append((attr, True, params))
                    # and another, this time with the name in the metadata and not
                    # the parameters
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default', name='the_name')
                    mock_client = MockApiClient()
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        else:
                            params[p.name] = None
                    all_params.append((attr, False, params))
                    # (probably) the last one: same as previous, but tell
                    # the client to generate a failure
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default', name='the_name')
                    mock_client = MockApiClient(gen_failure=True)
                    params = {'self': inst, 'client': mock_client}
                    for p in sig.parameters.values():
                        if p.name in {'client', 'self'}:
                            continue
                        else:
                            params[p.name] = None
                    all_params.append((attr, True, params))
                    if name != 'update':
                        continue
                    # ok, from here we're just putting in instances that
                    # are to be tested for context manager behaviour.
                    # first, a plain cm use that succeeds
                    inst = cls.get_empty_instance()
                    inst.metadata = om_class(namespace='default', name='the_name')
                    inst.client = MockApiClient(gen_failure=False)
                    cms_to_check.append(inst)
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
                        elif p.name == 'path':
                            params[p.name] = 'somePath'
                        else:
                            params[p.name] = None
                    all_params.append((smeth, False, params))
    #
    # misc.py has been removed for now; we'll keep this in case it comes back
    #
    # ok, that got the classes and instance methods; now find/test the Ops collections
    # mod = importlib.import_module(".misc", f"hikaru.model.rel_1_16.{version}")
    # test_classes = []
    # for c in vars(mod).values():
    #     if type(c) is type and issubclass(c, HikaruOpsBase) and c is not HikaruOpsBase:
    #         test_classes.append(c)
    # for cls in test_classes:
    #     for name, attr in vars(cls).items():
    #         if not name.startswith("__"):
    #             if isinstance(attr, staticmethod):
    #                 smeth = getattr(cls, name)
    #                 sig = signature(smeth)
    #                 mock_client = MockApiClient()
    #                 params = {}
    #                 for p in sig.parameters.values():
    #                     if p.name == 'client':
    #                         params['client'] = mock_client
    #                     elif p.name == 'namespace':
    #                         params[p.name] = 'the_namespace'
    #                     elif p.name == 'name':
    #                         params[p.name] = 'the_name'
    #                     elif p.name == 'path':
    #                         params[p.name] = 'somePath'
    #                     else:
    #                         params[p.name] = None
    #                 all_params.append((smeth, params))


@pytest.mark.parametrize('func, should_raise, kwargs', all_params)
def test_methods(func, should_raise, kwargs):
    if should_raise:
        try:
            func(**kwargs)
            assert False, f"should_raise case for {func} didn't"
        except:
            assert True
    else:
        func(**kwargs)


@pytest.mark.parametrize('inst', cms_to_check)
def test_plain_cm_succeeds(inst):
    with inst as i:
        pass


@pytest.mark.parametrize('inst', cms_to_check)
def test_plain_cm_fails(inst):
    try:
        with inst as i:
            raise CMTestException()
    except CMTestException:
        pass


@pytest.mark.parametrize('inst', cms_to_check)
def test_rollback_cm_succeeds(inst):
    with rollback_cm(inst) as i:
        pass


@pytest.mark.parametrize('inst', cms_to_check)
def test_rollback_cm_fails(inst):
    try:
        with rollback_cm(inst) as i:
            raise CMTestException()
    except CMTestException:
        pass


if __name__ == "__main__":
    beginning()
    try:
        for func, should_raise, params in all_params:
            test_methods(func, should_raise, params)
            print('.', end="")
        for inst in cms_to_check:
            test_plain_cm_succeeds(inst)
            print('.', end="")
            test_plain_cm_fails(inst)
            print('.', end="")
            test_rollback_cm_fails(inst)
            print('.', end="")
            test_rollback_cm_succeeds(inst)
            print('.', end="")
    finally:
        ending()
    print()

