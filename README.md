# Whot
CARD GAME BY GENESIS

# Manual
First time?  No worries, just check the game manual
Located in the menu for how to play and other rules

# Features
* Added new themes 
* Added name entry for customization
* Upgraded look and feel
* Added multiplayer

# Usage (Mainly for windows | linux has some issues with the GUI)
* git clone https://github.com/ChromeGenesis/Whot/
* cd Whot
* pip install customtkinter CTkMessagebox pillow
* python3 Whot.pyw

# Notes
* `customMenu.py` is vendored from https://github.com/ChromeGenesis/customtkinter-menu
  (dark/light-mode aware CTk menu bar). The game menu follows the Appearance setting.
* `config.json` is created on first run (name/theme/appearance/mode) and is not tracked.

# Card art
* Single vector spec in `CardArt.py` (master SVG frame + suit/number/palette
  substitution). Runtime cards are rasterized in memory with Pillow --
  Tkinter cannot display SVG and no cairo is needed.
* `python assets/build_cards_svg.py` stamps the committed vector sources in
  `assets/svg/<light|dark>/` from that same spec (fast, no Chrome).
* The game rasterizes cards in memory at startup, so it needs Pillow
  at runtime (no image files, no Chrome, no cairo).
