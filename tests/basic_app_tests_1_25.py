#
# Copyright (c) 2023 Incisive Technology Ltd
##
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from threading import Thread
from time import sleep
from typing import Optional, List, Dict
from kubernetes.client.exceptions import ApiException
from hikaru import *
set_default_release("rel_1_25")
from hikaru.model.rel_1_25.v1 import *
from hikaru.app import Application, Reporter
from hikaru.app import (get_app_instance_label_key, get_app_rsrc_attr_annotation_key,
                        set_app_instance_label_key, set_global_app_instance_label_key,
                        set_app_rsrc_attr_annotation_key, set_global_rsrc_attr_annotation_key,
                        AppWatcher)
from hikaru.crd import HikaruCRDDocumentMixin
from dataclasses import dataclass, Field, fields, field

from hikaru import app


class CRDTestExp(Exception):
    pass


class MockApiClient(object):
    def __init__(self, gen_failure=False, raise_exp=False, fail_on_verb=None, tweaker_func=None,
                 gen_failure_code=404, use_exception: Optional[BaseException] = ApiException):
        self.body = None
        self.client_side_validation = 1
        self.gen_failure = gen_failure
        self.raise_exp = raise_exp
        self.fail_on_verb = fail_on_verb.lower() if isinstance(fail_on_verb, str) else fail_on_verb
        self.tweaker_func = tweaker_func
        self.gen_failure_code = gen_failure_code
        self.call_count = 0
        self.post_count = 0
        self.put_count = 0
        self.get_count = 0
        self.use_exception = use_exception

    def select_header_accept(self, accepts):
        """Returns `Accept` based on an array of accepts provided.

        :param accepts: List of headers.
        :return: Accept (e.g. application/json).
        """
        if not accepts:
            return

        accepts = [x.lower() for x in accepts]

        if 'application/json' in accepts:
            return 'application/json'
        else:
            return ', '.join(accepts)

    def select_header_content_type(self, content_types: list):
        if not content_types:
            return 'application/json'

        content_types = [x.lower() for x in content_types]

        if 'application/json' in content_types or '*/*' in content_types:
            return 'application/json'
        else:
            return content_types[0]

    def allow_tweak(self, verb):
        if self.tweaker_func:
            self.tweaker_func(self, verb)

    def call_api(self, path, verb, path_params, query_params, header_params,
                 body=None, **kwargs):
        self.call_count += 1
        verb = verb.lower()
        if verb == "post":
            self.post_count += 1
        elif verb == "put":
            self.put_count += 1
        elif verb == "get":
            self.get_count += 1
        if self.fail_on_verb == verb:
            self.allow_tweak(verb)
            raise self.use_exception(self.gen_failure_code, "Synthetic not found", {})
        if self.raise_exp:
            self.allow_tweak(verb)
            raise CRDTestExp("Synthetic failure")
        if isinstance(body, dict) and body:
            body = from_dict(body)
        self.body = body
        self.allow_tweak(verb)
        return self.body, 400 if self.gen_failure else 200, {}


class MockReporter(Reporter):
    def __init__(self):
        super(MockReporter, self).__init__()
        self.app_starts = []
        self.app_ends = []
        self.reports = []
        self.abort = False
        self.ok_plan = True

    def report(self, app: Application, app_action: str, event_type: str, timestamp: str, attribute_name: str,
               resource: HikaruDocumentBase, additional_details: dict):
        if event_type == Reporter.APP_START_PROCESSING:
            self.app_starts.append((app, app_action, event_type, timestamp, attribute_name, resource, additional_details))
        elif event_type == Reporter.APP_DONE_PROCESSING:
            self.app_ends.append((app, app_action, event_type, timestamp, attribute_name, resource, additional_details))
        else:
            self.reports.append((app, app_action, event_type, timestamp, attribute_name, resource, additional_details))

    def reset(self):
        self.app_starts.clear()
        self.app_ends.clear()
        self.reports.clear()
        self.abort = False
        self.ok_plan = True

    def should_abort(self, app: Application) -> bool:
        return self.abort

    def advise_plan(self, app: 'Application', app_action: str, tranches: List[List["FieldInfo"]]) -> Optional[bool]:
        return self.ok_plan


