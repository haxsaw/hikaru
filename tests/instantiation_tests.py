import importlib
import pytest
from hikaru import HikaruBase, HikaruDocumentBase, get_clean_dict, from_dict
from hikaru.model.rel_1_16.versions import versions
from hikaru.model import NamespaceList


all_classes = []
for version in versions:
    mod = importlib.import_module(f".{version}", f"hikaru.model.rel_1_16.{version}")
    for o in vars(mod).values():
        if (type(o) is type and issubclass(o, HikaruBase) and
                o not in (HikaruBase, HikaruDocumentBase)):
            all_classes.append(o)


@pytest.mark.parametrize('cls', all_classes)
def test_instantiation(cls):
    assert issubclass(cls, HikaruBase)
    inst = cls.get_empty_instance()
    if issubclass(cls, HikaruDocumentBase):
        d = get_clean_dict(inst)
        _ = from_dict(d)
    else:
        d = get_clean_dict(inst)
        _ = from_dict(d, cls=cls)


if __name__ == "__main__":
    test_instantiation(NamespaceList)
    for cls in all_classes:
        test_instantiation(cls)
        print('.', end="")
    print()
