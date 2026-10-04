"""Builds the Venomfang helm: a closed, faceted full helm with a V-shaped visor and slanted
glowing eye slits, a keel-shaped chin prow, three crown ridges that sweep backwards into sharp
horns, and two hollow spider-fang mandibles off the jaw, fed by translucent venom conduits that
run round the cheeks from a reservoir at the back.

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
from poison_blades_build import hsl, material_for, int_attribute  # noqa: E402

UNITS = 128
HELM_PRIORITY = 7
SHOULDER_LINE = 170
MAX_TRIANGLES = 1200
EDGE_SPLIT_ANGLE = 40

HEAD_LABEL = 1
INVENTORY_LABEL = 0
CONDUIT_FACE_LABEL = 1
DROP_FACE_LABEL = 2

SHELL_SEGMENTS = 10
SHELL_RINGS = (
    (168, 12.0, 16.0, 14.0),
    (176, 15.0, 21.0, 17.0),
    (186, 16.5, 22.0, 18.5),
    (196, 15.5, 19.0, 18.5),
    (205, 12.0, 13.0, 15.0),
    (212, 6.0, 6.0, 8.0),
)
SHELL_APEX = (-1.0, 216.0)
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

BROW_POINTS = ((16.5, 14.5, 197.0), (25.0, 0.0, 189.0))
BROW_THICKNESS = 3.0
BROW_DEPTH = 4.0
SLIT_INNER = (23.6, 3.0, 186.5)
SLIT_OUTER = (19.4, 13.0, 191.5)
SLIT_HEIGHT = 2.4
SLIT_LIFT = 0.8
PROW_TOP = (23.0, 185.0)
PROW_BOTTOM = (20.0, 170.0)
PROW_TIP = (28.0, 175.0)
PROW_HALF_WIDTH = 2.5

CENTRE_RIDGE = (
    ((16, 0, 199), 3.0, 4.0), ((6, 0, 212), 5.0, 4.0), ((-6, 0, 214), 6.0, 3.6),
    ((-16, 0, 208), 5.0, 3.0), ((-28, 0, 204), 3.0, 2.0), ((-38, 0, 209), 0.0, 0.0),
)
SIDE_RIDGE = (
    ((12, 9, 202), 2.0, 3.0), ((2, 10, 208), 3.5, 3.0), ((-8, 11.5, 208), 4.0, 2.6),
    ((-18, 13, 202), 3.0, 2.0), ((-30, 15, 199), 0.0, 0.0),
)
RIDGE_SINK = 1.5
SHELL_EDGE_SPLIT_ANGLE = 12

MANDIBLE = ((13, 12, 177), (19, 15, 176), (25, 14, 175), (29, 10, 174.5), (30, 6, 175))
MANDIBLE_RADII = (2.7, 2.3, 1.8, 1.3, 0.8)
MANDIBLE_SIDES = 6
MANDIBLE_COLLARS = (1, 2)
COLLAR_GROWTH = 0.8
COLLAR_LENGTH = 1.6
FANG_CORE_RADIUS = 0.6

CONDUIT = ((-19, 4, 186), (-14, 13, 184), (-2, 17, 182), (8, 16, 180), (13, 12.5, 177))
CONDUIT_RADIUS = 1.3
CONDUIT_SIDES = 5
CONDUIT_COLLARS = (1, 3)
CONDUIT_ALPHA = 110
RESERVOIR = ((-19.5, 0, 186), 3.2)
DROP = ((30, 6, 171.5), 1.4)
DROP_ALPHA = 80

SHELL_HSL = hsl(28, 1, 45)
SHELL_LOW_HSL = hsl(28, 1, 34)
SHELL_TOP_HSL = hsl(28, 1, 52)
VISOR_HSL = hsl(28, 1, 26)
EDGE_HSL = hsl(41, 1, 96)
EDGE_DARK_HSL = hsl(41, 1, 70)
EYE_HSL = hsl(21, 7, 78)
FANG_CORE_HSL = hsl(21, 7, 80)
FANG_INNER_HSL = hsl(28, 1, 14)
COLLAR_HSL = hsl(41, 1, 58)


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


def ring_point(ring, k, nape=False):
    up, half_width, front, back = ring
    angle = 2 * math.pi * k / SHELL_SEGMENTS
    c, s = math.cos(angle), math.sin(angle)
    fwd = front * c if c >= 0 else back * c
    if nape and c < -0.3:
        up -= NAPE_DROP * (-c)
    return fwd, half_width * s, up


def build_shell(collection, label, collar, transform):
    """Faceted ellipsoid rings pinched at the jaw and brow, closed at the apex and sealed at the
    bottom to the neck collar."""
    verts, labels, faces, colors = [], [], [], []
    rings = []
    for index, ring in enumerate(SHELL_RINGS):
        rings.append(list(range(len(verts), len(verts) + SHELL_SEGMENTS)))
        for k in range(SHELL_SEGMENTS):
            verts.append(ring_point(ring, k, nape=index == 0))
            labels.append(label)
    apex = len(verts)
    verts.append((SHELL_APEX[0], 0.0, SHELL_APEX[1]))
    labels.append(label)

    ring_colors = (SHELL_LOW_HSL, SHELL_HSL, SHELL_HSL, SHELL_HSL, SHELL_TOP_HSL)
    for r in range(len(rings) - 1):
        for k in range(SHELL_SEGMENTS):
            a, b = rings[r][k], rings[r][(k + 1) % SHELL_SEGMENTS]
            c, d = rings[r + 1][(k + 1) % SHELL_SEGMENTS], rings[r + 1][k]
            faces += [(a, b, c), (a, c, d)]
            colors += [ring_colors[r]] * 2
    for k in range(SHELL_SEGMENTS):
        faces.append((rings[-1][k], rings[-1][(k + 1) % SHELL_SEGMENTS], apex))
        colors.append(SHELL_TOP_HSL)

    collar_ids = []
    for point, collar_label in collar:
        collar_ids.append(len(verts))
        verts.append(point)
        labels.append(collar_label if label != INVENTORY_LABEL else INVENTORY_LABEL)
    rim = rings[0]
    faces += stitch(verts, rim, collar_ids)
    colors += [SHELL_LOW_HSL] * (len(faces) - len(colors))
    for i in range(1, len(collar_ids) - 1):
        faces.append((collar_ids[0], collar_ids[i], collar_ids[i + 1]))
        colors.append(SHELL_LOW_HSL)
    return make(collection, "Shell", verts, faces, colors, labels, transform,
                fixed=set(collar_ids))


def angle_of(point):
    fwd, left, _ = point
    return math.atan2(left, fwd) % (2 * math.pi)


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


def unwrap(angle, index, count):
    return angle + (2 * math.pi if index >= count else 0)


def prism(path, half_widths, thickness_up, colors_top, color_side):
    """A bar along ``path`` with a square section, used for the brow ridge."""
    verts, faces, colors = [], [], []
    for point, half in zip(path, half_widths):
        fwd, left, up = point
        verts += [(fwd + half, left, up + thickness_up), (fwd + half, left, up - thickness_up),
                  (fwd - half, left, up - thickness_up), (fwd - half, left, up + thickness_up)]
    for s in range(len(path) - 1):
        a, b = 4 * s, 4 * (s + 1)
        for k in range(4):
            faces.append((a + k, a + (k + 1) % 4, b + (k + 1) % 4, b + k))
            colors.append(colors_top if k in (3, 0) else color_side)
    faces += [(0, 1, 2, 3), tuple(4 * (len(path) - 1) + k for k in (3, 2, 1, 0))]
    colors += [color_side, color_side]
    return verts, faces, colors


def mirrored(point):
    fwd, left, up = point
    return fwd, -left, up


def build_visor(collection, label, transform):
    """V-shaped brow ridge meeting in a point over the nose, glowing slits slanting up to the
    temples, and a keel-shaped chin prow."""
    temple, apex = BROW_POINTS
    brow = (temple, apex, mirrored(temple))
    verts, faces, colors = prism(brow, (BROW_DEPTH / 2,) * 3, BROW_THICKNESS / 2,
                                 EDGE_HSL, EDGE_DARK_HSL)
    make(collection, "Brow", verts, faces, colors, label, transform)

    for side in (1, -1):
        inner = (SLIT_INNER[0] + SLIT_LIFT, SLIT_INNER[1] * side, SLIT_INNER[2])
        outer = (SLIT_OUTER[0] + SLIT_LIFT, SLIT_OUTER[1] * side, SLIT_OUTER[2])
        h = SLIT_HEIGHT / 2
        glow = [(inner[0], inner[1], inner[2] - h), (outer[0], outer[1], outer[2] - h),
                (outer[0], outer[1], outer[2] + h), (inner[0], inner[1], inner[2] + h)]
        rim = [(x - 0.3, y * 1.0, z + (0.9 if i >= 2 else -0.9)) for i, (x, y, z) in enumerate(glow)]
        verts = glow + rim
        faces = [(0, 1, 2, 3), (4, 5, 1, 0), (7, 3, 2, 6), (4, 0, 3, 7), (1, 5, 6, 2)]
        colors = [EYE_HSL, VISOR_HSL, VISOR_HSL, VISOR_HSL, VISOR_HSL]
        make(collection, f"Slit{side}", verts, faces, colors, label, transform, recalc=False)

    top_fwd, top_up = PROW_TOP
    bottom_fwd, bottom_up = PROW_BOTTOM
    tip_fwd, tip_up = PROW_TIP
    w = PROW_HALF_WIDTH
    verts = [(top_fwd, w, top_up), (top_fwd, -w, top_up), (bottom_fwd, w, bottom_up),
             (bottom_fwd, -w, bottom_up), (tip_fwd, 0.0, tip_up),
             (top_fwd - 4, 0.0, (top_up + bottom_up) / 2)]
    faces = [(0, 4, 1), (2, 3, 4), (0, 2, 4), (1, 4, 3), (0, 1, 5), (3, 2, 5), (0, 5, 2), (1, 3, 5)]
    colors = [EDGE_HSL, EDGE_DARK_HSL, EDGE_HSL, EDGE_HSL, VISOR_HSL, VISOR_HSL, VISOR_HSL,
              VISOR_HSL]
    make(collection, "Prow", verts, faces, colors, label, transform)


def ellipse_reach(ring, fwd, left):
    """How far (fwd, left) lies out along the ring's ellipse: below 1 is inside the shell."""
    _, half_width, front, back = ring
    depth = front if fwd >= 0 else back
    return math.hypot(fwd / depth, left / half_width)


