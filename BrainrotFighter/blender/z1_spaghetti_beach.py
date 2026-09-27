"""
Brainrot Fighter - Zone 1 "Spaghetti Beach": decor kit + zone layout.
Written for Blender 4.x, also runs on 5.x.

HOW TO RUN
    Blender > Scripting tab > Open this file > Run Script (Alt+P).
    Headless:  blender -b --python z1_spaghetti_beach.py

WHAT IT BUILDS
    Z1_Assets   one of each asset, lined up in a row north of the zone. An asset
                is a single mesh, or an Empty named after the asset with one child
                mesh per colour (named <asset>__<colour>). Every origin sits at the
                centre of the asset's base (z = 0) and transforms are applied.
    Z1_Layout   linked copies placed on the 800 x 800 zone plan, plus preview-only
                helpers (sand floor, sauce sea, keep-out guides) in Z1_Preview.
    EXPORT_DIR  one FBX per asset of Z1_Assets, with Roblox's recommended settings.

CONVENTIONS
    1 Blender unit = 1 Roblox stud, Z up, a character is ~5 studs tall.
    The local front of every asset is -Y (what Blender's Front view shows).
    One flat colour per mesh (Principled BSDF Base Color): no texture, no text.
    Re-running deletes and rebuilds only what the script made (the Z1_ collections
    and Z1_ materials); the rest of the .blend file is left alone.
    The script checks its own output (triangle budget, origins, plan keep-outs)
    and ends with "CHECKS passed=N failed=M".

Nodes are looked up by type and sockets by identifier, never by their translated
names, so the script also runs on a Blender set to French.
"""

import math
import os
import random
import zlib

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

# ---------------------------------------------------------------- SETTINGS

# One FBX per asset lands here. Change it freely, e.g. r"D:\Roblox\Z1_FBX".
EXPORT_DIR = os.path.join(os.path.expanduser("~"), "BrainrotFighter", "Z1_SpaghettiBeach_FBX")
EXPORT_FBX = True

PREFIX = "Z1_"
ASSETS_COL = "Z1_Assets"
LAYOUT_COL = "Z1_Layout"
PREVIEW_COL = "Z1_Preview"

MAX_TRIS = 10000     # Roblox hard limit per MeshPart
SPLIT_TRIS = 9500    # a colour group above this is split into several meshes
ROW_X0 = -620.0      # the Z1_Assets row starts here...
ROW_Y = 760.0        # ...north of the zone preview
ROW_GAP = 16.0

# Zone plan (studs). The zone is 800 x 800, centred on the origin.
HALF = 400.0
SPAWN = (0.0, -340.0)
SPAWN_FREE_R = 40.0
STAR_POS = (-200.0, -340.0)
ARCH_X = (132.0, 168.0)          # two arches inside x = 120..180, on y = -340
ARCH_BAND = (120.0, 180.0)
COMBAT_Y = (-270.0, 140.0)
COMBAT_SIDE_X = 260.0            # |x| >= this counts as "the sides" of the combat zone
ARENA_POS = (0.0, 270.0)
ARENA_R = 90.0
VOLCANO_POS = (0.0, 480.0)
SMALL_MAX_H = 9.0                # tallest asset allowed in the middle of the combat zone
MIDDLE_SPACING = 45.0            # minimum distance between two small middle props

# sRGB hex colours. Roblox gets the same values in Studio (see README.md).
PALETTE = {
    "Pasta": "#F6C945",
    "PastaDark": "#E3A631",
    "Spinach": "#6DBE45",
    "Cheese": "#FFDD66",
    "Tomato": "#E23B2E",
    "SauceDeep": "#B8261C",
    "Basil": "#3FA34D",
    "Cream": "#FFF3D6",
    "Parmesan": "#F4DE8E",
    "Rind": "#D69A3C",
    "Meatball": "#7B4428",
    "Silver": "#C9D1D9",
    "Porcelain": "#FAF6EC",
    "Majolica": "#2F6FD0",
    "Gold": "#F2B632",
    "Wood": "#6E3F22",
    "Breadstick": "#D9A35B",
    "Glass": "#4F8F3A",
    "Oil": "#E8C43A",
    "Cork": "#C08A55",
    "Light": "#FFE680",
    "Glow": "#7CF08C",
    "Pistachio": "#A6D46E",
    "Strawberry": "#F592B0",
    "Waffle": "#D29B52",
    "Dark": "#4A2A1A",
    "Sand": "#F3D58E",
    "Guide": "#29B6F6",
}
ROUGHNESS = {"Silver": 0.3, "Gold": 0.3, "Glass": 0.15, "Porcelain": 0.25, "Oil": 0.2}
METALLIC = {"Silver": 0.9, "Gold": 0.9}

TAU = math.tau
UP = Vector((0.0, 0.0, 1.0))


# ---------------------------------------------------------------- MATERIALS


def find_node(tree, node_type):
    for node in tree.nodes:
        if node.type == node_type:
            return node
    return None


def find_socket(sockets, identifier):
    """Identifiers are stable; socket names are translated with the UI language."""
    for sock in sockets:
        if sock.identifier == identifier:
            return sock
    return None


def srgb_to_linear(hex_color):
    value = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(value[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def get_material(key):
    """One flat Principled BSDF per palette key, shared by every asset."""
    name = PREFIX + key
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    color = srgb_to_linear(PALETTE[key])
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0) and not mat.use_nodes:
        mat.use_nodes = True  # always on (and deprecated) from Blender 5.0
    tree = mat.node_tree
    bsdf = find_node(tree, "BSDF_PRINCIPLED")
    if bsdf is None:
        bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = find_node(tree, "OUTPUT_MATERIAL") or tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(bsdf.outputs[0], output.inputs[0])
    for identifier, value in (("Base Color", (*color, 1.0)),
                              ("Roughness", ROUGHNESS.get(key, 0.7)),
                              ("Metallic", METALLIC.get(key, 0.0))):
        sock = find_socket(bsdf.inputs, identifier)
        if sock is not None:
            sock.default_value = value
    mat.diffuse_color = (*color, 1.0)  # solid viewport colour
    mat["z1_color"] = key
    return mat


# ---------------------------------------------------------------- GEOMETRY


def clean_face(face):
    """Drop repeated indices (collapsed poles); None if nothing valid is left."""
    out = []
    for i in face:
        if not out or out[-1] != i:
            out.append(i)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) < 3 or len(set(out)) != len(out):
        return None
    return out


class Geo:
    """A vertex/face soup. Every primitive returns one; transforms chain."""

    def __init__(self, verts=None, faces=None):
        self.verts = [Vector(v) for v in (verts or [])]
        self.faces = []
        for f in faces or []:
            f = clean_face(f)
            if f:
                self.faces.append(f)

    def transform(self, matrix):
        self.verts = [matrix @ v for v in self.verts]
        return self

    def move(self, x=0.0, y=0.0, z=0.0):
        return self.transform(Matrix.Translation((x, y, z)))

    def rotate(self, degrees, axis="Z"):
        return self.transform(Matrix.Rotation(math.radians(degrees), 4, axis))

    def scale(self, sx, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        return self.transform(Matrix.Diagonal((sx, sy, sz, 1.0)))

    def align(self, direction):
        """Rotate so local +Z points along `direction`."""
        q = UP.rotation_difference(Vector(direction).normalized())
        return self.transform(q.to_matrix().to_4x4())

    def warp(self, fn):
        self.verts = [Vector(fn(v)) for v in self.verts]
        return self

    def add(self, other):
        offset = len(self.verts)
        self.verts.extend(v.copy() for v in other.verts)
        self.faces.extend([i + offset for i in f] for f in other.faces)
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)


def geo_from_bmesh(bm):
    bm.verts.index_update()
    return Geo([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces])


def geo_to_bmesh(geo):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in geo.verts]
    for f in geo.faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass  # duplicate face
    return bm


def clip_below(geo, z=0.0):
    """Cut everything under the ground plane and cap the hole."""
    bm = geo_to_bmesh(geo)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0), clear_inner=True)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    out = geo_from_bmesh(bm)
    bm.free()
    return out


def lathe(profile, segs, radial=None):
    """Surface of revolution around Z. `profile` is [(r, z)] from bottom to top;
    r = 0 collapses to a pole, otherwise the end is capped flat.
    radial(angle, z, r) -> r lets the caller carve ridges."""
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r < 1e-6:
            verts.append(Vector((0.0, 0.0, z)))
            rings.append([len(verts) - 1] * segs)
            continue
        ring = []
        for i in range(segs):
            a = TAU * i / segs
            rr = radial(a, z, r) if radial else r
            verts.append(Vector((rr * math.cos(a), rr * math.sin(a), z)))
            ring.append(len(verts) - 1)
        rings.append(ring)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            faces.append([lo[i], lo[j], hi[j], hi[i]])
    if profile[0][0] >= 1e-6:
        faces.append(list(reversed(rings[0])))
    if profile[-1][0] >= 1e-6:
        faces.append(list(rings[-1]))
    return Geo(verts, faces)


def revolve(section, segs, a0=0.0, a1=None):
    """Sweep a closed (r, z) section, counter-clockwise, around Z. Full turn when
    a1 is None, otherwise an arc from a0 to a1 capped at both ends."""
    full = a1 is None
    if full:
        a1 = a0 + TAU
    n_rings = segs if full else segs + 1
    m = len(section)
    verts = []
    for k in range(n_rings):
        a = a0 + (a1 - a0) * k / segs
        c, s = math.cos(a), math.sin(a)
        verts.extend(Vector((r * c, r * s, z)) for r, z in section)
    faces = []
    for k in range(segs):
        k2 = (k + 1) % n_rings
        for i in range(m):
            i2 = (i + 1) % m
            faces.append([k * m + i, k2 * m + i, k2 * m + i2, k * m + i2])
    if not full:
        faces.append(list(range(m)))
        faces.append([(n_rings - 1) * m + i for i in reversed(range(m))])
    return Geo(verts, faces)


def circle_section(rc, zc, radius, n=8):
    return [(rc + radius * math.cos(TAU * i / n), zc + radius * math.sin(TAU * i / n)) for i in range(n)]


def rect_section(r0, r1, z0, z1):
    return [(r0, z0), (r1, z0), (r1, z1), (r0, z1)]


