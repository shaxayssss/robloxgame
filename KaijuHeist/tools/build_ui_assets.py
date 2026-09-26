"""
Kaiju Heist - UI asset generator (Python 3 + Pillow).

    pip install pillow
    python KaijuHeist/tools/build_ui_assets.py

Draws every 2D asset of the HUD in the glossy "simulator" style of the
reference screenshots: thick dark outline, vertical gradient, top gloss,
diagonal stripes, drop shadow, big stroked cartoon text. Everything is
procedural, so a colour, a label or a size is one edit and a re-run.

Writes PNGs (transparent background) to ../assets/ui/, plus preview_hud.png,
a mock-up of the HUD assembled from those same files.

Fonts (tools/fonts/): Luckiest Guy (Apache 2.0) for titles, Fredoka Bold
(SIL OFL) for smaller text. Both may be embedded in a game.
"""

import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "ui"))
TITLE_FONT = os.path.join(HERE, "fonts", "LuckiestGuy-Regular.ttf")
BODY_FONT = os.path.join(HERE, "fonts", "Fredoka-Bold.ttf")
MAP_PREVIEW = os.path.normpath(os.path.join(HERE, "..", "assets", "map", "preview_lobby.png"))

SS = 4                              # supersampling factor: draw 4x, downscale
OUTLINE = (27, 16, 48)
WHITE = (255, 255, 255)

# (top, bottom) of the vertical gradients.
COLORS = {
    "red": ((255, 96, 124), (214, 18, 62)),
    "blue": ((92, 200, 255), (22, 102, 230)),
    "green": ((172, 246, 72), (48, 172, 30)),
    "yellow": ((255, 234, 92), (255, 150, 20)),
    "purple": ((206, 122, 255), (116, 46, 222)),
    "pink": ((255, 134, 216), (224, 38, 150)),
    "orange": ((255, 192, 84), (240, 98, 20)),
    "cyan": ((116, 246, 240), (20, 168, 212)),
    "gray": ((224, 230, 240), (136, 146, 168)),
    "dark": ((78, 62, 124), (34, 24, 66)),
}

# Same order and colours as src/Shared/KaijuDatabase.lua.
RARITIES = [
    ("common", "COMMUN", (150, 150, 150)),
    ("rare", "RARE", (70, 140, 255)),
    ("epic", "EPIQUE", (170, 70, 255)),
    ("legendary", "LEGENDAIRE", (255, 170, 30)),
    ("mythic", "MYTHIQUE", (255, 60, 90)),
]


# ---------------------------------------------------------------- BASICS


def S(v):
    return int(round(v * SS))


def B(box):
    return [S(v) for v in box]


def lighten(c, t):
    return tuple(int(c[i] + (255 - c[i]) * t) for i in range(3))


def darken(c, t):
    return tuple(int(c[i] * (1.0 - t)) for i in range(3))


def rarity_gradient(c):
    return lighten(c, 0.35), darken(c, 0.2)


def new_layer(w, h):
    return Image.new("RGBA", (S(w), S(h)), (0, 0, 0, 0))


def finish(layer, w, h):
    return layer.resize((w, h), Image.LANCZOS)


def save(img, *parts):
    path = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)
    return path


# -- masks (all in supersampled pixels, coordinates given in output pixels)

def m_new(layer):
    return Image.new("L", layer.size, 0)


def m_rrect(layer, box, r):
    m = m_new(layer)
    ImageDraw.Draw(m).rounded_rectangle(B(box), S(r), fill=255)
    return m


def m_ellipse(layer, box):
    m = m_new(layer)
    ImageDraw.Draw(m).ellipse(B(box), fill=255)
    return m


def m_poly(layer, pts):
    m = m_new(layer)
    ImageDraw.Draw(m).polygon([(S(x), S(y)) for x, y in pts], fill=255)
    return m


def m_rect(layer, box):
    m = m_new(layer)
    ImageDraw.Draw(m).rectangle(B(box), fill=255)
    return m


def m_union(*masks):
    out = masks[0]
    for m in masks[1:]:
        out = ImageChops.lighter(out, m)
    return out


def m_inter(a, b):
    return ImageChops.multiply(a, b)


def m_sub(a, b):
    return ImageChops.subtract(a, b)


def m_lines(layer, segments, width):
    m = m_new(layer)
    d = ImageDraw.Draw(m)
    for pts in segments:
        d.line([(S(x), S(y)) for x, y in pts], fill=255, width=S(width), joint="curve")
    return m


def gradient(size, top, bottom, horizontal=False):
    n = size[0] if horizontal else size[1]
    strip = Image.new("RGBA", (n, 1) if horizontal else (1, n))
    for i in range(n):
        t = i / max(1, n - 1)
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3)) + (255,)
        strip.putpixel((i, 0) if horizontal else (0, i), c)
    return strip.resize(size)


def multi_gradient(size, stops, horizontal=True):
    """Gradient through several colours (rainbow cards)."""
    n = size[0] if horizontal else size[1]
    strip = Image.new("RGBA", (n, 1) if horizontal else (1, n))
    for i in range(n):
        t = i / max(1, n - 1) * (len(stops) - 1)
        k = min(int(t), len(stops) - 2)
        f = t - k
        c = tuple(int(stops[k][j] + (stops[k + 1][j] - stops[k][j]) * f) for j in range(3)) + (255,)
        strip.putpixel((i, 0) if horizontal else (0, i), c)
    return strip.resize(size)


