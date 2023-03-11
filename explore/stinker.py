from dataclasses import dataclass, field, fields
from inspect import signature
from pprint import pprint as pp
from typing import List, Dict, Optional, get_type_hints
from hikaru import *
from hikaru.crd import CRDMixin, HikaruCRDDocumentBase
from hikaru.model.rel_1_23.v1 import JSONSchemaProps

set_default_release("rel_1_23")


@dataclass
class Spec(HikaruBase):
    s1: float
    s2: int
    s3: str


@dataclass
class Resource(HikaruCRDDocumentBase):
    f1: float
    f2: int
    f3: str
    f4: List[str]
    spec: Spec
    f5: bool
    f8: List[Spec]
    f6: Optional[float] = None
    f7: Optional[List[int]] = None
    apiVersion: str = 'v1'
    kind: str = "Resource"


if __name__ == "__main__":
    print("Hints for Resource:")
    pp(get_type_hints(Resource))
    print("\nJSONSchemaProps:")
    pp(Resource.get_crd_schema(JSONSchemaProps))