@dataclass
class App01(Application):
    ns: Namespace
    pod: Pod
    ns_name = "test-app01-ns"


def test01():
    """
    Test basic application creation
    """
    client = MockApiClient(fail_on_verb='get')
    ta01: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta01.client = client
    assert ta01.create(dry_run="All")
    assert client.call_count == 4, f"Expected 4 calls, got {client.call_count}"
    assert client.post_count == 2, f"Expected 2 posts, got {client.post_count}"


def test02():
    """
    Test that TestApp01 calls the reporter the proper number of times
    """
    client = MockApiClient(fail_on_verb='get')
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    ta02.set_reporter(reporter)
    assert ta02.create(dry_run="All")
    assert len(reporter.app_starts) == 1, f"Expected 1 op start, got {len(reporter.app_starts)}"
    assert len(reporter.app_ends) == 1, f"Expected 1 op end, got {len(reporter.app_ends)}"
    assert len(reporter.reports) == 8, f"Expected 10 reports, got {len(reporter.reports)}"


def test03():
    """
    Test that a created app has the proper metadata keys in all components
    """
    client = MockApiClient(fail_on_verb='get')
    ta03: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta03.client = client
    reporter = MockReporter()
    ta03.set_reporter(reporter)
    assert ta03.create(dry_run="All")
    instance_id = ta03.instance_id
    key = get_app_instance_label_key()
    f: Field
    for f in fields(ta03):
        if issubclass(f.type, HikaruDocumentBase):
            rsrc = getattr(ta03, f.name)
            assert key in rsrc.metadata.labels, f"labels: {rsrc.metadata.labels}"
            assert rsrc.metadata.labels[key] == instance_id, f"value for key {key} is '{rsrc.metadata.labels[key]}', not '{instance_id}'"


@dataclass
class App02(Application):
    pod: Pod
    ns: Namespace
    pod2: Pod
    ns_name = "test-app02-ns"


def test04():
    """
    Check that namespaces are created first
    """
    client = MockApiClient(fail_on_verb='get')
    ta04: App02 = App02(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app02-pod", namespace=App02.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app02-pod2", namespace=App02.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                            image="test-app01-image")])))
    ta04.client = client
    reporter = MockReporter()
    ta04.set_reporter(reporter)
    assert ta04.create(dry_run="All")
    ns_idx = -1
    pod_idx = -1
    pod2_idx = -1
    for i, report_rec in enumerate(reporter.reports):
        if report_rec[2] == Reporter.RSRC_START_PROCESSING:
            if report_rec[4] == 'ns':
                ns_idx = i
            elif report_rec[4] == 'pod':
                pod_idx = i
            elif report_rec[4] == "pod2":
                pod2_idx = i
            else:
                assert False, f"Unexpected resource found: {report_rec[4]}"
    assert ns_idx != -1
    assert pod_idx != -1
    assert pod2_idx != -1
    assert ns_idx < pod_idx, f"ns_idx is {ns_idx}, pod_idx is {pod_idx}"
    assert ns_idx < pod2_idx, f"ns_idx is {ns_idx}, pod_idx os {pod_idx}"


@dataclass
class T5Namespace(Namespace):
    pass


@dataclass
class App05(Application):
    pod: Pod
    ns: T5Namespace
    pod2: Pod
    ns_name = "test-app05-ns"


def test05():
    """
    Make sure that derived classes of namespace go first in creation
    """
    client = MockApiClient(fail_on_verb='get')
    ta05: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                            image="test-app01-image")])))
    ta05.client = client
    reporter = MockReporter()
    ta05.set_reporter(reporter)
    assert ta05.create(dry_run="All")
    ns_idx = -1
    pod_idx = -1
    pod2_idx = -1
    for i, report_rec in enumerate(reporter.reports):
        if report_rec[2] == Reporter.RSRC_START_PROCESSING:
            if report_rec[4] == 'ns':
                ns_idx = i
            elif report_rec[4] == 'pod':
                pod_idx = i
            elif report_rec[4] == "pod2":
                pod2_idx = i
            else:
                assert False, f"Unexpected resource found: {report_rec[4]}"
    assert ns_idx != -1
    assert pod_idx != -1
    assert pod2_idx != -1
    assert ns_idx < pod_idx, f"ns_idx is {ns_idx}, pod_idx is {pod_idx}"
    assert ns_idx < pod2_idx, f"ns_idx is {ns_idx}, pod_idx os {pod_idx}"


