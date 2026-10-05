"""Builds the Poison Blades item model: two large, curved, sulphur-blade style short swords
lying crossed on the ground, with polished steel, a venom-coated outer edge and translucent
poison drips running off the edges and tips.

Scale is 1 Blender unit = 1 tile, blades lie in the XY plane with +Z up. Every part carries an
``rs_color`` face attribute (OSRS 16-bit HSL) and an ``rs_label`` vertex label for
``osrs_model_export.py``; the drips also carry ``rs_alpha`` and ``rs_flabel`` so a future wield
animation can move or fade them. OSRS has no specular light, so the shine comes purely from
lightness contrast between the bevelled edges, the flats and the fuller.

Usage:
    blender --background --python tools/blender/poison_blades_build.py -- [out.blend] [out.dat] [preview.png]
or paste/run inside a live Blender session (no arguments needed).
"""

import colorsys
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

COLLECTION = "PoisonBlades"
MAX_TRIANGLES = 2000
EDGE_SPLIT_ANGLE = 40

BLADE_LENGTH = 0.85
BLADE_HALF_WIDTH = 0.07
BLADE_HALF_THICKNESS = 0.024
BLADE_CURVE = 0.09
BLADE_STATIONS = 16
BLADE_PROFILE = (
    (0.0, 0.72), (0.12, 0.8), (0.35, 0.95), (0.55, 1.0),
    (0.72, 0.9), (0.84, 0.66), (0.93, 0.36), (1.0, 0.0),
)
BEVEL_INSET = 0.6
BEVEL_HEIGHT = 0.55
FULLER_RANGE = (0.06, 0.6)
FULLER_DEPTH = 0.25
POISON_EDGE_START = 0.62
POISON_TIP_START = 0.86

HOOKS = (0.3, 0.48, 0.64)
HOOK_BASE = (-0.05, 0.02)
HOOK_REACH_BACK = 0.1
HOOK_REACH_OUT = 0.045
HOOK_HALF_THICKNESS = BLADE_HALF_THICKNESS * 0.3

GUARD_HALF_SPAN = 0.12
GUARD_SWEEP = 0.035
GUARD_HALF_DEPTH = 0.018
GUARD_HALF_HEIGHT = 0.026
GUARD_SPIKE = (0.05, 0.06)
GUARD_STATIONS = (0.0, 0.25, 0.6, 1.0)
GEM_RADIUS = 0.022

GRIP_START = -0.02
GRIP_END = -0.24
GRIP_RADIUS = 0.022
GRIP_BANDS = 8
GRIP_SIDES = 6
POMMEL_PROFILE = ((-0.245, 0.03), (-0.27, 0.038), (-0.295, 0.03), (-0.345, 0.0))

CROSS_AT = 0.4 * BLADE_LENGTH
CROSS_ANGLE = 35
RESTING_LIFT = 0.04
CROSS_GAP = 0.006

DRIPS = (
    (0.66, 1, 0.05, 0.03),
    (0.78, -1, 0.06, 0.032),
    (0.9, 1, 0.045, 0.026),
)
TIP_DRIP = (0.055, 0.032)
DROPLETS = ((0.72, 1, 0.11, 0.016), (0.84, -1, 0.12, 0.014))
STRAND_RADII = (0.02, 0.014)
STRAND_SIDES = 5
BULB_SEGMENTS = 8
BULB_RINGS = 4
BULB_SQUASH = 0.6
STRAND_ALPHA = 110
BULB_ALPHA = 70
DROPLET_ALPHA = 90


def hsl(hue, saturation, lightness):
    return (hue << 10) | (saturation << 7) | lightness


STEEL_HSL = hsl(41, 1, 100)
STEEL_DARK_HSL = hsl(41, 1, 78)
EDGE_HSL = hsl(41, 0, 122)
EDGE_UNDER_HSL = hsl(41, 0, 95)
FULLER_HSL = hsl(41, 1, 70)
GUARD_HSL = hsl(41, 1, 92)
GUARD_DARK_HSL = hsl(41, 1, 60)
WRAP_HSL = hsl(24, 3, 22)
WRAP_BAND_HSL = hsl(24, 3, 34)
POISON_HSL = hsl(21, 7, 55)
POISON_DARK_HSL = hsl(22, 7, 38)
GEM_HSL = hsl(21, 7, 70)
DRIP_HSL = hsl(21, 7, 72)
DRIP_CORE_HSL = hsl(19, 7, 92)

