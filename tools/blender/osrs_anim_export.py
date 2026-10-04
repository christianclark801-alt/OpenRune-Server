"""Encode classic (non-skeletal) OSRS animations: frame maps, frames and sequence configs.

A frame map is an ordered list of transforms, each acting on a set of labels:

    ORIGIN    (0) pivot = centroid of the labelled vertices (+ offset)
    TRANSLATE (1) move labelled vertices
    ROTATE    (2) rotate about the pivot; units of 8/2048 of a turn, applied Z, then X, then Y
    SCALE     (3) scale about the pivot; 128 = 1.0
    ALPHA     (5) face transparency += value * 8 on faces whose *face* label matches

A frame stores one value triple per transform it uses; unused transforms are skipped and the
client re-inserts the nearest preceding ORIGIN automatically. ``apply_frame`` mirrors the client
maths so poses can be previewed without a game client.
"""

import json
import math
import os
import struct
from dataclasses import dataclass

from osrs_model_export import RsModel, _short_smart

ORIGIN, TRANSLATE, ROTATE, SCALE, ALPHA = 0, 1, 2, 3, 5

_SINE = [int(65536.0 * math.sin(i * 0.0030679615)) for i in range(2048)]
_COSINE = [int(65536.0 * math.cos(i * 0.0030679615)) for i in range(2048)]


@dataclass(frozen=True)
class Transform:
    type: int
    labels: tuple


class FrameMap:
    def __init__(self, map_id, transforms):
        if len(transforms) > 255:
            raise ValueError("frame map holds at most 255 transforms")
        self.id = map_id
        self.transforms = transforms

    def encode(self):
        out = bytearray([len(self.transforms)])
        out += bytes(t.type for t in self.transforms)
        out += bytes(len(t.labels) for t in self.transforms)
        for transform in self.transforms:
            out += bytes(transform.labels)
        return bytes(out)


def load_reference_frame_map(path):
    """Loads a frame map dumped from the cache by ``gradlew dumpAnimReference``."""
    with open(path) as handle:
        data = json.load(handle)
    return FrameMap(data["id"], [Transform(t["type"], tuple(t["labels"])) for t in data["transforms"]])


def load_reference_frames(path):
    """Loads a dumped sequence as a list of ``{transform index: (x, y, z)}`` frames, filling
    components the frame leaves out with the transform default the client would use."""
    with open(path) as handle:
        data = json.load(handle)
    frames = []
    for frame in data["frames"]:
        values = {}
        for index, triple in frame["transforms"].items():
            values[int(index)] = tuple(triple)
        frames.append(values)
    return frames, data["frameDelays"]


def resolve_defaults(frame_map, values):
    """Replaces ``None`` components (left out of a cache frame) with the transform default."""
    resolved = {}
    for index, triple in values.items():
        default = _default(frame_map.transforms[index])
        resolved[index] = tuple(default if c is None else c for c in triple)
    return resolved


def _default(transform):
    return 128 if transform.type == SCALE else 0


def encode_frame(frame_map, values):
    """values: {transform index: (x, y, z)}; missing transforms are left untouched."""
    opcodes = bytearray()
    data = bytearray()
    for index, transform in enumerate(frame_map.transforms):
        triple = values.get(index)
        if triple is None:
            opcodes.append(0)
            continue
        default = _default(transform)
        opcode = 0
        for bit, component in zip((1, 2, 4), triple):
            if component != default:
                opcode |= bit
                data += _short_smart(int(component))
        opcodes.append(opcode)
    return struct.pack(">HB", frame_map.id, len(frame_map.transforms)) + bytes(opcodes) + bytes(data)


def write_rsanim(path, archive, frames):
    out = bytearray(b"RSAN")
    out += struct.pack(">BHH", 1, archive, len(frames))
    for file_id, data in enumerate(frames):
        out += struct.pack(">HH", file_id, len(data))
        out += data
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(out)


def _tdiv(a, b):
    return int(a / b)


def frame_id(archive, file_id):
    return (archive << 16) | file_id


