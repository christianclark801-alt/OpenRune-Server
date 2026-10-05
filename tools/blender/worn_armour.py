"""Shared machinery for worn body armour (torso, legs, gloves, boots, amulets).

Pieces are authored once in male player space as (forward, left, up) points, 128 = one tile,
and every worn variant is derived from that geometry:

* Vertex labels come from the nearest vertex of vanilla reference models (body kits plus a
  matching vanilla armour piece), limited to the labels a part may use. Pivot labels are then
  swapped for followers that ride the same bone without defining its pivot: the player
  animations rotate each joint around the mean of every vertex carrying its origin labels, so
  bulky armour on those labels drags the shoulder, knee or ankle out of place.
* The pivots themselves come from loose anchor vertices copied verbatim from the vanilla
  piece, so the joints turn exactly where they do in rune armour.
* Female variants are warped with a per-label affine fit between the vanilla male and female
  references, blended by distance, and relabelled against the female references.
* Inventory models are the male geometry posed like the vanilla icons, unlabelled.

References are dumped with ``gradlew :or-cache:dumpAnimReference -Prefs=...`` into ``ref/``.
"""

import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

import poison_blades_build as parts
from poison_blades_build import hsl, int_attribute, material_for

UNITS = 128
EDGE_SPLIT_ANGLE = 30
REF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref")

PIVOT_FOLLOWERS = {
    2: 8, 94: 8,
    21: 18, 25: 24, 17: 20, 23: 26,
    29: 30, 40: 43, 42: 44, 35: 43, 34: 44, 37: 38, 31: 32,
    47: 38, 48: 32,
    27: 200, 28: 194,
    10: 8, 9: 11, 14: 16, 13: 15,
}
PIVOT_LABELS = frozenset(PIVOT_FOLLOWERS) - {94} | {0, 3}

CHITIN_HSL = hsl(24, 3, 30)
CHITIN_LOW_HSL = hsl(24, 3, 22)
CHITIN_TOP_HSL = hsl(24, 3, 40)
CHITIN_EDGE_HSL = hsl(24, 3, 16)
OBSIDIAN_HSL = hsl(42, 2, 14)
OBSIDIAN_TOP_HSL = hsl(42, 2, 24)
OBSIDIAN_EDGE_HSL = hsl(42, 2, 8)
SOCKET_HSL = hsl(24, 2, 9)
VENOM_HSL = hsl(21, 7, 82)
VENOM_DIM_HSL = hsl(21, 7, 52)
TOXIC_HSL = hsl(50, 5, 48)
TOXIC_DARK_HSL = hsl(50, 5, 30)
BONE_HSL = hsl(8, 2, 104)
BONE_SHADOW_HSL = hsl(8, 2, 76)
NECROTIC_HSL = hsl(19, 7, 92)
NECROTIC_DIM_HSL = hsl(19, 6, 56)
SHROUD_HSL = hsl(50, 1, 22)
SHROUD_EDGE_HSL = hsl(50, 1, 13)
SHADOW_HSL = hsl(0, 0, 3)


def load_ref(name):
    """A dumped model as ``[(point, label)]`` in (forward, left, up) player space."""
    with open(os.path.join(REF_DIR, name + ".json")) as handle:
        data = json.load(handle)
    return [((-z, x, -y), label) for (x, y, z), label in zip(data["vertices"], data["labels"])]


class Part:
    """One mesh piece: faces wound outward, one colour and priority per face, and ``allowed``
    restricting which reference labels its vertices may take (``None`` = any). ``fixed`` maps a
    vertex index to a label that skips the transfer. ``worn_only`` parts are left out of the
    inventory model."""

    def __init__(self, name, priority, allowed=None, worn_only=False):
        self.name = name
        self.priority = priority
        self.allowed = allowed
        self.worn_only = worn_only
        self.verts = []
        self.faces = []
        self.colors = []
        self.priorities = []
        self.alphas = []
        self.emissive = []
        self.fixed = {}
        self.closed = False

    def vert(self, point):
        self.verts.append(tuple(point))
        return len(self.verts) - 1

    def face(self, indices, color, priority=None, outward=None, alpha=0, emissive=False):
        """``outward`` is a point the face must turn away from; without it the winding is
        kept, or fixed later for closed parts."""
        if outward is not None:
            a, b, c = (Vector(self.verts[i]) for i in indices[:3])
            normal = (b - a).cross(c - a)
            centre = sum((Vector(self.verts[i]) for i in indices), Vector()) / len(indices)
            if normal.dot(centre - Vector(outward)) < 0:
                indices = tuple(reversed(indices))
        self.faces.append(tuple(indices))
        self.colors.append(color)
        self.priorities.append(self.priority if priority is None else priority)
        self.alphas.append(alpha)
        self.emissive.append(emissive)


