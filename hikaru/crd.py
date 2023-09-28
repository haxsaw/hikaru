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
from dataclasses import is_dataclass, InitVar
from typing import Optional, Dict, Union, List
from .meta import HikaruDocumentBase, HikaruBase, WatcherDescriptor, FieldMetadata as fm
from .utils import (get_origin, get_args, HikaruCallableTyper, ParamSpec, get_hct,
                    Response)
from .naming import get_default_release, process_api_version
from hikaru.version_kind import register_version_kind_class
from hikaru import get_clean_dict
from kubernetes.client.api_client import ApiClient

_ignorable = {'apiVersion', 'kind', 'metadata', 'group'}
_type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}


# there are no production uses to change this value, but testing may alter it
model_root_package = "hikaru.model"


def get_crd_schema(cls, jsp_class: Optional[type] = None):
    """
    Return a JSONSchemaProps instance suitable for describing this class in a CustomResourceDefinition msg

    This function takes a HikaruBase/HikaruDocumentBase subclass (not instance!) and returns a JSONSchemaProps
    object that describes a schema that reflects the class. The function uses get_default_release() to determine
    which release to acquire the JSONSchemaProps class from. The user may also manually supply the JSONSchemaProps
    class to use to return the schema. The returned JSONSchemaProps object can then be used in creating a
    CustomResourceDefinition.

    Only works with a dataclass that is derived from HikaruBase!

    Limitations:

    - Cannot handle recursively defined classes (yet), neither direct nor indirect.
    - Cannot handle dicts whose values are anything but strings; if you need more complex types
      use a nested class.
    - Cannot handle Unions of multiple types.

    :param cls: a class object, derived from at least HikaruBase. A schema for this class will be
        generated and returned as the value of the function.
    :param jsp_class: optional type; should be a JSONSchemaProps class object (not instance). By default, this
        function uses get_default_release() to determine which of the currently supported JSONSchemaProps classes
        to use to return the schema. This parameter allows the caller to specify a particular release's class.
    """
    if jsp_class is not None:
        if jsp_class.__name__ != "JSONSchemaProps":
            raise TypeError("The jsp_class parameter must be one of the JSONSchemaProps classes for "
                            "one of the supported releases under hikaru.model")
    else:
        # pragma: no cover
        def_release = get_default_release()
        try:
            mod = import_module(".v1", f"{model_root_package}.{def_release}")
        except ImportError as e:  # pragma: no cover
            raise ImportError(f"Couldn't import the module with DeleteOptions: {e}")
        jsp_class = getattr(mod, "JSONSchemaProps")
    if jsp_class is None:  # pragma: no cover
        raise ValueError("No JSONSchemaProps class supplied, and one can't be found "
                         "in the v1 module of the default release")

    schema = _process_cls(cls)
    jsp = jsp_class(**schema)
    return jsp


def _set_if_non_null(metadata: dict, mkey: str, prop: dict, pkey: str):
    val = metadata.get(mkey)
    if val is not None:
        prop[pkey] = val


NoneType = type(None)


def _check_simple_type_modifiers(ptype: type, metadata: dict, prop: dict):
    _set_if_non_null(metadata, fm.FORMAT_KEY, prop, 'format')
    if ptype in (int, float):
        _set_if_non_null(metadata, fm.MIN_KEY, prop, 'minimum')
        _set_if_non_null(metadata, fm.EX_MIN_KEY, prop, 'exclusiveMinimum')
        _set_if_non_null(metadata, fm.MAX_KEY, prop, 'maximum')
        _set_if_non_null(metadata, fm.EX_MAX_KEY, prop, 'exclusiveMaximum')
        _set_if_non_null(metadata, fm.MULTIPLE_OF_KEY, prop, 'multipleOf')
    elif ptype is str:
        _set_if_non_null(metadata, fm.PATTERN_KEY, prop, 'pattern')
    return


