"""
BRAINROT FIGHTER - COSMIC EGG (collectible gacha egg, gamepass-icon style)

Built from the reference picture: a purple galaxy egg wearing an astronaut helmet with a
dark visor and two cosmic feathers, a tilted Saturn ring, a small Earth, a gold filigree
cartouche with stars, moons, a cross and a satellite, a spiral galaxy, nebula drips flowing
from under the helmet and ribbons wrapping the lower half.

Two stages:
  STAGE=1  colour blocking: pure volumes, flat colours from a palette texture (this file)
  STAGE=2  final look (textures, shaders, relief) once the stage 1 shape is validated

Outputs (in EXPORT_DIR):
  CosmicEgg_Stage<N>.fbx          one MeshPart, palette texture embedded (Studio > Import 3D)
  CosmicEgg_Palette.png           colour map (+ _Roughness / _Metalness for a SurfaceAppearance)
  previews/                       renders (RENDER_PREVIEW=1)
  CosmicEgg_Stage<N>.blend        optional (SAVE_BLEND=1)

Run headless:  EXPORT_DIR=out RENDER_PREVIEW=1 SAMPLES=48 python cosmic_egg.py
Scale: 1 Blender unit = 1 stud. The egg stands on z = 0, its front faces -Y.
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Matrix, Vector, noise

# ======================= SETTINGS =======================
EXPORT_DIR = os.environ.get(
    "EXPORT_DIR", os.path.join(os.path.expanduser("~"), "BrainrotFighter", "Items", "CosmicEgg"))
NAME = "CosmicEgg"
STAGE = int(os.environ.get("STAGE", "1"))
RENDER_PREVIEW = os.environ.get("RENDER_PREVIEW", "0") == "1"
TRI_MAX = 9500            # one MeshPart; Roblox's hard limit is 10 000

# Main dimensions (studs), measured on the reference picture (560 px = 4 studs)
H = 3.25                  # egg body height, base at z = 0 (its top is inside the helmet)
R = 1.42                  # widest radius of the egg
HELMET_C = Vector((0.0, 0.02, 3.26))
HELMET_R = Vector((0.82, 0.80, 0.64))
RING_Z = 1.66
RING_TILT = -16.0         # left end low, right end high (degrees around the view axis)
RING_LEAN = -4.0          # front edge raised a little: from the usual view the ring looks thin
RING_IN, RING_OUT = 1.50, 1.74

random.seed(11)
noise.seed_set(11)

# ======================= PALETTE =======================
PALETTE = {
    # galaxy body
    "void": (24, 14, 52), "purple_dark": (40, 18, 82), "purple": (68, 30, 124),
    "violet": (116, 58, 188), "magenta": (196, 52, 156), "pink": (236, 116, 196),
    "pink_light": (255, 192, 226), "nebula_blue": (58, 72, 168), "star": (255, 250, 236),
    # helmet
    "helmet": (72, 34, 136), "helmet_light": (116, 72, 190), "helmet_dark": (40, 18, 82),
    "visor": (20, 12, 38), "visor_glint": (126, 100, 200),
    # gold ornaments
    "gold": (232, 176, 58), "gold_light": (255, 222, 120), "gold_dark": (166, 112, 28),
    # Saturn ring
    "ring_cream": (230, 216, 190), "ring_tan": (198, 172, 134), "ring_brown": (142, 110, 80),
    "ring_dark": (98, 76, 58),
    # Earth
    "earth_blue": (52, 98, 188), "earth_green": (78, 150, 88), "earth_cloud": (236, 242, 255),
    # feathers
    "feather": (150, 138, 236), "feather_light": (204, 194, 255), "feather_dark": (92, 80, 198),
    "feather_shaft": (236, 232, 255),
    # spiral galaxy
    "galaxy_core": (255, 240, 202),
}
COLOURS = list(PALETTE)
ROUGHNESS = {"visor": 0.06, "visor_glint": 0.1, "helmet": 0.35, "helmet_light": 0.35, "helmet_dark": 0.4,
             "gold": 0.3, "gold_light": 0.25, "gold_dark": 0.35, "earth_blue": 0.3}
METALNESS = {"gold": 1.0, "gold_light": 1.0, "gold_dark": 1.0}
CELLS = 8
PX = 16
SMOOTH = {"Body", "Helmet", "Visor", "Planet", "Nebula", "Feathers", "Stars"}
UV = {n: ((i % CELLS + 0.5) / CELLS, (i // CELLS + 0.5) / CELLS) for i, n in enumerate(COLOURS)}


# ======================= EGG SURFACE =======================
def _profile(t):
    return 2.0 * math.sqrt(max(t * (1.0 - t), 0.0)) * (1.0 + 0.28 * (0.5 - t))


F_MAX = max(_profile(i / 1000) for i in range(1001))


def egg_r(z):
    """Radius of the egg at height z (egg shape: wider below the middle)."""
    return R * _profile(min(max(z / H, 0.0), 1.0)) / F_MAX


def egg_point(theta, z):
    """theta in degrees: 0 = front (-Y), 90 = right (+X), -90 = left."""
    a = math.radians(theta)
    r = egg_r(z)
    return Vector((r * math.sin(a), -r * math.cos(a), z))


def egg_normal(theta, z):
    e = 1e-3
    p = egg_point(theta, z)
    dt = egg_point(theta + e, z) - egg_point(theta - e, z)
    dz = egg_point(theta, min(z + e, H - 1e-4)) - egg_point(theta, max(z - e, 1e-4))
    n = dt.cross(dz)
    if n.dot(p - Vector((0, 0, z))) < 0:
        n = -n
    return n.normalized()


def front(x, z):
    """(theta, z) of the point of the egg's front seen at (x, z)."""
    r = egg_r(z)
    return math.degrees(math.asin(max(-0.999, min(0.999, x / r)))), z


