import sys
from typing import Dict, Tuple
from build import (load_stable, response_mismatches, get_path_version, get_path_domain,
                   Operation, get_version_ops, objop_param_mismatches)


def analyze_response_mismatches():
    matches: Dict[str, Tuple[str, str, Operation]] = {}
    print("\n")
    for key, op in response_mismatches.items():
        version = get_path_version(op.op_path)
        domain = get_path_domain(op.op_path)
        for altver in ['v1alpha1', 'v1beta1', 'v1beta2', 'v1', 'v2beta1']:
            if altver == version:
                continue
            altpath = op.op_path.replace(version, altver)
            vops = get_version_ops(altver)
            altdomain = vops.query_ops.get(domain)
            if altdomain is None:
                print(f"NO DOMAIN {domain} in {altver}")
                continue
            altop = altdomain.operations.get(op.op_id)
            if altop:
                matches[key] = (version, altver, op)
        else:
            print(f"No other version for {key} in "
                  f"{op.op_path}:{op.verb}")
    print("\nQUERY MATCHES")
    for k, (ver, altver, op) in matches.items():
        print(f"{k}: {ver}, {altver} {op.op_id}")


def analyze_obj_mismatches():
    matches: Dict[str, Tuple[str, str, Operation]] = {}
    print("\n")
    for pname, op in objop_param_mismatches.items():
        version = get_path_version(op.op_path)
        for altver in ['v1alpha1', 'v1beta1', 'v1beta2', 'v1', 'v2beta1']:
            if altver == version:
                continue
            altpath = op.op_path.replace(version, altver)
            vops = get_version_ops(altver)
            altop = vops.object_ops.get(altpath)
            if altop:
                matches[pname] = (version, altver, op)
                break
        else:
            print(f"No other version for '{pname}' in "
                  f"{op.op_path}:{op.verb}")

    print("\nOBJECT MATCHES:")
    for k, (ver, altver, op) in matches.items():
        print(f"{k}: {ver}, {altver} {op.op_id}")


def analyze_it(swagger_file: str):
    load_stable(swagger_file)
    analyze_obj_mismatches()
    analyze_response_mismatches()
    v1ops = get_version_ops("v1")
    for key, objops in v1ops.object_ops.items():
        print(f"class {key}")
        for k, op in objops.operations.items():
            print(f"\t{k} {op.as_python_method()}")


if __name__ == "__main__":
    analyze_it(sys.argv[1])
