import tkthread
tkthread.patch()
import tkinter as tk
import customtkinter as ctk
from tktooltip import ToolTip
from manual import manual
from GameImages import images
import Main
import socketServer, socketClient
from random import choice
import tkinter.messagebox as tmb
import time, threading, queue, os
import pickle, json
from typing import Literal
from icecream import ic
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')#, datefmt='%H:%M:%S')


class Whot(images):
    """Naija Whot Game in Grand Style - By Genesis Chrome"""

    def __init__(self):
        self._root = ctk.CTk()
        # self._orig_size = '760x690+592+7' #'650x690+706+6'  # 760x690+592+7'
        self._root.geometry('650x690+706+6')
        self._root.minsize(610, 690)
        self._title = 'Whot Game'
        self._root.title(self._title)
        self._root.protocol("WM_DELETE_WINDOW", self.__exit)
        super().__init__()

        ctk.set_appearance_mode('light')
        self.font_style = ('Comic Sans Ms bold', 17)
        self.smaller_font = (self.font_style[0], self.font_style[1]-4)

        self._config: dict[str, str | bool | dict[str, str | int]] = {}
        self.load_config_file()


        self._playedcard_curr_xy: tuple[float, float] = (0, 0)
        self._animated_images: list[int] = []
        self._animated_img_rectangles: list[int] = []

        self._player2_frame = ctk.CTkScrollableFrame(
            self._root,
            orientation='horizontal',
        )
        self._comp_frame = ctk.CTkScrollableFrame(
            self._root,
            orientation='horizontal',
        )
        self._played_frame = ctk.CTkCanvas(
            self._root, 
            background="#252526" if ctk.get_appearance_mode().lower() == 'dark' else "#E7E7E7", 
            highlightthickness=0,
        )
        self._played_frame.place(relx=0.014, rely=0.354, relheight=0.288, relwidth=0.974)
        
        self._played_frame.bind('<Configure>', self.rearrange_playedimages_onresize)
        ###################################################################
        # Main Initialisations
        ###################################################################
        self._whot = Main.Whot()
        self._whot.InitDepot()
        self._whot.InitPlayerCards()
        self._whot.InitComputerCards()
        self._whot.InitPlayer2Cards()
        self._computer = Main.Computer()
        self._player2 = Main.Player2()
        self._onlinep = Main.OnlinePlayer()
        self._whot.NormCards()

        self._onlinePlayerActive = False
        self._onlineServer: socketServer.Server = None
        self._onlineClient: socketClient.Client = None

        self._server_choice = None
        self._onlineNickname = ''
        self._connectionFailed = False

        self._onlinep_todo = {
            'pick_two': 0,
            'general_market': 0,
            'hold_on': False,
            'suspension': False,
        }

        self._delay_multiplayer_for_animations = True
        ###################################################################

        ##################################################################
        # To Check who played last
        ##################################################################
        self.__check_p2_played = False
        self.__checkcomp_played = False
        self.__checkop_played = False

        self.__current_player = None
        ##################################################################

        ##################################################################
        # Check Pick two, General market and checkmate
        ##################################################################
        self.__check_gameover = False

        self._check2 = 0
        self._check1 = 0

        ####################################################################
        # Computer Engine's (CompPlayEngine) containers
        ####################################################################
        self._found_str = []
        self._found_num = []
        self._found_20 = []
        self._found_request = []

        self.COMP_PLAY_DELAY = 500
        self.initialize_card_graphics()

        #####################################################################################
        # Menu
        #####################################################################################
        menu_bar = tk.Menu(self._root)
        about_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label='About', menu=about_menu)
        about_menu.add_command(label='Manual', accelerator='Ctrl+M', compound='left', command=self.Manual)

        game_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label='Game', menu=game_menu)
        game_menu.add_command(label='Restart Game', accelerator='Ctrl+R', compound='left', command=self.__restart)

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label='Setting', menu=settings_menu)
        settings_menu.add_command(label='Settings', accelerator='Ctrl+S', compound='left', command=self.settings)

        multiplayer_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label='Multiplayer', menu=multiplayer_menu)
        multiplayer_menu.add_command(label='Multiplayer', accelerator='Ctrl+Shift+M', compound='left',
                                     command=self.start_multiplayer_server_client)

        self._root.config(menu=menu_bar)
        ####################################################################################
        # Grids
        ####################################################################################
        self._player2_frame.place(relx=0.014, rely=0.648, relheight=0.297, relwidth=0.974)
        self._comp_frame.place(relx=0.014, rely=0.057, relheight=0.293, relwidth=0.974)
        ################################################################################################################
        # Card Length Widgets
        ################################################################################################################
        p2_card_length, comp_card_length = len(self._player2.cards()), len(self._computer.cards())
        self._comp_cards_left = ctk.CTkLabel(
            self._root,
            height=38,
            width=270,
            text=f'Number of computer cards: {comp_card_length}',
            font=self.font_style
        )
        self._p2_cards_left = ctk.CTkLabel(
            self._root,
            height=38,
            width=230,
            text=f'Number of your cards: {p2_card_length}',
            font=self.font_style
        )
        self._p2_cards_left.place(relx=0.0, rely=0.943)
        self._comp_cards_left.place(relx=0.0, rely=0.0)

        #################################################################################################################
        # Turn Indicators
        #################################################################################################################
        self._p2_turn_indicator = ctk.CTkLabel(
            self._root,
            height=38,
            width=159,
            text='Player',
            font=self.font_style
        )
        self._comp_turn_indicator = ctk.CTkLabel(
            self._root,
            height=38,
            width=159,
            text='Computer',
            font=self.font_style
        )
        self._p2_turn_indicator.place(relx=0.778, rely=0.942)
        self._comp_turn_indicator.place(relx=0.778, rely=0.0)

        ####################################################################################
        # Who Plays First and Turn Indicator
        ####################################################################################
        who_plays_first = ('player2', 'computer')
        final_choice = (choice(who_plays_first))
        if final_choice == 'player2':
            self.set_player_turn('p2')
        else:
            self.set_player_turn('comp')
        print(f'choice is: {final_choice}')

        self.__current_player = final_choice

        self._name_entry = ctk.CTkEntry(self._root)  #Entry for self.set_name()
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
            'Chartreuse': '#7FFF00',
            'Bright Green': '#000fff000',
            'Royal Blue': 'royal blue',
            'Dodger Blue': 'dodger blue',
            'Aquamarine': 'Aquamarine',
            'Default': '#d9d9d9',  # Light gray
            'Yellow': 'yellow',
            'Magenta': 'magenta',
            'Gold': 'gold',
            'Red': 'red',
            'Dark Violet': 'dark violet',
            'Pink': 'pink',
            'Black': 'black',
            'Orange': '#FFA500',
            'Olive': '#808000',
        }

        config_theme = self._config.get('theme', 'Default')
        self._theme_var.set(config_theme)
        self.set_theme()
        ####################################################################################
        # Update n Run
        ####################################################################################
        if self._config.get('show_setting'):
            self._root.after(1500, self.settings)
        self._difficulty_var.set(self._config.get('mode'))

        self._root.after(5800, self.compPlayEngine)
        self._root.after(1200, lambda: self.display_cards_animation([self._player2_btns[i] for i in range(5)]))
        ##################################################################################
        # Binding's
        ##################################################################################
        self._root.after(6000, self.root_bindings)
        self.balloon_bindings()
        self.bind_right_left_keys_to_p2_scrollable_frame(0.1)
        ####################################################################################
        # END
        ####################################################################################

    def balloon_bindings(self):
        """Balloon Tooltip Bindings"""
        return
        for btn in self._depot_p2_btns:
            ToolTip(btn, msg=f"{self._config.get('name')}'s Cards")

        if not self._onlinePlayerActive:
            for label in self._depot_comp_labels:
                ToolTip(label, msg="Computer's Cards")
        else:
            op_name = self._onlineNickname if self._onlineNickname else 'OnlinePlayer'
            for label in self._depot_onlinep_labels:
                ToolTip(label, msg=f"{op_name}'s Cards")
        ToolTip(self._market_btn, msg="Click To Go To Mart")


    def root_bindings(self):
        self._root.bind_all("<Control-m>", self.Manual)
        self._root.bind_all("<Control-r>", lambda event: self.__restart())
        self._root.bind("<Control-M>", self.start_multiplayer_server_client)
        self._root.bind("<Control-s>", self.settings)
        self.bind_return(method='mart')
        self._root.bind_all("<F11>", lambda event: self._root.state('zoomed'))
        self._root.bind_all("<Escape>", lambda event: self._root.state('normal'))
    
    def bind_return(self, method: Literal['mart', 'pick_two', 'pick_one']) -> None:
        if method == 'mart':
            self._root.bind("<Return>", lambda event: self.p2_mart(event=event))
        elif method == 'pick_two':
            self._root.unbind("<Return>")
            self._root.bind("<Return>", lambda event: self.check_p2_picked_two_cards(event=event))
        elif method == 'pick_one':
            self._root.unbind("<Return>")
            self._root.bind("<Return>", lambda event: self.check_p2_picked_a_card(event=event))

    def bind_right_left_keys_to_p2_scrollable_frame(self, X_INCREMENT=0.1):
        def scroll_right(event):
            x = self._player2_frame._parent_canvas.xview()[0]
            x += X_INCREMENT
            self._player2_frame._parent_canvas.xview_moveto(x)
        def scroll_left(event):
            x = self._player2_frame._parent_canvas.xview()[0]
            x -= X_INCREMENT
            self._player2_frame._parent_canvas.xview_moveto(x)

        self._player2_frame.bind_all('<Right>', scroll_right)
        self._player2_frame.bind_all('<Left>', scroll_left)


    def display_cards_animation(self, p2_btns: list[tk.Button]):
        preferred_labels = (self._onlinep_labels 
                            if self._onlinePlayerActive 
                            else self._computer_labels)

        self._root.after(3700, lambda: setattr(self, '_delay_multiplayer_for_animations', False))

        [card.config(state='disabled') for card in p2_btns]

        btn_duration = 50
        for btn, column in zip(p2_btns, range(1001, 1006)):
            self._root.after(btn_duration, lambda b=btn, c=column: b.grid(row=0, column=c, padx=6, pady=6))
            btn_duration += 250

        self._root.after(1500, self.create_playedcard_image)

        lab_duration = 2000
        for ref_no, column in zip(range(5), range(1001, 1006)):
            self._root.after(
                lab_duration,
                lambda r=ref_no, c=column: preferred_labels[r].grid(row=0, column=c, padx=6, pady=6))
            lab_duration += 200

        for card in p2_btns:
            self._root.after(3500, lambda c=card: (
                c.config(state='normal'),
                self._market_btn.configure(state='normal')
            ))

    def load_config_file(self):
        try:
            with open('./config.pkl', 'rb') as config_file:
                self._config = pickle.load(config_file)
        except (FileNotFoundError, EOFError, pickle.UnpicklingError):
            self._create_new_config_file()

    def _create_new_config_file(self):
        """Creates a new config file if the original one has been deleted/Truncated"""
        self._config = {
            'name': 'Genesis',
            'theme': 'Default',
            'mode': 'easy',
            'show_setting': True,
            'multiplayer': {
                'host': '127.0.0.1',
                'port': 55555,
                'nickname': 'Genesis',
                'server_choice': 'start server'
            }
        }

        with open('./config.pkl', 'wb+') as config_file:
            pickle.dump(self._config, config_file)

    def _write_config(
            self,
            data_type: str = None,
            data: str | bool = None,
            plain_save=False
    ):
        if not plain_save:
            self._config[data_type] = data

        with open('./config.pkl', 'wb+') as config_loc:
            pickle.dump(self._config, config_loc)

    def settings(self, event=None):
        """Settings for whot game"""
        top = self.create_toplevel_at_center(width=350, height=360)
        top.transient(self._root)
        top.title(f'{self._title} - Settings')
        top.resizable(False, False)

        root_tab = ctk.CTkTabview(top)

        root_tab.add('Themes')
        root_tab.add('Name')
        root_tab.add('Mode')

        self.choose_theme(root_tab.tab('Themes'), root=top)
        self.set_name(root_tab.tab('Name'))
        self.choose_difficulty_mode(root_tab.tab('Mode'))

        show_setting = ctk.CTkSwitch(
            top, 
            height=31,
            text='Show Setttings at startup',
            variable=self._show_setting_at_startup,
            font=self.smaller_font,
            command=lambda: self._write_config(
                'show_setting',
                self._show_setting_at_startup.get()
            )
        )
        disable_difficulty_modes = lambda: (
            setattr(self, '_game_started', True),
            top.destroy(), top.grab_release()
        )
        self._show_setting_at_startup.set(self._config.get('show_setting'))
        ok_btn = ctk.CTkButton(
            top, 
            height=25, 
            width=96,
            text='Ok', 
            command=disable_difficulty_modes
        )

        root_tab.place(relx=0.0, rely=0.0, relheight=0.909, relwidth=1.0)
        show_setting.place(relx=0.029, rely=0.923)
        ok_btn.place(relx=0.657, rely=0.923)
        top.protocol('WM_DELETE_WINDOW', disable_difficulty_modes)
        top.focus_set()
        top.grab_set()

    def choose_difficulty_mode(self, window: ctk.CTkFrame):
        """To choose the mode of the game, whether easy or hard"""

        hard_radbtn = ctk.CTkRadioButton(
            window,
            height=26,
            text='Hard',
            variable=self._difficulty_var,
            value='hard',
            font=self.smaller_font,
            command=lambda: self._write_config('mode', self._difficulty_var.get())
        )
        medium_radbtn = ctk.CTkRadioButton(
            window, 
            height=26,
            text='Medium',
            variable=self._difficulty_var,
            value='medium',
            font=self.smaller_font,
            command=lambda: self._write_config('mode', self._difficulty_var.get())
        )
        easy_radbtn = ctk.CTkRadioButton(
            window, 
            height=26,
            text='Easy',
            variable=self._difficulty_var,
            value='easy',
            font=self.smaller_font,
            command=lambda: self._write_config('mode', self._difficulty_var.get())
        )

        hard_radbtn.place(relx=0.376, rely=0.268)
        medium_radbtn.place(relx=0.376, rely=0.435)
        easy_radbtn.place(relx=0.376, rely=0.602)

        ctk.CTkLabel(
            window, 
            height=57, 
            width=290,
            text='Choose Desired Mode',
            font=self.font_style
        ).place(relx=0.07, rely=0.033)
        ctk.CTkLabel(
            window, 
            height=26, 
            width=180,
            text='(Can Only Be Set Once Per Game Session)',
            font=self.smaller_font
        ).place(relx=0.135, rely=0.769)
        window.focus_set()

        if self._game_started:
            [rbtn.configure(state='disabled') for rbtn in [hard_radbtn, medium_radbtn, easy_radbtn]]

    def create_toplevel_at_center(
            self, 
            width: int, 
            height: int,
            display_delay = 300
        ) -> ctk.CTkToplevel:
        self._root.update()
        toplevel = ctk.CTkToplevel(self._root)
        toplevel.update_idletasks()
        toplevel.withdraw()

        root_width = self._root.winfo_width()
        root_height = self._root.winfo_height()
        x = self._root.winfo_x() + (root_width - width) // 2
        y = self._root.winfo_y() + (root_height - height) // 2
        toplevel.geometry(f'{width}x{height}+{x}+{y}')
        self._root.after(display_delay, toplevel.deiconify)
        self._root.after(display_delay+10, self.redraw_window_if_still_withdrawn, toplevel)

        return toplevel

    def redraw_window_if_still_withdrawn(self, toplevel: ctk.CTkToplevel):
        if not toplevel.winfo_exists():
            return
        if toplevel.state() == 'withdrawn':
            toplevel.deiconify()
        self._root.after(10, self.redraw_window_if_still_withdrawn, toplevel)

    def get_actual_theme(self, for_text=False) -> str | tuple[str, str]:
        """
        Get the theme color used by the application.

        Args:
            for_text (bool): Whether the theme is for text or not.
            will return `(black, white)` if theme is `Default` and `for_text` is True.
        """
        theme = self._theme_var.get()
        if for_text and theme == 'Default':
            return ('black', 'white')
        return self._themes_dict[theme]

    def choose_theme(self, window: ctk.CTkFrame, root: ctk.CTkToplevel):
        """For choosing desired theme from the themes list"""

        window = ctk.CTkScrollableFrame(window)
        window.place(relx=0.0, rely=0.0, relheight=0.997, relwidth=0.994)

        ctk.CTkLabel(
            window, 
            height=39, 
            width=280,
            text="Select Theme:",
            font=self.font_style
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
                command=self.set_theme
            )
            rbtn.grid(
                row=(o // num_per_row) + 1, 
                column=o % num_per_row, 
                padx=padx, 
                pady=pady, 
                sticky="w"
            )
            theme_radbtns.append(rbtn)

        root.bind("<Down>", lambda event: self.scroll_theme('down'))
        root.bind("<Up>", lambda event: self.scroll_theme('up'))


    def scroll_theme(self, action: Literal['down', 'up']):
        value = self._theme_var.get()
        theme_keys = list(self._themes_dict.keys())
        current_index = theme_keys.index(value)

        if action == 'down':
            next_index = (current_index + 1) % len(theme_keys)
            next_theme = theme_keys[next_index]
            self._theme_var.set(next_theme)
            self.set_theme()

        if action == 'up':
            prev_index = (current_index - 1) % len(theme_keys)
            prev_theme = theme_keys[prev_index]
            self._theme_var.set(prev_theme)
            self.set_theme()

    def set_theme(self):
        preferred_depot_labels = (self._depot_onlinep_labels
                            if self._onlinePlayerActive
                            else self._depot_comp_labels)
        color = self._theme_var.get()

        if color not in self._themes_dict:
            self._write_config('theme', 'Default')
            return

        theme_color = self.get_actual_theme()

        try:
            self._root.option_add('*foreground', theme_color)
            for btn_lab in preferred_depot_labels + self._depot_p2_btns:
                btn_lab.configure(bg=theme_color)
            
            self.create_playedcard_image(from_theme=True)
            self._market_btn.configure(bg=theme_color)
            self._comp_cards_left.configure(text_color=theme_color)
            self._p2_cards_left.configure(text_color=theme_color)

            text_theme_color = self.get_actual_theme(for_text=True)
            self._comp_cards_left.configure(text_color=text_theme_color)
            self._p2_cards_left.configure(text_color=text_theme_color)

            self._write_config('theme', color)
            self._name_entry.configure(text_color=text_theme_color)
        except tk.TclError as e:
            print(e)

    def popup_message(
            self,
            title: str,
            text: str,
            duration: int = 900,
            wraplength: int = 140
    ) -> None:
        """Displays popup message containing information for 1 sec approx,
          (or the `duration` arg specification)"""
        top = self.create_toplevel_at_center(width=250, height=50, display_delay=150)
        top.grab_set()
        top.focus_set()
        top.transient(self._root)
        top.title(title.upper())

        theme = self.get_actual_theme(for_text=True)

        ctk.CTkLabel(
            top, 
            text=text, 
            text_color=theme, 
            font=self.font_style,
            padx=20, 
            pady=20, 
            wraplength=wraplength
        ).pack(fill='both', expand=True)

        top.after(duration, top.destroy)

    def set_name(self, window: ctk.CTkFrame):
        """Gets desired name from player"""
        theme = self.get_actual_theme(for_text=True)
        former_name = self._config.get('name')
        entry_var = tk.StringVar(value=former_name)

        name_label = ctk.CTkLabel(
            window,
            height=57, 
            width=225,
            text='Enter Desired Name:',
            font=self.font_style
        )
        name_label.place(relx=0.170, rely=0.067)

        self._name_entry = ctk.CTkEntry(
            window,
            textvariable=entry_var,
            font=self.font_style,
            text_color=theme,
            justify='center'
        )
        self._name_entry.place(relx=0.173, rely=0.334, relheight=0.104, relwidth=0.653)

        save_button = ctk.CTkButton(
            window,
            height=35, 
            width=96,
            text='Save',
            font=self.font_style,
            command=lambda: self.save_name_cmd(entry_var)
        )
        save_button.place(relx=0.347, rely=0.669)


    def save_name_cmd(self, name: tk.StringVar):
        """Sets (Registers) the desired name to the configuration file"""
        if name.get():
            self._write_config('name', name.get())
            # self.popup_message(
            #     title='Name Saved', 
            #     text=f'{name.get()} has been saved successfully...', 
            #     duration=400, 
            #     wraplength=200
            # )
            self.update_turn_indicator()
            self.balloon_bindings()

    def switch_player_turn(self):
        player2, computer, onlinep = ['player2', 'p2'], ['computer', 'comp'], ['onlinep', 'op']
        if not self._onlinePlayerActive:
            if self.__current_player in player2:
                self.__current_player = 'computer'
                self.set_player_turn('comp')
            elif self.__current_player in computer:
                self.__current_player = 'player2'
                self.set_player_turn('p2')
        else:
            if self.__current_player in player2:
                self.__current_player = 'onlineplayer'
                self.set_player_turn('op')
            elif self.__current_player in onlinep:
                self.__current_player = 'player2'
                self.set_player_turn('p2')

    def set_player_turn(self, player: Literal['comp', 'p2', 'op']):
        """Sets player's turn"""

        if player == 'comp':
            self.__checkcomp_played = False
            self.__check_p2_played = True

        elif player == 'p2':
            self.__check_p2_played = False
            if not self._onlinePlayerActive:
                self.__checkcomp_played = True
            else:
                self.__checkop_played = True

        elif player == 'op':
            self.__checkop_played = False
            self.__check_p2_played = True

        self.update_turn_indicator()

    def get_player_turn(self, player: Literal['comp', 'p2', 'op']) -> bool:
        """Return bool value for the valid player to play first or next"""
        if player == 'comp':
            return self.__check_p2_played

        elif player == 'p2':
            if self._onlinePlayerActive:
                return self.__checkop_played
            return self.__checkcomp_played

        elif player == 'op':
            return self.__check_p2_played

        return False

    def update_turn_indicator(self):
        p2_turn = self.get_player_turn('p2')
        comp_turn = self.get_player_turn('comp')
        op_turn = self.get_player_turn('op')

        if p2_turn and not comp_turn:
            self._p2_turn_indicator.configure(text_color='#000fff000')
            self._comp_turn_indicator.configure(text_color='red')

        elif comp_turn and not p2_turn and not self._onlinePlayerActive:
            self._p2_turn_indicator.configure(text_color='red')
            self._comp_turn_indicator.configure(text_color='#000fff000')

        # since its op's turn, we'll use comp's widgets to display the turn indicator
        elif op_turn and not p2_turn:
            self._p2_turn_indicator.configure(text_color='red')
            self._comp_turn_indicator.configure(text_color='#000fff000')

        # Set names
        p2_name = self._config.get('name').capitalize()
        self._p2_turn_indicator.configure(text=p2_name)
        if self._onlinePlayerActive:
            op_name = self._onlineNickname if self._onlineNickname else 'OnlinePlayer'
            op_name = op_name.capitalize()
            self._comp_turn_indicator.configure(text=op_name)
        else:
            self._comp_turn_indicator.configure(text='Computer')


    def display_number_of_cards(self, player: Literal['computer', 'player2', 'onlinep']):
        """Display number of cards left/remaining for the player"""
        if player == 'computer':
            no_of_cards = len(self._computer.cards())
            text = 'Last Card...' if no_of_cards == 1 else f"Number of computer cards : {no_of_cards}"
            self._comp_cards_left.configure(text=text)

        elif player == 'player2':
            no_of_cards = len(self._player2.cards())
            text = 'Last Card...' if no_of_cards == 1 else f"Number of your cards : {no_of_cards}"
            self._p2_cards_left.configure(text=text)

        elif player == 'onlinep':
            no_of_cards = len(self._onlinep.cards())
            if self._onlineNickname and self._onlinePlayerActive:
                text = 'Last Card...' if no_of_cards == 1 else f"Number of {self._onlineNickname}'s cards : {no_of_cards}"
            else:
                text = 'Last Card...' if no_of_cards == 1 else f"Number of your cards : {no_of_cards}"
            self._comp_cards_left.configure(text=text)

    def repopulate_containers(self, onlinePlayer=False):
        """Repopulates by appending one more container (list) to the Button | Label references and
         one more Button | Label to the depots after the reference containers have all been filled up"""

        used_p2_containers = [ref for ref in self._btn_reference if ref]
        used_comp_containers = [ref for ref in self._label_reference if ref]

        p2_full = len(used_p2_containers) == len(self._btn_reference)
        comp_full = len(used_comp_containers) == len(self._label_reference)

        if not p2_full and not comp_full:  # Empty containers present: all good
            return

        # No empty containers: have to add some
        self._btn_reference.append([])
        self._label_reference.append([])

        self._depot_p2_btns.append(tk.Button(self._player2_frame))
        self._player2_btns[max(self._player2_btns) + 1] = self._depot_p2_btns[-1]

        if not onlinePlayer:
            self._depot_comp_labels.append(tk.Label(self._comp_frame))
            self._computer_labels[max(self._computer_labels) + 1] = self._depot_comp_labels[-1]
        else:
            self._depot_onlinep_labels.append(tk.Label(self._comp_frame))
            self._onlinep_labels[max(self._onlinep_labels) + 1] = self._depot_onlinep_labels[-1]
        self.set_theme()  # Sets the theme for the newly added widgets


    def player2_play(
            self,
            card: list[tuple[tk.PhotoImage, tuple[str, int]]],
            card_display_btn: tk.Button,
            event=None
    ):
        """For player2 (actual player) to play his or her valid card"""
        if self.__check_gameover:
            return

        if self.get_player_turn('p2'):
            try:
                if self._player2.play(card[0]):
                    player = 'op' if self._onlinePlayerActive else 'comp'
                    self.set_player_turn(player)
                    self.p2_request_card_with_20(card)
            
                    self.move_card(
                        card[0][0], 
                        self._player2_frame._parent_canvas, 
                        self._played_frame, 
                        card_display_btn,
                        from_above=False
                    )

                    if not self._onlinePlayerActive:
                        card_display_btn.after(self.COMP_PLAY_DELAY, self.compPlayEngine)
                    else:
                        self._onlineClient.send_data(card[0][1], 'CARD')

                    # card_display_btn.grid_forget()
                    card.clear()

                    self.display_number_of_cards('player2')
                    self.pick_two(player)
                    self.go_gen_mart(player)
                    self.hold_on(player)
                    self.suspension(player)

                    self.gameover()
            except Main.WhotException as e:
                tmb.showwarning(title="INVALID MOVE", message=str(e).upper())
        else:
            tmb.showinfo("Not Your Turn", "Its not your turn to play")


    def p2_mart(self, power: int = None, event=None):
        """Responsible for making player2 to go to market (pick a card from the market)"""

        if not self.get_player_turn('p2') or self.__check_gameover:
            return

        if power:
            if power == 2:
                self._check2 += 1
            elif power == 1:
                self._check1 += 1

        for o, i in enumerate(self._btn_reference):
            if i:
                continue
            self._player2.gomart()
            self._btn_reference[o].append(self._player2.cards()[-1])
            new_btn = self._player2_btns.get(o)

            if event: #When we hit ENTER <RETURN>
                self._market_btn.config(relief='sunken')
                self._root.after(100, lambda: self._market_btn.config(relief='raised'))

            new_btn.config(
                image=self._player2.cards()[-1][0],
                command=lambda: self.player2_play(
                    self._btn_reference[o], 
                    self._player2_btns[o]
                )
            )
            self._root.after(200, self.insert_widget_at_first_column, new_btn)

            if self._onlinePlayerActive:
                self._onlineClient.send_data('MARKET', 'MART')
            break

        self.display_number_of_cards('player2')
        self.set_player_turn('comp' if not self._onlinePlayerActive else 'op')
        self.repopulate_containers()

        if self._check2 == 1:
            self._root.title(f'{self._title} - PICK TWO')
        elif self._check2 == 0 or not self._check2:
            self._root.title(self._title)
            self._root.after(self.COMP_PLAY_DELAY, self.compPlayEngine)
        else:
            self._root.title(self._title)
            self._root.after(self.COMP_PLAY_DELAY, self.compPlayEngine)

    def check_p2_picked_two_cards(self, player='comp', event=None):
        """Checks whether player2 clicked the mart button twice (in other words, checks whether player2 has
        picked two cards) and then unfreezes player2 cards (buttons) - for PICK TWO"""

        player = 'comp' if not self._onlinePlayerActive else 'op'
        self.p2_mart(power=2, event=event)
        self.set_player_turn('p2')
        self._root.title(f'{self._title} - PICK TWO')

        if self._check2 == 2:  # Done picking two cards
            self.set_player_turn(player)
            [btn.config(state='normal') for btn in self._depot_p2_btns]
            self._check2 = 0
            self._market_btn.configure(command=self.p2_mart)
            self.bind_return(method='mart')
            self._root.title(self._title)

    def check_p2_picked_a_card(self, player='comp', event=None):
        """Checks whether player2 clicked the mart button once (in other words, checks whether player2 has
        picked one card) and then unfreezes player2 cards (buttons) - for GENERAL MARKET"""
        player = 'comp' if not self._onlinePlayerActive else 'op'
        self.p2_mart(power=1, event=event)
        if self._check1 == 1:
            self.set_player_turn(player)
            [btn.config(state='normal') for btn in self._depot_p2_btns]
            self._check1 = 0
            self._market_btn.configure(command=self.p2_mart)
            self.bind_return(method='mart')

    def p2_request_card_with_20(self, card: list[tuple[tk.PhotoImage, tuple[str, int]]]):
        """Player2 (actual player) demands a particular card from computer after playing whot 20"""

        if len(self._player2.cards()) == 0 or not card[0][1][1] == 20:
            return

        self.set_player_turn('p2')

        card_root = ctk.CTkToplevel(self._root)
        card_root.transient(self._root)
        x, y = self._root.winfo_x(), self._root.winfo_y()
        card_root.geometry(f'230x480+{x}+{y}')
        card_root.title("Ask for a card")
        card_root.resizable(False, False)

        label_theme = self.get_actual_theme(for_text=True)
        button_theme = self._themes_dict.get(self._theme_var.get())

        command = lambda card_name, toplev: self._p2_clicked_card(card_name, toplev)

        card_buttons = [
            ('Cross', self._cross_icon),
            ('Circle', self._circle_icon),
            ('Star', self._star_icon),
            ('Triangle', self._triangle_icon),
            ('Square', self._square_icon)
        ]

        for i, (card_name, icon) in enumerate(card_buttons):
            button = tk.Button(
                card_root, 
                image=icon, 
                command=lambda i=i: command(card_buttons[i][0], card_root),
                bg=button_theme)
            button.grid(row=i, column=0, pady=3, padx=15)
            ctk.CTkLabel(
                card_root, 
                text=card_name, 
                text_color=label_theme,
                font=self.smaller_font
            ).grid(row=i, column=1)

        ctk.CTkLabel(
            card_root, 
            text='Choose Desired Card', 
            text_color=label_theme,
            font=self.font_style
        ).place(relx=0.13, rely=0.896)

        card_root.protocol('WM_DELETE_WINDOW', lambda: self._p2_clicked_card(None, card_root))
        card_root.focus_set()
        card_root.grab_set()

    def _p2_clicked_card(self, card: str, window: ctk.CTkToplevel):
        """Registers player2's Desired card and calls player1 (computer or OP) to respond to the request"""
        window.destroy()
        [btn.config(state='normal') for btn in self._depot_p2_btns]
        self._market_btn.configure(state='normal')
        window.grab_release()

        player = 'comp' if not self._onlinePlayerActive else 'op'
        self.set_player_turn(player)
        if not card:
            self._root.after(500, self.compPlayEngine)
            return
        
        if not self._onlinePlayerActive:
            self._whot.requests['player2'] = card
            # TODO
            self._player2.requested_card = card
            self._root.after(500, self.computer_response_to_card_20)
        else:
            self._onlineClient.send_data(card, data_type='REQUEST')

    # ----------------------------------------------------------------------------------------------------
    def create_playedcard_image(self, from_theme=False):
        played_canvas = self._played_frame
        image = self._whot.PlayedCards()[-1][0]
        theme = self.get_actual_theme()

        if from_theme:
            # [played_canvas.delete(img) for img in self._animated_images]
            [played_canvas.delete(rect) for rect in self._animated_img_rectangles]
            self._animated_img_rectangles.clear()

        x, y = self._playedcard_curr_xy
        image_id = played_canvas.create_image(x, y, image=image)
        image_id_rect = played_canvas.create_rectangle(
            *played_canvas.bbox(image_id), 
            outline=theme, 
            width=2
        )
        self._animated_images.append(image_id)
        self._animated_img_rectangles.append(image_id_rect)
    
    def move_card_(
        self,
        card_image: tk.PhotoImage, 
        player_canvas: tk.Canvas, 
        played_canvas: tk.Canvas, 
        widget: tk.Button | tk.Label,
        from_above=True
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

        # Calculate the initial offset for the card in the X direction
        offset_x = len(self._animated_images) * 2  # Adjust the offset as needed

        # Calculate the maximum allowed offset to stay within frame in the X direction
        max_offset_x = played_canvas.winfo_width() - card_image.width()

        # Set a threshold to determine when to push the stack rightward
        threshold = 470  # Adjust as needed

        if offset_x >= 25:
            self._animated_images
            [played_canvas.delete(img) for img in self._animated_images]
            self._animated_images.clear()
            self.create_playedcard_image()
            return
            # [played_canvas.delete(img) for img in self._animated_images[:-2]]
            # self._animated_images = self._animated_images[-2:]
            # played_canvas.after()

        if offset_x > max_offset_x - threshold:
            # If the offset in the X direction is close to the right edge, push the stack rightward
            offset_x = max_offset_x - abs(threshold)
        x_offset = min(offset_x, max_offset_x)

        x2, y2 = self._playedcard_curr_xy

        card = played_canvas.create_image(x1 + x_offset, y1, image=card_image)
        self._animated_images.append(card)

        # Animate the new card
        self.animate_frame(0, x1 + x_offset, y1, x2 + x_offset, y2, card, played_canvas, player_canvas)


    def move_card(
        self,
        card_image: tk.PhotoImage, 
        player_canvas: tk.Canvas, 
        played_canvas: tk.Canvas, 
        widget: tk.Button | tk.Label,
        from_above=True
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

        theme = self.get_actual_theme()
        card = played_canvas.create_image(x1, y1, image=card_image)
        card_rectangle = played_canvas.create_rectangle(*played_canvas.bbox(card), outline=theme, width=2)
        self._animated_images.append(card)
        self._animated_img_rectangles.append(card_rectangle)
        
        played_canvas.tag_raise(card)
        self.animate_frame(0, x1, y1, x2, y2, card, card_rectangle, played_canvas, player_canvas)


    def animate_frame(
        self,
        frame: int, 
        x: int, 
        y: int, 
        target_x: float, 
        target_y: float, 
        card: int,
        card_rectangle: int, 
        played_canvas: ctk.CTkCanvas, 
        player_canvas: ctk.CTkCanvas,
        NUM_FRAMES = 50,
        FRAME_DURATION = 10
    ):
        
        if frame < NUM_FRAMES:
            dx = (target_x - x) / NUM_FRAMES * 5
            dy = (target_y - y) / NUM_FRAMES * 5
            played_canvas.coords(card, x, y)
            played_canvas.coords(card_rectangle, *played_canvas.bbox(card))
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
                card_rectangle, 
                played_canvas, 
                player_canvas
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

        for img, rect in zip(self._animated_images, self._animated_img_rectangles):
            self._played_frame.coords(img, x, y)
            self._played_frame.coords(rect, *self._played_frame.bbox(img))
        self._playedcard_curr_xy = x, y

    def animate_widget_clicked(self, widget: tk.Button | tk.Label):
        """Animates the widget as being clicked"""
        widget.config(relief='sunken')
        self._root.after(200, lambda: widget.config(relief='raised'))

    def insert_widget_at_first_column(self, widget: tk.Button | tk.Label):
        """
        Inserts a widget at the first column in the grid layout.
        For either player2 or computer (onlineplayer) frame
        """
        def increment_column(grid_info):
            return grid_info['column'] + 1 if grid_info else None

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

    def generate_shuffle_seed(self):
        return int.from_bytes(os.urandom(4), 'big')

    def reinitialize_cards(
            self,
            onlinePlayer=False,
            shuffle_seed: int = None,
            conn_type='server',
            player_turn: str = None ,
            prev_onlinep=False
    ):
        self._onlinePlayerActive = onlinePlayer

        if prev_onlinep:
            self._title = 'Whot Game'
            self.update_turn_indicator()
            self._multiplayer_indicator.place_forget()
            self._multiplayer_switch.place_forget()

        self._root.title(self._title)

        [btn.grid_forget() for btn in self._depot_p2_btns]
        [lab.grid_forget() for lab in self._depot_comp_labels]
        try:
            [lab.grid_forget() for lab in self._depot_onlinep_labels]
        except AttributeError as e:
            ic(e)

        self._market_btn.place_forget()
        self._played_frame.delete('all')
        self._animated_images.clear()
        self._animated_img_rectangles.clear()

        if shuffle_seed:
            self._whot = Main.Whot(shuffle_seed)
        else:
            self._whot = Main.Whot()
        self._computer = Main.Computer()
        self._player2 = Main.Player2()
        self._onlinep = Main.OnlinePlayer()

        self._whot.InitDepot()
        self._whot.ResetRequests()
        self._whot.InitPlayerCards(onlinePlayer, conn_type)
        self.__check_gameover = False

        if onlinePlayer:
            self._whot.InitOnlinePlayerCards()
        else:
            self._whot.InitComputerCards()
        self._whot.InitPlayer2Cards()
        self._whot.NormCards()

        self.initialize_card_graphics(onlinePlayer=onlinePlayer)
        self._root.after(5000, self.compPlayEngine) if not onlinePlayer else None
        self.display_cards_animation([self._player2_btns[i] for i in range(5)])
        self.display_number_of_cards('player2')
        self.display_number_of_cards('onlinep') if onlinePlayer else self.display_number_of_cards('computer')
        self.balloon_bindings()
        self.root_bindings()

        if not player_turn:
            player_turn = 'p2' if choice(('player2', 'onlinep')) == 'player2' else 'op'
        self.__current_player = player_turn
        self.set_player_turn(player_turn)
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

        #---------------------------------------------------------------------------
        # Initialize and Display Player2 Buttons and Sync with their Button references (Butrefs)
        #-------------------------------
        self._btn_reference = [[] for _ in range(30)]
        self._depot_p2_btns = [tk.Button(self._player2_frame) for _ in range(30)]

        self._player2_btns = {i: self._depot_p2_btns[i] for i in range(30)}
        player2_cards = self._player2.cards()

        for i in range(5):
            self._btn_reference[i].append(player2_cards[i])
            self._player2_btns[i].config(
                image=player2_cards[i][0],
                command=lambda i=i: self.player2_play(self._btn_reference[i], self._player2_btns[i])
            )
        #----------------------------------------------------------------------------
        
        #----------------------------------------------------------------------------
        # Initialize for onlineplayer
        #----------------------------
        if onlinePlayer:
            self._label_reference = [[] for _ in range(30)]
            self._depot_onlinep_labels = [tk.Label(self._comp_frame, relief='raised') for _ in range(30)]

            self._onlinep_labels = {i: self._depot_onlinep_labels[i] for i in range(30)}
            for i in range(5):
                self._onlinep_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._onlinep.cards()[i])
            
        #----------------------------------------------------------------------------

        #----------------------------------------------------------------------------
        # Initialize for computer
        #-------------------------
        else:
            self._label_reference = [[] for _ in range(30)]
            self._depot_comp_labels = [tk.Label(self._comp_frame, relief='raised') for _ in range(30)]

            # Initialize and Display Computer Labels and Sync with their Label references (Labrefs)
            self._computer_labels = {i: self._depot_comp_labels[i] for i in range(30)}
            for i in range(5):
                self._computer_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._computer.cards()[i])
        #-------------------------------------------------------------------------------        
        self._market_btn = tk.Button(
            self._played_frame,
            image=self._misc_whot,
            command=self.p2_mart, 
            state='disabled'
        )
        self._market_btn.place(relx=0.027, rely=0.10)
        if onlinePlayer:
            self._other_client_connected = False
            self._multiplayer_switch_var = tk.BooleanVar(value=True)
            self._multiplayer_switch = ctk.CTkSwitch(
                self._root,
                height=21,
                text='On/Off',
                font=self.smaller_font,
                onvalue=True,
                offvalue=False,
                variable=self._multiplayer_switch_var,
                command=self.terminate_multiplayer
            )
            self._multiplayer_switch.place(relx=0.414, rely=0.954)
            self._multiplayer_indicator = ctk.CTkLabel(
                self._root,
                height=21,
                width=84,
                text='Waiting...',
                font=self.smaller_font,
                text_color=self.get_actual_theme(for_text=True),
            )
            self._multiplayer_indicator.place(relx=0.559, rely=0.954)
        return
    
    def update_multiplayer_indicators(self):
        self._multiplayer_switch_var.set(True)
        self._multiplayer_indicator.configure(text='Connected', text_color='red')
        self._other_client_connected = True

    def terminate_multiplayer(self):
        if not self._other_client_connected and not self._multiplayer_switch_var.get():
            if tmb.askyesno("QUIT WAITING", "Quit Waiting For The Connection?"):
                self.__restart(force=True)
            else:
                self._multiplayer_switch_var.set(True)

        elif self._other_client_connected and not self._multiplayer_switch_var.get():
            if tmb.askyesno("QUIT CONNECTION", "Quit The Connection?"):
                self.__restart(force=True)
            else:
                self._multiplayer_switch_var.set(True)
                

    def start_multiplayer_server_client(self, event=None):
        if self._delay_multiplayer_for_animations:
            self.popup_message(
                title='Please Wait', 
                text='Please wait for animations to finish',
                wraplength=240
            )
            return
        elif self._onlinePlayerActive:
            self.popup_message(
                title='MP Error',
                text='Multiplayer Already Active!',
                wraplength=240
            )
            return

        multiplayer = self.multiplayer_gui()
        print('multiplayer -->', multiplayer)
        if multiplayer is None:
            return
        host, port, nickname, server_choice = multiplayer
        self._server_choice = server_choice
        print('setting root title -->', self._title)
        self._title += ' - MULTIPLAYER'
        self._root.title(self._title)

        if server_choice == 'start server':
            self.start_init_server_thread(host, port)
            seed = self.generate_shuffle_seed()
            self.start_init_client_thread(host, port)
            try:
                player_turn = self.reinitialize_cards(onlinePlayer=True, shuffle_seed=seed, conn_type='server')
                player_turn = 'op' if player_turn == 'p2' else 'p2'
                init_data = {
                    'seed': seed,
                    'player_turn': player_turn,
                    'nickname': nickname
                }
                self.wait_for_client_to_connect()
                self._onlineClient.send_data(str(json.dumps(init_data)), 'INIT_DATA') # Send Init data to server
            except (OSError, ConnectionRefusedError, AttributeError, TimeoutError, tk.TclError) as e:
                ic('startMp', e)
                self._connectionFailed = True


        else:  # choice -> 'join server'
            self._onlinePlayerActive = True
            self.start_init_client_thread(host, port)
            init_d_queue = queue.Queue() #TODO: Implement
            init_data = self.get_init_data_from_server(init_d_queue)
            seed = init_data['seed']
            player_turn = init_data['player_turn']
            self._onlineNickname = init_data['nickname']
            self._onlineClient.send_data(nickname, data_type='NICKNAME')
            if not self._connectionFailed:
                self.reinitialize_cards(onlinePlayer=True, shuffle_seed=seed, conn_type='client',
                                        player_turn=player_turn)
                self.update_multiplayer_indicators()

        if not self._connectionFailed:
            self.start_listen_for_onlineP_card_thread()
        else:
            ic('connection failed')
            self._title = 'Whot Game'
            self._root.title(self._title)
            self._onlinePlayerActive = False
            self._connectionFailed = False
            self.__restart(force=True)


    def multiplayer_gui(self) -> tuple[str, int, str, str] | None:
        root = self.create_toplevel_at_center(width=274, height=168)
        root.transient(self._root)
        root.title("Multiplayer")
        root.focus_set()
        root.grab_set()
        return_value = None

        config = self._config['multiplayer']

        host_var, port_var = tk.StringVar(value=config['host']), tk.IntVar(value=config['port'])
        server_var = tk.StringVar(value=config['server_choice'])

        ctk.CTkLabel(
            root, 
            height=23, 
            width=38,
            text='Host:', 
            font=self.smaller_font
        ).place(relx=0.036, rely=0.06)
        ctk.CTkLabel(
            root, 
            height=23, 
            width=38,
            text='Port:', 
            font=self.smaller_font
        ).place(relx=0.036, rely=0.290)

        host_entry = ctk.CTkEntry(
            root, 
            width=170,
            textvariable=host_var,
            font=self.smaller_font
        )
        host_entry.place(relx=0.31, rely=0.071)
        port_entry = ctk.CTkEntry(
            root, 
            width=170,
            textvariable=port_var,
            font=self.smaller_font
        )
        port_entry.place(relx=0.31, rely=0.295)

        start_server = ctk.CTkRadioButton(
            root, 
            height=25,
            text='Start Server', 
            variable=server_var, 
            value='start server',
            font=self.smaller_font
        )
        start_server.place(relx=0.04, rely=0.620)
        join_server = ctk.CTkRadioButton(
            root, 
            height=25,
            text='Join Server', 
            variable=server_var, 
            value='join server',
            font=self.smaller_font
        )
        join_server.place(relx=0.605, rely=0.620)

        def close_window(exit_btn=False):
            nonlocal return_value
            root.destroy()
            root.quit()

            host, port = host_var.get(), port_var.get()
            nickname, server_choice = self._config['name'], server_var.get()

            config['host'] = host
            config['port'] = port
            config['nickname'] = nickname
            config['server_choice'] = server_choice

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
            command=close_window
        )
        connect_btn.place(relx=0.35, rely=0.805)
        host_entry.select_range(0, tk.END), port_entry.select_range(0, tk.END)

        root.protocol('WM_DELETE_WINDOW', lambda: close_window(exit_btn=True))
        root.mainloop()

        return return_value

    def start_init_server_thread(self, host, port):
        print('server host and port -->', host, port)
        init_server_thread = threading.Thread(target=self.init_server, args=(host, port))
        init_server_thread.start()

    def start_init_client_thread(self, host, port):
        print('client host and port -->', host, port)
        init_client_thread = threading.Thread(target=self.init_client, args=(host, port))
        init_client_thread.start()

    def start_listen_for_onlineP_card_thread(self):
        listen_op_thread = threading.Thread(target=self.onlineplayer_listener)
        listen_op_thread.start()

    def init_server(self, host=None, port=None):
        try:
            server = socketServer.Server(host, port)
        except (ConnectionRefusedError, OSError) as e:
            print(e)
            self._connectionFailed = True
        else:
            self._onlineServer = server
            print('server -->', self._onlineServer)
            return server

    def init_client(self, host=None, port=None):
        try:
            nickname = self._config['multiplayer']['nickname']
            client = socketClient.Client(host, port, nickname)
        except (ConnectionRefusedError, TimeoutError) as e:
            print(e)
            self._connectionFailed = True
        else:
            self._onlineClient = client
            print('client -->', self._onlineClient)
            return client

    def wait_for_client_to_connect(self, sleep_duration=1) -> bool:
        """
        Waits for a client to connect to the server.

        Args:
            sleep_duration (float): The duration in seconds to sleep between checks for a client connection.
        
        Returns:
            bool: True if a client successfully connects, False otherwise.
        """
        while self._onlineClient is None and self._onlinePlayerActive:
            if self._connectionFailed:
                tmb.showerror('Connection Failed', 'No Server To Be Joined')
                return False
            time.sleep(sleep_duration)
        return True


    def get_init_data_from_server(self, init_data_queue: queue.Queue):
        if not self.wait_for_client_to_connect():
            return

        client_init_data = self._onlineClient.client_init_data
        while self._onlinePlayerActive and not all(client_init_data.values()):
            print('client_init_data values -->', client_init_data.values(), all(client_init_data.values()))
            time.sleep(0.5)
        init_data_queue.put(client_init_data)
        return client_init_data


    def onlineplayer_listener(self):
        self.wait_for_client_to_connect(2.5)

        while self._onlinePlayerActive and self._onlineClient._client_is_alive:
            nick: str = self._onlineClient.client_data['conn_nickname']
            other_client_alive = self._onlineClient._other_client_alive
            card = self._onlineClient.client_data['card']
            mart = self._onlineClient.client_data['mart']
            request = self._onlineClient.client_data['request']

            if nick:
                self._onlineNickname = nick
                self.display_number_of_cards('onlinep')
                self._comp_turn_indicator.configure(text=nick.capitalize())
                self._onlineClient.client_data['conn_nickname'] = None
                self.update_multiplayer_indicators() # server_choice: start server
            
            if other_client_alive is False: # Essentially only False
                tmb.showerror("CLIENT ERROR", f"{self._onlineNickname or 'OnlinePlayer'} Disconnected!")
                self.__restart(force=True)

            if card:
                print('\n@@@@ onlineP sent card', card)
                index = self.get_onlinep_card_index(card)
                self.set_player_turn('op')
                self.onlinep_play(self._label_reference[index][0])

            if mart:  # Set for OP to play again
                print('\n!!!! nonlinep went to mart')
                self.set_player_turn('op')
                self.onlinep_mart()

            if request:
                print('\n$$$$ onlinep sent request')
                self.onlinep_request_card_with_20(request)

            time.sleep(0.5)
        

    def get_onlinep_card_index(self, card: tuple[str, int]):
        print('finding card...')
        index = None
        for i, sublist in enumerate(self._label_reference):
            for j, item in enumerate(sublist):
                if item[1] == card:  # item[1] - ('Square', 2)
                    index = i
                    print(f"Index of {card}: ({i}, {j})")
                    break

        if index is None:
            raise Main.WhotException('Cant Find OnlineP Card In Cardstack')

        return index

    def onlinep_mart(self):
        if not self.get_player_turn('op') or self.__check_gameover:
            print('\nin onlinep mart, its not op turn for mart')
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

        client_data = self._onlineClient.client_data
        client_data['mart'] = False  # Reset
        self.display_number_of_cards('onlinep')
        self.handle_onlinep_todos()

        self.repopulate_containers(onlinePlayer=True)
        self._root.title(self._title)

    def handle_onlinep_todos(self, card: tuple[tk.PhotoImage, tuple[str, int]]=None):
        if self._onlinep_todo['pick_two'] > 0:
            self._onlinep_todo['pick_two'] -= 1
            self.set_player_turn('p2' if self._onlinep_todo['pick_two'] == 0 else 'op')

        if self._onlinep_todo['general_market'] > 0:
            self._onlinep_todo['general_market'] -= 1
            self.set_player_turn('p2')

        if card and card[1][1] == 1: #HoldOn
            self._onlinep_todo['hold_on'] = True
            ic('setting to True in HOLD ON for', self._server_choice)
        
        if card and card[1][1] == 8: #Suspension
            self._onlinep_todo['suspension'] = True
            ic('setting to True in SUSPENSION for', self._server_choice)

        if card and card[1][1] != 1 and self._onlinep_todo['hold_on']:
            ic('HOLD On prev enabled, Continuing', self._server_choice)
            self._onlinep_todo['hold_on'] = False
            self.set_player_turn('op')
            self.continue_from_hold_or_suspension()
        elif not card and self._onlinep_todo['hold_on']: #For mart
            self._onlinep_todo['hold_on'] = False
            self.set_player_turn('op')
            self.continue_from_hold_or_suspension()
        
        if card and card[1][1] != 8 and self._onlinep_todo['suspension']:
            ic('SUSPENSIOn prev enabled, Continuing', self._server_choice)
            self._onlinep_todo['suspension'] = False
            self.set_player_turn('op')
            self.continue_from_hold_or_suspension()
        elif not card and self._onlinep_todo['suspension']:
            self._onlinep_todo['suspension'] = False
            self.set_player_turn('op')
            self.continue_from_hold_or_suspension()

        if card and card[1][1] == 20:
            self.set_player_turn('op')

        if not any(self._onlinep_todo.values()):
            self.set_player_turn('p2')
            

    def onlinep_request_card_with_20(self, request: str):
        # TODO: Make it such that the requested card is the only accepted card to be
        # TODO: played after the request (by one recursion) then market if card unavailable

        client_data = self._onlineClient.client_data

        if len(self._onlinep.cards()) == 0:
            client_data['request'] = ''
            return

        self.set_player_turn('p2')

        print('in req with card 20, request -->', request)
        self._whot.requests['onlineplayer'] = request
        tmb.showinfo("Request", f"I NEED {request.upper()}")
        self._root.title(f'{self._title} - Request {request.upper()}')
        client_data['request'] = ''

    def onlinep_play(
            self,
            card: tuple[tk.PhotoImage, tuple[str, int]],
            event=None
    ):
        """For OnlinePlayer to play their valid card"""

        print(f'onlineplayer just played {card}')
        if self.get_player_turn('op') and not self.__check_gameover:
            if self._onlinep.play(card):
                card_display_label = self.comp_op_get_next_available_label(is_gridded=True)
                self.move_card(
                    card[0], 
                    self._comp_frame._parent_canvas, 
                    self._played_frame, 
                    card_display_label,
                    from_above=True
                    )

                self._onlineClient.client_data['card'] = None

                self.display_number_of_cards('onlinep')
                self.handle_onlinep_todos(card)
                self.pick_two('p2')
                self.go_gen_mart('p2')
                self.hold_on('p2')
                self.suspension('p2')

                if card[1][1] == 20:
                    print('\nOP CARD IS 20, SETTING OP TO PLAY AGAIN')
                    self.set_player_turn('op')
                # else:
                #     self.set_player_turn('p2')

                self.gameover()

            else:  # Rare Happening
                raise Main.WhotException('OnlinePlayer Played Invalid Card')

    ##################################################################################################
    def apply_difficulty(self):
        """Applies Chosen Difficulty To The Game And Goes To Market"""

        if not choice([True, False, '', 'Whot']):
            print('not choice...')
            self.comp_mart()
            return

        difficulty = self._difficulty_var.get()
        difficulty_dict = {
            'hard': [2, 20, 1],
            'medium': [14, 8],
        }
        powerups = difficulty_dict.get(difficulty)
        if not powerups:
            self.comp_mart()
            return

        chosen = choice(powerups)
        print(f"mode var is {difficulty} and chosen is: ", chosen)
        if self._computer.search_and_append(chosen, 'comp'):
            self.comp_mart(gone_to_mart_before=True)
        else:
            self.comp_mart()

    def pick_two(self, player: Literal['comp', 'p2', 'op']):
        """Makes Player Pick two cards from the mart"""

        if player == 'comp':
            if self._player2.powerup_cards[2]:
                self.set_player_turn('comp')

                def comp_pick_two_animation(count: int):
                    if count < 2:
                        self.set_player_turn('comp')
                        self.apply_difficulty()
                        self._root.after(self.COMP_PLAY_DELAY, comp_pick_two_animation, count + 1)

                comp_pick_two_animation(0)

                self._player2.powerup_cards[2] = False
                self.set_player_turn('p2')
            return

        elif player == 'op':  # OP
            if self._player2.powerup_cards[2]:
                self.set_player_turn('op')
                self._onlinep_todo['pick_two'] = 2
                self._player2.powerup_cards[2] = False
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[2]:
                print('\nPICK TWO')
                self.popup_message("Pick Two", "Pick two cards from the mart")
                self._root.title(f'{self._title} - PICK TWO')
                [btn.config(state='disabled') for btn in self._depot_p2_btns]
                self._market_btn.configure(command=self.check_p2_picked_two_cards)
                self.bind_return(method='pick_two')
                powerup[2] = False

    def go_gen_mart(self, player: Literal['p2', 'comp', 'op']):
        """Makes Player go to general market"""

        if player == 'comp':
            if self.get_player_turn('comp'):
                if self._player2.powerup_cards[14]:
                    print("Computer Going to gen mart")

                    self.apply_difficulty()

                    self._player2.powerup_cards[14] = False
                    self.set_player_turn('p2')
            return

        elif player == 'op':
            logging.debug(f'GENERAL MARKET - {player}')
            if self._player2.powerup_cards[14]:
                self.set_player_turn('op')
                self._onlinep_todo['general_market'] = 1
                self._player2.powerup_cards[14] = False
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[14]:
                logging.debug(f'GENERAL MARKET - {player}')
                self.popup_message("General Market", "General Market")
                self._root.title(f'{self._title} - GENERAL MARKET')
                [btn.config(state='disabled') for btn in self._depot_p2_btns]
                self._market_btn.configure(command=self.check_p2_picked_a_card)
                self.bind_return(method='pick_one')
                powerup[14] = False

    def hold_on(self, player: Literal['p2', 'comp', 'op']):
        """Makes Player to hold on until the other player plays another card or goes to the mart,
        after playing a card with number 1 in it"""

        if player == 'comp':
            if self._player2.powerup_cards[1]:
                self.set_player_turn('p2')
                self._player2.powerup_cards[1] = False
            return

        elif player == 'op':
            logging.debug(f'HOLD ON - {player}')
            if self._player2.powerup_cards[1]:
                self.set_player_turn('p2')
                # Actual hold on handled in the recv end (self.handle_onlinep_todo)
                self._player2.powerup_cards[1] = False
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards

            if powerup[1]:
                logging.debug(f'HOLD ON - {player}')
                self.popup_message("Hold On", "Hold On")
                self._root.title(f'{self._title} - HOLD ON')
                powerup[1] = False
                self.gameover()
                if not self._onlinePlayerActive:
                    self._root.after(self.COMP_PLAY_DELAY, lambda: self.comp_card_streak(1))
                else:
                    self.set_player_turn('op')

            # self.set_player_turn('comp')

    def suspension(self, player: Literal['p2', 'comp', 'op']):
        """Just like hold on, it suspends the other player until they play
          another card or go to mart"""

        if player == 'comp':
            if self._player2.powerup_cards[8]:
                self.set_player_turn('p2')
                self._player2.powerup_cards[8] = False
            return

        elif player == 'op':
            logging.debug(f'SUSPENSION - {player}')
            if self._player2.powerup_cards[8]:
                self.set_player_turn('p2')
                # Actual suspension handled in the recv end (self.handle_onlinep_todo)
                self._player2.powerup_cards[8] = False
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.powerup_cards
            else:
                powerup = self._computer.powerup_cards
            if powerup[8]:
                logging.debug(f'SUSPENSION - {player}')
                self.popup_message("Hold On", "Suspension")
                self._root.title(f'{self._title} - SUSPENSION')

                powerup[8] = False
                self.gameover()

                if not self._onlinePlayerActive:
                    self._root.after(500, lambda: self.comp_card_streak(8))
                else:
                    self.set_player_turn('op')
            # self.set_player_turn('p2')

    def continue_from_hold_or_suspension(self):
        self.popup_message('Continue', 'Continue', 400)

    ##################################################################################################

    def computer_play(
            self,
            card: tuple[tk.PhotoImage, tuple[str, int]],
    ):
        """Plays any cards that are valid, from CompPlayEngine"""
        if not self.get_player_turn('comp') or self.__check_gameover:
            return

        try:
            if self._computer.play(card):
                card_display_label = self.comp_op_get_next_available_label(is_gridded=True)
                self.move_card(
                    card[0], 
                    self._comp_frame._parent_canvas, 
                    self._played_frame, 
                    card_display_label,
                    from_above=True
                    )

                self.computer_request_card_with_20(card)
                self.display_number_of_cards('computer')
                self.pick_two('p2')
                self.go_gen_mart('p2')
                self.hold_on('p2')
                self.suspension('p2')

                self.set_player_turn('p2')

                self.gameover()

            else:  # Rare Happening
                raise Main.WhotException('Computer Played Invalid Card')
        # TODO
        except Main.WhotException as e:
            tmb.showerror('Computer Error', e)

    def compPlayEngine(self, event=None):
        if (self.__check_gameover
            or self._onlinePlayerActive 
            or not self.get_player_turn('comp')
        ):
            return

        if self._computer.requested_card_idx is not None:
            idx = self._computer.requested_card_idx
            card = self._label_reference[idx]
            logging.debug(
                f'[requested_card_idx]: idx: {idx}, card: {card}, label_ref_index(card): {self._label_reference.index(card)}')
            if card:  # comp has somehow played that card (maybe p2 counter requested with whot20)

                last_played_card = self._whot.PlayedCards()[-1]
                if (card[0][1][0] == last_played_card[1][0] or
                        card[0][1][1] == last_played_card[1][1] or
                        last_played_card[1][1] == 20):

                    self.computer_play(card[0])
                    self._label_reference.pop(self._label_reference.index(card))
                    self._computer.requested_card_idx = None
                    return
                else:
                    self._computer.requested_card_idx = None
            else:
                # card idx now useless as a counter powerup was played by p2
                self._computer.requested_card_idx = None

        containers = [self._found_20, self._found_num, self._found_str]

        for idx, card in enumerate(self._label_reference):
            if not card:
                continue

            if card[0][1][1] == 20:
                self.parse_and_remove_comp_cards(containers[0], card, idx)
                break

            if not self._found_20 and card[0][1][1] == self._whot.PlayedCards()[-1][1][1]:
                self.parse_and_remove_comp_cards(containers[1], card, idx)
                break

            if not self._found_num and not self._found_20 and card[0][1][0] == self._whot.PlayedCards()[-1][1][0]:
                self.parse_and_remove_comp_cards(containers[2], card, idx)
                break

        # found_valid_card = []
        # ! Must not change the order of containers
        found_valid_card = next((container for container in containers if container), None)

        if found_valid_card:
            self.comp_engine_play_valid_card(
                containers.index(found_valid_card),
                found_valid_card[0][0],
            )
        else:
            self.apply_difficulty()

        for container in containers:
            container.clear()

    def parse_and_remove_comp_cards(
            self,
            found_card_container: list,
            card: list[tuple[tk.PhotoImage, tuple[str, int]]],
            index: int
        ):
        """Remove the computer card and add an empty list (card) to the same index in ``self._label_reference``"""
        found_card_container.append(card)
        self._label_reference.insert(index, [])
        self._label_reference.pop(self._label_reference.index(card))

    def comp_engine_play_valid_card(
            self,
            found_index: int,
            card: tuple[tk.PhotoImage, tuple[str, int]],
    ):

        logging.debug(f'[Comp Play Valid Card]: {found_index}, {card[1]}')
        if found_index == 1:  # found num
            if card[1][1] == self._whot.PlayedCards()[-1][1][1]:
                self.computer_play(card)
        elif found_index == 2:  # found str
            if card[1][0] == self._whot.PlayedCards()[-1][1][0]:
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
        preferred_label = (self._onlinep_labels.values() 
                           if self._onlinePlayerActive
                           else self._computer_labels.values())
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
        if self._whot.requests['player2']:
            self._root.after(self.COMP_PLAY_DELAY, self.compPlayEngine)
            return
        
        found_card_streak_no = []
        for idx, i in enumerate(self._label_reference):
            if i and i[0][1][1] == card_streak_no:
                found_card_streak_no = [idx, i]
                self._label_reference.insert(idx, [])
                self._label_reference.pop(self._label_reference.index(i))
                logging.debug(f'found a card streak --> {found_card_streak_no}')
                break

        self.set_player_turn('comp')

        # ! Issue might be stemming from here
        # ! might be supplying labels that arent displayed and we there grid forgetting
        if found_card_streak_no:
            self.computer_play(found_card_streak_no[1][0])

        else:
            # Computer's continue has to be after it plays a non streak card
            self._root.after(self.COMP_PLAY_DELAY // 2, self.compPlayEngine)

            self._root.after(
                int(self.COMP_PLAY_DELAY // 1.6), 
                lambda: self.popup_message("Continue", "Continue", 450)
            )
            self._root.after(self.COMP_PLAY_DELAY+100, self.set_player_turn, 'p2')


    def comp_mart(self, gone_to_mart_before=False):
        """Responsible for making the computer to go to market (pick a card from the mart)
        The 'gone_to_mart_before' argument checks whether the computer has already gone to mart before if the
        `self._computer.gomart` has beeen called before"""

        if not self.get_player_turn('comp') or self.__check_gameover:
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

        self.display_number_of_cards('computer')
        self.set_player_turn('p2')
        self.repopulate_containers()
        self._root.title(self._title)

    def computer_request_card_with_20(self, card: tuple[tk.PhotoImage, tuple[str, int]]):
        """Finds a viable (powerup) card to request from player2 after computer plays the Whot 20 card"""

        if card[1][1] != 20 or len(self._computer.cards()) == 0:
            return

        found_viable_card, idx = '', None

        for idx, i in enumerate(self._label_reference):
            if not i:
                continue
            if i[0][1][1] in [1, 2, 8, 14] and i[0][1][0] != 'Whot':
                found_viable_card = i[0][1][0]
                break

        if not found_viable_card:
            f = next(((idx, i) for idx, i in enumerate(self._label_reference) if i and i[0][1][0] != 'Whot'))
            idx, found_viable_card = f[0], f[1][0][1][0]

        # there'll always be a viable card, else tis game over!
        logging.debug(f'found_viable_card for comp, setting self._whot.requests["computer"] to {found_viable_card}...')
        tmb.showinfo("Request", f"I NEED {found_viable_card.upper()}")
        self._whot.requests['computer'] = found_viable_card
        self._root.title(f'{self._title} - Request {found_viable_card.upper()}')

        self._computer.requested_card_idx = idx
        logging.debug(f'computer requested card idx: {self._computer.requested_card_idx}')
        logging.debug(f'computer request and requests --> {self._whot.requests}')

    def computer_response_to_card_20(self):
        """Generates the computer's appropriate response to the requested
        whot card 20 by player2"""

        if not self.get_player_turn('comp') or self.__check_gameover:
            return

        card = self._whot.requests['player2']
        for o, i in enumerate(self._label_reference):
            if i and i[0][1][0] == card:
                self._found_request.append([o, i])
                self._label_reference.insert(o, [])
                self._label_reference.pop(self._label_reference.index(i))
                break

        if self._found_request:
            logging.debug('Computer is playing p2 request rn...')
            self.computer_play(self._found_request[0][1][0])  # * The play function should clear p2 request
            self._found_request.clear()
            return

        else:
            logging.debug("computer doesnt have the card going to mart")
            self.apply_difficulty()  # * The mart func will also clear p2 request

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
            wrap='word',
            font=self.font_style,
            text_color=theme
        )
        text_box.insert(tk.INSERT, manual)
        text_box.configure(state='disabled')
        text_box.focus_set()
        text_box.grab_set()
        text_box.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)

    def gameover(self):
        """Freezes all buttons and stops the computer | player2 | onlinep from playing 
        if any player's cards finish"""
        
        player2_cards = len(self._player2.cards())
        other_player_cards = len(self._onlinep.cards()) if self._onlinePlayerActive else len(self._computer.cards())        
        
        if player2_cards != 0 and other_player_cards != 0:
            return
        
        self.__check_p2_played = True
        self.__checkcomp_played = True
        self.__check_gameover = True
        self._root.unbind("<Return>")
        
        if not player2_cards:
            tmb.showinfo("Game Over", "You Are The Winner")
        elif not other_player_cards:
            if self._onlinePlayerActive:
                tmb.showinfo("Game Over", f"{self._onlineNickname or 'OnlinePlayer'} Is The Winner")
            else:
                tmb.showinfo("Game Over", "The Computer Is The Winner")
        
        for btn in self._depot_p2_btns:
            btn.configure(state='disabled')
        self._market_btn.configure(state='disabled')
        self._root.title(f'{self._title} - Game Over')
        self._root.after(200, self.__restart)


    def __restart(self, force=False):
        """Restart the Whot Game"""

        if self._onlinePlayerActive:
            if self._server_choice == 'start server':
                self._onlineServer.shutdown()
            self._onlineClient.shutdown()

        if not force:
            ask = tmb.askyesnocancel("Restart Game", "Do you want to restart the game?")
            if ask:
                self.reinitialize_cards(onlinePlayer=False)
            elif ask is None:
                pass
            else:
                self.__exit()
        else:
            self.reinitialize_cards(onlinePlayer=False, prev_onlinep=True)

    def __exit(self):
        if self._onlinePlayerActive:
            self._onlinePlayerActive = False
            if not self._connectionFailed:
                if self._server_choice == 'start server':
                    self._onlineServer.shutdown()
                self._onlineClient.shutdown()

        self._root.after(500, self._whot_threads)


    def _whot_threads(self):
        """Return Active Threads"""
        self._root.quit()
        self._root.destroy()

        for thread in threading.enumerate():
            print(f'thread name and is alive --> {[thread.name, thread.is_alive()]}')
        return threading.enumerate()

    def _mainloop(self):
        """calls tk mainloop"""
        self._root.focus_set()
        self._root.mainloop()


if __name__ == '__main__':
    app = Whot()
    app._mainloop()
