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
"""
The watch module provides support for performing K8s watch operations on resources
"""

import importlib
import threading
import queue
from kubernetes.client import ApiClient
from kubernetes.watch import Watch
from hikaru import HikaruDocumentBase, from_dict
from hikaru.meta import WatcherDescriptor

_api_class_cache = {}


def _get_api_class(wd: WatcherDescriptor) -> type:
    key = (wd.pkgname, wd.modname, wd.clsname)
    cls = _api_class_cache.get(key)
    if cls is None:
        mod = importlib.import_module(wd.modname, wd.pkgname)
        cls = getattr(mod, wd.clsname)
        _api_class_cache[key] = cls
    return cls


class BaseWatcher(object):

    def __init__(self):
        self._run = False

    def _setup(self):
        return

    def stream(self):
        self._setup()
        self._run = True
        while self._run:
            yield None

    def stop(self):
        self._run = False


class Watcher(BaseWatcher):
    def __init__(self, cls,
                 namespace: str = None,
                 allow_watch_bookmarks: bool = None,
                 continue_: str = None,
                 field_selector: str = None,
                 label_selector: str = None,
                 limit: int = None,
                 resource_version: str = None,
                 timeout_seconds: int = None,
                 pretty: str = None,
                 client: ApiClient = None):
        if not issubclass(cls, HikaruDocumentBase):
            raise TypeError("cls must be a subclass of HikaruDocumentBase")

        if namespace:
            if cls._namespaced_watcher is None:
                raise TypeError(f"{cls.__name__} has no namespaced watcher support")
            self.wd: WatcherDescriptor = cls._namespaced_watcher
        else:
            if cls._watcher is None:
                raise TypeError(f"{cls.__name__} has no watcher support")
            self.wd: WatcherDescriptor = cls._watcher

        super(Watcher, self).__init__()
        self.cls = cls
        self.kwargs = {'allow_watch_bookmarks': allow_watch_bookmarks,
                       '_continue': continue_,
                       'field_selector': field_selector,
                       'label_selector': label_selector,
                       'limit': limit,
                       'resource_version': resource_version,
                       'timeout_seconds': timeout_seconds,
                       'pretty': pretty}
        if namespace is not None:
            self.kwargs['namespace'] = namespace
        self.client = client
        self.k8s_watcher = Watch()
        apicls = _get_api_class(self.wd)
        inst = apicls(api_client=self.client)
        self.meth = getattr(inst, self.wd.methname)

    def stop(self):
        if self.k8s_watcher is not None:
            self.k8s_watcher.stop()
        super(Watcher, self).stop()

    def stream(self):
        self._run = True
        for e in self.k8s_watcher.stream(self.meth, **self.kwargs):
            o: HikaruDocumentBase = from_dict(e['object'].to_dict(),
                                              translate=True)
            yield o
            if not self._run:
                break


class MultiplexingWatcher(BaseWatcher):
    def __init__(self):
        super(MultiplexingWatcher, self).__init__()
        self.watchers = {}
        self.results_queue = queue.Queue()
