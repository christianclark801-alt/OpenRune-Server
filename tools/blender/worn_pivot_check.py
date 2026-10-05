"""Checks a worn armour set's joints against vanilla armour, using the client's model merge.

Every player joint turns around the mean of the vertices carrying its origin labels, and the
client only keeps face-referenced vertices when it merges worn models. This merges our models
and a vanilla set the way the client does, prints each joint pivot side by side, and poses both
through the idle, walk and run animations to compare how low they reach (y grows downwards,
so a bigger number sinks further into the ground).

Needs ``ref/framemap_0.json`` and the seqs, dumped with
    gradlew :or-cache:dumpAnimReference -Prefs=seq.human_ready,seq.human_walk_f,seq.human_running

Usage:
    python tools/blender/worn_pivot_check.py <ours.dat,...> <vanilla ref name,...>
e.g. ``... a_worn.dat,b_worn.dat rune_platebody_male0,rune_platebody_male1``. Exits 1 when a
pivot is missing or more than ``TOLERANCE`` units from vanilla.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osrs_anim_export import (  # noqa: E402
    apply_frame, load_reference_frame_map, load_reference_frames, resolve_defaults,
)
from osrs_model_export import load_reference_model  # noqa: E402

REF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref")
TOLERANCE = 2.0
SEQUENCES = ("human_ready", "human_walk_f", "human_running")
JOINTS = {
    0: "root", 3: "neck", 5: "waist", 8: "hip right", 10: "knee right", 12: "ankle right",
    14: "hip left", 16: "knee left", 18: "ankle left", 20: "shoulder right",
    23: "elbow right", 25: "wrist right", 28: "shoulder left", 31: "elbow left",
    33: "wrist left", 36: "cape top", 38: "cape middle", 40: "cape lower", 42: "cape hem",
}


def ref_path(name):
    return os.path.join(REF_DIR, name + ".json")


def pivots(model, frame_map):
    by_label = {}
    for index, label in enumerate(model.vertex_labels):
        by_label.setdefault(label, []).append(index)
    found = {}
    for index, name in JOINTS.items():
        members = [v for label in frame_map.transforms[index].labels
                   for v in by_label.get(label, [])]
        found[name] = (tuple(sum(model.vertices[v][k] for v in members) / len(members)
                             for k in range(3)) if members else None)
    return found


def main():
    ours_paths, vanilla_names = (arg.split(",") for arg in sys.argv[1:3])
    ours = load_reference_model(*ours_paths)
    vanilla = load_reference_model(*(ref_path(name) for name in vanilla_names))
    frame_map = load_reference_frame_map(ref_path("framemap_0"))

    failed = False
    ours_pivots, vanilla_pivots = pivots(ours, frame_map), pivots(vanilla, frame_map)
    for name in JOINTS.values():
        mine, theirs = ours_pivots[name], vanilla_pivots[name]
        if theirs is None:
            print(f"  {name:15s} not in the vanilla set, skipped")
            continue
        distance = math.dist(mine, theirs) if mine else math.inf
        failed |= distance > TOLERANCE
        mark = "ok" if distance <= TOLERANCE else "OFF"
        shown = tuple(round(c) for c in mine) if mine else None
        print(f"  {name:15s} {mark:3s} ours {shown}  vanilla "
              f"{tuple(round(c) for c in theirs)}  ({distance:.1f})")

    for sequence in SEQUENCES:
        frames, _ = load_reference_frames(ref_path(sequence))
        lows = []
        for values in frames:
            values = resolve_defaults(frame_map, values)
            mine, _ = apply_frame(ours, frame_map, values)
            theirs, _ = apply_frame(vanilla, frame_map, values)
            lows.append((max(p[1] for p in mine), max(p[1] for p in theirs)))
        worst = max(m - t for m, t in lows)
        print(f"  {sequence}: lowest point ours/vanilla {lows} (worst {worst:+d})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
