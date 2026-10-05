"""Builds Grips of the Defiled: blocky, oversized obsidian gauntlets with skeletal bone claws.

A square cuff flares over the forearm into a chunky obsidian hand block. Raised bone ridges run
down the back of the hand like exposed metacarpals, and four fingers and a thumb are chains of
bone phalanges, pinched at each knuckle, ending in claws that curl forward.

The hand rides the hand followers (200/194) so the claws can't drag the wrist pivot; the pivots
come from the vanilla leather gloves (see ``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.leather_gloves,idk.33,idk.67

Usage:
    blender --background --python tools/blender/lich_grips_build.py -- [out.blend] [models dir] [preview dir]
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, Part,
)

GLOVES_PRIORITY = 10
MAX_TRIANGLES = 460

FOREARM_LABELS = frozenset({19, 22})
HAND_LABELS = frozenset({27, 28})

ARM_AXIS = ((130.0, 27.4), (114.0, 28.3))
ARM_FORWARD = -0.5
CUFF = ((129.0, 6.6, 7.0), (121.0, 7.2, 7.6), (113.5, 7.8, 8.2))

HAND = (
    (114.0, 29.2, -0.5, 6.2, 7.4),
    (104.0, 31.4, -0.5, 6.8, 8.0),
    (96.5, 31.8, -0.3, 6.0, 7.4),
)
KNUCKLE_UP = 96.5

METACARPALS = (-4.5, -1.5, 1.5, 4.5)
METACARPAL_SPAN = (110.0, 98.0)
METACARPAL_LIFT = 1.3
METACARPAL_HALF = 0.85

FINGERS = (-4.8, -1.6, 1.6, 4.8)
FINGER_LATERAL = 0.6
PHALANGES = ((0.0, 0.0, 1.35), (-5.0, 0.6, 0.85), (-9.0, 1.6, 1.1), (-12.0, 3.2, 0.7))
CLAW_TIP = (-15.0, 5.6)
THUMB_BASE = (105.0, 0.0)
THUMB_PHALANGES = ((0.0, 0.0, 1.4), (-3.0, 3.0, 0.9), (-6.5, 5.0, 1.0))
THUMB_TIP = (-9.5, 7.8)


def lerp(points, up):
    if up >= points[0][0]:
        return points[0][1:]
    for upper, lower in zip(points, points[1:]):
        if up >= lower[0]:
            t = (up - upper[0]) / (lower[0] - upper[0])
            return tuple(a + (b - a) * t for a, b in zip(upper[1:], lower[1:]))
    return points[-1][1:]


def arm_centre(side, up):
    (left,) = lerp(ARM_AXIS, up)
    return ARM_FORWARD, side * left, up


def box_loop(part, centre, half_fwd, half_left):
    fwd, left, up = centre
    return [part.vert((fwd + df * half_fwd, left + dl * half_left, up))
            for df, dl in ((1, 1), (-1, 1), (-1, -1), (1, -1))]


def loft(part, loops, colors, outward):
    for a, b in zip(loops, loops[1:]):
        for k in range(4):
            n = (k + 1) % 4
            part.face((a[k], a[n], b[n], b[k]), colors[k], outward=outward)


def build_cuff(side):
    """A square cuff, widening in two steps towards the wrist like stacked plates."""
    part = Part(f"Cuff{side}", GLOVES_PRIORITY, FOREARM_LABELS)
    loops = [box_loop(part, arm_centre(side, up), half_fwd, half_left)
             for up, half_fwd, half_left in CUFF]
    loft(part, loops, (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL),
         arm_centre(side, 121.0))
    return part


def hand_centre(side, up):
    left, fwd, *_ = lerp(HAND, up)
    return fwd, side * left, up


def build_hand(side):
    part = Part(f"Hand{side}", GLOVES_PRIORITY, HAND_LABELS)
    part.closed = True
    loops = []
    for up, left, fwd, half_left, half_fwd in HAND:
        loops.append(box_loop(part, (fwd, side * left, up), half_fwd, half_left))
    colors = (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL)
    for a, b in zip(loops, loops[1:]):
        for k in range(4):
            n = (k + 1) % 4
            part.face((a[k], a[n], b[n], b[k]), colors[k])
    part.face(tuple(loops[0]), OBSIDIAN_EDGE_HSL)
    part.face(tuple(loops[-1]), OBSIDIAN_EDGE_HSL)
    return part


def back_of_hand(side, up):
    """Lateral position of the hand's outer face (the back of the hand) at ``up``."""
    left, _, half_left, _ = lerp(HAND, up)
    return side * (left + half_left)


