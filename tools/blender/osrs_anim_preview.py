"""Render frames of exported OSRS animations headless, posed with the client's transform maths.

Usage:
    blender --background --factory-startup --python tools/blender/osrs_anim_preview.py -- \
        <model.dat> <anims module> <out dir> [sequence[:frame,frame...]] ...

e.g. ``... -- broodmother.dat broodmother_anims out walk:0,2,4,6 death:9``. Without
sequence arguments the first, middle and last frame of every sequence are rendered.
"""

import colorsys
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osrs_anim_export import apply_frame  # noqa: E402
from osrs_model_export import UNITS_PER_TILE, decode_model  # noqa: E402

CAMERA_VIEWS = {
    "three_quarter": (6.5, -6.0, 4.5),
    "side": (0.0, -8.5, 1.8),
}


def hsl_to_rgb(value):
    hue = ((value >> 10) & 63) / 64 + 1 / 128
    saturation = ((value >> 7) & 7) / 8 + 1 / 16
    lightness = (value & 127) / 128
    return colorsys.hls_to_rgb(hue, lightness, saturation)


def to_blender(vertex):
    x, y, z = vertex
    return (-z / UNITS_PER_TILE, x / UNITS_PER_TILE, -y / UNITS_PER_TILE)


def material(color, alpha):
    name = f"preview_{color}_{alpha}"
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    created = bpy.data.materials.new(name)
    created.diffuse_color = hsl_to_rgb(color) + (1.0 - alpha / 255,)
    return created


def build_mesh(model, vertices, alphas):
    mesh = bpy.data.meshes.new("pose")
    mesh.from_pydata([to_blender(v) for v in vertices], [], model.faces)
    keys = []
    for color, alpha in zip(model.colors, alphas):
        key = (color, alpha)
        if key not in keys:
            keys.append(key)
            mesh.materials.append(material(color, alpha))
    for polygon in mesh.polygons:
        polygon.material_index = keys.index((model.colors[polygon.index], alphas[polygon.index]))
        polygon.use_smooth = model.render_types[polygon.index] != 1
    obj = bpy.data.objects.new("pose", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x = 480
    scene.render.resolution_y = 360
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def render(scene, camera, path):
    target = Vector((0.0, 0.0, 1.0))
    for view, position in CAMERA_VIEWS.items():
        camera.location = position
        camera.rotation_euler = (target - Vector(position)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = f"{path}_{view}.png"
        bpy.ops.render.render(write_still=True)


def selection(sequences, args):
    if not args:
        return [(s, sorted({0, len(s.frames) // 2, len(s.frames) - 1})) for s in sequences]
    chosen = []
    by_suffix = {s.name.split("_", 1)[-1]: s for s in sequences}
    for arg in args:
        name, _, frames = arg.partition(":")
        sequence = by_suffix.get(name) or next(s for s in sequences if s.name == name)
        indices = [int(f) for f in frames.split(",")] if frames else range(len(sequence.frames))
        chosen.append((sequence, list(indices)))
    return chosen


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    model_path, module_name, out_dir = args[:3]
    anims = importlib.import_module(module_name)
    with open(model_path, "rb") as handle:
        model = decode_model(handle.read())
    sequences = [build() for build in anims.SEQUENCES]
    scene, camera = setup_scene()
    os.makedirs(out_dir, exist_ok=True)
    for sequence, indices in selection(sequences, args[3:]):
        for index in indices:
            vertices, alphas = apply_frame(model, anims.FRAME_MAP, sequence.frames[index])
            obj = build_mesh(model, vertices, alphas)
            render(scene, camera, os.path.join(out_dir, f"{sequence.name}_{index:02d}"))
            bpy.data.objects.remove(obj, do_unlink=True)
    print(f"Rendered previews to {out_dir}")


main()
