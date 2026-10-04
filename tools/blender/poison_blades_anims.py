"""Poison Blades player animations and their effect spotanims.

Attack (18 frames): wind-up with both blades pulled back and a slight crouch, a snapping
horizontal slash with the right blade, a diagonal upslash with the left blade, then a settle
back to the ready stance while poison bursts from both tips. Idle (60 frames, looped): blades
held low with a subtle breathing tilt; its spotanim runs poison down each fuller and drips a
thick droplet off a tip every 20 frames.

The player frame map and body kits come from ``tools/blender/ref``; run
``gradlew :or-cache:dumpAnimReference -Prefs=obj.dual_macuahuitl,seq.pmoon_macuahuitl_crush,seq.human_ready,idk.0,idk.10,idk.18,idk.26,idk.33,idk.36,idk.42``
first, and ``poison_blades_worn_build.py`` to export the worn model. Then:

    python tools/blender/poison_blades_anims.py

Player space: Y-down, facing -Z, +X is the player's left. Rotations are frame units (256 per
turn) applied Z, X, Y about world axes. Blade poses are given as a grip position plus a yaw
(0 = forward, +90 = the player's right) and pitch (+ = up), authored for the right arm and
mirrored for the left, and solved into shoulder/elbow/wrist rotations by simulating the client
maths on the dumped skeleton. Frames are sampled from ease-out curves; the client never tweens.
"""

import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from osrs_anim_export import (  # noqa: E402
    ALPHA, ORIGIN, SCALE, TRANSLATE, FrameMap, Sequence, Transform, apply_frame, encode_frame,
    load_reference_frame_map, load_reference_frames, resolve_defaults, write_rsanim,
    write_sequences,
)
from osrs_model_export import RsModel, encode_model, load_reference_model  # noqa: E402

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(TOOLS_DIR, "ref")
PACK_DIR = os.path.join(
    TOOLS_DIR, "..", "..", "content", "skills", "poison-mastery", "pack", "src", "main",
    "resources", "pack",
)
WORN_MODEL = os.path.join(PACK_DIR, "models", "poison_blades_worn.dat")

ATTACK_ARCHIVE = 16001
ATTACK_FX_ARCHIVE = 16002
IDLE_ARCHIVE = 16003
IDLE_FX_ARCHIVE = 16004
ATTACK_FX_MAP_ID = 3001
IDLE_FX_MAP_ID = 3002

T_ROOT, T_NECK, T_TORSO = 1, 4, 7
T_LEFT_HIP, T_LEFT_KNEE, T_LEFT_FOOT = 9, 11, 13
T_RIGHT_HIP, T_RIGHT_KNEE, T_RIGHT_FOOT = 15, 17, 19
ARM_TRANSFORMS = {0: (30, 32, 35), 1: (22, 24, 27)}
FOOT_LABELS = {0: 45, 1: 46}
BLADE_LABELS = (27, 28)
RIGHT, LEFT = 0, 1

WINDUP_DELAYS = [5, 4, 4]
RIGHT_SLASH_DELAYS = [2, 2, 2, 3, 3]
LEFT_SLASH_DELAYS = [2, 2, 2, 3, 4]
SETTLE_DELAYS = [5, 5, 6, 6, 7]
ATTACK_DELAYS = WINDUP_DELAYS + RIGHT_SLASH_DELAYS + LEFT_SLASH_DELAYS + SETTLE_DELAYS
RIGHT_SLASH_START = len(WINDUP_DELAYS)
LEFT_SLASH_START = RIGHT_SLASH_START + len(RIGHT_SLASH_DELAYS)
SETTLE_START = LEFT_SLASH_START + len(LEFT_SLASH_DELAYS)
ATTACK_FRAMES = len(ATTACK_DELAYS)

IDLE_FRAMES = 60
IDLE_DELAY = 3
DRIP_PERIOD = 20
BREATH_UNITS = 2 / 360 * 256

CROUCH_DROP = 4
CROUCH_LEAN = 4
RIGHT_TWIST = -16
LEFT_TWIST = 14
NECK_COUNTER = -0.7

WINDUP = ((-44, -130, 12), 150, 20)
GUARD = ((-26, -118, -26), 25, 15)
LOADED = ((-40, -108, 8), 135, -35)
LOW = ((-30, -100, -14), 8, -38)

