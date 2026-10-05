"""Builds the Poison carapace torso: a heavy chest piece shaped as a segmented insect thorax.

Overlapping obsidian chitin bands layer down the chest like a scorpion's underbelly, each one
flaring at its lower lip over the band beneath. Between the left and right bands a sunken
channel runs down the sternum, carrying a neon-green vein ridge with chevron branches. The
shoulders carry three stacked elytra per side that jut sideways into sharp, forward-swept points,
widening the silhouette without adding height. Below the ribs the shell tapers hard into a
narrow, multi-segmented abdomen that stays inside the vanilla waist.

The body (male0) and sleeves (male1) are separate models like the vanilla platebodies; see
``worn_armour.py`` for labels, pivot anchors, the female warp and the inventory pose.

Needs references from:
    gradlew :or-cache:dumpAnimReference -Prefs=obj.rune_platebody,idk.18,idk.26,idk.56,idk.61

Usage:
    blender --background --python tools/blender/poison_carapace_torso_build.py -- [out.blend] [models dir] [preview dir]
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worn_armour as wa  # noqa: E402
from worn_armour import (  # noqa: E402
    OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, SOCKET_HSL, TOXIC_DARK_HSL, TOXIC_HSL,
    VENOM_DIM_HSL, VENOM_HSL, Part,
)

TORSO_PRIORITY = 3
MAX_TRIANGLES = 1300

TORSO_LABELS = frozenset({2, 4, 5, 8, 94})
SHOULDER_LABELS = frozenset({21, 25})
ARM_LABELS = frozenset({17, 19, 20, 21, 22, 23, 25, 26})

SHELL_SEGMENTS = 10
SHELL_RINGS = (
    (111.0, 15.5, 13.5, 12.0),
    (117.0, 13.5, 12.0, 11.0),
    (123.0, 12.5, 11.5, 10.5),
    (130.0, 14.5, 13.5, 11.0),
    (138.0, 17.5, 15.5, 12.5),
    (146.0, 19.5, 17.0, 13.0),
    (154.0, 19.5, 16.5, 13.0),
    (161.0, 17.0, 13.0, 11.5),
    (166.0, 11.5, 9.0, 9.0),
    (168.5, 7.5, 6.5, 6.5),
)

CHANNEL_HALF_WIDTH = 3.5
CHANNEL_LIFT = 0.3
VENTRAL_BANDS = (
    (165.0, 156.0, 95), (157.5, 148.5, 100), (150.0, 141.0, 100), (142.5, 134.0, 95),
    (135.5, 128.5, 80), (130.0, 123.5, 75), (125.0, 118.5, 75), (120.0, 111.0, 80),
)
DORSAL_BANDS = (
    (166.0, 155.0), (156.5, 145.0), (146.5, 135.0), (136.5, 127.0), (128.5, 119.0), (120.5, 111.0),
)
DORSAL_ARC = (110, 250)
BAND_STATIONS = 4
DORSAL_STATIONS = 7

VEIN_HALF_WIDTH = 0.9
VEIN_LIFT = 1.6
BRANCH_SPREAD = CHANNEL_HALF_WIDTH - 0.4
BRANCH_RISE = 2.4
BRANCH_HALF_WIDTH = 0.6
BRANCH_LIFT = 1.1

ELYTRA = (
    (11.0, 48.0, 163.5, 150.0, 13.5, 3.0, OBSIDIAN_HSL, VENOM_HSL),
    (12.0, 42.0, 166.5, 155.0, 12.0, 2.5, TOXIC_DARK_HSL, TOXIC_HSL),
    (13.0, 35.0, 169.5, 160.0, 10.0, 2.0, OBSIDIAN_TOP_HSL, VENOM_HSL),
)
ELYTRA_STATIONS = ((0.0, 0.85), (0.35, 1.0), (0.7, 0.75))
ELYTRA_RIDGE = 1.6
ELYTRA_EDGE_DROP = 2.2
ELYTRA_THICKNESS = 1.0
ELYTRA_UNDER_INSET = 0.92
ELYTRA_PRIORITY = 6

ARM_AXIS = ((161.0, 23.5), (146.0, 25.5), (130.0, 27.5), (114.0, 28.3))
ARM_FORWARD = -0.5
SLEEVE_SEGMENTS = ((161.0, 146.5, 6.2, 7.2), (148.0, 131.5, 5.6, 6.8), (133.0, 115.0, 5.0, 6.2))
SLEEVE_SIDES = 6
SLEEVE_TUCK = 0.7
SLEEVE_PRIORITY = 10

INVENTORY_CENTRE_UP = 140.0
INVENTORY_BACK = 14.0


def ring_at(up):
    rings = SHELL_RINGS
    if up <= rings[0][0]:
        return rings[0][1:]
    for lower, upper in zip(rings, rings[1:]):
        if up <= upper[0]:
            t = (up - lower[0]) / (upper[0] - lower[0])
            return tuple(a + (b - a) * t for a, b in zip(lower[1:], upper[1:]))
    return rings[-1][1:]


def shell_point(theta, up, lift=0.0):
    """A point ``lift`` out from the shell ellipse at angle ``theta`` (0 = sternum, +pi/2 =
    the player's left)."""
    half_width, front, back = ring_at(up)
    c, s = math.cos(theta), math.sin(theta)
    fwd, left = (front if c >= 0 else back) * c, half_width * s
    length = math.hypot(fwd, left)
    scale = (length + lift) / length
    return fwd * scale, left * scale, up


def axis(up):
    return 0.0, 0.0, up


def channel_angle(up):
    return math.asin(min(CHANNEL_HALF_WIDTH / ring_at(up)[0], 1.0))


def build_shell():
    part = Part("Shell", TORSO_PRIORITY, TORSO_LABELS)
    rings = []
    for up, *_ in SHELL_RINGS:
        rings.append([part.vert(shell_point(2 * math.pi * k / SHELL_SEGMENTS, up))
                      for k in range(SHELL_SEGMENTS)])
    shades = (OBSIDIAN_EDGE_HSL, OBSIDIAN_HSL)
    wa.ring_strip(part, rings, lambda r, k: shades[(r + k) % 2],
                  lambda r, k: axis(SHELL_RINGS[r][0]))
    return part


def build_channel():
    """The sunken floor between the chest bands: a dark strip barely off the shell."""
    part = Part("Channel", TORSO_PRIORITY + 1, TORSO_LABELS)
    rows = []
    for up, *_ in SHELL_RINGS[:-2]:
        edge = channel_angle(up) + 0.05
        rows.append([part.vert(shell_point(theta, up, CHANNEL_LIFT)) for theta in (-edge, 0.0, edge)])
    for r in range(len(rows) - 1):
        for k in range(2):
            part.face((rows[r][k], rows[r][k + 1], rows[r + 1][k + 1], rows[r + 1][k]), SOCKET_HSL,
                      outward=axis(SHELL_RINGS[r][0]))
    return part


def build_veins():
    """A raised green ridge down the channel centre and chevron branches at every band seam,
    each a two-faced knife edge so it reads as a sharp line of light."""
    part = Part("Veins", TORSO_PRIORITY + 2, TORSO_LABELS)
    top, bottom = VENTRAL_BANDS[0][0] - 1.0, VENTRAL_BANDS[-1][1] + 0.5
    steps = 6
    spine, ups = [], []
    for i in range(steps + 1):
        up = bottom + (top - bottom) * i / steps
        ups.append(up)
        half = VEIN_HALF_WIDTH * (0.5 if i in (0, steps) else 1.0)
        spine.append((part.vert(shell_point(-half / 10, up, CHANNEL_LIFT)),
                      part.vert(shell_point(0.0, up, VEIN_LIFT)),
                      part.vert(shell_point(half / 10, up, CHANNEL_LIFT))))
    for (r0, c0, l0), (r1, c1, l1), up in zip(spine, spine[1:], ups):
        part.face((r0, c0, c1, r1), VENOM_HSL, outward=axis(up))
        part.face((c0, l0, l1, c1), VENOM_DIM_HSL, outward=axis(up))

    for _, seam, _ in VENTRAL_BANDS[:-1]:
        for side in (1, -1):
            outer_up = seam + BRANCH_RISE
            outer_theta = side * math.asin(min(BRANCH_SPREAD / ring_at(outer_up)[0], 1.0))
            base_up = seam - 0.5
            low = part.vert(shell_point(side * 0.02, base_up - BRANCH_HALF_WIDTH, CHANNEL_LIFT))
            high = part.vert(shell_point(side * 0.02, base_up + BRANCH_HALF_WIDTH, CHANNEL_LIFT))
            crest = part.vert(shell_point(side * 0.02, base_up, BRANCH_LIFT))
            tip = part.vert(shell_point(outer_theta, outer_up, CHANNEL_LIFT))
            part.face((high, crest, tip), VENOM_HSL, outward=axis(base_up))
            part.face((crest, low, tip), VENOM_DIM_HSL, outward=axis(base_up))
    return part


def build_ventral():
    part = Part("Ventral", TORSO_PRIORITY + 2, TORSO_LABELS)
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL)
    for top, bottom, reach in VENTRAL_BANDS:
        inner = channel_angle((top + bottom) / 2)
        outer = math.radians(reach)
        for side in (1, -1):
            thetas = [side * (inner + (outer - inner) * i / (BAND_STATIONS - 1))
                      for i in range(BAND_STATIONS)]
            wa.band(part, shell_point, axis, top, bottom, thetas, colors,
                    (VENOM_DIM_HSL, OBSIDIAN_EDGE_HSL))
    return part


