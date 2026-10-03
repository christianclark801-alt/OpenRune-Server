"""Builds the Broodmother boss model: a low-poly spider queen facing +X, with an armoured
cephalothorax, a lumpy sagging poison abdomen with egg sacs, jointed spiked legs and a face
of eight eyes, chelicerae fangs and mandibles.

Scale is 1 Blender unit = 1 tile. Every part gets an ``rs_color`` face attribute (OSRS
16-bit HSL) and an ``rs_label`` vertex label for ``osrs_model_export.py``; the glow shells
also carry ``rs_alpha`` and ``rs_flabel`` so animations can pulse them. Viewport materials
are derived from the same HSL. Parts are smooth shaded with a 40 degree Edge Split, and the
.dat is exported unwelded so those hard edges survive the client's per-vertex smoothing.

Usage:
    blender --background --python tools/blender/broodmother_build.py -- [out.blend] [out.dat] [out.obj]
or paste/run inside a live Blender session (no arguments needed). Exporting the .dat also
writes the animations next to it (see ``broodmother_anims.py``) and the OBJ to ``OBJ_PATH``
unless a third argument overrides it.
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
OBJ_PATH = "C:/RSPS_Models/broodmother_smooth.obj"
MAX_TRIANGLES = 3800

CEPH_HALF = 0.55
CEPH_SCALE = (1.2, 1.0, 0.8)
CEPH_CENTER = Vector((0.55, 0.0, 1.25))
CEPH_CUTS_X = (-0.33, 0.33)
CEPH_RIDGE_GROWTH = 1.1
CEPH_FRONT_TAPER = 0.78
CEPH_BEVEL_WIDTH = 0.1
CEPH_BEVEL_SEGMENTS = 3
CEPH_BEVEL_ANGLE = 30

ABDOMEN_RADIUS = CEPH_HALF * 1.8
ABDOMEN_CENTER = Vector((-1.0, 0.0, 1.5))
ABDOMEN_SCALE = (1.1, 0.9, 0.8)
ABDOMEN_SEGMENTS = 16
ABDOMEN_RINGS = 32
ABDOMEN_GLOW_SEGMENTS = 10
ABDOMEN_GLOW_RINGS = 8
ABDOMEN_SAG = 0.3
ABDOMEN_SAG_BACK = 0.15
ABDOMEN_ASYMMETRY = 1.1
ABDOMEN_LUMP_STRENGTH = 0.15
ABDOMEN_LUMP_SIZE = 0.35
ABDOMEN_VEIN_CELL = 0.3
SAC_GLOW_GROWTH = 1.15
SAC_GLOW_ALPHA = 215

EGG_SACS = ((-0.35, 0.4, 0.27), (0.1, -0.35, 0.21), (-0.75, -0.15, 0.16))
EGG_SINK = 0.45
EGG_SEGMENTS = 10
EGG_RINGS = 6

LEG_SIDES = 12
JOINT_SEGMENTS = 8
JOINT_RINGS = 4
FEMUR_RADIUS = 0.13
TIBIA_RADIUS = 0.1
TARSUS_RADIUS = 0.07
KNEE_RADIUS = 0.16
ANKLE_RADIUS = 0.12
LEG_ROOTS_X = (1.0, 0.7, 0.4, 0.1)
LEG_SPLAY_X = (0.55, 0.2, -0.2, -0.55)
LEG_ROOT_Y = 0.36
LEG_ROOT_Z = 1.2
FEMUR_REACH = Vector((1.0, 0.7, 0.6))
TIBIA_REACH = Vector((0.6, 0.5, -1.5))
TARSUS_REACH = Vector((0.6, 0.4, -0.25))
SPIKES_ALONG_FEMUR = (0.3, 0.55, 0.8)
SPIKE_LENGTH = 0.17
SPIKE_RADIUS = 0.035

FACE_X = CEPH_CENTER.x + CEPH_HALF * CEPH_SCALE[0]
FANG_ROOT = Vector((FACE_X - 0.05, 0.17, 1.0))
FANG_REACH = Vector((0.3, -0.05, -0.75))
FANG_RADIUS = 0.09
FANG_GLOW_GROWTH = 1.9
FANG_GLOW_ALPHA = 185
FANG_SIDES = 12

EYE_ROWS = (
    (0.045, 1.52, (0.08, 0.22)),
    (0.075, 1.36, (0.1, 0.28)),
)
EYE_SEGMENTS = 8
EYE_RINGS = 4

MANDIBLE_SIZE = 0.13
MANDIBLE_CENTER = Vector((FACE_X + 0.04, 0.13, 1.12))
MANDIBLE_TIP_TAPER = 0.25

EDGE_SPLIT_ANGLE = 40

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
PLATE_HSL = hsl(3, 4, 20)
LEG_HSL = hsl(5, 2, 16)
JOINT_HSL = hsl(4, 3, 24)
SPIKE_HSL = hsl(5, 1, 8)
ABDOMEN_HSL = hsl(50, 4, 34)
ABDOMEN_VEIN_HSL = hsl(52, 5, 48)
EGG_HSL = hsl(10, 2, 95)
EYE_HSL = hsl(0, 0, 4)
MANDIBLE_HSL = hsl(4, 3, 14)
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
    mesh.materials.clear()
    palette = []
    for polygon, value in zip(mesh.polygons, colors_by_face):
        if value not in palette:
            palette.append(value)
            mesh.materials.append(material_for(value, alpha))
        polygon.material_index = palette.index(value)


def paint_solid(obj, value, label):
    paint(obj, [value] * len(obj.data.polygons), label)


def apply_transform(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def apply_modifier(obj, modifier):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def edit_mesh(obj, edit):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = edit(bm)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return result


def build_cephalothorax(collection):
    bpy.ops.mesh.primitive_cube_add(size=CEPH_HALF * 2, location=CEPH_CENTER)
    ceph = link(bpy.context.active_object, collection, "Broodmother_Cephalothorax")

    def armour(bm):
        cut_verts = set()
        for x in CEPH_CUTS_X:
            cut = bmesh.ops.bisect_plane(
                bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                plane_co=(x * CEPH_HALF, 0, 0), plane_no=(1, 0, 0),
            )
            cut_verts |= {g for g in cut["geom_cut"] if isinstance(g, bmesh.types.BMVert)}
        bmesh.ops.bisect_plane(
            bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 1, 0),
        )
        for vert in cut_verts:
            vert.co.y *= CEPH_RIDGE_GROWTH
            vert.co.z *= CEPH_RIDGE_GROWTH
        for vert in bm.verts:
            if vert.co.x > 0:
                vert.co.y *= CEPH_FRONT_TAPER
                vert.co.z *= CEPH_FRONT_TAPER
            vert.co = Vector(c * s for c, s in zip(vert.co, CEPH_SCALE))

    def band(x):
        return sum(1 for cut in CEPH_CUTS_X if x > cut * CEPH_HALF * CEPH_SCALE[0])

    edit_mesh(ceph, armour)
    bevel = ceph.modifiers.new("Rounding", "BEVEL")
    bevel.width = CEPH_BEVEL_WIDTH
    bevel.segments = CEPH_BEVEL_SEGMENTS
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(CEPH_BEVEL_ANGLE)
    apply_modifier(ceph, bevel)
    paint(ceph, [PLATE_HSL if band(p.center.x) % 2 else BODY_HSL for p in ceph.data.polygons],
          LABEL_BODY)
    return ceph


def build_abdomen(collection):
    abdomen = sac_sphere(collection, "Broodmother_Abdomen", ABDOMEN_SEGMENTS, ABDOMEN_RINGS, 1.0)

    texture = bpy.data.textures.get("Broodmother_Lumps") or bpy.data.textures.new(
        "Broodmother_Lumps", type="CLOUDS"
    )
    texture.noise_scale = ABDOMEN_LUMP_SIZE
    displace = abdomen.modifiers.new("Lumps", "DISPLACE")
    displace.texture = texture
    displace.strength = ABDOMEN_LUMP_STRENGTH
    apply_modifier(abdomen, displace)
    paint_abdomen(abdomen)

    glow = sac_sphere(collection, "Broodmother_Abdomen_Glow", ABDOMEN_GLOW_SEGMENTS,
                      ABDOMEN_GLOW_RINGS, SAC_GLOW_GROWTH)
    paint_glow(glow)
    return abdomen, glow


def sac_sphere(collection, name, segments, rings, growth):
    """A sagging, lopsided sphere; the abdomen and its glow shell share this shape."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=ABDOMEN_RADIUS, location=ABDOMEN_CENTER,
    )
    sac = link(bpy.context.active_object, collection, name)

    def shape(bm):
        for vert in bm.verts:
            vert.co = Vector(c * s for c, s in zip(vert.co, ABDOMEN_SCALE))
            low = max(0.0, -vert.co.z / (ABDOMEN_RADIUS * ABDOMEN_SCALE[2]))
            vert.co.z -= ABDOMEN_SAG * low * low
            vert.co.x -= ABDOMEN_SAG_BACK * low
            if vert.co.y > 0:
                vert.co.y *= ABDOMEN_ASYMMETRY
            vert.co *= growth

    edit_mesh(sac, shape)
    return sac


