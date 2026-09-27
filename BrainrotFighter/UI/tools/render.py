"""Approximate renderer of a Roblox GUI snapshot (JSON from the Luau mock).

Supports what BrainrotUI uses: Frame / TextLabel / TextButton / ScrollingFrame,
UICorner, UIStroke (border + text outline), UIGradient (colour + transparency),
UIListLayout, UIGridLayout, UIPadding, UIScale, UITextSizeConstraint, Rotation
(with inherited transforms), ClipsDescendants, ZIndex (sibling mode), emoji.
"""
import json
import math
import os
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("BRAINROTUI_FONTS", os.path.join(HERE, ".cache", "fonts"))
MAPS = os.path.join(HERE, "..", "..")

SS = 2  # supersampling
FONTS = {
    "FredokaOne": os.path.join(FONT_DIR, "FredokaOne.ttf"),
    "LuckiestGuy": os.path.join(FONT_DIR, "LuckiestGuy.ttf"),
}
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_font_cache = {}
_cmap_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, max(1, int(size)))
    return _font_cache[key]


def has_glyph(path, ch):
    """A glyph is missing when it renders exactly like the .notdef glyph."""
    key = (path, ch)
    if key not in _cmap_cache:
        f = font(path, 40)

        def raster(c):
            img = Image.new("L", (80, 80), 0)
            ImageDraw.Draw(img).text((10, 10), c, font=f, fill=255)
            return img.tobytes()

        _cmap_cache[key] = ch == " " or raster(ch) != raster("\ue000")
    return _cmap_cache[key]


def is_emoji(ch):
    cp = ord(ch)
    return cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF or cp in (0x2B50, 0x2B55, 0x231A, 0x23F0, 0x2705)


# ---------------------------------------------------------------- geometry
def mat_mul(a, b):
    return (
        a[0] * b[0] + a[1] * b[3], a[0] * b[1] + a[1] * b[4], a[0] * b[2] + a[1] * b[5] + a[2],
        a[3] * b[0] + a[4] * b[3], a[3] * b[1] + a[4] * b[4], a[3] * b[2] + a[4] * b[5] + a[5],
    )


def translate(x, y):
    return (1, 0, x, 0, 1, y)


