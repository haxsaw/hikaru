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

from os import getcwd
from pathlib import Path
from threading import Thread
import time
from kubernetes import config
from hikaru import set_global_default_release, load_full_yaml
from hikaru.model.rel_1_21 import Pod, Namespace, ObjectMeta
from hikaru.watch import Watcher, MultiplexingWatcher, WatchEvent

set_global_default_release('rel_1_21')

config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd

watch21_namespace = 'watcher-tests-21'


def test01():
    """
    test01: simple watcher test; timeout after load
    """
    w = Watcher(Pod, timeout_seconds=1)
    count = 0
    for we in w.stream(manage_resource_version=True, quit_on_timeout=True):
        assert isinstance(we.obj, Pod), f'got a {we.obj.__name__}, not a Pod'
        count += 1
    assert count > 0, 'got no Pod events'


def make_namespace(name):
    def do_it(nsname):
        time.sleep(0.1)
        ns = Namespace(metadata=ObjectMeta(name=nsname))
        ns.create()
        time.sleep(0.1)
        ns.delete()

    t = Thread(target=do_it, args=(name,))
    t.start()


def make_pod(name, nsname):
    def do_it(podname, ns):
        time.sleep(0.1)
        path = base_path / "core-pod.yaml"
        pod: Pod = load_full_yaml(path=str(path))[0]
        pod.metadata.name = podname
        pod.metadata.namespace = ns
        pod.create()
        time.sleep(0.1)
        pod.delete()

    t = Thread(target=do_it, args=(name, nsname))
    t.start()


def drain(w: Watcher) -> int:
    highest_rv = 0
    for we in w.stream(manage_resource_version=True, quit_on_timeout=True):
        rv = int(we.obj.metadata.resourceVersion)
        if rv > highest_rv:
            highest_rv = rv
    return highest_rv


def test02():
    """
    test02: watch for namespace events, create/delete a namespace
    """
    w = Watcher(Namespace)
    ns_name = "w21-test02-watch"
    highest_rv = drain(w)
    w = Watcher(Namespace, resource_version=highest_rv)
    make_namespace(ns_name)
    for we in w.stream(manage_resource_version=True, quit_on_timeout=True):
        assert isinstance(we.obj, Namespace)
        if we.obj.metadata.name == ns_name and we.etype == "DELETED":
            w.stop()


def test03():
    """
    test03: check we get all the events we expect for a create/delete
    """
    w = Watcher(Namespace)
    highest_rv = drain(w)
    w.update_resource_version(highest_rv)
    ns_name = 'w21-test03-watcher'
    expected_types = {'ADDED', 'MODIFIED', 'DELETED'}
    make_namespace(ns_name)
    seen_types = set()
    for we in w.stream(manage_resource_version=True, quit_on_timeout=False):
        assert isinstance(we.obj, Namespace)
        if we.obj.metadata.name != ns_name:
            continue
        seen_types.add(we.etype)
        if we.etype == 'DELETED':
            w.stop()
    assert expected_types == seen_types


def dump(we: WatchEvent):
    print(f"e:{we.etype} t:{we.obj.kind} n:{we.obj.metadata.name} ns:"
          f"{we.obj.metadata.namespace}")


def test04():
    """
    test04: check basic mux operation
    """
    ns_name = 'w21-test04-watch'
    podname = 'test04-pod'

    nsw = Watcher(Namespace)
    hns = drain(nsw)
    nsw.update_resource_version(hns)

    pw = Watcher(Pod, namespace=ns_name)
    hp = drain(pw)
    pw.update_resource_version(hp)

    mux = MultiplexingWatcher()
    mux.add_watcher(nsw)
    mux.add_watcher(pw)
    expected = {'ADDED', 'MODIFIED', 'DELETED'}
    pod_seen = set()
    ns_seen = set()
    make_namespace(ns_name)
    make_pod(podname, ns_name)
    stopped_mux = False
    for we in mux.stream(manage_resource_version=True, quit_on_timeout=False):
        if we.obj.kind == 'Pod' and we.obj.metadata.namespace == ns_name:
            pod_seen.add(we.etype)
        elif we.obj.kind == 'Namespace' and we.obj.metadata.name == ns_name:
            ns_seen.add(we.etype)
        if 'DELETED' in pod_seen and 'DELETED' in ns_seen:
            stopped_mux = True
            mux.stop()
    assert stopped_mux, "the mux exited via timeout or loss of watchers"
    assert expected == ns_seen, f'Not enough namespace events: {expected-ns_seen}'
    assert expected == pod_seen, f'Not enough pod events: {expected-pod_seen}'


def test05():
    """
    test05: check adding a Watcher on the fly to the mux
    """
    ns_name = 'w21-test05-watch'
    podname = 'test05-pod'

    nsw = Watcher(Namespace)
    hns = drain(nsw)
    nsw.update_resource_version(hns)

    pw = Watcher(Pod, namespace=ns_name)
    hp = drain(pw)
    pw.update_resource_version(hp)

    mux = MultiplexingWatcher()
    mux.add_watcher(nsw)
    expected = {'ADDED', 'MODIFIED', 'DELETED'}
    pod_seen = set()
    ns_seen = set()
    make_namespace(ns_name)
    make_pod(podname, ns_name)
    stopped_mux = False
    first = True
    for we in mux.stream(manage_resource_version=True, quit_on_timeout=False):
        if first:
            first = False
            mux.add_watcher(pw)
        if we.obj.kind == 'Pod' and we.obj.metadata.namespace == ns_name:
            pod_seen.add(we.etype)
        elif we.obj.kind == 'Namespace' and we.obj.metadata.name == ns_name:
            ns_seen.add(we.etype)
        if 'DELETED' in pod_seen and 'DELETED' in ns_seen:
            stopped_mux = True
            mux.stop()
    assert stopped_mux, "the mux exited via timeout or loss of watchers"
    assert expected == ns_seen, f'Not enough namespace events: {expected-ns_seen}'
    assert expected == pod_seen, f'Not enough pod events: {expected-pod_seen}'



if __name__ == "__main__":
    for k, v in dict(globals()).items():
        if callable(v) and k.startswith('test'):
            print(f'running {k}')
            try:
                v()
            except Exception as e:
                print(f'{k} failed with {e}')
