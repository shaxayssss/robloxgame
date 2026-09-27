"""
BRAINROT FIGHTER - PIRATE ISLAND (treasure island: one continuous terraced island, dense, alive)

Built from the reference picture of a pirate treasure island (isometric concept art) and the
level design rules that came with it:
  - distances compressed by 40 % (the isometric picture stretches them): about 360 x 340 studs
  - ONE continuous island in the sea: no floating piece, no flat plate anywhere
  - three terraces: L1 beach (spawn, z 0-4), L2 plateau (farm and transitions, z 12-17),
    L3 fortress roof (boss arena, z 31), linked by stairs cut into the cliffs, ramps and a
    grand staircase
  - a raised crater holding the giant stone skull in the middle, breaking the lines of sight
  - every gap filled with the picture's own props (palms, chests, barrels, cannons,
    cannonballs, gold, ruins, rocks) while clear lanes keep the zones connected

Outputs (in EXPORT_DIR):
  <NAME>.fbx              the map (Roblox Studio > Import 3D)
  <NAME>_Test.lua         installer to paste in the Studio command bar (EDIT mode, not Play)
  <NAME>_Palette.png      palette texture (only needed if the map imports grey)
  MapLife.client.lua      copy of the client animation script that the installer creates
  <NAME>.blend            optional (SAVE_BLEND=1)

Run from Blender: Scripting tab > New > paste this file > Run Script.
Run headless:     EXPORT_DIR=out RENDER_PREVIEW=1 SAMPLES=20 SAVE_BLEND=1 python pirate_island.py

Scale: 1 Blender unit = 1 stud. The island is centred on the origin, the spawn beach on -Y,
the fortress (boss) on +Y, Z is up and the sea surface is z = 0.
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Matrix, Vector, geometry, noise

# ======================= SETTINGS =======================
EXPORT_DIR = os.environ.get(
    "EXPORT_DIR", os.path.join(os.path.expanduser("~"), "BrainrotFighter", "PirateIsland"))
NAME = "PirateIsland"
RENDER_PREVIEW = os.environ.get("RENDER_PREVIEW", "0") == "1"
S = 480                  # extent of the chunk grid (studs)
H = S / 2
GRID = 6                 # 6 x 6 chunks of 80 studs: small MeshParts, local collision hulls
TRI_MAX = 9500           # hard cap per MeshPart (Roblox allows more, this keeps every importer happy)
OCEAN = 800              # half size of the sea around the island (terrain water in Roblox)

# Levels (z in studs, sea surface at 0)
Z_SEA_FLOOR = -14.0
Z_FOOT = 3.6             # L1: beach at the foot of the cliffs, sloping down to the sea
Z_COMPASS = 3.3          # L1: spawn plaza around the golden compass
Z_VAULT = 3.9            # L1: paved treasure vault
Z_L2 = 13.0              # L2: sand plateau (undulating)
Z_BLOCK = 18.0           # L2: grass blocks, 5 above the sand paths
Z_RIM = 23.5             # centre: rim of the skull crater
Z_CRATER = 21.0          # centre: crater floor around the skull
Z_WING = 26.0            # fortress east wing (lower than the keep)
Z_ROOF = 34.0            # L3: fortress roof = boss arena

# Landmarks read by the Roblox installer to recover the orientation (names shared by every zone)
COMPASS = (-100.0, -128.0)   # golden compass at the spawn          -> object "Star_Socle"
ARENA = (78.0, 91.0)         # fortress roof (boss arena)            -> object "Sol_Arene"
PADS = [(84, -130, 8.5), (56, -126, 6.0), (112, -124, 6.0), (68, -142, 5.0), (100, -113, 5.0)]
#                            round stone pads of the vault           -> object "Neon_arche"
SPAWN = (COMPASS[0], COMPASS[1], Z_COMPASS + 1.1)
MARKER = "Decor_SkullRock"   # object that only exists in this map

random.seed(77)
noise.seed_set(77)

# ======================= PALETTE =======================
PALETTE = {
    # sand and sea
    "sand": (240, 218, 164), "sand_light": (248, 232, 186), "sand_dark": (222, 192, 136),
    "sand_wet": (206, 176, 124), "sea_sand": (198, 204, 168), "sea_deep": (92, 132, 130),
    "foam": (248, 252, 255),
    # grass and dirt
    "grass": (116, 196, 62), "grass_dark": (72, 150, 46), "grass_light": (150, 214, 78),
    "dirt": (160, 106, 62), "dirt_dark": (118, 74, 42), "dirt_light": (184, 130, 80),
    # rock, stone, bone
    "rock": (142, 138, 134), "rock_dark": (106, 102, 100), "rock_light": (172, 168, 162),
    "stone": (168, 166, 160), "stone_dark": (130, 128, 124), "stone_light": (198, 196, 190),
    "bone": (208, 204, 194), "bone_dark": (168, 164, 154), "socket": (38, 34, 36),
    # wood, gold, iron
    "wood": (150, 96, 50), "wood_dark": (102, 62, 32), "wood_light": (188, 130, 72),
    "gold": (255, 204, 44), "gold_light": (255, 234, 122), "gold_dark": (212, 150, 22),
    "iron": (52, 54, 60), "iron_light": (86, 88, 96),
    # palms
    "trunk": (176, 128, 76), "trunk_dark": (138, 96, 56), "leaf": (104, 196, 56),
    "leaf_dark": (60, 140, 40), "leaf_light": (150, 214, 78), "coconut": (112, 72, 36),
    # compass, volcano, sky
    "cream": (250, 240, 214), "needle_red": (214, 48, 40), "needle_blue": (48, 98, 196),
    "glow": (255, 216, 96),
    "volcano": (128, 102, 86), "volcano_dark": (92, 72, 60), "volcano_light": (160, 132, 112),
    "lava": (110, 255, 90),
    "cloud": (255, 255, 255), "cloud_shade": (218, 230, 245),
}
COLOURS = list(PALETTE)
EMISSION = {"lava": 1.0, "glow": 1.0}
CELLS = 8
PX = 32
UV = {}
for _i, _n in enumerate(COLOURS):
    UV[_n] = ((_i % CELLS + 0.5) / CELLS, (_i // CELLS + 0.5) / CELLS)

# Neon objects: name prefix -> palette colour (the installer turns them into Neon parts)
NEON = {"Neon_gold": "glow", "Neon_lava": "lava"}
# Landmark kept textured although its name starts with Neon_ (the vault pads are plain carved stone)
TEXTURED_LANDMARKS = {"Neon_arche"}

STONE = ("stone", "stone_light", "stone_dark")
ROCK = ("rock", "rock_light", "rock_dark")
DIRT = ("dirt", "dirt_dark", "dirt_light")
C_GOLD = (1.0, 0.82, 0.35)
C_LAVA = (0.45, 1.0, 0.35)

# ======================= EXPORTED TABLES =======================
LIGHTS = []       # (pos, colour, power, radius, host object or "", pulse)
COLLISIONS = []   # walkable surfaces: (a, b, width, thickness, up) -> invisible Parts in Roblox
LIFE = {}         # object name -> animation parameters (read by the MapLife client script)
PARTICLES = []    # (kind, pos, size, host object or "", colour)


def light(pos, colour, power=4000, radius=1.0, host="", pulse=0.0):
    LIGHTS.append((Vector(pos), colour, power, radius, host, pulse))


def collision(a, b, width, thickness=4.0, up=(0, 0, 1)):
    """Walkable surface: a box whose TOP runs from a to b, tilted sideways to follow `up`."""
    COLLISIONS.append((Vector(a), Vector(b), width, thickness, Vector(up).normalized()))


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


def D(sx, sy, sz):
    return Matrix.Diagonal((sx, sy, sz, 1))


def align(up):
    """Rotation that sends local +Z to `up`."""
    return Vector(up).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()


I = Matrix.Identity(4)


# ======================= BUILDER =======================
class Builder:
    """Accumulates geometry per chunk key; each key becomes one MeshPart in Roblox.
    Every primitive is wound outward, so normals are never recalculated (that heuristic can flip
    open surfaces such as terrain) except for keys listed in `recalc`."""

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
        r = bmesh.ops.create_cube(b, size=1.0, matrix=M @ L @ D(sx, sy, sz))
        self.paint(b, {f for v in r["verts"] for f in v.link_faces}, colour)

    def cylinder(self, key, M, radius, height, colour, center=(0, 0, 0), radius2=None, segs=12, base=True):
        cx, cy, cz = center
        L = T(cx, cy, cz + (height / 2 if base else 0))
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
_BBOX = {}


def bbox(pts):
    b = _BBOX.get(id(pts))
    if b is None or b[4] is not pts:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = (min(xs), min(ys), max(xs), max(ys), pts)
        _BBOX[id(pts)] = b
    return b


def ccw(pts):
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    return list(pts) if area > 0 else list(reversed(pts))


def inside(pts, x, y):
    x0, y0, x1, y1, _ = bbox(pts)
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    ok = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            ok = not ok
        j = i
    return ok


def near(pts, x, y, margin):
    x0, y0, x1, y1, _ = bbox(pts)
    return x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin


def dist_to_edge(pts, x, y, closed=True):
    best = 1e9
    n = len(pts)
    for i in range(n if closed else n - 1):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def outline(half_x, half_y, n=160, wobble=6.0, p=5.0, seed=3, cx=0.0, cy=0.0):
    """Rounded square (superellipse of power p) with a slightly irregular edge, counter-clockwise."""
    rng = random.Random(seed)
    pts = []
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s_ = math.cos(t), math.sin(t)
        r = 1 / (abs(c) ** p + abs(s_) ** p) ** (1 / p)
        d = wobble * (math.sin(3 * t + ph1) + 0.6 * math.sin(7 * t + ph2)) + rng.uniform(-1.5, 1.5) * wobble / 6
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


def offset(pts, d):
    """Contour pushed outward by d (inward if d < 0)."""
    pts = ccw(pts)
    return [(x + nx * d, y + ny * d) for (x, y), (nx, ny) in zip(pts, vertex_normals(pts))]


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def n2(x, y, f, seed):
    return noise.noise(Vector((x * f, y * f, seed)))


def cut_notch(pts, q, d, width, depth):
    """Carves a straight corridor into a counter-clockwise contour, from the outside point q along
    the inward direction d, `width` wide and `depth` studs past the edge.
    Returns (new contour, edge point on the centre line, inner end of the corridor)."""
    pts = ccw(pts)
    n = len(pts)
    q, d = Vector(q), Vector(d).normalized()
    side = Vector((d.y, -d.x))

    def cross(a, b):
        return a.x * b.y - a.y * b.x

    def hit(off):
        o = q + side * off
        best = None
        for i in range(n):
            a = Vector(pts[i])
            e = Vector(pts[(i + 1) % n]) - a
            den = cross(d, e)
            if abs(den) < 1e-12:
                continue
            w = a - o
            t, u = cross(w, e) / den, cross(w, d) / den
            if 0 <= u < 1 and t > 0 and (best is None or t < best[0]):
                best = (t, i, o + d * t)
        return best

    _, il, pl = hit(-width / 2)
    _, ir, pr = hit(width / 2)
    tc, _, pc = hit(0.0)
    inner_l = q + side * (-width / 2) + d * (tc + depth)
    inner_r = q + side * (width / 2) + d * (tc + depth)
    out = [tuple(pr)] + [pts[(ir + 1 + k) % n] for k in range((il - ir) % n)] + \
          [tuple(pl), tuple(inner_l), tuple(inner_r)]
    return out, pc, q + d * (tc + depth)


def edge_y(pts, x, front=True):
    """Where a vertical line crosses a contour: the lowest crossing (front) or the highest."""
    ys = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        if (x0 <= x < x1) or (x1 <= x < x0):
            ys.append(y0 + (x - x0) / (x1 - x0) * (y1 - y0))
    return min(ys) if front else max(ys)


def pull_inside(pts, limit, margin):
    """Moves the points that come closer than `margin` to the contour `limit` towards the centre."""
    out = []
    for x, y in pts:
        v = Vector((x, y))
        for _ in range(40):
            if inside(limit, v.x, v.y) and dist_to_edge(limit, v.x, v.y) >= margin:
                break
            v *= 0.985
        out.append((v.x, v.y))
    return out


# ======================= LAYOUT =======================
SHORE = ccw(outline(174, 166, n=140, wobble=6, p=3.0, seed=11))      # the waterline
SEA_EDGE = ccw(outline(242, 234, n=110, wobble=4, p=2.6, seed=12))   # where the beach slope meets the sea floor
PLATEAU_BASE = ccw(outline(140, 128, n=110, wobble=4, p=3.2, seed=13, cx=6, cy=18))
_p, EDGE_L, TOP_L = cut_notch(PLATEAU_BASE, (-62, -260), (0, 1), 16, 12)   # stairs from the spawn beach
_p, EDGE_R, TOP_R = cut_notch(_p, (36, -260), (0, 1), 16, 12)              # stairs from the vault
_p, EDGE_W, TOP_W = cut_notch(_p, (-260, -40), (1, 0), 18, 20)             # sand ramp from the west beach
PLATEAU = ccw(_p)

MOUND_C = (-18.0, 8.0)
MOUND_R = (40.0, 36.0)
MOUND = ccw(outline(MOUND_R[0], MOUND_R[1], n=44, wobble=2.5, p=2.2, seed=51, cx=MOUND_C[0], cy=MOUND_C[1]))
RING = (MOUND_R[0] + 20, MOUND_R[1] + 20)          # sand ring around the crater (outer radii)
KEEP = rect(44, 58, 112, 124)
WING = rect(112, 66, 138, 112)
KEEP_M = rect(36, 50, 120, 132)                     # sand kept around the fortress
WING_M = rect(112, 58, 146, 120)
VOLCANO = (6.0, 186.0)
_top = [(x, min(edge_y(PLATEAU_BASE, x) - 4, -104.0)) for x in range(138, 21, -6)]
_bottom = [(x, edge_y(SHORE, x) + 13) for x in range(22, 139, 6)]
VAULT = ccw(_bottom + _top)

# Sand paths carved into the plateau (polyline, half width). Everything else on the plateau that is
# not the crater, its ring or the fortress becomes a raised grass block, as in the picture.
PATHS = [
    ([(-62, -150), (-62, -95), (-56, -60), (-50, -38)], 10),         # left stairs -> crater ring
    ([(36, -150), (36, -95), (40, -48), (44, -10)], 10),             # vault stairs -> crater ring
    ([(EDGE_W.x - 30, -40), (-106, -40), (-78, -30), (-64, -26)], 10),  # west ramp -> crater ring
    ([(-72, 36), (-124, 92)], 8),                                    # lookout to the north-west edge
    ([(-21, 60), (-21, 150)], 8),                                    # back alley
    ([(44, -44), (100, -52), (156, -58)], 8),                        # lookout to the east edge
    ([(40, 18), (80, 30), (86, 56)], 12),                            # fortress forecourt
    ([(60, 10), (60, 64)], 10),                                      # grand staircase
]
PLATEAU_EXT = offset(PLATEAU_BASE, 4)                # blocks overhang the plateau edge a little


def is_grass(x, y):
    if math.hypot((x - MOUND_C[0]) / RING[0], (y - MOUND_C[1]) / RING[1]) < 1:
        return False
    if inside(KEEP_M, x, y) or inside(WING_M, x, y) or math.hypot(x - VOLCANO[0], y - VOLCANO[1]) < 58:
        return False
    if any(dist_to_edge(line, x, y, closed=False) < hw for line, hw in PATHS):
        return False
    return inside(PLATEAU_EXT, x, y) and inside(SHORE, x, y) and dist_to_edge(SHORE, x, y) >= 15


def simplify(pts, tol):
    """Douglas-Peucker on a closed contour."""
    def dp(chain):
        if len(chain) < 3:
            return chain
        (ax, ay), (bx, by) = chain[0], chain[-1]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        far, idx = 0.0, 0
        for i in range(1, len(chain) - 1):
            d = abs((chain[i][0] - ax) * dy - (chain[i][1] - ay) * dx) / L
            if d > far:
                far, idx = d, i
        if far <= tol:
            return [chain[0], chain[-1]]
        return dp(chain[:idx + 1])[:-1] + dp(chain[idx:])
    k = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    return dp(pts[:k + 1])[:-1] + dp(pts[k:] + [pts[0]])[:-1]


def chaikin(pts, iterations=1):
    for _ in range(iterations):
        out = []
        for k in range(len(pts)):
            (ax, ay), (bx, by) = pts[k], pts[(k + 1) % len(pts)]
            out += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by), (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        pts = out
    return pts


def trace_blocks(step=2.0, x0=-150.0, y0=-130.0, x1=160.0, y1=160.0, min_area=350.0):
    """Grass mask on a grid -> outlines of its connected parts (pixel edges traced with the grass
    on the left), simplified and rounded into organic blocks."""
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    cells = [[is_grass(x0 + (i + 0.5) * step, y0 + (j + 0.5) * step) for j in range(ny)] for i in range(nx)]

    def filled(i, j):
        return 0 <= i < nx and 0 <= j < ny and cells[i][j]
    out = {}
    for i in range(nx):
        for j in range(ny):
            if cells[i][j]:
                if not filled(i, j - 1):
                    out.setdefault((i, j), []).append((i + 1, j))
                if not filled(i + 1, j):
                    out.setdefault((i + 1, j), []).append((i + 1, j + 1))
                if not filled(i, j + 1):
                    out.setdefault((i + 1, j + 1), []).append((i, j + 1))
                if not filled(i - 1, j):
                    out.setdefault((i, j + 1), []).append((i, j))
    blocks = []
    while out:
        start = next((kk for kk, v in out.items() if len(v) == 1), next(iter(out)))
        loop, cur, heading = [start], start, None
        while True:
            options = out[cur]
            if heading is None or len(options) == 1:
                nxt = options[0]
            else:                                      # touching corners: turn left, blocks stay apart
                nxt = max(options, key=lambda o: heading[0] * (o[1] - cur[1]) - heading[1] * (o[0] - cur[0]))
            options.remove(nxt)
            if not options:
                del out[cur]
            heading = (nxt[0] - cur[0], nxt[1] - cur[1])
            cur = nxt
            if cur == start:
                break
            loop.append(cur)
        pts = [(x0 + i * step, y0 + j * step) for i, j in loop]
        area = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1]
                   for k in range(len(pts))) / 2
        if area >= min_area:                           # counter-clockwise = outer outline of a block
            blocks.append(chaikin(simplify(pts, 1.6), 1))
    blocks.sort(key=lambda b: math.atan2(centroid(b)[1] - MOUND_C[1], centroid(b)[0] - MOUND_C[0]))
    return {f"Block{i + 1}": ccw(b) for i, b in enumerate(blocks)}


BLOCKS = trace_blocks()
HOLES_L2 = list(BLOCKS.values()) + [MOUND, KEEP, WING]

# Stairs, ramps and the grand staircase (a -> b)
STAIRS_L = (Vector((-62, EDGE_L.y - 22)), Vector((TOP_L.x, TOP_L.y - 1)))
STAIRS_R = (Vector((36, EDGE_R.y - 24)), Vector((TOP_R.x, TOP_R.y - 1)))
RAMP_W = (Vector((EDGE_W.x - 24, -40)), Vector((TOP_W.x - 1, -40)))
RAMP_MOUND_F = (Vector((-18, -47)), Vector((-18, -24)))
RAMP_MOUND_E = (Vector((44, 6)), Vector((18, 6)))
STAIRS_F = (Vector((60, 18)), Vector((60, 61)))

# Lanes kept free of props: the middle of every path, plus the beach ring and the spawn
LANES = [(line, max(5, hw - 3)) for line, hw in PATHS] + [
    ([COMPASS, (-62, -132)], 9),                                          # spawn -> left stairs
    ([(-18, -50), (-18, -20)], 7),                                        # crater ramp (front)
    ([(48, 6), (14, 6)], 7),                                              # crater ramp (east)
    ([(MOUND_C[0] + 50 * math.cos(a / 24 * 2 * math.pi), MOUND_C[1] + 46 * math.sin(a / 24 * 2 * math.pi))
      for a in range(25)], 6),                                            # sand ring around the crater
    (list(offset(PLATEAU_BASE, 14)) + [offset(PLATEAU_BASE, 14)[0]], 5),  # beach ring
]


# ======================= HEIGHTS =======================
def memo(fn):
    cache = {}

    def wrapped(x, y):
        k = (round(x, 2), round(y, 2))
        v = cache.get(k)
        if v is None:
            v = cache[k] = fn(x, y)
        return v
    return wrapped


@memo
def z_plateau(x, y):
    return Z_L2 + 0.9 * n2(x, y, 0.022, 3.1) + 0.45 * n2(x, y, 0.06, 7.7)


@memo
def z_block(x, y):
    return Z_BLOCK + 0.8 * n2(x, y, 0.045, 11.3) + 0.35 * n2(x, y, 0.12, 12.9)


@memo
def z_mound(x, y):
    """Raised crater: a rim at 23.5 around a floor at 21 where the skull sits."""
    q = math.hypot((x - MOUND_C[0]) / MOUND_R[0], (y - MOUND_C[1]) / MOUND_R[1])
    rim = Z_RIM + 0.35 * n2(x, y, 0.08, 13.7)
    floor = Z_CRATER + 0.2 * n2(x, y, 0.1, 17.1)
    return floor + (rim - floor) * smoothstep((q - 0.42) / 0.3)


@memo
def z_beach(x, y):
    """L1: the beach slopes from the cliff foot (3.6) to the waterline (0.25), then the sea floor."""
    if inside(SHORE, x, y):
        d_in = 0.0 if inside(PLATEAU, x, y) else dist_to_edge(PLATEAU, x, y)
        d_sh = dist_to_edge(SHORE, x, y)
        t = d_in / (d_in + d_sh + 1e-6)
        z = Z_FOOT - (Z_FOOT - 0.25) * smoothstep(t) + 0.25 * n2(x, y, 0.04, 5.5) * math.sin(math.pi * t)
    else:
        z = max(Z_SEA_FLOOR, 0.25 - 0.2 * dist_to_edge(SHORE, x, y))
    dc = math.hypot(x - COMPASS[0], y - COMPASS[1])
    if dc < 20:
        z += (Z_COMPASS - z) * smoothstep((20 - dc) / 6)
    if inside(VAULT, x, y):
        z = Z_VAULT - 0.6
    return z


def ground_z(x, y):
    """Height of the ground a prop stands on."""
    if inside(KEEP, x, y):
        return Z_ROOF
    if inside(WING, x, y):
        return Z_WING
    if inside(MOUND, x, y):
        return z_mound(x, y)
    for b in BLOCKS.values():
        if inside(b, x, y):
            return z_block(x, y)
    if inside(PLATEAU, x, y):
        return z_plateau(x, y)
    if inside(VAULT, x, y):
        return Z_VAULT
    return z_beach(x, y)


# ======================= TERRAIN MESHES =======================
def surface(prefix, outer, holes, zfn, colour, spacing=7.0, chunked=True):
    """Triangulated ground: constrained Delaunay over `outer` minus `holes`, heights from zfn and
    one colour per triangle from colour(x, y, z, normal)."""
    outer = ccw(outer)
    holes = [ccw(h) for h in holes]
    pts, edges = [], []

    def loop(poly):
        base = len(pts)
        pts.extend(Vector(p) for p in poly)
        edges.extend((base + i, base + (i + 1) % len(poly)) for i in range(len(poly)))

    loop(outer)
    for h in holes:
        loop(h)
    x0, y0, x1, y1, _ = bbox(outer)
    gx = x0 + spacing * 0.5
    while gx < x1:
        gy = y0 + spacing * 0.5
        while gy < y1:
            x = gx + random.uniform(-0.3, 0.3) * spacing
            y = gy + random.uniform(-0.3, 0.3) * spacing
            if inside(outer, x, y) and not any(inside(h, x, y) for h in holes) \
                    and dist_to_edge(outer, x, y) > spacing * 0.45 \
                    and all(dist_to_edge(h, x, y) > spacing * 0.45 for h in holes if near(h, x, y, spacing)):
                pts.append(Vector((x, y)))
            gy += spacing
        gx += spacing
    vs, _, faces, _, _, _ = geometry.delaunay_2d_cdt(pts, edges, [], 0, 1e-3)
    zs = [zfn(v.x, v.y) for v in vs]
    chunks = {}
    for f in faces:
        if len(f) != 3:
            continue
        a, b, c = f
        cx, cy = (vs[a].x + vs[b].x + vs[c].x) / 3, (vs[a].y + vs[b].y + vs[c].y) / 3
        if not inside(outer, cx, cy) or any(inside(h, cx, cy) for h in holes):
            continue
        p = [Vector((vs[i].x, vs[i].y, zs[i])) for i in (a, b, c)]
        nrm = (p[1] - p[0]).cross(p[2] - p[0])
        if nrm.length < 1e-9:
            continue
        if nrm.z < 0:
            a, b, c = a, c, b
            nrm = -nrm
        nrm.normalize()
        k = chunk(prefix, cx, cy) if chunked else prefix
        verts, index, fl, cl = chunks.setdefault(k, ([], {}, [], []))
        ids = []
        for i in (a, b, c):
            if i not in index:
                index[i] = len(verts)
                verts.append((vs[i].x, vs[i].y, zs[i]))
            ids.append(index[i])
        fl.append(tuple(ids))
        cl.append(colour(cx, cy, sum(zs[i] for i in (a, b, c)) / 3, nrm))
    for k, (verts, _, fl, cl) in chunks.items():
        ch.mesh(k, verts, fl, cl)


def cliff(key, pts, z_top, z_bot, flare, rows=3, colours=DIRT, lip="grass_dark"):
    """Faceted wall hanging from a contour: a lip, then irregular rows down to z_bot.
    z_top is a height or a function of (x, y). flare > 0 widens the foot."""
    pts = ccw(pts)
    n = len(pts)
    nrm = vertex_normals(pts)
    tops = [z_top(x, y) if callable(z_top) else z_top for x, y in pts]
    rings = [[Vector((x, y, t)) for (x, y), t in zip(pts, tops)]]
    rings.append([Vector((x + nx * 0.35, y + ny * 0.35, t - min(1.0, (t - z_bot) * 0.15)))
                  for (x, y), (nx, ny), t in zip(pts, nrm, tops)])
    for r in range(1, rows + 1):
        s = r / rows
        ring_ = []
        for (x, y), (nx, ny), t in zip(pts, nrm, tops):
            drop = min(1.0, (t - z_bot) * 0.15)
            off = flare * (0.15 + 0.85 * s ** 0.8) + random.uniform(-0.3, 0.3) * abs(flare)
            z = t - drop - (t - drop - z_bot) * s
            if r < rows:
                z += random.uniform(-1, 1) * (t - z_bot) / rows * 0.2
            ring_.append(Vector((x + nx * off, y + ny * off, z)))
        rings.append(ring_)
    verts = [v for rg in rings for v in rg]
    faces, cols = [], []
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            ui, uj, li, lj = r * n + i, r * n + j, (r + 1) * n + i, (r + 1) * n + j
            faces += [(ui, li, lj), (ui, lj, uj)]
            cols += [lip, lip] if r == 0 else [random.choice(colours), random.choice(colours)]
    ch.mesh(key, verts, faces, cols)


def wedge(key, a, b, width, z_bot, top, side, lift=0.0):
    """Solid whose top slopes from a to b (footprint: a rectangle `width` wide)."""
    a, b = Vector(a), Vector(b)
    u = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
    s = Vector((-u.y, u.x, 0)) * (width / 2)
    foot = [a - s, b - s, b + s, a + s]
    tops = [a.z + lift, b.z + lift, b.z + lift, a.z + lift]
    verts = [(p.x, p.y, t) for p, t in zip(foot, tops)] + [(p.x, p.y, z_bot) for p in foot]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4)] + [(i, 4 + i, 4 + (i + 1) % 4, (i + 1) % 4) for i in range(4)]
    ch.mesh(key, verts, faces, [top] + [side] * 5)


def rasterize(outer, holes, zfn, thickness, cell=7.0, step=2.0, tol=0.35, max_len=60.0):
    """Invisible walkable strips following the relief: rows along X, each row cut into segments
    that stay within `tol` of the ground and tilted sideways to the local slope. Where an edge
    crosses a row, the row is split in three thinner strips so that the floor reaches the edges."""
    outer = ccw(outer)
    x0, y0, x1, y1, _ = bbox(outer)
    zf = zfn if callable(zfn) else (lambda x, y: zfn)

    def ok(x, y):
        return inside(outer, x, y) and not any(inside(h, x, y) for h in holes)

    def dzdy(x, y):
        return (zf(x, y + 1) - zf(x, y - 1)) / 2

    def fits(s, e, y, width):
        za, zb = zf(s, y), zf(e, y)
        x = s + 1.0
        while x < e:
            if abs(zf(x, y) - (za + (zb - za) * (x - s) / (e - s))) > tol:
                return False
            x += 1.0
        return abs(dzdy(s, y) - dzdy(e, y)) * width / 2 <= tol

    def runs(y):
        out, start = [], None
        x = x0 + step / 2
        while x < x1 + step:
            if ok(x, y):
                if start is None:
                    start = x
            elif start is not None:
                out.append((start - step / 2, x - step / 2))
                start = None
            x += step
        return out

    def emit(row, y, width):
        for a, b in row:
            s = a
            while s < b - 0.01:
                e = min(b, s + step)
                while e < b - 0.01:
                    e2 = min(b, e + step)
                    if e2 - s > max_len or not fits(s, e2, y, width):
                        break
                    e = e2
                za, zb = zf(s, y), zf(e, y)
                up = Vector((-(zb - za) / (e - s), -dzdy((s + e) / 2, y), 1))
                th = thickness(max(za, zb)) if callable(thickness) else thickness
                collision((s, y, za), (e, y, zb), width + 0.4, th, up)
                s = e

    def intersect(a, b):
        out, i, j = [], 0, 0
        while i < len(a) and j < len(b):
            lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
            if hi - lo > 0.01:
                out.append((lo, hi))
            if a[i][1] < b[j][1]:
                i += 1
            else:
                j += 1
        return out

    def subtract(a, b):
        out = []
        for lo, hi in a:
            cur = lo
            for blo, bhi in b:
                if bhi <= cur or blo >= hi:
                    continue
                if blo - cur > 0.01:
                    out.append((cur, blo))
                cur = max(cur, bhi)
            if hi - cur > 0.01:
                out.append((cur, hi))
        return out

    n = max(1, math.ceil((y1 - y0) / cell))
    band = (y1 - y0) / n
    for k in range(n):
        y = y0 + band * (k + 0.5)
        subs = [y - band / 3, y, y + band / 3]
        rows = [runs(v) for v in subs]
        common = intersect(intersect(rows[0], rows[1]), rows[2])
        emit(common, y, band)                        # full-width strips where the whole band is floor
        for v, row in zip(subs, rows):               # thin strips only where an edge crosses the band
            emit(subtract(row, common), v, band / 3)


def sand_colour(x, y, z, nrm):
    r = random.random()
    if n2(x, y, 0.05, 21.0) > 0.3:
        return "sand_dark" if r < 0.7 else "sand"
    return "sand" if r < 0.6 else ("sand_light" if r < 0.85 else "sand_dark")


def beach_colour(x, y, z, nrm):
    if z < -7:
        return "sea_deep"
    if z < 0.2:
        return "sea_sand"
    if z < 1.0:
        return "sand_wet"
    return sand_colour(x, y, z, nrm)


def grass_colour(x, y, z, nrm):
    r = random.random()
    if n2(x, y, 0.07, 23.0) > 0.25:
        return "grass_light" if r < 0.7 else "grass"
    return "grass" if r < 0.7 else ("grass_dark" if r < 0.85 else "grass_light")


def mound_colour(x, y, z, nrm):
    r = random.random()
    if z < Z_CRATER + 0.8:
        return "sand_dark" if r < 0.6 else "sand"
    return "sand" if r < 0.45 else ("sand_dark" if r < 0.85 else "sand_light")


def paving_colour(x, y, z, nrm):
    return random.choice(STONE)


def build_terrain():
    """The one continuous island: sea floor, beach, plateau, grass blocks, skull crater."""
    square = rect(-OCEAN - 20, -OCEAN - 20, OCEAN + 20, OCEAN + 20)
    surface("Decor_Sea", square, [SEA_EDGE], z_beach, beach_colour, spacing=140, chunked=False)
    surface("Sol_Beach", SEA_EDGE, [PLATEAU], z_beach, beach_colour, spacing=7)
    surface("Sol_Plateau", PLATEAU, HOLES_L2, z_plateau, sand_colour, spacing=6)
    cliff("Sol_CliffPlateau", PLATEAU, z_plateau, 1.5, 1.6, lip="sand_dark")
    for name, pts in BLOCKS.items():
        surface(f"Sol_Block{name}", pts, [], z_block, grass_colour, spacing=6, chunked=False)
        cliff(f"Sol_Block{name}", pts, z_block, 1.5, 1.4, lip="grass_dark")
    surface("Sol_Mound", MOUND, [], z_mound, mound_colour, spacing=4.5, chunked=False)
    cliff("Sol_Mound", MOUND, z_mound, 11.0, 2.4, colours=("dirt", "dirt_dark", "rock", "dirt_light"), lip="sand_dark")
    surface("Sol_Vault", VAULT, [], lambda x, y: Z_VAULT, paving_colour, spacing=5.5, chunked=False)
    cliff("Sol_Vault", VAULT, Z_VAULT, Z_VAULT - 1.4, 0.3, rows=1, colours=STONE, lip="stone_dark")

    # walkable collisions following the relief (solid down to the level below)
    rasterize(offset(SHORE, 8), [PLATEAU, VAULT] + list(BLOCKS.values()) + [circle(*VOLCANO, 52)],
              z_beach, 4.0, tol=0.45)
    rasterize(PLATEAU, HOLES_L2, z_plateau, lambda z: z - 1.5)
    for pts in BLOCKS.values():
        rasterize(pts, [], z_block, lambda z: z - 1.5)
    rasterize(MOUND, [], z_mound, lambda z: z - 11.0, cell=5.0)
    rasterize(VAULT, [], Z_VAULT, 3.0)


def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ======================= PRIMITIVES =======================
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


def sphere(key, M, radius, colour, center=(0, 0, 0), scale=(1, 1, 1), subdiv=1):
    b = ch.bm(key)
    mat = M @ T(Vector(center)) @ D(*scale)
    r = bmesh.ops.create_icosphere(b, subdivisions=subdiv, radius=radius, matrix=mat)
    ch.paint(b, {f for v in r["verts"] for f in v.link_faces}, colour)


def facets(key, M, radius, colours, scale=(1, 1, 1), subdiv=1, jitter=0.0):
    """Icosphere with one random colour per facet (rocks, gold, clouds)."""
    b = ch.bm(key)
    res = bmesh.ops.create_icosphere(b, subdivisions=subdiv, radius=radius, matrix=M @ D(*scale))
    if jitter:
        for v in res["verts"]:
            v.co += Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * radius * jitter
    uv = b.loops.layers.uv.active
    for f in list(dict.fromkeys(f for v in res["verts"] for f in v.link_faces)):
        u, vv = UV[random.choice(colours)]
        for loop in f.loops:
            loop[uv].uv = (u, vv)


def segment(key, a, b, width, thick, colour):
    """Long box between two points."""
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    ch.box(key, T((a + b) / 2) @ rot, (width, thick, d.length + 0.2), colour, base=False)


# ======================= PROPS FROM THE PICTURE =======================
PALM_COUNT = [0]
PALM_MAX = 120


def frond(key, top, ang, length, colour, segs=3):
    """One palm leaf: a folded, drooping blade; its underside meets the top along the edges."""
    d = Vector((math.cos(ang), math.sin(ang), 0))
    side = Vector((-d.y, d.x, 0))
    width = length * 0.17
    spine, left, right = [], [], []
    for k in range(segs + 1):
        s = k / segs
        p = top + d * (length * s) + Vector((0, 0, length * (0.3 * s - 0.66 * s * s)))
        w = width * math.sin(math.pi * max(0.12, min(s, 0.95))) ** 0.7
        drop = Vector((0, 0, -0.3 * w))
        spine.append(p)
        left.append(p + side * w + drop)
        right.append(p - side * w + drop)
    verts, faces, cols = [], [], []
    for layer, under in ((0, Vector()), (1, Vector((0, 0, -0.22)))):
        ids = []
        for k in range(segs):
            ids.append(tuple(len(verts) + j for j in range(3)))
            verts += [spine[k] + under, left[k], right[k]]
        tip = len(verts)
        verts.append(spine[segs])
        tris = []
        for k in range(segs):
            s0, l0, r0 = ids[k]
            if k < segs - 1:
                s1, l1, r1 = ids[k + 1]
                tris += [(s0, s1, l1), (s0, l1, l0), (s0, r0, r1), (s0, r1, s1)]
            else:
                tris += [(s0, tip, l0), (s0, r0, tip)]
        for t in tris:
            faces.append(t if layer == 0 else (t[0], t[2], t[1]))
            cols.append(colour if layer == 0 else "leaf_dark")
    ch.mesh(key, verts, faces, cols)


def palm(x, y, z, height=None, lean=None, amount=None):
    """Curved trunk (static, collides) + crown of fronds (its own MeshPart, sways in the wind)."""
    PALM_COUNT[0] += 1
    h = height or random.uniform(14, 21)
    a = random.uniform(0, 2 * math.pi) if lean is None else lean
    amt = random.uniform(0.12, 0.32) if amount is None else amount
    d = Vector((math.cos(a), math.sin(a), 0))
    key = chunk("Decor", x, y)
    base = Vector((x, y, z - 0.6))
    pts = [base + Vector((0, 0, h * t)) + d * (h * amt * t * t) for t in [k / 5 for k in range(6)]]
    for k in range(5):
        seg = pts[k + 1] - pts[k]
        r0, r1 = 1.05 - 0.4 * k / 5, 1.05 - 0.4 * (k + 1) / 5
        ch.cylinder(key, T(pts[k]) @ align(seg), r0, seg.length + 0.2, "trunk" if k % 2 == 0 else "trunk_dark",
                    radius2=r1, segs=5)
    top = pts[-1] + Vector((0, 0, 0.3))
    crown = f"Decor_Palm_{PALM_COUNT[0]}"
    n = random.randint(6, 7)
    a0 = random.uniform(0, 2 * math.pi)
    for k in range(n):
        frond(crown, top, a0 + 2 * math.pi * k / n + random.uniform(-0.2, 0.2), random.uniform(8.5, 11.5),
              random.choice(["leaf", "leaf", "leaf_light"]))
    alive(crown, period=random.uniform(3.5, 6.0), sway=random.uniform(0.04, 0.07), pivot=tuple(top))


def chest(x, y, z, yaw, opened=False, s=1.0):
    key = chunk("Decor", x, y)
    M = T(x, y, z) @ R(yaw, "Z") @ D(s, s, s)
    ch.box(key, M, (4.0, 2.6, 2.3), "wood")
    ch.box(key, M, (4.1, 2.7, 0.3), "wood_dark")
    for bx in (-1.25, 1.25):
        ch.box(key, M, (0.4, 2.72, 2.34), "gold", center=(bx, 0, 0))
    lid = M @ T(0, 1.3, 2.3) @ R(-1.9 if opened else 0.0, "X") @ T(0, -1.3, 0)
    ch.cylinder(key, lid @ R(math.pi / 2, "Y"), 1.3, 4.0, "wood_light", segs=8, base=False)
    for bx in (-1.25, 1.25):
        ch.cylinder(key, lid @ T(bx, 0, 0) @ R(math.pi / 2, "Y"), 1.36, 0.42, "gold", segs=8, base=False)
    if opened:
        facets(key, M @ T(0, 0, 2.1), 1.0, ("gold", "gold_light", "gold_light"), scale=(1.7, 1.05, 0.6))
    else:
        ch.box(key, M, (0.6, 0.3, 0.8), "gold", center=(0, -1.38, 1.6))


def barrel(x, y, z, s=1.0, tipped=False, yaw=0.0):
    key = chunk("Decor", x, y)
    M = T(x, y, z) @ R(yaw, "Z") @ D(s, s, s)
    if tipped:
        M = M @ T(0, 0, 1.32) @ R(math.pi / 2, "X") @ T(0, 0, -1.7)
    ch.cylinder(key, M, 1.1, 1.7, "wood", radius2=1.32, segs=8)
    ch.cylinder(key, M, 1.32, 1.7, "wood_light", center=(0, 0, 1.7), radius2=1.1, segs=8)
    for zb in (0.45, 2.65):
        ch.cylinder(key, M, 1.27, 0.3, "iron", center=(0, 0, zb), segs=8)


def barrels(x, y, z, n=None):
    for k in range(n or random.randint(2, 4)):
        a = random.uniform(0, 6.28)
        r = 0 if k == 0 else random.uniform(2.4, 3.0)
        px, py = x + math.cos(a) * r, y + math.sin(a) * r
        barrel(px, py, ground_z(px, py), tipped=(k == 3 or random.random() < 0.12), yaw=random.uniform(0, 6.28))


def cannon(x, y, z, yaw):
    """Iron barrel on a wooden carriage; faces local +Y rotated by yaw."""
    key = chunk("Decor", x, y)
    M = T(x, y, z) @ R(yaw, "Z")
    ch.box(key, M, (2.6, 3.8, 1.3), "wood_dark", center=(0, 0, 0.8))
    for sx in (-1.5, 1.5):
        for sy in (-1.2, 1.2):
            ch.cylinder(key, M @ T(sx, sy, 0.95) @ R(math.pi / 2, "Y"), 0.95, 0.45, "wood", segs=10, base=False)
    gun = M @ T(0, -1.2, 2.3) @ R(-math.pi / 2 + 0.12, "X")
    ch.cylinder(key, gun, 0.95, 5.4, "iron", radius2=0.72, segs=10)
    ch.cylinder(key, gun, 0.86, 0.5, "iron_light", center=(0, 0, 5.1), segs=10)
    sphere(key, gun @ T(0, 0, -0.3), 0.6, "iron", subdiv=1)


def cannonballs(x, y, z, big=True, r=0.7):
    """Pyramid of black cannonballs."""
    key = chunk("Decor", x, y)
    n0 = 3 if big else 2
    c = Vector(((n0 - 1) * r, (n0 - 1) * r / math.sqrt(3), 0))
    for lv in range(n0):
        n = n0 - lv
        origin = Vector((lv * r, lv * r / math.sqrt(3), r + lv * r * 2 * math.sqrt(2 / 3)))
        for j in range(n):
            for i in range(n - j):
                p = origin + Vector(((i + j / 2) * 2 * r, j * math.sqrt(3) * r, 0)) - c
                sphere(key, T(x + p.x, y + p.y, z + p.z - 0.05), r, "iron", subdiv=1)


def gold_pile(x, y, z, r):
    key = chunk("Decor", x, y)
    facets(key, T(x, y, z - r * 0.12), 1.0, ("gold", "gold", "gold_light", "gold_dark"), scale=(r, r * 0.9, r * 0.5))
    for _ in range(int(3 + r)):
        a, d = random.uniform(0, 6.28), random.uniform(0.3, 1.25) * r
        px, py = x + math.cos(a) * d, y + math.sin(a) * d
        top = max(0.0, r * 0.5 * (1 - (d / r) ** 2)) if d < r else 0.0
        M = T(px, py, z + top + 0.05) @ R(random.uniform(-0.5, 0.5), "X") @ R(random.uniform(0, 3), "Z")
        ch.cylinder(key, M, 0.55, 0.14, random.choice(["gold_light", "gold"]), segs=8)


def rock(x, y, z, r, flat=0.75):
    key = chunk("Decor", x, y)
    facets(key, T(x, y, z + r * 0.25) @ R(random.uniform(0, 6.28), "Z"), r, ROCK,
           scale=(1.0, random.uniform(0.75, 1.05), flat), subdiv=1 if r > 2.2 else 0, jitter=0.12)


def rocks(x, y, n=None, rmax=3.2):
    for k in range(n or random.randint(2, 3)):
        a = random.uniform(0, 6.28)
        d = 0 if k == 0 else random.uniform(1.6, 3.2)
        px, py = x + math.cos(a) * d, y + math.sin(a) * d
        rock(px, py, ground_z(px, py), random.uniform(0.45, 1.0) * rmax)


def stone_block(x, y, z, size, yaw=0.0, tilt=0.0):
    ch.box(chunk("Decor", x, y), T(x, y, z - 0.3) @ R(yaw, "Z") @ R(tilt, "X"), size, random.choice(STONE))


def pillar(x, y, z, h, w=2.4, broken=False):
    key = chunk("Decor", x, y)
    M = T(x, y, z - 0.3)
    ch.box(key, M, (w + 0.9, w + 0.9, 1.0), "stone_dark")
    ch.box(key, M, (w, w, h), random.choice(STONE), center=(0, 0, 1.0))
    if broken:
        ch.box(key, M @ T(0.3, 0.2, h + 1.0) @ R(0.35, "Y"), (w * 0.8, w * 0.8, 1.2), "stone_light")
    else:
        ch.box(key, M, (w + 0.9, w + 0.9, 0.9), "stone_dark", center=(0, 0, h + 1.0))


def arch_gate(x, y, z, yaw, span=9.0, h=11.0):
    """Ruined stone gateway: two pillars and a lintel (left block of the picture)."""
    key = chunk("Decor", x, y)
    M = T(x, y, z - 0.3) @ R(yaw, "Z")
    for sx in (-span / 2, span / 2):
        ch.box(key, M, (3.2, 3.2, 1.0), "stone_dark", center=(sx, 0, 0))
        ch.box(key, M, (2.6, 2.6, h), "stone", center=(sx, 0, 1.0))
    ch.box(key, M, (span + 4.0, 3.0, 2.4), "stone_light", center=(0, 0, h + 1.0))
    ch.box(key, M, (span + 2.0, 2.6, 0.9), "stone_dark", center=(0, 0, h + 3.4))


def ruin_wall(x, y, z, length, yaw):
    """Broken wall: stacked blocks with an irregular top."""
    key = chunk("Decor", x, y)
    M = T(x, y, z - 0.4) @ R(yaw, "Z")
    s = -length / 2
    while s < length / 2:
        w = random.uniform(1.8, 2.8)
        for row in range(random.randint(1, 3)):
            ch.box(key, M, (w - 0.15, 1.8, 1.25), random.choice(STONE), center=(s + w / 2, 0, row * 1.3))
        s += w


def totem(x, y, z, yaw):
    """Small carved stone figure on the west beach (grey statue of the picture)."""
    key = chunk("Decor", x, y)
    M = T(x, y, z - 0.4) @ R(yaw, "Z")
    ch.box(key, M, (3.4, 3.0, 4.5), "stone")
    ch.box(key, M, (3.8, 3.4, 4.0), "stone_light", center=(0, 0, 4.5))
    ch.box(key, M, (4.2, 3.8, 0.8), "stone_dark", center=(0, 0, 8.5))
    for sx in (-0.9, 0.9):
        ch.box(key, M, (0.9, 0.4, 0.7), "socket", center=(sx, -1.75, 6.6))
    ch.box(key, M, (0.8, 0.8, 1.5), "stone", center=(0, -1.95, 5.2))
    ch.box(key, M, (2.0, 0.3, 0.35), "socket", center=(0, -1.75, 4.8))


# ======================= LANDMARK STRUCTURES =======================
def compass(x, y, z):
    """Golden compass lying on the sand: the spawn (Star_Socle), its needle turns slowly."""
    M = T(x, y, z)
    ch.cylinder("Star_Socle", M, 11.0, 0.7, "gold_dark", segs=32)
    ring("Star_Socle", M, 9.4, 11.0, 0.7, 0.5, "gold", n=40)
    ch.cylinder("Star_Socle", M, 9.4, 0.9, "cream", segs=32)
    for i in range(8):
        a = i * math.pi / 4
        long_ = i % 2 == 0
        ch.box("Star_Socle", M @ R(a, "Z"), (0.5 if long_ else 0.35, 2.2 if long_ else 1.3, 0.12), "gold_dark",
               center=(0, 7.6 if long_ else 8.0, 0.9))
    bow = M @ R(math.pi / 4, "Z") @ T(0, 12.3, 1.2) @ R(math.pi / 2, "X")
    ring("Star_Socle", bow, 1.3, 2.3, -0.4, 0.8, "gold", n=16)
    needle = "Decor_CompassNeedle"
    Mn = M @ T(0, 0, 1.0)
    ch.poly(needle, Mn, [(0, 7.2, 0.25), (-1.1, 0, 0.25), (1.1, 0, 0.25), (0, 7.2, 0), (-1.1, 0, 0), (1.1, 0, 0)],
            [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], "needle_red")
    ch.poly(needle, Mn, [(0, -7.2, 0.25), (1.1, 0, 0.25), (-1.1, 0, 0.25), (0, -7.2, 0), (1.1, 0, 0), (-1.1, 0, 0)],
            [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], "needle_blue")
    ch.cylinder(needle, Mn, 0.9, 0.6, "gold", segs=10)
    alive(needle, spin=0.35, pivot=(x, y, z + 1.2), period=8)
    ring("Neon_gold_compass", M @ T(0, 0, -0.05), 11.4, 13.6, 0, 0.2, "glow", n=48)
    alive("Neon_gold_compass", period=2.4, pulse=0.55)
    light((x, y, z + 7), C_GOLD, 5000, 3, host="Neon_gold_compass")
    fx("gold", (x, y, z + 2), (20, 20, 3), colour=C_GOLD)


def vault():
    """Treasure vault: paved floor, low stone walls, round carved pads, heaps of gold."""
    for x, y, r in PADS:
        assert inside(VAULT, x, y) and dist_to_edge(VAULT, x, y) > r + 2, f"pad {x},{y} does not fit the vault"
        M = T(x, y, Z_VAULT)
        ch.cylinder("Decor_Pads", M, r, 1.0, "stone", segs=24)
        ch.cylinder("Decor_Pads", M, r + 0.6, 0.4, "stone_dark", segs=24)
        ring("Neon_arche", M, r * 0.6, r * 0.7, 1.0, 0.12, "stone_dark", n=28)
        ring("Neon_arche", M, r * 0.25, r * 0.32, 1.0, 0.12, "stone_dark", n=16)
        for k in range(8):
            a = k * math.pi / 4
            ch.box("Neon_arche", M @ R(a, "Z"), (0.5, 1.1, 0.12), "stone_dark", center=(0, r * 0.83, 1.0))
    # walls along the sea side and the east end, open towards the spawn beach (west) and the stairs
    pts = ccw(VAULT)
    inset = offset(pts, -1.2)
    n = len(inset)
    for i in range(n):
        (x0, y0), (x1, y1) = inset[i], inset[(i + 1) % n]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        seaward = my < edge_y(PLATEAU_BASE, mx) - 12 and mx > 26
        east_end = mx > 133
        gap = 60 < mx < 72 or 100 < mx < 108
        if not (seaward or east_end) or gap:
            continue
        a, b = Vector((x0, y0, Z_VAULT)), Vector((x1, y1, Z_VAULT))
        yaw = math.atan2(y1 - y0, x1 - x0)
        ch.box("Decor_VaultWalls", T((a + b) / 2) @ R(yaw, "Z"), ((b - a).length + 0.3, 1.6, 2.8), random.choice(STONE))
        ch.box("Decor_VaultWalls", T(a), (2.4, 2.4, 3.8), "stone_dark")
    for x, y in ((26, -116), (26, -154)):                   # gate posts towards the spawn beach
        pillar(x, y, Z_VAULT, 4.5)
    for x, y, r in ((40, -150, 4.2), (122, -130, 4.5), (70, -122, 3.2), (96, -148, 3.6), (118, -116, 3.4),
                    (46, -118, 3.0), (84, -118, 2.6), (130, -120, 2.8)):
        if inside(VAULT, x, y) and dist_to_edge(VAULT, x, y) > r * 0.6:
            gold_pile(x, y, Z_VAULT, r)
            occupy(x, y, r)
    for x, y, yaw in ((33, -140, 0.3), (112, -140, -0.4), (126, -122, 2.8), (60, -156, 0.1), (98, -112, 3.0)):
        if inside(VAULT, x, y):
            chest(x, y, Z_VAULT, yaw, opened=True)
            occupy(x, y, 2.6)
    for x, y, r in PADS:
        occupy(x, y, r + 1.5)
    light((80, -134, 10), C_GOLD, 4000, 4)
    light((116, -126, 9), C_GOLD, 3000, 3)
    for x, y in ((40, -150), (122, -130), (96, -148)):
        fx("sparkle", (x, y, Z_VAULT + 3), (8, 8, 4), colour=C_GOLD)


def skull_rock(x, y, z, s=1.35):
    """Giant stone skull in the crater, facing the spawn side (-Y)."""
    k = MARKER
    M = T(x, y, z) @ D(s, s, s)
    sphere(k, M, 1.0, "bone", center=(0, 1.5, 13), scale=(10.5, 10, 9.5), subdiv=2)
    sphere(k, M, 1.0, "bone", center=(0, -4.2, 8.5), scale=(8.5, 6.5, 6.0), subdiv=2)
    for sx in (-1, 1):
        sphere(k, M, 1.0, "bone_dark", center=(sx * 6.3, -4.4, 9.2), scale=(3.2, 3.6, 3.0), subdiv=1)
        sphere(k, M, 1.0, "socket", center=(sx * 4.0, -8.9, 12.6), scale=(3.1, 1.7, 3.5), subdiv=2)
    sphere(k, M, 1.0, "socket", center=(0, -10.1, 8.9), scale=(1.3, 0.9, 1.9), subdiv=1)
    ch.box(k, M, (11.0, 7.0, 3.2), "bone_dark", center=(0, -5.0, -0.8))
    for i in range(6):
        ch.box(k, M, (1.45, 1.4, 2.2), "bone" if i % 2 else "bone_dark", center=(-4.0 + i * 1.6, -9.6, 3.8))
        ch.box(k, M, (1.45, 1.4, 1.7), "bone_dark" if i % 2 else "bone", center=(-4.0 + i * 1.6, -8.8, 2.1))
    for a in range(12):                                  # rocks piled around the skull
        ang = a * 0.52 + random.uniform(-0.2, 0.2)
        px, py = x + math.cos(ang) * random.uniform(15, 19) * s / 1.35, y + math.sin(ang) * random.uniform(14, 17) * s / 1.35
        if py < y - 8 and abs(px - x) < 9:
            continue                                     # keep the face visible
        rock(px, py, z_mound(px, py) - 0.5, random.uniform(2.2, 3.6))


def ship_wheel(x, y, z, r=15.0):
    """Giant ship's wheel lying on the fortress roof (picture) = centre of the boss arena."""
    k = "Decor_Wheel"
    M = T(x, y, z)
    ring(k, M, r - 2.2, r, 0, 1.1, "wood", n=40)
    ring(k, M, r - 3.0, r - 2.2, 0, 0.8, "wood_dark", n=40)
    ch.cylinder(k, M, 3.6, 1.5, "wood_light", segs=16)
    ch.cylinder(k, M, 1.6, 1.8, "gold", segs=12)
    for i in range(8):
        a = 2 * math.pi * i / 8
        Mi = M @ R(a, "Z")
        ch.box(k, Mi, (r - 5.8, 1.3, 0.9), "wood_light", center=((r + 1.0) / 2, 0, 0))
        ch.cylinder(k, Mi @ T(r - 0.4, 0, 0.55) @ R(math.pi / 2, "Y"), 0.55, 4.6, "wood", segs=8)
        sphere(k, Mi, 1.0, "wood_light", center=(r + 4.8, 0, 0.55), subdiv=1)


