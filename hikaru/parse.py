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
from typing import Union, AnyStr, Dict, List
from collections import OrderedDict

NoneType = type(None)

_api_version = "v1"


class Metadata(object):
    name: Union[AnyStr, NoneType]
    generate_name: Union[AnyStr, NoneType]
    namespace: Union[AnyStr, NoneType]
    labels: Dict[AnyStr, AnyStr]
    annotations: Dict[AnyStr, AnyStr]

    def __init__(self, name: AnyStr,
                 generate_name: Union[AnyStr, NoneType] = None,
                 namespace: Union[AnyStr, NoneType] = None,
                 labels: Union[Dict[AnyStr, AnyStr], NoneType] = None,
                 annotations: Union[Dict[AnyStr, AnyStr], NoneType] = None):
        self.name = name
        self.generate_name = generate_name
        self.namespace = namespace
        self.labels = OrderedDict() if labels is None else labels
        self.annotations = OrderedDict() if annotations is None else annotations

    def parse(self, yaml):
        self.name = yaml["name"]
        self.generate_name = yaml.get('generateName', None)
        self.generate_name = yaml.get('namespace', None)
        labels = yaml.get('labels', None)
        if labels is not None:
            self.labels.update((k, v) for k, v in labels.items())
        annotations = yaml.get('annotations', None)
        if annotations is not None:
            self.annotations.update((k, v) for k, v in annotations.items())


class ParseDocument(object):
    the_kind = None
    api_version: AnyStr
    kind: Union[AnyStr, NoneType]
    metadata: Union[Metadata, NoneType]

    def __init__(self, api_version):
        self.api_version = api_version
        self.kind = self.the_kind
        self.metadata = None

    def parse(self, yaml):
        self.api_version = yaml["apiVersion"]
        self.metadata = Metadata("__placeholder__")
        self.metadata.parse(yaml["metadata"])


class ContainerPort(object):
    container_port: int
    host_ip: Union[AnyStr, NoneType]
    host_port: Union[int, NoneType]
    name: Union[AnyStr, NoneType]
    protocol: Union[AnyStr, NoneType]

    def __init__(self, container_port: int,
                 host_ip: Union[AnyStr, NoneType] = None,
                 host_port: Union[int, NoneType] = None,
                 name: Union[AnyStr, NoneType] = None,
                 protocol: Union[AnyStr, NoneType] = None):
        self.container_port = container_port
        self.host_ip = host_ip
        self.host_port = host_port
        self.name = name
        self.protocol = protocol

    def parse(self, yaml):
        self.container_port = yaml["containerPort"]
        self.host_port = yaml.get("hostPort", None)
        self.host_ip = yaml.get("hostIP", None)
        self.name = yaml.get("name", None)
        self.protocol = yaml.get("protocol", None)


class ConfigMapKeySelector(object):
    key: AnyStr
    name: Union[AnyStr, NoneType]
    optional: Union[bool, NoneType]

    def __init__(self, key: AnyStr,
                 name: Union[AnyStr, NoneType] = None,
                 optional: Union[bool, NoneType] = None):
        self.key = key
        self.name = name
        self.optional = optional

    def parse(self, yaml):
        self.key = yaml["key"]
        self.name = yaml.get("name", None)
        self.optional = yaml.get("optional", None)


class ObjectFieldSelector(object):
    field_path: AnyStr
    api_version: Union[AnyStr, NoneType]

    def __init__(self, field_path: AnyStr,
                 api_version: Union[AnyStr, NoneType] = _api_version):
        self.field_path = field_path
        self.api_version = api_version

    def parse(self, yaml):
        self.field_path = yaml["fieldPath"]
        self.api_version = yaml.get("apiVersion", _api_version)


class ResourceFieldSelector(object):
    resource: AnyStr
    container_name: Union[AnyStr, NoneType]
    divisor: Union[float, NoneType]

    def __init__(self, resource: AnyStr,
                 container_name: Union[AnyStr, NoneType] = None,
                 divisor: Union[float, NoneType] = None):
        self.resource = resource
        self.container_name = container_name
        self.divisor = divisor

    def parse(self, yaml):
        self.resource = yaml["resource"]
        self.container_name = yaml.get("containerName", None)
        self.divisor = yaml.get("divisor", None)


