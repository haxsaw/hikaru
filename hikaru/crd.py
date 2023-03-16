#
# Copyright (c) 2023 Incisive Technology Ltd
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
from inspect import isclass, Parameter
from dataclasses import is_dataclass, InitVar, dataclass
from typing import Optional, Dict, Union, List
from .meta import HikaruDocumentBase, HikaruBase, WatcherDescriptor
from .utils import (get_origin, get_args, HikaruCallableTyper, ParamSpec, get_hct,
                    FieldMetadata as fm, Response)
from .naming import get_default_release, process_api_version
from hikaru.version_kind import register_version_kind_class
from hikaru import get_clean_dict
from kubernetes.client.api_client import ApiClient

ignorable = {'apiVersion', 'kind', 'metadata', 'group'}
type_map = {str: "string", int: "integer", float: "float", bool: "boolean"}


def get_crd_schema(cls, jsp_class: Optional[type] = None):
    """
    Return a JSONSchemaProps instance suitable for describing this class in a CustomResourceDefinition msg

    Only works with a dataclass!

    Limitations:

    - Cannot handle recursively defined classes (yet), neither direct nor indirect

    """
    if jsp_class is not None:
        if jsp_class.__name__ != "JSONSchemaProps":
            raise TypeError("The jsp_class parameter must be one of the JSONSchemaProps classes for "
                            "one of the supported releases under hikaru.model")
    else:
        def_release = get_default_release()
        try:
            mod = import_module(".v1", f"hikaru.model.{def_release}")
        except ImportError as e:
            raise ImportError(f"Couldn't import the module with DeleteOptions: {e}")
        jsp_class = getattr(mod, "JSONSchemaProps")
        if jsp_class is None:
            raise RuntimeError("No JSONSchemaProps class supplied, and one can't be found "
                               "in the v1 module of the default release")

    schema = _process_cls(cls)
    jsp = jsp_class(**schema)
    return jsp


def _process_cls(cls) -> dict:
    if not is_dataclass(cls):
        raise TypeError(f"The class {cls.__name__} is not a dataclass; Hikaru can't generate "
                        f"a schema for it.")
    props = {}
    jsp_args = {"type": "object", "properties": props}
    required = []
    hct: HikaruCallableTyper = get_hct(cls)
    p: ParamSpec
    for p in hct.values():
        if p.name in ignorable:
            continue
        if isinstance(p.hint_type, InitVar):
            continue
        if p.default is Parameter.empty:
            required.append(p.name)
        prop = props[p.name] = {}
        metadata = p.metadata
        description = metadata.get(fm.DESCRIPTION_KEY)
        if description is not None:
            prop['description'] = description
        enums = metadata.get(fm.ENUM_KEY)
        if enums is not None:
            prop['enum'] = enums
        if isclass(p.annotation) and issubclass(p.annotation, HikaruBase):
            if not is_dataclass(p.annotation):
                raise TypeError(f"The class {p.annotation.__name__} is not a dataclass; Hikaru can't generate "
                                f"a schema for it.")
            prop.update(_process_cls(p.annotation))
        elif p.annotation in type_map:
            prop.update({"type": type_map[p.annotation]})
        else:
            initial_type = p.annotation
            origin = get_origin(initial_type)
            if origin is Union:
                type_args = get_args(p.annotation)
                initial_type = type_args[0]
                if initial_type in type_map:
                    prop["type"] = type_map[initial_type]
                    continue
            origin = get_origin(initial_type)
            if origin in (list, List):
                prop["type"] = "array"
                list_of_type = get_args(initial_type)[0]
                if list_of_type in type_map:
                    prop["items"] = {"type": type_map[list_of_type]}
                elif isclass(list_of_type) and issubclass(list_of_type, HikaruBase):
                    if not is_dataclass(list_of_type):
                        raise TypeError(f"The list item type of attribute {p.name} is a subclass "
                                        f"of HikaruBase but is not a dataclass")
                    prop["items"] = _process_cls(list_of_type)
                else:
                    raise TypeError(f"Don't know how to process {p.name}'s type {p.annotation}; "
                                    f"origin: {get_origin(p.annotation)}, args: {get_args(p.annotation)}")
            elif isclass(initial_type) and issubclass(initial_type, HikaruBase):
                if not is_dataclass(initial_type):
                    raise TypeError(f"The type of {p.name} is a subclass of HikaruBase "
                                    f"but is not a dataclass")
                prop.update(_process_cls(initial_type))
            elif origin in (dict, Dict) or initial_type is object:
                prop["type"] = "object"
                # @TODO we currently don't have enough data to exactly how to output
                # this; we've lost some info if it came from K8s swagger. While this is
                # certainly an object, it's rendering can either involve key/value
                # pairs or a single string in a particular format. This is something
                # we can eventually clarify, but for now we'll just treat it as a k/v
                # pairs collection
                prop["additionalProperties"] = {"type": "string"}
            else:
                raise TypeError(f"Don't know how to process type {p.name}'s {p.annotation}; "
                                f"origin: {get_origin(p.annotation)}, args: {get_args(p.annotation)}")
    if required:
        jsp_args["required"] = required

    return jsp_args


