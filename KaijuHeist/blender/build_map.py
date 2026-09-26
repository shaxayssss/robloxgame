"""
Kaiju Heist - full world generator (Blender 5.x).

    blender -b --python build_map.py
    (or open this file in Blender's Text Editor and press Run Script)

Builds the whole playable world as a T seen from above:

    - the bar of the T is a huge lobby: marble plaza around a giant kaiju
      statue, the player bases ("enclos", B1..B4) along its west side, portals,
      leaderboard, rarity showcase, daily reward, tutorial, and two shops
      (BOUTIQUE / VENTE and VITESSE) at the corridor mouth;
    - the stem is the corridor of zones running east through a monumental gate:
      Zone Verte -> Zone de Lave -> Zone de Glace -> Zone de Pierre ->
      Zone Desert, which ends in a circular boss arena. Everything is driven by CONFIG / BIOMES / PALETTE below:
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
    # T-shaped world: the lobby is the bar of the T (north-south), the corridor
    # of zones is the stem, running east from the middle of the lobby.
    "base_count": 4,          # player bases ("enclos") along the lobby's west side
    "plot_width": 132.0,      # base width along the lobby edge (Y)
    "plot_depth": 122.0,      # base depth (X, measured from the plaza edge)
    "wall_thickness": 16.0,   # walls separating bases
    "wall_height": 40.0,
    "plaza_len": 302.0,       # grand plaza depth between the bases and the corridor
    "lobby_margin": 26.0,     # lobby width beyond the base column, at each end
    "corridor_half": 56.0,    # half-width of the walkable corridor
    "corridor_wall_height": 30.0,
    "corridor_margin": 60.0,  # scenery strip behind each corridor wall
    "zone_len": 160.0,        # length of each corridor zone
    "arena_len": 260.0,       # last zone: corridor end + circular boss arena
    "tile": 11.0,             # checker tile size for grounds and walls
    "dirt_depth": 60.0,       # dirt body thickness under the ground
    "taper_depth": 90.0,      # tapered island tip below the dirt
    "statue_scale": 1.25,     # the kaiju statue in the middle of the lobby
    "barrier_height": 40.0,   # invisible walls around the islands
    "seed": 7,
}

MAX_TRIS_PER_PART = 9500      # Roblox refuses a MeshPart above 10 000 triangles

# Corridor zones, in walking order from the lobby; the last one ends in the
# boss arena. Add an entry to lengthen the corridor. See ZONES.md.
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
     "decor": "desert", "street_props": 10, "margin_props": 10},
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
    "statue": _mat(0.30, 0.34, 0.40, roughness=0.6),
    "statue_dark": _mat(0.17, 0.19, 0.24, roughness=0.6),
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
    """Coordinates derived from CONFIG, shared by every builder.

    Top view (X east, Y north):

        +----------+
        | bases |  |
        |  B3   |  |
        |  B1   |  +----------------------------------------------+
        |       |P |  Zone 1 | Zone 2 | Zone 3 | Zone 4 | Zone 5 ( arena )
        |  B2   |  +----------------------------------------------+
        |  B4   |  |
        +----------+
          lobby      corridor of zones, from x = 0 eastwards
    """
    c = CONFIG
    cell = c["plot_width"] + c["wall_thickness"]
    n = c["base_count"]
    t = c["wall_thickness"]
    col_span = n * cell + t
    street_x = -c["plaza_len"]
    back_x = street_x - c["plot_depth"]
    ch = c["corridor_half"]
    corridor_len = (len(BIOMES) - 1) * c["zone_len"] + c["arena_len"]
    arena_r = 88.0
    arena_x = corridor_len - 100.0
    wall_y = ch + 4.0
    return {
        "cell": cell,
        "col_span": col_span,
        "base_centers": [-col_span / 2.0 + t + c["plot_width"] / 2.0 + k * cell for k in range(n)],
        "wall_centers": [-col_span / 2.0 + t / 2.0 + k * cell for k in range(n + 1)],
        "street_x": street_x,              # plaza edge the bases open onto
        "back_x": back_x,                  # back of the bases
        "lobby_x0": back_x - 16.0,
        "lobby_x1": 0.0,
        "lobby_half": col_span / 2.0 + c["lobby_margin"],
        "plaza_cx": street_x / 2.0,
        "corridor_len": corridor_len,
        "corridor_half": ch,
        "corridor_wall_y": wall_y,         # centre line of the corridor walls
        "island_y": wall_y + 4.0 + c["corridor_margin"],
        "arena_x": arena_x,
        "arena_r": arena_r,
        # Where the straight corridor walls meet the arena ring.
        "ring_x": arena_x - math.sqrt(arena_r ** 2 - wall_y ** 2),
    }


def biome_segments(L):
    """Corridor split into contiguous [x0, x1, biome] zones, from the lobby east."""
    segments = []
    x = 0.0
    for i, biome in enumerate(BIOMES):
        end = x + CONFIG["zone_len"] if i < len(BIOMES) - 1 else L["corridor_len"]
        segments.append((x, end, biome))
        x = end
    return segments


def section_name(index, biome):
    return "Zone%d_%s" % (index, biome["name"])


def capsule_area(L, index, x0, x1):
    """Rectangle (Blender XY) where world capsules may spawn in a zone: the
    middle lane of the corridor, clear of lamps and props."""
    lane = CONFIG["corridor_half"] - 24.0
    if index == len(BIOMES):
        return (x0 + 20.0, -lane, L["ring_x"] - 12.0, lane)
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
    elif kind == "desert":
        add_step_pyramid(mb, pal, x, y, 42.0 if north else 32.0, 5 if north else 4, 6.0, solid=False)


# ---------------------------------------------------------------- MONUMENTS


def add_kaiju_statue(mb, pal, f, z0, k=1.0):
    """The giant kaiju the lobby is built around: blocky, dark stone, gold claws,
    glowing eyes and dorsal spikes. Faces the frame's front; tail behind."""
    body, dark, gold = pal["statue"], pal["statue_dark"], pal["gold"]

    def part(lx, ly, z, sx, sy, sz, mat):
        mb.box(f.p(lx * k, ly * k, z0 + z * k), (sx * k, sy * k, sz * k), mat, rot_z=f.r)

    for side in (-1, 1):
        part(side * 6.5, -1.0, 1.5, 9, 12, 3, dark)                 # foot
        for toe in (-3.0, 0.0, 3.0):
            part(side * 6.5 + toe, -7.5, 1.2, 2, 2, 2.4, gold)      # toe claws
        part(side * 6.5, 1.0, 9.0, 7.5, 8.5, 12, body)              # shin
        part(side * 7.0, 2.0, 17.0, 9, 11, 8, body)                 # thigh
    part(0, 2.0, 22.0, 18, 15, 8, body)                             # hips
    part(0, 0.5, 31.0, 17, 14, 12, body)                            # belly
    part(0, -6.8, 30.0, 11, 1.0, 14, dark)                          # belly plates
    for z in (25.0, 29.0, 33.0):
        part(0, -7.5, z, 9, 0.6, 0.8, gold)
    part(0, -1.0, 41.0, 15, 13, 10, body)                           # chest
    for side in (-1, 1):
        part(side * 9.5, -3.0, 38.0, 4.5, 6, 5, body)               # upper arm
        part(side * 10.0, -7.0, 34.5, 4, 6, 4, body)                # forearm
        for claw in (-1.2, 0.0, 1.2):
            part(side * 10.0 + claw, -10.5, 33.5, 0.9, 2, 0.9, gold)
    part(0, -3.0, 48.5, 10, 10, 6, body)                            # neck
    part(0, -8.0, 54.0, 13, 15, 9, body)                            # skull
    part(0, -13.0, 49.8, 11, 9, 3, dark)                            # lower jaw
    for tooth in (-4.0, -2.0, 0.0, 2.0, 4.0):
        part(tooth, -16.5, 51.8, 1.0, 0.8, 1.6, pal["white"])
    part(0, -15.2, 55.5, 11, 3, 3, body)                            # snout
    for side in (-1, 1):
        part(side * 4.2, -15.6, 57.6, 2.6, 1.0, 1.4, pal["lava_glow"])   # eyes
        part(side * 5.0, -4.0, 60.5, 2.2, 2.2, 5.0, dark)                # horns
        part(side * 5.6, -5.5, 63.5, 1.6, 1.6, 3.0, gold)
    for ly, z, h in ((0.0, 60.0, 6.0), (4.0, 50.0, 8.0), (6.0, 42.0, 9.0),
                     (7.0, 34.0, 8.0), (8.0, 26.0, 6.0)):
        mb.cylinder(f.p(0, ly * k, z0 + (z + h / 2.0) * k), 2.2 * k, h * k, pal["glow_cyan"],
                    segments=5, taper=0.1)
    for ly, z, s in ((12.0, 22.0, 11.0), (19.0, 17.0, 9.0), (26.0, 12.0, 7.5),
                     (32.0, 8.0, 6.0), (37.0, 5.0, 4.5), (41.0, 3.5, 3.0)):
        part(0, ly, z, s, 7.5, s * 0.8, body)                       # tail
        mb.cylinder(f.p(0, ly * k, z0 + (z + s * 0.4 + 1.2) * k), 1.1 * k, 2.4 * k,
                    pal["glow_cyan"], segments=5, taper=0.1)
    # One box keeps players out of the legs and body.
    mb.collider("box", f.p(0, 1.0 * k, z0 + 27.0 * k), (20.0 * k, 18.0 * k, 54.0 * k), f.r)