class EnvVarSource(object):
    config_map_key_ref: Union[ConfigMapKeySelector, NoneType]
    field_ref: Union[ObjectFieldSelector, NoneType]
    resource_field_ref: Union[ResourceFieldSelector, NoneType]

    def __init__(self, config_map_key_ref: Union[ConfigMapKeySelector, NoneType] = None,
                 field_ref: Union[ObjectFieldSelector, NoneType] = None,
                 resource_field_ref: Union[ResourceFieldSelector, NoneType] = None):
        self.config_map_key_ref = config_map_key_ref
        self.field_ref = field_ref
        self.resource_field_ref = resource_field_ref

    def parse(self, yaml):
        # NOTE: the yaml is expecting to referring to the valueFrom
        # item, and the expectation is that there will be a sub-key
        # to indicate which of the different sources is being used
        if "configMapKeyRef" in yaml:
            self.config_map_key_ref = ConfigMapKeySelector("_placeholder_")
            self.config_map_key_ref.parse(yaml["configMapKeyRef"])
        elif "fieldRef" in yaml:
            self.field_ref = ObjectFieldSelector(".")
            self.field_ref.parse(yaml["fieldRef"])
        elif "resourceFieldRef" in yaml:
            self.resource_field_ref = ResourceFieldSelector(".")
            self.resource_field_ref.parse(yaml["resourceFieldRef"])


class ConfigMapRef(object):
    name: AnyStr
    optional: bool

    def __init__(self, name: AnyStr, optional: bool):
        self.name = name
        self.optional = optional

    def parse(self, yaml):
        self.name = yaml["name"]
        self.optional = yaml["optional"]


class SecretRef(object):
    name: AnyStr
    optional: bool

    def __init__(self, name: AnyStr, optional: bool):
        self.name = name
        self.optional = optional

    def parse(self, yaml):
        self.name = yaml["name"]
        self.optional = yaml["optional"]


class EnvFromSource(object):
    config_map_ref: Union[ConfigMapRef, NoneType]
    prefix: Union[AnyStr, NoneType]
    secret_ref: Union[SecretRef, NoneType]

    def __init__(self, config_map_ref: Union[ConfigMapRef, NoneType] = None,
                 prefix: Union[AnyStr, NoneType] = None,
                 secret_ref: Union[SecretRef, NoneType] = None):
        self.config_map_ref = config_map_ref
        self.prefix = prefix
        self.secret_ref = secret_ref

    def parse(self, yaml):
        if "configMapRef" in yaml:
            self.config_map_ref = ConfigMapRef('_placeholder_', True)
            self.config_map_ref.parse(yaml["configMapRef"])
        self.prefix = yaml.get('prefix', None)
        if "secretRef" in yaml:
            self.secret_ref = SecretRef("_placeholder_", True)
            self.secret_ref.parse(yaml["secretRef"])


class EnvVar(object):
    name: AnyStr
    value: Union[AnyStr, NoneType]
    value_from: Union[EnvVarSource, NoneType]

    def __init__(self, name: AnyStr,
                 value: Union[AnyStr, NoneType] = None,
                 value_from: Union[EnvVarSource, NoneType] = None):
        self.name = name
        self.value = value
        self.value_from = value_from

    def parse(self, yaml):
        self.name = yaml["name"]
        self.value = yaml.get("value", None)
        if "valueFrom" in yaml:
            evs = EnvVarSource()
            evs.parse(yaml["valueFrom"])
            self.value_from = evs


class VolumeMount(object):
    mount_path: AnyStr
    name: AnyStr
    mount_propagation: Union[AnyStr, NoneType]
    read_only: Union[bool, NoneType]
    sub_path: Union[AnyStr, NoneType]
    sub_path_expr: Union[AnyStr, NoneType]

    def __init__(self, mount_path: AnyStr, name: AnyStr,
                 mount_propagation: Union[AnyStr, NoneType] = None,
                 read_only: Union[bool, NoneType] = None,
                 sub_path: Union[AnyStr, NoneType] = None,
                 sub_path_expr: Union[AnyStr, NoneType] = None):
        self.mount_path = mount_path
        self.name = name
        self.mount_propagation = mount_propagation
        self.read_only = read_only
        self.sub_path = sub_path
        self.sub_path_expr = sub_path_expr

    def parse(self, yaml):
        self.mount_path = yaml["mountPath"]
        self.name = yaml["name"]
        self.mount_propagation = yaml.get("mountPropagation", None)
        self.read_only = yaml.get("readOnly", None)
        self.sub_path = yaml.get("subPath", None)
        self.sub_path_expr = yaml.get("subPathExpr", None)


