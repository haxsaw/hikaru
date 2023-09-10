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
from dataclasses import fields, Field
from inspect import signature, Signature, Parameter
from typing import Optional, TypeVar, Generic, get_type_hints, Dict, List
from multiprocessing.pool import ApplyResult
from kubernetes.client.models.v1_status import V1Status
from importlib import import_module

try:
    from typing import get_args, get_origin
except ImportError:  # pragma: no cover
    def get_args(tp):
        return tp.__args__ if hasattr(tp, "__args__") else ()

    def get_origin(tp):
        return tp.__origin__ if hasattr(tp, "__origin__") else None


field_metadata_domain = "hikaru"

# there are no production uses to change this value, but testing may alter it
model_root_package = "hikaru.model"


class ParamSpec(object):
    def __init__(self, param: Parameter, hint_type, field: Optional[Field]):
        self.param: Parameter = param
        self.hint_type = hint_type
        self.field = field

    def get_name(self):
        return self.param.name

    @property
    def name(self):
        return self.param.name

    def has_default(self):
        return self.param.default is not Parameter.empty

    def get_default(self):
        return self.param.default

    @property
    def default(self):
        return self.param.default

    def get_type(self):
        return self.hint_type

    @property
    def annotation(self):
        return self.hint_type

    @property
    def metadata(self):
        return self.field.metadata.get(field_metadata_domain, {}) if self.field is not None else {}


class HikaruCallableTyper(object):

    def __init__(self, cls):
        self.signature: Signature = signature(cls)
        self.hints: dict = get_type_hints(cls)
        self.params: Dict[str, ParamSpec] = {}
        p: Parameter
        field_dict: Dict[str, Field] = {f.name: f for f in fields(cls)}
        for p in self.signature.parameters.values():
            hint = self.hints[p.name]
            ps: ParamSpec = ParamSpec(p, hint, field_dict.get(p.name))
            self.params[p.name] = ps

    def values(self) -> List[ParamSpec]:
        return list(self.params.values())

    def has_param(self, param_name: str):
        return param_name in self.params


_inst_cache = {}


def get_hct(cls) -> HikaruCallableTyper:
    result: HikaruCallableTyper
    if cls in _inst_cache:
        result = _inst_cache[cls]
    else:
        result = _inst_cache[cls] = HikaruCallableTyper(cls)
    return result


T = TypeVar('T')


