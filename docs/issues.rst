*******************************
Issues, Changes and Limitations
*******************************

Python reserved words
---------------------

In the Kubernetes swagger file, there are some property names that are Python reserved words:
**except**, **continue**, **not**, **or**, and **from**. Since Python won't allow these words as attribute names,
they have had a '_' appended to them for use within Python, but get translated back to their
original versions when going back to YAML. So within Python, you'll use **except_**,
**continue_**, **not_**, etc. These are converted back to their official swagger names when YAML, JSON, or
Python dicts are generated from Hikaru objects.


Workarounds for JSONSchemProps
------------------------------

JSONSchemaProps has two incompatible surprises: it's definition contains property names
**$ref** and **$schema**. In Hikaru Python classes, these are transformed into **dollar_ref** and
**dollar_schema**, respectively. These are rendered back to their original form whenever you
leave Hikaru objects for YAML, JSON, or a Python dict.

Long-ish run times for formatting Python code
--------------------------------------------------------------

Hikaru uses the ``autopep`` and ``black`` packages to reformat generated code to be PEP8 compliant. However,
these packages can run into some issues with the kinds of deeply nested object instantiation
that is typical in making Python source for Hikaru objects from YAML, and can take a second
or two to return the formatted code. Nothing is wrong, just know that this operation can
take longer than you may expect. Black is the faster of these two.

Limited correctness checking
---------------------------------------------

Hikaru does little to check the correctness of parsed YAML, nor does it have any support to ensure
that API constraints such as "only one of these three alternative objects can be supplied here".
Hikaru will detect when required fields are absent, but it will not complain if semantically an optional
field has not been supplied.

It will also ignore any field that is not part of the API spec when
processing supplied YAML, and if re-generating YAML from Python objects that were originally created
by such YAML, the out-of-spec fields will not be part of the output YAML.

While all attributes in
the model objects are typed and IDEs will provide help to the author to select the proper type for
each keyword argument (or warn when the wrong one is provided), Python doesn't require this, and
will happily generate YAML for improperly constructed Hikaru objects. You can now use `get_type_warnings()`
to double-check that your object has been filled out properly according to specified types and
required fields, but currently there is no check for other usage constraints.

Finally, comments are not retained by the current version of Hikaru. So if you round-trip YAML through
Hikaru and back to YAML, the comments will be lost.

ruamel.yaml vs PyYAML
---------------------

Hikaru internally uses ruamel.yaml for YAML parsing, representation, and generation.
If using the high-level functions, this is never actually visible as you only
provide strings, paths to files, or file objects. The ruamel.yaml package was
used due to its support for newer YAML standards. However, since ruamel.yaml is
based on PyYAML, parsed-out YAML dictionaries from either package work with
Hikaru.

However, there is a lower-level method where you pass a ruamel.yaml object
to create a particular subclass of HikaruBase. These objects can be acquired using
the ``get_processors`` function, or alternatively you can create them yourself.