def build_dorsal():
    part = Part("Dorsal", TORSO_PRIORITY + 1, TORSO_LABELS)
    colors = (OBSIDIAN_HSL, OBSIDIAN_TOP_HSL, OBSIDIAN_EDGE_HSL)
    start, end = (math.radians(a) for a in DORSAL_ARC)
    for top, bottom in DORSAL_BANDS:
        thetas = [start + (end - start) * i / (DORSAL_STATIONS - 1) for i in range(DORSAL_STATIONS)]
        wa.band(part, shell_point, axis, top, bottom, thetas, colors,
                (OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL))
    return part


def build_elytra():
    """Three stacked wing covers per shoulder, longest at the bottom, each a thin closed shell
    with a raised spine, sloping down and sweeping forward into a single sharp tip."""
    parts = []
    for side in (1, -1):
        for layer, (inner, tip, base_up, tip_up, span, sweep, face, trim) in enumerate(ELYTRA):
            part = Part(f"Elytron{side}_{layer}", ELYTRA_PRIORITY, SHOULDER_LABELS)
            part.closed = True
            loops = []
            for t, width in ELYTRA_STATIONS:
                left = side * (inner + (tip - inner) * t)
                up = base_up + (tip_up - base_up) * t
                centre, half = sweep * t, span * width
                under = half * ELYTRA_UNDER_INSET
                low = up - ELYTRA_EDGE_DROP
                loops.append([
                    part.vert((centre - half, left, low)),
                    part.vert((centre, left, up + ELYTRA_RIDGE)),
                    part.vert((centre + half, left, low)),
                    part.vert((centre + under, left, low - ELYTRA_THICKNESS)),
                    part.vert((centre, left, up + ELYTRA_RIDGE - ELYTRA_THICKNESS * 2)),
                    part.vert((centre - under, left, low - ELYTRA_THICKNESS)),
                ])
            point = part.vert((sweep, side * tip, tip_up - ELYTRA_EDGE_DROP / 2))
            colors = (OBSIDIAN_HSL, face, trim, OBSIDIAN_EDGE_HSL, OBSIDIAN_EDGE_HSL, trim)
            for a, b in zip(loops, loops[1:]):
                for k in range(6):
                    part.face((a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k]), colors[k])
            for k in range(6):
                part.face((loops[-1][k], loops[-1][(k + 1) % 6], point), colors[k])
            part.face(tuple(reversed(loops[0])), OBSIDIAN_EDGE_HSL)
            parts.append(part)
    return parts


