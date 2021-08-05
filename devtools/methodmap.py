import importlib
from hikaru import HikaruDocumentBase
from hikaru.model.rel_1_17.v1 import documents


def map_em(docsmod) -> dict:
    """
    returns a mapping of method name to containing class

    Returns a dict whose keys are method names and whose values are the names
    of the class the method belongs to.

    :param docsmod: a module object containing classes

    Raises KeyError if a method name is already found in the mapping to return

    :return: dict
    """
    meth_to_class = {}
    for k, v in vars(docsmod).items():
        if (type(v) is not type or
                not issubclass(v, HikaruDocumentBase) or
                v is HikaruDocumentBase):
            continue

        cancall = [attrname for attrname in vars(v).keys()
                   if (callable(getattr(v, attrname)) and
                       not attrname.startswith('__'))]
        for methname in cancall:
            if methname in {'create', 'read', 'update', 'delete'}:
                continue
            if methname in meth_to_class:
                raise KeyError(f"method {methname} already found in "
                               f"class {meth_to_class[methname]}")
            meth_to_class[methname] = k
    return meth_to_class


if __name__ == "__main__":
    rel_version_method_class = {}
    for release in ['rel_1_16', 'rel_1_17']:
        rel_version_method_class[release] = version_method_class = {}
        version_mod = importlib.import_module('.versions',
                                              f'hikaru.model.{release}')
        for version in version_mod.versions:
            docmod = importlib.import_module('.documents',
                                             f'hikaru.model.{release}.{version}')
            version_method_class[version] = map_em(docmod)
    print(repr(rel_version_method_class))
