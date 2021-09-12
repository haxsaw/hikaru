*************
Release Notes
*************

v0.8.0b
-------

This release adds support for release 18.20 of the Python Kubernetes
client, which supports release 1.18 of the Kubernetes API swagger spec.
This release of the spec is smaller than the 1.17 release, and there is
a fair amount of pruning in evidence:

- An entire version has be removed in the 1.18 release of the spec:
  **v1beta2** no longer exists in the swagger file, and hence there is no
  longer a v1beta2 subpackge in the rel_1_18 model package.
- A number of operations (methods) have been dropped from the definition of
  resources in **v1beta1**. This appears to have been a full promotion to
  `v1` -only status.

Because of this, 'rel_1_17' will be retained as the default release in Hikaru
for some time to give consumers an opportunity to ensure that they don't rely
on anything from v1beta2 or methods on v1beta1 objects, and a point release
will be issued later where we switch to the default release to 'rel_1_18'.
As always, you can explicity set your release to rel_1_18 if you choose.

The total list of changes is too long to provide here; the CSV file
`rel_0-7_to_0-8_diffs.csv <https://github
.com/haxsaw/hikaru/blob/main/devtools/rel_0-7_to_0-8_diffs.csv>`_
provides a listing that shows, by release of the K8s swagger spec, the deleted
methods/classes compared with the 1.18 spec.

**If you are coming to 0.8 from 0.6.1 or earlier**

Please read the release notes for 0.7 as they may also impact you.

This release also adds compatibility with the newest release of the black
code formatter, 21.8b0.

v0.7.0b
-------

This release includes support for Kubernetes' `watch` facility, but also includes what might
be a breaking change for some to fix a bug in the model code generation.

- This release exposes the underlying Kubernetes `watch` facility, enabling you to easily create
  code that receives events detailing the activities that Kubernetes is carrying out. Events
  are delivered to you in the form of Hikaru model objects. The facility provides a higher-level
  absraction than is available from the underlying K8s Python client, enabling you to establish
  watches simply by naming the class you wish to receive events about. Additional assistance
  is provided to give you hints as to what classes are eligible for namespaced watches. See the
  "Watchers: Monitoring Kubernetes Activity" section of the documentation for full details.
- In the development of the `watch` facility, a bug was uncovered involving the auto-generated
  model classes. This bug resulted in certain object 'list' methods to be assigned to the wrong
  class. This had to be corrected in order to enable the `watch` implementation to be completed.
  Hence, some methods have been relocated to other classes. The tables below list the changes in
  method-class association that have been made in this release. It's recommended that you review
  the table and modify your code prior to adopting this release in production.

**Kubernetes release rel_1_16 model changes**

======== ========== ============================================= ========== ==============================
Ver      Action     Method                                        Old class  New class
======== ========== ============================================= ========== ==============================
v1       MOVED      listPodForAllNamespaces                       Pod        PodList
v1       MOVED      listPodTemplateForAllNamespaces               Pod        PodTemplateList
v1       MOVED      listHorizontalPodAutoscalerForAllNamespaces   Pod        HorizontalPodAutoscalerList
v1       MOVED      listSecretForAllNamespaces                    Secret     SecretList
v1       MOVED      listLeaseForAllNamespaces                     Lease      LeaseList
v1       MOVED      listEndpointsForAllNamespaces                 Endpoints  EndpointsList
v1       MOVED      listServiceAccountForAllNamespaces            Service    ServiceAccountList
v1       MOVED      listServiceForAllNamespaces                   Service    ServiceList
v1       MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
v1       MOVED      listEventForAllNamespaces                     Event      EventList
v1       MOVED      listJobForAllNamespaces                       Job        JobList
v1       MOVED      listRoleForAllNamespaces                      Role       RoleList
v1       MOVED      listRoleBindingForAllNamespaces               Binding    RoleBindingList
v1       ADDED      listPersistentVolumeClaimForAllNamespaces     --         PersistentVolumeClaimList
v1beta1  MOVED      listLeaseForAllNamespaces                     Lease      LeaseList
v1beta1  MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
v1beta1  MOVED      listEventForAllNamespaces                     Event      EventList
v1beta1  MOVED      listRoleBindingForAllNamespaces               Role       RoleBindingList
v1beta1  MOVED      listRoleForAllNamespaces                      Role	       RoleList
v1beta1  MOVED      listIngressForAllNamespaces                   Ingress    IngressList
v1beta2  MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
======== ========== ============================================= ========== ==============================

