from dataclasses import dataclass, field, fields, InitVar
from inspect import signature
from pprint import pprint as pp
from typing import List, Dict, Optional, get_type_hints
from hikaru import *
from hikaru.crd import get_crd_schema, register_crd_schema
from hikaru.model.rel_1_23.v1 import *
from hikaru.meta import FieldMetadata as fm

set_default_release("rel_1_23")


@dataclass
class Spec(HikaruBase):
    s1: float
    s2: int
    s3: str


@dataclass
class Resource(HikaruDocumentBase):
    f1: float
    f2: int
    f3: str
    f4: List[str]
    spec: Spec
    f5: bool
    f8: List['Spec']
    f13: str = field(metadata=fm(description="will this even work??"))
    f6: Optional[float] = None
    f7: Optional[List[int]] = field(default_factory=list,
                                    metadata=fm(description="Optional list of int field"))
    f9: Optional[Spec] = None
    f10: InitVar[Optional[Spec]] = None
    f11: InitVar[Optional[int]] = None
    f12: Optional[Dict[str, str]] = None
    apiVersion: str = 'v1'
    kind: str = "Resource"


register_crd_schema(Resource)


if __name__ == "__main__":
    print("\nJSONSchemaProps:")
    schema: JSONSchemaProps = get_crd_schema(Resource, JSONSchemaProps)
    pp(schema)
    print(get_yaml(schema))
    crd = CustomResourceDefinition(
        spec=CustomResourceDefinitionSpec(
            "wibble",
            names=CustomResourceDefinitionNames(
                kind="Resource",
                plural="rsrcs",
                singular="rsrc",
            ),
            scope="Namespaced",
            versions=[CustomResourceDefinitionVersion(
                'v1',
                True,
                True,
                schema=CustomResourceValidation(
                    openAPIV3Schema=schema)
            )
            ]
        )
    )
    raw_yaml = get_yaml(crd)
    remade_crd: CustomResourceDefinition = load_full_yaml(yaml=raw_yaml)[0]
    print(remade_crd)
    print(get_yaml(remade_crd))
