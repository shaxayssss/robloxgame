"""
Kaiju Heist - standalone corridor zone segments (Blender 5.x).

    blender -b --python build_zones.py

Builds the 5 zones of ZONES.md as SEPARATE models, one GLB each, to the kit's
corridor spec: 40 studs wide x 25 long, walls 15 high. Unlike a generated mesh
these actually tile: the wall cross-section is uniform along the length and no
prop crosses an end plane, so segment N+1 butts against segment N seamlessly.

Outputs to ../assets/zones/ : 5 GLB, 5 previews, and one chained preview proving
the segments connect.

Axis mapping - the spec is written in Roblox axes (Y up, Z = progression), this
file authors in Blender axes (Z up). With export_yup=True the exporter maps
Blender (x, y, z) -> Roblox (x, z, -y), so length is authored on -Y to land on
Roblox +Z. `along()` does that conversion; never write a raw Y here.
"""

import bpy
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_map import (  # noqa: E402  - path must be set first
    MeshBuilder,
    export_glb,
    make_material,
    new_collection,
    reset_scene,
)

# ---------------------------------------------------------------- SPEC

WIDTH = 40.0        # Roblox X, wall outer faces at -20 / +20
LENGTH = 25.0       # Roblox Z, one segment
WALL_H = 15.0       # floor to wall top
WALL_T = 2.0
FLOOR_T = 1.0       # slab below the walkable surface (top sits at z = 0)
PROP_MARGIN = 3.0   # keep props off the end planes so segments still tile

OUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "zones")
)


def along(y_local):
    """Length coordinate 0..LENGTH -> Blender Y, so Roblox Z ends up 0..LENGTH."""
    return -y_local