LABEL_BLADE = (1, 2)
LABEL_DRIPS = (3, 4)
FACE_LABEL_DRIPS = (1, 2)


def hsl_to_rgba(value):
    hue = ((value >> 10) & 63) / 64 + 1 / 128
    saturation = ((value >> 7) & 7) / 8 + 1 / 16
    lightness = (value & 127) / 128
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (r, g, b, 1.0)


def material_for(value, alpha=0, emissive=False):
    """Flat, rough, non-metallic material for one OSRS face colour. ``emissive`` also lights the
    face with its own colour; OSRS has no emission, so in game a glow is just a bright colour."""
    name = f"rs_{value}_{alpha}{'_glow' if emissive else ''}"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if not material.node_tree:
        material.use_nodes = True
    rgba = hsl_to_rgba(value)[:3] + (1.0 - alpha / 255,)
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = rgba
    for socket, amount in (("Roughness", 1.0), ("Metallic", 0.0)):
        if socket in bsdf.inputs:
            bsdf.inputs[socket].default_value = amount
    if emissive:
        for socket in ("Emission Color", "Emission"):
            if socket in bsdf.inputs:
                bsdf.inputs[socket].default_value = rgba[:3] + (1.0,)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 1.0
    material.diffuse_color = rgba
    material.roughness = 1.0
    material.metallic = 0.0
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


def int_attribute(mesh, name, domain, values):
    attribute = mesh.attributes.get(name) or mesh.attributes.new(name, "INT", domain)
    for index, value in enumerate(values):
        attribute.data[index].value = value