def rotate_about(cx, cy, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return mat_mul(translate(cx, cy), mat_mul((c, -s, 0, s, c, 0), translate(-cx, -cy)))


def apply(m, x, y):
    return (m[0] * x + m[1] * y + m[2], m[3] * x + m[4] * y + m[5])


def invert(m):
    a, b, c, d, e, f = m
    det = a * e - b * d
    return (e / det, -b / det, (b * f - c * e) / det, -d / det, a / det, (c * d - a * f) / det)


def is_axis_aligned(m):
    return abs(m[1]) < 1e-9 and abs(m[3]) < 1e-9 and abs(m[0] - 1) < 1e-9 and abs(m[4] - 1) < 1e-9


# ---------------------------------------------------------------- helpers
def kids(node, cls=None):
    return [k for k in node["k"] if cls is None or k["c"] == cls]


def first(node, cls):
    for k in node["k"]:
        if k["c"] == cls:
            return k
    return None


def is_gui(node):
    return node["c"] in ("Frame", "TextLabel", "TextButton", "ScrollingFrame", "ImageLabel", "ImageButton", "TextBox")


def seq_color(seq, t):
    t = min(max(t, 0), 1)
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        if a[0] <= t <= b[0]:
            u = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
            return [a[j] + (b[j] - a[j]) * u for j in (1, 2, 3)]
    return seq[-1][1:4]


def seq_num(seq, t):
    t = min(max(t, 0), 1)
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        if a[0] <= t <= b[0]:
            u = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * u
    return seq[-1][1]


def gradient_image(w, h, grad, base_rgb, base_alpha):
    """RGBA image of w x h: base colour multiplied by the gradient colour, alpha by (1 - transparency)."""
    import numpy as np
    w, h = max(1, int(w)), max(1, int(h))
    rot = math.radians(grad["p"].get("Rotation", 0))
    color = grad["p"].get("Color")
    trans = grad["p"].get("Transparency")
    if isinstance(trans, (int, float)):
        trans = [[0, trans], [1, trans]]
    dx, dy = math.cos(rot), math.sin(rot)
    # projection extent of the box on the gradient axis
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (-w / 2, h / 2), (w / 2, h / 2)]
    proj = [x * dx + y * dy for x, y in corners]
    lo, hi = min(proj), max(proj)
    n = 256
    lut_rgb = [seq_color(color, i / (n - 1)) if color else [1, 1, 1] for i in range(n)]
    lut_a = [1 - seq_num(trans, i / (n - 1)) if trans else 1 for i in range(n)]
    ys, xs = np.mgrid[0:h, 0:w]
    proj_px = (xs + 0.5 - w / 2) * dx + (ys + 0.5 - h / 2) * dy
    t = (proj_px - lo) / (hi - lo) if hi > lo else np.zeros_like(proj_px)
    idx = np.clip((t * (n - 1) + 0.5).astype(int), 0, n - 1)
    rgb = np.array(lut_rgb) * np.array(base_rgb)
    alpha = np.array(lut_a) * base_alpha
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = (rgb[idx] * 255).clip(0, 255).astype(np.uint8)
    out[..., 3] = (alpha[idx] * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def gradient_image_fast(w, h, grad, base_rgb, base_alpha):
    # render small then scale up (gradients are smooth); hard edges keep enough resolution at 128
    w, h = max(1, int(w)), max(1, int(h))
    sw, sh = min(w, 400), min(h, 400)
    img = gradient_image(sw, sh, grad, base_rgb, base_alpha)
    return img.resize((w, h), Image.BILINEAR)


def rounded_mask(w, h, radius):
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=max(0, min(radius, min(w, h) / 2)), fill=255)
    return m


# ---------------------------------------------------------------- text
def split_runs(text, main_path):
    runs = []
    for ch in text:
        if ch == "\n":
            kind = "nl"
        elif is_emoji(ch) or unicodedata.category(ch) == "Mn":
            kind = "emoji" if is_emoji(ch) else "skip"
        elif has_glyph(main_path, ch):
            kind = "main"
        else:
            kind = "fallback"
        if kind == "skip":
            continue
        if runs and runs[-1][0] == kind and kind != "nl":
            runs[-1][1] += ch
        else:
            runs.append([kind, ch])
    return runs


def run_width(kind, s, main_path, size):
    if kind == "emoji":
        return len(s) * size * 1.17
    path = main_path if kind == "main" else FALLBACK
    return font(path, size).getlength(s)


def layout_text(text, main_path, size, max_w, wrap):
    """Returns lines as lists of runs, and their widths."""
    words = []
    for para in text.split("\n"):
        words.append(para.split(" "))
    lines = []
    for para in words:
        cur = ""
        for word in para:
            cand = word if cur == "" else cur + " " + word
            if wrap and cur != "" and measure(cand, main_path, size) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = cand
        lines.append(cur)
    return lines


def measure(s, main_path, size):
    return sum(run_width(k, t, main_path, size) for k, t in split_runs(s, main_path))