def test06():
    """
    check we store the attribute name in the annotations for each rsrc created
    """
    from hikaru.app import _app_resource_attr_annotation_key
    key = get_app_rsrc_attr_annotation_key()
    client = MockApiClient()
    ta06: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                            image="test-app01-image")])))
    ta06.client = client
    assert key == _app_resource_attr_annotation_key
    assert ta06.create(dry_run="All")
    assert ta06.ns.metadata.annotations[key] == 'ns'
    assert ta06.pod2.metadata.annotations[key] == "pod2"
    assert ta06.pod.metadata.annotations[key] == "pod"


def test07():
    """
    Test that the per-thread app instance key is used as intended when creating an app instance
    """
    from hikaru.app import _app_instance_label_key
    test07_ai_key = "test07_app_instance_key"
    set_app_instance_label_key(test07_ai_key)
    client = MockApiClient()
    ta07: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App05.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app05-container",
                                                                            image="test-app05-image")])))
    ta07.client = client
    try:
        assert _app_instance_label_key != get_app_instance_label_key()
        assert ta07.create(dry_run="All")
        assert ta07.instance_id == ta07.ns.metadata.labels[test07_ai_key]
        assert ta07.instance_id == ta07.pod.metadata.labels[test07_ai_key]
        assert ta07.instance_id == ta07.pod2.metadata.labels[test07_ai_key]
    finally:
        set_app_instance_label_key()


def test08():
    """
    Test that an app instance key from one thread is not seen by another thread
    """
    class KeyCollector(object):
        def __init__(self):
            self.key = None

    kc: KeyCollector = KeyCollector()

    def work_func(kc_arg: KeyCollector):
        sleep(0.25)
        set_app_instance_label_key("worker_key")
        kc_arg.key = get_app_instance_label_key()
        set_app_instance_label_key()

    t: Thread = Thread(target=work_func, args=(kc,))
    t.start()
    set_app_instance_label_key("test08-main-key")
    key = get_app_instance_label_key()
    t.join()
    try:
        assert key != kc.key
    finally:
        set_app_instance_label_key()


def test09():
    """
    Test that an app instance key from one thread is not seen by another thread in created resources
    """
    class KeyCollector(object):
        def __init__(self):
            self.key = None
            self.ok = False

    kc: KeyCollector = KeyCollector()
    ta09: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App05.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                            image="test-app09-image")])))
    ta09.client = MockApiClient()

    def work_func(kc_arg: KeyCollector, keytouse: str, app: App05):
        sleep(0.25)
        set_app_instance_label_key(keytouse)
        set_default_release("rel_1_25")
        kc_arg.key = get_app_instance_label_key()
        kc_arg.ok = app.create(dry_run="All")
        # then clear out special key for this thread
        set_app_instance_label_key()

    worker_key = "t09_worker_key"
    t: Thread = Thread(target=work_func, args=(kc, worker_key, ta09))
    t.start()
    set_app_instance_label_key("test09-main-key")
    key = get_app_instance_label_key()
    t.join()
    try:
        assert key != kc.key, f"key: {key}, kc.key:{kc.key}"
        assert kc.ok, f"kc.ok: {kc.ok}"
        assert ta09.ns.metadata.labels[worker_key] == ta09.instance_id
        assert ta09.pod.metadata.labels[worker_key] == ta09.instance_id
        assert ta09.pod2.metadata.labels[worker_key] == ta09.instance_id
    finally:
        set_app_instance_label_key()


def test10():
    """
    Test that dup on basic apps works (only has fields that are resources)
    """
    ta10: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App05.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                            image="test-app09-image")])))
    ta10.client = MockApiClient()
    ta10.create(dry_run="All")
    ta10_copy = ta10.dup()
    assert not ta10_copy.diff(ta10), f"unexpected diffs: {ta10_copy.diff(ta10)}"


