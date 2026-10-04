"""Export Blender meshes to the unversioned (footer-only) OSRS model format.

Every object in the target collection is evaluated at the current frame, transformed to
world space and merged into one model. Optional mesh attributes drive the extra streams:

    rs_color  (FACE, int)  16-bit OSRS HSL colour; faces without it use ``DEFAULT_COLOR``
    rs_alpha  (FACE, int)  face transparency, 0 opaque .. 255 invisible
    rs_flabel (FACE, int)  face label, targeted by alpha (type 5) animation transforms
    rs_label  (POINT, int) vertex label, targeted by origin/translate/rotate/scale transforms

``flat_shading`` writes face render type 1 for every face, so the client shades each face flat
instead of Gouraud-smoothing across shared vertices. The client smooths per vertex index, so
``merge_vertices=False`` keeps every object's own vertices (including Edge Split seams) apart
instead of welding equal positions, which preserves hard edges under smooth shading.

Blender is Z-up; OSRS is Y-down with models facing south (-Z). The build scripts model the
creature facing Blender +X, so the conversion is:

    rs_x =  blender_y * 128
    rs_y = -blender_z * 128
    rs_z = -blender_x * 128

1 Blender unit = 1 tile = 128 model units.

Usage (headless):
    blender --background --python tools/blender/osrs_model_export.py -- <collection> <out.dat>
"""

import json
import struct
import sys
from dataclasses import dataclass, field

UNITS_PER_TILE = 128
DEFAULT_COLOR = 127
FLIP_WINDING = False


@dataclass
class RsModel:
    vertices: list = field(default_factory=list)
    vertex_labels: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    colors: list = field(default_factory=list)
    alphas: list = field(default_factory=list)
    face_labels: list = field(default_factory=list)
    render_types: list = field(default_factory=list)

    @property
    def has_vertex_labels(self):
        return any(self.vertex_labels)

    @property
    def has_face_labels(self):
        return any(self.face_labels)

    @property
    def has_alphas(self):
        return any(self.alphas)

    @property
    def has_render_types(self):
        return any(self.render_types)


def load_reference_model(*paths):
    """Merges models into one RsModel: ``.json`` dumps from ``gradlew dumpAnimReference`` and
    our own exported ``.dat`` files, e.g. a player's body kits plus a custom worn weapon."""
    model = RsModel()
    for path in paths:
        if path.endswith(".dat"):
            with open(path, "rb") as handle:
                part = decode_model(handle.read())
        else:
            with open(path) as handle:
                data = json.load(handle)
            faces = data["faces"]
            part = RsModel(
                [tuple(v) for v in data["vertices"]], data["labels"], [tuple(f) for f in faces],
                data["colors"], data["alphas"], data["faceLabels"], [0] * len(faces),
            )
        base = len(model.vertices)
        model.vertices += part.vertices
        model.vertex_labels += part.vertex_labels or [0] * len(part.vertices)
        model.faces += [tuple(i + base for i in face) for face in part.faces]
        model.colors += part.colors
        model.alphas += part.alphas or [0] * len(part.faces)
        model.face_labels += part.face_labels or [0] * len(part.faces)
        model.render_types += part.render_types or [0] * len(part.faces)
    return model


def _short_smart(value):
    if -64 <= value < 64:
        return bytes([value + 64])
    if -16384 <= value < 16384:
        return struct.pack(">H", value + 49152)
    raise ValueError(f"delta {value} out of short smart range")


def encode_model(model, priority=0):
    vertices, faces = model.vertices, model.faces
    if len(vertices) > 0xFFFF or len(faces) > 0xFFFF:
        raise ValueError("model too large")
    vertex_skins = model.has_vertex_labels
    face_skins = model.has_face_labels
    face_alphas = model.has_alphas
    render_types = model.has_render_types

    vertex_flags = bytearray()
    xs, ys, zs = bytearray(), bytearray(), bytearray()
    last = (0, 0, 0)
    for vertex in vertices:
        flag = 0
        for axis, stream, bit in ((0, xs, 1), (1, ys, 2), (2, zs, 4)):
            delta = vertex[axis] - last[axis]
            if delta != 0:
                flag |= bit
                stream += _short_smart(delta)
        vertex_flags.append(flag)
        last = vertex

    compress_types = bytearray()
    indices = bytearray()
    offset = 0
    for face in faces:
        compress_types.append(1)
        for vertex in face:
            indices += _short_smart(vertex - offset)
            offset = vertex

    face_colors = bytearray()
    for color in model.colors:
        face_colors += struct.pack(">H", color & 0xFFFF)

    body = bytes(vertex_flags) + bytes(compress_types)
    if face_skins:
        body += bytes(model.face_labels)
    if render_types:
        body += bytes(model.render_types)
    if vertex_skins:
        body += bytes(model.vertex_labels)
    if face_alphas:
        body += bytes(model.alphas)
    body += bytes(indices) + bytes(face_colors) + bytes(xs) + bytes(ys) + bytes(zs)

    footer = struct.pack(
        ">HHBBBBBBHHHH",
        len(vertices),
        len(faces),
        0,
        int(render_types),
        priority,
        int(face_alphas),
        int(face_skins),
        int(vertex_skins),
        len(xs),
        len(ys),
        len(zs),
        len(indices),
    )
    return body + footer


