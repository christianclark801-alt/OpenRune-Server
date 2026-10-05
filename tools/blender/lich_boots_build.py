"""Builds the Bone-Cracker boots: angular, heavy armoured boots with a bone spike at each toe.

A tall eight-sided obsidian shaft rises to mid-shin, faced by three plates that overlap as
they step down the shin. The foot is a blocky wedge ending in a flat toe cap, and a
square-section bone spike juts forward from each cap, kept within the vanilla toe length so it
stays above the ground when the foot flexes.

The shaft and plates ride the ankle labels (32/38) and the foot and spike the toe labels
(45/46), like the poison sabatons; the root and heel pivots come from the vanilla dragon boots
(see ``worn_armour.py``).

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.dragon_boots,idk.42,idk.79

Usage:
    blender --background --python tools/blender/lich_boots_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, Part,
)

BOOTS_PRIORITY = 0
PLATE_PRIORITY = 1
MAX_TRIANGLES = 420

ANKLE_LABELS = frozenset({32, 38})
FOOT_LABELS = frozenset({45, 46})

FOOT_LEFT = 9.0
GROUND = -6.0

SHAFT_CENTRE = (-1.0, FOOT_LEFT)
SHAFT_SIDES = 8
SHAFT_RINGS = ((34.0, 6.6), (18.0, 6.2), (4.0, 7.0))

SHIN_PLATES = ((33.0, 25.0), (26.5, 18.5), (20.0, 12.0))
SHIN_ARC = (-80, 80)
SHIN_STATIONS = 5
SHIN_LIFTS = (0.7, 1.9, 2.4, 0.5)

FOOT_STATIONS = (
    (-10.0, 5.2, 5.0),
    (-6.0, 6.2, 9.0),
    (1.0, 6.6, 9.5),
    (7.0, 6.6, 5.5),
    (11.0, 6.2, 2.5),
)
FOOT_SHOULDER = 0.7

SPIKE_BASE = (11.0, -1.5, 2.1)
SPIKE_MID = (15.5, -1.4, 1.2)
SPIKE_TIP = (19.5, -1.2)


def foot_point(side, fwd, lateral, up):
    return fwd, side * (FOOT_LEFT + lateral), up


def shaft_axis(side):
    fwd, left = SHAFT_CENTRE
    return lambda up: (fwd, side * left, up)


def shaft_point(side, theta, up, lift=0.0):
    fwd, left = SHAFT_CENTRE
    rings = sorted(SHAFT_RINGS)
    radius = rings[-1][1]
    for (u0, r0), (u1, r1) in zip(rings, rings[1:]):
        if u0 <= up <= u1:
            radius = r0 + (r1 - r0) * (up - u0) / (u1 - u0)
            break
    radius += lift
    return fwd + radius * math.cos(theta), side * (left + radius * math.sin(theta)), up


def build_shaft(side):
    part = Part(f"Shaft{side}", BOOTS_PRIORITY, ANKLE_LABELS)
    rings = [[part.vert(shaft_point(side, 2 * math.pi * k / SHAFT_SIDES, up))
              for k in range(SHAFT_SIDES)] for up, _ in SHAFT_RINGS]
    wa.ring_strip(part, rings, lambda r, k: OBSIDIAN_HSL if k % 2 else OBSIDIAN_EDGE_HSL,
                  lambda r, k: shaft_axis(side)(SHAFT_RINGS[r][0]))
    return part


def build_shin_plates(side):
    part = Part(f"ShinPlates{side}", PLATE_PRIORITY, ANKLE_LABELS)
    start, end = (math.radians(a) for a in SHIN_ARC)
    thetas = [start + (end - start) * i / (SHIN_STATIONS - 1) for i in range(SHIN_STATIONS)]
    surface = lambda theta, up, lift=0.0: shaft_point(side, theta, up, lift)  # noqa: E731
    for top, bottom in SHIN_PLATES:
        wa.band(part, surface, shaft_axis(side), top, bottom, thetas,
                (OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL),
                (OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL), lifts=SHIN_LIFTS)
    return part


def build_foot(side):
    """A blocky wedge from heel to toe cap: flat sides, a sloped top and a ridge down the
    instep."""
    part = Part(f"Foot{side}", BOOTS_PRIORITY, FOOT_LABELS)
    part.closed = True
    loops = []
    for fwd, half, top in FOOT_STATIONS:
        loops.append([part.vert(foot_point(side, fwd, lateral, up)) for lateral, up in (
            (-half, GROUND), (-half, top - 2.0), (-half * FOOT_SHOULDER, top), (0.0, top + 0.6),
            (half * FOOT_SHOULDER, top), (half, top - 2.0), (half, GROUND))])
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_HSL,
              OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL)
    for a, b in zip(loops, loops[1:]):
        for k in range(len(a)):
            n = (k + 1) % len(a)
            part.face((a[k], a[n], b[n], b[k]), colors[k])
    part.face(tuple(loops[0]), OBSIDIAN_EDGE_HSL)
    part.face(tuple(loops[-1]), OBSIDIAN_EDGE_HSL)
    return part


def build_spike(side):
    """A square bone spike from the toe cap, narrowing to a point straight ahead."""
    part = Part(f"Spike{side}", BOOTS_PRIORITY, FOOT_LABELS)
    part.closed = True
    loops = []
    for fwd, up, half in (SPIKE_BASE, SPIKE_MID):
        loops.append([part.vert(foot_point(side, fwd, dl * half, up + du * half))
                      for dl, du in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    tip = part.vert(foot_point(side, SPIKE_TIP[0], 0.0, SPIKE_TIP[1]))
    colors = (BONE_HSL, BONE_HSL, BONE_SHADOW_HSL, BONE_SHADOW_HSL)
    for k in range(4):
        n = (k + 1) % 4
        part.face((loops[0][k], loops[0][n], loops[1][n], loops[1][k]), colors[k])
        part.face((loops[1][k], loops[1][n], tip), colors[k])
    part.face(tuple(loops[0]), BONE_SHADOW_HSL)
    return part


def build_all():
    pieces = []
    for side in (1, -1):
        pieces += [build_shaft(side), build_shin_plates(side), build_foot(side),
                   build_spike(side)]
    rig = wa.Rig(
        male_refs=("dragon_boots_male0", "model_181"),
        female_refs=("dragon_boots_female0", "model_358"),
        male_anchor_refs=("dragon_boots_male0",),
        female_anchor_refs=("dragon_boots_female0",),
    )
    wa.build_variant("LichBootsMale", pieces, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichBootsFemale", pieces, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("LichBootsInventory", pieces, None, "inventory",
                     wa.grounded(lambda p: p, pieces))


MODELS = (
    ("LichBootsInventory", "lich_boots.dat"),
    ("LichBootsMale", "lich_boots_worn.dat"),
    ("LichBootsFemale", "lich_boots_worn_female.dat"),
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
        wa.render_previews(("LichBootsMale",), (0.03, 0, 0.1), args[2], scale=0.6)