def add_kaiju_head(mb, pal, f, z0, k=1.0):
    """Gargoyle head for the gate towers."""
    def part(lx, ly, z, sx, sy, sz, mat):
        mb.box(f.p(lx * k, ly * k, z0 + z * k), (sx * k, sy * k, sz * k), mat, rot_z=f.r)
    part(0, 0, 4.0, 12, 13, 8, pal["statue"])
    part(0, -6.5, 1.5, 10, 6, 3, pal["statue_dark"])
    part(0, -8.0, 5.0, 10, 3, 3, pal["statue"])
    for side in (-1, 1):
        part(side * 3.6, -8.2, 6.8, 2.4, 0.8, 1.2, pal["lava_glow"])
        part(side * 4.5, 2.0, 10.0, 2.0, 2.0, 5.0, pal["statue_dark"])
        part(side * 5.0, 1.0, 13.0, 1.4, 1.4, 2.4, pal["gold"])
    for tooth in (-3.0, -1.0, 1.0, 3.0):
        part(tooth, -9.4, 2.9, 0.9, 0.8, 1.4, pal["white"])


def add_tower(mb, pal, x, y, radius=10.0, height=46.0, banner=None):
    """Round corner tower: marble shaft, gold band, crenellations, cone roof."""
    mb.cylinder((x, y, height / 2.0), radius, height, pal["marble"], segments=10, solid=True)
    mb.cylinder((x, y, 2.0), radius + 1.2, 4.0, pal["marble_dark"], segments=10)
    mb.cylinder((x, y, height * 0.6), radius + 0.4, 1.4, pal["gold"], segments=10)
    for i in range(10):
        a = 2 * math.pi * i / 10
        mb.box((x + math.cos(a) * (radius - 0.6), y + math.sin(a) * (radius - 0.6), height + 1.6),
               (3.0, 2.2, 3.2), pal["marble_dark"], rot_z=a + math.pi / 2)
    mb.cylinder((x, y, height + 8.0), radius + 1.0, 14.0, pal["roof"], segments=10, taper=0.05)
    mb.sphere((x, y, height + 16.5), 1.8, pal["glow_gold"], rings=4, segments=8)
    for i in range(4):   # slit windows
        a = math.pi / 4 + i * math.pi / 2
        mb.box((x + math.cos(a) * radius, y + math.sin(a) * radius, height * 0.78),
               (1.6, 1.6, 5.0), pal["glow_gold"], rot_z=a)
    if banner:
        a = math.atan2(-y, -x) if (x or y) else 0.0
        bx, by = x + math.cos(a) * (radius + 0.6), y + math.sin(a) * (radius + 0.6)
        mb.box((bx, by, height * 0.36), (5.0, 0.6, 14.0), pal[banner], rot_z=a + math.pi / 2)
        mb.box((bx, by, height * 0.36 + 7.4), (6.0, 0.9, 0.9), pal["gold"], rot_z=a + math.pi / 2)


def add_brazier(mb, pal, x, y):
    mb.cylinder((x, y, 1.0), 3.0, 2.0, pal["marble_dark"], segments=8, solid=True)
    mb.cylinder((x, y, 4.0), 1.0, 4.0, pal["stone_dark"], segments=6)
    mb.cylinder((x, y, 6.6), 2.8, 1.4, pal["gold"], segments=8, taper=1.2)
    mb.cylinder((x, y, 8.6), 2.0, 3.0, pal["lava_glow"], segments=6, taper=0.2)
    mb.cylinder((x, y, 10.0), 1.0, 3.0, pal["glow_gold"], segments=5, taper=0.1)


def add_planter_tree(mb, pal, x, y, rng):
    mb.box((x, y, 0.9), (7.0, 7.0, 1.8), pal["marble_dark"], solid=True)
    mb.box((x, y, 1.9), (6.0, 6.0, 0.3), pal["dirt_dark"])
    add_tree(mb, pal, x, y, rng, solid=True)


def add_floating_crystal(mb, pal, x, y, z, size, mat):
    mb.frustum((x, y), z + size * 1.6, z, (0.3, 0.3), (size, size), mat)
    mb.frustum((x, y), z, z - size * 1.2, (size, size), (0.3, 0.3), mat)


