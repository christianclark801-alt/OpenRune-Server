"""Builds the Poison carapace sabatons: low-poly armoured boots with a split-claw toe box.

The foot is a faceted obsidian wedge that splits at the ball into two tarsal claws hooking down
into the ground. Upward-curving stinger barbs rise off the back of each heel, and an hourglass
collar wraps the ankle. The lowest rows of the boot step from neon green through dim green into
black, and a translucent green haze rings each sole, so a corrosive vapour seems to pool on the
tiles beneath the player.

The foot rides the toe labels (45/46) like the vanilla bandos boots; the root and heel pivots come
from the vanilla dragon boots (see ``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.dragon_boots,idk.42,idk.79

Usage:
    blender --background --python tools/blender/poison_carapace_sabatons_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from poison_blades_build import hsl  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, TOXIC_DARK_HSL, VENOM_DIM_HSL, VENOM_HSL,
    Part,
)

BOOTS_PRIORITY = 0
MAX_TRIANGLES = 440

ANKLE_LABELS = frozenset({32, 38})
FOOT_LABELS = frozenset({45, 46})

FOOT_LEFT = 9.0
GROUND = -6.0
CORROSION_ROWS = (GROUND, -4.0, -1.5, 1.0)
GRADIENT = ((-4.0, VENOM_HSL), (-1.5, VENOM_DIM_HSL), (1.0, hsl(21, 5, 22)))

FOOT_STATIONS = (
    (-9.5, 3.5, 5.0),
    (-6.0, 5.0, 8.0),
    (0.0, 5.8, 9.0),
    (11.0, 6.2, 2.5),
)
FOOT_SHOULDER = 0.75
FOOT_SHOULDER_DROP = 1.5

CLAWS = (
    # base centre, base half width, mid (fwd, centre, half width, top), tip (fwd, lateral)
    (3.2, 3.0, (16.5, 3.8, 2.1, 0.8), (21.0, 3.4)),
    (-2.9, 2.9, (16.5, -3.0, 2.1, 1.0), (22.0, -2.2)),
)
CLAW_BASE_FWD = 10.5
CLAW_BASE_TOP = 2.5
CLAW_TIP_UP = GROUND - 0.4

CUFF_SIDES = 6
CUFF_CENTRE = (-1.0, FOOT_LEFT)
CUFF_RINGS = ((20.0, 6.8), (15.0, 5.9), (9.0, 6.8))

BARBS = (
    # (lateral, base (fwd, up), control (fwd, up), tip (fwd, up), half height, half thickness)
    (0.0, (-9.0, 5.0), (-16.0, 8.0), (-13.5, 21.0), 2.4, 1.7),
    (3.8, (-7.5, 3.0), (-13.0, 5.0), (-12.0, 12.5), 1.7, 1.3),
)
BARB_STEPS = 3

VAPOUR_UP = GROUND + 0.3
VAPOUR_REACH = 3.5
VAPOUR_ALPHA = 150
VAPOUR_PRIORITY = 0


def gradient(up):
    for ceiling, color in GRADIENT:
        if up <= ceiling + 0.01:
            return color
    return None


def foot_point(side, fwd, lateral, up):
    """``lateral`` is measured outward from the foot centre line."""
    return fwd, side * (FOOT_LEFT + lateral), up


def section(part, side, fwd, centre, half, top):
    """A boot cross-section from the inner sole edge, up the inner side through the corrosion
    rows, over the ridge and back down the outer side."""
    inner = [foot_point(side, fwd, centre - half, up) for up in CORROSION_ROWS]
    outer = [foot_point(side, fwd, centre + half, up) for up in reversed(CORROSION_ROWS)]
    shoulder = top - FOOT_SHOULDER_DROP
    ridge = [foot_point(side, fwd, centre - half * FOOT_SHOULDER, shoulder),
             foot_point(side, fwd, centre, top),
             foot_point(side, fwd, centre + half * FOOT_SHOULDER, shoulder)]
    return [part.vert(p) for p in inner + ridge + outer]


def paint_by_height(part, face, fallback):
    """Faces wholly inside a corrosion row take its colour, so the green steps up the boot in
    bands from the sole."""
    return gradient(max(part.verts[i][2] for i in face)) or fallback


def loft(part, loops, fallbacks, closed_loop=True):
    for a, b in zip(loops, loops[1:]):
        count = len(a) if closed_loop else len(a) - 1
        for k in range(count):
            face = (a[k], a[(k + 1) % len(a)], b[(k + 1) % len(b)], b[k])
            part.face(face, paint_by_height(part, face, fallbacks[k % len(fallbacks)]))


def build_foot(side):
    part = Part(f"Foot{side}", BOOTS_PRIORITY, FOOT_LABELS)
    part.closed = True
    loops = [section(part, side, fwd, 0.0, half, top) for fwd, half, top in FOOT_STATIONS]
    fallbacks = (OBSIDIAN_HSL,) * 4 + (OBSIDIAN_TOP_HSL,) + (OBSIDIAN_HSL,) * 5 + (OBSIDIAN_EDGE_HSL,)
    loft(part, loops, fallbacks)
    part.face(tuple(loops[0]), OBSIDIAN_EDGE_HSL)
    part.face(tuple(loops[-1]), OBSIDIAN_EDGE_HSL)
    return part


def build_claws(side):
    """Each tarsal claw is a ridged wedge narrowing from the ball of the foot and hooking down to
    a point on the ground."""
    parts = []
    for index, (centre, half, (mid_fwd, mid_centre, mid_half, mid_top), (tip_fwd, tip_lat)) \
            in enumerate(CLAWS):
        part = Part(f"Claw{side}_{index}", BOOTS_PRIORITY, FOOT_LABELS)
        part.closed = True

        def claw_loop(fwd, c, h, top):
            return [part.vert(foot_point(side, fwd, c - h, GROUND)),
                    part.vert(foot_point(side, fwd, c - h, -4.0)),
                    part.vert(foot_point(side, fwd, c, top)),
                    part.vert(foot_point(side, fwd, c + h, -4.0)),
                    part.vert(foot_point(side, fwd, c + h, GROUND))]

        loops = [claw_loop(CLAW_BASE_FWD, centre, half, CLAW_BASE_TOP),
                 claw_loop(mid_fwd, mid_centre, mid_half, mid_top)]
        loft(part, loops, (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_HSL,
                           OBSIDIAN_EDGE_HSL))
        tip = part.vert(foot_point(side, tip_fwd, tip_lat, CLAW_TIP_UP))
        last = loops[-1]
        for k in range(5):
            face = (last[k], last[(k + 1) % 5], tip)
            part.face(face, paint_by_height(part, face, OBSIDIAN_TOP_HSL))
        part.face(tuple(loops[0]), OBSIDIAN_EDGE_HSL)
        parts.append(part)
    return parts


def build_cuff(side):
    part = Part(f"Cuff{side}", BOOTS_PRIORITY, ANKLE_LABELS)
    fwd, left = CUFF_CENTRE
    rings = [[part.vert((fwd + r * math.cos(2 * math.pi * k / CUFF_SIDES), side * left
                         + r * math.sin(2 * math.pi * k / CUFF_SIDES), up))
              for k in range(CUFF_SIDES)] for up, r in CUFF_RINGS]
    shades = ((OBSIDIAN_TOP_HSL, OBSIDIAN_HSL), (OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL))
    wa.ring_strip(part, rings, lambda r, k: shades[r][k % 2],
                  lambda r, k: (fwd, side * left, CUFF_RINGS[r][0]))
    return part


def bezier(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c for a, b, c in zip(p0, p1, p2))


def build_barbs(side):
    """Stinger barbs rising off the heel: diamond-section spikes curving up and back to a
    venom-green point."""
    parts = []
    for index, (lateral, base, control, tip, height, thickness) in enumerate(BARBS):
        part = Part(f"Barb{side}_{index}", BOOTS_PRIORITY, FOOT_LABELS)
        part.closed = True
        path = [bezier(base, control, tip, i / BARB_STEPS) for i in range(BARB_STEPS + 1)]
        loops = []
        for i, (fwd, up) in enumerate(path[:-1]):
            taper = 1 - i / BARB_STEPS
            loops.append([part.vert(foot_point(side, fwd, lateral, up + height * taper)),
                          part.vert(foot_point(side, fwd, lateral + thickness * taper, up)),
                          part.vert(foot_point(side, fwd, lateral, up - height * taper)),
                          part.vert(foot_point(side, fwd, lateral - thickness * taper, up))])
        point = part.vert(foot_point(side, path[-1][0], lateral, path[-1][1]))
        loft(part, loops, (TOXIC_DARK_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL))
        for k in range(4):
            part.face((loops[-1][k], loops[-1][(k + 1) % 4], point),
                      VENOM_HSL if k % 2 == 0 else VENOM_DIM_HSL)
        part.face(tuple(loops[0]), OBSIDIAN_EDGE_HSL)
        parts.append(part)
    return parts


def sole_outline():
    """The boot's footprint, heel to claw tips, as (fwd, lateral) going round the outside."""
    heel = [(fwd, half) for fwd, half, _ in FOOT_STATIONS]
    outer_claw, inner_claw = CLAWS
    return ([(-9.5, 0.0)]
            + heel + [(outer_claw[3][0], outer_claw[3][1] + 1.0), (14.5, 0.3),
                      (inner_claw[3][0], inner_claw[3][1] - 1.0)]
            + [(fwd, -half) for fwd, half, _ in reversed(FOOT_STATIONS)])