def test11():
    """
    Test that a changed dup does create a difference
    """
    ta11: App05 = App05(ns=T5Namespace(metadata=ObjectMeta(name=App05.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=App05.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                        pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=App05.ns_name),
                                 spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                            image="test-app09-image")])))
    ta11.instance_id = "bar"
    ta11_copy = ta11.dup()
    ta11_copy.pod.metadata.labels["foo"] = "bar"
    ta11_copy.pod2.spec.containers[0].image = "wibble"
    ta11_copy.instance_id += "foo"
    diffs = ta11_copy.diff(ta11)
    assert len(diffs) == 3, f"expected 3 diffs, got {len(diffs)}: {diffs}"


@dataclass
class FirstOptional(Application):
    p1: Pod
    p2: Optional[Pod] = None
    p3: Pod = None
    ns = "test-app12-ns"


def test12():
    """
    Test optional fields are processed correctly
    """
    ta12: FirstOptional = FirstOptional(p1=Pod(metadata=ObjectMeta(name="test-app12-pod1", namespace=FirstOptional.ns),
                                               spec=PodSpec(containers=[Container(name="test-app12-container1",
                                                                                  image="test-app12-image1")])))
    ta12.client = MockApiClient()
    ta12.create(dry_run="All")
    assert ta12.p2 is None
    assert ta12.p3 is None


def test13():
    """
    Test clearing the app instance label key

    Ensure that we can clear an app instance label key for a thread and use the global one instead
    """
    old_key = get_app_instance_label_key()
    key_to_set = "test13_key"
    set_global_app_instance_label_key(key_to_set)
    set_app_instance_label_key()
    new_key = get_app_instance_label_key()
    try:
        assert new_key == key_to_set, f"new key: {new_key}, old key: {old_key}, key to set: {key_to_set}"
    finally:
        set_app_instance_label_key(old_key)


def test14():
    """
    Test changing the app resource attribute key
    """
    testkey = "test14_app_attr_rsrc"
    old_key = get_app_rsrc_attr_annotation_key()
    set_app_rsrc_attr_annotation_key(testkey)
    new_key = get_app_rsrc_attr_annotation_key()
    try:
        assert old_key != new_key, f"old: {old_key}  new: {new_key}"
    finally:
        set_app_rsrc_attr_annotation_key(old_key)
    new_key = get_app_rsrc_attr_annotation_key()
    assert old_key == new_key, f"old: {old_key}  new: {new_key}"
    set_app_rsrc_attr_annotation_key()
    globkey = get_app_rsrc_attr_annotation_key()
    set_global_rsrc_attr_annotation_key(testkey)
    new_key = get_app_rsrc_attr_annotation_key()
    try:
        assert new_key == testkey, f"new key:{new_key},  test key:{testkey}"
    finally:
        set_global_rsrc_attr_annotation_key(globkey)
    # the per-thread key should still be the same
    new_key = get_app_rsrc_attr_annotation_key()
    assert new_key != testkey, f"new: {new_key}, test:{testkey}"


def test15():
    """
    make sure when clearing out a key in a new thread there isn't a problem
    """
    checker = [False]

    def worker(the_checker: list):
        set_app_rsrc_attr_annotation_key()
        the_checker[0] = True

    t = Thread(target=worker, args=(checker,))
    t.start()
    t.join()
    assert checker[0], f"checker is {checker}"


@dataclass
class FactoryDefault(Application):
    p: Optional[Pod] = field(default_factory=Pod.get_empty_instance)


def test16():
    """
    Check we handle a field with a default factory
    """
    fd: FactoryDefault = FactoryDefault()
    assert fd.p
    assert isinstance(fd.p, Pod)


@dataclass
class BadAttrClass17(Application):
    bad: Optional[ObjectMeta]


def test17():
    """
    Test we flag a bad type; a Hikaru model class but not a HikaruDocumentBase
    """
    try:
        b = BadAttrClass17(bad=ObjectMeta.get_empty_instance())
        b.create(dry_run=True)
        assert False, "should have raised"
    except TypeError:
        pass


@dataclass
class BadAttrClass18(Application):
    bunchOPods: List[Pod] = field(default_factory=list)


def test18():
    """
    Flag the presences of an attribute type we can't manage
    """
    try:
        b = BadAttrClass18()
        b.create(dry_run=True)
        assert False, "should have raised"
    except TypeError:
        pass