def _check_array_modifiers(metadata: dict, prop: dict):
    _set_if_non_null(metadata, fm.MIN_ITEMS_KEY, prop, 'minItems')
    _set_if_non_null(metadata, fm.MAX_ITEMS_KEY, prop, 'maxItems')
    _set_if_non_null(metadata, fm.UNIQUE_ITEMS_KEY, prop, 'uniqueItems')


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
        # can we skip this one?
        if p.name in _ignorable or isinstance(p.hint_type, InitVar):
            continue
        # if no default, then the param is required
        if p.default is Parameter.empty:
            required.append(p.name)

        # ok, we need to process it. set up the prop dict and get the field metadata
        prop = props[p.name] = {}
        metadata = p.metadata
        _set_if_non_null(metadata, fm.DESCRIPTION_KEY, prop, "description")

        if isclass(p.annotation) and issubclass(p.annotation, HikaruBase):
            if not is_dataclass(p.annotation):
                raise TypeError(f"The class {p.annotation.__name__} is not a dataclass; Hikaru can't generate "
                                f"a schema for it.")  # pragma: no cover
            prop.update(_process_cls(p.annotation))
        elif p.annotation in _type_map:
            prop.update({"type": _type_map[p.annotation]})
            if prop['type'] != 'boolean':
                _set_if_non_null(metadata, fm.ENUM_KEY, prop, 'enum')
            _check_simple_type_modifiers(p.annotation, metadata, prop)
        else:
            initial_type = p.annotation
            origin = get_origin(initial_type)
            if origin is Union:
                type_args = [a for a in get_args(p.annotation) if a is not NoneType]
                type_args_len = len(type_args)
                if type_args_len == 1:   # then this was an Optional
                    # we have an edge case where a field() doesn't have a default
                    # specified, but the type annotation is Optional. In this case
                    # we'd normally treat it as required due to the lack of default,
                    # but if optional then it should also not be required. So we'll
                    # just fish this item out of 'required' if it's in there
                    if p.default is Parameter.empty:  # normally would be required
                        try:
                            required.remove(p.name)
                        except ValueError:  # pragma: no cover
                            pass
                    initial_type = type_args[0]
                    if initial_type in _type_map:
                        prop["type"] = _type_map[initial_type]
                        if prop['type'] != 'boolean':
                            _set_if_non_null(metadata, fm.ENUM_KEY, prop, 'enum')
                        _check_simple_type_modifiers(initial_type, metadata, prop)
                        continue
                    # else we'll drop down below and look at what's in the Optional
                elif type_args_len == 0:  # pragma: no cover
                    continue   # weird edge case I guess
                else:
                    raise NotImplementedError("Multiple types in a oneOf not implemented yet")

            origin = get_origin(initial_type)
            if origin in (list, List):
                prop["type"] = "array"
                list_of_type = get_args(initial_type)[0]
                _check_array_modifiers(metadata, prop)
                if list_of_type in _type_map:
                    prop["items"] = {"type": _type_map[list_of_type]}
                    if prop['type'] != 'boolean':
                        _set_if_non_null(metadata, fm.ENUM_KEY, prop["items"], 'enum')
                    _check_simple_type_modifiers(list_of_type, metadata, prop["items"])
                elif isclass(list_of_type) and issubclass(list_of_type, HikaruBase):
                    if not is_dataclass(list_of_type):
                        raise TypeError(f"The list item type of attribute {p.name} is a subclass "
                                        f"of HikaruBase but is not a dataclass")  # pragma: no cover
                    prop["items"] = _process_cls(list_of_type)
                else:
                    raise TypeError(f"Don't know how to process {p.name}'s type {p.annotation}; "
                                    f"origin: {get_origin(p.annotation)}, args: {get_args(p.annotation)}")
            elif isclass(initial_type) and issubclass(initial_type, HikaruBase):
                if not is_dataclass(initial_type):
                    raise TypeError(f"The type of {p.name} is a subclass of HikaruBase "
                                    f"but is not a dataclass")  # pragma: no cover
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
            elif initial_type is InitVar:
                # some Python's let this through; skip it
                continue
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