def brick_wall(key, p0, p1, z0, z1, course=3.0, length=5.5, depth=0.35, skip=None):
    """Stone blocks laid in running bond over a wall face (p0 -> p1, counter-clockwise footprint)."""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0))
    d = p1 - p0
    L = d.length
    u = d / L
    out = Vector((u.y, -u.x, 0))
    rot = R(math.atan2(u.y, u.x), "Z")
    z, row = z0, 0
    while z < z1 - 0.5:
        h = min(course, z1 - z)
        s = -length / 2 if row % 2 else 0.0
        while s < L:
            a, b = max(0.0, s), min(L, s + length)
            if b - a > 0.8:
                c = p0 + u * ((a + b) / 2) + out * (depth / 2)
                if not (skip and skip(c.x, c.y, z + h / 2)):
                    ch.box(key, T(c.x, c.y, z) @ rot, (b - a - 0.22, depth, h - 0.22), random.choice(STONE))
            s += length
        z += course
        row += 1


def parapet(key, p0, p1, z, gaps=()):
    """Low wall with merlons along a roof edge (p0 -> p1), inset inside the footprint."""
    p0, p1 = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0))
    d = p1 - p0
    L = d.length
    u = d / L
    inward = Vector((-u.y, u.x, 0)) * 0.7
    rot = R(math.atan2(u.y, u.x), "Z")
    s = 0.0
    while s < L:
        e = min(L, s + 5.5)
        c = p0 + u * ((s + e) / 2) + inward
        if not any(g0 <= c.x <= g1 and abs(c.y - gy) < 2 for g0, g1, gy in gaps):
            ch.box(key, T(c.x, c.y, z - 0.3) @ rot, (e - s, 1.4, 1.5), "stone_dark")
            if e - s > 3.2:
                ch.box(key, T(c.x, c.y, z + 1.2) @ rot, (2.8, 1.4, 1.9), random.choice(STONE))
        s = e


