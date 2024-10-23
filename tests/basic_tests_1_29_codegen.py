#
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

from hikaru import *
from hikaru.model.rel_1_29 import *


set_default_release('rel_1_29')

p = None


def setup_pod() -> Pod:
    docs = load_full_yaml(stream=open("test.yaml", "r"))
    pod = docs[0]
    return pod


def setup():
    set_default_release('rel_1_29')
    global p
    p = setup_pod()


def test01():
    """
    get_python_source with the black style
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test02():
    """
    check that a modified loaded version of p isn't equal
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert isinstance(x, Pod)
    x.spec.containers[1].lifecycle.postStart.httpGet.port = 4
    assert x != p


def test03():
    """
    check that you can render explicitly to autopep8
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style='autopep8')
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test04():
    """
    check that you can render to black
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test05():
    """
    check that the assign_to arg works in get_python_source()
    """
    assert isinstance(p, Pod)
    s = get_python_source(p, style='black', assign_to='x')
    assert s.startswith('x =')


def test06():
    """
    ensure positional params are correct
    """
    own = OwnerReference('v1', 'OR', 'test084', 'asdf')
    s = get_python_source(own, style='black')
    o: OwnerReference = eval(s, globals(), locals())
    assert o.apiVersion == 'v1'
    assert o.kind == 'OR'
    assert o.name == 'test084'
    assert o.uid == 'asdf'


def test07():
    """
    Check two different code gen styles yield equivalent objects
    """
    assert isinstance(p, Pod)
    code1 = get_python_source(p)
    code2 = get_python_source(p, style='black')
    obj1 = eval(code1, globals(), locals())
    obj2 = eval(code2, globals(), locals())
    assert obj1 == obj2
