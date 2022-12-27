************
Introduction
************

Hikaru was created as an alternative for dealing with Kubernetes YAML files and objects.

YAML is a good format for a lot of uses, but it can become unwieldy with larger
semantic spaces like Kubernetes:

  - Due to the broad scope of the Kubernetes API, Kubernetes YAML files can become quite long, and due to indentation conventions it can be easy to lose your place or the context that a property or object exists in.
  - YAML has no intrinsic 'include' directive, and so a number of mechanisms are
    layered on top of it to facilitate either piecing larger YAML files together from
    smaller components or customizing values of specific fields for particular deployment
    environments.
  - YAML itself is just a markup language; for Kubernetes, it provides structure and agreed-upon semantics to data that the Kubernetes system uses to perform its tasks. But that data often has value in a variety of other enterprise processes such as affirming standards compliance, audit, and security review. YAML in and of itself provides no automated access to this data; some other agent must become involved to extract this data for other purposes.
  - Kubernetes YAML is quite rich, with hundreds of objects and even more fields. Authoring these files correctly requires some kind of additional support, lots of referring back to reference docs, copying chunks of existing YAML, or an encyclopedic knowledge of the API.

A number of solutions exist for these issues, but each entails different tooling. What Hikaru
strives for is providing an alternative representational mechanism that can help resolve
these issues, still be rendered as YAML for existing tooling, and enables other uses due to
the fact that the representation itself is in Python.

Hikaru is able to process Kubernetes YAML into a hierarchy of Python objects that are defined
in accordance with the official Kubernetes API swagger spec. Once in Python, the user can:

  - Easily modify attribute values to customize a base config to work in different deployment environments,
  - Facilitate the assembly of complex Kubernetes objects from standard parts from a library, making the top-level object simpler to understand,
  - Add or remove components from a set of objects.

...and then save it back out as YAML for processing by ``kubectl`` or other tooling.

You can also author Kubernetes objects directly in Python, and if done in IDEs such as PyCharm
the author will be provided assistance in terms of available attributes to set, as well as the type
of each attribute (and get warnings when the types don't match up). These can then be rendered as YAML for further processing.

Hikaru objects can also be rendered as JSON, which can serve as a handy form for storage in
a document DB for archival and audit purposes. The JSON representation can be turned back into the source Hikaru Python objects at a later time. Hikaru also supports round-tripping it's objects to Python dicts and back again.

Hikaru objects can also be queried while in memory, so inspection and audit processes can
be easily automated using the same tooling and representation as the above uses.

Additionally, Hikaru objects are integrated with the official Kubernetes Python API, so you 
can actually interact with Kubernetes directly in Hikaru; no need to go to YAML if you
don't wish to.

The single representation/multiple uses capability of Hikaru allow it to leverage your Kubernetes YAML assets further into your organization
and enterprise processes.