def paint_abdomen(abdomen):
    """Veins are picked per spatial cell rather than per face, so the thin rings of a UV sphere
    form blotches instead of stripes."""
    veined = {}
    colors = []
    for polygon in abdomen.data.polygons:
        cell = tuple(math.floor(c / ABDOMEN_VEIN_CELL) for c in polygon.center)
        if cell not in veined:
            veined[cell] = random.Random(hash(cell) ^ 11).random() < 0.25
        colors.append(ABDOMEN_VEIN_HSL if veined[cell] else ABDOMEN_HSL)
    paint(abdomen, colors, LABEL_SAC)


def paint_glow(glow):
    paint(glow, [SAC_GLOW_HSL] * len(glow.data.polygons), LABEL_SAC_GLOW,
          alpha=SAC_GLOW_ALPHA, face_label=FACE_LABEL_SAC_GLOW)


def build_egg_sacs(collection, abdomen):
    world = [abdomen.matrix_world @ v.co for v in abdomen.data.vertices]
    sacs = []
    for index, (dx, dy, radius) in enumerate(EGG_SACS):
        x, y = ABDOMEN_CENTER.x + dx, ABDOMEN_CENTER.y + dy
        nearby = [p for p in world if (p.x - x) ** 2 + (p.y - y) ** 2 < 0.3 ** 2]
        underside = min(p.z for p in nearby)
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=EGG_SEGMENTS, ring_count=EGG_RINGS, radius=radius,
            location=(x, y, underside + radius * EGG_SINK),
        )
        sac = link(bpy.context.active_object, collection, f"Broodmother_EggSac_{index + 1}")
        paint_solid(sac, EGG_HSL, LABEL_SAC)
        sacs.append(sac)
    return sacs