def add_shop(mb, pal, f, stripe, display):
    """Shop building facing the frame's front: shop body, gable roof, counter,
    striped awning, roof sign and wares on the counter.
    Returns (main sign text position, awning text position)."""
    mb.box(f.p(0, 6.0, 9.0), (34.0, 16.0, 18.0), pal["house"], rot_z=f.r, solid=True)
    mb.roof(f.p(0, 6.0, 21.5), (37.0, 19.0, 7.0), pal["roof"], rot_z=f.r)
    for lx in (-17.2, 17.2):
        mb.box(f.p(lx, 6.0, 9.0), (1.4, 16.4, 18.0), pal["wood"], rot_z=f.r)
    mb.box(f.p(0, -2.2, 8.0), (10.0, 0.6, 12.0), pal["board"], rot_z=f.r)        # door way
    mb.box(f.p(0, -6.0, 2.6), (28.0, 5.0, 5.2), pal["wood"], rot_z=f.r, solid=True)
    mb.box(f.p(0, -6.0, 5.5), (29.0, 6.0, 0.6), pal["wood_light"], rot_z=f.r)
    for lx in (-15.5, 15.5):
        mb.box(f.p(lx, -10.0, 7.0), (1.2, 1.2, 14.0), pal["wood_light"], rot_z=f.r)
    n = 8
    for i in range(n):
        lx = -17.0 + 34.0 / n * (i + 0.5)
        mb.box(f.p(lx, -6.0, 14.2), (34.0 / n, 10.0, 1.2),
               stripe if i % 2 == 0 else pal["white"], rot_z=f.r)
    mb.box(f.p(0, -11.2, 12.6), (35.0, 0.8, 3.6), stripe, rot_z=f.r)            # awning board
    mb.box(f.p(0, -3.0, 27.0), (30.0, 1.0, 7.0), pal["board"], rot_z=f.r)       # roof sign
    mb.box(f.p(0, -2.6, 27.0), (31.6, 0.8, 8.6), pal["gold"], rot_z=f.r)
    for lx in (-8.0, 0.0, 8.0):
        if display == "capsules":
            mb.cylinder(f.p(lx, -6.0, 6.3), 1.4, 1.0, pal["metal_mid"], segments=8)
            mb.sphere(f.p(lx, -6.0, 8.2), 1.5, pal[("rarity_rare", "rarity_epic", "rarity_legendary")
                                                     [int(lx / 8.0) + 1]])
        else:   # speed: glowing boots and bolts
            mb.box(f.p(lx - 1.0, -6.0, 6.8), (1.6, 3.2, 2.0), pal["glow_cyan"], rot_z=f.r)
            mb.box(f.p(lx + 1.0, -6.0, 6.8), (1.6, 3.2, 2.0), pal["glow_cyan"], rot_z=f.r)
            mb.box(f.p(lx, -6.0, 9.4), (0.8, 0.8, 3.0), pal["glow_gold"], rot_z=f.r + 0.5)
    for lx in (-20.0, 20.0):
        add_lamp(mb, pal, *f.p(lx, -12.0)[:2], glow=pal["glow_gold"])
    return f.p(0, -3.8, 27.0), f.p(0, -11.9, 12.6)


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
    add("title", "KAIJU HEIST", "glow_gold", 9.0, 0.8)
    add("classement", "CLASSEMENT", "glow_gold", 5.0, 0.4)
    add("rarities", "RARETES", "glow_gold", 3.6, 0.3)
    add("cadeau", "CADEAU DU JOUR", "glow_gold", 3.0, 0.3)
    add("tuto_title", "COMMENT JOUER", "glow_gold", 2.8, 0.25)
    for i, line in enumerate(("1  RAMASSE DES CAPSULES", "2  FAIS-LES ECLORE",
                              "3  GAGNE DE L'ICHOR", "4  VOLE LES AUTRES"), start=1):
        add("tuto_%d" % i, line, "text_decal", 2.0, 0.15)
    for i in (1, 2, 3):
        add("place_%d" % i, str(i), "glow_gold", 5.0, 0.3)
    add("shop_title", "BOUTIQUE", "glow_gold", 4.4, 0.4)
    add("shop_sub", "VENTE", "text_decal", 2.4, 0.2)
    add("speed_title", "VITESSE", "glow_cyan", 4.4, 0.4)
    add("speed_sub", "BOUTIQUE", "text_decal", 2.4, 0.2)
    add("portal_base", "MA BASE", "text_decal", 2.4, 0.2)
    add("portal_lobby", "LOBBY", "text_decal", 2.4, 0.2)
    for b in BIOMES:
        add("portal_" + b["id"], b["portal"], "text_decal", 2.4, 0.2)
        add("gate_" + b["id"], b["sign"], "text_decal", 4.2, 0.4)
    return t