def sweep(path, radius, sides=6, start="round", end="round", ridge=0.0, squash=(1.0, 1.0),
          up_hint=None):
    """Tube along a polyline with rotation-minimising frames.
    radius: float or fn(t) with t in 0..1 along the path.
    start / end: "round", "flat" or None (open). ridge > 0 alternates the radius
    of every other side (penne-style grooves)."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1] or 1.0
    tangents = []
    for i in range(n):
        d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tangents.append(d.normalized())
    t0 = tangents[0]
    hint = Vector(up_hint) if up_hint else (UP if abs(t0.z) < 0.9 else Vector((1.0, 0.0, 0.0)))
    nrm = (hint - t0 * hint.dot(t0)).normalized()
    frames = []
    for i in range(n):
        if i > 0:
            nrm = tangents[i - 1].rotation_difference(tangents[i]) @ nrm
            nrm = (nrm - tangents[i] * nrm.dot(tangents[i])).normalized()
        frames.append((nrm.copy(), tangents[i].cross(nrm)))

    def rad(i):
        return radius(lengths[i] / total) if callable(radius) else radius

    verts, faces = [], []
    for i, p in enumerate(pts):
        nv, bv = frames[i]
        r = rad(i)
        for k in range(sides):
            a = TAU * k / sides
            rr = r * (1.0 + (ridge if k % 2 == 0 else -ridge))
            verts.append(p + nv * (math.cos(a) * rr * squash[0]) + bv * (math.sin(a) * rr * squash[1]))
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append([i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k])

    def cap(ring_start, p, t, r, forward):
        ring = list(range(ring_start, ring_start + sides))
        if forward is None:
            return
        style = end if forward else start
        if style is None:
            return
        sign = 1.0 if forward else -1.0
        if style == "flat":
            faces.append(ring if forward else list(reversed(ring)))
            return
        nv, bv = frames[-1] if forward else frames[0]
        mid = len(verts)
        for k in range(sides):  # an inner ring, then the pole: a rounded tip
            a = TAU * k / sides
            verts.append(p + t * (sign * r * 0.55) + nv * (math.cos(a) * r * 0.72 * squash[0])
                         + bv * (math.sin(a) * r * 0.72 * squash[1]))
        pole = len(verts)
        verts.append(p + t * (sign * r * 0.95))
        for k in range(sides):
            k2 = (k + 1) % sides
            if forward:
                faces.append([ring[k], ring[k2], mid + k2, mid + k])
                faces.append([mid + k, mid + k2, pole])
            else:
                faces.append([ring[k2], ring[k], mid + k, mid + k2])
                faces.append([mid + k2, mid + k, pole])

    cap(0, pts[0], tangents[0], rad(0), False)
    cap((n - 1) * sides, pts[-1], tangents[-1], rad(n - 1), True)
    return Geo(verts, faces)


def thick_grid(fn, nu, nv, thickness, closed_u=False):
    """Solid sheet: fn(u, v) -> point on the mid-surface (u, v in 0..1), offset by
    +-thickness/2 along the surface normal, with side walls."""
    cols = nu if closed_u else nu + 1
    mid = [[Vector(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(cols)]

    def at(i, j):
        i = i % nu if closed_u else max(0, min(nu, i))
        return mid[i][max(0, min(nv, j))]

    verts = []
    for side in (1.0, -1.0):
        for i in range(cols):
            for j in range(nv + 1):
                n = (at(i + 1, j) - at(i - 1, j)).cross(at(i, j + 1) - at(i, j - 1))
                n = n.normalized() if n.length > 1e-9 else UP
                verts.append(mid[i][j] + n * (side * thickness * 0.5))
    off = cols * (nv + 1)

    def top(i, j):
        return (i % cols) * (nv + 1) + j

    def bot(i, j):
        return off + top(i, j)

    faces = []
    for i in range(nu):
        for j in range(nv):
            faces.append([top(i, j), top(i + 1, j), top(i + 1, j + 1), top(i, j + 1)])
            faces.append([bot(i, j + 1), bot(i + 1, j + 1), bot(i + 1, j), bot(i, j)])
        faces.append([top(i, 0), bot(i, 0), bot(i + 1, 0), top(i + 1, 0)])
        faces.append([top(i + 1, nv), bot(i + 1, nv), bot(i, nv), top(i, nv)])
    if not closed_u:
        for j in range(nv):
            faces.append([top(0, j + 1), bot(0, j + 1), bot(0, j), top(0, j)])
            faces.append([top(nu, j), bot(nu, j), bot(nu, j + 1), top(nu, j + 1)])
    return Geo(verts, faces)


def lattice_box(x0, x1, y0, y1, z0, z1, nx, ny, nz, warp=None):
    """Box skin subdivided nx * ny * nz; warp(point, (i, j, k)) moves each vertex."""
    index, verts = {}, []

    def vid(i, j, k):
        key = (i, j, k)
        if key not in index:
            p = Vector((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z0 + (z1 - z0) * k / nz))
            index[key] = len(verts)
            verts.append(Vector(warp(p, key)) if warp else p)
        return index[key]

    faces = []
    for i in range(nx):
        for j in range(ny):
            faces.append([vid(i, j, 0), vid(i, j + 1, 0), vid(i + 1, j + 1, 0), vid(i + 1, j, 0)])
            faces.append([vid(i, j, nz), vid(i + 1, j, nz), vid(i + 1, j + 1, nz), vid(i, j + 1, nz)])
    for i in range(nx):
        for k in range(nz):
            faces.append([vid(i, 0, k), vid(i + 1, 0, k), vid(i + 1, 0, k + 1), vid(i, 0, k + 1)])
            faces.append([vid(i, ny, k), vid(i, ny, k + 1), vid(i + 1, ny, k + 1), vid(i + 1, ny, k)])
    for j in range(ny):
        for k in range(nz):
            faces.append([vid(0, j, k), vid(0, j, k + 1), vid(0, j + 1, k + 1), vid(0, j + 1, k)])
            faces.append([vid(nx, j, k), vid(nx, j + 1, k), vid(nx, j + 1, k + 1), vid(nx, j, k + 1)])
    return Geo(verts, faces)


def x_extrude(section_at, x0, x1, nx):
    """Extrude a counter-clockwise (y, z) section along X; section_at(x) may vary
    with x. The end caps are planar at x0 and x1, so modular pieces tile exactly."""
    verts, faces, m = [], [], 0
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        sec = section_at(x)
        m = len(sec)
        verts.extend((x, y, z) for y, z in sec)
    for i in range(nx):
        for j in range(m):
            j2 = (j + 1) % m
            faces.append([i * m + j, i * m + j2, (i + 1) * m + j2, (i + 1) * m + j])
    faces.append(list(reversed(range(m))))
    faces.append([nx * m + j for j in range(m)])
    return Geo(verts, faces)


def prism(outline, depth):
    """Extrude a counter-clockwise XY outline along +Z, from 0 to depth."""
    n = len(outline)
    verts = [(x, y, 0.0) for x, y in outline] + [(x, y, depth) for x, y in outline]
    faces = [list(reversed(range(n))), list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    return Geo(verts, faces)


def radial_solid(rfun, layers, segs):
    """Closed solid with a free outline: rfun(angle) is the outline radius and
    layers = [(scale, z)] from bottom to top. Ends are closed on a centre vertex."""
    verts, faces, rings = [], [], []
    for scale, z in layers:
        ring = []
        for i in range(segs):
            a = TAU * i / segs
            r = rfun(a) * scale
            verts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
            ring.append(len(verts) - 1)
        rings.append(ring)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            faces.append([lo[i], lo[j], hi[j], hi[i]])
    cb = len(verts)
    verts.append(Vector((0.0, 0.0, layers[0][1])))
    ct = len(verts)
    verts.append(Vector((0.0, 0.0, layers[-1][1])))
    for i in range(segs):
        j = (i + 1) % segs
        faces.append([cb, rings[0][j], rings[0][i]])
        faces.append([ct, rings[-1][i], rings[-1][j]])
    return Geo(verts, faces)


def box(sx, sy, sz, bevel=0.0, segments=2):
    """Box centred on the origin, optionally with rounded (bevelled) edges."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if bevel > 0.0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segments,
                        affect="EDGES", profile=0.5)
    geo = geo_from_bmesh(bm)
    bm.free()
    return geo


