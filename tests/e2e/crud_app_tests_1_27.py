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
from dataclasses import dataclass
from os import getcwd
from pathlib import Path
import time
from typing import cast
from kubernetes import config
from kubernetes.client.exceptions import ApiException
from hikaru import *
from hikaru.model.rel_1_27.v1 import *
from hikaru.app import Application, Reporter
import pytest

set_default_release("rel_1_27")

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd

test_ns = "crud-app-test-ns-1-27"


def beginning():
    set_default_release("rel_1_27")
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    return True


def ending():
    pass


@pytest.fixture(scope="module", autouse=True)
def setup():
    res = beginning()
    yield res
    ending()


@dataclass
class CRUD_1_27(Application):
    dep: Deployment
    ns: Namespace

    @classmethod
    def standard_instance(cls, namespace: str):
        path = base_path / 'apps-deployment.yaml'
        dep = cast(Deployment, load_full_yaml(path=str(path))[0])
        dep.metadata.namespace = namespace
        app = CRUD_1_27(dep=dep, ns=Namespace(metadata=ObjectMeta(name=namespace)))
        return app


def test01():
    """
    Testing delete first so we have something that can wipe out a created app
    """
    app: CRUD_1_27 = CRUD_1_27.standard_instance(test_ns + "test01")
    result = False
    try:
        _ = app.delete()
    except ApiException as e:
        if e.status != 404:
            raise


def test02():
    """
    Testing create
    """
    app: CRUD_1_27 = CRUD_1_27.standard_instance(test_ns + "test02")
    assert app.create()
    assert app.delete()


def test03():
    """
    Test read for an existing app
    """
    ignore_attrs = {'resourceVersion', 'deployment.kubernetes.io/revision', 'managedFields', 'observedGeneration',
                    'unavailableReplicas', 'conditions'}
    bad_diff_types = {DiffType.INCOMPATIBLE_DIFF, DiffType.TYPE_CHANGED, DiffType.REMOVED, DiffType.VALUE_CHANGED}
    app: CRUD_1_27 = CRUD_1_27.standard_instance(test_ns + "test03")
    assert app.create()
    try:
        read_app: CRUD_1_27 = CRUD_1_27.read(instance_id=app.instance_id)
        assert read_app is not None
        assert read_app.instance_id == app.instance_id
        diffs: Dict[str, List[DiffDetail]] = app.diff(read_app)
        for attr, l in diffs.items():
            assert attr == "dep", f"unexpected attribute in diff: {attr}"
            for d in l:
                assert d.attrname in ignore_attrs, f"unexpected diff attr in dep: {d.attrname}"
    finally:
        app.delete()


def test04():
    """
    Perform an update on an app's components
    """
    app: CRUD_1_27 = CRUD_1_27.standard_instance(test_ns + "-test04")
    assert app.create()
    try:
        app = CRUD_1_27.read(app.instance_id)
        app = CRUD_1_27.read(app.instance_id)
        time.sleep(0.2)
        app = CRUD_1_27.read(app.instance_id)
        app.dep.metadata.annotations["test04"] = "dep-change"
        app.ns.metadata.annotations["test04"] = "ns-change"
        app.update()
        new_app: CRUD_1_27 = CRUD_1_27.read(app.instance_id)
        assert new_app.dep.metadata.annotations["test04"] == 'dep-change'
        assert new_app.ns.metadata.annotations['test04'] == 'ns-change'
    finally:
        app.delete()