def fortress():
    """Stone keep (roof = boss arena with the ship's wheel), lower crenellated east wing with a
    wooden balcony, wooden door, grand staircase with side walls."""
    kc, kb = "Decor_Fortress", "Decor_FortressBricks"
    ch.box(kc, I, (68, 66, Z_ROOF - 0.3 - 10), "stone_dark", center=(78, 91, 10))
    surface("Sol_Arene", KEEP, [], lambda x, y: Z_ROOF, paving_colour, spacing=8, chunked=False)
    ch.box(kc, I, (26, 46, Z_WING - 0.3 - 10), "stone_dark", center=(125, 89, 10))
    surface("Sol_Wing", WING, [], lambda x, y: Z_WING, paving_colour, spacing=7, chunked=False)
    rasterize(KEEP, [], Z_ROOF, Z_ROOF - 10.0, tol=0.05)
    rasterize(WING, [], Z_WING, Z_WING - 10.0, tol=0.05)

    def behind_wing(x, y, z):
        return abs(x - 112) < 1 and 66 <= y <= 112 and z < Z_WING
    for (x0, y0), (x1, y1) in zip(KEEP, KEEP[1:] + KEEP[:1]):
        brick_wall(kb, (x0, y0), (x1, y1), 12.0, Z_ROOF - 0.3, skip=behind_wing)
    for (x0, y0), (x1, y1) in (((112, 66), (138, 66)), ((138, 66), (138, 112)), ((138, 112), (112, 112))):
        brick_wall(kb, (x0, y0), (x1, y1), 12.0, Z_WING - 0.3)
    for cx_, cy_ in ((44, 58), (112, 58), (44, 124), (112, 124)):       # corner turrets
        ch.box(kc, I, (7.5, 7.5, Z_ROOF + 3.5 - 10), random.choice(STONE), center=(cx_, cy_, 10))
        for dx, dy in ((-2.6, -2.6), (2.6, -2.6), (-2.6, 2.6), (2.6, 2.6)):
            ch.box(kc, I, (2.2, 2.2, 1.8), "stone_dark", center=(cx_ + dx, cy_ + dy, Z_ROOF + 3.5))
    gap = ((52.5, 67.5, 58.7),)
    for (x0, y0), (x1, y1) in zip(KEEP, KEEP[1:] + KEEP[:1]):
        parapet(kc, (x0, y0), (x1, y1), Z_ROOF, gaps=gap)
    for (x0, y0), (x1, y1) in (((112, 66), (138, 66)), ((138, 66), (138, 112)), ((138, 112), (112, 112))):
        parapet(kc, (x0, y0), (x1, y1), Z_WING)
    # wooden door with a stone frame on the keep's front
    for sx in (91.0, 101.0):
        ch.box(kc, I, (1.8, 1.4, 12.5), "stone_light", center=(sx, 57.6, z_plateau(96, 55)))
    ch.box(kc, I, (12.0, 1.6, 1.8), "stone_light", center=(96, 57.5, z_plateau(96, 55) + 12.5))
    ch.box(kc, I, (8.2, 0.6, 12.0), "wood_dark", center=(96, 57.8, z_plateau(96, 55)))
    for k in range(4):
        ch.box(kc, I, (0.25, 0.3, 11.5), "wood", center=(93.2 + k * 1.9, 57.4, z_plateau(96, 55) + 0.2))
    # wooden balcony on the wing
    zb = 17.5
    ch.box(kc, I, (18, 4.5, 0.7), "wood", center=(125, 63.7, zb))
    for px in (117, 125, 133):
        ch.box(kc, I, (0.7, 0.7, zb - z_plateau(px, 62) + 0.4), "wood_dark", center=(px, 61.8, z_plateau(px, 62) - 0.4))
        ch.box(kc, I, (0.35, 0.35, 1.5), "wood_dark", center=(px, 61.7, zb + 0.7))
    ch.box(kc, I, (18, 0.35, 0.35), "wood_dark", center=(125, 61.7, zb + 2.0))
    # grand staircase from the plateau to the roof, with side walls
    a = Vector((STAIRS_F[0].x, STAIRS_F[0].y, z_plateau(*STAIRS_F[0])))
    b = Vector((STAIRS_F[1].x, STAIRS_F[1].y, Z_ROOF))
    stone_stairs(a, b, 13)
    for sgn in (-1, 1):
        o = Vector((sgn * 7.4, 0, 0))
        wedge(kc, a + o, b + o, 1.6, a.z - 1.0, "stone_dark", "stone", lift=2.4)
    light((78, 91, Z_ROOF + 18), (1.0, 0.95, 0.85), 6000, 6)


