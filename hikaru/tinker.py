
"""
docstring
"""
import dataclasses
from hikaru.model import *
from pprint import pprint as pp


from typing import List,  Optional

NoneType = type(None)


@dataclasses.dataclass
class Inner(object):
    f1: float
    s1: str
    l1: List[int] = None


@dataclasses.dataclass
class Outer(object):
    f2: float
    s1: str
    l2: Optional[List[Inner]] = dataclasses.field(default_factory=list)


o = Outer(3.14, "out")
o.l2.append(Inner(1.2, "asdf", [1, 2, 3]))

l2 = Outer(5, "boom")
_ = 0

y = Pod(apiVersion="v1",
        kind='Pod',
        spec=PodSpec(
            containers=[Container(name="cont1",
                                  image="image1"),
                        Container(name="cont2",
                                  image="image2")]
        ))

x = Pod(
    apiVersion='v1', kind='Pod',
    metadata=ObjectMeta(
        name='hello-kiamol-3', labels={'lab1': 'wibble', 'lab2': 'wobble', },),
    spec=PodSpec(
        containers=[
            Container(
                name='web', image='kiamol/ch02-hello-kiamol',
                ports=[ContainerPort(containerPort=3306,),
                       ContainerPort(containerPort=3307,), ],),
            Container(
                name='db', image='hibbie-forward-shake',
                lifecycle=Lifecycle(
                    postStart=Handler(
                        exec=ExecAction(
                            command=['cmd', 'arg1', 'arg2', ],),
                        httpGet=HTTPGetAction(
                            port=80, host='localhost', path='/home',
                            scheme='https',
                            httpHeaders=[
                                HTTPHeader(
                                    name='Content-Disposition',
                                    value='whatever',), ],),
                        tcpSocket=TCPSocketAction(
                            port=1025, host='devnull',),),
                    preStop=Handler(
                        exec=ExecAction(
                            command=['cmd', 'arg1', 'arg2', ],),),),
                livenessProbe=Probe(
                    exec=ExecAction(
                        command=['probe-cmd', 'arg1', 'arg2', ],),
                    failureThreshold=4, initialDelaySeconds=30, periodSeconds=5,
                    successThreshold=2, timeoutSeconds=3,),
                readinessProbe=Probe(
                    exec=ExecAction(
                        command=['probe-cmd2', 'arg1', 'arg2', 'arg3', ],),
                    failureThreshold=3, initialDelaySeconds=31, periodSeconds=4,
                    successThreshold=1, timeoutSeconds=2,),
                resources=ResourceRequirements(
                    limits={'cores': '4', 'mem-mb': '500', },
                    requests={'cores': '3', 'mem-mb': '400', },),
                securityContext=SecurityContext(
                    allowPrivilegeEscalation=True,
                    capabilities=Capabilities(
                        add=['create', 'read', 'update', ],
                        drop=['delete', ],),
                    privileged=False, procMount='DefaultProcMount',
                    readOnlyRootFilesystem=False, runAsGroup=55,
                    runAsNonRoot=True, runAsUser=1001,
                    seLinuxOptions=SELinuxOptions(
                        level='uno', role='dos', type='tres', user='quattro',),
                    seccompProfile=SeccompProfile(
                        type='summat', localhostProfile='nada',),
                    windowsOptions=WindowsSecurityContextOptions(
                        gmsaCredentialSpec='horrible',
                        gmsaCredentialSpecName='awful', runAsUserName='icky',),),
                terminationMessagePath='/goodbye/cruel/world.txt',
                terminationMessagePolicy='File',
                env=[EnvVar(name='HOME', value='here',),
                     EnvVar(
                    name='WIBBLE',
                    valueFrom=EnvVarSource(
                        configMapKeyRef=ConfigMapKeySelector(
                            key='thekey',),),), ],
                envFrom=[
                    EnvFromSource(
                        configMapRef=ConfigMapEnvSource(
                            name='test-map', optional=True,),
                        prefix='gabagabahey',
                        secretRef=SecretEnvSource(
                            name='seecrit', optional=False,),), ],
                volumeDevices=[
                    VolumeDevice(
                        devicePath='/dev/sd0a', name='root-disk',), ],
                volumeMounts=[
                    VolumeMount(
                        mountPath='/opt', name='opt-mount',
                        mountPropagation='wibble', readOnly=True,
                        subPath='', subPathExpr='',), ],), ],
        enableServiceLinks=False, nodeName='maxwell', runtimeClassName='classless',
        schedulerName='cecil',
        imagePullSecrets=[LocalObjectReference(name='one',),
                          LocalObjectReference(name='two',), ],
        nodeSelector={'key1': 'wibble', 'key2': 'wobble', },),)

# print(get_yaml(x))


possible_doc_types = {}
for k, v in dict(globals()).items():
    if k != 'HikaruBase' and type(v) == type and issubclass(v, HikaruBase):
        field_set = {f.name for f in dataclasses.fields(v)}
        if "apiVersion" in field_set and "api_version_group" in field_set:
            possible_doc_types[('v1', k)] = k

pp(possible_doc_types)
