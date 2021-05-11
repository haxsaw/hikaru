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
from importlib import import_module
from dataclasses import dataclass, InitVar
from typing import Optional, Any
from unittest import SkipTest
import pytest
from hikaru import *
from hikaru.model.rel_1_16 import *
import json
from hikaru.meta import DiffDetail, DiffType
from hikaru.naming import make_swagger_name, process_swagger_name
from hikaru.version_kind import get_version_kind_class

p = None


def setup_pod() -> Pod:
    docs = load_full_yaml(stream=open("test.yaml", "r"))
    pod = docs[0]
    # assert isinstance(pod, Pod)
    return pod


def setup():
    set_default_release('rel_1_16')
    global p
    p = setup_pod()


def test001():
    """
    get the basic machinery creaking to life
    """
    assert isinstance(p, Pod)
    assert p.metadata.name == "hello-kiamol-3", p.metadata.name


def test002():
    """
    ensure the labels are there
    """
    assert isinstance(p, Pod)
    assert p.metadata.labels["lab1"] == "wibble"
    assert p.metadata.labels["lab2"] == "wobble"


def test003():
    """
    look for the ports in the container
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[0].ports[0].containerPort == 3306
    assert p.spec.containers[0].ports[1].containerPort == 3307


def test004():
    """
    add another container
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].name == "db"


def test005():
    """
    check for env vars on second container
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].env) == 2


def test006():
    """
    check for a value of 'here' for first env
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].env[0].value == "here",  \
           f"it was {p.spec.containers[1].env[0].value}"


def test007():
    """
    Check that there's an envFrom with a configMapRef in it
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].configMapRef.name == "test-map"
    assert p.spec.containers[1].envFrom[0].configMapRef.optional is True


def test008():
    """
    Check that an envFrom has a prefix in it
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].prefix == "gabagabahey"


def test009():
    """
    Check that an envFrom handles a secretRef
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].secretRef.name == "seecrit"
    assert p.spec.containers[1].envFrom[0].secretRef.optional is False


def test010():
    """
    Check that volume mounts are processed properly
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].volumeMounts[0].mountPath == "/opt"
    assert p.spec.containers[1].volumeMounts[0].name == "opt-mount"
    assert p.spec.containers[1].volumeMounts[0].mountPropagation == "wibble"
    assert p.spec.containers[1].volumeMounts[0].readOnly is True
    assert p.spec.containers[1].volumeMounts[0].subPath == ""
    assert p.spec.containers[1].volumeMounts[0].subPathExpr == ""


def test011():
    """
    Check that volume devices is handled properly
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].volumeDevices[0].devicePath == "/dev/sd0a"
    assert p.spec.containers[1].volumeDevices[0].name == "root-disk"


def test012():
    """
    check that resources are respected
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].resources.limits["cores"] == 4
    assert p.spec.containers[1].resources.limits["mem-mb"] == 500
    assert p.spec.containers[1].resources.requests["cores"] == 3
    assert p.spec.containers[1].resources.requests["mem-mb"] == 400


def test013():
    """
    check that exec in lifecyle postStart works ok
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].lifecycle.postStart.exec.command) == 3


def test014():
    """
    check that httpGet in lifecyle postStart works
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].lifecycle.postStart.httpGet.port == "80"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.host == 'localhost'
    assert p.spec.containers[1].lifecycle.postStart.httpGet.path == "/home"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.scheme == "https"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.httpHeaders[0].name == \
           "Content-Disposition"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.httpHeaders[0].value == \
           "whatever"


def test015():
    """
    check that tcpSocket in lifecycle postStart works
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].lifecycle.postStart.tcpSocket.port == "1025"
    assert p.spec.containers[1].lifecycle.postStart.tcpSocket.host == "devnull"


def test016():
    """
    check exec lifecyle in pre_stop
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].lifecycle.preStop.exec.command) == 3


def test017():
    """
    check for the terminationPolicy items
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].terminationMessagePath == "/goodbye/cruel/world.txt"
    assert p.spec.containers[1].terminationMessagePolicy == "File"


def test018():
    """
    check livenessProbe
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].livenessProbe.exec.command) == 3
    assert p.spec.containers[1].livenessProbe.exec.command[0] == "probe-cmd"
    assert p.spec.containers[1].livenessProbe.initialDelaySeconds == 30
    assert p.spec.containers[1].livenessProbe.periodSeconds == 5
    assert p.spec.containers[1].livenessProbe.timeoutSeconds == 3
    assert p.spec.containers[1].livenessProbe.failureThreshold == 4
    assert p.spec.containers[1].livenessProbe.successThreshold == 2


