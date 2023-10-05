*************
Release Notes
*************

hikaru v1.2.0
-------------

Drops support for Kubernetes 23.x and adds support for 27.x.

hikaru-model-27 v1.1.0
----------------------

This is the first release of the model Hikaru model package to support the 27.x version of
the Kubernetes API/objects.

v1.1.0
------

This is a big release for Hikaru as it is not only delivered using a significant re-vamp of
the packaging approach, but also includes a new feature that supports whole applications
while still supporting the semantics of individual Kubernetes resource model classes.

Packaging
=========

In this release, Hikaru has been broken into a set of smaller packages that allows you to only install the
support you wish, while still offering a single "install everything" package. Either approach
retains the same set of APIs and package structure, so should be transparent to your code.

The new package structure is composed of:

- ``hikaru-core``, which contains all of the underlying machinery that makes Hikaru run, including:

  - Base model classes
  - YAML, JSON, and Python dict exchange formats
  - The new ``Application`` facility (more on this below)
  - Watch support
  - CRD support

  Note that ``hikaru-core`` DOES NOT include support for:

  - Any Kubernetes modeling classes (no Pods, Namespaces, etc)
  - Code generation; this has been moved to another package, ``hikaru-codegen`` (more on this below).

  There's really not much you can do with core alone; at a minimum you need a model package for
  useful work (you could do pure CRDs with just core, as long as they don't refer to any model classes).

- A set of ``hikaru-model-*`` packages, where each package supports a single release of the
  Kubernetes API. All model packages have ``hikaru-core`` as a requirement, so simply installing
  the model you wish to work with will also install the core. These are installed within the
  ``hikaru.model`` namespace package, so existing imports will work as they did before.
- Python code generation capabilities have been moved to the ``hikaru-codegen`` package, which,
  if installed, will only then install the ``black`` and ``autopep8`` code formatters.
- Finally, the old ``hikaru`` package will still be offered, but it will become a meta-package that
  installs the core, the four most recent models, and the codegen package.

This structure has a number of benefits, some of which are in response to user requests:

- **Smaller installs are now possible**: you can create minimal installs that only involve the
  core and the model release(s) you wish to work with, leaving other models behind as
  well as unneeded capabilities such as code formatting. Users who had Hikaru in AWS Lambdas
  will now have a smaller distributable package.
- **Model release deprecation is (mostly) over**: previously, Hikaru only supported four
  releases of models since all were rolled into the single package. To keep that package from growing without
  bound, older model releases would be deprecated so the Hikaru package didn't just keep growing.
  That is no longer an issue as you can now install only the release of the models you wish to
  work with. Models will only be deprecated if they are quite old and core has moved on.
- **Multiple model releases are still supported**: so if you want to install both ``hikaru-model-25`` and
  ``hikaru-model-26``, things will work as before. Multiple installed models will still require the use
  ``set_default_release()`` to inform Hikaru as to which release you want it to use to create objects
  received from Kubernetes.
- **Model packages can be updated independently of the core**: it hasn't happened so far, but there's
  always been the possibility that some older but non-deprecated release gets a patch from the keepers
  of the Python Kubernetes client, which would force an update to the overall Hikaru package when it
  really wasn't warranted. Now a patched model release can be created independently of the Hikaru core
  package.
- **New versions of models can be supported more quickly**: with the old package that contained multiple
  models, a new K8s Python client release would entail a new model release, which entailed full testing
  of all models in the overall Hikaru package. New models are time-consuming enough without adding all
  the additional testing. But now we only need a new model package to support the new K8s release and
  everything else can remain untouched (how we deal with the Hikaru meta-package is open for consideration).

Documentation is still offered at the single ReadTheDocs site, where the core, models, and codegen packages
are documented. The packages are all up on PyPI, so search there for hikaru to see all the available packages.

Applications
=============

The new release of Hikaru also includes a new facility for defining all the resources for a single system
or application in a single class. Supported by a base ``Application`` class, this facility provides similar
functionality to that provided by classes like ``Pod`` or ``Deployment``. With this facility, you can:

- Define methods to create canonical configurations of applications,
- Provide parameters to these methods to customize instance creation,
- Access CRUD methods to create/read/update/delete instances of applications within a K8s cluster,
- Persist application instances to/from JSON, YAML, and Python dicts,
- Access inspection and other management operations like diff and merge on whole application instance,
- Create watches on all the resources in the application and receive events for each component.

Consider this capability as an alternative to Helm, but instead of templatizing YAML files, you simply parameterize
factory methods on your application class.

This version does not include support for generating Python source code for the application, but that feature is
coming. Other features, such as assembling application definitions from existing objects created from YAML/JSON/dicts
or the cluster itself will follow on from there.

Other changes
==============

There are a few other changes in this new release:

- ``set_default_release()`` and ``set_global_default_release()`` now both automatically import the root package
  for the indicated release: the assumption here is that since you bothered setting a default release, you'll probably
  be using objects from it, so Hikaru front-end-loads the importation of the model package for the release you specify.
- A new function, ``hikaru.model.defrel.get_default_installed_release()`` returns name of the highest numbered release
  current *installed* on the system. This function actually examines the filesystem and has nothing to do with any preferred
  release indicated by calls to ``set_default_release()``. The function ``get_default_release()`` uses
  ``get_default_installed_release()`` if there has been no call to ``set_default_release()`` or ``set_global_default_release()``.
- The ``from_dict()`` function has gotten a speedup, and now works 3-10x faster depending on the kind of object being
  processed.
- **There is not longer a warning generated if the lowest-numbered release in the ``hikaru`` meta-package is imported**;
  this is because the ``hikaru`` package is meant only to provide backwards compatibility for existing users and
  because Hikaru will no longer be actually deprecating packages unless they won't work at all with a newer version of
  ``hikaru-core``.

Still broken
============

As of 26.x of Kubernetes, the swagger API spec for Event in the core group still doesn't match what is sent from
Kubernetes. In particular, a field named ``event_time`` which is marked as required either doesn't arrive as part
of the Event or has a null value. This causes the calls that deal with Events, namely methods on Event and EventList,
to fail as Hikaru processing expects there to be data in these fields according to the swagger. We know some users
have done some work-arounds using the lower-level Kubernetes APIs for Events, patch a value in, and then use
``from_dict()`` to get the Hikaru objects for these. Hopefully this will be fixed in the 27.x version of the API,
but if not we may investigate a workaround in the code to make these do something useful.

v1.0.1
------

*Default K8s release:* 26.x

*Deprecated K8s release:* 23.x

**Bugfix release**

This is a quick release to fix a bug where PodStatus was not properly populating the podIP
and hostIP attributes. This has now been corrected.

v1.0.0
-------

*Default K8s release:* 26.x

*Deprecated K8s release:* 23.x

This release of Hikaru introduces a significant new feature, support for user-defined
custom resource definitions (CRDs). The capability integrates smoothly with the current
capabilities of Hikaru and supports:

- The ability to define the structure of a CRD with Hikaru classes, either from scratch
  or to mimic one that is already in your environment,
- Sending the definition into Kubernetes where it will be established as a CRD managed
  by K8s,
- Managing instances of the new CRD using CRUD methods,
- Establishing Watchers on the new CRD to in order to monitor activity or create
  controllers in Python,
- The use of CRD classes as context managers, just like other Hikaru document classes.

The new features are found in the ``hikaru.crd`` and ``hikaru.meta`` modules, and consists
of two new classes and two new functions. The documentation at ReadTheDocs has details
with examples under the "Advanced Topics" section. There are also some examples in the
github repo under explore/crdexample.

Additionally, a pair of new methods has been added to HikaruDocumentBase: ``get_status()``
and ``clear_status()``. If the course of developing the CRD support, it was discovered that
certain Kubernetes calls return a Status object, but with ``apiVersion`` and ``kind``
attributes set to another object type. This has turned out to be a problem when
deleting CRDs, as the deletion message returns a Status that presents itself as the CRD,
and that mismatch causes an exception when processing the return.

Hikaru now senses this in general, and handles it in the following way:

1. The Status message is recognized and handled as a Status message.
2. The object on which the ``delete()`` was invoked has none of the data in the object
   changed.
3. The status object is held in a private variable and can be retrieved by calling
   ``get_status()`` on the object. If this returns None then there was no status returned.
4. The user can clear out a received status on an object with ``clear_status()``.

In this way the existing API to Hikaru classes remains intact but any Status that is
returned is now available for examination.

v0.16.0b
--------

*Default K8s release:* 26.x

*Deprecated K8s release:* 23.x

Hikaru 0.16.0b is a catch-up release that adds support for three K8s releases,
24.x, 25.x, and 26.x. The release used by Hikaru by default is 26.x; that is, unless
configured otherwise with a call to *set_default_release()*, a program using 0.16.0b
will expect to be working with a 26.x K8s installation, will install the 26.x Python
client, and will create objects from the rel_1_26 package in hikaru.model.

As a variety of circumstances have caused Hikaru to fall behind the official Python K8s
client, it was decided that it would be faster to deliver support for these three K8s
releases in a single Hikaru release, rather than creating a different Hikaru release
for each K8s client release.

Hikaru's requirements.txt is set up to allow a range of K8s clients, so you can install a
release
earlier then 26.x for use with Hikaru by installing the desired release first and then
installing Hikaru (it can also be done afterwards by uninstalling/installing the
desired release with pip). The associated PyPI packages for K8s Python client packages
supported by 0.16.0b are:

- for 23.x, use kubernetes==23.6.0
- for 24.x, use kubernetes==24.2.0
- for 25.x, use kubernetes==25.3.0
- for 26.x, use kubernetes==26.1.0

Besides adjustments for changes in the swagger from 23.x, no new functionality is included
in this release over what was added in 0.13.0b. Additionally, the definitions that were
noted as missing in the 0.13.0b release notes are still missing in the 26.x swagger.

v0.13.0b
--------

*Default K8s release:* 23.x

*Deprecated K8s release:* 20.x

Hikaru 0.13.0b provides support for the v23.x Python Kubernetes client.

The biggest change in this release is in the builder. The emergence of a v2 set of
model objects has occasioned me to review both the input swagger and the code generation
logic, as I felt that a v2 GA release should receive a bit of extra scrutiny. A good
thing too, since practices that were adopted in the earlier, less mature days of the
swagger spec file were becoming less desirable with some of the newer spec files.

Without getting too bogged down into detail the net result is this: starting in this
release and only with package hikaru.model.rel_1_23, version modules will only contain
the classes defined for that version, and will import classes from other versions as
needed. Previously, for a variety of reasons, if a class in one version required a
class from another version, the builder just replicated the class in the referencing
class's module. Now, instead of duplicating the code, import statements are generated
to pull the needed classes into the referencing module. This results in much smaller
generated code files in the hikaru.model subpackages, which will in turn make Hikaru
a smaller package to download an install as additional new releases of the K8s swagger
are supported. Interestingly, it turns out that there isn't a lot of stuff in the v2
module with this new practice put into place.

Most of the rest here is 'keeping the lights on' stuff:

- @arikalon1's performance enhancement change from the 0.13a release comes forward; this
  caches certain repeatable results internally increasing the speed of certain object
  creation operations.

- @R0ll1ngSt0ne noted that the black release was pinned to a pretty old version of that
  package in the requirements.txt file. Since hikaru is dependent on an unofficial API
  suggested by the black team, this has been updated to the newest black which also
  happily supports this. So a range of black releases are now supported, but we still
  retain an upper bound. I'm sure I'll be having this conversation again in the future
  ;-).

