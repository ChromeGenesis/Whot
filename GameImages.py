import tkinter as tk
import os

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Card-art palette (all 71 asset files use exactly these 3 colors):
#   background (254, 254, 254), suit red (237, 50, 55), ink (55, 52, 53)
_BG = (254, 254, 254)
_RED = (237, 50, 55)

# Dark-theme replacements. Card bg sits between the window bg (#252526)
# and the red suits so faces stay readable in dark mode.
_DARK_BG = (59, 59, 61)
_DARK_INK = (237, 237, 237)


def _to_dark(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
    """Map one light-theme pixel to its dark-theme equivalent.

    Rules are luminance/saturation based (not exact-match) so any
    anti-aliased edge pixels between the 3 palette colors follow along.
    """
    r, g, b = pixel
    if min(r, g, b) > 180:
        return _DARK_BG
    if r - g > 60 and r - b > 60:
        return pixel  # suit red pops on dark as-is
    # dark ink / anything else -> light ink
    lum = (r + g + b) // 3
    if lum > 200:
        return _DARK_BG
    if lum < 90:
        return _DARK_INK
    # mid-tone edge pixel: blend toward ink so shapes keep their outline
    t = (lum - 90) / 110
    return tuple(
        int(_DARK_INK[c] + t * (_DARK_BG[c] - _DARK_INK[c])) for c in range(3)
    )


class images:
    cards_dark = False  # theme the currently loaded images were built for

    def __init__(self):
        self._load_images()

    def _load_images(self):
        image_dir = os.path.join(os.getcwd(), "DIY")
        card_dir = os.path.join(os.getcwd(), "cards")

        circle = self.create_image_data(os.path.join(image_dir, "Circle"))
        triangle = self.create_image_data(os.path.join(image_dir, "Triangle"))
        square = self.create_image_data(os.path.join(image_dir, "Square"))
        cross = self.create_image_data(os.path.join(image_dir, "Cross"))
        star = self.create_image_data(os.path.join(image_dir, "Star"))

        whot_dir = os.path.join(image_dir, "Whot")
        whot_dir_list = os.listdir(whot_dir)
        whot = [
            (
                self.load_image(os.path.join(whot_dir, filename)),
                (os.path.basename(whot_dir), 20)
            )
            for filename in whot_dir_list
        ]

        self._cross_icon = self.load_image(os.path.join(card_dir, "cross.png"))
        self._circle_icon = self.load_image(os.path.join(card_dir, "circle.png"))
        self._triangle_icon = self.load_image(os.path.join(card_dir, "triangle.png"))
        self._square_icon = self.load_image(os.path.join(card_dir, "square.png"))
        self._star_icon = self.load_image(os.path.join(card_dir, "star.png"))

        misc_dir = os.path.join(image_dir, "Misc")
        self._misc_whot = self.load_image(os.path.join(misc_dir, "Misc_whot1.png"))
        self._misc_whot1 = self.load_image(os.path.join(misc_dir, "Misc_whot2.png"))

        self._DepotMarket = circle + triangle + square + cross + star + whot

    def load_image(self, path: str) -> tk.PhotoImage:
        'Load one asset, themed for the current cards_dark flag (PIL required for dark).'
        if images.cards_dark and _HAS_PIL:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.putdata([_to_dark(px) for px in im.getdata()])
                return ImageTk.PhotoImage(im)
        return tk.PhotoImage(file=path)

    def apply_theme(self, dark: bool):
        """Rebuild all images for the given theme.

        Must be called on the engine instance BEFORE InitDepot(), since
        InitDepot copies _DepotMarket references into the card pool.
        Safe to call on GUI instances too (only images are rebuilt).
        """
        images.cards_dark = bool(dark) and _HAS_PIL
        self._load_images()

    def create_image_data(self, directory: str) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        dir_list = os.listdir(directory)
        return [
            (
                self.load_image(os.path.join(directory, filename)),
                (os.path.basename(directory), int(filename.split('_')[-1].split('.')[0]))
            )
            for filename in dir_list
        ]

if __name__ == '__main__':
    root = tk.Tk()
    app = images()