def test019():
    """
    check readinessProbe
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].readinessProbe.exec.command) == 4
    assert p.spec.containers[1].readinessProbe.exec.command[0] == "probe-cmd2"
    assert p.spec.containers[1].readinessProbe.initialDelaySeconds == 31
    assert p.spec.containers[1].readinessProbe.periodSeconds == 4
    assert p.spec.containers[1].readinessProbe.timeoutSeconds == 2
    assert p.spec.containers[1].readinessProbe.failureThreshold == 3
    assert p.spec.containers[1].readinessProbe.successThreshold == 1


def test020():
    """
    check the flat items in securityContext of containers
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].securityContext.runAsUser == 1001
    assert p.spec.containers[1].securityContext.runAsNonRoot is True
    assert p.spec.containers[1].securityContext.runAsGroup == 55
    assert p.spec.containers[1].securityContext.readOnlyRootFilesystem is False
    assert p.spec.containers[1].securityContext.procMount == "DefaultProcMount"
    assert p.spec.containers[1].securityContext.privileged is False
    assert p.spec.containers[1].securityContext.allowPrivilegeEscalation is True


def test021():
    """
    check the capabilities sub item of securityContext in containers
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].securityContext.capabilities.add) == 3
    assert len(p.spec.containers[1].securityContext.capabilities.drop) == 1
    assert p.spec.containers[1].securityContext.capabilities.add[1] == "read"


def test022():
    """
    check the seccompProfile settings of securityContext
    """
    raise SkipTest("this field doesn't exist in release 1.16")
    assert isinstance(p, Pod)
    assert p.spec.containers[1].securityContext.seccompProfile.type == "summat"
    assert p.spec.containers[1].securityContext.seccompProfile.localhostProfile == \
           "nada"


def test023():
    """
    check the seLinuxOptions item of securityContext
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].securityContext.seLinuxOptions.level == "uno"
    assert p.spec.containers[1].securityContext.seLinuxOptions.role == "dos"
    assert p.spec.containers[1].securityContext.seLinuxOptions.type == "tres"
    assert p.spec.containers[1].securityContext.seLinuxOptions.user == "quattro"


def test024():
    """
    check the windowsOptions item of securityContext
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[
        1].securityContext.windowsOptions.gmsaCredentialSpec == "horrible", 'no horrible'
    assert p.spec.containers[
        1].securityContext.windowsOptions.gmsaCredentialSpecName == "awful", 'no awful'
    assert p.spec.containers[1].securityContext.windowsOptions.runAsUserName == \
           "icky", 'no icky'


def test025():
    """
    check the imagePullSecrets in the pod spec
    """
    assert isinstance(p, Pod)
    assert p.spec.imagePullSecrets[0].name == "one"
    assert p.spec.imagePullSecrets[1].name == "two"


def test026():
    """
    check enableServiceLinks
    """
    assert isinstance(p, Pod)
    assert p.spec.enableServiceLinks is False


def test027():
    """
    check nodeSelector
    """
    assert isinstance(p, Pod)
    assert p.spec.nodeSelector["key1"] == "wibble"
    assert p.spec.nodeSelector["key2"] == "wobble"


def test028():
    """
    check nodeName
    """
    assert isinstance(p, Pod)
    assert p.spec.nodeName == "maxwell"


def test029():
    """
    check schedulerName
    """
    assert isinstance(p, Pod)
    assert p.spec.schedulerName == "cecil"


def test030():
    """
    check runtimeClassName
    """
    assert isinstance(p, Pod)
    assert p.spec.runtimeClassName == "classless"


def test031():
    """
    Use find_by_name to find all containers
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('containers')
    assert len(results) == 2


def test032():
    """
    Use find_by_name to find all exec objects in lifecycles
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following=["containers", "lifecycle"])
    assert len(results) == 2


def test033():
    """
    Same test as test032, but with a single string
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following='containers.lifecycle')
    assert len(results) == 2


def test034():
    """
    Use find_by_name to find all exec objects in the lifecycle of the 2nd container
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following=['containers', 1, 'lifecycle'])
    assert len(results) == 2, f'len is {len(results)}'


def test035():
    """
    Same as test034, but using a single string for following
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following='containers.1.lifecycle')
    assert len(results) == 2, f'len is {len(results)}'