**Kubernetes release rel_1_17 model changes**

======== ========== ============================================= ========== ==============================
Ver      Action     Method                                        Old class  New class
======== ========== ============================================= ========== ==============================
v1       MOVED      listPodForAllNamespaces                       Pod        PodList
v1       MOVED      listPodTemplateForAllNamespaces               Pod        PodTemplateList
v1       MOVED      listHorizontalPodAutoscalerForAllNamespaces   Pod        HorizontalPodAutoscalerList
v1       MOVED      listSecretForAllNamespaces                    Secret     SecretList
v1       MOVED      listLeaseForAllNamespaces                     Lease      LeaseList
v1       MOVED      listEndpointsForAllNamespaces                 Endpoints  EndpointsList
v1       MOVED      listServiceAccountForAllNamespaces            Service    ServiceAccountList
v1       MOVED      listServiceForAllNamespaces                   Service    ServiceList
v1       MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
v1       MOVED      listEventForAllNamespaces                     Event      EventList
v1       MOVED      listCSINode                                   Node       CSINodeList
v1       MOVED      listJobForAllNamespaces                       Job        JobList
v1       MOVED      listRoleForAllNamespaces                      Role       RoleList
v1       MOVED      listRoleBindingForAllNamespaces               Binding    RoleBindingList
v1       ADDED      listPersistentVolumeClaimForAllNamespaces     --         PersistentVolumeClaimList
v1beta1  MOVED      listLeaseForAllNamespaces                     Lease      LeaseList
v1beta1  MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
v1beta1  MOVED      listEventForAllNamespaces                     Event      EventList
v1beta1  MOVED      listRoleBindingForAllNamespaces               Role       RoleBindingList
v1beta1  MOVED      listRoleForAllNamespaces                      Role       RoleList
v1beta1  MOVED      listIngressForAllNamespaces                   Ingress    IngressList
v1beta1  ADDED      listEndpointSliceForAllNamespaces             --         EndpointSliceList
v1beta2  MOVED      listDeploymentForAllNamespaces                Deployment DeploymentList
v1alpha1 MOVED      listRoleBindingForAllNamespaces               Role       RoleBindingList
v1alpha1 MOVED      listRoleForAllNamespaces                      Role       RoleList
======== ========== ============================================= ========== ==============================

v0.6.0b
-------

New models for the 1.17 K8s client

- **Import change**: the most impactful change in this release is that you can no longer
  use the ``from hikaru.model import *`` construct since Hikaru now supports both K8s clients
  1.16 and 1.17. This is because there *can* be incompatibilities with the new version of
  Hikaru and an older version of the K8s client for certain symboles in certain versions.
  This can cause some user's installations to break. I decided that it would be better to
  cause everyone a small bit of pain rather than utterly break some subset of users. I did
  try a variety of approaches to work around this, but everything else had other effects that
  impacted some aspect of Hikaru's value proposition. So sorry for the imposition, but you
  now have to import from a specific release such as ``from hikaru.model.rel_1_16 import *``.
  Hopefully such a change won't be needed again.
- Hikaru now supports both the 1.16 and 1.17 versions of the Kubernetes Python client. These
  are in packages ``rel_1_16`` and ``rel_1_17`` in the ``model`` package, respectively. It's
  a good idea to stick with importing the package that matches your version of the K8s client
  package, although in general things don't break if you stay in the v1 version.
- Have blessed support for the newest version of the ``black`` code formatter, so you can now
  upgrade that package and still have things work properly.

v0.5.1b
-------

A bug fix and requirements update release.

- Fixed a bug in the handling of sub-objects of NodeStatus. An attribute in DaemonEndpoint
  has a name that is capitalized and had been lower-cased previously to match the case
  usage in the K8s Python client, however properly formatted dicts that use the proper
  case for the attribute (Port) encounter a failure when using the from_yaml() method
  on Node. A fix for this bug and others like it that might creep in has been added.
