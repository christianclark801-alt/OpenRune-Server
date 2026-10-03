"""Builds the Broodmother boss model: a bloated low-poly tick/spider queen facing +X.

Scale is 1 Blender unit = 1 tile. Every part gets an ``rs_color`` face attribute (OSRS
16-bit HSL) and an ``rs_label`` vertex label for ``osrs_model_export.py``; the glow shells
also carry ``rs_alpha`` and ``rs_flabel`` so animations can pulse them. Viewport materials
are derived from the same HSL.

Usage:
    blender --background --python tools/blender/broodmother_build.py -- [out.blend] [out.dat]
or paste/run inside a live Blender session (no arguments needed). Exporting the .dat also
writes the animations next to it (see ``broodmother_anims.py``).
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
SAC_SCALE = (1.3, 1.05, 0.75)
SAC_GLOW_GROWTH = 1.12
SAC_GLOW_ALPHA = 170

MOUTH_INSET = 0.12
MOUTH_DEPTH = 0.35

FANG_LENGTH = 0.6
FANG_RADIUS = 0.11
FANG_GLOW_GROWTH = 1.9
FANG_GLOW_ALPHA = 185

LABEL_BODY = 0
LABEL_SAC = 1
LABEL_SAC_GLOW = 2
LABEL_FANGS = 3
LABEL_FANG_GLOW = 4
LABEL_LEG_FIRST = 10
LABEL_HIP_FIRST = 20
FACE_LABEL_SAC_GLOW = 1
FACE_LABEL_FANG_GLOW = 2


def hsl(hue, saturation, lightness):
    return (hue << 10) | (saturation << 7) | lightness


BODY_HSL = hsl(3, 4, 30)
BODY_SPOT_HSL = hsl(4, 5, 38)
LEG_HSL = hsl(5, 2, 16)
SAC_HSL = hsl(18, 6, 70)
SAC_VEIN_HSL = hsl(20, 5, 52)
MOUTH_HSL = hsl(0, 5, 8)
FANG_HSL = hsl(8, 1, 110)
SAC_GLOW_HSL = hsl(19, 7, 100)
FANG_GLOW_HSL = hsl(19, 7, 96)


def hsl_to_rgba(value):
    hue = ((value >> 10) & 63) / 64 + 1 / 128
    saturation = ((value >> 7) & 7) / 8 + 1 / 16
    lightness = (value & 127) / 128
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (r, g, b, 1.0)


def material_for(value, alpha=0):
    name = f"rs_{value}_{alpha}"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if not material.node_tree:
        material.use_nodes = True
    rgba = hsl_to_rgba(value)[:3] + (1.0 - alpha / 255,)
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


def int_attribute(mesh, name, domain, values):
    attribute = mesh.attributes.get(name) or mesh.attributes.new(name, "INT", domain)
    for index, value in enumerate(values):
        attribute.data[index].value = value


def paint(obj, colors_by_face, label, alpha=0, face_label=0):
    """colors_by_face: one HSL value per polygon; also builds matching viewport materials."""
    mesh = obj.data
    int_attribute(mesh, "rs_color", "FACE", colors_by_face)
    int_attribute(mesh, "rs_label", "POINT", [label] * len(mesh.vertices))
    if alpha:
        int_attribute(mesh, "rs_alpha", "FACE", [alpha] * len(mesh.polygons))
    if face_label:
        int_attribute(mesh, "rs_flabel", "FACE", [face_label] * len(mesh.polygons))
    palette = []
    for polygon, value in zip(mesh.polygons, colors_by_face):
        if value not in palette:
            palette.append(value)
            mesh.materials.append(material_for(value, alpha))
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
    paint(body, colors, LABEL_BODY)
    return body


def cylinder_between(collection, name, start, end, radius, label):
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=LEG_SIDES, radius=radius, depth=direction.length,
        location=(start + end) / 2,
    )
    obj = link(bpy.context.active_object, collection, name)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    apply_transform(obj)
    paint(obj, [LEG_HSL] * len(obj.data.polygons), label)
    return obj


def build_legs(collection):
    legs = []
    for side in (1, -1):
        for index, (root_x, splay_x) in enumerate(zip(LEG_ROOTS_X, LEG_SPLAY_X)):
            root = Vector((root_x, side * 0.95, 1.3))
            knee = Vector((root_x + splay_x, side * 1.65, 1.75))
            foot = Vector((root_x + splay_x * 1.6, side * 2.05, 0.0))
            tag = f"{'L' if side > 0 else 'R'}{index + 1}"
            leg = (0 if side > 0 else 4) + index
            upper = cylinder_between(collection, f"Broodmother_Leg_{tag}_Upper", root, knee,
                                     LEG_UPPER_RADIUS, LABEL_LEG_FIRST + leg)
            lower = cylinder_between(collection, f"Broodmother_Leg_{tag}_Lower", knee, foot,
                                     LEG_LOWER_RADIUS, LABEL_LEG_FIRST + leg)
            label_hip_ring(upper, root, LABEL_HIP_FIRST + leg)
            legs += [upper, lower]
    return legs


def label_hip_ring(upper, root, hip_label):
    """The ring at the leg root becomes the leg's rotation pivot."""
    labels = upper.data.attributes["rs_label"]
    for vertex in upper.data.vertices:
        if (upper.matrix_world @ vertex.co - root).length < LEG_UPPER_RADIUS * 1.5:
            labels.data[vertex.index].value = hip_label