- One of the classes that have the same name across different K8s API groups has
  finally gone, so I'm happy to report that we now only have a single Event class
  in the v1 model module.

- As in the alpha release, we still have some dangling type references in the swagger.
  The swagger contains some operations (paths) that name some parameters with types
  that the same swagger doesn't provide definitions for. It's worth repeating that list
  here:
    - PodAttachOptions
    - PodExecOptions
    - PodPortForwardOptions
    - PodProxyOptions
    - ServiceProxyOptions
    - NodeProxyOptions
  The builder skips generating methods that have parameters that reference these types
  since they can't be tied out. If they are really needed, we could look into just
  allowing a dict for them and leave it to the user to structure them properly. But as
  that is in conflict with Hikaru's base philosophy they have been discarded in this
  release.

Finally, like all past hikaru releases this one has a few classes that Hikaru gives
customized names. This is because same class name appears in multiple groups in the
K8s API, but Hikaru uses a single name space per version. To avoid collisions, this
short list of classes has the group name added to the class name. This release sports
fewer of these collisions, probably reflecting the deprecation of some duplicates in
the swagger spec. Here are the collisions for this release:

+----------+----------------------------------+----------------------+
|          | ServiceReference                 | TokenRequest         |
+----------+----------------------------------+----------------------+
| v1       | ServiceReference                 | TokenRequest         |
|          | ServiceReference_apiextensions   | TokenRequest_storage |
|          | ServiceReference_apiregistration |                      |
+----------+----------------------------------+----------------------+
| v1alpha1 |                                  |                      |
+----------+----------------------------------+----------------------+
| v1beta1  |                                  |                      |
+----------+----------------------------------+----------------------+
| v1beta2  |                                  |                      |
+----------+----------------------------------+----------------------+
| v2       |                                  |                      |
+----------+----------------------------------+----------------------+
| v2beta1  |                                  |                      |
+----------+----------------------------------+----------------------+
| v2beta2  |                                  |                      |
+----------+----------------------------------+----------------------+

