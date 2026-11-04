"""Build all Whot card art from original vector sources.

Writes per-card .svg files under assets/svg/<theme>/ (the source of truth),
renders them with headless Chrome contact sheets, and slices the screenshots
into the themed PNG trees the game loads:

    assets/svg/light  +  assets/svg/dark   (sources, committed)
    DIY/  cards/                            (light runtime set)
    DIY-dark/  cards-dark/                  (dark runtime set)

Run:  python assets/render_cards.py   (needs Chrome + Pillow, dev machine only;
the game itself needs neither Pillow nor Chrome at runtime.)
"""
import math
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CARD_W, CARD_H = 125, 171
ICON_W, ICON_H = 56, 76

PALETTES = {
    "light": {"bg": "#FEFEFE", "ink": "#373435", "red": "#ED3237",
              "border": "#B9B9B9"},
    "dark": {"bg": "#3B3B3D", "ink": "#EDEDED", "red": "#ED3237",
             "border": "#232325"},
}

# Exact deck composition (matches the original DIY/ file set).
NUMBERS = {
    "Circle": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14],
    "Triangle": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14],
    "Cross": [1, 2, 3, 5, 7, 10, 11, 13, 14],
    "Square": [1, 2, 3, 5, 7, 10, 11, 13, 14],
    "Star": [1, 2, 3, 4, 5, 7, 8],
}
WHOT_COUNT = 5   # Whot_1..Whot_5.png, all value 20
MISC_COUNT = 12  # Misc_whot1..Misc_whot12.png (card backs)
ICON_SUITS = ["circle", "cross", "square", "star", "triangle"]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def star_points(r_out, r_in, points=5):
    pts = []
    for i in range(2 * points):
        ang = math.radians(-90 + i * 180 / points)
        rad = r_out if i % 2 == 0 else r_in
        pts.append(f"{rad * math.cos(ang):.1f},{rad * math.sin(ang):.1f}")
    return " ".join(pts)


# Shape fragments centered on (0, 0) inside a ~96px box. Placed with
# <g transform="translate(x,y) scale(s)">.
SHAPES = {
    "Circle": '<circle cx="0" cy="0" r="40" fill="{red}"/>',
    "Triangle": '<polygon points="0,-42 38,30 -38,30" fill="{red}"/>',
    "Square": '<rect x="-38" y="-38" width="76" height="76" fill="{red}"/>',
    "Cross": ('<polygon points="-13,-38 13,-38 13,-13 38,-13 38,13 13,13 '
              '13,38 -13,38 -13,13 -38,13 -38,-13 -13,-13" fill="{red}"/>'),
    "Star": f'<polygon points="{star_points(42, 17)}" fill="{{red}}"/>',
}

SUIT_OF_ICON = {s: s.capitalize() for s in ICON_SUITS}

NUM_FONT = 'font-family="Arial, Helvetica, sans-serif" font-weight="bold"'
SCRIPT_FONT = 'font-family="Georgia, \'Times New Roman\', serif" font-style="italic" font-weight="bold"'


def shape_placed(shape_svg, x, y, scale):
    return (f'<g transform="translate({x},{y}) scale({scale})">'
            f'{shape_svg}</g>')


def card_svg(suit, num, pal):
    shape = SHAPES[suit].format(red=pal["red"])
    idx = (
        f'<text x="9" y="23" font-size="20" {NUM_FONT} fill="{pal["ink"]}">{num}</text>'
        + shape_placed(shape, 19, 41, 0.22)
        + f'<g transform="translate({CARD_W},{CARD_H}) rotate(180)">'
        f'<text x="9" y="23" font-size="20" {NUM_FONT} fill="{pal["ink"]}">{num}</text>'
        + shape_placed(shape, 19, 41, 0.22)
        + "</g>"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}">'
        f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>'
        + shape_placed(shape, CARD_W / 2, CARD_H / 2, 1.0)
        + idx + "</svg>"
    )


def script_lines(pal, size=34, cx=CARD_W / 2, cy=CARD_H / 2):
    return (
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="{size}" '
        f'{SCRIPT_FONT} fill="{pal["red"]}">whot</text>'
        f'<g transform="translate({2 * cx},{2 * cy}) rotate(180)">'
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="{size}" '
        f'{SCRIPT_FONT} fill="{pal["red"]}">whot</text></g>'
    )


def whot_svg(pal):
    idx = (
        f'<text x="9" y="23" font-size="20" {NUM_FONT} fill="{pal["ink"]}">20</text>'
        f'<g transform="translate({CARD_W},{CARD_H}) rotate(180)">'
        f'<text x="9" y="23" font-size="20" {NUM_FONT} fill="{pal["ink"]}">20</text></g>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}">'
        f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>'
        + script_lines(pal) + idx + "</svg>"
    )


