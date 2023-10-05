#
# Copyright (c) 2023 Incisive Technology Ltd
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

import pathlib
import os

_default_release = None


def get_default_installed_release() -> str:
    """
    Returns the highest numbered installed release which is the default

    :return: string; the name of the release package that is the highest numbered
        one currently installed. If none are installed, raises a RuntimeError.
        The first call inspects the filesystem to find the highest numbered installed
        release, subsequent calls return the cached value.
    """
    global _default_release
    if _default_release is None:
        module_path = os.path.abspath(__file__)
        module_dir = pathlib.Path(module_path).parent
        maxver = ""
        for content in module_dir.iterdir():
            if content.is_dir() and content.name.startswith('rel_'):
                if content.name > maxver:
                    maxver = content.name
        if not maxver:
            raise RuntimeError(f"No release packages found in {module_dir}; please install a "
                               f"hikaru-module package")
        _default_release = maxver
    return _default_release