def stone_stairs(a, b, width, key="Sol_Stairs", rise=0.8):
    """Steps cut into the ground from a (low) to b (high), with a solid collision under them."""
    a, b = Vector(a), Vector(b)
    d = b - a
    flat = Vector((d.x, d.y, 0))
    n = max(3, int(abs(d.z) / rise))
    rot = flat.to_track_quat("Y", "Z").to_matrix().to_4x4()
    base_z = min(a.z, b.z) - 2.0
    for i in range(n):
        p = a + flat * ((i + 0.5) / n)
        h = a.z + d.z * (i + 1) / n
        ch.box(key, T(p.x, p.y, base_z) @ rot, (width, flat.length / n + 0.15, h - base_z),
               "stone" if i % 2 == 0 else "stone_light")
    collision(a, b, width, abs(d.z) + 4)


def ramp(a, b, width, top="sand_dark", side="rock", key="Sol_Ramps"):
    a, b = Vector(a), Vector(b)
    wedge(key, a, b, width, min(a.z, b.z) - 2.0, top, side)
    collision(a, b, width, abs(b.z - a.z) + 4)


def volcano(cx, cy):
    """Volcano behind the fortress, rising from the sea, green glowing crater with smoke."""
    k = "Decor_Volcano"
    profile = [(62, Z_SEA_FLOOR), (57, 1.0), (45, 22), (33, 44), (22, 66), (15, 83), (12, 88)]
    segs = 18
    rings = []
    for i, (r, z) in enumerate(profile):
        rg = []
        for s in range(segs):
            a = 2 * math.pi * s / segs + (0.08 * i)
            rr = r * (1 + (random.uniform(-0.07, 0.07) if 0 < i < len(profile) - 1 else 0))
            zz = z + (random.uniform(-1.5, 1.5) if 0 < i < len(profile) - 1 else 0)
            rg.append(Vector((cx + math.cos(a) * rr, cy + math.sin(a) * rr, zz)))
        rings.append(rg)
    inner = [Vector((cx + (v.x - cx) * 0.78, cy + (v.y - cy) * 0.78, 84.0)) for v in rings[-1]]
    verts = [v for rg in rings for v in rg] + inner
    faces, cols = [], []
    for i in range(len(rings) - 1):
        for s in range(segs):
            t = (s + 1) % segs
            b0, b1, u0, u1 = i * segs + s, i * segs + t, (i + 1) * segs + s, (i + 1) * segs + t
            faces += [(b0, b1, u1), (b0, u1, u0)]
            base = "volcano" if i < 3 else ("volcano_dark" if i < 5 else "volcano_light")
            cols += [base, random.choice(["volcano", "volcano_dark", "volcano_light"])]
    top, low = (len(rings) - 1) * segs, len(rings) * segs
    for s in range(segs):
        t = (s + 1) % segs
        faces += [(top + s, top + t, low + t), (top + s, low + t, low + s)]
        cols += ["volcano_dark", "volcano_dark"]
    ch.mesh(k, verts, faces, cols)
    ch.cylinder("Neon_lava", T(cx, cy, 83.2), 9.8, 0.8, "lava", segs=18)
    alive("Neon_lava", period=3.0, pulse=0.5)
    light((cx, cy, 96), C_LAVA, 25000, 6, host="Neon_lava")
    fx("smoke", (cx, cy, 90), (14, 14, 4), colour=(0.55, 1.0, 0.45))