This simplification is due to both the maturity of the swagger spec as well as the
changes noted regarding the improved reuse of classes across version packages.

v0.13.0a
--------

*Default K8s release:* 23.x

*Deprecated K8s release:* 20.x

*PLEASE NOTE THIS IS AN ALPHA RELEASE!*

Hikaru 0.13.0a is meant to provide an early look at support for the v23.x Python
Kubernetes client. Given that this is an alpha, the notes here are going to focus more
on the issues surrounding the alpha nature or the release rather than a full accounting
of all the changes.

This version of the K8s client is based on an OpenAPI spec file that names a full-blown
'v2' API for Kubernetes, the first that I've seen. Given the appearance of this version,
some additional tests that focused on what is expected to be v2 functionality were
created. These didn't run as expected, and upon investigation it appears that there may
be some changes required in the code generator, but a deeper dive into the OpenAPI spec
will be required to fully determine this. However, v1 objects and methods all seem to be
passing their tests. Given this, it seemed worthwhile to create an alpha release that
has the v1 support in place for users to have a tinker with while the v2 issues are being
investigated further.

So the main advice for this alpha release is: _stick with the v1 model objects_ as they
are passing the existing tests. You should be safe to develop against those, but I'd
recommend steering clear of the v2 objects until the beta release comes out.

