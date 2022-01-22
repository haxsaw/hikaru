"""
This program compares two snapshots generated with methodmap and outputs
a report showing the differences

difference reports follow this form:

REL=<relnumber>;VER=<vernumber>;MISSING|MOVED|DEL|ADD;<msg>

The message following MISSING|MOVED|DEL|ADD will have the following
interpretation and form:

MISSING: means either the old or new map (or both) is/are missing
    example: no old map provided-- no further comparisons for this version

MOVED: means that the method has moved from one class to another
    example: method wibble moved from Foo to Bar in the new map

DEL: means a method no longer exists in the new map in any class
    example: method wibble on Foo doesn't exist in the new map

ADD: means a method has been added to the new map that isn't in the old one
    example: method wibble on Foo was added in the new map
"""

import csv
from ast import literal_eval
import sys


def compare_version(old_map: dict, new_map: dict) -> list:
    """
    Compare two dictionaries where the key is a method name and the value
    is the class containing the method.

    Either of old_map or new_map may be None, which case a message is
    printed and no further processing is done. If both dict args are present,
    then any differences between old_map and new_map are reported, even if one
    of them is an empty dict. This means both changes in the class that implements
    a method as well as any new/missing methods are noted.

    :param old_map: dict, possibly None; a previously captured mapping of
        method names to the class that contains the method
    :param new_map: dict, possibly None; a new mapping of method names
        to the class that contains the method
    :return: a list of strings of differences
    """
    diffs = []
    if old_map is None:
        diffs.append(['MISSING', "", '-no old map-', ""])
    if new_map is None:
        diffs.append(['MISSING', "", "", '-no new map-'])
    if diffs:
        return diffs

    # first, compare the old to the new map for changes or deletions
    for k, v in old_map.items():
        if k not in new_map:
            diffs.append(['DELETED', k, v, '--'])
        else:
            # various MOVED tests
            if isinstance(v, str):
                if isinstance(new_map[k], str):
                    if v != new_map[k]:
                        diffs.append(['MOVED', k, v, new_map[k]])
                elif v not in new_map[k]:  # assume new_map[k] is a list
                    diffs.append(['MOVED', k, v, new_map[k]])
            elif set(v) != set(new_map[k]):  # assume v is a list; new maps are never
                # strings
                for cn in v:
                    if cn not in new_map[k]:
                        diffs.append(['MOVED', k, v, new_map[k]])

    # now, compare the new map to the old for additions
    for k, v in new_map.items():
        if k not in old_map:
            diffs.append(['ADDED', k, '--', v])

    return diffs


def compare_release(old_rel: dict, new_rel: dict) -> list:
    """
    compares all the versions in an old and new release
    :param old_rel: dict; keys are version names, values are method/class dicts
    :param new_rel: dict; keys are version names, values are method/class dicts
    :return: list of strings describing the differences in the release
    """
    diffs = []
    compared = set()
    for vername, old_map in old_rel.items():
        new_map = new_rel.get(vername)
        verdiffs = compare_version(old_map, new_map)
        diffs.extend([[vername] + d for d in verdiffs])
        compared.add(vername)

    # now make sure there isn't a new version in the new_rel that should be covered
    for vername, new_map in new_rel.items():
        if vername in compared:
            continue
        verdiffs = compare_version(old_rel.get(vername), new_map)
        diffs.extend([[vername] + d for d in verdiffs])

    return diffs


def compare_snapshots(old_snap: dict, new_snap: dict) -> list:
    """
    compares all the releases in old and new snapshots

    :param old_snap: dict; keys are release names, values are release dicts
    :param new_snap:  dict; keys are release names, values are release dicts
    :return: list of strings describing the differences in the snapshot
    """
    diffs = []
    compared = set()
    for relname, old_map in old_snap.items():
        compared.add(relname)
        new_map = new_snap.get(relname)
        if new_map is None:
            sys.stderr.write(f"REL={relname};VER=N/A;MISSING;the new snapshot "
                             f"doesn't have release\n")
        else:
            reldiffs = compare_release(old_map, new_map)
            diffs.extend([[relname] + d for d in reldiffs])

    for relname, new_map in new_snap.items():
        if relname in compared:
            continue
        old_map = old_snap.get(relname)
        if old_map is None:
            sys.stderr.write(f"REL={relname};VER=N/A;MISSING;the old snapshot "
                             f"doesn't have this release\n")
        else:
            reldiffs = compare_release(old_map, new_map)
            diffs.extend([[relname] + d for d in reldiffs])
    return diffs


def load_and_compare_snapshots(old_snapshot_name: str,
                               new_snapshot_name: str) -> list:
    """
    Open the two snapshot files named and compare their contents
    :param old_snapshot_name: path to the 'old' snapshot file
    :param new_snapshot_name: path to the 'new' snapshot file
    :return: list of strings describing diffs between the two
    """
    oldf = open(old_snapshot_name, 'r')
    newf = open(new_snapshot_name, 'r')
    old_snapshot = literal_eval(oldf.read())
    new_snapshot = literal_eval(newf.read())
    return compare_snapshots(old_snapshot, new_snapshot)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <old-snapshot-file> <new-snapshot-file")
        sys.exit(1)
    diffs = load_and_compare_snapshots(sys.argv[1], sys.argv[2])
    csv_writer = csv.writer(sys.stdout)
    for l in diffs:
        csv_writer.writerow(l)
    sys.exit(0)