HIDDEN = 255
POISON_HSL = (22 << 10) | (7 << 7) | 70
POISON_LIGHT_HSL = (21 << 10) | (7 << 7) | 100
DRIP_HSL = (21 << 10) | (7 << 7) | 80
FULLER_HSL = (22 << 10) | (7 << 7) | 92


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_out_expo(t):
    return 1.0 if t >= 1 else (1 - 2 ** (-10 * t)) / (1 - 2 ** -10)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def direction(yaw, pitch):
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    return (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), -math.cos(yaw) * math.cos(pitch))


def angles(root, tip):
    dx, dy, dz = (t - r for t, r in zip(tip, root))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.degrees(math.atan2(-dx, -dz)), math.degrees(math.asin(-dy / length))


def mirror_pose(pose):
    (x, y, z), yaw, pitch = pose
    return (-x, y, z), -yaw, pitch


def blend_pose(a, b, t):
    return lerp3(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)


_frame_map = None
_stance = None


def player_frame_map():
    global _frame_map
    if _frame_map is None:
        path = os.path.join(REF_DIR, "framemap_0.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} missing - run gradlew :or-cache:dumpAnimReference")
        _frame_map = load_reference_frame_map(path)
    return _frame_map


def ready_stance():
    """Frame 0 of the vanilla ready animation: legs, hips and head every player frame needs."""
    global _stance
    if _stance is None:
        frames, _ = load_reference_frames(os.path.join(REF_DIR, "human_ready.json"))
        _stance = resolve_defaults(player_frame_map(), frames[0])
    return _stance


def __getattr__(name):
    if name == "FRAME_MAP":
        return player_frame_map()
    raise AttributeError(name)


class Skeleton:
    """The player (body kits + worn blades) posed with the client maths. Marker vertices
    carrying a blade's label ride along with that hand: grip, tip and fuller points."""

    def __init__(self):
        kits = sorted(glob.glob(os.path.join(REF_DIR, "model_*.json")))
        if not kits:
            raise FileNotFoundError("No body kits in tools/blender/ref - run dumpAnimReference")
        self.model = load_reference_model(*kits, WORN_MODEL)
        self.blade_points = []
        for label in BLADE_LABELS:
            blade = [v for v, l in zip(self.model.vertices, self.model.vertex_labels) if l == label]
            tip = min(blade, key=lambda v: v[2])
            pommel = max(blade, key=lambda v: v[2])
            grip = (tip[0], round((tip[1] + pommel[1]) / 2),
                    round(pommel[2] + (tip[2] - pommel[2]) * 0.3))
            self.blade_points.append({"grip": grip, "tip": tip, "fuller": fuller_line(blade)})
        self.markers = []
        for label, points in zip(BLADE_LABELS, self.blade_points):
            flat = [points["grip"], points["tip"]] + [p for seg in points["fuller"] for p in seg]
            start = len(self.model.vertices)
            self.model.vertices += flat
            self.model.vertex_labels += [label] * len(flat)
            self.markers.append(list(range(start, start + len(flat))))
        self.length = [dist(p["grip"], p["tip"]) for p in self.blade_points]
        self._foot_ids = {
            side: [i for i, l in enumerate(self.model.vertex_labels) if l == label]
            for side, label in FOOT_LABELS.items()
        }

    def pose(self, values):
        vertices, _ = apply_frame(self.model, player_frame_map(), values)
        return vertices

    def blade(self, vertices, side):
        ids = self.markers[side]
        return vertices[ids[0]], vertices[ids[1]]

    def fuller(self, vertices, side):
        """[(outer face quad points, inner face quad points)] per band, posed."""
        ids = self.markers[side][2:]
        points = [vertices[i] for i in ids]
        return [points[i:i + 4] for i in range(0, len(points), 4)]

    def foot(self, vertices, side):
        ids = self._foot_ids[side]
        return tuple(sum(vertices[i][k] for i in ids) / len(ids) for k in range(3))


FULLER_BANDS = 6
FULLER_FROM, FULLER_TO = 0.12, 0.78
FULLER_HALF_WIDTH = 1.4
FULLER_OFFSET = 2.6