def clouds():
    """Cartoon clouds drifting around the island (three rings, three speeds)."""
    for g, (z0, z1, spin) in enumerate(((70, 110, 0.012), (100, 140, -0.008), (120, 170, 0.01))):
        name = f"Decor_Sky_Clouds_{g + 1}"
        for c in range(4):
            a = 2 * math.pi * (c / 4 + g / 12) + random.uniform(-0.3, 0.3)
            rr = random.uniform(460, 560)
            cx, cy, cz = rr * math.cos(a), rr * math.sin(a), random.uniform(z0, z1)
            s = random.uniform(18, 28)
            for _ in range(random.randint(5, 7)):
                p = (cx + random.uniform(-1.8, 1.8) * s, cy + random.uniform(-0.7, 0.7) * s, cz + random.uniform(0, 0.6) * s)
                facets(name, T(Vector(p)), s * random.uniform(0.6, 1.0), ("cloud", "cloud", "cloud_shade"),
                       scale=(1.3, 1.0, 0.75), subdiv=2)
        alive(name, spin=spin, pivot=(0, 0, (z0 + z1) / 2))


def foam():
    """White foam line along the waterline; it breathes up and down with the waves."""
    pts = ccw(SHORE)
    nrm = vertex_normals(pts)
    inner = [(x - nx * 1.4, y - ny * 1.4) for (x, y), (nx, ny) in zip(pts, nrm)]
    outer = [(x + nx * 1.8, y + ny * 1.8) for (x, y), (nx, ny) in zip(pts, nrm)]
    n = len(pts)
    verts = [(x, y, max(z_beach(x, y), 0.0) + 0.14) for x, y in inner] + \
            [(x, y, max(z_beach(x, y), 0.0) + 0.14) for x, y in outer]
    faces = [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]      # counter-clockwise: faces up
    ch.mesh("Decor_Foam", verts, faces, ["foam"] * n)
    alive("Decor_Foam", bob=0.12, period=4.5)


