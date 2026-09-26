"""
Kaiju Heist - full world generator (Blender 5.x).

    blender -b --python build_map.py
    (or open this file in Blender's Text Editor and press Run Script)

Builds the whole playable world, in walking order:

    Lobby island -> bridge -> Zone Verte -> Zone de Lave -> Zone de Glace
    -> Zone de Pierre -> Zone Desert (boss arena)

with the 8 player bases ("cases", plots N1..N4 / S1..S4) along the central
street, two per zone. Everything is driven by CONFIG / BIOMES / PALETTE below:
change a value, re-run, done. Never hand-edit an output, it is overwritten.

Outputs:
    ../assets/map/kaiju_heist_map.blend + .glb   the whole world
    ../assets/map/sections/<Section>.glb         the same world, one GLB per section
    ../assets/map/preview_*.png                  renders
    ../src/Shared/MapData.lua                    anchors, zones, portals, materials
    ../src/Server/MapColliders.lua               invisible collision volumes

Roblox contract - what src/Server/MapService.lua relies on:
  * one material per object, named "<Name>__<materialKey>" (plus "__c<n>" when
    a part had to be split to stay under the triangle limit). MapService reads
    the key to apply the Roblox colour and material (Neon for anything glowing),
    whatever the 3D importer did with the glTF materials;
  * visual meshes never block players. MapService builds invisible boxes from
    MapColliders.lua instead: the hulls Roblox derives from imported meshes are
    unreliable on big merged meshes, and CollisionFidelity cannot be changed at
    runtime;
  * REF_Origin / REF_AxisX / REF_AxisY markers let MapService put the imported
    model back on the world origin, wherever the importer dropped it.

Units: 1 Blender unit = 1 Roblox stud. Blender is Z-up, Roblox is Y-up:
Blender (x, y, z) -> Roblox (x, z, -y), see to_roblox().

Blender may run in French on the authoring machine: nodes are looked up by
type and sockets by identifier, never by (translated) name.
"""

import bpy
import math
import os
import random
import re

# ---------------------------------------------------------------- CONFIG

CONFIG = {
    "street_half": 36.0,      # half-width of the central street (Y)
    "plot_width": 132.0,      # plot width along the street (X)
    "plot_depth": 122.0,      # plot depth (Y, measured from the street edge)
    "wall_thickness": 16.0,   # walls separating plots
    "wall_height": 40.0,
    "plots_per_side": 4,      # one plot cell per zone, so len(BIOMES) - 1
    "tile": 11.0,             # checker tile size for grounds and walls
    "island_margin_y": 57.0,  # scenery margin beyond the plot rows
    "entry_len": 60.0,        # entrance square between the bridge and the plots
    "desert_len": 215.0,      # desert + boss arena depth (+X end)
    "dirt_depth": 60.0,       # dirt body thickness under the ground
    "taper_depth": 90.0,      # tapered island tip below the dirt
    "lobby_size": 220.0,      # square lobby island
    "lobby_gap": 70.0,        # bridge length between lobby and main island
    "bridge_half": 16.0,
    "barrier_height": 40.0,   # invisible walls around the islands
    "seed": 7,
}

MAX_TRIS_PER_PART = 9500      # Roblox refuses a MeshPart above 10 000 triangles

# Corridor zones, in walking order from the lobby. Zone i (i < plots_per_side)
# covers plot cell i, so it holds 2 bases; the last one is the desert and its
# boss arena. See ZONES.md.
#
# Plot floors deliberately stay grass in every zone: a player must recognise a
# base at a glance, and re-tinting them would make the map unreadable.
BIOMES = [
    {"id": "green", "name": "Verte", "label": "Zone Verte", "sign": "ZONE VERTE",
     "portal": "VERTE", "floor": ("grass_a", "grass_b"), "wall": ("dirt", "dirt_dark"),
     "cap": "grass_a", "rim": "grass_rim", "glow": "glow_green", "ground": "Grass",
     "decor": "green", "street_props": 16, "margin_props": 22},
    {"id": "lava", "name": "Lave", "label": "Zone de Lave", "sign": "ZONE DE LAVE",
     "portal": "LAVE", "floor": ("lava_rock", "lava_rock_dark"),
     "wall": ("volcanic", "volcanic_dark"), "cap": "volcanic_dark", "rim": "lava_glow",
     "glow": "lava_glow", "ground": "Basalt", "decor": "lava",
     "street_props": 20, "margin_props": 26},
    {"id": "ice", "name": "Glace", "label": "Zone de Glace", "sign": "ZONE DE GLACE",
     "portal": "GLACE", "floor": ("ice", "ice_dark"), "wall": ("snow", "ice_dark"),
     "cap": "snow", "rim": "ice_crystal", "glow": "glow_cyan", "ground": "Snow",
     "decor": "ice", "street_props": 24, "margin_props": 30},
    {"id": "stone", "name": "Pierre", "label": "Zone de Pierre", "sign": "ZONE DE PIERRE",
     "portal": "PIERRE", "floor": ("rock_floor", "rock_floor_dark"),
     "wall": ("rock_wall", "stone_dark"), "cap": "rock_floor_dark", "rim": "rock_floor",
     "glow": "cave_crystal", "ground": "Slate", "decor": "stone",
     "street_props": 28, "margin_props": 34},
    {"id": "desert", "name": "Desert", "label": "Zone Desert", "sign": "ZONE DESERT",
     "portal": "BOSS", "floor": ("sand", "sand_dark"), "wall": ("sand_dark", "dirt"),
     "cap": "sand", "rim": "sand", "glow": "glow_gold", "ground": "Sand",
     "decor": "desert", "street_props": 0, "margin_props": 0},
]

# Rarity showcase in the lobby, same order and colours as KaijuDatabase.lua.
RARITIES = [
    ("Common", "rarity_common"),
    ("Rare", "rarity_rare"),
    ("Epic", "rarity_epic"),
    ("Legendary", "rarity_legendary"),
    ("Mythic", "rarity_mythic"),
]

# Reference markers (Blender coordinates), buried in the island's dirt body.
REF_MARKERS = {
    "REF_Origin": (0.0, 0.0, -30.0),
    "REF_AxisX": (200.0, 0.0, -30.0),
    "REF_AxisY": (0.0, 0.0, -10.0),
}
REF_SIZE = 4.0

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(_HERE, "..", "assets", "map"))
SECTIONS_DIR = os.path.join(OUT_DIR, "sections")
SRC_SHARED_DIR = os.path.normpath(os.path.join(_HERE, "..", "src", "Shared"))
SRC_SERVER_DIR = os.path.normpath(os.path.join(_HERE, "..", "src", "Server"))

# ---------------------------------------------------------------- PALETTE


def _mat(r, g, b, emission=0.0, roughness=0.85, metallic=0.0, rbx=None, transparency=0.0):
    """Palette entry. Colours are sRGB design values (what Roblox Color3 shows).

    `rbx` is the Roblox material MapService applies; anything glowing becomes
    Neon, which is how Roblox renders emission.
    """
    return {
        "color": (r, g, b),
        "emission": emission,
        "roughness": roughness,
        "metallic": metallic,
        "rbx": rbx or ("Neon" if emission > 0.0 else "SmoothPlastic"),
        "transparency": transparency,
    }


def _mat255(r, g, b, **kwargs):
    return _mat(r / 255.0, g / 255.0, b / 255.0, **kwargs)


PALETTE = {
    # Plots, street, generic props.
    "grass_a": _mat(0.20, 0.66, 0.11),
    "grass_b": _mat(0.35, 0.85, 0.20),
    "grass_rim": _mat(0.16, 0.95, 0.12),
    "dirt": _mat(0.62, 0.43, 0.25),
    "dirt_dark": _mat(0.50, 0.33, 0.18),
    "sand": _mat(0.90, 0.78, 0.47),
    "sand_dark": _mat(0.80, 0.66, 0.38),
    "stone": _mat(0.48, 0.49, 0.53),
    "stone_dark": _mat(0.33, 0.34, 0.38),
    "wood": _mat(0.42, 0.26, 0.13),
    "wood_light": _mat(0.66, 0.47, 0.26),
    "white": _mat(0.93, 0.93, 0.93),
    "red": _mat(0.84, 0.13, 0.13),
    "yellow": _mat(0.98, 0.79, 0.11),
    "blue": _mat(0.16, 0.44, 0.86),
    "metal_dark": _mat(0.26, 0.28, 0.33, roughness=0.5, metallic=0.5, rbx="Metal"),
    "metal_mid": _mat(0.45, 0.47, 0.52, roughness=0.45, metallic=0.6, rbx="Metal"),
    "glow_green": _mat(0.18, 1.00, 0.30, emission=1.6),
    "glow_cyan": _mat(0.25, 0.85, 1.00, emission=1.5),
    "glow_gold": _mat(1.00, 0.78, 0.18, emission=1.4),
    "glow_violet": _mat(0.65, 0.30, 1.00, emission=1.8),
    "glow_pink": _mat(1.00, 0.36, 0.72, emission=1.6),
    "text_decal": _mat(0.97, 0.97, 1.00, emission=0.9, rbx="SmoothPlastic"),
    "roof": _mat(0.74, 0.35, 0.22),
    "house": _mat(0.82, 0.72, 0.54),
    "leaf": _mat(0.16, 0.52, 0.18),
    "leaf_light": _mat(0.24, 0.66, 0.22),
    "cactus": _mat(0.21, 0.55, 0.26),
    "flower_pink": _mat(0.95, 0.45, 0.65),
    "flower_white": _mat(0.97, 0.95, 0.85),
    "water": _mat(0.20, 0.62, 0.90, roughness=0.15, transparency=0.25),
    # Zone grounds and walls. Hex values come from ZONES.md.
    "lava_rock": _mat(0.24, 0.15, 0.14),
    "lava_rock_dark": _mat(0.16, 0.10, 0.09),
    "lava_glow": _mat(1.00, 0.34, 0.13, emission=2.2),
    "volcanic": _mat(0.20, 0.17, 0.17),
    "volcanic_dark": _mat(0.12, 0.10, 0.10),
    "ice": _mat(0.51, 0.83, 0.98, roughness=0.25),
    "ice_dark": _mat(0.36, 0.66, 0.86, roughness=0.25),
    "snow": _mat(0.89, 0.95, 0.99),
    "ice_crystal": _mat(0.60, 0.92, 1.00, emission=0.8, roughness=0.15),
    "rock_floor": _mat(0.46, 0.46, 0.46),
    "rock_floor_dark": _mat(0.31, 0.31, 0.31),
    "rock_wall": _mat(0.26, 0.26, 0.26),
    "cave_crystal": _mat(0.55, 0.70, 0.95, emission=0.9),
    # Lobby.
    "marble": _mat(0.93, 0.91, 0.87, roughness=0.4, rbx="Marble"),
    "marble_dark": _mat(0.76, 0.74, 0.70, roughness=0.4, rbx="Marble"),
    "gold": _mat(1.00, 0.80, 0.25, roughness=0.3, metallic=0.8, rbx="Metal"),
    "board": _mat(0.13, 0.15, 0.22),
    "rarity_common": _mat255(150, 150, 150, emission=1.0),
    "rarity_rare": _mat255(70, 140, 255, emission=1.2),
    "rarity_epic": _mat255(170, 70, 255, emission=1.3),
    "rarity_legendary": _mat255(255, 170, 30, emission=1.4),
    "rarity_mythic": _mat255(255, 60, 90, emission=1.6),
    # Alignment markers, invisible in game.
    "ref": _mat(1.00, 0.00, 1.00, transparency=1.0),
}

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


def srgb_to_linear_rgb(color):
    """Palette colours are sRGB; Blender base colours are linear."""
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in color)


def make_material(name, color, emission=0.0, roughness=0.85, metallic=0.0):
    """Flat Roblox-style Principled BSDF. `color` is linear. emission > 0 glows."""
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0) and not mat.use_nodes:
        mat.use_nodes = True  # always on (and deprecated) from Blender 5.0

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
    pal = {}
    for key, spec in PALETTE.items():
        mat = make_material(key, srgb_to_linear_rgb(spec["color"]), emission=spec["emission"],
                            roughness=spec["roughness"], metallic=spec["metallic"])
        mat["kh_key"] = key
        pal[key] = mat
    return pal


def material_key(mat):
    """The key an object is named after: palette key, else a sanitised name."""
    key = mat.get("kh_key") if hasattr(mat, "get") else None
    return key or re.sub(r"[^A-Za-z0-9_]", "_", mat.name).lower()


# ---------------------------------------------------------------- MESH BUILDER


