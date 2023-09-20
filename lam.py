# these funcs support the activities of the fine-grained setup files for the
# separate packages in the new world of hikaru.

from pathlib import Path
from typing import List


def list_all_paths(d: str) -> List[Path]:
    root: Path = Path(d)
    all_paths = []
    if not root.is_dir():
        raise ValueError(f"path {d} is not a directory")
    # p: Path
    for p in root.iterdir():
        if "__pycache__" in str(p):
            continue
        if p.is_dir():
            all_paths.extend(list_all_paths(str(p)))
        else:
            all_paths.append(p)
    return all_paths


def list_all_modules(d: str) -> List[str]:
    all_mods = []
    for p in list_all_paths(d):
        full_mod = ".".join(p.parts)
        full_mod = full_mod.strip(".py")
        all_mods.append(full_mod)
    return all_mods