def helmet_point(lon, lat, grow=0.0):
    """Point of the helmet ellipsoid; lon 0 = front (-Y), lat 90 = top."""
    a, b = math.radians(lon), math.radians(lat)
    d = Vector((math.cos(b) * math.sin(a), -math.cos(b) * math.cos(a), math.sin(b)))
    p = Vector((d.x * (HELMET_R.x + grow), d.y * (HELMET_R.y + grow), d.z * (HELMET_R.z + grow)))
    return HELMET_C + p


def helmet_normal(p):
    q = p - HELMET_C
    return Vector((q.x / HELMET_R.x ** 2, q.y / HELMET_R.y ** 2, q.z / HELMET_R.z ** 2)).normalized()


def ellipsoid_scale(q):
    """How far q (relative to the helmet centre) is from the helmet surface: 1 = on it."""
    return math.sqrt((q.x / HELMET_R.x) ** 2 + (q.y / HELMET_R.y) ** 2 + (q.z / HELMET_R.z) ** 2)


def helmet_front_y(x, z):
    """y of the helmet surface in front, at (x, z)."""
    k = 1.0 - (x / HELMET_R.x) ** 2 - ((z - HELMET_C.z) / HELMET_R.z) ** 2
    return HELMET_C.y - HELMET_R.y * math.sqrt(max(k, 0.0))


# ======================= MESH BUILDER =======================
class Builder:
    """One bmesh per part; every face is painted with a palette cell (UV)."""

    def __init__(self):
        self.parts = {}
        self.unpainted = 0

    def bm(self, key):
        if key not in self.parts:
            b = bmesh.new()
            b.loops.layers.uv.new("UVMap")
            self.parts[key] = b
        return self.parts[key]

    def paint(self, b, faces, colour):
        uv = b.loops.layers.uv.active
        u, v = UV[colour]
        for f in faces:
            for loop in f.loops:
                loop[uv].uv = (u, v)

    def face(self, b, verts, colour):
        f = b.faces.new(verts)
        self.paint(b, [f], colour)
        return f

    def grid(self, key, rows, colour_fn, closed_u=True, cap_start=None, cap_end=None):
        """rows: list of vertex rings (lists of Vector), faces between consecutive rings.
        colour_fn(i, j) gives the colour of the quad between ring i and i+1, column j.
        cap_start / cap_end: colour of a fan closing the first / last ring (None = open)."""
        b = self.bm(key)
        vrows = [[b.verts.new(p) for p in row] for row in rows]
        n = len(rows[0])
        cols = n if closed_u else n - 1
        for i in range(len(vrows) - 1):
            for j in range(cols):
                a, c = vrows[i][j], vrows[i][(j + 1) % n]
                d, e = vrows[i + 1][(j + 1) % n], vrows[i + 1][j]
                self.face(b, (a, c, d, e), colour_fn(i, j))
        for ring, colour, flip in ((vrows[0], cap_start, True), (vrows[-1], cap_end, False)):
            if colour is None:
                continue
            centre = b.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for j in range(n if closed_u else n - 1):
                tri = (ring[j], ring[(j + 1) % n], centre)
                self.face(b, tri[::-1] if flip else tri, colour)
        return vrows


BUILD = Builder()


# ======================= PARTS =======================
SHIELD = [(-0.18, 2.78), (-0.52, 2.72), (-0.84, 2.5), (-1.02, 2.16), (-1.08, 1.78), (-0.98, 1.36),
          (-0.76, 1.02), (-0.44, 0.8), (-0.1, 0.68), (0.22, 0.64), (0.34, 0.9), (0.26, 1.2),
          (0.34, 1.5), (0.3, 1.76), (0.12, 2.0), (0.06, 2.3), (0.02, 2.56)]


def inside(poly, x, y):
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def nebula_colour(p):
    """Galaxy colour blocking on the body: a dark base crossed by broad flowing
    magenta and pink streams; lighter blue-violet nebula inside the gold cartouche."""
    q = Vector((p.x * 0.55, p.y * 0.55, p.z * 0.5))
    wobble = 1.6 * noise.noise(q + Vector((3.1, 0.7, 1.9)))
    stream = math.sin(math.atan2(p.x, -p.y) * 1.0 + p.z * 2.1 + wobble)
    shade = noise.noise(q * 1.7 + Vector((7.3, 2.1, 0.4)))
    if p.y < 0 and inside(SHIELD, p.x, p.z):
        return "pink" if stream > 0.75 else "violet"
    # broad two-tone blobs only: the pink streams are carried by the drapes and ribbons
    return "purple_dark" if shade + 0.25 * stream < -0.05 else "purple"


