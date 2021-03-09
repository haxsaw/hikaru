import json
from dataclasses import asdict
from io import StringIO
from typing import List

from autopep8 import fix_code
from ruamel.yaml import YAML

from hikaru.model import *
from hikaru.meta import num_positional


def get_python_source(obj: HikaruBase, assign_to: str = None) -> str:
    """
    returns formatted Python source that will re-create the supplied object

    :param obj: an instance of HikaruBase
    :param assign_to: if supplied, must be a legal Python identifier name,
        as the returned expression will be assigned to that variable.
    :return: fully formatted Python code that will re-create the supplied
        object
    """
    code = obj.as_python_source(assign_to=assign_to)
    result = fix_code(code, options={"max_line_length": 90,
                                     "experimental": 1})
    return result


def _clean_dict(d: dict) -> dict:
    # returns a new dict missing any keys in d that have None for its value
    clean = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (list, dict)) and not v:  # this is an empty container
            continue
        if isinstance(v, dict):
            clean[k] = _clean_dict(v)
        elif isinstance(v, list):
            new_list = list()
            for i in v:
                if isinstance(i, dict):
                    new_list.append(_clean_dict(i))
                else:
                    new_list.append(i)
            clean[k] = new_list
        else:
            clean[k] = v
    return clean


def get_clean_dict(obj: HikaruBase) -> dict:
    """
    turns an instance of a HikaruBase into a dict with values of None

    :param obj: some api_version_group of subclass of HikaruBase
    :return: a dict representation of the obj instance, but if any value
        in the dict was originally None, that key:value is removed from the
        returned dict, hence it is a minimal representation
    """
    initial_dict = asdict(obj)
    clean_dict = _clean_dict(initial_dict)
    return clean_dict


def get_yaml(obj: HikaruBase) -> str:
    """
    Creates a YAML representation of a HikaruBase model

    :param obj: instance of some HikaruBase subclass
    :return: big ol' string of YAML that represents the model
    """
    d: dict = get_clean_dict(obj)
    yaml = YAML()
    yaml.indent(offset=2, sequence=4)
    sio = StringIO()
    yaml.dump(d, sio)
    return "\n".join(["---", sio.getvalue()])


def get_json(obj: HikaruBase) -> str:
    """
    Creates a JSON representation of a HikaruBase model

    NOTE: current there is no way to go from JSON back to YAML or Python. This
        function is must useful for storing a model's representation in a
        document database.

    :param obj: instance of a HikaruBase model
    :return: string containing JSON that represents the information in the model
    """
    d = get_clean_dict(obj)
    s = json.dumps(d)
    return s


def load_full_yaml(path=None, stream=None, yaml=None) -> List[HikaruBase]:
    if path is None and stream is None and yaml is None:
        raise RuntimeError("One of path, stream, or yaml must be specified")
    objs = []
    if path:
        f = open(path, "r")
    if stream:
        f = stream
    if yaml:
        to_parse = yaml
    else:
        to_parse = f.read()
    parser = YAML()
    docs = list(parser.load_all(to_parse))
    for doc in docs:
        apiVersion = doc.get('apiVersion').split('/')[-1]
        kind = doc.get('kind')
        klass = kinds.get((apiVersion, kind))
        if klass is None:
            raise RuntimeError(f"No model class for {(apiVersion, kind)}")
        np = num_positional(klass.__init__) - 1
        inst = klass(*([None] * np), **{})
        inst.parse(doc)
        objs.append(inst)

    return objs