def cylinder_between(collection, name, start, end, radius, label, capped=True):
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=LEG_SIDES, radius=radius, depth=direction.length,
        location=(start + end) / 2, end_fill_type="NGON" if capped else "NOTHING",
    )
    obj = link(bpy.context.active_object, collection, name)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    apply_transform(obj)
    paint_solid(obj, LEG_HSL, label)
    return obj


def joint(collection, name, at, radius, label):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=JOINT_SEGMENTS, ring_count=JOINT_RINGS, radius=radius, location=at,
    )
    obj = link(bpy.context.active_object, collection, name)
    paint_solid(obj, JOINT_HSL, label)
    return obj


def build_legs(collection):
    legs = []
    for side in (1, -1):
        for index, (root_x, splay_x) in enumerate(zip(LEG_ROOTS_X, LEG_SPLAY_X)):
            mirror = Vector((1, side, 1))
            splay = Vector((splay_x, 1, 1))
            root = Vector((root_x, side * LEG_ROOT_Y, LEG_ROOT_Z))
            knee = root + scaled(FEMUR_REACH, splay, mirror)
            ankle = knee + scaled(TIBIA_REACH, splay, mirror)
            foot = ankle + scaled(TARSUS_REACH, splay, mirror)
            tag = f"{'L' if side > 0 else 'R'}{index + 1}"
            leg = (0 if side > 0 else 4) + index
            label = LABEL_LEG_FIRST + leg
            prefix = f"Broodmother_Leg_{tag}"
            femur = cylinder_between(collection, f"{prefix}_Femur", root, knee, FEMUR_RADIUS, label)
            tibia = cylinder_between(collection, f"{prefix}_Tibia", knee, ankle, TIBIA_RADIUS, label,
                                     capped=False)
            tarsus = cone_between(collection, f"{prefix}_Tarsus", ankle, foot, TARSUS_RADIUS, 1.0,
                                  sides=LEG_SIDES, capped=False)
            paint_solid(tarsus, LEG_HSL, label)
            joints = [
                joint(collection, f"{prefix}_Knee", knee, KNEE_RADIUS, label),
                joint(collection, f"{prefix}_Ankle", ankle, ANKLE_RADIUS, label),
            ]
            spikes = build_spikes(collection, prefix, root, knee, side, label)
            label_hip_ring(femur, root, LABEL_HIP_FIRST + leg)
            legs += [femur, tibia, tarsus, *joints, *spikes]
    return legs


