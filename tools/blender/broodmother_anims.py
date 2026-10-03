"""Broodmother's frame map and sequences: stand (poison glow pulse), walk (8-leg gait),
attack, defend and death. Called by ``broodmother_build.py`` after the model export.

Labels match the build script: 0 body, 1 sac, 2 sac glow, 3 fangs, 4 fang glow,
10..17 legs (L1..L4, R1..R4), 20..27 the matching hip rings. Face labels 1/2 are the sac and
fang glow shells. The model faces south (-z); +x is her left side; y points down.
"""

import math
import os

from osrs_anim_export import (
    ALPHA, ORIGIN, ROTATE, SCALE, TRANSLATE, FrameMap, Sequence, Transform, encode_frame,
    write_rsanim, write_sequences,
)

FRAME_MAP_ID = 3000
FRAME_ARCHIVE = 16000

BODY_GROUP = (0, 1, 2, 3, 4)
LEGS = range(8)
LEFT_LEGS = range(4)
GAIT_A = (0, 5, 2, 7)
ALL_LABELS = BODY_GROUP + tuple(10 + leg for leg in LEGS) + tuple(20 + leg for leg in LEGS)


def _build_frame_map():
    transforms = [
        Transform(ORIGIN, ALL_LABELS),
        Transform(TRANSLATE, ALL_LABELS),
        Transform(TRANSLATE, BODY_GROUP),
    ]
    for leg in LEGS:
        transforms += [
            Transform(ORIGIN, (20 + leg,)),
            Transform(ROTATE, (10 + leg, 20 + leg)),
        ]
    transforms += [
        Transform(ORIGIN, (1, 2)),
        Transform(SCALE, (1, 2)),
        Transform(ORIGIN, (3, 4)),
        Transform(ROTATE, (3, 4)),
        Transform(ALPHA, (1,)),
        Transform(ALPHA, (2,)),
    ]
    return FrameMap(FRAME_MAP_ID, transforms)


FRAME_MAP = _build_frame_map()
T_ALL = 1
T_BODY = 2
T_SAC_SCALE = 20
T_FANGS = 22
T_SAC_GLOW = 23
T_FANG_GLOW = 24


def t_leg(leg):
    return 4 + leg * 2


assert FRAME_MAP.transforms[T_ALL].type == TRANSLATE
assert FRAME_MAP.transforms[T_BODY].type == TRANSLATE
assert all(FRAME_MAP.transforms[t_leg(leg)].labels == (10 + leg, 20 + leg) for leg in LEGS)
assert FRAME_MAP.transforms[T_SAC_SCALE].type == SCALE
assert FRAME_MAP.transforms[T_FANGS].labels == (3, 4)
assert FRAME_MAP.transforms[T_SAC_GLOW].labels == (1,)
assert FRAME_MAP.transforms[T_FANG_GLOW].labels == (2,)


def side(leg):
    return 1 if leg in LEFT_LEGS else -1


def leg_pose(leg, yaw=0.0, lift=0.0):
    """yaw > 0 swings the foot forward, lift > 0 raises it; both in rotation units."""
    return round(side(leg) * yaw), round(side(leg) * lift)


def frame(body=(0, 0, 0), whole=(0, 0, 0), legs=None, sac=(128, 128, 128), fangs=0,
          sac_glow=0, fang_glow=0):
    values = {}
    if any(whole):
        values[T_ALL] = whole
    if any(body):
        values[T_BODY] = body
    for leg, (yaw, lift) in (legs or {}).items():
        if yaw or lift:
            values[t_leg(leg)] = (0, yaw, lift)
    if sac != (128, 128, 128):
        values[T_SAC_SCALE] = sac
    if fangs:
        values[T_FANGS] = (fangs, 0, 0)
    if sac_glow:
        values[T_SAC_GLOW] = (sac_glow, 0, 0)
    if fang_glow:
        values[T_FANG_GLOW] = (fang_glow, 0, 0)
    return values


