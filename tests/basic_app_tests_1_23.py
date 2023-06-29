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
from hikaru.model.rel_1_23.v1 import *
from hikaru.app import Application, Reporter
from hikaru.app import (get_app_instance_label_key, get_app_rsrc_attr_annotation_key,
                        set_app_instance_label_key)
from dataclasses import dataclass, Field, fields


set_default_release("rel_1_23")


class CRDTestExp(Exception):
    pass


class MockApiClient(object):
    def __init__(self, gen_failure=False, raise_exp=False, fail_on_verb=None):
        self.body = None
        self.client_side_validation = 1
        self.gen_failure = gen_failure
        self.raise_exp = raise_exp
        self.fail_on_verb = fail_on_verb.lower() if isinstance(fail_on_verb, str) else fail_on_verb
        self.call_count = 0
        self.post_count = 0
        self.put_count = 0
        self.get_count = 0

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
            raise ApiException(404, "Synthetic not found", {})
        if self.raise_exp:
            raise CRDTestExp("Synthetic failure")
        if isinstance(body, dict) and body:
            body = from_dict(body)
        self.body = body
        return self.body, 400 if self.gen_failure else 200, {}


class TestingReporter(Reporter):
    def __init__(self):
        super(TestingReporter, self).__init__()
        self.app_starts = []
        self.app_ends = []
        self.reports = []
        self.abort = False

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

    def should_abort(self, app: Application) -> bool:
        return self.abort


@dataclass
class TestApp01(Application):
    ns: Namespace
    pod: Pod
    ns_name = "test-app01-ns"


def test01():
    """
    Test basic application creation
    """
    client = MockApiClient(fail_on_verb='get')
    ta01: TestApp01 = TestApp01(ns=Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=TestApp01.ns_name),
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
    ta02: TestApp01 = TestApp01(ns=Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=TestApp01.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta02.client = client
    reporter = TestingReporter()
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
    ta03: TestApp01 = TestApp01(ns=Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app01-pod", namespace=TestApp01.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])))
    ta03.client = client
    reporter = TestingReporter()
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
class TestApp02(Application):
    pod: Pod
    ns: Namespace
    pod2: Pod
    ns_name = "test-app02-ns"


def test04():
    """
    Check that namespaces are created first
    """
    client = MockApiClient(fail_on_verb='get')
    ta04: TestApp02 = TestApp02(ns=Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app02-pod", namespace=TestApp02.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app02-pod2", namespace=TestApp02.ns_name),
                                         spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                            image="test-app01-image")])))
    ta04.client = client
    reporter = TestingReporter()
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
class Test5Namespace(Namespace):
    pass


@dataclass
class TestApp05(Application):
    pod: Pod
    ns: Test5Namespace
    pod2: Pod
    ns_name = "test-app05-ns"


def test05():
    """
    Make sure that derived classes of namespace go first in creation
    """
    client = MockApiClient(fail_on_verb='get')
    ta05: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
                                         spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                            image="test-app01-image")])))
    ta05.client = client
    reporter = TestingReporter()
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
    from hikaru_app import _app_resource_attr_annotation_key
    key = get_app_rsrc_attr_annotation_key()
    client = MockApiClient()
    ta06: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp01.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
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
    from hikaru_app import _app_instance_label_key
    test07_ai_key = "test07_app_instance_key"
    set_app_instance_label_key(test07_ai_key)
    client = MockApiClient()
    ta07: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp05.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app05-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app01-container",
                                                                           image="test-app01-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
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
    ta09: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp05.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
                                         spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                            image="test-app09-image")])))
    ta09.client = MockApiClient()

    def work_func(kc_arg: KeyCollector, keytouse: str, app: TestApp05):
        sleep(0.25)
        set_app_instance_label_key(keytouse)
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
        assert key != kc.key
        assert kc.ok
        assert ta09.ns.metadata.labels[worker_key] == ta09.instance_id
        assert ta09.pod.metadata.labels[worker_key] == ta09.instance_id
        assert ta09.pod2.metadata.labels[worker_key] == ta09.instance_id
    finally:
        set_app_instance_label_key()


def test10():
    """
    Test that dup on basic apps works (only has fields that are resources)
    """
    ta10: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp05.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
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
    ta11: TestApp05 = TestApp05(ns=Test5Namespace(metadata=ObjectMeta(name=TestApp05.ns_name)),
                                pod=Pod(metadata=ObjectMeta(name="test-app09-pod", namespace=TestApp05.ns_name),
                                        spec=PodSpec(containers=[Container(name="test-app09-container",
                                                                           image="test-app09-image")])),
                                pod2=Pod(metadata=ObjectMeta(name="test-app05-pod2", namespace=TestApp05.ns_name),
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


if __name__ == "__main__":
    for k, v in dict(globals()).items():
        if k.startswith("test") and callable(v):
            try:
                v()
            except Exception as e:
                print(f"test {k} failed with {e}")
