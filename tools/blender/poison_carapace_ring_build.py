"""Builds the Poison carapace ring: an oversized ring made to read from the top-down camera.

A thick octagonal hoop of dark, corroded chitin lies flat. On its outer edge a bezel carries a
glowing neon-green gem, gripped by four purple insect legs that arch up and over it. The gem's
top facets are near-white green and its underside is dark, so it seems lit from inside.

The whole model stays under 80 vertices: it is exported with positions merged and every face
flat shaded, so the hard angle breaks survive without duplicating vertices.

Usage:
    blender --background --python tools/blender/poison_carapace_ring_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from poison_blades_build import hsl  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, TOXIC_DARK_HSL, TOXIC_HSL, VENOM_HSL, Part,
)

MAX_VERTICES = 80

HOOP_SIDES = 8
HOOP_OUTER = 13.0
HOOP_INNER = 9.0
HOOP_HEIGHT = 4.5
CORRODED_HSL = hsl(21, 4, 24)

SETTING_ANGLE = math.pi
BEZEL_REACH = (HOOP_OUTER - 1.5, HOOP_OUTER + 5.0)
BEZEL_HALF_WIDTH = 4.0
BEZEL_TOP = HOOP_HEIGHT + 1.5

GEM_RADIUS = 5.0
GEM_CENTRE_UP = BEZEL_TOP + GEM_RADIUS * 0.75
GEM_SIDES = 6
GEM_LATITUDES = (40, -35)
GEM_GLOW_HSL = hsl(21, 7, 104)
GEM_HSL = VENOM_HSL
GEM_SHADOW_HSL = hsl(21, 7, 38)

LEG_ANGLES = (45, 135, 225, 315)
LEG_BASE_SPREAD = 1.6
LEG_KNEE_OUT = 2.6
LEG_KNEE_UP = 0.35
LEG_KNEE_WIDTH = 1.2
LEG_GRIP_LATITUDE = 50


def polar(radius, angle, up):
    return radius * math.cos(angle), radius * math.sin(angle), up


def build_hoop():
    """Square-section octagon: top and bottom faces, inner and outer walls. A few top facets
    are corroded to a green-black."""
    part = Part("Hoop", 0)
    rings = []
    for radius, up in ((HOOP_OUTER, 0.0), (HOOP_OUTER, HOOP_HEIGHT), (HOOP_INNER, HOOP_HEIGHT),
                       (HOOP_INNER, 0.0)):
        rings.append([part.vert(polar(radius, 2 * math.pi * k / HOOP_SIDES + math.pi / HOOP_SIDES,
                                      up)) for k in range(HOOP_SIDES)])
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL)
    for r in range(4):
        a, b = rings[r], rings[(r + 1) % 4]
        for k in range(HOOP_SIDES):
            n = (k + 1) % HOOP_SIDES
            color = CORRODED_HSL if r == 1 and k % 3 == 0 else colors[r]
            mid = sum(part.verts[i][2] for i in (a[k], b[k])) / 2
            part.face((a[k], a[n], b[n], b[k]), color, outward=_hoop_inside(part, a[k], b[k], mid))
    return part


def _hoop_inside(part, i, j, up):
    """A point inside the hoop's square section, between the two loops being joined."""
    (x0, y0, _), (x1, y1, _) = part.verts[i], part.verts[j]
    angle = math.atan2(y0 + y1, x0 + x1)
    return polar((HOOP_OUTER + HOOP_INNER) / 2, angle, HOOP_HEIGHT / 2)


def setting_point(radial, lateral, up):
    c, s = math.cos(SETTING_ANGLE), math.sin(SETTING_ANGLE)
    return radial * c - lateral * s, radial * s + lateral * c, up


def build_bezel():
    part = Part("Bezel", 0)
    part.closed = True
    near, far = BEZEL_REACH
    corners = [(near, -BEZEL_HALF_WIDTH), (near, BEZEL_HALF_WIDTH), (far, BEZEL_HALF_WIDTH * 0.7),
               (far, -BEZEL_HALF_WIDTH * 0.7)]
    bottom = [part.vert(setting_point(r, l, HOOP_HEIGHT * 0.3)) for r, l in corners]
    top = [part.vert(setting_point(r, l, BEZEL_TOP)) for r, l in corners]
    for k in range(4):
        n = (k + 1) % 4
        part.face((bottom[k], bottom[n], top[n], top[k]), TOXIC_DARK_HSL)
    part.face(tuple(top), TOXIC_DARK_HSL)
    part.face(tuple(reversed(bottom)), TOXIC_DARK_HSL)
    return part