def apply_frame(model, frame_map, values):
    """Returns (vertices, alphas) of ``model`` posed by one frame, using the client's maths."""
    xs = [v[0] for v in model.vertices]
    ys = [v[1] for v in model.vertices]
    zs = [v[2] for v in model.vertices]
    alphas = list(model.alphas)
    by_label = {}
    for index, label in enumerate(model.vertex_labels):
        by_label.setdefault(label, []).append(index)
    faces_by_label = {}
    for index, label in enumerate(model.face_labels):
        faces_by_label.setdefault(label, []).append(index)

    used = []
    last = -1
    for index, transform in enumerate(frame_map.transforms):
        if index not in values:
            continue
        if transform.type != ORIGIN:
            for j in range(index - 1, last, -1):
                if frame_map.transforms[j].type == ORIGIN:
                    used.append((j, (0, 0, 0)))
                    break
        used.append((index, values[index]))
        last = index

    ox = oy = oz = 0
    for index, (dx, dy, dz) in used:
        transform = frame_map.transforms[index]
        vertices = [v for label in transform.labels for v in by_label.get(label, [])]
        if transform.type == ORIGIN:
            if vertices:
                ox = dx + _tdiv(sum(xs[v] for v in vertices), len(vertices))
                oy = dy + _tdiv(sum(ys[v] for v in vertices), len(vertices))
                oz = dz + _tdiv(sum(zs[v] for v in vertices), len(vertices))
            else:
                ox, oy, oz = dx, dy, dz
        elif transform.type == TRANSLATE:
            for v in vertices:
                xs[v] += dx
                ys[v] += dy
                zs[v] += dz
        elif transform.type == ROTATE:
            ax, ay, az = (dx & 255) * 8, (dy & 255) * 8, (dz & 255) * 8
            for v in vertices:
                x, y, z = xs[v] - ox, ys[v] - oy, zs[v] - oz
                if az:
                    s, c = _SINE[az], _COSINE[az]
                    x, y = (y * s + x * c) >> 16, (y * c - x * s) >> 16
                if ax:
                    s, c = _SINE[ax], _COSINE[ax]
                    y, z = (y * c - z * s) >> 16, (y * s + z * c) >> 16
                if ay:
                    s, c = _SINE[ay], _COSINE[ay]
                    x, z = (z * s + x * c) >> 16, (z * c - x * s) >> 16
                xs[v], ys[v], zs[v] = x + ox, y + oy, z + oz
        elif transform.type == SCALE:
            for v in vertices:
                xs[v] = _tdiv((xs[v] - ox) * dx, 128) + ox
                ys[v] = _tdiv((ys[v] - oy) * dy, 128) + oy
                zs[v] = _tdiv((zs[v] - oz) * dz, 128) + oz
        elif transform.type == ALPHA:
            for label in transform.labels:
                for face in faces_by_label.get(label, []):
                    alphas[face] = max(0, min(255, alphas[face] + dx * 8))

    return list(zip(xs, ys, zs)), alphas


@dataclass
class Sequence:
    name: str
    frames: list
    delays: list
    max_loops: int = 99
    inherit: str = None


def write_sequences(toml_path, archive, sequences):
    """Writes every frame into one archive and an ``[[animation]]`` toml for the sequences."""
    lines = ["# Generated by tools/blender/osrs_anim_export.py - do not edit by hand.", ""]
    all_frames = []
    for sequence in sequences:
        start = len(all_frames)
        all_frames.extend(sequence.frames)
        ids = [frame_id(archive, start + i) for i in range(len(sequence.frames))]
        lines += [
            "[[animation]]",
            f'id = "seq.{sequence.name}"',
            *([f'inherit = "{sequence.inherit}"'] if sequence.inherit else []),
            f"frameIDs = [{', '.join(map(str, ids))}]",
            f"frameDelays = [{', '.join(map(str, sequence.delays))}]",
            f"maxLoops = {sequence.max_loops}",
            "",
        ]
    os.makedirs(os.path.dirname(toml_path), exist_ok=True)
    with open(toml_path, "w", newline="\n") as handle:
        handle.write("\n".join(lines))
    return all_frames