def make_mesh(collection, name, verts, faces, colors, label, alpha=0, face_label=0, matrix=None):
    """Creates an object from raw geometry, one HSL colour per face, with outward normals."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([Vector(v) for v in verts], [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if matrix is not None:
        bm.transform(matrix)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    int_attribute(mesh, "rs_color", "FACE", colors)
    int_attribute(mesh, "rs_label", "POINT", [label] * len(mesh.vertices))
    if alpha:
        int_attribute(mesh, "rs_alpha", "FACE", [alpha] * len(mesh.polygons))
    if face_label:
        int_attribute(mesh, "rs_flabel", "FACE", [face_label] * len(mesh.polygons))
    palette = []
    for polygon, value in zip(mesh.polygons, colors):
        if value not in palette:
            palette.append(value)
            mesh.materials.append(material_for(value, alpha))
        polygon.material_index = palette.index(value)
    return obj


def lerp_profile(t):
    for (t0, w0), (t1, w1) in zip(BLADE_PROFILE, BLADE_PROFILE[1:]):
        if t <= t1:
            return w0 + (w1 - w0) * (t - t0) / (t1 - t0)
    return BLADE_PROFILE[-1][1]


def blade_center_y(t, side):
    return BLADE_CURVE * side * t * t


def blade_edge(t, side, edge_sign):
    """Local position on the cutting edge (+1) or spine (-1) at blade fraction t."""
    w = BLADE_HALF_WIDTH * lerp_profile(t)
    return Vector((t * BLADE_LENGTH, blade_center_y(t, side) + edge_sign * side * w, 0.0))


def blade_strip_color(strip, t):
    in_fuller = FULLER_RANGE[0] <= t <= FULLER_RANGE[1]
    if t >= POISON_TIP_START:
        return POISON_HSL if strip in (0, 3) else POISON_DARK_HSL
    if strip in (0, 3):
        return POISON_HSL if t >= POISON_EDGE_START else EDGE_HSL
    if strip in (1, 2):
        return FULLER_HSL if in_fuller else STEEL_HSL
    if t >= POISON_EDGE_START and strip in (4, 7):
        return POISON_DARK_HSL
    return EDGE_UNDER_HSL if strip in (4, 7) else STEEL_DARK_HSL


def build_blade(collection, index, side, matrix):
    h = BLADE_HALF_THICKNESS
    verts, faces, colors, rings = [], [], [], []
    stations = [i / (BLADE_STATIONS - 1) for i in range(BLADE_STATIONS)]
    for t in stations[:-1]:
        x = t * BLADE_LENGTH
        cy = blade_center_y(t, side)
        w = BLADE_HALF_WIDTH * lerp_profile(t) * side
        taper = 1 - 0.7 * t
        ridge = h * taper * (FULLER_DEPTH if FULLER_RANGE[0] <= t <= FULLER_RANGE[1] else 1)
        bevel_z = h * taper * BEVEL_HEIGHT
        ring = [
            (x, cy + w, 0), (x, cy + w * BEVEL_INSET, bevel_z), (x, cy, ridge),
            (x, cy - w * BEVEL_INSET, bevel_z), (x, cy - w, 0),
            (x, cy - w * BEVEL_INSET, -bevel_z), (x, cy, -h * taper),
            (x, cy + w * BEVEL_INSET, -bevel_z),
        ]
        rings.append(list(range(len(verts), len(verts) + 8)))
        verts.extend(ring)
    tip = len(verts)
    verts.append((BLADE_LENGTH, blade_center_y(1.0, side), 0))

    faces.append(list(reversed(rings[0])))
    colors.append(STEEL_DARK_HSL)
    for i, (ring, nxt) in enumerate(zip(rings, rings[1:])):
        t_mid = (stations[i] + stations[i + 1]) / 2
        for k in range(8):
            faces.append([ring[k], ring[(k + 1) % 8], nxt[(k + 1) % 8], nxt[k]])
            colors.append(blade_strip_color(k, t_mid))
    last = rings[-1]
    for k in range(8):
        faces.append([last[k], last[(k + 1) % 8], tip])
        colors.append(blade_strip_color(k, 1.0))
    return make_mesh(collection, f"PoisonBlade{index}_Blade", verts, faces, colors,
                     LABEL_BLADE[index], matrix=matrix)


def build_hooks(collection, index, side, matrix):
    verts, faces, colors = [], [], []
    for t in HOOKS:
        root_a = blade_edge(t + HOOK_BASE[0], side, -1)
        root_b = blade_edge(t + HOOK_BASE[1], side, -1)
        apex = blade_edge(t - HOOK_REACH_BACK / BLADE_LENGTH, side, -1)
        apex.y -= side * HOOK_REACH_OUT
        base = len(verts)
        for point in (root_a, root_b, apex):
            verts.append((point.x, point.y, HOOK_HALF_THICKNESS))
        for point in (root_a, root_b, apex):
            verts.append((point.x, point.y, -HOOK_HALF_THICKNESS))
        top = POISON_HSL if t >= POISON_EDGE_START else EDGE_HSL
        faces += [[base, base + 1, base + 2], [base + 5, base + 4, base + 3]]
        colors += [top, STEEL_DARK_HSL]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            faces.append([base + a, base + 3 + a, base + 3 + b, base + b])
            colors.append(STEEL_HSL)
    return make_mesh(collection, f"PoisonBlade{index}_Hooks", verts, faces, colors,
                     LABEL_BLADE[index], matrix=matrix)


def build_guard(collection, index, matrix):
    dx, dz = GUARD_HALF_DEPTH, GUARD_HALF_HEIGHT
    stations = [-s for s in reversed(GUARD_STATIONS[1:])] + list(GUARD_STATIONS)
    verts, faces, colors, rings = [], [], [], []
    for s in stations:
        y = s * GUARD_HALF_SPAN
        x = GUARD_SWEEP * s * s
        rings.append(list(range(len(verts), len(verts) + 4)))
        verts += [(x - dx, y, dz), (x + dx, y, dz), (x + dx, y, -dz), (x - dx, y, -dz)]
    for ring, nxt in zip(rings, rings[1:]):
        for k in range(4):
            faces.append([ring[k], ring[(k + 1) % 4], nxt[(k + 1) % 4], nxt[k]])
            colors.append(GUARD_HSL if k == 0 else GUARD_DARK_HSL if k == 2 else STEEL_HSL)
    for ring, sign in ((rings[0], -1), (rings[-1], 1)):
        spike = len(verts)
        verts.append((GUARD_SWEEP + GUARD_SPIKE[0], sign * (GUARD_HALF_SPAN + GUARD_SPIKE[1]), 0))
        for k in range(4):
            faces.append([ring[k], ring[(k + 1) % 4], spike])
            colors.append(EDGE_HSL if k == 0 else STEEL_HSL)
    guard = make_mesh(collection, f"PoisonBlade{index}_Guard", verts, faces, colors,
                      LABEL_BLADE[index], matrix=matrix)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=GEM_RADIUS)
    bm.transform(Matrix.Translation((0, 0, dz)))
    gem_verts = [tuple(v.co) for v in bm.verts]
    gem_faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    gem = make_mesh(collection, f"PoisonBlade{index}_Gem", gem_verts, gem_faces,
                    [GEM_HSL] * len(gem_faces), LABEL_BLADE[index], matrix=matrix)
    return guard, gem


def build_grip(collection, index, matrix):
    band_step = (GRIP_END - GRIP_START) / GRIP_BANDS
    profile = [(GRIP_START + band_step * i, GRIP_RADIUS) for i in range(GRIP_BANDS + 1)]
    profile += list(POMMEL_PROFILE)
    verts, faces, colors, rings = [], [], [], []
    for x, r in profile[:-1]:
        rings.append(list(range(len(verts), len(verts) + GRIP_SIDES)))
        for k in range(GRIP_SIDES):
            angle = 2 * math.pi * k / GRIP_SIDES
            verts.append((x, r * math.cos(angle), r * math.sin(angle)))
    tip = len(verts)
    verts.append((profile[-1][0], 0, 0))
    faces.append(list(rings[0]))
    colors.append(STEEL_DARK_HSL)
    for i, (ring, nxt) in enumerate(zip(rings, rings[1:])):
        if i < GRIP_BANDS:
            color = WRAP_BAND_HSL if i % 2 else WRAP_HSL
        else:
            color = STEEL_HSL
        for k in range(GRIP_SIDES):
            faces.append([ring[k], ring[(k + 1) % GRIP_SIDES], nxt[(k + 1) % GRIP_SIDES], nxt[k]])
            colors.append(color)
    for k in range(GRIP_SIDES):
        faces.append([rings[-1][k], rings[-1][(k + 1) % GRIP_SIDES], tip])
        colors.append(EDGE_HSL)
    return make_mesh(collection, f"PoisonBlade{index}_Grip", verts, faces, colors,
                     LABEL_BLADE[index], matrix=matrix)


def blade_matrix(index):
    """Places a blade so its crossing point sits over the origin. The top blade rests its
    pommel on the ground and leans up over the lower blade."""
    angle = math.radians(CROSS_ANGLE if index == 0 else -CROSS_ANGLE)
    if index == 0:
        height, pitch = RESTING_LIFT, 0.0
    else:
        height = RESTING_LIFT + 2 * BLADE_HALF_THICKNESS + CROSS_GAP
        run = CROSS_AT - POMMEL_PROFILE[-1][0]
        pitch = math.asin((height - RESTING_LIFT) / run)
    return (
        Matrix.Translation((0, 0, height))
        @ Matrix.Rotation(angle, 4, "Z")
        @ Matrix.Rotation(-pitch, 4, "Y")
        @ Matrix.Translation((-CROSS_AT, 0, 0))
    )


def tube(points, radii, sides):
    """Verts and faces for a capped tube through ``points`` with matching ``radii``."""
    verts, faces, rings = [], [], []
    for i, (point, radius) in enumerate(zip(points, radii)):
        ahead = points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]
        axis = ahead.normalized()
        normal = axis.cross(Vector((0, 0, 1)))
        if normal.length < 1e-4:
            normal = axis.cross(Vector((1, 0, 0)))
        normal.normalize()
        binormal = axis.cross(normal)
        rings.append(list(range(len(verts), len(verts) + sides)))
        for k in range(sides):
            angle = 2 * math.pi * k / sides
            offset = normal * math.cos(angle) + binormal * math.sin(angle)
            verts.append(tuple(point + offset * radius))
    faces.append(list(rings[0]))
    for ring, nxt in zip(rings, rings[1:]):
        for k in range(sides):
            faces.append([ring[k], ring[(k + 1) % sides], nxt[(k + 1) % sides], nxt[k]])
    faces.append(list(reversed(rings[-1])))
    return verts, faces


def bulb(center, radius):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=BULB_SEGMENTS, v_segments=BULB_RINGS, radius=radius)
    bm.transform(Matrix.Translation(center) @ Matrix.Diagonal((1, 1, BULB_SQUASH, 1)))
    verts = [tuple(v.co) for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return verts, faces


def offset_faces(faces, base):
    return [[i + base for i in face] for face in faces]


def build_drips(collection, index, side, matrix):
    """Strands run from the edge out and down to a bulb resting on the ground."""
    rotation = matrix.to_3x3()
    strand_verts, strand_faces = [], []
    bulb_verts, bulb_faces = [], []
    droplet_verts, droplet_faces = [], []

    def add_drip(attach_local, outward_local, length, radius):
        attach = matrix @ attach_local
        outward = rotation @ outward_local
        outward.z = 0
        outward.normalize()
        end = attach + outward * length
        end.z = radius * BULB_SQUASH
        mid = attach.lerp(end, 0.55)
        mid.z = attach.z * 0.45 + end.z * 0.55
        verts, faces = tube([attach, mid, end], [STRAND_RADII[0], STRAND_RADII[1], radius * 0.6],
                            STRAND_SIDES)
        strand_faces.extend(offset_faces(faces, len(strand_verts)))
        strand_verts.extend(verts)
        verts, faces = bulb(end, radius)
        bulb_faces.extend(offset_faces(faces, len(bulb_verts)))
        bulb_verts.extend(verts)

    for t, edge_sign, length, radius in DRIPS:
        add_drip(blade_edge(t, side, edge_sign), Vector((-0.2, edge_sign * side, 0)), length, radius)
    add_drip(Vector((BLADE_LENGTH, blade_center_y(1.0, side), 0)), Vector((1, 0.3 * side, 0)),
             *TIP_DRIP)

    for t, edge_sign, distance, radius in DROPLETS:
        edge = matrix @ blade_edge(t, side, edge_sign)
        outward = rotation @ Vector((0, edge_sign * side, 0))
        outward.z = 0
        center = edge + outward.normalized() * distance
        center.z = radius * BULB_SQUASH
        verts, faces = bulb(center, radius)
        droplet_faces.extend(offset_faces(faces, len(droplet_verts)))
        droplet_verts.extend(verts)

    for name, verts, faces, color, alpha in (
        ("Strands", strand_verts, strand_faces, DRIP_HSL, STRAND_ALPHA),
        ("Bulbs", bulb_verts, bulb_faces, DRIP_CORE_HSL, BULB_ALPHA),
        ("Droplets", droplet_verts, droplet_faces, DRIP_HSL, DROPLET_ALPHA),
    ):
        make_mesh(collection, f"PoisonBlade{index}_Drip{name}", verts, faces,
                  [color] * len(faces), LABEL_DRIPS[index], alpha=alpha,
                  face_label=FACE_LABEL_DRIPS[index])


def triangles(objects):
    total = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def finish(collection):
    for obj in collection.all_objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        split = obj.modifiers.new("HardEdges", "EDGE_SPLIT")
        split.split_angle = math.radians(EDGE_SPLIT_ANGLE)


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    collection = reset_collection()
    for index, side in ((0, 1), (1, -1)):
        matrix = blade_matrix(index)
        build_blade(collection, index, side, matrix)
        build_hooks(collection, index, side, matrix)
        build_guard(collection, index, matrix)
        build_grip(collection, index, matrix)
        build_drips(collection, index, side, matrix)
    total = triangles(collection.all_objects)
    assert total <= MAX_TRIANGLES, f"{total} triangles exceeds budget of {MAX_TRIANGLES}"
    finish(collection)
    print(f"Built {COLLECTION}: {len(collection.all_objects)} objects, {total} triangles")
    return collection


def render_preview(path):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as error:
        print(f"Workbench unavailable, keeping {scene.render.engine}: {error}")
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = False
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.image_settings.file_format = "PNG"

    camera_data = bpy.data.cameras.get("PoisonPreviewCam") or bpy.data.cameras.new("PoisonPreviewCam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 1.6
    camera = bpy.data.objects.get("PoisonPreviewCam") or bpy.data.objects.new("PoisonPreviewCam",
                                                                              camera_data)
    if camera.name not in scene.collection.objects:
        scene.collection.objects.link(camera)
    camera.location = (1.1, -1.5, 1.7)
    direction = Vector((0, 0, 0.05)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered preview -> {path}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    collection = build()
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 1:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import osrs_model_export

        dat_path = os.path.abspath(args[1])
        os.makedirs(os.path.dirname(dat_path), exist_ok=True)
        osrs_model_export.export_collection(COLLECTION, dat_path, merge_vertices=False)
    if len(args) > 2:
        render_preview(args[2])
