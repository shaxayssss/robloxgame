"""
BRAINROT FIGHTER - Zone 6: VOID BRAINROT (v2: terraformed, gem mountains, living map)

Builds the whole zone in Blender from code, then exports it for Roblox Studio:
  <NAME>.fbx              the map (Roblox Studio > Avatar > Import 3D)
  <NAME>_Test.lua         installer to paste in the Studio command bar (EDIT mode, not Play)
  <NAME>_Palette.png      palette texture (only needed if the map imports grey)
  MapLife.client.lua      copy of the client animation script that the installer creates
  <NAME>.blend            optional (SAVE_BLEND=1)

What changed since v1:
  - terraforming: four gem mountain ranges close the left, back and right edges, every raised level
    (hill, summit, terraces, butte) has faceted rocky cliffs, rock arches and gem fissures on the ground
  - gems everywhere: amethyst, diamond, ruby, emerald and topaz clusters, spires and cut gems
  - a living map: eyes that follow the player, drifting islands, spinning gems and planets,
    a swirling black hole, glitches, twinkling stars, breathing neon and particles
  - raised levels are now solid (v1 let players walk into the hill from the plateau)

Run from Blender: Scripting tab > New > paste this file > Run Script.
Run headless:     EXPORT_DIR=out RENDER_PREVIEW=1 SAMPLES=20 SAVE_BLEND=1 python zone6_void_brainrot.py

Scale: 1 Blender unit = 1 stud. The playable area is about 600 x 600, centred on the origin.
Orientation: the entrance (golden island) is on -Y, the boss arena on +Y, Z is up.
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Matrix, Vector, noise

# ======================= SETTINGS =======================
EXPORT_DIR = os.environ.get(
    "EXPORT_DIR", os.path.join(os.path.expanduser("~"), "BrainrotFighter", "Zone6_VoidBrainrot"))
NAME = "Zone6_VoidBrainrot"
RENDER_PREVIEW = os.environ.get("RENDER_PREVIEW", "0") == "1"
S = 600
H = S / 2
GRID = 3                 # chunk grid: geometry is merged per (prefix, cell) to limit the MeshPart count
TRI_MAX = 9500           # hard cap per MeshPart (Roblox allows more, this keeps every importer happy)

# Landmarks used by the Roblox installer to recover the map orientation (names shared by every zone)
ARENA = (160, 172)           # boss platform above the black hole  -> object "Sol_Arene"
STAR = (-178, -238)          # golden pyramid (Star)               -> object "Star_Socle"
ARCHES_X = (122, 150, 178)   # teleporter arches                   -> object "Neon_arche"
ARCHES_Y = -238
SPAWN = (-155, -226, -4)     # spawn point (x, y, ground height)
MARKER = "Decor_Sky_Brain"   # object that only exists in this map (v2)

random.seed(66)
noise.seed_set(66)

# ======================= PALETTE =======================
PALETTE = {
    # ground
    "check_light": (212, 202, 236), "check_dark": (150, 134, 200), "check_gold": (255, 222, 120),
    "check_gold2": (236, 176, 64),
    # rock and frost
    "rock": (90, 54, 134), "rock_dark": (58, 30, 96), "rock_rim": (126, 96, 178), "rock_mid": (108, 70, 156),
    "rock_deep": (40, 20, 70), "frost": (228, 218, 250), "frost_shade": (186, 170, 230),
    # vegetation
    "grass": (46, 118, 92), "grass_dark": (30, 84, 72), "grass_light": (70, 150, 110),
    "vein": (120, 255, 110), "mushroom": (150, 232, 214), "stem": (206, 212, 232),
    # gems
    "crystal": (160, 84, 236), "crystal_light": (206, 150, 255), "crystal_dark": (104, 46, 188),
    "amethyst_glow": (190, 110, 255),
    "diamond": (180, 244, 255), "diamond_mid": (90, 205, 255), "diamond_dark": (40, 140, 225),
    "ruby": (255, 70, 160), "ruby_light": (255, 160, 210), "ruby_dark": (160, 20, 100),
    "emerald": (40, 220, 120), "emerald_light": (150, 255, 190), "emerald_dark": (12, 130, 84),
    "gold": (255, 208, 60), "gold_dark": (222, 158, 40),
    # neon
    "cyan": (60, 230, 255), "magenta": (255, 60, 200), "pink": (255, 120, 200), "water": (96, 240, 255),
    "bridge_neon": (196, 120, 255), "star": (255, 255, 255),
    # creatures and sky
    "white": (246, 244, 252), "iris_blue": (70, 146, 236), "iris_violet": (156, 72, 210),
    "pupil": (22, 14, 34), "lip": (224, 72, 136), "lip_dark": (150, 34, 96),
    "planet": (96, 126, 214), "planet2": (170, 96, 206), "planet_ring": (206, 176, 255),
    "brain": (186, 124, 255), "brain_dark": (126, 70, 206), "black": (14, 6, 26),
    # built
    "stair": (156, 146, 190), "stair_dark": (112, 100, 156), "bridge": (122, 100, 196),
}
COLOURS = list(PALETTE)
EMISSION = {"vein": 1.0, "crystal": 0.35, "crystal_light": 0.6, "crystal_dark": 0.15, "amethyst_glow": 1.0,
            "cyan": 1.0, "magenta": 1.0, "pink": 0.8, "gold": 0.8, "check_gold": 0.35, "water": 1.0,
            "mushroom": 0.7, "brain": 0.8, "brain_dark": 0.35, "bridge_neon": 1.0, "star": 1.0,
            "planet_ring": 0.3, "diamond": 0.6, "diamond_mid": 0.45, "diamond_dark": 0.2, "ruby": 0.45,
            "ruby_light": 0.6, "ruby_dark": 0.15, "emerald": 0.45, "emerald_light": 0.7, "emerald_dark": 0.15}
CELLS = 8
PX = 32
UV = {}
for _i, _n in enumerate(COLOURS):
    UV[_n] = ((_i % CELLS + 0.5) / CELLS, (_i // CELLS + 0.5) / CELLS)

# Neon objects: name prefix -> palette colour (the installer turns them into Neon parts of that colour)
NEON = {
    "Neon_arche": "crystal_light", "Neon_cyan": "cyan", "Neon_magenta": "magenta", "Neon_pink": "pink",
    "Neon_vein": "vein", "Neon_bridge": "bridge_neon", "Neon_water": "water", "Neon_mushroom": "mushroom",
    "Neon_star": "star", "Neon_gold": "gold", "Neon_amethyst": "amethyst_glow", "Star_Socle": "gold",
}

# Gem families: (light, mid, dark) palette colours, light colour for lamps, neon prefix for veins
GEMS = {
    "amethyst": ("crystal_light", "crystal", "crystal_dark"),
    "diamond": ("diamond", "diamond_mid", "diamond_dark"),
    "ruby": ("ruby_light", "ruby", "ruby_dark"),
    "emerald": ("emerald_light", "emerald", "emerald_dark"),
    "topaz": ("check_gold", "gold", "gold_dark"),
}
C_VIOLET = (0.72, 0.4, 1.0)
C_CYAN = (0.3, 0.9, 1.0)
C_GREEN = (0.45, 1.0, 0.45)
C_GOLD = (1.0, 0.82, 0.35)
C_PINK = (1.0, 0.4, 0.8)
GEM_LIGHT = {"amethyst": C_VIOLET, "diamond": (0.4, 0.88, 1.0), "ruby": (1.0, 0.35, 0.7),
             "emerald": (0.4, 1.0, 0.6), "topaz": C_GOLD}

# ======================= EXPORTED TABLES =======================
LIGHTS = []       # (pos, colour, power, radius, host object or "", pulse)
COLLISIONS = []   # walkable surfaces: (a, b, width, thickness) -> invisible Parts in Roblox
LIFE = {}         # object name -> animation parameters (read by the MapLife client script)
PARTICLES = []    # (kind, pos, size, host object or "", colour)


def light(pos, colour, power=4000, radius=1.0, host="", pulse=0.0):
    LIGHTS.append((Vector(pos), colour, power, radius, host, pulse))


def collision(a, b, width, thickness=4.0):
    """Walkable surface: a box whose TOP runs from a to b (may slope), `thickness` deep."""
    COLLISIONS.append((Vector(a), Vector(b), width, thickness))


def alive(name, bob=0.0, period=6.0, phase=None, spin=0.0, axis=(0, 0, 1), pivot=None, sway=0.0,
          look=None, glitch=False, pulse=0.0):
    """Registers an object for the client animation. Units: studs, seconds, radians."""
    LIFE[name] = dict(bob=bob, period=period, phase=random.random() if phase is None else phase, spin=spin,
                      axis=axis, pivot=pivot, sway=sway, look=look, glitch=glitch, pulse=pulse)


def fx(kind, pos, size=(1, 1, 1), host="", colour=(1, 1, 1)):
    PARTICLES.append((kind, Vector(pos), Vector(size), host, colour))


# ======================= MATRIX HELPERS =======================
def T(x, y=None, z=None):
    if y is None:
        return Matrix.Translation(Vector(x))
    return Matrix.Translation((x, y, z))


def R(angle, axis):
    return Matrix.Rotation(angle, 4, axis)


def align(up):
    """Rotation that sends local +Z to `up`."""
    return Vector(up).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


I = Matrix.Identity(4)


# ======================= BUILDER =======================
class Builder:
    """Accumulates geometry per chunk key; each key becomes one MeshPart in Roblox.
    Every primitive is wound outward, so normals are never recalculated (that heuristic can flip
    open surfaces such as a heightfield) except for keys listed in `recalc`."""

    def __init__(self):
        self.bms = {}
        self.recalc = set()

    def bm(self, key):
        if key not in self.bms:
            b = bmesh.new()
            b.loops.layers.uv.new("UVMap")
            self.bms[key] = b
        return self.bms[key]

    def paint(self, b, faces, colour):
        uv = b.loops.layers.uv.active
        u, v = UV[colour]
        for f in faces:
            for loop in f.loops:
                loop[uv].uv = (u, v)

    def box(self, key, M, size, colour, center=(0, 0, 0), rot=None, base=True):
        sx, sy, sz = size
        cx, cy, cz = center
        if base:
            cz += sz / 2
        L = T(cx, cy, cz)
        if rot is not None:
            L = L @ rot
        b = self.bm(key)
        r = bmesh.ops.create_cube(b, size=1.0, matrix=M @ L @ Matrix.Diagonal((sx, sy, sz, 1)))
        self.paint(b, {f for v in r["verts"] for f in v.link_faces}, colour)

    def cylinder(self, key, M, radius, height, colour, center=(0, 0, 0), radius2=None, segs=12, rot=None,
                 base=True):
        cx, cy, cz = center
        L = T(cx, cy, cz + (height / 2 if base else 0))
        if rot is not None:
            L = L @ rot
        b = self.bm(key)
        r = bmesh.ops.create_cone(b, cap_ends=True, cap_tris=False, segments=segs, radius1=radius,
                                  radius2=radius if radius2 is None else radius2, depth=height, matrix=M @ L)
        self.paint(b, {f for v in r["verts"] for f in v.link_faces}, colour)

    def poly(self, key, M, verts, faces, colour):
        b = self.bm(key)
        vs = [b.verts.new(M @ Vector(v)) for v in verts]
        fs = [b.faces.new([vs[i] for i in f]) for f in faces]
        self.paint(b, fs, colour)

    def mesh(self, key, verts, faces, colours):
        """Custom mesh with one colour per face (faces must already be wound outward)."""
        b = self.bm(key)
        vs = [b.verts.new(Vector(v)) for v in verts]
        uv = b.loops.layers.uv.active
        for f, c in zip(faces, colours):
            face = b.faces.new([vs[i] for i in f])
            u, v = UV[c]
            for loop in face.loops:
                loop[uv].uv = (u, v)


ch = Builder()


def chunk(prefix, x, y):
    ix = min(GRID - 1, max(0, int((x + H) / (S / GRID))))
    iy = min(GRID - 1, max(0, int((y + H) / (S / GRID))))
    return f"{prefix}_{ix}{iy}"


# ======================= 2D SHAPES =======================
def ccw(pts):
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    return list(pts) if area > 0 else list(reversed(pts))


def inside(pts, x, y):
    ok = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            ok = not ok
        j = i
    return ok


def dist_to_edge(pts, x, y):
    best = 1e9
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy + 1e-9)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def scaled(pts, s):
    cx, cy = centroid(pts)
    return [(cx + (x - cx) * s, cy + (y - cy) * s) for x, y in pts]


def hexagon(cx, cy, r, rot=0.0):
    return [(cx + r * math.cos(rot + i * math.pi / 3), cy + r * math.sin(rot + i * math.pi / 3)) for i in range(6)]


def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def outline(half_x, half_y, n=160, wobble=6.0, p=5.0, seed=3, cx=0.0, cy=0.0):
    """Rounded square (superellipse of power p) with a slightly irregular edge, counter-clockwise."""
    rng = random.Random(seed)
    pts = []
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s_ = math.cos(t), math.sin(t)
        r = 1 / (abs(c) ** p + abs(s_) ** p) ** (1 / p)
        d = wobble * (math.sin(3 * t + ph1) + 0.6 * math.sin(7 * t + ph2)) + rng.uniform(-1.5, 1.5)
        pts.append((cx + (r * half_x + d) * c, cy + (r * half_y + d) * s_))
    return pts


def vertex_normals(pts):
    """Outward unit normal at each vertex of a counter-clockwise contour."""
    n = len(pts)
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = Vector((y1 - y0, -(x1 - x0)))
        e2 = Vector((y2 - y1, -(x2 - x1)))
        if e1.length:
            e1.normalize()
        if e2.length:
            e2.normalize()
        v = e1 + e2
        out.append(v.normalized() if v.length > 1e-6 else e1)
    return out


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ======================= BASIC SOLIDS =======================
def prism(key, M, pts, z0, z1, colour):
    """Flat shape (any contour) extruded from z0 to z1."""
    pts = ccw(pts)
    n = len(pts)
    verts = [(x, y, z1) for x, y in pts] + [(x, y, z0) for x, y in pts]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, n + i, n + j, j))
    ch.poly(key, M, verts, faces, colour)


def cap(key, pts, z, colour):
    """Top face only (the sides come from a cliff)."""
    pts = ccw(pts)
    ch.poly(key, I, [(x, y, z) for x, y in pts], [tuple(range(len(pts)))], colour)


def ring(key, M, r1, r2, z0, thick, colour, n=40):
    """Solid ring without gaps between segments."""
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s_ = math.cos(a), math.sin(a)
        verts += [(r1 * c, r1 * s_, z0 + thick), (r2 * c, r2 * s_, z0 + thick), (r2 * c, r2 * s_, z0),
                  (r1 * c, r1 * s_, z0)]
    for i in range(n):
        a, b = 4 * i, 4 * ((i + 1) % n)
        faces += [(a, a + 1, b + 1, b), (a + 3, b + 3, b + 2, a + 2), (a + 1, a + 2, b + 2, b + 1),
                  (a, b, b + 3, a + 3)]
    ch.poly(key, M, verts, faces, colour)


def dashed_ring(key, M, r1, r2, z0, thick, colour, arcs=9, fill=0.62, steps=5):
    """Ring broken into arcs, so that its rotation is visible."""
    for k in range(arcs):
        a0 = 2 * math.pi * k / arcs
        a1 = a0 + 2 * math.pi / arcs * fill
        verts, faces = [], []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            c, s_ = math.cos(a), math.sin(a)
            verts += [(r1 * c, r1 * s_, z0 + thick), (r2 * c, r2 * s_, z0 + thick), (r2 * c, r2 * s_, z0),
                      (r1 * c, r1 * s_, z0)]
        for i in range(steps):
            a, b = 4 * i, 4 * (i + 1)
            faces += [(a, a + 1, b + 1, b), (a + 3, b + 3, b + 2, a + 2), (a + 1, a + 2, b + 2, b + 1),
                      (a, b, b + 3, a + 3)]
        last = 4 * steps
        faces += [(0, 3, 2, 1), (last, last + 1, last + 2, last + 3)]
        ch.poly(key, M, verts, faces, colour)


def arch_tube(key, M, r, hp, t, colour, n=16):
    """Inverted-U arch in one piece: two posts + half circle."""
    path = [(Vector((r, 0, 0)), Vector((1, 0, 0)))]
    for i in range(n + 1):
        a = math.pi * i / n
        u = Vector((math.cos(a), 0, math.sin(a)))
        path.append((Vector((0, 0, hp)) + r * u, u))
    path.append((Vector((-r, 0, 0)), Vector((-1, 0, 0))))
    v = Vector((0, 1, 0))
    verts = []
    for c, u in path:
        for su, sv in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            verts.append(tuple(c + su * t * u + sv * t * v))
    faces = []
    for i in range(len(path) - 1):
        a, b = 4 * i, 4 * (i + 1)
        for j in range(4):
            faces.append((a + j, a + (j + 1) % 4, b + (j + 1) % 4, b + j))
    last = 4 * (len(path) - 1)
    faces += [(3, 2, 1, 0), (last, last + 1, last + 2, last + 3)]
    ch.poly(key, M, verts, faces, colour)
    ch.recalc.add(key)


def sphere(key, M, radius, colour, center=(0, 0, 0), scale=(1, 1, 1), subdiv=1):
    b = ch.bm(key)
    mat = M @ T(Vector(center)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
    r = bmesh.ops.create_icosphere(b, subdivisions=subdiv, radius=radius, matrix=mat)
    ch.paint(b, {f for v in r["verts"] for f in v.link_faces}, colour)


def segment(key, a, b, width, thick, colour):
    """Long box between two points (neon lines, veins, bridge rails)."""
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    ch.box(key, T((a + b) / 2) @ rot, (width, thick, d.length + 0.4), colour, base=False)


def neon_line(key, points, z, width=1.0, colour="cyan"):
    for a, b in zip(points, points[1:]):
        segment(key, Vector((a[0], a[1], z)), Vector((b[0], b[1], z)), width, 0.14, colour)


def boulder(key, pos, r, scale=(1.0, 1.0, 0.8), colours=("rock", "rock_mid", "rock_dark", "rock_rim")):
    """Faceted rock: jittered icosphere, one colour per facet."""
    b = ch.bm(key)
    M = T(Vector(pos)) @ R(random.uniform(0, 6.28), "Z") @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
    res = bmesh.ops.create_icosphere(b, subdivisions=1, radius=r, matrix=M)
    for v in res["verts"]:
        v.co += Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * r * 0.12
    uv = b.loops.layers.uv.active
    faces = list(dict.fromkeys(f for v in res["verts"] for f in v.link_faces))   # stable order: same colours every run
    for f in faces:
        u, vv = UV[random.choice(colours)]
        for loop in f.loops:
            loop[uv].uv = (u, vv)


# ======================= TERRAFORMING =======================
def cliff(key, pts, z_top, z_bot, flare, rows=3, colours=("rock", "rock_mid", "rock_dark"), lip="rock_rim",
          gem=None):
    """Faceted rocky wall hanging from a contour: a thin lip, then irregular rows down to z_bot.
    flare > 0 widens the foot (raised levels), flare < 0 tucks it in (floating edges)."""
    pts = ccw(pts)
    n = len(pts)
    nrm = vertex_normals(pts)
    h = z_top - z_bot
    drop = min(1.2, h * 0.2)
    sign = 1 if flare >= 0 else -1
    rings = [[Vector((x, y, z_top)) for x, y in pts],
             [Vector((x + nx * 0.35 * sign, y + ny * 0.35 * sign, z_top - drop)) for (x, y), (nx, ny) in zip(pts, nrm)]]
    for r in range(1, rows + 1):
        t = r / rows
        ring_ = []
        for (x, y), (nx, ny) in zip(pts, nrm):
            off = flare * (0.15 + 0.85 * t ** 0.8) + random.uniform(-0.35, 0.35) * abs(flare)
            z = z_top - drop - (h - drop) * t
            if r < rows:
                z += random.uniform(-1, 1) * (h / rows) * 0.25
            ring_.append(Vector((x + nx * off, y + ny * off, z)))
        rings.append(ring_)
    gem_colour = GEMS[gem][1] if gem else None
    verts = [v for rg in rings for v in rg]
    faces, cols = [], []
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            ui, uj, li, lj = r * n + i, r * n + j, (r + 1) * n + i, (r + 1) * n + j
            faces += [(ui, li, lj), (ui, lj, uj)]
            for _ in range(2):
                if r == 0:
                    cols.append(lip)
                elif gem_colour and random.random() < 0.05:
                    cols.append(gem_colour)
                else:
                    cols.append(random.choice(colours))
    ch.mesh(key, verts, faces, cols)


def underside(key, pts, z_top, depth=14, spikes=20, rmax=16, lmax=60, gems=None):
    """Broken rock under a floating level: tucked-in cliff, slab, stalactites and hanging gems."""
    pts = ccw(pts)
    cliff(key, pts, z_top, z_top - 5, -3.0, rows=2, colours=("rock_rim", "rock", "rock_mid"))
    nrm = vertex_normals(pts)
    inset = [(x - nx * 2.4, y - ny * 2.4) for (x, y), (nx, ny) in zip(pts, nrm)]
    prism(key, I, inset, z_top - depth, z_top - 4, "rock")
    xs, ys = [p[0] for p in inset], [p[1] for p in inset]
    placed = tries = 0
    while placed < spikes and tries < spikes * 30:
        tries += 1
        x, y = random.uniform(min(xs), max(xs)), random.uniform(min(ys), max(ys))
        if not inside(inset, x, y):
            continue
        r = random.uniform(rmax * 0.4, rmax)
        L = random.uniform(lmax * 0.3, lmax)
        if gems and random.random() < 0.25:
            light_c, mid, _ = GEMS[random.choice(gems)]
            M = T(x, y, z_top - depth + 1) @ R(math.pi, "X") @ R(random.uniform(0, 6), "Z")
            ch.cylinder(key, M, r * 0.45, L * 0.45, mid, segs=6)
            ch.cylinder(key, M, r * 0.45, r * 1.1, light_c, center=(0, 0, L * 0.45), radius2=0.2, segs=6)
        else:
            colour = random.choice(["rock", "rock_dark", "rock_dark", "crystal_dark"])
            ch.cylinder(key, T(x, y, z_top - depth + 1 - L) @ R(random.uniform(0, 6), "Z"), 0.6, L, colour,
                        radius2=r, segs=6)
        placed += 1


def taper(key, pts, z_top, depth, colours=("rock", "rock_dark", "rock_mid")):
    """Inverted rocky cone under a small floating island."""
    pts = ccw(pts)
    cx, cy = centroid(pts)
    n = len(pts)
    rings = []
    for s, t in ((1.0, 0.0), (0.9, 0.12), (0.62, 0.38), (0.34, 0.68), (0.12, 0.9)):
        rg = []
        for x, y in pts:
            k = s if t == 0 else s + random.uniform(-0.08, 0.08)
            z = z_top - depth * t + (0 if t == 0 else random.uniform(-1, 1) * depth * 0.04)
            rg.append(Vector((cx + (x - cx) * k, cy + (y - cy) * k, z)))
        rings.append(rg)
    verts = [v for rg in rings for v in rg] + [Vector((cx, cy, z_top - depth))]
    tip = len(verts) - 1
    faces, cols = [], []
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            ui, uj, li, lj = r * n + i, r * n + j, (r + 1) * n + i, (r + 1) * n + j
            faces += [(ui, li, lj), (ui, lj, uj)]
            cols += [random.choice(colours), random.choice(colours)]
    last = (len(rings) - 1) * n
    for i in range(n):
        faces.append((last + i, tip, last + (i + 1) % n))
        cols.append(random.choice(colours))
    ch.mesh(key, verts, faces, cols)
    return rings


def rock_peak(key, x, y, z, r, h, segs=7):
    """Small faceted mountain (sky islands): rocky flanks, frosted tip."""
    a0 = random.uniform(0, 6.28)
    base, mid = [], []
    for i in range(segs):
        a = a0 + 2 * math.pi * i / segs
        rr = r * random.uniform(0.8, 1.1)
        base.append(Vector((x + math.cos(a) * rr, y + math.sin(a) * rr, z - 0.5)))
        rm = r * random.uniform(0.4, 0.55)
        mid.append(Vector((x + math.cos(a + 0.2) * rm, y + math.sin(a + 0.2) * rm, z + h * random.uniform(0.5, 0.62))))
    tip = Vector((x + random.uniform(-0.1, 0.1) * r, y + random.uniform(-0.1, 0.1) * r, z + h))
    verts = base + mid + [tip]
    faces, cols = [], []
    for i in range(segs):
        j = (i + 1) % segs
        faces += [(i, j, segs + j), (i, segs + j, segs + i), (segs + i, segs + j, 2 * segs)]
        cols += [random.choice(["rock", "rock_mid"]), random.choice(["rock_dark", "rock"]),
                 random.choice(["frost", "frost_shade"])]
    ch.mesh(key, verts, faces, cols)


def rasterize(pts, z, thickness=4.0, cell=6.0):
    """Walkable collision strips covering the contour at height z (solid `thickness` studs deep)."""
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    y = min(ys) + cell / 2
    while y < max(ys):
        x = min(xs) + cell / 2
        start = None
        while x < max(xs) + cell:
            ok = inside(pts, x, y)
            if ok and start is None:
                start = x
            if not ok and start is not None:
                collision((start - cell / 2, y, z), (x - cell / 2, y, z), cell + 0.3, thickness)
                start = None
            x += cell
        y += cell


def checker(prefix, pts, z, size=12.0, dark="check_dark", exclude=None, offset=(0.0, 0.0)):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    i0, i1 = int(math.floor((min(xs) - offset[0]) / size)), int(math.ceil((max(xs) - offset[0]) / size))
    j0, j1 = int(math.floor((min(ys) - offset[1]) / size)), int(math.ceil((max(ys) - offset[1]) / size))
    for i in range(i0, i1):
        for j in range(j0, j1):
            if (i + j) % 2:
                continue
            x0, y0 = offset[0] + i * size, offset[1] + j * size
            corners = [(x0, y0), (x0 + size, y0), (x0, y0 + size), (x0 + size, y0 + size)]
            if not all(inside(pts, cx_, cy_) for cx_, cy_ in corners):
                continue
            xc, yc = x0 + size / 2, y0 + size / 2
            if exclude and any(inside(e, xc, yc) for e in exclude):
                continue
            ch.box(chunk(prefix, xc, yc), I, (size, size, 0.06), dark, center=(xc, yc, z))


# ======================= GEMS =======================
def crystal_cluster(key, pos, size=1.0, gem="amethyst", up=(0, 0, 1), n=None, lean=0.35):
    """Cluster of hexagonal crystals growing along `up`."""
    x, y, z = pos
    light_c, mid, dark = GEMS[gem]
    base = T(x, y, z - 1) @ align(up)
    n = n or random.randint(3, 7)
    for i in range(n):
        h = random.uniform(8, 20) * size * (1.4 if i == 0 else 1)
        r = random.uniform(1.8, 3.2) * size * (1.3 if i == 0 else 1)
        a = random.uniform(0, 2 * math.pi)
        off = r * 0.8 if i else 0
        tilt = 0 if i == 0 else random.uniform(0.15, lean)
        M = base @ T(math.cos(a) * off, math.sin(a) * off, 0) @ R(a, "Z") @ R(tilt, "Y")
        c = random.choice([mid, mid, light_c, dark])
        ch.cylinder(key, M, r, h, c, segs=6)
        ch.cylinder(key, M, r, r * 2.2, c, center=(0, 0, h), radius2=0.2, segs=6)


def gem_spire(key, pos, height, radius, gem, up=(0, 0, 1)):
    """Giant crystal bursting out of a mountain, with a few small ones at its foot."""
    light_c, mid, dark = GEMS[gem]
    M = T(Vector(pos)) @ align(up) @ R(random.uniform(0, 6), "Z")
    ch.cylinder(key, M, radius, height, mid, segs=6)
    ch.cylinder(key, M, radius, radius * 2.6, light_c, center=(0, 0, height), radius2=0.3, segs=6)
    for i in range(4):
        a = i * math.pi / 2 + random.uniform(-0.4, 0.4)
        Mi = M @ T(math.cos(a) * radius * 1.3, math.sin(a) * radius * 1.3, -1) @ R(a, "Z") @ R(0.45, "Y")
        h = height * random.uniform(0.2, 0.35)
        r = radius * random.uniform(0.35, 0.5)
        c = random.choice([dark, mid, light_c])
        ch.cylinder(key, Mi, r, h, c, segs=6)
        ch.cylinder(key, Mi, r, r * 2.2, c, center=(0, 0, h), radius2=0.2, segs=6)


def cut_gem(key, M, r, gem, n=8):
    """Brilliant-cut gem (table, crown, girdle, pavilion) centred on the girdle."""
    light_c, mid, dark = GEMS[gem]
    table, crown, pav = r * 0.55, r * 0.42, r * 1.05
    verts = [(0, 0, -pav)]
    verts += [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0) for i in range(n)]
    verts += [(table * math.cos(2 * math.pi * (i + 0.5) / n), table * math.sin(2 * math.pi * (i + 0.5) / n), crown)
              for i in range(n)]
    faces, cols = [], []
    for i in range(n):
        j = (i + 1) % n
        faces += [(0, 1 + j, 1 + i), (1 + i, 1 + j, n + 1 + i), (1 + j, n + 1 + j, n + 1 + i)]
        cols += [dark if i % 2 else mid, light_c if i % 2 else mid, mid if i % 2 else light_c]
    faces.append(tuple(range(n + 1, 2 * n + 1)))
    cols.append(light_c)
    ch.mesh(key, [M @ Vector(v) for v in verts], faces, cols)


def bipyramid(key, M, r, h, gem, n=6):
    """Long double-pointed gem (small floating shards)."""
    light_c, mid, dark = GEMS[gem]
    verts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0) for i in range(n)]
    verts += [(0, 0, h), (0, 0, -h * 1.3)]
    faces, cols = [], []
    for i in range(n):
        j = (i + 1) % n
        faces += [(i, j, n), (n + 1, j, i)]
        cols += [light_c if i % 2 else mid, dark if i % 2 else mid]
    ch.mesh(key, [M @ Vector(v) for v in verts], faces, cols)


def floating_gem(name, pos, r, gem, spin=0.5, bob=1.5, power=9000, sparkle=True):
    """Big cut gem hovering and turning, with its own light and sparkles."""
    cut_gem(name, T(Vector(pos)) @ R(0.12, "X"), r, gem)
    alive(name, bob=bob, period=random.uniform(5, 8), spin=spin, pivot=pos, pulse=0.45)
    light(Vector(pos) + Vector((0, 0, r * 0.3)), GEM_LIGHT[gem], power, 3, host=name)
    if sparkle:
        fx("sparkle", pos, (r * 2, r * 2, r * 2), host=name, colour=GEM_LIGHT[gem])


# ======================= GEM MOUNTAINS =======================
class Massif:
    """Gem mountain range: a low-poly heightfield on a floating rock slab.
    Not walkable (the installer gives it a precise collision so nobody walks through it)."""

    def __init__(self, name, pts, peaks, gems, vein, seed, step=6.0, ramp=26.0, cap_z=-1.0):
        self.name = name
        self.pts = ccw(pts)
        self.peaks = peaks          # (x, y, height, radius)
        self.gems = gems
        self.vein = vein            # neon prefix of the glowing veins
        self.seed = seed
        self.step = step
        self.ramp = ramp
        self.cap_z = cap_z
        self.rng = random.Random(seed)
        self.top = max(p[2] for p in peaks)
        xs, ys = [p[0] for p in self.pts], [p[1] for p in self.pts]
        self.x0, self.x1, self.y0, self.y1 = min(xs), max(xs), min(ys), max(ys)
        self.tris = []
        self.cells = {}
        self.down = 0               # heightfield faces pointing down (must stay 0)

    def key(self, x, y):
        return chunk(f"Decor_Massif{self.name}", x, y)

    def height(self, x, y):
        """Analytic height (None outside the footprint)."""
        if not inside(self.pts, x, y):
            return None
        e = smoothstep(dist_to_edge(self.pts, x, y) / self.ramp)
        h = 0.0
        for px, py, ph, pr in self.peaks:
            q = math.hypot(x - px, y - py) / pr
            if q < 1:
                h = max(h, ph * (1 - q) ** 1.35)
        n1 = noise.noise(Vector((x * 0.03, y * 0.03, self.seed * 1.7)))
        n2 = noise.noise(Vector((x * 0.09, y * 0.09, self.seed * 2.3 + 5)))
        h = h * (1 + 0.16 * n1) + 7 * (1 - abs(n2)) * (0.3 + 0.7 * min(1.0, h / 20))
        return 0.4 + e * max(0.0, h)

    def gradient(self, x, y):
        def hz(a, b):
            v = self.height(a, b)
            return 0.0 if v is None else v
        return (hz(x + 1, y) - hz(x - 1, y)) / 2, (hz(x, y + 1) - hz(x, y - 1)) / 2

    def surface_z(self, x, y):
        """Height of the built mesh (not the analytic one) at (x, y), or None."""
        st = self.step
        ci, cj = int((x - self.x0) / st + 0.5), int((y - self.y0) / st + 0.5)
        for i in range(ci - 1, ci + 2):
            for j in range(cj - 1, cj + 2):
                for t in self.cells.get((i, j), ()):
                    a, b, c = self.tris[t]
                    d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
                    if abs(d) < 1e-9:
                        continue
                    l1 = ((b.y - c.y) * (x - c.x) + (c.x - b.x) * (y - c.y)) / d
                    l2 = ((c.y - a.y) * (x - c.x) + (a.x - c.x) * (y - c.y)) / d
                    l3 = 1 - l1 - l2
                    if min(l1, l2, l3) >= -1e-6:
                        return l1 * a.z + l2 * b.z + l3 * c.z
        return None

    def normal(self, x, y):
        gx, gy = self.gradient(x, y)
        return Vector((-gx, -gy, 1)).normalized()

    def build(self):
        rng, st = self.rng, self.step
        ni = int((self.x1 - self.x0) / st) + 2
        nj = int((self.y1 - self.y0) / st) + 2
        V = {}
        for i in range(ni + 1):
            for j in range(nj + 1):
                # jitter stays under 0.15 step: a cell can never fold over
                x = self.x0 + (i - 0.5) * st + rng.uniform(-0.15, 0.15) * st
                y = self.y0 + (j - 0.5) * st + rng.uniform(-0.15, 0.15) * st
                if not inside(self.pts, x, y) or dist_to_edge(self.pts, x, y) < 1.5:
                    continue
                V[(i, j)] = Vector((x, y, self.height(x, y)))
        tris = []
        for i in range(ni):
            for j in range(nj):
                a, b, c, d = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
                for t in (((a, b, c), (a, c, d)) if (i + j) % 2 == 0 else ((a, b, d), (b, c, d))):
                    if all(k in V for k in t):
                        self.cells.setdefault((i, j), []).append(len(tris))
                        tris.append(t)
        self.tris = [(V[a], V[b], V[c]) for a, b, c in tris]

        chunks = {}

        def add(k, pts3, colour):
            vl, idx, fl, cl = chunks.setdefault(k, ([], {}, [], []))
            ids = []
            for p in pts3:
                pk = (round(p.x, 3), round(p.y, 3), round(p.z, 3))
                if pk not in idx:
                    idx[pk] = len(vl)
                    vl.append(p.copy())
                ids.append(idx[pk])
            fl.append(tuple(ids))
            cl.append(colour)

        gem_faces = [GEMS[g][1] for g in self.gems] + [GEMS[g][2] for g in self.gems]
        for t in tris:
            p = [V[k] for k in t]
            nrm = (p[1] - p[0]).cross(p[2] - p[0]).normalized()
            cx, cy, zc = (p[0].x + p[1].x + p[2].x) / 3, (p[0].y + p[1].y + p[2].y) / 3, (p[0].z + p[1].z + p[2].z) / 3
            rel = zc / self.top
            self.down += nrm.z <= 0
            r = rng.random()
            if rel > 0.6 and nrm.z > 0.4:
                col = "frost" if r < 0.7 else "frost_shade"
            elif rel > 0.48 and nrm.z > 0.7:
                col = "frost_shade" if r < 0.5 else "rock_rim"
            elif nrm.z < 0.5:
                col = "rock_dark" if r < 0.55 else ("rock" if r < 0.93 else rng.choice(gem_faces))
            elif nrm.z < 0.8:
                col = "rock" if r < 0.5 else ("rock_mid" if r < 0.95 else rng.choice(gem_faces))
            else:
                col = "rock_rim" if r < 0.45 else ("rock_mid" if r < 0.8 else ("grass_dark" if rel < 0.25 else "rock"))
            add(self.key(cx, cy), p, col)

        # skirts under the open edge of the heightfield, down into the slab
        edges = set()
        for t in tris:
            edges |= {(t[0], t[1]), (t[1], t[2]), (t[2], t[0])}
        for u, w in edges:
            if (w, u) in edges:
                continue
            pu, pw = V[u], V[w]
            low = self.cap_z - 0.6
            add(self.key((pu.x + pw.x) / 2, (pu.y + pw.y) / 2),
                [pu, Vector((pu.x, pu.y, low)), Vector((pw.x, pw.y, low)), pw], "rock_dark")
        for k, (vl, _, fl, cl) in chunks.items():
            ch.mesh(k, vl, fl, cl)

        # rock slab the range stands on, and its underside
        base = f"Decor_Sky_MassifBase{self.name}"
        cap(base, self.pts, self.cap_z, "rock_rim")
        area = (self.x1 - self.x0) * (self.y1 - self.y0)
        underside(base, self.pts, self.cap_z, depth=18, spikes=int(area / 1100), rmax=18, lmax=70, gems=self.gems)

    def decorate(self, clusters=14, spires=3, veins=5):
        rng = self.rng
        placed = tries = 0
        while placed < clusters and tries < clusters * 50:
            tries += 1
            x, y = rng.uniform(self.x0, self.x1), rng.uniform(self.y0, self.y1)
            z = self.surface_z(x, y)
            if z is None or z < 6:
                continue
            up = (Vector((0, 0, 1)) * 0.55 + self.normal(x, y) * 0.45).normalized()
            crystal_cluster(self.key(x, y), (x, y, z), rng.uniform(0.55, 1.15), rng.choice(self.gems), up=up)
            placed += 1
        # giant spires near the highest peaks, leaning towards the playable area
        for px, py, ph, pr in sorted(self.peaks, key=lambda p: -p[2])[:spires]:
            to_c = Vector((-px, -py, 0)).normalized()
            x, y = px + to_c.x * pr * 0.35, py + to_c.y * pr * 0.35
            z = self.surface_z(x, y)
            if z is None:
                continue
            gem = rng.choice(self.gems)
            up = (Vector((0, 0, 1)) + to_c * 0.35).normalized()
            height = ph * rng.uniform(0.38, 0.5)
            gem_spire(self.key(x, y), (x, y, z - 4), height, rng.uniform(4.5, 7), gem, up=up)
            light((x, y, z + height * 0.6), GEM_LIGHT[gem], 7000, 3)
        # glowing veins running down the slopes (one neon object per range, breathing)
        k = f"Neon_{self.vein}_Massif{self.name}"
        colour = NEON[f"Neon_{self.vein}"]
        drawn = 0
        for v in range(veins):
            px, py, ph, pr = rng.choice(self.peaks)
            a = rng.uniform(0, 2 * math.pi)
            x, y = px + math.cos(a) * pr * 0.15, py + math.sin(a) * pr * 0.15
            pts = []
            for _ in range(90):
                z = self.surface_z(x, y)
                if z is None or z < 2.5:
                    break
                pts.append(Vector((x, y, z + 0.4)))
                gx, gy = self.gradient(x, y)
                g = math.hypot(gx, gy)
                if g > 1e-4:
                    a = math.atan2(-gy, -gx) + rng.uniform(-0.5, 0.5)
                x += math.cos(a) * 3.0
                y += math.sin(a) * 3.0
            if len(pts) > 5:
                for p0, p1 in zip(pts, pts[1:]):
                    segment(k, p0, p1, 1.3, 0.35, colour)
                if drawn < 2:
                    mid = pts[len(pts) // 2]
                    light(mid + Vector((0, 0, 4)), GEM_LIGHT[self.gems[0]], 3500, 2, pulse=0.5)
                drawn += 1
        if drawn:
            alive(k, period=rng.uniform(3, 5), pulse=0.55)



# ======================= PROPS =======================
def mushroom(x, y, z, s=1.0):
    M = T(x, y, z) @ R(random.uniform(-0.15, 0.15), "X")
    ch.cylinder(chunk("Decor", x, y), M, 0.45 * s, 2.2 * s, "stem", radius2=0.35 * s, segs=8)
    ch.cylinder("Neon_mushroom", M, 1.5 * s, 0.9 * s, "mushroom", center=(0, 0, 2.1 * s), radius2=0.35 * s, segs=10)


def crystal_arch(x, y, z):
    M = T(x, y, z) @ Matrix.Diagonal((1.35, 1.35, 1.35, 1))
    arch_tube("Decor_Arches", M, 6.8, 8, 1.2, "crystal_dark")
    arch_tube("Neon_arche", M, 5.4, 8, 0.4, "crystal_light")
    for sx in (-1, 1):
        crystal_cluster("Decor_Arches", (x + sx * 9.2 * 1.35, y, z), 0.45, n=3)
    top = z + (8 + 6.8 + 1.2) * 1.35
    crystal_cluster("Decor_Arches", (x, y, top - 1), 0.35, n=3)
    light((x, y, z + 8), C_VIOLET, 5000, 2)
    fx("portal", (x, y, z + 9), (12, 2, 16), colour=(0.8, 0.6, 1.0))


def star_pyramid(x, y, z):
    M = T(x, y, z)
    for i, (c, h) in enumerate(((18, 2.5), (13.5, 2.5), (9, 2.5), (4.5, 2))):
        ch.box("Star_Socle", M, (c, c, h), "gold" if i % 2 == 0 else "gold_dark", center=(0, 0, i * 2.5))
    # the golden ring turns like a coin above the pyramid
    ring("Neon_gold_star", M @ T(0, 0, 21) @ R(math.pi / 2, "X"), 6.2, 7.6, -0.6, 1.2, "gold", n=28)
    alive("Neon_gold_star", bob=0.6, period=3.2, spin=0.8, pivot=(x, y, z + 21), pulse=0.3)
    light((x, y, z + 8), C_GOLD, 20000, 4)
    light((x, y, z + 21), C_GOLD, 5000, 2, host="Neon_gold_star")
    fx("gold", (x, y, z + 12), (18, 18, 10), colour=C_GOLD)


def big_fountain(x, y, z):
    M = T(x, y, z)
    k = chunk("Decor", x, y)
    ch.cylinder(k, M, 12, 2.5, "stair", segs=6)
    ch.cylinder("Neon_water", M, 10.6, 0.4, "water", center=(0, 0, 2.2), segs=6)
    ch.cylinder(k, M, 6, 3, "stair_dark", center=(0, 0, 2.5), segs=6)
    ch.cylinder("Neon_water", M, 5, 0.4, "water", center=(0, 0, 5.3), segs=6)
    ch.cylinder(k, M, 1.4, 4, "stair", center=(0, 0, 5.5), segs=6)
    ch.cylinder(k, M, 3, 1, "stair_dark", center=(0, 0, 9.5), radius2=1.4, segs=6)
    ch.cylinder("Neon_water", M, 0.6, 5, "water", center=(0, 0, 10), radius2=0.2, segs=6)
    light((x, y, z + 8), C_CYAN, 7000, 3)


def small_fountain(x, y, z):
    M = T(x, y, z)
    ch.cylinder(chunk("Decor", x, y), M, 4, 1.5, "stair", segs=8)
    ch.cylinder("Neon_water", M, 3.3, 0.3, "water", center=(0, 0, 1.3), segs=8)
    ch.cylinder("Neon_water", M, 0.4, 3, "water", center=(0, 0, 1.4), radius2=0.15, segs=6)


def facing(pos, target=(0, 0, 25)):
    d = Vector(target) - Vector(pos)
    return T(Vector(pos)) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()


EYE_REST = (-150, -200, 10)   # at rest the eyes stare at the entrance, where players arrive


def eye(name, x, y, z, r):
    """Floating eye; the client script turns it towards the player."""
    M = facing((x, y, z), EYE_REST)
    sphere(name, M, r, "white", subdiv=2)
    ch.cylinder(name, M, r * 0.55, 0.6, random.choice(["iris_blue", "iris_violet"]), center=(0, 0, r - 0.25),
                segs=16, base=False)
    ch.cylinder(name, M, r * 0.27, 0.6, "pupil", center=(0, 0, r + 0.05), segs=12, base=False)
    ch.cylinder(name, M, r * 0.1, 0.4, "white", center=(r * 0.18, r * 0.18, r + 0.3), segs=6, base=False)
    look = (Vector(EYE_REST) - Vector((x, y, z))).normalized()
    alive(name, bob=r * 0.12, period=random.uniform(5, 8), pivot=(x, y, z), look=tuple(look))


def lips(key, x, y, z, s):
    M = facing((x, y, z)) @ R(math.pi / 2, "X")
    sphere(key, M, s, "lip", center=(0, s * 0.32, 0), scale=(1.7, 0.6, 0.55))
    sphere(key, M, s, "lip_dark", center=(0, -s * 0.34, 0), scale=(1.6, 0.65, 0.6))
    sphere(key, M, s, "black", center=(0, 0, 0.1), scale=(1.35, 0.18, 0.4))


def planet(name, x, y, z, r, colour):
    M = T(x, y, z)
    sphere(name, M, r, colour, subdiv=2)
    ring(name, M @ R(0.45, "X") @ R(0.2, "Y"), r * 1.4, r * 1.95, -0.2, 0.4, "planet_ring", n=32)
    alive(name, bob=2.0, period=random.uniform(10, 14), spin=0.1, axis=(0.25, 0.1, 1), pivot=(x, y, z))


def floating_ring(name, x, y, z, r):
    M = T(x, y, z) @ R(random.uniform(0, 6), "Z") @ R(math.pi / 2 + random.uniform(-0.4, 0.4), "X")
    ring(name, M, r - 1.6, r, -0.9, 1.8, random.choice(["crystal_dark", "crystal"]), n=24)
    axis = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.2, 1))
    alive(name, bob=1.5, period=random.uniform(6, 9), spin=random.uniform(0.3, 0.5), axis=axis, pivot=(x, y, z))


def glitch(i, x, y, z, s):
    M = T(x, y, z) @ R(random.uniform(0, 6.28), "Z") @ R(random.uniform(-0.3, 0.3), "X")
    for k, c in enumerate(["magenta", "cyan", "magenta"]):
        name = f"Neon_{c}_glitch_{i}"
        ch.box(name, M, (s * random.uniform(1, 1.8), s * 0.5, s / 3 - 0.2), c,
               center=(random.uniform(-s * 0.4, s * 0.4), 0, k * s / 3))
    for c in ("magenta", "cyan"):
        alive(f"Neon_{c}_glitch_{i}", bob=0.5, period=random.uniform(2, 4), glitch=True, pivot=(x, y, z))
    light((x, y, z + s / 2), random.choice([C_PINK, C_CYAN]), 1200, 2, host=f"Neon_magenta_glitch_{i}")


def shard(key, pos, s, colour=None):
    M = T(Vector(pos)) @ R(random.uniform(0, 6), "Z") @ R(random.uniform(-0.8, 0.8), "X")
    sphere(key, M, s, colour or random.choice(["rock", "rock_dark", "crystal_dark", "crystal"]),
           scale=(0.55, 0.5, 1.5))


def brain(x, y, z, r):
    M = T(x, y, z) @ R(0.35, "Z")
    for side in (-1, 1):                                     # two hemispheres made of folds
        for _ in range(26):
            u = random.uniform(-0.9, 0.9)
            v = random.uniform(0.05, 1.0)
            a = math.acos(u)
            p = Vector((side * (0.15 + 0.85 * v) * 0.55, math.cos(a) * 1.0, math.sin(a) * 0.62)) * r
            sphere(MARKER, M, r * random.uniform(0.2, 0.3), random.choice(["brain", "brain", "brain_dark"]),
                   center=tuple(p), scale=(1.2, 1.0, 0.8))
        sphere(MARKER, M, r * 0.55, "brain_dark", center=(side * r * 0.3, 0, r * 0.05), scale=(0.9, 1.7, 1.05))
    bob = dict(bob=3.0, period=9.0, phase=0.0, pivot=(x, y, z))
    alive(MARKER, **bob)
    for i, (ri, c, inc, spin) in enumerate(((r * 1.7, "pink", 0.35, 0.12), (r * 1.95, "cyan", -0.25, -0.09),
                                            (r * 2.25, "magenta", 0.12, 0.07))):
        name = f"Neon_{c}_brain"
        ring(name, M @ R(inc, "X") @ R(0.2 * (i - 1), "Y"), ri - 1.2, ri, -0.5, 1.0, c, n=64)
        alive(name, spin=spin, pulse=0.3, **bob)
    light((x, y, z), C_VIOLET, 60000, 12, host=MARKER)
    light((x, y, z - r - 10), C_PINK, 20000, 6, host=MARKER)


def sky_island(i, x, y, z, r, gem):
    """Floating mini-mountain with gems hanging underneath; drifts slowly."""
    name = f"Decor_Sky_Island_{i}"
    pts = outline(r, r * 0.85, n=14, wobble=r * 0.06, p=2.2, seed=100 + i, cx=x, cy=y)
    cap(name, pts, z, random.choice(["grass_dark", "check_light"]))
    rings = taper(name, pts, z, r * 1.9)
    for k in range(random.randint(2, 3)):
        rock_peak(name, x + random.uniform(-0.35, 0.35) * r, y + random.uniform(-0.35, 0.35) * r, z,
                  r * random.uniform(0.3, 0.45), r * random.uniform(0.6, 1.1))
    crystal_cluster(name, (x + random.uniform(-r / 3, r / 3), y + random.uniform(-r / 3, r / 3), z),
                    r / 22, gem)
    light_c, mid, _ = GEMS[gem]
    for v in random.sample(rings[2], min(4, len(rings[2]))):   # gems hanging under the rock
        M = T(v) @ R(math.pi, "X") @ R(random.uniform(-0.3, 0.3), "Y")
        h, rr = r * random.uniform(0.25, 0.45), r * random.uniform(0.06, 0.1)
        ch.cylinder(name, M, rr, h, mid, segs=6)
        ch.cylinder(name, M, rr, rr * 2.2, light_c, center=(0, 0, h), radius2=0.2, segs=6)
    alive(name, bob=random.uniform(2.5, 4), period=random.uniform(9, 14), sway=0.025, pivot=(x, y, z), pulse=0.3)
    light((x, y, z + 10), GEM_LIGHT[gem], 3500, 2, host=name)


def rock_arch(cx, cy, direction, radius=15, gem="amethyst"):
    """Natural arch of stacked boulders spanning a path (walk under it)."""
    d = Vector((direction[0], direction[1], 0)).normalized()
    perp = Vector((-d.y, d.x, 0))
    k = chunk("Decor", cx, cy)
    n = 11
    for i in range(n):
        a = math.pi * i / (n - 1)
        p = Vector((cx, cy, 0)) + perp * (math.cos(a) * radius) + Vector((0, 0, math.sin(a) * radius * 1.15 + 2))
        boulder(k, p, (5.5 if 0 < i < n - 1 else 7.0) * random.uniform(0.9, 1.1), scale=(1, 1, 1))
    for s in (-1, 1):
        boulder(k, Vector((cx, cy, 1)) + perp * s * radius, 8, scale=(1.2, 1.2, 0.7))
    crystal_cluster(k, (cx, cy, radius * 1.15 + 6), 0.7, gem)
    light((cx, cy, radius * 1.15 + 12), GEM_LIGHT[gem], 3000, 2)


def fissure(points, gem, crystals=True):
    """Glowing crack in the ground with gems pushing through it."""
    key = "Neon_amethyst_fissure" if gem != "diamond" else "Neon_cyan_fissure"
    neon_line(key, points, 0.1, 1.6, "amethyst_glow" if gem != "diamond" else "cyan")
    if crystals:
        for a, b in zip(points, points[1:]):
            t = random.uniform(0.3, 0.7)
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            crystal_cluster(chunk("Decor", x, y), (x, y, 0), random.uniform(0.5, 0.8), gem, n=random.randint(2, 4))
    mid = points[len(points) // 2]
    light((mid[0], mid[1], 5), GEM_LIGHT[gem], 2500, 2, pulse=0.5)


def orbit(name, center, radius, count, gem, spin=0.25):
    """Ring of small gems turning around a point."""
    cx, cy, cz = center
    for i in range(count):
        a = 2 * math.pi * i / count
        p = Vector((cx + math.cos(a) * radius, cy + math.sin(a) * radius, cz + math.sin(3 * a) * radius * 0.12))
        bipyramid(name, T(p) @ R(random.uniform(-0.5, 0.5), "X") @ R(a, "Z"), radius * 0.08, radius * 0.16, gem)
    alive(name, spin=spin, pivot=center, bob=0.8, period=6)


# ======================= LEVELS =======================
HOLE = (160, 172, 80)          # black hole cut into the plateau (centre x, y, radius)
PLATEAU = [(-250, -150), (-180, -168), (-110, -178), (-40, -182), (40, -180), (110, -176), (180, -160),
           (232, -110), (248, -40), (252, 40), (246, 100)]
PLATEAU += [(HOLE[0] + HOLE[2] * math.cos(math.radians(a)), HOLE[1] + HOLE[2] * math.sin(math.radians(a)))
            for a in range(-20, -251, -10)]
PLATEAU += [(60, 250), (-20, 254), (-100, 250), (-180, 240), (-235, 205), (-255, 140), (-262, 60),
            (-262, -40), (-258, -110)]
HILL = outline(78, 70, n=40, wobble=5, p=3, seed=6, cx=-20, cy=42)
SUMMIT = outline(34, 28, n=26, wobble=2.5, p=2.6, seed=16, cx=-30, cy=56)
TERRACE_R = outline(52, 66, n=28, wobble=3, p=4, seed=7, cx=188, cy=-12)
TERRACE_L = outline(66, 52, n=28, wobble=3, p=4, seed=8, cx=-168, cy=176)
BUTTE = outline(36, 28, n=24, wobble=2.5, p=2.8, seed=21, cx=-178, cy=-78)
ENTRY_HEX = hexagon(STAR[0], STAR[1], 40, math.pi / 6)
GROVE = outline(58, 44, n=28, wobble=4, p=3, seed=9, cx=150, cy=-240)
FOUNTAIN1 = hexagon(10, -250, 30, math.pi / 6)
FOUNTAIN2 = hexagon(-252, -276, 22)
ARENA_PTS = circle(ARENA[0], ARENA[1], 58, 40)
SPIRAL = (-190, 190)
BELVEDERE = hexagon(-165, 190, 11)

Z_HILL, Z_SUMMIT, Z_TR, Z_TL, Z_BUTTE = 16, 30, 8, 10, 12
Z_ENTRY, Z_GROVE, Z_F1, Z_F2, Z_ARENA = -4, -10, -14, -14, -6
Z_BELVEDERE = Z_TL + 37 * 1.3

MASSIFS = [
    Massif("Left", outline(55, 190, n=90, wobble=6, p=3, seed=31, cx=-296, cy=10),
           [(-305, -140, 62, 48), (-300, -75, 85, 55), (-310, -5, 70, 50), (-298, 65, 95, 55),
            (-305, 135, 78, 50), (-300, 185, 66, 40)],
           ["amethyst", "diamond"], "cyan", seed=31),
    Massif("Corner", outline(60, 60, n=60, wobble=7, p=2.2, seed=32, cx=-292, cy=248),
           [(-300, 252, 135, 72), (-262, 276, 88, 40)],
           ["amethyst", "ruby"], "magenta", seed=32, cap_z=-1.4),
    Massif("Back", outline(190, 55, n=90, wobble=6, p=3, seed=33, cx=-90, cy=292),
           [(-230, 305, 100, 55), (-160, 312, 80, 50), (-95, 318, 56, 50), (-30, 318, 70, 45),
            (35, 310, 95, 50), (85, 300, 70, 40)],
           ["amethyst", "ruby", "diamond"], "amethyst", seed=33, cap_z=-1.8),
    Massif("Right", outline(52, 135, n=80, wobble=6, p=3, seed=34, cx=298, cy=-25),
           [(305, -130, 70, 45), (300, -70, 90, 55), (310, -5, 75, 48), (300, 60, 88, 50), (292, 100, 55, 35)],
           ["emerald", "amethyst"], "vein", seed=34, cap_z=-2.2),
]


def sky_z(x, y, z, clearance):
    """Raise a floating object so that it clears the mountains below it."""
    top = 0.0
    for m in MASSIFS:
        h = m.height(x, y)
        if h is not None:
            top = max(top, h)
    return max(z, top + clearance)


def plateau():
    cap("Sol_Plateau", PLATEAU, 0, "check_light")
    underside("Sol_Under", PLATEAU, 0, depth=18, spikes=45, rmax=22, lmax=90, gems=["amethyst", "diamond"])
    checker("Sol_Checker", PLATEAU, 0, exclude=[HILL, TERRACE_R, TERRACE_L, BUTTE] + [m.pts for m in MASSIFS])
    rasterize(PLATEAU, 0)


def raised(key, pts, z, z_below, top, flare=2.0, gem=None, rim=True, rows=3):
    """Raised level: faceted cliff down to the level below, rim, top, solid collision."""
    z_rim = z - 0.3 if rim else z
    cliff(key, pts, z_rim, z_below - 0.6, flare, rows=rows, gem=gem)
    if rim:
        cap(key, pts, z_rim, "rock_rim")
        prism(key, I, scaled(pts, 0.97), z_rim - 0.1, z, top)   # closed slab, no open sheet edge
    else:
        cap(key, pts, z, top)
    rasterize(pts, z, thickness=z - z_below)


def veins(key, starts, keep_in, keep_out, z, steps=9, width=2.4):
    """Branching green veins that crawl away from the start points."""
    for p, a in starts:
        pts = [p]
        for _ in range(steps):
            a += random.uniform(-0.6, 0.6)
            q = (p[0] + math.cos(a) * random.uniform(6, 10), p[1] + math.sin(a) * random.uniform(6, 10))
            if not inside(keep_in, *q) or (keep_out and inside(keep_out, *q)):
                break
            pts.append(q)
            if random.random() < 0.3:
                a2 = a + random.choice([-1, 1]) * random.uniform(0.7, 1.2)
                r2 = (q[0] + math.cos(a2) * 9, q[1] + math.sin(a2) * 9)
                if inside(keep_in, *r2) and not (keep_out and inside(keep_out, *r2)):
                    neon_line(key, [q, r2], z + 0.08, 1.4, "vein")
            p = q
        neon_line(key, pts, z + 0.08, width, "vein")


def hill():
    """Two-tier hill: the green vein hill of v1, now crowned by a summit and its emerald heart."""
    raised("Sol_Hill", HILL, Z_HILL, 0, "grass", flare=2.2, gem="emerald")
    inset = scaled(HILL, 0.97)
    for _ in range(14):
        x, y = random.uniform(-80, 40), random.uniform(-10, 100)
        if inside(inset, x, y) and not inside(SUMMIT, x, y):
            prism("Sol_Hill", I, outline(random.uniform(5, 12), random.uniform(4, 9), n=12, wobble=1,
                                         seed=random.randint(0, 99), cx=x, cy=y),
                  Z_HILL, Z_HILL + 0.08, random.choice(["grass_dark", "grass_light"]))
    raised("Sol_Summit", SUMMIT, Z_SUMMIT, Z_HILL, "grass_light", flare=1.8, gem="emerald")

    # veins: from the summit foot across the hill, and from the heart across the summit
    starts = []
    sc = centroid(SUMMIT)
    for b in range(8):
        a = 2 * math.pi * b / 8 + random.uniform(-0.2, 0.2)
        starts.append(((sc[0] + math.cos(a) * 40, sc[1] + math.sin(a) * 33), a))
    veins("Neon_vein_hill", starts, inset, scaled(SUMMIT, 1.12), Z_HILL)
    top = [((sc[0] + random.uniform(-3, 3), sc[1] + random.uniform(-3, 3)), 2 * math.pi * b / 6) for b in range(6)]
    veins("Neon_vein_hill", top, scaled(SUMMIT, 0.95), None, Z_SUMMIT, steps=4, width=2.0)
    alive("Neon_vein_hill", period=3.5, pulse=0.5)
    for p in ((-20, 42), (-75, 60), (22, 18), (-10, 95)):
        light((p[0], p[1], Z_HILL + 8), C_GREEN, 7000, 4, pulse=0.35)
    fx("vein", (-20, 42, Z_HILL + 1), (140, 130, 2), colour=C_GREEN)

    # emerald heart: ring of emerald crystals and a big cut gem turning above the summit
    for b in range(6):
        a = 2 * math.pi * b / 6 + 0.3
        crystal_cluster("Decor_Summit", (sc[0] + math.cos(a) * 15, sc[1] + math.sin(a) * 12, Z_SUMMIT), 0.55,
                        "emerald", n=3, up=(math.cos(a) * 0.3, math.sin(a) * 0.3, 1))
    floating_gem("Decor_Sky_GemSummit", (sc[0], sc[1], Z_SUMMIT + 15), 6.5, "emerald", spin=0.6, power=14000)

    # crystal clusters on the hill and on its cliffs
    for x, y, t, g in ((-68, 70, 1.8, "amethyst"), (-72, 20, 1.3, "amethyst"), (22, 88, 1.5, "amethyst"),
                       (35, 40, 1.2, "diamond"), (-82, 90, 1.1, "amethyst"), (5, -8, 1.0, "amethyst"),
                       (-45, 5, 0.9, "emerald")):
        if inside(inset, x, y) and not inside(scaled(SUMMIT, 1.1), x, y):
            crystal_cluster(chunk("Decor", x, y), (x, y, Z_HILL), t, g)
    for x, y, t in ((-68, 70, 1.8), (22, 88, 1.5), (-72, 20, 1.3)):
        light((x, y, Z_HILL + 12 * t), C_VIOLET, 4000, 2)
    for i in range(0, len(HILL), 4):
        x, y = HILL[i]
        crystal_cluster(chunk("Decor", x, y), (x, y, random.uniform(3, 10)), 0.6, n=3, lean=0.9)
    for _ in range(50):                                          # grass tufts
        x, y = random.uniform(-95, 55), random.uniform(-25, 110)
        if inside(inset, x, y) and not inside(scaled(SUMMIT, 1.1), x, y):
            ch.cylinder(chunk("Decor", x, y), T(x, y, Z_HILL), 0.9, 2.6, "grass_light", radius2=0.1, segs=5)


def black_hole_and_arena():
    cx, cy, r = HOLE
    ch.cylinder("Decor_Hole_Disk", T(cx, cy, -60), r + 6, 2, "black", segs=40)
    # accretion disc: dashed arcs turning in opposite directions, plus orbiting shards
    dashed_ring("Neon_magenta_hole", T(cx, cy, -58), r - 8, r + 4, 0, 0.6, "magenta", arcs=9)
    dashed_ring("Neon_cyan_hole", T(cx, cy, -57.5), r - 24, r - 16, 0, 0.5, "cyan", arcs=7, fill=0.5)
    ring("Neon_pink_hole", T(cx, cy, -58.5), 10, 16, 0, 0.5, "pink", n=32)
    alive("Neon_magenta_hole", spin=0.22, pivot=(cx, cy, -58), pulse=0.35, period=2.8)
    alive("Neon_cyan_hole", spin=-0.38, pivot=(cx, cy, -58), pulse=0.35, period=3.6)
    alive("Neon_pink_hole", pulse=0.6, period=1.8)
    for _ in range(28):
        a = random.uniform(0, 2 * math.pi)
        rr = random.uniform(40, 78)
        shard("Decor_Sky_HoleShards", (cx + rr * math.cos(a), cy + rr * math.sin(a), random.uniform(-45, -10)),
              random.uniform(1, 3))
    alive("Decor_Sky_HoleShards", spin=0.16, pivot=(cx, cy, -30))
    light((cx, cy, -45), C_PINK, 20000, 10, pulse=0.4)
    fx("rise", (cx, cy, -52), (130, 130, 2), colour=(1.0, 0.35, 0.85))

    # boss platform (object "Sol_Arene" is a landmark of the installer: keep the name)
    ax, ay = ARENA
    ch.cylinder("Sol_Arene", T(ax, ay, Z_ARENA - 5), 58, 5, "rock_rim", segs=40)
    ch.cylinder("Sol_Arene", T(ax, ay, Z_ARENA - 0.2), 55.5, 0.2, "check_light", segs=40)
    checker("Sol_ArenaChecker", circle(ax, ay, 54, 40), Z_ARENA, size=10, offset=(ax, ay))
    ring("Sol_Arene", T(ax, ay, Z_ARENA - 0.2), 55.5, 58, 0, 0.25, "crystal_dark", n=48)
    underside("Decor_Sky_UnderArena", ARENA_PTS, Z_ARENA - 5, depth=8, spikes=14, rmax=12, lmax=45,
              gems=["amethyst", "ruby"])
    ring("Neon_bridge_arena", T(ax, ay, Z_ARENA), 52, 53, 0, 0.1, "bridge_neon", n=48)
    for ri, c, inc, spin in ((68, "pink", 0.1, 0.05), (76, "cyan", -0.08, -0.04)):
        name = f"Neon_{c}_arena"
        ring(name, T(ax, ay, Z_ARENA + 3) @ R(inc, "X") @ R(inc * 0.6, "Y"), ri - 1, ri, -0.4, 0.8, c, n=64)
        alive(name, spin=spin, pivot=(ax, ay, Z_ARENA + 3), pulse=0.3, period=4)
    rasterize(ARENA_PTS, Z_ARENA)
    light((ax, ay, Z_ARENA + 25), C_VIOLET, 30000, 10)
    light((ax - 30, ay - 25, Z_ARENA + 12), C_PINK, 8000, 5)


def low_island(pts, z, key, top="check_light", gems=None, spikes=10):
    cap(key, pts, z, top)
    underside(key, pts, z, depth=10, spikes=spikes, rmax=10, lmax=40, gems=gems)
    rasterize(pts, z)


def bridge(a, b, width=10.0):
    """Glowing bridge between two points (may go up or down)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    side = Vector((-d.y, d.x, 0)).normalized()
    up = Vector((0, 0, 1))
    segment("Sol_Bridges", a - up * 0.6, b - up * 0.6, width, 1.2, "bridge")
    segment("Sol_Bridges", a - up * 1.6, b - up * 1.6, width * 0.6, 1.0, "rock_rim")
    for s in (-1, 1):
        o = side * (width / 2 - 0.3) * s
        segment("Neon_bridge", a + o + up * 2.6, b + o + up * 2.6, 0.5, 0.5, "bridge_neon")
        segment("Neon_bridge", a + o + up * 0.05, b + o + up * 0.05, 0.35, 0.2, "bridge_neon")
        n = max(2, int(d.length // 8))
        for i in range(n + 1):
            p = a + d * (i / n) + o
            ch.box("Sol_Bridges", T(p), (0.7, 0.7, 2.6), "bridge")
    collision(a, b, width)
    light(tuple((a + b) / 2 + up * 4), C_VIOLET, 1500, 1)


def stairs(a, b, width, steps=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    flat = Vector((d.x, d.y, 0))
    n = steps or max(3, int(abs(d.z) / 1.2))
    rot = flat.to_track_quat("Y", "Z").to_matrix().to_4x4()
    for i in range(n):
        p = a + flat * ((i + 0.5) / n)
        h = a.z + d.z * (i + 1) / n
        ch.box("Sol_Stairs", T(p.x, p.y, min(a.z, b.z) - 1) @ rot,
               (width, flat.length / n + 0.2, h - min(a.z, b.z) + 1), "stair" if i % 2 == 0 else "stair_dark")
    collision(a, b, width)


def spiral_stairs(cx, cy, z0, steps=36, radius=16):
    for i in range(steps):
        a = math.radians(i * 20)
        z = z0 + (i + 1) * 1.3
        d = Vector((math.cos(a), math.sin(a), 0))
        c = Vector((cx, cy, 0)) + d * radius
        rot = R(a, "Z")
        ch.box("Sol_Stairs", T(c.x, c.y, z - 1.2) @ rot, (11, 4.8, 1.2), "stair" if i % 2 == 0 else "stair_dark")
        ch.box("Sol_Stairs", T(c.x, c.y, z - 3.4) @ rot, (9, 3.8, 2.2), "stair_dark")
        collision(Vector((cx, cy, z)) + d * (radius - 5.5), Vector((cx, cy, z)) + d * (radius + 5.5), 4.8, 1.2)


def crystal_tower_and_belvedere():
    """The v1 'stairs to nowhere' now climb around a crystal tower to a floating lookout."""
    x, y = SPIRAL
    k = "Decor_Tower"
    ch.cylinder(k, T(x, y, Z_TL - 1) @ R(0.2, "Z"), 8, 54, "crystal", segs=6)
    ch.cylinder(k, T(x, y, Z_TL + 53) @ R(0.2, "Z"), 8, 16, "crystal_light", radius2=0.4, segs=6)
    for i in range(5):
        a = i * 1.26
        crystal_cluster(k, (x + math.cos(a) * 7, y + math.sin(a) * 7, Z_TL), 0.6, n=2,
                        up=(math.cos(a) * 0.4, math.sin(a) * 0.4, 1))
    light((x, y, Z_TL + 30), C_VIOLET, 6000, 3)
    orbit("Decor_Sky_OrbitTower", (x, y, Z_TL + 58), 13, 8, "amethyst", spin=0.3)

    # lookout: a small floating hexagon at the top of the spiral, with a topaz above it
    bx, by = centroid(BELVEDERE)
    cap("Sol_Belvedere", BELVEDERE, Z_BELVEDERE, "check_gold")
    checker("Sol_Belvedere", BELVEDERE, Z_BELVEDERE, size=5, dark="check_gold2", offset=(bx, by))
    underside("Sol_Belvedere", BELVEDERE, Z_BELVEDERE, depth=6, spikes=5, rmax=5, lmax=14, gems=["topaz"])
    rasterize(BELVEDERE, Z_BELVEDERE, thickness=3)
    for vx, vy in BELVEDERE[::2]:
        crystal_cluster("Decor_Tower", (bx + (vx - bx) * 0.82, by + (vy - by) * 0.82, Z_BELVEDERE), 0.35,
                        "topaz", n=3)
    floating_gem("Decor_Sky_GemBelvedere", (bx, by, Z_BELVEDERE + 10), 3.5, "topaz", spin=0.9, power=6000)


def butte():
    """Rocky butte on the left of the battlefield with an open diamond geode on top."""
    raised("Sol_Butte", BUTTE, Z_BUTTE, 0, "grass_dark", flare=2.0, gem="diamond")
    gx, gy = centroid(BUTTE)
    ring("Decor_Geode", T(gx, gy, Z_BUTTE), 6.5, 9.5, 0, 2.5, "rock_dark", n=14)
    for i in range(7):
        a = 2 * math.pi * i / 7
        crystal_cluster("Decor_Geode", (gx + math.cos(a) * 4.5, gy + math.sin(a) * 4.5, Z_BUTTE + 0.5), 0.5,
                        "diamond", n=2, up=(-math.cos(a) * 0.5, -math.sin(a) * 0.5, 1))
    crystal_cluster("Decor_Geode", (gx, gy, Z_BUTTE), 0.8, "diamond", n=4)
    light((gx, gy, Z_BUTTE + 6), GEM_LIGHT["diamond"], 6000, 3, pulse=0.5)
    fx("sparkle", (gx, gy, Z_BUTTE + 6), (10, 10, 8), colour=GEM_LIGHT["diamond"])
    for x, y, t, g in ((-200, -95, 0.9, "amethyst"), (-160, -60, 0.7, "diamond"), (-196, -58, 0.6, "amethyst")):
        crystal_cluster(chunk("Decor", x, y), (x, y, Z_BUTTE), t, g)
    for i in range(0, len(BUTTE), 3):
        x, y = BUTTE[i]
        crystal_cluster(chunk("Decor", x, y), (x, y, random.uniform(3, 7)), 0.5, "diamond", n=2, lean=0.9)


# ======================= COMPOSITION =======================
def compose():
    for m in MASSIFS:
        m.build()
    plateau()
    hill()
    raised("Sol_TerraceR", TERRACE_R, Z_TR, 0, "check_light", flare=1.8, gem="amethyst", rim=False, rows=2)
    checker("Sol_Checker", TERRACE_R, Z_TR, offset=(6, 6))
    raised("Sol_TerraceL", TERRACE_L, Z_TL, 0, "check_light", flare=1.8, gem="amethyst", rim=False, rows=2)
    checker("Sol_Checker", TERRACE_L, Z_TL, offset=(6, 6))
    butte()
    black_hole_and_arena()
    for m in MASSIFS:
        m.decorate()

    # --- golden entrance island + Star ---
    low_island(ENTRY_HEX, Z_ENTRY, "Sol_Entry", top="check_gold2", gems=["topaz"])
    checker("Sol_Entry", ENTRY_HEX, Z_ENTRY, size=8, dark="check_gold")
    star_pyramid(STAR[0], STAR[1], Z_ENTRY)
    light((STAR[0] + 15, STAR[1] + 10, Z_ENTRY + 3), C_GOLD, 6000, 8)

    # --- low islands: mushroom grove with the arches, fountains ---
    low_island(GROVE, Z_GROVE, "Sol_Grove", top="grass", gems=["amethyst", "emerald"])
    for x in ARCHES_X:
        crystal_arch(x, ARCHES_Y, Z_GROVE)
    for _ in range(26):
        x, y = random.uniform(100, 205), random.uniform(-280, -200)
        if inside(GROVE, x, y) and abs(y - ARCHES_Y) > 10:
            mushroom(x, y, Z_GROVE, random.uniform(1.2, 3.2))
    alive("Neon_mushroom", period=4.5, pulse=0.45)
    for p in ((110, -225), (195, -225), (150, -265)):
        light((p[0], p[1], Z_GROVE + 6), (0.4, 1.0, 0.85), 2500, 2, pulse=0.4)
    crystal_cluster(chunk("Decor", 105, -262), (105, -262, Z_GROVE), 0.9)
    crystal_cluster(chunk("Decor", 198, -258), (198, -258, Z_GROVE), 1.0, "emerald")

    low_island(FOUNTAIN1, Z_F1, "Sol_Fountain1", gems=["diamond"])
    checker("Sol_Fountain1", FOUNTAIN1, Z_F1, size=8)
    big_fountain(10, -250, Z_F1)
    low_island(FOUNTAIN2, Z_F2, "Sol_Fountain2", top="grass", gems=["diamond"], spikes=6)
    for dx, dy in ((-7, -7), (7, -7), (-7, 7), (7, 7)):
        small_fountain(-252 + dx, -276 + dy, Z_F2)
    light((-252, -276, Z_F2 + 5), C_CYAN, 3000, 2)
    alive("Neon_water", period=2.6, pulse=0.35)

    # --- bridges, ramps and stairs between the levels ---
    bridge((-160, -207, Z_ENTRY), (-150, -168, 0), 11)                 # entrance -> plateau
    bridge((150, -166, 0), (150, -198, Z_GROVE), 11)                   # plateau -> grove
    bridge((10, -178, 0), (10, -222, Z_F1), 9)                         # plateau -> fountain
    bridge((-214, -258, Z_ENTRY), (-236, -268, Z_F2), 7)               # entrance -> small fountains
    bridge((-20, -74, 0), (-20, -30, Z_HILL), 12)                      # front ramp of the hill
    bridge((42, 48, Z_HILL), (0, 56, Z_SUMMIT), 11)                    # hill -> summit
    bridge((52, 18, Z_HILL), (134, 4, Z_TR), 10)                       # hill -> right terrace
    bridge((-78, 88, Z_HILL), (-122, 134, Z_TL), 10)                   # hill -> left terrace
    bridge((40, 92, Z_HILL), (112, 140, Z_ARENA), 12)                  # hill -> boss arena
    bridge((202, 100, 0), (190, 124, Z_ARENA), 10)                     # plateau -> arena
    bridge((-108, -80, 0), (-146, -78, Z_BUTTE), 11)                   # plateau -> butte
    alive("Neon_bridge", period=4.0, pulse=0.25)
    stairs((-122, 42, 0), (-96, 42, Z_HILL), 12)                       # left stairs of the hill
    stairs((-30, 8, Z_HILL), (-30, 33, Z_SUMMIT), 10)                  # hill -> summit, south side
    stairs((188, -104, 0), (188, -78, Z_TR), 14)                       # right terrace
    stairs((-168, 96, 0), (-168, 124, Z_TL), 14)                       # left terrace
    spiral_stairs(SPIRAL[0], SPIRAL[1], Z_TL)                          # up to the lookout
    crystal_tower_and_belvedere()

    # --- cyan circuits on the ground ---
    for path in ([(-150, -166), (-96, -120), (-60, -120), (-60, -84), (-20, -84)],
                 [(10, -176), (10, -130), (60, -130), (96, -96), (150, -96), (188, -110)],
                 [(150, -164), (150, -130), (96, -130)],
                 [(-108, -86), (-120, -30), (-120, 30)],
                 [(66, 70), (100, 70), (118, 50), (118, 20)],
                 [(-230, 100), (-190, 100), (-190, 60), (-150, 60)]):
        neon_line("Neon_cyan_circuit", path, 0.1, 1.1, "cyan")
    alive("Neon_cyan_circuit", period=5.0, pulse=0.3)

    # --- terraforming on the plateau: gem fissures, rock arches, boulders ---
    fissure([(-238, -30), (-222, -24), (-214, -8), (-196, -12)], "amethyst")
    fissure([(-70, 246), (-60, 232), (-52, 222), (-58, 205)], "amethyst")
    fissure([(252, -118), (236, -110), (222, -104), (206, -118)], "diamond")
    alive("Neon_amethyst_fissure", period=3.2, pulse=0.55)
    alive("Neon_cyan_fissure", period=2.9, pulse=0.55)
    rock_arch(-108, -140, (0.76, 0.65), gem="diamond")
    rock_arch(80, -112, (0.73, 0.69), gem="amethyst")
    for x, y, r, g in ((-232, -100, 6, "amethyst"), (-230, -52, 5, None), (-228, 88, 6.5, "diamond"),
                       (-222, 150, 5, None), (-150, 232, 6, "ruby"), (-10, 240, 5.5, None), (42, 236, 7, "amethyst"),
                       (236, -136, 6, "emerald"), (238, 70, 5.5, None), (226, 88, 4, None), (-40, -168, 4, None),
                       (130, -150, 5, "amethyst"), (-236, 20, 4.5, None)):
        boulder(chunk("Decor", x, y), (x, y, r * 0.4), r)
        if g:
            crystal_cluster(chunk("Decor", x, y), (x + r * 0.3, y, r * 0.9), 0.5, g, n=3)

    # --- props on the plateau ---
    for x, y, t, g in ((-228, -120, 1.3, "amethyst"), (-222, 60, 1.5, "diamond"), (-215, 120, 1.0, "amethyst"),
                       (220, -140, 1.2, "emerald"), (225, 80, 1.4, "amethyst"), (-120, -150, 0.8, "amethyst"),
                       (90, -150, 0.9, "diamond"), (70, 200, 1.2, "ruby"), (-60, 210, 1.1, "amethyst"),
                       (120, 100, 0.8, "amethyst")):
        crystal_cluster(chunk("Decor", x, y), (x, y, 0), t, g)
        light((x, y, 14 * t), GEM_LIGHT[g], 3000, 2)
    for x, y in ((-150, 200), (-205, 150), (-130, 160)):
        crystal_cluster(chunk("Decor", x, y), (x, y, Z_TL), 1.1)
    for x, y in ((210, -50), (215, 30), (165, 30)):
        crystal_cluster(chunk("Decor", x, y), (x, y, Z_TR), 0.9, random.choice(["amethyst", "emerald"]))
    light((190, -10, Z_TR + 12), C_VIOLET, 4000, 2)
    light((-165, 150, Z_TL + 12), C_VIOLET, 4000, 2)
    blocked = [HILL, TERRACE_R, TERRACE_L, BUTTE] + [m.pts for m in MASSIFS]
    for _ in range(30):                                          # orbs and cubes
        x, y = random.uniform(-240, 240), random.uniform(-165, 240)
        if inside(PLATEAU, x, y) and not any(inside(b, x, y) for b in blocked):
            if random.random() < 0.55:
                sphere(chunk("Decor", x, y), T(x, y, 2.2), random.uniform(1.6, 3),
                       random.choice(["crystal_dark", "crystal"]), subdiv=2)
            else:
                s = random.uniform(3, 6)
                ch.box(chunk("Decor", x, y), T(x, y, 0) @ R(random.uniform(0, 1), "Z"), (s, s, s),
                       random.choice(["crystal_dark", "rock_rim"]))
    for x, y in ((-90, -100), (95, -60), (-190, -20)):           # small rings standing on the ground
        M = T(x, y, 5) @ R(random.uniform(0, 3), "Z") @ R(math.pi / 2, "X")
        ring(chunk("Decor", x, y), M, 3.2, 4.6, -0.6, 1.2, "crystal_dark", n=18)
    lips(chunk("Decor", 105, 20), 105, 20, 5, 5)
    lips(chunk("Decor", -222, -10), -222, -10, 6, 4)
    fx("dust", (0, 20, 10), (470, 420, 16), colour=(0.75, 0.55, 1.0))

    # --- floating things: eyes, mouths, planets, rings, cubes, glitches ---
    for i, (x, y, z, r) in enumerate(((-150, 110, 60, 9), (-95, 160, 75, 6), (-215, 160, 50, 7), (240, 180, 45, 8),
                                      (-40, 140, 90, 5), (60, -40, 70, 6), (262, -20, 60, 7), (-270, -150, 40, 6))):
        eye(f"Decor_Sky_Eye_{i + 1}", x, y, sky_z(x, y, z, r * 1.6 + 8), r * 1.6)
    for i, (x, y, z, s) in enumerate(((-190, 60, 45, 6), (90, 170, 60, 5), (250, -80, 35, 6), (-60, -120, 55, 4))):
        name = f"Decor_Sky_Lips_{i + 1}"
        z = sky_z(x, y, z, s * 3 + 6)
        lips(name, x, y, z, s * 1.5)
        alive(name, bob=1.5, period=random.uniform(4, 6), sway=0.12, pivot=(x, y, z))
    for i, (x, y, z, r, c) in enumerate(((-110, 260, 95, 10, "planet"), (40, 240, 120, 7, "planet2"),
                                         (280, 120, 90, 8, "planet2"), (-250, 230, 110, 6, "planet"))):
        planet(f"Decor_Sky_Planet_{i + 1}", x, y, sky_z(x, y, z, r * 2.5), r, c)
    for i, (x, y, z, r) in enumerate(((-140, 190, 80, 9), (-70, 150, 55, 6), (60, 150, 45, 5), (-200, -60, 60, 7),
                                      (240, -180, 60, 6))):
        floating_ring(f"Decor_Sky_Ring_{i + 1}", x, y, sky_z(x, y, z, r + 6), r)
    for i in range(18):
        x, y = random.uniform(-280, 280), random.uniform(-280, 280)
        z = sky_z(x, y, random.uniform(25, 110), 10)
        s = random.uniform(2, 5)
        c = random.choice(["crystal", "crystal_dark", "cyan"])
        name = f"Neon_cyan_cube_{i + 1}" if c == "cyan" else f"Decor_Sky_Cube_{i + 1}"
        ch.box(name, T(x, y, z) @ R(random.uniform(0, 3), "Z") @ R(random.uniform(0, 3), "X"), (s, s, s), c,
               base=False)
        axis = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        alive(name, bob=random.uniform(1, 2.5), period=random.uniform(5, 9), spin=random.uniform(0.4, 0.9),
              axis=axis, pivot=(x, y, z))
    for i, (x, y, z) in enumerate(((-230, 40, 30), (-150, 280, 70), (290, 150, 40), (270, 260, 90),
                                   (-120, -290, 20), (60, 290, 50), (-200, -300, 10), (290, -240, 25))):
        glitch(i + 1, x, y, sky_z(x, y, z, 12), random.uniform(4, 8))

    # --- big gems floating above the peaks ---
    for m, name, gem, r in ((MASSIFS[1], "Decor_Sky_GemPeak", "amethyst", 11), (MASSIFS[0], "Decor_Sky_GemLeft", "diamond", 7),
                            (MASSIFS[2], "Decor_Sky_GemBack", "ruby", 8), (MASSIFS[3], "Decor_Sky_GemRight", "emerald", 7)):
        px, py, ph, _ = max(m.peaks, key=lambda p: p[2])
        z = (m.surface_z(px, py) or ph) + 22 + r
        floating_gem(name, (px, py, z), r, gem, spin=0.35, bob=2.5, power=12000)
        if name == "Decor_Sky_GemPeak":
            orbit("Decor_Sky_OrbitPeak", (px, py, z), r * 2.4, 12, "ruby", spin=-0.2)

    # --- floating mini-mountains around the map (drifting) ---
    for i, (x, y, z, r, g) in enumerate(((-385, -60, 70, 18, "diamond"), (-362, 170, 110, 16, "amethyst"),
                                         (-200, 382, 130, 20, "ruby"), (40, 386, 118, 18, "amethyst"),
                                         (305, 232, 35, 32, "amethyst"), (238, 338, 72, 22, "ruby"),
                                         (382, -120, 60, 18, "emerald"), (332, -270, 30, 16, "diamond"),
                                         (-332, -272, 35, 15, "amethyst"), (122, -332, 12, 13, "topaz"))):
        sky_island(i + 1, x, y, z, r, g)

    # --- cosmic brain above the black hole ---
    brain(HOLE[0] + 25, HOLE[1] + 40, 118, 44)

    # --- rock and crystal shards drifting around the whole zone (three rings, three speeds) ---
    for i, (z0, z1, spin) in enumerate(((-70, 10, 0.018), (10, 90, -0.013), (90, 170, 0.01))):
        name = f"Decor_Sky_Shards_{i + 1}"
        for _ in range(34):
            a = random.uniform(0, 2 * math.pi)
            rr = random.uniform(355, 410)
            shard(name, (rr * math.cos(a), rr * math.sin(a), random.uniform(z0, z1)), random.uniform(1.5, 5))
        alive(name, spin=spin, pivot=(0, 0, (z0 + z1) / 2))
    # --- stars in three groups that twinkle out of phase ---
    for i in range(3):
        name = f"Neon_star_{i + 1}"
        for _ in range(60):
            a = random.uniform(0, 2 * math.pi)
            rr = random.uniform(430, 470)
            s = random.uniform(0.6, 1.6)
            ch.box(name, T(rr * math.cos(a), rr * math.sin(a), random.uniform(-160, 260)) @ R(0.7, "Z") @ R(0.6, "X"),
                   (s, s, s), "star", base=False)
        alive(name, period=2.4 + i * 1.1, pulse=0.8, phase=i / 3)


# ======================= BLENDER SCENE =======================
def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for d in list(coll):
            coll.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def sock(sockets, identifier):
    """Socket by identifier: names are translated in a localised Blender, identifiers are not."""
    for s in sockets:
        if s.identifier == identifier:
            return s
    raise KeyError(identifier)


def make_palette():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    size = CELLS * PX
    images = []
    for suffix, value in (("Palette", lambda n: [c / 255 for c in PALETTE[n]]),
                          ("Emission", lambda n: [EMISSION.get(n, 0.0)] * 3)):
        img = bpy.data.images.new(f"{NAME}_{suffix}", size, size)
        pix = [0.0] * (size * size * 4)
        for i, n in enumerate(COLOURS):
            c, r = i % CELLS, i // CELLS
            rgb = value(n)
            for yy in range(r * PX, (r + 1) * PX):
                for xx in range(c * PX, (c + 1) * PX):
                    j = (yy * size + xx) * 4
                    pix[j:j + 4] = (rgb[0], rgb[1], rgb[2], 1.0)
        img.pixels.foreach_set(pix)
        if suffix == "Palette":
            img.filepath_raw = os.path.join(EXPORT_DIR, f"{NAME}_Palette.png")
            img.file_format = "PNG"
            img.save()
        img.pack()
        images.append(img)
    return images


def make_material(img, mask):
    mat = bpy.data.materials.new(f"{NAME}_Palette")
    if not mat.node_tree:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.links.new(sock(tex.outputs, "Color"), sock(bsdf.inputs, "Base Color"))
    sock(bsdf.inputs, "Roughness").default_value = 0.85
    tm = nt.nodes.new("ShaderNodeTexImage")
    tm.image = mask
    tm.interpolation = "Closest"
    tm.image.colorspace_settings.name = "Non-Color"
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = 6.0
    nt.links.new(sock(tm.outputs, "Color"), mult.inputs[0])
    nt.links.new(mult.outputs[0], sock(bsdf.inputs, "Emission Strength"))
    nt.links.new(sock(tex.outputs, "Color"), sock(bsdf.inputs, "Emission Color"))
    return mat


def make_lights():
    coll = bpy.data.collections.new(f"{NAME}_Lights")
    bpy.context.scene.collection.children.link(coll)
    for i, (pos, colour, power, radius, _, _) in enumerate(LIGHTS):
        li = bpy.data.lights.new(f"Light_{i}", "POINT")
        li.color = colour
        li.energy = power
        li.shadow_soft_size = radius
        ob = bpy.data.objects.new(f"Light_{i}", li)
        ob.location = pos
        coll.objects.link(ob)


def build_objects(mat):
    colls = {}
    for n in ("Sol", "Decor", "Neon", "Star"):
        c = bpy.data.collections.new(f"{NAME}_{n}")
        bpy.context.scene.collection.children.link(c)
        colls[n] = c
    report = []

    def emit(name, b):
        me = bpy.data.meshes.new(name)
        b.to_mesh(me)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        colls[name.split("_")[0]].objects.link(ob)
        report.append((name, len(me.polygons)))

    for k in sorted(ch.bms):
        b = ch.bms[k]
        if k in ch.recalc:
            bmesh.ops.recalc_face_normals(b, faces=b.faces)
        # the triangulation projects each n-gon along its normal: it must be up to date, or a concave
        # outline (the plateau around the black hole) gets filled across its notch
        b.normal_update()
        bmesh.ops.triangulate(b, faces=b.faces[:])
        if len(b.faces) <= TRI_MAX:
            emit(k, b)
        else:
            # too big for one MeshPart: split along the longest axis into equal groups
            b.faces.ensure_lookup_table()
            xs = [f.calc_center_median() for f in b.faces]
            ext = [max(v[a] for v in xs) - min(v[a] for v in xs) for a in range(3)]
            axis = ext.index(max(ext))
            order = sorted(range(len(b.faces)), key=lambda i: xs[i][axis])
            parts = math.ceil(len(order) / TRI_MAX)
            size = math.ceil(len(order) / parts)
            for p in range(parts):
                keep = set(order[p * size:(p + 1) * size])
                b2 = b.copy()
                b2.faces.ensure_lookup_table()
                bmesh.ops.delete(b2, geom=[f for i, f in enumerate(b2.faces) if i not in keep], context="FACES")
                emit(f"{k}_{p + 1}", b2)
                b2.free()
        b.free()
    return report


# ======================= ROBLOX INSTALLER =======================
CLIENT_LUA = r"""-- MapLife: client-side ambient animation for the Brainrot Fighter maps.
-- Animates every BasePart tagged "MapLife" on this player's screen only (nothing replicates, the
-- server never pays for it). The map installers create this LocalScript and set these attributes:
--   LifeBob (studs)   LifePeriod (s)   LifePhase (0-1)   LifeSpin (rad/s)   LifeAxis (Vector3)
--   LifePivot (Vector3)   LifeSway (rad)   LifeLook (Vector3: resting gaze, the part follows the player)
--   LifeGlitch (bool)   LifePulse (0-1: neon colour and light brightness breathing)
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local TAG = "MapLife"
local MAX_DISTANCE = 900 -- parts farther than this from the camera are left alone
local PULSE_INTERVAL = 1 / 20 -- colours and lights are refreshed 20 times per second at most
local GAZE_SPEED = 3

local movers = {}
local pulsers = {}
local clock = 0
local pulseClock = 0
local parts = {}
local frames = {}

local function rotationBetween(a, b)
	local axis = a:Cross(b)
	local dot = math.clamp(a:Dot(b), -1, 1)
	if axis.Magnitude < 1e-5 then
		if dot > 0 then
			return CFrame.identity
		end
		local other = if math.abs(a.Y) < 0.9 then Vector3.yAxis else Vector3.xAxis
		return CFrame.fromAxisAngle(a:Cross(other).Unit, math.pi)
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(dot))
end

local function register(inst)
	if not inst:IsA("BasePart") or movers[inst] or pulsers[inst] then
		return
	end
	local period = inst:GetAttribute("LifePeriod") or 6
	local axis = inst:GetAttribute("LifeAxis") or Vector3.yAxis
	local state = {
		rest = inst.CFrame,
		pivot = inst:GetAttribute("LifePivot") or inst.Position,
		bob = inst:GetAttribute("LifeBob") or 0,
		omega = 2 * math.pi / math.max(period, 0.5),
		phase = (inst:GetAttribute("LifePhase") or 0) * 2 * math.pi,
		spin = inst:GetAttribute("LifeSpin") or 0,
		axis = if axis.Magnitude > 1e-6 then axis.Unit else Vector3.yAxis,
		sway = inst:GetAttribute("LifeSway") or 0,
		look = inst:GetAttribute("LifeLook"),
		glitch = inst:GetAttribute("LifeGlitch") == true,
		pulse = inst:GetAttribute("LifePulse") or 0,
		color = inst.Color,
		transparency = inst.Transparency,
		gaze = CFrame.identity,
		jitter = Vector3.zero,
		nextGlitch = 0,
		lights = {},
	}
	for _, d in inst:GetDescendants() do
		if d:IsA("Light") then
			table.insert(state.lights, { light = d, brightness = d.Brightness })
		end
	end
	if state.bob ~= 0 or state.spin ~= 0 or state.sway ~= 0 or state.look or state.glitch then
		movers[inst] = state
	end
	if state.pulse > 0 then
		pulsers[inst] = state
	end
end

local function unregister(inst)
	movers[inst] = nil
	pulsers[inst] = nil
end

local function focusPoint(camera)
	local character = Players.LocalPlayer.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if root then
		return root.Position + Vector3.new(0, 1.5, 0)
	end
	return camera.CFrame.Position
end

local function step(dt)
	clock += dt
	local camera = workspace.CurrentCamera
	if not camera then
		return
	end
	local eye = camera.CFrame.Position
	local target = focusPoint(camera)
	table.clear(parts)
	table.clear(frames)
	for part, s in movers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local w = clock * s.omega + s.phase
			local rot = CFrame.identity
			if s.spin ~= 0 then
				rot = CFrame.fromAxisAngle(s.axis, clock * s.spin)
			end
			if s.sway ~= 0 then
				rot = CFrame.Angles(math.sin(w * 0.8) * s.sway, 0, math.cos(w * 0.6) * s.sway) * rot
			end
			if s.look then
				local toTarget = target - s.pivot
				if toTarget.Magnitude > 1 then
					local want = rotationBetween(s.look, toTarget.Unit)
					s.gaze = s.gaze:Lerp(want, math.min(1, dt * GAZE_SPEED))
				end
				rot = s.gaze * rot
			end
			local offset = Vector3.new(0, math.sin(w) * s.bob, 0)
			if s.glitch then
				if clock >= s.nextGlitch then
					s.nextGlitch = clock + 0.05 + math.random() * 0.6
					if math.random() < 0.55 then
						s.jitter = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 3
					else
						s.jitter = Vector3.zero
					end
					part.Transparency = if math.random() < 0.2 then 1 else s.transparency
				end
				offset += s.jitter
			end
			table.insert(parts, part)
			table.insert(frames, CFrame.new(s.pivot + offset) * rot * CFrame.new(-s.pivot) * s.rest)
		end
	end
	if #parts > 0 then
		workspace:BulkMoveTo(parts, frames, Enum.BulkMoveMode.FireCFrameChanged)
	end

	pulseClock += dt
	if pulseClock < PULSE_INTERVAL then
		return
	end
	pulseClock = 0
	for part, s in pulsers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local f = 1 + s.pulse * 0.45 * math.sin(clock * s.omega + s.phase)
			if part.Material == Enum.Material.Neon then
				local c = s.color
				part.Color = Color3.new(math.min(1, c.R * f), math.min(1, c.G * f), math.min(1, c.B * f))
			end
			for _, entry in s.lights do
				entry.light.Brightness = entry.brightness * f
			end
		end
	end
end

for _, inst in CollectionService:GetTagged(TAG) do
	register(inst)
end
CollectionService:GetInstanceAddedSignal(TAG):Connect(register)
CollectionService:GetInstanceRemovedSignal(TAG):Connect(unregister)
RunService.Heartbeat:Connect(step)
"""

TEMPLATE_LUA = r"""--[[
	BRAINROT FIGHTER - @@NAME@@ installer (standalone test map, v2: terraformed and alive)
	Paste this whole file into the Studio command bar in EDIT mode (not during Play),
	after importing @@NAME@@.fbx with the 3D Importer. Safe to run again as many times as needed.
	  - finds the imported map, anchors it, fixes its size, position and orientation
	  - @@NBC@@ invisible walkable surfaces (plateau, hill, summit, terraces, butte, islands, bridges, stairs)
	  - spawn on the golden entrance island, facing the map
	  - neon, @@NBL@@ lights, @@NBP@@ particle emitters, starry sky and violet ambience
	  - @@NBA@@ living objects, animated on each player's screen by the "MapLife" LocalScript
	The void surrounds the map: if you fall, you respawn at the entrance.
]]
local NAME = "@@NAME@@"

-- SCALE: 1 = intended size (about 600 playable studs). 0.8 = smaller, 1.2 = bigger...
local SCALE = 1
local WIDTH = @@WIDTH@@ * SCALE -- full model width (floating decor included)
local ZONE_CENTER = Vector3.new(0, 0, 0)
local OFFSET = Vector3.new(@@DX@@, @@DY@@, @@DZ@@)

-- Landmarks (original positions in studs): arena, Star, arches, spawn
local MARK_ARENA = Vector2.new(@@AX@@, @@AZ@@)
local MARK_STAR = Vector2.new(@@FX@@, @@FZ@@)
local MARK_ARCHES = Vector2.new(@@BX@@, @@BZ@@)
local SPAWN = Vector3.new(@@EX@@, @@EY@@, @@EZ@@)
local UNIQUE_MARKER = "@@MARKER@@" -- object that only exists in this map

-- If the map is grey after the import: import @@NAME@@_Palette.png (Asset Manager),
-- paste its ID here (rbxassetid://...) and run the script again.
local TEXTURE_ID = ""

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local ServerStorage = game:GetService("ServerStorage")
local StarterPlayer = game:GetService("StarterPlayer")
print("----- Installation de " .. NAME .. " -----")

-- 0. Find the imported map ------------------------------------------------------------
local function isThisMap(obj)
	return obj:FindFirstChild("Sol_Arene", true) ~= nil and obj:FindFirstChild(UNIQUE_MARKER, true) ~= nil
end
local found = {}
for _, obj in workspace:GetChildren() do
	if not obj:IsA("BasePart") and not obj:IsA("Terrain") and isThisMap(obj) then
		table.insert(found, obj)
	end
end
local m = found[1]
if not m and workspace:FindFirstChild(UNIQUE_MARKER) then
	m = Instance.new("Model")
	m.Parent = workspace
	for _, obj in workspace:GetChildren() do
		local n = obj.Name
		if n:match("^Sol_") or n:match("^Decor_") or n:match("^Neon_") or n:match("^Star_") then
			obj.Parent = m
		end
	end
end
assert(m, "❌ Map introuvable : as-tu bien importé " .. NAME .. ".fbx dans le Workspace ?")
for i = 2, #found do
	found[i].Parent = ServerStorage
	print("⚠️ Copie en trop rangée dans ServerStorage")
end
if not m:IsA("Model") then
	local model = Instance.new("Model")
	model.Parent = workspace
	for _, child in m:GetChildren() do
		child.Parent = model
	end
	m:Destroy()
	m = model
end
m.Name = NAME

-- What a previous run created is rebuilt below
for _, name in { "Collisions", "Lights", "Particles" } do
	local old = m:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
for _, d in m:GetDescendants() do
	if d.Name == "MapLight" or d.Name == "MapFx" then
		d:Destroy()
	end
end

for _, p in m:GetDescendants() do
	if p:IsA("BasePart") then
		p.Anchored = true
	end
end
print("✅ Tout est ancré")

-- Other test maps already here: move 1500 studs aside
local others = {}
for _, obj in workspace:GetChildren() do
	if obj ~= m and obj:IsA("Model") and obj:FindFirstChild("Sol_Arene", true) then
		table.insert(others, (obj:GetBoundingBox()).Position)
	end
end
local moved = true
while moved do
	moved = false
	for _, pos in others do
		if (pos * Vector3.new(1, 0, 1) - ZONE_CENTER).Magnitude < 1200 then
			ZONE_CENTER += Vector3.new(1500, 0, 0)
			moved = true
		end
	end
end
if ZONE_CENTER.X ~= 0 then
	print("ℹ️ D'autres maps sont déjà là : " .. NAME .. " est placée à X = " .. math.floor(ZONE_CENTER.X))
end

-- 1. Size and position ------------------------------------------------------------------
local cf, size = m:GetBoundingBox()
for _, p in m:GetDescendants() do
	if p:IsA("MeshPart") and math.max(p.Size.X, p.Size.Y, p.Size.Z) >= 2040 then
		warn("⚠️ Import beaucoup trop grand : réimporte le FBX en changeant l'unité d'échelle.")
		break
	end
end
local currentWidth = math.max(size.X, size.Z)
if math.abs(currentWidth - WIDTH) > 5 then
	m:ScaleTo(m:GetScale() * WIDTH / currentWidth)
	cf, size = m:GetBoundingBox()
end
m:PivotTo(CFrame.new(ZONE_CENTER + OFFSET * SCALE - cf.Position) * m:GetPivot())
print("✅ Taille : " .. math.floor(size.X) .. " x " .. math.floor(size.Z) .. " studs")

-- 2. Real orientation (from the landmarks) ------------------------------------------------
local function centerOf(name)
	local obj = m:FindFirstChild(name, true)
	if not obj then
		return nil
	end
	if obj:IsA("BasePart") then
		return obj.Position
	end
	return (obj:GetBoundingBox()).Position
end
local function v2(v)
	return Vector2.new(v.X, v.Z)
end
local function cross(a, b)
	return a.X * b.Y - a.Y * b.X
end
local Aw, Fw, Bw = centerOf("Sol_Arene"), centerOf("Star_Socle"), centerOf("Neon_arche")
local transform
local k = SCALE
if Aw and Fw then
	local a2, f2 = v2(Aw), v2(Fw)
	local ue, uw = (MARK_STAR - MARK_ARENA).Unit, (f2 - a2).Unit
	local ne, nw = Vector2.new(-ue.Y, ue.X), Vector2.new(-uw.Y, uw.X)
	k = (f2 - a2).Magnitude / (MARK_STAR - MARK_ARENA).Magnitude
	local mirror = 1
	if Bw then
		mirror = math.sign(cross(ue, MARK_ARCHES - MARK_ARENA)) * math.sign(cross(uw, v2(Bw) - a2))
		if mirror == 0 then
			mirror = 1
		end
	end
	local kk = k
	transform = function(ex, ey, ez)
		local d = Vector2.new(ex, ez) - MARK_ARENA
		local w = a2 + uw * (d:Dot(ue) * kk) + nw * (d:Dot(ne) * kk * mirror)
		return Vector3.new(w.X, ZONE_CENTER.Y + ey * kk, w.Y)
	end
	print("✅ Orientation détectée" .. (mirror < 0 and " (map inversée par l'import, corrigé)" or ""))
else
	warn("⚠️ Repères introuvables : orientation supposée standard")
	transform = function(ex, ey, ez)
		return ZONE_CENTER + Vector3.new(ex, ey, ez) * SCALE
	end
end
local function worldDir(d)
	local v = transform(d[1], d[2], d[3]) - transform(0, 0, 0)
	return if v.Magnitude > 1e-6 then v.Unit else Vector3.yAxis
end
local mapRotation = CFrame.fromMatrix(Vector3.zero, worldDir({ 1, 0, 0 }), Vector3.yAxis) -- boxes follow the map

-- 3. Invisible walkable surfaces (every level) ---------------------------------------------
local COLLISIONS = {
@@COLLISIONS@@
}
local collisionFolder = Instance.new("Folder")
collisionFolder.Name = "Collisions"
collisionFolder.Parent = m
for i, c in COLLISIONS do
	local a = transform(c[1], c[2], c[3])
	local b = transform(c[4], c[5], c[6])
	local width, thickness = c[7] * k, c[8] * k
	local length = (b - a).Magnitude
	if length > 0.05 then
		local p = Instance.new("Part")
		p.Name = "Sol_" .. i
		p.Anchored = true
		p.Transparency = 1
		p.CanCollide = true
		p.CastShadow = false
		p.Size = Vector3.new(width, thickness, length)
		p.CFrame = CFrame.lookAt((a + b) / 2, b) * CFrame.new(0, -thickness / 2, 0)
		p.Parent = collisionFolder
	end
end
print("✅ " .. #COLLISIONS .. " surfaces de collision créées")

-- Spawn on the golden island, facing the middle of the map
local spawn = m:FindFirstChild("SpawnVoid") or Instance.new("SpawnLocation")
spawn.Name = "SpawnVoid"
spawn.Anchored = true
spawn.Transparency = 1
spawn.CanCollide = false
spawn.Neutral = true
spawn.Duration = 0
spawn.Enabled = true
spawn.Size = Vector3.new(10, 1, 10)
local spawnPos = transform(SPAWN.X, SPAWN.Y, SPAWN.Z) + Vector3.new(0, 0.6, 0)
local lookAt = transform(0, SPAWN.Y, 0)
spawn.CFrame = CFrame.lookAt(spawnPos, Vector3.new(lookAt.X, spawnPos.Y, lookAt.Z))
spawn.Parent = m
for _, s in workspace:GetDescendants() do
	if s:IsA("SpawnLocation") and s ~= spawn then
		s.Enabled = false
	end
end
local baseplate = workspace:FindFirstChild("Baseplate")
if baseplate and (baseplate.Position - ZONE_CENTER).Magnitude < 800 then
	baseplate:Destroy()
end

-- 4. Parts: neon, texture, collisions -------------------------------------------------------
local NEON = {
@@NEON@@
}
local NO_COLLISION = { "^Sol_", "^Decor_Sky", "^Decor_Hole" } -- floors (handled above) and far decor
local function noCollision(name)
	for _, pattern in NO_COLLISION do
		if name:match(pattern) then
			return true
		end
	end
	return false
end
for _, p in m:GetDescendants() do
	if p:IsA("BasePart") and p.Parent ~= collisionFolder and p ~= spawn then
		local prefix = p.Name:match("^(Neon_%a+)") or p.Name
		if NEON[prefix] then
			pcall(function()
				p.TextureID = ""
			end)
			p.Color = NEON[prefix]
			p.Material = Enum.Material.Neon
			p.CastShadow = false
			p.CanCollide = (prefix == "Star_Socle")
		else
			if TEXTURE_ID ~= "" and p:IsA("MeshPart") then
				p.TextureID = TEXTURE_ID
			end
			if noCollision(p.Name) then
				p.CanCollide = false
			else
				-- mountains, rocks, crystals: nobody walks through them
				pcall(function()
					p.CollisionFidelity = Enum.CollisionFidelity.PreciseConvexDecomposition
				end)
				p.CanCollide = true
			end
		end
	end
end

-- 5. Ambience: violet night, starry sky --------------------------------------------------------
for _, e in Lighting:GetChildren() do
	if e:IsA("Atmosphere") or e:IsA("Sky") or e:IsA("PostEffect") then
		e:Destroy()
	end
end
pcall(function()
	Lighting.Technology = Enum.Technology.Future
end)
Lighting.ClockTime = 0
Lighting.Brightness = 1.2
Lighting.Ambient = Color3.fromRGB(64, 36, 110)
Lighting.OutdoorAmbient = Color3.fromRGB(96, 64, 150)
Lighting.ColorShift_Top = Color3.fromRGB(190, 140, 255)
Lighting.EnvironmentDiffuseScale = 0.5
Lighting.EnvironmentSpecularScale = 0.6
local sky = Instance.new("Sky")
sky.Name = "VoidSky"
sky.StarCount = 6000
sky.CelestialBodiesShown = false
sky.Parent = Lighting
local atmosphere = Instance.new("Atmosphere")
atmosphere.Name = "VoidAtmosphere"
atmosphere.Density = 0.3
atmosphere.Offset = 0.05
atmosphere.Color = Color3.fromRGB(120, 70, 200)
atmosphere.Decay = Color3.fromRGB(40, 12, 90)
atmosphere.Glare = 0.4
atmosphere.Haze = 1.2
atmosphere.Parent = Lighting
local colors = Instance.new("ColorCorrectionEffect")
colors.Name = "VoidColors"
colors.Saturation = 0.25
colors.Contrast = 0.12
colors.TintColor = Color3.fromRGB(236, 220, 255)
colors.Parent = Lighting
local bloom = Instance.new("BloomEffect")
bloom.Name = "VoidBloom"
bloom.Intensity = 1
bloom.Size = 32
bloom.Threshold = 0.85
bloom.Parent = Lighting

-- 6. Lights (positions exported from Blender) ------------------------------------------------
-- {x, y, z, r, g, b, power, object carrying the light (moves with it) or "", pulse}
local LIGHTS = {
@@LIGHTS@@
}
local lightFolder = Instance.new("Folder")
lightFolder.Name = "Lights"
lightFolder.Parent = m
for i, L in LIGHTS do
	local pos = transform(L[1], L[2], L[3])
	local host = if L[8] ~= "" then m:FindFirstChild(L[8], true) else nil
	local holder: Instance
	if host and host:IsA("BasePart") then
		-- carried by a moving object: the light follows it
		local attachment = Instance.new("Attachment")
		attachment.Name = "MapLight"
		attachment.Position = host.CFrame:PointToObjectSpace(pos)
		attachment.Parent = host
		holder = attachment
	else
		local support = Instance.new("Part")
		support.Name = "Light_" .. i
		support.Size = Vector3.new(0.5, 0.5, 0.5)
		support.Transparency = 1
		support.Anchored = true
		support.CanCollide = false
		support.CanQuery = false
		support.CanTouch = false
		support.Position = pos
		support.Parent = lightFolder
		if L[9] > 0 then
			support:SetAttribute("LifePulse", L[9])
			support:SetAttribute("LifePeriod", 2.5 + (i % 7) * 0.45)
			support:SetAttribute("LifePhase", (i * 0.37) % 1)
			CollectionService:AddTag(support, "MapLife")
		end
		holder = support
	end
	local pl = Instance.new("PointLight")
	pl.Color = Color3.fromRGB(L[4], L[5], L[6])
	pl.Brightness = math.clamp(L[7] / 2500, 0.8, 6)
	pl.Range = math.clamp(math.sqrt(L[7]) / 2 * k, 8, 60)
	pl.Shadows = L[7] >= 15000
	pl.Parent = holder
end
print("✅ " .. #LIGHTS .. " lumières")

-- 7. Living objects (animated by the MapLife LocalScript) ---------------------------------------
local LIFE = {
@@LIFE@@
}
local living = 0
for _, e in LIFE do
	local p = m:FindFirstChild(e.name, true)
	if p and p:IsA("BasePart") then
		p:SetAttribute("LifeBob", (e.bob or 0) * k)
		p:SetAttribute("LifePeriod", e.period or 6)
		p:SetAttribute("LifePhase", e.phase or 0)
		p:SetAttribute("LifeSpin", e.spin or 0)
		p:SetAttribute("LifeSway", e.sway or 0)
		p:SetAttribute("LifePulse", e.pulse or 0)
		p:SetAttribute("LifeGlitch", e.glitch == true)
		p:SetAttribute("LifeAxis", worldDir(e.axis or { 0, 1, 0 }))
		p:SetAttribute("LifePivot", if e.pivot then transform(e.pivot[1], e.pivot[2], e.pivot[3]) else nil)
		p:SetAttribute("LifeLook", if e.look then worldDir(e.look) else nil)
		if e.bob or e.spin or e.sway or e.look or e.glitch then
			-- moving decor is purely visual
			p.CanCollide = false
			p.CanTouch = false
			p.CanQuery = false
		end
		CollectionService:AddTag(p, "MapLife")
		living += 1
	else
		warn("⚠️ Objet animé introuvable : " .. e.name)
	end
end
print("✅ " .. living .. " objets vivants")

-- 8. Particles ---------------------------------------------------------------------------------
-- {kind, x, y, z, size x, size y, size z, object carrying the emitter or "", r, g, b}
local PARTICLES = {
@@PARTICLES@@
}
local function fade(peak)
	return NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.15, peak),
		NumberSequenceKeypoint.new(0.75, peak + 0.2),
		NumberSequenceKeypoint.new(1, 1),
	})
end
local FX = {
	dust = { rate = 10, life = NumberRange.new(8, 14), speed = NumberRange.new(0.3, 1.2), size = NumberSequence.new(0.35, 0.05),
		spread = Vector2.new(180, 180), accel = Vector3.new(0, 0.3, 0), shape = Enum.ParticleEmitterShape.Box, peak = 0.25 },
	rise = { rate = 14, life = NumberRange.new(4, 7), speed = NumberRange.new(5, 10), size = NumberSequence.new(0.9, 0.1),
		spread = Vector2.new(8, 8), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Cylinder, peak = 0.1 },
	portal = { rate = 6, life = NumberRange.new(1.5, 3), speed = NumberRange.new(0.5, 2), size = NumberSequence.new(0.5, 0),
		spread = Vector2.new(30, 30), accel = Vector3.new(0, 1, 0), shape = Enum.ParticleEmitterShape.Box, peak = 0 },
	gold = { rate = 6, life = NumberRange.new(2, 3), speed = NumberRange.new(2, 4), size = NumberSequence.new(0.6, 0),
		spread = Vector2.new(25, 25), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0 },
	vein = { rate = 6, life = NumberRange.new(2, 4), speed = NumberRange.new(1, 2.5), size = NumberSequence.new(0.5, 0),
		spread = Vector2.new(15, 15), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0.1 },
	sparkle = { rate = 5, life = NumberRange.new(0.8, 1.8), speed = NumberRange.new(0.5, 2), size = NumberSequence.new(0.7, 0),
		spread = Vector2.new(180, 180), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0 },
}
local particleFolder = Instance.new("Folder")
particleFolder.Name = "Particles"
particleFolder.Parent = m
for i, P in PARTICLES do
	local spec = FX[P[1]]
	local pos = transform(P[2], P[3], P[4])
	local host = if P[8] ~= "" then m:FindFirstChild(P[8], true) else nil
	local e = Instance.new("ParticleEmitter")
	e.Name = "MapFx"
	e.Texture = "rbxasset://textures/particles/sparkles_main.dds"
	e.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(P[9], P[10], P[11]))
	e.LightEmission = 1
	e.LightInfluence = 0
	e.Size = spec.size
	e.Transparency = fade(spec.peak)
	e.Lifetime = spec.life
	e.Rate = spec.rate
	e.Speed = spec.speed
	e.SpreadAngle = spec.spread
	e.Acceleration = spec.accel
	e.Rotation = NumberRange.new(0, 360)
	e.RotSpeed = NumberRange.new(-60, 60)
	e.EmissionDirection = Enum.NormalId.Top
	e.Shape = spec.shape
	e.ShapeStyle = Enum.ParticleEmitterShapeStyle.Volume
	if host and host:IsA("BasePart") then
		e.ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface
		e.Parent = host
	else
		local support = Instance.new("Part")
		support.Name = "Fx_" .. i
		support.Size = Vector3.new(P[5], P[6], P[7]) * k
		support.Transparency = 1
		support.Anchored = true
		support.CanCollide = false
		support.CanQuery = false
		support.CanTouch = false
		support.CastShadow = false
		support.CFrame = CFrame.new(pos) * mapRotation
		support.Parent = particleFolder
		e.Parent = support
	end
end
print("✅ " .. #PARTICLES .. " émetteurs de particules")

-- 9. Client animation script ---------------------------------------------------------------------
local SOURCE = [==[
@@CLIENT@@
]==]
local playerScripts = StarterPlayer:FindFirstChildOfClass("StarterPlayerScripts")
if playerScripts then
	local old = playerScripts:FindFirstChild("MapLife")
	if old then
		old:Destroy()
	end
	local ls = Instance.new("LocalScript")
	ls.Name = "MapLife"
	local ok = pcall(function()
		ls.Source = SOURCE
	end)
	if ok then
		ls.Parent = playerScripts
		print("✅ Script d'animation MapLife installé dans StarterPlayerScripts")
	else
		ls:Destroy()
		warn("⚠️ Impossible d'écrire le script : crée un LocalScript \"MapLife\" dans StarterPlayerScripts et colle MapLife.client.lua dedans.")
	end
else
	warn("⚠️ StarterPlayerScripts introuvable : le décor ne sera pas animé.")
end

print("✅ " .. NAME .. " prête ! Lance Play : tu apparais sur l'île dorée de l'entrée.")
"""


def bounding_box():
    mn = Vector((1e9, 1e9, 1e9))
    mx = -mn
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            mn = Vector(map(min, mn, p))
            mx = Vector(map(max, mx, p))
    return mn, mx


def rb(v):
    """Blender (x, y, z) -> Roblox (x, z, -y)."""
    return (v[0], v[2], -v[1])


def write_roblox_script(mn, mx):
    lights = []
    for p, c, w, _, host, pulse in LIGHTS:
        x, y, z = rb(p)
        lights.append('\t{%.1f, %.1f, %.1f, %d, %d, %d, %d, "%s", %.2f},' % (
            x, y, z, int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), int(w), host, pulse))
    cols = []
    for a, b, width, thick in COLLISIONS:
        cols.append("\t{%.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f}," % (*rb(a), *rb(b), width, thick))
    life = []
    for name, p in LIFE.items():
        f = [f'name = "{name}"', "period = %.2f" % p["period"], "phase = %.3f" % p["phase"]]
        if p["bob"]:
            f.append("bob = %.2f" % p["bob"])
        if p["spin"]:
            f.append("spin = %.4f" % p["spin"])
            f.append("axis = {%.3f, %.3f, %.3f}" % rb(Vector(p["axis"]).normalized()))
        if p["pivot"] is not None:
            f.append("pivot = {%.2f, %.2f, %.2f}" % rb(p["pivot"]))
        if p["sway"]:
            f.append("sway = %.3f" % p["sway"])
        if p["look"] is not None:
            f.append("look = {%.3f, %.3f, %.3f}" % rb(Vector(p["look"]).normalized()))
        if p["glitch"]:
            f.append("glitch = true")
        if p["pulse"]:
            f.append("pulse = %.2f" % p["pulse"])
        life.append("\t{ " + ", ".join(f) + " },")
    parts = []
    for kind, pos, size, host, c in PARTICLES:
        parts.append('\t{"%s", %.1f, %.1f, %.1f, %.1f, %.1f, %.1f, "%s", %d, %d, %d},' % (
            kind, *rb(pos), size.x, size.z, size.y, host, int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)))
    neon = ["\t%s = Color3.fromRGB(%d, %d, %d)," % (k, *PALETTE[v]) for k, v in NEON.items()]
    repl = {
        "@@NAME@@": NAME, "@@NBL@@": str(len(LIGHTS)), "@@NBC@@": str(len(COLLISIONS)),
        "@@NBA@@": str(len(LIFE)), "@@NBP@@": str(len(PARTICLES)),
        "@@WIDTH@@": "%.1f" % max(mx.x - mn.x, mx.y - mn.y),
        "@@DX@@": "%.2f" % ((mn.x + mx.x) / 2), "@@DY@@": "%.2f" % ((mn.z + mx.z) / 2),
        "@@DZ@@": "%.2f" % (-(mn.y + mx.y) / 2),
        "@@AX@@": str(ARENA[0]), "@@AZ@@": str(-ARENA[1]),
        "@@FX@@": str(STAR[0]), "@@FZ@@": str(-STAR[1]),
        "@@BX@@": "%.1f" % (sum(ARCHES_X) / len(ARCHES_X)), "@@BZ@@": str(-ARCHES_Y),
        "@@EX@@": str(SPAWN[0]), "@@EY@@": str(SPAWN[2]), "@@EZ@@": str(-SPAWN[1]),
        "@@MARKER@@": MARKER,
        "@@NEON@@": "\n".join(neon), "@@LIGHTS@@": "\n".join(lights), "@@COLLISIONS@@": "\n".join(cols),
        "@@LIFE@@": "\n".join(life), "@@PARTICLES@@": "\n".join(parts),
        "@@CLIENT@@": CLIENT_LUA.rstrip("\n"),
    }
    lua = TEMPLATE_LUA
    for a, b in repl.items():
        lua = lua.replace(a, b)
    with open(os.path.join(EXPORT_DIR, f"{NAME}_Test.lua"), "w", encoding="utf-8") as f:
        f.write(lua)
    with open(os.path.join(EXPORT_DIR, "MapLife.client.lua"), "w", encoding="utf-8") as f:
        f.write(CLIENT_LUA)


def export_fbx():
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT_DIR, f"{NAME}.fbx"),
        use_selection=False, object_types={"MESH"}, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=True, axis_forward="-Z", axis_up="Y",
        apply_scale_options="FBX_SCALE_NONE", global_scale=1.0)