class MeshBuilder:
    """Accumulates primitives, then emits Blender meshes.

    Primitives flagged solid=True also record a collision volume, which ends up
    in MapColliders.lua once the builder is registered with a section.
    """

    def __init__(self):
        self.verts = []
        self.faces = []
        self.face_mats = []
        self.mats = []
        self._mat_index = {}
        self.colliders = []

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

    def collider(self, shape, center, size, rot_z=0.0, kind="solid", material=None):
        """Record a collision volume. `size` is (x, y, z) in Blender axes; for a
        cylinder it is (diameter, diameter, height)."""
        self.colliders.append({
            "shape": shape, "center": tuple(center), "size": tuple(size),
            "rot": rot_z, "kind": kind, "material": material,
        })

    # -- primitives ------------------------------------------------

    def box(self, center, size, material, rot_z=0.0, solid=False):
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
        if solid:
            self.collider("box", center, size, rot_z)

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

    def cylinder(self, center, radius, height, material, segments=10, taper=1.0, solid=False):
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
        if solid:
            d = radius * (1.0 + min(taper, 1.0))  # mean diameter for tapered spikes
            self.collider("cylinder", center, (d, d, height))

    def sphere(self, center, radius, material, rings=5, segments=10):
        """Low-poly UV sphere (capsule eggs, ornaments)."""
        cx, cy, cz = center
        pts = [(cx, cy, cz - radius)]
        for i in range(1, rings):
            phi = math.pi * i / rings - math.pi / 2.0
            z = cz + radius * math.sin(phi)
            r = radius * math.cos(phi)
            for j in range(segments):
                a = 2.0 * math.pi * j / segments
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        pts.append((cx, cy, cz + radius))
        top = len(pts) - 1
        faces = []
        for j in range(segments):
            faces.append((0, 1 + (j + 1) % segments, 1 + j))
        for i in range(rings - 2):
            r0 = 1 + i * segments
            r1 = r0 + segments
            for j in range(segments):
                k = (j + 1) % segments
                faces.append((r0 + j, r0 + k, r1 + k, r1 + j))
        last = 1 + (rings - 2) * segments
        for j in range(segments):
            faces.append((last + j, last + (j + 1) % segments, top))
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
        """Vertical checker on a plane facing X (cliff and wall faces)."""
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
        """One multi-material object (kept for build_zones.py and quick tests)."""
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

    def make_meshes(self, name):
        """One mesh per material, split further to stay under MAX_TRIS_PER_PART.

        Returns [(suffix, mesh)], suffix being "<key>" or "<key>__c<n>". One
        material per mesh means one colour per Roblox MeshPart, whatever the
        importer does with multi-material meshes.
        """
        groups = {}
        for face, mi in zip(self.faces, self.face_mats):
            groups.setdefault(mi, []).append(face)
        out = []
        for mi, faces in groups.items():
            mat = self.mats[mi]
            key = material_key(mat)
            chunks, current, tris = [], [], 0
            for face in faces:
                t = len(face) - 2
                if current and tris + t > MAX_TRIS_PER_PART:
                    chunks.append(current)
                    current, tris = [], 0
                current.append(face)
                tris += t
            if current:
                chunks.append(current)
            for ci, chunk in enumerate(chunks):
                remap, verts, new_faces = {}, [], []
                for face in chunk:
                    nf = []
                    for vi in face:
                        if vi not in remap:
                            remap[vi] = len(verts)
                            verts.append(self.verts[vi])
                        nf.append(remap[vi])
                    new_faces.append(tuple(nf))
                suffix = key if len(chunks) == 1 else "%s__c%d" % (key, ci + 1)
                mesh = bpy.data.meshes.new("%s__%s" % (name, suffix))
                mesh.from_pydata(verts, [], new_faces)
                mesh.materials.append(mat)
                mesh.validate(verbose=False)
                mesh.update()
                out.append((suffix, mesh))
        return out

    def build_split(self, name, collection, parent=None):
        """make_meshes() + one object per mesh. Returns the objects."""
        objs = []
        for suffix, mesh in self.make_meshes(name):
            obj = bpy.data.objects.new("%s__%s" % (name, suffix), mesh)
            collection.objects.link(obj)
            if parent is not None:
                obj.parent = parent
            objs.append(obj)
        return objs


# ---------------------------------------------------------------- HELPERS


class Frame:
    """Local placement: origin (x, y) plus a rotation r around Z.

    Convention used by every prop builder: at r = 0 the prop faces -Y. So
    r = pi/2 faces +X, r = pi faces +Y, r = -pi/2 faces -X.
    """

    def __init__(self, x, y, r=0.0):
        self.x, self.y, self.r = x, y, r
        self.c, self.s = math.cos(r), math.sin(r)

    def p(self, lx, ly, z=0.0):
        return (self.x + lx * self.c - ly * self.s, self.y + lx * self.s + ly * self.c, z)

    def front(self):
        """Unit vector the prop faces, in Blender XY."""
        return (self.s, -self.c)


def upright(r):
    """Euler rotation of an upright text mesh facing like a Frame with rotation r."""
    return (math.pi / 2.0, 0.0, r)


def new_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def text_mesh(body, name, material, size=12.0, extrude=0.4):
    """Text -> reusable low-poly mesh: converted once, then instanced."""
    curve = bpy.data.curves.new(name + "_curve", type="FONT")
    curve.body = body
    curve.size = size
    curve.extrude = extrude
    curve.resolution_u = 3
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


def ensure_active_object(candidates=None):
    """The glTF exporter reads bpy.context.active_object, so guarantee one.

    Iterates bpy.data rather than view_layer.objects: right after a rebuild the
    view layer can still hand out stale/None entries. select_set() raises if the
    object is not in the view layer, which doubles as the membership test.
    """
    view_layer = bpy.context.view_layer
    view_layer.update()
    for obj in candidates if candidates is not None else bpy.data.objects:
        if obj is None or obj.type != "MESH":
            continue
        try:
            obj.select_set(True)
        except RuntimeError:
            continue
        view_layer.objects.active = obj
        return


def export_glb(filepath, objects=None):
    """GLB export that works both windowed (UI) and headless (-b).

    With `objects`, only those are exported (selection export); otherwise the
    whole scene is.
    """
    if objects is not None:
        wanted = set(objects)
        for obj in bpy.data.objects:
            try:
                obj.select_set(obj in wanted)
            except RuntimeError:
                pass
        ensure_active_object(objects)
    else:
        ensure_active_object()
    settings = dict(
        filepath=filepath,
        export_format="GLB",
        use_selection=objects is not None,
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


# ---------------------------------------------------------------- WORLD / SECTIONS

COLLIDERS = []   # every collision volume, Blender coordinates, filled by sections
KEEP_OUT = []    # (x0, y0, x1, y1) rectangles scattered decor must avoid


def keep_out(x0, y0, x1, y1):
    KEEP_OUT.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))


def keep_out_around(x, y, r):
    keep_out(x - r, y - r, x + r, y + r)


def is_free(x, y, r=0.0):
    for x0, y0, x1, y1 in KEEP_OUT:
        if x0 - r < x < x1 + r and y0 - r < y < y1 + r:
            return False
    return True


def scatter(rng, count, sample, radius, attempts=8):
    """Up to `count` positions from sample(rng) that avoid KEEP_OUT and each other."""
    spots = []
    for _ in range(count * attempts):
        if len(spots) >= count:
            break
        x, y = sample(rng)
        if is_free(x, y, radius):
            spots.append((x, y))
            keep_out_around(x, y, radius * 0.8)
    return spots


class Section:
    """One collection + one parent empty. Becomes one GLB and one Roblox Model."""

    def __init__(self, world, name):
        self.name = name
        self.collection = new_collection(name, world.collection)
        self.empty = bpy.data.objects.new(name, None)
        self.empty.empty_display_size = 4.0
        self.collection.objects.link(self.empty)
        self.empty.parent = world.empty
        self.objects = []

    def emit(self, mb, name):
        """Build `mb` in world coordinates and register its colliders."""
        objs = mb.build_split(name, self.collection, parent=self.empty)
        self.objects.extend(objs)
        register_colliders(mb, self.name)
        return objs

    def place(self, meshes, name, frame):
        """Instance shared meshes (from make_meshes) at a Frame."""
        for suffix, mesh in meshes:
            obj = bpy.data.objects.new("%s__%s" % (name, suffix), mesh)
            obj.location = (frame.x, frame.y, 0.0)
            obj.rotation_euler = (0.0, 0.0, frame.r)
            self.collection.objects.link(obj)
            obj.parent = self.empty
            self.objects.append(obj)

    def text(self, mesh, name, location, rotation=(0.0, 0.0, 0.0)):
        obj = place_mesh(mesh, "%s__%s" % (name, material_key(mesh.materials[0])),
                         location, self.collection, rotation)
        obj.parent = self.empty
        self.objects.append(obj)
        return obj


class World:
    def __init__(self):
        self.collection = new_collection("KaijuHeistMap")
        self.empty = bpy.data.objects.new("KaijuHeistMap", None)
        self.collection.objects.link(self.empty)
        self.sections = {}

    def section(self, name):
        if name not in self.sections:
            self.sections[name] = Section(self, name)
        return self.sections[name]


def register_colliders(mb, section, frame=None):
    for col in mb.colliders:
        cx, cy, cz = col["center"]
        rot = col["rot"]
        if frame is not None:
            cx, cy, _ = frame.p(cx, cy)
            rot += frame.r
        entry = dict(col)
        entry.update(center=(cx, cy, cz), rot=rot, section=section)
        COLLIDERS.append(entry)


def barrier(section, x0, y0, x1, y1, thickness=2.0):
    """Invisible wall along an axis-aligned segment (colliders only)."""
    h = CONFIG["barrier_height"]
    if abs(x1 - x0) >= abs(y1 - y0):
        size = (abs(x1 - x0), thickness, h)
    else:
        size = (thickness, abs(y1 - y0), h)
    COLLIDERS.append({
        "shape": "box", "center": ((x0 + x1) / 2.0, (y0 + y1) / 2.0, h / 2.0),
        "size": size, "rot": 0.0, "kind": "barrier", "material": None, "section": section,
    })


# ---------------------------------------------------------------- LAYOUT


def layout():
    """Coordinates derived from CONFIG, shared by every builder."""
    c = CONFIG
    cell = c["plot_width"] + c["wall_thickness"]
    n = c["plots_per_side"]
    row_span = cell * n
    row_x0 = -row_span / 2.0
    row_x1 = row_x0 + row_span
    plot_y_far = c["street_half"] + c["plot_depth"]
    island_x_min = row_x0 - c["entry_len"]
    island_x_max = row_x1 + c["desert_len"]
    lobby_x1 = island_x_min - c["lobby_gap"]
    desert_x0 = row_x1 + 12.0
    return {
        "cell": cell,
        "plot_centers": [row_x0 + i * cell + c["wall_thickness"] + c["plot_width"] / 2.0
                         for i in range(n)],
        "wall_centers": [row_x0 + i * cell + c["wall_thickness"] / 2.0 for i in range(n + 1)],
        "row_x0": row_x0,
        "row_x1": row_x1,
        "plot_y_far": plot_y_far,
        "back_wall_y": plot_y_far + 3.0,
        "island_y": plot_y_far + c["island_margin_y"],
        "island_x_min": island_x_min,
        "island_x_max": island_x_max,
        "desert_x0": desert_x0,
        "arena_x": (desert_x0 + island_x_max - 12.0) / 2.0,
        "lobby_x0": lobby_x1 - c["lobby_size"],
        "lobby_x1": lobby_x1,
        "lobby_cx": lobby_x1 - c["lobby_size"] / 2.0,
        "lobby_half": c["lobby_size"] / 2.0,
    }


def biome_segments(L):
    """Corridor split into [x0, x1, biome] bands, covering the whole island.

    The entrance square is folded into the first band and the last cell runs up
    to the desert, so the bands are contiguous: no unpainted strip on the ground
    and no position on the island where GetZoneAt would return nil.
    """
    n = CONFIG["plots_per_side"]
    segments = []
    start = L["island_x_min"]
    for i in range(n):
        end = L["row_x0"] + (i + 1) * L["cell"] if i < n - 1 else L["desert_x0"]
        segments.append((start, end, BIOMES[min(i, len(BIOMES) - 2)]))
        start = end
    segments.append((start, L["island_x_max"], BIOMES[-1]))
    return segments


def section_name(index, biome):
    return "Zone%d_%s" % (index, biome["name"])


def capsule_area(L, index, x0, x1):
    """Rectangle (Blender XY) where world capsules may spawn in a zone: the
    running lane of the street, or the open sand in front of the boss arena."""
    lane = CONFIG["street_half"] - 16.0
    if index == len(BIOMES):
        return (L["desert_x0"] + 12.0, -30.0, L["arena_x"] - 48.0, 30.0)
    return (x0 + 20.0, -lane, x1 - 20.0, lane)


def facing_yaw(dx, dy):
    """Roblox yaw (CFrame.Angles(0, yaw, 0)) whose LookVector points along the
    Blender direction (dx, dy)."""
    return math.atan2(-dx, dy)


# ---------------------------------------------------------------- PROPS


