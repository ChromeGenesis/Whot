import os
import tkinter as tk

from PIL import ImageTk

import CardArt


class images:
    """Card art loader (SVG-first, zero image files).

    Art is specified once in CardArt.py from the master SVG frame
    (186.3 x 255.5, rounded card + center shape + corner minis + numbers).
    Cards are rasterized in memory with Pillow and wrapped in PhotoImages --
    Tkinter cannot display SVG natively and this machine has no working SVG
    rasterizer (no cairo), so in-memory Pillow raster is the fastest
    dependency-free path. No DIY/*/cards* PNG trees are read.

    Performance: every theme is built ONCE per process into a shared
    bundle (`_CACHE`). The GUI plus all four engine instances used to
    each rasterize ~60 cards (~400ms a pop, ~2s of startup); now the
    second and later instances just borrow references, and an appearance
    flip is a pointer swap instead of a ~400ms GUI-thread rebuild
    (that rebuild freeze was the theme-switch flicker).

    Public surface is unchanged: _DepotMarket, suit icons, card backs,
    cards_dark, apply_theme(), create_image_data().
    """

    cards_dark = False  # theme the currently loaded images were built for
    _CACHE: dict[tuple[str, int], dict] = {}

    def __init__(self):
        self._use_theme("dark" if images.cards_dark else "light")

    @classmethod
    def _cache_key(cls, theme: str) -> tuple[str, int]:
        # One bundle per (theme, Tk interpreter): PhotoImages belong to the
        # interp that created them and are invisible to any other.
        root = tk._get_default_root()
        return (theme, id(root))

    @classmethod
    def _bundle(cls, theme: str) -> dict:
        """Return the shared photo bundle for a theme, building it once."""
        key = cls._cache_key(theme)
        bundle = cls._CACHE.get(key)
        if bundle is None:
            bundle = cls._build(theme)
            cls._CACHE[key] = bundle
        return bundle

    @classmethod
    def _build(cls, theme: str) -> dict:
        photos: list = []

        def photo(pil_image):
            p = ImageTk.PhotoImage(pil_image)
            photos.append(p)  # cache owns the refs; instances just borrow
            return p

        depot = []
        for suit, numbers in CardArt.NUMBERS.items():
            for n in numbers:
                depot.append(
                    (photo(CardArt.render_card(suit, n, theme)), (suit, n)))
        for _ in range(CardArt.WHOT_COUNT):
            depot.append(
                (photo(CardArt.render_whot(theme)), ("Whot", 20)))
        icons = {s: photo(CardArt.render_icon(s, theme))
                 for s in CardArt.ICON_SUITS}
        misc = photo(CardArt.render_back(theme))
        misc1 = photo(CardArt.render_back(theme))
        return {"photos": photos, "depot": depot,
                "icons": icons, "misc": misc, "misc1": misc1}

    def _use_theme(self, theme: str):
        bundle = self._bundle(theme)
        self._DepotMarket = bundle["depot"]
        icons = bundle["icons"]
        self._cross_icon = icons["cross"]
        self._circle_icon = icons["circle"]
        self._triangle_icon = icons["triangle"]
        self._square_icon = icons["square"]
        self._star_icon = icons["star"]
        self._misc_whot = bundle["misc"]
        self._misc_whot1 = bundle["misc1"]

    def apply_theme(self, dark: bool):
        """Point this instance at the theme bundle (builds once, else swap).

        Must be called on the engine instance BEFORE InitDepot(), since
        InitDepot copies _DepotMarket references into the card pool.
        Safe to call on GUI instances too (only references are repointed).
        """
        images.cards_dark = bool(dark)
        self._use_theme("dark" if images.cards_dark else "light")

    def create_image_data(
        self, directory: str
    ) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        """Build (PhotoImage, (suit, number)) pairs for a suit.

        Accepts either a suit name ('Circle') or a directory path ending in
        the suit name (legacy callers passed DIY/... paths). Photos are
        shared bundle references, not new rasters.
        """
        suit = os.path.basename(os.path.normpath(directory)).capitalize()
        theme = "dark" if images.cards_dark else "light"
        return [entry for entry in self._bundle(theme)["depot"]
                if entry[1][0] == suit or (suit == "Whot"
                                            and entry[1] == ("Whot", 20))]


if __name__ == '__main__':
    root = tk.Tk()
    app = images()
    print(len(app._DepotMarket), "cards loaded")