class HikaruCRDDocumentMixin(object):
    """
    HikaruDocumentBase mixin to add support for CRUD methods

    This class provides adjunct capabilities to subclasses of HikaruDocumentBase,
    specifically for generalized CRUD operations on CRD resources.

    Add this class to the list of bases for classes meant to be used as the basis
    for a custom resource definitions. It will provide:

    - create, read, update, delete methods,
    - context manager capabilities,
    - enable using the CRD class in a Watch

    NOTE: this mixin only works properly when used with HikaruDocumentBase as
        a sibling base class; it shouldn't be used with HikaruBase
    """

    def __post_init__(self, *args, **kwargs):  # pragma: no cover
        super(HikaruCRDDocumentMixin, self).__post_init__(*args, **kwargs)
        client = kwargs.get('client')
        if client is None:
            client = ApiClient()
        self.client: ApiClient = client

    @classmethod
    def get_additional_watch_args(cls) -> dict:
        reg: _RegisterCRD = _crd_registration_details.get(cls)
        if reg is None:
            raise ValueError(f"Class {cls.__name__} has not been registered as "
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
                 async_req: bool = False):
        """
        Generalized method for calling into the K8s client API for custom objects

        This is the generalized call for K8s custom objects. All the CRD CRUD methods use this
        method to access the underlying functionality of K8s; all behaviors are specified via the
        parameters. You probably don't need to access this directly

        :param method: str; HTTP method for the call (GET, POST, PUT, etc)
        :param url: str; the path portion of the URL for the resource to operate on. The host portion
            will be supplied by the underlying library based on the configuration supplied to K8s.
        :param alt_body: optional HikaruDocumentBase instance. If supplied, it becomes the body o of the
            request instead of self which is the default.
        :param field_manager: optional str; fieldManager is a name associated with the actor or
            entity that is making these changes. The value must be less than or 128 characters long,
            and only contain printable characters, as defined by
            https://golang.org/pkg/unicode/#IsPrint.
        :param field_validation: optional str; fieldValidation instructs the server on how to handle
            objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided
            that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are:

            - Ignore: This will ignore any unknown fields that are silently dropped from the object,
              and will ignore all but the last duplicate field that the decoder encounters. This is
              the default behavior prior to v1.23 and is the default behavior when the
              `ServerSideFieldValidation` feature gate is disabled.
            - Warn: This will send a warning via the standard warning response header for each unknown
              field that is dropped from the object, and for each duplicate field that is encountered. The
              request will still succeed if there are no other errors, and will only persist the last of
              any duplicate fields. This is the default when the `ServerSideFieldValidation` feature
              gate is enabled.
            - Strict: This will fail the request with a BadRequest error if any unknown fields would be
              dropped from the object, or if any duplicate fields are present. The error returned from
              the server will contain all unknown and duplicate fields encountered.

        :param pretty: optional str; if True then the output is pretty printed.
        :param dry_run: optional str; When present, indicates that modifications should not be
            persisted. An invalid or unrecognized dryRun directive will result
            in an error response and no further processing of the request. Valid
            values are:

            - All: all dry run stages will be processed.

        :param async_req: optional bool; if True, the call is async and the result requires the caller
            to invoke get() on the returned Response object. Default is False, making the call blocking.
        :return Response: if the call was sync, then Response.obj will contain the result, if async, then
            you must call Response.get() to get the result.
        """
        if not self.client:
            self.client = ApiClient()
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
        if pretty is not None:  # pragma: no cover
            query_params.append(('pretty', pretty))
        if dry_run is not None:  # pragma: no cover
            query_params.append(('dryRun', dry_run))
        if field_manager is not None:  # pragma: no cover
            query_params.append(('fieldManager', field_manager))
        if field_validation is not None:  # pragma: no cover
            query_params.append(('fieldValidation', field_validation))

        header_params = dict()
        header_params['Accept'] = self.client.select_header_accept(
            ['application/json', 'application/yaml', 'application/vnd.kubernetes.protobuf'])  # noqa: E501
        auth_settings = ['BearerToken']
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
        """
        Creates a new instance of the CRD embodied by self.

        Results in a call to K8s to create a new instance of the CRD containing the data in 'self'. This
        requires first that the CRD has been defined to K8s with a CustomResourceDefinition object (or by
        some other means such as sending the appropriate YAML into K8s). The instance will be created as
        long as another instance with the same name/scope doesn't already exist.

        Returns a new instance of the resource with additional data filled by K8s. If an async call is done,
        then a Response object is returned and the new instance can be acquired by calling .get() on that
        object.

        If this object already exists, and ApiError is raised by the K8s libraries.

        :param field_manager: optional str; fieldManager is a name associated with the actor or
            entity that is making these changes. The value must be less than or 128 characters long,
            and only contain printable characters, as defined by
            https://golang.org/pkg/unicode/#IsPrint.
        :param field_validation: optional str; fieldValidation instructs the server on how to handle
            objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided
            that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are:

            - Ignore: This will ignore any unknown fields that are silently dropped from the object,
              and will ignore all but the last duplicate field that the decoder encounters. This is
              the default behavior prior to v1.23 and is the default behavior when the
              `ServerSideFieldValidation` feature gate is disabled.
            - Warn: This will send a warning via the standard warning response header for each unknown
              field that is dropped from the object, and for each duplicate field that is encountered. The
              request will still succeed if there are no other errors, and will only persist the last of
              any duplicate fields. This is the default when the `ServerSideFieldValidation` feature
              gate is enabled.
            - Strict: This will fail the request with a BadRequest error if any unknown fields would be
              dropped from the object, or if any duplicate fields are present. The error returned from
              the server will contain all unknown and duplicate fields encountered.
        :param pretty: optional str; if True then the output is pretty printed.
        :param dry_run: optional str; When present, indicates that modifications should not be
            persisted. An invalid or unrecognized dryRun directive will result
            in an error response and no further processing of the request. Valid
            values are:

            - All: all dry run stages will be processed.
        :param async_req: optional bool; if True, the call is async and the result requires the caller
            to invoke get() on the returned Response object. Default is False, making the call blocking.
        """
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
        resp = self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)
        if async_req:
            return resp
        else:
            return resp.obj

    def _get_existing_url(self) -> str:
        reg_details: _RegisterCRD = _crd_registration_details.get(self.__class__)
        if reg_details is None:
            raise TypeError(f"The class {self.__class__.__name__} has not been registered "
                            f"with register_crd_schema()")  # pragma: no cover
        parts = self.apiVersion.split("/")
        if len(parts) != 2:
            raise TypeError(f"The apiVersion does not appear to have exactly two parts "
                            f"(group/version) split with a '/'")  # pragma: no cover
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
        """
        Reads an existing K8s CRD resource and retuns a populated object

        Sends a read request to K8s for an existing CRD based on the data in self. If it doesn't exist,
        the K8s libraries raise an error. If it does it returns a new instance that contains all the details
        of the resource.

        :param field_manager: optional str; fieldManager is a name associated with the actor or
            entity that is making these changes. The value must be less than or 128 characters long,
            and only contain printable characters, as defined by
            https://golang.org/pkg/unicode/#IsPrint.
        :param field_validation: optional str; fieldValidation instructs the server on how to handle
            objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided
            that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are:

            - Ignore: This will ignore any unknown fields that are silently dropped from the object,
              and will ignore all but the last duplicate field that the decoder encounters. This is
              the default behavior prior to v1.23 and is the default behavior when the
              `ServerSideFieldValidation` feature gate is disabled.
            - Warn: This will send a warning via the standard warning response header for each unknown
              field that is dropped from the object, and for each duplicate field that is encountered. The
              request will still succeed if there are no other errors, and will only persist the last of
              any duplicate fields. This is the default when the `ServerSideFieldValidation` feature
              gate is enabled.
            - Strict: This will fail the request with a BadRequest error if any unknown fields would be
              dropped from the object, or if any duplicate fields are present. The error returned from
              the server will contain all unknown and duplicate fields encountered.
        :param pretty: optional str; if True then the output is pretty printed.
        :param dry_run: optional str; When present, indicates that modifications should not be
            persisted. An invalid or unrecognized dryRun directive will result
            in an error response and no further processing of the request. Valid
            values are:
            - All: all dry run stages will be processed.
        :param async_req: optional bool; if True, the call is async and the result requires the caller
            to invoke get() on the returned Response object. Default is False, making the call blocking.
        """
        method: str = "GET"
        url = self._get_existing_url()
        resp = self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)
        if async_req:
            return resp
        else:
            return resp.obj

    def update(self, field_manager: Optional[str] = None,
               field_validation: Optional[str] = None,
               pretty: Optional[bool] = None,
               dry_run: Optional[str] = None,
               async_req: bool = False):
        """
        Updates an existing CRD resource.

        Takes the data from self and generates and update message to K8s. The updated instance is returned
        as a new object. If the instance doesn't exist, the K8s library raises and ApiError.

        NOTE: An update can only be performed on an instance that was "read" first. However, when the update
            is sent, if the instance has changed in K8s first, the update will fail with a message that the
            update isn't on the latest version of the resource. You will need to read the resource again,
            re-apply the changes, and then call update() once again..

        :param field_manager: optional str; fieldManager is a name associated with the actor or
            entity that is making these changes. The value must be less than or 128 characters long,
            and only contain printable characters, as defined by
            https://golang.org/pkg/unicode/#IsPrint.
        :param field_validation: optional str; fieldValidation instructs the server on how to handle
            objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided
            that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are:

            - Ignore: This will ignore any unknown fields that are silently dropped from the object,
              and will ignore all but the last duplicate field that the decoder encounters. This is
              the default behavior prior to v1.23 and is the default behavior when the
              `ServerSideFieldValidation` feature gate is disabled.
            - Warn: This will send a warning via the standard warning response header for each unknown
              field that is dropped from the object, and for each duplicate field that is encountered. The
              request will still succeed if there are no other errors, and will only persist the last of
              any duplicate fields. This is the default when the `ServerSideFieldValidation` feature
              gate is enabled.
            - Strict: This will fail the request with a BadRequest error if any unknown fields would be
              dropped from the object, or if any duplicate fields are present. The error returned from
              the server will contain all unknown and duplicate fields encountered.
        :param pretty: optional str; if True then the output is pretty printed.
        :param dry_run: optional str; When present, indicates that modifications should not be
            persisted. An invalid or unrecognized dryRun directive will result
            in an error response and no further processing of the request. Valid
            values are:

            - All: all dry run stages will be processed.
        :param async_req: optional bool; if True, the call is async and the result requires the caller
            to invoke get() on the returned Response object. Default is False, making the call blocking.
        """
        method: str = "PUT"
        url: str = self._get_existing_url()
        resp = self.api_call(method, url, field_manager=field_manager,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)
        if async_req:
            return resp
        else:
            return resp.obj

    def delete(self,
               grace_period_seconds: Optional[int] = None,
               orphan_dependents: Optional[bool] = None,
               preconditions = None,
               propagation_policy: Optional[str] = None,
               field_manager: Optional[str] = None,
               field_validation: Optional[str] = None,
               pretty: Optional[bool] = None,
               dry_run: Optional[str] = None,
               async_req: bool = False):
        """
        Delete the resource using the DeleteOptions from the current release.

        :param grace_period_seconds: The duration in seconds before the object should be deleted.
            Value must be non-negative integer. The value zero indicates delete immediately. If
            this value is nil, the default grace period for the specified type will be used.
            Defaults to a per object value if not specified. zero means delete immediately.
        :param orphan_dependents: Deprecated: please use the PropagationPolicy, this field will be
            deprecated in 1.7. Should the dependent objects be orphaned. If true/false, the "orphan"
            finalizer will be added to/removed from the object's finalizers list. Either this field or
            PropagationPolicy may be set, but not both.
        :param preconditions: optional Preconditions instances. Must be fulfilled before a deletion
            is carried out. If not possible, a 409 Conflict status will be returned.
        :param propagation_policy: Whether and how garbage collection will be performed. Either this
            field or OrphanDependents may be set, but not both. The default policy is decided by the
            existing finalizer set in the metadata.finalizers and the resource-specific default policy.
            Acceptable values are:

            - 'Orphan' - orphan the dependents;
            - 'Background' - allow the garbage collector to delete the dependents
              in the background;
            - 'Foreground' - a cascading policy that deletes all dependents in the foreground.
        :param field_manager: optional str; fieldManager is a name associated with the actor or
            entity that is making these changes. The value must be less than or 128 characters long,
            and only contain printable characters, as defined by
            https://golang.org/pkg/unicode/#IsPrint.
        :param field_validation: optional str; fieldValidation instructs the server on how to handle
            objects in the request (POST/PUT/PATCH) containing unknown or duplicate fields, provided
            that the `ServerSideFieldValidation` feature gate is also enabled. Valid values are:

            - Ignore: This will ignore any unknown fields that are silently dropped from the object,
              and will ignore all but the last duplicate field that the decoder encounters. This is
              the default behavior prior to v1.23 and is the default behavior when the
              `ServerSideFieldValidation` feature gate is disabled.
            - Warn: This will send a warning via the standard warning response header for each unknown
              field that is dropped from the object, and for each duplicate field that is encountered. The
              request will still succeed if there are no other errors, and will only persist the last of
              any duplicate fields. This is the default when the `ServerSideFieldValidation` feature
              gate is enabled.
            - Strict: This will fail the request with a BadRequest error if any unknown fields would be
              dropped from the object, or if any duplicate fields are present. The error returned from
              the server will contain all unknown and duplicate fields encountered.
        :param pretty: optional str; if True then the output is pretty printed.
        :param dry_run: optional str; When present, indicates that modifications should not be
            persisted. An invalid or unrecognized dryRun directive will result
            in an error response and no further processing of the request. Valid
            values are:

            - All: all dry run stages will be processed.
        :param async_req: optional bool; if True, the call is async and the result requires the caller
            to invoke get() on the returned Response object. Default is False, making the call blocking.
        :return: Depends on the resource. Often it is an instance of the deleted resource, but may also
            be an instance of the Status object; what is returned is defined by the swagger spec.
        """
        def_release = get_default_release()
        try:
            mod = import_module(".v1", f"{model_root_package}.{def_release}")
        except ImportError as e:  # pragma: no cover
            raise ImportError(f"Couldn't import the module with DeleteOptions: {e}")

        DeleteOptions = getattr(mod, "DeleteOptions")
        method: str = "DELETE"
        url: str = self._get_existing_url()
        delops_args = dict()
        delops_args['gracePeriodSeconds'] = grace_period_seconds
        delops_args['orphanDependents'] = orphan_dependents
        delops_args['preconditions'] = preconditions
        delops_args["propagationPolicy"] = propagation_policy
        delops_args['dryRun'] = dry_run
        do: DeleteOptions = DeleteOptions(**delops_args)
        resp = self.api_call(method, url, field_manager=field_manager,
                             alt_body=do,
                             field_validation=field_validation,
                             pretty=pretty,
                             dry_run=dry_run,
                             async_req=async_req)
        if async_req:
            return resp
        else:
            return self

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        passed = ex_type is None and ex_value is None and ex_traceback is None
        has_rollback = hasattr(self, "__rollback")
        if passed:
            try:
                self.update()
            except Exception:
                if has_rollback:
                    self.merge(getattr(self, "__rollback"), overwrite=True)
                    delattr(self, "__rollback")
                raise
        if has_rollback:
            if not passed:
                self.merge(getattr(self, "__rollback"), overwrite=True)
            delattr(self, "__rollback")
        return False