def surface_up(fwd, left):
    """Height of the shell's outer surface above (fwd, left), or None past its silhouette."""
    rings = list(SHELL_RINGS) + [(SHELL_APEX[1], 0.01, 0.01, 0.01)]
    for lower, upper in zip(reversed(rings[:-1]), reversed(rings[1:])):
        inner, outer = ellipse_reach(lower, fwd, left), ellipse_reach(upper, fwd, left)
        if inner <= 1 < outer:
            t = (1 - inner) / (outer - inner)
            return lower[0] + (upper[0] - lower[0]) * t
    return None


def ridge(stations, side=1):
    """A triangular fin along ``stations`` of (point, height, half base width); the last station
    is the sharp tip. On the shell the base follows its surface, sunk RIDGE_SINK below it so it
    never shows a gap; past the back of the helm the fin carries on as a free horn."""
    verts, faces, colors = [], [], []
    for point, height, half in stations:
        fwd, left, up = point
        left *= side
        surface = surface_up(fwd, left)
        if surface is not None:
            up = surface
        if half == 0:
            verts.append((fwd, left, up))
            continue
        verts += [(fwd, left + half, up - RIDGE_SINK), (fwd, left - half, up - RIDGE_SINK),
                  (fwd, left, up + height)]
    tip = len(verts) - 1
    sections = (len(verts) - 1) // 3
    for s in range(sections - 1):
        a, b = 3 * s, 3 * (s + 1)
        faces += [(a, b, b + 2, a + 2), (a + 1, a + 2, b + 2, b + 1), (a, a + 1, b + 1, b)]
        colors += [EDGE_HSL, EDGE_DARK_HSL, SHELL_LOW_HSL]
    last = 3 * (sections - 1)
    faces += [(last, tip, last + 2), (last + 1, last + 2, tip), (last, last + 1, tip),
              (0, 2, 1)]
    colors += [EDGE_HSL, EDGE_DARK_HSL, SHELL_LOW_HSL, EDGE_HSL]
    return verts, faces, colors


