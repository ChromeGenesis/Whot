"""Single source of truth for Whot card art.

The game used to ship ~200 hand-maintained SVGs plus ~200 pre-rendered PNGs
(DIY/, cards/, DIY-dark/, cards-dark/). This module replaces all of that with
one parametric spec:

* :func:`card_svg` stamps the master SVG template (user's Illustrator frame,
  186.3 x 255.5) with the real number + suit shape. Used for export / the
  ``assets/svg/`` tree via ``assets/build_cards_svg.py``.
* :func:`render_card` draws the same layout with Pillow for Tkinter at
  runtime. Tkinter's PhotoImage cannot display SVG, and this machine has no
  working SVG rasterizer (no cairo), so in-memory Pillow raster is the
  fastest dependency-free path: no file I/O, no per-card files, results
  cached in memory.

Deck composition matches the original file set.
"""

from __future__ import annotations

import functools
import math

# Exact deck composition (matches the original DIY/ file set).
NUMBERS: dict[str, list[int]] = {
    "Circle": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14],
    "Triangle": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14],
    "Cross": [1, 2, 3, 5, 7, 10, 11, 13, 14],
    "Square": [1, 2, 3, 5, 7, 10, 11, 13, 14],
    "Star": [1, 2, 3, 4, 5, 7, 8],
}
WHOT_COUNT = 5   # Whot_1..Whot_5, all value 20
MISC_COUNT = 12  # card backs
ICON_SUITS = ["circle", "cross", "square", "star", "triangle"]

PALETTES = {
    # User's Illustrator frame: cream card, deep maroon art.
    "light": {"bg": "#F4F4F2", "ink": "#791026", "red": "#7D1228",
              "border": "#000000", "shadow": "#D8D8D2"},
    # Dark card: deep slate face (darker than the table, lighter than the art
    # shadow), light edge, vivid red art.
    "dark": {"bg": "#333338", "ink": "#FFFFFF", "red": "#FF5C72",
             "border": "#7A7A82", "shadow": "#1C1C21"},
}

# Master frame geometry (user's 186.3 x 255.5 viewBox).
VB_W, VB_H = 186.3, 255.5
CENTER = (93.15, 127.75)
CENTER_R = 57.2
CORNER_TL = (23.6, 54.5)
CORNER_SCALE = 9.3 / 57.2  # corner shapes are scaled-down centers
SHADOW_DX, SHADOW_DY = 2.5, 3.0  # drop-shadow offset, svg units
NUM_TL = (15.9, 31.6)
NUM_FONT_SIZE = 26.9

CARD_W, CARD_H = 125, 171  # runtime raster size (matches old PNGs)
ICON_W, ICON_H = 56, 76


def _star_points(r_out: float, r_in: float, points: int = 5) -> str:
    pts = []
    for i in range(2 * points):
        ang = math.radians(-90 + i * 180 / points)
        rad = r_out if i % 2 == 0 else r_in
        pts.append(f"{rad * math.cos(ang):.1f},{rad * math.sin(ang):.1f}")
    return " ".join(pts)


# Suit fragments centered on (0, 0), sized for CENTER_R. Mirrored 1:1 in
# render_card() with Pillow primitives.
def _suit_fragment(suit: str, red: str) -> str:
    r = CENTER_R
    if suit == "Circle":
        return f'<circle cx="0" cy="0" r="{r}" fill="{red}"/>'
    if suit == "Triangle":
        return (f'<polygon points="0,{-r} {r * 0.9:.1f},{r * 0.7:.1f} '
                f'{-r * 0.9:.1f},{r * 0.7:.1f}" fill="{red}"/>')
    if suit == "Square":
        s = r * 0.9
        return (f'<rect x="{-s:.1f}" y="{-s:.1f}" width="{2 * s:.1f}" '
                f'height="{2 * s:.1f}" fill="{red}"/>')
    if suit == "Cross":
        a, e = r * 0.34, r * 0.9  # arm half-width, extent
        return (f'<polygon points="{-a:.1f},{-e:.1f} {a:.1f},{-e:.1f} '
                f'{a:.1f},{-a:.1f} {e:.1f},{-a:.1f} {e:.1f},{a:.1f} '
                f'{a:.1f},{a:.1f} {a:.1f},{e:.1f} {-a:.1f},{e:.1f} '
                f'{-a:.1f},{a:.1f} {-e:.1f},{a:.1f} {-e:.1f},{-a:.1f} '
                f'{-a:.1f},{-a:.1f}" fill="{red}"/>')
    if suit == "Star":
        return f'<polygon points="{_star_points(r, r * 0.404)}" fill="{red}"/>'
    raise ValueError(f"unknown suit: {suit}")


