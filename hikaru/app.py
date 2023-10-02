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

from dataclasses import dataclass, fields, MISSING
from datetime import datetime
from importlib import import_module
from io import StringIO
import json
from inspect import getmodule
from uuid import uuid4
from kubernetes.client import ApiClient
from kubernetes.client.exceptions import ApiException
from ruamel.yaml import YAML
from typing import (Optional, List, Tuple, Dict, Generator, Any, Callable, Union,
                    TextIO)
from .utils import get_args, get_origin
from threading import current_thread, Thread
from . import (HikaruDocumentBase, get_default_release, DiffDetail, HikaruBase, DiffType,
               set_default_release, get_clean_dict, from_dict, TypeWarning, CatalogEntry)
from .crd import HikaruCRDDocumentMixin
from .utils import Response
from .watch import MultiplexingWatcher, Watcher

# _hikaru_app_version_key denotes the version of the metadata scheme that is used by hikaru-app
# when storing information in resource metadata.labels and metadata.annotations. This version number
# may or may not change when a new version of hikaru-app is released. If it does change, then older
# versions of hikaru-app will not be able to read the metadata.labels and metadata.annotations data,
# however, newer versions of hikaru-app will be able to read the older data.
_hikaru_app_version_key = "HIKARU_APP_VERSION_KEY"
_hikaru_app_metadata_version = "1.0.0"
_app_instance_label_key = "app.kubernetes.io/instance"
_per_thread_instance_label_keys: Dict[str, str] = {}
_app_resource_attr_annotation_key = "HIKARU_RSRC_ATTR_KEY"
_per_thread_attr_annotation_keys: Dict[str, str] = {}

# there are no production uses to change this value, but testing may alter it
model_root_package = "hikaru.model"


def record_resource_metadata(rsrc: HikaruDocumentBase, instance_id: str, name: str):
    """
    Set the instance_id and resource name in the resource's metadata key/value stores

    Hikaru uses this function internally to set the instance_id in the resource's metadata.labels key/value store
    and the resource name in the resource's metadata.annotations key/value store. This is used to identify all
    resources that are part of the same instance of an application and the name of the resource that is being
    created, updated, or deleted. This function is not intended to be called by users of hikaru-app, but is provided
    in case a user wants to use the same mechanism for their own purposes.

    Since Hikaru handles the invocation of this normally, users shouldn't use this function
    unless they have a specific need. One such need is to gather a set of existing resources
    into an Application instance by calling this function on a series of resources, providing
    a constant instance_id and varying values for name that match the attributes of an Application
    subclass, and then calling update() on each in turn.

    :param rsrc: HikaruDocumentBase; the resource to set the metadata on
    :param instance_id: str; the unique Application instance id
    :param name: str; name of the attributes that the resource is known by within the application
    """
    rsrc.metadata.labels[_hikaru_app_version_key] = _hikaru_app_metadata_version
    ai_key = get_app_instance_label_key()
    if ai_key not in rsrc.metadata.labels:
        rsrc.metadata.labels[ai_key] = instance_id
    ra_key = get_app_rsrc_attr_annotation_key()
    if ra_key not in rsrc.metadata.annotations:
        rsrc.metadata.annotations[ra_key] = name


def resource_name_matches_metadata(rsrc: HikaruDocumentBase, name: str) -> bool:
    """
    Return True if the resource name matches the metadata annotation

    Since we obscure how we store the resource name in the resource's metadata, this function is provided
    to test if a specific resource has metadata that matches the name of the resource.

    :param rsrc: HikaDocumentBase; the resource to check
    :param name: the name of the resource we want to check the metadata against
    :return: bool; True if the resource name matches the metadata-stored name
    """

    # This assumes a 1.0.0 storage scheme for the metadata
    key = get_app_rsrc_attr_annotation_key()
    return key in rsrc.metadata.annotations and rsrc.metadata.annotations[key] == name


def get_label_selector_for_instance_id(instance_id: str) -> str:
    """
    Return a string suitable to use as a label selector when reading for resources from a specific app instance

    This function returns a string that can be used as the label_selector parameter to a Kubernetes resource
    list call. This is used when trying to find all the resources of particular type that are part of an
    Application instance.

    :param instance_id: str; the unique Application instance id for an already-created hikaru-app application
    :return: string; a label selector expression string it can be combined with other label selectors according
        to the syntax specified by Kubernetes.
    """
    metadata_key = get_app_instance_label_key()
    selector = f"{metadata_key}={instance_id}"
    return selector


def get_app_instance_label_key() -> str:
    """
    This is the key that will be added to a rsrc's metadata.labels to id all rsrcs that are of the same app instance

    Hikaru-app will use the string returned by this function as the key to store the internally generated instance_id
    that all resources from an instance of an application will share. This key has a default value, but can be
    changed by setting the key to use with set_app_instance_label key. Regardless of what value is returned,
    the key will be used in the resource's metadata.labels key/value store so that it can be queried later.

    NOTE:
    The underlying facility allows for multiple threads with each one supporting a different instance label key.
    That means when you call this function the key for this thread is returned. If no specific key has been established
    for this thread then the global key is returned.
    """
    t: Thread = current_thread()
    key: str = _per_thread_instance_label_keys.get(t.name, _app_instance_label_key)
    return key


def set_app_instance_label_key(newkey: Optional[str] = None):
    """
    Set the per-thread key to use to identify all resources that are part of the same app

    This function allows you to specify the key that Hikaru-app will use when noting that a resource is part of
    a particular instance of an Application subclass. Hikaru-app will use this as the key in the resource's
    metadata.labels k/v store, and the value will be the id for the Application instance. By default, the key used is
    a key private to Hikaru-app, but if you want integration with other tools, you may want to use this function
    to change the key to:

    app.kubernetes.io/instance

    ...as Kubernetes documents this as a standard key to use to identify resources that belong to an instance of an app.
    You should not modify this key or the associated value with any other tools!

    NOTE:
    This function sets the per-thread value for the instance label key. Any per-thread values take precedence over
    the global instance key value. If you want to change the global key value then call
    set_global_app_instance_label_key()

    :param newkey: optional str, defaults to None; string value of the key to use when performing CRUD operations on
        Hikaru-app applications for the current thread. If this value is an empty string or None, then the per-thread
        value is deleted and the global app instance label key will subsequently be used for this thread.
    """
    global _app_instance_label_key, _per_thread_instance_label_keys
    t: Thread = current_thread()
    if not newkey:
        try:
            del _per_thread_instance_label_keys[t.name]
        except KeyError:
            pass
    else:
        _per_thread_instance_label_keys[t.name] = newkey


