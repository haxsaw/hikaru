*************
Release Notes
*************

v0.4b
-----

Hikaru had to break the API contract implied by the semantic version number as the package structure has changed to support future features; this will
slightly change the API for import statements (see below); this should be a one-time change. 

- Enriched the output of the ``diff()`` method of HikaruBase objects to provide more details on the difference as well as the differing values in the DiffDetail dataclass. You can now see exactly what was added/removed/modified.
- Integrated the official Kubernetes Python client with the Hikaru classes; you can now invoke relevant operations from the objects that the operations involve, for example creating a Pod directly from the Pod object.
- Re-organized the structure of the ``model`` subpackage to provide future support for multiple releases of Kubernetes in the future. The user will always be able to determine which is the current *default* release that is in use, but will also be able to specify a different release to use. This is covered in more detail in the documentation on versions and releases.
- As part of the revamp to support multiple releases, added a ``documents`` modules that provides a view of just the ``HikaruDocumentBase`` subclasses if all your require in your namespace are the top-level classes. This keeps the namespace from getting cluttered.
- Modified the approach to annotations previously taken that now allows forward references to classes and cyclic dependencies. Hence, recursive objects can now be directly represented in the model files, and objects with mutual references can be created. This is important in support attaching operations as methods to relevant classes. This eliminates the need for the workarounds for ``JSONSchemProps``, and that class now is modeled just like all of the others.
- Fixed a bug in populating the field catalog that each HikaruBase object maintains; now all fields are always properly reported after a repopulate_catalog() call.

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