def build_body():
    rings, segs = 22, 40
    zs = [H * (1 - math.cos(math.pi * (i + 1) / (rings + 1))) / 2 for i in range(rings)]
    zs = [z for z in zs if z < 3.05]            # the top of the egg is inside the helmet
    rows = [[egg_point(360 * j / segs, z) for j in range(segs)] for z in zs]

    def colour(i, j):
        z = (zs[i] + zs[i + 1]) / 2
        return nebula_colour(egg_point(360 * (j + 0.5) / segs, z))
    BUILD.grid("Body", rows, colour, cap_start="purple_dark", cap_end="purple_dark")


def build_helmet():
    lats = [-70, -52, -36, -22, -8, 6, 20, 34, 48, 62, 74, 84]
    segs = 28
    rows = [[helmet_point(360 * j / segs, lat) for j in range(segs)] for lat in lats]

    def colour(i, j):
        lat = (lats[i] + lats[i + 1]) / 2
        lon = (360 * (j + 0.5) / segs + 180) % 360 - 180
        if lat > 40 and abs(lon) < 60:
            return "helmet_light"                 # sheen on the upper front
        if lat < -30:
            return "helmet_dark"
        return "helmet"
    BUILD.grid("Helmet", rows, colour, cap_end="helmet_light")

    # headband from ear to ear, passing over the top just in front of the crown
    tilt = math.radians(28)
    across, over = Vector((1.0, 0.0, 0.0)), Vector((0.0, -math.sin(tilt), math.cos(tilt)))
    path = []
    for a in range(0, 181, 10):
        d = across * math.cos(math.radians(a)) + over * math.sin(math.radians(a))
        p = HELMET_C + d / ellipsoid_scale(d)        # onto the ellipsoid
        path.append(p + helmet_normal(p) * 0.02)
    ribbon_on(path, [helmet_normal(p) for p in path], 0.2, 0.05, lambda k: "helmet_light", key="Helmet")

    # ear disks on both sides
    for side in (-1, 1):
        centre = HELMET_C + Vector((side * (HELMET_R.x + 0.02), 0.08, -0.02))
        disk(centre, Vector((side, 0, 0)), 0.2, 0.1, "helmet_light", "helmet_dark", key="Helmet")
        disk(centre + Vector((side * 0.1, 0, 0)), Vector((side, 0, 0)), 0.1, 0.05, "helmet_dark", "helmet_dark",
             key="Helmet")


def build_visor():
    a, b, zc = 0.6, 0.33, HELMET_C.z + 0.08
    segs, rings = 32, 7
    rows = []
    for i in range(rings + 1):
        u = 1.0 - i / rings                     # rim first, centre last
        row = []
        for j in range(segs):
            v = 2 * math.pi * j / segs
            x, z = a * u * math.cos(v), zc + b * u * math.sin(v)
            bulge = 0.14 * math.sqrt(max(1 - u * u, 0.0)) + 0.025
            row.append(Vector((x, helmet_front_y(x, z) - bulge, z)))
        rows.append(row)

    def colour(i, j):
        u = 1.0 - (i + 0.5) / rings
        v = 360 * (j + 0.5) / segs
        if 0.35 < u < 0.8 and 115 < v < 165:
            return "visor_glint"                  # reflection, upper left
        return "visor"
    BUILD.grid("Visor", rows, colour, cap_end="visor")

    # frame around the visor
    loop = []
    for j in range(30):
        v = 2 * math.pi * j / 30
        x, z = (a + 0.05) * math.cos(v), zc + (b + 0.05) * math.sin(v)
        loop.append(Vector((x, helmet_front_y(x, z) - 0.03, z)))
    tube(loop, [0.055] * len(loop), lambda k: "helmet_light", closed=True, key="Helmet", sides=5)


def build_feathers():
    base = helmet_point(62, 26, -0.03)
    for direction, length, width, roll in (((0.55, 0.15, 1.0), 0.86, 0.27, 25), ((1.0, 0.25, -0.12), 0.8, 0.24, -15)):
        feather(base, Vector(direction).normalized(), length, width, roll)


def feather(base, direction, length, width, roll):
    """Curved feather with a lens-shaped cross-section (closed, visible from both sides)."""
    side = direction.cross(Vector((0, -1, 0))).normalized()
    side = Matrix.Rotation(math.radians(roll), 3, direction) @ side
    up = side.cross(direction).normalized()
    steps = 9
    spine, rows_top, rows_bottom = [], [], []
    for i in range(steps + 1):
        s = i / steps
        bend = 0.18 * length * s * s
        centre = base + direction * (length * s) + side * bend
        half = width * math.sin(math.pi * min(s * 1.04, 1.0)) ** 0.6 + 0.012
        thick = 0.03 * (1 - s) + 0.008
        left, right = centre - side * half, centre + side * half
        rows_top.append([left, centre + up * thick, right])
        rows_bottom.append([right, centre - up * thick, left])
        spine.append(centre)

    def colour(i, j):
        s = (i + 0.5) / steps
        if s < 0.3:
            return "feather_light"
        return "feather" if s < 0.72 else "feather_dark"
    for rows in (rows_top, rows_bottom):
        BUILD.grid("Feathers", rows, colour, closed_u=False)
    shaft = [c + up * 0.03 for c in spine[:-1]]
    tube(shaft, [0.022 * (1 - 0.6 * i / len(shaft)) for i in range(len(shaft))], lambda k: "feather_shaft",
         key="Feathers", sides=4)
    # shaft sticking out at the base
    tube([base - direction * 0.12, base + direction * 0.05], [0.025, 0.02], lambda k: "feather_shaft",
         key="Feathers")


