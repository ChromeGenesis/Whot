"""Stamp out every card SVG from the single master template in CardArt.

Replaces hand-editing ~200 SVG files. Pure string substitution, no Chrome,
no Pillow, millisecond-fast:

    python assets/build_cards_svg.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import CardArt

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    count = 0
    for theme in ("light", "dark"):
        root = os.path.join(HERE, "svg", theme)
        for suit, numbers in CardArt.NUMBERS.items():
            d = os.path.join(root, suit)
            os.makedirs(d, exist_ok=True)
            for n in numbers:
                with open(os.path.join(d, f"{suit}_{n}.svg"), "w",
                          encoding="utf-8") as f:
                    f.write(CardArt.card_svg(suit, n, theme))
                count += 1
        d = os.path.join(root, "Whot")
        os.makedirs(d, exist_ok=True)
        for i in range(1, CardArt.WHOT_COUNT + 1):
            with open(os.path.join(d, f"Whot_{i}.svg"), "w",
                      encoding="utf-8") as f:
                f.write(CardArt.whot_svg(theme))
            count += 1
        d = os.path.join(root, "Misc")
        os.makedirs(d, exist_ok=True)
        for i in range(1, CardArt.MISC_COUNT + 1):
            with open(os.path.join(d, f"Misc_whot{i}.svg"), "w",
                      encoding="utf-8") as f:
                f.write(CardArt.back_svg(theme))
            count += 1
        d = os.path.join(root, "icons")
        os.makedirs(d, exist_ok=True)
        for icon in CardArt.ICON_SUITS:
            with open(os.path.join(d, f"{icon}.svg"), "w",
                      encoding="utf-8") as f:
                f.write(CardArt.icon_svg(icon, theme))
            count += 1
    print(f"wrote {count} svg sources")


if __name__ == "__main__":
    main()