Other things worth mentioning:

User @arikalon1 found a performance issue when performing a lot of operations that
call get_empty_instance() a lot, and suggested a caching scheme that would speed up
the intermediate results this call uses to get an instance. This has been implemented
in the alpha code.

The OpenAPI JSON file contain a number of references to types that aren't defined
in the spec file. These references are for types and are used as arguments to various
methods, but there is no definition for the type in the swagger file. When hikaru's
builder encounters such items, the method itself is skipped from code generation since
it isn't clear what's needed here. The list of these undefined types is:

- PodAttachOptions
- PodExecOptions
- PodPortForwardOptions
- PodProxyOptions
- ServiceProxyOptions
- NodeProxyOptions

If anyone can point me in the direction of where I can find info to resolve these it
would be helpful.

v0.12.0b
--------

*Default K8s release:* 22.x

*Deprecated K8s release:* 19.x

Hikaru 0.12.0b is focused on helping bring Hikaru up-to-date with the current releases
of the Python Kubernetes client. It has been delayed for two major reasons: an odd
bug that caused support for Kubernetes 21.x to fail in various tests, and life in
general.
Both are now in hand, and we're shooting for a series of Hikaru releases to catch up with
the Kubernetes client.

Besides adding support for Kubernetes 22.x, this release of Hikaru enjoys a document
update and tidy-up.

In line with Hikaru's deprecation policy, 0.12.0b drops support for Kubernetes 18.x.
Support for 19.x is now deprecated, and the next release of Hikaru will drop support for
this release.

Kubernetes 22.x client appears to have dropped support for quite a few classes in the
v1beta1 model package. If you're using version of the model, it's a good idea to
consult the
devtools/rel_0_11_0_12_diffs.csv document to see what is no longer found in Hikaru
0.12.0b.

As with past releases, Hikaru 0.12.0b applies a naming convention to differentiate
identical
object names that are in different groups in the Kubernetes API spec, leaving what Hikaru
considers the 'primary' name as-is and applying a suffix (the group name) to the
alternatives. The table below shows which classes this processing has been performed on
for each version of the model in the 22.x spec. Note that previously v1beta1 had more
variations on the Subject class than it does in this release.