def fuller_line(blade):
    """Quad corners for each fuller band on both flats of one blade, in bind space. The blade's
    flats face +-X and its length runs along Z, so the fuller follows the centre of each slice."""
    tip_z = min(v[2] for v in blade)
    guard_z = tip_z + (max(v[2] for v in blade) - tip_z) * 0.55
    centre_x = sum(v[0] for v in blade) / len(blade)

    def centre_y(z):
        near = [v for v in blade if abs(v[2] - z) <= 4] or blade
        return (min(v[1] for v in near) + max(v[1] for v in near)) / 2

    bands = []
    for band in range(FULLER_BANDS):
        z0 = lerp(guard_z, tip_z, lerp(FULLER_FROM, FULLER_TO, band / FULLER_BANDS))
        z1 = lerp(guard_z, tip_z, lerp(FULLER_FROM, FULLER_TO, (band + 1) / FULLER_BANDS))
        y0, y1 = centre_y(z0), centre_y(z1)
        for side in (-1, 1):
            x = centre_x + side * FULLER_OFFSET
            corners = ((x, y0 - FULLER_HALF_WIDTH, z0), (x, y1 - FULLER_HALF_WIDTH, z1),
                       (x, y1 + FULLER_HALF_WIDTH, z1), (x, y0 + FULLER_HALF_WIDTH, z0))
            bands.append(tuple(tuple(round(c) for c in p) for p in corners))
    return bands


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


_skeleton = None


def skeleton():
    global _skeleton
    if _skeleton is None:
        _skeleton = Skeleton()
    return _skeleton


def body_values(lean, twist, crouch):
    values = dict(ready_stance())
    x, y, z = values.get(T_TORSO, (0, 0, 0))
    values[T_TORSO] = (round(x + lean), round(y + twist), z)
    nx, ny, nz = values.get(T_NECK, (0, 0, 0))
    values[T_NECK] = (nx, round(ny + twist * NECK_COUNTER), nz)
    values.update(crouch_legs(crouch))
    return values


_crouch_cache = {}


def crouch_legs(amount):
    """Root lowered by ``amount`` x CROUCH_DROP with hips and knees bent so both feet stay
    planted where the ready stance has them."""
    drop = round(amount * CROUCH_DROP)
    if drop in _crouch_cache:
        return _crouch_cache[drop]
    stance = ready_stance()
    if drop == 0:
        return {t: stance.get(t, (0, 0, 0)) for t in (T_ROOT, T_LEFT_HIP, T_LEFT_KNEE, T_LEFT_FOOT,
                                                       T_RIGHT_HIP, T_RIGHT_KNEE, T_RIGHT_FOOT)}
    rig = skeleton()
    planted = rig.pose(stance)
    values = {T_ROOT: tuple(c + d for c, d in zip(stance.get(T_ROOT, (0, 0, 0)), (0, drop, 0)))}
    for side, (hip, knee, foot) in ((LEFT, (T_LEFT_HIP, T_LEFT_KNEE, T_LEFT_FOOT)),
                                    (RIGHT, (T_RIGHT_HIP, T_RIGHT_KNEE, T_RIGHT_FOOT))):
        target = rig.foot(planted, side)
        best = None
        for bend_hip in range(-24, 25):
            for bend_knee in range(-40, 41):
                trial = dict(stance)
                trial.update(values)
                trial[hip] = add(stance.get(hip, (0, 0, 0)), (bend_hip, 0, 0))
                trial[knee] = add(stance.get(knee, (0, 0, 0)), (bend_knee, 0, 0))
                trial[foot] = add(stance.get(foot, (0, 0, 0)), (-bend_hip - bend_knee, 0, 0))
                error = dist(rig.foot(rig.pose(trial), side), target)
                if best is None or error < best[0]:
                    best = (error, trial[hip], trial[knee], trial[foot])
        values.update({hip: best[1], knee: best[2], foot: best[3]})
    _crouch_cache[drop] = values
    return values


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def solve_arm(body, side, pose, warm):
    """Shoulder/elbow/wrist rotations putting the blade grip and tip on ``pose``, by coordinate
    descent from ``warm`` (the previous frame) so consecutive frames stay continuous."""
    rig = skeleton()
    grip, yaw, pitch = pose if side == RIGHT else mirror_pose(pose)
    tip = add(grip, tuple(c * rig.length[side] for c in direction(yaw, pitch)))
    transforms = ARM_TRANSFORMS[side]
    params = [c for t in transforms for c in warm[t]]

    def cost(p):
        values = dict(body)
        for i, t in enumerate(transforms):
            values[t] = tuple(p[i * 3:i * 3 + 3])
        got_grip, got_tip = rig.blade(rig.pose(values), side)
        error = dist(got_grip, grip) ** 2 + dist(got_tip, tip) ** 2
        drift = sum((a - b) ** 2 for a, b in zip(p, params_start))
        wrist = sum(c * c for c in p[6:9])
        return error + 0.04 * drift + 0.05 * wrist

    params_start = list(params)
    best = cost(params)
    for step in (16, 8, 4, 2, 1):
        improved = True
        while improved:
            improved = False
            for i in range(len(params)):
                for delta in (step, -step):
                    trial = list(params)
                    trial[i] = max(-128, min(127, trial[i] + delta))
                    score = cost(trial)
                    if score < best:
                        best, params, improved = score, trial, True
    return {t: tuple(params[i * 3:i * 3 + 3]) for i, t in enumerate(transforms)}