def decode_model(data):
    """Minimal decoder for the same unversioned layout; used to verify round trips."""
    (vc, fc, tex_count, has_tex, priority, has_alpha, has_fskin, has_vskin,
     x_len, y_len, _z_len, idx_len) = struct.unpack(">HHBBBBBBHHHH", data[-18:])
    pos = 0
    flags_off = pos
    pos += vc
    compress_off = pos
    pos += fc
    if priority == 0xFF:
        pos += fc
    fskin_off = pos
    if has_fskin == 1:
        pos += fc
    render_off = pos
    if has_tex == 1:
        pos += fc
    vskin_off = pos
    if has_vskin == 1:
        pos += vc
    alpha_off = pos
    if has_alpha == 1:
        pos += fc
    idx_off = pos
    pos += idx_len
    color_off = pos
    pos += fc * 2
    pos += tex_count * 6
    x_off = pos
    pos += x_len
    y_off = pos
    pos += y_len
    z_off = pos

    def reader(start):
        state = {"p": start}

        def smart():
            p = state["p"]
            peek = data[p]
            if peek < 128:
                state["p"] = p + 1
                return peek - 64
            state["p"] = p + 2
            return ((peek << 8) | data[p + 1]) - 49152

        return smart

    model = RsModel()
    rx, ry, rz = reader(x_off), reader(y_off), reader(z_off)
    last = [0, 0, 0]
    for i in range(vc):
        flag = data[flags_off + i]
        last = [
            last[0] + (rx() if flag & 1 else 0),
            last[1] + (ry() if flag & 2 else 0),
            last[2] + (rz() if flag & 4 else 0),
        ]
        model.vertices.append(tuple(last))
        model.vertex_labels.append(data[vskin_off + i] if has_vskin == 1 else 0)

    ri = reader(idx_off)
    a = b = c = offset = 0
    for i in range(fc):
        kind = data[compress_off + i]
        if kind == 1:
            a = ri() + offset
            b = ri() + a
            c = ri() + b
            offset = c
        elif kind == 2:
            b = c
            c = ri() + offset
            offset = c
        elif kind == 3:
            a = c
            c = ri() + offset
            offset = c
        elif kind == 4:
            a, b = b, a
            c = ri() + offset
            offset = c
        model.faces.append((a, b, c))
        model.colors.append(struct.unpack(">H", data[color_off + i * 2:color_off + i * 2 + 2])[0])
        model.face_labels.append(data[fskin_off + i] if has_fskin == 1 else 0)
        model.alphas.append(data[alpha_off + i] if has_alpha == 1 else 0)
        model.render_types.append(data[render_off + i] if has_tex == 1 else 0)
    return model


def _face_values(mesh, name):
    attribute = mesh.attributes.get(name)
    if attribute is None or attribute.domain != "FACE":
        return None
    return [value.value for value in attribute.data]


def _point_values(mesh, name):
    attribute = mesh.attributes.get(name)
    if attribute is None or attribute.domain != "POINT":
        return None
    return [value.value for value in attribute.data]


def collect_collection(collection_name, flat_shading=False, merge_vertices=True):
    import bpy

    collection = bpy.data.collections[collection_name]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertex_index = {}
    model = RsModel()

    for obj_index, obj in enumerate(sorted(collection.all_objects, key=lambda o: o.name)):
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        colors = _face_values(mesh, "rs_color")
        alphas = _face_values(mesh, "rs_alpha")
        face_labels = _face_values(mesh, "rs_flabel")
        labels = _point_values(mesh, "rs_label")

        local_to_model = []
        for vertex in mesh.vertices:
            world = matrix @ vertex.co
            position = (
                round(world.y * UNITS_PER_TILE),
                round(-world.z * UNITS_PER_TILE),
                round(-world.x * UNITS_PER_TILE),
            )
            label = labels[vertex.index] if labels else 0
            key = (position, label) if merge_vertices else (obj_index, vertex.index)
            if key not in vertex_index:
                vertex_index[key] = len(model.vertices)
                model.vertices.append(position)
                model.vertex_labels.append(label)
            local_to_model.append(vertex_index[key])

        for triangle in mesh.loop_triangles:
            a, b, c = (local_to_model[v] for v in triangle.vertices)
            if a == b or b == c or a == c:
                continue
            polygon = triangle.polygon_index
            model.faces.append((a, c, b) if FLIP_WINDING else (a, b, c))
            model.colors.append(colors[polygon] if colors else DEFAULT_COLOR)
            model.alphas.append(alphas[polygon] if alphas else 0)
            model.face_labels.append(face_labels[polygon] if face_labels else 0)
            model.render_types.append(1 if flat_shading else 0)

        evaluated.to_mesh_clear()

    return model


def export_collection(collection_name, out_path, flat_shading=False, merge_vertices=True):
    model = collect_collection(collection_name, flat_shading, merge_vertices)
    data = encode_model(model)
    with open(out_path, "wb") as handle:
        handle.write(data)

    decoded = decode_model(data)
    assert decoded == model, "round trip mismatch"
    print(f"Exported {collection_name}: {len(model.vertices)} vertices, {len(model.faces)} faces, "
          f"{len(data)} bytes -> {out_path}")
    return model


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    export_collection(args[0], args[1])