def wave(phase):
    return 0.5 - 0.5 * math.cos(2 * math.pi * phase)


def stand():
    frames = []
    for i in range(12):
        pulse = wave(i / 12)
        swell = 128 + round(18 * pulse)
        frames.append(frame(
            body=(0, -round(3 * pulse), 0),
            sac=(swell, 128 + round(6 * pulse), swell),
            sac_glow=-round(12 * pulse),
            fang_glow=-round(10 * wave(i / 12 + 0.25)),
        ))
    return Sequence("broodmother_stand", frames, [6] * 12)


def walk():
    frames = []
    for i in range(8):
        phase = i / 8
        legs = {}
        for leg in LEGS:
            offset = 0.0 if leg in GAIT_A else 0.5
            angle = 2 * math.pi * (phase + offset)
            legs[leg] = leg_pose(leg, yaw=11 * math.sin(angle), lift=6 * max(0.0, math.cos(angle)))
        frames.append(frame(
            body=(0, -round(5 * wave(phase * 2)), 0),
            legs=legs,
            sac_glow=-round(8 * wave(phase)),
            fang_glow=-round(6 * wave(phase + 0.5)),
        ))
    return Sequence("broodmother_walk", frames, [4] * 8)


def attack():
    keys = [
        # body z, body y, fang rotation, fang glow, front-leg lift
        (10, -6, -4, -4, 3),
        (20, -12, -8, -8, 6),
        (24, -14, -10, -12, 8),
        (-30, 0, 8, -20, 4),
        (-48, 6, 12, -22, 0),
        (-36, 4, 6, -16, 0),
        (-14, 2, 2, -8, 0),
        (0, 0, 0, -2, 0),
    ]
    frames = []
    for z, y, fang, glow, lift in keys:
        legs = {leg: leg_pose(leg, lift=lift) for leg in (0, 4)}
        frames.append(frame(body=(0, y, z), legs=legs, fangs=fang, fang_glow=glow,
                            sac_glow=glow // 2))
    return Sequence("broodmother_attack", frames, [3] * 8, max_loops=1)


def defend():
    frames = [frame(body=(0, y, z)) for z, y in ((6, -2), (12, -4), (8, -3), (2, -1))]
    return Sequence("broodmother_defend", frames, [4] * 4, max_loops=1)


def death():
    frames = []
    for i in range(10):
        t = i / 9
        legs = {leg: leg_pose(leg, yaw=-3 * t, lift=18 * t) for leg in LEGS}
        frames.append(frame(
            whole=(0, round(45 * t), 0),
            legs=legs,
            sac=(128 + round(20 * t), 128 - round(60 * t), 128 + round(20 * t)),
            sac_glow=round(10 * t),
            fang_glow=round(9 * t),
        ))
    return Sequence("broodmother_death", frames, [6] * 9 + [100], max_loops=1)


SEQUENCES = (stand, walk, attack, defend, death)


def generate(model, pack_dir):
    """pack_dir: the module's ``src/main/resources/pack`` directory."""
    sequences = [build() for build in SEQUENCES]
    frames = write_sequences(
        os.path.join(pack_dir, "configs", "broodmother_anims.toml"), FRAME_ARCHIVE, sequences
    )
    encoded = [encode_frame(FRAME_MAP, values) for values in frames]
    write_rsanim(os.path.join(pack_dir, "anims", "broodmother.rsanim"), FRAME_ARCHIVE, encoded)
    map_path = os.path.join(pack_dir, "anims", "framemaps", f"{FRAME_MAP_ID}.dat")
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    with open(map_path, "wb") as handle:
        handle.write(FRAME_MAP.encode())
    print(f"Animations: {len(sequences)} sequences, {len(encoded)} frames, "
          f"frame map {FRAME_MAP_ID} ({len(FRAME_MAP.transforms)} transforms)")
    return sequences
