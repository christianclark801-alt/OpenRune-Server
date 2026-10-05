"""Builds Garb of the Underworld: a blocky robed torso under two oversized skull pauldrons, with
a tattered cape hanging down the back.

The robe is a squared eight-sided shell cinched by an obsidian belt, with a dark tabard panel
down the front. Each shoulder carries a big bone skull: a bevelled cranium box with sunken
eye sockets, a nose notch and a jaw block, facing forward. Bell sleeves flare at the wrist. The
cape is a two-sided cloth panel from the shoulders to the shins whose hem is cut to staggered
heights.

The skulls ride the upper-arm followers (18/24) like the poison elytra. The cape is rigged with
the vanilla cape chain (labels 9-16, moved onto their followers) so it sways like a real cape,
and its pivots come from the magic skillcape; the torso pivots come from the rune platebody (see
``worn_armour.py``). The cape is left out of the inventory model so the icon reads as the robe.

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.ancestral_robe_top,obj.rune_platebody,obj.skillcape_magic,idk.18,idk.26,idk.56,idk.61

Usage:
    blender --background --python tools/blender/lich_garb_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, SHADOW_HSL,
    SHROUD_EDGE_HSL, SHROUD_HSL, Part,
)

ROBE_PRIORITY = 3
TRIM_PRIORITY = 4
CAPE_PRIORITY = 5
CAPE_LINING_PRIORITY = 0
SKULL_PRIORITY = 6
SOCKET_PRIORITY = 7
SLEEVE_PRIORITY = 10
MAX_TRIANGLES = 700

TORSO_LABELS = frozenset({2, 4, 5, 8, 94})
SHOULDER_LABELS = frozenset({21, 25})
ARM_LABELS = frozenset({17, 19, 20, 21, 22, 23, 25, 26})
CAPE_LABELS = frozenset({9, 10, 11, 12, 13, 14, 15, 16})

SEGMENTS = 8
SQUARENESS = 0.6
ROBE_RINGS = (
    (106.0, 17.0, 14.0, 13.0),
    (118.0, 15.0, 12.5, 11.5),
    (130.0, 16.0, 14.0, 11.5),
    (142.0, 19.0, 16.0, 13.0),
    (154.0, 19.5, 16.0, 13.0),
    (162.0, 16.5, 12.5, 11.5),
    (167.0, 10.5, 8.5, 8.5),
    (169.5, 7.5, 6.5, 6.5),
)
BELT = (122.0, 115.0)
BELT_STATIONS = 9
TABARD = ((160.0, 6.0), (130.0, 5.0), (107.0, 6.5))
TABARD_LIFT = 0.9

SKULL_CENTRE = (0.0, 25.0, 160.0)
SKULL_HALF = (8.0, 7.5)
SKULL_LEVELS = ((0.0, 1.0), (11.0, 1.0), (14.0, 0.62))
JAW = ((4.0, 8.6), 5.0, 4.5)
SOCKETS = (((-3.2, 8.0), (-0.8, 8.0)), ((0.8, 8.0), (3.2, 8.0)))
SOCKET_HEIGHT = (6.0, 9.5)
NOSE = ((-1.0, 3.6), (1.0, 3.6), (0.0, 5.6))

ARM_AXIS = ((161.0, 23.5), (146.0, 25.5), (130.0, 27.5), (114.0, 28.3))
ARM_FORWARD = -0.5
SLEEVE_SIDES = 6
SLEEVE_SEGMENTS = ((161.0, 132.0, 6.6, 7.4), (134.0, 113.0, 6.4, 10.5))

CAPE_ROWS = (
    (164.0, 12.0, -12.5),
    (152.0, 15.0, -15.5),
    (130.0, 16.0, -14.5),
    (108.0, 17.0, -16.5),
    (85.0, 18.0, -18.0),
    (62.0, 19.0, -19.5),
    (42.0, 20.0, -21.0),
)
CAPE_COLUMNS = 7
CAPE_WRAP = 2.5
CAPE_TATTER = (0.0, 7.0, 2.5, 9.0, 1.0, 6.0, 0.5)
CAPE_LINING_DEPTH = 0.5

INVENTORY_CENTRE_UP = 140.0
INVENTORY_BACK = 14.0


def lerp_rows(rows, up):
    rows = sorted(rows)
    if up <= rows[0][0]:
        return rows[0][1:]
    for lower, upper in zip(rows, rows[1:]):
        if up <= upper[0]:
            t = (up - lower[0]) / (upper[0] - lower[0])
            return tuple(a + (b - a) * t for a, b in zip(lower[1:], upper[1:]))
    return rows[-1][1:]


def squash(value):
    return math.copysign(abs(value) ** SQUARENESS, value)


def robe_point(theta, up, lift=0.0):
    half_width, front, back = lerp_rows(ROBE_RINGS, up)
    c, s = math.cos(theta), math.sin(theta)
    fwd, left = (front if c >= 0 else back) * squash(c), half_width * squash(s)
    length = math.hypot(fwd, left)
    scale = (length + lift) / length
    return fwd * scale, left * scale, up


def axis(up):
    return 0.0, 0.0, up


def build_robe():
    part = Part("Robe", ROBE_PRIORITY, TORSO_LABELS)
    rings = [[part.vert(robe_point(2 * math.pi * k / SEGMENTS, up)) for k in range(SEGMENTS)]
             for up, *_ in ROBE_RINGS]
    wa.ring_strip(part, rings, lambda r, k: SHROUD_HSL if r else SHROUD_EDGE_HSL,
                  lambda r, k: axis(ROBE_RINGS[r][0]))
    return part


def build_belt():
    part = Part("Belt", TRIM_PRIORITY, TORSO_LABELS)
    thetas = [2 * math.pi * i / (BELT_STATIONS - 1) for i in range(BELT_STATIONS)]
    wa.band(part, robe_point, axis, *BELT, thetas,
            (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL), None, lifts=(0.4, 1.2, 1.4, 0.3))
    return part


def build_tabard():
    """A flat dark panel down the front, narrowing at the waist and flaring over the hips."""
    part = Part("Tabard", TRIM_PRIORITY, TORSO_LABELS)
    rows = []
    for up, half in TABARD:
        width = lerp_rows(ROBE_RINGS, up)[0]
        rows.append([part.vert(robe_point(math.asin(l / width), up, TABARD_LIFT))
                     for l in (-half, 0.0, half)])
    for a, b in zip(rows, rows[1:]):
        for k in range(2):
            part.face((a[k], a[k + 1], b[k + 1], b[k]), SHROUD_EDGE_HSL,
                      outward=axis(part.verts[a[k]][2]))
    return part


def build_skull(side):
    """A bevelled cranium box facing forward over the shoulder, a jaw block under its face,
    and dark sockets and a nose notch set just proud of the face."""
    cx, cy, cz = SKULL_CENTRE
    cy *= side
    half_fwd, half_left = SKULL_HALF
    cranium = Part(f"Skull{side}", SKULL_PRIORITY, SHOULDER_LABELS)
    cranium.closed = True
    loops = []
    for rise, scale in SKULL_LEVELS:
        loops.append([cranium.vert((cx + df * half_fwd * scale, cy + dl * half_left * scale,
                                    cz + rise))
                      for df, dl in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    colors = (BONE_HSL, BONE_SHADOW_HSL, BONE_SHADOW_HSL, BONE_HSL)
    for a, b in zip(loops, loops[1:]):
        for k in range(4):
            n = (k + 1) % 4
            cranium.face((a[k], a[n], b[n], b[k]), colors[k])
    cranium.face(tuple(loops[-1]), BONE_HSL)
    cranium.face(tuple(loops[0]), BONE_SHADOW_HSL)

    jaw = Part(f"Jaw{side}", SKULL_PRIORITY, SHOULDER_LABELS)
    jaw.closed = True
    (jaw_back, jaw_front), jaw_half, jaw_drop = JAW
    box = []
    for up in (cz, cz - jaw_drop):
        box.append([jaw.vert((cx + f, cy + l, up))
                    for f, l in ((jaw_front, jaw_half), (jaw_back, jaw_half),
                                 (jaw_back, -jaw_half), (jaw_front, -jaw_half))])
    for k in range(4):
        n = (k + 1) % 4
        jaw.face((box[0][k], box[0][n], box[1][n], box[1][k]), BONE_SHADOW_HSL)
    jaw.face(tuple(box[0]), BONE_SHADOW_HSL)
    jaw.face(tuple(box[1]), BONE_SHADOW_HSL)

    face = Part(f"SkullFace{side}", SOCKET_PRIORITY, SHOULDER_LABELS)
    front = cx + half_fwd + 0.15
    low, high = SOCKET_HEIGHT
    behind = (front - 5.0, cy, cz + 7.0)
    for (l0, _), (l1, _) in SOCKETS:
        quad = [face.vert((front, cy + l, cz + u)) for l, u in ((l0, low), (l1, low), (l1, high),
                                                             (l0, high))]
        face.face(tuple(quad), SHADOW_HSL, outward=behind)
    nose = [face.vert((front, cy + l, cz + u)) for l, u in NOSE]
    face.face(tuple(nose), SHADOW_HSL, outward=behind)
    return [cranium, jaw, face]


def arm_centre(up, side):
    for (u0, l0), (u1, l1) in zip(ARM_AXIS, ARM_AXIS[1:]):
        if u1 <= up <= u0:
            t = (up - u0) / (u1 - u0)
            return ARM_FORWARD, side * (l0 + (l1 - l0) * t), up
    edge = ARM_AXIS[0] if up > ARM_AXIS[0][0] else ARM_AXIS[-1]
    return ARM_FORWARD, side * edge[1], up


def build_sleeves():
    """Hexagonal robe sleeves; the forearm flares into a wide bell at the wrist."""
    parts = []
    for side in (1, -1):
        part = Part(f"Sleeve{side}", SLEEVE_PRIORITY, ARM_LABELS)
        for top, bottom, top_radius, bottom_radius in SLEEVE_SEGMENTS:
            rings = []
            for up, radius in ((top, top_radius), (bottom, bottom_radius)):
                fwd, left, _ = arm_centre(up, side)
                rings.append([part.vert((fwd + radius * math.cos(2 * math.pi * k / SLEEVE_SIDES),
                                         left + radius * math.sin(2 * math.pi * k / SLEEVE_SIDES),
                                         up)) for k in range(SLEEVE_SIDES)])
            middle = (top + bottom) / 2
            wa.ring_strip(part, rings, lambda r, k: SHROUD_HSL if k % 3 else SHROUD_EDGE_HSL,
                          lambda r, k, middle=middle: arm_centre(middle, side))
        parts.append(part)
    return parts


def build_cape():
    """A cloth panel hanging off the shoulders, curling forward at its edges, with every other
    hem point cut higher so the bottom hangs in tatters. The lining is its own sheet a hair
    closer to the body (the client shares vertices by position, which would cancel the two
    sides' lighting) and draws at the lowest priority, so the robe and skirt cover it."""
    cape = Part("Cape", CAPE_PRIORITY, CAPE_LABELS, worn_only=True)
    sheets = []
    for depth in (0.0, CAPE_LINING_DEPTH):
        grid = []
        for r, (up, half, fwd) in enumerate(CAPE_ROWS):
            row = []
            for c in range(CAPE_COLUMNS):
                t = c / (CAPE_COLUMNS - 1) * 2 - 1
                hem = CAPE_TATTER[c] if r == len(CAPE_ROWS) - 1 else 0.0
                row.append(cape.vert((fwd + CAPE_WRAP * t * t + depth, t * half, up + hem)))
            grid.append(row)
        sheets.append(grid)
    outer, lining = sheets
    for r in range(len(outer) - 1):
        inside = (0.0, 0.0, CAPE_ROWS[r][0])
        for c in range(CAPE_COLUMNS - 1):
            quad = (outer[r][c], outer[r][c + 1], outer[r + 1][c + 1], outer[r + 1][c])
            cape.face(quad, SHROUD_HSL if c % 2 else SHROUD_EDGE_HSL, outward=inside)
            quad = (lining[r][c], lining[r][c + 1], lining[r + 1][c + 1], lining[r + 1][c])
            cape.face(quad, SHADOW_HSL, CAPE_LINING_PRIORITY, outward=(-40.0, 0.0, CAPE_ROWS[r][0]))
    return cape


def inventory_pose(point):
    fwd, left, up = point
    return -(up - INVENTORY_CENTRE_UP), left, fwd + INVENTORY_BACK


def build_all():
    body = [build_robe(), build_belt(), build_tabard(), build_cape()]
    for side in (1, -1):
        body += build_skull(side)
    arms = build_sleeves()
    rig = wa.Rig(
        male_refs=("ancestral_robe_top_male0", "ancestral_robe_top_male1", "rune_platebody_male0",
                   "rune_platebody_male1", "model_28515", "model_26632", "skillcape_magic_male0"),
        female_refs=("ancestral_robe_top_female0", "ancestral_robe_top_female1",
                     "rune_platebody_female0", "rune_platebody_female1", "model_18554",
                     "model_3476", "skillcape_magic_female0"),
        male_anchor_refs=("rune_platebody_male0", "rune_platebody_male1", "skillcape_magic_male0"),
        female_anchor_refs=("rune_platebody_female0", "rune_platebody_female1",
                            "skillcape_magic_female0"),
    )
    wa.build_variant("LichGarbMale", body, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichGarbMaleArms", arms, rig, "male", anchors=False)
    wa.build_variant("LichGarbFemale", body, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichGarbFemaleArms", arms, rig, "female", anchors=False)
    wa.build_variant("LichGarbInventory", body + arms, None, "inventory", inventory_pose)


MODELS = (
    ("LichGarbInventory", "lich_garb.dat"),
    ("LichGarbMale", "lich_garb_worn.dat"),
    ("LichGarbMaleArms", "lich_garb_worn_arms.dat"),
    ("LichGarbFemale", "lich_garb_worn_female.dat"),
    ("LichGarbFemaleArms", "lich_garb_worn_female_arms.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], ROBE_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        for names in (("LichGarbMale", "LichGarbMaleArms"),
                      ("LichGarbFemale", "LichGarbFemaleArms")):
            wa.render_previews(names, (0, 0, 0.85), args[2], scale=1.6)
        wa.render_previews(("LichGarbInventory",), (0, 0, 0.1), args[2], scale=0.8,
                           views=(("top", (0.02, 0, 2)),))