def scaled(reach, splay, mirror):
    return Vector((splay.x * reach.x, mirror.y * reach.y, reach.z))


def build_spikes(collection, prefix, root, knee, side, label):
    femur = knee - root
    outward = Vector((0, side, 1)).normalized()
    outward = (outward - femur.normalized() * outward.dot(femur.normalized())).normalized()
    spikes = []
    for index, along in enumerate(SPIKES_ALONG_FEMUR):
        base = root + femur * along + outward * FEMUR_RADIUS * 0.6
        tip = base + outward * SPIKE_LENGTH
        spike = cone_between(collection, f"{prefix}_Spike_{index + 1}", base, tip, SPIKE_RADIUS, 1.0)
        paint_solid(spike, SPIKE_HSL, label)
        spikes.append(spike)
    return spikes


def label_hip_ring(femur, root, hip_label):
    """The ring at the leg root becomes the leg's rotation pivot."""
    labels = femur.data.attributes["rs_label"]
    for vertex in femur.data.vertices:
        if (femur.matrix_world @ vertex.co - root).length < FEMUR_RADIUS * 1.5:
            labels.data[vertex.index].value = hip_label


def build_fangs(collection):
    fangs = []
    for side in (1, -1):
        mirror = Vector((1, side, 1))
        root = FANG_ROOT * 1
        root.y *= side
        tip = root + Vector(c * m for c, m in zip(FANG_REACH, mirror))
        tag = "L" if side > 0 else "R"
        fangs.append(cone_between(collection, f"Broodmother_Fang_{tag}", root, tip,
                                  FANG_RADIUS, 1.0, sides=FANG_SIDES))
        paint_solid(fangs[-1], FANG_HSL, LABEL_FANGS)
        glow = cone_between(collection, f"Broodmother_Fang_{tag}_Glow", root, tip,
                            FANG_RADIUS * FANG_GLOW_GROWTH, 1.15, sides=FANG_SIDES)
        paint(glow, [FANG_GLOW_HSL] * len(glow.data.polygons), LABEL_FANG_GLOW,
              alpha=FANG_GLOW_ALPHA, face_label=FACE_LABEL_FANG_GLOW)
    return fangs


