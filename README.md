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
* pip install customtkinter CTkMessagebox tkthread icecream
* python3 Whot.pyw

# Notes
* `customMenu.py` is vendored from https://github.com/ChromeGenesis/customtkinter-menu
  (dark/light-mode aware CTk menu bar). The game menu follows the Appearance setting.
* `config.json` is created on first run (name/theme/appearance/mode) and is not tracked.

# Card art
* Original vector sources live in `assets/svg/<light|dark>/` (our own drawing,
  no third-party art).
* `python assets/render_cards.py` re-renders every PNG (`DIY/`, `DIY-dark/`,
  `cards/`, `cards-dark/`) via headless Chrome. Needs Chrome + Pillow, dev
  machine only — the game itself loads plain PNGs and needs neither.