def arm_values(values, side):
    return {t: values.get(t, (0, 0, 0)) for t in ARM_TRANSFORMS[side]}


def ready_pose(side):
    """The ready stance's blade pose, in right-arm space."""
    rig = skeleton()
    grip, tip = rig.blade(rig.pose(ready_stance()), side)
    yaw, pitch = angles(grip, tip)
    pose = (grip, yaw, pitch)
    return pose if side == RIGHT else mirror_pose(pose)


def right_slash(s):
    """Horizontal forehand: from pulled back on the right, across the front to the left."""
    yaw = lerp(WINDUP[1], -65, s)
    pitch = WINDUP[2] * (1 - s) ** 2 - 8 * s
    swing = math.radians(0.55 * yaw)
    grip = (-10 - 34 * math.sin(swing), -126 + 4 * s, -6 - 34 * math.cos(swing) + 18 * (1 - s) ** 2)
    return grip, yaw, pitch


def left_upslash(s):
    """Diagonal forehand (right-arm space): from low behind the hip up across to high front."""
    yaw = lerp(LOADED[1], -60, s)
    pitch = lerp(LOADED[2], 45, s)
    swing = math.radians(0.55 * yaw)
    grip = (-10 - 34 * math.sin(swing), -108 - 38 * s, -6 - 34 * math.cos(swing) + 14 * (1 - s) ** 2)
    return grip, yaw, pitch


def attack_keys():
    """Per frame: (lean, twist, crouch, right blade pose, left blade pose)."""
    ready = {RIGHT: ready_pose(RIGHT), LEFT: ready_pose(LEFT)}
    keys = []
    for k in range(1, len(WINDUP_DELAYS) + 1):
        t = ease_out_cubic(k / len(WINDUP_DELAYS))
        keys.append((CROUCH_LEAN * t, 0, t, blend_pose(ready[RIGHT], right_slash(0), t),
                     blend_pose(ready[LEFT], WINDUP, t)))
    for k in range(1, len(RIGHT_SLASH_DELAYS) + 1):
        s = ease_out_expo(k / len(RIGHT_SLASH_DELAYS))
        t = ease_out_cubic(k / len(RIGHT_SLASH_DELAYS))
        keys.append((CROUCH_LEAN, RIGHT_TWIST * s, 1, right_slash(s), blend_pose(WINDUP, LOADED, t)))
    for k in range(1, len(LEFT_SLASH_DELAYS) + 1):
        s = ease_out_cubic(k / len(LEFT_SLASH_DELAYS))
        keys.append((CROUCH_LEAN, lerp(RIGHT_TWIST, LEFT_TWIST, s), 1,
                     blend_pose(right_slash(1), GUARD, s), left_upslash(s)))
    return keys


_attack_frames = None


def attack_frames():
    global _attack_frames
    if _attack_frames is None:
        stance = ready_stance()
        warm = {side: arm_values(stance, side) for side in (RIGHT, LEFT)}
        frames = []
        for lean, twist, crouch, right, left in attack_keys():
            values = body_values(lean, twist, crouch)
            for side, pose in ((RIGHT, right), (LEFT, left)):
                warm[side] = solve_arm(values, side, pose, warm[side])
                values.update(warm[side])
            frames.append(values)
        for k in range(1, len(SETTLE_DELAYS) + 1):
            frames.append(blended(frames[SETTLE_START - 1], stance,
                                  ease_out_cubic(k / len(SETTLE_DELAYS))))
        _attack_frames = frames
    return _attack_frames


_idle_frames = None