# ======================= PLACEMENT =======================
OCC = []


def occupy(x, y, r):
    OCC.append((x, y, r))


def free(x, y, r, margin=0.8):
    for ox, oy, orr in OCC:
        if abs(ox - x) < r + orr + margin and math.hypot(ox - x, oy - y) < r + orr + margin:
            return False
    for line, hw in LANES:
        if dist_to_edge(line, x, y, closed=False) < hw + r:
            return False
    return True


KINDS = {}


def place(kind, x, y, **kw):
    """Puts one prop on the ground and records its footprint."""
    KINDS[kind] = KINDS.get(kind, 0) + 1
    z = ground_z(x, y)
    if kind == "palm":
        palm(x, y, z, **kw)
        occupy(x, y, 2.2)
    elif kind == "barrels":
        barrels(x, y, z, kw.get("n"))
        occupy(x, y, 3.6)
    elif kind == "chest":
        chest(x, y, z, kw.get("yaw", random.uniform(0, 6.28)), kw.get("opened", random.random() < 0.35))
        occupy(x, y, 2.6)
    elif kind == "cannon":
        cannon(x, y, z, kw["yaw"])
        occupy(x, y, 3.4)
    elif kind == "balls":
        cannonballs(x, y, z, kw.get("big", random.random() < 0.35))
        occupy(x, y, 2.2)
    elif kind == "rocks":
        rocks(x, y, kw.get("n"), kw.get("rmax", 3.2))
        occupy(x, y, kw.get("rmax", 3.2) + 1.5)
    elif kind == "gold":
        gold_pile(x, y, z, kw.get("r", 2.5))
        occupy(x, y, kw.get("r", 2.5))
    elif kind == "ruin":
        choice = kw.get("what", random.choice(["pillar", "broken", "blocks", "wall"]))
        if choice == "pillar":
            pillar(x, y, z, random.uniform(5, 8))
        elif choice == "broken":
            pillar(x, y, z, random.uniform(2.5, 4.5), broken=True)
        elif choice == "blocks":
            for _ in range(random.randint(2, 4)):
                stone_block(x + random.uniform(-2, 2), y + random.uniform(-2, 2), z,
                            (random.uniform(1.8, 3), random.uniform(1.8, 3), random.uniform(1.2, 2.2)),
                            random.uniform(0, 1.5), random.uniform(-0.2, 0.2))
        else:
            ruin_wall(x, y, z, random.uniform(6, 10), random.uniform(0, 3.14))
        occupy(x, y, 3.2)


def outward_yaw(x, y):
    """Yaw that points a cannon (local +Y) away from the island centre."""
    return math.atan2(y, x) - math.pi / 2


def zone_points(test, spacing):
    """Jittered candidate points on a grid, shuffled."""
    pts = []
    for gx in range(-230, 231, spacing):
        for gy in range(-230, 231, spacing):
            x, y = gx + random.uniform(-0.45, 0.45) * spacing, gy + random.uniform(-0.45, 0.45) * spacing
            if test(x, y):
                pts.append((x, y))
    random.shuffle(pts)
    return pts


def fill(test, spacing, table, margin=0.8, limit=None):
    """Fills a zone: every candidate point that is free gets a prop drawn from `table`."""
    total = sum(w for _, w, _ in table)
    placed = 0
    for x, y in zone_points(test, spacing):
        if limit and placed >= limit:
            break
        r = random.uniform(0, total)
        for kind, w, radius in table:
            r -= w
            if r <= 0:
                break
        if kind == "palm" and PALM_COUNT[0] >= PALM_MAX:
            kind, radius = "rocks", 3.2
        if free(x, y, radius, margin):
            kw = {}
            if kind == "cannon":
                kw["yaw"] = outward_yaw(x, y)
            place(kind, x, y, **kw)
            placed += 1
    return placed


def on_block(name, edge=2.5):
    pts = BLOCKS[name]
    return lambda x, y: inside(pts, x, y) and dist_to_edge(pts, x, y) > edge


def on_plateau(x, y):
    return inside(PLATEAU, x, y) and not any(inside(h, x, y) for h in HOLES_L2) and \
        dist_to_edge(PLATEAU, x, y) > 3 and all(dist_to_edge(h, x, y) > 2.5 for h in HOLES_L2 if near(h, x, y, 4))


def on_beach(x, y):
    if not inside(SHORE, x, y) or dist_to_edge(SHORE, x, y) < 6 or inside(PLATEAU, x, y) or inside(VAULT, x, y):
        return False
    if any(inside(b, x, y) for b in BLOCKS.values()) or math.hypot(x - VOLCANO[0], y - VOLCANO[1]) < 60:
        return False
    return dist_to_edge(PLATEAU, x, y) > 3 and math.hypot(x - COMPASS[0], y - COMPASS[1]) > 17


STEPPED = []      # (block name, point on top) of the blocks that have steps: checked for walkability


def block_steps():
    """Stone steps from the sand paths up onto every large grass block."""
    solid = HOLES_L2
    for name, pts in BLOCKS.items():
        area = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1]
                   for k in range(len(pts))) / 2
        if area < 700:
            continue
        nrm = vertex_normals(pts)
        order = sorted(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - MOUND_C[0], pts[i][1] - MOUND_C[1]))
        for i in order:
            d = -Vector(nrm[i])
            foot = Vector(pts[i]) - d * 9
            head = Vector(pts[i]) + d * 2.5
            top = Vector(pts[i]) + d * 8
            if not inside(PLATEAU, foot.x, foot.y) or any(inside(h, foot.x, foot.y) for h in solid):
                continue
            if not (inside(pts, head.x, head.y) and inside(pts, top.x, top.y)):
                continue
            a = Vector((foot.x, foot.y, z_plateau(foot.x, foot.y)))
            b = Vector((head.x, head.y, z_block(head.x, head.y)))
            stone_stairs(a, b, 7)
            LANES.append(([tuple(foot), tuple(top)], 4.5))
            STEPPED.append((name, (top.x, top.y)))
            break


def ground_ok(x, y):
    return inside(SHORE, x, y) and not any(inside(h, x, y) for h in (VAULT, KEEP, WING, MOUND))


def hero(kind, x, y, r=3.0, **kw):
    """Places one of the picture's key props near (x, y), nudged out of the lanes if needed."""
    for rr in (0, 3, 6, 9, 12):
        for k in range(8 if rr else 1):
            px, py = x + math.cos(k * math.pi / 4) * rr, y + math.sin(k * math.pi / 4) * rr
            if ground_ok(px, py) and free(px, py, r):
                if kind == "cannon":
                    kw["yaw"] = outward_yaw(px, py)
                place(kind, px, py, **kw)
                return True
    return False


def props():
    # --- the picture's key props, where the picture shows them ---
    for x, y in ((-124, 50), (-120, 40), (-110, 58)):
        if ground_ok(x, y) and free(x, y, 7):
            arch_gate(x, y, ground_z(x, y), 0.6)
            occupy(x, y, 7)
            break
    for x, y in ((-132, 6), (-112, 120), (140, -20), (142, 26), (-12, -104), (96, -100), (-140, -70), (120, 60)):
        hero("cannon", x, y, 3.4)
    for x, y in ((-126, -8), (-94, 54), (-58, 122), (-96, 96), (138, -6), (136, 40), (-6, 104), (80, -96)):
        hero("balls", x, y, 2.2, big=True)
    for x, y in ((-84, 30), (-110, 36), (-48, 98), (-72, 88), (100, 30), (-30, -78), (10, 80), (60, -40)):
        hero("chest", x, y, 2.6)
    for x, y, what in ((-100, 60, "pillar"), (104, 32, "pillar"), (100, -30, "wall"), (122, 40, "broken"),
                       (6, -100, "broken"), (78, -70, "blocks"), (-150, -96, "blocks"), (-132, 40, "blocks")):
        hero("ruin", x, y, 3.2, what=what)
    totem(-160, -84, z_beach(-160, -84), 0.9)
    occupy(-160, -84, 3)
    for x, y in ((-172, -104), (-164, -112), (-168, -96), (-150, -150)):        # loose cannonballs on the sand
        if inside(SHORE, x, y):
            sphere(chunk("Decor", x, y), T(x, y, z_beach(x, y) + 0.5), 0.7, "iron", subdiv=2)
    for x, y in ((40, 62), (116, 58), (136, 60), (40, 110), (120, 118), (30, 128)):   # barrels by the fortress
        hero("barrels", x, y, 3.6)
    # palms leaning over the sea on the beach
    for x, y in ((-140, -120), (-70, -150), (-4, -148), (150, -84), (160, 44), (150, 110), (-156, 104),
                 (-140, 146), (-162, 10), (100, 146), (-96, 160)):
        if on_beach(x, y):
            place("palm", x, y, lean=math.atan2(y, x), amount=random.uniform(0.35, 0.5))

    # --- fill every remaining gap with the picture's props, lanes stay clear ---
    # palms first, the budget shared by area so that every block is a palm grove (as in the picture)
    areas = {name: sum(p[k][0] * p[(k + 1) % len(p)][1] - p[(k + 1) % len(p)][0] * p[k][1]
                       for k in range(len(p))) / 2 for name, p in BLOCKS.items()}
    budget = PALM_MAX - PALM_COUNT[0] - 12
    for name in BLOCKS:
        fill(on_block(name), 4, [("palm", 1, 4.0)], margin=0.4,
             limit=max(2, int(budget * areas[name] / sum(areas.values()))))
    for name in BLOCKS:
        fill(on_block(name), 7, [("barrels", 1.2, 3.6), ("chest", 0.9, 2.6), ("balls", 0.6, 2.2),
                                 ("ruin", 0.9, 3.2), ("rocks", 0.4, 3.0)], margin=2.2)
    fill(on_plateau, 6, [("rocks", 1.6, 3.2), ("barrels", 2, 3.6), ("chest", 1.4, 2.6), ("balls", 0.8, 2.2),
                         ("palm", 2.2, 2.2), ("ruin", 1.2, 3.2)], margin=1.4)
    fill(on_beach, 8, [("rocks", 1.0, 3.2), ("palm", 2.4, 2.2), ("barrels", 1.2, 3.6), ("balls", 0.7, 2.2),
                       ("chest", 0.7, 2.6), ("ruin", 0.7, 3.2)], margin=1.6)
    fill(lambda x, y: inside(VAULT, x, y) and dist_to_edge(VAULT, x, y) > 3.5, 6,
         [("gold", 3, 3.0), ("chest", 1, 2.6)], margin=1.2)