- As the 'black' code formatter has been released, the requirements.txt file has been
  updated to reflect the range of releases of this package that Hikaru has validated
  work as expected.
- Corrected a typo regarding the supported release of the K8s Python client in the doc.

v0.5b
-----

- Hikaru has acquired a set of higher-level *CRUD*-style methods on HikaruDocumentBase
  subclasses. These have a simpler interface and while they can do a bit less (no
  async), they also
  have consistent names and more uniform arguments. For the full capability of the API
  you can continue to use the existing more verbosely-named methods.
- CRUD-supporting classes that implement an **update()** method are also now context
  managers; you can use an instance in a ``with`` statement block and at the end of the
  block the object's ``update()`` method will be called if there were no exceptions
  in the block. You can also optionally apply a wrapper, **rollback_cm()**, that
  will cause of the previous state of the context object to be restored if an
  exception occurs during the ``with`` statement.
- Added a **merge()** method to HikaruBase the can merge the contents of one object
  into another. Merges can either only merge new values or else overwrite all values
  of the target object.
- Fixed a bug in the field catalog where you can sometimes get duplicated field
  entries.
- Fixed a bug in handling timestamps from K8s; now returns a properly formatted
  string instead of a datetime object.
- Fixed a bug in creating 'empty' instances so that they always round-trip
  properly (this was mostly an issue in testing).
- Fixed a bug in building Hikaru model modules from the swagger spec file where certain
  objects were being incorrectly created as subclasses of HikaruDocumentBase.
- Fixed a bug in class registration where subclasses weren't being created when nested
  inside of other document classes (for instance, a MyPod subclass of Pod not being used
  when reading a PodList), and to properly support existing classes that have apiVersion
  values that are actually both a group and version.
- Fixed the bug where the ``body`` argument wasn't being passed on to the Kubernetes
  Python client for certain ``delete*()`` methods.
- Pinned Hikaru to a specific version of black since we're currently using some internal
  interface and black's public API isn't available yet.
- The ``object_at_path()`` method now can properly navigate to specific dictionary
  entries from the results of a ``diff()`` that finds differences in two dicts.

v0.4b
-----

Hikaru had to break the API contract implied by the semantic version number as the
``model`` sub-package structure has changed to support future features; this will
slightly change the API for import statements (see below). This should be a one-time
change.

- Integrated the official Kubernetes Python client with the Hikaru classes; you can now
  invoke relevant operations from the objects that the operations involve, for example
  creating a Pod directly from the Pod object. More work remains to create high-level
  interfaces on these basic operations. Because of this integration, Hikaru now requires
  the Kubernetes Python client, so be sure to upgrade your dependencies. Usage is
  covered in the documentation. Additionally, there is currently no support in Hikaru
  itself for other Kubernetes Python client abilities such as ``watch`` and ``stream``.
  Hikaru can still be used with these facilities, but you'll need to run the Hikaru
  objects into Python dicts and use the lower-level Kubernetes interfaces.
- Added support for multiple releases for Kubernetes in the **model** subpackage.
  Users will now be able to direct their code to use Hikaru objects from a specific
  Kubernetes release. If you don't need work with multiple releases, Hikaru makes
  sensible choices for defaults and you can query what release Hikaru is defaulting to.
  Release selection can be global for a program or on a per-thread basis. See the
  documentation for the functions **get_default_release()**, **set_default_release()**,
  and **set_global_default_release()**.
- Added the ability for users to create their own derived classes of Hikaru document
  classes such as ``Pod`` or ``Deployment``, and then register their new subclass
  with Hikaru so that it will make instances of the user's class instead of the parent
  class. For details, see the documentation for the **register_version_kind_class()**
  function. **NOTE**: There is currently no support in Hikaru for sending custom
  operators into Kubernetes; you'll need to access the lower-level Kubernetes client
  if you want to do that currently.
- Enriched the output of the **diff()** method of HikaruBase objects to provide more details
  on the difference as well as the differing values in the ``DiffDetail`` dataclass. You
  can now see exactly what was added/removed/modified.
- As part of the revamp to support multiple releases, added a **documents** modules that
  provides a view of just the ``HikaruDocumentBase`` subclasses if all you require in
  your namespace are the top-level classes. This keeps the namespace from getting cluttered.