def test036():
    """
    Use find_by_name to find a field with non-consecutive following fields
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('name', following='containers.lifecycle.httpGet')
    assert len(results) == 1


def test037():
    """
    check that equals returns true for the same object
    """
    assert isinstance(p, Pod)
    q = setup_pod()
    assert p == q


def test038():
    """
    check that equals returns False for a tweaked object
    """
    assert isinstance(p, Pod)
    q: Pod = setup_pod()
    q.spec.containers[1].securityContext.capabilities.add.append("wibble")
    assert p != q


def test039():
    """
    check that dup produces equal objects
    """
    assert isinstance(p, Pod)
    q: Pod = p.dup()
    assert p == q


def test040():
    """
    check that a twiddled dup'd object isn't equal
    """
    assert isinstance(p, Pod)
    q: Pod = p.dup()
    q.spec.containers[1].lifecycle.postStart.httpGet.port = "1234"
    assert p != q


def test041():
    """
    get_python_source with the autopep8 style
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test042():
    """
    check that a modified loaded version of p isn't equal
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert isinstance(x, Pod)
    x.spec.containers[1].lifecycle.postStart.httpGet.port = 4
    assert x != p


def test043():
    """
    check that you can render explicitly to autopep8
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style='autopep8')
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test044():
    """
    check that you can render to black
    """
    assert isinstance(p, Pod)
    code = get_python_source(p, style="black")
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test045():
    """
    check that illegal styles are caught
    """
    assert isinstance(p, Pod)
    try:
        code = get_python_source(p, style="groovy")
        assert False, "we should have got an exception about bad style"
    except RuntimeError:
        pass


def test046():
    """
    check that None instead of dict generates a warning
    """
    om = ObjectMeta()
    copy: ObjectMeta = om.dup()
    copy.annotations = None
    warnings = copy.get_type_warnings()
    assert len(warnings) == 1, f"{len(warnings)} warnings"
    assert warnings[0].cls == ObjectMeta
    assert warnings[0].attrname == "annotations"
    assert "empty dict" in warnings[0].warning


def test047():
    """
    check that None instead of a list generates a warning
    """
    om = ObjectMeta()
    copy: ObjectMeta = om.dup()
    copy.finalizers = None
    warnings = copy.get_type_warnings()
    assert len(warnings) == 1, f"{len(warnings)} warnings"
    assert warnings[0].cls == ObjectMeta
    assert warnings[0].attrname == 'finalizers'
    assert "empty list" in warnings[0].warning


def test048():
    """
    check that None instead of a required str generates a warning
    """
    ref: OwnerReference = OwnerReference('v1', 'OwnerReference',
                                         'wibble', '1')
    ref.kind = None
    warnings = ref.get_type_warnings()
    assert len(warnings) == 1, f"{len(warnings)} warnings"
    assert warnings[0].cls == OwnerReference
    assert warnings[0].attrname == "kind"
    assert "should have been" in warnings[0].warning


def test049():
    """
    check that the wrong basic type is gives a warning
    """
    om = ObjectMeta(name=5)
    warnings = om.get_type_warnings()
    assert len(warnings) == 1, f"Got {len(warnings)} warnings"
    assert warnings[0].cls == ObjectMeta
    assert warnings[0].attrname == "name"
    assert "expecting" in warnings[0].warning, f"warning: {warnings[0].warning}"


def test050():
    """
    check the big test Pod for warnings (should be none)
    """
    assert isinstance(p, Pod)
    warnings = p.get_type_warnings()
    wstrings = "\n".join(w.warning for w in warnings)
    assert not warnings, f"warnings: {wstrings}"


def test051():
    """
    check that the wrong contained type in a list generates a warning
    """
    ps = PodSpec(containers=['asdf'])
    warnings = ps.get_type_warnings()
    assert len(warnings) == 1, f"got {len(warnings)} warnings"
    assert len(warnings[0].path) == 2, f"path is {warnings[0].path}"


def test052():
    """
    Put a correct object inside an appropriate list; should be no warnings.
    """
    own = OwnerReference(apiVersion='v1', kind='OwnerReference',
                         name="wibble", uid='1234')
    om = ObjectMeta(ownerReferences=[own])
    warnings = om.get_type_warnings()
    assert len(warnings) == 0, f'got {len(warnings)} warnings'