@dataclass
class CRDForT19(HikaruDocumentBase, HikaruCRDDocumentMixin):
    metadata: ObjectMeta = None
    apiVersion: str = "example/v1"
    kind: str = "CRDForT19"


@dataclass
class T19App(Application):
    d: Deployment = field(default_factory=Deployment.get_empty_instance)
    crd: CRDForT19 = field(default_factory=CRDForT19.get_empty_instance)
    ns: Namespace = field(default_factory=Namespace.get_empty_instance)
    v: StorageClass = field(default_factory=StorageClass.get_empty_instance)


def test19():
    """
    Check that we order processing all the fields properly
    """
    i: T19App = T19App()
    p1, p2, p3, p4 = i._compute_create_order()
    assert len(p1) == 1, f"wrong number p1 items: {p1}"
    assert issubclass(p1[0].type, Namespace), f"p1[0] is {p1[0].type}"
    assert len(p2) == 1, f"too manywrong number p2 items: {p2}"
    assert issubclass(p2[0].type, StorageClass), f"p2[0] is {p2[0].type}"
    assert len(p3) == 1, f"wrong number p3 items: {p3}"
    assert issubclass(p3[0].type, Deployment), f"p3[0] is {p3[0].type}"
    assert len(p4) == 1, f"wrong number p4 items: {p4}"
    assert issubclass(p4[0].type, CRDForT19), f"p4[0] is {p4[0].type}"


@dataclass
class T20App(Application):
    ns: Namespace


def test20():
    """
    Check that a field that is supposed to have a value but doesn't raises
    """
    i: T20App = T20App(ns=None)
    try:
        i.create(dry_run=True)
        assert False, "we should not have been able to create"
    except ValueError:
        pass


def test21():
    """
    Handle exception when creating
    """
    def tweak_mock(m: MockApiClient, verb: str):
        if verb == "get":
            m.fail_on_verb = "post"

    i: T20App = T20App(ns=Namespace(metadata=ObjectMeta(name="t21")))
    i.client = MockApiClient(fail_on_verb='get', tweaker_func=tweak_mock)
    try:
        res = i.create(dry_run="All")
    except ApiException:
        pass


@dataclass
class Merger(Application):
    ns1: Optional[Namespace] = None
    ns2: Optional[Namespace] = None
    p1: Optional[Pod] = None
    p2: Optional[Pod] = None


def test22():
    """
    Exercise merging
    """
    merge_into = Merger(ns1=None,
                        ns2=Namespace(metadata=ObjectMeta(name="into")),
                        p1=Pod(metadata=ObjectMeta(name="test-app22-pod1",
                                                   namespace="into",
                                                   labels={"wibble": "wobble"}),
                               spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                  image="test-app01-image")])),
                        p2=None)
    orig_into = merge_into.dup()
    merge_from = Merger(ns1=Namespace.get_empty_instance(),
                        ns2=Namespace.get_empty_instance(),
                        p1=Pod.get_empty_instance(),
                        p2=Pod(metadata=ObjectMeta(name="test-app22-pod2",
                                                   namespace="into",
                                                   labels={"wibble": "bobble",
                                                           "willie": "wonka"}),
                               spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                  image="test-app01-image")])))
    merge_into.merge(merge_from)
    assert merge_into.p2.metadata.name == "test-app22-pod2"
    assert merge_into.p2.metadata.labels["wibble"] == "bobble"
    assert merge_into.ns1
    assert not merge_into.ns1.metadata
    # assert not merge_into.ns2.metadata   # this fails, but maybe it should???


@dataclass
class EmptyApp(Application):
    dep: Deployment
    ns: Namespace
    pod: Pod


def test23():
    """
    Check getting an empty instance
    """
    i: EmptyApp = EmptyApp.get_empty_instance()
    assert i.dep
    assert i.ns
    assert i.pod


@dataclass
class RoundTheHorn(Application):
    ns: Namespace
    pod: Pod
    dep: Optional[Deployment] = None


def test24():
    """
    Test going to/from a dict
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    d = i.get_clean_dict()
    i_prime: RoundTheHorn = RoundTheHorn.from_dict(d)
    diffs = i_prime.diff(i)
    assert not diffs


def test25():
    """
    Test going to/from JSON
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app25-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app25-container",
                                                                      image="test-app25-image")])))
    j = i.get_json()
    i_prime: RoundTheHorn = RoundTheHorn.from_json(j)
    diffs = i_prime.diff(i)
    assert not diffs


