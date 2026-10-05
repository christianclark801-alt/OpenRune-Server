"""Builds the Venomfang helm: a low-profile, angular insectoid headpiece fitted close to the head.
A sunken visor framed by a brow overhang and cheek blades holds a cluster of six neon-green
compound eyes cut as faceted pyramidal pits; purple mandibles wrap the jawline and interlock at
the chin; the flat top is three overlapping obsidian plates, edged in neon green, stepping down towards
the back into a sharp, low crest. Colours come from the poison armour palette in
``worn_armour.py``.

Everything is authored in player-space units (forward, left, up; 128 = one tile) and converted
to Blender units, where 1 BU = 1 tile, +X is forward, +Y is the player's left and +Z is up. Worn
models carry the head label (1) on every vertex except the eight neck-collar anchors, copied from
the rune full helm, that tie the helm's rim to the neck so it bends with it. The female variant
is the male helm scaled and lowered onto the female head with the female anchors. The inventory
model is the same geometry, unlabelled and rebased onto the ground like the vanilla icons.

Usage:
    blender --background --python tools/blender/venomfang_helm_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import poison_blades_build as parts  # noqa: E402
from poison_blades_build import hsl, int_attribute, material_for  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, SOCKET_HSL, TOXIC_DARK_HSL, TOXIC_HSL,
    VENOM_DIM_HSL, VENOM_HSL,
)

UNITS = 128
HELM_PRIORITY = 7
SHOULDER_LINE = 170
MAX_TRIANGLES = 1200
EDGE_SPLIT_ANGLE = 30

HEAD_LABEL = 1
INVENTORY_LABEL = 0

SHELL_SEGMENTS = 8
SHELL_RINGS = (
    (168, 9.5, 15.5, 12.5),
    (176, 11.5, 19.0, 14.5),
    (186, 13.0, 21.5, 16.0),
    (196, 13.0, 19.5, 16.5),
    (203, 11.0, 15.5, 15.5),
    (205.5, 8.5, 11.5, 12.5),
)
SHELL_CAP = (-0.5, 205.5)
NAPE_DROP = 5.0

MALE_COLLAR = (
    ((9, 3, 169), 3), ((8, 7, 164), 2), ((-4, 7, 165), 2), ((-2, 5, 173), 3),
    ((-2, -5, 173), 3), ((-4, -7, 165), 2), ((8, -7, 164), 2), ((9, -3, 169), 3),
)
FEMALE_COLLAR = (
    ((5, 2, 168), 3), ((3, 4, 161), 49), ((-5, 5, 162), 2), ((-4, 5, 169), 3),
    ((-4, -5, 169), 3), ((-5, -5, 162), 2), ((3, -4, 161), 49), ((5, -2, 168), 3),
)
FEMALE_SCALE = (0.9, 0.9, 0.9)
FEMALE_UP_SHIFT = -6.0

VISOR_LEFT = 10.0
VISOR_BOTTOM, VISOR_TOP = 181.0, 197.0
VISOR_COLUMNS, VISOR_ROWS = 4, 2
VISOR_LIFT = 1.6

BROW = ((-12.5, 200.0), (0.0, 195.0), (12.5, 200.0))
BROW_OVERHANG = 4.0
BROW_HEIGHT = 3.5
CHEEK_LEFT = 11.5
CHEEK_SPAN = (180.5, 197.5)
CHEEK_PROTRUDE = 2.5
CHEEK_DEPTH = 1.5
LIP = ((-10.0, 180.5), (0.0, 179.5), (10.0, 180.5))
LIP_PROTRUDE = 1.8
LIP_HEIGHT = 1.6

EYES = ((3.5, 190.0, 2.2), (-3.5, 190.0, 2.2), (8.0, 192.0, 1.7), (-8.0, 192.0, 1.7),
        (5.5, 185.5, 1.5), (-5.5, 185.5, 1.5))
EYE_SIDES = 6
EYE_RIM_LIFT = 1.4
EYE_PIT_DEPTH = 1.3
EYE_SOCKET_GROWTH = 0.7

MANDIBLE_UP = {1: 175.5, -1: 172.5}
MANDIBLE_ANGLES = (85.0, 60.0, 35.0, 12.0, -6.0, -18.0)
MANDIBLE_WIDTHS = (2.0, 3.0, 3.4, 3.0, 2.0, 0.0)
MANDIBLE_CURL = (0.0, 0.0, 0.0, 0.5, 1.2, 2.0)
MANDIBLE_HALF_HEIGHT = 1.7
MANDIBLE_GAP = 0.6
TEETH = ((2, 1.4), (3, 1.2))
TOOTH_DROP = 0.6

PLATES = (
    (13.0, 1.0, 207.5, 10.0),
    (4.0, -10.0, 206.2, 10.0),
    (-7.0, -17.0, 204.6, 9.0),
)
PLATE_RISE = 1.0
PLATE_CHAMFER = 3.5
PLATE_THICKNESS = 1.5
PLATE_SLOPE = 1.0
CREST_TIP = (-27.0, 201.0)
CREST_HALF_WIDTH = 1.5
CREST_HEIGHT = 2.0

OBSIDIAN_LOW_HSL = hsl(42, 2, 11)


def to_blender(point, gender_transform):
    fwd, left, up = gender_transform(point)
    return fwd / UNITS, left / UNITS, up / UNITS


def male(point):
    return point


def female(point):
    fwd, left, up = point
    sf, sl, su = FEMALE_SCALE
    centre_up = 186.0
    return fwd * sf, left * sl, centre_up + (up - centre_up) * su + FEMALE_UP_SHIFT


def make(collection, name, verts, faces, colors, labels, transform, alpha=0, face_label=0,
         recalc=True, fixed=()):
    """Vertices in ``fixed`` skip the gender transform: the neck anchors must sit exactly where
    the vanilla helms put them."""
    mesh = bpy.data.meshes.new(name)
    placed = [Vector(to_blender(v, male if i in fixed and transform is female else transform))
              for i, v in enumerate(verts)]
    mesh.from_pydata(placed, [], faces)
    mesh.update()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if isinstance(colors, int):
        colors = [colors] * len(mesh.polygons)
    if isinstance(labels, int):
        labels = [labels] * len(mesh.vertices)
    int_attribute(mesh, "rs_color", "FACE", colors)
    int_attribute(mesh, "rs_label", "POINT", labels)
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


def ring_at(up):
    """The shell ring interpolated to ``up``: (half width, front, back)."""
    rings = SHELL_RINGS
    if up <= rings[0][0]:
        return rings[0][1:]
    for lower, upper in zip(rings, rings[1:]):
        if up <= upper[0]:
            t = (up - lower[0]) / (upper[0] - lower[0])
            return tuple(a + (b - a) * t for a, b in zip(lower[1:], upper[1:]))
    return rings[-1][1:]


def surface_fwd(left, up):
    """Forward depth of the faceted shell front at (left, up). The front centre segment and its
    two neighbours are flat facets, so this follows the chords, not the ellipse."""
    half_width, front, _ = ring_at(up)
    step = 2 * math.pi / SHELL_SEGMENTS
    corner = (front * math.cos(step), half_width * math.sin(step))
    t = min(abs(left) / corner[1], 1.0)
    return front + (corner[0] - front) * t


def ring_point(ring, k, nape=False):
    up, half_width, front, back = ring
    angle = 2 * math.pi * k / SHELL_SEGMENTS
    c, s = math.cos(angle), math.sin(angle)
    fwd = front * c if c >= 0 else back * c
    if nape and c < -0.3:
        up -= NAPE_DROP * (-c)
    return fwd, half_width * s, up


def angle_of(point):
    fwd, left, _ = point
    return math.atan2(left, fwd) % (2 * math.pi)


def unwrap(angle, index, count):
    return angle + (2 * math.pi if index >= count else 0)


def stitch(verts, outer, inner):
    """Triangle strip joining two loops by walking both in angle order."""
    outer = sorted(outer, key=lambda i: angle_of(verts[i]))
    inner = sorted(inner, key=lambda i: angle_of(verts[i]))
    faces = []
    i = j = 0
    while i < len(outer) or j < len(inner):
        o0, o1 = outer[i % len(outer)], outer[(i + 1) % len(outer)]
        n0, n1 = inner[j % len(inner)], inner[(j + 1) % len(inner)]
        advance_outer = j >= len(inner) or (
            i < len(outer) and unwrap(angle_of(verts[o1]), i + 1, len(outer))
            <= unwrap(angle_of(verts[n1]), j + 1, len(inner))
        )
        if advance_outer:
            faces.append((o0, o1, n0))
            i += 1
        else:
            faces.append((o0, n1, n0))
            j += 1
    return faces


def build_shell(collection, label, collar, transform):
    """Tight eight-sided shell with a hard keel down the face and a flat top, sealed at the bottom
    to the neck collar."""
    verts, labels, faces, colors = [], [], [], []
    rings = []
    for index, ring in enumerate(SHELL_RINGS):
        rings.append(list(range(len(verts), len(verts) + SHELL_SEGMENTS)))
        for k in range(SHELL_SEGMENTS):
            verts.append(ring_point(ring, k, nape=index == 0))
            labels.append(label)
    cap = len(verts)
    verts.append((SHELL_CAP[0], 0.0, SHELL_CAP[1]))
    labels.append(label)

    ring_colors = (OBSIDIAN_LOW_HSL, OBSIDIAN_HSL, OBSIDIAN_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL)
    for r in range(len(rings) - 1):
        for k in range(SHELL_SEGMENTS):
            a, b = rings[r][k], rings[r][(k + 1) % SHELL_SEGMENTS]
            c, d = rings[r + 1][(k + 1) % SHELL_SEGMENTS], rings[r + 1][k]
            faces += [(a, b, c), (a, c, d)]
            colors += [ring_colors[r]] * 2
    for k in range(SHELL_SEGMENTS):
        faces.append((rings[-1][k], rings[-1][(k + 1) % SHELL_SEGMENTS], cap))
        colors.append(OBSIDIAN_TOP_HSL)

    collar_ids = []
    for point, collar_label in collar:
        collar_ids.append(len(verts))
        verts.append(point)
        labels.append(collar_label if label != INVENTORY_LABEL else INVENTORY_LABEL)
    faces += stitch(verts, rings[0], collar_ids)
    colors += [OBSIDIAN_LOW_HSL] * (len(faces) - len(colors))
    for i in range(1, len(collar_ids) - 1):
        faces.append((collar_ids[0], collar_ids[i], collar_ids[i + 1]))
        colors.append(OBSIDIAN_LOW_HSL)
    return make(collection, "Shell", verts, faces, colors, labels, transform,
                fixed=set(collar_ids))


def visor_point(left, up, lift=VISOR_LIFT):
    return surface_fwd(left, up) + lift, left, up


def wedge(path, outward, height, colors):
    """A triangular-section bar along ``path`` of (left, up) points on the face: its back edge
    lies on the shell and its front edge stands ``outward`` proud, ``height`` below the top."""
    verts, faces, face_colors = [], [], []
    for left, up in path:
        base = surface_fwd(left, up)
        verts += [(base, left, up + height), (base + outward, left, up), (base, left, up)]
    for s in range(len(path) - 1):
        a, b = 3 * s, 3 * (s + 1)
        for k in range(3):
            faces.append((a + k, a + (k + 1) % 3, b + (k + 1) % 3, b + k))
            face_colors.append(colors[k])
    faces += [(0, 1, 2), (len(verts) - 1, len(verts) - 2, len(verts) - 3)]
    face_colors += [colors[0], colors[0]]
    return verts, faces, face_colors


def build_visor(collection, label, transform):
    """Dark socket plate following the face, framed by a brow overhang, cheek blades and a lower
    lip that all stand proud of it, so the visor reads as sunk into the head."""
    verts, faces = [], []
    for row in range(VISOR_ROWS + 1):
        up = VISOR_BOTTOM + (VISOR_TOP - VISOR_BOTTOM) * row / VISOR_ROWS
        for col in range(VISOR_COLUMNS + 1):
            left = -VISOR_LEFT + 2 * VISOR_LEFT * col / VISOR_COLUMNS
            verts.append(visor_point(left, up))
    width = VISOR_COLUMNS + 1
    for row in range(VISOR_ROWS):
        for col in range(VISOR_COLUMNS):
            a = row * width + col
            faces.append((a, a + 1, a + width + 1, a + width))
    make(collection, "Socket", verts, faces, SOCKET_HSL, label, transform)

    brow = [(left, up) for left, up in BROW]
    verts, faces, colors = wedge(brow, BROW_OVERHANG, BROW_HEIGHT,
                                 (OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL))
    make(collection, "Brow", verts, faces, colors, label, transform)
    lip = [(left, up) for left, up in LIP]
    verts, faces, colors = wedge(lip, LIP_PROTRUDE, LIP_HEIGHT,
                                 (OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_LOW_HSL))
    make(collection, "Lip", verts, faces, colors, label, transform)

    for side in (1, -1):
        left = CHEEK_LEFT * side
        verts = []
        for up in CHEEK_SPAN:
            base = surface_fwd(left, up)
            verts += [(base, left, up), (base + CHEEK_PROTRUDE, left - CHEEK_DEPTH * side, up),
                      (base - CHEEK_DEPTH, left + CHEEK_DEPTH * side, up)]
        faces = [(0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5), (0, 2, 1), (3, 4, 5)]
        colors = [OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_LOW_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_TOP_HSL]
        make(collection, f"Cheek{side}", verts, faces, colors, label, transform)


def build_eyes(collection, label, transform):
    """Each compound eye is a raised hexagonal rim around an inverted pyramid: the facets slope
    into a pit whose apex sits back on the socket plate, so the eye reads as a sharp hollow."""
    for index, (left, up, radius) in enumerate(EYES):
        plate = surface_fwd(left, up) + VISOR_LIFT
        verts = [(plate + 0.1, left, up)]
        for k in range(EYE_SIDES):
            angle = 2 * math.pi * k / EYE_SIDES + math.pi / 6
            l, u = left + radius * math.cos(angle), up + radius * math.sin(angle)
            verts.append((plate + EYE_RIM_LIFT, l, u))
        for k in range(EYE_SIDES):
            angle = 2 * math.pi * k / EYE_SIDES + math.pi / 6
            grown = radius + EYE_SOCKET_GROWTH
            l, u = left + grown * math.cos(angle), up + grown * math.sin(angle)
            verts.append((plate, l, u))
        verts[0] = (plate + EYE_RIM_LIFT - EYE_PIT_DEPTH, left, up)
        faces, colors = [], []
        for k in range(EYE_SIDES):
            rim, nxt = 1 + k, 1 + (k + 1) % EYE_SIDES
            outer, outer_nxt = 1 + EYE_SIDES + k, 1 + EYE_SIDES + (k + 1) % EYE_SIDES
            faces.append(oriented(verts, (0, rim, nxt), toward=(1, 0, 0)))
            colors.append(VENOM_HSL)
            faces.append(oriented(verts, (rim, outer, outer_nxt), toward=(1, 0, 0)))
            faces.append(oriented(verts, (rim, outer_nxt, nxt), toward=(1, 0, 0)))
            colors += [VENOM_DIM_HSL, VENOM_DIM_HSL]
        make(collection, f"Eye{index}", verts, faces, colors, label, transform, recalc=False)


def oriented(verts, face, toward):
    """``face`` wound so its normal points along ``toward``; open pieces like the eye pits must
    face the viewer, which a closed-mesh normal fix can't decide."""
    a, b, c = (Vector(verts[i]) for i in face)
    normal = (b - a).cross(c - a)
    blender_normal = Vector((normal.x, normal.y, normal.z))
    return face if blender_normal.dot(Vector(toward)) >= 0 else (face[0], face[2], face[1])


