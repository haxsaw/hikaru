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

import time
from kubernetes.client import ApiException
from hikaru import watch
from hikaru.meta import WatcherDescriptor
from hikaru.model.rel_1_17.v1 import (Pod, Namespace, ObjectMeta, PodList,
                                      SelfSubjectRulesReview)

saved_get_api_class = watch._get_api_class
saved_k8s_watch_factory = watch._k8s_watch_factory
Watcher = watch.Watcher
WatchEvent = watch.WatchEvent
MultiplexingWatcher = watch.MultiplexingWatcher


class MockK8sWatch(object):
    def __init__(self):
        self.run = False

    def stop(self):
        self.run = False

    def stream(self, meth, **kwargs):
        self.run = True
        rv = 1
        while self.run:
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion=str(rv))
            rv += 1
            yield {'object': obj,
                   'type': 'ADDED'}
            time.sleep(0.1)


watch_to_vend = MockK8sWatch


def mock_k8s_watch_factory():
    return watch_to_vend()


class MockAPIClass(object):
    # in the derived class, this must be set to the class to emit
    class_watched = None

    def __init__(self, **kwargs):
        self.requested_item = None

    def __getattr__(self, item):
        self.requested_item = item
        return self.list_method

    def list_method(self, *args, **kwargs):
        pass


class_to_vend: type = None


def _mock_get_api_class(wd: WatcherDescriptor) -> type:
    return class_to_vend


def setup():
    watch._get_api_class = _mock_get_api_class
    watch._k8s_watch_factory = mock_k8s_watch_factory
    watch._should_translate = False


def teardown():
    watch._get_api_class = saved_get_api_class
    watch._k8s_watch_factory = saved_k8s_watch_factory
    watch._should_translate = True


def test01():
    """
    Check the basic function of the mocks
    """
    global class_to_vend

    class Test001Check(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test001Check

    watcher = Watcher(Pod)
    for we in watcher.stream():
        assert isinstance(we.obj, Pod)
        watcher.stop()
    assert True


def test02():
    """
    test02: Check we quit on a timeout
    """
    global class_to_vend, watch_to_vend

    class Test02Check(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test02Check

    class Test02Watch(MockK8sWatch):
        def stream(self, meth, **kwargs):
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='1')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test02Watch
    watcher = Watcher(Pod)
    count = 0
    try:
        for we in watcher.stream(quit_on_timeout=True):
            assert isinstance(we.obj, Pod)
            count += 1
            if count > 1:
                break
        assert count == 1
    finally:
        watch_to_vend = old_watch_factory


def test03():
    """
    test03: Check we get the a newer resource_version if ours is too low
    """
    global class_to_vend, watch_to_vend

    class Test03API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test03API

    class Test03Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            rv = int(resource_version)
            if rv < 5:
                raise ApiException(410, "Expired: asf (5)")
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='5')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test03Watch
    watcher = Watcher(Pod, resource_version='1')
    try:
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            assert isinstance(we.obj, Pod)
            assert we.obj.metadata.resourceVersion == '5'
    finally:
        watch_to_vend = old_watch_factory


def test04():
    """
    test04: check to make sure we catch things that aren't documents
    """
    try:
        w = Watcher(ObjectMeta)
        assert False, "ObjectMeta is not a HikaruDocumentBase subclass"
    except TypeError:
        pass


def test05():
    """
    test05: check to make sure we can use the List classes
    """
    w = Watcher(PodList)


def test06():
    """
    test06: check that we raise when a namespace isn't supported
    """
    try:
        w = Watcher(Namespace, namespace='oops')
        assert False, "Namespace objects can't watch with a namespace"
    except TypeError:
        pass


def test07():
    """
    test07: check we accept a namespace when it is supported
    """
    w = Watcher(Pod, namespace='okay')


def test08():
    """
    test08: check we raise for a document with no watcher support
    """
    try:
        w = Watcher(SelfSubjectRulesReview)
        assert False, "SelfSubjectRulesReview has no watcher support"
    except TypeError:
        pass


def test09():
    """
    test09: check guard on updating the resource version
    """
    w = Watcher(Pod)
    try:
        w.update_resource_version(None)
        assert False, "update_resource_version shouldn't allow None"
    except RuntimeError:
        pass


