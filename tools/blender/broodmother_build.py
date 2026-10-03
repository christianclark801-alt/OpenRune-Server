"""Builds the Broodmother boss model: a bloated low-poly tick/spider queen facing +X.

Scale is 1 Blender unit = 1 tile. Every part gets an ``rs_color`` face attribute (OSRS
16-bit HSL) for ``osrs_model_export.py``; viewport materials are derived from the same HSL.

Usage:
    blender --background --python tools/blender/broodmother_build.py -- [out.blend] [out.dat]
or paste/run inside a live Blender session (no arguments needed).
"""

import colorsys
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

COLLECTION = "Broodmother"

BODY_RADIUS = 1.2
BODY_STRETCH_X = 1.5
BODY_CENTER = Vector((0.0, 0.0, 1.55))

LEG_SIDES = 6
LEG_UPPER_RADIUS = 0.22
LEG_LOWER_RADIUS = 0.17
LEG_ROOTS_X = (1.0, 0.35, -0.35, -1.0)
LEG_SPLAY_X = (0.45, 0.15, -0.15, -0.45)

SAC_RADIUS = 0.9
SAC_CENTER = Vector((-0.6, 0.0, 0.7))
SAC_PULSE_SCALE = 1.12
SAC_PULSE_FRAMES = 24

MOUTH_INSET = 0.12
MOUTH_DEPTH = 0.35

FANG_LENGTH = 0.6
FANG_RADIUS = 0.11


def hsl(hue, saturation, lightness):
    return (hue << 10) | (saturation << 7) | lightness


BODY_HSL = hsl(3, 4, 30)
BODY_SPOT_HSL = hsl(4, 5, 38)
LEG_HSL = hsl(5, 2, 16)
SAC_HSL = hsl(18, 6, 70)
SAC_VEIN_HSL = hsl(20, 5, 52)
MOUTH_HSL = hsl(0, 5, 8)
FANG_HSL = hsl(8, 1, 110)


def hsl_to_rgba(value):
    hue = ((value >> 10) & 63) / 64 + 1 / 128
    saturation = ((value >> 7) & 7) / 8 + 1 / 16
    lightness = (value & 127) / 128
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (r, g, b, 1.0)


def material_for(value):
    name = f"rs_{value}"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if not material.node_tree:
        material.use_nodes = True
    rgba = hsl_to_rgba(value)
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = rgba
    material.diffuse_color = rgba
    return material


def reset_collection():
    existing = bpy.data.collections.get(COLLECTION)
    if existing is not None:
        for obj in list(existing.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(existing)
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def link(obj, collection, name):
    obj.name = name
    obj.data.name = name
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def paint(obj, colors_by_face):
    """colors_by_face: one HSL value per polygon; also builds matching viewport materials."""
    mesh = obj.data
    attribute = mesh.attributes.get("rs_color") or mesh.attributes.new(
        "rs_color", "INT", "FACE"
    )
    palette = []
    for polygon, value in zip(mesh.polygons, colors_by_face):
        attribute.data[polygon.index].value = value
        if value not in palette:
            palette.append(value)
            mesh.materials.append(material_for(value))
        polygon.material_index = palette.index(value)


def apply_transform(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def build_body(collection):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12, ring_count=8, radius=BODY_RADIUS, location=BODY_CENTER,
        rotation=(0.0, math.radians(90), 0.0),
    )
    body = link(bpy.context.active_object, collection, "Broodmother_Body")
    apply_transform(body)
    body.scale = (BODY_STRETCH_X, 1.0, 1.0)
    apply_transform(body)

    bm = bmesh.new()
    bm.from_mesh(body.data)
    front_tip = max(bm.verts, key=lambda v: v.co.x)
    mouth_faces = list(front_tip.link_faces)
    inset = bmesh.ops.inset_region(bm, faces=mouth_faces, thickness=MOUTH_INSET, depth=0.0)
    mouth_set = set(mouth_faces)
    mouth_verts = {v for f in mouth_faces for v in f.verts}
    for vert in mouth_verts:
        vert.co.x -= MOUTH_DEPTH
    rim_faces = set(inset["faces"])
    bm.faces.ensure_lookup_table()

    rng = random.Random(7)
    colors = []
    for face in bm.faces:
        if face in mouth_set:
            colors.append(MOUTH_HSL)
        elif face in rim_faces:
            colors.append(LEG_HSL)
        else:
            colors.append(BODY_SPOT_HSL if rng.random() < 0.18 else BODY_HSL)
    bm.to_mesh(body.data)
    bm.free()
    paint(body, colors)
    return body


def cylinder_between(collection, name, start, end, radius):
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=LEG_SIDES, radius=radius, depth=direction.length,
        location=(start + end) / 2,
    )
    obj = link(bpy.context.active_object, collection, name)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    apply_transform(obj)
    paint(obj, [LEG_HSL] * len(obj.data.polygons))
    return obj