def jaw_point(angle, up, radial):
    """A point ``radial`` out from the shell at ``angle`` around the head (0 = front centre)."""
    half_width, front, back = ring_at(up)
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    depth = front if c >= 0 else back
    length = math.hypot(depth * c, half_width * s)
    scale = (length + radial) / length if length else 1
    return depth * c * scale, half_width * s * scale, up


def build_mandibles(collection, label, transform):
    """Flat purple blades hugging the jaw, each running from under the ear round the cheek and
    past the chin centre. The two sides sit at different heights so their tips overlap and lock
    together; two small teeth hook down off each blade."""
    for side in (1, -1):
        up = MANDIBLE_UP[side]
        verts, faces, colors = [], [], []
        for angle, width, curl in zip(MANDIBLE_ANGLES, MANDIBLE_WIDTHS, MANDIBLE_CURL):
            a = angle * side
            at = up + curl
            inner = jaw_point(a, at, MANDIBLE_GAP)
            outer = jaw_point(a, at, MANDIBLE_GAP + max(width, 0.01))
            height = MANDIBLE_HALF_HEIGHT * (width / max(MANDIBLE_WIDTHS))
            verts += [(inner[0], inner[1], at + height), outer, (inner[0], inner[1], at - height)]
        for s in range(len(MANDIBLE_ANGLES) - 1):
            a, b = 3 * s, 3 * (s + 1)
            faces += [(a, b, b + 1, a + 1), (a + 1, b + 1, b + 2, a + 2), (a + 2, b + 2, b, a)]
            colors += [TOXIC_HSL, TOXIC_DARK_HSL, TOXIC_DARK_HSL]
        faces.append((0, 1, 2))
        colors.append(TOXIC_DARK_HSL)
        for station, length in TEETH:
            base = 3 * station
            low, edge = verts[base + 2], verts[base + 1]
            mid = tuple((p + q) / 2 for p, q in zip(low, edge))
            tip = (mid[0] - length * 0.4, mid[1] - length * 0.6 * side, up - MANDIBLE_HALF_HEIGHT
                   - TOOTH_DROP)
            t = len(verts)
            verts += [tip]
            faces += [(base + 1, base + 2, t), (base + 2, base + 1, t)]
            colors += [TOXIC_HSL, TOXIC_DARK_HSL]
        make(collection, f"Mandible{side}", verts, faces, colors, label, transform)


