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
import importlib
from dataclasses import fields
from typing import Dict, Optional
from hikaru.meta import HikaruDocumentBase
from hikaru.naming import get_default_release, process_api_version

_release_version_kind_class_cache: Dict[str, Dict[str, Dict[str, type]]] = {}


def register_version_kind_class(cls: type, version: str, kind: str,
                                release: Optional[str] = None) -> Optional[type]:
    """
    Register a class for Hikaru to instantiate based on version/kind

    This function allows you to register a dataclass for Hikaru to instantiate
    whenever it encounters the specified version/kind values in the 'apiVersion'
    and 'kind' fields of a YAML, Python dict, or JSON representation of a K8s
    object. Class must be a subclass of HikaruDocumentBase; either a direct
    subclass of that class (useful when creating custom operator classes) or
    a subclass of an existing HikaruDocumentBase subclass such as Pod or Deployment
    (good if you just want to add some custom methods/data to these classes).

    If creating a subclass of an existing class, you need to supply the identical
    apiVersion and kind values that are used by Hikaru for identifying this
    original class. A simple way to do this is to just pass references to these
    class attributes on the base class to the registration call. So for example,
    if you have a class MyPod which is derived from Pod, you can register it like
    so:

    ``register_version_kind_class(MyPod, Pod.apiVersion, Pod.kind)``

    Now when Hikaru needs to create a Pod instance, it will instantiate MyPod
    instead of Pod.

    If you do not specify the release parameter, the registration will be for
    the default release for the thread. Otherwise, pass in the string name of
    a release package under ``hikaru.model``, and this class will only be
    registered for use in the specified release.

    **Requirements of the 'cls' parameter**

    Besides being a subclass of HikaurDocumentBase, when defining a new
    class for Hikaru to instantiate, there are a few variations
    on what you define that are available to you, however there are two constraints
    that must always be followed:

    1. The module that contains the subclass **must** include a suitable
       wild-card import for all the symbols in the model module that you want
       to base your subclass on. So for example, if you are creating a subclass
       of Pod, you will run into errors if the module that contains your Pod
       subclass only has:

       ``from hikaru.model.rel_1_16.v1 import Pod``

       You must instead import all symbols from that release/version:

       ``from hikaru.model.rel_1_16.v1 import *``

    2. The classes must be defined at the top-level within the module.

    Further conditions may apply depending on the nature of the subclass you are
    creating:

    *If only adding methods to an existing subclass (no new attrs):*

    If your subclass is only adding methods, then there are no further conditions
    to meet to define this subclass.

    *If adding instance attrs that are NOT passed in during instantiation:*

    If you are adding additional attributes that aren't passed in from the
    instance creation call, you should simply implement the ``__post_init__()``
    method, making sure to call super() with the client argument before adding
    your new attributes and values:

    .. code:: python

        from hikaru.model.rel_1_17 import *
        from typing import Any

        class MyPod(Pod):
            def __post_init__(self, client: Any = None):
                super(MyPod, self).__post_init__(client=client)
                # your additional attributes are set up here
                self.x = []
                self.y = {}

    *If only adding instance attrs that are passed in during instantiation:*

    It is possible to define such classes, but NOTE: Hikaru will be unable
    to create instances of these classes that contain anything other than
    default values, as it has no way to know what values to provide.

    In this case, you need to make a new dataclass and use type annotations
    to declare the new parameters are to be `InitVar`, which makes the dataclass
    only use them during init processing, but does not add them to the set
    of fields managed by the dataclass:

    .. code:: python

        from hikaru.model.rel_1_16 import *
        from dataclasses import dataclass, InitVar
        from typing import Any

        @dataclass
        class MyPod(Pod):
            x: InitVar[Any] = None
            y: InitVar[Any] = None

            def __post_init__(self, client: Any = None, x=None, y=None):
                super(MyPod, self).__post_init__(client=client)
                self.x = x
                self.y = y

    Note that any new fields will come after the ``client`` parameter in
    the ``__post_init__()`` method. NOTE: if you do not use InitVar for these
    fields, Hikaru will consider them part of the data that is to be sent out
    or read in from YAML, which may yield unpredictable results or errors.

    *If declaring a new subclass of HikaruDocumentBase:*

    You can use this approach when creating a custom operator that will consume
    a custom YAML document. In this case, you will need to define a dataclass
    that is a subclass of HikaruDocumentBase that contains
    all of the fields that you require, including apiVersion and kind (these are
    critical; more below). Additionally, there's no ``client`` InitVar attribute
    since that's used to send messages into the underlying K8s Python client
    code.

    When you do this, Hikaru will then be able to consume a YAML document with
    the data fields and types you name in your dataclass. You can even specify
    contained objects within your top level object, and Hikaru will create
    instances of these contained objects automatically when consuming the YAML.

    It is critical that your custom dataclass include the apiVersion and kind
    fields, as those are what is used when registering your class. So an
    example of an operator class might look like the following:

    .. code:: python

        from hikaru.model.rel_1_16 import *
        from dataclasses import dataclass, InitVar
        from typing import Any

        # this is contained in the new top-level class, and so is
        # derived from HikaruBase
        @dataclass
        class PostgresSpec(HikaruBase):
            teamId: Optional[str] = None
            numberOfInstances: Optional[int] = 1
            # and so forth

        # now our top-level class
        @dataclass
        class Postgres(HikaruDocumentBase):
            apiVersion: Optional[str] = 'v1'  # or whatever you want
            kind: Optional[str] = 'postgres'
            metadata: Optional[ObjectMeta] = None
            spec: Optional[PostgresSpec] = None

    Such a set of classes would then be able to process YAML docs of the following
    form:

    .. code:: yaml

        apiVersion: "v1"
        kind: postgres
        metadata:
          name: acid-minimal-cluster
          namespace: default
        spec:
          teamId: "acid"
          numberOfInstances: 2

    :param cls: a class object which is a subclass of HikaruDocumentBase
    :param version: string; the version you want this class associated with
    :param kind: string; the kind of object this is
    :param release: optional string; if supplied, the name of the release where
        cls is to be registered. Otherwise, it will be registered in the release
        that is default for the calling thread.
    :raises TypeError: if the provided class is not a subclass of
        HikaruDocumentBase, or if the class doesn't have apiVersion or kind
        attributes
    :return: If replacing an existing class, the previously registered class
        is returned. If a new class, then None is returned.
    """
    if not issubclass(cls, HikaruDocumentBase):
        raise TypeError("The class to register must be a HikaruDocumentBase "
                        "subclass")
    fset = {f.name for f in fields(cls)}
    if 'apiVersion' not in fset or 'kind' not in fset:
        raise TypeError("The class must have both apiVersion and kind "
                        "attributes")
    _, use_version = process_api_version(version)
    old_cls = get_version_kind_class(use_version, kind, release=release)
    kind_dict = _get_vk_dict(use_version, kind, release=release)
    kind_dict[kind] = cls
    return old_cls


