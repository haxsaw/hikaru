import importlib
from types import MethodType, FunctionType
from inspect import signature
from hikaru.meta import HikaruDocumentBase
from hikaru.model.rel_1_16.versions import versions
from hikaru import set_default_release
import pytest


set_default_release('rel_1_16')


special_classes_to_test = {'Patch'}


all_params = []
for version in versions:
    test_classes = []
    mod = importlib.import_module(f".{version}", 'hikaru.model.rel_1_16')
    for c in vars(mod).values():
        if (type(c) is type and ((issubclass(c, HikaruDocumentBase) and
                c is not HikaruDocumentBase) or
                c.__name__ in special_classes_to_test)):
            test_classes.append(c)
    for cls in test_classes:
        for name, attr in vars(cls).items():
            if not name.startswith("__"):
                if isinstance(attr, MethodType) or isinstance(attr, FunctionType):
                    inst = cls.get_empty_instance()
                    params = {'self': inst}
                    sig = signature(attr)
                    for p in sig.parameters.values():
                        if p.name == 'client' or p.name == 'self':
                            continue
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