def build_metacarpals(side):
    """Thin bone ridges standing off the back of the hand from the wrist to the knuckles."""
    part = Part(f"Metacarpals{side}", GLOVES_PRIORITY, HAND_LABELS)
    top, bottom = METACARPAL_SPAN
    for fwd in METACARPALS:
        rows = []
        for up in (top, bottom):
            face = back_of_hand(side, up)
            rows.append([part.vert((fwd - METACARPAL_HALF, face, up)),
                         part.vert((fwd, face + side * METACARPAL_LIFT, up)),
                         part.vert((fwd + METACARPAL_HALF, face, up))])
        inside = hand_centre(side, (top + bottom) / 2)
        part.face((rows[0][0], rows[0][1], rows[1][1], rows[1][0]), BONE_HSL, outward=inside)
        part.face((rows[0][1], rows[0][2], rows[1][2], rows[1][1]), BONE_SHADOW_HSL,
                  outward=inside)
    return part


def phalanx_chain(part, base, steps, tip):
    """Square-section bone segments hanging from ``base`` (fwd, left, up): each step is
    (down, forward, half size), pinching and swelling at the knuckles, ending in a claw."""
    fwd0, left0, up0 = base
    loops = [box_loop(part, (fwd0 + forward, left0, up0 + down), half, half)
             for down, forward, half in steps]
    colors = (BONE_HSL, BONE_SHADOW_HSL, BONE_SHADOW_HSL, BONE_HSL)
    for a, b in zip(loops, loops[1:]):
        for k in range(4):
            n = (k + 1) % 4
            part.face((a[k], a[n], b[n], b[k]), colors[k])
    down, forward = tip
    point = part.vert((fwd0 + forward, left0, up0 + down))
    for k in range(4):
        part.face((loops[-1][k], loops[-1][(k + 1) % 4], point), colors[k])
    part.face(tuple(loops[0]), BONE_SHADOW_HSL)


def build_fingers(side):
    parts = []
    _, centre_left, _ = hand_centre(side, KNUCKLE_UP)
    for index, fwd in enumerate(FINGERS):
        part = Part(f"Finger{side}_{index}", GLOVES_PRIORITY, HAND_LABELS)
        part.closed = True
        base = (fwd, centre_left + side * FINGER_LATERAL, KNUCKLE_UP + 0.5)
        phalanx_chain(part, base, PHALANGES, CLAW_TIP)
        parts.append(part)
    thumb = Part(f"Thumb{side}", GLOVES_PRIORITY, HAND_LABELS)
    thumb.closed = True
    up, lateral = THUMB_BASE
    fwd, left, _ = hand_centre(side, up)
    half_fwd = lerp(HAND, up)[3]
    base = (fwd + half_fwd - 0.5, left + side * lateral, up)
    phalanx_chain(thumb, base, THUMB_PHALANGES, THUMB_TIP)
    parts.append(thumb)
    return parts


def inventory_pose(point):
    """The pair laid flat, backs of the hands up and claws pointing down the icon."""
    fwd, left, up = point
    side = 1 if left > 0 else -1
    return -(up - 110.0), side * (11.0 + fwd), side * left


def build_all():
    pieces = []
    for side in (1, -1):
        pieces += [build_cuff(side), build_hand(side), build_metacarpals(side),
                   *build_fingers(side)]
    rig = wa.Rig(
        male_refs=("leather_gloves_male0", "model_176"),
        female_refs=("leather_gloves_female0", "model_353"),
        male_anchor_refs=("leather_gloves_male0",),
        female_anchor_refs=("leather_gloves_female0",),
    )
    wa.build_variant("LichGripsMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichGripsFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichGripsInventory", pieces, None, "inventory",
                     wa.grounded(inventory_pose, pieces))


MODELS = (
    ("LichGripsInventory", "lich_grips.dat"),
    ("LichGripsMale", "lich_grips_worn.dat"),
    ("LichGripsFemale", "lich_grips_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], GLOVES_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        wa.render_previews(("LichGripsMale",), (0, 0, 0.82), args[2], scale=0.8,
                           views=(("front", (2, 0, 0.3)), ("three_quarter", (1.4, -1.4, 0.5)),
                                  ("side", (0, -2, 0.1))))
        wa.render_previews(("LichGripsInventory",), (0, 0, 0.05), args[2], scale=0.6,
                           views=(("top", (0.02, 0, 2)),))