def test26():
    """
    Test going to/from YAML
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app26-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app26-container",
                                                                      image="test-app26-image")])))
    j = i.get_yaml()
    i_prime: RoundTheHorn = RoundTheHorn.from_yaml(yaml=j)
    diffs = i_prime.diff(i)
    assert not diffs


@dataclass
class FindByNameApp(Application):
    p1: Pod
    p2: Pod
    d1: Deployment


def test27():
    """
    Test findByName for a class that will result in multiple hits
    """
    i: FindByNameApp = FindByNameApp(p1=Pod(metadata=ObjectMeta(name="p1",
                                                                namespace="t27"),
                                            spec=PodSpec(containers=[Container(name="t27-p1-container",
                                                                               image="t27-p1-image")])),
                                     p2=Pod(metadata=ObjectMeta(name="p2",
                                                                namespace="t27"),
                                            spec=PodSpec(containers=[Container(name="t27-p2-container",
                                                                               image="t27-p2-image")])),
                                     d1=Deployment(metadata=ObjectMeta(name="d1",
                                                                       namespace="t27"),
                                                   spec=DeploymentSpec(selector=LabelSelector(),
                                                                       template=PodTemplateSpec(metadata=ObjectMeta(name="t27spec"),
                                                                                        spec=PodSpec(containers=[
                                                                                            Container(name="t27-d1-spec",
                                                                                                      image="t27-d1-img")
                                                                                        ])))))
    results1 = i.find_by_name("spec")
    assert len(results1) == 4, f"got {len(results1)} results"
    for result in results1:
        assert result.path[0] in {"p1", "p2", "d1"}, f"path {result.path} starts with unexpected element"
    results2 = i.find_by_name("spec", following="d1")
    assert len(results2) == 2, f"got {len(results2)} results"
    for result in results2:
        assert result.path[0] in {"p1", "p2", "d1"}, f"path {result.path} starts with unexpected element"
    results3 = i.find_by_name("spec", following="d1.template")
    assert len(results3) == 1, f"got {len(results3)} results"
    for result in results3:
        assert result.path[0] in {"p1", "p2", "d1"}, f"path {result.path} starts with unexpected element"
    results4 = i.find_by_name("spec", following=["d1", "template"])
    assert len(results4) == 1, f"got {len(results4)} results"
    for result in results4:
        assert result.path[0] in {"p1", "p2", "d1"}, f"path {result.path} starts with unexpected element"


def test28():
    """
    Check that if we say 'no' to the plan nothing goes forward
    """
    client = MockApiClient()
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                   image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    reporter.ok_plan = False
    ta02.set_reporter(reporter)
    assert not ta02.create(dry_run="All")
    assert len(reporter.app_starts) == 0


def test29():
    """
    Check we handle other status codes besides 404
    """
    client = MockApiClient(fail_on_verb="get", gen_failure_code=420)
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    ta02.set_reporter(reporter)
    try:
        assert not ta02.create(dry_run="All")
    except ApiException as e:
        assert e.status == 420
    assert len(reporter.app_starts) == 1
    assert len(reporter.reports) == 4


def test30():
    """
    Test that we handle some other exception from below with grace and control
    """
    client = MockApiClient(fail_on_verb="get", gen_failure_code=420, use_exception=NotImplementedError)
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    ta02.set_reporter(reporter)
    try:
        assert not ta02.create(dry_run="All")
    except ApiException as e:
        assert False, "should have raised NotImplementedError"
    except NotImplementedError as _:
        pass
    assert len(reporter.app_starts) == 1
    assert len(reporter.reports) == 4


def test31():
    """
    Abort a delete's plan
    """
    client = MockApiClient()
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                   image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    reporter.ok_plan = False
    ta02.set_reporter(reporter)
    assert not ta02.delete(dry_run="All")
    assert len(reporter.app_starts) == 0


def test32():
    """
    Test the basic update flow
    """
    client = MockApiClient()
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                   image="test-app01-image")])))
    ta02.client = client
    reporter = MockReporter()
    ta02.set_reporter(reporter)
    assert ta02.create(dry_run="All")
    ta02.pod.metadata.labels["new-label"] = "summat"
    assert ta02.update(dry_run="All")


def test33():
    """
    Test that we can't diff the wrong objects
    """
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                   image="test-app01-image")])))
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    try:
        ta02.diff(i)
        assert False, "should have raised a ValueError"
    except TypeError:
        pass


def test34():
    """
    Make sure diff notes when something is missing
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])),
                                   dep=Deployment.get_empty_instance())
    i_copy = i.dup()
    i_copy.dep = None
    diffs = i.diff(i_copy)
    assert 'dep' in diffs
    assert len(diffs['dep']) == 1
    assert diffs['dep'][0].diff_type == DiffType.REMOVED


