"""Export Blender meshes to the unversioned (footer-only) OSRS model format.

Every object in the target collection is evaluated at the current frame, transformed to
world space and merged into one model. Per-face colours come from the integer face
attribute ``rs_color`` (16-bit OSRS HSL); faces without it fall back to ``DEFAULT_COLOR``.

Blender is Z-up; OSRS is Y-down with models facing south (-Z). The build scripts model the
creature facing Blender +X, so the conversion is:

    rs_x =  blender_y * 128
    rs_y = -blender_z * 128
    rs_z = -blender_x * 128

1 Blender unit = 1 tile = 128 model units.

Usage (headless):
    blender --background --python tools/blender/osrs_model_export.py -- <collection> <out.dat>
"""

import struct
import sys

UNITS_PER_TILE = 128
DEFAULT_COLOR = 127
FLIP_WINDING = False


def _short_smart(value):
    if -64 <= value < 64:
        return bytes([value + 64])
    if -16384 <= value < 16384:
        return struct.pack(">H", value + 49152)
    raise ValueError(f"delta {value} out of short smart range")


def encode_model(vertices, faces, colors, priority=0):
    """vertices: [(x, y, z)] ints in model space; faces: [(a, b, c)]; colors: [hsl16]."""
    if len(vertices) > 0xFFFF or len(faces) > 0xFFFF:
        raise ValueError("model too large")

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
    for color in colors:
        face_colors += struct.pack(">H", color & 0xFFFF)

    body = (
        bytes(vertex_flags)
        + bytes(compress_types)
        + bytes(indices)
        + bytes(face_colors)
        + bytes(xs)
        + bytes(ys)
        + bytes(zs)
    )
    footer = struct.pack(
        ">HHBBBBBBHHHH",
        len(vertices),
        len(faces),
        0,
        0,
        priority,
        0,
        0,
        0,
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
    if has_fskin == 1:
        pos += fc
    if has_tex == 1:
        pos += fc
    if has_vskin == 1:
        pos += vc
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

    rx, ry, rz = reader(x_off), reader(y_off), reader(z_off)
    vertices = []
    last = [0, 0, 0]
    for i in range(vc):
        flag = data[flags_off + i]
        last = [
            last[0] + (rx() if flag & 1 else 0),
            last[1] + (ry() if flag & 2 else 0),
            last[2] + (rz() if flag & 4 else 0),
        ]
        vertices.append(tuple(last))

    ri = reader(idx_off)
    faces = []
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
        faces.append((a, b, c))

    colors = [struct.unpack(">H", data[color_off + i * 2:color_off + i * 2 + 2])[0]
              for i in range(fc)]
    return vertices, faces, colors


def collect_collection(collection_name):
    import bpy

    collection = bpy.data.collections[collection_name]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertex_index = {}
    vertices, faces, colors = [], [], []

    for obj in collection.all_objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        attribute = mesh.attributes.get("rs_color")
        face_colors = (
            [value.value for value in attribute.data]
            if attribute is not None and attribute.domain == "FACE"
            else None
        )

        local_to_model = []
        for vertex in mesh.vertices:
            world = matrix @ vertex.co
            key = (
                round(world.y * UNITS_PER_TILE),
                round(-world.z * UNITS_PER_TILE),
                round(-world.x * UNITS_PER_TILE),
            )
            if key not in vertex_index:
                vertex_index[key] = len(vertices)
                vertices.append(key)
            local_to_model.append(vertex_index[key])

        for triangle in mesh.loop_triangles:
            a, b, c = (local_to_model[v] for v in triangle.vertices)
            if a == b or b == c or a == c:
                continue
            faces.append((a, c, b) if FLIP_WINDING else (a, b, c))
            colors.append(
                face_colors[triangle.polygon_index] if face_colors else DEFAULT_COLOR
            )

        evaluated.to_mesh_clear()

    return vertices, faces, colors


def export_collection(collection_name, out_path):
    vertices, faces, colors = collect_collection(collection_name)
    data = encode_model(vertices, faces, colors)
    with open(out_path, "wb") as handle:
        handle.write(data)

    decoded = decode_model(data)
    assert decoded == (vertices, faces, colors), "round trip mismatch"
    print(f"Exported {collection_name}: {len(vertices)} vertices, {len(faces)} faces, "
          f"{len(data)} bytes -> {out_path}")
    return len(vertices), len(faces)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    export_collection(args[0], args[1])
