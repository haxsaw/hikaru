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
from hikaru import *

p = None


def setup_pod() -> Pod:
    docs = load_full_yaml(stream=open("test.yaml", "r"))
    pod = docs[0]
    assert isinstance(pod, Pod)
    return pod


def setup():
    global p
    p = setup_pod()


def test01():
    """
    get the basic machinery creaking to life
    """
    assert isinstance(p, Pod)
    assert p.metadata.name == "hello-kiamol-3", p.metadata.name


def test02():
    """
    ensure the labels are there
    """
    assert isinstance(p, Pod)
    assert p.metadata.labels["lab1"] == "wibble"
    assert p.metadata.labels["lab2"] == "wobble"


def test03():
    """
    look for the ports in the container
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[0].ports[0].containerPort == 3306
    assert p.spec.containers[0].ports[1].containerPort == 3307


def test04():
    """
    add another container
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].name == "db"


def test05():
    """
    check for env vars on second container
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].env) == 2


def test06():
    """
    check for a value of 'here' for first env
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].env[0].value == "here",  \
           f"it was {p.spec.containers[1].env[0].value}"


def test07():
    """
    Check that there's an envFrom with a configMapRef in it
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].configMapRef.name == "test-map"
    assert p.spec.containers[1].envFrom[0].configMapRef.optional is True


def test08():
    """
    Check that an envFrom has a prefix in it
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].prefix == "gabagabahey"


def test09():
    """
    Check that an envFrom handles a secretRef
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].envFrom[0].secretRef.name == "seecrit"
    assert p.spec.containers[1].envFrom[0].secretRef.optional is False


def test10():
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


def test11():
    """
    Check that volume devices is handled properly
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].volumeDevices[0].devicePath == "/dev/sd0a"
    assert p.spec.containers[1].volumeDevices[0].name == "root-disk"


def test12():
    """
    check that resources are respected
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].resources.limits["cores"] == 4
    assert p.spec.containers[1].resources.limits["mem-mb"] == 500
    assert p.spec.containers[1].resources.requests["cores"] == 3
    assert p.spec.containers[1].resources.requests["mem-mb"] == 400


def test13():
    """
    check that exec in lifecyle postStart works ok
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].lifecycle.postStart.exec.command) == 3


def test14():
    """
    check that httpGet in lifecyle postStart works
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].lifecycle.postStart.httpGet.port == 80
    assert p.spec.containers[1].lifecycle.postStart.httpGet.host == 'localhost'
    assert p.spec.containers[1].lifecycle.postStart.httpGet.path == "/home"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.scheme == "https"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.httpHeaders[0].name == \
           "Content-Disposition"
    assert p.spec.containers[1].lifecycle.postStart.httpGet.httpHeaders[0].value == \
           "whatever"


def test15():
    """
    check that tcpSocket in lifecycle postStart works
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].lifecycle.postStart.tcpSocket.port == 1025
    assert p.spec.containers[1].lifecycle.postStart.tcpSocket.host == "devnull"


def test16():
    """
    check exec lifecyle in pre_stop
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].lifecycle.preStop.exec.command) == 3


def test17():
    """
    check for the terminationPolicy items
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].terminationMessagePath == "/goodbye/cruel/world.txt"
    assert p.spec.containers[1].terminationMessagePolicy == "File"


def test18():
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


def test19():
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


def test20():
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


def test21():
    """
    check the capabilities sub item of securityContext in containers
    """
    assert isinstance(p, Pod)
    assert len(p.spec.containers[1].securityContext.capabilities.add) == 3
    assert len(p.spec.containers[1].securityContext.capabilities.drop) == 1
    assert p.spec.containers[1].securityContext.capabilities.add[1] == "read"