def back_svg(pal):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}">'
        f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>'
        + script_lines(pal) + "</svg>"
    )


def icon_svg(suit, pal):
    shape = SHAPES[suit].format(red=pal["red"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ICON_W}" height="{ICON_H}" '
        f'viewBox="0 0 {ICON_W} {ICON_H}">'
        f'<rect x="0.5" y="0.5" width="{ICON_W - 1}" height="{ICON_H - 1}" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>'
        + shape_placed(shape, ICON_W / 2, ICON_H / 2, 0.42)
        + "</svg>"
    )


def build_jobs():
    """Return ordered [(svg_text, out_png_path, w, h)] plus svg source saves."""
    jobs, sources = [], []
    for theme in ("light", "dark"):
        pal = PALETTES[theme]
        svg_root = os.path.join(HERE, "svg", theme)
        png_root = ROOT if theme == "light" else ROOT  # outputs below
        for suit, numbers in NUMBERS.items():
            for n in numbers:
                name = f"{suit}_{n}.png"
                svg = card_svg(suit, n, pal)
                sources.append((os.path.join(svg_root, suit, name[:-4] + ".svg"), svg))
                out = os.path.join(png_root,
                                   "DIY" if theme == "light" else "DIY-dark",
                                   suit, name)
                jobs.append((svg, out, CARD_W, CARD_H))
        for i in range(1, WHOT_COUNT + 1):
            svg = whot_svg(pal)
            sources.append((os.path.join(svg_root, "Whot", f"Whot_{i}.svg"), svg))
            out = os.path.join(png_root,
                               "DIY" if theme == "light" else "DIY-dark",
                               "Whot", f"Whot_{i}.png")
            jobs.append((svg, out, CARD_W, CARD_H))
        for i in range(1, MISC_COUNT + 1):
            svg = back_svg(pal)
            sources.append((os.path.join(svg_root, "Misc", f"Misc_whot{i}.svg"), svg))
            out = os.path.join(png_root,
                               "DIY" if theme == "light" else "DIY-dark",
                               "Misc", f"Misc_whot{i}.png")
            jobs.append((svg, out, CARD_W, CARD_H))
        for icon in ICON_SUITS:
            svg = icon_svg(SUIT_OF_ICON[icon], pal)
            sources.append((os.path.join(svg_root, "icons", f"{icon}.svg"), svg))
            out = os.path.join(png_root,
                               "cards" if theme == "light" else "cards-dark",
                               f"{icon}.png")
            jobs.append((svg, out, ICON_W, ICON_H))
    return jobs, sources


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    raise SystemExit("Chrome not found; edit CHROME_CANDIDATES in render_cards.py")


def sheet_html(cells, cols):
    parts = ['<html><head><meta charset="utf-8"></head>'
             '<body style="margin:0;padding:0;line-height:0;">']
    parts.extend(cells)
    parts.append("</body></html>")
    return "".join(parts)


def render_sheet(chrome, cells, cols, cell_w, cell_h, shot_path):
    rows = (len(cells) + cols - 1) // cols
    html_path = shot_path + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(sheet_html(cells, cols))
    # Pad last row so the sheet is a full grid (keeps slicing trivial).
    vw, vh = cols * cell_w, rows * cell_h
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=1",
         f"--screenshot={shot_path}", f"--window-size={vw},{vh}",
         "file:///" + html_path.replace("\\", "/")],
        check=True, capture_output=True)
    img = Image.open(shot_path)
    if img.size != (vw, vh):
        raise SystemExit(f"unexpected sheet size {img.size}, wanted {(vw, vh)}")
    return img, rows


def main():
    jobs, sources = build_jobs()
    for path, svg in sources:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"wrote {len(sources)} svg sources")

    chrome = find_chrome()
    for theme in ("light", "dark"):
        # Split card-size cells from icon-size cells (uniform slicing).
        for (w, h) in ((CARD_W, CARD_H), (ICON_W, ICON_H)):
            cells = [(svg, out) for (svg, out, cw, ch) in jobs
                     if cw == w and ch == h
                     and (theme == "dark") == ("-dark" in out)]
            if not cells:
                continue
            cols = 8 if w == CARD_W else 5
            svgs = [svg for (svg, _) in cells]
            shot = os.path.join(HERE, f"sheet-{theme}-{w}x{h}.png")
            img, rows = render_sheet(chrome, svgs, cols, w, h, shot)
            for i, (_, out) in enumerate(cells):
                r, c = divmod(i, cols)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                img.crop((c * w, r * h, (c + 1) * w, (r + 1) * h)).save(out)
            os.remove(shot)
            os.remove(shot + ".html")
            print(f"{theme} {w}x{h}: {len(cells)} files "
                  f"({'DIY-dark' if theme == 'dark' and w == CARD_W else ''})")
    print("done")


if __name__ == "__main__":
    main()