def idle_frames():
    global _idle_frames
    if _idle_frames is None:
        stance = ready_stance()
        values = dict(stance)
        for side in (RIGHT, LEFT):
            values.update(solve_arm(values, side, LOW, arm_values(stance, side)))
        frames = []
        for frame in range(IDLE_FRAMES):
            tilt = round(BREATH_UNITS * math.sin(2 * math.pi * frame / IDLE_FRAMES))
            breathing = dict(values)
            for side in (RIGHT, LEFT):
                wrist = ARM_TRANSFORMS[side][2]
                breathing[wrist] = add(values[wrist], (tilt, 0, 0))
            frames.append(breathing)
        _idle_frames = frames
    return _idle_frames


def attack():
    return Sequence("poison_blades_attack", attack_frames(), ATTACK_DELAYS, max_loops=1,
                    inherit="seq.pmoon_macuahuitl_crush")


def idle():
    return Sequence("poison_blades_idle", idle_frames(), [IDLE_DELAY] * IDLE_FRAMES,
                    inherit="seq.human_ready")


SEQUENCES = (attack, idle)


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


def reveal(alpha):
    return round((alpha - HIDDEN) / 8), 0, 0


def transform_index(frame_map, transform_type, label):
    return next(i for i, t in enumerate(frame_map.transforms)
                if t.type == transform_type and t.labels == (label,))


TRAIL_STEPS = 3
TRAIL_INNER = 0.5
TRAIL_SPLIT = 0.8
TRAIL_ALPHAS = (70, 140, 200)
BURST_DROPS = 5
BURST_RADIUS = 3
BURST_SPEED = 9
BURST_LIFT = 7
BURST_GRAVITY = 6
GROUND_Y = -2


def trail_label(side, step):
    return 1 + side * len(RIGHT_SLASH_DELAYS) + step


def burst_label(side, drop):
    return 20 + side * BURST_DROPS + drop


def slash_window(side):
    return (RIGHT_SLASH_START, LEFT_SLASH_START) if side == RIGHT else (LEFT_SLASH_START, SETTLE_START)


def blended(a, b, t):
    keys = set(a) | set(b)
    zero = (0, 0, 0)
    return {k: tuple(round(lerp(x, y, t)) for x, y in zip(a.get(k, zero), b.get(k, zero)))
            for k in keys}


def build_attack_fx():
    """Ribbons swept by the outer part of each blade during its slash, then a burst of drops
    from both tips at the start of the settle. Every face starts hidden."""
    rig = skeleton()
    frames = attack_frames()
    fx = FxBuilder()
    for side in (RIGHT, LEFT):
        start, end = slash_window(side)
        for step, index in enumerate(range(start, end)):
            previous = frames[index - 1]
            for sub in range(TRAIL_STEPS):
                a = rig.blade(rig.pose(blended(previous, frames[index], sub / TRAIL_STEPS)), side)
                b = rig.blade(rig.pose(blended(previous, frames[index], (sub + 1) / TRAIL_STEPS)), side)
                inner = along(*a, TRAIL_INNER), along(*b, TRAIL_INNER)
                split = along(*a, TRAIL_SPLIT), along(*b, TRAIL_SPLIT)
                label = trail_label(side, step)
                fx.quad((inner[0], split[0], split[1], inner[1]), POISON_HSL, label)
                fx.quad((split[0], a[1], b[1], split[1]), POISON_LIGHT_HSL, label)
    posed = rig.pose(frames[SETTLE_START])
    for side in (RIGHT, LEFT):
        _, tip = rig.blade(posed, side)
        for drop in range(BURST_DROPS):
            fx.bulb(tip, BURST_RADIUS, DRIP_HSL, burst_label(side, drop))
    return fx.model


def along(root, tip, fraction):
    return tuple(r + (t - r) * fraction for r, t in zip(root, tip))


def attack_fx_map():
    transforms = []
    for side in (RIGHT, LEFT):
        transforms += [Transform(ALPHA, (trail_label(side, step),))
                       for step in range(len(RIGHT_SLASH_DELAYS))]
    for side in (RIGHT, LEFT):
        for drop in range(BURST_DROPS):
            label = burst_label(side, drop)
            transforms += [Transform(ORIGIN, (label,)), Transform(TRANSLATE, (label,)),
                           Transform(ALPHA, (label,))]
    return FrameMap(ATTACK_FX_MAP_ID, transforms)


ATTACK_FX_MAP = attack_fx_map()


