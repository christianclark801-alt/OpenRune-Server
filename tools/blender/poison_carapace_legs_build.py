"""Builds the Poison carapace legs: leg guards shaped like the armoured, articulated legs of a
predatory arachnid.

Each thigh carries two broad, flat-shaded obsidian plates edged with razor-thin neon-green trim
columns. Purple diamond kneecaps jut forward into joint spikes, and the shins are guarded by
three plates that step down and back, each tucked under the one above. The legs are
eight-sided tubes whose inner faces are flattened so the thighs and calves stay clear of each
other through the running and attack animations. A segmented girdle closes the waist under the
torso.

Labels, pivot anchors, the female warp and the inventory pose come from ``worn_armour.py``; the
kneecaps sit on the kneecap labels (33/36), which ride the knee without moving its pivot.

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.rune_platelegs,idk.36,idk.70

Usage:
    blender --background --python tools/blender/poison_carapace_legs_build.py -- [out.blend] [models dir] [preview dir]
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

LEGS_PRIORITY = 1
PLATE_PRIORITY = 2
MAX_TRIANGLES = 900

GIRDLE_LABELS = frozenset({5, 29, 30, 41})
LEG_LABELS = frozenset({31, 32, 33, 34, 35, 36, 37, 38, 40, 42, 43, 44})
KNEECAP_LABELS = frozenset({33, 36})

GIRDLE_SEGMENTS = 8
GIRDLE_RINGS = ((114.0, 16.0, 12.5, 12.0), (105.0, 17.0, 13.0, 12.5), (97.0, 18.0, 13.5, 13.0))
GIRDLE_BANDS = ((114.0, 105.5), (106.5, 97.0))
GIRDLE_STATIONS = 9

LEG_SEGMENTS = 8
LEG_STATIONS = (
    (101.0, 9.0, 0.0, 8.5, 7.0, 10.5, 10.5),
    (84.0, 9.5, 0.5, 8.0, 7.0, 9.5, 9.0),
    (66.0, 9.0, 0.5, 6.8, 6.0, 8.0, 7.5),
    (58.0, 9.0, 0.0, 6.5, 5.8, 7.5, 7.0),
    (44.0, 9.0, -0.5, 6.0, 5.0, 6.5, 7.5),
    (30.0, 9.0, -0.5, 5.0, 4.0, 5.5, 5.5),
    (18.0, 9.0, -0.5, 4.8, 4.0, 5.5, 5.5),
)
INNER_FLATTEN = 1.4

THIGH_PLATES = ((98.0, 83.0, -35, 125), (84.0, 68.0, -30, 120))
THIGH_STATIONS = 3
TRIM_WIDTH = 0.1
THIGH_LIFTS = (1.0, 2.2, 2.6, 0.6)

KNEE_UP = 61.0
KNEE_HALF_HEIGHT = 5.5
KNEE_HALF_ANGLE = 40
KNEE_BASE_LIFT = 1.0
KNEE_SPIKE = 7.0
KNEE_SPIKE_DROP = 1.5
KNEE_RIDGE_LIFT = 2.6

SHIN_PLATES = ((57.0, 45.0, 1.0), (46.0, 34.0, 0.8), (35.0, 23.0, 0.6))
SHIN_ARC = (-60, 80)
SHIN_STATIONS = 4
SHIN_LIFTS = (0.8, 2.1, 2.6, 0.5)

INVENTORY_CENTRE_UP = 66.0
INVENTORY_BACK = 11.0


def lerp_rows(rows, up):
    if up >= rows[0][0]:
        return rows[0][1:]
    for upper, lower in zip(rows, rows[1:]):
        if up >= lower[0]:
            t = (up - upper[0]) / (lower[0] - upper[0])
            return tuple(a + (b - a) * t for a, b in zip(upper[1:], lower[1:]))
    return rows[-1][1:]


def girdle_point(theta, up, lift=0.0):
    half_width, front, back = lerp_rows(GIRDLE_RINGS, up)
    c, s = math.cos(theta), math.sin(theta)
    fwd, left = (front if c >= 0 else back) * c, half_width * s
    length = math.hypot(fwd, left)
    scale = (length + lift) / length
    return fwd * scale, left * scale, up


def girdle_axis(up):
    return 0.0, 0.0, up


def leg_point(side, theta, up, lift=0.0):
    """A point on leg ``side``'s section: ``theta`` 0 is the front and +pi/2 the outside. The
    inner half is pressed flat, so three facets form one plane facing the other leg."""
    centre_left, centre_fwd, outer, inner, front, back = lerp_rows(LEG_STATIONS, up)
    c, s = math.cos(theta), math.sin(theta)
    fwd = (front if c >= 0 else back) * c
    lateral = outer * s if s >= 0 else -inner * min(1.0, -s * INNER_FLATTEN)
    length = math.hypot(fwd, lateral)
    scale = (length + lift) / length
    return centre_fwd + fwd * scale, side * (centre_left + lateral * scale), up


def leg_axis(side):
    def centre(up):
        centre_left, centre_fwd, *_ = lerp_rows(LEG_STATIONS, up)
        return centre_fwd, side * centre_left, up
    return centre


def on_leg(side):
    return lambda theta, up, lift=0.0: leg_point(side, theta, up, lift)


def build_girdle():
    part = Part("Girdle", LEGS_PRIORITY, GIRDLE_LABELS)
    rings = [[part.vert(girdle_point(2 * math.pi * k / GIRDLE_SEGMENTS, up))
              for k in range(GIRDLE_SEGMENTS)] for up, *_ in GIRDLE_RINGS]
    wa.ring_strip(part, rings, lambda r, k: OBSIDIAN_EDGE_HSL,
                  lambda r, k: girdle_axis(GIRDLE_RINGS[r][0]))
    plates = Part("GirdlePlates", PLATE_PRIORITY, GIRDLE_LABELS)
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL)
    thetas = [2 * math.pi * i / (GIRDLE_STATIONS - 1) for i in range(GIRDLE_STATIONS)]
    for top, bottom in GIRDLE_BANDS:
        wa.band(plates, girdle_point, girdle_axis, top, bottom, thetas, colors, None,
                lifts=(0.6, 1.6, 2.0, 0.4))
    return [part, plates]


def build_leg(side):
    part = Part(f"Leg{side}", LEGS_PRIORITY, LEG_LABELS)
    rings = [[part.vert(leg_point(side, 2 * math.pi * k / LEG_SEGMENTS, up))
              for k in range(LEG_SEGMENTS)] for up, *_ in LEG_STATIONS]
    shades = (OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL)
    wa.ring_strip(part, rings, lambda r, k: shades[(r + k) % 2],
                  lambda r, k: leg_axis(side)(LEG_STATIONS[r][0]))
    return part


def trimmed_thetas(start, end, stations):
    """Plate columns with a hair-thin column at each end, painted as the green edge trim."""
    a, b = math.radians(start), math.radians(end)
    inner = [a + TRIM_WIDTH + (b - a - 2 * TRIM_WIDTH) * i / (stations - 1) for i in range(stations)]
    return [a, *inner, b]


def build_thighs(side):
    part = Part(f"Thigh{side}", PLATE_PRIORITY, LEG_LABELS)
    for top, bottom, start, end in THIGH_PLATES:
        thetas = trimmed_thetas(start, end, THIGH_STATIONS)
        last = len(thetas) - 2

        def paint(facet, column, last=last):
            if column in (0, last):
                return VENOM_HSL
            return (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL)[facet]

        wa.band(part, on_leg(side), leg_axis(side), top, bottom, thetas, paint,
                (VENOM_DIM_HSL, VENOM_DIM_HSL), lifts=THIGH_LIFTS, ridge_at=0.5)
    return part


def build_kneecap(side):
    """A diamond on the knee front whose four facets rise to a spike jutting forward and
    slightly down; a lighter ridge along the top two edges keeps the point sharp."""
    part = Part(f"Kneecap{side}", PLATE_PRIORITY, KNEECAP_LABELS)
    surface = on_leg(side)
    half = math.radians(KNEE_HALF_ANGLE)
    top = part.vert(surface(0.0, KNEE_UP + KNEE_HALF_HEIGHT, KNEE_BASE_LIFT))
    outer = part.vert(surface(half, KNEE_UP, KNEE_BASE_LIFT))
    bottom = part.vert(surface(0.0, KNEE_UP - KNEE_HALF_HEIGHT, KNEE_BASE_LIFT))
    inner = part.vert(surface(-half, KNEE_UP, KNEE_BASE_LIFT))
    fwd, left, _ = surface(0.0, KNEE_UP, KNEE_BASE_LIFT)
    tip = part.vert((fwd + KNEE_SPIKE, left, KNEE_UP - KNEE_SPIKE_DROP))
    mid_fwd, mid_left, _ = surface(0.0, KNEE_UP + KNEE_HALF_HEIGHT * 0.45, KNEE_RIDGE_LIFT)
    crest = part.vert((mid_fwd, mid_left, KNEE_UP + KNEE_HALF_HEIGHT * 0.45))
    centre = leg_axis(side)(KNEE_UP)
    part.face((top, outer, crest), TOXIC_HSL, outward=centre)
    part.face((top, crest, inner), TOXIC_HSL, outward=centre)
    part.face((crest, outer, tip), TOXIC_HSL, outward=centre)
    part.face((crest, tip, inner), TOXIC_HSL, outward=centre)
    part.face((outer, bottom, tip), TOXIC_DARK_HSL, outward=centre)
    part.face((bottom, inner, tip), TOXIC_DARK_HSL, outward=centre)
    return part


def build_shins(side):
    part = Part(f"Shin{side}", PLATE_PRIORITY, LEG_LABELS)
    start, end = (math.radians(a) for a in SHIN_ARC)
    thetas = [start + (end - start) * i / (SHIN_STATIONS - 1) for i in range(SHIN_STATIONS)]
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL)
    for top, bottom, scale in SHIN_PLATES:
        wa.band(part, on_leg(side), leg_axis(side), top, bottom, thetas, colors,
                (VENOM_DIM_HSL, OBSIDIAN_EDGE_HSL), lifts=tuple(l * scale for l in SHIN_LIFTS))
    return part


def inventory_pose(point):
    """Laid on its back with the waist towards +z, like the vanilla platelegs icons."""
    fwd, left, up = point
    return -(up - INVENTORY_CENTRE_UP), left, fwd + INVENTORY_BACK


def build_all():
    pieces = build_girdle()
    for side in (1, -1):
        pieces += [build_leg(side), build_thighs(side), build_kneecap(side), build_shins(side)]
    rig = wa.Rig(
        male_refs=("rune_platelegs_male0", "model_28285"),
        female_refs=("rune_platelegs_female0", "model_14423"),
        male_anchor_refs=("rune_platelegs_male0",),
        female_anchor_refs=("rune_platelegs_female0",),
    )
    wa.build_variant("CarapaceLegsMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("CarapaceLegsFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("CarapaceLegsInventory", pieces, None, "inventory", inventory_pose)


MODELS = (
    ("CarapaceLegsInventory", "poison_carapace_legs.dat"),
    ("CarapaceLegsMale", "poison_carapace_legs_worn.dat"),
    ("CarapaceLegsFemale", "poison_carapace_legs_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], LEGS_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        for name in ("CarapaceLegsMale", "CarapaceLegsFemale"):
            wa.render_previews((name,), (0, 0, 0.5), args[2], scale=1.0)
        wa.render_previews(("CarapaceLegsInventory",), (0, 0, 0.1), args[2], scale=1.0,
                           views=(("top", (0.02, 0, 2)), ("tilted", (1.2, -0.8, 1.2))))
