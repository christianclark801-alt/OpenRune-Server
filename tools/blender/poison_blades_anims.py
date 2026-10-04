"""Poison Blades X-slash: the player's attack seq (frames on the cache's player frame map 0)
and the slash effect spotanim (its own model and frame map). Both sequences share frame timing:
2 windup frames (blades behind the back), 8 slash frames, 4 follow-through and 6 reset frames.
The effect shows motion-blur ghosts during the slash, green trails that linger 10 frames after
it, and drips falling off the tips during the reset.

The player frame map and body kits come from ``tools/blender/ref``; run
``gradlew :or-cache:dumpAnimReference -Prefs=obj.dual_macuahuitl,seq.pmoon_macuahuitl_crush,seq.human_ready,idk.0,idk.10,idk.18,idk.26,idk.33,idk.36,idk.42``
first, and ``poison_blades_worn_build.py`` to export the worn model. Then:

    python tools/blender/poison_blades_anims.py

Rotations are in frame units (256 per turn) applied Z, X, Y about world axes; the player is
Y-down, faces -Z, and +X is their left. The arm poses were solved against hand/elbow/tip targets
by simulating the client maths on the dumped skeleton.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osrs_anim_export import (  # noqa: E402
    ALPHA, ORIGIN, TRANSLATE, FrameMap, Sequence, Transform, apply_frame, encode_frame,
    load_reference_frame_map, write_rsanim, write_sequences,
)
from osrs_model_export import RsModel, encode_model, load_reference_model  # noqa: E402

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(TOOLS_DIR, "ref")
PACK_DIR = os.path.join(
    TOOLS_DIR, "..", "..", "content", "skills", "poison-mastery", "pack", "src", "main",
    "resources", "pack",
)
WORN_MODEL = os.path.join(PACK_DIR, "models", "poison_blades_worn.dat")
PLAYER_FRAME_ARCHIVE = 16001
FX_FRAME_ARCHIVE = 16002
FX_FRAME_MAP_ID = 3001

T_TORSO = 7
T_RIGHT_SHOULDER, T_RIGHT_ELBOW, T_RIGHT_WRIST = 30, 32, 35
T_LEFT_SHOULDER, T_LEFT_ELBOW, T_LEFT_WRIST = 22, 24, 27

WINDUP_FRAMES = 2
SLASH_FRAMES = 8
FOLLOW_FRAMES = 4
RESET_FRAMES = 6
LEFT_LAG = 0.12
DELAYS = [4, 3] + [2] * SLASH_FRAMES + [3] * FOLLOW_FRAMES + [4] * RESET_FRAMES
SLASH_START = WINDUP_FRAMES
LINGER_START = WINDUP_FRAMES + SLASH_FRAMES
RESET_START = LINGER_START + FOLLOW_FRAMES
FRAME_COUNT = RESET_START + RESET_FRAMES

READY = {"shoulder": (16, 0, 0), "elbow": (-34, 0, 0), "wrist": (0, -8, 0), "torso": (0, 0, 0)}
BEHIND_BACK = {"shoulder": (12, 30, -111), "elbow": (41, 69, 32), "wrist": (0, 0, 0),
               "torso": (6, 0, 0)}
CROSSING = {"shoulder": (-60, -20, 0), "elbow": (17, -7, -9), "wrist": (0, 0, 0),
            "torso": (-4, 0, 0)}
CROSSED_LOW = {"shoulder": (-34, -20, 0), "elbow": (39, -4, -23), "wrist": (0, 0, 0),
               "torso": (-8, 0, 0)}

BLADE_LABELS = (27, 28)
BLUR_GHOSTS = 3
BLUR_WIDTH = 7
GHOST_ALPHAS = (200, 160, 120)
TRAIL_START = 0.55
TRAIL_SPLIT = 0.8
TRAIL_FIRST_FRAME = 3
TRAIL_STEPS = 4
TRAIL_ALPHA = 80
LINGER_FRAMES = 10
TRAIL_FADE_FRAMES = 3
DRIP_SPAWNS = (RESET_START - 1, RESET_START + 1, RESET_START + 3)
DRIP_FALL = (0, 10, 24, 42)
DRIP_RADIUS = 3
DRIP_ALPHA = 60
HIDDEN = 255

GHOST_HSL = (41 << 10) | (1 << 7) | 112
TRAIL_INNER_HSL = (22 << 10) | (7 << 7) | 70
TRAIL_OUTER_HSL = (21 << 10) | (7 << 7) | 100
DRIP_HSL = (21 << 10) | (7 << 7) | 88

BLUR_LABEL_BASE = 1
TRAIL_LABEL_BASE = 60
DRIP_LABEL_BASE = 100

_frame_map = None


def player_frame_map():
    global _frame_map
    if _frame_map is None:
        path = os.path.join(REF_DIR, "framemap_0.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} missing - run gradlew :or-cache:dumpAnimReference")
        _frame_map = load_reference_frame_map(path)
    return _frame_map


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ease(t):
    return t * t * (3 - 2 * t)


def blend(pose_a, pose_b, t):
    return {key: lerp(pose_a[key], pose_b[key], ease(t)) for key in pose_a}


def mirror(rotation):
    x, y, z = rotation
    return x, -y, -z


def player_frame(right, left):
    """Both arms posed; the left arm mirrors its pose across the body. Torso follows the right."""
    return {
        T_TORSO: right["torso"],
        T_RIGHT_SHOULDER: right["shoulder"],
        T_RIGHT_ELBOW: right["elbow"],
        T_RIGHT_WRIST: right["wrist"],
        T_LEFT_SHOULDER: mirror(left["shoulder"]),
        T_LEFT_ELBOW: mirror(left["elbow"]),
        T_LEFT_WRIST: mirror(left["wrist"]),
    }


def slash_pose(t):
    if t < 0.5:
        return blend(BEHIND_BACK, CROSSING, t * 2)
    return blend(CROSSING, CROSSED_LOW, (t - 0.5) * 2)


def slash_progress(blade, step):
    """Slash progress (0..1) of a blade at ``step`` slash frames in; the left blade lags."""
    t = step / SLASH_FRAMES
    return t if blade == 0 else max(0.0, t - LEFT_LAG)


def slash_frame_values(step):
    return player_frame(slash_pose(slash_progress(0, step)), slash_pose(slash_progress(1, step)))


def reset_frame_values(i):
    pose = blend(CROSSED_LOW, READY, (i + 1) / RESET_FRAMES)
    return player_frame(pose, pose)


def xslash():
    frames = []
    for i in range(WINDUP_FRAMES):
        pose = blend(READY, BEHIND_BACK, (i + 1) / WINDUP_FRAMES)
        frames.append(player_frame(pose, pose))
    frames += [slash_frame_values(i + 1) for i in range(SLASH_FRAMES)]
    frames += [player_frame(CROSSED_LOW, CROSSED_LOW)] * FOLLOW_FRAMES
    frames += [reset_frame_values(i) for i in range(RESET_FRAMES)]
    return Sequence("poison_blades_xslash", frames, DELAYS, max_loops=1,
                    inherit="seq.pmoon_macuahuitl_crush")


SEQUENCES = (xslash,)


def __getattr__(name):
    if name == "FRAME_MAP":
        return player_frame_map()
    raise AttributeError(name)


class BladeTracker:
    """Poses the player (body kits + worn blades) to read where each blade's root and tip are.
    Marker vertices carrying the blade labels ride along with the arms."""

    def __init__(self):
        kits = sorted(glob.glob(os.path.join(REF_DIR, "model_*.json")))
        if not kits:
            raise FileNotFoundError("No body kits in tools/blender/ref - run dumpAnimReference")
        self.model = load_reference_model(*kits, WORN_MODEL)
        self.markers = []
        for label in BLADE_LABELS:
            blade = [v for v, l in zip(self.model.vertices, self.model.vertex_labels) if l == label]
            tip = min(blade, key=lambda v: v[2])
            pommel = max(blade, key=lambda v: v[2])
            root = (tip[0], round((tip[1] + pommel[1]) / 2),
                    round(pommel[2] + (tip[2] - pommel[2]) * 0.3))
            start = len(self.model.vertices)
            self.model.vertices += [root, tip]
            self.model.vertex_labels += [label, label]
            self.markers.append((start, start + 1))

    def blades(self, values):
        """[(root, tip)] per blade for one player frame."""
        vertices, _ = apply_frame(self.model, player_frame_map(), values)
        return [(vertices[r], vertices[t]) for r, t in self.markers]

    def at_slash_step(self, step):
        return self.blades(slash_frame_values(step))


def along(root, tip, fraction):
    return tuple(r + (t - r) * fraction for r, t in zip(root, tip))


def shifted(point, offset, sign):
    return tuple(p + o * sign for p, o in zip(point, offset))


class FxBuilder:
    def __init__(self):
        self.model = RsModel()

    def vertex(self, position, label=0):
        self.model.vertices.append(tuple(round(c) for c in position))
        self.model.vertex_labels.append(label)
        return len(self.model.vertices) - 1

    def face(self, a, b, c, color, face_label):
        self.model.faces.append((a, b, c))
        self.model.colors.append(color)
        self.model.alphas.append(HIDDEN)
        self.model.face_labels.append(face_label)
        self.model.render_types.append(0)

    def quad(self, corners, color, face_label):
        """Double sided, since the client culls back faces."""
        a, b, c, d = (self.vertex(p) for p in corners)
        for tri in ((a, b, c), (a, c, d), (a, c, b), (a, d, c)):
            self.face(*tri, color, face_label)

    def bulb(self, center, radius, color, label):
        x, y, z = center
        points = [(x + radius, y, z), (x - radius, y, z), (x, y - radius, z),
                  (x, y + radius * 1.6, z), (x, y, z + radius), (x, y, z - radius)]
        ids = [self.vertex(p, label) for p in points]
        for a in ids[0:2]:
            for b in ids[2:4]:
                for c in ids[4:6]:
                    self.face(a, b, c, color, label)
                    self.face(a, c, b, color, label)


def blur_label(blade, slash_frame, ghost):
    return BLUR_LABEL_BASE + (blade * SLASH_FRAMES + slash_frame) * BLUR_GHOSTS + ghost


def trail_label(blade, slash_frame):
    return TRAIL_LABEL_BASE + blade * SLASH_FRAMES + slash_frame


def drip_label(blade, spawn):
    return DRIP_LABEL_BASE + blade * len(DRIP_SPAWNS) + spawn


def build_fx(tracker):
    """Every effect face starts hidden; the effect seq reveals each group with alpha transforms.
    Blur ghosts are blade smears widened along the tip's motion, sampled between the body's slash
    frames; trails are ribbons swept by the outer blade over the forward,
    crossing part of the swing; drips sit at the tips during the reset."""
    fx = FxBuilder()
    for frame in range(SLASH_FRAMES):
        for ghost in range(BLUR_GHOSTS):
            step = frame + (ghost + 1) / (BLUR_GHOSTS + 1)
            before, now, after = (tracker.at_slash_step(step + d) for d in (-0.15, 0, 0.15))
            for blade, (root, tip) in enumerate(now):
                motion = [a - b for a, b in zip(after[blade][1], before[blade][1])]
                length = max(1.0, sum(m * m for m in motion) ** 0.5)
                offset = [m / length * BLUR_WIDTH for m in motion]
                fx.quad(
                    (shifted(root, offset, -1), shifted(tip, offset, -1),
                     shifted(tip, offset, 1), shifted(root, offset, 1)),
                    GHOST_HSL, blur_label(blade, frame, ghost),
                )
        for sub in range(TRAIL_STEPS if frame >= TRAIL_FIRST_FRAME else 0):
            start = tracker.at_slash_step(frame + sub / TRAIL_STEPS)
            end = tracker.at_slash_step(frame + (sub + 1) / TRAIL_STEPS)
            for blade in range(2):
                (ra, ta), (rb, tb) = start[blade], end[blade]
                inner = along(ra, ta, TRAIL_START), along(rb, tb, TRAIL_START)
                split = along(ra, ta, TRAIL_SPLIT), along(rb, tb, TRAIL_SPLIT)
                label = trail_label(blade, frame)
                fx.quad((inner[0], split[0], split[1], inner[1]), TRAIL_INNER_HSL, label)
                fx.quad((split[0], ta, tb, split[1]), TRAIL_OUTER_HSL, label)
    for spawn, frame in enumerate(DRIP_SPAWNS):
        if frame >= RESET_START:
            values = reset_frame_values(frame - RESET_START)
        else:
            values = player_frame(CROSSED_LOW, CROSSED_LOW)
        for blade, (_, tip) in enumerate(tracker.blades(values)):
            fx.bulb(tip, DRIP_RADIUS, DRIP_HSL, drip_label(blade, spawn))
    return fx.model


def fx_frame_map():
    transforms = []
    for blade in range(2):
        for frame in range(SLASH_FRAMES):
            transforms += [Transform(ALPHA, (blur_label(blade, frame, ghost),))
                           for ghost in range(BLUR_GHOSTS)]
    for blade in range(2):
        transforms += [Transform(ALPHA, (trail_label(blade, frame),))
                       for frame in range(TRAIL_FIRST_FRAME, SLASH_FRAMES)]
    for blade in range(2):
        for spawn in range(len(DRIP_SPAWNS)):
            label = drip_label(blade, spawn)
            transforms += [Transform(ORIGIN, (label,)), Transform(TRANSLATE, (label,)),
                           Transform(ALPHA, (label,))]
    return FrameMap(FX_FRAME_MAP_ID, transforms)


FX_FRAME_MAP = fx_frame_map()


def fx_transform(transform_type, label):
    return next(i for i, t in enumerate(FX_FRAME_MAP.transforms)
                if t.type == transform_type and t.labels == (label,))


def reveal(alpha):
    return round((alpha - HIDDEN) / 8), 0, 0


def xslash_fx():
    frames = [{} for _ in range(FRAME_COUNT)]
    for slash_frame in range(SLASH_FRAMES):
        for blade in range(2):
            for ghost, alpha in enumerate(GHOST_ALPHAS):
                transform = fx_transform(ALPHA, blur_label(blade, slash_frame, ghost))
                frames[SLASH_START + slash_frame][transform] = reveal(alpha)

    fade_from = LINGER_START + LINGER_FRAMES - TRAIL_FADE_FRAMES
    for index in range(SLASH_START, min(FRAME_COUNT, LINGER_START + LINGER_FRAMES)):
        fade = max(0, index - fade_from + 1) / (TRAIL_FADE_FRAMES + 1)
        alpha = round(TRAIL_ALPHA + (HIDDEN - TRAIL_ALPHA) * fade)
        for blade in range(2):
            for slash_frame in range(TRAIL_FIRST_FRAME, min(SLASH_FRAMES, index - SLASH_START + 1)):
                frames[index][fx_transform(ALPHA, trail_label(blade, slash_frame))] = reveal(alpha)

    for spawn, start in enumerate(DRIP_SPAWNS):
        for age, fall in enumerate(DRIP_FALL):
            index = start + age
            if index >= FRAME_COUNT:
                break
            alpha = DRIP_ALPHA + (HIDDEN - DRIP_ALPHA) * age // (len(DRIP_FALL) + 1)
            for blade in range(2):
                label = drip_label(blade, spawn)
                frames[index][fx_transform(TRANSLATE, label)] = (0, fall, 0)
                frames[index][fx_transform(ALPHA, label)] = reveal(alpha)
    return Sequence("poison_blades_xslash_fx", frames, DELAYS, max_loops=1)


FX_SEQUENCES = (xslash_fx,)


def write_archive(pack_dir, name, archive, frame_map, sequences):
    frames = write_sequences(os.path.join(pack_dir, "configs", f"{name}.toml"), archive, sequences)
    write_rsanim(os.path.join(pack_dir, "anims", f"{name}.rsanim"), archive,
                 [encode_frame(frame_map, values) for values in frames])
    return frames


def generate(pack_dir=PACK_DIR):
    player_frames = write_archive(pack_dir, "poison_blades_xslash", PLAYER_FRAME_ARCHIVE,
                                  player_frame_map(), [xslash()])
    fx_model = build_fx(BladeTracker())
    with open(os.path.join(pack_dir, "models", "poison_blades_fx.dat"), "wb") as handle:
        handle.write(encode_model(fx_model))
    fx_frames = write_archive(pack_dir, "poison_blades_xslash_fx", FX_FRAME_ARCHIVE,
                              FX_FRAME_MAP, [xslash_fx()])
    map_path = os.path.join(pack_dir, "anims", "framemaps", f"{FX_FRAME_MAP_ID}.dat")
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    with open(map_path, "wb") as handle:
        handle.write(FX_FRAME_MAP.encode())
    print(f"Player seq: {len(player_frames)} frames. Fx: {len(fx_model.vertices)} vertices, "
          f"{len(fx_model.faces)} faces, {len(fx_frames)} frames, frame map {FX_FRAME_MAP_ID} "
          f"({len(FX_FRAME_MAP.transforms)} transforms)")


if __name__ == "__main__":
    generate()