def build_vapour(side):
    """A translucent green ring lying on the ground around the sole, a little wider than the
    boot, facing up."""
    part = Part(f"Vapour{side}", VAPOUR_PRIORITY, FOOT_LABELS, worn_only=True)
    outline = sole_outline()
    centre = (5.0, 0.0)
    inner, outer = [], []
    for fwd, lat in outline:
        dx, dy = fwd - centre[0], lat - centre[1]
        length = math.hypot(dx, dy) or 1.0
        inner.append(part.vert(foot_point(side, fwd, lat, VAPOUR_UP)))
        outer.append(part.vert(foot_point(side, fwd + dx / length * VAPOUR_REACH,
                                          lat + dy / length * VAPOUR_REACH, VAPOUR_UP)))
    above = foot_point(side, centre[0], centre[1], VAPOUR_UP - 10.0)
    for k in range(len(outline)):
        nxt = (k + 1) % len(outline)
        part.face((inner[k], inner[nxt], outer[nxt], outer[k]), VENOM_HSL, outward=above,
                  alpha=VAPOUR_ALPHA)
    return part


def build_all():
    pieces = []
    for side in (1, -1):
        pieces += [build_foot(side), *build_claws(side), build_cuff(side), *build_barbs(side),
                   build_vapour(side)]
    rig = wa.Rig(
        male_refs=("dragon_boots_male0", "model_181"),
        female_refs=("dragon_boots_female0", "model_358"),
        male_anchor_refs=("dragon_boots_male0",),
        female_anchor_refs=("dragon_boots_female0",),
    )
    wa.build_variant("SabatonsMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("SabatonsFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("SabatonsInventory", pieces, None, "inventory",
                     wa.grounded(lambda p: p, pieces))


MODELS = (
    ("SabatonsInventory", "poison_carapace_sabatons.dat"),
    ("SabatonsMale", "poison_carapace_sabatons_worn.dat"),
    ("SabatonsFemale", "poison_carapace_sabatons_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], BOOTS_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        wa.render_previews(("SabatonsMale",), (0.03, 0, 0.05), args[2], scale=0.5)