def build_legs(collection):
    legs = []
    for side in (1, -1):
        for index, (root_x, splay_x) in enumerate(zip(LEG_ROOTS_X, LEG_SPLAY_X)):
            root = Vector((root_x, side * 0.95, 1.3))
            knee = Vector((root_x + splay_x, side * 1.65, 1.75))
            foot = Vector((root_x + splay_x * 1.6, side * 2.05, 0.0))
            tag = f"{'L' if side > 0 else 'R'}{index + 1}"
            legs.append(cylinder_between(
                collection, f"Broodmother_Leg_{tag}_Upper", root, knee, LEG_UPPER_RADIUS))
            legs.append(cylinder_between(
                collection, f"Broodmother_Leg_{tag}_Lower", knee, foot, LEG_LOWER_RADIUS))
    return legs


def build_sac(collection):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=SAC_RADIUS, location=SAC_CENTER,
    )
    sac = link(bpy.context.active_object, collection, "Broodmother_PoisonSac")
    sac.scale = (1.3, 1.05, 0.75)
    rng = random.Random(11)
    paint(sac, [SAC_VEIN_HSL if rng.random() < 0.25 else SAC_HSL
                for _ in sac.data.polygons])

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = SAC_PULSE_FRAMES
    base = sac.scale.copy()
    for frame, factor in ((1, 1.0), (SAC_PULSE_FRAMES // 2 + 1, SAC_PULSE_SCALE),
                          (SAC_PULSE_FRAMES + 1, 1.0)):
        sac.scale = base * factor
        sac.keyframe_insert(data_path="scale", frame=frame)
    sac.scale = base
    for curve in action_fcurves(sac):
        curve.modifiers.new(type="CYCLES")
    return sac


def action_fcurves(obj):
    animation = obj.animation_data
    if animation is None or animation.action is None:
        return []
    action = animation.action
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    from bpy_extras import anim_utils

    channelbag = anim_utils.action_get_channelbag_for_slot(action, animation.action_slot)
    return list(channelbag.fcurves) if channelbag else []


def build_fangs(collection):
    mouth_x = BODY_CENTER.x + BODY_RADIUS * BODY_STRETCH_X - MOUTH_DEPTH
    fangs = []
    for side in (1, -1):
        root = Vector((mouth_x + 0.15, side * 0.28, BODY_CENTER.z - 0.25))
        tip = root + Vector((0.25, -side * 0.08, -FANG_LENGTH))
        direction = tip - root
        bpy.ops.mesh.primitive_cone_add(
            vertices=4, radius1=FANG_RADIUS, radius2=0.0, depth=direction.length,
            location=(root + tip) / 2,
        )
        fang = link(bpy.context.active_object, collection,
                    f"Broodmother_Fang_{'L' if side > 0 else 'R'}")
        fang.rotation_mode = "QUATERNION"
        fang.rotation_quaternion = direction.to_track_quat("Z", "Y")
        apply_transform(fang)
        paint(fang, [FANG_HSL] * len(fang.data.polygons))
        fangs.append(fang)
    return fangs


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    collection = reset_collection()
    build_body(collection)
    build_legs(collection)
    build_sac(collection)
    build_fangs(collection)
    bpy.context.scene.frame_set(1)
    faces = sum(len(o.data.polygons) for o in collection.all_objects)
    print(f"Built {COLLECTION}: {len(collection.all_objects)} objects, {faces} faces")
    return collection


if __name__ == "__main__":
    build()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 1:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import osrs_model_export

        osrs_model_export.export_collection(COLLECTION, os.path.abspath(args[1]))