def build_plates(collection, label, transform):
    """Three chitin slabs over the flat top, each a shallow chevron in section and tilted back,
    stepping down so every plate's front edge tucks under the one before; the last runs into a
    narrow, low crest that ends in a sharp point behind the head."""
    for index, (front, back, up, half) in enumerate(PLATES):
        section = ((-half, -PLATE_CHAMFER), (-half * 0.4, 0.0), (0.0, PLATE_RISE),
                   (half * 0.4, 0.0), (half, -PLATE_CHAMFER))
        verts = []
        for fwd, height in ((front, up), (back, up - PLATE_SLOPE)):
            verts += [(fwd, left, height + dz) for left, dz in section]
            verts += [(fwd, left, height + dz - PLATE_THICKNESS) for left, dz in section]
        n = len(section)
        faces, colors = [], []
        for k in range(n - 1):
            faces.append((k, k + 1, 2 * n + k + 1, 2 * n + k))
            colors.append(OBSIDIAN_TOP_HSL if 0 < k < n - 2 else OBSIDIAN_HSL)
            faces.append((n + k + 1, n + k, 3 * n + k, 3 * n + k + 1))
            colors.append(OBSIDIAN_EDGE_HSL)
        for end in (0, 2 * n):
            for k in range(n - 1):
                faces.append((end + k, end + n + k, end + n + k + 1, end + k + 1))
                colors.append(OBSIDIAN_EDGE_HSL)
        for k in (0, n - 1):
            faces.append((k, n + k, 3 * n + k, 2 * n + k))
            colors.append(VENOM_HSL)
        make(collection, f"Plate{index}", verts, faces, colors, label, transform)

    front, back, up, _ = PLATES[-1]
    base_up = up - PLATE_SLOPE + PLATE_RISE
    tip_fwd, tip_up = CREST_TIP
    verts = [(back + 2, CREST_HALF_WIDTH, base_up - 0.5), (back + 2, -CREST_HALF_WIDTH, base_up - 0.5),
             (back + 2, 0.0, base_up + CREST_HEIGHT), (tip_fwd, 0.0, tip_up)]
    faces = [(0, 2, 3), (1, 3, 2), (0, 3, 1), (0, 1, 2)]
    colors = [OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL]
    make(collection, "Crest", verts, faces, colors, label, transform)