def ico(radius, subdiv=2, lumps=0.0, seed=0, squash=1.0):
    """Icosphere centred on the origin; lumps > 0 makes it knobbly (meatballs)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    geo = geo_from_bmesh(bm)
    bm.free()
    off = Vector((seed * 7.31, seed * 3.17, seed * 5.53))

    def shape(v):
        d = v.normalized()
        k = 1.0
        if lumps > 0.0:
            k += lumps * noise.noise(d * 1.7 + off) + lumps * 0.5 * noise.noise(d * 4.1 + off)
        return Vector((d.x * radius * k, d.y * radius * k, d.z * radius * k * squash))

    return geo.warp(shape)


def sphere(radius, segs=12, rings=7):
    profile = [(radius * math.sin(math.pi * i / rings), -radius * math.cos(math.pi * i / rings))
               for i in range(rings + 1)]
    return lathe(profile, segs)


def cylinder(radius, height, segs=12):
    return lathe([(0.0, 0.0), (radius, 0.0), (radius, height), (0.0, height)], segs)


def blob(radius, height, seed, segs=18, wobble=0.16):
    """Wobbly flat puddle / mound resting on z = 0."""
    rng = random.Random(seed)
    p1, p2 = rng.uniform(0, TAU), rng.uniform(0, TAU)

    def rfun(a):
        return radius * (1.0 + wobble * (0.6 * math.sin(3 * a + p1) + 0.4 * math.sin(5 * a + p2)))

    return radial_solid(rfun, [(1.0, 0.0), (0.93, height * 0.75), (0.55, height)], segs)


def leaf(length, width, thickness=0.3, fold=0.18, bend=0.25):
    """Basil leaf along +X from the origin, folded along its midrib."""
    def fn(u, v):
        s = (v - 0.5) * 2.0
        half = width * 0.5 * max(math.sin(math.pi * u) ** 0.7, 0.05) * (1.0 - 0.3 * u)
        z = fold * width * abs(s) - bend * length * (u - 0.35) ** 2 + bend * length * 0.12
        return (u * length, s * half, z)

    return thick_grid(fn, 8, 4, thickness)


def surface_frame(normal):
    return UP.rotation_difference(Vector(normal).normalized()).to_matrix().to_4x4()


def periodic_hash(x, y, period, half):
    """Stable 0..1 value that repeats every `period` along x (modular pieces)."""
    kx = round((x + half) % period, 2) % period
    ky = round(y, 2) + 0.0
    return (zlib.crc32(f"{kx:.2f}|{ky:.2f}".encode()) & 0xFFFFFFFF) / 2 ** 32


def interp_profile(profile, z):
    """Radius of a (r, z) profile, z increasing, at height z."""
    if z <= profile[0][1]:
        return profile[0][0]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        if z0 <= z <= z1:
            f = (z - z0) / (z1 - z0) if z1 > z0 else 0.0
            return r0 + (r1 - r0) * f
    return profile[-1][0]


# ---------------------------------------------------------------- ASSET


class Asset:
    """Collects geometry per colour, then emits one mesh per colour.

    anchor: forced (x, y) origin, e.g. the foot of a leaning trunk. By default the
    origin is the centre of the bounding box footprint. The lowest point always
    ends up at z = 0.
    """

    def __init__(self, name, anchor=None):
        self.name = PREFIX + name
        self.anchor = anchor
        self.groups = {}
        self.root = None
        self.bbox = None     # (min Vector, max Vector) in local space, after pivoting

    def add(self, color, geo, smooth=False):
        if color not in PALETTE:
            raise KeyError(f"{self.name}: unknown colour '{color}'")
        self.groups.setdefault(color, []).append((geo, smooth))
        return geo

    def _pivot(self):
        pts = [v for chunks in self.groups.values() for geo, _ in chunks for v in geo.verts]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        cx, cy = self.anchor if self.anchor else ((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5)
        shift = Vector((-cx, -cy, -lo.z))
        self.bbox = (lo + shift, hi + shift)
        return shift

    def _buckets(self, chunks):
        buckets, current, count = [], [], 0
        for geo, smooth in chunks:
            t = geo.tris()
            if current and count + t > SPLIT_TRIS:
                buckets.append(current)
                current, count = [], 0
            current.append((geo, smooth))
            count += t
        if current:
            buckets.append(current)
        return buckets

    def build(self, collection):
        shift = self._pivot()
        meshes = []
        for color, chunks in self.groups.items():
            for n, bucket in enumerate(self._buckets(chunks)):
                suffix = f"__{color}" + (f"_{n + 1}" if n else "")
                meshes.append(make_mesh_object(self.name + suffix, bucket, color, shift, collection))
        if len(meshes) == 1:
            obj = meshes[0]
            obj.name = self.name
            obj.data.name = self.name
            self.root = obj
            return obj
        root = bpy.data.objects.new(self.name, None)
        root.empty_display_type = "PLAIN_AXES"
        root.empty_display_size = 3.0
        collection.objects.link(root)
        for obj in meshes:
            obj.parent = root
        self.root = root
        return root

    def footprint_radius(self):
        lo, hi = self.bbox
        return max(Vector((x, y)).length for x in (lo.x, hi.x) for y in (lo.y, hi.y))

    def height(self):
        return self.bbox[1].z - self.bbox[0].z


def make_mesh_object(name, bucket, color, shift, collection):
    verts, faces, flags = [], [], []
    for geo, smooth in bucket:
        off = len(verts)
        verts.extend(tuple(v + shift) for v in geo.verts)
        faces.extend([i + off for i in f] for f in geo.faces)
        flags.extend([smooth] * len(geo.faces))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    if len(mesh.polygons) == len(flags):
        mesh.polygons.foreach_set("use_smooth", flags)
    mesh.validate(clean_customdata=False)
    if any(flags):
        if hasattr(mesh, "set_sharp_from_angle"):          # Blender 4.1+
            mesh.set_sharp_from_angle(angle=math.radians(48.0))
        elif hasattr(mesh, "use_auto_smooth"):             # Blender 4.0
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = math.radians(48.0)
    mesh.materials.append(get_material(color))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------- ASSETS: BEACH


def fork_palm(label, height, seed):
    """Fork handle trunk planted in the sand, tines up, a nest of spaghetti
    twirled on the tines and two tiers of fat noodles drooping like palm fronds,
    meatball 'coconuts'. The origin is the foot of the handle."""
    rng = random.Random(seed)
    s = height / 40.0
    a = Asset(f"ForkPalm_{label}", anchor=(0.0, 0.0))
    trunk_h = height * 0.66
    lean = height * 0.10
    head_h, tine_len = 3.6 * s, 6.5 * s

    path = [Vector((lean * math.sin(t * math.pi / 2.0), 0.0, trunk_h * t))
            for t in (i / 12 for i in range(13))]

    def handle_r(t):
        return s * (2.0 - 0.85 * t + 0.4 * math.exp(-((t - 0.06) / 0.07) ** 2))

    a.add("Silver", sweep(path, handle_r, sides=10, start="flat", end="flat",
                          squash=(1.0, 0.5), up_hint=(1.0, 0.0, 0.0)), smooth=True)

    # Fork head: a flat outline (neck, shoulders, 4 tines) extruded in Y.
    w0, wide, zb = 1.15 * s, 3.3 * s, head_h
    gap = 0.7 * s
    tw = (2 * wide - 3 * gap) / 4
    pts = [(-w0, 0.0), (w0, 0.0)]
    for k in range(1, 5):
        f = k / 4
        pts.append((w0 + (wide - w0) * math.sin(f * math.pi / 2), zb * f))
    for ti in range(4):
        xr = wide - ti * (tw + gap)
        xl = xr - tw
        pts += [(xr, zb + tine_len), ((xr + xl) / 2, zb + tine_len + tw * 0.6), (xl, zb + tine_len)]
        if ti < 3:
            pts += [(xl, zb + 0.3 * s), (xl - gap, zb + 0.3 * s)]
    for k in (3, 2, 1):
        f = k / 4
        pts.append((-(w0 + (wide - w0) * math.sin(f * math.pi / 2)), zb * f))
    thick = 1.1 * s
    head = prism(pts, thick).rotate(90, "X").move(lean, thick / 2, trunk_h - 0.3 * s)
    a.add("Silver", head)

    # A fat nest of spaghetti twirled around the tines: three helices.
    top = trunk_h + zb
    strand = 0.85 * s
    nest_h = tine_len * 0.7
    for phase, tilt in ((0.0, 0.0), (2.1, 0.6), (4.2, -0.6)):
        helix = []
        turns, steps = 2.2, 36
        for i in range(steps + 1):
            t = i / steps
            ang = phase + TAU * turns * t
            rx = wide * (1.2 + 0.1 * math.sin(t * 7 + phase))
            z = top + 0.5 * s + nest_h * t + tilt * s * math.sin(ang)
            helix.append((lean + rx * math.cos(ang), wide * 0.9 * math.sin(ang), z))
        a.add("Pasta", sweep(helix, strand, sides=6), smooth=True)

    # Fronds: long ones rising then drooping, shorter ones in between.
    z0 = top + 0.5 * s + nest_h
    fronds = {"Small": 12, "Medium": 14, "Large": 16}[label]
    for k in range(fronds):
        upper = k % 2 == 0
        phi = TAU * k / fronds + rng.uniform(-0.12, 0.12)
        direction = Vector((math.cos(phi), math.sin(phi), 0.0))
        perp = Vector((-direction.y, direction.x, 0.0))
        length = height * (rng.uniform(0.40, 0.48) if upper else rng.uniform(0.27, 0.33))
        rise = 0.6 if upper else 0.3
        start = Vector((lean, 0.0, z0 - (0.0 if upper else 1.4 * s))) + direction * (wide * 0.8)
        frond = []
        for i in range(15):
            t = i / 14
            wig = 0.4 * s * math.sin(t * 9.0 + k)
            frond.append(start + direction * (length * t) + perp * wig
                         + UP * (length * (rise * t - (rise + 0.5) * t * t)))
        tail = frond[-1]
        for j in range(1, 4):
            frond.append(tail + direction * (0.4 * s * j) + UP * (-1.8 * s * j)
                         + perp * (0.3 * s * math.sin(j * 2.0 + k)))
        a.add("Pasta", sweep(frond, strand * (1.0 if upper else 0.9), sides=6), smooth=True)

    # Meatball coconuts under the nest.
    for k, ang in enumerate((0.5, 2.6, 4.4)):
        ball = ico(1.4 * s, 2, lumps=0.1, seed=seed + k)
        a.add("Meatball", ball.move(lean + 2.3 * s * math.cos(ang), 1.6 * s * math.sin(ang),
                                    top - 0.4 * s), smooth=True)
    return a


def pasta_penne():
    """Ridged hollow tube lying half-sunk in the sand. The slanted cuts face
    sideways so the hollow shows from the ground."""
    a = Asset("PastaRock_Penne")
    length, r_out, r_in, sides, rings, slant = 16.0, 3.4, 2.2, 24, 6, 0.8
    outer, inner, verts = [], [], []
    for i in range(rings):
        u = i / (rings - 1)
        o_row, i_row = [], []
        for j in range(sides):
            th = TAU * j / sides
            ro = r_out * (1.0 + (0.09 if j % 2 == 0 else -0.09))
            for radius, row in ((ro, o_row), (r_in, i_row)):
                y, z = radius * math.cos(th), radius * math.sin(th)
                x = (-length / 2 + slant * y) + length * u
                row.append(len(verts))
                verts.append((x, y, z))
        outer.append(o_row)
        inner.append(i_row)
    faces = []
    for i in range(rings - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append([outer[i][j], outer[i][j2], outer[i + 1][j2], outer[i + 1][j]])
            faces.append([inner[i][j], inner[i + 1][j], inner[i + 1][j2], inner[i][j2]])
    last = rings - 1
    for j in range(sides):
        j2 = (j + 1) % sides
        faces.append([outer[0][j], inner[0][j], inner[0][j2], outer[0][j2]])
        faces.append([outer[last][j], outer[last][j2], inner[last][j2], inner[last][j]])
    geo = Geo(verts, faces).rotate(7, "Y").move(0, 0, r_out * 1.09 - 0.9)
    a.add("Pasta", clip_below(geo))
    return a


def pasta_farfalle():
    """Bow-tie pasta with fluted ends, one wing dug into the sand."""
    a = Asset("PastaRock_Farfalle")
    length, width = 15.0, 10.0

    def fn(u, v):
        e = abs(2 * u - 1)
        half = width * 0.5 * (0.32 + 0.68 * e ** 0.8)
        s = (v - 0.5) * 2.0
        x = (u - 0.5) * length
        if e > 0.99:  # fluted (zig-zag) ends
            x += math.copysign(0.7, u - 0.5) * math.cos(math.pi * v * 10)
        z = 1.3 * math.sin(math.pi * s * 1.5) * (1 - e) ** 2 + 1.1 * e ** 2
        return (x, s * half, z)

    geo = thick_grid(fn, 18, 10, 1.1).rotate(32, "X").rotate(8, "Y")
    geo.move(0, 0, -min(v.z for v in geo.verts) - 1.0)
    a.add("Spinach", clip_below(geo), smooth=True)
    return a


def pasta_conchiglie():
    """Ridged shell pasta, opening turned up and towards the front."""
    a = Asset("PastaRock_Conchiglie")
    length, radius = 13.0, 4.4

    def fn(u, v):
        opening = 1.0 + 1.3 * math.sin(math.pi * u)            # widest slit in the middle
        th = math.pi / 2 + opening / 2 + v * (TAU - opening)
        r = radius * max(math.sin(math.pi * u) ** 0.6, 0.18)
        r *= 1.0 + 0.07 * math.cos(TAU * 6 * u)                # ridges
        lip = min(v, 1 - v)
        r *= 1.0 - 0.22 * max(0.0, 0.18 - lip) / 0.18           # lips curl in
        return ((u - 0.5) * length, r * math.cos(th), r * math.sin(th))

    geo = thick_grid(fn, 24, 14, 1.0).rotate(40, "X").rotate(-6, "Y")
    geo.move(0, 0, -min(v.z for v in geo.verts) - 0.8)
    a.add("PastaDark", clip_below(geo), smooth=True)
    return a


def pizza_parasol():
    a = Asset("PizzaParasol")
    radius, z_rim, dome = 8.5, 10.4, 2.3
    a.add("Cream", cylinder(0.42, z_rim + dome - 0.2, 10), smooth=True)
    a.add("Cream", blob(1.4, 0.6, seed=3, wobble=0.0))

    def cone_z(r):
        return z_rim + dome * (1.0 - (r / radius) ** 1.4)

    top = [(radius * (1 - i / 6), cone_z(radius * (1 - i / 6))) for i in range(7)]
    a.add("Cheese", lathe(top, 24), smooth=True)
    under = [(radius * i / 5, z_rim - 0.25 + dome * 0.55 * (1 - i / 5)) for i in range(6)]
    a.add("Breadstick", lathe(under, 24), smooth=True)
    a.add("Breadstick", revolve(circle_section(radius, z_rim - 0.05, 0.8), 24), smooth=True)

    def slope_normal(r, ang):
        d = dome * 1.4 * (r / radius) ** 0.4 / radius
        return Vector((d * math.cos(ang), d * math.sin(ang), 1.0))

    for k, (r, ang) in enumerate([(3.2, 0.3), (5.8, 1.1), (3.9, 2.2), (6.4, 2.9),
                                  (4.2, 3.9), (6.0, 4.7), (3.4, 5.5), (1.2, 4.0)]):
        n = slope_normal(r, ang)
        disk = cylinder(1.15, 0.28, 12).transform(surface_frame(n))
        disk.move(r * math.cos(ang), r * math.sin(ang), cone_z(r) - 0.08)
        a.add("SauceDeep", disk, smooth=True)
    for k, (r, ang) in enumerate([(5.0, 0.7), (4.8, 3.4), (2.3, 1.9)]):
        n = slope_normal(r, ang)
        lf = leaf(2.6, 1.5, 0.18).move(-1.3, 0, 0).rotate(math.degrees(ang) + 60 * k, "Z")
        lf.transform(surface_frame(n)).move(r * math.cos(ang), r * math.sin(ang), cone_z(r) + 0.05)
        a.add("Basil", lf)
    return a


def beach_lounger():
    """Breadstick frame, a wavy lasagna sheet as the sling, a raviolo pillow.
    Foot at -Y, backrest at +Y."""
    a = Asset("BeachLounger")
    half_w = 2.0

    def rail_point(t):  # side profile of the chair, t: 0 foot .. 1 head
        if t < 0.62:
            f = t / 0.62
            return Vector((0.0, -4.4 + 6.4 * f, 1.25 + 0.25 * f))
        f = (t - 0.62) / 0.38
        return Vector((0.0, 2.0 + 1.6 * f, 1.5 + 3.4 * f))

    rail = [rail_point(i / 14) for i in range(15)]
    for side in (-1, 1):
        a.add("Breadstick", sweep([p + Vector((side * half_w, 0, 0)) for p in rail], 0.28, sides=6),
              smooth=True)
        for y0, y1 in ((-4.0, -4.1), (1.1, 1.0), (3.4, 4.2)):
            z_top = 1.3 if y0 < 3 else 4.2
            a.add("Breadstick", sweep([(side * half_w, y1, 0.0), (side * half_w, y0, z_top)], 0.24,
                                      sides=6, start="flat"), smooth=True)
    for t in (0.0, 1.0):
        p = rail_point(t)
        a.add("Breadstick", sweep([(-half_w, p.y, p.z), (half_w, p.y, p.z)], 0.26, sides=6), smooth=True)

    def sling(u, v):
        p = rail_point(0.03 + 0.94 * u)
        x = (v - 0.5) * 2 * (half_w - 0.35)
        edge = abs(2 * v - 1)
        ruffle = 0.22 * math.sin(u * 34) * max(0.0, edge - 0.7) / 0.3
        return (x, p.y, p.z + 0.05 - 0.18 * (1 - edge ** 2) + ruffle)

    a.add("Pasta", thick_grid(sling, 20, 6, 0.25))
    pillow = ico(1.0, 2, squash=0.45).scale(1.5, 0.9, 1.0).rotate(-60, "X").move(0, 3.4, 4.9)
    a.add("PastaDark", pillow, smooth=True)
    return a


def meatball_rock(label, radius, seed):
    a = Asset(f"MeatballRock_{label}")
    ball = ico(radius, 3 if radius > 5 else 2, lumps=0.09, seed=seed, squash=0.92)
    a.add("Meatball", clip_below(ball.move(0, 0, radius * 0.72)), smooth=True)
    a.add("Tomato", blob(radius * 1.45, max(0.35, radius * 0.06), seed=seed), smooth=True)
    top = radius * 0.72 + radius * 0.92
    lf = leaf(radius * 0.8, radius * 0.45, 0.2).rotate(-25, "Y").rotate(30, "Z")
    a.add("Basil", lf.move(-radius * 0.15, 0, top - radius * 0.12))
    rng = random.Random(seed)
    for k in range(6):
        ang = rng.uniform(0, TAU)
        elev = rng.uniform(0.35, 1.2)
        d = Vector((math.cos(ang) * math.cos(elev), math.sin(ang) * math.cos(elev), math.sin(elev)))
        p = Vector((0, 0, radius * 0.72)) + Vector((d.x * radius, d.y * radius, d.z * radius * 0.92))
        flake = box(radius * 0.12, radius * 0.09, radius * 0.06).transform(surface_frame(d)).move(*p)
        a.add("Parmesan", flake)
    return a


# ---------------------------------------------------------------- ASSETS: BORDERS

CLIFF_W, CLIFF_D, CLIFF_H = 40.0, 24.0, 38.0


def cliff_top(x):
    k = TAU / CLIFF_W
    return CLIFF_H + 3.5 * math.sin(k * x + 0.7) + 2.0 * math.sin(2 * k * x + 2.1) + 1.2 * math.sin(3 * k * x + 4.0)


def cliff_front(x, z):
    """Outward bulge of the front face; periodic in x so segments tile."""
    k = TAU / CLIFF_W
    d = 1.6 * math.sin(2 * k * x + 0.4) * math.cos(z * 0.21) + 1.0 * math.sin(3 * k * x + z * 0.3)
    for px, pz, pr in ((-9.0, 14.0, 3.2), (6.0, 26.0, 2.6), (12.5, 9.0, 2.2), (-2.0, 31.0, 1.8)):
        d -= 1.6 * math.exp(-(((x - px) ** 2 + (z - pz) ** 2) / (pr * pr)))  # crumbly pits
    return d + 1.0 * periodic_hash(x, z, CLIFF_W, CLIFF_W / 2)


def parmesan_cliff():
    """Modular border block: exactly 40 wide in X, flat end faces, and every
    displacement repeats every 40 studs, so segments butt together seamlessly.
    Front (craggy face) = -Y."""
    a = Asset("ParmesanCliff")
    y0, y1 = -CLIFF_D / 2, CLIFF_D / 2
    nx, ny, nz = 10, 4, 7

    def warp(p, idx):
        x, y, zf = p.x, p.y, p.z
        z = zf * cliff_top(x)
        if idx[1] == 0:
            y -= cliff_front(x, z)
        if idx[2] == nz:
            z += 0.8 * periodic_hash(x, y, CLIFF_W, CLIFF_W / 2)
            if idx[1] == 0:
                z -= 1.8
                y += 1.2
        return (x, y + z * 0.07, z)

    a.add("Parmesan", lattice_box(-CLIFF_W / 2, CLIFF_W / 2, y0, y1, 0.0, 1.0, nx, ny, nz, warp))

    def rind_warp(p, idx):
        x, y = p.x, p.y
        base = cliff_top(x) - 1.6
        z = base + p.z * 3.6 + (0.5 * math.sin(TAU * 3 * x / CLIFF_W + y) if idx[2] == 1 else 0.0)
        if idx[1] == 0:
            y = y0 - cliff_front(x, cliff_top(x)) - 0.4
        return (x, y + z * 0.07, z)

    a.add("Rind", lattice_box(-CLIFF_W / 2, CLIFF_W / 2, y0 - 1.0, y1, 0.0, 1.0, nx, 3, 1, rind_warp))
    for k, (x, r) in enumerate(((-9.0, 2.0), (4.0, 1.6), (12.0, 2.4))):
        chunk = ico(r, 1, lumps=0.2, seed=40 + k).scale(1.2, 1.0, 0.8)
        a.add("Parmesan", chunk.move(x, y0 - cliff_front(x, 0) - r * 0.6, r * 0.5))
    return a


def parmesan_corner():
    """Chunky block that closes the corners and caps the cliff ends by the sea."""
    a = Asset("ParmesanCliff_Corner")
    size, height = 44.0, 46.0
    off = Vector((11.3, 4.2, 7.7))

    def body_warp(p, idx):
        zf = p.z
        shrink = 1.0 - 0.12 * zf
        x, y = p.x * shrink, p.y * shrink
        d = Vector((x, y, 0.0))
        radial = d.normalized() if d.length > 1e-6 else Vector((0, 0, 0))
        n = noise.noise(Vector((x, y, zf * height)) * 0.09 + off)
        corner = (abs(p.x) / (size / 2)) * (abs(p.y) / (size / 2))
        push = 2.4 * n - 3.5 * corner                   # knock the vertical edges off
        return (x + radial.x * push, y + radial.y * push, zf * height + (1.2 * n if idx[2] == 10 else 0.0))

    a.add("Parmesan", lattice_box(-size / 2, size / 2, -size / 2, size / 2, 0.0, 1.0, 10, 10, 10, body_warp))

    def rind_warp(p, idx):
        x, y = p.x * 0.88, p.y * 0.88
        corner = (abs(p.x) / (size / 2)) * (abs(p.y) / (size / 2))
        k = 1.0 - 0.08 * corner
        z = height - 1.8 + p.z * 3.4 + 0.6 * noise.noise(Vector((x, y, 0.0)) * 0.2 + off)
        return (x * k, y * k, z)

    a.add("Rind", lattice_box(-size / 2 - 1, size / 2 + 1, -size / 2 - 1, size / 2 + 1, 0.0, 1.0,
                              8, 8, 1, rind_warp))
    return a


WAVE_W = 40.0


def wave_section():
    """Breaking-wave cross-section in (y, z), front curl towards -Y."""
    return [(-10.0, 0.0), (22.0, 0.0), (22.0, 1.2), (15.0, 2.4), (9.0, 5.5), (4.0, 10.5),
            (0.5, 15.0), (-3.0, 17.2), (-7.0, 17.4), (-10.5, 16.0), (-12.0, 13.8), (-11.6, 12.0),
            (-10.0, 12.2), (-8.2, 13.2), (-6.4, 12.8), (-5.4, 11.0), (-5.6, 8.0), (-6.6, 5.0),
            (-8.2, 2.4), (-9.6, 0.8)]


def wave_vary(x):
    """Per-x crest height and sway, periodic so segments tile."""
    k = TAU / WAVE_W
    return (1.0 + 0.10 * math.sin(k * x + 0.6) + 0.14 * math.sin(2 * k * x + 2.3),
            1.2 * math.sin(2 * k * x + 1.9))


def sauce_wave():
    """Modular tomato-sauce wave with a strip of sea behind it. Exactly 40 wide in
    X with matching ends. Front (curl) = -Y."""
    a = Asset("SauceWave")
    k = TAU / WAVE_W

    def wave_point(y, z, x):
        zs, sway = wave_vary(x)
        return (y + sway * min(1.0, z / 6.0), z * zs)

    def body(x):
        return [wave_point(y, z, x) for y, z in wave_section()]

    def foam(y, z, radius, n):
        def section(x):
            cy, cz = wave_point(y, z, x)
            return circle_section(cy, cz, radius(x), n)
        return section

    a.add("Tomato", x_extrude(body, -WAVE_W / 2, WAVE_W / 2, 24), smooth=True)
    # Creamy foam on the crest, on the lip and where the wave meets the sand.
    a.add("Cream", x_extrude(foam(-6.5, 17.6, lambda x: 1.2 * (1 + 0.25 * math.sin(3 * k * x)), 8),
                             -WAVE_W / 2, WAVE_W / 2, 16), smooth=True)
    for i in range(12):  # bubbly foam along the crest, kept off the module ends
        x = -17.0 + 34.0 * i / 11
        cy, cz = wave_point(-6.8 + 1.2 * math.sin(i * 2.1), 17.9, x)
        a.add("Cream", ico(1.5 + 0.5 * math.sin(i * 1.7), 1).move(x, cy, cz), smooth=True)
    a.add("Cream", x_extrude(foam(-11.4, 13.0, lambda x: 1.0 * (1 + 0.2 * math.sin(4 * k * x)), 6),
                             -WAVE_W / 2, WAVE_W / 2, 16), smooth=True)
    a.add("Cream", x_extrude(foam(-10.2, 0.3, lambda x: 0.9 * (1 + 0.3 * math.sin(5 * k * x)), 6),
                             -WAVE_W / 2, WAVE_W / 2, 16), smooth=True)

    def sea_warp(p, idx):
        z = p.z * (0.95 + 0.35 * math.sin(2 * k * p.x + 0.3 * p.y)) if idx[2] == 1 else 0.0
        return (p.x, p.y, z)

    a.add("SauceDeep", lattice_box(-WAVE_W / 2, WAVE_W / 2, 18.0, 62.0, 0.0, 1.0, 10, 6, 1, sea_warp))
    rng = random.Random(77)
    for _ in range(9):
        r = rng.uniform(0.6, 1.4)
        a.add("Cream", sphere(r, 8, 4).move(rng.uniform(-16, 16), rng.uniform(24, 58), 0.9), smooth=True)
    return a


# ---------------------------------------------------------------- ASSETS: LANDMARKS


def pepper_mill_lighthouse():
    """Giant pepper mill turned lighthouse: wooden body with tomato stripes,
    chrome rings and gallery, a lantern (make it Neon in Studio), crank on top."""
    a = Asset("PepperMillLighthouse")
    body = [(0.0, 0.0), (9.6, 0.0), (9.6, 1.6), (8.8, 3.0), (7.6, 6.0), (6.8, 11.0), (6.9, 16.0),
            (7.5, 22.0), (7.3, 28.0), (6.4, 34.0), (5.6, 39.0), (5.3, 42.5), (0.0, 42.5)]
    outer = body[1:-1]
    a.add("Wood", lathe(body, 20), smooth=True)

    def band(z0, z1, out):
        zm = (z0 + z1) / 2
        r = [interp_profile(outer[1:], z) for z in (z0, zm, z1)]
        return revolve([(r[0] - 0.4, z0), (r[0] + out, z0), (r[1] + out, zm), (r[2] + out, z1),
                        (r[2] - 0.4, z1), (r[1] - 0.4, zm)], 20)

    a.add("Tomato", band(13.0, 17.0, 0.22), smooth=True)
    a.add("Tomato", band(24.0, 28.0, 0.22), smooth=True)
    a.add("Silver", band(3.2, 4.3, 0.45), smooth=True)
    a.add("Silver", band(33.6, 34.8, 0.45), smooth=True)
    a.add("Silver", revolve(rect_section(4.0, 8.8, 42.5, 43.7), 20))
    a.add("Silver", revolve(rect_section(8.2, 8.7, 43.7, 45.8), 20))
    a.add("Light", lathe([(0.0, 43.7), (4.4, 43.7), (4.4, 50.5), (0.0, 50.5)], 16), smooth=True)
    for k in range(6):
        ang = TAU * k / 6 + 0.26
        a.add("Silver", box(0.55, 0.55, 6.8).move(4.5 * math.cos(ang), 4.5 * math.sin(ang), 47.1))
    head = [(0.0, 50.2), (5.6, 50.2), (5.9, 51.2), (5.6, 53.5), (4.6, 56.5), (3.0, 58.5), (0.0, 59.2)]
    a.add("Wood", lathe(head, 20), smooth=True)
    crank = [(0.0, 58.8), (1.3, 58.8), (1.3, 60.8), (2.0, 61.3), (2.0, 62.4), (1.2, 63.2), (0.0, 63.4)]
    a.add("Silver", lathe(crank, 12), smooth=True)

    # Door and portholes on the body, following its slope.
    arch = [(-2.1, 0.0), (2.1, 0.0), (2.1, 4.0)] + [
        (2.1 * math.cos(math.pi * i / 6), 4.0 + 2.1 * math.sin(math.pi * i / 6)) for i in range(1, 6)
    ] + [(-2.1, 4.0)]
    z0, z1 = 3.3, 9.4
    r0, r1 = interp_profile(outer[1:], z0), interp_profile(outer[1:], z1)
    tilt = math.degrees(math.atan2(r0 - r1, z1 - z0))
    door = prism(arch, 0.9).rotate(90, "X").rotate(-tilt, "X")
    a.add("Dark", door.move(0.0, -(r0 + r1) / 2 - 0.05, z0))
    for z, ang in ((20.0, -90.0), (30.5, 0.0), (30.5, 180.0)):
        r = interp_profile(outer[1:], z)
        rad = math.radians(ang)
        port = cylinder(1.2, 0.7, 12).align((math.cos(rad), math.sin(rad), 0.0))
        a.add("Dark", port.move((r - 0.3) * math.cos(rad), (r - 0.3) * math.sin(rad), z))
    return a


def olive_oil_bottle():
    """Giant bottle planted at an angle in a sand mound, with a spill of oil."""
    tilt, sink, k = 17.0, 4.5, 1.3
    ax = math.tan(math.radians(tilt)) * sink
    a = Asset("OliveOilBottle", anchor=(ax, 0.0))

    def plant(geo):
        geo.scale(k).rotate(tilt, "Y").move(0, 0, -sink)
        return clip_below(geo)

    glass = [(0.0, 0.0), (5.0, 0.0), (5.4, 0.8), (5.4, 15.5), (5.0, 17.5), (3.4, 20.0),
             (2.0, 22.0), (1.8, 26.0), (2.3, 26.3), (2.3, 27.4), (1.5, 27.6), (0.0, 27.6)]
    a.add("Glass", plant(lathe(glass, 20)), smooth=True)
    cork = [(0.0, 27.0), (1.55, 27.0), (1.65, 30.2), (1.4, 31.0), (0.0, 31.2)]
    a.add("Cork", plant(lathe(cork, 12)), smooth=True)
    a.add("Cream", plant(revolve(rect_section(5.25, 5.7, 6.0, 12.5), 20)), smooth=True)
    a.add("Gold", plant(revolve(rect_section(1.7, 2.1, 24.6, 25.6), 12)), smooth=True)
    a.add("Sand", blob(8.5, 1.6, seed=21).move(ax, 0, 0), smooth=True)
    a.add("Oil", blob(9.0, 0.25, seed=22).move(ax + 6.0, -3.0, 0), smooth=True)
    return a


def gelateria_hut():
    """Small beach kiosk: cream walls, striped awning, counter, giant cone on the
    roof. No text, no logo. Front = -Y."""
    a = Asset("GelateriaHut")
    a.add("Waffle", box(19.0, 15.0, 0.8, 0.25).move(0, 0, 0.4))
    a.add("Cream", box(16.0, 12.0, 10.0, 0.5).move(0, 0, 5.8))
    a.add("Dark", box(10.0, 0.5, 4.6, 0.15).move(0, -6.0, 7.4))
    a.add("Pistachio", box(12.0, 2.6, 0.7, 0.2).move(0, -7.0, 5.0))
    a.add("Pistachio", box(17.6, 13.6, 1.4, 0.5).move(0, 0, 11.5))

    stripes = 7
    width = 16.0 / stripes
    y_back, z_back, y_front, z_front = -6.1, 10.4, -10.3, 8.4
    slope = math.degrees(math.atan2(z_back - z_front, y_back - y_front))
    run = math.hypot(z_back - z_front, y_back - y_front) + 0.3
    for i in range(stripes):
        xc = -8.0 + width * (i + 0.5)
        color = "Tomato" if i % 2 == 0 else "Cream"
        slab = box(width, run, 0.35).rotate(slope, "X").move(xc, (y_back + y_front) / 2, (z_back + z_front) / 2)
        a.add(color, slab)
        scallop = cylinder(width * 0.48, 0.3, 12).rotate(90, "X").move(xc, y_front + 0.15, z_front)
        a.add(color, scallop)

    a.add("Waffle", lathe([(0.0, 12.2), (3.3, 19.6), (3.6, 20.0), (0.0, 20.0)], 12))
    a.add("Strawberry", ico(3.6, 2, squash=0.85).move(0, 0, 21.9), smooth=True)
    a.add("Strawberry", revolve(circle_section(3.3, 20.5, 0.7), 16), smooth=True)
    a.add("Pistachio", ico(3.0, 2, squash=0.85).move(0, 0, 25.6), smooth=True)
    a.add("Pistachio", revolve(circle_section(2.8, 24.4, 0.6), 16), smooth=True)
    a.add("Tomato", sphere(1.0, 10, 6).move(0, 0, 28.8), smooth=True)
    for x in (-3.2, 3.2):
        a.add("Waffle", cylinder(0.3, 2.6, 8).move(x, -9.6, 0.0))
        a.add("Strawberry", cylinder(1.0, 0.45, 12).move(x, -9.6, 2.6), smooth=True)
    return a


def star_pedestal():
    """Pedestal for the Star: a decorated plate, exactly 30 studs across."""
    a = Asset("StarPedestal")
    plate = [(0.0, 0.0), (12.4, 0.0), (12.8, 0.4), (12.6, 1.1), (9.4, 1.4), (8.6, 1.8), (8.6, 3.0),
             (9.2, 3.3), (14.2, 4.4), (14.6, 4.95), (14.3, 5.3), (12.2, 5.1), (11.2, 4.7), (0.0, 4.7)]
    a.add("Porcelain", lathe(plate, 40), smooth=True)
    a.add("Gold", revolve(circle_section(14.63, 5.05, 0.37, 8), 40), smooth=True)
    a.add("Majolica", revolve(rect_section(9.4, 10.8, 4.62, 4.84), 40))
    a.add("Majolica", revolve(rect_section(8.45, 8.85, 2.05, 2.75), 40))
    for k in range(12):
        ang = TAU * k / 12
        a.add("Majolica", sphere(0.55, 8, 4).scale(1, 1, 0.6).move(11.0 * math.cos(ang), 11.0 * math.sin(ang), 1.3),
              smooth=True)
    return a


def teleporter_arch():
    """Elbow-macaroni arch over a raviolo pad of exactly 16 studs across.
    The arch stands in the XZ plane; walk through it along Y."""
    a = Asset("TeleporterArch")
    span, leg, tube = 11.0, 7.0, 2.4
    path = [(-span, 0.0, leg * t) for t in (0.0, 0.5)]
    path += [(-span * math.cos(math.pi * i / 16), 0.0, leg + span * math.sin(math.pi * i / 16)) for i in range(17)]
    path += [(span, 0.0, leg * t) for t in (0.5, 0.0)]
    a.add("Pasta", sweep(path, tube, sides=16, ridge=0.06, start="flat", end="flat",
                         up_hint=(0.0, 1.0, 0.0)), smooth=True)
    for x in (-span, span):
        a.add("Parmesan", box(6.0, 6.0, 1.8, 0.4).move(x, 0, 0.9))
    apex = leg + span + tube
    a.add("Tomato", ico(1.6, 2).move(0, 0, apex + 1.1), smooth=True)
    for ang in (35, 145):
        a.add("Basil", leaf(3.4, 1.9, 0.2).rotate(-ang, "Y").move(0, 0, apex + 1.5))

    def crimp(ang):
        return 7.6 + 0.4 * math.cos(16 * ang)

    a.add("PastaDark", radial_solid(crimp, [(1.0, 0.0), (1.0, 0.45), (0.94, 0.7)], 64))
    a.add("Glow", radial_solid(lambda ang: 5.2, [(1.0, 0.55), (0.96, 0.95), (0.6, 1.2), (0.2, 1.28)], 32),
          smooth=True)
    return a


def boss_arena_rim():
    """Rim of a giant 180-stud plate: a raised ring with 4 openings (on +-X and
    +-Y), a porcelain floor, majolica band, gold edge, tomato bollards."""
    a = Asset("BossArenaRim")
    rim = [(76.0, 0.0), (86.5, 0.0), (88.6, 2.6), (89.7, 5.2), (89.9, 6.3), (89.4, 7.0),
           (86.0, 7.0), (82.5, 5.6), (79.0, 2.9), (76.6, 0.8)]
    gap = math.asin(9.0 / 83.0)  # 18-stud openings
    for q in range(4):
        a0 = q * math.pi / 2 + gap
        a1 = (q + 1) * math.pi / 2 - gap
        a.add("Porcelain", revolve(rim, 22, a0, a1), smooth=True)
        a.add("Majolica", revolve(rect_section(86.4, 89.0, 6.9, 7.25), 22, a0, a1))
        a.add("Gold", revolve(circle_section(89.95, 6.4, 0.45, 6), 22, a0, a1), smooth=True)
    a.add("Porcelain", lathe([(0.0, 0.0), (77.0, 0.0), (77.0, 0.3), (0.0, 0.3)], 64))
    for q in range(4):
        for side in (-1, 1):
            ang = q * math.pi / 2 + side * (gap + 2.4 / 87.5)
            x, y = 87.5 * math.cos(ang), 87.5 * math.sin(ang)
            a.add("Tomato", ico(2.6, 2).move(x, y, 9.0), smooth=True)
            a.add("Basil", leaf(2.4, 1.4, 0.2).rotate(-30, "Y").rotate(math.degrees(ang), "Z").move(x, y, 11.3))
    return a


VOLCANO_PROFILE = [(105.0, 0.0), (99.0, 5.0), (90.0, 13.0), (78.0, 26.0), (66.0, 42.0), (55.0, 62.0),
                   (46.0, 84.0), (38.0, 106.0), (32.0, 126.0), (29.5, 139.0), (28.5, 146.0)]


def volcano_ridge(a, z):
    """Twirled-spaghetti grooves spiralling around the cone."""
    amp = 0.05 * min(1.0, z / 10.0) * max(0.0, min(1.0, (144.0 - z) / 8.0))
    return 1.0 + amp * math.sin(9 * a + z * 0.07)


def volcano_surface(a, z, lift=0.0):
    r = interp_profile(VOLCANO_PROFILE, z) * volcano_ridge(a, z) + lift
    return Vector((r * math.cos(a), r * math.sin(a), z))


def spaghetti_volcano():
    """~150-stud monument: a twirled mound of spaghetti, a crater of sauce, sauce
    flows (the main one faces -Y, towards the boss arena), meatball boulders,
    grated parmesan snow, a basil garnish."""
    a = Asset("SpaghettiVolcano", anchor=(0.0, 0.0))
    dense = []
    for (r0, z0), (r1, z1) in zip(VOLCANO_PROFILE, VOLCANO_PROFILE[1:]):
        steps = max(1, int(round((z1 - z0) / 6.0)))
        dense += [(r0 + (r1 - r0) * i / steps, z0 + (z1 - z0) * i / steps) for i in range(steps)]
    dense.append(VOLCANO_PROFILE[-1])
    crater = [(26.5, 149.5), (23.5, 149.0), (20.0, 144.5), (15.0, 139.0), (0.0, 138.5)]
    profile = [(0.0, 0.0)] + dense + crater
    a.add("Pasta", lathe(profile, 72, radial=lambda ang, z, r: r * volcano_ridge(ang, z) if r > 27 else r),
          smooth=True)

    rng = random.Random(151)
    for k in range(16):
        a0 = TAU * k / 16 + rng.uniform(-0.1, 0.1)
        drop = rng.uniform(45.0, 95.0)
        path = [volcano_surface(a0, 146.0, -6.0) + UP * 1.0, volcano_surface(a0, 149.0, -1.5) + UP * 2.4]
        for i in range(1, 23):
            t = i / 22
            z = 147.0 - drop * t
            ang = a0 + 0.1 * math.sin(t * 5 + k)
            path.append(volcano_surface(ang, z, 1.9))
        a.add("Pasta", sweep(path, 1.7, sides=6), smooth=True)

    def flow(a_mid, z_end, w0, w1, meander):
        def fn(u, v):
            z = 147.5 - (147.5 - z_end) * u
            s = (v - 0.5) * 2.0
            r = interp_profile(VOLCANO_PROFILE, z)
            ang = a_mid + meander * math.sin(u * 4.0) + s * (w0 + (w1 - w0) * u) * 0.5 / r
            return volcano_surface(ang, z, 0.9 + 1.1 * (1.0 - s * s))
        return thick_grid(fn, 40, 6, 0.8)

    a.add("Tomato", flow(-math.pi / 2, 1.0, 6.0, 18.0, 0.1), smooth=True)
    a.add("Tomato", flow(-2.6, 60.0, 4.0, 9.0, 0.06), smooth=True)
    a.add("Tomato", blob(17.0, 0.7, seed=5).move(0.0, -104.0, 0.0), smooth=True)
    a.add("Tomato", radial_solid(lambda ang: 21.0 * (1 + 0.04 * math.sin(7 * ang)),
                                 [(1.0, 141.0), (0.96, 144.2), (0.5, 145.0)], 36), smooth=True)

    for k, (ang, z, r) in enumerate(((-1.05, 20.0, 7.0), (-2.0, 9.0, 9.0), (3.5, 45.0, 6.0),
                                     (0.6, 30.0, 7.5), (-1.4, 3.0, 8.0))):
        p = volcano_surface(ang, z, r * 0.45)
        a.add("Meatball", ico(r, 2, lumps=0.1, seed=60 + k).move(*p), smooth=True)
    a.add("Meatball", ico(8.0, 2, lumps=0.1, seed=70).move(4.0, 2.0, 146.0), smooth=True)

    def snow(u, v):
        ang = TAU * u
        z_low = 126.0 + 6.0 * math.sin(5 * ang) + 4.0 * math.sin(11 * ang + 1.0)
        z = z_low + (145.5 - z_low) * v
        return volcano_surface(ang, z, 0.6)

    a.add("Parmesan", thick_grid(snow, 72, 4, 0.5, closed_u=True), smooth=True)

    for k, (ang, tilt) in enumerate(((1.9, 32.0), (1.5, 22.0), (2.3, 27.0))):
        base = volcano_surface(ang, 147.0, -1.0)
        lf = leaf(16.0, 8.0, 0.7, fold=0.12, bend=0.12).rotate(-tilt, "Y").rotate(math.degrees(ang), "Z")
        a.add("Basil", lf.move(*base))
    return a


# ---------------------------------------------------------------- CATALOGUE


def build_catalogue():
    """Every asset of the kit, in row order."""
    return [
        fork_palm("Small", 26.0, seed=11),
        fork_palm("Medium", 36.0, seed=12),
        fork_palm("Large", 48.0, seed=13),
        pasta_penne(),
        pasta_farfalle(),
        pasta_conchiglie(),
        pizza_parasol(),
        beach_lounger(),
        meatball_rock("Small", 3.6, seed=31),
        meatball_rock("Large", 7.5, seed=32),
        parmesan_cliff(),
        parmesan_corner(),
        pepper_mill_lighthouse(),
        olive_oil_bottle(),
        gelateria_hut(),
        sauce_wave(),
        star_pedestal(),
        teleporter_arch(),
        boss_arena_rim(),
        spaghetti_volcano(),
    ]


# ---------------------------------------------------------------- LAYOUT PLAN

# (asset, x, y, rotation in degrees). Borders are generated in layout_borders().
# Small, low props only in the middle of the combat zone; tall ones on the sides.
LAYOUT = [
    # Entrance line (y = -340): Star pedestal, teleporter arches.
    ("StarPedestal", -200.0, -340.0, 0.0),
    ("TeleporterArch", ARCH_X[0], -340.0, 0.0),
    ("TeleporterArch", ARCH_X[1], -340.0, 0.0),
    # Beach by the sea, south of the combat zone.
    ("GelateriaHut", -95.0, -352.0, 90.0),
    ("PepperMillLighthouse", 330.0, -362.0, 0.0),
    ("PizzaParasol", -290.0, -360.0, 0.0),
    ("BeachLounger", -294.0, -362.0, 8.0),
    ("BeachLounger", -285.0, -362.0, -6.0),
    ("PizzaParasol", -60.0, -372.0, 0.0),
    ("BeachLounger", -64.0, -374.0, 4.0),
    ("PizzaParasol", 245.0, -362.0, 0.0),
    ("BeachLounger", 241.0, -364.0, -5.0),
    ("BeachLounger", 250.0, -364.0, 7.0),
    ("ForkPalm_Medium", -250.0, -300.0, 20.0),
    ("ForkPalm_Small", -130.0, -300.0, 140.0),
    ("ForkPalm_Small", 80.0, -300.0, 250.0),
    ("ForkPalm_Large", 230.0, -300.0, 70.0),
    ("ForkPalm_Large", -350.0, -300.0, 300.0),
    ("MeatballRock_Small", 205.0, -378.0, 0.0),
    ("PastaRock_Conchiglie", -160.0, -380.0, 200.0),
    # Combat zone, west side.
    ("ForkPalm_Large", -345.0, -235.0, 10.0),
    ("OliveOilBottle", -325.0, -150.0, 160.0),
    ("ForkPalm_Medium", -350.0, -70.0, 200.0),
    ("MeatballRock_Large", -305.0, 5.0, 0.0),
    ("PastaRock_Penne", -330.0, 60.0, 35.0),
    ("ForkPalm_Large", -350.0, 120.0, 90.0),
    ("PastaRock_Farfalle", -290.0, -200.0, 120.0),
    # Combat zone, east side.
    ("ForkPalm_Medium", 345.0, -230.0, 45.0),
    ("MeatballRock_Large", 300.0, -165.0, 0.0),
    ("ForkPalm_Large", 350.0, -100.0, 180.0),
    ("PizzaParasol", 312.0, -25.0, 0.0),
    ("BeachLounger", 308.0, -27.0, 90.0),
    ("ForkPalm_Small", 290.0, 60.0, 300.0),
    ("PastaRock_Conchiglie", 330.0, 105.0, 30.0),
    ("ForkPalm_Medium", 360.0, 25.0, 130.0),
    # Combat zone, middle: small, low, spread out.
    ("MeatballRock_Small", -150.0, -200.0, 0.0),
    ("PastaRock_Conchiglie", 120.0, -190.0, 70.0),
    ("PastaRock_Farfalle", -40.0, -120.0, 20.0),
    ("MeatballRock_Small", 200.0, -80.0, 0.0),
    ("PastaRock_Penne", -200.0, -40.0, 130.0),
    ("MeatballRock_Small", 60.0, -10.0, 0.0),
    ("PastaRock_Conchiglie", -110.0, 70.0, 250.0),
    ("PastaRock_Farfalle", 150.0, 100.0, 300.0),
    ("MeatballRock_Small", -10.0, 125.0, 0.0),
    # Boss arena and its surroundings.
    ("BossArenaRim", ARENA_POS[0], ARENA_POS[1], 0.0),
    ("SpaghettiVolcano", VOLCANO_POS[0], VOLCANO_POS[1], 0.0),
    ("ForkPalm_Large", -150.0, 250.0, 30.0),
    ("ForkPalm_Medium", -130.0, 335.0, 160.0),
    ("ForkPalm_Large", 150.0, 250.0, 210.0),
    ("ForkPalm_Small", 135.0, 340.0, 80.0),
    ("MeatballRock_Large", -205.0, 180.0, 0.0),
    ("PastaRock_Penne", 210.0, 170.0, 250.0),
    ("ForkPalm_Medium", -290.0, 300.0, 250.0),
    ("MeatballRock_Large", 290.0, 320.0, 0.0),
    ("PastaRock_Farfalle", -300.0, 220.0, 45.0),
    ("ForkPalm_Small", 300.0, 220.0, 15.0),
]


def layout_borders(assets):
    """Parmesan cliffs on W, N and E, sauce waves on S, corner blocks. The two
    northern segments in front of the volcano are left out: its slope closes
    the border there."""
    placements = []
    cliff = assets["ParmesanCliff"]
    back = cliff.bbox[1].y                      # local +Y = back of the block
    n = int(2 * HALF / CLIFF_W)
    for i in range(n):
        c = -HALF + CLIFF_W * (i + 0.5)
        placements.append(("ParmesanCliff", -HALF + back, c, 90.0))
        placements.append(("ParmesanCliff", HALF - back, c, -90.0))
        if abs(c) > CLIFF_W * 0.75:
            placements.append(("ParmesanCliff", c, HALF - back, 0.0))
    wave = assets["SauceWave"]
    front = wave.bbox[0].y                      # local -Y = foot of the curl
    for i in range(n):
        c = -HALF + WAVE_W * (i + 0.5)
        placements.append(("SauceWave", c, -386.0 + front, 180.0))
    corners = ((-HALF + 20, HALF - 20), (HALF - 20, HALF - 20), (-HALF + 18, -HALF + 6), (HALF - 18, -HALF + 6),
               (-CLIFF_W - 4, HALF - 12), (CLIFF_W + 4, HALF - 12))   # the last two flank the volcano
    for x, y in corners:
        placements.append(("ParmesanCliff_Corner", x, y, 0.0))
    return placements


# ---------------------------------------------------------------- SCENE


def remove_collection_tree(col):
    for child in list(col.children):
        remove_collection_tree(child)
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)


def clear_previous_run():
    """Delete only what this script created on a previous run."""
    for name in (LAYOUT_COL, ASSETS_COL):
        col = bpy.data.collections.get(name)
        if col is not None:
            remove_collection_tree(col)
    for mesh in list(bpy.data.meshes):
        if mesh.name.startswith(PREFIX) and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.name.startswith(PREFIX) and mat.users == 0:
            bpy.data.materials.remove(mat)


def new_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def place_copy(asset, collection, index, x, y, rot_deg):
    """Linked copy (mesh data shared) of an asset hierarchy."""
    src = asset.root
    root = src.copy()
    root.name = f"{src.name}_L{index:02d}"
    collection.objects.link(root)
    for child in src.children:
        c = child.copy()
        c.name = f"{child.name}_L{index:02d}"
        collection.objects.link(c)
        c.parent = root
        c.matrix_parent_inverse = Matrix.Identity(4)
    root.location = (x, y, 0.0)
    root.rotation_euler = (0.0, 0.0, math.radians(rot_deg))
    return root


def preview_plane(name, x0, y0, x1, y1, z, color, collection):
    geo = Geo([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [[0, 1, 2, 3]])
    obj = make_mesh_object(name, [(geo, False)], color, Vector(), collection)
    return obj


def preview_guides(collection):
    """Keep-out areas drawn on the ground (preview only, never exported)."""
    guides = Geo()
    w = 0.8
    for cx, cy, r in ((SPAWN[0], SPAWN[1], SPAWN_FREE_R), (STAR_POS[0], STAR_POS[1], 15.0),
                      (ARENA_POS[0], ARENA_POS[1], ARENA_R)):
        guides.add(revolve(rect_section(r - w, r, 0.05, 0.15), 64).move(cx, cy, 0.0))
    y0, y1 = COMBAT_Y
    for (xa, ya, xb, yb) in ((-HALF, y0, HALF, y0), (-HALF, y1, HALF, y1),
                             (-COMBAT_SIDE_X, y0, -COMBAT_SIDE_X, y1), (COMBAT_SIDE_X, y0, COMBAT_SIDE_X, y1),
                             (ARCH_BAND[0], -356.0, ARCH_BAND[1], -356.0), (ARCH_BAND[0], -324.0, ARCH_BAND[1], -324.0)):
        length = math.hypot(xb - xa, yb - ya)
        ang = math.degrees(math.atan2(yb - ya, xb - xa))
        guides.add(box(length, w, 0.1).rotate(ang, "Z").move((xa + xb) / 2, (ya + yb) / 2, 0.1))
    make_mesh_object("Z1_Preview_Guides", [(guides, False)], "Guide", Vector(), collection)


def widen_viewport_clip():
    screen = getattr(bpy.context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.clip_end = max(space.clip_end, 20000.0)


# ---------------------------------------------------------------- CHECKS


class Checks:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def expect(self, ok, message):
        if ok:
            self.passed += 1
        else:
            self.failed.append(message)

    def report(self):
        for message in self.failed:
            print("  FAILED:", message)
        print(f"CHECKS passed={self.passed} failed={len(self.failed)}")


def mesh_tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def check_assets(assets, checks):
    for asset in assets:
        root = asset.root
        meshes = [root] if root.type == "MESH" else [c for c in root.children if c.type == "MESH"]
        checks.expect(root.name.startswith(PREFIX), f"{root.name}: missing {PREFIX} prefix")
        checks.expect(tuple(root.rotation_euler) == (0.0, 0.0, 0.0) and tuple(root.scale) == (1.0, 1.0, 1.0),
                      f"{root.name}: transforms not applied")
        checks.expect(abs(asset.bbox[0].z) < 1e-4, f"{root.name}: base not at z = 0 ({asset.bbox[0].z:.3f})")
        for obj in meshes:
            t = mesh_tris(obj)
            checks.expect(t <= MAX_TRIS, f"{obj.name}: {t} triangles > {MAX_TRIS}")
            checks.expect(len(obj.data.materials) == 1, f"{obj.name}: {len(obj.data.materials)} materials")
            checks.expect(obj.name.startswith(PREFIX), f"{obj.name}: missing {PREFIX} prefix")


def check_layout(placements, assets, checks):
    """The plan's rules: free spawn, free Star and arch spots, clear combat zone
    middle, empty arena."""
    reserved = {"StarPedestal", "TeleporterArch", "BossArenaRim", "SpaghettiVolcano"}
    border = {"ParmesanCliff", "ParmesanCliff_Corner", "SauceWave"}
    middle = []
    for name, x, y, _ in placements:
        asset = assets[name]
        r = asset.footprint_radius()
        if name in border:
            continue
        checks.expect(math.hypot(x - SPAWN[0], y - SPAWN[1]) - r >= SPAWN_FREE_R,
                      f"{name} at ({x:.0f}, {y:.0f}) enters the spawn circle")
        if name in reserved:
            continue
        checks.expect(math.hypot(x - STAR_POS[0], y - STAR_POS[1]) - r >= 15.0 + 4.0,
                      f"{name} at ({x:.0f}, {y:.0f}) crowds the Star pedestal")
        dx = max(ARCH_BAND[0] - x, 0.0, x - ARCH_BAND[1])
        dy = max(-356.0 - y, 0.0, y + 324.0)
        checks.expect(math.hypot(dx, dy) - r >= 2.0, f"{name} at ({x:.0f}, {y:.0f}) crowds the arches")
        checks.expect(math.hypot(x - ARENA_POS[0], y - ARENA_POS[1]) - r >= ARENA_R + 2.0,
                      f"{name} at ({x:.0f}, {y:.0f}) is inside the boss arena")
        checks.expect(abs(x) <= HALF - 10 and abs(y) <= HALF - 10, f"{name} at ({x:.0f}, {y:.0f}) is off the zone")
        if COMBAT_Y[0] <= y <= COMBAT_Y[1] and abs(x) < COMBAT_SIDE_X:
            checks.expect(asset.height() <= SMALL_MAX_H,
                          f"{name} ({asset.height():.1f} high) is too tall for the middle of the combat zone")
            checks.expect(abs(x) + r <= COMBAT_SIDE_X or asset.height() <= SMALL_MAX_H,
                          f"{name} at ({x:.0f}, {y:.0f}) spills into the middle")
            middle.append((name, x, y))
    for i, (na, xa, ya) in enumerate(middle):
        for nb, xb, yb in middle[i + 1:]:
            checks.expect(math.hypot(xa - xb, ya - yb) >= MIDDLE_SPACING,
                          f"{na} and {nb} are closer than {MIDDLE_SPACING:.0f} studs")
    arena = assets["BossArenaRim"]
    checks.expect(abs(arena.bbox[1].x - arena.bbox[0].x - 2 * ARENA_R) < 0.5,
                  f"arena is {arena.bbox[1].x - arena.bbox[0].x:.2f} across, expected {2 * ARENA_R:.0f}")
    star = assets["StarPedestal"]
    checks.expect(abs(star.bbox[1].x - star.bbox[0].x - 30.0) < 0.3,
                  f"Star pedestal is {star.bbox[1].x - star.bbox[0].x:.2f} across, expected 30")
    volcano = assets["SpaghettiVolcano"]
    checks.expect(140.0 <= volcano.height() <= 170.0, f"volcano is {volcano.height():.1f} high, expected ~150")
    for name in ("ParmesanCliff", "SauceWave"):
        lo, hi = assets[name].bbox
        checks.expect(abs(hi.x - lo.x - 40.0) < 1e-3, f"{name} is {hi.x - lo.x:.3f} wide, modules must be 40")


# ---------------------------------------------------------------- EXPORT


def ensure_fbx_exporter():
    if hasattr(bpy.ops.export_scene, "fbx"):
        return True
    try:
        import addon_utils
        addon_utils.enable("io_scene_fbx", default_set=True)
    except Exception as exc:  # noqa: BLE001 - reported below
        print("FBX exporter unavailable:", exc)
    return hasattr(bpy.ops.export_scene, "fbx")


def export_asset(root, filepath):
    """Export one asset hierarchy at the world origin, Roblox settings:
    Apply Scalings = FBX Unit Scale, Forward = Z, Up = Y (Roblox Creator Docs,
    'Blender export settings'). In Studio's 3D Importer keep Scale Unit = Stud."""
    view_layer = bpy.context.view_layer
    wanted = {root, *root.children_recursive}
    for obj in view_layer.objects:
        obj.select_set(obj in wanted)
    view_layer.objects.active = root
    saved = root.location.copy()
    root.location = (0.0, 0.0, 0.0)
    view_layer.update()
    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            object_types={"EMPTY", "MESH"},
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_UNITS",
            axis_forward="Z",
            axis_up="Y",
            use_space_transform=True,
            bake_space_transform=False,
            use_mesh_modifiers=True,
            mesh_smooth_type="FACE",
            use_triangles=True,
            use_custom_props=False,
            add_leaf_bones=False,
            bake_anim=False,
            path_mode="COPY",
            embed_textures=True,
        )
    finally:
        root.location = saved
        for obj in view_layer.objects:
            obj.select_set(False)