def draw_text_block(img, text, box, size, main_path, color, alpha, xalign, yalign, wrap, stroke, grad):
    """Draws text into img (RGBA) inside box=(x, y, w, h)."""
    x0, y0, bw, bh = box
    lines = layout_text(text, main_path, size, bw, wrap)
    f = font(main_path, size)
    ascent, descent = f.getmetrics()
    line_h = size * 1.0 if "Luckiest" in main_path else size * 1.18
    total_h = line_h * len(lines)
    if yalign == "Top":
        ty = y0
    elif yalign == "Bottom":
        ty = y0 + bh - total_h
    else:
        ty = y0 + (bh - total_h) / 2
    text_mask = Image.new("L", img.size, 0)
    stroke_mask = Image.new("L", img.size, 0)
    emoji_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dm, ds = ImageDraw.Draw(text_mask), ImageDraw.Draw(stroke_mask)
    sw = int(round(stroke[0])) if stroke else 0
    for i, line in enumerate(lines):
        lw = measure(line, main_path, size)
        if xalign == "Left":
            tx = x0
        elif xalign == "Right":
            tx = x0 + bw - lw
        else:
            tx = x0 + (bw - lw) / 2
        ly = ty + i * line_h
        cx = tx
        for kind, s in split_runs(line, main_path):
            if kind == "emoji":
                for ch in s:
                    e = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
                    ImageDraw.Draw(e).text((0, 0), ch, font=font(EMOJI, 109), embedded_color=True)
                    bb = e.getbbox()
                    if bb:
                        e = e.crop((0, 0, 136, 128))
                        tgt = max(1, int(size * 1.17))
                        e = e.resize((tgt, max(1, int(tgt * 128 / 136))), Image.LANCZOS)
                        if alpha < 1:
                            a = e.split()[3].point(lambda v: int(v * alpha))
                            e.putalpha(a)
                        emoji_layer.alpha_composite(e, (int(cx), int(ly + line_h / 2 - e.size[1] / 2)))
                    cx += size * 1.17
                continue
            path = main_path if kind == "main" else FALLBACK
            ff = font(path, size)
            # vertical centring of the glyph box in the line
            bbox = ff.getbbox("Hg")
            gy = ly + (line_h - (bbox[3] - bbox[1])) / 2 - bbox[1]
            if sw > 0:
                ds.text((cx, gy), s, font=ff, fill=255, stroke_width=sw, stroke_fill=255)
            dm.text((cx, gy), s, font=ff, fill=255)
            cx += ff.getlength(s)
    if stroke and sw > 0:
        scol = stroke[1]
        s_alpha = stroke[2]
        layer = Image.new("RGBA", img.size, tuple(int(c * 255) for c in scol) + (0,))
        layer.putalpha(stroke_mask.point(lambda v: int(v * s_alpha)))
        img.alpha_composite(layer)
    if grad is not None:
        fill = gradient_image_fast(bw, max(1, total_h), grad, color, 1)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        layer.paste(fill, (int(x0), int(ty)))
        a = Image.new("L", img.size, 0)
        a.paste(text_mask, (0, 0))
        la = layer.split()[3]
        from PIL import ImageChops
        layer.putalpha(ImageChops.multiply(la, text_mask.point(lambda v: int(v * alpha))))
    else:
        layer = Image.new("RGBA", img.size, tuple(int(c * 255) for c in color) + (0,))
        layer.putalpha(text_mask.point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)
    img.alpha_composite(emoji_layer)


def fit_text_size(text, main_path, box_w, box_h, max_size, wrap=True):
    lo, hi = 1, int(max_size)
    best = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        lines = layout_text(text, main_path, mid, box_w, wrap)
        line_h = mid * (1.0 if "Luckiest" in main_path else 1.18)
        width = max(measure(l, main_path, mid) for l in lines) if lines else 0
        if width <= box_w and line_h * len(lines) <= box_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


