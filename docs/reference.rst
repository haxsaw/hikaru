*********
Reference
*********

Objects returned when querying Hikaru itself
********************************************

.. _CatalogEntry doc:

.. autoclass:: hikaru.CatalogEntry
   :members:

CatalogEntry is a namedtuple that is returned as list elements from the
:meth:`find_by_name()<hikaru.HikaruBase.find_by_name>` method of HikaruBase.

.. _TypeWarning doc:

.. autoclass:: hikaru.TypeWarning
   :members:

TypeWarning is a dataclass that is returned as list elements from the
:meth:`get_type_warnings()<hikaru.HikaruBase.get_type_warnings>` method of HikaruBase.

.. _DiffDetail doc:

.. autoclass:: hikaru.DiffDetail
   :members:

.. _DiffType doc:

.. autoclass:: hikaru.DiffType



Hikaru modelling base classes
*****************************
.. _HikaruBase doc:

.. autoclass:: hikaru.HikaruBase
   :members:

.. _HikaruDocumentBase doc:

.. autoclass:: hikaru.HikaruDocumentBase
   :members:

.. _HikaruCRDDocumentMixin doc:

.. autoclass:: hikaru.crd.HikaruCRDDocumentMixin
   :members:

Hikaru Application classes
****************************

.. _Application doc:

.. autoclass:: hikaru.app.Application

    .. automethod:: create
    .. automethod:: delete
    .. automethod:: diff
    .. automethod:: dup
    .. automethod:: find_by_name
    .. automethod:: find_uses_of_class
    .. automethod:: from_dict
    .. automethod:: from_json
    .. automethod:: from_yaml
    .. automethod:: get_clean_dict
    .. automethod:: get_empty_instance
    .. automethod:: get_json
    .. automethod:: get_type_warnings
    .. automethod:: get_yaml
    .. automethod:: merge
    .. automethod:: object_at_path
    .. automethod:: read
    .. automethod:: set_reporter
    .. automethod:: update

.. autoclass:: hikaru.app.Reporter
    :members:

.. autoclass:: hikaru.app.FieldInfo
    :members:

.. _FieldMetadata doc:

.. autoclass:: hikaru.meta.FieldMetadata

   .. automethod::  __init__

.. _Response doc:

.. autoclass:: hikaru.Response
   :members:

Hikaru Watchers
***************

.. _WatchEvent doc:

.. autoclass:: hikaru.watch.WatchEvent
   :members:

.. _Watcher doc:

.. autoclass:: hikaru.watch.Watcher
   :members:

   .. automethod:: __init__

.. _MultiplexingWatcher doc:

.. autoclass:: hikaru.watch.MultiplexingWatcher
   :members:

   .. automethod:: __init__

Hikaru functions
****************

.. _from_dict doc:

.. autofunction:: hikaru.from_dict

.. _from_json doc:

.. autofunction:: hikaru.from_json

.. _get_clean_dict doc:

.. autofunction:: hikaru.get_clean_dict

.. _get_json doc:

.. autofunction:: hikaru.get_json

.. _get_processors doc:

.. autofunction:: hikaru.get_processors

.. _get_python_source doc:

.. autofunction:: hikaru.get_python_source

.. _get_yaml doc:

.. autofunction:: hikaru.get_yaml

.. _load_full_yaml doc:

.. autofunction:: hikaru.load_full_yaml

.. _process_api_version doc:

.. autofunction:: hikaru.process_api_version

.. _get_default_release doc:

.. autofunction:: hikaru.get_default_release

.. _set_default_release doc:

.. autofunction:: hikaru.set_default_release

.. _set_global_default_release doc:

.. autofunction:: hikaru.set_global_default_release

.. _get_version_kind_class doc:

.. autofunction:: hikaru.get_version_kind_class

.. _register_version_kind_class doc:

.. autofunction:: hikaru.register_version_kind_class

.. _rollback_cm doc:

.. autofunction:: hikaru.rollback_cm

.. _get_crd_schema doc:

.. autofunction:: hikaru.crd.get_crd_schema

.. _register_crd_class doc:

.. autofunction:: hikaru.crd.register_crd_class

.. _get_default_installed_release doc:

.. autofunction:: hikaru.model.defrel.get_default_installed_release

.. _get_label_selector_for_instance_id doc:

.. autofunction:: hikaru.app.get_label_selector_for_instance_id

.. _get_app_instance_label_key doc:

.. autofunction:: hikaru.app.get_app_instance_label_key

.. _set_app_instance_label_key doc:

.. autofunction:: hikaru.app.set_app_instance_label_key

.. _set_global_app_instance_label_key doc:

.. autofunction:: hikaru.app.set_global_app_instance_label_key

.. _record_resource_metadata doc:

.. autofunction:: hikaru.app.record_resource_metadata

.. _resource_name_matches_metadata doc:

.. autofunction:: hikaru.app.resource_name_matches_metadata