def build_lobby(world, pal, L, texts):
    """The bar of the T: a huge marble plaza around a giant kaiju statue, with
    the player bases on its west side, portals, leaderboard, rarity showcase,
    daily reward, tutorial, two shops and the monumental gate of the corridor."""
    sec = world.section("Lobby")
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 300)
    x0, x1, H = L["lobby_x0"], L["lobby_x1"], L["lobby_half"]
    sx, pcx = L["street_x"], L["plaza_cx"]
    ch, wy = L["corridor_half"], L["corridor_wall_y"]
    rim = 10.0
    edge = H - rim

    # Island, grass, rims (no east rim: the corridor island continues there).
    add_floating_body(mb, pal, x0, -H, x1, H, 70.0, 110.0, rng, rocks=24)
    mb.checker(x0 + rim, -edge, x1, edge, 0.0, CONFIG["tile"], pal["grass_a"], pal["grass_b"])
    add_rims(mb, pal["grass_rim"], x0, -H, x1, H, rim, east=False)
    mb.collider("box", ((x0 + x1) / 2.0, 0.0, -2.0), (x1 - x0, 2 * H, 4.0), kind="ground",
                material="Grass")

    # Marble plaza with gold borders, crossed by two stone avenues.
    px0, px1, py = sx + 6.0, x1 - 6.0, edge - 6.0
    mb.checker(px0, -py, px1, py, 0.05, 12.0, pal["marble"], pal["marble_dark"])
    mb.collider("box", ((px0 + px1) / 2.0, 0.0, -0.45), (px1 - px0, 2 * py, 1.0), kind="ground",
                material="Marble")
    for s in (-1, 1):
        mb.box(((px0 + px1) / 2.0, s * (py + 0.8), 0.2), (px1 - px0 + 3.2, 1.6, 0.4), pal["gold"])
    mb.box((px0 - 0.8, 0.0, 0.2), (1.6, 2 * py, 0.4), pal["gold"])
    mb.checker(px0, -22.0, px1, 22.0, 0.09, 8.0, pal["stone"], pal["stone_dark"])
    mb.checker(pcx - 22.0, -py, pcx + 22.0, py, 0.14, 8.0, pal["stone"], pal["stone_dark"])
    for s in (-1, 1):
        mb.box(((px0 + px1) / 2.0, s * 22.8, 0.2), (px1 - px0, 1.6, 0.3), pal["gold"])
        mb.box((pcx + s * 22.8, 0.0, 0.25), (1.6, 2 * py, 0.3), pal["gold"])
    keep_out(px0 - 6, -28, px1 + 6, 28)
    keep_out(pcx - 28, -py, pcx + 28, py)
    keep_out(sx - 2, -L["col_span"] / 2.0, sx + 18, L["col_span"] / 2.0)   # base fronts

    # Centre piece: medallion, reflecting pool, fountain jets, tiered pedestal, statue.
    mb.cylinder((pcx, 0.0, 0.2), 52.0, 0.4, pal["marble_dark"], segments=24)
    mb.cylinder((pcx, 0.0, 0.3), 50.0, 0.4, pal["gold"], segments=24)
    mb.cylinder((pcx, 0.0, 1.2), 46.0, 2.4, pal["stone"], segments=24, solid=True)
    mb.cylinder((pcx, 0.0, 2.3), 46.6, 0.5, pal["gold"], segments=24)
    mb.cylinder((pcx, 0.0, 2.35), 43.5, 0.5, pal["water"], segments=24)
    for i in range(8):
        a = 2 * math.pi * i / 8 + math.pi / 8
        jx, jy = pcx + math.cos(a) * 36.0, math.sin(a) * 36.0
        mb.cylinder((jx, jy, 7.0), 0.7, 9.0, pal["glow_cyan"], segments=6, taper=0.4)
        mb.sphere((jx, jy, 11.8), 1.3, pal["glow_cyan"], rings=4, segments=8)
    mb.cylinder((pcx, 0.0, 4.4), 24.0, 4.0, pal["stone_dark"], segments=16, solid=True)
    mb.cylinder((pcx, 0.0, 6.5), 24.4, 0.6, pal["gold"], segments=16)
    mb.cylinder((pcx, 0.0, 8.4), 19.0, 4.0, pal["marble"], segments=16, solid=True)
    mb.cylinder((pcx, 0.0, 11.9), 14.0, 3.0, pal["marble_dark"], segments=16, solid=True)
    for i in range(16):
        a = 2 * math.pi * i / 16
        mb.box((pcx + math.cos(a) * 19.2, math.sin(a) * 19.2, 9.0), (1.2, 2.2, 2.2),
               pal["glow_violet"], rot_z=a)
    k = CONFIG["statue_scale"]
    add_kaiju_statue(mb, pal, Frame(pcx, 0.0, math.pi / 2.0), 13.4, k)
    keep_out_around(pcx, 0.0, 82.0)
    for i in range(6):
        a = 2 * math.pi * i / 6 + 0.3
        add_floating_crystal(mb, pal, pcx + math.cos(a) * 58.0, math.sin(a) * 58.0,
                             78.0 + 12.0 * (i % 3), 6.0, pal["glow_violet"])

    # Spawn ring between the pool and the colonnade.
    spawns = []
    for i in range(8):
        a = math.radians(22.5 + 45.0 * i)
        px, py_ = pcx + math.cos(a) * 58.0, math.sin(a) * 58.0
        mb.cylinder((px, py_, 0.3), 5.0, 0.5, pal["marble_dark"], segments=12)
        mb.cylinder((px, py_, 0.35), 3.6, 0.52, pal["glow_cyan"], segments=12)
        spawns.append((px, py_, 0.05))

    # Colonnade ring with lintels, open where the avenues cross it.
    radius, pillars = 72.0, {}
    for i in range(16):
        if i % 4 == 0:
            continue
        a = 2 * math.pi * i / 16
        cx_, cy_ = pcx + math.cos(a) * radius, math.sin(a) * radius
        pillars[i] = a
        mb.box((cx_, cy_, 1.0), (7.0, 7.0, 2.0), pal["marble_dark"], rot_z=a)
        mb.cylinder((cx_, cy_, 17.0), 2.6, 30.0, pal["marble"], segments=10, solid=True)
        mb.box((cx_, cy_, 33.1), (7.0, 7.0, 2.2), pal["gold"], rot_z=a)
        mb.sphere((cx_, cy_, 36.2), 2.0, pal["glow_violet"], rings=4, segments=8)
    chord = 2 * radius * math.sin(math.pi / 16)
    for i in range(16):
        if i in pillars and (i + 1) % 16 in pillars:
            am = 2 * math.pi * (i + 0.5) / 16
            rm = radius * math.cos(math.pi / 16)
            mb.box((pcx + math.cos(am) * rm, math.sin(am) * rm, 34.6), (chord + 7.0, 3.6, 1.6),
                   pal["stone_dark"], rot_z=am + math.pi / 2)

    # North wing: gallery of portals, one per zone plus MA BASE.
    portals = []
    targets = [("base", "portal_base", "base", "glow_pink", "MA BASE")]
    targets += [(b["id"], "portal_" + b["id"], "zone:" + b["id"], b["glow"], b["portal"])
                for b in BIOMES]
    gy = 170.0
    gw = 30.0 * len(targets) + 20.0
    mb.box((pcx, gy, 11.0), (gw, 4.0, 22.0), pal["marble"], solid=True)
    mb.box((pcx, gy, 22.8), (gw + 4.0, 6.0, 1.6), pal["stone_dark"])
    mb.box((pcx, gy, 24.2), (gw + 5.0, 6.6, 1.2), pal["gold"])
    for i in range(len(targets) + 1):
        mb.box((pcx - gw / 2.0 + 2.0 + i * (gw - 4.0) / len(targets), gy - 2.6, 12.0),
               (3.6, 1.6, 24.0), pal["marble_dark"])
    for k_, (pid, text_key, target, glow, label) in enumerate(targets):
        f = Frame(pcx + 30.0 * (k_ - (len(targets) - 1) / 2.0), gy - 20.0, 0.0)
        trigger, label_pos = add_portal(mb, pal, f, glow)
        mb.box((f.x, gy - 2.4, 13.0), (7.0, 0.6, 16.0), pal[glow])          # banner
        mb.box((f.x, gy - 2.7, 21.4), (8.4, 1.0, 1.0), pal["gold"])
        sec.text(texts[text_key], "Lobby_PortalText_" + pid, label_pos, upright(f.r))
        portals.append(dict(trigger, id="lobby_" + pid, label=label, target=target))
    keep_out(pcx - gw / 2.0 - 6, gy - 32, pcx + gw / 2.0 + 6, gy + 6)

    # Rarity showcase: giant capsule eggs behind the gallery.
    showcase = []
    ey = 238.0
    for i, (rarity, key) in enumerate(RARITIES):
        ex = pcx + 42.0 * (i - (len(RARITIES) - 1) / 2.0)
        mb.cylinder((ex, ey, 3.0), 6.0, 6.0, pal["marble"], segments=12, solid=True)
        mb.cylinder((ex, ey, 6.2), 6.6, 0.6, pal["gold"], segments=12)
        mb.cylinder((ex, ey, 7.2), 2.2, 1.6, pal["metal_mid"], segments=8)
        mb.sphere((ex, ey, 12.0), 5.0, pal[key], rings=6, segments=12)
        mb.sphere((ex, ey, 15.8), 3.8, pal[key], rings=5, segments=10)
        showcase.append({"rarity": rarity, "position": (ex, ey, 12.0)})
    fb = Frame(pcx, ey + 16.0, math.pi)
    for lx in (-46.0, 46.0):
        mb.box(fb.p(lx, 0, 9.0), (2.0, 2.0, 18.0), pal["wood"], rot_z=fb.r, solid=True)
    mb.box(fb.p(0, 0, 16.0), (96.0, 1.2, 6.0), pal["board"], rot_z=fb.r)
    mb.box(fb.p(0, 0.2, 16.0), (98.0, 1.0, 7.4), pal["gold"], rot_z=fb.r)
    sec.text(texts["rarities"], "Lobby_Text_Raretes", fb.p(0, -0.9, 16.0), upright(fb.r))
    keep_out(pcx - 110, ey - 10, pcx + 110, ey + 20)

    # South wing: giant leaderboard and podium, tutorial board, daily reward.
    f = Frame(pcx, -200.0, math.pi)
    for lx in (-30.0, 30.0):
        mb.box(f.p(lx, 0.8, 20.0), (3.0, 3.0, 40.0), pal["wood"], rot_z=f.r, solid=True)
    mb.box(f.p(0, 0, 21.0), (64.0, 2.0, 34.0), pal["gold"], rot_z=f.r, solid=True)
    mb.box(f.p(0, -0.8, 21.0), (60.0, 1.0, 30.0), pal["board"], rot_z=f.r)
    mb.box(f.p(0, 0, 42.0), (40.0, 1.6, 7.0), pal["board"], rot_z=f.r)
    sec.text(texts["classement"], "Lobby_Text_Classement", f.p(0, -1.2, 42.0), upright(f.r))
    leaderboard = {"position": f.p(0, -1.3, 21.0), "width": 60.0, "height": 30.0,
                   "yaw": facing_yaw(*f.front())}
    for place, lx, h in ((2, -15.0, 7.0), (1, 0.0, 10.0), (3, 15.0, 5.0)):
        mb.box(f.p(lx, -22.0, h / 2.0), (13.0, 13.0, h), pal["marble"], rot_z=f.r, solid=True)
        mb.box(f.p(lx, -22.0, h + 0.2), (13.6, 13.6, 0.4), pal["gold"], rot_z=f.r)
        sec.text(texts["place_%d" % place], "Lobby_Text_Place%d" % place,
                 f.p(lx, -28.8, h / 2.0), upright(f.r))
    keep_out(pcx - 40, -212, pcx + 40, -168)

    tuto = Frame(pcx - 100.0, -150.0, math.pi)
    for lx in (-16.0, 16.0):
        mb.box(tuto.p(lx, 0.8, 12.0), (1.8, 1.8, 24.0), pal["wood"], rot_z=tuto.r, solid=True)
    mb.box(tuto.p(0, 0, 14.0), (34.0, 1.2, 20.0), pal["board"], rot_z=tuto.r, solid=True)
    mb.box(tuto.p(0, 0.2, 14.0), (35.6, 1.0, 21.6), pal["wood_light"], rot_z=tuto.r)
    sec.text(texts["tuto_title"], "Lobby_Text_Tuto", tuto.p(0, -0.8, 21.0), upright(tuto.r))
    for i in range(1, 5):
        sec.text(texts["tuto_%d" % i], "Lobby_Text_Tuto%d" % i,
                 tuto.p(0, -0.8, 21.0 - 3.8 * i), upright(tuto.r))
    keep_out(tuto.x - 22, tuto.y - 8, tuto.x + 22, tuto.y + 6)

    chest = Frame(pcx + 100.0, -150.0, math.pi)
    mb.cylinder(chest.p(0, 0, 0.2), 11.0, 0.3, pal["glow_gold"], segments=16)
    mb.cylinder(chest.p(0, 0, 0.9), 9.5, 1.4, pal["marble_dark"], segments=16, solid=True)
    mb.box(chest.p(0, 0, 5.5), (14.0, 9.0, 8.0), pal["wood"], rot_z=chest.r, solid=True)
    mb.roof(chest.p(0, 0, 10.8), (14.4, 9.4, 2.8), pal["wood_light"], rot_z=chest.r)
    for lx in (-4.5, 4.5):
        mb.box(chest.p(lx, 0, 6.8), (1.4, 9.4, 10.6), pal["gold"], rot_z=chest.r)
    mb.box(chest.p(0, -4.7, 7.2), (2.4, 0.8, 3.0), pal["gold"], rot_z=chest.r)
    for i in range(6):
        a = 2 * math.pi * i / 6
        mb.sphere(chest.p(math.cos(a) * 8.0, math.sin(a) * 8.0, 2.4), 1.0, pal["glow_gold"],
                  rings=3, segments=6)
    sec.text(texts["cadeau"], "Lobby_Text_Cadeau", chest.p(0, 0, 17.0), upright(chest.r))
    keep_out(chest.x - 14, chest.y - 14, chest.x + 14, chest.y + 14)

    # The two shops flanking the corridor mouth, as on the plan.
    shops = {}
    for key, sy, stripe, display, title, sub in (
            ("shop", 1, pal["yellow"], "capsules", "shop_title", "shop_sub"),
            ("speedShop", -1, pal["blue"], "speed", "speed_title", "speed_sub")):
        f = Frame(-40.0, sy * (wy + 44.0), 0.0 if sy > 0 else math.pi)
        main_pos, sub_pos = add_shop(mb, pal, f, stripe, display)
        sec.text(texts[title], "Lobby_Text_" + title, main_pos, upright(f.r))
        sec.text(texts[sub], "Lobby_Text_" + sub, sub_pos, upright(f.r))
        shops[key] = {"position": f.p(0, -9.0, 0.0), "yaw": facing_yaw(*f.front())}
        keep_out(f.x - 26, f.y - 20, f.x + 26, f.y + 20)

    # Monumental gate over the corridor mouth, with kaiju gargoyles.
    ty = wy + 12.0
    for s in (-1, 1):
        mb.box((0.0, s * ty, 33.0), (22.0, 22.0, 66.0), pal["marble"], solid=True)
        for z in (1.5, 22.0, 46.0):
            mb.box((0.0, s * ty, z), (23.4, 23.4, 1.6 if z > 2 else 3.0), pal["gold"])
        mb.box((0.0, s * ty, 67.5), (26.0, 26.0, 3.0), pal["stone_dark"])
        mb.box((-11.2, s * ty, 36.0), (0.8, 8.0, 18.0), pal[BIOMES[0]["glow"]])
        add_kaiju_head(mb, pal, Frame(0.0, s * ty, -math.pi / 2.0), 69.0, 1.3)
    mb.box((0.0, 0.0, 59.0), (16.0, 2 * ty, 12.0), pal["marble"])
    mb.box((0.0, 0.0, 52.6), (16.8, 2 * ty, 1.0), pal["gold"])
    mb.box((0.0, 0.0, 52.0), (5.0, 2 * wy, 1.0), pal["glow_violet"])
    mb.box((0.0, 0.0, 69.0), (10.0, 60.0, 8.0), pal["marble_dark"])
    mb.sphere((0.0, 0.0, 76.5), 3.2, pal["glow_violet"], rings=5, segments=10)
    sec.text(texts["title"], "Lobby_Text_Title", (-8.6, 0.0, 59.0), upright(-math.pi / 2.0))
    mb.box((-8.0, 0.0, 47.5), (3.0, 72.0, 6.0), pal["stone_dark"])
    sec.text(texts["gate_" + BIOMES[0]["id"]], "Lobby_GateText", (-9.9, 0.0, 47.5),
             upright(-math.pi / 2.0))
    mb.box((-4.0, 0.0, 0.2), (2.0, 2 * ch, 0.3), pal[BIOMES[0]["glow"]])
    keep_out(-40, -ty - 14, 1, ty + 14)

    # Corner towers, braziers, balustrades, lamps.
    for tx, ty_, banner in ((x0 + 14.0, edge - 4.0, "glow_violet"), (x0 + 14.0, -edge + 4.0, "glow_violet"),
                            (x1 - 14.0, edge - 4.0, "glow_gold"), (x1 - 14.0, -edge + 4.0, "glow_gold")):
        add_tower(mb, pal, tx, ty_, banner=banner)
        keep_out_around(tx, ty_, 14.0)
    for bx, by in ((px0 + 14.0, 34.0), (px0 + 14.0, -34.0), (-26.0, 34.0), (-26.0, -34.0),
                   (pcx - 34.0, py - 12.0), (pcx + 34.0, py - 12.0),
                   (pcx - 34.0, -py + 12.0), (pcx + 34.0, -py + 12.0)):
        add_brazier(mb, pal, bx, by)
        keep_out_around(bx, by, 5.0)
    for s in (-1, 1):
        yb = s * (edge - 1.0)
        mb.box(((x0 + rim + 24.0 + x1 - 24.0) / 2.0, yb, 1.4), (x1 - x0 - rim - 48.0, 1.6, 2.8),
               pal["marble"], solid=True)
        for i in range(int((x1 - x0 - rim - 48.0) // 12.0) + 1):
            mb.box((x0 + rim + 24.0 + i * 12.0, yb, 1.8), (2.4, 2.4, 3.6), pal["marble_dark"])
            mb.sphere((x0 + rim + 24.0 + i * 12.0, yb, 4.2), 0.9, pal["gold"], rings=3, segments=6)
        ya, yb2 = s * (ty + 12.0), s * (edge - 24.0)
        mb.box((x1 - 1.0, (ya + yb2) / 2.0, 1.4), (1.6, abs(yb2 - ya), 2.8), pal["marble"], solid=True)
    for x in range(int(px0) + 20, int(px1) - 10, 34):
        if abs(x - pcx) < 88.0:
            continue
        for s in (-1, 1):
            add_lamp(mb, pal, float(x), s * 30.0, glow=pal["glow_gold"])
            keep_out_around(float(x), s * 30.0, 3.5)
    for y in range(90, int(py) - 10, 34):
        for s in (-1, 1):
            for lx in (-30.0, 30.0):
                if is_free(pcx + lx, s * y, 3.5):
                    add_lamp(mb, pal, pcx + lx, s * float(y), glow=pal["glow_violet"])
                    keep_out_around(pcx + lx, s * float(y), 3.5)

    # Gardens: trees in marble planters and flower beds across the free plaza.
    for x, y in scatter(rng, 34, lambda r: (r.uniform(px0 + 8, px1 - 8), r.uniform(-py + 8, py - 8)),
                        7.0):
        if rng.random() < 0.65:
            add_planter_tree(mb, pal, x, y, rng)
        else:
            mb.box((x, y, 0.5), (8.0, 5.0, 1.0), pal["marble_dark"])
            add_flowers(mb, pal, x, y, rng)

    sec.emit(mb, "Lobby")

    # Invisible walls: lobby edges, and the lobby's east edge around the corridor.
    barrier("Lobby", x0, H + 1.0, x1, H + 1.0)
    barrier("Lobby", x0, -H - 1.0, x1, -H - 1.0)
    barrier("Lobby", x0 - 1.0, -H, x0 - 1.0, H)
    barrier("Lobby", x1 + 1.0, wy, x1 + 1.0, H)
    barrier("Lobby", x1 + 1.0, -H, x1 + 1.0, -wy)

    return {
        "center": (pcx, 0.0, 0.05),
        "bounds": ((x0, -H, 0.0), (x1, H, 0.0)),
        "spawns": spawns,
        "spawnYaw": facing_yaw(1.0, 0.0),
        "portals": portals,
        "leaderboard": leaderboard,
        "showcase": showcase,
        "shop": shops["shop"],
        "speedShop": shops["speedShop"],
        "dailyReward": chest.p(0, 0, 0.0),
        "statue": (pcx, 0.0, 13.4),
        "tutorialBoard": {"position": tuto.p(0, -0.7, 14.0), "width": 34.0, "height": 20.0,
                          "yaw": facing_yaw(*tuto.front())},
    }


def build_island_base(world, pal, L):
    sec = world.section("Island")
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] + 99)
    add_floating_body(mb, pal, 0.0, -L["island_y"], L["corridor_len"], L["island_y"],
                      CONFIG["dirt_depth"], CONFIG["taper_depth"], rng, rocks=26)
    sec.emit(mb, "Island_Body")