class VolumeDevice(object):
    device_path: AnyStr
    name: AnyStr

    def __init__(self, device_path: AnyStr, name: AnyStr):
        self.device_path = device_path
        self.name = name

    def parse(self, yaml):
        self.device_path = yaml["devicePath"]
        self.name = yaml["name"]


class ResourceRequirements(object):
    limits: Union[Dict[AnyStr, float], NoneType]
    requests: Union[Dict[AnyStr, float], NoneType]

    def __init__(self, limits: Union[Dict[AnyStr, float], NoneType] = None,
                 requests: Union[Dict[AnyStr, float], NoneType] = None):
        self.limits = {} if limits is None else {(k, v) for k, v in limits.items()}
        self.requests = {} if requests is None else {(k, v) for k, v in requests.items()}

    def parse(self, yaml):
        if "limits" in yaml:
            self.limits.update((k, v) for k, v in yaml["limits"].items())
        if "requests" in yaml:
            self.requests.update((k, v) for k, v in yaml["requests"].items())


class HTTPHeader(object):
    name: AnyStr
    value: AnyStr

    def __init__(self, name: AnyStr, value: AnyStr):
        self.name = name
        self.value = value

    def parse(self, yaml):
        self.name = yaml["name"]
        self.value = yaml["value"]


class HTTPGetAction(object):
    port: Union[int, AnyStr]
    host: Union[AnyStr, NoneType]
    http_headers: Union[List[HTTPHeader], NoneType]
    path: Union[AnyStr, NoneType]
    scheme: Union[AnyStr, NoneType]

    def __init__(self, port: Union[int, AnyStr],
                 host: Union[AnyStr, NoneType] = None,
                 http_headers: Union[List[HTTPHeader], NoneType] = None,
                 path: Union[AnyStr, NoneType] = None,
                 scheme: Union[AnyStr, NoneType] = None):
        self.port = port
        self.host = host
        self.http_headers = [] if http_headers is None else [h for h in http_headers]
        self.path = path
        self.scheme = scheme

    def parse(self, yaml):
        self.port = yaml["port"]
        self.host = yaml.get("host", None)
        if "httpHeaders" in yaml:
            for h_yaml in yaml["httpHeaders"]:
                h = HTTPHeader("", "")
                h.parse(h_yaml)
                self.http_headers.append(h)
        self.path = yaml.get("path", None)
        self.scheme = yaml.get("scheme", None)


class TCPSocketAction(object):
    port: Union[AnyStr, int]
    host: Union[AnyStr, NoneType]

    def __init__(self, port: Union[AnyStr, int],
                 host: Union[AnyStr, NoneType] = None):
        self.port = port
        self.host = host

    def parse(self, yaml):
        self.port = yaml["port"]
        self.host = yaml.get("host", None)


class Handler(object):
    exec: Union[List[AnyStr], NoneType]
    http_get: Union[HTTPGetAction, NoneType]
    tcp_socket: Union[TCPSocketAction, NoneType]

    def __init__(self, exec: Union[List[AnyStr], NoneType] = None,
                 http_get: Union[HTTPGetAction, NoneType] = None,
                 tcp_socket: Union[TCPSocketAction, NoneType] = None):
        self.exec = [] if exec is None else exec
        self.http_get = http_get
        self.tcp_socket = tcp_socket

    def parse(self, yaml):
        if "exec" in yaml:
            self.exec = list(s for s in yaml["exec"])
        if "httpGet" in yaml:
            self.http_get = HTTPGetAction(0)
            self.http_get.parse(yaml["httpGet"])
        if "tcpSocket" in yaml:
            self.tcp_socket = TCPSocketAction(0)
            self.tcp_socket.parse(yaml["tcpSocket"])


class Lifecycle(object):
    post_start: Union[Handler, NoneType]
    pre_stop: Union[Handler, NoneType]

    def __init__(self, post_start: Union[Handler, NoneType] = None,
                 pre_stop: Union[Handler, NoneType] = None):
        self.post_start = post_start
        self.pre_stop = pre_stop

    def parse(self, yaml):
        if "postStart" in yaml:
            self.post_start = Handler()
            self.post_start.parse(yaml["postStart"])
        if "preStop" in yaml:
            self.pre_stop = Handler()
            self.pre_stop.parse(yaml["preStop"])