def build_ring():
    segs = 48
    bands = [(RING_IN, "ring_dark"), (1.55, "ring_cream"), (1.62, "ring_tan"), (1.66, "ring_cream"),
             (1.70, "ring_brown"), (RING_OUT, None)]
    M = (Matrix.Translation((0, 0, RING_Z)) @ Matrix.Rotation(math.radians(RING_TILT), 4, "Y")
         @ Matrix.Rotation(math.radians(RING_LEAN), 4, "X"))
    half = 0.022
    for sign, radii in ((1, [r for r, _ in bands]), (-1, [RING_IN, RING_OUT])):   # banded top, plain underside
        rows = [[M @ Vector((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs),
                             sign * half)) for j in range(segs)] for r in radii]
        BUILD.grid("Ring", rows, lambda i, j: bands[i][1] if sign > 0 else "ring_tan")
    for r, sign in ((RING_IN, -1), (RING_OUT, 1)):  # inner and outer walls
        rows = [[M @ Vector((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), h))
                 for j in range(segs)] for h in ((half, -half) if sign > 0 else (-half, half))]
        BUILD.grid("Ring", rows, lambda i, j: "ring_dark")


def build_planet():
    theta, z = -58, 1.52
    n = egg_normal(theta, z)
    centre = egg_point(theta, z) + n * 0.12
    r = 0.25
    rows = []
    lats = [-80, -60, -40, -20, 0, 20, 40, 60, 80]
    for lat in lats:
        b = math.radians(lat)
        rows.append([centre + r * Vector((math.cos(b) * math.cos(2 * math.pi * j / 16),
                                          math.cos(b) * math.sin(2 * math.pi * j / 16), math.sin(b)))
                     for j in range(16)])

    def colour(i, j):
        lat = (lats[i] + lats[i + 1]) / 2
        v = noise.noise(Vector((math.cos(2 * math.pi * j / 16), math.sin(2 * math.pi * j / 16), lat / 50)))
        if abs(lat) > 65 or v > 0.45:
            return "earth_cloud"
        return "earth_green" if v > 0.05 else "earth_blue"
    BUILD.grid("Planet", rows, colour, cap_start="earth_cloud", cap_end="earth_cloud")


def chaikin(pts, iterations=2, closed=True):
    for _ in range(iterations):
        out = []
        n = len(pts)
        for i in range(n if closed else n - 1):
            a, b = pts[i], pts[(i + 1) % n]
            out += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        if not closed:
            out = [pts[0]] + out + [pts[-1]]
        pts = out
    return pts


def surface_path(points_xz, lift, closed=True, smooth=2):
    """Front-projected (x, z) points -> smoothed points on the egg, with normals."""
    pts = chaikin([Vector(p) for p in points_xz], smooth, closed)
    out, normals = [], []
    for p in pts:
        theta, z = front(p.x, p.y)
        n = egg_normal(theta, z)
        out.append(egg_point(theta, z) + n * lift)
        normals.append(n)
    return out, normals


def build_gold():
    # cartouche: a shield outline with scrolls, around the upper left of the front
    path, normals = surface_path(SHIELD, 0.025)
    ribbon_on(path, normals, 0.07, 0.035, lambda k: "gold" if k % 7 else "gold_light", key="Gold", closed=True)
    # inner filigree: a curl hanging from the top border and one rising from the bottom
    for scroll in ([(-0.62, 2.62), (-0.58, 2.42), (-0.7, 2.3), (-0.82, 2.38)],
                   [(-0.2, 0.74), (-0.24, 0.96), (-0.1, 1.06), (0.0, 0.98)]):
        path, normals = surface_path(scroll, 0.02, closed=False, smooth=2)
        ribbon_on(path, normals, 0.045, 0.03, lambda k: "gold", key="Gold")

    for x, z, size in ((-0.36, 2.52, 0.09), (1.0, 1.08, 0.09), (-1.05, 0.95, 0.07), (0.55, 2.25, 0.07),
                       (-0.5, 1.62, 0.06), (0.78, 1.72, 0.06)):
        star(*front(x, z), size)
    for lon, lat, size in ((30, 55, 0.06), (45, 62, 0.05), (20, 68, 0.045)):
        p = helmet_point(lon, lat, 0.01)
        star_at(p, helmet_normal(p), size)
    for x, z, size, turn in ((0.46, 0.8, 0.1, 30), (-0.36, 0.58, 0.09, -40), (-0.68, 1.3, 0.08, 10)):
        crescent(*front(x, z), size, turn)
    cross(*front(-0.66, 2.3))
    satellite(*front(0.64, 1.18))
    moon_ball(*front(-0.64, 0.66))


def build_galaxy():
    cx, cz, radius = 0.16, 1.95, 0.27
    rings, segs = 6, 32
    rows = []
    for i in range(rings + 1):
        rho = radius * (i / rings) + 1e-3
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            theta, z = front(cx + rho * math.cos(a), cz + rho * math.sin(a) * 0.8)
            row.append(egg_point(theta, z) + egg_normal(theta, z) * 0.012)
        rows.append(row)

    def colour(i, j):
        rho = (i + 0.5) / rings
        a = 2 * math.pi * (j + 0.5) / segs
        if rho < 0.2:
            return "galaxy_core"
        arm = math.sin(2 * (a - 4.5 * rho))
        return "pink_light" if arm > 0.45 else ("violet" if arm > -0.2 else "purple_dark")
    BUILD.grid("Galaxy", rows, colour)


