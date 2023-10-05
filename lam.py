# Copyright (c) 2021 Incisive Technology Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
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