def test053():
    """
    Put a broken object into the list in another; get warnings
    """
    own = OwnerReference(apiVersion=1, kind='OwnerReference',
                         name='wibble', uid='345')
    om = ObjectMeta(ownerReferences=[own])
    warnings = om.get_type_warnings()
    assert len(warnings) == 1, f'got {len(warnings)} warnings'
    assert len(warnings[0].path) == 3, f'path was {warnings[0].path}'
    assert 0 in warnings[0].path, f'path was {warnings[0].path}'


def test054():
    """
    Put the wrong object inside another; get warnings
    """
    own = OwnerReference(apiVersion=1, kind='OwnerReference',
                         name='wibble', uid='345')
    p = Pod(spec=PodSpec(containers=[own]))
    warnings = p.get_type_warnings()
    assert len(warnings) == 1, f'got {len(warnings)} warnings'
    assert 0 in warnings[0].path, f'path was {warnings[0].path}'


def test055():
    """
    check that a single change is detected by diff
    """
    assert isinstance(p, Pod)
    copy = p.dup()
    del copy.spec.containers[0]
    # copy.spec.containers[1].securityContext.seLinuxOptions.role = 'overlord'
    diffs = p.diff(copy)
    assert len(diffs) == 1
    assert "Length" in diffs[0].report


def test056():
    """
    check a single deeply nested change is detected
    """
    assert isinstance(p, Pod)
    copy = p.dup()
    copy.spec.containers[1].securityContext.seLinuxOptions.role = 'overlord'
    diffs = p.diff(copy)
    assert len(diffs) == 1
    assert len(diffs[0].path) == 6, f'path is {diffs[0].path}'


def test057():
    """
    check different types yield a diff
    """
    assert isinstance(p, Pod)
    diffs = p.diff(p.metadata)
    assert len(diffs) == 1
    assert "Incompatible" in diffs[0].report


def test058():
    """
    check that a type mismatch diff is caught
    """
    om1 = ObjectMeta(clusterName=5)
    om2 = ObjectMeta(clusterName="willie")
    diffs = om2.diff(om1)
    assert len(diffs) == 1
    assert "Type mismatch" in diffs[0].report


def test059():
    """
    check that a value mismatch diff is caught
    """
    om1 = ObjectMeta(namespace='ns1')
    om2 = ObjectMeta(namespace='ns2')
    diffs = om1.diff(om2)
    assert len(diffs) == 1
    assert "Value mismatch" in diffs[0].report


def test060():
    """
    check that dict key differences are caught by diff
    """
    om1 = ObjectMeta(labels={'a': '1', 'b': '2'})
    om2 = ObjectMeta(labels={'a': '1', 'c': '2'})
    diffs = om1.diff(om2)
    assert len(diffs) == 2
    assert any(map(lambda d: d.diff_type == DiffType.ADDED, diffs))
    assert any(map(lambda d: d.diff_type == DiffType.REMOVED, diffs))


def test061():
    """
    check that dict value differences are caught by diff
    """
    om1 = ObjectMeta(labels={'a': '1', 'b': '2'})
    om2 = ObjectMeta(labels={'a': '1', 'b': '99'})
    diffs = om1.diff(om2)
    assert len(diffs) == 1
    assert diffs[0].diff_type == DiffType.VALUE_CHANGED


def test062():
    """
    check that lists with different element types generate a diff
    """
    ps1 = PodSpec(containers=[Container('first')])
    ps2 = PodSpec(containers=[ObjectMeta()])
    diffs = ps1.diff(ps2)
    assert len(diffs) == 1
    assert diffs[0].diff_type == DiffType.INCOMPATIBLE_DIFF


def test063():
    """
    check that lists with elements that don't match are caught
    """
    ps1 = PodSpec(containers=[Container('first')])
    ps2 = PodSpec(containers=[Container('second')])
    diffs = ps1.diff(ps2)
    assert len(diffs) == 1
    assert diffs[0].diff_type == DiffType.VALUE_CHANGED


def test064():
    """
    check we can reload a doc from a get_clean_dict() dump
    """
    assert isinstance(p, Pod)
    d = get_clean_dict(p)
    new_p = from_dict(d)
    assert p == new_p


