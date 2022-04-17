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
"""
DO NOT EDIT THIS FILE!

This module is automatically generated using the Hikaru build program that turns
a Kubernetes swagger spec into the code for the hikaru.model package.
"""

from .v1 import *


class Watchables(object):  # pragma: no cover
    """
    Attributes of this class are classes that support watches without the namespace
    keyword argument
    """
    MutatingWebhookConfigurationList = MutatingWebhookConfigurationList
    MutatingWebhookConfiguration = MutatingWebhookConfiguration
    ValidatingWebhookConfigurationList = ValidatingWebhookConfigurationList
    ValidatingWebhookConfiguration = ValidatingWebhookConfiguration
    ControllerRevisionList = ControllerRevisionList
    ControllerRevision = ControllerRevision
    DaemonSetList = DaemonSetList
    DaemonSet = DaemonSet
    DeploymentList = DeploymentList
    Deployment = Deployment
    ReplicaSetList = ReplicaSetList
    ReplicaSet = ReplicaSet
    StatefulSetList = StatefulSetList
    StatefulSet = StatefulSet
    HorizontalPodAutoscalerList = HorizontalPodAutoscalerList
    HorizontalPodAutoscaler = HorizontalPodAutoscaler
    CronJobList = CronJobList
    CronJob = CronJob
    JobList = JobList
    Job = Job
    CertificateSigningRequestList = CertificateSigningRequestList
    CertificateSigningRequest = CertificateSigningRequest
    LeaseList = LeaseList
    Lease = Lease
    ComponentStatusList = ComponentStatusList
    ComponentStatus = ComponentStatus
    ConfigMapList = ConfigMapList
    ConfigMap = ConfigMap
    EndpointsList = EndpointsList
    Endpoints = Endpoints
    LimitRangeList = LimitRangeList
    LimitRange = LimitRange
    NamespaceList = NamespaceList
    Namespace = Namespace
    NodeList = NodeList
    Node = Node
    PersistentVolumeClaimList = PersistentVolumeClaimList
    PersistentVolumeClaim = PersistentVolumeClaim
    PersistentVolumeList = PersistentVolumeList
    PersistentVolume = PersistentVolume
    PodList = PodList
    Pod = Pod
    PodTemplateList = PodTemplateList
    PodTemplate = PodTemplate
    ReplicationControllerList = ReplicationControllerList
    ReplicationController = ReplicationController
    ResourceQuotaList = ResourceQuotaList
    ResourceQuota = ResourceQuota
    SecretList = SecretList
    Secret = Secret
    ServiceAccountList = ServiceAccountList
    ServiceAccount = ServiceAccount
    ServiceList = ServiceList
    Service = Service
    EndpointSliceList = EndpointSliceList
    EndpointSlice = EndpointSlice
    IngressClassList = IngressClassList
    IngressClass = IngressClass
    IngressList = IngressList
    Ingress = Ingress
    NetworkPolicyList = NetworkPolicyList
    NetworkPolicy = NetworkPolicy
    RuntimeClassList = RuntimeClassList
    RuntimeClass = RuntimeClass
    PodDisruptionBudgetList = PodDisruptionBudgetList
    PodDisruptionBudget = PodDisruptionBudget
    ClusterRoleBindingList = ClusterRoleBindingList
    ClusterRoleBinding = ClusterRoleBinding
    ClusterRoleList = ClusterRoleList
    ClusterRole = ClusterRole
    RoleBindingList = RoleBindingList
    RoleBinding = RoleBinding
    RoleList = RoleList
    Role = Role
    PriorityClassList = PriorityClassList
    PriorityClass = PriorityClass
    CSIDriverList = CSIDriverList
    CSIDriver = CSIDriver
    CSINodeList = CSINodeList
    CSINode = CSINode
    StorageClassList = StorageClassList
    StorageClass = StorageClass
    VolumeAttachmentList = VolumeAttachmentList
    VolumeAttachment = VolumeAttachment
    CustomResourceDefinitionList = CustomResourceDefinitionList
    CustomResourceDefinition = CustomResourceDefinition
    APIServiceList = APIServiceList
    APIService = APIService
    EventList = EventList
    Event = Event


watchables = Watchables


class NamespacedWatchables(object):  # pragma: no cover
    """
    Attributes of this class are classes that support watches with the namespace
    keyword argument
    """
    ControllerRevisionList = ControllerRevisionList
    DaemonSetList = DaemonSetList
    DeploymentList = DeploymentList
    ReplicaSetList = ReplicaSetList
    StatefulSetList = StatefulSetList
    HorizontalPodAutoscalerList = HorizontalPodAutoscalerList
    CronJobList = CronJobList
    JobList = JobList
    LeaseList = LeaseList
    ConfigMapList = ConfigMapList
    EndpointsList = EndpointsList
    LimitRangeList = LimitRangeList
    PersistentVolumeClaimList = PersistentVolumeClaimList
    PodList = PodList
    PodTemplateList = PodTemplateList
    ReplicationControllerList = ReplicationControllerList
    ResourceQuotaList = ResourceQuotaList
    SecretList = SecretList
    ServiceAccountList = ServiceAccountList
    ServiceList = ServiceList
    EndpointSliceList = EndpointSliceList
    IngressList = IngressList
    NetworkPolicyList = NetworkPolicyList
    PodDisruptionBudgetList = PodDisruptionBudgetList
    RoleBindingList = RoleBindingList
    RoleList = RoleList
    EventList = EventList
    ControllerRevision = ControllerRevision
    DaemonSet = DaemonSet
    Deployment = Deployment
    ReplicaSet = ReplicaSet
    StatefulSet = StatefulSet
    HorizontalPodAutoscaler = HorizontalPodAutoscaler
    CronJob = CronJob
    Job = Job
    Lease = Lease
    ConfigMap = ConfigMap
    Endpoints = Endpoints
    LimitRange = LimitRange
    PersistentVolumeClaim = PersistentVolumeClaim
    Pod = Pod
    PodTemplate = PodTemplate
    ReplicationController = ReplicationController
    ResourceQuota = ResourceQuota
    Secret = Secret
    ServiceAccount = ServiceAccount
    Service = Service
    EndpointSlice = EndpointSlice
    Ingress = Ingress
    NetworkPolicy = NetworkPolicy
    PodDisruptionBudget = PodDisruptionBudget
    RoleBinding = RoleBinding
    Role = Role
    Event = Event


namespaced_watchables = NamespacedWatchables