# ======================= SELF CHECKS =======================
def self_checks(report):
    names = {n for n, _ in report}
    passed, failed = [], []

    def check(ok, label):
        (passed if ok else failed).append(label)
        if not ok:
            print("  CHECK FAILED:", label)

    check(len(COLOURS) <= CELLS * CELLS, f"palette fits the {CELLS}x{CELLS} texture ({len(COLOURS)} colours)")
    for landmark in ("Sol_Arene", "Star_Socle", "Neon_arche", MARKER):
        check(landmark in names, f"landmark {landmark} exported as one object")
    check(all(t <= TRI_MAX for _, t in report), f"every object under {TRI_MAX} triangles")
    check(all(n in names for n in LIFE), "every living object exists (and was not split)")
    check(all(h == "" or h in names for _, _, _, _, h, _ in LIGHTS), "every light host exists")
    check(all(h == "" or h in names for _, _, _, h, _ in PARTICLES), "every particle host exists")
    check(all(n.split("_")[0] in ("Sol", "Decor", "Neon", "Star") for n in names), "every object has a known prefix")
    neon_ok = all(any(n.startswith(p) for p in NEON) for n in names if n.startswith("Neon_"))
    check(neon_ok, "every Neon_ object has a colour in the installer")
    sx, sy, sz = SPAWN
    under = any(abs(a.z - sz) < 0.01 and abs(a.y - sy) <= w / 2 and min(a.x, b.x) <= sx <= max(a.x, b.x)
                for a, b, w, _ in COLLISIONS)
    check(under, "a walkable surface lies under the spawn point")
    # the terrain must face up: an upside-down face is invisible in Roblox
    down = sum(m.down for m in MASSIFS)
    check(down == 0, f"mountain heightfields face up ({down} faces upside down)")
    # rays from above and from the four sides must always hit the FRONT of a face (Roblox hides back faces)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    backs, hits = {}, 0
    # (odd offsets keep the rays off the round coordinates of vertices, where a grazing hit is meaningless)
    rays = [(Vector((x + 0.37, y + 0.61, 400)), Vector((0, 0, -1)))
            for x in range(-340, 341, 5) for y in range(-340, 341, 5)]
    for z in (1.3, 6.3, 14.3, 24.3, 40.3, 70.3):
        for t in range(-330, 331, 4):
            t += 0.29
            rays += [(Vector((t, -500, z)), Vector((0, 1, 0))), (Vector((t, 500, z)), Vector((0, -1, 0))),
                     (Vector((-500, t, z)), Vector((1, 0, 0))), (Vector((500, t, z)), Vector((-1, 0, 0)))]
    for origin, direction in rays:
        ok, loc, nrm, _, ob, _ = scene.ray_cast(depsgraph, origin, direction)
        if ok:
            hits += 1
            if nrm.dot(direction) > 0.05:
                backs[ob.name] = backs.get(ob.name, 0) + 1
    worst = sorted(backs.items(), key=lambda kv: -kv[1])[:5]
    check(sum(backs.values()) <= hits * 0.001, f"no back face in sight ({sum(backs.values())}/{hits} rays: {worst})")
    check(len(LIGHTS) <= 130, f"light budget ({len(LIGHTS)} lights)")
    print(f"CHECKS passed={len(passed)} failed={len(failed)}")
    return not failed