def test065():
    """
    Check if from_dict works with a named class that was dumped
    """
    ps = PodSpec(containers=[Container('first')])
    d = get_clean_dict(ps)
    new_ps = from_dict(d, cls=PodSpec)
    assert ps == new_ps


def test066():
    """
    Check if we can reload a doc from a get_json() dump
    """
    assert isinstance(p, Pod)
    j = get_json(p)
    new_p = from_json(j)
    assert p == new_p


def test067():
    """
    Check if from_json works with a named class that was dumped
    """
    ps = PodSpec(containers=[Container('first')])
    j = get_json(ps)
    new_ps = from_json(j, cls=PodSpec)
    assert ps == new_ps


def test068():
    """
    Check catching a bad path attribute for a list
    """
    assert isinstance(p, Pod)
    path = ['spec', 'containers', 'lifecycle']
    try:
        o = p.object_at_path(path)
        assert False, 'should have got a gripe about "lifecycle"'
    except ValueError:
        pass


def test069():
    """
    Check catching a bad index for a list
    """
    assert isinstance(p, Pod)
    path = ['spec', 'containers', 99]
    try:
        o = p.object_at_path(path)
        assert False, "should have got a gripe about index 99"
    except IndexError:
        pass


def test070():
    """
    Check catching a bad attribute on a regular object
    """
    assert isinstance(p, Pod)
    path = ['spec', 'containers', 1, 'wibble', 'wobble']
    try:
        o = p.object_at_path(path)
        assert False, "should have got a gripe about attribute 'wibble'"
    except AttributeError:
        pass


def test071():
    """
    Check that repopulating the cataloge doesn't blow up
    """
    assert isinstance(p, Pod)
    p.repopulate_catalog()


def test072():
    """
    Check that find_by_name()'s name parameter check works
    """
    assert isinstance(p, Pod)
    try:
        p.find_by_name(object())
        assert False, "should have gotten a TypeError"
    except TypeError:
        pass


def test073():
    """
    Check that find_by_name()'s following parameter check works
    """
    assert isinstance(p, Pod)
    try:
        p.find_by_name('name', following=object())
        assert False, "should have gotten a TypeError about following"
    except TypeError:
        pass


def test074():
    """
    Check that weird type where there should be an int index is caught
    """
    assert isinstance(p, Pod)
    try:
        p.find_by_name('name', following=['spec', 'containers', object()])
        assert False, "should have gotten a ValueError"
    except ValueError:
        pass


def test075():
    """
    Check that a None in a list raises a gripe
    """
    assert isinstance(p, Pod)
    copy: Pod = p.dup()
    copy.spec.containers.append(None)
    try:
        o = copy.object_at_path(["spec", "containers", 2])
        assert False, "should have gotten a RuntimeError"
    except RuntimeError:
        pass


def test076():
    """
    Check a bad attr is found an griped about
    """
    assert isinstance(p, Pod)
    path = [object()]
    try:
        o = p.object_at_path(path)
        assert False, "should have gotten an TypeError"
    except TypeError:
        pass


def test077():
    """
    Find an object properly
    """
    assert isinstance(p, Pod)
    path = ['spec', 'containers', 0]
    con = p.object_at_path(path)
    assert isinstance(con, Container)


def test078():
    """
    Make a diff detail on a basic string
    """
    assert isinstance(p, Pod)
    copy: Pod = p.dup()
    copy.metadata.name = 'adsgad'
    diffs = p.diff(copy)
    assert len(diffs) == 1


def test079():
    """
    check that mismatched list items are caught in a diff
    """
    assert isinstance(p, Pod)
    copy1: Pod = p.dup()
    copy2: Pod = p.dup()
    copy1.metadata.finalizers = ["one", "two", "three"]
    copy2.metadata.finalizers = ["one", "two", "four"]
    diffs = copy1.diff(copy2)
    assert len(diffs) == 1


def test080():
    """
    check that mismatched dict keys are caught in a diff
    """
    assert isinstance(p, Pod)
    copy1: Pod = p.dup()
    copy2: Pod = p.dup()
    copy1.metadata.annotations = {"one": "uno", "two": "dos", "same" : "val"}
    copy2.metadata.annotations = {"two": "dos", "three": "tres", "same" : "val"}
    diffs = copy1.diff(copy2)
    assert len(diffs) == 2


