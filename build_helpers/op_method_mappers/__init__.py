import importlib
from pathlib import  PurePath
import re
from types import ModuleType


class OpToMethodMapper:
    NO_MATCH = "NO_MATCH"

    def __init__(self, module: ModuleType):
        self.mapper_dict = module.all_mappers

    def get_methname_for_op(self, api_group: str, op, cd) -> str:
        group_map = self.mapper_dict.get(api_group, {})
        methname = group_map.get(op._op_id, self.NO_MATCH)
        if callable(methname):
            # not really a meth name, but a function that will return the methname
            methname = methname(op, cd)
        return methname

    def __contains__(self, item):
        return item in self.mapper_dict


class MapperVendor:
    pat = re.compile(r"swagger_(?P<ver>[0-9-]+)\.json")

    @classmethod
    def get_mapper_for_swagger(cls, swagger_file_path: str) -> "OpToMethodMapper":
        path = PurePath(swagger_file_path)
        swagger_file = path.name
        m = cls.pat.match(swagger_file)
        if m is None:
            raise Exception("Invalid swagger file name")
        version = m.group('ver')
        version = version.replace('-', "_")
        try:
            mod = importlib.import_module(f".op_to_method_maps_{version}", __name__)
        except ImportError:
            raise ImportError(f"Unable to to find a map module for version {version}")
        return OpToMethodMapper(mod)
