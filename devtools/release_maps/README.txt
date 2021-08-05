This directory contains output from the methodmap.py program.

These are snapshots of how the build.py program generates
code and what methods are attached to what class. The snapshots
are just nested dictionaries with the following structure:

Release (such as rel_1_17) key to dict value:
    Version (such as v1) key to dict value:
        method name key, containing class name value

These are simply written out as repr() of the top-level dict,
and can be reloaded with ast.literal_eval(open('snapshot-name', 'r').read())

The snapshots are named for the releases they are made from.
