import importlib
from types import MethodType, FunctionType
from inspect import signature
from hikaru.meta import HikaruDocumentBase
from hikaru.model.rel_unversioned.versions import versions
from hikaru import set_default_release
import pytest


set_default_release('rel_unversioned')


all_params = []
for version in versions:
    test_classes = []
    mod = importlib.import_module(f".{version}", 'hikaru.model.rel_unversioned')
    for c in vars(mod).values():
        if (type(c) is type and issubclass(c, HikaruDocumentBase) and
                c is not HikaruDocumentBase):
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
                    all_params.append((name, attr, params))


@pytest.mark.parametrize('name, func, kwargs', all_params)
def test_methods(name, func, kwargs):
    if name == "deleteAdmissionregistrationCollectionMutatingWebhookConfiguration":
        _ = 1
    func(**kwargs)


if __name__ == "__main__":
    for name, func, params in all_params:
        test_methods(name, func, params)
        print('.', end="")
    print()

