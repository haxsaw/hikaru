Help on tools

methodmap.py
------------

This hoovers up all versions of all models and outputs a map of method
names to their containing classes by version and by release. The output is
dict literal that can be re-constituted for further processing. The intent is
to capture the output in a snapshot file inside of the release_maps
subdirectory whenever a release is made so changes can be tracked
moving forward.

mcompare.py
-----------
This program outputs a sort of 'diff' report of two maps generated
by methodmap.py. It shows what methods have been moved, added, or
deleted from which class, identifying the model release and version
for every change. This provides grist for release notes.