class _RegisterCRD(object):
    def __init__(self, plural_name: str, api_version: str, is_namespaced: bool = True):
        group, version = process_api_version(api_version)
        self.group: str = group
        self.version: str = version
        self.plural_name: str = plural_name
        self.is_namespaced: bool = is_namespaced


_crd_registration_details: Dict[type(HikaruDocumentBase), _RegisterCRD] = {}


class HikaruCRDCRUDDocumentMixin(object):
    """
    HikaruDocumentBase mixin to add support for CRUD methods

    This class provides adjust capabilities to subclasses of HikaruDocumentBase,
    specifically for generalized CRUD operations on CRD-based resources.

    Add this class to the list of bases for classes meant to be used as the basis
    for custom resource definitions. It will provide create(), read(), update(),
    and delete() methods, as well as a generalized API call for supporting
    additional related methods.

    NOTE: this mixin only works properly when used with HikaruDocumentBase as
        a sibling base class
    """

    def __post_init__(self, *args, **kwargs):
        super(HikaruCRDCRUDDocumentMixin, self).__post_init__(*args, **kwargs)
        client = kwargs.get('client')
        if client is None:
            client = ApiClient()
        self.client: ApiClient = client

    @classmethod
    def get_additional_watch_args(cls) -> dict:
        reg: _RegisterCRD = _crd_registration_details.get(cls)
        if reg is None:
            raise RuntimeError(f"Class {cls.__name__} has not been registered as "
                               f"a CRD with register_crd_schema()")
        return {'plural': reg.plural_name,
                'version': reg.version,
                'group': reg.group}

    def api_call(self, method: str, url: str,
                 alt_body: Optional[HikaruDocumentBase] = None,
                 field_manager: Optional[str] = None,
                 field_validation: Optional[str] = None,
                 pretty: Optional[bool] = None,
                 dry_run: Optional[str] = None,
                 async_req: bool = False,):
        # things that won't get filled out further
        form_params = []
        local_var_files = {}
        collection_formats = {}
        path_params = {}
        response_type = object

        # now stuff driven by the request
        if alt_body is not None:
            body = get_clean_dict(alt_body)
        else:
            body = get_clean_dict(self)
        query_params = []
        if pretty is not None:  # noqa: E501
            query_params.append(('pretty', pretty))
        if dry_run is not None:  # noqa: E501
            query_params.append(('dryRun', dry_run))  # noqa: E501
        if field_manager is not None:  # noqa: E501
            query_params.append(('fieldManager', field_manager))  # noqa: E501
        if field_validation is not None:  # noqa: E501
            query_params.append(('fieldValidation', field_validation))  # noqa: E501

        header_params = dict()
        header_params['Accept'] = self.client.select_header_accept(
            ['application/json', 'application/yaml', 'application/vnd.kubernetes.protobuf'])  # noqa: E501
        auth_settings = ['BearerToken']  # noqa: E501
        result = self.client.call_api(url,
                                      method,
                                      path_params,
                                      header_params,
                                      body=body,
                                      post_params=form_params,
                                      files=local_var_files,
                                      response_type=response_type,
                                      auth_settings=auth_settings,
                                      async_req=async_req,
                                      collection_formats=collection_formats)
        codes_returning_objects = (200, 201, 202)
        return Response[self.__class__](result, codes_returning_objects)

    def create(self, field_manager: Optional[str] = None,
               field_validation: Optional[str] = None,
               pretty: Optional[bool] = None,
               dry_run: Optional[str] = None,
               async_req: bool = False):
        method: str = "POST"
        reg_details: _RegisterCRD = _crd_registration_details.get(self.__class__)
        if reg_details is None:
            raise TypeError(f"The class {self.__class__.__name__} has not been registered "
                            f"with register_crd_schema()")
        parts = self.apiVersion.split("/")
        if len(parts) != 2:
            raise TypeError(f"The apiVersion does not appear to have exactly two parts "
                            f"(group/version) split with a '/'")
        group, version = parts
        if reg_details.is_namespaced:
            namespace = self.metadata.namespace
            if not namespace:
                namespace = "default"
            url: str = f"/apis/{group}/{version}/namespaces/{namespace}/{reg_details.plural_name}"
        else:
            url: str = f"/apis/{group}/{version}/{reg_details.plural_name}"
        return self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)

    def _get_existing_url(self) -> str:
        reg_details: _RegisterCRD = _crd_registration_details.get(self.__class__)
        if reg_details is None:
            raise TypeError(f"The class {self.__class__.__name__} has not been registered "
                            f"with register_crd_schema()")
        parts = self.apiVersion.split("/")
        if len(parts) != 2:
            raise TypeError(f"The apiVersion does not appear to have exactly two parts "
                            f"(group/version) split with a '/'")
        group, version = parts
        if reg_details.is_namespaced:
            namespace = self.metadata.namespace
            if not namespace:
                namespace = "default"
            url: str = f"/apis/{group}/{version}/namespaces/{namespace}/{reg_details.plural_name}/{self.metadata.name}"
        else:
            url: str = f"/apis/{group}/{version}/{reg_details.plural_name}/{self.metadata.name}"
        return url

    def read(self, field_manager: Optional[str] = None,
             field_validation: Optional[str] = None,
             pretty: Optional[bool] = None,
             dry_run: Optional[str] = None,
             async_req: bool = False):
        method: str = "GET"
        url = self._get_existing_url()
        return self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)

    def update(self, field_manager: Optional[str] = None,
               field_validation: Optional[str] = None,
               pretty: Optional[bool] = None,
               dry_run: Optional[str] = None,
               async_req: bool = False):
        method: str = "PUT"
        url: str = self._get_existing_url()
        return self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)

    def delete(self, field_manager: Optional[str] = None,
               field_validation: Optional[str] = None,
               pretty: Optional[bool] = None,
               dry_run: Optional[str] = None,
               async_req: bool = False):
        """
        Delete the resource using the DeleteOptions from the current release.

        :param field_manager:
        :param field_validation:
        :param pretty:
        :param dry_run:
        :param async_req:
        :return:
        """
        def_release = get_default_release()
        try:
            mod = import_module(".v1", f"hikaru.model.{def_release}")
        except ImportError as e:
            raise ImportError(f"Couldn't import the module with DeleteOptions: {e}")

        DeleteOptions = getattr(mod, "DeleteOptions")
        method: str = "DELETE"
        url: str = self._get_existing_url()
        do: DeleteOptions = DeleteOptions()
        return self.api_call(method, url, field_manager=field_manager,
                             alt_body=do,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)