def register_crd_class(crd_cls, plural_name: str, is_namespaced: bool = True):
    """
    Registers a CRD class with Hikaru, so it can find the proper class to instantiate on message receipt

    Registers your CRD class with Hikaru's class tracking code so that when a message is received that
    is associated with your CRD, Hikaru knows what class to instantiate.

    The supplied class must be a subclass of HikaruDocumentBase and HikaruCRDDocumentMixin for all features
    to work properly. Additionally, the class must contain the string attributes apiVersion and kind, as
    well as a metadata attribute of type ObjectMeta; these are used both by Hikaru and K8s to direct
    processing of entities sent to/from K8s.

    If all requirements are met, after this call CRUD operations and Watch() objects can be used.

    NOTE: for CRD classes, you should be using register_crd_schema() instead of
        register_version_kind_class() as you normally would for custom classes.

    :param crd_cls: A class object that has both HikaruDocumentBase and HikaruCRDDocumentMixin as base
        classes.
    :param plural_name: str; a plural name for your resource in all lower case. This should match the plural
        entry in the CustomResourceDefinitionNames object inside your CustomResourceDefintion.
    :param is_namespaced: bool, defaults to True. If True, then the resource's instances will be created
        within a namespace (rather than cluster-wide), and hence the namespace attribute of ObjectMeta
        must name an existing namespace. If False, no namespace is required, and the resource's instances
        will be created within the cluster as a whole.
    :return: the crd_cls value is returned to the caller.
    """
    if not issubclass(crd_cls, HikaruDocumentBase) or not issubclass(crd_cls, HikaruCRDDocumentMixin):
        raise TypeError("A CRD registered class must be a subclass of both "
                        "HikaruCRDDocumentBase and HikaruDocumentBase")
    hct: HikaruCallableTyper = HikaruCallableTyper(crd_cls)
    if not hasattr(crd_cls, 'apiVersion') or not hasattr(crd_cls, 'kind') or not hct.has_param('metadata'):
        raise TypeError("The decorated class must have apiVersion, kind, and metadata attributes")
    if not is_dataclass(crd_cls):
        raise TypeError(f"The class {crd_cls.__name__} must be a dataclass")  # pragma: no cover
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


__all__ = ["HikaruCRDDocumentMixin", "register_crd_class", "get_crd_schema"]