- Modified the approach to annotations previously taken that now allows forward references
  to classes and cyclic dependencies. Hence, recursive objects can now be directly
  represented in the model files, and objects with mutual references can be created. This
  eliminates the need for the workarounds for ``JSONSchemaProps`` in previous releases.
- Fixed a bug in populating the field catalog that each HikaruBase object maintains; now
  all fields are always properly reported after a repopulate_catalog() call.

.. note::

    Hikaru was integration tested on K3s and some issues have emerged. The following are
    known problems and will be investigated further:

    - Using the **APIServerList.listAPIService()** class method results in an exception
      in the underlying Kubernetes Python client when processing the results from K3s; it
      complains about a field that is None that is supposed to be required. It is unclear if
      the problem lies in the client code or in what is sent back from K3s.
    - Some methods of **Scale** don't return with success although the calls seem to
      operate correctly. Reading Scales from other objects like a ReplicationController
      yields correct results, patching a Scale results in an error 'object not found'.
      More investigation is needed to determine if the methods are being used incorrectly
      of if the issue is with K3s.
    - The following objects and/or methods haven't been integration tested:

      ===============================  =========================================
      Class/Method                     Issue
      ===============================  =========================================
      Binding                          Marked as deprecated; not tested
      ControllerRevision               Documented as internal; skipped
      LocalSubjectAccessReview (CRUD)  Need useful examples
      MutatingWebhookConfiguration     Need useful examples
      Node.createNode()                Need a better dev environment
      SubjectAccessReview (CRUD)       Need useful examples
      SubjectAccessRulesReview (CRUD)  Need useful examples
      StorageClass (CRUD)              Need useful examples
      SubjectAccessReivew (CRUD)       Need useful examples
      TokenReview (CRUD)               Need useful examples
      VolumeAttachment (CRUD)          Need useful examples
      \'collection\' methods           Need useful examples
      ===============================  =========================================

      In many cases, tests reading lists of these objects has been conducted successfully,
      but good examples of CRUD operations on these objects are required to put
      together some illustrative tests. In some cases, the existing infrastructure
      is an impediment.

      As it has been tested that **every** Hikaru method can be called which
      in turn invokes the underlying Kubernetes Python client API call and all arguments
      are passed successfully, not all argument combinations into Hikaru methods have
      been tested. However, both async and dry run calls have been minimally tested and
      operate properly.

v0.3b
------

- Implemented a solution for the recursive objects in the `apiextensions` group in the swagger spec file. Hikaru now models all objects in the Kubernetes swagger spec and, with the exception of some attributes in a single object, all types are properly annotated on all `apiextensions` objects.
- Fixed a bug for YAML, JSON, and Python dicts generated from Hikaru objects; previously, the renamed keywords such as `except_` or `continue_` weren't being changed back to their original forms when generating YAML, JSON or Python dicts. This has now been corrected.
- Put in workarounds for properties in YAML that start with **$**; in Hikaru objects, these are replaced with the prefix **dollar_**, so **$ref** becomes **dollar_ref**. These are transformed back when going from Hikaru objects to YAML, JSON, or a Python dict.

v0.2a0
------

- Added support a new two new styles of generated code from `get_python_source()`: the 'black' style, using the 'black' formatter, and None, which outputs syntactically correct Python but with no formatting at all (this is the fastest generation option and is good if the code is going to be dynamically executed).
- New `get_type_warnings()` method on HikaruBase objects; compares actual values with the types currently populating an instance, and looks for required values that are missing. Generates a list of warning records for any problems found.
- New `diff()` method of HikaruBase; compares to object hierarchies and generates difference records indicating where they are different.
- Removed dead code.
- Improved and documented all exceptions that are raised.
- Added support for round-tripping between YAML, Python objects, Python source, JSON, and Python dicts. You can now start with any of these, move between them, and get back the original representation.
- Raised testing coverage to 99% overall.
- Documentation updates; includes a section on patterns and recipes.

v0.1.1a0
--------

Bug fix; when creating Python source, when literal dicts were being written out,
non-string values were quoted as if they were strings. Now all dict values appropriately
include quotes.

v0.1a0
------

Initial release