+----------+----------------------------------+----------------------+--------------+---------------------+
|          | ServiceReference                 | TokenRequest         | Event        | Subject             |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1       | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1alpha1 | ServiceReference                 | TokenRequest         | Event        | Subject             |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   | Subject\_\*         |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1beta1  | ServiceReference                 | TokenRequest         | Event        | Subject             |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   | Subject\_\*         |
|          | ServiceReference_apiregistration | TokenRequest\_\*     | Event_events |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta1  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta2  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+



v0.11.0b
--------

*Default K8s release:* 1.21

*Deprecated K8s release:* 1.18

Hikaru 0.11.0b is another catch-up release that had to wait for the rewrite of
Hikaru's build system. The Kubernetes Python client went through several releases
during this rewrite and so we're just now getting caught up on the releases put out
by the K8s team in the interim. As of this writing, support of 1.21 is the last
official release as part of this catch-up, however an alpha pre-release of 1.22
is currently available so the Hikaru project will be working to support that
once it is official.

In line with the deprecation policy introduced with Hikaru 0.9.0b, this release of
Hikaru drops support for release 1.17 of the K8s Python client, and marks the support
of 1.18 as now deprecated.

Version 1.21 appears to have dropped the definition of objects in the v2alpha1 version
of the K8s swagger file, and consequently Hikaru no longer has support for v2alpha1
objects in the 1.21 models. This shouldn't cause any particular hardships.

As first started in Hikaru 0.9.0b, we've introduced a naming convention for classes
that have the same base name across different groups in the original swagger. Since
Hikaru doesn't use groups, it has to distinguish these name collisions by appending
the group name as a suffix to the class where the name collisions lie. The table below
Illustrates the collisions in the various K8s version modules in Hikaru 0.11.0b:

+----------+----------------------------------+----------------------+--------------+---------------------+
|          | ServiceReference                 | TokenRequest         | Event        | Subject             |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1       | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1alpha1 | ServiceReference                 | TokenRequest         | Event        | Subject             |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   | Subject\_\*         |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1beta1  | ServiceReference                 | TokenRequest         | Event        | Subject             |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   | Subject_flowcontrol |
|          | ServiceReference_apiregistration | TokenRequest\_\*     | Event_events | Subject_rbac        |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta1  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta2  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+

\* The builder was unable to find a group name for this resource in the source swagger, so there is no suffix

*Method deletions from 0.10*

There have been no movements of methods to correct mis-associations from v0.10, however with the deletion
of support for v2alpha1, all those objects and their methods are no longer available. This probably
impact just about no one, but you can find the detailed changes here:
`rel_0-10_to_0-11_diffs.csv
<https://github.com/haxsaw/hikaru/blob/main/devtools/rel_0_10_to_0_11_diffs.csv>`_


*Known bugs*

The K8s Python client's support for some EventList operations remains broken, and hence exceptions are
raised in Hikaru in some circumstances when this object is used. The underlying bug is documented here
https://github.com/kubernetes-client/python/issues/1616, and has been identified as a K8s Python client
regression. We'll roll out patch releases for past supported versions if/when past K8s Python clients are
patched.

v0.10.0b
--------

*Default K8s release:* 1.20

*Deprecated K8s release:* 1.17

Hikaru 0.10.0b is largely a catch-up release to bring support for Kubernetes 1.20 Python client to Hikaru.
As such, no significant new features are in this release-- it is focused on providing an update on the
models so that K8s 1.20 Python client code can safely be used.

In line with the deprecation policy introduced with Hikaru 0.9, support for the K8s 1.16 Python client has
been dropped with this release: these models will no longer be included nor supported by Hikaru, so if you
require support for K8s 1.16 you should pin your dependencies on Hikaru 0.9, as that's the last release of
Hikaru with support for that version of the K8s Python client.

Also in line with this policy, we are now marking release 1.17 models as deprecated in Hikaru 0.10.0b, and
support for K8s 1.17 will be dropped when Hikaru 0.11 is released.

As was introduced in Hikaru 0.9, an implementation choice was made to address the name collisions that have
emerged within a single version of K8s resources that are are made distinct in K8s by the colliding resources
existing in separate groups (see the release notes for 0.9 for more details). Hikaru's solution to this problem
has been to identify a 'primary' variation of the resource name, and then to add the group name as a suffix to
the other variations to reflect which group the variation comes from. The following table shows all colliding
names and their variants in Hikaru 0.10:

