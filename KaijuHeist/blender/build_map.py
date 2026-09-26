"""
Kaiju Heist - procedural map generator (Blender 5.x).

    blender -b --python build_map.py

Writes to ../assets/map/ : .blend, .glb (for the Roblox 3D importer) and 3 PNG
previews. Also emits ../src/Shared/MapData.lua so gameplay code can read anchor
positions instead of hardcoding them.

Everything is driven by CONFIG below: change a value, re-run, done.
Never hand-edit the .blend - it is overwritten on every run.

Units: 1 Blender unit = 1 Roblox stud. Z is up.
"""

import bpy
import math
import os
import random

# ---------------------------------------------------------------- CONFIG

CONFIG = {
    "street_half": 36.0,      # half-width of the central street (Y)
    "plot_width": 132.0,      # plot width along the street (X)
    "plot_depth": 122.0,      # plot depth (Y, measured from the street edge)
    "wall_thickness": 16.0,   # dirt walls separating plots
    "wall_height": 40.0,
    "plots_per_side": 4,
    "tile": 11.0,             # checker tile size for grass and dirt
    "island_margin_y": 57.0,  # grass margin beyond the plot rows
    "spawn_len": 140.0,       # spawn plaza depth (-X end)
    "desert_len": 215.0,      # desert zone depth (+X end)
    "dirt_depth": 60.0,       # dirt body thickness under the grass
    "taper_depth": 90.0,      # tapered island tip below the dirt
    "seed": 7,
}

# Corridor biomes, in walking order from the spawn plaza. The first
# `plots_per_side` entries each cover one plot cell; the last one covers the
# desert end where the boss altar sits. See ZONES.md.
#
# Plot floors deliberately stay grass in every biome: a player must recognise a
# base at a glance, and re-tinting them would make the map unreadable.
BIOMES = [
    {"id": "green", "label": "Zone Verte",
     "floor": ("grass_a", "grass_b"), "wall": ("dirt", "dirt_dark"),
     "cap": "grass_a", "rim": "grass_rim", "decor": "green"},
    {"id": "lava", "label": "Zone de Lave",
     "floor": ("lava_rock", "lava_rock_dark"), "wall": ("volcanic", "volcanic_dark"),
     "cap": "volcanic_dark", "rim": "lava_glow", "decor": "lava"},
    {"id": "ice", "label": "Zone de Glace",
     "floor": ("ice", "ice_dark"), "wall": ("snow", "ice_dark"),
     "cap": "snow", "rim": "ice_crystal", "decor": "ice"},
    {"id": "stone", "label": "Zone de Pierre",
     "floor": ("rock_floor", "rock_floor_dark"), "wall": ("rock_wall", "stone_dark"),
     "cap": "rock_floor_dark", "rim": "rock_floor", "decor": "stone"},
    {"id": "desert", "label": "Zone Desert",
     "floor": ("sand", "sand_dark"), "wall": ("sand_dark", "dirt"),
     "cap": "sand", "rim": "sand", "decor": "desert"},
]

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "assets", "map"))
SRC_SHARED_DIR = os.path.normpath(os.path.join(_HERE, "..", "src", "Shared"))

# ---------------------------------------------------------------- MATERIALS


def find_socket(sockets, identifier):
    """Look up by identifier. Node and socket *names* are localised when Blender
    runs in a language other than English (a French build names the node
    'BSDF guidee'), but identifiers are stable."""
    for sock in sockets:
        if sock.identifier == identifier:
            return sock
    return None


def find_node(node_tree, node_type):
    for node in node_tree.nodes:
        if node.type == node_type:
            return node
    return None


def make_material(name, color, emission=0.0, roughness=0.85, metallic=0.0):
    """Flat Roblox-style Principled BSDF. emission > 0 makes a glowing panel."""
    mat = bpy.data.materials.new(name)
    if not mat.use_nodes:
        mat.use_nodes = True

    tree = mat.node_tree
    bsdf = find_node(tree, "BSDF_PRINCIPLED")
    if bsdf is None:
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = find_node(tree, "OUTPUT_MATERIAL") or tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(bsdf.outputs[0], output.inputs[0])

    def put(identifier, value):
        sock = find_socket(bsdf.inputs, identifier)
        if sock is not None:
            sock.default_value = value

    put("Base Color", (*color, 1.0))
    put("Roughness", roughness)
    put("Metallic", metallic)
    if emission > 0.0:
        put("Emission Color", (*color, 1.0))
        put("Emission Strength", emission)
    mat.diffuse_color = (*color, 1.0)
    return mat


def build_palette():
    m = make_material
    return {
        "grass_a": m("Grass_A", (0.20, 0.66, 0.11)),
        "grass_b": m("Grass_B", (0.35, 0.85, 0.20)),
        "grass_rim": m("Grass_Rim", (0.16, 0.95, 0.12)),
        "grass_dark": m("Grass_Dark", (0.13, 0.42, 0.09)),
        "dirt": m("Dirt", (0.62, 0.43, 0.25)),
        "dirt_dark": m("Dirt_Dark", (0.50, 0.33, 0.18)),
        "sand": m("Sand", (0.90, 0.78, 0.47)),
        "sand_dark": m("Sand_Dark", (0.80, 0.66, 0.38)),
        "stone": m("Stone", (0.48, 0.49, 0.53)),
        "stone_dark": m("Stone_Dark", (0.33, 0.34, 0.38)),
        "wood": m("Wood", (0.42, 0.26, 0.13)),
        "wood_light": m("Wood_Light", (0.66, 0.47, 0.26)),
        "white": m("White", (0.93, 0.93, 0.93)),
        "red": m("Red", (0.84, 0.13, 0.13)),
        "yellow": m("Yellow", (0.98, 0.79, 0.11)),
        "blue": m("Blue", (0.16, 0.44, 0.86)),
        "metal_dark": m("Metal_Dark", (0.26, 0.28, 0.33), roughness=0.5, metallic=0.5),
        "metal_mid": m("Metal_Mid", (0.45, 0.47, 0.52), roughness=0.45, metallic=0.6),
        "glow_green": m("Glow_Green", (0.18, 1.00, 0.30), emission=1.6),
        "glow_cyan": m("Glow_Cyan", (0.25, 0.85, 1.00), emission=1.5),
        "glow_gold": m("Glow_Gold", (1.00, 0.78, 0.18), emission=1.4),
        "glow_violet": m("Glow_Violet", (0.65, 0.30, 1.00), emission=1.8),
        "text_decal": m("Text_Decal", (0.97, 0.97, 1.00), emission=0.9),
        "roof": m("Roof", (0.74, 0.35, 0.22)),
        "house": m("House_Wall", (0.82, 0.72, 0.54)),
        "leaf": m("Leaf", (0.16, 0.52, 0.18)),
        "leaf_light": m("Leaf_Light", (0.24, 0.66, 0.22)),
        "cactus": m("Cactus", (0.21, 0.55, 0.26)),
        "flower_pink": m("Flower_Pink", (0.95, 0.45, 0.65)),
        "flower_white": m("Flower_White", (0.97, 0.95, 0.85)),
        "water": m("Water", (0.20, 0.62, 0.90), roughness=0.15),
        # Biome grounds and walls. Hex values come from ZONES.md.
        "lava_rock": m("Lava_Rock", (0.24, 0.15, 0.14)),
        "lava_rock_dark": m("Lava_Rock_Dark", (0.16, 0.10, 0.09)),
        "lava_glow": m("Lava_Glow", (1.00, 0.34, 0.13), emission=2.2),
        "volcanic": m("Volcanic", (0.20, 0.17, 0.17)),
        "volcanic_dark": m("Volcanic_Dark", (0.12, 0.10, 0.10)),
        "ice": m("Ice", (0.51, 0.83, 0.98), roughness=0.25),
        "ice_dark": m("Ice_Dark", (0.36, 0.66, 0.86), roughness=0.25),
        "snow": m("Snow", (0.89, 0.95, 0.99)),
        "ice_crystal": m("Ice_Crystal", (0.60, 0.92, 1.00), emission=0.8, roughness=0.15),
        "rock_floor": m("Rock_Floor", (0.46, 0.46, 0.46)),
        "rock_floor_dark": m("Rock_Floor_Dark", (0.31, 0.31, 0.31)),
        "rock_wall": m("Rock_Wall", (0.26, 0.26, 0.26)),
        "cave_crystal": m("Cave_Crystal", (0.55, 0.70, 0.95), emission=0.9),
    }