def test22():
    """
    check the seccompProfile settings of securityContext
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].securityContext.seccompProfile.type == "summat"
    assert p.spec.containers[1].securityContext.seccompProfile.localhostProfile == \
           "nada"


def test23():
    """
    check the seLinuxOptions item of securityContext
    """
    assert isinstance(p, Pod)
    assert p.spec.containers[1].securityContext.seLinuxOptions.level == "uno"
    assert p.spec.containers[1].securityContext.seLinuxOptions.role == "dos"
    assert p.spec.containers[1].securityContext.seLinuxOptions.type == "tres"
    assert p.spec.containers[1].securityContext.seLinuxOptions.user == "quattro"


def test24():
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


def test25():
    """
    check the imagePullSecrets in the pod spec
    """
    assert isinstance(p, Pod)
    assert p.spec.imagePullSecrets[0].name == "one"
    assert p.spec.imagePullSecrets[1].name == "two"


def test26():
    """
    check enableServiceLinks
    """
    assert isinstance(p, Pod)
    assert p.spec.enableServiceLinks is False


def test27():
    """
    check nodeSelector
    """
    assert isinstance(p, Pod)
    assert p.spec.nodeSelector["key1"] == "wibble"
    assert p.spec.nodeSelector["key2"] == "wobble"


def test28():
    """
    check nodeName
    """
    assert isinstance(p, Pod)
    assert p.spec.nodeName == "maxwell"


def test29():
    """
    check schedulerName
    """
    assert isinstance(p, Pod)
    assert p.spec.schedulerName == "cecil"


def test30():
    """
    check runtimeClassName
    """
    assert isinstance(p, Pod)
    assert p.spec.runtimeClassName == "classless"


def test31():
    """
    Use find_by_name to find all containers
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('containers')
    assert len(results) == 2


def test32():
    """
    Use find_by_name to find all exec objects in lifecycles
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following=["containers", "lifecycle"])
    assert len(results) == 2


def test33():
    """
    Same test as test32, but with a single string
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following='containers.lifecycle')
    assert len(results) == 2


def test34():
    """
    Use find_by_name to find all exec objects in the lifecycle of the 2nd container
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following=['containers', 1, 'lifecycle'])
    assert len(results) == 2, f'len is {len(results)}'


def test35():
    """
    Same as test34, but using a single string for following
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('exec', following='containers.1.lifecycle')
    assert len(results) == 2, f'len is {len(results)}'


def test36():
    """
    Use find_by_name to find a field with non-consecutive following fields
    """
    assert isinstance(p, Pod)
    results = p.find_by_name('name', following='containers.lifecycle.httpGet')
    assert len(results) == 1


def test37():
    """
    check that equals returns true for the same object
    """
    assert isinstance(p, Pod)
    q = setup_pod()
    assert p == q


def test38():
    """
    check that equals returns False for a tweaked object
    """
    assert isinstance(p, Pod)
    q: Pod = setup_pod()
    q.spec.containers[1].securityContext.capabilities.add.append("wibble")
    assert p != q


def test39():
    """
    check that dup produces equal objects
    """
    assert isinstance(p, Pod)
    q: Pod = p.dup()
    assert p == q


def test40():
    """
    check that a twiddled dup'd object isn't equals
    """
    assert isinstance(p, Pod)
    q: Pod = p.dup()
    q.spec.containers[1].lifecycle.postStart.httpGet.port = "1234"
    assert p != q


def test41():
    """
    get_python_source with the autopep8 style
    """
    assert isinstance(p, Pod)
    code = get_python_source(p)
    x = eval(code, globals(), locals())
    assert p == x, "the two aren't the same"


def test42():
    """
    check that a modified loaded version of p isn't equal
    """
    assert isinstance(p, Pod)
    code = get_python_source(p)
    x = eval(code, globals(), locals())
    assert isinstance(x, Pod)
    x.spec.containers[1].lifecycle.postStart.httpGet.port = 4
    assert x != p


if __name__ == "__main__":
    setup()
    the_tests = {k: v for k, v in globals().items()
                 if k.startswith('test') and callable(v)}
    for k, v in the_tests.items():
        try:
            v()
        except Exception as e:
            print(f'{k} failed with {str(e)}')