def add_floating_body(mb, pal, x0, y0, x1, y1, depth, taper, rng, rocks):
    """Dirt body under a floating island: checker cliffs, tapered tip, rocks."""
    top = -0.8   # rim boxes cover 0 .. -0.8; staying below the ground avoids z-fighting
    bottom = -depth
    mb.box(((x0 + x1) / 2.0, (y0 + y1) / 2.0, (top + bottom) / 2.0),
           (x1 - x0, y1 - y0, top - bottom), pal["dirt"])
    mb.frustum(((x0 + x1) / 2.0, (y0 + y1) / 2.0), bottom, bottom - taper,
               (x1 - x0, y1 - y0), ((x1 - x0) * 0.22, (y1 - y0) * 0.14), pal["dirt_dark"])
    t = CONFIG["tile"] * 1.4
    mb.checker_yz(x0 - 0.2, y0, bottom, y1, top, t, pal["dirt"], pal["dirt_dark"], facing=-1)
    mb.checker_yz(x1 + 0.2, y0, bottom, y1, top, t, pal["dirt"], pal["dirt_dark"], facing=1)
    mb.checker_xz(y0 - 0.2, x0, bottom, x1, top, t, pal["dirt"], pal["dirt_dark"], facing=-1)
    mb.checker_xz(y1 + 0.2, x0, bottom, x1, top, t, pal["dirt"], pal["dirt_dark"], facing=1)
    for _ in range(rocks):
        rx = rng.uniform(x0 + (x1 - x0) * 0.1, x1 - (x1 - x0) * 0.1)
        ry = rng.uniform(y0 + (y1 - y0) * 0.1, y1 - (y1 - y0) * 0.1)
        rz = rng.uniform(bottom - taper * 0.75, bottom - 6.0)
        s = rng.uniform(6.0, 20.0)
        mb.box((rx, ry, rz), (s, s * rng.uniform(0.6, 1.3), s * rng.uniform(0.5, 1.1)),
               pal["dirt_dark"], rot_z=rng.uniform(0, math.pi))


def add_rims(mb, mat, x0, y0, x1, y1, rim, west=True, east=True, north=True, south=True):
    """Bright border strips flush with the ground (top at z = 0), never overlapping."""
    if north:
        mb.box(((x0 + x1) / 2.0, y1 - rim / 2.0, -0.4), (x1 - x0, rim, 0.8), mat)
    if south:
        mb.box(((x0 + x1) / 2.0, y0 + rim / 2.0, -0.4), (x1 - x0, rim, 0.8), mat)
    inner = (y1 - rim) - (y0 + rim)
    if west:
        mb.box((x0 + rim / 2.0, (y0 + y1) / 2.0, -0.4), (rim, inner, 0.8), mat)
    if east:
        mb.box((x1 - rim / 2.0, (y0 + y1) / 2.0, -0.4), (rim, inner, 0.8), mat)


def add_lamp(mb, pal, x, y, glow=None, solid=True):
    mb.cylinder((x, y, 0.8), 2.4, 1.6, pal["stone_dark"], segments=8)
    mb.cylinder((x, y, 11.0), 0.9, 21.0, pal["metal_dark"], segments=8)
    mb.box((x, y, 22.4), (3.4, 3.4, 2.2), pal["metal_dark"])
    mb.box((x, y, 21.0), (2.6, 2.6, 1.6), glow or pal["glow_gold"])
    if solid:
        mb.collider("box", (x, y, 11.0), (1.8, 1.8, 22.0))


def add_bush(mb, pal, x, y, rng, solid=False):
    s = rng.uniform(3.4, 6.2)
    mb.box((x, y, s * 0.45), (s, s * rng.uniform(0.8, 1.2), s * 0.9),
           pal["leaf"], rot_z=rng.uniform(0, math.pi))
    mb.box((x + rng.uniform(-1.6, 1.6), y + rng.uniform(-1.6, 1.6), s * 0.95),
           (s * 0.6, s * 0.6, s * 0.5), pal["leaf_light"], rot_z=rng.uniform(0, math.pi))


def add_rock(mb, pal, x, y, rng, solid=False):
    s = rng.uniform(2.6, 6.0)
    mb.box((x, y, s * 0.35), (s, s * rng.uniform(0.7, 1.3), s * 0.7),
           pal["stone"], rot_z=rng.uniform(0, math.pi), solid=solid)
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


def add_tree(mb, pal, x, y, rng, solid=False):
    h = rng.uniform(14.0, 22.0)
    mb.cylinder((x, y, h / 2.0), 1.9, h, pal["wood"], segments=8, solid=solid)
    for i in range(3):
        s = (3 - i) * 5.0 + 6.0
        mb.box((x, y, h + 3.0 + i * 4.2), (s, s, 5.0),
               pal["leaf"] if i % 2 == 0 else pal["leaf_light"],
               rot_z=rng.uniform(0, math.pi / 2))


def add_cactus(mb, pal, x, y, rng, solid=False):
    h = rng.uniform(10.0, 18.0)
    mb.box((x, y, h / 2.0), (3.4, 3.4, h), pal["cactus"], solid=solid)
    if rng.random() < 0.7:
        side = rng.choice((-1, 1))
        mb.box((x + side * 3.4, y, h * 0.58), (4.0, 2.6, 2.6), pal["cactus"])
        mb.box((x + side * 5.2, y, h * 0.74), (2.6, 2.6, 7.0), pal["cactus"])


def add_crate(mb, pal, x, y, rng, solid=False):
    s = rng.uniform(4.0, 6.0)
    r = rng.uniform(0, math.pi)
    mb.box((x, y, s / 2.0), (s, s, s), pal["wood_light"], rot_z=r, solid=solid)
    mb.box((x, y, s / 2.0), (s + 0.3, s * 0.2, s * 0.2), pal["wood"], rot_z=r)
    if rng.random() < 0.4:
        mb.box((x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), s + s * 0.35),
               (s * 0.7, s * 0.7, s * 0.7), pal["wood"], rot_z=rng.uniform(0, math.pi))


def add_obsidian(mb, pal, x, y, rng, solid=False):
    """Lava zone: sharp black rock, sometimes with a glowing seam."""
    h = rng.uniform(5.0, 11.0)
    rot = rng.uniform(0, math.pi)
    size = (rng.uniform(4, 7), rng.uniform(4, 7), h)
    mb.box((x, y, h / 2.0), size, pal["volcanic_dark"], rot_z=rot, solid=solid)
    if rng.random() < 0.45:
        mb.box((x, y, h * 0.55), (size[0] + 0.4, 1.2, 1.2), pal["lava_glow"], rot_z=rot)


def add_lava_crack(mb, pal, x, y, rng, solid=False):
    """Glowing fissure lying flush with the ground (walkable, never solid)."""
    length = rng.uniform(10.0, 22.0)
    rot = rng.uniform(0, math.pi)
    mb.box((x, y, 0.12), (length, rng.uniform(2.0, 3.5), 0.24), pal["lava_glow"], rot_z=rot)
    mb.box((x, y, 0.06), (length + 3.0, rng.uniform(5.0, 7.0), 0.12),
           pal["lava_rock_dark"], rot_z=rot)


def add_ice_spike(mb, pal, x, y, rng, solid=False):
    h = rng.uniform(8.0, 18.0)
    mb.cylinder((x, y, h / 2.0), rng.uniform(2.0, 3.4), h, pal["ice"],
                segments=6, taper=0.12, solid=solid)
    if rng.random() < 0.4:
        mb.cylinder((x + rng.uniform(-2.5, 2.5), y + rng.uniform(-2.5, 2.5), h * 0.3),
                    1.4, h * 0.6, pal["ice_crystal"], segments=5, taper=0.2)


def add_snow_mound(mb, pal, x, y, rng, solid=False):
    s = rng.uniform(5.0, 9.0)
    mb.box((x, y, 0.6), (s, s * rng.uniform(0.7, 1.2), 1.2), pal["snow"],
           rot_z=rng.uniform(0, math.pi))


def add_stalagmite(mb, pal, x, y, rng, solid=False):
    h = rng.uniform(7.0, 16.0)
    mb.cylinder((x, y, h / 2.0), rng.uniform(2.4, 3.6), h, pal["rock_wall"],
                segments=6, taper=0.18, solid=solid)
    if rng.random() < 0.35:
        mb.box((x, y, h + 1.0), (2.0, 2.0, 2.0), pal["cave_crystal"],
               rot_z=rng.uniform(0, math.pi))


def add_biome_decor(mb, pal, biome, x, y, rng, solid=False):
    """Dispatch one scattered prop appropriate to the zone."""
    kind = biome["decor"]
    roll = rng.random()
    if kind == "green":
        fn = add_bush if roll < 0.45 else add_rock if roll < 0.75 else add_tree
    elif kind == "lava":
        fn = add_obsidian if roll < 0.6 else add_lava_crack
    elif kind == "ice":
        fn = add_ice_spike if roll < 0.55 else add_snow_mound
    elif kind == "stone":
        fn = add_stalagmite if roll < 0.6 else add_rock
    else:
        fn = add_cactus if roll < 0.5 else add_rock
    fn(mb, pal, x, y, rng, solid=solid)


def fence_run(mb, pal, a, b, height=7.0, step=9.0):
    """Straight axis-aligned fence from a to b: inner posts, two rails, one
    collider. Corner and gate posts are placed by the caller, so no two posts
    ever overlap (identical boxes would z-fight)."""
    (ax, ay), (bx, by) = a, b
    length = math.hypot(bx - ax, by - ay)
    n = max(1, int(round(length / step)))
    for i in range(1, n):
        t = i / n
        mb.box((ax + (bx - ax) * t, ay + (by - ay) * t, height / 2.0),
               (1.5, 1.5, height), pal["wood_light"])
    along_x = abs(bx - ax) >= abs(by - ay)
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    for z in (height * 0.38, height * 0.78):
        size = (length, 0.8, 1.1) if along_x else (0.8, length, 1.1)
        mb.box((mx, my, z), size, pal["wood"])
    mb.collider("box", (mx, my, height / 2.0),
                (length, 1.0, height) if along_x else (1.0, length, height))


def add_pen(mb, pal, cx, cy, sx, sy, gap=8.0, height=7.0):
    """Kaiju pen (axis-aligned, plot-local) with a gate on its street side (-Y)."""
    hx, hy = sx / 2.0, sy / 2.0
    x0, x1, y0, y1 = cx - hx, cx + hx, cy - hy, cy + hy
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1),
                   (cx - gap / 2.0, y0), (cx + gap / 2.0, y0)):
        mb.box((px, py, height / 2.0), (1.5, 1.5, height), pal["wood_light"])
    fence_run(mb, pal, (x0, y1), (x1, y1), height)
    fence_run(mb, pal, (x0, y0), (x0, y1), height)
    fence_run(mb, pal, (x1, y0), (x1, y1), height)
    fence_run(mb, pal, (x0, y0), (cx - gap / 2.0, y0), height)
    fence_run(mb, pal, (cx + gap / 2.0, y0), (x1, y0), height)
    # Display podium the kaiju stands on.
    mb.cylinder((cx, cy, 0.45), 7.2, 0.9, pal["stone_dark"], segments=12)
    mb.cylinder((cx, cy, 1.05), 6.2, 0.8, pal["stone"], segments=12)
    mb.cylinder((cx, cy, 1.55), 2.1, 0.5, pal["glow_cyan"], segments=10)
    mb.collider("cylinder", (cx, cy, 0.725), (14.4, 14.4, 1.45))


def add_stall(mb, pal, f, stripe):
    """Merchant stall: counter, striped awning, sign board. Returns where the
    sign text goes."""
    w, d = 18.0, 9.0
    mb.box(f.p(0, 0, 4.0), (w, d, 8.0), pal["wood"], rot_z=f.r, solid=True)
    mb.box(f.p(0, 0, 8.4), (w + 1.5, d + 1.5, 1.0), pal["wood_light"], rot_z=f.r)
    for lx in (-w / 2 + 1.2, w / 2 - 1.2):
        for ly in (-d / 2 + 1.2, d / 2 - 1.2):
            mb.box(f.p(lx, ly, 7.6), (1.2, 1.2, 15.2), pal["wood_light"], rot_z=f.r)
    n = 7
    bw = (w + 4.0) / n
    for i in range(n):
        lx = -(w + 4.0) / 2 + bw * (i + 0.5)
        mb.box(f.p(lx, 0, 15.8), (bw, d + 5.0, 1.6),
               stripe if i % 2 == 0 else pal["white"], rot_z=f.r)
    mb.box(f.p(0, -(d + 5.0) / 2, 14.6), (w + 4.6, 1.4, 2.6), pal["wood"], rot_z=f.r)
    mb.box(f.p(0, -(d / 2 + 0.9), 11.2), (w * 0.78, 0.7, 4.6), stripe, rot_z=f.r)
    return f.p(0, -(d / 2 + 0.9) - 0.6, 11.2)


def add_house(mb, pal, f):
    mb.box(f.p(0, 0, 8.0), (18.0, 16.0, 16.0), pal["house"], rot_z=f.r, solid=True)
    mb.roof(f.p(0, 0, 19.5), (19.5, 18.0, 7.0), pal["roof"], rot_z=f.r)
    mb.box(f.p(0, -8.2, 5.0), (5.0, 1.0, 10.0), pal["wood"], rot_z=f.r)
    for lx in (-6.0, 6.0):
        mb.box(f.p(lx, -8.2, 11.0), (4.0, 1.0, 4.0), pal["glow_gold"], rot_z=f.r)
    mb.box(f.p(6.0, 5.0, 24.0), (3.0, 3.0, 9.0), pal["stone"], rot_z=f.r)


