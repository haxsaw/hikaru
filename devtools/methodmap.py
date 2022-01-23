import importlib
from hikaru import HikaruDocumentBase
from collections import defaultdict
import json


def map_em(docsmod, release: str, version: str) -> dict:
    """
    returns a mapping of method name to containing class

    Returns a dict whose keys are method names and whose values are the names
    of the class the method belongs to.

    :param docsmod: a module object containing classes

    Raises KeyError if a method name is already found in the mapping to return

    :return: dict
    """
    meth_to_class = {}
    meth_to_class = defaultdict(list)
    for k, v in vars(docsmod).items():
        if (type(v) is not type or
                not issubclass(v, HikaruDocumentBase) or
                v is HikaruDocumentBase):
            continue

        cancall = [attrname for attrname in vars(v).keys()
                   if (callable(getattr(v, attrname)) and
                       not attrname.startswith('_'))]
        for methname in cancall:
            if methname in {'create', 'read', 'update', 'delete'}:
                continue
            # if methname in meth_to_class:
            #     raise KeyError(f"method {methname} already found in "
            #                    f"class {meth_to_class[methname]} for "
            #                    f"release {release}, version {version}")
            meth_to_class[methname].append(k)
            # meth_to_class[methname] = k
    return meth_to_class


if __name__ == "__main__":
    rel_version_method_class = {}
    for release in ['rel_1_16', 'rel_1_17', 'rel_1_18', 'rel_1_19']:
        rel_version_method_class[release] = version_method_class = {}
        version_mod = importlib.import_module('.versions',
                                              f'hikaru.model.{release}')
        for version in version_mod.versions:
            docmod = importlib.import_module('.documents',
                                             f'hikaru.model.{release}.{version}')
            version_method_class[version] = map_em(docmod, release, version)
    rvmc = json.loads(json.dumps(rel_version_method_class))
    print(rvmc)
    # print(repr(rel_version_method_class))