# ---------------------------------------------------------------- MESH BUILDER


class MeshBuilder:
    """Accumulates primitives, then emits one multi-material object."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.face_mats = []
        self.mats = []
        self._mat_index = {}

    def _mat(self, material):
        key = material.name
        if key not in self._mat_index:
            self._mat_index[key] = len(self.mats)
            self.mats.append(material)
        return self._mat_index[key]

    def _emit(self, points, faces, material):
        base = len(self.verts)
        self.verts.extend(points)
        mi = self._mat(material)
        for f in faces:
            self.faces.append(tuple(base + i for i in f))
            self.face_mats.append(mi)

    # -- primitives ------------------------------------------------

    def box(self, center, size, material, rot_z=0.0):
        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        cx, cy, cz = center
        c, s = math.cos(rot_z), math.sin(rot_z)
        local = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
        ]
        pts = [(cx + x * c - y * s, cy + x * s + y * c, cz + z) for x, y, z in local]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self._emit(pts, faces, material)

    def frustum(self, center_xy, z_top, z_bottom, top_size, bottom_size, material):
        cx, cy = center_xy
        tx, ty = top_size[0] / 2.0, top_size[1] / 2.0
        bx, by = bottom_size[0] / 2.0, bottom_size[1] / 2.0
        pts = [
            (cx - bx, cy - by, z_bottom), (cx + bx, cy - by, z_bottom),
            (cx + bx, cy + by, z_bottom), (cx - bx, cy + by, z_bottom),
            (cx - tx, cy - ty, z_top), (cx + tx, cy - ty, z_top),
            (cx + tx, cy + ty, z_top), (cx - tx, cy + ty, z_top),
        ]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self._emit(pts, faces, material)

    def cylinder(self, center, radius, height, material, segments=10, taper=1.0):
        cx, cy, cz = center
        hz = height / 2.0
        pts = []
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius, cz - hz))
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            r = radius * taper
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, cz + hz))
        faces = [tuple(range(segments - 1, -1, -1)), tuple(range(segments, segments * 2))]
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((i, j, segments + j, segments + i))
        self._emit(pts, faces, material)

    def wedge(self, center, size, material, rot_z=0.0):
        """Ramp: tall at +X, flat at -X."""
        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        cx, cy, cz = center
        c, s = math.cos(rot_z), math.sin(rot_z)
        local = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (hx, -hy, hz), (hx, hy, hz),
        ]
        pts = [(cx + x * c - y * s, cy + x * s + y * c, cz + z) for x, y, z in local]
        faces = [(0, 3, 2, 1), (0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)]
        self._emit(pts, faces, material)

    def roof(self, center, size, material, rot_z=0.0):
        """Gable roof (triangular prism, ridge running along X)."""
        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        cx, cy, cz = center
        c, s = math.cos(rot_z), math.sin(rot_z)
        local = [
            (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
            (-hx, 0.0, hz), (hx, 0.0, hz),
        ]
        pts = [(cx + x * c - y * s, cy + x * s + y * c, cz + z) for x, y, z in local]
        faces = [(0, 3, 2, 1), (0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
        self._emit(pts, faces, material)

    def checker(self, x0, y0, x1, y1, z, tile, mat_a, mat_b):
        """Checkerboard floor (alternating quads)."""
        nx = max(1, int(round((x1 - x0) / tile)))
        ny = max(1, int(round((y1 - y0) / tile)))
        sx = (x1 - x0) / nx
        sy = (y1 - y0) / ny
        for i in range(nx):
            for j in range(ny):
                ax, bx = x0 + i * sx, x0 + (i + 1) * sx
                ay, by = y0 + j * sy, y0 + (j + 1) * sy
                mat = mat_a if (i + j) % 2 == 0 else mat_b
                self._emit(
                    [(ax, ay, z), (bx, ay, z), (bx, by, z), (ax, by, z)],
                    [(0, 1, 2, 3)],
                    mat,
                )

    def checker_yz(self, x, y0, z0, y1, z1, tile, mat_a, mat_b, facing=1):
        """Vertical checker on a plane facing X (dirt cliff faces)."""
        ny = max(1, int(round(abs(y1 - y0) / tile)))
        nz = max(1, int(round(abs(z1 - z0) / tile)))
        sy = (y1 - y0) / ny
        sz = (z1 - z0) / nz
        for i in range(ny):
            for j in range(nz):
                ay, by = y0 + i * sy, y0 + (i + 1) * sy
                az, bz = z0 + j * sz, z0 + (j + 1) * sz
                mat = mat_a if (i + j) % 2 == 0 else mat_b
                quad = [(x, ay, az), (x, by, az), (x, by, bz), (x, ay, bz)]
                if facing < 0:
                    quad.reverse()
                self._emit(quad, [(0, 1, 2, 3)], mat)

    def checker_xz(self, y, x0, z0, x1, z1, tile, mat_a, mat_b, facing=1):
        """Vertical checker on a plane facing Y."""
        nx = max(1, int(round(abs(x1 - x0) / tile)))
        nz = max(1, int(round(abs(z1 - z0) / tile)))
        sx = (x1 - x0) / nx
        sz = (z1 - z0) / nz
        for i in range(nx):
            for j in range(nz):
                ax, bx = x0 + i * sx, x0 + (i + 1) * sx
                az, bz = z0 + j * sz, z0 + (j + 1) * sz
                mat = mat_a if (i + j) % 2 == 0 else mat_b
                quad = [(ax, y, az), (ax, y, bz), (bx, y, bz), (bx, y, az)]
                if facing < 0:
                    quad.reverse()
                self._emit(quad, [(0, 1, 2, 3)], mat)

    # -- output ----------------------------------------------------

    def build(self, name, collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        for mat in self.mats:
            mesh.materials.append(mat)
        for poly, mi in zip(mesh.polygons, self.face_mats):
            poly.material_index = mi
        mesh.validate(verbose=False)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


# ---------------------------------------------------------------- HELPERS


def new_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def text_mesh(body, name, material, size=12.0, extrude=0.4):
    """Text -> reusable mesh: converted once, then instanced."""
    curve = bpy.data.curves.new(name + "_curve", type="FONT")
    curve.body = body
    curve.size = size
    curve.extrude = extrude
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    tmp = bpy.data.objects.new(name + "_tmp", curve)
    bpy.context.scene.collection.objects.link(tmp)
    deps = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
    mesh.name = name
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(curve)
    mesh.materials.clear()
    mesh.materials.append(material)
    return mesh


def place_mesh(mesh, name, location, collection, rotation=(0.0, 0.0, 0.0)):
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    return obj


def reset_scene():
    """Clear the scene without reloading the file.

    read_factory_settings() would invalidate the context when this runs from
    Blender's text editor, and the glTF export would then fail. Text datablocks
    are kept on purpose: the running script lives in one.
    """
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(scene.collection.children):
        scene.collection.children.unlink(col)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                  bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for item in list(block):
            block.remove(item)


def ensure_active_object():
    """The glTF exporter reads bpy.context.active_object, so guarantee one.

    Iterates bpy.data rather than view_layer.objects: right after a rebuild the
    view layer can still hand out stale/None entries. select_set() raises if the
    object is not in the view layer, which doubles as the membership test.
    """
    view_layer = bpy.context.view_layer
    view_layer.update()
    for obj in bpy.data.objects:
        if obj is None or obj.type != "MESH":
            continue
        try:
            obj.select_set(True)
        except RuntimeError:
            continue
        view_layer.objects.active = obj
        return


def export_glb(filepath):
    """GLB export that works both windowed (UI) and headless (-b)."""
    ensure_active_object()
    settings = dict(
        filepath=filepath,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )
    wm = getattr(bpy.context, "window_manager", None)
    window = wm.windows[0] if wm and len(wm.windows) > 0 else None
    if window is not None and hasattr(bpy.context, "temp_override"):
        with bpy.context.temp_override(
            window=window,
            screen=window.screen,
            scene=bpy.context.scene,
            view_layer=bpy.context.view_layer,
        ):
            bpy.ops.export_scene.gltf(**settings)
    else:
        bpy.ops.export_scene.gltf(**settings)


# ---------------------------------------------------------------- GEOMETRY


def layout():
    """Coordinates derived from CONFIG, shared by every builder."""
    c = CONFIG
    cell = c["plot_width"] + c["wall_thickness"]
    row_span = cell * c["plots_per_side"]
    row_x0 = -row_span / 2.0

    plot_centers = [
        row_x0 + i * cell + c["wall_thickness"] + c["plot_width"] / 2.0
        for i in range(c["plots_per_side"])
    ]
    wall_centers = [
        row_x0 + i * cell + c["wall_thickness"] / 2.0
        for i in range(c["plots_per_side"] + 1)
    ]

    plot_y_far = c["street_half"] + c["plot_depth"]
    island_y = plot_y_far + c["island_margin_y"]
    island_x_min = row_x0 - c["spawn_len"]
    island_x_max = row_x0 + row_span + c["desert_len"]

    return {
        "cell": cell,
        "plot_centers": plot_centers,
        "wall_centers": wall_centers,
        "row_x0": row_x0,
        "row_x1": row_x0 + row_span,
        "plot_y_far": plot_y_far,
        "island_y": island_y,
        "island_x_min": island_x_min,
        "island_x_max": island_x_max,
        "desert_x0": row_x0 + row_span + 12.0,
    }


def biome_segments(L):
    """Corridor split into [x0, x1, biome] bands, covering the whole island.

    The spawn approach reuses the first biome so the ground does not change
    material under the plaza, and the desert band runs to the island edge.
    """
    cell = L["cell"]
    count = CONFIG["plots_per_side"]
    segments = []
    # The spawn approach is folded into the first cell's band, and the last cell
    # runs up to the desert, so the bands are contiguous: no unpainted strip on
    # the ground, and no position where GetZoneAt would return nil.
    start = L["island_x_min"]
    for i in range(count):
        end = L["row_x0"] + (i + 1) * cell if i < count - 1 else L["desert_x0"]
        segments.append((start, end, BIOMES[min(i, len(BIOMES) - 2)]))
        start = end
    segments.append((start, L["island_x_max"], BIOMES[-1]))
    return segments


def biome_for_x(L, x):
    for x0, x1, biome in biome_segments(L):
        if x0 <= x <= x1:
            return biome
    return BIOMES[0]


def add_obsidian(mb, pal, x, y, rng):
    """Lava biome: sharp black rock, sometimes with a glowing seam."""
    h = rng.uniform(5.0, 11.0)
    mb.box((x, y, h / 2.0), (rng.uniform(4, 8), rng.uniform(4, 8), h),
           pal["volcanic_dark"], rot_z=rng.uniform(0, math.pi))
    if rng.random() < 0.45:
        mb.box((x, y, h * 0.55), (1.2, 6.0, 1.2), pal["lava_glow"],
               rot_z=rng.uniform(0, math.pi))


def add_lava_crack(mb, pal, x, y, rng):
    """Glowing fissure lying flush with the ground."""
    length = rng.uniform(14.0, 30.0)
    rot = rng.uniform(0, math.pi)
    mb.box((x, y, 0.12), (length, rng.uniform(2.5, 5.0), 0.24), pal["lava_glow"], rot_z=rot)
    mb.box((x, y, 0.08), (length + 4.0, rng.uniform(6.0, 9.0), 0.16),
           pal["lava_rock_dark"], rot_z=rot)


def add_ice_spike(mb, pal, x, y, rng):
    h = rng.uniform(8.0, 18.0)
    mb.cylinder((x, y, h / 2.0), rng.uniform(2.0, 3.6), h, pal["ice"],
                segments=6, taper=0.12)
    if rng.random() < 0.4:
        mb.cylinder((x + rng.uniform(-4, 4), y + rng.uniform(-4, 4), h * 0.3),
                    1.6, h * 0.6, pal["ice_crystal"], segments=5, taper=0.2)


def add_snow_mound(mb, pal, x, y, rng):
    s = rng.uniform(6.0, 13.0)
    mb.box((x, y, 1.0), (s, s * rng.uniform(0.7, 1.2), 2.0), pal["snow"],
           rot_z=rng.uniform(0, math.pi))


def add_stalagmite(mb, pal, x, y, rng):
    h = rng.uniform(7.0, 16.0)
    mb.cylinder((x, y, h / 2.0), rng.uniform(2.4, 4.2), h, pal["rock_wall"],
                segments=6, taper=0.18)
    if rng.random() < 0.35:
        mb.box((x, y, h + 1.0), (2.0, 2.0, 2.0), pal["cave_crystal"],
               rot_z=rng.uniform(0, math.pi))


def add_biome_decor(mb, pal, biome, x, y, rng):
    """Dispatch one scattered prop appropriate to the biome."""
    kind = biome["decor"]
    roll = rng.random()
    if kind == "green":
        (add_bush if roll < 0.45 else add_rock if roll < 0.75 else add_tree)(mb, pal, x, y, rng)
    elif kind == "lava":
        (add_obsidian if roll < 0.6 else add_lava_crack)(mb, pal, x, y, rng)
    elif kind == "ice":
        (add_ice_spike if roll < 0.55 else add_snow_mound)(mb, pal, x, y, rng)
    elif kind == "stone":
        (add_stalagmite if roll < 0.6 else add_rock)(mb, pal, x, y, rng)
    else:  # desert
        (add_cactus if roll < 0.5 else add_rock)(mb, pal, x, y, rng)


def build_island(pal, col, L):
    """Island base: checker grass, bright rim, dirt body, tapered tip."""
    mb = MeshBuilder()
    x0, x1 = L["island_x_min"], L["island_x_max"]
    y0, y1 = -L["island_y"], L["island_y"]
    rim = 11.0

    # Ground, painted band by band so the corridor walks through biomes.
    for sx0, sx1, biome in biome_segments(L):
        a, b = biome["floor"]
        tile = CONFIG["tile"] * (1.6 if biome["id"] == "desert" else 1.0)
        mb.checker(max(sx0, x0 + rim), y0 + rim, min(sx1, x1 - rim), y1 - rim,
                   0.0, tile, pal[a], pal[b])

    # Bright rim along the island edge, following the biome it borders.
    for sx0, sx1, biome in biome_segments(L):
        mat = pal[biome["rim"]]
        span = min(sx1, x1) - max(sx0, x0)
        mid = (max(sx0, x0) + min(sx1, x1)) / 2.0
        mb.box((mid, y0 + rim / 2.0, -0.4), (span, rim, 0.8), mat)
        mb.box((mid, y1 - rim / 2.0, -0.4), (span, rim, 0.8), mat)
    mb.box((x0 + rim / 2.0, 0.0, -0.4), (rim, y1 - y0, 0.8), pal[BIOMES[0]["rim"]])
    mb.box((x1 - rim / 2.0, 0.0, -0.4), (rim, y1 - y0, 0.8), pal[BIOMES[-1]["rim"]])

    # Dirt body plus tip. Top stays below the grass to avoid z-fighting.
    dirt_top = -1.2
    dirt_bottom = -CONFIG["dirt_depth"]
    mb.box(((x0 + x1) / 2.0, 0.0, (dirt_top + dirt_bottom) / 2.0),
           (x1 - x0, y1 - y0, dirt_top - dirt_bottom), pal["dirt"])
    mb.frustum(((x0 + x1) / 2.0, 0.0), dirt_bottom,
               dirt_bottom - CONFIG["taper_depth"],
               (x1 - x0, y1 - y0), ((x1 - x0) * 0.22, (y1 - y0) * 0.14), pal["dirt_dark"])

    # Dirt checker on all four island cliff faces.
    t = CONFIG["tile"] * 1.4
    mb.checker_yz(x0 - 0.2, y0, dirt_bottom, y1, dirt_top, t, pal["dirt"], pal["dirt_dark"], facing=-1)
    mb.checker_yz(x1 + 0.2, y0, dirt_bottom, y1, dirt_top, t, pal["dirt"], pal["dirt_dark"], facing=1)
    mb.checker_xz(y0 - 0.2, x0, dirt_bottom, x1, dirt_top, t, pal["dirt"], pal["dirt_dark"], facing=-1)
    mb.checker_xz(y1 + 0.2, x0, dirt_bottom, x1, dirt_top, t, pal["dirt"], pal["dirt_dark"], facing=1)

    # Rocks clinging under the island.
    rng = random.Random(CONFIG["seed"] + 99)
    for _ in range(26):
        rx = rng.uniform(x0 + 40, x1 - 40)
        ry = rng.uniform(y0 + 30, y1 - 30)
        rz = rng.uniform(dirt_bottom - 70, dirt_bottom - 6)
        s = rng.uniform(6, 20)
        mb.box((rx, ry, rz), (s, s * rng.uniform(0.6, 1.3), s * rng.uniform(0.5, 1.1)),
               pal["dirt_dark"], rot_z=rng.uniform(0, math.pi))

    return mb.build("Island_Base", col)


def build_walls(pal, col, L):
    """Dirt walls between plots, grass-capped."""
    mb = MeshBuilder()
    h = CONFIG["wall_height"]
    t = CONFIG["wall_thickness"]
    depth = CONFIG["plot_depth"]
    y_mid = CONFIG["street_half"] + depth / 2.0

    tile = CONFIG["tile"]
    for i, wx in enumerate(L["wall_centers"]):
        # Each wall wears the biome of the cell it opens onto; the trailing wall
        # reuses the last cell's so the corridor ends cleanly.
        biome = BIOMES[min(i, CONFIG["plots_per_side"] - 1, len(BIOMES) - 2)]
        wall_a, wall_b = (pal[k] for k in biome["wall"])
        cap = pal[biome["cap"]]
        for side in (1, -1):
            y_a = side * CONFIG["street_half"]
            y_b = side * (CONFIG["street_half"] + depth)
            mb.box((wx, side * y_mid, h / 2.0), (t, depth, h), wall_a)
            mb.box((wx, side * y_mid, h + 1.0), (t + 1.5, depth + 1.5, 2.0), cap)
            # Checker on both flanks plus the street-facing nose.
            mb.checker_yz(wx - t / 2.0 - 0.2, min(y_a, y_b), 0.0, max(y_a, y_b), h,
                          tile, wall_a, wall_b, facing=-1)
            mb.checker_yz(wx + t / 2.0 + 0.2, min(y_a, y_b), 0.0, max(y_a, y_b), h,
                          tile, wall_b, wall_a, facing=1)
            mb.checker_xz(y_a - side * 0.2, wx - t / 2.0, 0.0, wx + t / 2.0, h,
                          tile, wall_a, wall_b, facing=-side)

    # Back wall behind the plot rows.
    back = L["plot_y_far"] + 3.0
    for side in (1, -1):
        mb.box(((L["row_x0"] + L["row_x1"]) / 2.0, side * back, h / 2.0),
               (L["row_x1"] - L["row_x0"], 6.0, h), pal["dirt"])
        mb.box(((L["row_x0"] + L["row_x1"]) / 2.0, side * back, h + 1.0),
               (L["row_x1"] - L["row_x0"], 7.5, 2.0), pal["grass_a"])

    return mb.build("Plot_Walls", col)


def add_fence(mb, pal, cx, cy, sx, sy, post_step=9.0, height=7.0, rot=0.0):
    """Pen fence: posts plus two rails."""
    hx, hy = sx / 2.0, sy / 2.0
    post = pal["wood_light"]
    rail = pal["wood"]

    nx = max(2, int(round(sx / post_step)))
    ny = max(2, int(round(sy / post_step)))

    def world(lx, ly):
        c, s = math.cos(rot), math.sin(rot)
        return (cx + lx * c - ly * s, cy + lx * s + ly * c)

    for i in range(nx + 1):
        lx = -hx + sx * i / nx
        for ly in (-hy, hy):
            wx, wy = world(lx, ly)
            mb.box((wx, wy, height / 2.0), (1.5, 1.5, height), post, rot_z=rot)
    for j in range(ny + 1):
        ly = -hy + sy * j / ny
        for lx in (-hx, hx):
            wx, wy = world(lx, ly)
            mb.box((wx, wy, height / 2.0), (1.5, 1.5, height), post, rot_z=rot)

    for z in (height * 0.38, height * 0.78):
        for ly in (-hy, hy):
            wx, wy = world(0.0, ly)
            mb.box((wx, wy, z), (sx, 0.8, 1.1), rail, rot_z=rot)
        for lx in (-hx, hx):
            wx, wy = world(lx, 0.0)
            mb.box((wx, wy, z), (0.8, sy, 1.1), rail, rot_z=rot)


def add_stall(mb, pal, x, y, stripe, rot=0.0, sign_mat=None):
    """Merchant stall: wooden counter, striped awning, sign board."""
    w, d = 18.0, 9.0
    mb.box((x, y, 4.0), (w, d, 8.0), pal["wood"], rot_z=rot)
    mb.box((x, y, 8.4), (w + 1.5, d + 1.5, 1.0), pal["wood_light"], rot_z=rot)

    c, s = math.cos(rot), math.sin(rot)
    for lx in (-w / 2 + 1.2, w / 2 - 1.2):
        for ly in (-d / 2 + 1.2, d / 2 - 1.2):
            px, py = x + lx * c - ly * s, y + lx * s + ly * c
            mb.box((px, py, 7.6), (1.2, 1.2, 15.2), pal["wood_light"])

    # Awning: alternating stripes.
    n = 7
    bw = (w + 4.0) / n
    for i in range(n):
        lx = -(w + 4.0) / 2 + bw * (i + 0.5)
        mat = stripe if i % 2 == 0 else pal["white"]
        px, py = x + lx * c, y + lx * s
        mb.box((px, py, 15.8), (bw, d + 5.0, 1.6), mat, rot_z=rot)
    mb.box((x, y - (d + 5.0) / 2 * c, 14.6), (w + 4.6, 1.4, 2.6), pal["wood"], rot_z=rot)

    if sign_mat is not None:
        by = y - (d / 2 + 0.9) * c
        bx = x + (d / 2 + 0.9) * s
        mb.box((bx, by, 11.2), (w * 0.78, 0.7, 4.6), sign_mat, rot_z=rot)


def add_house(mb, pal, x, y, rot=0.0):
    mb.box((x, y, 8.0), (18.0, 16.0, 16.0), pal["house"], rot_z=rot)
    mb.roof((x, y, 19.5), (19.5, 18.0, 7.0), pal["roof"], rot_z=rot)
    c, s = math.cos(rot), math.sin(rot)
    door_y = y - 8.2 * c
    door_x = x + 8.2 * s
    mb.box((door_x, door_y, 5.0), (5.0, 1.0, 10.0), pal["wood"], rot_z=rot)
    for lx in (-6.0, 6.0):
        wx, wy = x + lx * c + 8.2 * s, y + lx * s - 8.2 * c
        mb.box((wx, wy, 11.0), (4.0, 1.0, 4.0), pal["glow_gold"], rot_z=rot)
    mb.box((x + 6.0 * c, y + 5.0 * s, 24.0), (3.0, 3.0, 9.0), pal["stone"], rot_z=rot)


def add_machine(mb, pal, x, y, rot=0.0):
    """Hatching machine: metal block, green panels, capsule dome."""
    mb.box((x, y, 8.0), (16.0, 13.0, 16.0), pal["metal_dark"], rot_z=rot)
    mb.box((x, y, 16.8), (17.5, 14.5, 2.0), pal["metal_mid"], rot_z=rot)
    c, s = math.cos(rot), math.sin(rot)
    for lx in (-5.6, 5.6):
        px, py = x + lx * c, y + lx * s
        mb.box((px, py, 9.5), (3.6, 13.6, 9.0), pal["glow_green"], rot_z=rot)
    mb.box((x, y - 7.1 * c, 9.0), (7.0, 0.8, 8.0), pal["glow_cyan"], rot_z=rot)
    mb.cylinder((x, y, 21.5), 3.4, 6.0, pal["glow_green"], segments=12)
    for lx in (-8.6, 8.6):
        px, py = x + lx * c, y + lx * s
        mb.box((px, py, 5.0), (2.4, 2.4, 10.0), pal["metal_mid"])
        mb.box((px, py, 11.0), (3.4, 3.4, 2.0), pal["glow_green"])
    # Steps.
    for i in range(3):
        mb.box((x, y - (7.0 + i * 2.6) * c, (3 - i) * 1.1 - 0.5),
               (11.0, 2.6, 2.2), pal["metal_mid"], rot_z=rot)


def add_conveyor(mb, pal, x, y, rot=0.0):
    """Conveyor ramp feeding a raised platform."""
    length, width = 26.0, 10.0
    mb.wedge((x, y, 3.0), (length, width, 6.0), pal["metal_dark"], rot_z=rot)
    c, s = math.cos(rot), math.sin(rot)
    for i in range(7):
        lx = -length / 2 + 2.0 + i * (length - 4.0) / 6.0
        h = 6.0 * (i + 1) / 7.0
        px, py = x + lx * c, y + lx * s
        mb.box((px, py, h - 0.2), (1.6, width - 1.4, 0.8), pal["metal_mid"], rot_z=rot)
    ex, ey = x + (length / 2 + 4.0) * c, y + (length / 2 + 4.0) * s
    mb.box((ex, ey, 3.0), (9.0, width + 2.0, 6.0), pal["metal_mid"], rot_z=rot)
    mb.box((ex, ey, 6.4), (9.6, width + 2.6, 0.9), pal["glow_cyan"], rot_z=rot)


def add_lamp(mb, pal, x, y, glow=None):
    mb.cylinder((x, y, 0.8), 2.4, 1.6, pal["stone_dark"], segments=8)
    mb.cylinder((x, y, 11.0), 0.9, 21.0, pal["metal_dark"], segments=8)
    mb.box((x, y, 22.4), (3.4, 3.4, 2.2), pal["metal_dark"])
    mb.box((x, y, 21.0), (2.6, 2.6, 1.6), glow or pal["glow_gold"])


def add_bush(mb, pal, x, y, rng):
    s = rng.uniform(3.4, 6.2)
    mb.box((x, y, s * 0.45), (s, s * rng.uniform(0.8, 1.2), s * 0.9),
           pal["leaf"], rot_z=rng.uniform(0, math.pi))
    mb.box((x + rng.uniform(-1.6, 1.6), y + rng.uniform(-1.6, 1.6), s * 0.95),
           (s * 0.6, s * 0.6, s * 0.5), pal["leaf_light"], rot_z=rng.uniform(0, math.pi))


def add_rock(mb, pal, x, y, rng):
    s = rng.uniform(2.6, 6.0)
    mb.box((x, y, s * 0.35), (s, s * rng.uniform(0.7, 1.3), s * 0.7),
           pal["stone"], rot_z=rng.uniform(0, math.pi))
    if rng.random() < 0.5:
        mb.box((x + s * 0.4, y - s * 0.3, s * 0.25), (s * 0.5, s * 0.5, s * 0.5),
               pal["stone_dark"], rot_z=rng.uniform(0, math.pi))


def add_flowers(mb, pal, x, y, rng):
    for _ in range(rng.randint(2, 4)):
        fx = x + rng.uniform(-3.5, 3.5)
        fy = y + rng.uniform(-3.5, 3.5)
        mb.box((fx, fy, 1.1), (0.4, 0.4, 2.2), pal["leaf"])
        mat = pal["flower_pink"] if rng.random() < 0.5 else pal["flower_white"]
        mb.box((fx, fy, 2.5), (1.5, 1.5, 1.0), mat, rot_z=rng.uniform(0, math.pi))


def add_tree(mb, pal, x, y, rng):
    h = rng.uniform(14.0, 22.0)
    mb.cylinder((x, y, h / 2.0), 1.9, h, pal["wood"], segments=8)
    for i in range(3):
        s = (3 - i) * 5.0 + 6.0
        mb.box((x, y, h + 3.0 + i * 4.2), (s, s, 5.0),
               pal["leaf"] if i % 2 == 0 else pal["leaf_light"],
               rot_z=rng.uniform(0, math.pi / 2))


def add_cactus(mb, pal, x, y, rng):
    h = rng.uniform(10.0, 18.0)
    mb.box((x, y, h / 2.0), (3.4, 3.4, h), pal["cactus"])
    if rng.random() < 0.7:
        side = rng.choice((-1, 1))
        mb.box((x + side * 3.4, y, h * 0.58), (4.0, 2.6, 2.6), pal["cactus"])
        mb.box((x + side * 5.2, y, h * 0.74), (2.6, 2.6, 7.0), pal["cactus"])


def add_crate(mb, pal, x, y, rng):
    s = rng.uniform(4.0, 6.0)
    r = rng.uniform(0, math.pi)
    mb.box((x, y, s / 2.0), (s, s, s), pal["wood_light"], rot_z=r)
    mb.box((x, y, s / 2.0), (s + 0.3, s * 0.2, s * 0.2), pal["wood"], rot_z=r)
    if rng.random() < 0.4:
        mb.box((x + rng.uniform(-2, 2), y + rng.uniform(-2, 2), s + s * 0.35),
               (s * 0.7, s * 0.7, s * 0.7), pal["wood"], rot_z=rng.uniform(0, math.pi))


def build_plot(pal, col, L, index, side, text_meshes):
    """One complete plot. side=+1 (north row) or -1 (south row)."""
    cx = L["plot_centers"][index]
    rng = random.Random(CONFIG["seed"] * 100 + index * 7 + (0 if side > 0 else 3))
    name = "Plot_%s%d" % ("N" if side > 0 else "S", index + 1)

    w = CONFIG["plot_width"]
    d = CONFIG["plot_depth"]
    hw = w / 2.0

    def P(lx, ly):
        """Local (along-street, depth-from-street) -> world."""
        return (cx + side * lx, side * (CONFIG["street_half"] + ly))

    def rot(a=0.0):
        return a if side > 0 else a + math.pi

    mb = MeshBuilder()

    # Plot floor: same checker as the street, one shade lighter.
    y_near = side * CONFIG["street_half"]
    y_far = side * (CONFIG["street_half"] + d)
    mb.checker(cx - hw, min(y_near, y_far), cx + hw, max(y_near, y_far),
               0.05, CONFIG["tile"], pal["grass_b"], pal["grass_a"])

    # Safe-zone line and shield markers.
    lx0, ly0 = P(0.0, 4.0)
    mb.box((lx0, ly0, 0.16), (w - 4.0, 1.6, 0.3), pal["red"])
    for lx in (-30.0, 30.0):
        px, py = P(lx, 12.0)
        mb.cylinder((px, py, 0.18), 3.0, 0.3, pal["blue"], segments=6)

    # Stalls, hatching machine, conveyor.
    sx, sy = P(-44.0, 24.0)
    add_stall(mb, pal, sx, sy, pal["red"], rot=rot(), sign_mat=pal["red"])
    sx, sy = P(44.0, 24.0)
    add_stall(mb, pal, sx, sy, pal["yellow"], rot=rot(), sign_mat=pal["yellow"])
    mx, my = P(0.0, 26.0)
    add_machine(mb, pal, mx, my, rot=rot())
    kx, ky = P(-16.0, 46.0)
    add_conveyor(mb, pal, kx, ky, rot=rot(math.pi / 2))

    # Pens: 3 columns x 2 rows, each with its display podium.
    pen_anchors = []
    for ly in (66.0, 104.0):
        for colx in (-46.0, -12.0, 22.0):
            px, py = P(colx, ly)
            pen_anchors.append((px, py, 1.8))
            add_fence(mb, pal, px, py, 30.0, 32.0, rot=rot())
            # Kaiju display podium: stone step plus a glowing marker.
            mb.cylinder((px, py, 0.45), 7.2, 0.9, pal["stone_dark"], segments=12)
            mb.cylinder((px, py, 1.05), 6.2, 0.8, pal["stone"], segments=12)
            mb.cylinder((px, py, 1.55), 2.1, 0.5, pal["glow_cyan"], segments=10)
            if rng.random() < 0.55:
                add_flowers(mb, pal, px + rng.uniform(-11, 11), py + rng.uniform(-12, 12), rng)

    # House at the back of the plot.
    hx, hy = P(50.0, 98.0)
    add_house(mb, pal, hx, hy, rot=rot(math.pi))

    # Corner lamp posts.
    for lx, ly in ((-hw + 8.0, 10.0), (hw - 8.0, 10.0),
                   (-hw + 8.0, d - 8.0), (hw - 8.0, d - 8.0)):
        px, py = P(lx, ly)
        add_lamp(mb, pal, px, py, glow=pal["glow_gold"] if side > 0 else pal["glow_cyan"])

    # Crates beside the stalls.
    for lx, ly in ((-56.0, 20.0), (-52.0, 30.0), (56.0, 20.0), (52.0, 31.0)):
        px, py = P(lx, ly)
        add_crate(mb, pal, px, py, rng)

    # Scattered decor, skipping the pen block and the entrance.
    for _ in range(16):
        lx = rng.uniform(-hw + 6.0, hw - 6.0)
        ly = rng.uniform(8.0, d - 6.0)
        if 40.0 < ly < 118.0 and -62.0 < lx < 40.0:
            continue
        if ly < 36.0 and abs(lx) < 58.0:
            continue
        px, py = P(lx, ly)
        roll = rng.random()
        if roll < 0.45:
            add_bush(mb, pal, px, py, rng)
        elif roll < 0.75:
            add_rock(mb, pal, px, py, rng)
        else:
            add_tree(mb, pal, px, py, rng)

    obj = mb.build(name, col)

    # Ground text, readable from the street.
    tx, ty = P(0.0, 14.0)
    flat_rot = (0.0, 0.0, 0.0 if side > 0 else math.pi)
    place_mesh(text_meshes["zone"], name + "_SafeZoneText", (tx, ty, 0.3), col, flat_rot)

    # Upright signs on both stalls, facing the street.
    sign_rot = (math.pi / 2, 0.0, 0.0 if side > 0 else math.pi)
    for key, lx in (("vendre", -44.0), ("boutique", 44.0)):
        px, py = P(lx, 18.0)
        place_mesh(text_meshes[key], "%s_Sign_%s" % (name, key), (px, py, 11.2), col, sign_rot)

    # Anchors consumed by the Lua side through the generated MapData module.
    ey = side * CONFIG["street_half"]
    anchors = {
        "id": "%s%d" % ("N" if side > 0 else "S", index + 1),
        "side": "north" if side > 0 else "south",
        "center": P(0.0, d / 2.0) + (0.0,),
        "entrance": P(0.0, 4.0) + (0.0,),
        "spawn": P(0.0, 16.0) + (0.0,),
        "machine": P(0.0, 26.0) + (0.0,),
        "sellStand": P(-44.0, 24.0) + (0.0,),
        "shopStand": P(44.0, 24.0) + (0.0,),
        "conveyor": P(-16.0, 46.0) + (0.0,),
        "house": P(50.0, 98.0) + (0.0,),
        "pens": pen_anchors,
        "bounds": (
            (cx - hw, min(ey, y_far), 0.0),
            (cx + hw, max(ey, y_far), CONFIG["wall_height"]),
        ),
    }
    return obj, anchors


def build_street(pal, col, L):
    """Central street: lamps, crates, bushes, ground markings."""
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 21)
    sh = CONFIG["street_half"]

    for x in range(int(L["row_x0"]) + 20, int(L["row_x1"]), 74):
        for side in (1, -1):
            add_lamp(mb, pal, float(x), side * (sh - 6.0), glow=pal["glow_gold"])

    # Ground dashes marking the street axis, tinted per biome for contrast.
    for x in range(int(L["row_x0"]), int(L["row_x1"]), 26):
        dash_mat = pal[biome_for_x(L, float(x))["wall"][1]]
        mb.box((float(x) + 6.0, 0.0, 0.12), (12.0, 2.2, 0.24), dash_mat)

    # Decor hugs the edges so the running lane stays clear, and matches the
    # biome the player is currently walking through.
    for _ in range(80):
        x = rng.uniform(L["island_x_min"] + 24, L["desert_x0"] - 14)
        y = rng.choice((1, -1)) * rng.uniform(sh - 14.0, sh - 4.0)
        add_biome_decor(mb, pal, biome_for_x(L, x), x, y, rng)

    # Outer margins, behind the back walls.
    for _ in range(120):
        x = rng.uniform(L["island_x_min"] + 20, L["desert_x0"] - 20)
        y = rng.choice((1, -1)) * rng.uniform(L["plot_y_far"] + 12, L["island_y"] - 14)
        add_biome_decor(mb, pal, biome_for_x(L, x), x, y, rng)

    return mb.build("Street_Props", col)


def build_spawn(pal, col, L, text_meshes):
    """Spawn plaza: stone slab, archway, leaderboard podium, fountain."""
    mb = MeshBuilder()
    cx = L["island_x_min"] + CONFIG["spawn_len"] / 2.0 + 10.0
    half = CONFIG["spawn_len"] / 2.0 - 14.0

    mb.box((cx, 0.0, 0.35), (half * 2 + 6.0, 146.0, 0.7), pal["stone_dark"])
    mb.checker(cx - half, -70.0, cx + half, 70.0, 0.75, 13.0, pal["stone"], pal["stone_dark"])

    # Central fountain.
    mb.cylinder((cx, 0.0, 1.6), 17.0, 3.2, pal["stone"], segments=14)
    mb.cylinder((cx, 0.0, 3.3), 15.0, 0.8, pal["water"], segments=14)
    mb.cylinder((cx, 0.0, 6.0), 4.0, 9.0, pal["stone_dark"], segments=10)
    mb.cylinder((cx, 0.0, 11.5), 6.5, 2.0, pal["stone"], segments=12, taper=0.5)
    mb.cylinder((cx, 0.0, 15.0), 2.2, 6.0, pal["glow_cyan"], segments=8)

    # Archway onto the street.
    ax = L["row_x0"] - 16.0
    for side in (1, -1):
        mb.box((ax, side * 38.0, 22.0), (10.0, 12.0, 44.0), pal["stone"])
        mb.box((ax, side * 38.0, 45.0), (13.0, 15.0, 3.0), pal["stone_dark"])
        mb.box((ax, side * 30.0, 30.0), (5.0, 3.0, 5.0), pal["glow_violet"])
    mb.box((ax, 0.0, 48.0), (12.0, 88.0, 8.0), pal["stone"])
    mb.box((ax, 0.0, 53.5), (14.0, 92.0, 3.0), pal["stone_dark"])
    mb.box((ax, 0.0, 44.0), (6.0, 60.0, 2.5), pal["glow_violet"])

    # Leaderboard podium: 2nd / 1st / 3rd.
    for ly, h in ((-52.0, 15.0), (-34.0, 22.0), (-16.0, 11.0)):
        mb.box((cx - 34.0, ly, h / 2.0), (15.0, 15.0, h), pal["stone"])
        mb.box((cx - 34.0, ly, h + 0.9), (16.5, 16.5, 1.8), pal["stone_dark"])
        mb.box((cx - 34.0, ly, h + 2.4), (6.0, 6.0, 1.2), pal["glow_gold"])
        mb.cylinder((cx - 34.0, ly, h + 9.0), 1.2, 12.0, pal["metal_mid"], segments=6)

    rng = random.Random(CONFIG["seed"] + 5)
    for _ in range(18):
        x = rng.uniform(cx - half - 24, cx + half + 10)
        y = rng.choice((1, -1)) * rng.uniform(76.0, L["island_y"] - 16.0)
        (add_tree if rng.random() < 0.5 else add_bush)(mb, pal, x, y, rng)
    for i in range(6):
        add_lamp(mb, pal, cx - half + i * (half * 2 / 5), 66.0, glow=pal["glow_violet"])
        add_lamp(mb, pal, cx - half + i * (half * 2 / 5), -66.0, glow=pal["glow_violet"])

    obj = mb.build("Spawn_Plaza", col)
    place_mesh(text_meshes["spawn"], "Spawn_Text", (cx, 44.0, 0.4), col)
    return obj


def build_desert(pal, col, L):
    """Desert zone plus boss altar (floating platform and beam)."""
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 42)
    x0 = L["desert_x0"]
    x1 = L["island_x_max"] - 12.0
    cx = (x0 + x1) / 2.0

    # Dunes.
    for _ in range(26):
        dx = rng.uniform(x0 + 12, x1 - 12)
        dy = rng.uniform(-L["island_y"] + 22, L["island_y"] - 22)
        s = rng.uniform(16, 42)
        mb.box((dx, dy, 1.4), (s, s * rng.uniform(0.6, 1.2), 2.8),
               pal["sand_dark"], rot_z=rng.uniform(0, math.pi))

    for _ in range(40):
        dx = rng.uniform(x0 + 10, x1 - 10)
        dy = rng.uniform(-L["island_y"] + 18, L["island_y"] - 18)
        if abs(dy) < 30 and abs(dx - cx) < 60:
            continue
        roll = rng.random()
        if roll < 0.5:
            add_cactus(mb, pal, dx, dy, rng)
        elif roll < 0.8:
            add_rock(mb, pal, dx, dy, rng)
        else:
            add_crate(mb, pal, dx, dy, rng)

    # Altar: stepped base, pillars, beam.
    mb.cylinder((cx, 0.0, 1.5), 40.0, 3.0, pal["stone"], segments=16)
    mb.cylinder((cx, 0.0, 4.0), 32.0, 3.0, pal["stone_dark"], segments=16)
    mb.cylinder((cx, 0.0, 6.4), 25.0, 2.6, pal["stone"], segments=16)
    mb.cylinder((cx, 0.0, 8.2), 9.0, 1.8, pal["glow_violet"], segments=12)
    for i in range(6):
        a = 2 * math.pi * i / 6
        px, py = cx + math.cos(a) * 29.0, math.sin(a) * 29.0
        mb.box((px, py, 17.0), (7.0, 7.0, 26.0), pal["stone"], rot_z=a)
        mb.box((px, py, 31.0), (9.0, 9.0, 3.0), pal["stone_dark"], rot_z=a)
        mb.box((px, py, 33.5), (3.5, 3.5, 3.0), pal["glow_violet"], rot_z=a)
    mb.cylinder((cx, 0.0, 82.0), 5.5, 148.0, pal["glow_violet"], segments=12, taper=0.55)

    # Rocks floating above the altar.
    for i in range(7):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(16, 52)
        mb.box((cx + math.cos(a) * r, math.sin(a) * r, rng.uniform(60, 130)),
               (rng.uniform(9, 22), rng.uniform(9, 22), rng.uniform(5, 12)),
               pal["stone_dark"], rot_z=rng.uniform(0, math.pi))

    return mb.build("Desert_Zone", col)


# ---------------------------------------------------------------- MAP DATA EXPORT


def to_roblox(point):
    """Blender (Z-up) -> Roblox/glTF (Y-up), matching export_yup=True on the GLB.

    Get this wrong and every anchor lands somewhere else than the mesh it
    belongs to, so it is the one conversion worth stating explicitly.
    """
    x, y, z = point
    return (x, z, -y)


def _v3(point):
    # +0.0 normalises "-0.00" away.
    x, y, z = (v + 0.0 for v in to_roblox(point))
    return "Vector3.new(%.2f, %.2f, %.2f)" % (x, y, z)


def _bounds(corner_a, corner_b):
    """Axis-aligned box as (min, max) in Roblox axes.

    The Y-up conversion flips Y, so a Blender corner pair is not sorted any more
    once converted: sort per component or every containment test breaks.
    """
    a, b = to_roblox(corner_a), to_roblox(corner_b)
    low = tuple(min(a[i], b[i]) for i in range(3))
    high = tuple(max(a[i], b[i]) for i in range(3))
    fmt = "Vector3.new(%.2f, %.2f, %.2f)"
    return (fmt % tuple(v + 0.0 for v in low), fmt % tuple(v + 0.0 for v in high))


def write_map_data(filepath, L, plot_anchors):
    """Emit src/Shared/MapData.lua so gameplay code never hardcodes a position."""
    lines = [
        "--!strict",
        "-- GENERATED FILE - do not edit by hand.",
        "-- Produced by KaijuHeist/blender/build_map.py; re-run that script to update.",
        "--",
        "-- Positions are studs in Roblox axes (Y up), matching kaiju_heist_map.glb",
        "-- imported at scale 1. Plot ids are N1..N4 (north row) and S1..S4 (south row).",
        "",
        "local MapData = {}",
        "",
    ]

    x0, x1 = L["island_x_min"], L["island_x_max"]
    y0, y1 = -L["island_y"], L["island_y"]
    sh = CONFIG["street_half"]

    island_lo, island_hi = _bounds((x0, y1, -CONFIG["dirt_depth"]), (x1, y0, 0.0))
    street_lo, street_hi = _bounds((x0, sh, 0.0), (L["desert_x0"], -sh, 0.0))
    capsule_lo, capsule_hi = _bounds((L["row_x0"], sh - 16.0, 0.0),
                                     (L["row_x1"], -(sh - 16.0), 0.0))

    lines += [
        "MapData.island = {",
        "\tmin = %s," % island_lo,
        "\tmax = %s," % island_hi,
        "}",
        "",
        "MapData.street = {",
        "\tmin = %s," % street_lo,
        "\tmax = %s," % street_hi,
        "\twidth = %.1f," % (sh * 2.0),
        "}",
        "",
        "MapData.spawnPlaza = {",
        "\tcenter = %s," % _v3((x0 + CONFIG["spawn_len"] / 2.0 + 10.0, 0.0, 0.0)),
        "\tradius = %.1f," % (CONFIG["spawn_len"] / 2.0),
        "}",
        "",
        "MapData.bossAltar = {",
        "\tcenter = %s," % _v3(((L["desert_x0"] + x1 - 12.0) / 2.0, 0.0, 0.0)),
        "\tradius = 40.0,",
        "}",
        "",
        "-- Street band where world capsules may spawn: the running lane, clear of decor.",
        "MapData.capsuleZone = {",
        "\tmin = %s," % capsule_lo,
        "\tmax = %s," % capsule_hi,
        "}",
        "",
        "-- Corridor biomes in walking order from the spawn plaza. `index` grows with",
        "-- distance, so it doubles as a difficulty / reward tier.",
        "MapData.zones = {",
    ]

    for order, (sx0, sx1, biome) in enumerate(biome_segments(L), start=1):
        zone_lo, zone_hi = _bounds((sx0, y1, 0.0), (sx1, y0, 0.0))
        lines.append("\t{")
        lines.append('\t\tid = "%s",' % biome["id"])
        lines.append('\t\tlabel = "%s",' % biome["label"])
        lines.append("\t\tindex = %d," % order)
        lines.append("\t\tbounds = { min = %s, max = %s }," % (zone_lo, zone_hi))
        lines.append("\t},")

    lines += [
        "}",
        "",
        "-- Which biome a world position falls into (ignores height).",
        "function MapData.GetZoneAt(position: Vector3)",
        "\tfor _, zone in ipairs(MapData.zones) do",
        "\t\tif position.X >= zone.bounds.min.X and position.X <= zone.bounds.max.X then",
        "\t\t\treturn zone",
        "\t\tend",
        "\tend",
        "\treturn nil",
        "end",
        "",
        "MapData.plots = {",
    ]

    for anchor in plot_anchors:
        lines.append("\t{")
        lines.append('\t\tid = "%s",' % anchor["id"])
        lines.append('\t\tside = "%s",' % anchor["side"])
        for key in ("center", "entrance", "spawn", "machine",
                    "sellStand", "shopStand", "conveyor", "house"):
            lines.append("\t\t%s = %s," % (key, _v3(anchor[key])))
        lines.append("\t\tpens = {")
        for pen in anchor["pens"]:
            lines.append("\t\t\t%s," % _v3(pen))
        lines.append("\t\t},")
        low, high = _bounds(anchor["bounds"][0], anchor["bounds"][1])
        lines.append("\t\tbounds = { min = %s, max = %s }," % (low, high))
        lines.append("\t},")

    lines += [
        "}",
        "",
        "function MapData.GetPlot(id: string)",
        "\tfor _, plot in ipairs(MapData.plots) do",
        "\t\tif plot.id == id then",
        "\t\t\treturn plot",
        "\t\tend",
        "\tend",
        "\treturn nil",
        "end",
        "",
        "return MapData",
        "",
    ]

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def check_mesh_budget(limit=10000):
    """Roblox refuses a MeshPart above 10k triangles - fail loudly, not at import."""
    worst = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        worst.append((tris, obj.name))
    worst.sort(reverse=True)
    over = [row for row in worst if row[0] > limit]
    total = sum(row[0] for row in worst)
    print("MESH_BUDGET total=%d objects=%d max=%d (%s)"
          % (total, len(worst), worst[0][0], worst[0][1]))
    for tris, name in over:
        print("MESH_OVER_LIMIT %s has %d tris (limit %d) - split it" % (name, tris, limit))
    return not over


# ---------------------------------------------------------------- SCENE


def build_world():
    """Night-blue gradient sky with stars."""
    world = bpy.data.worlds.new("KaijuSky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    add = nt.nodes.new("ShaderNodeAddShader")
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    bg_stars = nt.nodes.new("ShaderNodeBackground")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    star_ramp = nt.nodes.new("ShaderNodeValToRGB")

    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.02, 0.10, 0.52, 1.0)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.01, 0.02, 0.22, 1.0)

    find_socket(noise.inputs, "Scale").default_value = 420.0
    find_socket(noise.inputs, "Detail").default_value = 2.0
    star_ramp.color_ramp.elements[0].position = 0.68
    star_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    star_ramp.color_ramp.elements[1].position = 0.72
    star_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    generated = find_socket(tex.outputs, "Generated")
    nt.links.new(generated, find_socket(sep.inputs, "Vector"))
    nt.links.new(find_socket(sep.outputs, "Z"), find_socket(ramp.inputs, "Fac"))
    nt.links.new(generated, find_socket(noise.inputs, "Vector"))
    nt.links.new(find_socket(noise.outputs, "Fac"), find_socket(star_ramp.inputs, "Fac"))
    nt.links.new(find_socket(ramp.outputs, "Color"), bg_sky.inputs[0])
    nt.links.new(find_socket(star_ramp.outputs, "Color"), bg_stars.inputs[0])
    nt.links.new(bg_sky.outputs[0], add.inputs[0])
    nt.links.new(bg_stars.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    bg_sky.inputs[1].default_value = 1.0
    bg_stars.inputs[1].default_value = 1.0


def build_lights(col, L):
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 4.6
    sun_data.angle = math.radians(12.0)
    sun_data.color = (1.0, 0.97, 0.90)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(42.0), 0.0, math.radians(-125.0))
    sun.location = (0.0, 0.0, 400.0)
    col.objects.link(sun)

    # Two neutral fills so shadows stay readable instead of going navy.
    for name, energy, color, rot in (
        ("Fill_Front", 2.4, (0.85, 0.90, 1.0), (55.0, 0.0, 55.0)),
        ("Fill_Back", 1.5, (1.0, 0.95, 0.85), (68.0, 0.0, 175.0)),
    ):
        data = bpy.data.lights.new(name, type="SUN")
        data.energy = energy
        data.color = color
        obj = bpy.data.objects.new(name, data)
        obj.rotation_euler = tuple(math.radians(a) for a in rot)
        col.objects.link(obj)


def add_camera(name, location, look_at, col, lens=35.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_end = 5000.0
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = location
    col.objects.link(cam)

    target = bpy.data.objects.new(name + "_Target", None)
    target.location = look_at
    col.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return cam


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    if hasattr(scene, "eevee"):
        for attr, value in (("taa_render_samples", 48), ("use_bloom", True),
                            ("use_gtao", True)):
            if hasattr(scene.eevee, attr):
                setattr(scene.eevee, attr, value)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


def render_to(camera, filepath):
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.filepath = filepath
    try:
        bpy.ops.render.render(write_still=True)
        print("RENDER_OK", filepath)
    except Exception as exc:  # noqa: BLE001 - preview only, never fatal
        print("RENDER_FAIL", filepath, exc)


# ---------------------------------------------------------------- MAIN


def main():
    reset_scene()
    random.seed(CONFIG["seed"])
    os.makedirs(OUT_DIR, exist_ok=True)

    pal = build_palette()
    L = layout()

    # Collections mirror the zone table in the map-reference-analysis skill, so
    # the Roblox outliner ends up organised the same way as the spec.
    col_terrain = new_collection("Terrain")
    col_plots = new_collection("Plots")
    col_spawn = new_collection("Spawn")
    col_decor = new_collection("Decor")
    col_rig = new_collection("Rig")

    text_meshes = {
        "zone": text_mesh("ZONE SURE", "Text_ZoneSure", pal["text_decal"], size=8.5),
        "spawn": text_mesh("KAIJU HEIST", "Text_Spawn", pal["glow_gold"], size=18.0),
        "vendre": text_mesh("VENDRE", "Text_Vendre", pal["text_decal"], size=3.1, extrude=0.25),
        "boutique": text_mesh("BOUTIQUE", "Text_Boutique", pal["text_decal"], size=3.1, extrude=0.25),
    }

    build_island(pal, col_terrain, L)
    build_walls(pal, col_terrain, L)

    plot_anchors = []
    for i in range(CONFIG["plots_per_side"]):
        for side in (1, -1):
            _, anchors = build_plot(pal, col_plots, L, i, side, text_meshes)
            plot_anchors.append(anchors)

    build_street(pal, col_decor, L)
    build_spawn(pal, col_spawn, L, text_meshes)
    build_desert(pal, col_decor, L)

    build_world()
    build_lights(col_rig, L)

    mid_x = (L["island_x_min"] + L["island_x_max"]) / 2.0
    cam_aerial = add_camera("Cam_Aerial", (mid_x - 640.0, -880.0, 640.0),
                            (mid_x + 30.0, 0.0, 0.0), col_rig, lens=34.0)
    cam_street = add_camera("Cam_Street", (L["row_x0"] + 40.0, 0.0, 26.0),
                            (L["row_x1"] + 180.0, 0.0, 30.0), col_rig, lens=30.0)
    plot_x = L["plot_centers"][1]
    cam_plot = add_camera("Cam_Plot", (plot_x - 150.0, -60.0, 175.0),
                          (plot_x, CONFIG["street_half"] + 62.0, 6.0), col_rig, lens=40.0)

    setup_render()

    blend_path = os.path.join(OUT_DIR, "kaiju_heist_map.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("SAVED_BLEND", blend_path)

    glb_path = os.path.join(OUT_DIR, "kaiju_heist_map.glb")
    export_glb(glb_path)
    print("SAVED_GLB", glb_path)

    map_data_path = os.path.join(SRC_SHARED_DIR, "MapData.lua")
    write_map_data(map_data_path, L, plot_anchors)
    print("SAVED_MAPDATA", map_data_path)

    check_mesh_budget()

    render_to(cam_aerial, os.path.join(OUT_DIR, "preview_aerial.png"))
    render_to(cam_street, os.path.join(OUT_DIR, "preview_street.png"))
    render_to(cam_plot, os.path.join(OUT_DIR, "preview_plot.png"))


if __name__ == "__main__":
    main()