def build_sac(collection):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=SAC_RADIUS, location=SAC_CENTER,
    )
    sac = link(bpy.context.active_object, collection, "Broodmother_PoisonSac")
    sac.scale = SAC_SCALE
    apply_transform(sac)
    rng = random.Random(11)
    paint(sac, [SAC_VEIN_HSL if rng.random() < 0.25 else SAC_HSL
                for _ in sac.data.polygons], LABEL_SAC)

    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=SAC_RADIUS * SAC_GLOW_GROWTH, location=SAC_CENTER,
    )
    glow = link(bpy.context.active_object, collection, "Broodmother_PoisonSac_Glow")
    glow.scale = SAC_SCALE
    apply_transform(glow)
    paint(glow, [SAC_GLOW_HSL] * len(glow.data.polygons), LABEL_SAC_GLOW,
          alpha=SAC_GLOW_ALPHA, face_label=FACE_LABEL_SAC_GLOW)
    return sac


def build_fangs(collection):
    mouth_x = BODY_CENTER.x + BODY_RADIUS * BODY_STRETCH_X - MOUTH_DEPTH
    fangs = []
    for side in (1, -1):
        root = Vector((mouth_x + 0.15, side * 0.28, BODY_CENTER.z - 0.25))
        tip = root + Vector((0.25, -side * 0.08, -FANG_LENGTH))
        tag = "L" if side > 0 else "R"
        fangs.append(cone_between(collection, f"Broodmother_Fang_{tag}", root, tip,
                                  FANG_RADIUS, 1.0))
        paint(fangs[-1], [FANG_HSL] * len(fangs[-1].data.polygons), LABEL_FANGS)
        glow = cone_between(collection, f"Broodmother_Fang_{tag}_Glow", root, tip,
                            FANG_RADIUS * FANG_GLOW_GROWTH, 1.15)
        paint(glow, [FANG_GLOW_HSL] * len(glow.data.polygons), LABEL_FANG_GLOW,
              alpha=FANG_GLOW_ALPHA, face_label=FACE_LABEL_FANG_GLOW)
    return fangs


def cone_between(collection, name, root, tip, radius, length_factor):
    direction = tip - root
    bpy.ops.mesh.primitive_cone_add(
        vertices=4, radius1=radius, radius2=0.0, depth=direction.length * length_factor,
        location=root + direction * (length_factor / 2),
    )
    cone = link(bpy.context.active_object, collection, name)
    cone.rotation_mode = "QUATERNION"
    cone.rotation_quaternion = direction.to_track_quat("Z", "Y")
    apply_transform(cone)
    return cone


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
        import broodmother_anims
        import osrs_model_export

        dat_path = os.path.abspath(args[1])
        model = osrs_model_export.export_collection(COLLECTION, dat_path)
        broodmother_anims.generate(model, os.path.dirname(os.path.dirname(dat_path)))
