import importlib
from hikaru.meta import HikaruDocumentBase
try:
    from hikaru.model.versions import versions
except ImportError:
    versions = []

version_kind_map = {}

for version in versions:
    try:
        mod = importlib.import_module(f".{version}", "hikaru.model")
    except ImportError:
        continue
    for o in vars(mod).values():
        if (type(o) == type and issubclass(o, HikaruDocumentBase) and
                o is not HikaruDocumentBase):
            version_kind_map[(version, o.__name__)] = o

