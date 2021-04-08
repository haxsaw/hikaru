*************
Release Notes
*************

v0.3b
------

- Implemented a solution for the recursive objects in the `apiextensions` group in the swagger spec file. Hikaru now models all objects in the Kubernetes swagger spec and, with the exception of some attributes in a single object, all types are properly annotated on all `apiextensions` objects.
- Fixed a bug for YAML, JSON, and Python dicts generated from Hikaru objects; previously, the renamed keywords such as `except_` or `continue_` weren't being changed back to their original forms when generating YAML, JSON or Python dicts. This has now been corrected.
- Put in workarounds for properties in YAML that start with **$**; in Hikaru objects, these are replaced with the prefix **dollar_**, so **$ref** becomes **dollar_ref**. These are transformed back when going from Hikaru objects to YAML, JSON, or a Python dict.

v0.2a0
------

- Added support a new two new styles of generated code from `get_python_source()`: the 'black' style, using the 'black' formatter, and None, which outputs syntactically correct Python but with no formatting at all (this is the fastest generation option and is good if the code is going to be dynamically executed).
- New `get_type_warnings()` method on HikaruBase objects; compares actual values with the types currently populating an instance, and looks for required values that are missing. Generates a list of warning records for any problems found.
- New `diff()` method of HikaruBase; compares to object hierarchies and generates difference records indicating where they are differerent.
- Removed dead code.
- Improved and documented all exceptions that are raised.
- Added support for round-tripping between YAML, Python objects, Python source, JSON, and Python dicts. You can now start with any of these, move between them, and get back the original represenation.
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