def test081():
    """
    check that a required attr is caught in a typecheck
    """
    owner = OwnerReference(apiVersion="v1", kind=None,
                           name="test081", uid="asdf")
    warnings = owner.get_type_warnings()
    assert len(warnings) == 1


def test082():
    """
    check that __repr__ gets called
    """
    assert isinstance(p, Pod)
    s = repr(p)
    assert s


def test083():
    """
    check that the assign_to arg works in get_python_source()
    """
    assert isinstance(p, Pod)
    s = get_python_source(p, style='black', assign_to='x')
    assert s.startswith('x =')


def test084():
    """
    ensure positional params are correct
    """
    own = OwnerReference('v1', 'OR', 'test084', 'asdf')
    s = get_python_source(own, style='black')
    o: OwnerReference = eval(s, globals(), locals())
    assert o.apiVersion == 'v1'
    assert o.kind == 'OR'
    assert o.name == 'test084'
    assert o.uid == 'asdf'


def test085():
    """
    test the checks in get_clean_dict()
    """
    try:
        d = get_clean_dict({})
        assert False, 'should have raised a TypeError'
    except TypeError:
        pass


def test086():
    """
    Test proper generation of YAML
    """
    assert isinstance(p, Pod)
    yaml = get_yaml(p)
    procs = get_processors(yaml=yaml)
    new_p = Pod.from_yaml(procs[0])
    assert p == new_p


def test087():
    """
    Test guard code in get_yaml()
    """
    try:
        yaml = get_yaml(get_clean_dict(p))
        assert False, "This should have raised a TypeError"
    except TypeError:
        pass


def test088():
    """
    Test guard code in get_json
    """
    try:
        j = get_json(get_clean_dict(p))
        assert False, "This should have raised a TypeError"
    except TypeError:
        pass


def test089():
    """
    Test guard code in from_dict
    """
    try:
        h = from_dict(p)
        assert False, "This should have raised a TypeError about adict"
    except TypeError:
        pass
    try:
        h = from_dict(get_clean_dict(p), cls=list)
        assert False, "This should ahve raised a TypeError about cls"
    except TypeError:
        pass


def test090():
    """
    Check guard code in get_processors
    """
    try:
        p = get_processors()
        assert False, "This should have raised about no args"
    except RuntimeError:
        pass


def test091():
    """
    Check using a path for get_processors()
    """
    p = get_processors(path="test.yaml")
    assert len(p) == 2


def test092():
    """
    Check that a bad apiVersion/kind raises a RuntimeError
    """
    try:
        docs = load_full_yaml(path="bad.yaml")
        assert False, f"num docs: {len(docs)}"
    except RuntimeError:
        pass


def test093():
    """
    Check that required but empty lists raise a type warning
    """
    assert isinstance(p, Pod)
    copy: Pod = p.dup()
    copy.spec.containers = []
    warnings = copy.get_type_warnings()
    assert len(warnings) == 1


def test094():
    """
    Check we get a TypeError when parsing YAML with missing required prop
    """
    try:
        _ = load_full_yaml(path="bad2.yaml")
        assert False, "Should have raised a TypeError"
    except TypeError:
        pass


def test095():
    """
    Check two different code gen styles yield equivalent objects
    """
    assert isinstance(p, Pod)
    code1 = get_python_source(p)
    code2 = get_python_source(p, style='black')
    obj1 = eval(code1, globals(), locals())
    obj2 = eval(code2, globals(), locals())
    assert obj1 == obj2


def test096():
    """
    Test processing the group, version, name back into a swagger name
    """
    try:
        from build import ClassDescriptor
    except ImportError:  # this test is only for in dev for the build
        pass
    else:
        f = open("recursive.json", "r")
        jdict = json.load(f)
        for k, v in jdict.items():
            cd = ClassDescriptor(k, v)
            swagger_name = make_swagger_name(cd.group, cd.version, cd.short_name)
            break
        g, v, n = process_swagger_name(swagger_name)
        assert g == cd.group, "Group doesn't match"
        assert v == cd.version, "Version doesn't match"
        assert n == cd.short_name, "Named doesn't match"


def test097():
    """
    Check that we can process a recursively defined swagger object
    """
    try:
        from build import ClassDescriptor
    except ImportError:  # this test is only for in dev for the build
        pass
    else:
        f = open("recursive.json", "r")
        jdict = json.load(f)
        cd = None
        for k, v in jdict.items():
            cd = ClassDescriptor(k, v)
            cd.process_properties()
            break
        assert True


