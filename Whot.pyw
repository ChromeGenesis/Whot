import tkinter as tk
import customtkinter as ctk
import CTkMessagebox
import customMenu
from manual import manual
from GameImages import images
import Main
import multiplayer
from random import choice
import time, threading, queue, os
import json
from typing import Literal, Callable
import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s\n', filename='whot.log')#, datefmt='%H:%M:%S')
logging.basicConfig(level=logging.DEBUG, format="%(message)s\n", filename="whot.log")


class Whot(images):
    """Naija Whot Game in Grand Style - By Genesis Chrome"""

    def __init__(self):
        self._root = ctk.CTk()
        # self._orig_size = '760x690+592+7' #'650x690+706+6'  # 760x690+592+7'
        self._root.geometry("650x715+706+6")
        self._root.minsize(610, 690)
        self._title = "Whot Game"
        self._root.title(self._title)
        self._root.wm_iconbitmap("genesis.ico")
        self._root.protocol("WM_DELETE_WINDOW", self.__exit)
        super().__init__()

        self.font_style = ("Comic Sans Ms bold", 17)
        self.smaller_font = (self.font_style[0], self.font_style[1] - 4)

        self._config_location = "./config.json"
        self._config: dict[str, str | bool | dict[str, str | int]] = {}
        self.load_config_file()
        # Card faces are drawn from the single vector spec in CardArt.py
        # (master SVG frame + Pillow in-memory raster, see
        # assets/build_cards_svg.py), so this just picks the theme palette.
        self.apply_theme(self._config.get("appearance", "dark") == "dark")

        self._playedcard_curr_xy: tuple[float, float] = (0, 0)
        self._animated_images: list[tuple[int, tuple[str, int]]] = []

        self._player2_frame = ctk.CTkScrollableFrame(
            self._root,
            orientation="horizontal",
        )
        self._player2_frame.place(
            relx=0.014, rely=0.640, relheight=0.292, relwidth=0.974
        )

        self._comp_frame = ctk.CTkScrollableFrame(
            self._root,
            orientation="horizontal",
        )
        self._comp_frame.place(relx=0.014, rely=0.082, relheight=0.281, relwidth=0.974)

        self._played_frame = ctk.CTkCanvas(
            self._root,
            highlightthickness=0,
        )

        self._played_frame.place(
            relx=0.014, rely=0.360, relheight=0.281, relwidth=0.974
        )

        self._played_frame.bind("<Configure>", self.rearrange_playedimages_onresize)
        ###################################################################
        # Main Initialisations
        ###################################################################
        self._whot = Main.Whot()
        self._whot.InitDepot()
        self._whot.shuffle_cards()
        self._whot.InitPlayerCards()
        self._computer = Main.Computer()
        self._player2 = Main.Player2()
        self._onlinep = Main.OnlinePlayer()
        self._whot.InitComputerCards()
        self._whot.InitPlayer2Cards()
        self._whot.NormCards()

        self._onlinePlayerActive = False
        self._onlineServer: multiplayer.Server = None
        self._onlineClient: multiplayer.Client = None

        self._server_choice = ""
        self._onlineNickname = ""
        self._connectionFailed = False

        # Async handshake state: workers never touch Tk, they just post a
        # result here; the main-thread watchdog (_mp_watch) runs it.
        self._mp_result = None
        self._mp_handshake_active = False

        self._onlinep_todo: dict[str, int | bool] = {
            "pick_two": 0,
            "general_market": 0,
            "hold_on": False,
            "suspension": False,
        }

        self._delay_multiplayer_for_animations = True
        self._delete_multiplayer_indicators = False
        ###################################################################

        ##################################################################
        # To Check who played last
        ##################################################################
        self.__check_p2_played = False
        self.__checkcomp_played = False
        self.__checkop_played = False
        ##################################################################

        ##################################################################
        # Check Pick two, General market and checkmate
        ##################################################################
        self.__check_gameover = False

        self._p2_picked_2_cards_count = 0
        self._p2_picked_1_card_count = 0

        self.COMP_PLAY_DELAY = 500
        self.INITIAL_COMP_PLAY_DELAY = 4700
        self.initialize_card_graphics()

        #####################################################################################
        # Menu
        #####################################################################################
        Menu = customMenu.Menu(self._root)

        gear_img = tk.PhotoImage(file="gear_small.png", height=30, width=30)

        about_menu = Menu.menu_bar(text="About", tearoff=0)
        about_menu.add_command(
            label="Manual", accelerator="Ctrl+M", compound="left", command=self.Manual
        )

        game_menu = Menu.menu_bar(text="Game", tearoff=0)
        game_menu.add_command(
            label="Restart Game",
            accelerator="Ctrl+R",
            compound="left",
            command=self.__restart,
        )

        settings_menu = Menu.menu_bar(text="Setting", tearoff=0)
        settings_menu.add_command(
            label="Settings",
            accelerator="Ctrl+S",
            compound="left",
            command=self.settings,
        )

        multiplayer_menu = Menu.menu_bar(text="Multiplayer", tearoff=0)
        multiplayer_menu.add_command(
            label="Multiplayer",
            accelerator="Ctrl+Shift+M",
            compound="left",
            command=self.start_multiplayer_server_client,
        )

        self._appearance_var = tk.StringVar(value=self._config["appearance"])
        appearance_menu = Menu.menu_bar(text="Appearance", tearoff=0)
        appearance_menu.add_radiobutton(
            label="Dark",
            variable=self._appearance_var,
            value="dark",
            command=self.set_appearance,
        )
        appearance_menu.add_radiobutton(
            label="light",
            variable=self._appearance_var,
            value="light",
            command=self.set_appearance,
        )
        ctk.AppearanceModeTracker().add(self.set_appearance)
        self.set_appearance()
        ################################################################################################################
        # Card Length Widgets
        ################################################################################################################
        self._comp_cards_left = ctk.CTkLabel(
            self._root,
            height=38,
            width=270,
            text=f"Number of computer cards: {len(self._computer.cards())}",
            font=self.font_style,
        )
        self._p2_cards_left = ctk.CTkLabel(
            self._root,
            height=38,
            width=230,
            text=f"Number of your cards: {len(self._player2.cards())}",
            font=self.font_style,
        )
        self._p2_cards_left.place(relx=0.0, rely=0.943)
        self._comp_cards_left.place(relx=0.0, rely=0.03)

        #################################################################################################################
        # Turn Indicators
        #################################################################################################################
        self._p2_turn_indicator = ctk.CTkLabel(
            self._root, height=38, width=159, text="Player", font=self.font_style
        )
        self._comp_turn_indicator = ctk.CTkLabel(
            self._root, height=38, width=159, text="Computer", font=self.font_style
        )
        self._p2_turn_indicator.place(relx=0.778, rely=0.942)
        self._comp_turn_indicator.place(relx=0.778, rely=0.03)

        ####################################################################################
        # Who Plays First and Name Entry Widget
        ####################################################################################
        who_plays_first = ("p2", "comp")
        self.set_player_turn(choice(who_plays_first))

        self._name_entry = ctk.CTkEntry(self._root)  # Entry for self.set_name()
        ####################################################################################
        # Show Setting At Startup Variables
        ####################################################################################
        self._game_started = False
        self._show_setting_at_startup = tk.BooleanVar()

        ##############################################################################################################
        # Theme and Difficulty Var Init
        ##############################################################################################################
        self._theme_var = tk.StringVar()
        self._difficulty_var = tk.StringVar()

        self._themes_dict = {
            "Chartreuse": "#7FFF00",
            "Bright Green": "#000fff000",
            "Royal Blue": "royal blue",
            "Dodger Blue": "dodger blue",
            "Aquamarine": "Aquamarine",
            "Default": "#d9d9d9",  # Light gray
            "Yellow": "yellow",
            "Magenta": "magenta",
            "Gold": "gold",
            "Red": "red",
            "Dark Violet": "dark violet",
            "Pink": "pink",
            "Black": "black",
            "Orange": "#FFA500",
            "Olive": "#808000",
        }

        config_theme = self._config.get("theme", "Default")
        self._theme_var.set(config_theme)
        self.set_theme()
        ####################################################################################
        # Update n Run
        ####################################################################################
        if self._config.get("show_setting"):
            self._root.after(1500, self.settings)
        self._difficulty_var.set(self._config.get("mode"))

        self._root.after(self.INITIAL_COMP_PLAY_DELAY, self.compPlayEngine)  # 5800
        self._root.after(
            1200,
            lambda: self.display_cards_animation(
                [self._player2_btns[i] for i in range(5)]
            ),
        )
        ##################################################################################
        # Binding's
        ##################################################################################
        self._root.after(6000, self.root_bindings)
        self.bind_right_left_keys_to_p2_scrollable_frame(0.1)
        ####################################################################################
        # END
        ####################################################################################

    def root_bindings(self):
        self._root.bind_all("<Control-m>", self.Manual)
        self._root.bind_all("<Control-r>", lambda event: self.__restart())
        self._root.bind("<Control-M>", self.start_multiplayer_server_client)
        self._root.bind("<Control-s>", self.settings)
        self.bind_return(method="mart")
        self._root.bind_all("<F11>", lambda event: self._root.state("zoomed"))
        self._root.bind_all("<Escape>", lambda event: self._root.state("normal"))

    def bind_return(self, method: Literal["mart", "pick_two", "pick_one"]) -> None:
        if method == "mart":
            self._root.bind("<Return>", lambda event: self.p2_mart(event=event))
        elif method == "pick_two":
            self._root.unbind("<Return>")
            self._root.bind(
                "<Return>", lambda event: self.check_p2_picked_two_cards(event=event)
            )
        elif method == "pick_one":
            self._root.unbind("<Return>")
            self._root.bind(
                "<Return>", lambda event: self.check_p2_picked_a_card(event=event)
            )

    def bind_right_left_keys_to_p2_scrollable_frame(self, X_INCREMENT=0.1):
        def scroll_right(event):
            x = self._player2_frame._parent_canvas.xview()[0]
            x += X_INCREMENT
            self._player2_frame._parent_canvas.xview_moveto(x)

        def scroll_left(event):
            x = self._player2_frame._parent_canvas.xview()[0]
            x -= X_INCREMENT
            self._player2_frame._parent_canvas.xview_moveto(x)

        self._player2_frame.bind_all("<Right>", scroll_right)
        self._player2_frame.bind_all("<Left>", scroll_left)

    def display_cards_animation(self, p2_btns: list[tk.Button]):
        preferred_labels = (
            self._onlinep_labels if self._onlinePlayerActive else self._computer_labels
        )

        self._root.after(
            3700, lambda: setattr(self, "_delay_multiplayer_for_animations", False)
        )

        [card.config(state="disabled") for card in p2_btns]

        btn_duration = 50
        for btn, column in zip(p2_btns, range(5), strict=True):
            self._root.after(
                btn_duration,
                lambda b=btn, c=column: b.grid(row=0, column=c, padx=6, pady=6),
            )
            btn_duration += 250

        self._root.after(1500, self.create_playedcard_image)

        lab_duration = 2000
        for lab_ref_num, column in zip(range(5), range(5)):
            self._root.after(
                lab_duration,
                lambda r=lab_ref_num, c=column: preferred_labels[r].grid(
                    row=0, column=c, padx=6, pady=6
                ),
            )
            lab_duration += 200

        for card in p2_btns:
            self._root.after(
                3500,
                lambda c=card: (
                    c.config(state="normal"),
                    self._market_btn.configure(state="normal"),
                ),
            )

    def load_config_file(self):
        if os.path.exists(self._config_location):
            try:
                with open(self._config_location, "r") as conf_file:
                    conf = json.load(conf_file)
                    self._config = conf or {}
            except (json.JSONDecodeError, UnicodeDecodeError, IOError) as e:
                print("Error with file:", e)
                self.message_box("File Error", f"Error With File\n{e}")
                self._create_new_config_file()
        else:
            self._create_new_config_file()

    def _create_new_config_file(self):
        """Creates a new config file if the original one has been deleted/Truncated"""
        self._config = {
            "name": "Genesis",
            "theme": "Default",
            "appearance": "dark",
            "mode": "easy",
            "show_setting": True,
            "multiplayer": {
                "host": "127.0.0.1",
                "port": 55555,
                "nickname": "Genesis",
                "server_choice": "start server",
            },
        }

        with open(self._config_location, "w") as config_file:
            json.dump(self._config, config_file, indent=4)
            print("In create new config file, config -->", self._config)

    def _write_config(
        self, data_type: str = None, data: str | bool = None, plain_save=False
    ):
        if not plain_save:
            self._config[data_type] = data

        with open(self._config_location, "w") as config_loc:
            json.dump(self._config, config_loc, indent=4)

    def message_box(
        self, title: str, message: str, icon="info", **kwargs
    ) -> CTkMessagebox.CTkMessagebox:
        """Creates a message box"""
        msg = CTkMessagebox.CTkMessagebox(
            self._root,
            width=270,
            title=title,
            message=message,
            icon=icon,
            justify="center",
            font=self.smaller_font,
            sound=True,
            **kwargs,
        )
        return msg

    def Manual(self, event=None):
        """See the Manual of the Game"""
        root = self.create_toplevel_at_center(width=650, height=420)
        root.title("<Manual>")
        root.transient(self._root)
        root.resizable(False, False)

        theme = self.get_actual_theme(for_text=True)
        text_box = ctk.CTkTextbox(
            root,
            width=650,
            height=420,
            wrap="word",
            font=self.font_style,
            text_color=theme,
        )
        text_box.insert(tk.INSERT, manual)
        text_box.configure(state="disabled")
        text_box.focus_set()
        text_box.grab_set()
        text_box.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)

    def set_appearance(self, theme_callback: str = None):
        theme = "#252526" if self._appearance_var.get() == "dark" else "#E9E9E9"
        ctk.set_appearance_mode(
            (theme_callback.lower() if theme_callback else None)
            or self._appearance_var.get()
        )
        self._played_frame.configure(background=theme)
        self._write_config("appearance", self._appearance_var.get())
        # Card faces retheme live now -- no restart needed.
        if theme_callback is None and (
            (self._appearance_var.get() == "dark") != images.cards_dark
        ):
            self.retheme_cards(self._appearance_var.get() == "dark")

    def gameover(self):
        """Freezes all buttons and stops the computer | player2 | onlinep from playing
        if any player's cards finish"""

        player2_cards = len(self._player2.cards())
        other_player_cards = (
            len(self._onlinep.cards())
            if self._onlinePlayerActive
            else len(self._computer.cards())
        )

        if player2_cards != 0 and other_player_cards != 0:
            return

        self.__check_p2_played = True
        self.__checkcomp_played = True
        self.__check_gameover = True
        self._root.unbind("<Return>")

        if player2_cards == 0:
            self.popup_message("Game Over", "You Are The Winner", duration=1500)
            if self._onlinePlayerActive and self.multiplayer_restart_game():
                return

        elif other_player_cards == 0:
            if self._onlinePlayerActive:  # A way to restart for OP
                self.popup_message(
                    "Game Over",
                    f"{self._onlineNickname or 'OnlinePlayer'} Is The Winner",
                    duration=1500,
                )
                if self.multiplayer_restart_game():
                    return
            else:
                self.popup_message("Game Over", "The Computer Is The Winner", 1500)

        for btn in self._depot_p2_btns:
            btn.configure(state="disabled")
        self._market_btn.configure(state="disabled")
        self._root.title(f"{self._title} - Game Over")
        self._root.after(200, self.__restart)

    def __restart(self, force=False):
        """Restart the Whot Game"""
        if self._onlinePlayerActive:
            if self._server_choice == "start server":
                self._onlineServer.shutdown()
            self._onlineClient.shutdown()

        if not force:
            ask = self.message_box(
                "Restart Game",
                "Do you want to restart the game?",
                icon="question",
                option_1="Cancel",
                option_2="No",
                option_3="Restart",
                option_focus=3,
            )
            if ask.get() == "Restart":
                self.reinitialize_cards(onlinePlayer=False)
            elif ask.get() == "No":
                self.__exit()
            elif ask.get() == "Cancel":
                pass
        else:
            self.reinitialize_cards(onlinePlayer=False, prev_onlinep=True)

    def __exit(self):
        if self._onlinePlayerActive:
            self._onlinePlayerActive = False
            if not self._connectionFailed:
                if self._server_choice == "start server":
                    self._onlineServer.shutdown()
                self._onlineClient.shutdown()

        self._root.after(500, self._whot_threads)

    def _whot_threads(self):
        """Return Active Threads"""
        self._root.quit()
        self._root.destroy()

        for thread in threading.enumerate():
            print(f"thread name and is alive --> {[thread.name, thread.is_alive()]}")
        return threading.enumerate()

    # ------------------------------------------------------------------------------------
    # SETTINGS
    # ------------------------------------------------------------------------------------
    def settings(self, event=None):
        """Settings for whot game"""
        top = self.create_toplevel_at_center(width=350, height=360)
        top.transient(self._root)
        top.title(f"{self._title} - Settings")
        top.resizable(False, False)

        root_tab = ctk.CTkTabview(top)

        root_tab.add("Themes")
        root_tab.add("Name")
        root_tab.add("Mode")

        self.choose_theme(root_tab.tab("Themes"), root=top)
        self.set_name(root_tab.tab("Name"))
        self.choose_difficulty_mode(root_tab.tab("Mode"))

        show_setting = ctk.CTkSwitch(
            top,
            height=31,
            text="Show Setttings at startup",
            variable=self._show_setting_at_startup,
            font=self.smaller_font,
            command=lambda: self._write_config(
                "show_setting", self._show_setting_at_startup.get()
            ),
        )
        disable_difficulty_modes = lambda: (
            setattr(self, "_game_started", True),
            top.destroy(),
            top.grab_release(),
        )
        self._show_setting_at_startup.set(self._config.get("show_setting"))
        ok_btn = ctk.CTkButton(
            top, height=25, width=96, text="Ok", command=disable_difficulty_modes
        )

        root_tab.place(relx=0.0, rely=0.0, relheight=0.909, relwidth=1.0)
        show_setting.place(relx=0.029, rely=0.923)
        ok_btn.place(relx=0.657, rely=0.923)
        top.protocol("WM_DELETE_WINDOW", disable_difficulty_modes)
        top.focus_set()
        top.grab_set()

    def choose_difficulty_mode(self, window: ctk.CTkFrame):
        """To choose the mode of the game, whether easy or hard"""

        hard_radbtn = ctk.CTkRadioButton(
            window,
            height=26,
            text="Hard",
            variable=self._difficulty_var,
            value="hard",
            font=self.smaller_font,
            command=lambda: self._write_config("mode", self._difficulty_var.get()),
        )
        medium_radbtn = ctk.CTkRadioButton(
            window,
            height=26,
            text="Medium",
            variable=self._difficulty_var,
            value="medium",
            font=self.smaller_font,
            command=lambda: self._write_config("mode", self._difficulty_var.get()),
        )
        easy_radbtn = ctk.CTkRadioButton(
            window,
            height=26,
            text="Easy",
            variable=self._difficulty_var,
            value="easy",
            font=self.smaller_font,
            command=lambda: self._write_config("mode", self._difficulty_var.get()),
        )

        hard_radbtn.place(relx=0.376, rely=0.268)
        medium_radbtn.place(relx=0.376, rely=0.435)
        easy_radbtn.place(relx=0.376, rely=0.602)

        ctk.CTkLabel(
            window,
            height=57,
            width=290,
            text="Choose Desired Mode",
            font=self.font_style,
        ).place(relx=0.07, rely=0.033)
        ctk.CTkLabel(
            window,
            height=26,
            width=180,
            text="(Can Only Be Set Once Per Game Session)",
            font=self.smaller_font,
        ).place(relx=0.135, rely=0.769)
        window.focus_set()

        if self._game_started:
            [
                rbtn.configure(state="disabled")
                for rbtn in [hard_radbtn, medium_radbtn, easy_radbtn]
            ]

    def create_toplevel_at_center(
        self, width: int, height: int, display_delay=300
    ) -> ctk.CTkToplevel:
        self._root.update()
        toplevel = ctk.CTkToplevel(self._root)
        toplevel.update_idletasks()
        toplevel.withdraw()

        root_width = self._root.winfo_width()
        root_height = self._root.winfo_height()
        x = self._root.winfo_x() + (root_width - width) // 2
        y = self._root.winfo_y() + (root_height - height) // 2
        toplevel.geometry(f"{width}x{height}+{x}+{y}")
        self._root.after(display_delay, toplevel.deiconify)
        self._root.after(200, toplevel.wm_iconbitmap, "genesis.ico")
        self._root.after(
            display_delay + 10, self.redraw_window_if_still_withdrawn, toplevel
        )

        return toplevel

    def redraw_window_if_still_withdrawn(self, toplevel: ctk.CTkToplevel):
        if not toplevel.winfo_exists():
            return
        if toplevel.state() == "withdrawn":
            toplevel.deiconify()
            # Only keep polling while it is still hidden; the old version
            # rescheduled unconditionally, i.e. a 100Hz busy-loop forever
            # per dialog created.
            self._root.after(10, self.redraw_window_if_still_withdrawn, toplevel)

    def get_actual_theme(self, for_text=False) -> str | tuple[str, str]:
        """
        Get the theme color used by the application.

        Args:
            for_text (bool): Whether the theme is for text or not.
            will return `(black, white)` if theme is `Default` and `for_text` is True.
        """
        theme = self._theme_var.get()
        if for_text and theme == "Default":
            return ("black", "white")
        return self._themes_dict[theme]

    def choose_theme(self, window: ctk.CTkFrame, root: ctk.CTkToplevel):
        """For choosing desired theme from the themes list"""

        window = ctk.CTkScrollableFrame(window)
        window.place(relx=0.0, rely=0.0, relheight=0.997, relwidth=0.994)

        ctk.CTkLabel(
            window, height=39, width=280, text="Select Theme:", font=self.font_style
        ).grid(row=0, column=0, columnspan=2, padx=(25, 0))

        theme_radbtns = []
        num_per_row = 2
        # padx, pady = 19, 10
        padx, pady = 20, 8

        for o, i in enumerate(self._themes_dict.keys()):
            rbtn = ctk.CTkRadioButton(
                window,
                text=i.title(),
                variable=self._theme_var,
                value=i,
                font=self.smaller_font,
                command=self.set_theme,
            )
            rbtn.grid(
                row=(o // num_per_row) + 1,
                column=o % num_per_row,
                padx=padx,
                pady=pady,
                sticky="w",
            )
            theme_radbtns.append(rbtn)

        root.bind("<Down>", lambda event: self.scroll_theme("down"))
        root.bind("<Up>", lambda event: self.scroll_theme("up"))

    def scroll_theme(self, action: Literal["down", "up"]):
        value = self._theme_var.get()
        theme_keys = list(self._themes_dict.keys())
        current_index = theme_keys.index(value)

        if action == "down":
            next_index = (current_index + 1) % len(theme_keys)
            next_theme = theme_keys[next_index]
            self._theme_var.set(next_theme)
            self.set_theme()

        if action == "up":
            prev_index = (current_index - 1) % len(theme_keys)
            prev_theme = theme_keys[prev_index]
            self._theme_var.set(prev_theme)
            self.set_theme()

    def _card_base_bg(self) -> str:
        """Neutral backdrop behind the transparent card corners.

        Must match the appearance background (see set_appearance), never
        the accent theme color, or it bleeds through the corners. Also
        used as the button press color so clicks don't flash white.
        """
        return (
            "#252526" if self._config.get("appearance", "dark") == "dark"
            else "#E9E9E9"
        )

    def set_theme(self):
        preferred_depot_labels = (
            self._depot_onlinep_labels
            if self._onlinePlayerActive
            else self._depot_comp_labels
        )
        color = self._theme_var.get()

        if color not in self._themes_dict:
            self._write_config("theme", "Default")
            return

        theme_color = self.get_actual_theme()

        try:
            # Card widgets sit directly behind the transparent card corners,
            # so they take the neutral appearance background. The accent
            # theme color would bleed through the corners (it stays on
            # text accents only).
            appearance_bg = self._card_base_bg()
            for btn_lab in preferred_depot_labels + self._depot_p2_btns:
                btn_lab.configure(bg=appearance_bg)
                if isinstance(btn_lab, tk.Button):
                    btn_lab.configure(activebackground=appearance_bg)
            self._market_btn.configure(bg=appearance_bg,
                                       activebackground=appearance_bg)
            self._comp_cards_left.configure(text_color=theme_color)
            self._p2_cards_left.configure(text_color=theme_color)

            text_theme_color = self.get_actual_theme(for_text=True)
            self._comp_cards_left.configure(text_color=text_theme_color)
            self._p2_cards_left.configure(text_color=text_theme_color)

            self._write_config("theme", color)
            self._name_entry.configure(text_color=text_theme_color)
        except tk.TclError as e:
            print(e)

    def retheme_cards(self, dark: bool):
        """Rebuild card art for an appearance flip without restarting.

        Swaps the PhotoImage inside every live pile (depot, both hands,
        played cards, widget references) by (suit, number) key, then
        refreshes all card widgets and played-canvas items. Game logic
        only ever compares the (suit, number) half of each tuple, so
        play validity is untouched.
        """
        if dark == images.cards_dark:
            return
        piles = [Main.Whot.Cards, self._whot.PlayedCards()]
        for name in ("card1", "card2"):
            hand = getattr(Main, name, None)
            if hand is not None:
                piles.append(hand)

        old_whots = [photo for pile in piles for photo, key in pile
                     if key[0] == "Whot"]

        self.apply_theme(dark)  # rebuilds _DepotMarket/icons/backs, sets flag

        new_by_key = {}
        new_whots = []
        for photo, key in self._DepotMarket:
            if key[0] == "Whot":
                new_whots.append(photo)
            else:
                new_by_key[key] = photo
        whot_map = dict(zip([id(p) for p in old_whots], new_whots))

        def swap(card):
            photo, key = card
            if key[0] == "Whot":
                return (whot_map.get(id(photo), photo), key)
            return (new_by_key.get(key, photo), key)

        for pile in piles:
            pile[:] = [swap(card) for card in pile]
        for ref in self._btn_reference + self._label_reference:
            ref[:] = [swap(card) for card in ref]

        appearance_bg = self._card_base_bg()
        for i, ref in enumerate(self._btn_reference):
            if i not in self._player2_btns:
                continue
            btn = self._player2_btns[i]
            # Backdrop first: empty slots keep no image, but their
            # corners must already match or the next card dealt here
            # arrives with stale-theme corners.
            btn.configure(bg=appearance_bg, activebackground=appearance_bg)
            if ref:
                btn.configure(image=ref[0][0])
        for attr in ("_computer_labels", "_onlinep_labels"):
            for lab in getattr(self, attr, {}).values():
                lab.configure(image=self._misc_whot1, bg=appearance_bg)
        self._market_btn.configure(image=self._misc_whot, bg=appearance_bg,
                                   activebackground=appearance_bg)
        # Canvas items carry their own (suit, number) key, so each one is
        # remapped exactly -- no positional zip that drifts when items and
        # the played pile get out of step.
        whot_photos = iter(new_whots)
        for item, key in self._animated_images:
            if key[0] == "Whot":
                photo = next(whot_photos, None)
            else:
                photo = new_by_key.get(key)
            if photo is not None:
                self._played_frame.itemconfig(item, image=photo)

    def popup_message(
        self, title: str, text: str, duration: int = 900, wraplength: int = 140
    ) -> None:
        """Displays popup message containing information for 1 sec approx,
        (or the `duration` arg specification)"""
        top = self.create_toplevel_at_center(width=250, height=50, display_delay=150)
        top.transient(self._root)
        top.title(title.upper())
        top.resizable(False, False)

        theme = self.get_actual_theme(for_text=True)

        ctk.CTkLabel(
            top,
            text=text,
            text_color=theme,
            font=self.font_style,
            padx=20,
            pady=20,
            wraplength=wraplength,
        ).pack(fill="both", expand=True)

        top.focus_set()
        # top.grab_set()
        top.bell()  # TODO
        top.after(duration, top.destroy)

    def set_name(self, window: ctk.CTkFrame):
        """Gets desired name from player"""
        theme = self.get_actual_theme(for_text=True)
        former_name = self._config.get("name")
        entry_var = tk.StringVar(value=former_name)

        name_label = ctk.CTkLabel(
            window,
            height=57,
            width=225,
            text="Enter Desired Name:",
            font=self.font_style,
        )
        name_label.place(relx=0.170, rely=0.067)

        self._name_entry = ctk.CTkEntry(
            window,
            textvariable=entry_var,
            font=self.font_style,
            text_color=theme,
            justify="center",
        )
        self._name_entry.place(relx=0.173, rely=0.334, relheight=0.104, relwidth=0.653)

        save_button = ctk.CTkButton(
            window,
            height=35,
            width=96,
            text="Save",
            font=self.font_style,
            command=lambda: self.save_name_cmd(entry_var),
        )
        save_button.place(relx=0.347, rely=0.669)

    def save_name_cmd(self, name: tk.StringVar):
        """Sets (Registers) the desired name to the configuration file"""
        name = name.get()
        if name:
            self._write_config("name", name)
            self.update_turn_indicator()

    def set_player_turn(self, player: Literal["comp", "p2", "op"]):
        """Sets player's turn"""

        if player == "comp":
            self.__checkcomp_played = False
            self.__check_p2_played = True

        elif player == "p2":
            self.__check_p2_played = False
            if not self._onlinePlayerActive:
                self.__checkcomp_played = True
            else:
                self.__checkop_played = True

        elif player == "op":
            self.__checkop_played = False
            self.__check_p2_played = True

        self.update_turn_indicator()

    def get_player_turn(self, player: Literal["comp", "p2", "op"]) -> bool:
        """Return bool value for the valid player to play first or next"""
        if player == "comp":
            return self.__check_p2_played

        elif player == "p2":
            if self._onlinePlayerActive:
                return self.__checkop_played
            return self.__checkcomp_played

        elif player == "op":
            return self.__check_p2_played

        return False

    def update_turn_indicator(self):
        p2_turn = self.get_player_turn("p2")
        comp_turn = self.get_player_turn("comp")
        op_turn = self.get_player_turn("op")

        if p2_turn and not comp_turn:
            self._p2_turn_indicator.configure(text_color="#000fff000")
            self._comp_turn_indicator.configure(text_color="red")

        elif comp_turn and not p2_turn and not self._onlinePlayerActive:
            self._p2_turn_indicator.configure(text_color="red")
            self._comp_turn_indicator.configure(text_color="#000fff000")

        # since its op's turn, we'll use comp's widgets to display the turn indicator
        elif op_turn and not p2_turn and self._onlinePlayerActive:
            self._p2_turn_indicator.configure(text_color="red")
            self._comp_turn_indicator.configure(text_color="#000fff000")

        # Set names
        p2_name = self._config.get("name")
        self._p2_turn_indicator.configure(text=p2_name)
        if self._onlinePlayerActive:
            op_name = self._onlineNickname if self._onlineNickname else "OnlinePlayer"
            self._comp_turn_indicator.configure(text=op_name)
        else:
            self._comp_turn_indicator.configure(text="Computer")

    def display_number_of_cards(
        self, player: Literal["computer", "player2", "onlinep"]
    ):
        """Display number of cards left/remaining for the player"""
        if player == "computer":
            no_of_cards = len(self._computer.cards())
            text = (
                "Last Card..."
                if no_of_cards == 1
                else f"Number of computer cards : {no_of_cards}"
            )
            self._comp_cards_left.configure(text=text)

        elif player == "player2":
            no_of_cards = len(self._player2.cards())
            text = (
                "Last Card..."
                if no_of_cards == 1
                else f"Number of your cards : {no_of_cards}"
            )
            self._p2_cards_left.configure(text=text)

        elif player == "onlinep":
            no_of_cards = len(self._onlinep.cards())
            if self._onlineNickname and self._onlinePlayerActive:
                text = (
                    "Last Card..."
                    if no_of_cards == 1
                    else f"Number of {self._onlineNickname}'s cards : {no_of_cards}"
                )
            else:
                text = (
                    "Last Card..."
                    if no_of_cards == 1
                    else f"Number of your cards : {no_of_cards}"
                )
            self._comp_cards_left.configure(text=text)

    def repopulate_containers(self, onlinePlayer=False):
        """Repopulates by appending one more container (list) to the Button | Label references and
        one more Button | Label to the depots after the reference containers have all been filled up
        """

        used_p2_containers = [ref for ref in self._btn_reference if ref]
        used_comp_containers = [ref for ref in self._label_reference if ref]

        p2_full = len(used_p2_containers) == len(self._btn_reference)
        comp_full = len(used_comp_containers) == len(self._label_reference)

        if not p2_full and not comp_full:  # Empty containers present: all good
            return

        # No empty containers: have to add some
        self._btn_reference.append([])
        self._label_reference.append([])

        self._depot_p2_btns.append(
            tk.Button(self._player2_frame, bd=0, highlightthickness=0,
                      relief="flat",
                      activebackground=self._card_base_bg())
        )
        self._player2_btns[max(self._player2_btns) + 1] = self._depot_p2_btns[-1]

        if not onlinePlayer:
            self._depot_comp_labels.append(
                tk.Label(self._comp_frame, bd=0, highlightthickness=0,
                         relief="flat")
            )
            self._computer_labels[
                max(self._computer_labels) + 1
            ] = self._depot_comp_labels[-1]
        else:
            self._depot_onlinep_labels.append(
                tk.Label(self._comp_frame, bd=0, highlightthickness=0,
                         relief="flat")
            )
            self._onlinep_labels[
                max(self._onlinep_labels) + 1
            ] = self._depot_onlinep_labels[-1]
        self.set_theme()  # Sets the theme for the newly added widgets

    # ---------------------------------------------------------------------------------
    # POWERUPS
    # ---------------------------------------------------------------------------------
    def pick_two(self, player: Literal["comp", "p2", "op"]):
        """Makes Player Pick two cards from the mart"""

        if player == "comp":
            if self._player2.powerup_cards[2]:
                self.set_player_turn("comp")

                def comp_pick_two_animation(count: int):
                    if count < 2:
                        self.set_player_turn("comp")
                        self.apply_difficulty()
                        self._root.after(
                            self.COMP_PLAY_DELAY, comp_pick_two_animation, count + 1
                        )

                comp_pick_two_animation(0)

                self._player2.powerup_cards[2] = False
                self.set_player_turn("p2")
            return

        elif player == "op":  # OP
            if self._player2.powerup_cards[2]:
                self.set_player_turn("op")
                self._onlinep_todo["pick_two"] = 2
                self._player2.powerup_cards[2] = False
                return

        elif player == "p2":
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[2]:
                print("\nPICK TWO")
                self.popup_message("Pick Two", "Pick two cards from the mart")
                self._root.title(f"{self._title} - PICK TWO")
                [btn.config(state="disabled") for btn in self._depot_p2_btns]
                self._market_btn.configure(command=self.check_p2_picked_two_cards)
                self.bind_return(method="pick_two")
                powerup[2] = False

    def go_gen_mart(self, player: Literal["p2", "comp", "op"]):
        """Makes Player go to general market"""
        logging.debug(f"GENERAL MARKET - {player}")

        if player == "comp":
            if self.get_player_turn("comp") and self._player2.powerup_cards[14]:
                print("Computer Going to gen mart")
                self.apply_difficulty()
                self._player2.powerup_cards[14] = False
                self.set_player_turn("p2")
            else:
                return

        elif player == "op":
            if self._player2.powerup_cards[14]:
                self.set_player_turn("op")
                self._onlinep_todo["general_market"] = 1
                self._player2.powerup_cards[14] = False
                return

        elif player == "p2":
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[14]:
                self.popup_message("General Market", "General Market")
                self._root.title(f"{self._title} - GENERAL MARKET")
                [btn.config(state="disabled") for btn in self._depot_p2_btns]
                self._market_btn.configure(command=self.check_p2_picked_a_card)
                self.bind_return(method="pick_one")
                powerup[14] = False

    def hold_on(self, player: Literal["p2", "comp", "op"]):
        """Makes Player to hold on until the other player plays another card or goes to the mart,
        after playing a card with number 1 in it"""

        logging.debug(f"HOLD ON - {player}")

        if player == "comp":
            if self._player2.powerup_cards[1]:
                self.set_player_turn("p2")
                self._player2.powerup_cards[1] = False
            return

        elif player == "op":
            if self._player2.powerup_cards[1]:
                self.set_player_turn("p2")
                # Actual hold on handled in the recv end (self.handle_onlinep_todo)
                self._player2.powerup_cards[1] = False
                return

        elif player == "p2":
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[1]:
                self.popup_message("Hold On", "Hold On")
                powerup[1] = False
                self.gameover()
                if not self._onlinePlayerActive:
                    self._root.after(
                        self.COMP_PLAY_DELAY, lambda: self.comp_card_streak(1)
                    )
                else:
                    self.set_player_turn("op")

    def suspension(self, player: Literal["p2", "comp", "op"]):
        """Just like hold on, it suspends the other player until they play
        another card or go to mart"""

        if player == "comp":
            if self._player2.powerup_cards[8]:
                self.set_player_turn("p2")
                self._player2.powerup_cards[8] = False
            return

        elif player == "op":
            logging.debug(f"SUSPENSION - {player}")
            if self._player2.powerup_cards[8]:
                self.set_player_turn("p2")
                # Actual suspension handled in the recv end (self.handle_onlinep_todo)
                self._player2.powerup_cards[8] = False
                return

        elif player == "p2":
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards
            if powerup[8]:
                logging.debug(f"SUSPENSION - {player}")
                self.popup_message("Hold On", "Suspension")

                powerup[8] = False
                self.gameover()

                if not self._onlinePlayerActive:
                    self._root.after(
                        self.COMP_PLAY_DELAY, lambda: self.comp_card_streak(8)
                    )
                else:
                    self.set_player_turn("op")

    # --------------------------------------------------------------------------------------
    # ANIMATIONS
    # ---------------------------------------------------------------------------------------
    def create_playedcard_image(self):
        played_canvas = self._played_frame
        image = self._whot.PlayedCards()[-1][0]
        key = self._whot.PlayedCards()[-1][1]

        x, y = self._playedcard_curr_xy
        image_id = played_canvas.create_image(x, y, image=image)
        self._animated_images.append((image_id, key))

    def move_card(
        self,
        playcard: tuple[tk.PhotoImage, tuple[str, int]],
        player_canvas: tk.Canvas,
        played_canvas: tk.Canvas,
        widget: tk.Button | tk.Label,
        from_above=True,
    ):
        widget.grid_forget()

        # Get the absolute position of the player frame
        px = player_canvas.winfo_rootx()
        py = player_canvas.winfo_rooty()

        if from_above:
            # Pos of the upper widget
            x1, y1 = widget.winfo_rootx(), widget.winfo_rooty()
        else:
            # Pos of the lower widget
            x1 = widget.winfo_rootx() + widget.winfo_width()
            y1 = widget.winfo_rooty() + widget.winfo_height()

        # Subtract the canvas origin from the pointer position
        x1 -= px
        y1 -= py

        # Get the dynamic pos to place the played image
        x2, y2 = self._playedcard_curr_xy

        cardstack_x_offset = len(self._animated_images) / 2  # / 5
        # print('cardstack_x_offset -->', cardstack_x_offset, flush=True)

        card = played_canvas.create_image(x1, y1, image=playcard[0])
        self._animated_images.append((card, playcard[1]))

        played_canvas.tag_raise(card)
        self.animate_frame(
            0,
            x1,
            y1,
            (x2 + cardstack_x_offset),
            y2,
            card,
            played_canvas,
            player_canvas,
        )

    def animate_frame(
        self,
        frame: int,
        x: int,
        y: int,
        target_x: float,
        target_y: float,
        card: int,
        played_canvas: ctk.CTkCanvas,
        player_canvas: ctk.CTkCanvas,
        NUM_FRAMES=36,
        FRAME_DURATION=12,
    ):
        if frame < NUM_FRAMES:
            # Linear glide: fixed step per frame. (The old
            # (remaining/N)*5 step arrived in ~2 frames then crawled.)
            dx = (target_x - x) / NUM_FRAMES
            dy = (target_y - y) / NUM_FRAMES
            played_canvas.coords(card, x, y)
            x += dx
            y += dy
            player_canvas.after(
                FRAME_DURATION,
                self.animate_frame,
                frame + 1,
                x,
                y,
                target_x,
                target_y,
                card,
                played_canvas,
                player_canvas,
            )

    def rearrange_playedimages_onresize(self, event: tk.Event):
        image = self._whot.PlayedCards()[-1][0]
        X_OFFSET = image.width() / 2
        if event.width >= 900:
            X_OFFSET += 60
        elif event.width >= 1100:
            X_OFFSET += 30
        if not event.width >= 750:
            X_OFFSET = 0

        x, y = 0.69 * event.width - X_OFFSET, 0.55 * event.height

        for img, _key in self._animated_images:
            self._played_frame.coords(img, x, y)
        self._playedcard_curr_xy = x, y

    def animate_widget_clicked(self, widget: tk.Button | tk.Label):
        """Animates the widget as being clicked"""
        widget.config(relief="sunken")
        self._root.after(200, lambda: widget.config(relief="raised"))

    def insert_widget_at_first_column(self, widget: tk.Button | tk.Label):
        """
        Inserts a widget at the first column in the grid layout.
        For either player2 or computer (onlineplayer) frame
        """

        def increment_column(grid_info):
            return grid_info["column"] + 1 if grid_info else None

        if isinstance(widget, tk.Button):
            for btn in self._player2_btns.values():
                column = increment_column(btn.grid_info())
                if column is not None:
                    btn.grid(row=0, column=column)
            widget.grid(row=0, column=0, padx=6, pady=6)

        elif isinstance(widget, tk.Label):
            labels = (
                self._onlinep_labels.values()
                if self._onlinePlayerActive
                else self._computer_labels.values()
            )
            for label in labels:
                column = increment_column(label.grid_info())
                if column is not None:
                    label.grid(row=0, column=column)
            widget.grid(row=0, column=0, padx=6, pady=6)

    # -------------------------------------------------------------------------------------
    # CARDS INITIALIZATION
    # -------------------------------------------------------------------------------------
    def reinitialize_cards(
        self,
        onlinePlayer=False,
        shuffle_seed: int = None,
        conn_type="server",
        player_turn: str = None,
        prev_onlinep=False,
    ):
        self._onlinePlayerActive = onlinePlayer

        if prev_onlinep:
            self._title = "Whot Game"
            self.update_turn_indicator()
            self._multiplayer_indicator.place_forget()
            self._multiplayer_switch.place_forget()
            self._delete_multiplayer_indicators = False

        self._root.title(self._title)

        [btn.grid_forget() for btn in self._depot_p2_btns]
        [lab.grid_forget() for lab in self._depot_comp_labels]
        try:
            [lab.grid_forget() for lab in self._depot_onlinep_labels]
        except AttributeError as e:
            print(e)

        self._market_btn.place_forget()
        self._played_frame.delete("all")
        self._animated_images.clear()

        self._whot = Main.Whot()
        self._whot.InitDepot()
        self._whot.shuffle_cards(shuffle_seed)
        self._computer = Main.Computer()
        self._player2 = Main.Player2()
        self._onlinep = Main.OnlinePlayer()

        self._whot.Reset()
        dark = self._config.get("appearance", "dark") == "dark"
        self.apply_theme(dark)
        self._whot.apply_theme(dark)
        self._whot.InitPlayerCards(onlinePlayer, conn_type)
        self._whot.InitComputerCards()
        self._whot.InitPlayer2Cards()
        self._whot.NormCards()

        self.__check_gameover = False
        self.initialize_card_graphics(onlinePlayer)
        self._root.after(
            self.INITIAL_COMP_PLAY_DELAY, self.compPlayEngine
        ) if not onlinePlayer else None
        self.display_cards_animation([self._player2_btns[i] for i in range(5)])
        self.display_number_of_cards("player2")
        self.display_number_of_cards("onlinep" if onlinePlayer else "computer")
        self.root_bindings()

        if player_turn:
            self.set_player_turn(player_turn)
        else:
            next_player = ("p2", "comp" if not onlinePlayer else "op")
            self.set_player_turn(choice(next_player))
        self.set_theme()

        return player_turn

    def initialize_card_graphics(self, onlinePlayer=False) -> None:
        """
        Initializes the graphics for the card game, specifically the buttons and labels for Player 2 and Computer players.

        Parameters:
            onlinePlayer (bool): A flag indicating whether the game is being played with an online player
            (Multiplayer).
        """
        self._btn_reference: list[list[tuple[tk.PhotoImage, tuple[str, int]]]]
        self._label_reference: list[list[tuple[tk.PhotoImage, tuple[str, int]]]]

        # +++++++++++++++++++++++
        # Initialize for player2
        # +++++++++++++++++++++++
        self._btn_reference = [[] for _ in range(30)]
        self._depot_p2_btns = [
            tk.Button(self._player2_frame, bd=0, highlightthickness=0,
                      relief="flat",
                      activebackground=self._card_base_bg())
            for _ in range(30)
        ]

        self._player2_btns = {i: self._depot_p2_btns[i] for i in range(30)}
        player2_cards = self._player2.cards()

        for i in range(5):
            self._btn_reference[i].append(player2_cards[i])
            self._player2_btns[i].configure(
                image=player2_cards[i][0],
                command=lambda i=i: self.player2_play(
                    self._btn_reference[i], self._player2_btns[i]
                ),
            )

        # ++++++++++++++++++++++++++++
        # Initialize for onlineplayer
        # ++++++++++++++++++++++++++++
        if onlinePlayer:
            self._label_reference = [[] for _ in range(30)]
            self._depot_onlinep_labels = [
                tk.Label(self._comp_frame, bd=0, highlightthickness=0,
                         relief="flat") for _ in range(30)
            ]

            self._onlinep_labels = {i: self._depot_onlinep_labels[i] for i in range(30)}
            for i in range(5):
                self._onlinep_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._onlinep.cards()[i])

        # ++++++++++++++++++++++++
        # Initialize for computer
        # ++++++++++++++++++++++++
        else:
            self._label_reference = [[] for _ in range(30)]
            self._depot_comp_labels = [
                tk.Label(self._comp_frame, bd=0, highlightthickness=0,
                         relief="flat") for _ in range(30)
            ]

            # Initialize and Display Computer Labels and Sync with their Label references (Labrefs)
            self._computer_labels = {i: self._depot_comp_labels[i] for i in range(30)}
            for i in range(5):
                self._computer_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._computer.cards()[i])

        self._market_btn = tk.Button(
            self._played_frame,
            image=self._misc_whot,
            command=self.p2_mart,
            state="disabled",
            bd=0,
            highlightthickness=0,
            relief="flat",
            activebackground=self._card_base_bg(),
        )
        self._market_btn.place(relx=0.027, rely=0.10)
        if onlinePlayer and not self._delete_multiplayer_indicators:
            self.create_multiplayer_indicators()
        return

    # -------------------------------------------------------------------------------------
    # PLAYER2
    # -------------------------------------------------------------------------------------
    def player2_play(
        self,
        card: list[tuple[tk.PhotoImage, tuple[str, int]]],
        card_display_btn: tk.Button,
    ):
        """For player2 (actual player) to play their valid card"""
        if self.__check_gameover:
            return

        if self.get_player_turn("p2"):
            try:
                if self._player2.play(card[0]):
                    player = "op" if self._onlinePlayerActive else "comp"
                    self.set_player_turn(player)
                    self.p2_request_card_with_20(card)

                    self.move_card(
                        card[0],
                        self._player2_frame._parent_canvas,
                        self._played_frame,
                        card_display_btn,
                        from_above=False,
                    )

                    if not self._onlinePlayerActive:
                        card_display_btn.after(
                            self.COMP_PLAY_DELAY, self.compPlayEngine
                        )
                    else:
                        self._onlineClient.send_data(card[0][1], "CARD")

                    card.clear()
                    self.display_number_of_cards("player2")
                    self.pick_two(player)
                    self.go_gen_mart(player)
                    self.hold_on(player)
                    self.suspension(player)

                    self.gameover()
            except Main.WhotException as e:
                self.message_box(
                    title="INVALID MOVE", message=str(e).upper(), icon="warning"
                )
        else:
            self.message_box("Not Your Turn", "Its not your turn to play")

    def p2_mart(self, power: int = None, event=None):
        """Responsible for making player2 to go to market (pick a card from the market).
        `power` indicates how many times the computer should go to market
        """

        if not self.get_player_turn("p2") or self.__check_gameover:
            return

        if power:
            if power == 2:
                self._p2_picked_2_cards_count += 1
            elif power == 1:
                self._p2_picked_1_card_count += 1

        for idx, i in enumerate(self._btn_reference):
            if i:
                continue
            self._player2.gomart()
            self._btn_reference[idx].append(self._player2.cards()[-1])
            new_btn = self._player2_btns.get(idx)

            if event:  # When we hit ENTER <RETURN>
                self._market_btn.configure(relief="sunken")
                self._root.after(
                    100, lambda: self._market_btn.configure(relief="raised")
                )

            new_btn.configure(
                image=self._player2.cards()[-1][0],
                command=lambda: self.player2_play(
                    self._btn_reference[idx], self._player2_btns[idx]
                ),
            )
            self._root.after(200, self.insert_widget_at_first_column, new_btn)

            if self._onlinePlayerActive:
                self._onlineClient.send_data("MARKET", "MART")
            break

        self.display_number_of_cards("player2")
        self.set_player_turn("comp" if not self._onlinePlayerActive else "op")
        self.repopulate_containers()

        if self._p2_picked_2_cards_count == 1:
            self._root.title(f"{self._title} - PICK TWO")

        elif not self._p2_picked_2_cards_count or not self._p2_picked_1_card_count:
            self._root.title(self._title)
            self._root.after(self.COMP_PLAY_DELAY, self.compPlayEngine)
        else:
            self._root.title(self._title)
            self._root.after(self.COMP_PLAY_DELAY, self.compPlayEngine)

    def check_p2_picked_two_cards(self, player="comp", event=None):
        """Checks whether player2 clicked the mart button twice (in other words, checks whether player2 has
        picked two cards) and then unfreezes player2 cards (buttons) - for PICK TWO"""

        player = "comp" if not self._onlinePlayerActive else "op"
        self.p2_mart(power=2, event=event)
        self.set_player_turn("p2")
        self._root.title(f"{self._title} - PICK TWO")

        if self._p2_picked_2_cards_count == 2:  # Done picking two cards
            self.set_player_turn(player)
            [btn.config(state="normal") for btn in self._depot_p2_btns]
            self._p2_picked_2_cards_count = 0
            self._market_btn.configure(command=self.p2_mart)
            self.bind_return(method="mart")
            self._root.title(self._title)

    def check_p2_picked_a_card(self, player="comp", event=None):
        """Checks whether player2 clicked the mart button once (in other words, checks whether player2 has
        picked one card) and then unfreezes player2 cards (buttons) - for GENERAL MARKET
        """

        player = "comp" if not self._onlinePlayerActive else "op"
        self.p2_mart(power=1, event=event)
        if self._p2_picked_1_card_count == 1:
            self.set_player_turn(player)
            [btn.config(state="normal") for btn in self._depot_p2_btns]
            self._p2_picked_1_card_count = 0
            self._market_btn.configure(command=self.p2_mart)
            self.bind_return(method="mart")

    def p2_request_card_with_20(
        self, card: list[tuple[tk.PhotoImage, tuple[str, int]]]
    ):
        """Player2 (actual player) demands a particular card from computer after playing whot 20"""

        if len(self._player2.cards()) == 0 or not card[0][1][1] == 20:
            return

        self.set_player_turn("p2")

        card_root = ctk.CTkToplevel(self._root)
        card_root.transient(self._root)
        x, y = self._root.winfo_x(), self._root.winfo_y()
        card_root.geometry(f"230x480+{x}+{y}")
        card_root.title("Ask for a card")
        card_root.resizable(False, False)
        card_root.after(250, card_root.wm_iconbitmap, "genesis.ico")

        label_theme = self.get_actual_theme(for_text=True)
        button_theme = self._themes_dict.get(self._theme_var.get())

        command = lambda card_name, toplev: self._p2_clicked_card(card_name, toplev)

        card_buttons = [
            ("Cross", self._cross_icon),
            ("Circle", self._circle_icon),
            ("Star", self._star_icon),
            ("Triangle", self._triangle_icon),
            ("Square", self._square_icon),
        ]

        for i, (card_name, icon) in enumerate(card_buttons):
            button = tk.Button(
                card_root,
                image=icon,
                command=lambda i=i: command(card_buttons[i][0], card_root),
                bg=button_theme,
                bd=0,
                highlightthickness=0,
                relief="flat",
                activebackground=button_theme,
            )
            button.grid(row=i, column=0, pady=3, padx=15)
            ctk.CTkLabel(
                card_root,
                text=card_name,
                text_color=label_theme,
                font=self.smaller_font,
            ).grid(row=i, column=1)

        ctk.CTkLabel(
            card_root,
            text="Choose Desired Card",
            text_color=label_theme,
            font=self.font_style,
        ).place(relx=0.13, rely=0.896)

        card_root.protocol(
            "WM_DELETE_WINDOW", lambda: self._p2_clicked_card(None, card_root)
        )
        card_root.focus_set()
        card_root.grab_set()

    def _p2_clicked_card(self, card: str, window: ctk.CTkToplevel):
        """Registers player2's Desired card and calls player1 (computer or OP) to respond to the request"""
        window.destroy()
        [btn.config(state="normal") for btn in self._depot_p2_btns]
        self._market_btn.configure(state="normal")
        window.grab_release()

        player = "comp" if not self._onlinePlayerActive else "op"
        self.set_player_turn(player)
        if not card:
            self._root.after(500, self.compPlayEngine)
            return

        if not self._onlinePlayerActive:
            self._whot.requests["player2"] = card
            self._root.after(500, self.computer_response_to_card_20)
        else:
            self._onlineClient.send_data(card, data_type="REQUEST")

    # ----------------------------------------------------------------------------------------
    # MULTIPLAYER
    # ----------------------------------------------------------------------------------------
    def create_multiplayer_indicators(self):
        print("creating multiplayer indicators")
        self._other_client_connected = False
        self._multiplayer_switch_var = tk.BooleanVar(value=True)
        self._multiplayer_switch = ctk.CTkSwitch(
            self._root,
            height=21,
            text="On/Off",
            font=self.smaller_font,
            onvalue=True,
            offvalue=False,
            variable=self._multiplayer_switch_var,
            command=self.terminate_multiplayer,
        )
        self._multiplayer_switch.place(relx=0.414, rely=0.954)
        self._multiplayer_indicator = ctk.CTkLabel(
            self._root,
            height=21,
            width=84,
            text="Waiting...",
            font=self.smaller_font,
            text_color=self.get_actual_theme(for_text=True),
        )
        self._multiplayer_indicator.place(relx=0.559, rely=0.954)

    def update_multiplayer_indicators(self):
        self._multiplayer_switch_var.set(True)
        self._multiplayer_indicator.configure(text="Connected", text_color="red")
        self._other_client_connected = True

    def multiplayer_restart_game(self):
        play_question = self.message_box(
            "PLAY AGAIN",
            "Do You Want To Play Again?",
            icon="question",
            option_1="No",
            option_2="Yes",
        ).get()
        if play_question == "Yes":
            self.initialize_multiplayer(self._onlineNickname, conn_use_threads=False)
            return True

        return False

    def terminate_multiplayer(self):
        if not self._other_client_connected and not self._multiplayer_switch_var.get():
            if (
                self.message_box(
                    "QUIT WAITING",
                    "Quit Waiting For Connection?",
                    icon="question",
                    option_1="No",
                    option_2="Yes",
                ).get()
                == "Yes"
            ):
                self.__restart(force=True)
            else:
                self._multiplayer_switch_var.set(True)

        elif self._other_client_connected and not self._multiplayer_switch_var.get():
            if (
                self.message_box(
                    "QUIT CONNECTION",
                    "Terminate Existing Connection?",
                    icon="question",
                    option_1="No",
                    option_2="Yes",
                ).get()
                == "Yes"
            ):
                self.__restart(force=True)
            else:
                self._multiplayer_switch_var.set(True)

    def generate_shuffle_seed(self) -> int:
        return int.from_bytes(os.urandom(4), "big")

    MP_HANDSHAKE_TIMEOUT = 25.0  # seconds to wait for a peer before giving up

    def initialize_multiplayer(
        self, nickname: str, host: str = None, port: int = None, conn_use_threads=True
    ):
        if not conn_use_threads:
            self._delete_multiplayer_indicators = True

        if self._server_choice == "start server":
            seed = self.generate_shuffle_seed()
            if conn_use_threads:
                self.start_mp_server_or_client_thread(self.init_server, host, port)
                self.start_mp_server_or_client_thread(self.init_client, host, port)

            try:
                player_turn = self.reinitialize_cards(
                    onlinePlayer=True,
                    shuffle_seed=seed,
                    conn_type="server",
                )
                player_turn = "op" if player_turn == "p2" else "p2"
                init_data = {
                    "seed": seed,
                    "player_turn": player_turn,
                    "nickname": nickname,
                }
                if conn_use_threads:
                    # Hand the blocking wait to a worker; the GUI stays live.
                    # Completion runs on the main thread via _mp_watch.
                    self._mp_result = None
                    self._mp_handshake_active = True
                    threading.Thread(
                        target=self._host_handshake, args=(init_data,),
                        daemon=True,
                    ).start()
                    self._root.after(200, self._mp_watch)
                else:
                    self._onlineClient.send_data(
                        str(json.dumps(init_data)), "INIT_DATA")
            except (
                OSError,
                ConnectionRefusedError,
                AttributeError,
                TimeoutError,
                tk.TclError,
            ) as e:
                print("startMp", e)
                self._connectionFailed = True

        elif self._server_choice == "join server":
            if conn_use_threads:
                self.start_mp_server_or_client_thread(self.init_client, host, port)
                # Blocking seed-wait goes to a worker; the GUI stays live.
                # Completion runs on the main thread via _mp_watch.
                self._mp_result = None
                self._mp_handshake_active = True
                threading.Thread(
                    target=self._join_handshake, args=(nickname,),
                    daemon=True,
                ).start()
                self._root.after(200, self._mp_watch)
            else:
                init_data = self.get_init_data_from_server(queue.Queue)
                print(init_data)
                self._onlineNickname = init_data["nickname"]
                self._onlineClient.send_data(nickname, data_type="NICKNAME")

                if not self._connectionFailed:
                    self.reinitialize_cards(
                        onlinePlayer=True,
                        shuffle_seed=init_data["seed"],
                        conn_type="client",
                        player_turn=init_data["player_turn"],
                    )
                    self.update_multiplayer_indicators()

                cleared_init_data = self._onlineClient.client_init_data
                for key in cleared_init_data:
                    cleared_init_data[key] = None

        if not conn_use_threads:
            self._finish_mp_setup()

    def _finish_mp_setup(self):
        """Shared tail of multiplayer setup (main thread)."""
        self._mp_handshake_active = False
        if not self._connectionFailed:
            self.start_onlineplayer_listener_thread()
        else:
            print("connection Failed")
            self._mp_connect_failed("Connection Failed")

    def _wait_for_peer(self, ready) -> bool:
        """Worker-thread wait: `ready()` true means proceed; timeout/fail out."""
        deadline = time.time() + self.MP_HANDSHAKE_TIMEOUT
        while time.time() < deadline:
            if self._connectionFailed:
                return False
            if ready():
                return True
            time.sleep(0.2)
        return False

    def _mp_watch(self):
        """Main-thread watchdog: run handshake completions posted by workers.

        Workers never call Tk (unsafe across threads); they only assign
        self._mp_result. This polls it on the mainloop and dispatches.
        """
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return
        job = self._mp_result
        self._mp_result = None
        if job is not None:
            kind, payload = job
            if kind == "host-ok":
                self._finish_mp_setup()
            elif kind == "join-ok":
                self._finish_join(payload)
            elif kind == "fail":
                self._mp_connect_failed(payload)
        if self._mp_handshake_active:
            self._root.after(200, self._mp_watch)

    def _host_handshake(self, init_data: dict):
        """Worker thread: publish the seed once our client is up."""
        if not self._wait_for_peer(lambda: self._onlineClient is not None):
            self._mp_result = ("fail", "No Client Joined")
            return
        try:
            self._onlineClient.send_data(str(json.dumps(init_data)), "INIT_DATA")
        except (OSError, AttributeError) as e:
            print("host handshake send failed:", e)
            self._mp_result = ("fail", "Connection Failed")
            return
        self._mp_result = ("host-ok", None)

    def _join_handshake(self, nickname: str):
        """Worker thread: wait for the host's seed, then join on the GUI."""
        def seeded():
            client = self._onlineClient
            return client is not None and all(
                v not in (None, "") for v in client.client_init_data.values()
            )

        if not self._wait_for_peer(seeded):
            self._mp_result = ("fail", "No Server To Be Joined")
            return
        self._mp_result = ("join-ok", nickname)

    def _finish_join(self, nickname: str):
        """Main thread: complete a join after the seed arrived."""
        self._mp_handshake_active = False
        if self._connectionFailed or self._onlineClient is None:
            self._mp_connect_failed("Connection Failed")
            return
        init_data = dict(self._onlineClient.client_init_data)
        self._onlineNickname = init_data.get("nickname") or "OnlinePlayer"
        try:
            self._onlineClient.send_data(nickname, data_type="NICKNAME")
        except (OSError, AttributeError) as e:
            print("join nick send failed:", e)
            self._mp_connect_failed("Connection Failed")
            return
        self.reinitialize_cards(
            onlinePlayer=True,
            shuffle_seed=init_data.get("seed"),
            conn_type="client",
            player_turn=init_data.get("player_turn"),
        )
        self.update_multiplayer_indicators()
        for key in self._onlineClient.client_init_data:
            self._onlineClient.client_init_data[key] = None
        self._finish_mp_setup()

    def _mp_connect_failed(self, message="Connection Failed"):
        """Main thread: tear down a failed handshake and restart locally."""
        self._mp_handshake_active = False
        self.message_box("Connection Failed", message, icon="cancel")
        self._title = "Whot Game"
        self._root.title(self._title)
        self._onlinePlayerActive = False
        self._connectionFailed = False
        self.__restart(force=True)

    def start_multiplayer_server_client(self, event=None):
        if self._delay_multiplayer_for_animations:
            self.popup_message(
                title="Please Wait",
                text="Please wait for animations to finish",
                wraplength=240,
            )
            return
        elif self._onlinePlayerActive:
            self.popup_message(
                title="MP Error", text="Multiplayer Already Active!", wraplength=240
            )
            return

        multiplayer = self.multiplayer_gui()
        print("multiplayer -->", multiplayer)
        if multiplayer is None:
            return
        host, port, nickname, server_choice = multiplayer
        self._server_choice = server_choice
        self._title += " - MULTIPLAYER"
        self._root.title(self._title)

        self.initialize_multiplayer(
            nickname=nickname, host=host, port=port, conn_use_threads=True
        )

    def multiplayer_gui(self) -> tuple[str, int, str, str] | None:
        root = self.create_toplevel_at_center(width=274, height=168)
        root.transient(self._root)
        root.resizable(False, False)
        root.title("Multiplayer")
        return_value = None

        config = self._config["multiplayer"]

        host_var, port_var = tk.StringVar(value=config["host"]), tk.IntVar(
            value=config["port"]
        )
        server_var = tk.StringVar(value=config["server_choice"])

        ctk.CTkLabel(
            root, height=23, width=38, text="Host:", font=self.smaller_font
        ).place(relx=0.036, rely=0.06)
        ctk.CTkLabel(
            root, height=23, width=38, text="Port:", font=self.smaller_font
        ).place(relx=0.036, rely=0.290)

        host_entry = ctk.CTkEntry(
            root, width=170, textvariable=host_var, font=self.smaller_font
        )
        host_entry.place(relx=0.31, rely=0.071)
        port_entry = ctk.CTkEntry(
            root, width=170, textvariable=port_var, font=self.smaller_font
        )
        port_entry.place(relx=0.31, rely=0.295)

        start_server = ctk.CTkRadioButton(
            root,
            height=25,
            text="Start Server",
            variable=server_var,
            value="start server",
            font=self.smaller_font,
        )
        start_server.place(relx=0.04, rely=0.620)
        join_server = ctk.CTkRadioButton(
            root,
            height=25,
            text="Join Server",
            variable=server_var,
            value="join server",
            font=self.smaller_font,
        )
        join_server.place(relx=0.605, rely=0.620)

        def close_window(exit_btn=False):
            nonlocal return_value
            root.destroy()
            root.quit()

            host, port = host_var.get(), port_var.get()
            nickname, server_choice = self._config["name"], server_var.get()

            config["host"] = host
            config["port"] = port
            config["nickname"] = nickname
            config["server_choice"] = server_choice

            self._write_config(plain_save=True)
            if exit_btn:
                return_value = None
            else:
                return_value = (host, port, nickname, server_choice)

        connect_btn = ctk.CTkButton(
            root,
            height=30,
            width=86,
            text="Connect",
            font=self.smaller_font,
            command=close_window,
        )
        connect_btn.place(relx=0.35, rely=0.805)
        host_entry.select_range(0, tk.END), port_entry.select_range(0, tk.END)

        root.protocol("WM_DELETE_WINDOW", lambda: close_window(exit_btn=True))
        root.focus_set()
        root.grab_set()
        root.mainloop()

        return return_value

    def start_mp_server_or_client_thread(self, target: Callable, host: str, port: int):
        print(f"{target} host and port -->", host, port)
        init_thread = threading.Thread(target=target, args=(host, port))
        init_thread.start()

    def init_server(self, host: str, port: int):
        try:
            server = multiplayer.Server(host, port)
        except (ConnectionRefusedError, OSError) as e:
            print(e)
            self._connectionFailed = True
        else:
            self._onlineServer = server
            print("server -->", self._onlineServer)
            return server  # TODO: Implement a queue object and put this server, idek why yet...

    def init_client(self, host: str, port: int):
        try:
            nickname = self._config["name"]
            client = multiplayer.Client(host, port, nickname)
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            print(e)
            self._connectionFailed = True
        else:
            self._onlineClient = client
            print("client -->", self._onlineClient)
            return client

    def start_onlineplayer_listener_thread(self):
        """Poll the network state on the mainloop (no thread, no Tk races).

        Keeps the historical name; call sites are unchanged.
        """
        self._poll_onlinep_once()

    def _poll_onlinep_once(self):
        try:
            if not self._root.winfo_exists():
                return
        except tk.TclError:
            return  # root gone (shutdown); stop the chain silently
        if not self._onlinePlayerActive or self._onlineClient is None:
            return
        self.onlineplayer_listener()
        self._root.after(250, self._poll_onlinep_once)

    # ------------------------------------------------------------------------------------
    # ONLINEPLAYER
    # ------------------------------------------------------------------------------------
    def onlineplayer_listener(self):
        """Single main-thread pass over the latest network state."""
        if self._onlineClient is None:
            return
        client_data = self._onlineClient.client_data

        nick: str = client_data["conn_nickname"]
        other_client_alive = self._onlineClient._other_client_alive
        card_index = client_data["card_index"]
        card = client_data["card"]
        mart = client_data["mart"]
        request = client_data["request"]

        if nick:
            self._onlineNickname = nick
            self.display_number_of_cards("onlinep")
            self._comp_turn_indicator.configure(text=nick.capitalize())
            client_data["conn_nickname"] = None
            self.update_multiplayer_indicators()  # server_choice: start server

        if other_client_alive is False:
            self.message_box(
                "CLIENT ERROR",
                f"{self._onlineNickname or 'OnlinePlayer'} Disconnected!",
                icon="cancel",
            )
            self.__restart(force=True)

        if card_index:
            self.set_player_turn("op")
            self.onlinep_play(self._label_reference[card_index])

        if card:
            print("\n@@@@ onlineP sent card", card)
            index = self.get_onlinep_card_index(card)
            self.set_player_turn("op")
            self.onlinep_play(self._label_reference[index])

        if mart:  # Set for OP to play again
            print("\n!!!! onlinep went to mart")
            self.set_player_turn("op")
            self.onlinep_mart()

        if request:
            print("\n$$$$ onlinep sent request")
            self.onlinep_request_card_with_20(request)

    def get_onlinep_card_index(self, card: tuple[str, int]):
        print("finding card...")
        index = None
        for i, sublist in enumerate(self._label_reference):
            for j, carditem in enumerate(sublist):
                if carditem[1] == card:  # item[1] - ('Square', 2)
                    index = i
                    print(f"Index of {card}: ({i}, {j})")
                    break
            if index:
                break

        if index is None:
            raise Main.WhotException("Cant Find OnlineP Card In Cardstack")

        return index

    def onlinep_mart(self):
        if not self.get_player_turn("op") or self.__check_gameover:
            print("\nin onlinep mart, its not op turn for mart")
            return

        for o, i in enumerate(self._label_reference):
            if i:
                continue
            self._onlinep.gomart()
            self._label_reference[o].append(self._onlinep.cards()[-1])

            new_label = self.comp_op_get_next_available_label(is_gridded=False)
            self.animate_widget_clicked(self._market_btn)
            new_label.configure(image=self._misc_whot1)
            self._root.after(200, self.insert_widget_at_first_column, new_label)
            break

        self._onlineClient.client_data["mart"] = False  # Reset
        self.display_number_of_cards("onlinep")
        self.handle_onlinep_todos()

        self.repopulate_containers(onlinePlayer=True)
        self._root.title(self._title)

    def handle_onlinep_todos(self, card: tuple[tk.PhotoImage, tuple[str, int]] = None):
        todo = self._onlinep_todo

        if todo["pick_two"] > 0:
            todo["pick_two"] -= 1
            self.set_player_turn("p2" if todo["pick_two"] == 0 else "op")

        if todo["general_market"] > 0:
            todo["general_market"] -= 1
            self.set_player_turn("p2")

        if card:
            if card[1][1] == 1:  # HoldOn
                todo["hold_on"] = True

            if card[1][1] == 8:  # Suspension
                todo["suspension"] = True

            if card[1][1] != 1 and todo["hold_on"]:
                todo["hold_on"] = False
                self.set_player_turn("op")
                self.op_continue_from_hold_or_suspension()

            if card[1][1] != 8 and todo["suspension"]:
                todo["suspension"] = False
                self.set_player_turn("op")
                self.op_continue_from_hold_or_suspension()

            if card[1][1] == 20:
                self.set_player_turn("op")

        elif not card and todo["hold_on"]:  # For mart
            todo["hold_on"] = False
            self.set_player_turn("op")
            self.op_continue_from_hold_or_suspension()

        elif not card and todo["suspension"]:
            todo["suspension"] = False
            self.set_player_turn("op")
            self.op_continue_from_hold_or_suspension()

        if not any(todo.values()):
            self.set_player_turn("p2")

    def op_continue_from_hold_or_suspension(self):
        self.popup_message("Continue", "Continue", 400)

    def onlinep_request_card_with_20(self, request: str):
        client_data = self._onlineClient.client_data

        if len(self._onlinep.cards()) == 0:
            client_data["request"] = ""
            return

        self.set_player_turn("p2")

        print("in req with card 20, request -->", request)
        self._whot.requests["onlineplayer"] = request
        self._root.title(f"{self._title} - Request {request.upper()}")
        client_data["request"] = ""
        self.message_box("Request", f"I NEED {request.upper()}")

    def onlinep_play(
        self, card: list[tuple[tk.PhotoImage, tuple[str, int]]], event=None
    ):
        """For OnlinePlayer to play their valid card"""

        print(f"onlineplayer just played {card[0]}")
        if self.get_player_turn("op") and not self.__check_gameover:
            if self._onlinep.play(card[0]):
                card_display_label = self.comp_op_get_next_available_label(
                    is_gridded=True
                )
                self.move_card(
                    card[0],
                    self._comp_frame._parent_canvas,
                    self._played_frame,
                    card_display_label,
                    from_above=True,
                )

                self._onlineClient.client_data["card"] = None

                self.display_number_of_cards("onlinep")
                self.handle_onlinep_todos(card[0])
                self.pick_two("p2")
                self.go_gen_mart("p2")
                self.hold_on("p2")
                self.suspension("p2")

                if card[0][1][1] == 20:
                    print("\nOP CARD IS 20, SETTING OP TO PLAY AGAIN")
                    self.set_player_turn("op")
                card.clear()
                self.gameover()

            else:  # Rare Happening
                raise Main.WhotException("OnlinePlayer Played Invalid Card")

    # ---------------------------------------------------------------------------------------------------
    # COMPUTER
    # ---------------------------------------------------------------------------------------------------
    def apply_difficulty(self):
        """Applies Chosen Difficulty To The Game And Goes To Market"""

        if not choice([True, False, "", "Whot"]):
            print("not choice...")
            self.comp_mart()
            return

        difficulty = self._difficulty_var.get()
        difficulty_dict = {
            "hard": [2, 20, 1],
            "medium": [14, 8],
        }
        powerups = difficulty_dict.get(difficulty)
        if not powerups:
            self.comp_mart()
            return

        chosen = choice(powerups)
        print(f"mode var is {difficulty} and chosen is: ", chosen)
        if self._computer.search_and_append(chosen, "comp"):
            self.comp_mart(gone_to_mart_before=True)
        else:
            self.comp_mart()

    def computer_play(
        self,
        card: list[tuple[tk.PhotoImage, tuple[str, int]]],
    ):
        """Plays any cards that are valid, from CompPlayEngine"""
        if not self.get_player_turn("comp") or self.__check_gameover:
            return

        try:
            if self._computer.play(card[0]):
                card_display_label = self.comp_op_get_next_available_label(
                    is_gridded=True
                )
                self.move_card(
                    card[0],
                    self._comp_frame._parent_canvas,
                    self._played_frame,
                    card_display_label,
                    from_above=True,
                )

                self.computer_request_card_with_20(card[0])
                self.display_number_of_cards("computer")
                self.pick_two("p2")
                self.go_gen_mart("p2")
                self.hold_on("p2")
                self.suspension("p2")

                self.set_player_turn("p2")
                card.clear()
                self.gameover()

            else:  # Rare Happening
                raise Main.WhotException("Computer Played Invalid Card")
        # TODO
        except Main.WhotException as e:
            self.message_box("Computer Error", e, icon="cancel")

    def compPlayEngine(self, event=None):
        if (
            self.__check_gameover
            or self._onlinePlayerActive
            or not self.get_player_turn("comp")
        ):
            return

        if self._computer.requested_card_idx is not None:
            idx = self._computer.requested_card_idx
            card = self._label_reference[idx]
            logging.debug(
                f"[requested_card_idx]: idx: {idx}, card: {card}, label_ref_index(card): {self._label_reference.index(card)}"
            )
            if (
                card
            ):  # comp has somehow played that card (maybe p2 counter requested with whot20)
                last_played_card = self._whot.PlayedCards()[-1]
                if (
                    card[0][1][0] == last_played_card[1][0]
                    or card[0][1][1] == last_played_card[1][1]
                    or last_played_card[1][1] == 20
                ):
                    self.computer_play(card)
                    self._label_reference.pop(self._label_reference.index(card))
                    self._computer.requested_card_idx = None
                    return
                else:
                    self._computer.requested_card_idx = None
            else:
                # card idx now useless as a counter powerup was played by p2
                self._computer.requested_card_idx = None

        found_whot20_card, found_num_card, found_str_card = [], [], []

        containers: list[list[list[tuple[tk.PhotoImage, tuple[str, int]]]]]
        containers = [found_whot20_card, found_num_card, found_str_card]

        for idx, card in enumerate(self._label_reference):
            if not card:
                continue

            if card[0][1][1] == 20:
                self.parse_and_remove_comp_cards(containers[0], card, idx)
                break

            if (
                not found_whot20_card
                and card[0][1][1] == self._whot.PlayedCards()[-1][1][1]
            ):
                self.parse_and_remove_comp_cards(containers[1], card, idx)
                break

            if (
                not found_num_card
                and not found_whot20_card
                and card[0][1][0] == self._whot.PlayedCards()[-1][1][0]
            ):
                self.parse_and_remove_comp_cards(containers[2], card, idx)
                break

        # ! Must not change the order of containers
        found_valid_card = next(
            (container for container in containers if container), None
        )

        if found_valid_card:
            self.comp_engine_play_valid_card(
                containers.index(found_valid_card),
                found_valid_card[0],
            )
        else:
            self.apply_difficulty()

        for container in containers:
            container.clear()

    def parse_and_remove_comp_cards(
        self,
        found_card_container: list,
        card: list[tuple[tk.PhotoImage, tuple[str, int]]],
        index: int,
    ):
        """Remove the computer card and add an empty list (card) to the same index in ``self._label_reference``"""
        found_card_container.append(card)
        self._label_reference.insert(index, [])
        self._label_reference.pop(self._label_reference.index(card))

    def comp_engine_play_valid_card(
        self,
        found_index: int,
        card: list[tuple[tk.PhotoImage, tuple[str, int]]],
    ):
        logging.debug(f"[Comp Play Valid Card]: {found_index}, {card[0][1]}")
        if found_index == 1:  # found num
            if card[0][1][1] == self._whot.PlayedCards()[-1][1][1]:
                self.computer_play(card)
        elif found_index == 2:  # found str
            if card[0][1][0] == self._whot.PlayedCards()[-1][1][0]:
                self.computer_play(card)
        else:
            self.computer_play(card)

    def comp_op_get_next_available_label(self, is_gridded=False) -> tk.Label:
        """
        Retrieve the next available label for computer or Onlineplayer.

        Parameters:
            is_gridded (bool): Optional. If True, only return a label that is currently gridded.
            If False, return the next label that hasnt been gridded.
        """
        preferred_label = (
            self._onlinep_labels.values()
            if self._onlinePlayerActive
            else self._computer_labels.values()
        )
        if is_gridded:
            return next((label for label in preferred_label if label.grid_info()))
        else:
            return next((label for label in preferred_label if not label.grid_info()))

    def comp_card_streak(self, card_streak_no: int):
        """This Searches For Similar Cards In Computer's Cardstack And Plays It.
        (Specifically Streaks For When Computer Encounters An 8 0r 1 Card - The Hold On And Suspension Cards)
        """
        if self.__check_gameover:
            return

        found_card_streak_no = []
        for idx, i in enumerate(self._label_reference):
            if i and i[0][1][1] == card_streak_no:
                found_card_streak_no = [idx, i]
                self._label_reference.insert(idx, [])
                self._label_reference.pop(self._label_reference.index(i))
                logging.debug(f"found a card streak --> {found_card_streak_no}")
                break

        self.set_player_turn("comp")

        if found_card_streak_no:
            self.computer_play(found_card_streak_no[1])

        else:
            # Computer's continue has to be after it plays a non streak card
            self._root.after(self.COMP_PLAY_DELAY // 2, self.compPlayEngine)

            self._root.after(
                int(self.COMP_PLAY_DELAY // 1.6),
                lambda: self.popup_message("Continue", "Continue", 450),
            )
            self._root.after(self.COMP_PLAY_DELAY + 150, self.set_player_turn, "p2")

    def comp_mart(self, gone_to_mart_before=False):
        """Responsible for making the computer to go to market (pick a card from the mart)
        The 'gone_to_mart_before' argument checks whether the `self._computer.gomart` has beeen called before
        """

        if not self.get_player_turn("comp") or self.__check_gameover:
            return

        for o, i in enumerate(self._label_reference):
            if i:
                continue
            if not gone_to_mart_before:
                self._computer.gomart()
            self._label_reference[o].append(self._computer.cards()[-1])

            new_lab = self.comp_op_get_next_available_label(is_gridded=False)
            self.animate_widget_clicked(self._market_btn)
            new_lab.configure(image=self._misc_whot1)
            self._root.after(200, self.insert_widget_at_first_column, new_lab)
            break

        self.display_number_of_cards("computer")
        self.set_player_turn("p2")
        self.repopulate_containers()
        self._root.title(self._title)

    def computer_request_card_with_20(
        self, card: tuple[tk.PhotoImage, tuple[str, int]]
    ):
        """Finds a viable (powerup) card to request from player2 after computer plays the Whot 20 card"""

        if card[1][1] != 20 or len(self._computer.cards()) == 0:
            return

        found_viable_card, idx = "", None

        for idx, i in enumerate(self._label_reference):
            if not i:
                continue
            if i[0][1][1] in [1, 2, 8, 14] and i[0][1][0] != "Whot":
                found_viable_card = i[0][1][0]
                break

        if not found_viable_card:
            f = next(
                (
                    (idx, i)
                    for idx, i in enumerate(self._label_reference)
                    if i and i[0][1][0] != "Whot"
                )
            )
            idx, found_viable_card = f[0], f[1][0][1][0]

        # there'll always be a viable card, else tis game over!
        logging.debug(
            f'found_viable_card for comp, setting self._whot.requests["computer"] to {found_viable_card}...'
        )
        self._whot.requests["computer"] = found_viable_card
        self._root.title(f"{self._title} - Request {found_viable_card.upper()}")

        self._computer.requested_card_idx = idx
        logging.debug(
            f"computer requested card idx: {self._computer.requested_card_idx}"
        )
        logging.debug(f"computer request and requests --> {self._whot.requests}")
        self.message_box("Request", f"I NEED {found_viable_card.upper()}")

    def computer_response_to_card_20(self):
        """Generates the computer's appropriate response to the requested
        whot card 20 by player2"""

        if not self.get_player_turn("comp") or self.__check_gameover:
            return

        card = self._whot.requests["player2"]
        found_request = []

        for o, i in enumerate(self._label_reference):
            if i and i[0][1][0] == card:
                found_request.append([o, i])
                self._label_reference.insert(o, [])
                self._label_reference.pop(self._label_reference.index(i))
                break

        if found_request:
            logging.debug("Computer is playing p2 request rn...")
            # * The play function should clear p2 request
            self.computer_play(found_request[0][1])
            found_request.clear()
            return

        else:
            logging.debug("computer doesnt have the card going to mart")
            self.apply_difficulty()  # * The mart func will also clear p2 request

    def _mainloop(self):
        """calls tk mainloop"""
        self._root.focus_set()
        self._root.mainloop()


if __name__ == "__main__":
    app = Whot()
    app._mainloop()