+----------+----------------------------------+----------------------+--------------+---------------------+
|          | ServiceReference                 | TokenRequest         | Event        | Subject             |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1       | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1alpha1 | ServiceReference                 | TokenRequest         | Event        | Subject             |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   | Subject_flowcontrol |
|          | ServiceReference_apiregistration |                      |              | Subject_rbac        |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v1beta1  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration | TokenRequest\_\*     | Event_events |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2alpha1 | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta1  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+
| v2beta2  | ServiceReference                 | TokenRequest         | Event        |                     |
|          | ServiceReference_apiextensions   | TokenRequest_storage | Event_core   |                     |
|          | ServiceReference_apiregistration |                      |              |                     |
+----------+----------------------------------+----------------------+--------------+---------------------+

\* The builder was unable to find a group name for this resource in the source swagger, so there is no suffix

*Method deletions from 0.9*

The release comparison report shows some methods have been removed from some classes
between release 1.19 and 1.20 of the K8s Python client; these deletions are reflected
in the methods exposed in Hikaru. As these deletions are all in the **v1alpha1**
version of
1.19, there's a good chance that only very early adopters will be impacted by these
deletions.

The deletions are too long for this note; please see `rel_0-9_to_0-10_diffs.csv
<https://github.com/haxsaw/hikaru/blob/main/devtools/rel_0_9_to_0_10_diffs.csv>`_ for a full accounting
of the methods that were deleted from objects in v1alpha1.

*Known bugs*

The K8s Python client's support for some EventList operations remains broken, and hence exceptions are
raised in Hikaru in some circumstances when this object is used. The underlying bug is documented here
https://github.com/kubernetes-client/python/issues/1616, and has been identified as a K8s Python client
regression. We'll roll out patch releases for past supported versions if/when past K8s Python clients are
patched.

v0.9.0b
-------

This release may produce some breaking changes due to changes in the K8s swagger.

This release has taken a while as the 1.19 version of the K8s Python client is
based on a swagger file that breaks some of the build system's assumptions.
This has required consideration as to how to address the changes as well as a
rebuild of the build system for Hikaru, a non-trivia task.

The changes that have caused the breakage is the emergence of identically-named
resources in different groups but within the same version. It has appeared that up
to this K8s release resources with the same names only appeared in different
versions, and hence Hikaru was able disregard group names, offering a single
namespace per version so that it is easier to find the resource classes required.

Release 1.19 of the K8s Python client is based on a swagger file that introduces
a small number of resource definitions with the same name in the same version,
but in different groups. Since we don't want to introduce the concept of 'group'
into Hikaru at this point due to the disruption it would cause existing users,
options for addressing this problem had to be weighed along with implementation
impact.

In the end, a new build system was created that allows for the manual
specification of a single resource class to be the 'primary' resource with that
name, and all other resources with the same name are renamed to have the
conflicting name, followed by '_', followed by the group name (if it can be
determined).

The following table summarizes the resource classes that have gone through this
renaming process, showing what versions of the API are affected, and the names
that have been generated for each of these versions:

+----------+----------------------------------+--------------+---------------------+
|          | ServiceReference                 | Event        | Subject             |
+==========+==================================+==============+=====================+
| v1       | ServiceReference                 | Event        |                     |
|          | ServiceReference_apiextensions   | Event_core   |                     |
|          | ServiceReference_apiregistration |              |                     |
+----------+----------------------------------+--------------+---------------------+
| v1alpha1 | ServiceReference                 | Event        | Subject             |
|          | ServiceReference_apiextensions   | Event_core   | Subject_flowcontrol |
|          | ServiceReference_apiregistration |              | Subject_rbac        |
+----------+----------------------------------+--------------+---------------------+
| v1beta1  | ServiceReference                 | Event        | Subject             |
|          | ServiceReference_apiextensions   | Event_core   | Subject\_*          |
|          | ServiceReference_apiregistration | Event_events |                     |
+----------+----------------------------------+--------------+---------------------+
| v2alpha1 | ServiceReference                 | Event        |                     |
|          | ServiceReference_apiextensions   | Event_core   |                     |
|          | ServiceReference_apiregistration |              |                     |
+----------+----------------------------------+--------------+---------------------+
| v2beta1  | ServiceReference                 | Event        |                     |
|          | ServiceReference_apiextensions   | Event_core   |                     |
|          | ServiceReference_apiregistration |              |                     |
+----------+----------------------------------+--------------+---------------------+
| v2beta2  | ServiceReference                 | Event        |                     |
|          | ServiceReference_apiextensions   | Event_core   |                     |
|          | ServiceReference_apiregistration |              |                     |
+----------+----------------------------------+--------------+---------------------+