class Rig:
    """Label transfer and female warp for one armour slot."""

    def __init__(self, male_refs, female_refs, male_anchor_refs, female_anchor_refs,
                 anchor_labels=PIVOT_LABELS):
        """``anchor_labels`` can add non-pivot labels whose vanilla vertices must still be
        copied, e.g. a hat's neck ring, which takes over the torso's neck vertices when the
        client shares equal positions."""
        self.male = [v for name in male_refs for v in load_ref(name) if v[1] != 0]
        self.female = [v for name in female_refs for v in load_ref(name) if v[1] != 0]
        self.male_anchors = [v for name in male_anchor_refs for v in load_ref(name)
                             if v[1] in anchor_labels]
        self.female_anchors = [v for name in female_anchor_refs for v in load_ref(name)
                               if v[1] in anchor_labels]
        self.fits = self._fit_labels()

    def _fit_labels(self):
        def boxes(points):
            groups = {}
            for point, label in points:
                groups.setdefault(label, []).append(point)
            return {label: ([min(p[i] for p in ps) for i in range(3)],
                            [max(p[i] for p in ps) for i in range(3)]) for label, ps in groups.items()}

        male, female = boxes(self.male), boxes(self.female)
        fits = []
        for label in male.keys() & female.keys():
            (m_lo, m_hi), (f_lo, f_hi) = male[label], female[label]
            m_centre = [(a + b) / 2 for a, b in zip(m_lo, m_hi)]
            f_centre = [(a + b) / 2 for a, b in zip(f_lo, f_hi)]
            scale = []
            for i in range(3):
                m_ext, f_ext = m_hi[i] - m_lo[i], f_hi[i] - f_lo[i]
                scale.append(min(max(f_ext / m_ext, 0.6), 1.3) if m_ext >= 4 and f_ext >= 2 else 1.0)
            fits.append((m_centre, f_centre, scale))
        return fits

    def warp(self, point):
        total, moved = 0.0, [0.0, 0.0, 0.0]
        for m_centre, f_centre, scale in self.fits:
            weight = 1.0 / (math.dist(point, m_centre) ** 2 + 4.0) ** 2
            total += weight
            for i in range(3):
                moved[i] += weight * (f_centre[i] + (point[i] - m_centre[i]) * scale[i])
        return tuple(m / total for m in moved)

    @staticmethod
    def _nearest(point, refs, allowed):
        best, best_distance = None, math.inf
        for ref_point, label in refs:
            if allowed is not None and label not in allowed:
                continue
            distance = math.dist(point, ref_point)
            if distance < best_distance:
                best, best_distance = label, distance
        assert best is not None, f"no reference label in {allowed} near {point}"
        return PIVOT_FOLLOWERS.get(best, best)

    def male_label(self, point, allowed):
        return self._nearest(point, self.male, allowed)

    def female_label(self, point, allowed):
        return self._nearest(point, self.female, allowed)


def grounded(pose, part_list):
    """``pose`` shifted so the lowest posed vertex rests on the ground, like vanilla icons."""
    lowest = min(pose(v)[2] for part in part_list if not part.worn_only for v in part.verts)
    return lambda point: (lambda p: (p[0], p[1], p[2] - lowest))(pose(point))


def place(point):
    return Vector(tuple(c / UNITS for c in point))