def fill(layer, mask, top, bottom=None, alpha=255, image=None):
    """Paint a mask with a flat colour, a vertical gradient over the mask's
    bounding box, or a given image."""
    bbox = mask.getbbox()
    if not bbox:
        return
    src = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    if image is not None:
        src.paste(image.resize((bbox[2] - bbox[0], bbox[3] - bbox[1])), bbox[:2])
    elif bottom is None:
        src = Image.new("RGBA", layer.size, tuple(top[:3]) + (255,))
    else:
        src.paste(gradient((bbox[2] - bbox[0], bbox[3] - bbox[1]), top, bottom), bbox[:2])
    if alpha < 255:
        mask = mask.point(lambda v: v * alpha // 255)
    src.putalpha(ImageChops.multiply(src.getchannel("A"), mask))
    layer.alpha_composite(src)


def stripes(layer, mask, alpha=26, step=26, width=11):
    """Diagonal light stripes clipped to a mask (the look of the reference buttons)."""
    m = m_new(layer)
    d = ImageDraw.Draw(m)
    w, h = layer.size
    for x in range(-h, w, S(step)):
        d.line([(x, h), (x + h, 0)], fill=255, width=S(width))
    fill(layer, m_inter(m, mask), WHITE, alpha=alpha)


def gloss(layer, box, r, alpha=80, frac=0.46):
    x0, y0, x1, y1 = box
    inset = max(2.0, (y1 - y0) * 0.06)
    g = m_rrect(layer, (x0 + inset, y0 + inset * 0.6, x1 - inset, y0 + (y1 - y0) * frac), max(1, r - inset))
    fill(layer, g, WHITE, alpha=alpha)


def shift(mask, dy):
    out = Image.new("L", mask.size, 0)
    out.paste(mask, (0, S(dy)))
    return out


def sticker(layer, thick=6.0, shadow=5.0, color=OUTLINE):
    """Thick dark outline + drop shadow around everything drawn on the layer."""
    a = layer.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    grown = a
    for _ in range(max(1, int(round(S(thick) / 2.0)))):
        grown = grown.filter(ImageFilter.MaxFilter(5))
    grown = grown.filter(ImageFilter.GaussianBlur(S(0.5)))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    if shadow:
        fill(out, shift(grown, shadow), darken(color, 0.2), alpha=235)
    fill(out, grown, color)
    out.alpha_composite(layer)
    return out


# -- text

def font(path, size):
    return ImageFont.truetype(path, S(size))


def fit_font(path, text, size, max_w):
    while size > 8:
        f = font(path, size)
        box = f.getbbox(text, stroke_width=0)
        if box[2] - box[0] <= S(max_w):
            return f, size
        size -= 1
    return font(path, size), size


def text(layer, xy, body, size, top=WHITE, bottom=None, stroke=5.0, shadow=3.0,
         path=TITLE_FONT, max_w=None, anchor="mm", stroke_color=OUTLINE):
    """Cartoon text: gradient fill, thick dark stroke, drop shadow."""
    f, size = fit_font(path, body, size, max_w) if max_w else (font(path, size), size)
    pos = (S(xy[0]), S(xy[1]))
    fm, sm = m_new(layer), m_new(layer)
    ImageDraw.Draw(fm).text(pos, body, font=f, fill=255, anchor=anchor)
    ImageDraw.Draw(sm).text(pos, body, font=f, fill=255, anchor=anchor,
                            stroke_width=S(stroke), stroke_fill=255)
    if shadow:
        fill(layer, shift(sm, shadow), darken(stroke_color, 0.3))
    fill(layer, sm, stroke_color)
    fill(layer, fm, top, bottom)


# ---------------------------------------------------------------- SHAPES


def panel_shape(layer, box, r, top, bottom, thick=6.0, shadow=6.0, stripe=True, shine=True):
    """Outlined, glossy rounded rectangle: the base of buttons, tiles and panels."""
    x0, y0, x1, y1 = box
    if shadow:
        fill(layer, m_rrect(layer, (x0, y0 + shadow, x1, y1 + shadow), r), darken(OUTLINE, 0.2))
    fill(layer, m_rrect(layer, box, r), OUTLINE)
    inner = (x0 + thick, y0 + thick, x1 - thick, y1 - thick)
    ir = max(1, r - thick)
    m = m_rrect(layer, inner, ir)
    fill(layer, m, top, bottom)
    # Darker lip along the bottom edge, like a pressed plastic button.
    lip = m_sub(m, m_rrect(layer, (inner[0], inner[1], inner[2], inner[3] - (y1 - y0) * 0.08), ir))
    fill(layer, lip, darken(bottom, 0.25), alpha=200)
    if stripe:
        stripes(layer, m)
    if shine:
        gloss(layer, inner, ir)
    return inner


# ---------------------------------------------------------------- ICONS
# Each icon is drawn on a 256 x 256 canvas, then outlined with sticker().


def icon_capsule(color):
    L = new_layer(256, 256)
    body = m_ellipse(L, (62, 22, 194, 234))
    upper = m_inter(body, m_rect(L, (0, 0, 256, 128)))
    lower = m_inter(body, m_rect(L, (0, 128, 256, 256)))
    fill(L, upper, lighten(color, 0.55), lighten(color, 0.15))
    fill(L, lower, color, darken(color, 0.4))
    for i, x in enumerate((96, 128, 160)):   # little kaiju spikes on the dome
        fill(L, m_inter(body, m_poly(L, [(x - 12, 92), (x, 62 - 8 * (i == 1)), (x + 12, 92)])),
             darken(color, 0.25), alpha=150)
    fill(L, m_inter(body, m_rect(L, (0, 116, 256, 142))), (255, 226, 90), (220, 150, 20))
    fill(L, m_inter(body, m_lines(L, [[(40, 116), (216, 116)], [(40, 142), (216, 142)]], 3)), OUTLINE)
    fill(L, m_ellipse(L, (116, 118, 140, 140)), WHITE)
    fill(L, m_ellipse(L, (86, 40, 124, 84)), WHITE, alpha=170)
    fill(L, m_ellipse(L, (150, 170, 164, 184)), WHITE, alpha=120)
    return sticker(L)


def icon_ichor():
    L = new_layer(256, 256)
    drop = m_union(m_ellipse(L, (62, 96, 194, 228)), m_poly(L, [(128, 18), (68, 150), (188, 150)]))
    fill(L, drop, (180, 255, 130), (20, 160, 70))
    fill(L, m_ellipse(L, (90, 128, 166, 204)), (230, 255, 190), alpha=90)
    fill(L, m_ellipse(L, (92, 110, 118, 150)), WHITE, alpha=200)
    fill(L, m_ellipse(L, (150, 170, 164, 184)), WHITE, alpha=140)
    return sticker(L)


def hexagon(cx, cy, r, rot=0.0):
    return [(cx + r * math.cos(rot + i * math.pi / 3), cy + r * math.sin(rot + i * math.pi / 3))
            for i in range(6)]


def icon_gem():
    L = new_layer(256, 256)
    outer, inner = hexagon(128, 128, 104, math.pi / 6), hexagon(128, 128, 62, math.pi / 6)
    fill(L, m_poly(L, outer), (190, 250, 255), (40, 150, 230))
    for i in range(6):   # facets
        tri = [outer[i], outer[(i + 1) % 6], inner[(i + 1) % 6], inner[i]]
        fill(L, m_poly(L, tri), WHITE if i in (4, 5) else OUTLINE, alpha=70 if i in (4, 5) else 40)
    fill(L, m_poly(L, inner), (220, 255, 255), (90, 200, 245))
    fill(L, m_lines(L, [[outer[i], inner[i]] for i in range(6)], 3), OUTLINE, alpha=120)
    fill(L, m_poly(L, [(104, 96), (128, 82), (140, 90), (112, 110)]), WHITE, alpha=220)
    return sticker(L)


def icon_gift():
    L = new_layer(256, 256)
    red = COLORS["red"]
    fill(L, m_rrect(L, (50, 116, 206, 226), 10), red[0], red[1])
    fill(L, m_rrect(L, (38, 88, 218, 128), 10), lighten(red[0], 0.2), red[0])
    fill(L, m_rect(L, (114, 88, 142, 226)), (255, 232, 90), (240, 160, 20))
    fill(L, m_rect(L, (38, 128, 218, 136)), OUTLINE, alpha=110)
    for box in ((64, 34, 130, 96), (126, 34, 192, 96)):
        ring = m_sub(m_ellipse(L, box), m_ellipse(L, (box[0] + 16, box[1] + 16, box[2] - 16, box[3] - 16)))
        fill(L, ring, (255, 236, 100), (240, 160, 20))
    fill(L, m_ellipse(L, (110, 70, 146, 100)), (255, 214, 60))
    fill(L, m_rrect(L, (60, 136, 104, 160), 8), WHITE, alpha=60)
    return sticker(L)


def icon_basket():
    L = new_layer(256, 256)
    handle = m_inter(m_sub(m_ellipse(L, (66, 24, 190, 148)), m_ellipse(L, (86, 44, 170, 128))),
                     m_rect(L, (0, 0, 256, 104)))
    fill(L, handle, (130, 40, 70), (80, 20, 50))
    body = m_poly(L, [(44, 112), (212, 112), (190, 222), (66, 222)])
    fill(L, body, COLORS["red"][0], COLORS["red"][1])
    fill(L, m_inter(body, m_lines(L, [[(x, 118), (x + (128 - x) * 0.12, 222)] for x in (86, 128, 170)]
                                  + [[(40, 170), (216, 170)]], 5)), OUTLINE, alpha=120)
    fill(L, m_rrect(L, (32, 96, 224, 124), 10), lighten(COLORS["red"][0], 0.25), COLORS["red"][0])
    fill(L, m_rrect(L, (46, 100, 150, 108), 4), WHITE, alpha=120)
    return sticker(L)


def star(cx, cy, r_out, r_in, rot=-math.pi / 2):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def icon_star():
    L = new_layer(256, 256)
    fill(L, m_poly(L, star(128, 136, 112, 50)), (255, 240, 110), (255, 150, 20))
    fill(L, m_poly(L, star(128, 136, 66, 30)), (255, 250, 190), alpha=110)
    fill(L, m_ellipse(L, (100, 76, 124, 100)), WHITE, alpha=200)
    return sticker(L)


def icon_ticket():
    L = new_layer(256, 256)
    body = m_rrect(L, (34, 70, 222, 186), 18)
    for cx in (34, 222):
        body = m_sub(body, m_ellipse(L, (cx - 18, 110, cx + 18, 146)))
    fill(L, body, (255, 236, 96), (250, 160, 20))
    fill(L, m_lines(L, [[(160, y), (160, y + 9)] for y in range(84, 176, 16)], 4), OUTLINE, alpha=150)
    fill(L, m_poly(L, star(100, 130, 36, 16)), (255, 120, 60), (220, 40, 40))
    fill(L, m_rrect(L, (48, 80, 150, 92), 6), WHITE, alpha=130)
    return sticker(L.rotate(-16, resample=Image.BICUBIC, center=(S(128), S(128))))


def icon_rebirth():
    L = new_layer(256, 256)
    ring = m_sub(m_ellipse(L, (34, 34, 222, 222)), m_ellipse(L, (78, 78, 178, 178)))
    ring = m_sub(ring, m_poly(L, [(128, 128), (238, 20), (250, 96)]))
    fill(L, ring, (130, 240, 255), (30, 110, 230))
    fill(L, m_poly(L, [(150, 14), (238, 30), (196, 98)]), (130, 240, 255), (40, 150, 240))
    fill(L, m_ellipse(L, (98, 98, 158, 158)), (255, 110, 140), (210, 20, 70))
    fill(L, m_ellipse(L, (60, 52, 100, 80)), WHITE, alpha=150)
    return sticker(L)


def icon_book():
    L = new_layer(256, 256)
    fill(L, m_rrect(L, (70, 44, 212, 216), 10), WHITE, (210, 210, 225))
    fill(L, m_rrect(L, (46, 36, 196, 212), 12), COLORS["blue"][0], COLORS["blue"][1])
    fill(L, m_rrect(L, (46, 36, 74, 212), 10), darken(COLORS["blue"][1], 0.2))
    fill(L, m_rrect(L, (92, 70, 176, 122), 10), (255, 234, 96), (250, 160, 20))
    fill(L, m_poly(L, star(134, 96, 20, 9)), OUTLINE, alpha=160)
    fill(L, m_rrect(L, (84, 46, 186, 58), 5), WHITE, alpha=110)
    return sticker(L)


def icon_bolt():
    L = new_layer(256, 256)
    bolt = m_poly(L, [(156, 14), (58, 142), (118, 142), (92, 242), (200, 104), (138, 104), (178, 14)])
    fill(L, bolt, (255, 246, 120), (255, 150, 20))
    fill(L, m_poly(L, [(150, 30), (92, 118), (110, 118), (162, 36)]), WHITE, alpha=140)
    return sticker(L)


def icon_clover():
    L = new_layer(256, 256)
    leaves = m_union(*[m_ellipse(L, (cx - 44, cy - 44, cx + 44, cy + 44))
                       for cx, cy in ((92, 92), (164, 92), (92, 158), (164, 158))])
    fill(L, m_lines(L, [[(128, 150), (150, 232)]], 14), (60, 150, 40))
    fill(L, leaves, (150, 245, 90), (30, 150, 40))
    fill(L, m_lines(L, [[(128, 60), (128, 196)], [(60, 125), (196, 125)]], 4), OUTLINE, alpha=110)
    for cx, cy in ((80, 76), (152, 76)):
        fill(L, m_ellipse(L, (cx, cy, cx + 22, cy + 16)), WHITE, alpha=150)
    return sticker(L)


def icon_cash():
    L = new_layer(256, 256)
    for dy, dark in ((-26, 0.25), (0, 0.0)):
        bill = m_rrect(L, (30, 86 + dy, 226, 186 + dy), 12)
        fill(L, bill, darken((150, 240, 110), dark), darken((40, 160, 60), dark))
        fill(L, m_sub(m_rrect(L, (44, 98 + dy, 212, 174 + dy), 8),
                      m_rrect(L, (50, 104 + dy, 206, 168 + dy), 6)), OUTLINE, alpha=80)
    fill(L, m_ellipse(L, (100, 108, 156, 164)), (220, 255, 200))
    text(L, (128, 138), "$", 42, top=(40, 150, 60), stroke=0, shadow=0, path=BODY_FONT)
    return sticker(L)


def icon_trophy():
    L = new_layer(256, 256)
    gold = ((255, 240, 110), (230, 140, 20))
    for box in ((30, 58, 102, 130), (154, 58, 226, 130)):
        fill(L, m_sub(m_ellipse(L, box), m_ellipse(L, (box[0] + 14, box[1] + 14, box[2] - 14, box[3] - 14))),
             *gold)
    cup = m_union(m_rect(L, (66, 40, 190, 110)), m_ellipse(L, (66, 40, 190, 170)))
    fill(L, cup, *gold)
    fill(L, m_rect(L, (112, 160, 144, 196)), *gold)
    fill(L, m_rrect(L, (76, 190, 180, 226), 8), (150, 90, 60), (100, 50, 30))
    fill(L, m_poly(L, star(128, 104, 30, 13)), WHITE, alpha=200)
    fill(L, m_rrect(L, (78, 48, 110, 110), 12), WHITE, alpha=110)
    return sticker(L)


def icon_shield():
    L = new_layer(256, 256)
    sh = m_poly(L, [(128, 20), (214, 54), (206, 150), (128, 236), (50, 150), (42, 54)])
    fill(L, sh, COLORS["blue"][0], COLORS["blue"][1])
    fill(L, m_poly(L, [(128, 44), (190, 68), (184, 144), (128, 208), (72, 144), (66, 68)]),
         lighten(COLORS["blue"][0], 0.2), COLORS["blue"][0])
    fill(L, m_poly(L, star(128, 124, 44, 20)), (255, 240, 110), (250, 160, 20))
    fill(L, m_poly(L, [(72, 70), (126, 50), (126, 64), (80, 82)]), WHITE, alpha=150)
    return sticker(L)


def icon_house():
    L = new_layer(256, 256)
    fill(L, m_rect(L, (58, 116, 198, 222)), (255, 236, 200), (220, 180, 130))
    fill(L, m_poly(L, [(128, 24), (236, 124), (20, 124)]), COLORS["red"][0], COLORS["red"][1])
    fill(L, m_rrect(L, (106, 150, 150, 222), 10), (150, 90, 60), (100, 50, 30))
    fill(L, m_rrect(L, (160, 140, 186, 166), 4), (120, 220, 255))
    fill(L, m_poly(L, [(128, 40), (200, 112), (184, 112), (128, 56)]), WHITE, alpha=110)
    return sticker(L)


def icon_lock():
    L = new_layer(256, 256)
    fill(L, m_sub(m_rrect(L, (70, 26, 186, 150), 58), m_rrect(L, (94, 50, 162, 150), 34)),
         (230, 236, 246), (140, 150, 170))
    fill(L, m_rrect(L, (46, 108, 210, 232), 22), (255, 234, 96), (240, 150, 20))
    fill(L, m_union(m_ellipse(L, (112, 140, 144, 172)), m_rect(L, (120, 160, 136, 200))), OUTLINE)
    fill(L, m_rrect(L, (58, 116, 198, 136), 10), WHITE, alpha=100)
    return sticker(L)


def icon_kaiju():
    """The Kaiju Heist mascot: a grumpy green kaiju head."""
    L = new_layer(256, 256)
    for i, x in enumerate((70, 104, 138, 172)):
        fill(L, m_poly(L, [(x - 22, 70), (x + 4, 12 + 10 * (i % 2)), (x + 22, 70)]),
             (140, 250, 255), (30, 160, 220))
    head = m_union(m_rrect(L, (34, 50, 222, 204), 56), m_rrect(L, (70, 120, 238, 236), 40))
    fill(L, head, (150, 236, 90), (40, 150, 50))
    fill(L, m_rrect(L, (84, 190, 228, 224), 16), (60, 30, 50))
    for x in range(96, 220, 22):
        fill(L, m_poly(L, [(x, 190), (x + 10, 208), (x + 20, 190)]), WHITE)
    for cx in (96, 166):
        fill(L, m_ellipse(L, (cx - 26, 88, cx + 26, 140)), WHITE)
        fill(L, m_ellipse(L, (cx - 8, 104, cx + 14, 132)), OUTLINE)
        fill(L, m_ellipse(L, (cx + 2, 108, cx + 10, 116)), WHITE)
    fill(L, m_lines(L, [[(66, 78), (120, 98)], [(196, 78), (142, 98)]], 10), OUTLINE)
    fill(L, m_ellipse(L, (196, 150, 208, 162)), OUTLINE)
    fill(L, m_rrect(L, (54, 60, 130, 76), 8), WHITE, alpha=90)
    return sticker(L)


def icon_crown():
    L = new_layer(256, 256)
    crown = m_poly(L, [(30, 84), (82, 132), (128, 52), (174, 132), (226, 84), (206, 206), (50, 206)])
    fill(L, crown, (255, 240, 110), (230, 140, 20))
    fill(L, m_rrect(L, (46, 184, 210, 214), 8), (255, 214, 70), (210, 120, 10))
    for cx, col in ((84, (255, 70, 100)), (128, (80, 160, 255)), (172, (120, 230, 90))):
        fill(L, m_ellipse(L, (cx - 12, 158, cx + 12, 182)), col)
    for cx, cy in ((30, 84), (128, 52), (226, 84)):
        fill(L, m_ellipse(L, (cx - 14, cy - 14, cx + 14, cy + 14)), (255, 250, 200))
    return sticker(L)


def icon_arrow_up():
    L = new_layer(256, 256)
    fill(L, m_poly(L, [(128, 18), (226, 120), (166, 120), (166, 232), (90, 232), (90, 120), (30, 120)]),
         (180, 255, 100), (40, 160, 30))
    fill(L, m_poly(L, [(128, 38), (196, 108), (176, 108), (128, 58)]), WHITE, alpha=130)
    return sticker(L)


def icon_egg():
    L = new_layer(256, 256)
    egg = m_ellipse(L, (58, 20, 198, 236))
    fill(L, egg, (255, 250, 236), (220, 200, 170))
    for cx, cy, r in ((96, 150, 16), (160, 110, 12), (138, 190, 10), (110, 84, 9)):
        fill(L, m_ellipse(L, (cx - r, cy - r, cx + r, cy + r)), (120, 200, 90))
    fill(L, m_ellipse(L, (86, 44, 120, 90)), WHITE, alpha=200)
    return sticker(L)


def icon_symbol(kind, color):
    """Round badge with a white symbol: close, plus, check, alert."""
    L = new_layer(256, 256)
    top, bottom = COLORS[color]
    fill(L, m_ellipse(L, (20, 20, 236, 236)), top, bottom)
    fill(L, m_ellipse(L, (50, 36, 206, 120)), WHITE, alpha=70)
    if kind == "close":
        sym = m_lines(L, [[(80, 80), (176, 176)], [(176, 80), (80, 176)]], 34)
    elif kind == "plus":
        sym = m_lines(L, [[(128, 66), (128, 190)], [(66, 128), (190, 128)]], 34)
    elif kind == "check":
        sym = m_lines(L, [[(68, 130), (110, 172), (190, 84)]], 32)
    else:   # alert
        sym = m_union(m_rrect(L, (112, 52, 144, 150), 14), m_ellipse(L, (110, 164, 146, 200)))
    fill(L, m_union(sym), WHITE)
    return sticker(L, thick=7)


ICONS = {
    "ichor": icon_ichor,
    "gem": icon_gem,
    "gift": icon_gift,
    "basket": icon_basket,
    "star": icon_star,
    "ticket": icon_ticket,
    "rebirth": icon_rebirth,
    "book": icon_book,
    "bolt": icon_bolt,
    "clover": icon_clover,
    "cash": icon_cash,
    "trophy": icon_trophy,
    "shield": icon_shield,
    "house": icon_house,
    "lock": icon_lock,
    "kaiju": icon_kaiju,
    "crown": icon_crown,
    "arrow_up": icon_arrow_up,
    "egg": icon_egg,
    "close": lambda: icon_symbol("close", "red"),
    "plus": lambda: icon_symbol("plus", "green"),
    "check": lambda: icon_symbol("check", "green"),
    "alert": lambda: icon_symbol("alert", "red"),
}


def icon(name, size=256):
    """Final icon at `size` px (icons are cached at full resolution)."""
    if name not in _ICON_CACHE:
        fn = ICONS.get(name)
        if fn is None and name.startswith("capsule_"):
            color = dict((k, c) for k, _, c in RARITIES)[name[len("capsule_"):]]
            fn = lambda: icon_capsule(color)   # noqa: E731
        _ICON_CACHE[name] = fn()
    return _ICON_CACHE[name].resize((size, size), Image.LANCZOS)


_ICON_CACHE = {}


def paste_icon(layer, name, cx, cy, size):
    """Paste an icon onto a supersampled layer, centred at (cx, cy) output px."""
    img = icon(name, S(size))
    layer.alpha_composite(img, (S(cx) - img.width // 2, S(cy) - img.height // 2))


# ---------------------------------------------------------------- WIDGETS


def button(w, h, color, label=None, icon_name=None, radius=None, size=None):
    L = new_layer(w, h + 8)
    r = radius if radius is not None else h * 0.28
    top, bottom = COLORS[color]
    inner = panel_shape(L, (3, 3, w - 3, h - 3), r, top, bottom)
    x_text = w / 2.0
    if icon_name:
        isz = (inner[3] - inner[1]) * 1.05
        paste_icon(L, icon_name, inner[0] + isz * 0.55, (inner[1] + inner[3]) / 2.0, isz)
        x_text = (inner[0] + isz * 1.05 + inner[2]) / 2.0
    if label:
        max_w = (inner[2] - inner[0]) - (isz * 1.1 if icon_name else 0) - 16
        text(L, (x_text, (inner[1] + inner[3]) / 2.0 + 2), label, size or h * 0.46,
             stroke=max(3.0, h * 0.06), shadow=max(2.0, h * 0.035), max_w=max_w)
    return finish(L, w, h + 8)


def tile(label, icon_name, color, size=220, badge=False):
    L = new_layer(size, size + 8)
    top, bottom = COLORS[color]
    inner = panel_shape(L, (3, 3, size - 3, size - 3), size * 0.14, top, bottom)
    paste_icon(L, icon_name, size / 2.0, size * 0.42, size * 0.62)
    text(L, (size / 2.0, size * 0.83), label, size * 0.17, stroke=5, shadow=3,
         max_w=inner[2] - inner[0] - 10)
    if badge:
        paste_icon(L, "alert", size - 26, 26, 54)
    return finish(L, size, size + 8)


def panel(w, h, color, title=None, icon_name=None, close=True):
    """Window: dark body, coloured striped header with title and close button."""
    L = new_layer(w, h + 10)
    head = 104
    body_top, body_bottom = COLORS["dark"]
    panel_shape(L, (4, 30, w - 4, h - 4), 30, body_top, body_bottom, thick=8, shadow=8,
                stripe=False, shine=False)
    fill(L, m_rrect(L, (22, head + 30, w - 22, h - 24), 20), (18, 12, 40), alpha=110)
    top, bottom = COLORS[color]
    hb = panel_shape(L, (0, 0, w, head + 14), 28, top, bottom, thick=8, shadow=6)
    x = hb[0] + 24
    if icon_name:
        paste_icon(L, icon_name, hb[0] + 66, head * 0.52, 128)
        x = hb[0] + 136
    if title:
        text(L, (x, head * 0.58), title, 66, stroke=7, shadow=4, anchor="lm",
             max_w=w - x - (150 if close else 40))
    if close:
        cl = button(92, 84, "red", "X", size=58)
        L.alpha_composite(cl.resize((S(92), S(92))), (S(w - 118), S(14)))
    return finish(L, w, h + 10)


def card(w, h, stops, title=None):
    L = new_layer(w, h + 8)
    x0, y0, x1, y1 = 3, 3, w - 3, h - 3
    fill(L, m_rrect(L, (x0, y0 + 6, x1, y1 + 6), 22), darken(OUTLINE, 0.2))
    fill(L, m_rrect(L, (x0, y0, x1, y1), 22), OUTLINE)
    m = m_rrect(L, (x0 + 6, y0 + 6, x1 - 6, y1 - 6), 17)
    fill(L, m, (0, 0, 0), image=multi_gradient((S(w), S(h)), stops))
    stripes(L, m, alpha=30, step=34, width=14)
    gloss(L, (x0 + 6, y0 + 6, x1 - 6, y1 - 6), 17, alpha=60, frac=0.4)
    if title:
        text(L, (w * 0.62, 36), title, 38, stroke=5, shadow=3, max_w=w * 0.7)
    return finish(L, w, h + 8)


def slot(color, label=None, w=150, h=176):
    L = new_layer(w, h + 8)
    top, bottom = rarity_gradient(color)
    inner = panel_shape(L, (3, 3, w - 3, h - 3), 18, top, bottom, thick=6, shadow=6, stripe=True)
    fill(L, m_rrect(L, (inner[0] + 6, inner[1] + 6, inner[2] - 6, inner[3] - 42), 12), WHITE, alpha=45)
    fill(L, m_rrect(L, (inner[0], inner[3] - 36, inner[2], inner[3]), 10), OUTLINE, alpha=150)
    if label:
        text(L, (w / 2.0, inner[3] - 18), label, 22, stroke=3, shadow=2, path=BODY_FONT,
             max_w=inner[2] - inner[0] - 10)
    return finish(L, w, h + 8)


def level_bar(w=900, h=64):
    """Frame, plus the fill that goes inside it: the fill is 18 px smaller than
    the frame on each axis, so place it at offset (9, 9) and scale its width."""
    frame = new_layer(w, h + 8)
    panel_shape(frame, (3, 3, w - 3, h - 3), h * 0.4, (60, 50, 90), (26, 20, 48), thick=6,
                shadow=6, stripe=False, shine=False)
    fw, fh = w - 18, h - 18
    fill_layer = new_layer(fw, fh)
    m = m_rrect(fill_layer, (0, 0, fw, fh), fh * 0.45)
    fill(fill_layer, m, (255, 214, 70), (250, 130, 20))
    stripes(fill_layer, m, alpha=40, step=30, width=12)
    gloss(fill_layer, (0, 0, fw, fh), fh * 0.45, alpha=90)
    return finish(frame, w, h + 8), finish(fill_layer, fw, fh)


def logo(w=1024, h=512):
    L = new_layer(w, h)
    paste_icon(L, "kaiju", 210, 256, 320)
    for body, y, size, top, bottom in (("KAIJU", 178, 160, (255, 250, 150), (255, 160, 30)),
                                       ("HEIST", 344, 160, (140, 240, 255), (40, 120, 255))):
        text(L, (640, y), body, size, top=top, bottom=bottom, stroke=14, shadow=9)
    text(L, (640, 458), "VOLE  -  COLLECTIONNE  -  DOMINE", 30, stroke=5, shadow=3, path=BODY_FONT)
    return finish(L, w, h)


# ---------------------------------------------------------------- BUILD


NAV = [("nav_boutique", "BOUTIQUE", "red", 300, 96), ("nav_ma_base", "MA BASE", "blue", 380, 116),
       ("nav_ameliorations", "AMELIORER", "green", 330, 96)]
TILES = [("tile_cadeaux", "CADEAUX", "gift", "green", True), ("tile_boutique", "BOUTIQUE", "basket", "red", False),
         ("tile_pass", "PASS", "ticket", "yellow", False), ("tile_renaissance", "RENAISSANCE", "rebirth", "red", False),
         ("tile_index", "INDEX", "book", "blue", False), ("tile_classement", "CLASSEMENT", "trophy", "purple", False),
         ("tile_vitesse", "VITESSE", "bolt", "cyan", False), ("tile_base", "MA BASE", "house", "orange", False)]
PANELS = [("panel_boutique", "BOUTIQUE", "basket", "red"), ("panel_ameliorations", "AMELIORATIONS", "arrow_up", "green"),
          ("panel_index", "INDEX", "book", "blue"), ("panel_cadeaux", "CADEAUX", "gift", "yellow"),
          ("panel_vitesse", "VITESSE", "bolt", "cyan"), ("panel_renaissance", "RENAISSANCE", "rebirth", "purple")]
RAINBOW = [(255, 120, 90), (255, 210, 80), (140, 240, 110), (90, 200, 255), (190, 110, 255), (255, 110, 200)]
PURPLE = [(210, 90, 255), (255, 110, 190), (170, 80, 255)]


def build():
    files = []
    for name in list(ICONS) + ["capsule_" + k for k, _, _ in RARITIES]:
        files.append(save(icon(name, 256), "icons", name + ".png"))

    for name, label, color, w, h in NAV:
        files.append(save(button(w, h, color, label), "buttons", name + ".png"))
    for color in COLORS:
        files.append(save(button(300, 96, color), "buttons", "blank_%s.png" % color))
    for name, label, color, icon_name in (("price_gem", None, "green", "gem"),
                                          ("price_ichor", None, "green", "ichor"),
                                          ("buy", "ACHETER", "green", None),
                                          ("equip", "EQUIPER", "blue", None),
                                          ("sell", "VENDRE", "yellow", None),
                                          ("hatch", "ECLORE", "purple", "egg"),
                                          ("upgrade", "AMELIORER", "green", "arrow_up")):
        files.append(save(button(260, 84, color, label, icon_name), "buttons", name + ".png"))
    for n in (5, 10, 25):
        files.append(save(button(220, 64, "green", "+%d NIVEAUX" % n), "buttons", "plus_%d_niveaux.png" % n))
    files.append(save(button(92, 84, "red", "X", size=58), "buttons", "close.png"))

    for name, label, icon_name, color, badge in TILES:
        files.append(save(tile(label, icon_name, color, badge=badge), "tiles", name + ".png"))

    for name, title, icon_name, color in PANELS:
        files.append(save(panel(1000, 640, color, title, icon_name), "panels", name + ".png"))
    files.append(save(panel(1000, 640, "red", close=True), "panels", "panel_blank.png"))
    body = new_layer(256, 264)
    panel_shape(body, (4, 4, 252, 252), 30, *COLORS["dark"], thick=8, shadow=8, stripe=False, shine=False)
    files.append(save(finish(body, 256, 264), "panels", "panel_body_9slice.png"))
    files.append(save(card(900, 220, RAINBOW), "panels", "card_rainbow.png"))
    files.append(save(card(900, 220, PURPLE), "panels", "card_purple.png"))
    for key, label, color in RARITIES:
        files.append(save(slot(color), "panels", "slot_%s.png" % key))
        files.append(save(slot(color, label), "panels", "slot_%s_label.png" % key))

    frame, bar = level_bar()
    files.append(save(frame, "hud", "level_bar_frame.png"))
    files.append(save(bar, "hud", "level_bar_fill.png"))
    for name, label, icon_name in (("boost_x2_argent", "X2 ARGENT", "cash"),
                                   ("boost_x2_chance", "X2 CHANCE", "clover"),
                                   ("boost_x2_vitesse", "X2 VITESSE", "bolt")):
        files.append(save(button(280, 80, "dark", label, icon_name), "hud", name + ".png"))
    files.append(save(button(340, 84, "dark", None, "ichor"), "hud", "currency_ichor.png"))
    files.append(save(button(340, 84, "dark", None, "gem"), "hud", "currency_gem.png"))
    files.append(save(tile("PACK DEPART", "gift", "purple"), "hud", "starter_pack.png"))

    files.append(save(logo(), "logo", "logo_kaiju_heist.png"))
    files.append(save(mockup(), "preview_hud.png"))
    return files


def mockup(w=1280, h=720):
    """The HUD assembled from the files above, over a render of the lobby."""
    img = Image.new("RGBA", (w, h), (120, 190, 255, 255))
    if os.path.exists(MAP_PREVIEW):
        bg = Image.open(MAP_PREVIEW).convert("RGBA").resize((w, h), Image.LANCZOS)
        img.alpha_composite(bg.filter(ImageFilter.GaussianBlur(1.5)))

    def put(im, x, y, scale=1.0):
        if scale != 1.0:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        img.alpha_composite(im, (int(x), int(y)))
        return im

    open_ = lambda *p: Image.open(os.path.join(OUT, *p)).convert("RGBA")   # noqa: E731
    put(open_("buttons", "nav_boutique.png"), 330, 10, 0.72)
    put(open_("buttons", "nav_ma_base.png"), 548, 4, 0.72)
    put(open_("buttons", "nav_ameliorations.png"), 824, 10, 0.72)
    for i, (name, *_rest) in enumerate(TILES[:6]):
        put(open_("tiles", name + ".png"), 14 + (i % 2) * 104, 150 + (i // 2) * 104, 0.45)

    # Shop window with its content.
    pw = 700
    px, py = (w - pw) // 2, 110
    put(open_("panels", "panel_boutique.png"), px, py, pw / 1000.0)
    put(open_("panels", "card_rainbow.png"), px + 24, py + 102, 652 / 900.0)
    put(icon("capsule_legendary", 120), px + 40, py + 120)
    for i, (key, _, _) in enumerate(RARITIES):
        put(open_("panels", "slot_%s.png" % key), px + 250 + i * 80, py + 150, 0.46)
        put(icon("capsule_" + key, 56), px + 257 + i * 80, py + 158)
    put(open_("buttons", "price_gem.png"), px + 330, py + 238, 0.62)
    put(open_("buttons", "price_ichor.png"), px + 500, py + 238, 0.62)
    put(open_("panels", "card_purple.png"), px + 24, py + 300, 652 / 900.0)
    put(icon("gift", 120), px + 40, py + 314)
    for i, name in enumerate(("cash", "clover", "bolt")):
        put(open_("panels", "slot_epic.png"), px + 250 + i * 86, py + 336, 0.46)
        put(icon(name, 56), px + 257 + i * 86, py + 344)
    put(open_("buttons", "buy.png"), px + 520, py + 360, 0.62)

    put(open_("hud", "starter_pack.png"), w - 150, 120, 0.55)
    for i, name in enumerate(("boost_x2_argent", "boost_x2_chance")):
        put(open_("hud", name + ".png"), w - 210, 260 + i * 66, 0.7)
    put(open_("hud", "currency_ichor.png"), 10, h - 150, 0.7)
    put(open_("hud", "level_bar_frame.png"), 360, h - 120, 0.62)
    fill_img = open_("hud", "level_bar_fill.png")
    fill_img = fill_img.resize((int(fill_img.width * 0.62), int(fill_img.height * 0.62)), Image.LANCZOS)
    img.alpha_composite(fill_img.crop((0, 0, int(fill_img.width * 0.57), fill_img.height)),
                        (360 + int(9 * 0.62), h - 120 + int(9 * 0.62)))
    for i, n in enumerate((5, 10, 25)):
        put(open_("buttons", "plus_%d_niveaux.png" % n), 380 + i * 170, h - 64, 0.7)

    # Live values are text in Roblox; drawn here only to show the layout.
    over = new_layer(w, h)
    text(over, (110, h - 118), "572 831", 30, top=(255, 250, 160), bottom=(255, 180, 40), stroke=4,
         shadow=2, anchor="lm")
    text(over, (640, h - 101), "NIVEAU 5   57/100 XP", 20, stroke=3, shadow=2, path=BODY_FONT)
    text(over, (px + 330 + 70, py + 262), "55", 26, stroke=3, shadow=2)
    text(over, (px + 500 + 70, py + 262), "29", 26, stroke=3, shadow=2)
    text(over, (px + 250 + 200, py + 128), "CAPSULE EXCLUSIVE !", 26, stroke=4, shadow=2)
    text(over, (px + 250 + 200, py + 318), "PACK DE DEPART LIMITE !", 26, stroke=4, shadow=2)
    img.alpha_composite(finish(over, w, h))
    return img


def main():
    files = build()
    total = sum(os.path.getsize(f) for f in files)
    print("UI_ASSETS %d files, %.1f MB -> %s" % (len(files), total / 1e6, OUT))
    too_big = [f for f in files if max(Image.open(f).size) > 1024 and "preview" not in f]
    print("UI_OVERSIZE (Roblox max 1024 px): %s" % (too_big or "none"))


if __name__ == "__main__":
    main()
