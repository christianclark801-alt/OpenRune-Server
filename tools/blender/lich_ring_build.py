"""Builds the Ring of Eternal Servitude: a blocky bone band standing on a small display plinth,
crowned by an oversized faceted neon-green gem.

A two-tier obsidian plinth holds the band upright so it reads from the top-down camera and in
the inventory. The band is a square-section octagonal hoop of bone. The gem is a brilliant
cut: a hexagonal table, a sloped crown, a girdle and a pavilion whose point sinks into the top
of the band. Its faces are emissive in Blender and lit brightest on top, which is all a glow
can be in game.

The model is exported flat shaded with positions merged, like the poison ring, so the facets
stay sharp without duplicating vertices.

Usage:
    blender --background --python tools/blender/lich_ring_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from poison_blades_build import hsl  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, NECROTIC_DIM_HSL, NECROTIC_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL,
    OBSIDIAN_TOP_HSL, Part,
)

MAX_VERTICES = 80

PLINTH = ((0.0, 2.0, 9.0, 12.0), (2.0, 3.5, 6.5, 9.0))

HOOP_SIDES = 8
HOOP_OUTER = 8.5
HOOP_INNER = 5.8
HOOP_HALF_DEPTH = 2.4
HOOP_CENTRE_UP = PLINTH[-1][1] + HOOP_OUTER

GEM_SIDES = 6
GEM_GIRDLE_RISE = 2.8
GEM_TABLE_RISE = 4.2
GEM_TABLE_RADIUS = 3.6
GEM_CULET = -2.5
GEM_RADIUS = 6.0
GEM_BASE_UP = HOOP_CENTRE_UP + HOOP_OUTER - 1.0
GEM_GLOW_HSL = hsl(19, 7, 112)


def build_plinth():
    part = Part("Plinth", 0)
    part.closed = True
    for index, (bottom, top, half_fwd, half_left) in enumerate(PLINTH):
        corners = ((1, 1), (-1, 1), (-1, -1), (1, -1))
        low = [part.vert((f * half_fwd, l * half_left, bottom)) for f, l in corners]
        high = [part.vert((f * half_fwd, l * half_left, top)) for f, l in corners]
        for k in range(4):
            n = (k + 1) % 4
            part.face((low[k], low[n], high[n], high[k]), OBSIDIAN_EDGE_HSL)
        part.face(tuple(high), OBSIDIAN_TOP_HSL if index else OBSIDIAN_HSL)
        part.face(tuple(reversed(low)), OBSIDIAN_EDGE_HSL)
    return part


def build_hoop():
    """An upright octagonal band facing forward, square in section."""
    part = Part("Band", 0)
    loops = []
    for radius, depth in ((HOOP_OUTER, HOOP_HALF_DEPTH), (HOOP_OUTER, -HOOP_HALF_DEPTH),
                          (HOOP_INNER, -HOOP_HALF_DEPTH), (HOOP_INNER, HOOP_HALF_DEPTH)):
        loops.append([part.vert((depth, radius * math.cos(a), HOOP_CENTRE_UP + radius * math.sin(a)))
                      for a in (2 * math.pi * k / HOOP_SIDES + math.pi / HOOP_SIDES
                                for k in range(HOOP_SIDES))])
    colors = (BONE_SHADOW_HSL, BONE_HSL, BONE_SHADOW_HSL, BONE_HSL)
    for r in range(4):
        a, b = loops[r], loops[(r + 1) % 4]
        for k in range(HOOP_SIDES):
            n = (k + 1) % HOOP_SIDES
            angle = 2 * math.pi * (k + 0.5) / HOOP_SIDES + math.pi / HOOP_SIDES
            mid = (HOOP_OUTER + HOOP_INNER) / 2
            inside = (0.0, mid * math.cos(angle), HOOP_CENTRE_UP + mid * math.sin(angle))
            part.face((a[k], a[n], b[n], b[k]), colors[r], outward=inside)
    return part


def build_gem():
    part = Part("Gem", 0)
    part.closed = True
    rings = []
    for rise, radius, offset in ((GEM_GIRDLE_RISE + GEM_TABLE_RISE, GEM_TABLE_RADIUS, 0.5),
                                 (GEM_GIRDLE_RISE, GEM_RADIUS, 0.0)):
        rings.append([part.vert((radius * math.cos(a), radius * math.sin(a), GEM_BASE_UP + rise))
                      for a in (2 * math.pi * (k + offset) / GEM_SIDES for k in range(GEM_SIDES))])
    table, girdle = rings
    culet = part.vert((0.0, 0.0, GEM_BASE_UP + GEM_CULET))
    part.face(tuple(table), GEM_GLOW_HSL, emissive=True)
    for k in range(GEM_SIDES):
        n = (k + 1) % GEM_SIDES
        part.face((table[k], girdle[k], girdle[n]), NECROTIC_HSL, emissive=True)
        part.face((table[k], girdle[n], table[n]), GEM_GLOW_HSL if k % 2 else NECROTIC_HSL,
                  emissive=True)
        part.face((girdle[n], girdle[k], culet), NECROTIC_DIM_HSL, emissive=True)
    return part


def build_all():
    pieces = [build_plinth(), build_hoop(), build_gem()]
    vertices = sum(len(p.verts) for p in pieces)
    assert vertices < MAX_VERTICES, f"ring has {vertices} vertices, budget {MAX_VERTICES}"
    wa.build_variant("LichRing", pieces, None, "inventory", lambda p: p)
    print(f"Ring: {vertices} vertices")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        import osrs_model_export

        os.makedirs(args[1], exist_ok=True)
        osrs_model_export.export_collection("LichRing", os.path.join(args[1], "lich_ring.dat"),
                                            flat_shading=True, merge_vertices=True)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        wa.render_previews(("LichRing",), (0, 0, 0.12), args[2], scale=0.45,
                           views=(("front", (2, 0, 0.4)), ("tilted", (1.2, -1.0, 1.2)),
                                  ("top", (0.01, 0, 2))))