class Probe(Handler):
    initial_delay_seconds: Union[int, NoneType]
    period_seconds: Union[int, NoneType]
    timeout_seconds: Union[int, NoneType]
    failure_threshold: Union[int, NoneType]
    success_threshold: Union[int, NoneType]

    def __init__(self, exec: Union[List[AnyStr], NoneType] = None,
                 http_get: Union[HTTPGetAction, NoneType] = None,
                 tcp_socket: Union[TCPSocketAction, NoneType] = None,
                 initial_delay_seconds: Union[int, NoneType] = None,
                 period_seconds: Union[int, NoneType] = None,
                 timeout_seconds: Union[int, NoneType] = None,
                 failure_threshold: Union[int, NoneType] = None,
                 success_threshold: Union[int, NoneType] = None):
        super(Probe, self).__init__(exec, http_get, tcp_socket)
        self.initial_delay_seconds = initial_delay_seconds
        self.period_seconds = period_seconds
        self.timeout_seconds = timeout_seconds
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold

    def parse(self, yaml):
        super(Probe, self).parse(yaml)
        self.initial_delay_seconds = yaml.get("initialDelaySeconds", None)
        self.period_seconds = yaml.get("periodSeconds", None)
        self.timeout_seconds = yaml.get("timeoutSeconds", None)
        self.failure_threshold = yaml.get("failureThreshold", None)
        self.success_threshold = yaml.get("successThreshold", None)


class Capabilities(object):
    add: Union[List[AnyStr], NoneType]
    drop: Union[List[AnyStr], NoneType]

    def __init__(self, add: Union[List[AnyStr], NoneType] = None,
                 drop: Union[List[AnyStr], NoneType] = None):
        self.add = [] if add is None else [s for s in add]
        self.drop = [] if drop is None else [s for s in drop]

    def parse(self, yaml):
        if "add" in yaml:
            self.add.extend(s for s in yaml["add"])
        if "drop" in yaml:
            self.drop.extend(s for s in yaml["drop"])


class SELinuxOptions(object):
    level: AnyStr
    role: AnyStr
    type: AnyStr
    user: AnyStr

    def __init__(self, level: AnyStr, role: AnyStr, type: AnyStr,
                 user: AnyStr):
        self.level = level
        self.role = role
        self.type = type
        self.user = user

    def parse(self, yaml):
        self.level = yaml["level"]
        self.role = yaml["role"]
        self.type = yaml["type"]
        self.user = yaml["user"]


class WindowsSecurityContextOptions(object):
    gmsa_credential_spec: AnyStr
    gmsa_credential_spec_name: AnyStr
    run_as_user_name: AnyStr

    def __init__(self, gmsa_credential_spec: AnyStr, gmsa_credential_spec_name: AnyStr,
                 run_as_user_name: AnyStr):
        self.gmsa_credential_spec = gmsa_credential_spec
        self.gmsa_credential_spec_name = gmsa_credential_spec_name
        self.run_as_user_name = run_as_user_name

    def parse(self, yaml):
        self.gmsa_credential_spec = yaml["gmsaCredentialSpec"]
        self.gmsa_credential_spec_name = yaml["gmsaCredentialSpecName"]
        self.run_as_user_name = yaml["runAsUserName"]


class SeccompProfile(object):
    type: AnyStr
    local_host_profile: Union[AnyStr, NoneType]

    def __init__(self, type: AnyStr, local_host_profile: Union[AnyStr, NoneType] = None):
        self.type = type
        self.local_host_profile = local_host_profile

    def parse(self, yaml):
        self.type = yaml["type"]
        self.local_host_profile = yaml.get("localHostProfile", None)


