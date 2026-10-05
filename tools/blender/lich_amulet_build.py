"""Builds the Amulet of the Reaper: a tiny angular skull hanging on five chunky diamond links.

Two bone diamond links run down each side of the neck to a fifth link that holds the
pendant, a small necrotic-green skull with dark sockets. The whole piece floats a little off
the Garb of the Underworld's chest, using the Garb's own surface and female warp, so it hovers
the same way on both bodies. Everything is open at the back, so nothing can show through the
torso from behind, and it draws at priority 7 above the Garb's skulls.

The inventory model is the same piece laid flat and face up, as seen from the front.

Needs the Garb references (see ``lich_garb_build.py``).

Usage:
    blender --background --python tools/blender/lich_amulet_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lich_garb_build as garb  # noqa: E402
import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    BONE_HSL, BONE_SHADOW_HSL, NECROTIC_DIM_HSL, NECROTIC_HSL, SHADOW_HSL, Part,
)

AMULET_PRIORITY = 7
SOCKET_PRIORITY = 8
MAX_TRIANGLES = 200

CHEST_LABELS = frozenset({2, 8, 94})

FLOAT_LIFT = 2.5
CHAIN_PATH = ((40.0, 162.5), (1.0, 152.0))
CHAIN_STOPS = (0.36, 0.84)
LINK_LENGTH = 4.0
LINK_WIDTH = 2.3
LINK_HOLE = 0.42
LINK_THICKNESS = 1.0

PENDANT_TOP = 151.0
BAIL_V = 0.8
SKULL_CRANIUM = ((-1.2, 2.6, 3.6), (-5.6, 2.8, 4.0))
SKULL_CROWN = (0.0, 1.6, 2.6)
SKULL_JAW = ((-5.6, 1.9, 3.2), (-7.8, 1.6, 2.8))
SOCKETS = ((0.4, 2.0), (-2.0, -0.4))
SOCKET_V = (-2.5, -4.4)
NOSE = ((-0.5, -4.8), (0.5, -4.8), (0.0, -5.5))

INVENTORY_LIFT = 1.0
INVENTORY_CENTRE_UP = 166.0


def chest_point(theta, up, lift=FLOAT_LIFT):
    return garb.robe_point(theta, up, lift)


def worn_frame(lateral, v, depth):
    up = PENDANT_TOP + v
    width = garb.lerp_rows(garb.ROBE_RINGS, up)[0]
    theta = math.asin(max(-1.0, min(1.0, lateral / width)))
    fwd, left, _ = chest_point(theta, up)
    return fwd + depth, lateral, up


def inventory_frame(lateral, v, depth):
    return -(PENDANT_TOP + v - INVENTORY_CENTRE_UP), lateral, depth


def diamond_link(part, centre, normal, tangent):
    """A chunky rhombus ring lying on the surface: a front face with a diamond hole and an
    outer rim stepping back, open behind."""
    normal, tangent = Vector(normal).normalized(), Vector(tangent).normalized()
    across = normal.cross(tangent).normalized()
    tangent = across.cross(normal).normalized()
    centre = Vector(centre)
    tips = (tangent * LINK_LENGTH, across * LINK_WIDTH, -tangent * LINK_LENGTH, -across * LINK_WIDTH)
    outer = [part.vert(centre + tip) for tip in tips]
    inner = [part.vert(centre + tip * LINK_HOLE) for tip in tips]
    back = [part.vert(centre + tip - normal * LINK_THICKNESS) for tip in tips]
    behind = centre - normal * 5
    for k in range(4):
        n = (k + 1) % 4
        part.face((outer[k], outer[n], inner[n], inner[k]), BONE_HSL if k < 2 else BONE_SHADOW_HSL,
                  outward=behind)
        part.face((outer[k], back[k], back[n], outer[n]), BONE_SHADOW_HSL, outward=centre)


def chain_point(side, t):
    (a0, u0), (a1, u1) = CHAIN_PATH
    return side * math.radians(a0 + (a1 - a0) * t), u0 + (u1 - u0) * t


def worn_link(side, t):
    theta, up = chain_point(side, t)
    centre = Vector(chest_point(theta, up, FLOAT_LIFT + LINK_THICKNESS))
    ahead = Vector(chest_point(*chain_point(side, min(t + 0.05, 1.0))))
    behind = Vector(chest_point(*chain_point(side, max(t - 0.05, 0.0))))
    normal = centre - Vector((0.0, 0.0, up))
    normal.z = 0
    return centre, normal, ahead - behind


def inventory_link(side, t):
    centre, _, tangent = worn_link(side, t)
    flat = Vector(inventory_frame(centre.y, centre.z - PENDANT_TOP, INVENTORY_LIFT))
    return flat, Vector((0, 0, 1)), Vector((-tangent.z, tangent.y, 0))


def build_chain(link_frame, frame):
    part = Part("Chain", AMULET_PRIORITY, CHEST_LABELS)
    for side in (1, -1):
        for t in CHAIN_STOPS:
            diamond_link(part, *link_frame(side, t))
    bail = Vector(frame(0.0, BAIL_V + LINK_LENGTH * 0.6, LINK_THICKNESS))
    up = Vector(frame(0.0, BAIL_V + LINK_LENGTH * 0.6 + 1.0, LINK_THICKNESS)) - bail
    normal = Vector(frame(0.0, 0.0, 1.0)) - Vector(frame(0.0, 0.0, 0.0))
    diamond_link(part, bail, normal, up)
    return part


def build_skull(frame):
    """An angular skull in local (lateral, v, depth) space: a cranium box whose top is
    chamfered to a crown, a narrower jaw block, and dark sockets and a nose notch on the face.
    Open at the back."""
    skull = Part("Skull", AMULET_PRIORITY, CHEST_LABELS)
    behind = frame(0.0, -4.0, -6.0)

    def ring(v, half, depth):
        return [skull.vert(frame(l, v, d)) for l, d in ((-half, 0.0), (-half, depth),
                                                         (half, depth), (half, 0.0))]

    crown_v, crown_half, crown_depth = SKULL_CROWN
    loops = [ring(crown_v, crown_half, crown_depth)] + [ring(*row) for row in SKULL_CRANIUM]
    loops += [ring(*row) for row in SKULL_JAW]
    colors = (NECROTIC_DIM_HSL, NECROTIC_HSL, NECROTIC_DIM_HSL)
    for r, (a, b) in enumerate(zip(loops, loops[1:])):
        for k in range(3):
            face = (a[k], a[k + 1], b[k + 1], b[k])
            skull.face(face, colors[k], outward=behind, emissive=True)
    top = loops[0]
    skull.face((top[0], top[1], top[2], top[3]), NECROTIC_HSL, outward=frame(0.0, -6.0, 0.5),
               emissive=True)
    bottom = loops[-1]
    skull.face((bottom[0], bottom[1], bottom[2], bottom[3]), NECROTIC_DIM_HSL,
               outward=frame(0.0, 0.0, 0.5), emissive=True)

    face = Part("SkullFace", SOCKET_PRIORITY, CHEST_LABELS)
    front = SKULL_CRANIUM[0][2] + 0.15
    low, high = SOCKET_V
    for l0, l1 in SOCKETS:
        quad = [face.vert(frame(l, v, front - (v - SKULL_CRANIUM[0][0]) * 0.09))
                for l, v in ((l0, low), (l1, low), (l1, high), (l0, high))]
        face.face(tuple(quad), SHADOW_HSL, outward=behind)
    nose = [face.vert(frame(l, v, front - (v - SKULL_CRANIUM[0][0]) * 0.09)) for l, v in NOSE]
    face.face(tuple(nose), SHADOW_HSL, outward=behind)
    return [skull, face]


def build_all():
    worn = [build_chain(worn_link, worn_frame), *build_skull(worn_frame)]
    inventory = [build_chain(inventory_link, inventory_frame), *build_skull(inventory_frame)]
    rig = wa.Rig(
        male_refs=("rune_platebody_male0", "rune_platebody_male1", "model_28515", "model_26632"),
        female_refs=("rune_platebody_female0", "rune_platebody_female1", "model_18554",
                     "model_3476"),
        male_anchor_refs=(),
        female_anchor_refs=(),
    )
    wa.build_variant("ReaperAmuletMale", worn, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("ReaperAmuletFemale", worn, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("ReaperAmuletInventory", inventory, None, "inventory",
                     wa.grounded(lambda p: p, inventory))


MODELS = (
    ("ReaperAmuletInventory", "lich_amulet.dat"),
    ("ReaperAmuletMale", "lich_amulet_worn.dat"),
    ("ReaperAmuletFemale", "lich_amulet_worn_female.dat"),
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
        garb.build_all()
        wa.render_previews(("ReaperAmuletMale", "LichGarbMale"), (0, 0, 1.22), args[2],
                           scale=0.5, views=(("front", (2, 0, 0.3)),
                                             ("three_quarter", (1.4, -1.4, 0.6))))
        wa.render_previews(("ReaperAmuletMale",), (0.1, 0, 1.2), args[2], scale=0.3,
                           views=(("alone", (2, -0.6, 0.3)),))
        wa.render_previews(("ReaperAmuletInventory",), (0, 0, 0.0), args[2], scale=0.4,
                           views=(("top", (0.02, 0, 2)),))
