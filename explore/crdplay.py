from typing import get_type_hints, Optional
from functools import partial


class CallProp(object):
    def __init__(self, o, m):
        self.o = o
        self.m = m

    def __call__(self, *args, **kwargs):
        print(f"args: {args}, kwargs: {kwargs}")


class Caller(object):
    def __init__(self, verb: str, p1: str, p2: str):
        self.verb = verb
        self.p1 = p1
        self.p2 = p2
        self.prop = None

    def __call__(self, m):
        th = get_type_hints(m)
        self.prop = CallProp(self, m)
        return self.prop

    def m(self):
        pass


call_read = partial(Caller, 'read')


class Thing(object):
    pass


class SomeCRD(object):
    @call_read('x', 'y')
    def read(self, namespace: str, dryrun: bool, conn: Optional[Thing] = None):
        pass

    def othermeth(self, ns, dr):
        pass


def f(x: str, y: Optional[int]) -> int:
    return 0


sc = SomeCRD()
sc.read('default', True, conn=None)
_ = 1