class SecurityContext(object):
    run_as_user: Union[int, NoneType]
    run_as_non_root: Union[bool, NoneType]
    run_as_group: Union[int, NoneType]
    read_only_root_filesystem: Union[bool, NoneType]
    proc_mount: Union[AnyStr, NoneType]
    privileged: Union[bool, NoneType]
    allow_privilege_escalation: Union[bool, NoneType]
    capabilities: Union[Capabilities, NoneType]
    seccomp_profile: Union[SeccompProfile, NoneType]
    se_linux_options: Union[SELinuxOptions, NoneType]
    windows_options: Union[WindowsSecurityContextOptions, NoneType]

    def __init__(self, run_as_user: Union[int, NoneType] = None,
                 run_as_non_root: Union[bool, NoneType] = None,
                 run_as_group: Union[int, NoneType] = None,
                 read_only_root_filesystem: Union[bool, NoneType] = None,
                 proc_mount: Union[AnyStr, NoneType] = None,
                 privileged: Union[bool, NoneType] = None,
                 allow_privilege_escalation: Union[bool, NoneType] = None,
                 capabilities: Union[Capabilities, NoneType] = None,
                 seccomp_profile: Union[SeccompProfile, NoneType] = None,
                 se_linux_options: Union[SELinuxOptions, NoneType] = None,
                 windows_options: Union[WindowsSecurityContextOptions, NoneType] = None):
        self.run_as_user = run_as_user
        self.run_as_non_root = run_as_non_root
        self.run_as_group = run_as_group
        self.read_only_root_filesystem = read_only_root_filesystem
        self.proc_mount = proc_mount
        self.privileged = privileged
        self.allow_privilege_escalation = allow_privilege_escalation
        self.capabilities = capabilities
        self.seccomp_profile = seccomp_profile
        self.se_linux_options = se_linux_options
        self.windows_options = windows_options

    def parse(self, yaml):
        self.run_as_user = yaml.get("runAsUser", None)
        self.run_as_non_root = yaml.get("runAsNonRoot", None)
        self.run_as_group = yaml.get("runAsGroup", None)
        self.read_only_root_filesystem = yaml.get("readOnlyRootFilesystem", None)
        self.proc_mount = yaml.get("procMount", None)
        self.privileged = yaml.get("privileged", None)
        self.allow_privilege_escalation = yaml.get("allowPrivilegeEscalation", None)
        if "capabilities" in yaml:
            self.capabilities = Capabilities()
            self.capabilities.parse(yaml["capabilities"])
        if "seccompProfile" in yaml:
            self.seccomp_profile = SeccompProfile("")
            self.seccomp_profile.parse(yaml["seccompProfile"])
        if "seLinuxOptions" in yaml:
            self.se_linux_options = SELinuxOptions("", "", "", "")
            self.se_linux_options.parse(yaml["seLinuxOptions"])
        if "windowsOptions" in yaml:
            self.windows_options = WindowsSecurityContextOptions("", "", "")
            self.windows_options.parse(yaml["windowsOptions"])