def _get_vk_dict(version: str, kind: str, release: str = None) -> Dict[str, type]:
    # this function expects a version that has the group already peeled off
    use_release = release if release is not None else get_default_release()
    version_kind = _release_version_kind_class_cache.get(use_release)
    if version_kind is None:
        version_kind = {}
        _release_version_kind_class_cache[use_release] = version_kind
    kind_dict = version_kind.get(version)
    if kind_dict is None:
        kind_dict = {}
        version_kind[version] = kind_dict
    return kind_dict


def get_version_kind_class(version: str, kind: str,
                           release: Optional[str] = None) -> Optional[type]:
    """
    Return a class for a subclasses of HikaruDocumentBase for a specific K8s version

    :param version: string; name of the version in which to look for the object
    :param kind: string; value of the 'kind' parameter for a document; same as
        the name of the class that models the document
    :param release: optional string; if supplied, indicates which release to load classes
        from. Must be one of the subpackage of hikaru.model, such as rel_1_16.
        If unspecified, the release specified from
        hikaru.naming.set_default_release() is used; if that hasn't been called,
        then the default from when hikaru was built will be used.
    :return: a class object that is a subclass of HikaruDocumentBase

    NOTE: this function does lazy loading of modules in order to avoid
        dependency loops and speed startup. Hence the first time a kind is
        requested from a version the function may run a bit longer as it loads
        up the needed modules and processes its symbols
    """
    _, use_version = process_api_version(version)
    kind_dict = _get_vk_dict(use_version, kind, release=release)
    use_release = release if release is not None else get_default_release()
    if len(kind_dict) == 0:
        try:
            mod = importlib.import_module(f".{use_version}",
                                          f"hikaru.model.{use_release}.{use_version}")
        except ImportError:
            pass
        else:
            for o in vars(mod).values():
                if (type(o) == type and issubclass(o, HikaruDocumentBase) and
                        o is not HikaruDocumentBase):
                    kind_dict[o.__name__] = o
    return kind_dict.get(kind)