def set_global_app_instance_label_key(newkey: str):
    """
    Set the global app instance label key to use to identify all resources that are part of the same app, regardless
    of thread.

    This function allows you to specify the key that Hikaru-app will use when noting that a resource is part of
    a particular instance of an Application subclass. Hikaru-app will use this as the key in the resource's
    metadata.labels k/v store, and the value will be the id for the Application instance. By default, the key used is
    a key private to Hikaru-app, but if you want integration with other tools, you may want to use this function
    to change the key to:

    app.kubernetes.io/instance

    ...as Kubernetes documents this as a standard key to use to identify resources that belong to an instance of an app.
    You should not modify this key or the associated value with any other tools!

    NOTE:
    This functions set the global key that will be used whenever there is no thread-specific key to use for this purpose.
    If a thread-specific key is desired, then call set_app_instance_label_key() from the thread in which you want the
    custom key to be used.

    :param newkey: str; key for hikaru-app to use when setting values in an Application resource's
        metadata.annotations k/v store.
    """
    global _app_instance_label_key
    _app_instance_label_key = newkey


def get_app_rsrc_attr_annotation_key() -> str:
    """
    Get the per-thread key to use to store hikaru-app info about a resource into that resource's metadata.annotations
    k/v store

    Returns a string that hikaru-app will use when storing data about a resource in that resource's metadata.annotations
    key/value store. This is primarily used to determine into which attribute of an Application subclass instance a
    resource should be stored when an instance of the Application is populated from the cluster.

    You should not modify this key or associated value with any other tools!

    NOTE:
    If a per-thread value for this key has been established with set_app_rsrc_attr_annotation_key(), then that key will
    be returned. Otherwise, the global resource attribute annotation key will be returned.
    """
    t: Thread = current_thread()
    return _per_thread_attr_annotation_keys.get(t.name, _app_resource_attr_annotation_key)


def set_app_rsrc_attr_annotation_key(newkey: Optional[str] = None):
    """
    Sets the per-thread key for hikaru-app to use to store info about the app instance in a resource's
    metadata.annotations k/v store.

    Allows the user to change the key that hikaru-app will use when storing information about an application instance
    into a resource's metadata.annotations key/value store. One of the keys uses hikaru-app makes for values under
    this key to is note which instance attribute a resource belongs to; this allows instances to be recreated when
    read from a cluster.

    If the vale of newkey is empty or None, then this deletes any per-thread attribute annotation key to use and
    subsequent calls from this same thread to get this key will return the global attribute annotation key.

    You should not modify this key or associated value with any other tools!

    NOTE:
    This changes the per-thread key value that hikaru-app will use, so calls to get_app_rsrc_attr_annotation_key()
    from the same thread that call this function will return the supplied key.

    :param newkey: optional str, default None: sets the per-thread key to use to set hikaru-app data into
        an Application resource's metadata.annotations k/v store. IF newkey is empty or None, then any thread-
        specific keys are deleted and subsequent calls from the same thread will return the global
        attribute annotation key.
    """
    t: Thread = current_thread()
    if not newkey:
        try:
            del _per_thread_attr_annotation_keys[t.name]
        except KeyError:
            pass
    else:
        _per_thread_attr_annotation_keys[t.name] = newkey


def set_global_rsrc_attr_annotation_key(newkey: str):
    """
    Set the global attribute annotation key for hikaru-app to use when adding annotations to Application resources.

    This call sets the global key that hikaru-app will use when setting values into an Application resource's
    metadta.annotations k/v store. This is the key tht will be used if a per-thread has not not been set up
    by the caller previously.

    :param newkey: str; the key that hikaru-app will use when setting values in an Application resource's
        k/v store.
    """
    global _app_resource_attr_annotation_key
    _app_resource_attr_annotation_key = newkey


class Reporter(object):
    """
    Reporters are objects that Applications can report progress to during operations

    A Reporter is an object that can be used to report progress during the execution of
    long operations on an Application. It is used to provide feedback to the user about
    what is happening during the operation, and to provide a means to cancel the
    operation if desired. It is also used to provide a means to report errors that
    occur during the operation.

    The Reporter class is an abstract base class that defines the interface that
    concrete Reporter classes must implement. It also provides a default implementation
    of the interface that can be used as a base class for concrete Reporter classes.

    The Reporter class is not intended to be instantiated directly. Instead, it is
    intended to be used as a base class for concrete Reporter classes that implement
    the interface defined by the Reporter class.

    Users create Reporter derived class instances and pass them to an Application
    subclass prior to operations such as create(), delete(), and update(). During the
    execution of these operations, the Application will call the Reporter's methods to
    report progress and errors.
    """
    # the types of events that the reporter can handle
    APP_START_PROCESSING = 'app_start'    # sent when an application starts processing
    APP_DONE_PROCESSING = 'app_done'      # sent when an application finishes processing
    RSRC_START_PROCESSING = 'rsrc_start'  # sent when a resource starts processing
    RSRC_DONE_PROCESSING = 'rsrc_done'    # sent when a resource finishes processing
    RSRC_READ_OP = 'rsrc_read'            # sent when a resource is read from the cluster
    RSRC_CREATE_OP = 'rsrc_create'        # sent when a resource is created in the cluster
    RSRC_UPDATE_OP = 'rsrc_update'        # sent when a resource is updated in the cluster
    RSRC_DELETE_OP = 'rsrc_delete'        # sent when a resource is deleted from the cluster
    RSRC_ERROR = 'rsrc_error'             # sent when an error occurs during processing; followed
                                          # by a RSRC_DONE_PROCESSING
    RSRC_CHANGING = 'rsrc_changing'       # sent when a resource operation has yet to complete;
                                          # the final resource state has not yet been reached

    # the following describes the normal series of events that occur during an application operation:
    # APP_START_PROCESSING -> <resource-progress-events>* -> APP_DONE_PROCESSING

    # the following describes the normal series of events that occur during a resource operation:
    # RSRC_START_PROCESSING -> RSRC_*_OP -> RSRC_CHANGING* -> RSRC_DONE_PROCESSING
    #  where RSRC_*_OP is one of RSRC_CREATE_OP, RSRC_READ_OP, RSRC_UPDATE_OP, or RSRC_DELETE_OP,
    #  and RSRC_CHANGING* is zero or more RSRC_CHANGING events
    #
    # a flow with an error will generate the following event stream:
    # RSRC_START_PROCESSING -> RSRC_*_OP -> RSRC_CHANGING* -> RSRC_ERROR -> RSRC_DONE_PROCESSING
    #  where RSRC_*_OP and RSRC_CHANGING* are as described above

    def __init__(self, *args, **kwargs):
        pass

    def advise_plan(self, app: 'Application', app_action: str, tranches: List[List["FieldInfo"]]) -> Optional[bool]:
        """
        Tells the reporter the work to be performed in create or delete CRUD operations

        This advisory method is called by the Application instance when a CRUD create or delete is executed on
        an Application. It is meant to give a Reporter instance early notice (and right of refusal) for a set of work
        to perform for these operations.

        The method is called after the order of work has been determined but before any work starts. It is passed a
        list of lists (tranches) of FieldInfo objects that identifies the HikaruDocumentBase subclasses that will be
        involved in the operation, and in what order the work will be carried out. Each inner list contains resources
        that can be actioned simultaneously, and the outer list sequences the processing of each inner list. So for a
        value of tranches like:

        [  [a], [b, c, d], [e, f]  ]

        The Application object will first action 'a', then 'b', 'c', and 'd' in parallel, and then when all of
        those are done will then action 'e' and 'f' in parallel.

        If the implementation of advise_plan() returns False, then processing of the CRUD operation is aborted. This
        provides a means to allow inspection of the plan and to veto its execution. If you run into cases where Hikaru
        computes an incorrect plan please file a bug report.

        :param app: Application; the Application subclass instance the plan is for
        :param app_action: str; the type of operation to be performed (create, delete)
        :param tranches: list of lists of FieldInfo objects; this is the work that is to be performed
            and in what order. The outer list sequences the work, and each HikaruDocumentBase resource in an inner
            list may be processed at the same time. FieldInfo objects describe key details of a field on a dataclass
            but can also optionally include a reference to the actual instance of the object the field describes. Hence,
            this method should look at the 'instance' attribute of the FieldInfo object for the actual object that will
            be actioned in the operation. NOTE: the value of 'instance' may be None if the field was optional in the
            dataclass.
        :return: optional bool. If False, then processing the provided plan is aborted. Any other value allows
            processing to proceed. Returning None is fine; this will allow processing to continue.
        """
        return True  # pragma: no cover

    def report(self, app: "Application", app_action: str, event_type: str, timestamp: str, attribute_name: str,
               resource: HikaruDocumentBase, additional_details: dict):
        """
        Report an event to the Reporter

        This method is called by an Application to report an event to the Reporter. The
        event_type parameter specifies the type of event being reported, and the event
        parameter contains the details of the event.

        This method is intended to be overridden by concrete Reporter classes.

        :param app: the Application instance reporting to this Reporter. This allows multiple
            Applications to use the same Reporter.
        :param app_action: str; identifies what action is being taken on the app: create, read,
            update, or delete
        :param event_type: str; the type of event being reported
        :param timestamp: str; a datetime string in ISO 8601 format of when the application
            generated the event; this may be different from when the Reporter deals with the event
        :param attribute_name: str; the name of the attribute from the Application object that
            this event is for
        :param resource: HikaruDocumentBase; the resource that the event is for
        :param additional_details: dict; different for each event type, but not absolutely
            needed to understand the event. Possible keys/values:

            +----------------------------------+---------------------------------+
            | 'error': str                     | used for RSRC_ERROR             |
            +----------------------------------+---------------------------------+
            | 'index': int                     | used when the resource is an    |
            |                                  | element of a list; index of the |
            |                                  | resource being reported on      |
            +----------------------------------+---------------------------------+
            | 'key': str                       | used when the resource is a     |
            |                                  | value in a dict of resources;   |
            |                                  | string value of the key of the  |
            |                                  | resource                        |
            +----------------------------------+---------------------------------+
            | 'app-operation': str             | used when the event is for an   |
            |                                  | application operation; one of   |
            |                                  | 'create', 'read', 'update',     |
            |                                  | 'delete'                        |
            +----------------------------------+---------------------------------+
            | 'manifest':                      | list of all resources to        |
            | list of                          | process; present with           |
            | (str, HikaruDocumentBase) tuples | APP_START_PROCESSING events     |
            +----------------------------------+---------------------------------+
        """
        pass  # pragma: no cover

    def should_abort(self, app: "Application") -> bool:
        """
        Returns True if the Application should stop processing resources
        :return: bool; True if the Application should stop resource processing, False to keep going
        """
        return False  # pragma: no cover


