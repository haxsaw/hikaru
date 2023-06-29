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
from typing import cast
from kubernetes import config
from hikaru import *
from hikaru.model.rel_1_23.v1 import *
from hikaru.app import Application, Reporter

cwd = getcwd()
if cwd.endswith('/e2e'):
    # then we're running in the e2e directory itself
    base_path = Path('../test_yaml')
else:
    # assume we're running in the parent directory
    base_path = Path('test_yaml')
del cwd

test_ns = "crud-test-ns-1-23"


def beginning():
    set_default_release("rel_1_23")
    config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")


def ending():
    pass


@dataclass
class TestCRUD_1_23(Application):
    dep: Deployment
    ns: Namespace

    @classmethod
    def standard_instance(cls, namespace: str):
        path = base_path / 'apps-deployment.yaml'
        dep = cast(Deployment, load_full_yaml(path=str(path))[0])
        app = TestCRUD_1_23(dep=dep, ns=Namespace(metadata=ObjectMeta(name=namespace)))
        return app


def test01():
    """
    Testing delete first so we have something that can wipe out a created app
    """
    app: TestCRUD_1_23 = TestCRUD_1_23.standard_instance(test_ns + "test01")
    assert app.delete()


def test02():
    """
    Testing create
    """
    app: TestCRUD_1_23 = TestCRUD_1_23.standard_instance(test_ns + "test02")
    assert app.create()
    assert app.delete()


def test03():
    """
    Test read for an existing app
    """
    bad_diff_types = {DiffType.INCOMPATIBLE_DIFF, DiffType.TYPE_CHANGED, DiffType.REMOVED, DiffType.VALUE_CHANGED}
    app: TestCRUD_1_23 = TestCRUD_1_23.standard_instance(test_ns + "test03")
    assert app.create()
    try:
        read_app: TestCRUD_1_23 = TestCRUD_1_23.read(instance_id=app.instance_id)
        assert read_app is not None
        assert read_app.instance_id == app.instance_id
        diffs: Dict[str, List[DiffDetail]] = app.diff(read_app)
        for attr, l in diffs.items():
            for d in l:
                assert d.diff_type not in bad_diff_types, f"diff type {d.diff_type} found in {attr} with path {d.path}"
    finally:
        app.delete()
