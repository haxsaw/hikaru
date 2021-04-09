*******************************
Issues, Changes and Limitations
*******************************

Python reserved words
---------------------

In the Kubernetes swagger file, there are some property names that are Python reserved words:
**except**, **continue**, and **from**. Since Python won't allow these words as attribute names,
they have had a '_' appended to them for use within Python, but get translated back to their
original versions when going back to YAML. So within Python, you'll use **except_**,
**continue_**, and **from_**. These are converted back to their official swagger names when YAML, JSON, or Python dicts are generated from Hikaru objects.


Workarounds for JSONSchemProps
------------------------------

The `apiextensions` group wasn't previously modeled by Hikaru as it contained a recusively-
defined object that couldn't be modelled using the techniques in earlier releases. From
**0.3a0** onwards, this group and its objects are now part of Hikaru, including the recursive 
object.

This object is **JSONSchemaProps**. In order to create Python dataclasses that provide a
similar feel to the others in Hikaru, this object has been broken into two parts, one
inheriting from the other. The class **JSONSchemaPropsHikaruBase** contains all the non-
recursive fields from the original JSONSchemaProps swagger definition. The **JSONSchemaProps**
class inherits from JSONSchemaPropsHikaruBase, and only contains the attributes that
originally refered back to JSONSchemaProps, but now refer instead to the parent class,
JSONSchemaPropsHikaruBase. In general, you will only need to create instances of
JSONSchemaProps, not its parent class. Anywhere there is an argument or attribute that
is annotated as needing a `JSONSchemaPropsHikaruBase` instance, you are free to use
`JSONSchemProps` instead, and your IDE won't have any complaints, and ``get_type_warnings()``
shouldn't raise any warnings.

JSONSchemaProps has two more incompatible surprises: it's definition contains property names
**$ref** and **$schema**. In Hikaru Python classes, these are transformed into **dollar_ref** and
**dollar_schema**, respectively. These are rendered back to their original form whenever you
leave Hikaru objects for YAML, JSON, or a Python dict.

Long-ish run times for formatting Python code
--------------------------------------------------------------

Hikaru uses the ``autopep`` and ``black`` packages to reformat generated code to be PEP8 compliant. However,
these packages can run into some issues with the kinds of deeply nested object instantiation
that is typical in making Python source for Hikaru objects from YAML, and can take a second
or two to return the formatted code. Nothing is wrong, just know that this operation can
take longer than you may expect.

Limited correctness checking
---------------------------------------------

Hikaru does little to check the correctness of parsed YAML, nor does it have any support to ensure
that API constraints such as "only one of these three alternative objects can be supplied here".
Hikaru will detect when required fields are absent, it will not complain if semantically an optional
field has not been supplied. It will also ignore any field that is not part of the API spec when
processing supplied YAML, and if re-generating YAML from Python objects that were originally created
by such YAML, the out-of-spec fields will not be part of the output YAML. While all attributes in
the model objects are typed and IDEs will provide help to the author to select the proper type for
each keyword argument (or warn when the wrong one is provided), Python doesn't require this, and
will happily generate YAML for improperly constructed Hikaru objects. You can now use `get_type_warnings()`
to double-check that your object has been filled out properly according to specified types and
required fields, but currently there is no check for other usage constraints.

Classes not derived from HikaruBase
------------------------------------------

The vast majority of object classes in the Kubernetes API contain other properties and objects, and
hence are derived from HikaruBase. However, in a handful of cases the Kubernetes swagger API defines
API objects that are really just renames of the `str` type. It's unclear why this is done; there's no
real documentation motivation since each property can have a description in the swagger file, so there's
really no need for an additional class just to have class documentation. It does avoid putting the
doc in more than once in the file, but the motivation is unclear. In any event, since these objects
don't have their own properties, Hikaru simply makes a derived class of ``str`` with the proper name.
While they process YAML correctly, be aware that they exist and won't support the methods that were
documented for the HikaruBase class.

Providing values for fields annotated to be of these classes may generate IDE warnings even if you
supply a ``str`` value for these fields. The code will operate correctly, but the IDE may highlight
these with warnings.

In the default (v1) version of the API model, the following classes are derived from ``str`` and
not HikaruBase:

  - Time
  - MicroTime
  - IntOrString
  - Quantity

In particular, `IntOrString` is a bit of a nuisance. While in the swagger spec file this is simply
defined as a string, apparently the intent is to allow the user to supply either string or an
actual integer. Since this component is automatically generated by the Hikaru build process, it
is defined as a str, so the use of an int in attrs defined IntOrString can receive a warning from
`get_type_warnings()`. If the type of the supplied value is actually an int you can safely ignore
this warning.

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

The ruamel.yaml package was used due to its support for newer YAML standards.
However, since ruamel.yaml is based on PyYAML, parsed-out YAML dictionaries from either
package work with Hikaru.