def arm_centre(up, side):
    for (u0, l0), (u1, l1) in zip(ARM_AXIS, ARM_AXIS[1:]):
        if u1 <= up <= u0:
            t = (up - u0) / (u1 - u0)
            return ARM_FORWARD, side * (l0 + (l1 - l0) * t), up
    edge = ARM_AXIS[0] if up > ARM_AXIS[0][0] else ARM_AXIS[-1]
    return ARM_FORWARD, side * edge[1], up


def build_sleeves():
    """Each arm is three hexagonal limb segments, keel forward, each flaring towards its lower
    rim and tucking under so the next segment starts inside it."""
    parts = []
    for side in (1, -1):
        part = Part(f"Sleeve{side}", SLEEVE_PRIORITY, ARM_LABELS)
        for top, bottom, top_radius, bottom_radius in SLEEVE_SEGMENTS:
            rings = []
            for up, radius in ((top, top_radius), (bottom, bottom_radius),
                               (bottom + 1.0, bottom_radius * SLEEVE_TUCK)):
                fwd, left, _ = arm_centre(up, side)
                rings.append([part.vert((fwd + radius * math.cos(2 * math.pi * k / SLEEVE_SIDES),
                                         left + radius * math.sin(2 * math.pi * k / SLEEVE_SIDES),
                                         up)) for k in range(SLEEVE_SIDES)])
            colors = ((OBSIDIAN_TOP_HSL, OBSIDIAN_HSL, OBSIDIAN_HSL, OBSIDIAN_EDGE_HSL,
                       OBSIDIAN_HSL, OBSIDIAN_HSL), (OBSIDIAN_EDGE_HSL,) * SLEEVE_SIDES)
            for r in range(2):
                for k in range(SLEEVE_SIDES):
                    a, b = rings[r][k], rings[r][(k + 1) % SLEEVE_SIDES]
                    c, d = rings[r + 1][(k + 1) % SLEEVE_SIDES], rings[r + 1][k]
                    part.face((a, b, c, d), colors[r][k],
                              outward=arm_centre((top + bottom) / 2, side))
        parts.append(part)
    return parts