class FieldInfo(object):
    """
    Class used to hold flattened out type info for a dataclass field

    Instances of this class are used both internally by Hikaru and are also passed
    to a user via the Reporter (if one is supplied) to inform them of various activities
    the Application object is conducting on their behalf.
    """
    def __init__(self, name: str, ftype: type, has_default: bool, default: Any = None,
                 default_factory: Callable = None):
        self.name = name
        self.type = ftype
        self.has_default = has_default
        self.default_factory = default_factory
        self.instance: Optional[HikaruDocumentBase] = None  # filled out later


@dataclass
class Application(object):
    """
    Define a collection of Kubernetes objects that are to be deployed together

    The Application class provides a way to define a collection of Kubernetes resources
    that are to be deployed together to implement the infrastructure for a single
    application system. It provides a means to define the order in which the resources
    are to be deployed, and to define dependencies between them. It also provides a
    set of convenience methods to support the automated inspection of the resources
    contained within the Application to facilitate the implementation of automated
    inspection processes for compliance, security, inventory control, forecasting, and
    other management-level activities commonly needed in organizations that have
    multiple application systems in production.

    The Application class not only can deploy the resources it contains, it can also de
    -deploy them in the reverse order of deployment. This is useful for performing tear-downs
    after running operations such as CI/CD pipelines, or for performing clean-up after
    testing. It can also leverage Hikaru's diffing capabilities to determine what changes
    may have occurred to the resources since they were deployed, and can change existing
    resources to match the desired state.

    Application objects can survive partial deployments. This means that if a resource
    fails to deploy, the Application will still contain the resources that were deployed
    successfully. This allows for the implementation of a retry mechanism for the
    failed resource, and for the deployment of the remainder of the resources in the
    Application. This is useful for implementing idempotent deployments.

    Application objects can render their contents as JSON or YAML, and can also render
    the Python source code that would be needed to create the Application object. This
    allows for the creation of Application objects from JSON or YAML, and for the
    serialization of Application objects to JSON or YAML.

    Application objects can be created from a single Kubernetes resource, or from a
    collection of Kubernetes resources. They can also be created from a list of
    Kubernetes resources, or from a directory containing Kubernetes resource files.

    They can also be created from a Helm chart. This is done by creating an Application
    object from the Helm chart, and then calling the Application's create() method.

    Application objects can also be created by interrogating a Kubernetes cluster to
    discover the resources that are deployed there that are part of a single application.
    This is done by creating a shell Application object, and then calling its
    discover() method, providing it a few details about the application. The Application
    object will then interrogate the cluster to discover the resources that are part of
    the application, and add them to itself. It will also discover the dependencies
    between the resources, and will add those to itself as well. The resulting
    Application object can then be used to deploy the application to another cluster,
    perform other operations on the application, or render the object into Hikaru source
    code.

    Application objects can also be versioned, and differences between the version can be
    generated. This provides a worklist that shows what changes need to be made to the
    application to bring it up to date with the new version. This is useful for
    automating update procedures on existing applications.

    Application objects may contain references to existing application resources, allowing
    the representation of integration points between applications. This allows for modeling
    applications that contain resources that must be deployed as well as those that belong
    to other applications that are used by the application being modeled. This allows for
    the creation of a complete model of the application landscape of an organization.

    To define an Application, the user creates a subclass of the Application class, and uses
    the same dataclass techniques used in other Hikaru classes to define the resources that
    comprise the application.
    """
    # client: InitVar[Optional[ApiClient]] = None

    def __post_init__(self) -> None:
        self.client = None
        self._resource_fields: List[FieldInfo] = []
        self._created: List[HikaruDocumentBase] = []
        self._deleted: List[HikaruDocumentBase] = []
        self._reporter: Optional[Reporter] = None
        self.instance_id: Optional[str] = None

    def set_reporter(self, reporter: Reporter):
        self._reporter = reporter
        return self

    def advise_plan(self, app_action: str, tranches: List[List[FieldInfo]]) -> Optional[bool]:
        """
        Notify any reporter of the proposed plan for the indicated operation

        If the Application has a reporter, notify it of the processing plan indicated by the content of 'tranches'
        for the action specified by 'app_action'.

        This method returns any value returned from the reporter, otherwise None

        :param app_action:
        :param tranches:

        Returns:

        """
        if self._reporter:
            tcopy = list(list(l) for l in tranches)
            retval = self._reporter.advise_plan(self, app_action, tcopy)
        else:
            retval = None
        return retval

    def report(self, app_action: str, event_type: str, additional_details: dict,
               resource: Optional[HikaruDocumentBase] = None, attribute_name: Optional[str] = None):
        """
        Report an event to the Reporter

        This method is called by an Application to report an event to the Reporter. The
        event_type parameter specifies the type of event being reported, and the event
        parameter contains the details of the event.

        This method is intended to be overridden by concrete Reporter classes.

        :param app_action: str; identifies what action is being taken on the app: create, read,
            update, or delete
        :param event_type: str; the type of event being reported
            generated the event; this may be different from when the Reporter deals with the event
        :param attribute_name: str; the name of the attribute from the Application object that
            this event is for
        :param resource: HikaruDocumentBase; the resource that the event is for
        :param additional_details: dict; different for each event type, but not absolutely
            needed to understand the event. Possible keys/values:
            'error': <the-error-string>  # used for RSRC_ERROR
            'index': int  # used when the resource is an element of a list; index of the
                          # resource being reported on
            'key': str    # used when the resource is a value in a dict of resources; string
                          # value of the key of the resource
            'app-operation': str  # used when the event is for an application operation; one
                                  # of 'create', 'read', 'update', 'delete'
            'manifest': list of (str, HikaruDocumentBase) tuples  # list of all resources to
                          # processes; present with APP_START_PROCESSING events
        """
        if self._reporter:
            self._reporter.report(self, app_action, event_type, datetime.now().isoformat(),
                                  attribute_name, resource, additional_details)

    _pri1_classes = ["Namespace"]
    _pri2_classes = ["Node", "ClusterRole", "Role", "PersistentVolume",
                     "StorageClass", "Endpoint", "Service"]

    @classmethod
    def iterate_fields(cls) -> Generator[FieldInfo, None, None]:
        """
        generator for the fields from a dataclass, peeling open Optional and container types

        This method provides a generator that yields information about the fields from a dataclass.
        It can operate in two modes: one that returns info on every field, and one that only return
        data about fields that K8s resources (subclasses of HikaruDocumentBase). It is able to
        determine the type of the field in a number of different circumstances, such as when it is
        typed as an Optional, or when it is a container type like List or Dict. It also returns default
        values for the field if one is defined.

        To help with the interpretation of the data returned by this method, the method yields
        instances of the FieldInfo class. This class has the following attributes:

        NOTES:
        I think for an initial implementation, we'll cover:
        - fields that are HikaruDocumentBase subclasses
        - fields that are Optional[HikaruDocumentBase] subclasses with a default

        The big reason for this is that we can't automatically make instances from data read from
        a cluster for fields that are not HikaruDocumentBase subclasses. We can't know what the
        values should be. There are other use cases that are difficult as well, such as making
        empty instances. Generally speaking, passed in values shouldn't have an effect on the form
        of the resources passed into the __init__() method; they should be configured correctly by
        the caller. If custom resource instances are to be used in an Application based on some
        variable values, the preferred approach is to create class methods on the Application subclass,
        and from within this class method create the properly customized resource instances and pass
        those into the __init__() method. This will then allow things like read(), make_empty_instance(),
        dup(), etc, all work without things having to get complicated.
        """
        for f in fields(cls):
            if type(f.type) is type and issubclass(f.type, HikaruDocumentBase):
                has_default = f.default is not MISSING or f.default_factory is not MISSING
                yield FieldInfo(f.name, f.type, has_default, default=f.default,
                                default_factory=f.default_factory)
            elif get_origin(f.type) is Union:  # optional is implemented as Union[T, None]
                op_type = get_args(f.type)[0]
                if issubclass(op_type, HikaruDocumentBase):
                    if f.default is MISSING:  # pragma: no cover
                        default = None
                        df = f.default_factory
                    else:
                        default = f.default
                        df = None
                    yield FieldInfo(f.name, op_type, True, default=default, default_factory=df)
                else:
                    raise TypeError(f"Optional field {f.name} is not a HikaruDocumentBase subclass")
            else:
                raise TypeError(f"field {f.name} is not a HikaruDocumentBase subclass or an "
                                f"Optional[HikaruDocumentBase] subclass")

    def _compute_create_order(self) -> Tuple[List[FieldInfo], List[FieldInfo], List[FieldInfo], List[FieldInfo]]:
        # provides 4 lists of fields that can be provisioned in parallel
        pri1: List[FieldInfo] = []
        pri2: List[FieldInfo] = []
        pri3: List[FieldInfo] = []
        pri4: List[FieldInfo] = []
        relname = get_default_release()
        v1mod = import_module(".v1", f"{model_root_package}.{relname}")
        # these could be cached by release
        pri1_classses = tuple([getattr(v1mod, c) for c in self._pri1_classes])
        pri2_classses = tuple([getattr(v1mod, c) for c in self._pri2_classes])
        for fi in self.iterate_fields():
            fi.instance = getattr(self, fi.name, None)
            if issubclass(fi.type, pri1_classses):
                pri1.append(fi)
            elif issubclass(fi.type, pri2_classses):
                pri2.append(fi)
            elif not issubclass(fi.type, HikaruCRDDocumentMixin):
                pri3.append(fi)
            else:
                pri4.append(fi)
        return pri1, pri2, pri3, pri4

    def create(self, dry_run: Optional[str] = None, client: Optional[ApiClient] = None) -> bool:
        """
        Create the resources in the Application

        This method will deploy the resources in the Application to the Kubernetes cluster

        :param dry_run: optional str, default None. May have the value 'All' which indicates to perform a dry run on
            all processing stages for each resources
        :param client: optional ApiClient, default None. You can create your ApiClient object which will be used when
            contacting Kubernetes, or you can have the K8s client library do it for you by specifying the location
            of a config file with the KUBECONFIG environment variable.
        :return: bool; True if all resources were deployed successfully, False otherwise
        """
        # get some objects from the default release module
        try:
            if self.instance_id is None:
                self.instance_id = str(uuid4())
            # first, find the namespaces
            if client is None:
                client = self.client
            # TODO: improve processing from _compute_create_order() so that
            # items in the same list are processed in parallel. what we do now
            # preserves the priority but doesn't do parallel processing.
            # NOTE: we may need to have each spawned thread set the app_instance_label_key
            # before work starts to ensure that the thread that called this method shares
            # the same key as the threads it spawns.
            if not self._resource_fields:
                tranches = list(self._compute_create_order())
                if self.advise_plan("create", tranches) is False:
                    return False
                for l in tranches:
                    self._resource_fields.extend(l)
            self.report("create", Reporter.APP_START_PROCESSING, {'manifest': list(self._resource_fields)})

            # OK, right now the following deployment logic is limited; it tears off
            # deploying things, but if it fails then it just keeps going with the next
            # item.

            f: FieldInfo
            for f in self._resource_fields:
                r: HikaruDocumentBase = getattr(self, f.name, None)
                if r is None:
                    if f.has_default:
                        continue
                    else:
                        raise ValueError(f"field {f.name} is not set and has no default")
                record_resource_metadata(r, self.instance_id, f.name)
                self.report("create", Reporter.RSRC_START_PROCESSING, {}, r, f.name)
                # check if this resource already exists, create if not
                try:
                    self.report("create", Reporter.RSRC_READ_OP, {}, r, f.name)
                    _ = r.read(client=client)
                except ApiException as e:
                    if e.status == 404:
                        # namespace doesn't exist, so create it
                        r.client = client
                        self.report("create", Reporter.RSRC_CREATE_OP, {}, r, f.name)
                        try:
                            r.create(dry_run=dry_run, client=client)
                            # TODO: we need to add checks about when the resource is ready
                            self.report("create", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                        except Exception as e:
                            self.report("create", Reporter.RSRC_ERROR, {'error': str(e)}, r, f.name)
                            self.report("create", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                            raise
                    else:
                        self.report("create", Reporter.RSRC_ERROR, {'error': str(e)}, r, f.name)
                        self.report("create", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                        raise
                except Exception as e:
                    self.report("create", Reporter.RSRC_ERROR, {'error': str(e)}, r, f.name)
                    self.report("create", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                    raise
        finally:
            self.report("create", Reporter.APP_DONE_PROCESSING, {})

        return True

    @classmethod
    def read(cls, instance_id: str, client: Optional[ApiClient] = None):
        """
        Read the contents of an app instance from K8s based on the instance id

        This method returns an instance of an Application subclass based on the instance id of the app. It does this
        by listing all the existing resources of the app by type that have an instance label whose value matches
        the supplied instance_id. Further, it can only populate attributes in the class that have an annotation that
        identifies which attribute from the Application model the resource is from. This is most easily done by
        querying apps that were created with hikaru-app in the first place, as it ensures that this metadata is put
        on each resource, but existing resources can be noted manually by setting the following values on these
        metadata k/v collections:

        hikaru_app.get_app_instance_label_key() in metadata.labels:
        This key is for a value that is shared by all resources that are in the same app instance within a cluster
        (so should be unique for an app instance in a cluster). So the return value of the function is the key
        where the value should be stored in metadata.labels for all resources in the same instance of an app.

        hikaru_app.get_app_rsrc_attr_annotation_key() in metadata.annotations:
        The above function returns a key that must appear in a resource's metadata.annotations k/v store; the value
        of the key is the name of the attribute on the Application subclass where the resource is defined. For
        example, if an Application subclass has a class attribute "ns: Namespace", then the corresponding Namespace
        resource must have a metadata.annotations with the key returned by get_app_rsrc_attr_annotation_key() and
        a value of 'ns'.

        LIMITATIONS:
        ============

        - Since hikaru-app only models first-order resources, Kubernetes-managed resources derived from the first-order
          ones will not be part of what's read. So for example, if an Application subclass contains a Deployment, reading
          an instance of this Application will only yield the Deployment, not the Pods that Kubernetes may have spun up
          based on the rules in the deployment.
        - CRDs currently are not supported, so if you use CRDs within your application there's no way to read them back
          with this method.

        :param instance_id: str; the string value of the application instance's id; this will be used to locate only
            resources that are part of the app instance
        :param client: optional ApiClient object; used to identify the client to use to contact the cluster. Can be
            supplied via other usual means, such as telling K8s the location of a config file with credentials.
        """
        relname = get_default_release()
        # TODO; we may need to search through more versions in a release
        v1mod = import_module(".v1", f"{model_root_package}.{relname}")
        selector = get_label_selector_for_instance_id(instance_id)
        init_vars = {}
        for f in cls.iterate_fields():
            model_cls = getattr(v1mod, f"{f.type.__name__}List")
            # ok, search for a suitable method to list the resources
            if hasattr(model_cls, f"list{f.type.__name__}ForAllNamespaces"):
                meth = getattr(model_cls, f"list{f.type.__name__}ForAllNamespaces")
            elif hasattr(model_cls, f"list{f.type.__name__}"):
                meth = getattr(model_cls, f"list{f.type.__name__}")
            else:  # pragma: no cover
                raise TypeError(f"Can't find a suitable method to list {f.type.__name__} resources")
            response: Response[model_cls] = meth(label_selector=selector, client=client)
            obj_list: list = response.obj.items
            for r in obj_list:
                if resource_name_matches_metadata(r, f.name):
                    init_vars[f.name] = r
                    break
        app = cls(**init_vars)
        app.instance_id = instance_id
        return app

    def delete(self, dry_run: Optional[str] = None, client: Optional[ApiClient] = None) -> bool:
        """
        Delete the constituent resources of the application

        Delete all of the resources from a previously created Application instance. The deletions are done based
        on name and namespace parameters for each resource. The Application (subclass) instance must either be the
        one that was used to create the instance or has been re-created from some external store using one of the
        external loading class methods (from_dict(), from_yaml(), from_json()).

        If this call fails mid-way through the set of resources that comprise the Application, it can safely be called
        again to delete any remaining resources.

        NOTE: when the call completes, tools such as kubectl may still list the resource; this due to K8s resources
        not being deleted immediately in some cases, but their state should be reflected as "Terminating".

        :param dry_run: optional str, default None. May have the value 'All' which indicates to perform a dry run on
            all processing stages for each resources
        :param client: optional ApiClient, default None. You can create your ApiClient object which will be used when
            contacting Kubernetes, or you can have the K8s client library do it for you by specifying the location
            of a config file with the KUBECONFIG environment variable.

        :return: True if the update ran successfully, False otherwise        """
        try:
            if client is None:
                client = self.client
            # TODO: same parallelism is needed here as in create
            if not self._resource_fields:
                tranches = list(self._compute_create_order())
                if self.advise_plan("delete", tranches) is False:
                    return False
                for l in tranches:
                    self._resource_fields.extend(l)
            resource_fields = self._resource_fields[:]
            resource_fields.reverse()
            self.report("delete", Reporter.APP_START_PROCESSING, {})
            for f in resource_fields:
                r: HikaruDocumentBase = getattr(self, f.name)
                # TODO; need to decide if we should check the instance_id and skip if it doesn't match
                # TODO; need to have a better way to record items that are created/deleted that survive reanimation
                self.report("delete", Reporter.RSRC_START_PROCESSING, {}, r, f.name)
                if r in self._deleted:
                    self.report("delete", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                    continue
                try:
                    self.report("delete", Reporter.RSRC_DELETE_OP, {}, r, f.name)
                    r.delete(dry_run=dry_run, client=client)
                    self._deleted.append(r)
                    self.report("delete", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                except Exception as e:
                    self.report("delete", Reporter.RSRC_ERROR, {"error": str(e)}, r, f.name)
                    self.report("delete", Reporter.RSRC_DONE_PROCESSING, {}, r, f.name)
                    raise
        finally:
            self.report("delete", Reporter.APP_DONE_PROCESSING, {})
        return True

    def update(self, dry_run: Optional[str] = None, client: Optional[ApiClient] = None) -> bool:
        """
        Update all resources in the Application instance

        This method iterates over all resources in the Application and invokes 'update()' on each. It updates
        all resources, making no attempt to only update resources that have changed.

        :param dry_run: optional str, default None. May have the value 'All' which indicates to perform a dry run on
            all processing stages for each resources
        :param client: optional ApiClient, default None. You can create your ApiClient object which will be used when
            contacting Kubernetes, or you can have the K8s client library do it for you by specifying the location
            of a config file with the KUBECONFIG environment variable.

        :return: True if the update ran successfully, False otherwise
        """
        if client is None:
            client = self.client
        self.report("update", Reporter.APP_START_PROCESSING, {})
        try:
            for f in self.iterate_fields():
                rsrc: HikaruDocumentBase = getattr(self, f.name, None)
                self.report("update", Reporter.RSRC_START_PROCESSING, {}, attribute_name=f.name, resource=rsrc)
                if rsrc is None:
                    self.report("update", Reporter.RSRC_DONE_PROCESSING, {}, attribute_name=f.name, resource=rsrc)
                    continue   # nothing to update; @TODO: should we check to see if it was there and should be del'd?
                try:
                    self.report("update", Reporter.RSRC_UPDATE_OP, {}, attribute_name=f.name, resource=rsrc)
                    rsrc.update(dry_run=dry_run, client=client)
                    self.report("update", Reporter.RSRC_DONE_PROCESSING, {}, attribute_name=f.name, resource=rsrc)
                except Exception as e:
                    self.report("update", Reporter.RSRC_ERROR, {"error": str(e)},
                                attribute_name=f.name, resource=rsrc)
                    self.report("update", Reporter.RSRC_DONE_PROCESSING, {},
                                attribute_name=f.name, resource=rsrc)
                    raise
        finally:
            self.report("update", Reporter.APP_DONE_PROCESSING, {})
        return True

    def diff(self, other) -> Dict[str, List[DiffDetail]]:
        """
        Compare this application instance to another

        This method compares the resources in this Application instance to those of the supplied instance and
        returns a report of the differences. The report is a dictionary keyed by the attribute name of the resource
        in the Application instance. The value is a list of DiffDetail objects, each of which contains the class
        of the object where the difference was found, the name of the attribute that was different, the kind
        of difference, some explanatory text, and other supporting data depending on the kind of difference.

        It is possible to receive some superfluous differences when comparing a new Application instance and one
        read from the cluster. This is because the read instance will have some fields that are not present in the
        new instance, such as the resource version. These differences can be ignored by the caller.

        :param other: an instance of the same Application subclass as this instance
        :raises: TypeError if other is not an instance of the same Application subclass as this instance
        """
        if not isinstance(other, self.__class__):
            raise TypeError(f"other must be an instance of {self.__class__.__name__}")
        differences = {}
        for f in self.iterate_fields():
            r1: HikaruBase = getattr(self, f.name, None)
            r2: HikaruBase = getattr(other, f.name, None)
            if r1 is None:
                if r2 is None:
                    continue  # nothing to see here; keep going
                differences[f.name] = [DiffDetail(DiffType.ADDED, self.__class__, f.name, [f.name],
                                                  "resource missing from self but present in other")]
                continue
            if r2 is None:
                differences[f.name] = [DiffDetail(DiffType.REMOVED, self.__class__, f.name, [f.name],
                                                  "resource missing from other instance but present in self")]
                continue
            diffs = r1.diff(r2)
            if diffs:
                differences[f.name] = diffs
        if self.instance_id != other.instance_id:
            differences["instance_id"] = [DiffDetail(DiffType.VALUE_CHANGED, self.__class__, "instance_id",
                                                     ["instance_id"],
                                                     "instance_id values differ",
                                                     value=self.instance_id,
                                                     other_value=other.instance_id)]
        return differences

    def dup(self) -> "Application":
        """
        Duplicate this Application instance

        This method returns a new Application instance that is a duplicate of this instance. The duplicate will have
        the same values for all attributes as this instance, but will not be the same object. This is useful if you
        want to create a new Application instance that is a copy of this one, but you want to modify the new instance
        without affecting this instance.

        Given that Applications are dataclasses and custom attributes may be added by implementing the
        __post_init__() method on a subclass, dup() will only work on the attributes defined as part of
        the dataclass, not any additional attributes added into a subclass's __post_init__() method.

        To allow for such attributes to be copied, subclasses should provide their own dup() method that
        calls super().dup() and then copies the additional attributes.

        Note: for any dataclass field that is a subclass of HikaruBase (which includes HikaruDocumentBase), the
        method will use that object's dup() method to create a duplicate of that field.

        :return: a new Application instance that is a duplicate of this instance
        """
        init_args = {}
        for f in self.iterate_fields():
            r = getattr(self, f.name, None)
            if r is None:
                if f.has_default:
                    continue
                else:  # pragma: no cover
                    raise ValueError(f"field {f.name} has no default value and is missing from this instance")
            init_args[f.name] = r.dup()
        dup = self.__class__(**init_args)
        dup.instance_id = self.instance_id
        return dup

    def merge(self, other: "Application", overwrite: Optional[bool] = False,
              enforce_version: Optional[bool] = False) -> "Application":
        """
        Merge the data from the supplied Application instance into this instance

        This method merges the data from the supplied application instance into
        self. This is a 'deep' merge-- each constituent resource in other is merged
        with the corresponding resource in self. If there is no corresponding resource
        in self, then the resource from other is added to self, that is, if it is defined
        on self's dataclass. Additionally, other must be an instance of the same class
        as self.

        TypeError is raised in any case where the types of the two objects don't align
        properly.

        When merging data in subclasses of Application, this method only handles the attributes
        that are defined for the dataclass. Only attributes of HikaruDocumentBase are merged; any
        other value is the responsibility of the subclass to merge properly, as hikaru_app
        isn't able to determine in all cases what a 'proper' merge looks like.

        If a subclass adds additional attributes using the
        __post_init__() method, then the subclass should provide its own merge() method
        which should call super().merge() and then merge the additional attributes the
        subclass defines.

        merge() will NEVER overwrite an instance_id in self with a different value, even
        if overwrite is True. merge() will pull the instance_id from other and use that
        if the instance_id in self is None.

        The method returns self, so it can be chained with other methods.

        :param other: the Application instance to merge into self
        :param overwrite: optional bool, default False. The default only merges in
            attributes from other that are non-None. Hence, None attributes in other
            will never replace actual values in self. If True, then all data is taken
            from other verbatim, which can result in a loss of attribute values in self.
        :param enforce_version: optional bool, default False. The default simply checks
            to see if self and other have the same class *names* rather than the
            same actual class. This allows for merging data from objects from one
            version of Kubernetes to another. If enforce_version is True, then merge()
            will check to see both self and other are from the same class. If either
            of these versions of type checking don't match, then merge will raise
            a TypeError. This is actually enforced at the resource level.
        :raises TypeError: if other has an attribute to merge into self that self
            doesn't know about, or if checking that the 'type' of self and other,
            or any of their components, results in them not being merge-able.
        :return: self with values for other merged in
        """
        if self.__class__ is not other.__class__:
            raise TypeError(f"other must be an instance of {self.__class__.__name__}")
        for f in self.iterate_fields():
            self_attr: HikaruDocumentBase = getattr(self, f.name, None)
            other_attr: HikaruDocumentBase = getattr(other, f.name, None)
            if self_attr is None:
                if other_attr is not None:
                    setattr(self, f.name, other_attr.dup())
            elif other_attr is not None:
                self_attr.merge(other_attr, overwrite=overwrite, enforce_version=enforce_version)

        if other.instance_id and not self.instance_id:
            self.instance_id = other.instance_id
            # TODO: should we also copy over the bookkeeping data?
        return self

    @classmethod
    def get_empty_instance(cls) -> "Application":
        """
        Return an empty instance of this Application subclass

        This method returns an empty instance of this Application subclass. This is useful for understanding
        the basic struction of an Application and all of its constituent resources. The method relies on
        each resource's get_empty_instance() method to return an empty instance of that resource, and then
        creates an instance of the class with those empty instances as its attributes.

        get_empty_instance() in a resource only populate the attributes that are required for the resource
        to be created. Hence, most of the content of an empty instance will be None, empty lists, dicts, etc.

        If a subclass adds additional fields using annotations the class level, get_empty_instance() will
        attempt to populate those fields with empty instances of the appropriate type. If a
        """
        args = {}
        for f in cls.iterate_fields():
            args[f.name] = f.type.get_empty_instance()
        return cls(**args)

    _dump_format_version = "1.0"

    def get_clean_dict(self) -> dict:
        """
        Convert this Application instance to a dict that can then be saved externally

        This method takes an Application subclass instance and converts it to a dict in a common
        format that can be saved to disk and read later to re-create the object.
        """
        m = getmodule(self)
        resources = []
        d = {
            "version": self._dump_format_version,
            "app_class": self.__class__.__name__,
            "app_module": m.__name__,
            "app_package": m.__package__,
            "model_release": get_default_release(),
            "instance_id": self.instance_id,
            "state_when_dumped": "provisioned",   # TODO: this isn't correct!
            "resources": resources
        }
        for f in self.iterate_fields():
            v = getattr(self, f.name, None)
            if v is None:
                if f.has_default:
                    continue
                else:
                    raise ValueError(f"field {f.name} has no default value and is missing from this instance; can't persist")
            resources.append({"attr_name": f.name, "data": get_clean_dict(v)})
        return d

    @classmethod
    def _v1keycheck(cls, d: dict):
        # checks that all the proper keys are present in the dict to recreate an instance from, raises a useful
        # error if missing ones are found
        missing = []
        for k in ["version", "app_class", "app_module", "app_package", "model_release",
                  "instance_id", "state_when_dumped", "resources"]:
            if k not in d:
                missing.append(f"key '{k}' is missing from the dict")
        if missing:
            raise ValueError("\n".join(missing))

    @classmethod
    def from_dict(cls, d: dict, target_cls: Optional[type] = None) -> "Application":
        """
        Create an Application instance from a dict that was previously saved

        This class method takes a dict that was previously created by to_dict() and recreates
        the Application instance that was used to create it. It is able to create an instance of
        the proper subclass of Application, provided that the package/module are on the PYTHONPATH.

        :param d: the dict to recreate the Application instance from. must have been created
            by a previous call to to_dict().
        :param target_cls: optional type, default None. If not None, then the dict is assumed
            to be of the type specified by target_cls. This allows the class to not be on the
            PYTHONPATH since the user has provided it (though it probably is). If None, then
            the class to instatiate will be read from the dict
        """
        cls._v1keycheck(d)
        if d["version"] != cls._dump_format_version:
            raise ValueError(f"dict version {d['version']} doesn't match expected version {cls._dump_format_version}")
        release_at_start = get_default_release()
        pkgname = d["app_package"]
        modname = d["app_module"]
        clsname = d["app_class"]
        try:
            set_default_release(d["model_release"])
            m = import_module(modname, pkgname)
            cls = getattr(m, clsname)  # TODO: catch missing class exception
            args = {rd["attr_name"]: from_dict(rd["data"]) for rd in d["resources"]}
            app = cls(**args)
            app.instance_id = d["instance_id"]
        finally:
            set_default_release(release_at_start)
        return app

    def get_json(self) -> str:
        """
        Convert this Application instance to a JSON string that can then be saved externally

        This method takes an Application subclass instance and converts it to a JSON string in a common
        format that can be saved to disk and read later to re-create the object.
        """
        return json.dumps(self.get_clean_dict())

    @classmethod
    def from_json(cls, s: str, target_cls: Optional[type] = None) -> "Application":
        """
        Create an Application instance from a JSON string that was previously saved

        This class method takes a JSON string that was previously created by get_json() and recreates
        the Application instance that was used to create it. It is able to create an instance of
        the proper subclass of Application, provided that the package/module are on the PYTHONPATH.

        :param s: the JSON string to recreate the Application instance from. must have been created
            by a previous call to get_json().
        :param target_cls: optional type, default None. If not None, then the dict is assumed
            to be of the type specified by target_cls. This allows the class to not be on the
            PYTHONPATH since the user has provided it (though it probably is). If None, then
            the class to instatiate will be read from the dict.
        """
        return cls.from_dict(json.loads(s), target_cls=target_cls)

    def get_yaml(self) -> str:
        """
        Convert this Application instance to a YAML string that can then be saved externally
        """
        d: dict = self.get_clean_dict()
        yaml = YAML(typ="safe")
        yaml.indent(offset=2, sequence=4)
        sio = StringIO()
        yaml.dump(d, sio)
        return "\n".join(["---", sio.getvalue()])

    @classmethod
    def from_yaml(cls, path: str = None, stream: TextIO = None,
                  yaml: str = None, release: str = None) -> "Application":
        """
        Create an Application subclass instance from a YAML string that was previously saved from get_yaml

        This class method takes a YAML string that was previously created by get_yaml() and recreates
        the Application instance that was used to create it. It is able to create an instance of
        the proper subclass of Application, provided that the package/module are on the PYTHONPATH.

        This is expecting a YAML source with a single application document in it. If there are more than
        one then only the first one will be processed and have an object recreated for it.

        The caller must supply one of the *path*, *stream*, or *yaml* arguments, as these are the source
        of the YAML that will be processed.

        :param path: str, optional. If supplied, this is the path to a file containing YAML previously
            saved with a call to get_yaml().
        :param stream: TextIO, optional. If supplied, this is an open file-like object that contains the
            YAML that is to be processed. The YAML must have been previously saved with a call to get_yaml().
        :param yaml: str, optional. If supplied, this is a YAML string to process. The YAML must have
            been previously saved with a call to get_yaml().
        :param release: str, optional. If supplied, this is the release to use when creating the instance.
            This must be of the form of the name of a model release package such as 'rel_1_24'. If not
            supplied, then the default release for this thread will be used.
        """
        if path is None and stream is None and yaml is None:
            raise ValueError("one of path, stream, or yaml must be supplied")
        if path:
            f = open(path, "r")
        if stream:
            f = stream
        if yaml:
            to_parse = yaml
        else:
            to_parse = f.read()
        parser = YAML(typ="safe")
        doc = list(parser.load_all(to_parse))[0]
        return cls.from_dict(doc)

    def object_at_path(self, path: list):
        """
        returns the value named by path starting at self

        Returns an object or base value by navigating the supplied path starting at 'self'. The elements of path are
        either strings representing attribute names or else integers in the case where an attribute name reaches a
        list (the int is used as an index into the list). Generally, the thing to do is to use the 'path' attribute
        of a returned CatalogEntry from find_by_name()

        :param path: A list of strings or ints. :return: Whatever value is found at the end of the path; this could
            be another HikaruBase instance or a plain Python object (str, bool, dict, etc).

        :raises RuntimeError: raised if path[0] is None but there are more elements
        :raises IndexError: raised if a path index value is beyond the end of a list-valued attribute
        :raises ValueError: if an index for a list can't be turned into an int
        :raises AttributeError: raised if any attribute on the path isn't an attribute of the previous object on
            the path
        :return: a
        """
        if not hasattr(self, path[0]):
            raise AttributeError(f"The application doesn't have an attribute named {path[0]}")
        topmost_rsrc: HikaruDocumentBase = getattr(self, path[0], None)
        if topmost_rsrc is None:
            if len(path) > 1:
                raise RuntimeError(f"The attribute {path[0]} in the application is None")
            else:
                return topmost_rsrc
        final_rsrc = topmost_rsrc.object_at_path(path[1:])
        return final_rsrc

    def find_by_name(self, name: str, following: Union[str, List] = None) -> List[CatalogEntry]:
        """
        Returns a list of catalog entries for the named field wherever it occurs
        in the Application's resources.

        This is a convenience method that uses the method of the same name from HikaruBase
        on each of the components of the application object. The returned CatalogEntry
        objects have a path that includes the name of the attribute in the Application where
        the item can be found.

        See the doc for HikaruBase.find_by_name for complete documentation.


        :param name: string containing a name for an attribute somewhere in the model,
            the search for with starts at 'self'. This must be a legal Python identifier,
            not an integer.
        :param following: optional sequence of strings or a single string with '.' separators
            that names path under which search for name should be conducted. See the doc
            for HikaruBase.find_by_name() for further details.
        :return: list of CatalogEntry objects that match the query criteria.
        :raises TypeError: if 'name' is not a string, or if 'following' is not
            a string or list
        :raises ValueError: if 'following' is a list and one of the elements is not
            a str or an int
        """
        results: List[CatalogEntry] = []
        first_bit = None
        if following is not None:
            if isinstance(following, str):
                parts = following.split('.')
                first_bit = parts[0]
                try:
                    first_bit = int(first_bit)
                except ValueError:
                    pass
            elif isinstance(following, list):
                first_bit = following[0]
                try:
                    first_bit = int(first_bit)
                except ValueError:
                    pass
            if isinstance(first_bit, int):
                first_bit = None  # can't have an index at the app level
        attr_set = set(fi.name for fi in self.iterate_fields())
        if first_bit in attr_set:
            # then we're only to look under this attr
            attr_set = {first_bit}
            # ANNND we have to adjust 'following' to not have the initial component since it won't be found
            if isinstance(following, str):
                following = ".".join(following.split('.')[1:])
                following = following if following else None
            else:  # must have been a list
                following = following[1:] if following[1:] else None
        for attrname in attr_set:
            rsrc: HikaruBase = getattr(self, attrname, None)
            if rsrc is not None:
                entries: List[CatalogEntry] = rsrc.find_by_name(name, following)
                for ce in entries:
                    ce.path.insert(0, attrname)
                results.extend(entries)
        return results

    def get_type_warnings(self) -> Dict[str, List[TypeWarning]]:
        """
        Get all the type warnings for this app and its resources

        This method checks the types of all the fields in the app and its resources and returns a list
        any type mismatches it finds. The list will be empty if there are no type mismatches.
        """
        all_warnings: Dict[str, List[TypeWarning]] = {}
        for f in self.iterate_fields():
            r = getattr(self, f.name, None)
            warnings: List[TypeWarning] = []
            all_warnings[f.name] = warnings
            if r is None:
                if f.has_default:
                    continue
                else:
                    warnings.append(TypeWarning(self.__class__, f.name, f.name,
                                                f"required field {f.name} is None"))
            else:
                if not isinstance(r, f.type):
                    warnings.append(TypeWarning(self.__class__, f.name, f.name,
                                                f"field {f.name} is {type(r)} but should be {f.type}"))
                elif not isinstance(r, HikaruDocumentBase):
                    warnings.append(TypeWarning(self.__class__, f.name, f.name,
                                                f"field {f.name} is {type(r)} but should be a HikaruDocumentBase"))
                else:
                    warnings.extend(r.get_type_warnings())
        return all_warnings

    def find_uses_of_class(self, cls: type) -> List[HikaruDocumentBase]:
        """
        Search through the app and find all uses of the specified class (or its subclasses)

        This method searches through the app's resources and returns any that are of the specified
        type (or its subclasses). Searches only work on top-level classes that are subclasses of
        HikaruDocumentBase; that is, you can search for Pod but not PodSpec.

        :param cls: the class to search for. Must be a subclass of HikaruDocumentSpec
        """
        if not issubclass(cls, HikaruDocumentBase):
            raise TypeError("cls must be a subclass of HikaruDocumentBase")
        if cls == HikaruDocumentBase:
            raise TypeError("cls must be a subclass of HikaruDocumentBase")
        found: List[HikaruDocumentBase] = []
        for r in self.iterate_fields():
            a = getattr(self, r.name)
            if isinstance(a, cls):
                found.append(a)
        return found


class AppWatcher(MultiplexingWatcher):
    """
    A class to watch all the resources within a single hikaru_app Application subclass

    This class wraps up the tasks needed to create a unified stream of watcher events across
    all of the resources in a single Application subclass. It is mostly a convenience class,
    as the same thing could be accomplished by creating a MultiplexingWatcher and adding
    all of the resource watchers to it.
    """
    def __init__(self, app: Application, exception_callback=None):
        """
        :param exception_callback: a function that will be called if any of the watchers
            raise an exception. The function will be called with a single argument, the
            exception object.
        """
        super(AppWatcher, self).__init__(exception_callback=exception_callback)
        self._app = app
        self._rel = get_default_release()  # TODO; move this into the base class
        label_sel = get_label_selector_for_instance_id(app.instance_id)
        for f in app.iterate_fields():
            r = getattr(app, f.name, None)
            if r is None:
                continue
            w = Watcher(r.__class__, label_selector=label_sel)
            self.add_watcher(w)

    # TODO: we need to move the capture of the default release into the MultiplexingWatcher
    # base class, and then have the spawned thread set that release for use for objects to
    # watch.