# ======================= COMPOSITION =======================
def compose():
    build_terrain()
    compass(COMPASS[0], COMPASS[1], Z_COMPASS)
    occupy(COMPASS[0], COMPASS[1], 16)
    vault()
    skull_rock(MOUND_C[0], MOUND_C[1] + 5, Z_CRATER - 0.6)
    fortress()
    ship_wheel(ARENA[0], ARENA[1], Z_ROOF)
    volcano(*VOLCANO)
    # stairs cut into the cliffs, ramps
    zl = lambda p: z_beach(p.x, p.y)                     # noqa: E731
    stone_stairs(Vector((STAIRS_L[0].x, STAIRS_L[0].y, zl(STAIRS_L[0]))),
                 Vector((STAIRS_L[1].x, STAIRS_L[1].y, z_plateau(*STAIRS_L[1]))), 14)
    stone_stairs(Vector((STAIRS_R[0].x, STAIRS_R[0].y, Z_VAULT)),
                 Vector((STAIRS_R[1].x, STAIRS_R[1].y, z_plateau(*STAIRS_R[1]))), 14)
    ramp(Vector((RAMP_W[0].x, RAMP_W[0].y, zl(RAMP_W[0]))),
         Vector((RAMP_W[1].x, RAMP_W[1].y, z_plateau(*RAMP_W[1]))), 16, top="sand_dark", side="dirt")
    for a, b in (RAMP_MOUND_F, RAMP_MOUND_E):
        ramp(Vector((a.x, a.y, z_plateau(a.x, a.y))), Vector((b.x, b.y, z_mound(b.x, b.y))), 12,
             top="sand_dark", side="dirt")
    block_steps()
    for x, y in ((-40, -8), (6, 36), (-58, 26), (-8, -24)):                   # rocks at the foot of the crater
        rocks(x, y, 3, 3.6)
    clouds()
    foam()
    props()


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
    sock(bsdf.inputs, "Roughness").default_value = 0.8
    tm = nt.nodes.new("ShaderNodeTexImage")
    tm.image = mask
    tm.interpolation = "Closest"
    tm.image.colorspace_settings.name = "Non-Color"
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = 5.0
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
        # the triangulation projects each n-gon along its normal: it must be up to date
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
	BRAINROT FIGHTER - @@NAME@@ installer (standalone test map: pirate treasure island)
	Paste this whole file into the Studio command bar in EDIT mode (not during Play),
	after importing @@NAME@@.fbx with the 3D Importer. Safe to run again as many times as needed.
	  - finds the imported map, anchors it, fixes its size, position and orientation
	  - @@NBC@@ invisible walkable surfaces that follow the relief (beach, plateau, grass blocks,
	    skull crater, fortress, stairs and ramps)
	  - Roblox terrain water all around (swimmable), a sea floor and invisible walls far out
	  - spawn on the golden compass, facing the island
	  - sunny day: sky, clouds, @@NBL@@ lights, @@NBP@@ particle emitters
	  - @@NBA@@ living objects (palms in the wind, compass needle, drifting clouds, foam...),
	    animated on each player's screen by the "MapLife" LocalScript
]]
local NAME = "@@NAME@@"

-- SCALE: 1 = intended size (island of about 360 studs). 0.8 = smaller, 1.2 = bigger...
local SCALE = 1
local WIDTH = @@WIDTH@@ * SCALE -- full model width (sea floor included)
local ZONE_CENTER = Vector3.new(0, 0, 0)
local OFFSET = Vector3.new(@@DX@@, @@DY@@, @@DZ@@)

-- Landmarks (original positions in studs): arena, Star (compass), pads, spawn
local MARK_ARENA = Vector2.new(@@AX@@, @@AZ@@)
local MARK_STAR = Vector2.new(@@FX@@, @@FZ@@)
local MARK_ARCHES = Vector2.new(@@BX@@, @@BZ@@)
local SPAWN = Vector3.new(@@EX@@, @@EY@@, @@EZ@@)
local UNIQUE_MARKER = "@@MARKER@@" -- object that only exists in this map
local OCEAN = @@OCEAN@@ -- half size of the sea (studs)

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
for _, name in { "Collisions", "Lights", "Particles", "Sea" } do
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
			ZONE_CENTER += Vector3.new(2000, 0, 0)
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

-- 3. Invisible walkable surfaces that follow the relief -------------------------------------
-- one entry per surface: a (x,y,z) ; b (x,y,z) ; width ; thickness ; up vector (x,y,z)
local COLLISIONS = "@@COLLISIONS@@"
local collisionFolder = Instance.new("Folder")
collisionFolder.Name = "Collisions"
collisionFolder.Parent = m
local collisionCount = 0
for entry in COLLISIONS:gmatch("[^;]+") do
	local c = {}
	for value in entry:gmatch("[^,]+") do
		table.insert(c, tonumber(value))
	end
	local a = transform(c[1], c[2], c[3])
	local b = transform(c[4], c[5], c[6])
	local width, thickness = c[7] * k, c[8] * k
	local length = (b - a).Magnitude
	if length > 0.05 then
		collisionCount += 1
		local p = Instance.new("Part")
		p.Name = "Sol_" .. collisionCount
		p.Anchored = true
		p.Transparency = 1
		p.CanCollide = true
		p.CastShadow = false
		p.Size = Vector3.new(width, thickness, length)
		p.CFrame = CFrame.lookAt((a + b) / 2, b, worldDir({ c[9], c[10], c[11] })) * CFrame.new(0, -thickness / 2, 0)
		p.Parent = collisionFolder
	end
end
print("✅ " .. collisionCount .. " surfaces de collision créées")

-- Spawn on the golden compass, facing the island
local spawn = m:FindFirstChild("SpawnIsland") or Instance.new("SpawnLocation")
spawn.Name = "SpawnIsland"
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

-- 4. The sea: Roblox terrain water, a floor and walls far out ---------------------------------
local terrain = workspace.Terrain
local depth = 28 * k
local reach = OCEAN * k
local seaFrame = CFrame.new(transform(0, -14, 0)) * mapRotation
terrain:FillBlock(seaFrame, Vector3.new(reach * 2 + 64, depth + 24, reach * 2 + 64), Enum.Material.Air)
terrain:FillBlock(seaFrame, Vector3.new(reach * 2, depth, reach * 2), Enum.Material.Water)
terrain.WaterColor = Color3.fromRGB(28, 176, 196)
terrain.WaterTransparency = 0.72
terrain.WaterReflectance = 0.35
terrain.WaterWaveSize = 0.12
terrain.WaterWaveSpeed = 8
local skyClouds = terrain:FindFirstChildOfClass("Clouds") or Instance.new("Clouds")
skyClouds.Cover = 0.55
skyClouds.Density = 0.6
skyClouds.Color = Color3.new(1, 1, 1)
skyClouds.Parent = terrain
local seaFolder = Instance.new("Folder")
seaFolder.Name = "Sea"
seaFolder.Parent = m
local function invisibleWall(name, frame, wallSize)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.Transparency = 1
	p.CanCollide = true
	p.CastShadow = false
	p.Size = wallSize
	p.CFrame = frame
	p.Parent = seaFolder
end
invisibleWall("SeaFloor", seaFrame * CFrame.new(0, -depth / 2 - 1, 0), Vector3.new(reach * 2, 2, reach * 2))
for i, side in { Vector3.new(1, 0, 0), Vector3.new(-1, 0, 0), Vector3.new(0, 0, 1), Vector3.new(0, 0, -1) } do
	local wallSize = if side.X ~= 0 then Vector3.new(2, depth + 92, reach * 2) else Vector3.new(reach * 2, depth + 92, 2)
	invisibleWall("SeaWall_" .. i, seaFrame * CFrame.new(side * reach + Vector3.new(0, 46, 0)), wallSize)
end
print("✅ Mer créée (eau du terrain Roblox)")

-- 5. Parts: neon, texture, collisions -------------------------------------------------------
local NEON = {
@@NEON@@
}
local NO_COLLISION = { "^Sol_", "^Decor_Sky", "^Decor_Sea", "^Decor_Foam" } -- floors (handled above), far decor
local function noCollision(name)
	for _, pattern in NO_COLLISION do
		if name:match(pattern) then
			return true
		end
	end
	return false
end
for _, p in m:GetDescendants() do
	if p:IsA("BasePart") and p.Parent ~= collisionFolder and p.Parent ~= seaFolder and p ~= spawn then
		local prefix = p.Name:match("^(Neon_%a+)") or p.Name
		if NEON[prefix] then
			pcall(function()
				p.TextureID = ""
			end)
			p.Color = NEON[prefix]
			p.Material = Enum.Material.Neon
			p.CastShadow = false
			p.CanCollide = false
		else
			if TEXTURE_ID ~= "" and p:IsA("MeshPart") then
				p.TextureID = TEXTURE_ID
			end
			if noCollision(p.Name) then
				p.CanCollide = false
				if p.Name:match("^Decor_Sky") then
					p.CastShadow = false -- clouds far away: no shadow blobs on the sea
				end
			else
				-- rocks, props, fortress, skull: nobody walks through them
				pcall(function()
					p.CollisionFidelity = Enum.CollisionFidelity.PreciseConvexDecomposition
				end)
				p.CanCollide = true
			end
		end
	end
end

-- 6. Ambience: sunny tropical day ------------------------------------------------------------
for _, e in Lighting:GetChildren() do
	if e:IsA("Atmosphere") or e:IsA("Sky") or e:IsA("PostEffect") then
		e:Destroy()
	end
end
pcall(function()
	Lighting.Technology = Enum.Technology.Future
end)
Lighting.ClockTime = 14
Lighting.GeographicLatitude = 20
Lighting.Brightness = 2.4
Lighting.Ambient = Color3.fromRGB(96, 100, 112)
Lighting.OutdoorAmbient = Color3.fromRGB(150, 150, 165)
Lighting.ColorShift_Top = Color3.fromRGB(255, 244, 222)
Lighting.ColorShift_Bottom = Color3.fromRGB(0, 0, 0)
Lighting.EnvironmentDiffuseScale = 1
Lighting.EnvironmentSpecularScale = 0.6
Lighting.GlobalShadows = true
local sky = Instance.new("Sky")
sky.Name = "IslandSky"
sky.CelestialBodiesShown = true
sky.StarCount = 0
sky.SunAngularSize = 14
sky.Parent = Lighting
local atmosphere = Instance.new("Atmosphere")
atmosphere.Name = "IslandAtmosphere"
atmosphere.Density = 0.22
atmosphere.Offset = 0.15
atmosphere.Color = Color3.fromRGB(199, 226, 255)
atmosphere.Decay = Color3.fromRGB(92, 154, 214)
atmosphere.Glare = 0.25
atmosphere.Haze = 1.2
atmosphere.Parent = Lighting
local colors = Instance.new("ColorCorrectionEffect")
colors.Name = "IslandColors"
colors.Saturation = 0.22
colors.Contrast = 0.08
colors.Brightness = 0.02
colors.TintColor = Color3.fromRGB(255, 252, 245)
colors.Parent = Lighting
local bloom = Instance.new("BloomEffect")
bloom.Name = "IslandBloom"
bloom.Intensity = 0.5
bloom.Size = 24
bloom.Threshold = 1.4
bloom.Parent = Lighting
local rays = Instance.new("SunRaysEffect")
rays.Name = "IslandSunRays"
rays.Intensity = 0.04
rays.Spread = 0.7
rays.Parent = Lighting

-- 7. Lights (positions exported from Blender) ------------------------------------------------
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

-- 8. Living objects (animated by the MapLife LocalScript) ---------------------------------------
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

