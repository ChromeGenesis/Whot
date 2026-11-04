import tkinter as tk
import os


class images:
    """Card art loader.

    Art is authored as original vectors in assets/svg/<theme>/ and rendered
    to PNG trees by assets/render_cards.py (headless Chrome, dev machine).
    The game just picks a pre-rendered tree per appearance mode, so no
    imaging libraries are needed at runtime:

        DIY/  cards/          light theme
        DIY-dark/  cards-dark/  dark theme
    """

    cards_dark = False  # theme the currently loaded images were built for

    def __init__(self):
        self._load_images()

    def _load_images(self):
        theme = "dark" if images.cards_dark else "light"
        image_dir = os.path.join(os.getcwd(), "DIY" if theme == "light" else "DIY-dark")
        card_dir = os.path.join(os.getcwd(), "cards" if theme == "light" else "cards-dark")

        circle = self.create_image_data(os.path.join(image_dir, "Circle"))
        triangle = self.create_image_data(os.path.join(image_dir, "Triangle"))
        square = self.create_image_data(os.path.join(image_dir, "Square"))
        cross = self.create_image_data(os.path.join(image_dir, "Cross"))
        star = self.create_image_data(os.path.join(image_dir, "Star"))

        whot_dir = os.path.join(image_dir, "Whot")
        whot_dir_list = os.listdir(whot_dir)
        whot = [
            (
                tk.PhotoImage(file=os.path.join(whot_dir, filename)),
                (os.path.basename(whot_dir), 20)
            )
            for filename in whot_dir_list
        ]

        self._cross_icon = tk.PhotoImage(file=os.path.join(card_dir, "cross.png"))
        self._circle_icon = tk.PhotoImage(file=os.path.join(card_dir, "circle.png"))
        self._triangle_icon = tk.PhotoImage(file=os.path.join(card_dir, "triangle.png"))
        self._square_icon = tk.PhotoImage(file=os.path.join(card_dir, "square.png"))
        self._star_icon = tk.PhotoImage(file=os.path.join(card_dir, "star.png"))

        misc_dir = os.path.join(image_dir, "Misc")
        self._misc_whot = tk.PhotoImage(file=os.path.join(misc_dir, "Misc_whot1.png"))
        self._misc_whot1 = tk.PhotoImage(file=os.path.join(misc_dir, "Misc_whot2.png"))

        self._DepotMarket = circle + triangle + square + cross + star + whot

    def apply_theme(self, dark: bool):
        """Rebuild all images for the given theme.

        Must be called on the engine instance BEFORE InitDepot(), since
        InitDepot copies _DepotMarket references into the card pool.
        Safe to call on GUI instances too (only images are rebuilt).
        """
        images.cards_dark = bool(dark)
        self._load_images()

    def create_image_data(self, directory: str) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        dir_list = os.listdir(directory)
        return [
            (
                tk.PhotoImage(file=os.path.join(directory, filename)),
                (os.path.basename(directory), int(filename.split('_')[-1].split('.')[0]))
            )
            for filename in dir_list
        ]

if __name__ == '__main__':
    root = tk.Tk()
    app = images()
