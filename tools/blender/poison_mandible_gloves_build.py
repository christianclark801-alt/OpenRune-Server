"""Builds the Poison mandible gloves: forearm-length gauntlets shaped like segmented insect limbs.

Two flared hexagonal segments, keel forward, guard the forearm and tuck into each other like
the joints of an insect leg. The hand is a faceted chitin block with a row of small pyramid
spikes along the knuckles, and the thumb and index finger are curved purple mandible blades,
venom-green at the tips, that cross in front of the fist like a pincer.

The hand geometry rides the hand followers (200/194) so the pincers can't drag the wrist pivot;
the pivots come from the vanilla leather gloves (see ``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.leather_gloves,idk.33,idk.67

Usage:
    blender --background --python tools/blender/poison_mandible_gloves_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, TOXIC_DARK_HSL, TOXIC_HSL, VENOM_DIM_HSL,
    VENOM_HSL, Part,
)

GLOVES_PRIORITY = 10
MAX_TRIANGLES = 400

FOREARM_LABELS = frozenset({19, 22})
HAND_LABELS = frozenset({27, 28})

ARM_AXIS = ((131.0, 27.3), (114.0, 28.3))
ARM_FORWARD = -0.5
CUFF_SIDES = 6
CUFF_SEGMENTS = ((130.0, 122.0, 7.0, 8.4), (123.0, 113.5, 6.6, 8.0))
CUFF_TUCK = 0.72

HAND_SIDES = 6
HAND_SECTIONS = (
    (114.0, 28.6, -0.5, 4.2, 4.8),
    (104.0, 31.0, -0.5, 4.6, 5.4),
    (97.0, 31.3, -0.3, 4.2, 5.2),
    (92.0, 31.5, 0.0, 3.0, 3.8),
)
HAND_TIP_UP = 90.0

KNUCKLE_UP = 97.5
KNUCKLE_FORWARDS = (-3.2, -1.1, 1.1, 3.2)
SPIKE_BASE = 1.2
SPIKE_HEIGHT = 3.4

PINCERS = (
    ((107.0, 0.0), (11.0, 103.0), (13.5, 96.0), 2.4, 1.3),
    ((92.5, 0.0), (10.0, 92.5), (14.0, 100.0), 2.2, 1.3),
)
PINCER_STEPS = 3


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


def build_cuff(side):
    part = Part(f"Cuff{side}", GLOVES_PRIORITY, FOREARM_LABELS)
    for top, bottom, top_radius, bottom_radius in CUFF_SEGMENTS:
        rings = []
        for up, radius in ((top, top_radius), (bottom, bottom_radius),
                           (bottom + 1.0, bottom_radius * CUFF_TUCK)):
            fwd, left, _ = arm_centre(side, up)
            rings.append([part.vert((fwd + radius * math.cos(2 * math.pi * k / CUFF_SIDES),
                                     left + radius * math.sin(2 * math.pi * k / CUFF_SIDES), up))
                          for k in range(CUFF_SIDES)])
        shades = (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL,
                  OBSIDIAN_HSL, OBSIDIAN_HSL)
        middle = (top + bottom) / 2
        wa.ring_strip(part, rings,
                      lambda r, k: shades[k] if r == 0 else VENOM_DIM_HSL,
                      lambda r, k, middle=middle: arm_centre(side, middle))
    return part


def hand_point(side, up, angle, lift=0.0):
    """A point on the hand block at ``angle`` (0 = front, the thumb side; +pi/2 = the back of the
    hand, facing away from the body)."""
    centre_left, centre_fwd, half_width, half_depth = lerp(HAND_SECTIONS, up)
    c, s = math.cos(angle), math.sin(angle)
    return (centre_fwd + (half_depth + lift) * c, side * (centre_left + (half_width + lift) * s), up)


def hand_centre(side, up):
    centre_left, centre_fwd, *_ = lerp(HAND_SECTIONS, up)
    return centre_fwd, side * centre_left, up


def build_hand(side):
    part = Part(f"Hand{side}", GLOVES_PRIORITY, HAND_LABELS)
    angles = [2 * math.pi * k / HAND_SIDES for k in range(HAND_SIDES)]
    rings = [[part.vert(hand_point(side, up, a)) for a in angles] for up, *_ in HAND_SECTIONS]
    shades = (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL,
              OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL)
    wa.ring_strip(part, rings, lambda r, k: shades[k],
                  lambda r, k: hand_centre(side, HAND_SECTIONS[r][0]))
    tip = part.vert(hand_centre(side, HAND_TIP_UP))
    for k in range(HAND_SIDES):
        part.face((rings[-1][k], rings[-1][(k + 1) % HAND_SIDES], tip), OBSIDIAN_EDGE_HSL,
                  outward=hand_centre(side, HAND_SECTIONS[-1][0]))
    return part


def build_knuckles(side):
    """Square-based pyramids standing straight out of the back of the hand."""
    part = Part(f"Knuckles{side}", GLOVES_PRIORITY, HAND_LABELS)
    for fwd in KNUCKLE_FORWARDS:
        _, left, _ = hand_point(side, KNUCKLE_UP, math.pi / 2)
        corners = [part.vert((fwd + df, left, KNUCKLE_UP + du))
                   for df, du in ((SPIKE_BASE, 0), (0, SPIKE_BASE), (-SPIKE_BASE, 0), (0, -SPIKE_BASE))]
        apex = part.vert((fwd, left + side * SPIKE_HEIGHT, KNUCKLE_UP))
        for k in range(4):
            part.face((corners[k], corners[(k + 1) % 4], apex),
                      OBSIDIAN_TOP_HSL if k < 2 else OBSIDIAN_EDGE_HSL,
                      outward=hand_centre(side, KNUCKLE_UP))
    return part


def bezier(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c for a, b, c in zip(p0, p1, p2))


def build_pincers(side):
    """The thumb sweeps down and the index finger sweeps up from the front of the hand, each a
    diamond-section blade thinning to a point; the two tips cross like closed mandibles."""
    part = Part(f"Pincers{side}", GLOVES_PRIORITY, HAND_LABELS)
    _, left, _ = hand_centre(side, 100.0)
    for (base_up, base_fwd_lift), (mid_fwd, mid_up), (tip_fwd, tip_up), height, thickness \
            in PINCERS:
        base_fwd = hand_point(side, base_up, 0.0)[0] - 0.5 + base_fwd_lift
        path = [bezier((base_fwd, base_up), (mid_fwd, mid_up), (tip_fwd, tip_up), i / PINCER_STEPS)
                for i in range(PINCER_STEPS + 1)]
        loops = []
        for i, (fwd, up) in enumerate(path[:-1]):
            taper = 1 - i / PINCER_STEPS
            loops.append([part.vert((fwd, left, up + height * taper)),
                          part.vert((fwd, left + thickness * taper, up)),
                          part.vert((fwd, left, up - height * taper)),
                          part.vert((fwd, left - thickness * taper, up))])
        point = part.vert((path[-1][0], left, path[-1][1]))
        for i, (a, b) in enumerate(zip(loops, loops[1:])):
            color = (TOXIC_HSL, TOXIC_HSL, TOXIC_DARK_HSL, TOXIC_DARK_HSL)
            for k in range(4):
                centre = tuple((part.verts[a[k]][j] + part.verts[a[(k + 2) % 4]][j]) / 2
                               for j in range(3))
                part.face((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]), color[k], outward=centre)
        last = loops[-1]
        centre = tuple(sum(part.verts[v][j] for v in last) / 4 for j in range(3))
        for k in range(4):
            part.face((last[k], last[(k + 1) % 4], point), VENOM_HSL if k % 2 == 0 else VENOM_DIM_HSL,
                      outward=centre)
        part.face(tuple(loops[0]), TOXIC_DARK_HSL, outward=part.verts[loops[1][0]])
    return part


def inventory_pose(point):
    """The pair laid flat, backs of the hands up and thumbs out, cuffs towards +z."""
    fwd, left, up = point
    side = 1 if left > 0 else -1
    return -(up - 110.0), side * (10.0 + fwd), side * left


def build_all():
    pieces = []
    for side in (1, -1):
        pieces += [build_cuff(side), build_hand(side), build_knuckles(side), build_pincers(side)]
    rig = wa.Rig(
        male_refs=("leather_gloves_male0", "model_176"),
        female_refs=("leather_gloves_female0", "model_353"),
        male_anchor_refs=("leather_gloves_male0",),
        female_anchor_refs=("leather_gloves_female0",),
    )
    wa.build_variant("MandibleGlovesMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("MandibleGlovesFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("MandibleGlovesInventory", pieces, None, "inventory",
                     wa.grounded(inventory_pose, pieces))


MODELS = (
    ("MandibleGlovesInventory", "poison_mandible_gloves.dat"),
    ("MandibleGlovesMale", "poison_mandible_gloves_worn.dat"),
    ("MandibleGlovesFemale", "poison_mandible_gloves_worn_female.dat"),
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
        wa.render_previews(("MandibleGlovesMale",), (0, 0, 0.85), args[2], scale=0.75,
                           views=(("front", (2, 0, 0.3)), ("three_quarter", (1.4, -1.4, 0.5)),
                                  ("side", (0, -2, 0.1)), ("back", (-1.6, 1.0, 0.6))))
        wa.render_previews(("MandibleGlovesInventory",), (0, 0, 0.05), args[2], scale=0.6,
                           views=(("top", (0.02, 0, 2)), ("tilted", (1.2, -0.8, 1.2))))