def build_ridges(collection, label, transform):
    verts, faces, colors = ridge(CENTRE_RIDGE)
    make(collection, "RidgeCentre", verts, faces, colors, label, transform)
    for side in (1, -1):
        verts, faces, colors = ridge(SIDE_RIDGE, side)
        make(collection, f"Ridge{side}", verts, faces, colors, label, transform)


def vectors(points, side):
    return [Vector((fwd, left * side, up)) for fwd, left, up in points]


def collar_ring(points, radii, index, growth, length, sides):
    centre = points[index]
    axis = (points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]).normalized()
    half = axis * (length / 2)
    return parts.tube([centre - half, centre + half], [radii[index] + growth] * 2, sides)


def build_mandibles(collection, label, transform):
    """Chelicera fangs: tapered hex tubes curving out, forward and back in toward the mouth, with
    two collars each and a hollow tip holding a glowing venom core."""
    for side in (1, -1):
        points = vectors(MANDIBLE, side)
        verts, faces = parts.tube(points, MANDIBLE_RADII, MANDIBLE_SIDES)
        colors = [EDGE_DARK_HSL] + [EDGE_HSL if f % 2 else EDGE_DARK_HSL
                                    for f in range(len(faces) - 2)] + [FANG_INNER_HSL]
        make(collection, f"Mandible{side}", [tuple(v) for v in verts], faces, colors, label,
             transform)
        for index in MANDIBLE_COLLARS:
            verts, faces = collar_ring(points, MANDIBLE_RADII, index, COLLAR_GROWTH,
                                       COLLAR_LENGTH, MANDIBLE_SIDES)
            make(collection, f"MandibleCollar{side}{index}", [tuple(v) for v in verts], faces,
                 COLLAR_HSL, label, transform)
        tip_axis = (points[-1] - points[-2]).normalized()
        verts, faces = parts.bulb(points[-1] + tip_axis * 0.2, FANG_CORE_RADIUS)
        make(collection, f"FangCore{side}", verts, faces, FANG_CORE_HSL, label, transform)