def build_zone(world, pal, L, index, x0, x1, biome, texts):
    """One corridor zone: ground, the two corridor walls, lamps and props along
    them, the gate with the zone's name, landmarks behind the walls - and for
    the last zone, the boss arena."""
    sec = world.section(section_name(index, biome))
    mb = MeshBuilder()
    rng = random.Random(CONFIG["seed"] * 31 + index)
    ch, wy, iy, rim = L["corridor_half"], L["corridor_wall_y"], L["island_y"], 10.0
    h = CONFIG["corridor_wall_height"]
    is_last = index == len(BIOMES)
    wall_a, wall_b = pal[biome["wall"][0]], pal[biome["wall"][1]]

    # Ground and rims.
    a, b = biome["floor"]
    tile = CONFIG["tile"] * (1.6 if biome["decor"] == "desert" else 1.0)
    mb.checker(x0, -iy + rim, x1 - rim if is_last else x1, iy - rim, 0.0, tile, pal[a], pal[b])
    add_rims(mb, pal[biome["rim"]], x0, -iy, x1, iy, rim, west=False, east=is_last)
    mb.collider("box", ((x0 + x1) / 2.0, 0.0, -2.0), (x1 - x0, 2 * iy, 4.0),
                kind="ground", material=biome["ground"])

    # Corridor walls (in the last zone they stop where the arena ring starts).
    wall_end = L["ring_x"] + 6.0 if is_last else x1
    wl, wm = wall_end - x0, (x0 + wall_end) / 2.0
    for s in (1, -1):
        mb.box((wm, s * wy, h / 2.0), (wl, 8.0, h), wall_a, solid=True)
        mb.box((wm, s * wy, h + 1.0), (wl, 9.6, 2.0), pal[biome["cap"]])
        mb.checker_xz(s * (wy - 4.2), x0, 0.0, wall_end, h, CONFIG["tile"], wall_a, wall_b,
                      facing=-s)
        mb.checker_xz(s * (wy + 4.2), x0, 0.0, wall_end, h, CONFIG["tile"], wall_b, wall_a,
                      facing=s)
        mb.box((wm, s * (ch - 0.4), 0.1), (wl, 0.8, 0.2), pal[biome["glow"]])

    # Gate with the zone name (zone 1's gate is the lobby's monumental gate).
    if index > 1:
        for s in (1, -1):
            mb.box((x0, s * wy, 20.0), (14.0, 14.0, 40.0), wall_b, solid=True)
            mb.box((x0, s * wy, 40.8), (15.4, 15.4, 1.6), pal[biome["cap"]])
            mb.sphere((x0, s * wy, 43.4), 2.6, pal[biome["glow"]], rings=4, segments=8)
        mb.box((x0, 0.0, 36.0), (12.0, 2 * wy + 14.0, 6.0), wall_b)
        mb.box((x0, 0.0, 39.4), (12.6, 2 * wy + 15.0, 0.8), pal[biome["cap"]])
        mb.box((x0, 0.0, 32.6), (4.0, 2 * ch, 0.8), pal[biome["glow"]])
        mb.box((x0, 0.0, 0.08), (1.6, 2 * ch, 0.16), pal[biome["glow"]])
        sec.text(texts["gate_" + biome["id"]], sec.name + "_GateText", (x0 - 6.45, 0.0, 36.0),
                 upright(-math.pi / 2.0))

    # Lamps along the walls, props at the foot of the walls, scenery behind them.
    for x in range(int(x0) + 20, int(wall_end) - 10, 40):
        for s in (1, -1):
            add_lamp(mb, pal, float(x), s * (ch - 5.0), glow=pal[biome["glow"]])
            keep_out_around(float(x), s * (ch - 5.0), 4.0)
    for x, y in scatter(rng, biome["street_props"],
                        lambda r: (r.uniform(x0 + 12.0, wall_end - 12.0),
                                   r.choice((1, -1)) * r.uniform(ch - 16.0, ch - 9.0)), 4.0):
        add_biome_decor(mb, pal, biome, x, y, rng, solid=True)
    landmark_x = (x0 + x1) / 2.0 if not is_last else x0 + 48.0
    for s in (1, -1):
        keep_out_around(landmark_x, s * (wy + 34.0), 24.0)
        add_landmark(mb, pal, biome, landmark_x, s * (wy + 34.0), rng)
    mx1 = wall_end - 30.0 if is_last else x1 - 4.0
    for x, y in scatter(rng, biome["margin_props"],
                        lambda r: (r.uniform(x0 + 4.0, mx1),
                                   r.choice((1, -1)) * r.uniform(wy + 10.0, iy - rim - 4.0)), 4.0):
        add_biome_decor(mb, pal, biome, x, y, rng)

    return_portal = None
    if is_last:
        return_portal = build_arena(mb, pal, L, rng, sec, texts)

    sec.emit(mb, sec.name)
    if is_last:
        barrier(sec.name, x1 + 1.0, -iy, x1 + 1.0, iy)

    area = capsule_area(L, index, x0, x1)
    return {
        "biome": biome,
        "index": index,
        "section": sec.name,
        "bounds": ((x0, -iy, 0.0), (x1, iy, 0.0)),
        "spawn": (x0 + (30.0 if index == 1 else 18.0), 0.0, 0.0),
        "spawnYaw": facing_yaw(1.0, 0.0),
        "capsuleArea": ((area[0], area[1], 0.0), (area[2], area[3], 0.0)),
        "returnPortal": return_portal,
    }