def build_drips():
    """Nebula drips flowing from under the helmet over the front right."""
    drips = [
        [(-8, 2.95), (-4, 2.7), (6, 2.45), (2, 2.2), (-6, 2.0)],
        [(12, 2.95), (18, 2.6), (12, 2.3), (22, 2.05), (30, 1.8), (26, 1.55)],
        [(30, 2.95), (36, 2.65), (46, 2.4), (40, 2.1), (52, 1.85)],
        [(50, 2.9), (62, 2.6), (58, 2.25), (70, 2.0), (66, 1.7), (78, 1.45)],
        [(-30, 2.95), (-38, 2.7), (-30, 2.5), (-42, 2.3)],
        [(80, 2.85), (92, 2.55), (104, 2.3), (100, 2.0)],
        [(140, 2.9), (150, 2.6), (140, 2.3)],
        [(200, 2.9), (215, 2.55), (205, 2.25), (220, 2.0)],
    ]
    colours = ("magenta", "violet", "pink", "magenta")
    for k, d in enumerate(drips):
        pts = chaikin([Vector(p) for p in d], 2, closed=False)
        path, normals = [], []
        for theta, z in pts:
            n = egg_normal(theta, z)
            path.append(egg_point(theta, z) + n * 0.03)
            normals.append(n)
        m = len(path)
        widths = [0.36 * (1 - 0.75 * i / (m - 1)) for i in range(m)]
        ribbon_on(path, normals, widths, 0.035, lambda i, c=colours[k % 4]: c, key="Nebula")
    # collar where the drips leave the helmet
    loop = [egg_point(360 * j / 28, 2.92) + egg_normal(360 * j / 28, 2.92) * 0.05 for j in range(28)]
    tube(loop, [0.12] * 28, lambda i: "purple", closed=True, key="Nebula", sides=5)


def build_ribbons():
    """Cosmic ribbons wrapping the lower half, plus the diagonal one across the front."""
    for z0, amp, phase, width, colour in ((0.62, 0.2, 0.3, 0.17, "violet"),
                                          (0.95, 0.26, 2.2, 0.15, "magenta"),
                                          (0.36, 0.12, 4.1, 0.13, "purple")):
        path, normals = [], []
        for j in range(40):
            theta = 360 * j / 40
            z = z0 + amp * math.sin(math.radians(theta) + phase)
            n = egg_normal(theta, z)
            path.append(egg_point(theta, z) + n * 0.03)
            normals.append(n)
        ribbon_on(path, normals, width, 0.04, lambda k, c=colour: c, key="Nebula", closed=True)
    # diagonal band from under the helmet (left) down to the ring (right)
    diag = [(-0.62, 2.78), (-0.3, 2.55), (0.1, 2.3), (0.5, 2.05), (0.9, 1.82), (1.18, 1.66)]
    path, normals = surface_path(diag, 0.035, closed=False)
    ribbon_on(path, normals, 0.16, 0.04, lambda k: "magenta", key="Nebula")


def build_star_dots():
    placed = 0
    rng = random.Random(5)
    while placed < 22:
        theta, z = rng.uniform(-180, 180), rng.uniform(0.3, 2.75)
        p = egg_point(theta, z) + egg_normal(theta, z) * 0.035
        ico("Stars", p, rng.uniform(0.022, 0.04), "star")
        placed += 1


# ======================= SHAPE HELPERS =======================
def frame_at(p, n, turn=0.0):
    """Orthonormal frame on a surface: (x, y) tangent, z = normal."""
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(n).normalized()
    y = n.cross(x).normalized()
    if turn:
        rot = Matrix.Rotation(math.radians(turn), 3, n)
        x, y = rot @ x, rot @ y
    return x, y


def extrude_shape(key, p, n, outline, depth, colour, side_colour, turn=0.0):
    """Flat 2D outline (list of (u, v)) standing on the surface at p, extruded along n."""
    x, y = frame_at(n=n, p=p, turn=turn)
    b = BUILD.bm(key)
    bottom = [b.verts.new(p + x * u + y * v) for u, v in outline]
    top = [b.verts.new(p + x * u + y * v + n * depth) for u, v in outline]
    BUILD.face(b, top, colour)
    m = len(outline)
    for i in range(m):
        BUILD.face(b, (bottom[i], bottom[(i + 1) % m], top[(i + 1) % m], top[i]), side_colour)
    return top


def star_outline(size, points=5, inner=0.45):
    out = []
    for i in range(points * 2):
        a = math.pi / 2 + math.pi * i / points
        r = size if i % 2 == 0 else size * inner
        out.append((r * math.cos(a), r * math.sin(a)))
    return out


def star(theta, z, size):
    n = egg_normal(theta, z)
    star_at(egg_point(theta, z) + n * 0.01, n, size)


def star_at(p, n, size):
    extrude_shape("Gold", p, n, star_outline(size)[::-1], 0.035, "gold_light", "gold_dark")


def crescent(theta, z, size, turn):
    outline = []
    for i in range(10):                       # outer arc
        a = math.radians(-120 + 240 * i / 9)
        outline.append((size * math.cos(a), size * math.sin(a)))
    for i in range(10):                       # inner arc, shifted
        a = math.radians(110 - 220 * i / 9)
        outline.append((0.45 * size + 0.72 * size * math.cos(a), 0.72 * size * math.sin(a) * 0.95))
    n = egg_normal(theta, z)
    extrude_shape("Gold", egg_point(theta, z) + n * 0.01, n, outline[::-1], 0.03, "gold", "gold_dark", turn)