def _corner_pair(fragment: str) -> str:
    cx, cy = CENTER
    x, y = CORNER_TL
    s = CORNER_SCALE
    return (
        f'<g transform="translate({x},{y}) scale({s:.4f})">{fragment}</g>'
        f'<g transform="translate({2 * cx},{2 * cy}) rotate(180)">'
        f'<g transform="translate({x},{y}) scale({s:.4f})">{fragment}</g>'
        "</g>"
    )


def _number_pair(num: int | str, ink: str) -> str:
    x, y = NUM_TL
    cx, cy = CENTER
    fs = NUM_FONT_SIZE
    return (
        f'<text x="{x}" y="{y}" font-size="{fs}" font-family="Arial, '
        f'Helvetica, sans-serif" font-weight="bold" fill="{ink}">{num}</text>'
        f'<g transform="translate({2 * cx},{2 * cy}) rotate(180)">'
        f'<text x="{x}" y="{y}" font-size="{fs}" font-family="Arial, '
        f'Helvetica, sans-serif" font-weight="bold" fill="{ink}">{num}</text>'
        "</g>"
    )


def _whot_lines(fill: str) -> str:
    """Center 'whot' script + its 180-degree twin (reads upright either way)."""
    cx, cy = CENTER
    return (
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="34" '
        f'font-family="Georgia, \'Times New Roman\', serif" '
        f'font-style="italic" font-weight="bold" '
        f'fill="{fill}">whot</text>'
        f'<g transform="translate({2 * cx},{2 * cy}) rotate(180)">'
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="34" '
        f'font-family="Georgia, \'Times New Roman\', serif" '
        f'font-style="italic" font-weight="bold" '
        f'fill="{fill}">whot</text></g>'
    )


def _card_frame(pal: dict) -> str:
    return (
        f'<rect x="2" y="2" width="{VB_W - 4}" height="{VB_H - 4}" rx="14.2" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}" stroke-width="2"/>'
    )


@functools.lru_cache(maxsize=None)
def card_svg(suit: str, num: int, theme: str = "light") -> str:
    """Full SVG text for one number card. Pure string substitution (fast)."""
    pal = PALETTES[theme]
    frag = _suit_fragment(suit, pal["red"])
    shadow = _suit_fragment(suit, pal["shadow"])
    cx, cy = CENTER
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VB_W} {VB_H}" width="{CARD_W}" height="{CARD_H}">'
        + _card_frame(pal)
        + f'<g transform="translate({cx + SHADOW_DX},{cy + SHADOW_DY})" '
        f'opacity="0.6">{shadow}</g>'
        f'<g transform="translate({cx},{cy})">{frag}</g>'
        + _corner_pair(frag) + _number_pair(num, pal["ink"]) + "</svg>"
    )


@functools.lru_cache(maxsize=None)
def whot_svg(theme: str = "light") -> str:
    """Whot (20) card: script center, 20 corners."""
    pal = PALETTES[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VB_W} {VB_H}" width="{CARD_W}" height="{CARD_H}">'
        + _card_frame(pal)
        + f'<g transform="translate({SHADOW_DX},{SHADOW_DY})" opacity="0.6">'
        + _whot_lines(pal["shadow"]) + "</g>"
        + _whot_lines(pal["red"])
        + _number_pair(20, pal["ink"]) + "</svg>"
    )


