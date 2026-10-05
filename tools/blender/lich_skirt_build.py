"""Builds Skirt of the Crypt: a long, angular robe skirt with a shredded hem.

A squared twelve-sided robe falls from an obsidian waistband to the ankles, shaded in vertical
folds. Its hem points are cut to staggered heights so the bottom rim hangs in tatters. The
robe hides the leg kit, so two dark shin tubes run inside it; they fill the gaps between the
tatters and the opening between the legs when the robe parts mid-stride.

Labels come from the vanilla ancestral robe bottom, so the robe bends with the legs the way a
Jagex long robe does, and its waist, hip and knee pivots come from that model too (see
``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.ancestral_robe_bottom,idk.36,idk.70

Usage:
    blender --background --python tools/blender/lich_skirt_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, SHADOW_HSL, SHROUD_EDGE_HSL, SHROUD_HSL,
    Part,
)

SKIRT_PRIORITY = 1
BAND_PRIORITY = 2
MAX_TRIANGLES = 480

SHIN_LABELS = frozenset({31, 32, 33, 34, 35, 36, 37, 38})

SEGMENTS = 12
SQUARENESS = 0.6
SKIRT_RINGS = (
    (115.0, 16.0, 12.5, 12.0),
    (104.0, 18.0, 13.5, 13.0),
    (90.0, 19.5, 14.5, 14.0),
    (70.0, 21.0, 15.5, 15.0),
    (48.0, 22.5, 16.5, 16.0),
    (16.0, 24.0, 17.5, 17.0),
)
HEM_RISE = (0.0, 10.0, 3.5, 13.0, 1.5, 8.0, 0.0, 11.5, 4.0, 9.5, 0.5, 13.5)
WAISTBAND = (116.0, 108.0)
WAISTBAND_STATIONS = 13

SHIN_LEFT = 9.0
SHIN_FORWARD = -0.5
SHIN_SIDES = 6
SHIN_RINGS = ((64.0, 6.0), (16.0, 4.6))

INVENTORY_CENTRE_UP = 66.0
INVENTORY_BACK = 18.0


def lerp_rings(up):
    rings = sorted(SKIRT_RINGS)
    if up <= rings[0][0]:
        return rings[0][1:]
    for lower, upper in zip(rings, rings[1:]):
        if up <= upper[0]:
            t = (up - lower[0]) / (upper[0] - lower[0])
            return tuple(a + (b - a) * t for a, b in zip(lower[1:], upper[1:]))
    return rings[-1][1:]


def squash(value):
    return math.copysign(abs(value) ** SQUARENESS, value)


def skirt_point(theta, up, lift=0.0):
    half_width, front, back = lerp_rings(up)
    c, s = math.cos(theta), math.sin(theta)
    fwd, left = (front if c >= 0 else back) * squash(c), half_width * squash(s)
    length = math.hypot(fwd, left)
    scale = (length + lift) / length
    return fwd * scale, left * scale, up


def axis(up):
    return 0.0, 0.0, up


def build_skirt():
    part = Part("Skirt", SKIRT_PRIORITY)
    rings = []
    for r, (up, *_) in enumerate(SKIRT_RINGS):
        loop = []
        for k in range(SEGMENTS):
            fwd, left, height = skirt_point(2 * math.pi * k / SEGMENTS, up)
            if r == len(SKIRT_RINGS) - 1:
                height += HEM_RISE[k]
            loop.append(part.vert((fwd, left, height)))
        rings.append(loop)
    wa.ring_strip(part, rings, lambda r, k: SHROUD_HSL if k % 2 else SHROUD_EDGE_HSL,
                  lambda r, k: axis(SKIRT_RINGS[r][0]))
    return part


def build_waistband():
    part = Part("Waistband", BAND_PRIORITY)
    thetas = [2 * math.pi * i / (WAISTBAND_STATIONS - 1) for i in range(WAISTBAND_STATIONS)]
    wa.band(part, skirt_point, axis, *WAISTBAND, thetas,
            (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL), None, lifts=(0.4, 1.3, 1.6, 0.3))
    return part


def build_shins():
    parts = []
    for side in (1, -1):
        part = Part(f"Shin{side}", SKIRT_PRIORITY, SHIN_LABELS)
        rings = [[part.vert((SHIN_FORWARD + r * math.cos(2 * math.pi * k / SHIN_SIDES),
                             side * SHIN_LEFT + r * math.sin(2 * math.pi * k / SHIN_SIDES), up))
                  for k in range(SHIN_SIDES)] for up, r in SHIN_RINGS]
        wa.ring_strip(part, rings, lambda r, k: SHADOW_HSL,
                      lambda r, k: (SHIN_FORWARD, side * SHIN_LEFT, 40.0))
        parts.append(part)
    return parts


def inventory_pose(point):
    """Laid on its back with the waist towards +z, like the vanilla robe bottom icons."""
    fwd, left, up = point
    return -(up - INVENTORY_CENTRE_UP), left, fwd + INVENTORY_BACK


def build_all():
    pieces = [build_skirt(), build_waistband(), *build_shins()]
    rig = wa.Rig(
        male_refs=("ancestral_robe_bottom_male0",),
        female_refs=("ancestral_robe_bottom_female0",),
        male_anchor_refs=("ancestral_robe_bottom_male0",),
        female_anchor_refs=("ancestral_robe_bottom_female0",),
    )
    wa.build_variant("LichSkirtMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichSkirtFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichSkirtInventory", pieces, None, "inventory", inventory_pose)


MODELS = (
    ("LichSkirtInventory", "lich_skirt.dat"),
    ("LichSkirtMale", "lich_skirt_worn.dat"),
    ("LichSkirtFemale", "lich_skirt_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], SKIRT_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        for name in ("LichSkirtMale", "LichSkirtFemale"):
            wa.render_previews((name,), (0, 0, 0.5), args[2], scale=1.1)