# ---------------------------------------------------------------- renderer
class Renderer:
    def __init__(self, width, height, inset, background=None):
        self.W, self.H, self.inset = width * SS, height * SS, inset * SS
        self.canvas = Image.new("RGBA", (self.W, self.H), (40, 60, 90, 255))
        if background:
            bg = Image.open(background).convert("RGBA")
            scale = max(self.W / bg.width, self.H / bg.height)
            bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
            ox, oy = (bg.width - self.W) // 2, (bg.height - self.H) // 2
            self.canvas.alpha_composite(bg.crop((ox, oy, ox + self.W, oy + self.H)))
        # Roblox top bar
        d = ImageDraw.Draw(self.canvas)
        for i in range(3):
            x = (12 + i * 52) * SS
            d.rounded_rectangle([x, 10 * SS, x + 44 * SS, 54 * SS if inset > 40 else 32 * SS], radius=22 * SS, fill=(20, 20, 26, 190))
        self.warnings = []

    # size & position ---------------------------------------------------------
    def compute_box(self, node, content, scale):
        p = node["p"]
        size = p.get("Size", [0, 0, 0, 0])
        w = content[2] * size[0] + size[1] * scale
        h = content[3] * size[2] + size[3] * scale
        own = first(node, "UIScale")
        k = own["p"].get("Scale", 1) if own else 1
        ar = first(node, "UIAspectRatioConstraint")
        if ar:
            ratio = ar["p"].get("AspectRatio", 1)
            if w / max(h, 1e-6) > ratio:
                w = h * ratio
            else:
                h = w / ratio
        return w, h, k

    def render(self, root):
        # ScreenGui content box: below the top bar inset
        children = sorted([c for c in root["k"] if is_gui(c)], key=lambda c: c["p"].get("ZIndex", 1))
        for child in children:
            self.render_node(child, translate(0, self.inset), (0, 0, self.W, self.H - self.inset), SS, None, placed=None)

    def layout_children(self, node, content, scale):
        """Returns {id(child): (x, y)} for children placed by a layout."""
        lst = first(node, "UIListLayout")
        grid = first(node, "UIGridLayout")
        guis = [c for c in node["k"] if is_gui(c) and c["p"].get("Visible", True)]
        placed = {}
        if lst:
            p = lst["p"]
            order = sorted(enumerate(guis), key=lambda e: (e[1]["p"].get("LayoutOrder", 0), e[0]))
            vertical = p.get("FillDirection", "Vertical") == "Vertical"
            pad = p.get("Padding", [0, 0])
            gap = (content[3] if vertical else content[2]) * pad[0] + pad[1] * scale
            sizes = []
            for _, c in order:
                w, h, k = self.compute_box(c, content, scale)
                sizes.append((w * k, h * k))
            total = sum(s[1] if vertical else s[0] for s in sizes) + gap * max(0, len(sizes) - 1)
            main_align = p.get("VerticalAlignment", "Top") if vertical else p.get("HorizontalAlignment", "Left")
            cross_align = p.get("HorizontalAlignment", "Left") if vertical else p.get("VerticalAlignment", "Top")
            extent = content[3] if vertical else content[2]
            start = 0 if main_align in ("Top", "Left") else (extent - total if main_align in ("Bottom", "Right") else (extent - total) / 2)
            cursor = start
            for (_, c), (w, h) in zip(order, sizes):
                if vertical:
                    cross = content[2]
                    x = 0 if cross_align == "Left" else (cross - w if cross_align == "Right" else (cross - w) / 2)
                    placed[id(c)] = (x, cursor)
                    cursor += h + gap
                else:
                    cross = content[3]
                    y = 0 if cross_align == "Top" else (cross - h if cross_align == "Bottom" else (cross - h) / 2)
                    placed[id(c)] = (cursor, y)
                    cursor += w + gap
            return placed, (total if vertical else None)
        if grid:
            p = grid["p"]
            cs = p.get("CellSize", [0, 100, 0, 100])
            cp = p.get("CellPadding", [0, 5, 0, 5])
            cw, ch = content[2] * cs[0] + cs[1] * scale, content[3] * cs[2] + cs[3] * scale
            px, py = content[2] * cp[0] + cp[1] * scale, content[3] * cp[2] + cp[3] * scale
            cols = max(1, int((content[2] + px + 1e-6) // (cw + px)))
            order = sorted(enumerate(guis), key=lambda e: (e[1]["p"].get("LayoutOrder", 0), e[0]))
            used = min(len(order), cols)
            block = used * cw + (used - 1) * px
            align = p.get("HorizontalAlignment", "Left")
            ox = 0 if align == "Left" else (content[2] - block if align == "Right" else (content[2] - block) / 2)
            for i, (_, c) in enumerate(order):
                r, col = divmod(i, cols)
                placed[id(c)] = (ox + col * (cw + px), r * (ch + py), cw, ch)
            rows = (len(order) + cols - 1) // cols
            return placed, rows * ch + max(0, rows - 1) * py
        return placed, None

    def render_node(self, node, parent_m, content, scale, clip, placed):
        p = node["p"]
        if not p.get("Visible", True):
            return
        if placed and id(node) in placed and len(placed[id(node)]) == 4:
            x, y, w, h = placed[id(node)]
            k = 1
            own = first(node, "UIScale")
            if own:
                k = own["p"].get("Scale", 1)
            tl = (content[0] + x, content[1] + y)
        else:
            w, h, k = self.compute_box(node, content, scale)
            ap = p.get("AnchorPoint", [0, 0])
            if placed and id(node) in placed:
                x, y = placed[id(node)]
                tl = (content[0] + x, content[1] + y)
                w, h = w * k, h * k
            else:
                pos = p.get("Position", [0, 0, 0, 0])
                ax = content[0] + content[2] * pos[0] + pos[1] * scale
                ay = content[1] + content[3] * pos[2] + pos[3] * scale
                w, h = w * k, h * k
                tl = (ax - ap[0] * w, ay - ap[1] * h)
        s_children = scale * k
        m = mat_mul(parent_m, translate(tl[0], tl[1]))
        rot = p.get("Rotation", 0) or 0
        if rot:
            m = mat_mul(m, rotate_about(w / 2, h / 2, rot))
        self.draw_self(node, m, w, h, s_children, clip)

        # children
        pad = first(node, "UIPadding")
        pl = pr = pt = pb = 0
        if pad:
            pp = pad["p"]
            pl = w * pp.get("PaddingLeft", [0, 0])[0] + pp.get("PaddingLeft", [0, 0])[1] * s_children
            pr = w * pp.get("PaddingRight", [0, 0])[0] + pp.get("PaddingRight", [0, 0])[1] * s_children
            pt = h * pp.get("PaddingTop", [0, 0])[0] + pp.get("PaddingTop", [0, 0])[1] * s_children
            pb = h * pp.get("PaddingBottom", [0, 0])[0] + pp.get("PaddingBottom", [0, 0])[1] * s_children
        child_content = (pl, pt, w - pl - pr, h - pt - pb)
        child_clip = clip
        rotated_chain = not is_axis_aligned((m[0], m[1], 0, m[3], m[4], 0))
        clips = p.get("ClipsDescendants") or node["c"] == "ScrollingFrame"
        if clips and not rotated_chain:
            x0, y0 = apply(m, 0, 0)
            rect = (x0, y0, x0 + w, y0 + h)
            child_clip = rect if clip is None else (max(clip[0], rect[0]), max(clip[1], rect[1]), min(clip[2], rect[2]), min(clip[3], rect[3]))
        child_m = m
        if node["c"] == "ScrollingFrame":
            cpos = p.get("CanvasPosition", [0, 0])
            child_m = mat_mul(m, translate(-cpos[0], -cpos[1]))
        placed_children, extent = self.layout_children(node, child_content, s_children)
        if node["c"] == "ScrollingFrame" and extent is not None and extent + pt + pb > h + 1:
            # scrollbar hint
            x0, y0 = apply(m, w - 6 * s_children, 4 * s_children)
            bar_h = h * h / (extent + pt + pb)
            d = ImageDraw.Draw(self.canvas)
            d.rounded_rectangle([x0, y0, x0 + 5 * s_children, y0 + bar_h - 8 * s_children], radius=3 * s_children, fill=(196, 190, 228, 200))
        guis = [c for c in node["k"] if is_gui(c)]
        guis = sorted(enumerate(guis), key=lambda e: (e[1]["p"].get("ZIndex", 1), e[0]))
        for _, child in guis:
            self.render_node(child, child_m, child_content, s_children, child_clip, placed_children)

    def draw_self(self, node, m, w, h, s, clip):
        p = node["p"]
        if w <= 0.5 or h <= 0.5:
            return
        corner = first(node, "UICorner")
        radius = 0
        if corner:
            cr = corner["p"].get("CornerRadius", [0, 8])
            radius = min(w, h) * cr[0] + cr[1] * s
        strokes = [k for k in kids(node, "UIStroke") if k["p"].get("Enabled", True)]
        border = next((k for k in strokes if k["p"].get("ApplyStrokeMode") == "Border"), None)
        textstroke = next((k for k in strokes if k["p"].get("ApplyStrokeMode") == "Contextual"), None)
        is_text = node["c"] in ("TextLabel", "TextButton", "TextBox")
        if not is_text and textstroke and not border:
            border = textstroke  # contextual stroke on a frame outlines its border
        grad = first(node, "UIGradient")
        grad = grad if grad and grad["p"].get("Enabled", True) else None
        bt = p.get("BackgroundTransparency", 0)
        margin = int(math.ceil((border["p"].get("Thickness", 1) * s + 2) if border else 2))
        lw, lh = int(math.ceil(w)) + 2 * margin, int(math.ceil(h)) + 2 * margin
        if lw > 6000 or lh > 6000:
            return
        layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        drew = False
        # background
        if bt < 1:
            col = p.get("BackgroundColor3", [0.64, 0.635, 0.647])
            mask = rounded_mask(w, h, radius)
            if grad and not is_text:
                fill = gradient_image_fast(mask.size[0], mask.size[1], grad, col, 1 - bt)
            else:
                fill = Image.new("RGBA", mask.size, tuple(int(c * 255) for c in col) + (int((1 - bt) * 255),))
            a = fill.split()[3]
            from PIL import ImageChops
            fill.putalpha(ImageChops.multiply(a, mask))
            layer.alpha_composite(fill, (margin, margin))
            drew = True
        # border stroke (outside)
        if border:
            t = border["p"].get("Thickness", 1) * s
            st = border["p"].get("Transparency", 0)
            if st < 1 and t > 0:
                outer = rounded_mask(w + 2 * t, h + 2 * t, radius + t if radius > 0 else 0)
                inner = Image.new("L", outer.size, 0)
                inner.paste(rounded_mask(w, h, radius), (int(round(t)), int(round(t))))
                from PIL import ImageChops
                ring = ImageChops.subtract(outer, inner)
                sgrad = first(border, "UIGradient")
                col = border["p"].get("Color", [0, 0, 0])
                if sgrad:
                    fill = gradient_image_fast(ring.size[0], ring.size[1], sgrad, col, 1 - st)
                else:
                    fill = Image.new("RGBA", ring.size, tuple(int(c * 255) for c in col) + (int((1 - st) * 255),))
                fill.putalpha(ImageChops.multiply(fill.split()[3], ring))
                layer.alpha_composite(fill, (int(round(margin - t)), int(round(margin - t))))
                drew = True
        # text
        if is_text and p.get("Text"):
            text = p["Text"]
            family = p.get("FontFace", "FredokaOne")
            main_path = FONTS.get(family, FALLBACK)
            size = p.get("TextSize", 14) * s
            tsc = first(node, "UITextSizeConstraint")
            if p.get("TextScaled"):
                max_size = 100 * s
                if tsc:
                    max_size = min(max_size, tsc["p"].get("MaxTextSize", 100) * s)
                size = fit_text_size(text, main_path, w, h, max_size, True)
            elif tsc:
                size = min(size, tsc["p"].get("MaxTextSize", 100) * s)
            ta = 1 - p.get("TextTransparency", 0)
            if ta > 0:
                stroke = None
                if textstroke:
                    stroke = (textstroke["p"].get("Thickness", 1) * s, textstroke["p"].get("Color", [0, 0, 0]), (1 - textstroke["p"].get("Transparency", 0)) * ta)
                draw_text_block(
                    layer, text, (margin, margin, w, h), size, main_path, p.get("TextColor3", [0, 0, 0]), ta,
                    p.get("TextXAlignment", "Center"), p.get("TextYAlignment", "Center"),
                    p.get("TextWrapped") or p.get("TextScaled"), stroke, grad,
                )
                drew = True
                # overflow warning
                if not p.get("TextScaled"):
                    lines = layout_text(text, main_path, size, w, p.get("TextWrapped"))
                    widest = max(measure(l, main_path, size) for l in lines)
                    if widest > w + 2 * s or len(lines) * size * 1.1 > h + 6 * s:
                        self.warnings.append(f"text overflow: {text!r} ({widest / s:.0f}x{len(lines) * size / s:.0f} in {w / s:.0f}x{h / s:.0f})")
        if not drew:
            return
        self.composite(layer, m, margin, clip)

    def composite(self, layer, m, margin, clip):
        # element local (0,0) is at layer (margin, margin)
        full = mat_mul(m, translate(-margin, -margin))
        lw, lh = layer.size
        pts = [apply(full, x, y) for x, y in ((0, 0), (lw, 0), (0, lh), (lw, lh))]
        x0, y0 = math.floor(min(p[0] for p in pts)), math.floor(min(p[1] for p in pts))
        x1, y1 = math.ceil(max(p[0] for p in pts)), math.ceil(max(p[1] for p in pts))
        if clip:
            x0, y0 = max(x0, math.floor(clip[0])), max(y0, math.floor(clip[1]))
            x1, y1 = min(x1, math.ceil(clip[2])), min(y1, math.ceil(clip[3]))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, self.W), min(y1, self.H)
        if x1 <= x0 or y1 <= y0:
            return
        if abs(full[1]) < 1e-9 and abs(full[3]) < 1e-9 and abs(full[0] - 1) < 1e-9 and abs(full[4] - 1) < 1e-9:
            ox, oy = full[2], full[5]
            crop = layer.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy))
        else:
            inv = invert(mat_mul(translate(-x0, -y0), full))
            crop = layer.transform((x1 - x0, y1 - y0), Image.AFFINE, inv, resample=Image.BILINEAR)
        self.canvas.alpha_composite(crop, (x0, y0))

    def save(self, path):
        out = self.canvas.resize((self.W // SS, self.H // SS), Image.LANCZOS).convert("RGB")
        out.save(path)


def render_log(log, outdir):
    """Renders every SNAP line of a session log into outdir/<name>.png."""
    os.makedirs(outdir, exist_ok=True)
    backgrounds = {
        "hud": os.path.join(MAPS, "PirateIsland", "previews", "PirateIsland_Preview_Spawn.png"),
        "hud_fresh": os.path.join(MAPS, "Zone6_VoidBrainrot", "previews", "Zone6_VoidBrainrot_Preview_Entrance.png"),
    }
    default_bg = os.path.join(MAPS, "PirateIsland", "previews", "PirateIsland_Preview_Center.png")
    for line in open(log, encoding="utf-8"):
        if not line.startswith("SNAP "):
            continue
        _, name, w, h, inset, payload = line.split(" ", 5)
        tree = json.loads(payload)
        background = backgrounds.get(name, default_bg)
        r = Renderer(int(w), int(h), int(inset), background if os.path.exists(background) else None)
        r.render(tree)
        r.save(os.path.join(outdir, f"{name}.png"))
        for warning in sorted(set(r.warnings)):
            print(f"[{name}] {warning}")
        print("rendered", name)


if __name__ == "__main__":
    render_log(sys.argv[1], sys.argv[2])