def srgb_to_linear(hex_color):
    """ZONES.md gives sRGB hex; Blender base colors are linear."""
    value = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        channel = int(value[i:i + 2], 16) / 255.0
        out.append(channel / 12.92 if channel <= 0.04045
                   else ((channel + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# Colours straight from ZONES.md.
ZONES = [
    {
        "id": "ZoneVerte", "label": "Zone Verte",
        "floor": "#4CAF50", "floor_alt": "#43A047", "wall": "#795548",
        "wall_alt": "#6D4C41", "ceiling": None, "decor": "green",
    },
    {
        "id": "ZoneLave", "label": "Zone de Lave",
        "floor": "#3E2723", "floor_alt": "#33201C", "wall": "#212121",
        "wall_alt": "#171717", "ceiling": None, "decor": "lava",
    },
    {
        "id": "ZoneGlace", "label": "Zone de Glace",
        "floor": "#81D4FA", "floor_alt": "#6DC4EE", "wall": "#E3F2FD",
        "wall_alt": "#C9E4F6", "ceiling": None, "decor": "ice",
    },
    {
        "id": "ZoneDesert", "label": "Zone Desert",
        "floor": "#FDD835", "floor_alt": "#EFC72B", "wall": "#D7CCC8",
        "wall_alt": "#C3B8B3", "ceiling": None, "decor": "desert",
    },
    {
        "id": "ZonePierre", "label": "Zone de Pierre",
        "floor": "#757575", "floor_alt": "#646464", "wall": "#424242",
        "wall_alt": "#363636", "ceiling": "#3A3A3A", "decor": "stone",
    },
]

ACCENTS = {
    "lava": "#FF5722",
    "cactus": "#388E3C",
    "trunk": "#6D4C41",
    "foliage": "#43A047",
    "rock": "#9E9E9E",
    "rock_dark": "#6E6E6E",
    "ice_crystal": "#B3E5FC",
    "cave_crystal": "#7986CB",
    "ember": "#FF8A50",
    "sand_rock": "#BCAAA4",
    "grass_tuft": "#66BB6A",
}


def zone_palette(zone):
    pal = {
        "floor": make_material("Floor", srgb_to_linear(zone["floor"])),
        "floor_alt": make_material("Floor_Alt", srgb_to_linear(zone["floor_alt"])),
        "wall": make_material("Wall", srgb_to_linear(zone["wall"])),
        "wall_alt": make_material("Wall_Alt", srgb_to_linear(zone["wall_alt"])),
    }
    if zone["ceiling"]:
        pal["ceiling"] = make_material("Ceiling", srgb_to_linear(zone["ceiling"]))
    for name, hex_color in ACCENTS.items():
        emission = 2.0 if name in ("lava", "ember") else 0.0
        if name in ("ice_crystal", "cave_crystal"):
            emission = 0.7
        pal[name] = make_material(name.title(), srgb_to_linear(hex_color),
                                  emission=emission)
    return pal


# ---------------------------------------------------------------- SHELL


def build_shell(mb, pal, zone):
    """Floor slab, two side walls, optional ceiling. Uniform along the length."""
    half_w = WIDTH / 2.0
    mid = along(LENGTH / 2.0)

    mb.box((0.0, mid, -FLOOR_T / 2.0), (WIDTH, LENGTH, FLOOR_T), pal["floor"])

    # Checker inlay on the walkable surface, for readability and Roblox feel.
    tile = 5.0
    for i in range(int(WIDTH // tile)):
        for j in range(int(LENGTH // tile)):
            if (i + j) % 2:
                continue
            cx = -half_w + tile * (i + 0.5)
            cy = along(tile * (j + 0.5))
            mb.box((cx, cy, 0.03), (tile, tile, 0.06), pal["floor_alt"])

    for sign in (-1, 1):
        wx = sign * (half_w - WALL_T / 2.0)
        mb.box((wx, mid, (WALL_H - FLOOR_T) / 2.0),
               (WALL_T, LENGTH, WALL_H + FLOOR_T), pal["wall"])
        # Horizontal banding: reads as strata, costs 3 boxes.
        for k in range(3):
            z = WALL_H * (0.25 + 0.25 * k)
            mb.box((wx - sign * 0.12, mid, z),
                   (WALL_T * 0.9, LENGTH, 0.8), pal["wall_alt"])

    if zone["ceiling"]:
        mb.box((0.0, mid, WALL_H + 0.5), (WIDTH, LENGTH, 1.0), pal["ceiling"])


# ---------------------------------------------------------------- PROPS


def prop_slots(rng, count):
    """Scattered positions that never touch an end plane, so segments tile."""
    slots = []
    for _ in range(count):
        x = rng.uniform(-WIDTH / 2.0 + 5.0, WIDTH / 2.0 - 5.0)
        y = rng.uniform(PROP_MARGIN, LENGTH - PROP_MARGIN)
        slots.append((x, along(y)))
    return slots


def decor_green(mb, pal, rng):
    for x, y in prop_slots(rng, 3):
        h = rng.uniform(5.0, 8.0)
        mb.cylinder((x, y, h / 2.0), 0.7, h, pal["trunk"], segments=6)
        for k in range(2):
            s = 5.0 - k * 1.6
            mb.box((x, y, h + 1.2 + k * 2.0), (s, s, 2.2), pal["foliage"],
                   rot_z=rng.uniform(0, math.pi / 2))
    for x, y in prop_slots(rng, 3):
        s = rng.uniform(1.6, 3.0)
        mb.box((x, y, s * 0.4), (s, s * 0.8, s * 0.8), pal["rock"],
               rot_z=rng.uniform(0, math.pi))
    for x, y in prop_slots(rng, 6):
        mb.box((x, y, 0.5), (1.2, 1.2, 1.0), pal["grass_tuft"],
               rot_z=rng.uniform(0, math.pi))


def decor_lava(mb, pal, rng):
    # Lava streams cross the full width, per the spec. They reach the walls but
    # never the end planes, so tiling is preserved.
    for y_local in (8.0, 17.0):
        y = along(y_local)
        mb.box((0.0, y, 0.05), (WIDTH, rng.uniform(2.4, 3.6), 0.12), pal["lava"])
        mb.box((0.0, y, 0.02), (WIDTH, rng.uniform(4.5, 6.0), 0.06), pal["floor_alt"])
    for x, y in prop_slots(rng, 4):
        h = rng.uniform(2.5, 5.0)
        mb.box((x, y, h / 2.0), (rng.uniform(2, 3.5), rng.uniform(2, 3.5), h),
               pal["wall_alt"], rot_z=rng.uniform(0, math.pi))
    for x, y in prop_slots(rng, 5):
        mb.box((x, y, rng.uniform(1.0, 4.0)), (0.5, 0.5, 0.5), pal["ember"])


def decor_ice(mb, pal, rng):
    for x, y in prop_slots(rng, 3):
        h = rng.uniform(5.0, 10.0)
        mb.cylinder((x, y, h / 2.0), rng.uniform(1.2, 2.0), h, pal["floor_alt"],
                    segments=5, taper=0.12)
    for x, y in prop_slots(rng, 4):
        h = rng.uniform(2.0, 4.0)
        mb.cylinder((x, y, h / 2.0), 0.9, h, pal["ice_crystal"],
                    segments=5, taper=0.25)
    for x, y in prop_slots(rng, 3):
        s = rng.uniform(2.5, 4.5)
        mb.box((x, y, 0.35), (s, s * 0.7, 0.7), pal["wall_alt"],
               rot_z=rng.uniform(0, math.pi))


def decor_desert(mb, pal, rng):
    for x, y in prop_slots(rng, 3):
        h = rng.uniform(4.0, 7.0)
        mb.box((x, y, h / 2.0), (1.4, 1.4, h), pal["cactus"])
        if rng.random() < 0.7:
            side = rng.choice((-1, 1))
            mb.box((x + side * 1.4, y, h * 0.6), (1.8, 1.1, 1.1), pal["cactus"])
            mb.box((x + side * 2.2, y, h * 0.78), (1.1, 1.1, 2.6), pal["cactus"])
    for x, y in prop_slots(rng, 4):
        s = rng.uniform(1.8, 3.2)
        mb.box((x, y, s * 0.35), (s, s * 0.8, s * 0.7), pal["sand_rock"],
               rot_z=rng.uniform(0, math.pi))
    # Low dunes.
    for x, y in prop_slots(rng, 3):
        s = rng.uniform(6.0, 10.0)
        mb.box((x, y, 0.3), (s, s * 0.6, 0.6), pal["floor_alt"],
               rot_z=rng.uniform(0, math.pi))


def decor_stone(mb, pal, rng):
    for x, y in prop_slots(rng, 3):
        h = rng.uniform(4.0, 8.0)
        mb.cylinder((x, y, h / 2.0), rng.uniform(1.4, 2.4), h, pal["rock_dark"],
                    segments=5, taper=0.15)
    # Stalactites hang from the ceiling this zone has.
    for x, y in prop_slots(rng, 3):
        h = rng.uniform(3.0, 6.0)
        mb.cylinder((x, y, WALL_H - h / 2.0), rng.uniform(1.2, 2.0), h,
                    pal["rock_dark"], segments=5, taper=0.15)
    for x, y in prop_slots(rng, 4):
        mb.cylinder((x, y, 1.0), 0.8, 2.0, pal["cave_crystal"], segments=5, taper=0.2)


DECOR = {
    "green": decor_green,
    "lava": decor_lava,
    "ice": decor_ice,
    "desert": decor_desert,
    "stone": decor_stone,
}


def build_zone(zone, collection, offset_y=0.0, seed_bump=0):
    """Build one zone into `collection`; offset_y chains segments for the proof shot."""
    pal = zone_palette(zone)
    rng = random.Random(hash(zone["id"]) % 9999 + seed_bump)
    mb = MeshBuilder()
    build_shell(mb, pal, zone)
    DECOR[zone["decor"]](mb, pal, rng)
    obj = mb.build(zone["id"], collection)
    obj.location = (0.0, offset_y, 0.0)
    return obj


# ---------------------------------------------------------------- SCENE


def setup_scene(bounds_center, span, top_down=False):
    world = bpy.data.worlds.new("ZoneWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.07, 0.12, 1.0)
        bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world

    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 4.0
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-125))
    bpy.context.scene.collection.objects.link(sun)

    fill_data = bpy.data.lights.new("Fill", type="SUN")
    fill_data.energy = 1.8
    fill_data.color = (0.85, 0.90, 1.0)
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.rotation_euler = (math.radians(58), 0.0, math.radians(60))
    bpy.context.scene.collection.objects.link(fill)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 35.0
    cam_data.clip_end = 5000.0
    cam = bpy.data.objects.new("Cam", cam_data)
    if top_down:
        cam.location = (span * 0.35, bounds_center[1] - span * 0.30, span * 0.75)
    else:
        cam.location = (span * 0.55, bounds_center[1] + span * 0.70, span * 0.45)
    bpy.context.scene.collection.objects.link(cam)

    target = bpy.data.objects.new("Target", None)
    target.location = (bounds_center[0], bounds_center[1], WALL_H * 0.3)
    bpy.context.scene.collection.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    scene = bpy.context.scene
    scene.camera = cam
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 760
    scene.view_settings.view_transform = "Standard"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 40
    return cam


def render_to(path):
    bpy.context.scene.render.filepath = path
    try:
        bpy.ops.render.render(write_still=True)
        print("RENDER_OK", path)
    except Exception as exc:  # noqa: BLE001 - preview only
        print("RENDER_FAIL", path, exc)


def tri_count():
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
               for o in bpy.data.objects if o.type == "MESH")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for zone in ZONES:
        reset_scene()
        col = new_collection(zone["id"])
        build_zone(zone, col)
        tris = tri_count()

        glb = os.path.join(OUT_DIR, zone["id"] + ".glb")
        export_glb(glb)
        print("ZONE_EXPORT %s tris=%d -> %s" % (zone["id"], tris, glb))

        setup_scene((0.0, along(LENGTH / 2.0)), 60.0)
        render_to(os.path.join(OUT_DIR, zone["id"] + "_preview.png"))

    # Proof shot: the five segments chained end to end.
    reset_scene()
    col = new_collection("Chained")
    for i, zone in enumerate(ZONES):
        build_zone(zone, col, offset_y=along(LENGTH) * i, seed_bump=i)
    total = along(LENGTH * len(ZONES))
    setup_scene((0.0, total / 2.0), LENGTH * len(ZONES) * 1.6)
    render_to(os.path.join(OUT_DIR, "zones_chained.png"))
    print("CHAINED_TRIS", tri_count())


if __name__ == "__main__":
    main()