def make_object(collection, name, verts, faces, colors, priorities, labels, closed, alphas=(),
                emissive=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([place(v) for v in verts], [], faces)
    mesh.update()
    if closed:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if faces:
        int_attribute(mesh, "rs_color", "FACE", colors)
        int_attribute(mesh, "rs_priority", "FACE", priorities)
    if any(alphas):
        int_attribute(mesh, "rs_alpha", "FACE", alphas)
    int_attribute(mesh, "rs_label", "POINT", labels)
    palette = []
    glows = list(emissive) or [False] * len(colors)
    for polygon, value, glow in zip(mesh.polygons, colors, glows):
        key = (value, glow)
        if key not in palette:
            palette.append(key)
            mesh.materials.append(material_for(value, max(alphas, default=0), glow))
        polygon.material_index = palette.index(key)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    split = obj.modifiers.new("HardEdges", "EDGE_SPLIT")
    split.split_angle = math.radians(EDGE_SPLIT_ANGLE)
    return obj


def new_collection(name):
    existing = bpy.data.collections.get(name)
    if existing is not None:
        for obj in list(existing.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(existing)
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def build_anchors(collection, points, priority):
    """The client only keeps vertices a face references when it merges worn models, so each
    pivot anchor is three coincident vertices joined by a zero-area triangle: kept, never
    drawn, and folded back into one vertex by the client's position sharing."""
    verts, faces, labels = [], [], []
    for point, label in points:
        faces.append(tuple(range(len(verts), len(verts) + 3)))
        verts += [point] * 3
        labels += [label] * 3
    make_object(collection, "Anchors", verts, faces, [OBSIDIAN_EDGE_HSL] * len(faces),
                [priority] * len(faces), labels, False)


def build_variant(name, part_list, rig, variant, pose=None, max_triangles=None, anchors=True):
    """``variant`` is "male", "female" or "inventory"; inventory parts go through ``pose``.
    Only one model per slot should carry the pivot ``anchors``."""
    collection = new_collection(name)
    for part in part_list:
        if variant == "inventory" and part.worn_only:
            continue
        if variant == "male":
            verts = part.verts
            labels = [part.fixed.get(i) or rig.male_label(v, part.allowed)
                      for i, v in enumerate(verts)]
        elif variant == "female":
            verts = [rig.warp(v) for v in part.verts]
            labels = [part.fixed.get(i) or rig.female_label(v, part.allowed)
                      for i, v in enumerate(verts)]
        else:
            verts = [pose(v) for v in part.verts]
            labels = [0] * len(verts)
        make_object(collection, part.name, verts, part.faces, part.colors, part.priorities,
                    labels, part.closed, part.alphas, part.emissive)
    if anchors and variant != "inventory":
        points = rig.male_anchors if variant == "male" else rig.female_anchors
        if points:
            lowest = min(p for part in part_list for p in part.priorities)
            build_anchors(collection, points, lowest)
    total = parts.triangles([o for o in collection.all_objects
                             if not o.name.startswith("Anchors")])
    if max_triangles is not None:
        assert total <= max_triangles, f"{name}: {total} triangles exceeds {max_triangles}"
    print(f"Built {name}: {len(collection.all_objects)} objects, {total} triangles")
    return collection


def ring_strip(part, rings, color_for, outward_for, closed_loop=True):
    """Quads between consecutive vertex loops ``rings`` (lists of indices)."""
    for r in range(len(rings) - 1):
        lower, upper = rings[r], rings[r + 1]
        count = len(lower) if closed_loop else len(lower) - 1
        for k in range(count):
            a, b = lower[k], lower[(k + 1) % len(lower)]
            c, d = upper[(k + 1) % len(upper)], upper[k]
            part.face((a, b, c, d), color_for(r, k), outward=outward_for(r, k))


BAND_LIFTS = (0.8, 2.3, 2.9, 0.6)


def band(part, surface, centre, top, bottom, thetas, colors, end_colors, lifts=BAND_LIFTS,
         ridge_at=0.45, tuck_rise=0.6):
    """One overlapping chitin band across ``thetas`` on ``surface(theta, up, lift)``: a sloped
    upper facet, a steeper lower facet flaring to the lip, and an underside tucked back to the
    surface that the next band down hides behind. ``colors`` holds the three facet colours, or
    is a ``(facet, column)`` function; ``end_colors`` paint the start and end caps (``None``
    for a band that wraps all the way round), and ``centre(up)`` is the axis every facet turns
    away from."""
    ridge = top - (top - bottom) * ridge_at
    tuck = bottom + tuck_rise
    rows = []
    for theta in thetas:
        rows.append([part.vert(surface(theta, up, lift))
                     for up, lift in zip((top, ridge, bottom, tuck), lifts)])
    paint = colors if callable(colors) else (lambda facet, column: colors[facet])
    for s in range(len(rows) - 1):
        a, b = rows[s], rows[s + 1]
        for k in range(3):
            part.face((a[k], b[k], b[k + 1], a[k + 1]), paint(k, s),
                      outward=centre((top + bottom) / 2))
    if end_colors is None:
        return
    for row, neighbour, color in ((rows[0], rows[1], end_colors[0]),
                                  (rows[-1], rows[-2], end_colors[1])):
        part.face(tuple(row), color, outward=part.verts[neighbour[1]])


def render_previews(collection_names, centre, out_dir, scale=0.9, views=None):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as error:
        print(f"Workbench unavailable, keeping {scene.render.engine}: {error}")
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = scene.render.resolution_y = 700
    for collection in bpy.data.collections:
        collection.hide_render = collection.name not in collection_names
    camera_data = bpy.data.cameras.get("ArmourCam") or bpy.data.cameras.new("ArmourCam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera = bpy.data.objects.get("ArmourCam") or bpy.data.objects.new("ArmourCam", camera_data)
    if camera.name not in scene.collection.objects:
        scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector(centre)
    views = views or (("front", (2, 0, 0.6)), ("three_quarter", (1.4, -1.4, 0.9)),
                      ("side", (0, -2, 0.3)), ("back", (-1.6, 1.0, 0.9)))
    for view, offset in views:
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(os.path.abspath(out_dir),
                                             f"{collection_names[0]}_{view}.png")
        bpy.ops.render.render(write_still=True)
    print(f"Rendered {collection_names[0]} previews -> {out_dir}")


def export(models, out_dir, priority):
    import osrs_model_export

    os.makedirs(out_dir, exist_ok=True)
    for collection_name, file_name in models:
        model = osrs_model_export.export_collection(
            collection_name, os.path.join(out_dir, file_name), merge_vertices=False,
            priority=priority)
        used = {i for face in model.faces for i in face}
        unused = len(model.vertices) - len(used)
        assert not unused, f"{file_name}: {unused} vertices no face uses; the client drops them"