def test102():
    """
    ensure that the $-starting attrs get rendered properly
    """
    x = JSONSchemaProps(dollar_ref='wibble',
                        x_kubernetes_list_type='wobble')
    d = get_clean_dict(x)
    assert '$ref' in d
    assert 'x-kubernetes-list-type' in d
    y = get_yaml(x)
    assert '$ref' in y
    assert 'x-kubernetes-list-type' in y


def test103():
    """
    ensure that keywords are transformed properly when exporting
    """
    ipb = IPBlock("192.168.6.1/32", except_=['wibble', 'wobble'])
    d = get_clean_dict(ipb)
    assert 'except_' not in d and 'except' in d
    y = get_yaml(ipb)
    assert 'except_' not in y and 'except' in y


def test104():
    """
    ensure that you can acquire a version of the v1 Pod class
    """
    pod = get_version_kind_class('v1', 'Pod')
    assert pod is not None


def test105():
    """
    ensure that you can acquire a version of the v1alpha1 Pod class
    """
    from hikaru.model.rel_1_16 import v1alpha1
    pod = get_version_kind_class('v1alpha1', 'Pod')
    assert pod is not None


def test106():
    """
    ensure that you can acquire a version of the v1beta1 Pod class
    """
    pod = get_version_kind_class('v1beta1', 'Pod')
    assert pod is not None


def test107():
    """
    ensure that you can acquire a version of the v2beta1 Pod class
    """
    pod = get_version_kind_class('v2beta1', 'Pod')
    assert pod is not None


def test108():
    """
    ensure that you can acquire a version of the v2beta2 Pod class
    """
    pod = get_version_kind_class('v2beta2', 'Pod')
    assert pod is not None


def test109():
    """
    ensure that you can acquire a version of the v1beta2 Pod class
    """
    pod = get_version_kind_class('v1beta2', 'Pod')
    assert pod is not None


def test110():
    """
    ensure that you can acquire a version of the v2alpha1 Pod class
    """
    pod = get_version_kind_class('v2alpha1', 'Pod')
    assert pod is not None


def test111():
    """
    check that you can set the proper default release
    """
    raise SkipTest("This release has been removed for the time being")
    # from hikaru.model.rel_1_15 import Pod
    # defrel = get_default_release()
    # set_default_release('rel_1_15')
    # pod = setup_pod()
    # set_default_release(defrel)
    # assert pod.__class__ is Pod


def test112():
    """
    Check for an error when passing the wrong arg into process_api_version
    """
    try:
        _, _ = process_api_version(5)
        assert False, "should have complained about the arg type"
    except TypeError:
        pass


def test113():
    """
    Check that we get a None version if one is missing in the swagger name
    """
    _, version, _ = process_swagger_name('first.second.Pod')
    assert version is None


def test114():
    """
    Check we can turn camel case to pep8 format
    """
    pep8 = camel_to_pep8('thisIsCamelCase')
    assert pep8 == 'this_is_camel_case'


def test115():
    """
    Check that repopulating catalogs doesn't impact the find_by_name results
    """
    p = setup_pod()
    res1 = p.find_by_name('exec', following='containers.1.lifecycle')
    p.repopulate_catalog()
    res2 = p.find_by_name('exec', following='containers.1.lifecycle')
    assert res1 == res2


def test116():
    """
    check that the wrong object where a list goes causes a warning
    """
    p: Pod = setup_pod()
    prior_warnings = p.get_type_warnings()
    assert not prior_warnings
    om = ObjectMeta()
    p.spec.containers = om
    later_warnings = p.get_type_warnings()
    assert len(later_warnings) == 1, f"got {len(later_warnings)} warnings"


# this block of code computes the params for test117
from hikaru.model.rel_1_16.versions import versions


@pytest.mark.parametrize('rel_version', versions)
def test117(rel_version: str):
    """
    ensure there are no issues in importing the documents module for each version
    :param rel_version: string; name of the version module use when getting documents
    """
    mod = import_module(".documents", f"hikaru.model.rel_1_16.{rel_version}")
    assert mod


class Pod118(Pod):
    def bibble(self):
        return 'babble'


