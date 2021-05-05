import importlib
import pytest
from hikaru import HikaruBase, HikaruDocumentBase
from hikaru.model.rel_1_16.versions import versions


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
    _ = cls.get_empty_instance()


if __name__ == "__main__":
    for cls in all_classes:
        test_instantiation(cls)
        print('.', end="")
    print()