def build_conduits(collection, label, transform):
    """Translucent venom tubes from the back reservoir round the cheeks into each fang root."""
    centre, radius = RESERVOIR
    verts, faces = parts.bulb(Vector(centre), radius)
    make(collection, "Reservoir", verts, faces, COLLAR_HSL, label, transform)
    for side in (1, -1):
        points = vectors(CONDUIT, side)
        verts, faces = parts.tube(points, [CONDUIT_RADIUS] * len(points), CONDUIT_SIDES)
        make(collection, f"Conduit{side}", [tuple(v) for v in verts], faces, parts.POISON_HSL,
             label, transform, alpha=CONDUIT_ALPHA, face_label=CONDUIT_FACE_LABEL)
        for index in CONDUIT_COLLARS:
            verts, faces = collar_ring(points, [CONDUIT_RADIUS] * len(points), index,
                                       COLLAR_GROWTH, COLLAR_LENGTH, CONDUIT_SIDES)
            make(collection, f"ConduitCollar{side}{index}", [tuple(v) for v in verts], faces,
                 COLLAR_HSL, label, transform)
        (fwd, left, up), drop_radius = DROP
        verts, faces = parts.bulb(Vector((fwd, left * side, up)), drop_radius)
        make(collection, f"Drop{side}", verts, faces, parts.DRIP_HSL, label, transform,
             alpha=DROP_ALPHA, face_label=DROP_FACE_LABEL)


def finish(collection):
    for obj in collection.all_objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        split = obj.modifiers.new("HardEdges", "EDGE_SPLIT")
        angle = SHELL_EDGE_SPLIT_ANGLE if obj.name.startswith("Shell") else EDGE_SPLIT_ANGLE
        split.split_angle = math.radians(angle)


def new_collection(name):
    existing = bpy.data.collections.get(name)
    if existing is not None:
        for obj in list(existing.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(existing)
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


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


def build_helm(name, label, collar, transform):
    collection = new_collection(name)
    build_shell(collection, label, collar, transform)
    build_visor(collection, label, transform)
    build_ridges(collection, label, transform)
    build_mandibles(collection, label, transform)
    build_conduits(collection, label, transform)
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
    camera_data.ortho_scale = 0.75
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
        render_previews("VenomfangHelmMale", (0.02, 0, 1.47), args[2])