def cone_between(collection, name, root, tip, radius, length_factor, sides=4, capped=True):
    direction = tip - root
    bpy.ops.mesh.primitive_cone_add(
        vertices=sides, radius1=radius, radius2=0.0, depth=direction.length * length_factor,
        location=root + direction * (length_factor / 2),
        end_fill_type="NGON" if capped else "NOTHING",
    )
    cone = link(bpy.context.active_object, collection, name)
    cone.rotation_mode = "QUATERNION"
    cone.rotation_quaternion = direction.to_track_quat("Z", "Y")
    apply_transform(cone)
    return cone


def build_eyes(collection):
    eyes = []
    for row, (radius, z, offsets) in enumerate(EYE_ROWS):
        for offset in offsets:
            for side in (1, -1):
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=EYE_SEGMENTS, ring_count=EYE_RINGS, radius=radius,
                    location=(FACE_X - radius * 0.3, side * offset, z),
                )
                eye = link(bpy.context.active_object, collection,
                           f"Broodmother_Eye_{row + 1}_{len(eyes) + 1}")
                paint_solid(eye, EYE_HSL, LABEL_BODY)
                eyes.append(eye)
    return eyes


def build_mandibles(collection):
    mandibles = []
    for side in (1, -1):
        center = MANDIBLE_CENTER * 1
        center.y *= side
        bpy.ops.mesh.primitive_cube_add(size=MANDIBLE_SIZE, location=center)
        mandible = link(bpy.context.active_object, collection,
                        f"Broodmother_Mandible_{'L' if side > 0 else 'R'}")

        def taper(bm):
            for vert in bm.verts:
                if vert.co.x > 0:
                    vert.co.x += MANDIBLE_SIZE * 0.6
                    vert.co.y = vert.co.y * MANDIBLE_TIP_TAPER - side * MANDIBLE_SIZE * 0.3
                    vert.co.z *= MANDIBLE_TIP_TAPER

        edit_mesh(mandible, taper)
        paint_solid(mandible, MANDIBLE_HSL, LABEL_BODY)
        mandibles.append(mandible)
    return mandibles


def triangles(objects):
    total = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def fit_budget(collection, abdomen, glow):
    """Decimates the abdomen (and its glow shell) until the whole model fits MAX_TRIANGLES."""
    total = triangles(collection.all_objects)
    if total <= MAX_TRIANGLES:
        return total
    own = triangles([abdomen, glow])
    ratio = max(0.1, 1 - (total - MAX_TRIANGLES) / own)
    for obj, repaint in ((abdomen, paint_abdomen), (glow, paint_glow)):
        decimate = obj.modifiers.new("Budget", "DECIMATE")
        decimate.ratio = ratio
        apply_modifier(obj, decimate)
        repaint(obj)
    return triangles(collection.all_objects)


def finish(collection):
    meshes = [o for o in collection.all_objects if o.type == "MESH"]
    for obj in meshes:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        split = obj.modifiers.new("HardEdges", "EDGE_SPLIT")
        split.split_angle = math.radians(EDGE_SPLIT_ANGLE)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    collection = reset_collection()
    build_cephalothorax(collection)
    abdomen, glow = build_abdomen(collection)
    build_egg_sacs(collection, abdomen)
    build_legs(collection)
    build_fangs(collection)
    build_eyes(collection)
    build_mandibles(collection)
    total = fit_budget(collection, abdomen, glow)
    finish(collection)
    bpy.context.scene.frame_set(1)
    print(f"Built {COLLECTION}: {len(collection.all_objects)} objects, {total} triangles")
    return collection


def export_obj(collection, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in collection.all_objects:
        obj.select_set(True)
    bpy.ops.wm.obj_export(
        filepath=path, export_selected_objects=True, export_uv=True, export_materials=True,
    )
    print(f"Exported OBJ -> {path}")


if __name__ == "__main__":
    collection = build()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 1:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import broodmother_anims
        import osrs_model_export

        dat_path = os.path.abspath(args[1])
        model = osrs_model_export.export_collection(COLLECTION, dat_path, merge_vertices=False)
        broodmother_anims.generate(model, os.path.dirname(os.path.dirname(dat_path)))
        export_obj(collection, args[2] if len(args) > 2 else OBJ_PATH)