-- 9. Particles ---------------------------------------------------------------------------------
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
local SPARKLES = "rbxasset://textures/particles/sparkles_main.dds"
local SMOKE = "rbxasset://textures/particles/smoke_main.dds"
local FX = {
	smoke = { rate = 5, life = NumberRange.new(5, 8), speed = NumberRange.new(3, 6), size = NumberSequence.new(4, 12),
		spread = Vector2.new(12, 12), accel = Vector3.new(0, 0.5, 0), peak = 0.35, texture = SMOKE, emission = 0.4 },
	gold = { rate = 6, life = NumberRange.new(2, 3), speed = NumberRange.new(2, 4), size = NumberSequence.new(0.6, 0),
		spread = Vector2.new(25, 25), accel = Vector3.zero, peak = 0 },
	sparkle = { rate = 5, life = NumberRange.new(0.8, 1.8), speed = NumberRange.new(0.5, 2), size = NumberSequence.new(0.7, 0),
		spread = Vector2.new(180, 180), accel = Vector3.zero, peak = 0 },
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
	e.Texture = spec.texture or SPARKLES
	e.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(P[9], P[10], P[11]))
	e.LightEmission = spec.emission or 1
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
	e.Shape = Enum.ParticleEmitterShape.Box
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

-- 10. Client animation script --------------------------------------------------------------------
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

print("✅ " .. NAME .. " prête ! Lance Play : tu apparais sur la boussole dorée de la plage.")
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
    for a, b, width, thick, up in COLLISIONS:
        cols.append("%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f" % (
            *rb(a), *rb(b), width, thick, *rb(up)))
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
    arches = (sum(p[0] for p in PADS) / len(PADS), sum(p[1] for p in PADS) / len(PADS))
    repl = {
        "@@NAME@@": NAME, "@@NBL@@": str(len(LIGHTS)), "@@NBC@@": str(len(COLLISIONS)),
        "@@NBA@@": str(len(LIFE)), "@@NBP@@": str(len(PARTICLES)), "@@OCEAN@@": str(OCEAN),
        "@@WIDTH@@": "%.1f" % max(mx.x - mn.x, mx.y - mn.y),
        "@@DX@@": "%.2f" % ((mn.x + mx.x) / 2), "@@DY@@": "%.2f" % ((mn.z + mx.z) / 2),
        "@@DZ@@": "%.2f" % (-(mn.y + mx.y) / 2),
        "@@AX@@": str(ARENA[0]), "@@AZ@@": str(-ARENA[1]),
        "@@FX@@": str(COMPASS[0]), "@@FZ@@": str(-COMPASS[1]),
        "@@BX@@": "%.1f" % arches[0], "@@BZ@@": "%.1f" % -arches[1],
        "@@EX@@": str(SPAWN[0]), "@@EY@@": "%.2f" % SPAWN[2], "@@EZ@@": str(-SPAWN[1]),
        "@@MARKER@@": MARKER,
        "@@NEON@@": "\n".join(neon), "@@LIGHTS@@": "\n".join(lights), "@@COLLISIONS@@": ";".join(cols),
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
    return len(lua.encode("utf-8"))


def export_fbx():
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT_DIR, f"{NAME}.fbx"),
        use_selection=False, object_types={"MESH"}, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=True, axis_forward="-Z", axis_up="Y",
        apply_scale_options="FBX_SCALE_NONE", global_scale=1.0)


# ======================= SELF CHECKS =======================
def walk_graph():
    """Where a character can walk: every collision top sampled on a 3-stud grid, neighbouring
    samples linked when the height step is small enough to walk (no jumping)."""
    cell = 3.0
    tops = {}
    for a, b, w, _, up in COLLISIONS:
        d = b - a
        L = d.length
        if L < 0.05:
            continue
        u = d / L
        side = u.cross(up).normalized()
        steps_l, steps_w = max(1, int(L / 1.5)), max(1, int(w / 1.5))
        for i in range(steps_l + 1):
            for j in range(steps_w + 1):
                p = a + u * (L * i / steps_l) + side * (w * (j / steps_w - 0.5))
                key = (int(math.floor(p.x / cell)), int(math.floor(p.y / cell)))
                zs = tops.setdefault(key, [])
                if all(abs(z - p.z) > 0.6 for z in zs):
                    zs.append(p.z)
    return tops, cell


def reachable(tops, cell, start, max_step=1.8):
    sx, sy, sz = start
    k0 = (int(math.floor(sx / cell)), int(math.floor(sy / cell)))
    z0 = min(tops.get(k0, [sz]), key=lambda z: abs(z - sz))
    seen = {(k0, round(z0, 1))}
    todo = [(k0, z0)]
    while todo:
        (ix, iy), z = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nk = (ix + dx, iy + dy)
                for nz in tops.get(nk, ()):
                    if abs(nz - z) <= max_step and (nk, round(nz, 1)) not in seen:
                        seen.add((nk, round(nz, 1)))
                        todo.append((nk, nz))
    return seen


def self_checks(report, lua_size):
    names = {n for n, _ in report}
    passed, failed = [], []

    def check(ok, label):
        (passed if ok else failed).append(label)
        print(("  ok    " if ok else "  FAIL  ") + label)

    check(len(COLOURS) <= CELLS * CELLS, f"palette fits the {CELLS}x{CELLS} texture ({len(COLOURS)} colours)")
    for landmark in ("Sol_Arene", "Star_Socle", "Neon_arche", MARKER):
        check(landmark in names, f"landmark {landmark} exported as one object")
    check(all(t <= TRI_MAX for _, t in report), f"every object under {TRI_MAX} triangles")
    check(all(n in names for n in LIFE), "every living object exists (and was not split)")
    check(all(h == "" or h in names for _, _, _, _, h, _ in LIGHTS), "every light host exists")
    check(all(h == "" or h in names for _, _, _, h, _ in PARTICLES), "every particle host exists")
    check(all(n.split("_")[0] in ("Sol", "Decor", "Neon", "Star") for n in names), "every object has a known prefix")
    neon_ok = all(any(n.startswith(p) for p in NEON) or n in TEXTURED_LANDMARKS for n in names if n.startswith("Neon_"))
    check(neon_ok, "every Neon_ object has a colour in the installer")

    tops, cell = walk_graph()
    sx, sy, sz = SPAWN
    k0 = (int(math.floor(sx / cell)), int(math.floor(sy / cell)))
    under = [z for z in tops.get(k0, []) if z <= sz + 0.5]
    check(bool(under) and sz - max(under) < 2.5, "a walkable surface lies under the spawn point")
    seen = reachable(tops, cell, (sx, sy, max(under) if under else sz))
    goals = {"plateau (L2)": (-40, -40, z_plateau(-40, -40)), "skull crater rim": (-18, -20, z_mound(-18, -20)),
             "crater floor": (-40, 10, z_mound(-40, 10)), "fortress roof (L3)": (78, 76, Z_ROOF),
             "treasure vault": (84, -146, Z_VAULT), "west ramp top": (-100, -40, z_plateau(-100, -40)),
             "back beach": (60, 158, z_beach(60, 158))}
    for name, (x, y) in STEPPED:
        goals[f"grass {name}"] = (x, y, z_block(x, y))
    for label, (x, y, z) in goals.items():
        k = (int(math.floor(x / cell)), int(math.floor(y / cell)))
        ok = any(kk == k and abs(zz - z) < 2.5 for kk, zz in seen)
        check(ok, f"{label} reachable on foot from the spawn")
    # the ground is never a flat plate
    for label, pts, fn, holes in (("beach", offset(SHORE, -8), z_beach, HOLES_L2 + [PLATEAU, VAULT]),
                                  ("plateau", PLATEAU, z_plateau, HOLES_L2)):
        zs = [fn(x, y) for x in range(-180, 181, 9) for y in range(-180, 181, 9)
              if inside(pts, x, y) and not any(inside(h, x, y) for h in holes)]
        span = max(zs) - min(zs)
        check(span > 1.5, f"the {label} is not flat (heights {min(zs):.1f} to {max(zs):.1f})")
    # rays from above and from the four sides must always hit the FRONT of a face
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    backs, hits = {}, 0
    rays = [(Vector((x + 0.37, y + 0.61, 400)), Vector((0, 0, -1)))
            for x in range(-220, 221, 4) for y in range(-220, 221, 4)]
    for z in (1.3, 6.3, 14.3, 20.3, 28.3, 40.3):
        for t in range(-220, 221, 3):
            t += 0.29
            rays += [(Vector((t, -600, z)), Vector((0, 1, 0))), (Vector((t, 600, z)), Vector((0, -1, 0))),
                     (Vector((-600, t, z)), Vector((1, 0, 0))), (Vector((600, t, z)), Vector((-1, 0, 0)))]
    for origin, direction in rays:
        ok, _, nrm, _, ob, _ = scene.ray_cast(depsgraph, origin, direction)
        if ok:
            hits += 1
            if nrm.dot(direction) > 0.05:
                backs[ob.name] = backs.get(ob.name, 0) + 1
    worst = sorted(backs.items(), key=lambda kv: -kv[1])[:5]
    check(sum(backs.values()) <= hits * 0.001, f"no back face in sight ({sum(backs.values())}/{hits} rays: {worst})")
    check(len(COLLISIONS) <= 1600, f"collision budget ({len(COLLISIONS)} surfaces)")
    check(lua_size < 200_000, f"installer small enough to paste ({lua_size // 1024} KB)")
    check(len(LIGHTS) <= 40, f"light budget ({len(LIGHTS)} lights)")
    print(f"CHECKS passed={len(passed)} failed={len(failed)}")
    return not failed


# ======================= PREVIEW =======================
def prepare_preview(mat):
    """Sunny day, turquoise sea (preview only: Roblox uses terrain water), back faces hidden."""
    sc = bpy.context.scene
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if os.environ.get("DEBUG_BACKFACES") == "1":
        back = nt.nodes.new("ShaderNodeBsdfDiffuse")
        back.inputs[0].default_value = (1, 0, 0, 1)
    else:
        back = nt.nodes.new("ShaderNodeBsdfTransparent")
    nt.links.new(sock(geo.outputs, "Backfacing"), mix.inputs[0])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(back.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], sock(out.inputs, "Surface"))

    water = bpy.data.materials.new("PreviewWater")
    if not water.node_tree:
        water.use_nodes = True
    wb = next(n for n in water.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    sock(wb.inputs, "Base Color").default_value = (0.03, 0.5, 0.6, 1)
    sock(wb.inputs, "Roughness").default_value = 0.06
    sock(wb.inputs, "Alpha").default_value = 0.72
    me = bpy.data.meshes.new("PreviewWater")
    b = bmesh.new()
    bmesh.ops.create_grid(b, x_segments=1, y_segments=1, size=OCEAN)
    b.to_mesh(me)
    b.free()
    me.materials.append(water)
    ob = bpy.data.objects.new("PreviewWater", me)
    sc.collection.objects.link(ob)

    world = sc.world or bpy.data.worlds.new("Sky")
    sc.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.2, 0.5, 1.0, 1)
    bg.inputs[1].default_value = 1.3
    for ob in bpy.data.objects:
        if ob.name.startswith(("Decor_Sky", "Decor_Sea")):
            ob.visible_shadow = False
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.2
    sun.data.color = (1.0, 0.95, 0.86)
    sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(-38))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.clip_end = 6000
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
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass


VIEWS = {
    "Preview_Global": ((-70, -470, 300), (0, 10, 10), 33),
    "Preview_Spawn": ((-128, -176, 16), (-50, -60, 14), 22),
    "Preview_Center": ((-18, -96, 52), (-18, 13, 26), 26),
    "Preview_Fortress": ((12, -44, 46), (82, 92, 34), 27),
    "Preview_Vault": ((10, -190, 26), (90, -128, 4), 26),
    "Preview_Plan": ((0, 0, 900), None, 400),
}


def preview():
    sc = bpy.context.scene
    cam = sc.camera
    only = os.environ.get("VIEWS")
    os.makedirs(os.path.join(EXPORT_DIR, "previews"), exist_ok=True)
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
lua_size = write_roblox_script(mn, mx)
export_fbx()

total = sum(t for _, t in report)
print(f"\n{len(report)} objects, {total} triangles, {len(LIGHTS)} lights, {len(COLLISIONS)} collisions, "
      f"{len(LIFE)} living objects, {len(PARTICLES)} particle emitters, {PALM_COUNT[0]} palms, {len(OCC)} props")
print("  props by kind:", dict(sorted(KINDS.items())))
for k, t in sorted(report, key=lambda r: -r[1])[:12]:
    print(f"  {k:34s} {t:6d} tris")
print(f"Bounding box: {tuple(round(v) for v in mn)} -> {tuple(round(v) for v in mx)}")
self_checks(report, lua_size)

if os.environ.get("SAVE_BLEND"):
    # saved before the preview setup, so the .blend holds exactly what was exported
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXPORT_DIR, f"{NAME}.blend"))
if RENDER_PREVIEW:
    prepare_preview(material)
    preview()