class Container(object):
    name: AnyStr
    image: Union[AnyStr, NoneType]
    image_pull_policy: Union[AnyStr, NoneType]
    command: Union[List[AnyStr], NoneType]
    args: Union[List[AnyStr], NoneType]
    working_dir: Union[AnyStr, NoneType]
    ports: Union[List[ContainerPort], NoneType]
    env: Union[List[EnvVar], NoneType]
    env_from: Union[List[EnvFromSource], NoneType]
    volume_mounts: Union[List[VolumeMount], NoneType]
    volume_devices: Union[List[VolumeDevice], NoneType]
    resources: Union[ResourceRequirements, NoneType]
    lifecycle: Union[Lifecycle, NoneType]
    termination_message_path: Union[AnyStr, NoneType]
    termination_message_policy: Union[AnyStr, NoneType]
    liveness_probe: Union[Probe, NoneType]
    readiness_probe: Union[Probe, NoneType]
    security_context: Union[SecurityContext, NoneType]

    def __init__(self, name: AnyStr,
                 image: Union[AnyStr, NoneType] = None,
                 image_pull_policy: Union[AnyStr, NoneType] = None,
                 command: Union[List[AnyStr], NoneType] = None,
                 args: Union[List[AnyStr], NoneType] = None,
                 working_dir: Union[AnyStr, NoneType] = None,
                 ports: Union[List[ContainerPort], NoneType] = None,
                 env: Union[List[EnvVar], NoneType] = None,
                 env_from: Union[List[EnvFromSource], NoneType] = None,
                 volume_mounts: Union[List[VolumeMount], NoneType] = None,
                 volume_devices: Union[List[VolumeDevice], NoneType] = None,
                 resources: Union[ResourceRequirements, NoneType] = None,
                 lifecycle: Union[Lifecycle, NoneType] = None,
                 termination_message_path: Union[AnyStr, NoneType] = None,
                 termination_message_policy: Union[AnyStr, NoneType] = None,
                 liveness_probe: Union[Probe, NoneType] = None,
                 readiness_probe: Union[Probe, NoneType] = None,
                 security_context: Union[SecurityContext, NoneType] = None):
        self.name = name
        self.image = image
        self.image_pull_policy = image_pull_policy
        self.command = [] if command is None else [s for s in command]
        self.args = [] if args is None else [s for s in args]
        self.working_dir = working_dir
        self.ports = [] if ports is None else [cp for cp in ports]
        self.env = [] if env is None else [ev for ev in env]
        self.env_from = [] if env_from is None else [efs for efs in env_from]
        self.volume_mounts = [] if volume_mounts is None else [vm for vm in volume_mounts]
        self.volume_devices = ([] if volume_devices is None else
                               [vd for vd in volume_devices])
        self.resources = resources
        self.lifecycle = lifecycle
        self.termination_message_path = termination_message_path
        self.termination_message_policy = termination_message_policy
        self.liveness_probe = liveness_probe
        self.readiness_probe = readiness_probe
        self.security_context = security_context

    def parse(self, yaml):
        self.name = yaml["name"]
        self.image = yaml.get("image", None)
        self.image_pull_policy = yaml.get("imagePullPolicy", None)
        command = yaml.get("command", None)
        if command is not None:
            self.command = [s for s in command]
        args = yaml.get("args", None)
        if args is not None:
            self.args = [s for s in args]
        self.working_dir = yaml.get("workingDir", None)
        ports = yaml.get("ports", None)
        if ports is not None:
            for port in ports:
                cp = ContainerPort(0)
                cp.parse(port)
                self.ports.append(cp)
        env = yaml.get("env", None)
        if env is not None:
            for ev in env:
                v = EnvVar('_placeholder_')
                v.parse(ev)
                self.env.append(v)
        env_from = yaml.get("envFrom", None)
        if env_from is not None:
            for efs in yaml["envFrom"]:
                v = EnvFromSource()
                v.parse(efs)
                self.env_from.append(v)
        volume_mounts = yaml.get("volumeMounts", None)
        if volume_mounts is not None:
            for vm in yaml["volumeMounts"]:
                m = VolumeMount("", "")
                m.parse(vm)
                self.volume_mounts.append(m)
        volume_devices = yaml.get("volumeDevices", None)
        if volume_devices is not None:
            for vd in yaml["volumeDevices"]:
                d = VolumeDevice("", "")
                d.parse(vd)
                self.volume_devices.append(d)
        if "resources" in yaml:
            self.resources = ResourceRequirements()
            self.resources.parse(yaml["resources"])
        if "lifecycle" in yaml:
            self.lifecycle = Lifecycle()
            self.lifecycle.parse(yaml["lifecycle"])
        self.termination_message_path = yaml.get("terminationMessagePath", None)
        self.termination_message_policy = yaml.get("terminationMessagePolicy", None)
        if 'livenessProbe' in yaml:
            self.liveness_probe = Probe()
            self.liveness_probe.parse(yaml["livenessProbe"])
        if "readinessProbe" in yaml:
            self.readiness_probe = Probe()
            self.readiness_probe.parse(yaml["readinessProbe"])
        if "securityContext" in yaml:
            self.security_context = SecurityContext()
            self.security_context.parse(yaml["securityContext"])


class LocalObjectReference(object):
    pass


class Volume(object):
    pass


class Affinity(object):
    pass


class Toleration(object):
    pass


class PodReadinessGate(object):
    pass


class HostAlias(object):
    pass


class PodSpec(object):
    containers: List[Container]
    initContainers: List[Container]
    imagePullSecrets: List[LocalObjectReference]
    enableServiceLinks: Union[bool, NoneType]
    volumes: List[Volume]
    nodeSelector: Dict[AnyStr, AnyStr]
    nodeName: Union[AnyStr, NoneType]
    affinity: Union[Affinity, NoneType]
    tolerations: List[Toleration]
    schedulerName: Union[AnyStr, NoneType]
    runtimeClassName: Union[AnyStr, NoneType]
    priorityClassName: Union[AnyStr, NoneType]
    priority: Union[int, NoneType]
    restartPolicy: Union[AnyStr, NoneType]
    terminationGracePeriodSeconds: Union[int, NoneType]
    activeDeadlineSeconds: Union[int, NoneType]
    readinessGates: List[PodReadinessGate]
    hostname: Union[AnyStr, NoneType]
    setHostnameAsFDQN: Union[bool, NoneType]
    subdomain: Union[AnyStr, NoneType]

    def __init__(self, containers: List[Container]):
        self.containers = list(containers)

    def parse(self, yaml):
        for c in yaml["containers"]:
            nc = Container("__placeholder__")
            nc.parse(c)
            self.containers.append(nc)


class Pod(ParseDocument):
    the_kind = 'Pod'
    spec: Union[PodSpec, NoneType]

    def __init__(self):
        super(Pod, self).__init__(_api_version)
        self.spec = None

    def parse(self, yaml):
        super(Pod, self).parse(yaml)
        self.spec = PodSpec([])
        self.spec.parse(yaml["spec"])