# ======================= PREVIEW =======================
def prepare_ambience(mat):
    """Violet cosmic night: dark sky, cold moon, neon and bloom. Back faces are hidden like in Roblox."""
    sc = bpy.context.scene
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if os.environ.get("DEBUG_BACKFACES") == "1":
        # matt red (not emissive: a glowing back face would tint its neighbours and mislead)
        back = nt.nodes.new("ShaderNodeBsdfDiffuse")
        back.inputs[0].default_value = (1, 0, 0, 1)
    else:
        back = nt.nodes.new("ShaderNodeBsdfTransparent")
    nt.links.new(sock(geo.outputs, "Backfacing"), mix.inputs[0])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(back.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], sock(out.inputs, "Surface"))

    world = sc.world or bpy.data.worlds.new("Sky")
    sc.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.07, 0.02, 0.17, 1)
    bg.inputs[1].default_value = 1.5
    moon = bpy.data.objects.new("Moon", bpy.data.lights.new("Moon", "SUN"))
    moon.data.energy = 2.4
    moon.data.color = (0.72, 0.62, 1.0)
    moon.data.angle = math.radians(6)
    moon.rotation_euler = (math.radians(50), math.radians(-10), math.radians(-35))
    sc.collection.objects.link(moon)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.clip_end = 5000
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(os.environ.get("SAMPLES", "24"))
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        pass
    for look in ("AgX - Punchy", "Punchy"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            pass
    try:
        ng = bpy.data.node_groups.new("Bloom", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        gl = ng.nodes.new("CompositorNodeGlare")
        out = ng.nodes.new("NodeGroupOutput")
        for name_, val in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", 0.7), ("Strength", 0.8), ("Size", 0.7)):
            try:
                gl.inputs[name_].default_value = val
            except Exception:
                pass
        ng.links.new(rl.outputs[0], gl.inputs[0])
        ng.links.new(gl.outputs[0], out.inputs[0])
        sc.compositing_node_group = ng
    except Exception as e:
        print("Bloom unavailable:", e)


VIEWS = {
    "Preview_Global": ((-500, -660, 440), (10, 30, 0), 29),
    "Preview_Entrance": ((-205, -290, 20), (-60, -60, 18), 24),
    "Preview_Hill": ((80, -150, 60), (-40, 60, 28), 24),
    "Preview_Boss": ((-10, 40, 60), (170, 200, 45), 24),
    "Preview_Mountains": ((-140, -60, 40), (-300, 170, 75), 22),
    "Preview_Plan": ((0, 30, 900), None, 1000),
}


def preview():
    sc = bpy.context.scene
    cam = sc.camera
    only = os.environ.get("VIEWS")
    for name, (pos, target, lens) in VIEWS.items():
        if only and name not in only.split(","):
            continue
        cam.location = pos
        if target is None:                                    # top-down plan
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = lens
            cam.rotation_euler = (0, 0, 0)
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
            cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(EXPORT_DIR, "previews", f"{NAME}_{name}.png")
        bpy.ops.render.render(write_still=True)
    try:
        from PIL import Image
    except ImportError:
        return
    files = [os.path.join(EXPORT_DIR, "previews", f"{NAME}_{n}.png") for n in VIEWS]
    files = [f for f in files if os.path.exists(f)]
    if files:
        sheet = Image.new("RGB", (1920, 540 * math.ceil(len(files) / 2)))
        for i, f in enumerate(files):
            sheet.paste(Image.open(f).convert("RGB").resize((960, 540)), ((i % 2) * 960, (i // 2) * 540))
        sheet.save(os.path.join(EXPORT_DIR, f"{NAME}_Previews.png"))


# ======================= RUN =======================
clear_scene()
compose()
image, mask = make_palette()
material = make_material(image, mask)
report = build_objects(material)
make_lights()
mn, mx = bounding_box()
write_roblox_script(mn, mx)
export_fbx()

total = sum(t for _, t in report)
print(f"\n{len(report)} objects, {total} triangles, {len(LIGHTS)} lights, {len(COLLISIONS)} collisions, "
      f"{len(LIFE)} living objects, {len(PARTICLES)} particle emitters")
for k, t in sorted(report, key=lambda r: -r[1])[:12]:
    print(f"  {k:34s} {t:6d} tris")
print(f"Bounding box: {tuple(round(v) for v in mn)} -> {tuple(round(v) for v in mx)}")
self_checks(report)

if os.environ.get("SAVE_BLEND"):
    # saved before the preview setup, so the .blend holds exactly what was exported
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXPORT_DIR, f"{NAME}.blend"))
if RENDER_PREVIEW:
    prepare_ambience(material)
    preview()