def check_shoulder_line(collection, transform):
    """Everything hanging off the shell must stay above the shoulders, or it cuts into the
    body when the head nods and the arms swing."""
    if transform is not male:
        return
    for obj in collection.all_objects:
        if obj.name.startswith("Shell"):
            continue
        lowest = min(v.co.z for v in obj.data.vertices) * UNITS
        assert lowest >= SHOULDER_LINE - 0.5, f"{obj.name} dips to {lowest:.1f}, below the shoulders"


def finish(collection):
    for obj in collection.all_objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        split = obj.modifiers.new("HardEdges", "EDGE_SPLIT")
        split.split_angle = math.radians(EDGE_SPLIT_ANGLE)


def new_collection(name):
    existing = bpy.data.collections.get(name)
    if existing is not None:
        for obj in list(existing.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(existing)
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def build_helm(name, label, collar, transform):
    collection = new_collection(name)
    build_shell(collection, label, collar, transform)
    build_visor(collection, label, transform)
    build_eyes(collection, label, transform)
    build_mandibles(collection, label, transform)
    build_plates(collection, label, transform)
    check_shoulder_line(collection, transform)
    total = parts.triangles(collection.all_objects)
    assert total <= MAX_TRIANGLES, f"{name}: {total} triangles exceeds budget of {MAX_TRIANGLES}"
    finish(collection)
    print(f"Built {name}: {len(collection.all_objects)} objects, {total} triangles")
    return collection


INVENTORY_REBASE = (-2.0, 0.0, -164.0)


def inventory(point):
    fwd, left, up = point
    return fwd + INVENTORY_REBASE[0], left + INVENTORY_REBASE[1], up + INVENTORY_REBASE[2]


HELMS = (
    ("VenomfangHelmMale", "venomfang_helm_worn.dat", HEAD_LABEL, MALE_COLLAR, male),
    ("VenomfangHelmFemale", "venomfang_helm_worn_female.dat", HEAD_LABEL, FEMALE_COLLAR, female),
    ("VenomfangHelmInventory", "venomfang_helm.dat", INVENTORY_LABEL, MALE_COLLAR, inventory),
)


def render_previews(collection_name, centre, out_dir):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as error:
        print(f"Workbench unavailable, keeping {scene.render.engine}: {error}")
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = scene.render.resolution_y = 700
    for collection in bpy.data.collections:
        collection.hide_render = collection.name != collection_name
    camera_data = bpy.data.cameras.get("HelmCam") or bpy.data.cameras.new("HelmCam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.6
    camera = bpy.data.objects.get("HelmCam") or bpy.data.objects.new("HelmCam", camera_data)
    if camera.name not in scene.collection.objects:
        scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector(centre)
    for view, offset in (("front", (2, 0, 0.15)), ("three_quarter", (1.4, -1.4, 0.6)),
                         ("side", (0, -2, 0.1)), ("back", (-1.4, 1.2, 0.7))):
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(os.path.abspath(out_dir),
                                             f"{collection_name}_{view}.png")
        bpy.ops.render.render(write_still=True)
    print(f"Rendered {collection_name} previews -> {out_dir}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for name, _, label, collar, transform in HELMS:
        build_helm(name, label, collar, transform)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 1:
        import osrs_model_export

        os.makedirs(args[1], exist_ok=True)
        for name, file_name, *_ in HELMS:
            osrs_model_export.export_collection(name, os.path.join(args[1], file_name),
                                                merge_vertices=False, priority=HELM_PRIORITY)
    if len(args) > 2:
        render_previews("VenomfangHelmMale", (0.02, 0, 1.46), args[2])
