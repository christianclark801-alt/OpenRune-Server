"""Builds the Poison vial amulet: a faceted glass stinger vial on a chain of chunky hexagonal links.

The links alternate dull silver and toxic purple and lie on the carapace torso's chest plates
round the neck. The pendant is a silver cap over a glass vial cut as an inverted pyramid that
narrows to a stinger point; inside, an opaque neon-green faceted core reads as volatile fluid
through the translucent glass.

The pendant and chain are open at the back, and every back vertex sits on the torso's
chest-plate lip surface (taken from ``poison_carapace_torso_build``), just proud of it, so
nothing can z-fight with the torso. The amulet draws at priority 7 so it stays on top of the
chest plates (5) and the elytra (6). The female variant uses the torso's own warp, so the
pendant lands on the female torso the same way. The inventory model is a separate flat
layout: the chain as an oval with the vial lying face up, like the vanilla necklace icons.

Needs the torso references (see ``poison_carapace_torso_build.py``).

Usage:
    blender --background --python tools/blender/poison_vial_amulet_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import poison_carapace_torso_build as torso  # noqa: E402
import worn_armour as wa  # noqa: E402
from poison_blades_build import hsl  # noqa: E402
from worn_armour import TOXIC_DARK_HSL, TOXIC_HSL, VENOM_DIM_HSL, VENOM_HSL, Part  # noqa: E402

AMULET_PRIORITY = 7
GLASS_PRIORITY = 8
MAX_TRIANGLES = 560

CHEST_LABELS = frozenset({2, 8, 94})

SILVER_HSL = hsl(41, 1, 78)
SILVER_DARK_HSL = hsl(41, 1, 56)
GLASS_HSL = hsl(22, 1, 112)
GLASS_ALPHA = 90

REST_LIFT = wa.BAND_LIFTS[2] + 0.15
NECK_LIFT = 1.2

LINKS_PER_SIDE = 9
LINK_RADIUS = 2.0
LINK_STRETCH = 1.25
LINK_HOLE = 0.45
LINK_THICKNESS = 0.8
CHAIN_PATH = ((10, 152.5), (25, 157.0), (45, 161.5), (70, 164.5), (100, 166.0), (140, 166.8),
              (180, 166.8))

PENDANT_TOP = 152.5
CAP = ((0.0, 2.6, 2.2), (-2.8, 2.6, 2.2))
VIAL = ((-2.8, 4.4, 3.2), (-5.6, 5.0, 4.0))
VIAL_TIP = (-19.0, 1.4)
FLUID = ((-3.6, 3.3, 2.4), (-6.0, 3.8, 3.0))
FLUID_TIP = (-14.0, 1.0)
FLUID_DEPTH_SCALE = 0.9
FACET_ANGLES = (-90, -45, 0, 45, 90)

INVENTORY_CAP_Z = -21.0
INVENTORY_LOOP = (9.0, 12.0)
INVENTORY_LINK_LIFT = 0.8


def chest_point(left, up, lift):
    half_width = torso.ring_at(up)[0]
    theta = math.asin(max(-1.0, min(1.0, left / half_width)))
    return torso.shell_point(theta, up, lift)


def worn_pendant_frame(lateral, v, depth):
    up = PENDANT_TOP + v
    fwd, _, _ = chest_point(lateral, up, REST_LIFT)
    return fwd + depth, lateral, up


def inventory_pendant_frame(lateral, v, depth):
    return -(INVENTORY_CAP_Z + v), lateral, depth


def link(part, centre, normal, tangent, color, rim_color):
    """A chunky hexagonal ring lying on the surface: a front face with a hole and an outer rim
    stepping back towards the surface, open behind."""
    normal, tangent = Vector(normal).normalized(), Vector(tangent).normalized()
    across = normal.cross(tangent).normalized()
    tangent = across.cross(normal).normalized()
    centre = Vector(centre)
    outer, inner, back = [], [], []
    for k in range(6):
        angle = math.pi * k / 3
        offset = tangent * math.cos(angle) * LINK_STRETCH + across * math.sin(angle)
        outer.append(part.vert(centre + offset * LINK_RADIUS))
        inner.append(part.vert(centre + offset * LINK_RADIUS * LINK_HOLE))
        back.append(part.vert(centre + offset * LINK_RADIUS - normal * LINK_THICKNESS))
    behind = centre - normal * 5
    for k in range(6):
        n = (k + 1) % 6
        part.face((outer[k], outer[n], inner[n], inner[k]), color, outward=behind)
        part.face((outer[k], back[k], back[n], outer[n]), rim_color, outward=centre)


def chain_path_point(side, t):
    """The chain path at ``t`` (0 = the pendant cap, 1 = the back of the neck)."""
    path = CHAIN_PATH
    position = t * (len(path) - 1)
    i = min(int(position), len(path) - 2)
    f = position - i
    (a0, u0), (a1, u1) = path[i], path[i + 1]
    theta = side * math.radians(a0 + (a1 - a0) * f)
    up = u0 + (u1 - u0) * f
    lift = REST_LIFT + (NECK_LIFT - REST_LIFT) * min(1.0, t * 2)
    return theta, up, lift


def worn_link_frame(side, t):
    theta, up, lift = chain_path_point(side, t)
    centre = Vector(torso.shell_point(theta, up, lift))
    ahead = Vector(torso.shell_point(*chain_path_point(side, min(t + 0.02, 1.0))))
    behind = Vector(torso.shell_point(*chain_path_point(side, max(t - 0.02, 0.0))))
    normal = centre - Vector((0.0, 0.0, up))
    normal.z = 0
    return centre + normal.normalized() * LINK_THICKNESS, normal, ahead - behind


def inventory_link_frame(side, t):
    width, length = INVENTORY_LOOP
    phi = t * math.pi
    z = INVENTORY_CAP_Z + 1.0 + length * (1 - math.cos(phi))
    x = side * width * math.sin(phi)
    dz = length * math.sin(phi)
    dx = side * width * math.cos(phi)
    return Vector((-z, x, INVENTORY_LINK_LIFT)), Vector((0, 0, 1)), Vector((-dz, dx, 0))


def build_chain(frame):
    part = Part("Chain", AMULET_PRIORITY, CHEST_LABELS)
    index = 0
    for side in (1, -1):
        for i in range(LINKS_PER_SIDE):
            t = (i + 0.5) / LINKS_PER_SIDE
            centre, normal, tangent = frame(side, t)
            purple = index % 2 == 1
            link(part, centre, normal, tangent, TOXIC_HSL if purple else SILVER_HSL,
                 TOXIC_DARK_HSL if purple else SILVER_DARK_HSL)
            index += 1
    return part


def facet_rows(part, frame, rows, depth_scale=1.0):
    """Rows of (v, half width, depth) as front-half sections: the outermost points sit on the
    back plane and the rest fan round the front."""
    loops = []
    for v, half, depth in rows:
        loop = []
        for angle in FACET_ANGLES:
            a = math.radians(angle)
            loop.append(part.vert(frame(half * math.sin(a), v, depth * depth_scale * math.cos(a))))
        loops.append(loop)
    return loops


def pendant_faces(part, loops, tip, colors, outward_frame):
    for r, (a, b) in enumerate(zip(loops, loops[1:])):
        for k in range(len(a) - 1):
            part.face((a[k], a[k + 1], b[k + 1], b[k]), colors(r, k), outward=outward_frame)
    for k in range(len(loops[-1]) - 1):
        part.face((loops[-1][k], loops[-1][k + 1], tip), colors(len(loops), k),
                  outward=outward_frame)


def build_pendant(frame):
    """The cap's top is closed; the vial and its fluid are open at the back, where they meet
    the chest."""
    parts = []
    behind = frame(0.0, -6.0, -6.0)

    cap = Part("Cap", AMULET_PRIORITY, CHEST_LABELS)
    loops = facet_rows(cap, frame, CAP)
    for k in range(len(FACET_ANGLES) - 1):
        cap.face((loops[0][k], loops[0][k + 1], loops[1][k + 1], loops[1][k]),
                 SILVER_HSL if k in (1, 2) else SILVER_DARK_HSL, outward=behind)
    top_centre = cap.vert(frame(0.0, CAP[0][0], 0.0))
    for k in range(len(FACET_ANGLES) - 1):
        cap.face((loops[0][k], loops[0][k + 1], top_centre), SILVER_HSL,
                 outward=frame(0.0, -3.0, 0.0))
    parts.append(cap)

    fluid = Part("Fluid", AMULET_PRIORITY, CHEST_LABELS)
    loops = facet_rows(fluid, frame, FLUID, FLUID_DEPTH_SCALE)
    tip = fluid.vert(frame(0.0, FLUID_TIP[0], FLUID_TIP[1]))
    pendant_faces(fluid, loops, tip,
                  lambda r, k: VENOM_HSL if k in (1, 2) else VENOM_DIM_HSL, behind)
    top_centre = fluid.vert(frame(0.0, FLUID[0][0] + 0.4, 0.4))
    for k in range(len(FACET_ANGLES) - 1):
        fluid.face((loops[0][k], loops[0][k + 1], top_centre), VENOM_HSL,
                   outward=frame(0.0, -8.0, 0.0))
    parts.append(fluid)

    glass = Part("Glass", GLASS_PRIORITY, CHEST_LABELS)
    loops = facet_rows(glass, frame, VIAL)
    tip = glass.vert(frame(0.0, VIAL_TIP[0], VIAL_TIP[1]))
    for r, (a, b) in enumerate(zip(loops, loops[1:])):
        for k in range(len(a) - 1):
            glass.face((a[k], a[k + 1], b[k + 1], b[k]), GLASS_HSL, outward=behind,
                       alpha=GLASS_ALPHA)
    for k in range(len(loops[-1]) - 1):
        glass.face((loops[-1][k], loops[-1][k + 1], tip), GLASS_HSL, outward=behind,
                   alpha=GLASS_ALPHA)
    parts.append(glass)
    return parts


def build_all():
    worn = [build_chain(worn_link_frame), *build_pendant(worn_pendant_frame)]
    inventory = [build_chain(inventory_link_frame), *build_pendant(inventory_pendant_frame)]
    rig = wa.Rig(
        male_refs=("rune_platebody_male0", "rune_platebody_male1", "model_28515", "model_26632"),
        female_refs=("rune_platebody_female0", "rune_platebody_female1", "model_18554",
                     "model_3476"),
        male_anchor_refs=(),
        female_anchor_refs=(),
    )
    wa.build_variant("VialAmuletMale", worn, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("VialAmuletFemale", worn, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("VialAmuletInventory", inventory, None, "inventory", lambda p: p)


MODELS = (
    ("VialAmuletInventory", "poison_vial_amulet.dat"),
    ("VialAmuletMale", "poison_vial_amulet_worn.dat"),
    ("VialAmuletFemale", "poison_vial_amulet_worn_female.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], AMULET_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        torso.build_all()
        wa.render_previews(("VialAmuletMale", "CarapaceTorsoMale"), (0, 0, 1.2), args[2],
                           scale=0.55)
        wa.render_previews(("VialAmuletMale",), (0, 0, 1.2), args[2], scale=0.4,
                           views=(("alone_front", (2, 0, 0.3)), ("alone_side", (0.3, -2, 0.3))))
        wa.render_previews(("VialAmuletInventory",), (0, 0, 0.0), args[2], scale=0.6,
                           views=(("top", (0.02, 0, 2)),))