def build_arena(mb, pal, L, rng, sec, texts):
    """Circular boss arena closing the corridor: ring wall, tribunes, altar."""
    ax, r = L["arena_x"], L["arena_r"]
    h = CONFIG["corridor_wall_height"]
    wy = L["corridor_wall_y"]
    mb.cylinder((ax, 0.0, 0.1), r - 4.0, 0.2, pal["stone_dark"], segments=32)
    mb.cylinder((ax, 0.0, 0.15), r - 10.0, 0.2, pal["sand_dark"], segments=32)
    mb.cylinder((ax, 0.0, 0.2), 60.0, 0.2, pal["stone"], segments=32)

    # Ring wall, open to the west where the corridor arrives.
    n = 16
    chord = 2 * r * math.sin(math.pi / n)
    for i in range(n):
        am = 2 * math.pi * (i + 0.5) / n
        if math.cos(am) < 0 and abs(math.sin(am)) * r < wy + 2.0:
            continue
        rm = r * math.cos(math.pi / n)
        cx_, cy_ = ax + math.cos(am) * rm, math.sin(am) * rm
        # Overlong on purpose: straight segments must overlap on the outside of the curve.
        mb.box((cx_, cy_, h / 2.0), (chord + 6.0, 8.0, h), pal["sand_dark"], rot_z=am + math.pi / 2,
               solid=True)
        mb.box((cx_, cy_, h + 1.0), (chord + 7.0, 9.6, 2.0), pal["sand"], rot_z=am + math.pi / 2)
        mb.box((ax + math.cos(am) * (rm - 4.2), math.sin(am) * (rm - 4.2), h * 0.6),
               (5.0, 0.6, 7.0), pal["glow_violet"], rot_z=am + math.pi / 2)
        # Tribunes behind the wall (scenery).
        for step in range(3):
            rr = rm + 8.0 + step * 6.0
            mb.box((ax + math.cos(am) * rr, math.sin(am) * rr, h * 0.45 + step * 5.0),
                   (chord + 6.0 + step * 4.0, 6.0, 4.0), pal["stone"] if step % 2 == 0
                   else pal["stone_dark"], rot_z=am + math.pi / 2)

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
        rr = rng.uniform(16, 52)
        mb.box((ax + math.cos(a) * rr, math.sin(a) * rr, rng.uniform(60, 130)),
               (rng.uniform(9, 22), rng.uniform(9, 22), rng.uniform(5, 12)),
               pal["stone_dark"], rot_z=rng.uniform(0, math.pi))
    keep_out_around(ax, 0.0, r)

    # Return portal to the lobby, against the east wall.
    f = Frame(ax + r - 20.0, 0.0, -math.pi / 2.0)
    trigger, label_pos = add_portal(mb, pal, f, "glow_violet")
    sec.text(texts["portal_lobby"], sec.name + "_PortalText", label_pos, upright(f.r))
    return dict(trigger, id="return_arena", label="LOBBY", target="lobby")