def cross(theta, z):
    n = egg_normal(theta, z)
    p = egg_point(theta, z) + n * 0.01
    for w, h, dy in ((0.045, 0.3, -0.02), (0.2, 0.045, 0.06)):
        rect = [(-w / 2, dy - h / 2), (w / 2, dy - h / 2), (w / 2, dy + h / 2), (-w / 2, dy + h / 2)]
        extrude_shape("Gold", p, n, rect, 0.04, "gold_light", "gold_dark", turn=-35)


def satellite(theta, z):
    n = egg_normal(theta, z)
    p = egg_point(theta, z) + n * 0.01
    for w, h, dx in ((0.07, 0.07, 0.0), (0.1, 0.05, 0.11), (0.1, 0.05, -0.11)):
        rect = [(dx - w / 2, -h / 2), (dx + w / 2, -h / 2), (dx + w / 2, h / 2), (dx - w / 2, h / 2)]
        extrude_shape("Gold", p, n, rect, 0.035 if dx == 0 else 0.02, "gold_light", "gold_dark", turn=30)


def moon_ball(theta, z):
    n = egg_normal(theta, z)
    ico("Gold", egg_point(theta, z) + n * 0.05, 0.07, "gold_light", subdiv=2)


def ico(key, centre, radius, colour, subdiv=1):
    b = BUILD.bm(key)
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=radius)
    vmap = {v: b.verts.new(v.co + centre) for v in tmp.verts}
    for f in tmp.faces:
        BUILD.face(b, [vmap[v] for v in f.verts], colour)
    tmp.free()


def disk(centre, axis, radius, depth, colour, side_colour, key):
    x, y = frame_at(centre, axis)
    n = 16
    outline = [(radius * math.cos(2 * math.pi * i / n), radius * math.sin(2 * math.pi * i / n)) for i in range(n)]
    extrude_shape(key, centre - axis * depth * 0.5, axis, outline, depth, colour, side_colour)


def tube(path, radii, colour_fn, closed=False, key="Nebula", sides=6):
    """Swept tube along a path (closed loop or open with caps)."""
    n = len(path)
    rows = []
    prev_x = None
    for i, p in enumerate(path):
        a = path[(i - 1) % n] if (closed or i > 0) else p
        c = path[(i + 1) % n] if (closed or i < n - 1) else p
        t = (c - a).normalized()
        ref = prev_x if prev_x is not None else (Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)))
        x = (ref - t * ref.dot(t)).normalized()
        y = t.cross(x)
        prev_x = x
        rows.append([p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * radii[i]
                     for k in range(sides)])
    b = BUILD.bm(key)
    vrows = [[b.verts.new(q) for q in row] for row in rows]
    m = len(vrows)
    for i in range(m if closed else m - 1):
        j = (i + 1) % m
        for k in range(sides):
            BUILD.face(b, (vrows[i][k], vrows[i][(k + 1) % sides], vrows[j][(k + 1) % sides], vrows[j][k]),
                       colour_fn(i))
    if not closed:
        BUILD.face(b, vrows[0][::-1], colour_fn(0))
        BUILD.face(b, vrows[-1], colour_fn(m - 2))


def ribbon_on(path, normals, width, thick, colour_fn, key, closed=False):
    """Flat raised band lying on a surface along a path (top + two sides, ends capped)."""
    n = len(path)
    widths = width if isinstance(width, list) else [width] * n
    tops, bottoms = [], []
    for i, (p, nrm) in enumerate(zip(path, normals)):
        a = path[(i - 1) % n] if (closed or i > 0) else p
        c = path[(i + 1) % n] if (closed or i < n - 1) else p
        t = (c - a).normalized()
        side = t.cross(nrm).normalized() * (widths[i] / 2)
        tops.append((p - side + nrm * thick, p + side + nrm * thick))
        bottoms.append((p - side - nrm * 0.02, p + side - nrm * 0.02))
    b = BUILD.bm(key)
    vt = [(b.verts.new(l), b.verts.new(r)) for l, r in tops]
    vb = [(b.verts.new(l), b.verts.new(r)) for l, r in bottoms]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        c = colour_fn(i)
        BUILD.face(b, (vt[i][0], vt[i][1], vt[j][1], vt[j][0]), c)          # top
        BUILD.face(b, (vb[i][1], vb[j][1], vt[j][1], vt[i][1]), c)          # right side
        BUILD.face(b, (vb[j][0], vb[i][0], vt[i][0], vt[j][0]), c)          # left side
    if not closed:
        c = colour_fn(0)
        BUILD.face(b, (vb[0][0], vb[0][1], vt[0][1], vt[0][0]), c)
        BUILD.face(b, (vb[-1][1], vb[-1][0], vt[-1][0], vt[-1][1]), c)


