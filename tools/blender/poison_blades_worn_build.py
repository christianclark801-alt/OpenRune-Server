"""Builds the Poison Blades worn model: one blade per hand, reusing the item model's parts.

Placement copies the Dual macuahuitl's worn model (dumped by ``gradlew dumpAnimReference``):
each blade is gripped at the hand, points forward and is labelled with the player skeleton's
weapon label for that hand (27 right, 28 left) so it follows the arm in every player animation.

Usage:
    blender --background --python tools/blender/poison_blades_worn_build.py -- [out.blend] [out.dat] [preview.png]
"""

import math
import os
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import poison_blades_build as parts  # noqa: E402

COLLECTION = "PoisonBladesWorn"
MAX_TRIANGLES = 1600
SCALE = 0.6
GRIP_CENTER = (parts.GRIP_START + parts.GRIP_END) / 2
HAND_HEIGHT = 100 / 128
HAND_SPREAD = 31 / 128
RIGHT_HAND_LABEL = 27
LEFT_HAND_LABEL = 28


def hand_matrix(index):
    """Right blade (index 0) at -Y, left at +Y; blade flats stand upright, spine on top."""
    y = -HAND_SPREAD if index == 0 else HAND_SPREAD
    roll = math.radians(-90 if index == 0 else 90)
    return (
        Matrix.Translation((0, y, HAND_HEIGHT))
        @ Matrix.Scale(SCALE, 4)
        @ Matrix.Translation((-GRIP_CENTER, 0, 0))
        @ Matrix.Rotation(roll, 4, "X")
    )


def build():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    parts.COLLECTION = COLLECTION
    parts.LABEL_BLADE = (RIGHT_HAND_LABEL, LEFT_HAND_LABEL)
    collection = parts.reset_collection()
    for index, side in ((0, 1), (1, -1)):
        matrix = hand_matrix(index)
        parts.build_blade(collection, index, side, matrix)
        parts.build_hooks(collection, index, side, matrix)
        parts.build_guard(collection, index, matrix)
        parts.build_grip(collection, index, matrix)
    total = parts.triangles(collection.all_objects)
    assert total <= MAX_TRIANGLES, f"{total} triangles exceeds budget of {MAX_TRIANGLES}"
    parts.finish(collection)
    print(f"Built {COLLECTION}: {len(collection.all_objects)} objects, {total} triangles")
    return collection


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    build()
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 1:
        import osrs_model_export

        dat_path = os.path.abspath(args[1])
        os.makedirs(os.path.dirname(dat_path), exist_ok=True)
        osrs_model_export.export_collection(COLLECTION, dat_path, merge_vertices=False)
    if len(args) > 2:
        parts.COLLECTION = COLLECTION
        parts.render_preview(args[2])