def build_plot_template(pal):
    """One base ("case"), in plot-local coordinates: x along the plaza edge, y
    the depth from it. Built once and instanced, so every player gets the exact
    same base."""
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
    """The bases ("enclos" on the plan), in a column along the lobby's west side,
    opening east onto the plaza, separated by marble walls."""
    sec = world.section("Plots")
    mb, local, signs = build_plot_template(pal)
    meshes = mb.make_meshes("PlotTemplate")
    d, hw = CONFIG["plot_depth"], CONFIG["plot_width"] / 2.0
    h, t = CONFIG["wall_height"], CONFIG["wall_thickness"]
    sx, bx = L["street_x"], L["back_x"]

    # Closest to the central avenue first: PlotService hands them out in this order.
    order = sorted(range(CONFIG["base_count"]),
                   key=lambda k: (abs(L["base_centers"][k]), -L["base_centers"][k]))
    anchors = []
    for rank, k in enumerate(order, start=1):
        cy = L["base_centers"][k]
        pid = "B%d" % rank
        f = Frame(sx, cy, math.pi / 2.0)   # local +y (depth) runs west, into the base
        name = "Plot_" + pid
        sec.place(meshes, name, f)
        register_colliders(mb, sec.name, f)
        sec.text(texts["zone_sure"], name + "_SafeZoneText", f.p(0.0, 14.0, 0.3), (0, 0, f.r))
        for key, pos in signs.items():
            sec.text(texts[key], "%s_Sign_%s" % (name, key.title()), f.p(pos[0], pos[1], pos[2]),
                     upright(f.r))
        entry = {"id": pid, "side": "west", "zone": "lobby"}
        for key in ("center", "entrance", "spawn", "machine", "sellStand", "shopStand",
                    "conveyor", "house", "sign"):
            p = local[key]
            entry[key] = f.p(p[0], p[1], p[2])
        entry["spawnYaw"] = facing_yaw(-1.0, 0.0)
        entry["pens"] = [f.p(p[0], p[1], p[2]) for p in local["pens"]]
        entry["bounds"] = ((sx - d, cy - hw, 0.0), (sx, cy + hw, h))
        anchors.append(entry)

    # Marble walls between the bases, and the back wall.
    wb = MeshBuilder()
    wall_a, wall_b, cap = pal["marble"], pal["marble_dark"], pal["gold"]
    xm = (sx + bx) / 2.0
    for wy_ in L["wall_centers"]:
        wb.box((xm, wy_, h / 2.0), (d, t, h), wall_a, solid=True)
        wb.box((xm, wy_, h + 1.0), (d + 1.5, t + 1.5, 2.0), cap)
        wb.checker_xz(wy_ - t / 2.0 - 0.2, bx, 0.0, sx, h, CONFIG["tile"], wall_a, wall_b, facing=-1)
        wb.checker_xz(wy_ + t / 2.0 + 0.2, bx, 0.0, sx, h, CONFIG["tile"], wall_b, wall_a, facing=1)
        wb.checker_yz(sx + 0.2, wy_ - t / 2.0, 0.0, wy_ + t / 2.0, h, CONFIG["tile"],
                      wall_a, wall_b, facing=1)
        wb.sphere((sx - 2.0, wy_, h + 4.0), 2.4, pal["glow_violet"], rings=4, segments=8)
    span = L["col_span"]
    wb.box((bx - 3.0, 0.0, h / 2.0), (6.0, span, h), wall_a, solid=True)
    wb.box((bx - 3.0, 0.0, h + 1.05), (7.5, span, 2.1), cap)
    sec.emit(wb, "Plots_Walls")
    return anchors


