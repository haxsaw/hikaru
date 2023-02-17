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
from typing import Tuple, Optional, Dict
from threading import current_thread, Thread


# this is the prefix to use for attributes that otherwise start with '$'
dprefix = 'dollar_'


_default_release = None

_default_release_by_thread: Dict[str, str] = {}


def get_default_release() -> Optional[str]:
    """
    Returns the currently set default release to use when loading YAML/JSON

    :return: string; the value of the default release for the current thread.
        If unknown, the current global default release is returned, whatever
        the value (possibly None).
    """
    global _default_release
    ct: Thread = current_thread()
    def_rel = _default_release_by_thread.get(ct.name)
    if def_rel is None:
        if _default_release is None:
            from hikaru.model import default_release
            _default_release = default_release
        def_rel = _default_release
    return def_rel


def set_default_release(relname: str):
    """
    Sets the default release for the current thread.

    :param relname: string; the name of the release to use for this same thread.
         NOTE: there is no checking that this release package exists!
    """
    ct: Thread = current_thread()
    _default_release_by_thread[ct.name] = relname


def set_global_default_release(relname: str):
    """
    Sets the global default release to use to the specified release

    This is the release value used if there is no per-thread default release

    :param relname: string; the name of a release module in the model
        package. NOTE: there is no checking that this release package
        exists!
    """
    global _default_release
    _default_release = relname


def process_api_version(api_version: str) -> Tuple[str, str]:
    """
    Takes the value of an apiVersion property and returns group and version

    :param api_version: the value of a apiVersion property
    :return: tuple of two strings: published object group, version. If the
        group is unspecified it defaults to 'core'
    :raises TypeError: if api_version isn't a string
    """
    if not isinstance(api_version, str):
        raise TypeError("api_version is not a str")
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
    version = name_parts[-2] if len(name_parts) >= 2 else None
    if version and (version.startswith("v1") or version.startswith("v2")):
        swagger_group = ".".join(name_parts[:-2])
    else:
        version = None
        swagger_group = ".".join(name_parts[:-1])
    if not swagger_group:
        swagger_group = None
    return swagger_group, version, name


def make_swagger_name(group: str, version: str, name: str) -> str:
    """
    This function creates properly formatted swagger names for an object
    :param group: string; group that the object belongs to
    :param version: string; version that the object belongs to
    :param name: string: name of the object (class)
    :return: A single string that combines the three input elements; can
        be fed to process_swagger_name() and receive the original broken-out
        parts.
    """
    return f"{group}.{version}.{name}" if group is not None else f"{version}.{name}"


def camel_to_pep8(name: str) -> str:
    """
    Converts a camelcase identifier name a PEP8 param name using underscores
    :param name: string; a possibly camel-cased name
    :return: a PEP8 equivalent with the upper case leter mapped to '_<lower>'

    NOTE: will turn strings like 'FQDN' to '_f_q_d_n'; probably not what you want.
    """
    letters = [a if a.islower() else f"_{a.lower()}"
               for a in name]
    result = ''.join(letters)
    # ok, there are rare names that start with an uppercase letter, which
    # the above will turn into '_<lower version>'. We need to spot these and
    # turn them back into the upper case version without the leading '_'
    if result[0] == "_":
        result = result[1].upper() + result[2:]
    # icky patch for when we've split apart 'API', 'CSI', or 'V<number>'
    return (result.replace("a_p_i", "api").replace("c_s_i", "csi").
            replace('v_1', 'v1').replace('v_2', 'v2').replace('beta_1', 'beta1').
            replace('beta_2', 'beta2').replace('alpha_1', 'alpha1').
            replace('f_q_d_n', 'fqdn').replace('u_u_i_d', 'uuid').
            replace('c_i_d_r', 'cidr').
            replace('_i_d', '_id').replace('t_l_s', 'tls'))


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


# inverted version of the above map
swagger_to_api_group_map = {v: k for k, v in _api_group_swagger_map.items()}