@functools.lru_cache(maxsize=None)
def back_svg(theme: str = "light") -> str:
    """Card back: script center, no numbers."""
    pal = PALETTES[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VB_W} {VB_H}" width="{CARD_W}" height="{CARD_H}">'
        + _card_frame(pal)
        + f'<g transform="translate({SHADOW_DX},{SHADOW_DY})" opacity="0.6">'
        + _whot_lines(pal["shadow"]) + "</g>"
        + _whot_lines(pal["red"]) + "</svg>"
    )


@functools.lru_cache(maxsize=None)
def icon_svg(suit: str, theme: str = "light") -> str:
    """Small suit icon for the 'request card' dialog."""
    pal = PALETTES[theme]
    frag = _suit_fragment(suit.capitalize(), pal["red"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {ICON_W} {ICON_H}" width="{ICON_W}" height="{ICON_H}">'
        f'<rect x="0.5" y="0.5" width="{ICON_W - 1}" height="{ICON_H - 1}" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>'
        f'<g transform="translate({ICON_W / 2},{ICON_H / 2}) scale(0.42)">'
        f"{frag}</g></svg>"
    )


# ---------------------------------------------------------------------------
# Pillow runtime raster (Tkinter cannot display SVG; no cairo on this box).
# Same layout as the SVG template, drawn vector-crisp at 3x then downscaled.
# ---------------------------------------------------------------------------

def _clip_corners(img, k: float):
    """Punch transparent corners outside the rounded card outline.

    Without this the bitmap is an opaque square and the face color shows
    as a halo around the rounded corners on the table.
    """
    from PIL import Image, ImageDraw

    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, img.size[0], img.size[1]], radius=int(14.2 * k), fill=255)
    img.putalpha(mask)
    return img


_FONT_CACHE: dict[int, object] = {}


def _pillow_font(size: int):
    """Cached font handle (truetype loads are ~ms each; suits share sizes)."""
    hit = _FONT_CACHE.get(size)
    if hit is None:
        from PIL import ImageFont

        for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
            try:
                hit = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        else:
            hit = ImageFont.load_default()
        _FONT_CACHE[size] = hit
    return hit


def _draw_suit(draw, cx: float, cy: float, r: float, suit: str, red):
    if suit == "Circle":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=red)
    elif suit == "Triangle":
        draw.polygon([(cx, cy - r), (cx + r * 0.9, cy + r * 0.7),
                      (cx - r * 0.9, cy + r * 0.7)], fill=red)
    elif suit == "Square":
        s = r * 0.9
        draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=red)
    elif suit == "Cross":
        a, e = r * 0.34, r * 0.9
        draw.polygon([
            (cx - a, cy - e), (cx + a, cy - e), (cx + a, cy - a),
            (cx + e, cy - a), (cx + e, cy + a), (cx + a, cy + a),
            (cx + a, cy + e), (cx - a, cy + e), (cx - a, cy + a),
            (cx - e, cy + a), (cx - e, cy - a), (cx - a, cy - a),
        ], fill=red)
    elif suit == "Star":
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            rad = r if i % 2 == 0 else r * 0.404
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        draw.polygon(pts, fill=red)
    else:
        raise ValueError(f"unknown suit: {suit}")