def add_machine(mb, pal, f):
    """Hatching machine: metal block, green panels, capsule dome, front steps."""
    mb.box(f.p(0, 0, 8.0), (16.0, 13.0, 16.0), pal["metal_dark"], rot_z=f.r, solid=True)
    mb.box(f.p(0, 0, 16.8), (17.5, 14.5, 2.0), pal["metal_mid"], rot_z=f.r)
    for lx in (-5.6, 5.6):
        mb.box(f.p(lx, 0, 9.5), (3.6, 13.6, 9.0), pal["glow_green"], rot_z=f.r)
    mb.box(f.p(0, -7.1, 9.0), (7.0, 0.8, 8.0), pal["glow_cyan"], rot_z=f.r)
    mb.cylinder(f.p(0, 0, 21.5), 3.4, 6.0, pal["glow_green"], segments=12)
    for lx in (-8.6, 8.6):
        mb.box(f.p(lx, 0, 5.0), (2.4, 2.4, 10.0), pal["metal_mid"], rot_z=f.r)
        mb.box(f.p(lx, 0, 11.0), (3.4, 3.4, 2.0), pal["glow_green"], rot_z=f.r)
    for i in range(3):
        mb.box(f.p(0, -(7.0 + i * 2.6), (3 - i) * 1.1 - 0.5), (11.0, 2.6, 2.2),
               pal["metal_mid"], rot_z=f.r)


def add_conveyor(mb, pal, f):
    """Conveyor ramp feeding a raised platform (tall end towards local +X)."""
    length, width = 26.0, 10.0
    mb.wedge(f.p(0, 0, 3.0), (length, width, 6.0), pal["metal_dark"], rot_z=f.r)
    for i in range(7):
        lx = -length / 2 + 2.0 + i * (length - 4.0) / 6.0
        h = 6.0 * (i + 1) / 7.0
        mb.box(f.p(lx, 0, h - 0.2), (1.6, width - 1.4, 0.8), pal["metal_mid"], rot_z=f.r)
    ex = length / 2 + 4.0
    mb.box(f.p(ex, 0, 3.0), (9.0, width + 2.0, 6.0), pal["metal_mid"], rot_z=f.r, solid=True)
    mb.box(f.p(ex, 0, 6.4), (9.6, width + 2.6, 0.9), pal["glow_cyan"], rot_z=f.r)


def add_portal(mb, pal, f, glow):
    """Teleport gate facing the frame's front. Returns (trigger, label position)."""
    mb.box(f.p(0, 0, 0.25), (18.0, 7.0, 0.5), pal["marble_dark"], rot_z=f.r)
    for lx in (-7.4, 7.4):
        mb.box(f.p(lx, 0, 9.0), (2.6, 2.6, 18.0), pal["stone"], rot_z=f.r, solid=True)
    mb.box(f.p(0, 0, 19.6), (18.4, 3.2, 2.6), pal["stone_dark"], rot_z=f.r)
    mb.box(f.p(0, 0, 9.0), (12.2, 0.5, 17.0), pal[glow], rot_z=f.r)
    mb.box(f.p(0, -1.0, 23.1), (15.0, 0.8, 4.2), pal["board"], rot_z=f.r)
    for lx in (-7.4, 7.4):
        mb.sphere(f.p(lx, 0, 22.2), 1.2, pal[glow], rings=4, segments=8)
    trigger = {"center": f.p(0, 0, 9.0), "size": (12.0, 4.0, 17.0), "rot": f.r}
    return trigger, f.p(0, -1.75, 23.1)


def add_zone_gate(mb, pal, biome, gx):
    """Lintel across the street between two plot walls, plus a glowing border."""
    sh = CONFIG["street_half"]
    mb.box((gx, 0.0, 33.0), (12.0, 2 * sh + 16.0, 6.0), pal[biome["wall"][1]])
    mb.box((gx, 0.0, 36.4), (12.6, 2 * sh + 17.0, 0.8), pal[biome["cap"]])
    mb.box((gx, 0.0, 29.6), (4.0, 2 * sh, 0.8), pal[biome["glow"]])
    mb.box((gx, 0.0, 0.08), (1.6, 2 * sh, 0.16), pal[biome["glow"]])


def add_step_pyramid(mb, pal, x, y, base, tiers, tier_h, solid):
    s = base
    for i in range(tiers):
        s = base * (1.0 - i / float(tiers))
        mat = pal["sand"] if i % 2 == 0 else pal["sand_dark"]
        mb.box((x, y, tier_h * (i + 0.5)), (s, s, tier_h), mat, solid=solid)
    mb.box((x, y, tier_h * tiers + 1.2), (s * 0.35, s * 0.35, 2.4), pal["glow_gold"])


def add_volcano(mb, pal, x, y, base, height, rng):
    mb.frustum((x, y), height, 0.0, (base * 0.3, base * 0.3), (base, base), pal["volcanic_dark"])
    mb.frustum((x, y), height * 0.7, 0.0, (base * 0.36, base * 0.36), (base * 0.8, base * 0.8),
               pal["volcanic"])
    mb.box((x, y, height + 0.3), (base * 0.26, base * 0.26, 1.0), pal["lava_glow"])
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        r = base * 0.62
        mb.box((x + math.cos(a) * r, y + math.sin(a) * r, 1.2), (3.0, 3.0, 2.4),
               pal["lava_glow"], rot_z=a)


def add_landmark(mb, pal, biome, x, y, rng):
    """One big silhouette per zone, in the scenery margins behind the plots."""
    kind = biome["decor"]
    north = y > 0
    if kind == "green":
        if north:   # giant tree
            mb.cylinder((x, y, 14.0), 3.6, 28.0, pal["wood"], segments=8)
            for i, s in enumerate((26.0, 20.0, 13.0)):
                mb.box((x, y, 30.0 + i * 6.5), (s, s, 7.0),
                       pal["leaf"] if i % 2 == 0 else pal["leaf_light"], rot_z=i * 0.5)
        else:       # pond with stones
            mb.cylinder((x, y, 0.15), 14.0, 0.3, pal["water"], segments=16)
            for i in range(10):
                a = 2 * math.pi * i / 10
                mb.box((x + math.cos(a) * 15.5, y + math.sin(a) * 15.5, 0.9),
                       (3.2, 2.6, 1.8), pal["stone"], rot_z=a)
    elif kind == "lava":
        add_volcano(mb, pal, x, y, 44.0 if north else 30.0, 46.0 if north else 30.0, rng)
    elif kind == "ice":
        if north:   # ice castle
            s = 12.0
            for dx in (-s, s):
                for dy in (-s, s):
                    mb.cylinder((x + dx, y + dy, 13.0), 4.5, 26.0, pal["ice"], segments=8)
                    mb.cylinder((x + dx, y + dy, 30.5), 5.5, 9.0, pal["snow"], segments=8,
                                taper=0.06)
            for dy in (-s, s):
                mb.box((x, y + dy, 8.0), (2 * s, 3.0, 16.0), pal["ice_dark"])
            for dx in (-s, s):
                mb.box((x + dx, y, 8.0), (3.0, 2 * s, 16.0), pal["ice_dark"])
            mb.box((x, y, 15.0), (11.0, 11.0, 30.0), pal["ice"])
            mb.cylinder((x, y, 34.5), 8.0, 9.0, pal["snow"], segments=4, taper=0.06)
            mb.box((x, y - 5.6, 22.0), (3.0, 0.6, 5.0), pal["ice_crystal"])
        else:       # crystal cluster
            for _ in range(7):
                h = rng.uniform(10.0, 26.0)
                mb.cylinder((x + rng.uniform(-9, 9), y + rng.uniform(-9, 9), h / 2.0),
                            rng.uniform(2.0, 3.8), h, pal["ice_crystal"], segments=5, taper=0.1)
    elif kind == "stone":
        if north:   # rock arch
            for dx in (-12.0, 12.0):
                mb.box((x + dx, y, 14.0), (7.0, 7.0, 28.0), pal["rock_wall"])
            mb.box((x, y, 31.0), (33.0, 9.0, 7.0), pal["stone_dark"])
            mb.box((x, y, 27.0), (5.0, 1.0, 2.0), pal["cave_crystal"])
        else:       # boulder pile with crystals
            for _ in range(8):
                s = rng.uniform(6.0, 13.0)
                mb.box((x + rng.uniform(-10, 10), y + rng.uniform(-8, 8), s * 0.45),
                       (s, s * 0.9, s * 0.9), pal["rock_wall"], rot_z=rng.uniform(0, math.pi))
            for _ in range(4):
                mb.cylinder((x + rng.uniform(-8, 8), y + rng.uniform(-8, 8), 3.0), 1.4, 6.0,
                            pal["cave_crystal"], segments=5, taper=0.2)


# ---------------------------------------------------------------- SECTIONS


def build_texts(pal):
    t = {}

    def add(key, body, mat, size, extrude=0.3):
        # The mesh name carries the material key too, in case the importer names
        # MeshParts after meshes rather than objects.
        t[key] = text_mesh(body, "Text_%s__%s" % (key, mat), pal[mat], size=size, extrude=extrude)

    add("zone_sure", "ZONE SURE", "text_decal", 8.5, 0.4)
    add("vendre", "VENDRE", "text_decal", 3.1, 0.25)
    add("boutique", "BOUTIQUE", "text_decal", 3.1, 0.25)
    add("title", "KAIJU HEIST", "glow_gold", 6.0, 0.6)
    add("classement", "CLASSEMENT", "glow_gold", 3.4, 0.3)
    add("rarities", "RARETES", "text_decal", 2.2, 0.2)
    add("cadeau", "CADEAU", "glow_gold", 2.6, 0.3)
    add("tuto_title", "COMMENT JOUER", "glow_gold", 2.4, 0.2)
    for i, line in enumerate(("1  RAMASSE DES CAPSULES", "2  FAIS-LES ECLORE",
                              "3  GAGNE DE L'ICHOR", "4  VOLE LES AUTRES"), start=1):
        add("tuto_%d" % i, line, "text_decal", 1.7, 0.15)
    add("portal_base", "MA BASE", "text_decal", 2.4, 0.2)
    add("portal_lobby", "LOBBY", "text_decal", 2.4, 0.2)
    for b in BIOMES:
        add("portal_" + b["id"], b["portal"], "text_decal", 2.4, 0.2)
        add("gate_" + b["id"], b["sign"], "text_decal", 6.0 if b is BIOMES[0] else 4.2, 0.4)
    return t