def test35():
    """
    Make sure diff notes when something is added
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    i_copy = i.dup()
    i_copy.dep = Deployment.get_empty_instance()
    diffs = i.diff(i_copy)
    assert 'dep' in diffs
    assert len(diffs['dep']) == 1
    assert diffs['dep'][0].diff_type == DiffType.ADDED


def test36():
    """
    Make sure we can't merge dissimilar objects
    """
    ta02: App01 = App01(ns=Namespace(metadata=ObjectMeta(name=App01.ns_name)),
                        pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=App01.ns_name),
                                spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                   image="test-app01-image")])))
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    try:
        ta02.merge(i)
        assert False, "should have raised a ValueError"
    except TypeError:
        pass


def test37():
    """
    make sure we can find diff paths
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    i_copy = i.dup()
    i_copy.dep = Deployment.get_empty_instance()
    diffs = i.diff(i_copy)
    o = i_copy.object_at_path(diffs['dep'][0].path)
    assert isinstance(o, Deployment)
    # while we're at it, let's make sure that if we have a bad path we get and attr error
    try:
        i_copy.object_at_path(["NOT_THERE"])
        assert False, "we should have had an AttributeError"
    except AttributeError:
        pass


def test38():
    """
    Check some of the edge cases for object_at_path()
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    o = i.object_at_path(['dep'])
    assert o is None
    try:
        _ = i.object_at_path(['dep', 'metadata'])
        assert False, "should have raised a RuntimeError"
    except RuntimeError:
        pass


def test39():
    """
    Exercise the get_type_warnings() method
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    tw = i.get_type_warnings()
    assert len(tw) == 3
    assert len(tw['dep']) == 0
    i.dep = Pod.get_empty_instance()
    tw = i.get_type_warnings()
    assert len(tw) == 3
    assert len(tw['dep']) != 0
    i.dep = None
    i.pod = None
    tw = i.get_type_warnings()
    assert len(tw) == 3
    assert len(tw['dep']) == 0
    assert len(tw['pod']) != 0
    i.pod = PodSpec.get_empty_instance()
    tw = i.get_type_warnings()
    assert len(tw) == 3
    assert len(tw['pod']) != 0


def test40():
    """
    Test find uses of class
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])))
    uses = i.find_uses_of_class(Pod)
    assert len(uses) == 1
    uses = i.find_uses_of_class(Deployment)
    assert len(uses) == 0
    try:
        _ = i.find_uses_of_class(PodSpec)
        assert False, "Should have raised a TypeError"
    except TypeError:
        pass
    try:
        _ = i.find_uses_of_class(HikaruDocumentBase)
        assert  False, "Should have raised a TypeError"
    except TypeError:
        pass


def test41():
    """
    Try creating a watcher on an app
    """
    i: RoundTheHorn = RoundTheHorn(ns=Namespace(metadata=ObjectMeta(name="round_the_horn")),
                                   pod=Pod(metadata=ObjectMeta(name="test-app24-pod", namespace="round_the_horn"),
                                   spec=PodSpec(containers=[Container(name="test-app24-container",
                                                                      image="test-app24-image")])),
                                   dep=Deployment.get_empty_instance())
    _ = AppWatcher(i)
    # this is just loading a MultiplexingWatcher with the contents of the app


if __name__ == "__main__":
    for k, v in dict(globals()).items():
        if k.startswith("test") and callable(v):
            try:
                v()
            except Exception as e:
                print(f"test {k} failed with {e}")