def burst_offset(side, drop, age):
    """Drops fan out from the tip, kick upwards, then fall under gravity onto the floor."""
    angle = 2 * math.pi * (drop + 0.5 * side) / BURST_DROPS
    vx, vz = BURST_SPEED * math.cos(angle), BURST_SPEED * math.sin(angle)
    return vx * age, -BURST_LIFT * age + BURST_GRAVITY * age * age / 2, vz * age


def attack_fx():
    rig = skeleton()
    settle = [rig.pose(values) for values in attack_frames()[SETTLE_START:]]
    tips = {side: [rig.blade(posed, side)[1] for posed in settle] for side in (RIGHT, LEFT)}
    frames = [{} for _ in range(ATTACK_FRAMES)]
    for side in (RIGHT, LEFT):
        start, end = slash_window(side)
        for step in range(end - start):
            transform = transform_index(ATTACK_FX_MAP, ALPHA, trail_label(side, step))
            for age, alpha in enumerate(TRAIL_ALPHAS):
                index = start + step + age
                if index < ATTACK_FRAMES:
                    frames[index][transform] = reveal(alpha)
    for side in (RIGHT, LEFT):
        for drop in range(BURST_DROPS):
            label = burst_label(side, drop)
            for age in range(ATTACK_FRAMES - SETTLE_START):
                index = SETTLE_START + age
                follow = [t - s for t, s in zip(tips[side][age], tips[side][0])]
                dx, dy, dz = add(burst_offset(side, drop, age), follow)
                dy = min(dy, GROUND_Y - tips[side][0][1])
                alpha = round(lerp(40, 230, age / (ATTACK_FRAMES - SETTLE_START)))
                frames[index][transform_index(ATTACK_FX_MAP, TRANSLATE, label)] = (
                    round(dx), round(dy), round(dz))
                frames[index][transform_index(ATTACK_FX_MAP, ALPHA, label)] = reveal(alpha)
    return Sequence("poison_blades_attack_fx", frames, ATTACK_DELAYS, max_loops=1)