class Response(Generic[T]):
    """
    Response bundles up the possible responses that can be generated by K8s calls

    All Hikaru methods and functions return Response objects, which Hikaru fills out
    upon receiving a response from the underlying K8s method calls. K8s may return
    one of two kinds of values: for blocking calls, K8s returns the response code,
    data object, and headers. For async calls, K8s returns the thread that is
    processing the call. Hikaru's Response objects cover both of these possibilities.

    Public attributes can be interpreted as follows:

    If the call is blocking:

    - code: integer response code from K8s
    - obj: the data returned for the call. May be plain data, or may be an
      instance of a HikaruDocumentBase subclass, depending on the call.
    - headers: a dict-like object of the response headers

    If the call is non-blocking:

    - code, obj, headers: all None UNTIL .get() is called on the Response
        instance, at which point all three are populated as above as well
        as .get() returning a 3-tuple of (object, code, headers)

    Response objects also act as a proxy for the underlying multiprocessing
    thread object (multiprocessing.pool.ApplyResult) and will forward on
    the other public methods of that class.

    If .get() or any of the other async supporting calls are made on a Response
    object that was called blocking then they will all return None.
    """
    # this flag sets the 'translate' argument to from_dict()
    # when retrieving results from K8s. In normal integration cases
    # it should be True, but for certain tests it needs to be False.
    # Testing code that doesn't integrate into Kubernetes can set this
    # to False to avoid improperly named attributes.
    set_false_for_internal_tests = True

    def __init__(self, k8s_response, codes_with_objects):
        """
        Creates a new response:
        :param k8s_response: a 3-tuple consisting of:
            - return value dict
            - return code
            - headers
        :param codes_with_objects: an iterable of ints that are codes for which
            the self.obj field is a K8s object
        """
        self.code: Optional[int] = None
        self.obj: T = None
        self.headers: Optional[dict] = None
        self._thread: Optional[ApplyResult] = None
        self.codes_with_objects = set(codes_with_objects)
        if type(k8s_response) is tuple:
            self._process_result(k8s_response)
        else:
            # assume an ApplyResult
            self._thread = k8s_response

    def _process_result(self, result: tuple):
        from hikaru.generate import from_dict
        self.obj = result[0]
        self.code = result[1]
        self.headers = result[2]
        if self.code in self.codes_with_objects:
            if hasattr(self.obj, 'to_dict'):
                # OK, this is a patch over what I think to be a problem with the
                # K8s API spec. For delete operations it appears a K8s V1Status
                # object is returned, however, the kind and apiVersion attributes
                # are set to the values that would be involved with returning an
                # object of the type that was deleted. So for example, if you
                # delete a Pod, the kind/apiVersion values are for Pod, even
                # though the object returned is a V1Status. This works in lots of
                # cases since, for the most part, detail data for the object is
                # kept in an Optional 'spec' sub-object, and if it isn't in the
                # V1Status message, no one is the wiser. However, after poking
                # into some of the advanced corners of K8s it turns out there
                # are required spec sub-objects, and that results in an exception
                # when processing. So what we'll try doing here is detect if
                # we've got a V1Status, and if so, we'll change the kind/apiVersion
                # to the proper values for a Status object and that will pass
                # through. However, this may break some code that looks to
                # the return from a delete and expects to find the object that
                # was deleted. We'll also need to update the builder to change
                # what the class is showing as being returned.
                if isinstance(self.obj, V1Status):
                    from .naming import get_default_release
                    drel = get_default_release()
                    mod = import_module(".v1", f"{model_root_package}.{drel}")
                    self.obj.api_version = mod.Status.apiVersion
                    self.obj.kind = mod.Status.kind
                self.obj = from_dict(self.obj.to_dict(),
                                     translate=self.set_false_for_internal_tests)
            elif isinstance(self.obj, dict) and len(self.obj):
                # these are CRDs; don't do a translation
                # TODO; see about controlling translate for CRDs
                self.obj = from_dict(self.obj, translate=False)

    def ready(self):
        return self._thread.ready()

    def successful(self):
        return self._thread.successful()

    def wait(self, timeout=None):
        self._thread.wait(timeout=timeout)

    def get(self, timeout=None) -> tuple:
        """
        Fetch the results of an async call into K8s.

        This method waits for a response to a previously submitted request, either
        for a specified amount of time or indefinitely, and either raises an exception
        or returns the delivered response.

        :param timeout: optional float; if supplied, only waits 'timeout' seconds
            for a response until it raises a TimeoutError exception if the response
            hasn't arrived. If not supplied, blocks indefinitely.

        :return: a 3-tuple of (Hikaru object, result code (int), headers). These
            values are also stored in the public attributes of the instance, so
            you don't actually have to capture them upon return if you don't wish to.

        :raises TimeoutError: if a response has not arrived before the specified timeout
            has elapsed.
        :raises RuntimeError: if the reply is the wrong type altogether (should be
            reported).

        May also pass through any other exception.
        """
        result = self._thread.get(timeout=timeout)
        if type(result) is tuple:
            self._process_result(result)
        else:
            raise RuntimeError(f"Received an unknown type of response from K8s: "
                               f"type={type(result)}, value={result}")  # pragma: no cover
        return self.obj, self.code, self.headers


def rollback_cm(obj):
    """
    Rollback a HikaruDocumentBase instance if there's an error in a ``with`` block

    This function allows you to mark a ``HikaruDocumentBase`` subclass instance as being
    subject to a rollback if there's an error in processing the instance inside a
    ``with`` block for which the instance is the context manager. So instead of
    doing something like this:

    .. code:: python

        with Pod().read(name='something', namespace='something') as p:
            # and so forth

    ...where you'd need to recover the initial state of p if there was an error,
    you can instead do this:

    .. code:: python

        with rollback_cm(Pod().read(name='summat', namespace='summat')) as p:
            # and so forth

    If an error occurs inside the with block, then p will have the same state after
    the with block as it did at the start.

    If there is no error, the ``update()`` method is invoked on p as usual.

    :param obj: an instance of a subclass of HikaruDocumentBase
    :return: returns the input object which is a context manager.
    """
    # the __exit__ method looks for this attribute
    setattr(obj, "__rollback", obj.dup())
    return obj