@functools.lru_cache(maxsize=None)
def render_card(suit: str, num: int, theme: str = "light",
                w: int = CARD_W, h: int = CARD_H):
    """Render a number card to a Pillow image (cached)."""
    from PIL import Image, ImageDraw

    pal = PALETTES[theme]
    ss = 3
    W, H = w * ss, h * ss
    img = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(img)
    k = W / VB_W  # svg units -> supersampled px
    cx, cy = CENTER[0] * k, CENTER[1] * k
    r = CENTER_R * k
    red = pal["red"]
    odx, ody = SHADOW_DX * k, SHADOW_DY * k
    _draw_suit(d, cx + odx, cy + ody, r, suit, pal["shadow"])
    _draw_suit(d, cx, cy, r, suit, red)
    # corner minis
    for (ccx, ccy) in ((CORNER_TL[0] * k, CORNER_TL[1] * k),
                       ((2 * CENTER[0] - CORNER_TL[0]) * k,
                        (2 * CENTER[1] - CORNER_TL[1]) * k)):
        _draw_suit(d, ccx, ccy, r * CORNER_SCALE, suit, red)
    # rounded border
    d.rounded_rectangle([ss, ss, W - ss, H - ss], radius=int(14.2 * k),
                        outline=pal["border"], width=2 * ss)
    # numbers (not rotated at runtime; corners read fine unrotated)
    fnt = _pillow_font(20 * ss)
    d.text((NUM_TL[0] * k, NUM_TL[1] * k - int(22 * k)), str(num),
           font=fnt, fill=pal["ink"], anchor="lt")
    d.text((W - NUM_TL[0] * k, H - (NUM_TL[1] * k - int(22 * k))), str(num),
           font=fnt, fill=pal["ink"], anchor="rb")
    _clip_corners(img, k)
    return img.resize((w, h), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def render_whot(theme: str = "light", w: int = CARD_W, h: int = CARD_H):
    from PIL import Image, ImageDraw

    pal = PALETTES[theme]
    ss = 3
    W, H = w * ss, h * ss
    img = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(img)
    k = W / VB_W
    fnt_big = _pillow_font(32 * ss)
    fnt = _pillow_font(20 * ss)
    od = 2 * ss
    d.text((W / 2 + od, H / 2 + od), "whot", font=fnt_big,
           fill=pal["shadow"], anchor="mm")
    d.text((W / 2, H / 2), "whot", font=fnt_big, fill=pal["red"],
           anchor="mm")
    d.rounded_rectangle([ss, ss, W - ss, H - ss], radius=int(14.2 * k),
                        outline=pal["border"], width=2 * ss)
    d.text((NUM_TL[0] * k, NUM_TL[1] * k - int(22 * k)), "20",
           font=fnt, fill=pal["ink"], anchor="lt")
    d.text((W - NUM_TL[0] * k, H - (NUM_TL[1] * k - int(22 * k))), "20",
           font=fnt, fill=pal["ink"], anchor="rb")
    _clip_corners(img, k)
    return img.resize((w, h), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def render_back(theme: str = "light", w: int = CARD_W, h: int = CARD_H):
    from PIL import Image, ImageDraw

    pal = PALETTES[theme]
    ss = 3
    W, H = w * ss, h * ss
    img = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(img)
    k = W / VB_W
    fnt_big = _pillow_font(32 * ss)
    od = 2 * ss
    d.text((W / 2 + od, H / 2 + od), "whot", font=fnt_big,
           fill=pal["shadow"], anchor="mm")
    d.text((W / 2, H / 2), "whot", font=fnt_big, fill=pal["red"],
           anchor="mm")
    d.rounded_rectangle([ss, ss, W - ss, H - ss], radius=int(14.2 * k),
                        outline=pal["border"], width=2 * ss)
    _clip_corners(img, k)
    return img.resize((w, h), Image.LANCZOS)


@functools.lru_cache(maxsize=None)
def render_icon(suit: str, theme: str = "light",
                w: int = ICON_W, h: int = ICON_H):
    from PIL import Image, ImageDraw

    pal = PALETTES[theme]
    img = Image.new("RGB", (w, h), pal["bg"])
    d = ImageDraw.Draw(img)
    _draw_suit(d, w / 2 + 1, h / 2 + 1, min(w, h) * 0.36,
               suit.capitalize(), pal["shadow"])
    _draw_suit(d, w / 2, h / 2, min(w, h) * 0.36, suit.capitalize(),
               pal["red"])
    d.rectangle([0, 0, w - 1, h - 1], outline=pal["border"])
    return img


def deck_keys() -> list[tuple[str, int]]:
    """All (suit, number) pairs in the deck, Whot 20s included."""
    keys = [(s, n) for s, ns in NUMBERS.items() for n in ns]
    keys += [("Whot", 20)] * WHOT_COUNT
    return keys