def export_all(assets, checks):
    if not ensure_fbx_exporter():
        checks.expect(False, "FBX exporter add-on is not available")
        return
    os.makedirs(EXPORT_DIR, exist_ok=True)
    for asset in assets:
        path = os.path.join(EXPORT_DIR, asset.root.name + ".fbx")
        export_asset(asset.root, path)
        checks.expect(os.path.isfile(path) and os.path.getsize(path) > 0, f"{path} was not written")
    print(f"Exported {len(assets)} FBX files to {EXPORT_DIR}")


# ---------------------------------------------------------------- MAIN


def main():
    if bpy.context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")
    clear_previous_run()
    scene = bpy.context.scene
    # Roblox: keep every scale at 1.0 so 1 unit = 1 stud with 'FBX Unit Scale'.
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    assets_col = new_collection(ASSETS_COL)
    layout_col = new_collection(LAYOUT_COL)
    preview_col = new_collection(PREVIEW_COL, parent=layout_col)

    catalogue = build_catalogue()
    assets = {}
    cursor = ROW_X0
    print(f"{'asset':34} {'meshes':>6} {'tris':>6}  size x/y/z (studs)")
    for asset in catalogue:
        root = asset.build(assets_col)
        lo, hi = asset.bbox
        root.location = (cursor - lo.x, ROW_Y, 0.0)
        cursor += (hi.x - lo.x) + ROW_GAP
        assets[asset.name[len(PREFIX):]] = asset
        meshes = [root] if root.type == "MESH" else list(root.children)
        tris = [mesh_tris(m) for m in meshes]
        size = hi - lo
        print(f"{root.name:34} {len(meshes):>6} {max(tris):>6}  {size.x:6.1f} {size.y:6.1f} {size.z:6.1f}")

    placements = LAYOUT + layout_borders(assets)
    for index, (name, x, y, rot) in enumerate(placements, start=1):
        place_copy(assets[name], layout_col, index, x, y, rot)
    preview_plane("Z1_Preview_Sand", -HALF, -HALF, HALF, HALF, -0.02, "Sand", preview_col)
    preview_plane("Z1_Preview_SauceSea", -1200.0, -1100.0, 1200.0, -440.0, 0.8, "SauceDeep", preview_col)
    preview_guides(preview_col)
    print(f"Layout: {len(placements)} copies placed")

    checks = Checks()
    check_assets(catalogue, checks)
    check_layout(placements, assets, checks)
    if EXPORT_FBX:
        export_all(catalogue, checks)
    widen_viewport_clip()
    checks.report()


if __name__ == "__main__":
    main()