def build_ref_markers(world, pal):
    sec = world.section("REF")
    for name, pos in REF_MARKERS.items():
        mb = MeshBuilder()
        mb.box(pos, (REF_SIZE, REF_SIZE, REF_SIZE), pal["ref"])
        sec.emit(mb, name)


def build_island_barriers(L):
    """Invisible walls around the corridor island. Its scenery strips are
    already sealed by the corridor walls; these catch anything that gets over."""
    iy, x1 = L["island_y"], L["corridor_len"]
    barrier("Island", 0.0, iy + 1.0, x1, iy + 1.0)
    barrier("Island", 0.0, -iy - 1.0, x1, -iy - 1.0)


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
    ch = L["corridor_half"]
    iy = L["island_y"]
    lane = ch - 24.0

    tables = {}
    tables["reference"] = {
        "origin": V3(REF_MARKERS["REF_Origin"]),
        "axisX": V3(REF_MARKERS["REF_AxisX"]),
        "axisY": V3(REF_MARKERS["REF_AxisY"]),
        "markerSize": REF_SIZE,
    }
    tables["island"] = bounds((L["lobby_x0"], L["lobby_half"], -CONFIG["dirt_depth"]),
                              (L["corridor_len"], -L["lobby_half"], 0.0))
    tables["corridor"] = dict(bounds((0.0, ch, 0.0), (L["corridor_len"], -ch, 0.0)),
                              width=ch * 2.0)
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
        "shop": {"position": V3(lobby["shop"]["position"]), "yaw": Num(lobby["shop"]["yaw"])},
        "speedShop": {"position": V3(lobby["speedShop"]["position"]),
                      "yaw": Num(lobby["speedShop"]["yaw"])},
        "dailyReward": V3(lobby["dailyReward"]),
        "statue": V3(lobby["statue"]),
        "showcase": [{"rarity": s["rarity"], "position": V3(s["position"])}
                     for s in lobby["showcase"]],
    }

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

    tables["capsuleZone"] = bounds((0.0, lane, 0.0), (L["ring_x"], -lane, 0.0))
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
        "lobby": "The bar of the T: spawns, portals, shops, bases. `index` 0 sorts it first.",
        "zones": "Corridor zones in walking order. `index` grows with the distance from the\n"
                 "-- lobby, so it doubles as a difficulty / reward tier.",
        "portals": "Teleport triggers. target = \"base\", \"lobby\" or \"zone:<id>\".\n"
                   "-- position/size/yaw describe the trigger box (CFrame.Angles(0, yaw, 0)).",
        "capsuleZone": "Legacy: the whole corridor lane. Prefer zones[i].capsuleArea.",
        "plots": "Player bases (\"enclos\") on the lobby's west side, B1 closest to the avenue.",
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
    check("zones_contiguous", not gaps and segs[0][0] == L["lobby_x1"]
          and segs[-1][1] == L["corridor_len"], str(gaps))

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

    # Bases sit inside the lobby.
    (lx0, ly0, _), (lx1, ly1, _) = lobby["bounds"]
    for p in plots:
        (px0, py0, _), (px1, py1, _) = p["bounds"]
        check("plot_%s_in_lobby" % p["id"], lx0 <= px0 < px1 <= lx1 and ly0 <= py0 < py1 <= ly1)

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
    keep_out(0.0, -L["corridor_half"] + 20.0, L["corridor_len"], L["corridor_half"] - 20.0)

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
    mid_x = (L["lobby_x0"] + L["corridor_len"]) / 2.0
    pcx, b1 = L["plaza_cx"], L["base_centers"][len(L["base_centers"]) // 2]
    cams = {
        "aerial": add_camera("Cam_Aerial", (mid_x - 760.0, -1150.0, 900.0),
                             (mid_x + 30.0, 0.0, -30.0), rig, lens=32.0),
        "lobby": add_camera("Cam_Lobby", (60.0, -260.0, 150.0),
                            (pcx - 10.0, 20.0, 10.0), rig, lens=26.0),
        "statue": add_camera("Cam_Statue", (-30.0, -24.0, 14.0),
                             (pcx, 0.0, 52.0), rig, lens=26.0),
        "street": add_camera("Cam_Street", (-60.0, 0.0, 14.0),
                             (L["corridor_len"], 0.0, 30.0), rig, lens=28.0),
        "plot": add_camera("Cam_Plot", (L["street_x"] + 110.0, b1 - 120.0, 120.0),
                           (L["street_x"] - 60.0, b1, 0.0), rig, lens=36.0),
        "boss": add_camera("Cam_Boss", (L["ring_x"] - 40.0, -60.0, 90.0),
                           (L["arena_x"], 0.0, 20.0), rig, lens=30.0),
    }
    setup_render()

    blend_path = os.path.join(OUT_DIR, "kaiju_heist_map.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("SAVED_BLEND", blend_path)

    # Only the map goes into the GLB: no cameras, lights or camera targets.
    map_objects = [world.empty]
    for sec in world.sections.values():
        map_objects += [sec.empty] + sec.objects
    glb_path = os.path.join(OUT_DIR, "kaiju_heist_map.glb")
    export_glb(glb_path, map_objects)
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