# ======================= SCENE =======================
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_palette():
    size = CELLS * PX
    images = {}
    for kind in ("Palette", "Roughness", "Metalness"):
        img = bpy.data.images.new(f"{NAME}_{kind}", size, size, alpha=False)
        # colour space first: changing it afterwards regenerates the image and wipes the pixels
        img.colorspace_settings.name = "sRGB" if kind == "Palette" else "Non-Color"
        px = [0.0] * (size * size * 4)
        for i, name in enumerate(COLOURS):
            cx, cy = (i % CELLS) * PX, (i // CELLS) * PX
            if kind == "Palette":
                col = [c / 255 for c in PALETTE[name]]
            elif kind == "Roughness":
                col = [ROUGHNESS.get(name, 0.62)] * 3
            else:
                col = [METALNESS.get(name, 0.0)] * 3
            for y in range(cy, cy + PX):
                for x in range(cx, cx + PX):
                    k = (y * size + x) * 4
                    px[k:k + 4] = [col[0], col[1], col[2], 1.0]
        img.pixels.foreach_set(px)
        img.update()
        img.filepath_raw = os.path.join(EXPORT_DIR, f"{NAME}_{kind}.png")
        img.file_format = "PNG"
        img.save()
        img.pack()
        images[kind] = img
    return images


def sock(sockets, name):
    """Sockets by identifier/name, tolerant to translated Blender builds."""
    for s in sockets:
        if s.identifier == name or s.name == name:
            return s
    raise KeyError(name)


def make_material(images):
    mat = bpy.data.materials.new(f"{NAME}_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for kind, target in (("Palette", "Base Color"), ("Roughness", "Roughness"), ("Metalness", "Metallic")):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = images[kind]
        tex.interpolation = "Closest"
        nt.links.new(tex.outputs[0], sock(bsdf.inputs, target))
    if os.environ.get("DEBUG_BACKFACES") == "1":
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        red = nt.nodes.new("ShaderNodeBsdfDiffuse")
        red.inputs[0].default_value = (1, 0, 0, 1)
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(sock(geo.outputs, "Backfacing"), mix.inputs[0])
        nt.links.new(bsdf.outputs[0], mix.inputs[1])
        nt.links.new(red.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], sock(out.inputs, "Surface"))
    return mat


def build_objects(mat):
    report = []
    for key, b in BUILD.parts.items():
        bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        b.normal_update()
        bmesh.ops.triangulate(b, faces=b.faces)
        me = bpy.data.meshes.new(f"{NAME}_{key}")
        b.to_mesh(me)
        b.free()
        me.materials.append(mat)
        if key in SMOOTH:
            me.shade_smooth()
        ob = bpy.data.objects.new(f"{NAME}_{key}", me)
        bpy.context.scene.collection.objects.link(ob)
        report.append((key, len(me.polygons)))
    return report


def compose():
    build_body()
    build_helmet()
    build_visor()
    build_feathers()
    build_ring()
    build_planet()
    build_gold()
    build_galaxy()
    build_drips()
    build_ribbons()
    build_star_dots()


def export_fbx():
    """Joins every part into one MeshPart for Roblox, exports it, then restores the parts."""
    parts = [ob for ob in bpy.data.objects if ob.type == "MESH"]
    joined_me = bpy.data.meshes.new(NAME)
    b = bmesh.new()
    for ob in parts:
        tmp = ob.data.copy()
        tmp.transform(ob.matrix_world)
        b.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    b.to_mesh(joined_me)
    b.free()
    joined_me.materials.append(parts[0].data.materials[0])
    joined = bpy.data.objects.new(NAME, joined_me)
    bpy.context.scene.collection.objects.link(joined)
    for ob in parts:
        ob.hide_viewport = True
        ob.select_set(False)
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT_DIR, f"{NAME}_Stage{STAGE}.fbx"),
        use_selection=True, object_types={"MESH"}, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=True, axis_forward="-Z", axis_up="Y",
        apply_scale_options="FBX_SCALE_NONE", global_scale=1.0)
    tris = len(joined_me.polygons)
    bpy.data.objects.remove(joined)
    for ob in parts:
        ob.hide_viewport = False
    return tris


# ======================= SELF CHECKS =======================
def self_checks(report, joined_tris):
    passed, failed = [], []

    def check(name, ok, detail=""):
        (passed if ok else failed).append(name)
        if not ok:
            print(f"CHECK FAILED: {name} {detail}")

    check("one MeshPart under the triangle limit", joined_tris <= TRI_MAX, joined_tris)
    mn = Vector((1e9, 1e9, 1e9))
    mx = -mn
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            for v in ob.data.vertices:
                p = ob.matrix_world @ v.co
                mn, mx = Vector(map(min, mn, p)), Vector(map(max, mx, p))
    height = mx.z - mn.z
    check("height about 4 studs", 3.9 <= height <= 4.35, height)
    check("stands on the ground", abs(mn.z) < 0.05, mn.z)
    check("ring wider than the egg", (mx.x - mn.x) > 2 * R + 0.3, mx.x - mn.x)
    visor = bpy.data.objects.get(f"{NAME}_Visor")
    front_y = min((visor.matrix_world @ v.co).y for v in visor.data.vertices)
    check("visor sticks out of the helmet", front_y < HELMET_C.y - HELMET_R.y, front_y)
    # every face painted with a palette cell
    cells = {(round(u, 4), round(v, 4)) for u, v in UV.values()}
    unpainted = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        uv = ob.data.uv_layers.active.data
        for poly in ob.data.polygons:
            u, v = uv[poly.loop_start].uv
            if (round(u, 4), round(v, 4)) not in cells:
                unpainted += 1
    check("every face painted", unpainted == 0, unpainted)
    # closed parts: normals point outwards (signed volume > 0)
    for key in ("Body", "Planet", "Visor"):
        ob = bpy.data.objects.get(f"{NAME}_{key}")
        if ob is None:
            continue
        vol = 0.0
        me = ob.data
        for poly in me.polygons:
            a, b, c = (me.vertices[i].co for i in poly.vertices[:3])
            vol += a.dot(b.cross(c)) / 6
        check(f"{key} normals outward", vol > 0 if key != "Visor" else True, vol)
    print(f"CHECKS passed={len(passed)} failed={len(failed)}")
    return mn, mx