def inventory_pose(point):
    """Laid on its back with the chest facing up and the neck towards +z, like the vanilla
    platebody icons."""
    fwd, left, up = point
    return -(up - INVENTORY_CENTRE_UP), left, fwd + INVENTORY_BACK


def build_all():
    body = [build_shell(), build_channel(), build_veins(), build_ventral(), build_dorsal(),
            *build_elytra()]
    arms = build_sleeves()
    rig = wa.Rig(
        male_refs=("rune_platebody_male0", "rune_platebody_male1", "model_28515", "model_26632"),
        female_refs=("rune_platebody_female0", "rune_platebody_female1", "model_18554",
                     "model_3476"),
        male_anchor_refs=("rune_platebody_male0", "rune_platebody_male1"),
        female_anchor_refs=("rune_platebody_female0", "rune_platebody_female1"),
    )
    wa.build_variant("CarapaceTorsoMale", body, rig, "male", max_triangles=MAX_TRIANGLES)
    wa.build_variant("CarapaceTorsoMaleArms", arms, rig, "male", anchors=False)
    wa.build_variant("CarapaceTorsoFemale", body, rig, "female", max_triangles=MAX_TRIANGLES)
    wa.build_variant("CarapaceTorsoFemaleArms", arms, rig, "female", anchors=False)
    wa.build_variant("CarapaceTorsoInventory", body + arms, None, "inventory", inventory_pose)


MODELS = (
    ("CarapaceTorsoInventory", "poison_carapace_torso.dat"),
    ("CarapaceTorsoMale", "poison_carapace_torso_worn.dat"),
    ("CarapaceTorsoMaleArms", "poison_carapace_torso_worn_arms.dat"),
    ("CarapaceTorsoFemale", "poison_carapace_torso_worn_female.dat"),
    ("CarapaceTorsoFemaleArms", "poison_carapace_torso_worn_female_arms.dat"),
)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build_all()
    if len(args) > 1:
        wa.export(MODELS, args[1], TORSO_PRIORITY)
    if args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
    if len(args) > 2:
        for names in (("CarapaceTorsoMale", "CarapaceTorsoMaleArms"),
                      ("CarapaceTorsoFemale", "CarapaceTorsoFemaleArms")):
            wa.render_previews(names, (0, 0, 1.1), args[2])
        wa.render_previews(("CarapaceTorsoInventory",), (0, 0, 0.1), args[2], scale=0.7,
                           views=(("top", (0.02, 0, 2)), ("tilted", (1.2, -0.8, 1.2))))