FULLER_ALPHAS = {0: 30, 1: 90, 2: 140}
FULLER_BASE_ALPHA = 175
IDLE_DROP_RADIUS = 4
DROP_FORM, DROP_STRETCH, DROP_FALL = 6, 4, 8
DROP_OFFSET = {RIGHT: 0, LEFT: DRIP_PERIOD // 2}


def fuller_label(side, band):
    return 1 + side * FULLER_BANDS + band


def drop_label(side):
    return 40 + side


def build_idle_fx():
    rig = skeleton()
    posed = rig.pose(idle_frames()[0])
    fx = FxBuilder()
    for side in (RIGHT, LEFT):
        quads = rig.fuller(posed, side)
        for band in range(FULLER_BANDS):
            for face in quads[band * 2:band * 2 + 2]:
                fx.quad(face, FULLER_HSL, fuller_label(side, band))
        _, tip = rig.blade(posed, side)
        fx.bulb(tip, IDLE_DROP_RADIUS, DRIP_HSL, drop_label(side))
    return fx.model


def idle_fx_map():
    transforms = [Transform(ALPHA, (fuller_label(side, band),))
                  for side in (RIGHT, LEFT) for band in range(FULLER_BANDS)]
    for side in (RIGHT, LEFT):
        label = drop_label(side)
        transforms += [Transform(ORIGIN, (label,)), Transform(TRANSLATE, (label,)),
                       Transform(SCALE, (label,)), Transform(ALPHA, (label,))]
    return FrameMap(IDLE_FX_MAP_ID, transforms)


IDLE_FX_MAP = idle_fx_map()


def drop_state(age, fall_height):
    """(translate y, scale (x, y, z), alpha) of a droplet ``age`` frames into its cycle, or
    None while it is hidden: it swells at the tip, stretches, then falls with gravity."""
    if age < DROP_FORM:
        size = round(lerp(30, 128, ease_out_cubic((age + 1) / DROP_FORM)))
        return 0, (size, size, size), round(lerp(200, 60, (age + 1) / DROP_FORM))
    age -= DROP_FORM
    if age < DROP_STRETCH:
        t = ease_out_cubic((age + 1) / DROP_STRETCH)
        return round(3 * t), (round(lerp(128, 100, t)), round(lerp(128, 200, t)),
                              round(lerp(128, 100, t))), 60
    age -= DROP_STRETCH
    if age < DROP_FALL:
        t = (age + 1) / DROP_FALL
        return round(3 + fall_height * t * t), (100, 170, 100), round(lerp(60, 150, t))
    return None


def idle_fx():
    rig = skeleton()
    posed = rig.pose(idle_frames()[0])
    frames = [{} for _ in range(IDLE_FRAMES)]
    for frame in range(IDLE_FRAMES):
        for side in (RIGHT, LEFT):
            head = (frame // 2) % FULLER_BANDS
            for band in range(FULLER_BANDS):
                alpha = FULLER_ALPHAS.get(head - band, FULLER_BASE_ALPHA)
                frames[frame][transform_index(IDLE_FX_MAP, ALPHA, fuller_label(side, band))] = \
                    reveal(alpha)
            _, tip = rig.blade(posed, side)
            state = drop_state((frame - DROP_OFFSET[side]) % DRIP_PERIOD, GROUND_Y - tip[1] - 3)
            label = drop_label(side)
            if state is None:
                continue
            dy, scale, alpha = state
            frames[frame][transform_index(IDLE_FX_MAP, TRANSLATE, label)] = (0, dy, 0)
            frames[frame][transform_index(IDLE_FX_MAP, SCALE, label)] = scale
            frames[frame][transform_index(IDLE_FX_MAP, ALPHA, label)] = reveal(alpha)
    return Sequence("poison_blades_idle_fx", frames, [IDLE_DELAY] * IDLE_FRAMES)


def preview_pose(sequence, index):
    """(model, vertices, alphas) of the player with the matching effect merged in, for
    ``osrs_anim_preview.py``."""
    rig = skeleton()
    vertices, alphas = apply_frame(rig.model, player_frame_map(), sequence.frames[index])
    if sequence.name == "poison_blades_attack":
        fx_model, fx_map, fx_seq = build_attack_fx(), ATTACK_FX_MAP, attack_fx()
    else:
        fx_model, fx_map, fx_seq = build_idle_fx(), IDLE_FX_MAP, idle_fx()
    fx_vertices, fx_alphas = apply_frame(fx_model, fx_map, fx_seq.frames[index])
    merged = RsModel(
        rig.model.vertices + fx_model.vertices, rig.model.vertex_labels + fx_model.vertex_labels,
        rig.model.faces + [tuple(i + len(rig.model.vertices) for i in f) for f in fx_model.faces],
        rig.model.colors + fx_model.colors, rig.model.alphas + fx_model.alphas,
        rig.model.face_labels + fx_model.face_labels,
        rig.model.render_types + fx_model.render_types,
    )
    return merged, vertices + fx_vertices, alphas + fx_alphas


def write_archive(pack_dir, name, archive, frame_map, sequence):
    frames = write_sequences(os.path.join(pack_dir, "configs", f"{name}.toml"), archive, [sequence])
    write_rsanim(os.path.join(pack_dir, "anims", f"{name}.rsanim"), archive,
                 [encode_frame(frame_map, values) for values in frames])


def write_fx(pack_dir, name, model, frame_map, archive, sequence):
    with open(os.path.join(pack_dir, "models", f"{name}.dat"), "wb") as handle:
        handle.write(encode_model(model))
    write_archive(pack_dir, name, archive, frame_map, sequence)
    map_path = os.path.join(pack_dir, "anims", "framemaps", f"{frame_map.id}.dat")
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    with open(map_path, "wb") as handle:
        handle.write(frame_map.encode())
    print(f"{name}: {len(model.vertices)} vertices, {len(model.faces)} faces, "
          f"frame map {frame_map.id} ({len(frame_map.transforms)} transforms)")


def generate(pack_dir=PACK_DIR):
    write_archive(pack_dir, "poison_blades_attack", ATTACK_ARCHIVE, player_frame_map(), attack())
    write_archive(pack_dir, "poison_blades_idle", IDLE_ARCHIVE, player_frame_map(), idle())
    write_fx(pack_dir, "poison_blades_attack_fx", build_attack_fx(), ATTACK_FX_MAP,
             ATTACK_FX_ARCHIVE, attack_fx())
    write_fx(pack_dir, "poison_blades_idle_fx", build_idle_fx(), IDLE_FX_MAP,
             IDLE_FX_ARCHIVE, idle_fx())


if __name__ == "__main__":
    generate()