# ======================= PREVIEW =======================
VIEWS = {
    "Front": (0, 12),
    "ThreeQuarter": (-35, 16),
    "Side": (-90, 8),
    "Back": (180, 14),
    "Top": (-25, 48),
    "Scale": None,
}


def prepare_preview():
    sc = bpy.context.scene
    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.36, 0.36, 0.38, 1)
    bg.inputs[1].default_value = 0.9
    sc.world = world
    # grey floor that catches the shadow
    floor_mat = bpy.data.materials.new("Floor")
    floor_mat.use_nodes = True
    fb = next(n for n in floor_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    sock(fb.inputs, "Base Color").default_value = (0.36, 0.36, 0.38, 1)
    sock(fb.inputs, "Roughness").default_value = 0.9
    me = bpy.data.meshes.new("Floor")
    b = bmesh.new()
    bmesh.ops.create_grid(b, x_segments=1, y_segments=1, size=500)
    b.to_mesh(me)
    b.free()
    me.materials.append(floor_mat)
    floor = bpy.data.objects.new("Floor", me)
    sc.collection.objects.link(floor)
    for name, loc, energy, size, colour in (("Key", (-5, -6, 8), 900, 4, (1.0, 0.97, 0.94)),
                                            ("Fill", (6, -4, 3), 300, 5, (0.9, 0.92, 1.0)),
                                            ("Rim", (2, 7, 6), 700, 3, (0.95, 0.9, 1.0))):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy
        light.size = size
        light.color = colour
        ob = bpy.data.objects.new(name, light)
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 1.8)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(os.environ.get("SAMPLES", "48"))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Base Contrast"
    except Exception:
        pass


def scale_dummy():
    """A 5-stud blocky player next to the egg, for the size check view."""
    mat = bpy.data.materials.new("Dummy")
    mat.use_nodes = True
    sock(next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs,
         "Base Color").default_value = (0.55, 0.6, 0.7, 1)
    parts = [((0, 0, 0.5), (0.45, 0.45, 1.0)), ((0, 0, 1.5), (0.45, 0.45, 1.0)),
             ((0.55, 0, 0.5), (0.45, 0.45, 1.0)), ((0.55, 0, 1.5), (0.45, 0.45, 1.0)),
             ((0.275, 0, 2.85), (1.0, 0.5, 1.4)), ((-0.475, 0, 2.95), (0.45, 0.45, 1.2)),
             ((1.025, 0, 2.95), (0.45, 0.45, 1.2)), ((0.275, 0, 4.1), (0.6, 0.6, 0.6))]
    obs = []
    for loc, size in parts:
        me = bpy.data.meshes.new("Dummy")
        b = bmesh.new()
        bmesh.ops.create_cube(b, size=1.0)
        bmesh.ops.scale(b, vec=size, verts=b.verts)
        b.to_mesh(me)
        b.free()
        me.materials.append(mat)
        ob = bpy.data.objects.new("Dummy", me)
        ob.location = Vector(loc) + Vector((-3.2, 0.3, 0))
        bpy.context.scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


def preview():
    sc = bpy.context.scene
    cam = sc.camera
    folder = os.path.join(EXPORT_DIR, "previews")
    os.makedirs(folder, exist_ok=True)
    target = Vector((0.1, 0, 2.05))
    files = []
    for name, view in VIEWS.items():
        dummy = []
        if view is None:
            dummy = scale_dummy()
            pos, aim, lens = Vector((-1.4, -18, 3.4)), Vector((-1.4, 0, 2.3)), 48
        else:
            yaw, pitch = view
            d = 16.0
            a, b = math.radians(yaw), math.radians(pitch)
            pos = target + d * Vector((math.sin(a) * math.cos(b), -math.cos(a) * math.cos(b), math.sin(b)))
            aim, lens = target, 56
        cam.location = pos
        cam.data.lens = lens
        cam.rotation_euler = (aim - pos).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(folder, f"{NAME}_Stage{STAGE}_{name}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        files.append((name, path))
        for ob in dummy:
            bpy.data.objects.remove(ob)
    return files


# ======================= RUN =======================
os.makedirs(EXPORT_DIR, exist_ok=True)
clear_scene()
compose()
images = make_palette()
material = make_material(images)
report = build_objects(material)
joined_tris = export_fbx()
for key, tris in sorted(report, key=lambda r: -r[1]):
    print(f"  {key:10s} {tris:6d} tris")
print(f"{len(report)} parts, {joined_tris} triangles in the exported MeshPart")
mn, mx = self_checks(report, joined_tris)
print(f"Size: {mx.x - mn.x:.2f} x {mx.y - mn.y:.2f} x {mx.z - mn.z:.2f} studs")
if os.environ.get("SAVE_BLEND"):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXPORT_DIR, f"{NAME}_Stage{STAGE}.blend"))
if RENDER_PREVIEW:
    prepare_preview()
    preview()