\* The builder could not locate a group in the swagger, hence the class name ends in '_'.

All references to the appropriate variation of each resource class will use this
new name for the desired variation of the resource, so type hints in IDEs
will be able to guide the user in selecting the correct variation. It was
admittedly a bit of a guess as to the proper class to make the primary, so
feedback about making a different choice would be appreciated.

Only the rel_1_19 package is built using this new approach; rel_1_18 and earlier
releases continue to use the old build system in order to maintain a stable API
for users.

Given the potential disruption this may cause, the 'default release' is being
held at 1.18 instead of being advanced to 1.19. Users can access the 1.19 code
in the normal way by importing from 'hikaru.model.rel_1_19'.

This release also has the following additional changes:

- Python 3.10 has been added as a supported version of Python.

- The latest version of the *black* code formatter (21.12b0) has been verified
  to work with Hikaru and is now accepted as a version that satisfies the package's
  requirements.

- The Response object has been modified to be a generic type, with the type
  parameter serving as a means to establish a type annotation on the 'obj'
  attribute of this class. This allows the assignment of the
  attribute's value to an appropriately typed variable without a cast. This
  applies to all K8s versions supported in this Hikaru release.

- A policy of only supporting four releases of the underlying K8s Python client
  has been established; this is because the generated code is getting quite
  large, making the overall package grow substantially with each new supported
  K8s release. Given that most of the previous K8s releases no longer have
  support, this seems a reasonable constraint. The oldest supported release
  will output a deprecation warning when imported, instructing the user that
  the imported version will be dropped in the next release of Hikaru and
  encouraging the migration to a newer release. In 0.9.0b, this message is
  output if rel_1_16 is imported.

*Known bugs*

The 1.19 release of the K8s Python client has a bug that was reported here:
https://github.com/kubernetes-client/python/issues/1616. The problem appears
to be a regression in properly handling turing off client side validation for
the EventList resource; an exception is thrown in the K8s Python client code
upon receipt of data from Kubernetes saying that 'event_time' must not be None.
Trying to change default client configs, or specifying a different client
config for the APIClient doesn't seem to have any effect, and the K8s maintainers
acknowledge this is a regression. This bug impacts the *listNamespacedEvent()*
and *listEventForAllNamespaces()* methods of the EventList class. We haven't
been able to find a workaround for this bug, and hopefully it will be addressed
in upcoming K8s client releases.

v0.8.1b
-------

This bug fix/maintenance release provides the following:

- This release officially works with the most recent versions of the `black`
  code formatter; this is reflected in the updated requirements.txt.
- Since importing the `black` package has side effects in terms of writing
  configuration files into the user's home directory, the import of black
  has been moved into the function that uses it so that it will only carry
  out these actions in the case that actual code formatting will be performed.
- A bug was fixed that was turning '_' to '-' in keys in labels dictionary.
  This was a side-effect of the attribute renaming logic for attributes that
  have the same name as Python keywords.

v0.8.0b
-------

This release adds support for release 18.20 of the Python Kubernetes
client, which supports release 1.18 of the Kubernetes API swagger spec.
This release of the spec is smaller than the 1.17 release, and there is
a fair amount of pruning in evidence:

- An entire version has be removed in the 1.18 release of the spec:
  **v1beta2** no longer exists in the swagger file, and hence there is no
  longer a v1beta2 subpackage in the rel_1_18 model package.
- A number of operations (methods) have been dropped from the definition of
  resources in **v1beta1**. This appears to have been a full promotion to
  `v1` -only status.

Because of this, 'rel_1_17' will be retained as the default release in Hikaru
for some time to give consumers an opportunity to ensure that they don't rely
on anything from v1beta2 or methods on v1beta1 objects, and a point release
will be issued later where we switch to the default release to 'rel_1_18'.
As always, you can explicitly set your release to rel_1_18 if you choose.

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
  abstraction than is available from the underlying K8s Python client, enabling you to establish
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
  Hikaru and an older version of the K8s client for certain symbols in certain versions.
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
      SubjectAccessReview (CRUD)       Need useful examples
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