def register_crd_schema(crd_cls, plural_name: str, is_namespaced: bool = True):
    if not issubclass(crd_cls, HikaruDocumentBase) or not issubclass(crd_cls, HikaruCRDCRUDDocumentMixin):
        raise TypeError("A CRD registered class must be a subclass of both "
                        "HikaruCRDDocumentBase and HikaruDocumentBase")
    if not hasattr(crd_cls, 'apiVersion') or not hasattr(crd_cls, 'kind'):
        raise TypeError("The decorated class must have both an apiVersion and kind attribute")
    if not is_dataclass(crd_cls):
        raise TypeError(f"The class {crd_cls.__name__} must be a dataclass")
    # _, version = process_api_version(crd_cls.apiVersion)
    # register_version_kind_class(crd_cls, version, crd_cls.kind)
    register_version_kind_class(crd_cls, crd_cls.apiVersion, crd_cls.kind)
    crdr = _RegisterCRD(plural_name, crd_cls.apiVersion, is_namespaced=is_namespaced)
    _crd_registration_details[crd_cls] = crdr
    # set the proper watcher
    if is_namespaced:
        crd_cls._namespaced_watcher = WatcherDescriptor(
            "kubernetes",
            ".client",
            "CustomObjectsApi",
            "list_namespaced_custom_object_with_http_info")
    else:
        crd_cls._watcher = WatcherDescriptor(
            "kubernetes",
            ".client",
            "CustomObjectsApi",
            "list_cluster_custom_object")
    return crd_cls