def test10():
    """
    test10: check that we can find the oldest resourceVersion
    """
    global class_to_vend, watch_to_vend

    class Test10API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test10API

    class Test10Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            rv = int(resource_version)
            if rv < 5:
                raise ApiException(410, "Expired: asf (5)")
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='6')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test10Watch
    watcher = Watcher(Pod)
    try:
        for we in watcher.stream(manage_resource_version=True,
                                 quit_on_timeout=True):
            assert isinstance(we.obj, Pod)
            assert we.obj.metadata.resourceVersion == '6'
    finally:
        watch_to_vend = old_watch_factory


def test11():
    """
    test11: check we raise through on any status other than 410
    """
    global class_to_vend, watch_to_vend

    class Test11API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test11API

    class Test11Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            raise ApiException(500, 'who cares?')

    old_watch_factory = watch_to_vend
    watch_to_vend = Test11Watch
    watcher = Watcher(Pod)
    try:
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            assert False, 'this should have raised an ApiException'
    except ApiException as e:
        watch_to_vend = old_watch_factory
        assert e.status == 500


def test12():
    """
    test12: check we raise through with a 410 that doesn't have the oldest rv
    """
    global class_to_vend, watch_to_vend

    class Test12API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test12API

    class Test12Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            raise ApiException(410, 'Expired: oh noes!')

    old_watch_factory = watch_to_vend
    watch_to_vend = Test12Watch
    watcher = Watcher(Pod)
    try:
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            assert False, 'this should have raised an ApiExecption'
    except ApiException:
        pass
    finally:
        watch_to_vend = old_watch_factory


def test13():
    """
    test13: check we properly increment the highest rv we've seen
    """
    global class_to_vend, watch_to_vend

    class Test13API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test13API

    class Test13Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            if resource_version == '1':
                raise ApiException(status=410, reason='Expired: (5)')
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='6')
            yield {'object': obj,
                   'type': 'ADDED'}
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='10')
            yield {'object': obj,
                   'type': 'ADDED'}
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='11')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test13Watch
    watcher = Watcher(Pod)
    try:
        for _ in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            pass
        assert watcher.highest_resource_version == 11
    finally:
        watch_to_vend = old_watch_factory


def test14():
    """
    test14: check to see if you get one message and then a non-410 error you re-raise
    """
    global class_to_vend, watch_to_vend

    class Test14API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test14API

    class Test14Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            if resource_version == '1':
                raise ApiException(status=410, reason='Expired: (5)')
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='6')
            yield {'object': obj,
                   'type': 'ADDED'}
            raise ApiException(500, 'who cares?')

    old_watch_factory = watch_to_vend
    watch_to_vend = Test14Watch
    watcher = Watcher(Pod)
    try:
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            pass
    except ApiException as e:
        assert e.status == 500
    finally:
        watch_to_vend = old_watch_factory


def test14a():
    """
    test14a: manage rv but supply an initial value & restart stream
    """
    global class_to_vend, watch_to_vend

    class Test14aAPI(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test14aAPI

    class Test14a1Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            if resource_version == '1':
                raise ApiException(status=410, reason='Expired: (5)')
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='6')
            yield {'object': obj,
                   'type': 'ADDED'}

    class Test14a2Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='7')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test14a1Watch
    watcher = Watcher(Pod, resource_version='1')
    try:
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            pass
        watch_to_vend = Test14a2Watch
        for we in watcher.stream(manage_resource_version=True, quit_on_timeout=True):
            pass
        assert watcher.highest_resource_version == 7
    finally:
        watch_to_vend = old_watch_factory


def test15():
    """
    test15: test basics of the mux
    """
    global class_to_vend, watch_to_vend

    class Test15API(MockAPIClass):
        class_watched = Pod

    class_to_vend = Test15API

    class Test15Watch(MockK8sWatch):
        def stream(self, meth, resource_version=None, **kwargs):
            obj = class_to_vend.class_watched.get_empty_instance()
            obj.metadata = ObjectMeta(resourceVersion='6')
            yield {'object': obj,
                   'type': 'ADDED'}

    old_watch_factory = watch_to_vend
    watch_to_vend = Test15Watch
    watcher = Watcher(Pod)
    mux = MultiplexingWatcher()
    w = Watcher(Pod, timeout_seconds=1)
    # for mux.stream(quit_on_timeout=True):



if __name__ == "__main__":
    setup()
    # test14a()
    for k, v in dict(globals()).items():
        if callable(v) and k.startswith('test'):
            print(f'running {k}')
            try:
                v()
            except Exception as e:
                print(f'{k} failed with {e}')
    teardown()