def test118():
    """
    test you can direct Hikaru to use a different v/k class with new methods
    """
    register_version_kind_class(Pod118, Pod.apiVersion, Pod.kind)
    p: Pod = setup_pod()
    try:
        assert isinstance(p, Pod118), f"Got type {p.__class__.__name__}"
        assert p.bibble() == 'babble'
    finally:
        register_version_kind_class(Pod, Pod.apiVersion, Pod.kind)


class Pod119(Pod):
    def __post_init__(self, client: Any = None):
        super(Pod119, self).__post_init__(client=client)
        self.frank = 'hi'
        self.zappa = 'there'

    def greet(self):
        return f"{self.frank} {self.zappa}"


def test119():
    """
    add instance attrs (not from init args) to a subclass with no impact
    """
    register_version_kind_class(Pod119, Pod.apiVersion, Pod.kind)
    p: Pod = setup_pod()
    try:
        assert isinstance(p, Pod119)
        yaml = get_yaml(p)
        assert 'frank' not in yaml
        assert p.greet() == "hi there"
        new_p: Pod119 = load_full_yaml(yaml=yaml)[0]
        assert new_p.zappa == p.zappa
        d = get_clean_dict(p)
        assert 'frank' not in d
    finally:
        register_version_kind_class(Pod, Pod.apiVersion, Pod.kind)


@dataclass
class Pod120(Pod):
    moonshadow: InitVar[Optional[str]] = 'followed'

    def __post_init__(self, client: Any = None,
                      moonshadow: InitVar[Optional[str]] = None):
        super(Pod120, self).__post_init__(client=client)
        self.moonshadow = moonshadow


def test120():
    """
    add instance attrs (from init args) to a subclass with no impact
    """
    register_version_kind_class(Pod120, Pod.apiVersion, Pod.kind)
    p: Pod120 = setup_pod()
    try:
        assert isinstance(p, Pod120)
        yaml = get_yaml(p)
        assert 'moonshadow' not in yaml
        assert p.moonshadow == 'followed'
        new_p: Pod120 = Pod120(moonshadow='hunted')
        assert new_p.moonshadow == 'hunted'
    finally:
        register_version_kind_class(Pod, Pod.apiVersion, Pod.kind)


@dataclass
class Inner121(HikaruBase):
    strField: str
    intField: int
    optStrField: Optional[str] = None
    optIntField: Optional[int] = None


@dataclass
class Outer121(HikaruDocumentBase):
    apiVersion: str = 'hikaru.v1'
    kind: str = 'outer121'
    metadata: Optional[ObjectMeta] = None
    inner: Optional[Inner121] = None


def test121():
    """
    test creating your own custom class which Hikaru can handle
    """
    register_version_kind_class(Outer121, Outer121.apiVersion, Outer121.kind)
    o: Outer121 = load_full_yaml(path="custom_op.yaml")[0]
    assert isinstance(o, Outer121)
    assert o.kind == 'outer121'
    assert o.metadata.name == 'custom-tester'
    assert o.metadata.namespace == 'default'
    assert isinstance(o.inner, Inner121)
    assert o.inner.strField == 'gotta have it'
    assert o.inner.intField == 43
    assert o.inner.optIntField == 121
    assert o.inner.optStrField is None
    yaml = get_yaml(o)
    new_o = load_full_yaml(yaml=yaml)[0]
    assert isinstance(new_o, Outer121)
    assert new_o.kind == 'outer121'
    assert new_o.metadata.name == 'custom-tester'
    assert new_o.metadata.namespace == 'default'
    assert isinstance(new_o.inner, Inner121)
    assert new_o.inner.strField == 'gotta have it'
    assert new_o.inner.intField == 43
    assert new_o.inner.optIntField == 121
    assert new_o.inner.optStrField is None


def test122():
    """
    test that you can run object_at_path on the path returned by diff()
    """
    pod = Pod(spec=PodSpec(containers=[Container(name="a")]))
    pod2 = pod.dup()
    pod2.spec.containers[0].name = "b"
    diff = pod.diff(pod2)
    assert pod2.object_at_path(diff[0].path) == "b"
    assert diff[0].attrname == 'name'


if __name__ == "__main__":
    setup()
    the_tests = {k: v for k, v in globals().items()
                 if k.startswith('test') and callable(v)}
    for k, v in the_tests.items():
        try:
            if k == "test117":
                for ver in versions:
                    v(ver)
            else:
                v()
        except SkipTest:
            pass
        except Exception as e:
            print(f'{k} failed with {str(e)}, {e.__class__}')
            raise
