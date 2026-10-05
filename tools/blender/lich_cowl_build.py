"""Builds Lich's Cowl: a blocky, tattered hood whose face is a deep pit of shadow.

The hood is a squared twelve-sided shell rising to a point behind the head. Its front is pushed
deep into the head as a near-black cavity, and two small faceted necrotic-green eyes hang in
the dark. Short bone horns jut out of the temples, sweeping back and up, and the hem is cut
to staggered heights so it hangs in tatters over the shoulders.

The hem rides the neck label (49) like the vanilla ancestral hat, so it stays on the shoulders
when the head turns; everything else is on the head label (1). The neck pivot anchors come
from the ancestral hat (see ``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.ancestral_hat

Usage:
    blender --background --python tools/blender/lich_cowl_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, NECROTIC_DIM_HSL, NECROTIC_HSL, SHADOW_HSL, SHROUD_EDGE_HSL,
    SHROUD_HSL, Part,
)

HELM_PRIORITY = 7
EYE_PRIORITY = 8
MAX_TRIANGLES = 420

HEAD_LABEL = 1
NECK_LABEL = 49
HEAD_LABELS = frozenset({HEAD_LABEL})

SEGMENTS = 12
SQUARENESS = 0.55
HOOD_RINGS = (
    (161.5, 17.5, 16.0, 16.0),
    (168.0, 16.0, 15.0, 15.0),
    (176.0, 15.5, 16.5, 15.5),
    (186.0, 15.5, 17.5, 16.0),
    (196.0, 15.5, 17.5, 16.5),
    (205.0, 14.0, 15.5, 16.0),
    (212.0, 10.0, 10.5, 12.5),
)
HOOD_PEAK = (-7.0, 0.0, 217.0)
TATTER_RISE = (0.0, 6.0, 2.0, 7.5)

CAVITY_RINGS = (3, 4)
CAVITY_DEPTH = {0: 7.0, 1: 5.5, SEGMENTS - 1: 5.5}

EYE_UP = 190.0
EYE_LEFT = 3.6
EYE_HALF_WIDTH = 2.0
EYE_HALF_HEIGHT = 1.3
EYE_POINT = 1.3
EYE_LIFT = 0.6

HORN_UP = 199.0
HORN_BASE = 1.7
HORN_MID = ((-1.0, 5.0, 3.0), 1.0)
HORN_TIP = (-3.5, 9.0, 8.0)


def ring_point(ring, k):
    """Point ``k`` of a squared ring: the sine and cosine are flattened towards +-1 so the
    hood reads as a block with bevelled corners rather than a tube."""
    up, half_width, front, back = ring
    angle = 2 * math.pi * k / SEGMENTS
    c, s = math.cos(angle), math.sin(angle)
    squash = lambda v: math.copysign(abs(v) ** SQUARENESS, v)  # noqa: E731
    fwd = (front if c >= 0 else back) * squash(c)
    return fwd, half_width * squash(s), up


def axis(up):
    return 0.0, 0.0, up


def build_hood():
    part = Part("Hood", HELM_PRIORITY, HEAD_LABELS)
    rings = []
    for r, ring in enumerate(HOOD_RINGS):
        loop = []
        for k in range(SEGMENTS):
            fwd, left, up = ring_point(ring, k)
            if r == 0:
                up += TATTER_RISE[k % len(TATTER_RISE)]
            if r in CAVITY_RINGS and k in CAVITY_DEPTH:
                fwd -= CAVITY_DEPTH[k]
            index = part.vert((fwd, left, up))
            if r == 0:
                part.fixed[index] = NECK_LABEL
            loop.append(index)
        rings.append(loop)

    cavity = {rings[r][k] for r in CAVITY_RINGS for k in CAVITY_DEPTH}
    for r in range(len(rings) - 1):
        for k in range(SEGMENTS):
            n = (k + 1) % SEGMENTS
            face = (rings[r][k], rings[r][n], rings[r + 1][n], rings[r + 1][k])
            hollow = sum(i in cavity for i in face)
            if hollow >= 2:
                color = SHADOW_HSL
            elif hollow or r == 0:
                color = SHROUD_EDGE_HSL
            else:
                color = SHROUD_HSL
            part.face(face, color, outward=axis(HOOD_RINGS[r][0]))
    peak = part.vert(HOOD_PEAK)
    for k in range(SEGMENTS):
        part.face((rings[-1][k], rings[-1][(k + 1) % SEGMENTS], peak), SHROUD_HSL,
                  outward=axis(HOOD_RINGS[-1][0]))
    return part


def cavity_floor_fwd():
    fwd, _, _ = ring_point(HOOD_RINGS[CAVITY_RINGS[0]], 0)
    return fwd - CAVITY_DEPTH[0]


def build_eyes():
    """Two small diamonds facing out of the dark, lit brightest across the top facets."""
    part = Part("Eyes", EYE_PRIORITY, HEAD_LABELS)
    base = cavity_floor_fwd() + EYE_LIFT
    for side in (1, -1):
        left = side * EYE_LEFT
        top = part.vert((base, left, EYE_UP + EYE_HALF_HEIGHT))
        outer = part.vert((base, left + side * EYE_HALF_WIDTH, EYE_UP))
        bottom = part.vert((base, left, EYE_UP - EYE_HALF_HEIGHT))
        inner = part.vert((base, left - side * EYE_HALF_WIDTH, EYE_UP))
        point = part.vert((base + EYE_POINT, left, EYE_UP))
        behind = (base - 5.0, left, EYE_UP)
        for a, b, color in ((top, outer, NECROTIC_HSL), (inner, top, NECROTIC_HSL),
                            (outer, bottom, NECROTIC_DIM_HSL), (bottom, inner, NECROTIC_DIM_HSL)):
            part.face((a, b, point), color, outward=behind, emissive=True)
    return part


def build_horns():
    """Square-section bone spikes rising out of the temples, narrowing to a point."""
    parts = []
    for side in (1, -1):
        part = Part(f"Horn{side}", HELM_PRIORITY, HEAD_LABELS)
        part.closed = True
        _, surface_left, _ = ring_point((HORN_UP, 15.5, 17.5, 16.0), 3)
        base_left = side * (surface_left - 1.0)
        (mid_fwd, mid_out, mid_up), mid_half = HORN_MID
        sections = (((0.0, base_left, HORN_UP), HORN_BASE),
                    ((mid_fwd, base_left + side * mid_out, HORN_UP + mid_up), mid_half))
        loops = []
        for (fwd, left, up), half in sections:
            loops.append([part.vert((fwd + df * half, left, up + du * half))
                          for df, du in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
        tip_fwd, tip_out, tip_up = HORN_TIP
        tip = part.vert((tip_fwd, base_left + side * tip_out, HORN_UP + tip_up))
        colors = (BONE_HSL, BONE_SHADOW_HSL, BONE_SHADOW_HSL, BONE_HSL)
        for k in range(4):
            n = (k + 1) % 4
            part.face((loops[0][k], loops[0][n], loops[1][n], loops[1][k]), colors[k])
            part.face((loops[1][k], loops[1][n], tip), colors[k])
        part.face(tuple(loops[0]), BONE_SHADOW_HSL)
        parts.append(part)
    return parts


def build_all():
    pieces = [build_hood(), build_eyes(), *build_horns()]
    rig = wa.Rig(
        male_refs=("ancestral_hat_male0",),
        female_refs=("ancestral_hat_female0",),
        male_anchor_refs=("ancestral_hat_male0",),
        female_anchor_refs=("ancestral_hat_female0",),
        anchor_labels=wa.PIVOT_LABELS | {NECK_LABEL},
    )
    wa.build_variant("LichCowlMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichCowlFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichCowlInventory", pieces, None, "inventory",
                     wa.grounded(lambda p: p, pieces))


MODELS = (
    ("LichCowlInventory", "lich_cowl.dat"),
    ("LichCowlMale", "lich_cowl_worn.dat"),
    ("LichCowlFemale", "lich_cowl_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], HELM_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        for name in ("LichCowlMale", "LichCowlFemale"):
            wa.render_previews((name,), (0, 0, 1.48), args[2], scale=0.55,
                               views=(("front", (2, 0, 0.15)), ("three_quarter", (1.4, -1.4, 0.5)),
                                      ("side", (0, -2, 0.1)), ("back", (-1.4, 1.2, 0.6))))