def build_lobby(world, pal, L, texts):
    """Spawn island: fountain + spawn ring, portals, leaderboard, rarity
    showcase, shop, daily reward, tutorial, and the bridge to the main island."""
    sec = world.section("Lobby")
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 300)
    cx, half = L["lobby_cx"], L["lobby_half"]
    x0, x1, y0, y1 = cx - half, cx + half, -half, half
    rim = 8.0
    bh = CONFIG["bridge_half"]
    plaza = half - 35.0   # marble plaza half-size; grows with lobby_size

    add_floating_body(mb, pal, x0, y0, x1, y1, 40.0, 60.0, rng, rocks=10)
    mb.checker(x0 + rim, y0 + rim, x1 - rim, y1 - rim, 0.0, CONFIG["tile"],
               pal["grass_a"], pal["grass_b"])
    add_rims(mb, pal["grass_rim"], x0, y0, x1, y1, rim)
    mb.collider("box", (cx, 0.0, -2.0), (x1 - x0, y1 - y0, 4.0), kind="ground", material="Grass")

    # Marble plaza with a gold trim, and the path to the bridge gate.
    mb.checker(cx - plaza, -plaza, cx + plaza, plaza, 0.05, 10.0, pal["marble"], pal["marble_dark"])
    mb.collider("box", (cx, 0.0, -0.45), (2 * plaza, 2 * plaza, 1.0), kind="ground",
                material="Marble")
    for sy in (-1, 1):
        mb.box((cx, sy * (plaza + 0.8), 0.2), (2 * plaza + 3.2, 1.6, 0.4), pal["gold"])
        # The east trim leaves a gap where the path heads for the bridge.
        mb.box((cx + plaza + 0.8, sy * (plaza + bh) / 2.0, 0.2), (1.6, plaza - bh, 0.4), pal["gold"])
    mb.box((cx - plaza - 0.8, 0.0, 0.2), (1.6, 2 * plaza, 0.4), pal["gold"])
    mb.checker(cx + plaza, -bh, x1, bh, 0.05, 8.0, pal["stone"], pal["stone_dark"])
    mb.collider("box", ((cx + plaza + x1) / 2.0, 0.0, -0.45), (x1 - cx - plaza, 2 * bh, 1.0),
                kind="ground", material="Slate")
    keep_out(cx - plaza - 4, -plaza - 4, cx + plaza + 4, plaza + 4)
    keep_out(cx + plaza, -bh - 6, x1, bh + 6)

    # Fountain and the ring of spawn pads around it.
    mb.cylinder((cx, 0.0, 1.6), 17.0, 3.2, pal["stone"], segments=14, solid=True)
    mb.cylinder((cx, 0.0, 3.3), 15.0, 0.8, pal["water"], segments=14)
    mb.cylinder((cx, 0.0, 6.0), 4.0, 9.0, pal["stone_dark"], segments=10, solid=True)
    mb.cylinder((cx, 0.0, 11.5), 6.5, 2.0, pal["stone"], segments=12, taper=0.5)
    mb.cylinder((cx, 0.0, 15.0), 2.2, 6.0, pal["glow_cyan"], segments=8)
    spawns = []
    for k in range(8):
        a = math.radians(22.5 + 45.0 * k)
        px, py = cx + math.cos(a) * 32.0, math.sin(a) * 32.0
        mb.cylinder((px, py, 0.25), 4.5, 0.4, pal["marble_dark"], segments=10)
        mb.cylinder((px, py, 0.3), 3.2, 0.42, pal["glow_cyan"], segments=10)
        spawns.append((px, py, 0.05))

    # Portal row on the north side, facing the fountain.
    portals = []
    targets = [("base", "portal_base", "base", "glow_pink", "MA BASE")]
    targets += [(b["id"], "portal_" + b["id"], "zone:" + b["id"], b["glow"], b["portal"])
                for b in BIOMES]
    for k, (pid, text_key, target, glow, label) in enumerate(targets):
        # One portal per zone, centred; 26 studs apart, so 6 fit a 150-stud plaza.
        f = Frame(cx + 26.0 * (k - (len(targets) - 1) / 2.0), plaza - 9.0, 0.0)
        trigger, label_pos = add_portal(mb, pal, f, glow)
        sec.text(texts[text_key], "Lobby_PortalText_" + pid, label_pos, upright(f.r))
        portals.append(dict(trigger, id="lobby_" + pid, label=label, target=target))

    # Leaderboard, south side, facing the fountain.
    f = Frame(cx, -70.0, math.pi)
    for lx in (-19.0, 19.0):
        mb.box(f.p(lx, 0.6, 14.0), (2.4, 2.4, 28.0), pal["wood"], rot_z=f.r, solid=True)
    mb.box(f.p(0, 0, 16.0), (44.0, 1.6, 24.0), pal["wood_light"], rot_z=f.r, solid=True)
    mb.box(f.p(0, -0.6, 16.0), (41.0, 0.8, 21.0), pal["board"], rot_z=f.r)
    mb.box(f.p(0, 0, 30.5), (30.0, 1.2, 5.0), pal["board"], rot_z=f.r)
    sec.text(texts["classement"], "Lobby_Text_Classement", f.p(0, -0.9, 30.5), upright(f.r))
    board_face = f.p(0, -1.0, 16.0)
    for lx, h in ((-12.0, 5.0), (0.0, 7.5), (12.0, 3.5)):   # 2nd, 1st, 3rd seen from the plaza
        mb.box(f.p(lx, -14.0, h / 2.0), (10.0, 10.0, h), pal["marble"], rot_z=f.r, solid=True)
        mb.box(f.p(lx, -14.0, h + 0.2), (4.0, 4.0, 0.4), pal["glow_gold"], rot_z=f.r)
    leaderboard = {"position": board_face, "width": 41.0, "height": 21.0,
                   "yaw": facing_yaw(*f.front())}

    # Rarity showcase: one glowing capsule per rarity.
    showcase = []
    for k, (rarity, key) in enumerate(RARITIES):
        px, py = cx + 30.0 + 10.0 * k, -50.0
        mb.cylinder((px, py, 1.5), 3.0, 3.0, pal["marble"], segments=10, solid=True)
        mb.cylinder((px, py, 3.2), 3.4, 0.4, pal["gold"], segments=10)
        mb.cylinder((px, py, 4.0), 1.4, 1.2, pal["metal_mid"], segments=8)
        mb.sphere((px, py, 5.9), 1.8, pal[key])
        showcase.append({"rarity": rarity, "position": (px, py, 5.9)})
    fb = Frame(cx + 50.0, -57.0, math.pi)
    for lx in (-21.0, 21.0):
        mb.box(fb.p(lx, 0, 5.0), (1.2, 1.2, 10.0), pal["wood"], rot_z=fb.r, solid=True)
    mb.box(fb.p(0, 0, 9.2), (44.0, 0.8, 3.2), pal["board"], rot_z=fb.r)
    sec.text(texts["rarities"], "Lobby_Text_Raretes", fb.p(0, -0.6, 9.2), upright(fb.r))

    # West side: shop, daily reward chest, how-to-play board, all facing +X.
    shop = Frame(cx - 64.0, -34.0, math.pi / 2.0)
    sign = add_stall(mb, pal, shop, pal["yellow"])
    sec.text(texts["boutique"], "Lobby_Text_Boutique", sign, upright(shop.r))
    chest = Frame(cx - 64.0, 34.0, math.pi / 2.0)
    mb.cylinder(chest.p(0, 0, 0.12), 7.0, 0.24, pal["glow_gold"], segments=12)
    mb.box(chest.p(0, 0, 2.6), (9.0, 6.0, 5.0), pal["wood"], rot_z=chest.r, solid=True)
    mb.box(chest.p(0, 0, 5.9), (9.4, 6.4, 1.6), pal["wood_light"], rot_z=chest.r)
    for lx in (-3.0, 3.0):
        mb.box(chest.p(lx, 0, 3.4), (1.0, 6.3, 6.8), pal["gold"], rot_z=chest.r)
    mb.box(chest.p(0, -3.3, 4.2), (1.6, 0.6, 2.0), pal["gold"], rot_z=chest.r)
    sec.text(texts["cadeau"], "Lobby_Text_Cadeau", chest.p(0, 0, 10.5), upright(chest.r))
    tuto = Frame(cx - 70.0, 0.0, math.pi / 2.0)
    for lx in (-14.0, 14.0):
        mb.box(tuto.p(lx, 0.8, 11.0), (1.6, 1.6, 22.0), pal["wood"], rot_z=tuto.r, solid=True)
    mb.box(tuto.p(0, 0, 13.0), (30.0, 1.2, 18.0), pal["board"], rot_z=tuto.r, solid=True)
    mb.box(tuto.p(0, 0.2, 13.0), (31.6, 1.0, 19.6), pal["wood_light"], rot_z=tuto.r)
    sec.text(texts["tuto_title"], "Lobby_Text_Tuto", tuto.p(0, -0.8, 19.5), upright(tuto.r))
    for i in range(1, 5):
        sec.text(texts["tuto_%d" % i], "Lobby_Text_Tuto%d" % i,
                 tuto.p(0, -0.8, 19.5 - 3.4 * i), upright(tuto.r))

    # Bridge gate with the game title, facing the plaza.
    gx = x1 - 6.0
    for sy in (-1, 1):
        mb.box((gx, sy * 24.0, 17.0), (8.0, 8.0, 34.0), pal["marble"], solid=True)
        mb.box((gx, sy * 24.0, 35.0), (9.5, 9.5, 2.0), pal["gold"])
    mb.box((gx, 0.0, 36.0), (8.0, 60.0, 8.0), pal["marble"])
    mb.box((gx, 0.0, 40.6), (9.0, 62.0, 1.2), pal["gold"])
    mb.box((gx, 0.0, 31.6), (3.0, 40.0, 0.8), pal["glow_violet"])
    sec.text(texts["title"], "Lobby_Text_Title", (gx - 4.4, 0.0, 36.0), upright(-math.pi / 2.0))
    keep_out(gx - 8, -32, x1, 32)

    # Lamps and greenery around the plaza.
    corner, path_a, path_b = plaza + 3.0, plaza + 9.0, plaza + 19.0
    for lx, ly in ((corner, corner), (-corner, corner), (corner, -corner), (-corner, -corner),
                   (path_a, 20), (path_a, -20), (path_b, 20), (path_b, -20)):
        add_lamp(mb, pal, cx + lx, ly, glow=pal["glow_gold"])
        keep_out_around(cx + lx, ly, 4.0)
    ring = [(x, y) for x, y in scatter(
        rng, 26, lambda r: (r.uniform(x0 + rim + 4, x1 - rim - 4), r.uniform(y0 + rim + 4, y1 - rim - 4)),
        5.0)]
    for x, y in ring:
        roll = rng.random()
        if roll < 0.4:
            add_tree(mb, pal, x, y, rng, solid=True)
        elif roll < 0.8:
            add_bush(mb, pal, x, y, rng)
        else:
            add_flowers(mb, pal, x, y, rng)

    # Bridge to the main island.
    bx0, bx1 = L["lobby_x1"], L["island_x_min"]
    bm, blen = (bx0 + bx1) / 2.0, bx1 - bx0
    mb.box((bm, 0.0, -0.9), (blen, 2 * bh, 1.8), pal["wood"])
    n = int(blen // 3.5)
    for i in range(n):
        if i % 2 == 0:
            mb.box((bx0 + (i + 0.5) * blen / n, 0.0, 0.03), (blen / n - 0.3, 2 * bh - 1.0, 0.06),
                   pal["wood_light"])
    mb.collider("box", (bm, 0.0, -1.0), (blen, 2 * bh, 2.0), kind="ground", material="WoodPlanks")
    for sy in (-1, 1):
        yr = sy * (bh - 0.5)
        for i in range(int(blen // 7.0) + 1):
            mb.box((bx0 + i * blen / int(blen // 7.0), yr, 2.25), (1.0, 1.0, 4.5), pal["wood_light"])
        mb.box((bm, yr, 4.2), (blen, 0.7, 0.7), pal["wood"])
        mb.box((bm, yr, 2.2), (blen, 0.5, 0.5), pal["wood"])
        mb.box((bm, sy * (bh - 1.6), 0.08), (blen, 0.5, 0.16), pal["glow_cyan"])
        mb.collider("box", (bm, yr, 2.25), (blen, 1.0, 4.5))
    for px in (bx0 + 18.0, bx1 - 18.0):
        mb.box((px, 0.0, -24.0), (8.0, 2 * bh - 6.0, 44.0), pal["stone_dark"])

    sec.emit(mb, "Lobby")

    # Invisible walls around the lobby, open where the bridge leaves.
    barrier("Lobby", x0, y1 + 1.0, x1, y1 + 1.0)
    barrier("Lobby", x0, y0 - 1.0, x1, y0 - 1.0)
    barrier("Lobby", x0 - 1.0, y0, x0 - 1.0, y1)
    barrier("Lobby", x1 + 1.0, bh, x1 + 1.0, y1)
    barrier("Lobby", x1 + 1.0, y0, x1 + 1.0, -bh)

    return {
        "center": (cx, 0.0, 0.05),
        "bounds": ((x0, y0, 0.0), (bx1, y1, 0.0)),
        "spawns": spawns,
        "spawnYaw": facing_yaw(0.0, 1.0),
        "portals": portals,
        "leaderboard": leaderboard,
        "showcase": showcase,
        "shop": shop.p(0, 0, 0.0),
        "dailyReward": chest.p(0, 0, 0.0),
        "tutorialBoard": {"position": tuto.p(0, -0.6, 13.0), "width": 30.0, "height": 18.0,
                          "yaw": facing_yaw(*tuto.front())},
        "bridge": ((bx0, -bh, 0.0), (bx1, bh, 0.0)),
    }


def build_island_base(world, pal, L):
    sec = world.section("Island")
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 99)
    add_floating_body(mb, pal, L["island_x_min"], -L["island_y"], L["island_x_max"], L["island_y"],
                      CONFIG["dirt_depth"], CONFIG["taper_depth"], rng, rocks=26)
    sec.emit(mb, "Island_Body")


def build_zone(world, pal, L, index, x0, x1, biome, texts):
    """One corridor zone: ground band, rims, plot walls and back walls of its
    cell, street props, zone gate, landmarks - or the desert and its arena."""
    sec = world.section(section_name(index, biome))
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] * 31 + index)
    sh, iy, rim = CONFIG["street_half"], L["island_y"], 11.0
    n = CONFIG["plots_per_side"]
    is_first, is_last = index == 1, index == len(BIOMES)
    h, t, depth = CONFIG["wall_height"], CONFIG["wall_thickness"], CONFIG["plot_depth"]

    # Ground and rims.
    a, b = biome["floor"]
    tile = CONFIG["tile"] * (1.6 if biome["decor"] == "desert" else 1.0)
    gx0 = x0 + rim if is_first else x0
    gx1 = x1 - rim if is_last else x1
    mb.checker(gx0, -iy + rim, gx1, iy - rim, 0.0, tile, pal[a], pal[b])
    add_rims(mb, pal[biome["rim"]], x0, -iy, x1, iy, rim, west=is_first, east=is_last)
    mb.collider("box", ((x0 + x1) / 2.0, 0.0, -2.0), (x1 - x0, 2 * iy, 4.0),
                kind="ground", material=biome["ground"])

    # Plot walls of this cell (wall i opens cell i; the trailing wall closes the last one).
    for w, wx in enumerate(L["wall_centers"]):
        if min(w, n - 1) + 1 != index:
            continue
        wall_a, wall_b = pal[biome["wall"][0]], pal[biome["wall"][1]]
        for side in (1, -1):
            y_a, y_b = side * sh, side * (sh + depth)
            mb.box((wx, side * (sh + depth / 2.0), h / 2.0), (t, depth, h), wall_a, solid=True)
            mb.box((wx, side * (sh + depth / 2.0), h + 1.0), (t + 1.5, depth + 1.5, 2.0),
                   pal[biome["cap"]])
            mb.checker_yz(wx - t / 2.0 - 0.2, min(y_a, y_b), 0.0, max(y_a, y_b), h,
                          CONFIG["tile"], wall_a, wall_b, facing=-1)
            mb.checker_yz(wx + t / 2.0 + 0.2, min(y_a, y_b), 0.0, max(y_a, y_b), h,
                          CONFIG["tile"], wall_b, wall_a, facing=1)
            mb.checker_xz(y_a - side * 0.2, wx - t / 2.0, 0.0, wx + t / 2.0, h,
                          CONFIG["tile"], wall_a, wall_b, facing=-side)

    if index <= n:
        # Back walls closing the two plots of this cell.
        bx0 = L["row_x0"] + (index - 1) * L["cell"]
        bxm = bx0 + L["cell"] / 2.0
        for side in (1, -1):
            mb.box((bxm, side * L["back_wall_y"], h / 2.0), (L["cell"], 6.0, h),
                   pal[biome["wall"][0]], solid=True)
            mb.box((bxm, side * L["back_wall_y"], h + 1.05), (L["cell"], 7.5, 2.1),
                   pal[biome["cap"]])
        # Street lamps and axis dashes.
        for x in range(int(L["row_x0"]) + 20, int(L["row_x1"]), 74):
            if x0 <= x < x1:
                for side in (1, -1):
                    add_lamp(mb, pal, float(x), side * (sh - 6.0), glow=pal[biome["glow"]])
                    keep_out_around(float(x), side * (sh - 6.0), 4.0)
        for x in range(int(L["row_x0"]), int(L["row_x1"]), 26):
            if x0 <= x + 6.0 < x1:
                mb.box((x + 6.0, 0.0, 0.12), (12.0, 2.2, 0.24), pal[biome["wall"][1]])
        # Props along the street edges (solid, players walk past them) ...
        ex0 = max(x0, L["island_x_min"] + 24.0)
        for x, y in scatter(rng, biome["street_props"],
                            lambda r: (r.uniform(ex0, x1 - 6.0),
                                       r.choice((1, -1)) * r.uniform(sh - 11.0, sh - 4.0)), 4.0):
            add_biome_decor(mb, pal, biome, x, y, rng, solid=True)
        # ... and scenery in the margins behind the back walls (unreachable).
        mx0, mx1 = max(x0, L["row_x0"]) + 6.0, min(x1, L["row_x1"]) - 6.0
        ym0, ym1 = L["back_wall_y"] + 9.0, iy - 14.0
        landmark_x = L["plot_centers"][index - 1]
        for side in (1, -1):
            keep_out_around(landmark_x, side * 190.0, 24.0)
            add_landmark(mb, pal, biome, landmark_x, side * 190.0, rng)
        for x, y in scatter(rng, biome["margin_props"],
                            lambda r: (r.uniform(mx0, mx1), r.choice((1, -1)) * r.uniform(ym0, ym1)),
                            4.0):
            add_biome_decor(mb, pal, biome, x, y, rng)

    zone_spawn_x = x0 + 26.0
    return_portal = None
    if is_first:
        # Entrance square: return portal, stone path from the bridge, archway.
        f = Frame(L["island_x_min"] + 22.0, -62.0, math.pi / 2.0)
        trigger, label_pos = add_portal(mb, pal, f, "glow_violet")
        keep_out_around(f.x, f.y, 14.0)
        sec.text(texts["portal_lobby"], sec.name + "_PortalText", label_pos, upright(f.r))
        return_portal = dict(trigger, id="return_entrance", label="LOBBY", target="lobby")
        ax = L["row_x0"] - 16.0
        mb.checker(L["island_x_min"], -CONFIG["bridge_half"], ax - 5.0, CONFIG["bridge_half"],
                   0.05, 8.0, pal["stone"], pal["stone_dark"])
        for side in (1, -1):
            mb.box((ax, side * 38.0, 22.0), (10.0, 12.0, 44.0), pal["stone"], solid=True)
            mb.box((ax, side * 38.0, 45.0), (13.0, 15.0, 3.0), pal["stone_dark"])
            mb.box((ax, side * 30.0, 30.0), (5.0, 3.0, 5.0), pal[biome["glow"]])
            keep_out(ax - 7, side * 30.0, ax + 7, side * 46.0)
        mb.box((ax, 0.0, 48.0), (12.0, 88.0, 8.0), pal["stone"])
        mb.box((ax, 0.0, 53.5), (14.0, 92.0, 3.0), pal["stone_dark"])
        mb.box((ax, 0.0, 44.0), (6.0, 60.0, 2.5), pal[biome["glow"]])
        sec.text(texts["gate_" + biome["id"]], sec.name + "_GateText", (ax - 6.4, 0.0, 48.0),
                 upright(-math.pi / 2.0))
        keep_out(L["island_x_min"], -CONFIG["bridge_half"] - 4, ax + 6, CONFIG["bridge_half"] + 4)
        zone_spawn_x = L["island_x_min"] + 22.0
        ex_x0, ex_x1 = L["island_x_min"] + 14.0, L["row_x0"] - 8.0
        for x, y in scatter(rng, 14, lambda r: (r.uniform(ex_x0, ex_x1),
                                                r.choice((1, -1)) * r.uniform(52.0, iy - 16.0)), 5.0):
            (add_tree if rng.random() < 0.5 else add_bush)(mb, pal, x, y, rng, solid=True)
    elif index <= n + 1:
        gx = L["wall_centers"][index - 1]
        add_zone_gate(mb, pal, biome, gx)
        sec.text(texts["gate_" + biome["id"]], sec.name + "_GateText", (gx - 6.45, 0.0, 33.0),
                 upright(-math.pi / 2.0))
        zone_spawn_x = gx + 18.0

    if is_last:
        return_portal = build_desert(mb, pal, L, x0, x1, biome, rng, sec, texts)
        zone_spawn_x = L["desert_x0"] + 14.0

    sec.emit(mb, sec.name)

    area = capsule_area(L, index, x0, x1)
    return {
        "biome": biome,
        "index": index,
        "section": sec.name,
        "bounds": ((x0, -iy, 0.0), (x1, iy, 0.0)),
        "spawn": (zone_spawn_x, 0.0, 0.0),
        "spawnYaw": facing_yaw(1.0, 0.0),
        "capsuleArea": ((area[0], area[1], 0.0), (area[2], area[3], 0.0)),
        "returnPortal": return_portal,
    }


def build_desert(mb, pal, L, x0, x1, biome, rng, sec, texts):
    """Desert band: dunes, cacti, step pyramids and the boss altar."""
    iy = L["island_y"]
    ax = L["arena_x"]

    # Altar: stepped base, pillars, beam, floating rocks.
    mb.cylinder((ax, 0.0, 1.5), 40.0, 3.0, pal["stone"], segments=16, solid=True)
    mb.cylinder((ax, 0.0, 4.0), 32.0, 3.0, pal["stone_dark"], segments=16, solid=True)
    mb.cylinder((ax, 0.0, 6.4), 25.0, 2.6, pal["stone"], segments=16, solid=True)
    mb.cylinder((ax, 0.0, 8.2), 9.0, 1.8, pal["glow_violet"], segments=12)
    for i in range(6):
        a = 2 * math.pi * i / 6
        px, py = ax + math.cos(a) * 29.0, math.sin(a) * 29.0
        mb.box((px, py, 17.0), (7.0, 7.0, 26.0), pal["stone"], rot_z=a, solid=True)
        mb.box((px, py, 31.0), (9.0, 9.0, 3.0), pal["stone_dark"], rot_z=a)
        mb.box((px, py, 33.5), (3.5, 3.5, 3.0), pal["glow_violet"], rot_z=a)
    mb.cylinder((ax, 0.0, 82.0), 5.5, 148.0, pal["glow_violet"], segments=12, taper=0.55)
    for _ in range(7):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(16, 52)
        mb.box((ax + math.cos(a) * r, math.sin(a) * r, rng.uniform(60, 130)),
               (rng.uniform(9, 22), rng.uniform(9, 22), rng.uniform(5, 12)),
               pal["stone_dark"], rot_z=rng.uniform(0, math.pi))
    keep_out_around(ax, 0.0, 46.0)

    # Step pyramids (climbable, so solid tier by tier).
    for px, py, base, tiers in ((x1 - 45.0, 160.0, 50.0, 6), (x0 + 48.0, -168.0, 36.0, 4)):
        add_step_pyramid(mb, pal, px, py, base, tiers, 6.0, solid=True)
        keep_out_around(px, py, base / 2.0 + 4.0)

    # Return portal to the lobby, facing the arriving players.
    f = Frame(x0 + 34.0, 72.0, 0.0)
    trigger, label_pos = add_portal(mb, pal, f, "glow_violet")
    keep_out_around(f.x, f.y, 14.0)
    sec.text(texts["portal_lobby"], sec.name + "_PortalText", label_pos, upright(f.r))

    gx = L["wall_centers"][-1]
    keep_out(gx - 10.0, -CONFIG["street_half"], x0 + 30.0, CONFIG["street_half"])

    # Low dunes (walkable, never solid) and props.
    for _ in range(26):
        dx = rng.uniform(x0 + 16, x1 - 16)
        dy = rng.uniform(-iy + 22, iy - 22)
        if is_free(dx, dy, 6.0):
            s = rng.uniform(14, 34)
            mb.box((dx, dy, 0.35), (s, s * rng.uniform(0.6, 1.2), 0.7),
                   pal["sand_dark"], rot_z=rng.uniform(0, math.pi))
    for x, y in scatter(rng, 34, lambda r: (r.uniform(x0 + 20, x1 - 14),
                                             r.uniform(-iy + 18, iy - 18)), 5.0):
        roll = rng.random()
        if roll < 0.5:
            add_cactus(mb, pal, x, y, rng, solid=True)
        elif roll < 0.8:
            add_rock(mb, pal, x, y, rng, solid=True)
        else:
            add_crate(mb, pal, x, y, rng, solid=True)

    return dict(trigger, id="return_arena", label="LOBBY", target="lobby")


def build_plot_template(pal):
    """One base ("case"), in plot-local coordinates: x along the street, y the
    depth from the street edge. Built once and instanced 8 times, so every
    player gets the exact same base."""
    w, d = CONFIG["plot_width"], CONFIG["plot_depth"]
    hw = w / 2.0
    rng = random.Random(CONFIG["seed"] * 100)
    mb = MeshBuilder()

    mb.checker(-hw, 0.0, hw, d, 0.05, CONFIG["tile"], pal["grass_b"], pal["grass_a"])
    mb.collider("box", (0.0, d / 2.0, -0.45), (w, d, 1.0), kind="ground", material="Grass")

    # Safe-zone line and shield markers.
    mb.box((0.0, 4.0, 0.16), (w - 4.0, 1.6, 0.3), pal["red"])
    for lx in (-30.0, 30.0):
        mb.cylinder((lx, 12.0, 0.18), 3.0, 0.3, pal["blue"], segments=6)

    signs = {
        "vendre": add_stall(mb, pal, Frame(-44.0, 24.0), pal["red"]),
        "boutique": add_stall(mb, pal, Frame(44.0, 24.0), pal["yellow"]),
    }
    add_machine(mb, pal, Frame(0.0, 26.0))
    add_conveyor(mb, pal, Frame(-16.0, 46.0, math.pi / 2.0))

    pens = []
    for ly in (66.0, 104.0):
        for lx in (-46.0, -12.0, 22.0):
            pens.append((lx, ly, 1.8))
            add_pen(mb, pal, lx, ly, 30.0, 32.0)
            if rng.random() < 0.55:
                add_flowers(mb, pal, lx + rng.uniform(-11, 11), ly + rng.uniform(4, 12), rng)

    add_house(mb, pal, Frame(50.0, 98.0))

    for lx, ly in ((-hw + 8.0, 10.0), (hw - 8.0, 10.0), (-hw + 8.0, d - 8.0), (hw - 8.0, d - 8.0)):
        add_lamp(mb, pal, lx, ly, glow=pal["glow_gold"])
    for lx, ly in ((-57.0, 18.0), (-55.0, 31.0), (57.0, 18.0), (55.0, 31.0)):
        add_crate(mb, pal, lx, ly, rng, solid=True)

    # Scattered decor, skipping the pens, the house and the entrance.
    for _ in range(16):
        lx = rng.uniform(-hw + 6.0, hw - 6.0)
        ly = rng.uniform(8.0, d - 6.0)
        if 44.0 < ly < 122.0 and -64.0 < lx < 40.0:
            continue
        if ly < 38.0 and abs(lx) < 60.0:
            continue
        if abs(lx - 50.0) < 15.0 and abs(ly - 98.0) < 14.0:
            continue
        roll = rng.random()
        if roll < 0.45:
            add_bush(mb, pal, lx, ly, rng)
        elif roll < 0.75:
            add_rock(mb, pal, lx, ly, rng, solid=True)
        else:
            add_tree(mb, pal, lx, ly, rng, solid=True)

    anchors = {
        "center": (0.0, d / 2.0, 0.05),
        "entrance": (0.0, 4.0, 0.05),
        "spawn": (0.0, 8.0, 0.05),
        "machine": (0.0, 26.0, 0.0),
        "sellStand": (-44.0, 24.0, 0.0),
        "shopStand": (44.0, 24.0, 0.0),
        "conveyor": (-16.0, 46.0, 0.0),
        "house": (50.0, 98.0, 0.0),
        "sign": (0.0, 26.0, 34.0),
        "pens": pens,
    }
    return mb, anchors, signs


def build_plots(world, pal, L, texts):
    sec = world.section("Plots")
    mb, local, signs = build_plot_template(pal)
    meshes = mb.make_meshes("PlotTemplate")
    sh, d, hw = CONFIG["street_half"], CONFIG["plot_depth"], CONFIG["plot_width"] / 2.0
    anchors = []
    for i, cx in enumerate(L["plot_centers"]):
        for tag, side in (("N", 1), ("S", -1)):
            pid = "%s%d" % (tag, i + 1)
            f = Frame(cx, side * sh, 0.0 if side > 0 else math.pi)
            name = "Plot_" + pid
            sec.place(meshes, name, f)
            register_colliders(mb, sec.name, f)
            sec.text(texts["zone_sure"], name + "_SafeZoneText", f.p(0.0, 14.0, 0.3), (0, 0, f.r))
            for key, pos in signs.items():
                sec.text(texts[key], "%s_Sign_%s" % (name, key.title()), f.p(pos[0], pos[1], pos[2]),
                         upright(f.r))

            def P(point):
                return f.p(point[0], point[1], point[2])

            entry = {
                "id": pid,
                "side": "north" if side > 0 else "south",
                "zone": BIOMES[min(i, len(BIOMES) - 2)]["id"],
            }
            for key in ("center", "entrance", "spawn", "machine", "sellStand", "shopStand",
                        "conveyor", "house", "sign"):
                entry[key] = P(local[key])
            entry["spawnYaw"] = facing_yaw(0.0, float(side))
            entry["pens"] = [P(p) for p in local["pens"]]
            entry["bounds"] = ((cx - hw, side * sh, 0.0),
                               (cx + hw, side * (sh + d), CONFIG["wall_height"]))
            anchors.append(entry)
    return anchors


def build_ref_markers(world, pal):
    sec = world.section("REF")
    for name, pos in REF_MARKERS.items():
        mb = MeshBuilder()
        mb.box(pos, (REF_SIZE, REF_SIZE, REF_SIZE), pal["ref"])
        sec.emit(mb, name)


def build_island_barriers(L):
    """Invisible walls: island edge (open at the bridge) and the scenery margins
    behind the plot rows, which are decor only."""
    ix0, ix1, iy = L["island_x_min"], L["island_x_max"], L["island_y"]
    bh = CONFIG["bridge_half"]
    barrier("Island", ix0, iy + 1.0, ix1, iy + 1.0)
    barrier("Island", ix0, -iy - 1.0, ix1, -iy - 1.0)
    barrier("Island", ix1 + 1.0, -iy, ix1 + 1.0, iy)
    barrier("Island", ix0 - 1.0, bh, ix0 - 1.0, iy)
    barrier("Island", ix0 - 1.0, -iy, ix0 - 1.0, -bh)
    east = L["row_x1"] + CONFIG["wall_thickness"]
    for side in (1, -1):
        y_a, y_b = side * CONFIG["street_half"] + side * CONFIG["plot_depth"], side * iy
        barrier("Island", L["row_x0"], y_a, L["row_x0"], y_b)
        barrier("Island", east, y_a, east, y_b)


# ---------------------------------------------------------------- LUA EXPORT


def to_roblox(point):
    """Blender (Z-up) -> Roblox/glTF (Y-up), matching export_yup=True on the GLB.

    Get this wrong and every anchor lands somewhere else than the mesh it
    belongs to, so it is the one conversion worth stating explicitly.
    """
    x, y, z = point
    return (x, z, -y)


class V3:
    """A Blender point, written as a Roblox Vector3."""

    def __init__(self, point):
        self.point = point

    def lua(self):
        x, y, z = (v + 0.0 for v in to_roblox(self.point))
        return "Vector3.new(%.2f, %.2f, %.2f)" % (x + 0.0, y + 0.0, z + 0.0)


class Size3:
    """A Blender (sx, sy, sz) size, written as a Roblox Vector3 size."""

    def __init__(self, size):
        self.size = size

    def lua(self):
        sx, sy, sz = self.size
        return "Vector3.new(%.2f, %.2f, %.2f)" % (sx, sz, sy)


class RGB:
    def __init__(self, color):
        self.color = color

    def lua(self):
        return "Color3.fromRGB(%d, %d, %d)" % tuple(int(round(c * 255)) for c in self.color)


class Num:
    def __init__(self, value, digits=4):
        self.value, self.digits = value, digits

    def lua(self):
        return "%.*f" % (self.digits, round(self.value, self.digits) + 0.0)


def bounds(corner_a, corner_b):
    """Axis-aligned box as {min, max} in Roblox axes.

    The Y-up conversion flips Y, so a Blender corner pair is not sorted any more
    once converted: sort per component or every containment test breaks.
    """
    a, b = to_roblox(corner_a), to_roblox(corner_b)
    low = tuple(min(a[i], b[i]) for i in range(3))
    high = tuple(max(a[i], b[i]) for i in range(3))
    # V3 expects Blender coordinates: invert to_roblox on the sorted corners.
    return {"min": V3((low[0], -low[2], low[1])), "max": V3((high[0], -high[2], high[1]))}


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def lua_value(value, indent=0):
    pad = "\t" * (indent + 1)
    if hasattr(value, "lua"):
        return value.lua()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return "%.2f" % (value + 0.0)
    if isinstance(value, str):
        return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for key, item in value.items():
            k = key if _IDENT.match(key) else '["%s"]' % key
            lines.append("%s%s = %s," % (pad, k, lua_value(item, indent + 1)))
        lines.append("\t" * indent + "}")
        return "\n".join(lines)
    if isinstance(value, (list, tuple)):
        if not value:
            return "{}"
        lines = ["{"]
        for item in value:
            lines.append("%s%s," % (pad, lua_value(item, indent + 1)))
        lines.append("\t" * indent + "}")
        return "\n".join(lines)
    raise TypeError("cannot write %r to Lua" % (value,))


def portal_entry(p):
    return {
        "id": p["id"],
        "label": p["label"],
        "target": p["target"],
        "position": V3(p["center"]),
        "size": Size3(p["size"]),
        "yaw": Num(p["rot"]),
    }


def write_map_data(filepath, L, lobby, zones, plots):
    """Emit src/Shared/MapData.lua so gameplay code never hardcodes a position."""
    sh = CONFIG["street_half"]
    iy = L["island_y"]
    lane = sh - 16.0

    tables = {}
    tables["reference"] = {
        "origin": V3(REF_MARKERS["REF_Origin"]),
        "axisX": V3(REF_MARKERS["REF_AxisX"]),
        "axisY": V3(REF_MARKERS["REF_AxisY"]),
        "markerSize": REF_SIZE,
    }
    tables["island"] = bounds((L["island_x_min"], iy, -CONFIG["dirt_depth"]),
                              (L["island_x_max"], -iy, 0.0))
    tables["street"] = dict(bounds((L["island_x_min"], sh, 0.0), (L["desert_x0"], -sh, 0.0)),
                            width=sh * 2.0)
    tables["lobby"] = {
        "id": "lobby",
        "label": "Lobby",
        "index": 0,
        "color": RGB(PALETTE["glow_violet"]["color"]),
        "bounds": bounds(*lobby["bounds"]),
        "center": V3(lobby["center"]),
        "spawns": [V3(p) for p in lobby["spawns"]],
        "spawnYaw": Num(lobby["spawnYaw"]),
        "leaderboard": {
            "position": V3(lobby["leaderboard"]["position"]),
            "width": lobby["leaderboard"]["width"],
            "height": lobby["leaderboard"]["height"],
            "yaw": Num(lobby["leaderboard"]["yaw"]),
        },
        "tutorialBoard": {
            "position": V3(lobby["tutorialBoard"]["position"]),
            "width": lobby["tutorialBoard"]["width"],
            "height": lobby["tutorialBoard"]["height"],
            "yaw": Num(lobby["tutorialBoard"]["yaw"]),
        },
        "shop": V3(lobby["shop"]),
        "dailyReward": V3(lobby["dailyReward"]),
        "showcase": [{"rarity": s["rarity"], "position": V3(s["position"])}
                     for s in lobby["showcase"]],
    }
    tables["bridge"] = bounds(*lobby["bridge"])

    zone_rows = []
    for z in zones:
        b = z["biome"]
        zone_rows.append({
            "id": b["id"],
            "label": b["label"],
            "index": z["index"],
            "section": z["section"],
            "color": RGB(PALETTE[b["glow"]]["color"]),
            "bounds": bounds(*z["bounds"]),
            "spawn": V3(z["spawn"]),
            "spawnYaw": Num(z["spawnYaw"]),
            "capsuleArea": bounds(*z["capsuleArea"]),
        })
    tables["zones"] = zone_rows

    portals = [portal_entry(p) for p in lobby["portals"]]
    portals += [portal_entry(z["returnPortal"]) for z in zones if z["returnPortal"]]
    tables["portals"] = portals

    tables["capsuleZone"] = bounds((L["row_x0"], lane, 0.0), (L["row_x1"], -lane, 0.0))
    tables["bossAltar"] = {
        "center": V3((L["arena_x"], 0.0, 0.0)),
        "top": V3((L["arena_x"], 0.0, 9.1)),
        "radius": 40.0,
    }

    plot_rows = []
    for p in plots:
        row = {"id": p["id"], "side": p["side"], "zone": p["zone"]}
        for key in ("center", "entrance", "spawn", "machine", "sellStand", "shopStand",
                    "conveyor", "house", "sign"):
            row[key] = V3(p[key])
        row["spawnYaw"] = Num(p["spawnYaw"])
        row["pens"] = [V3(pen) for pen in p["pens"]]
        row["bounds"] = bounds(*p["bounds"])
        plot_rows.append(row)
    tables["plots"] = plot_rows

    tables["materials"] = {
        key: {
            "color": RGB(spec["color"]),
            "material": spec["rbx"],
            "transparency": spec["transparency"],
        }
        for key, spec in PALETTE.items()
    }

    notes = {
        "reference": "Alignment markers baked into the GLB (see MapService).",
        "lobby": "Spawn island. `index` 0 so it sorts before the corridor zones.",
        "zones": "Corridor zones in walking order. `index` grows with the distance from the\n"
                 "-- lobby, so it doubles as a difficulty / reward tier.",
        "portals": "Teleport triggers. target = \"base\", \"lobby\" or \"zone:<id>\".\n"
                   "-- position/size/yaw describe the trigger box (CFrame.Angles(0, yaw, 0)).",
        "capsuleZone": "Legacy: the street lane across the plot rows. Prefer zones[i].capsuleArea.",
        "plots": "Player bases (\"cases\"). Ids N1..N4 (north row) and S1..S4 (south row).",
        "materials": "Roblox look per material key: MeshPart names end in \"__<key>\".",
    }

    lines = [
        "--!strict",
        "-- GENERATED FILE - do not edit by hand.",
        "-- Produced by KaijuHeist/blender/build_map.py; re-run that script to update.",
        "--",
        "-- Positions are studs in Roblox axes (Y up), matching kaiju_heist_map.glb once",
        "-- MapService has aligned it on the world origin. Yaws are radians around Y.",
        "",
        "local MapData = {}",
        "",
    ]
    for key, value in tables.items():
        if key in notes:
            lines.append("-- " + notes[key])
        lines.append("MapData.%s = %s" % (key, lua_value(value)))
        lines.append("")

    lines += [
        "local function inside(bounds: any, position: Vector3): boolean",
        "\treturn position.X >= bounds.min.X and position.X <= bounds.max.X",
        "\t\tand position.Z >= bounds.min.Z and position.Z <= bounds.max.Z",
        "end",
        "",
        "-- Which corridor zone a world position falls into (ignores height).",
        "function MapData.GetZoneAt(position: Vector3): any",
        "\tfor _, zone in ipairs(MapData.zones) do",
        "\t\tif inside(zone.bounds, position) then",
        "\t\t\treturn zone",
        "\t\tend",
        "\tend",
        "\treturn nil",
        "end",
        "",
        "-- Lobby (bridge included) or corridor zone at a position; nil off the map.",
        "function MapData.GetAreaAt(position: Vector3): any",
        "\tif inside(MapData.lobby.bounds, position) then",
        "\t\treturn MapData.lobby",
        "\tend",
        "\treturn MapData.GetZoneAt(position)",
        "end",
        "",
        "function MapData.GetZoneById(id: string): any",
        "\tfor _, zone in ipairs(MapData.zones) do",
        "\t\tif zone.id == id then",
        "\t\t\treturn zone",
        "\t\tend",
        "\tend",
        "\treturn nil",
        "end",
        "",
        "function MapData.GetPlot(id: string): any",
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


def write_colliders(filepath):
    """Emit src/Server/MapColliders.lua, the collision volumes MapService builds."""
    lines = [
        "-- GENERATED FILE - do not edit by hand.",
        "-- Produced by KaijuHeist/blender/build_map.py; re-run that script to update.",
        "--",
        "-- Invisible collision volumes for the imported map, built by MapService.",
        "-- The visual meshes never block players: these volumes do.",
        "--   shape    \"box\" or \"cylinder\" (vertical axis)",
        "--   kind     \"ground\" (floors), \"solid\" (walls, props), \"barrier\" (island edges)",
        "--   material Roblox material for footstep sounds (ground only)",
        "--   position, size in Roblox axes; yaw in radians around Y",
        "return {",
    ]
    for c in sorted(COLLIDERS, key=lambda e: (e["section"], e["kind"])):
        fields = [
            'shape = "%s"' % c["shape"],
            'kind = "%s"' % c["kind"],
        ]
        if c.get("material"):
            fields.append('material = "%s"' % c["material"])
        fields += [
            'section = "%s"' % c["section"],
            "position = %s" % V3(c["center"]).lua(),
            "size = %s" % Size3(c["size"]).lua(),
            "yaw = %s" % Num(c["rot"] % (2 * math.pi)).lua(),
        ]
        lines.append("\t{ %s }," % ", ".join(fields))
    lines += ["}", ""]
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


# ---------------------------------------------------------------- CHECKS


def _corners(cx, cy, sx, sy, rot):
    c, s = math.cos(rot), math.sin(rot)
    hx, hy = sx / 2.0, sy / 2.0
    return [(cx + x * c - y * s, cy + x * s + y * c)
            for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]


def _overlap_2d(a, b, eps=0.01):
    """Separating-axis test between two convex quads."""
    for poly in (a, b):
        for i in range(4):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % 4]
            nx, ny = y2 - y1, x1 - x2
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            norm = math.hypot(nx, ny) or 1.0
            if max(pa) <= min(pb) + eps * norm or max(pb) <= min(pa) + eps * norm:
                return False
    return True


def _collider_quad(c):
    cx, cy, _ = c["center"]
    return _corners(cx, cy, c["size"][0], c["size"][1], c["rot"])


def _z_range(c):
    cz, sz = c["center"][2], c["size"][2]
    return cz - sz / 2.0, cz + sz / 2.0


def blocking(quad, z0, z1, kinds=("solid", "barrier")):
    """Colliders of the given kinds intersecting a quad over [z0, z1]."""
    hits = []
    for c in COLLIDERS:
        if c["kind"] not in kinds:
            continue
        c0, c1 = _z_range(c)
        if c1 <= z0 or c0 >= z1:
            continue
        if _overlap_2d(quad, _collider_quad(c)):
            hits.append(c)
    return hits


def ground_top(x, y):
    """Highest ground collider top under a point, or None."""
    best = None
    for c in COLLIDERS:
        if c["kind"] != "ground":
            continue
        quad = _collider_quad(c)
        if _overlap_2d(quad, _corners(x, y, 0.1, 0.1, 0.0)):
            top = _z_range(c)[1]
            best = top if best is None else max(best, top)
    return best


def run_checks(L, lobby, zones, plots, world):
    """Measure the output instead of trusting it. Prints CHECK_OK / CHECK_FAIL."""
    failures = []
    passed = [0]

    def check(name, ok, detail=""):
        if ok:
            passed[0] += 1
            print("CHECK_OK", name)
        else:
            failures.append(name)
            print("CHECK_FAIL", name, detail)

    # Zones are contiguous and cover the island exactly.
    segs = biome_segments(L)
    gaps = [(a[1], b[0]) for a, b in zip(segs, segs[1:]) if abs(a[1] - b[0]) > 1e-6]
    check("zones_contiguous", not gaps and segs[0][0] == L["island_x_min"]
          and segs[-1][1] == L["island_x_max"], str(gaps))

    # Every place a character is put down stands on ground and is clear of walls.
    standing = [("lobby_spawn_%d" % i, p) for i, p in enumerate(lobby["spawns"])]
    standing += [("zone_spawn_%s" % z["biome"]["id"], z["spawn"]) for z in zones]
    standing += [("plot_spawn_%s" % p["id"], p["spawn"]) for p in plots]
    for name, (x, y, z) in standing:
        top = ground_top(x, y)
        check(name + "_grounded", top is not None and abs(top - z) < 0.3, "top=%s z=%s" % (top, z))
        hits = blocking(_corners(x, y, 3.0, 3.0, 0.0), z + 0.3, z + 5.5)
        check(name + "_clear", not hits, str([(h["section"], h["center"]) for h in hits][:3]))

    # Portal triggers do not overlap anything solid (they would be unreachable).
    all_portals = lobby["portals"] + [z["returnPortal"] for z in zones if z["returnPortal"]]
    for p in all_portals:
        cx, cy, cz = p["center"]
        quad = _corners(cx, cy, p["size"][0], p["size"][1], p["rot"])
        hits = blocking(quad, cz - p["size"][2] / 2.0 + 0.5, cz + p["size"][2] / 2.0)
        check("portal_%s_clear" % p["id"], not hits,
              str([(h["section"], h["center"]) for h in hits][:3]))

    # Capsule areas: inside their zone and free of anything solid.
    for z in zones:
        (ax0, ay0, _), (ax1, ay1, _) = z["capsuleArea"]
        (zx0, zy0, _), (zx1, zy1, _) = z["bounds"]
        check("capsules_%s_in_zone" % z["biome"]["id"],
              zx0 <= ax0 < ax1 <= zx1 and zy0 <= ay0 < ay1 <= zy1)
        quad = _corners((ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0, ax1 - ax0 + 2.0, ay1 - ay0 + 2.0, 0.0)
        hits = blocking(quad, 0.2, 6.0)
        check("capsules_%s_clear" % z["biome"]["id"], not hits,
              str([(h["section"], h["center"]) for h in hits][:3]))

    # Plots sit inside the zone they are attributed to.
    for p in plots:
        zone = next(z for z in zones if z["biome"]["id"] == p["zone"])
        (px0, _, _), (px1, _, _) = p["bounds"]
        (zx0, _, _), (zx1, _, _) = zone["bounds"]
        check("plot_%s_in_zone" % p["id"], zx0 <= min(px0, px1) and max(px0, px1) <= zx1)

    # Mesh budget and naming contract of every exported object.
    worst = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        tris = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
        worst = max(worst, tris)
        m = re.match(r"^.+?__([A-Za-z0-9_]+?)(?:__c\d+)?$", obj.name)
        check("name_" + obj.name, m is not None and m.group(1) in PALETTE
              and len(obj.data.materials) == 1, "tris=%d" % tris)
    check("mesh_budget", worst <= MAX_TRIS_PER_PART, "worst=%d" % worst)

    print("CHECKS passed=%d failed=%d" % (passed[0], len(failures)))
    return not failures


def check_mesh_budget(limit=10000):
    """Roblox refuses a MeshPart above 10k triangles - fail loudly, not at import."""
    rows = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        rows.append((sum(len(p.vertices) - 2 for p in obj.data.polygons), obj.name))
    rows.sort(reverse=True)
    unique = len({obj.data.name for obj in bpy.data.objects if obj.type == "MESH"})
    total = sum(r[0] for r in rows)
    print("MESH_BUDGET total=%d objects=%d unique_meshes=%d max=%d (%s)"
          % (total, len(rows), unique, rows[0][0], rows[0][1]))
    for tris, name in rows:
        if tris > limit:
            print("MESH_OVER_LIMIT %s has %d tris (limit %d) - split it" % (name, tris, limit))
    kinds = {}
    for c in COLLIDERS:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print("COLLIDERS total=%d %s" % (len(COLLIDERS), kinds))
    return all(r[0] <= limit for r in rows)


# ---------------------------------------------------------------- SCENE


def build_world_sky():
    """Night-blue gradient sky with stars."""
    world = bpy.data.worlds.new("KaijuSky")
    bpy.context.scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True  # always on (and deprecated) from Blender 5.0
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


def build_lights(col):
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
    cam_data.clip_end = 6000.0
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


def pick_render_engine(scene):
    """EEVEE by default (its id changed between 4.x and 5.x). KAIJU_RENDER_ENGINE
    overrides it, e.g. CYCLES on a machine without a GPU."""
    wanted = os.environ.get("KAIJU_RENDER_ENGINE")
    for engine in ([wanted] if wanted else []) + ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"]:
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = int(os.environ.get("KAIJU_RENDER_SAMPLES", "32"))
        scene.cycles.device = "CPU"
    return scene.render.engine


def setup_render():
    scene = bpy.context.scene
    pick_render_engine(scene)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = int(os.environ.get("KAIJU_RENDER_PERCENT", "100"))
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
    COLLIDERS.clear()
    KEEP_OUT.clear()
    random.seed(CONFIG["seed"])
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SECTIONS_DIR, exist_ok=True)

    pal = build_palette()
    L = layout()
    texts = build_texts(pal)
    world = World()

    # Reserve the capsule lanes and the street lane before any decor is scattered.
    segments = biome_segments(L)
    for index, (x0, x1, _) in enumerate(segments, start=1):
        ax0, ay0, ax1, ay1 = capsule_area(L, index, x0, x1)
        keep_out(ax0 - 2.0, ay0 - 2.0, ax1 + 2.0, ay1 + 2.0)
    keep_out(L["island_x_min"], -CONFIG["street_half"] + 12.0, L["desert_x0"],
             CONFIG["street_half"] - 12.0)

    lobby = build_lobby(world, pal, L, texts)
    build_island_base(world, pal, L)
    zones = [build_zone(world, pal, L, i, x0, x1, biome, texts)
             for i, (x0, x1, biome) in enumerate(segments, start=1)]
    plots = build_plots(world, pal, L, texts)
    build_ref_markers(world, pal)
    build_island_barriers(L)

    rig = new_collection("Rig")
    build_world_sky()
    build_lights(rig)
    mid_x = (L["lobby_x0"] + L["island_x_max"]) / 2.0
    cams = {
        "aerial": add_camera("Cam_Aerial", (mid_x - 700.0, -1050.0, 760.0),
                             (mid_x + 40.0, 0.0, -20.0), rig, lens=32.0),
        "lobby": add_camera("Cam_Lobby", (L["lobby_cx"] + 70.0, -175.0, 105.0),
                            (L["lobby_cx"] - 5.0, 18.0, 6.0), rig, lens=30.0),
        "street": add_camera("Cam_Street", (L["island_x_min"] + 8.0, 0.0, 22.0),
                             (L["row_x1"] + 180.0, 0.0, 26.0), rig, lens=28.0),
        "plot": add_camera("Cam_Plot", (L["plot_centers"][1] - 150.0, -60.0, 175.0),
                           (L["plot_centers"][1], CONFIG["street_half"] + 62.0, 6.0), rig, lens=40.0),
        "boss": add_camera("Cam_Boss", (L["desert_x0"] - 30.0, -150.0, 120.0),
                           (L["arena_x"] + 10.0, 10.0, 18.0), rig, lens=30.0),
    }
    setup_render()

    blend_path = os.path.join(OUT_DIR, "kaiju_heist_map.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("SAVED_BLEND", blend_path)

    glb_path = os.path.join(OUT_DIR, "kaiju_heist_map.glb")
    export_glb(glb_path)
    print("SAVED_GLB", glb_path)

    for stale in os.listdir(SECTIONS_DIR):
        if stale.endswith(".glb"):
            os.remove(os.path.join(SECTIONS_DIR, stale))
    ref = world.sections["REF"]
    for name, sec in world.sections.items():
        if name == "REF":
            continue
        path = os.path.join(SECTIONS_DIR, name + ".glb")
        export_glb(path, [world.empty, sec.empty] + sec.objects + [ref.empty] + ref.objects)
        print("SAVED_SECTION", path)

    map_data_path = os.path.join(SRC_SHARED_DIR, "MapData.lua")
    write_map_data(map_data_path, L, lobby, zones, plots)
    print("SAVED_MAPDATA", map_data_path)
    colliders_path = os.path.join(SRC_SERVER_DIR, "MapColliders.lua")
    write_colliders(colliders_path)
    print("SAVED_COLLIDERS", colliders_path)

    check_mesh_budget()
    run_checks(L, lobby, zones, plots, world)

    if os.environ.get("KAIJU_SKIP_RENDER"):
        print("RENDER_SKIPPED")
        return
    for key, cam in cams.items():
        render_to(cam, os.path.join(OUT_DIR, "preview_%s.png" % key))


if __name__ == "__main__":
    main()