kinds = {('v1', 'APIGroup'): APIGroup,
 ('v1', 'APIGroupList'): APIGroupList,
 ('v1', 'APIResourceList'): APIResourceList,
 ('v1', 'APIService'): APIService,
 ('v1', 'APIServiceList'): APIServiceList,
 ('v1', 'APIVersions'): APIVersions,
 ('v1', 'Binding'): Binding,
 ('v1', 'BoundObjectReference'): BoundObjectReference,
 ('v1', 'CSIDriver'): CSIDriver,
 ('v1', 'CSIDriverList'): CSIDriverList,
 ('v1', 'CSINode'): CSINode,
 ('v1', 'CSINodeList'): CSINodeList,
 ('v1', 'CertificateSigningRequest'): CertificateSigningRequest,
 ('v1', 'CertificateSigningRequestList'): CertificateSigningRequestList,
 ('v1', 'ClusterRole'): ClusterRole,
 ('v1', 'ClusterRoleBinding'): ClusterRoleBinding,
 ('v1', 'ClusterRoleBindingList'): ClusterRoleBindingList,
 ('v1', 'ClusterRoleList'): ClusterRoleList,
 ('v1', 'ComponentStatus'): ComponentStatus,
 ('v1', 'ComponentStatusList'): ComponentStatusList,
 ('v1', 'ConfigMap'): ConfigMap,
 ('v1', 'ConfigMapList'): ConfigMapList,
 ('v1', 'ControllerRevision'): ControllerRevision,
 ('v1', 'ControllerRevisionList'): ControllerRevisionList,
 ('v1', 'CrossVersionObjectReference'): CrossVersionObjectReference,
 ('v1', 'DaemonSet'): DaemonSet,
 ('v1', 'DaemonSetList'): DaemonSetList,
 ('v1', 'DeleteOptions'): DeleteOptions,
 ('v1', 'Deployment'): Deployment,
 ('v1', 'DeploymentList'): DeploymentList,
 ('v1', 'Endpoints'): Endpoints,
 ('v1', 'EndpointsList'): EndpointsList,
 ('v1', 'EphemeralContainers'): EphemeralContainers,
 ('v1', 'Event'): Event,
 ('v1', 'EventList'): EventList,
 ('v1', 'HorizontalPodAutoscaler'): HorizontalPodAutoscaler,
 ('v1', 'HorizontalPodAutoscalerList'): HorizontalPodAutoscalerList,
 ('v1', 'Ingress'): Ingress,
 ('v1', 'IngressClass'): IngressClass,
 ('v1', 'IngressClassList'): IngressClassList,
 ('v1', 'IngressList'): IngressList,
 ('v1', 'Job'): Job,
 ('v1', 'JobList'): JobList,
 ('v1', 'Lease'): Lease,
 ('v1', 'LeaseList'): LeaseList,
 ('v1', 'LimitRange'): LimitRange,
 ('v1', 'LimitRangeList'): LimitRangeList,
 ('v1', 'LocalSubjectAccessReview'): LocalSubjectAccessReview,
 ('v1', 'MutatingWebhookConfiguration'): MutatingWebhookConfiguration,
 ('v1', 'MutatingWebhookConfigurationList'): MutatingWebhookConfigurationList,
 ('v1', 'Namespace'): Namespace,
 ('v1', 'NamespaceList'): NamespaceList,
 ('v1', 'NetworkPolicy'): NetworkPolicy,
 ('v1', 'NetworkPolicyList'): NetworkPolicyList,
 ('v1', 'Node'): Node,
 ('v1', 'NodeList'): NodeList,
 ('v1', 'ObjectReference'): ObjectReference,
 ('v1', 'OwnerReference'): OwnerReference,
 ('v1', 'PersistentVolume'): PersistentVolume,
 ('v1', 'PersistentVolumeClaim'): PersistentVolumeClaim,
 ('v1', 'PersistentVolumeClaimList'): PersistentVolumeClaimList,
 ('v1', 'PersistentVolumeList'): PersistentVolumeList,
 ('v1', 'Pod'): Pod,
 ('v1', 'PodList'): PodList,
 ('v1', 'PodTemplate'): PodTemplate,
 ('v1', 'PodTemplateList'): PodTemplateList,
 ('v1', 'PriorityClass'): PriorityClass,
 ('v1', 'PriorityClassList'): PriorityClassList,
 ('v1', 'ReplicaSet'): ReplicaSet,
 ('v1', 'ReplicaSetList'): ReplicaSetList,
 ('v1', 'ReplicationController'): ReplicationController,
 ('v1', 'ReplicationControllerList'): ReplicationControllerList,
 ('v1', 'ResourceQuota'): ResourceQuota,
 ('v1', 'ResourceQuotaList'): ResourceQuotaList,
 ('v1', 'Role'): Role,
 ('v1', 'RoleBinding'): RoleBinding,
 ('v1', 'RoleBindingList'): RoleBindingList,
 ('v1', 'RoleList'): RoleList,
 ('v1', 'RuntimeClass'): RuntimeClass,
 ('v1', 'RuntimeClassList'): RuntimeClassList,
 ('v1', 'Scale'): Scale,
 ('v1', 'Secret'): Secret,
 ('v1', 'SecretList'): SecretList,
 ('v1', 'SelfSubjectAccessReview'): SelfSubjectAccessReview,
 ('v1', 'SelfSubjectRulesReview'): SelfSubjectRulesReview,
 ('v1', 'Service'): Service,
 ('v1', 'ServiceAccount'): ServiceAccount,
 ('v1', 'ServiceAccountList'): ServiceAccountList,
 ('v1', 'ServiceList'): ServiceList,
 ('v1', 'StatefulSet'): StatefulSet,
 ('v1', 'StatefulSetList'): StatefulSetList,
 ('v1', 'Status'): Status,
 ('v1', 'StorageClass'): StorageClass,
 ('v1', 'StorageClassList'): StorageClassList,
 ('v1', 'SubjectAccessReview'): SubjectAccessReview,
 ('v1', 'TokenReview'): TokenReview,
 ('v1', 'ValidatingWebhookConfiguration'): ValidatingWebhookConfiguration,
 ('v1', 'ValidatingWebhookConfigurationList'): ValidatingWebhookConfigurationList,
 ('v1', 'VolumeAttachment'): VolumeAttachment,
 ('v1', 'VolumeAttachmentList'): VolumeAttachmentList}