def gem_centre():
    return setting_point(sum(BEZEL_REACH) / 2, 0.0, GEM_CENTRE_UP)


def build_gem():
    """A faceted ball: a pole, two rings of six and a pole, shaded from glowing white-green on top
    to dark underneath."""
    part = Part("Gem", 0)
    part.closed = True
    cx, cy, cz = gem_centre()
    top = part.vert((cx, cy, cz + GEM_RADIUS))
    rings = []
    for index, latitude in enumerate(GEM_LATITUDES):
        lat = math.radians(latitude)
        offset = math.pi / GEM_SIDES * index
        rings.append([part.vert((cx + GEM_RADIUS * math.cos(lat) * math.cos(a),
                                 cy + GEM_RADIUS * math.cos(lat) * math.sin(a),
                                 cz + GEM_RADIUS * math.sin(lat)))
                      for a in (2 * math.pi * k / GEM_SIDES + offset for k in range(GEM_SIDES))])
    bottom = part.vert((cx, cy, cz - GEM_RADIUS))
    upper, lower = rings
    for k in range(GEM_SIDES):
        n = (k + 1) % GEM_SIDES
        part.face((top, upper[k], upper[n]), GEM_GLOW_HSL)
        part.face((upper[k], lower[k], upper[n]), GEM_HSL)
        part.face((upper[n], lower[k], lower[n]), GEM_HSL if k % 2 else GEM_SHADOW_HSL)
        part.face((bottom, lower[n], lower[k]), GEM_SHADOW_HSL)
    return part


def build_legs():
    """Each leg rises from a bezel corner, kinks outward past the gem's equator and hooks back
    in to clamp the gem above it: a two-sided ribbon so it reads from every side."""
    part = Part("Legs", 0)
    cx, cy, cz = gem_centre()
    for angle in LEG_ANGLES:
        a = math.radians(angle)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        base_r = GEM_RADIUS * 0.9
        knee_r = GEM_RADIUS + LEG_KNEE_OUT
        grip = math.radians(LEG_GRIP_LATITUDE)
        base = [part.vert((cx + dx * base_r + px * s * LEG_BASE_SPREAD,
                           cy + dy * base_r + py * s * LEG_BASE_SPREAD, BEZEL_TOP))
                for s in (-1, 1)]
        knee_up = cz + GEM_RADIUS * LEG_KNEE_UP
        knee = [part.vert((cx + dx * knee_r + px * s * LEG_KNEE_WIDTH,
                           cy + dy * knee_r + py * s * LEG_KNEE_WIDTH, knee_up)) for s in (-1, 1)]
        tip = part.vert((cx + dx * GEM_RADIUS * math.cos(grip) * 0.95,
                         cy + dy * GEM_RADIUS * math.cos(grip) * 0.95,
                         cz + GEM_RADIUS * math.sin(grip) + 0.6))
        for face, color in (((base[0], base[1], knee[1], knee[0]), TOXIC_DARK_HSL),
                            ((knee[0], knee[1], tip), TOXIC_HSL)):
            part.face(face, color)
            part.face(tuple(reversed(face)), color)
    return part


def build_all():
    pieces = [build_hoop(), build_bezel(), build_gem(), build_legs()]
    vertices = sum(len(p.verts) for p in pieces)
    assert vertices < MAX_VERTICES, f"ring has {vertices} vertices, budget {MAX_VERTICES}"
    wa.build_variant("CarapaceRing", pieces, None, "inventory", lambda p: p)
    print(f"Ring: {vertices} vertices")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        import osrs_model_export

        os.makedirs(args[1], exist_ok=True)
        model = osrs_model_export.export_collection(
            "CarapaceRing", os.path.join(args[1], "poison_carapace_ring.dat"),
            flat_shading=True, merge_vertices=True)
        assert len(model.vertices) < MAX_VERTICES, f"exported {len(model.vertices)} vertices"
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        wa.render_previews(("CarapaceRing",), (-0.03, 0, 0.03), args[2], scale=0.45,
                           views=(("top", (0.01, 0, 2)), ("tilted", (1.0, -0.9, 1.1)),
                                  ("side", (0, -2, 0.2))))
