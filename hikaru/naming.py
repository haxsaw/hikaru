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
from typing import Tuple, Optional


def process_api_version(api_version: str) -> Tuple[str, str]:
    """
    Takes the value of an apiVersion property and returns group and version
    :param api_version: the value of a apiVersion property
    :return: tuple of two strings: published object group, version
    """
    parts = api_version.split("/")
    if len(parts) == 1:
        group = "core"
        api_version = parts[0]
    else:
        group, api_version = parts
    return group, api_version


def full_swagger_name(sname: str) -> str:
    """
    takes any full swagger name, either def or ref, and only returns the name part
    :param sname: string containing a swagger name for some object
    :return: a return with just the name, no other bits
    """
    base_parts = sname.split("/")
    return base_parts[-1]


def process_swagger_name(sname: str) -> Tuple[str, str, str]:
    """
    This takes a swagger file name, either ref or name, and splits it into
    its components
    :param sname: Either the key name from a definition in the swagger
        file, or a $ref name of an embedded object that is a property
    :return: tuple of three strings: swagger group, version, name
    """
    full_name = full_swagger_name(sname)
    name_parts = full_name.split(".")
    name = name_parts[-1]
    version = name_parts[-2]
    if version.startswith("v1") or version.startswith("v2"):
        swagger_group = ".".join(name_parts[:-2])
    else:
        version = None
        swagger_group = ".".join(name_parts[:-1])
    return swagger_group, version, name


# mapping the group in apiVersion to the swagger group string
_api_group_swagger_map = {
    "admissionregistration.k8s.io": "io.k8s.api.admissionregistration",
    "apiextensions.k8s.io": "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions",
    "apiregistration.k8s.io": "io.k8s.kube-aggregator.pkg.apis.apiregistration",
    "apps": "io.k8s.api.apps",
    "authentication.k8s.io": "io.k8s.api.authentication",
    "authorization.k8s.io": "io.k8s.api.authorization",
    "autoscaling": "io.k8s.api.autoscaling",
    "batch": "io.k8s.api.batch",
    "certificates.k8s.io": "io.k8s.api.certificates",
    "coordination.k8s.io": "io.k8s.api.coordination",
    "core": "io.k8s.api.core",
    "discovery.k8s.io": "io.k8s.api.discovery",
    "events.k8s.io": "io.k8s.api.events",
    "extensions": "io.k8s.api.extensions",
    "flowcontrol.apiserver.k8s.io": "io.k8s.api.flowcontrol",
    "internal.apiserver.k8s.io": "io.k8s.api.apiserverinternal",
    "networking.k8s.io": "io.k8s.api.networking",
    "node.k8s.io": "io.k8s.api.node",
    "policy": "io.k8s.api.policy",
    "rbac.authorization.k8s.io": "io.k8s.api.rbac",
    "scheduling.k8s.io": "io.k8s.api.scheduling",
    "storage.k8s.io": "io.k8s.api.storage"
}


def get_swagger_group_from_api_version_group(api_version_group: str) -> str:
    """
    returns the associated swagger group string for the provided group from apiVersion
    :param api_version_group: the group portion of the apiVersion string
    :return: string that is the associated group from the swagger spec
    """
    return _api_group_swagger_map[api_version_group]
