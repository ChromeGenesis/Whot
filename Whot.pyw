import tkthread; tkthread.patch()
from tkinter import ttk
import tkinter as tk
import tkinter.scrolledtext as tks
from manual import manual
from GameImages import images
import Main
import socketServer, socketClient
from random import choice
import Pmw
import tkinter.messagebox as tmb
import time, sys, threading, os
import pickle, json, inspect
from typing import Literal
from icecream import ic
import logging
logging.basicConfig(level=logging.DEBUG, filename='whot.log')
ic.prefix = '[LOG]'

class Whot(images):
    """Naija Whot Game in Grand Style - By Genesis Chrome"""
    def __init__(self):
        self._root = tk.Tk()
        Pmw.initialise(self._root)
        self._orig_size = '650x690+706+6' #760x690+592+7'
        self._root.geometry(self._orig_size)
        self._title = 'Whot Game'
        self._root.title(self._title)
        ttk.Style().theme_use('clam')
        self._root.protocol("WM_DELETE_WINDOW", self.__exit)
        super().__init__()

        self._config: dict[str, str | bool | dict[str, str | int]] = {}
        self.load_config_file()
        
        self._player2_frame = Pmw.ScrolledFrame(self._root, 
                                                labelpos='s', 
                                                usehullsize=1,
                                                hull_width=100,
                                                hull_height=225
                                            )
        
        self._played_cards_frame = tk.Frame(self._root)

        self._comp_frame = Pmw.ScrolledFrame(self._root,
                                            labelpos='n', 
                                            usehullsize=1,
                                            hull_width=100,
                                            hull_height=225,
                                            label_text='Computer'
                                        )

        self._comp_frame_int: tk.Frame = self._comp_frame.interior()
        self._p2_frame_int: tk.Frame = self._player2_frame.interior()

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
        self.__check2_played = False
        self.__checkcomp_played = False
        self.__checkop_played = False

        self.__current_player = None
        ##################################################################
        
        ##################################################################
        # Check Pick two, General market and checkmate
        ##################################################################
        self.__check_checkmate = False

        self._check2 = 0
        self._check1 = 0

        ####################################################################
        # Computer Engine's (CompPlayEngine) containers
        ####################################################################
        self._found_str = []
        self._found_num = []
        self._found_20 = []
        self._found_request = []
        
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
        multiplayer_menu.add_command(label='Multiplayer', accelerator='Ctrl+Shift+M', compound='left', command=self.start_multiplayer_server_client)
    
        self._root.config(menu=menu_bar)
        ####################################################################################
        # Grids
        ####################################################################################
        self._player2_frame.grid(row=3, columnspan=4, sticky='we')
        self._comp_frame.grid(row=1, columnspan=4, sticky='we')
        self._played_cards_frame.grid(row=2, column=2)

        self._market_btn.grid(row=2, column=0, sticky='w')

        self._root.grid_columnconfigure(2, weight=1)
        self._played_cards_frame.grid_columnconfigure(0, weight=1)
        
        ################################################################################################################
        # Card Length Widgets
        ################################################################################################################
        p2_card_length, comp_card_length = len(self._player2.cards()), len(self._computer.cards())
        self._comp_cards_left = tk.Label(self._root, text=f"Number of computer cards: {comp_card_length}", font='Consolas 15 italic')
        self._p2_cards_left = tk.Label(self._root, text=f"Number of your cards: {p2_card_length}", font='Consolas 15 italic')
        self._p2_cards_left.grid(row=4, column=0, sticky='w')
        self._comp_cards_left.grid(row=0, column=0)
        
        #################################################################################################################
        # Turn Indicators
        #################################################################################################################
        self._p2_turn_indicator = tk.Label(self._root, text='Player', font='Consolas 15 italic')
        self._comp_turn_indicator = tk.Label(self._root, text='Computer', font='Consolas 15 italic')
        
        self._p2_turn_indicator.grid(row=4, column=2, sticky='e')
        self._comp_turn_indicator.grid(row=0, column=2, sticky='e')

        ##################################################################################
        # Binding's
        ##################################################################################
        self._root.bind_all("<Control-m>", self.Manual)
        self._root.bind_all("<Control-r>", self.__restart)
        self._root.bind_all("<Control-M>", self.start_multiplayer_server_client)
        self._root.bind("<Control-s>", self.settings)
        self._root.bind("<Return>", self.p2_mart)
        self._root.bind_all("<F11>", self._toggle_on_fullscreen)
        self._root.bind_all("<Escape>", self._toggle_off_fullscreen)

        self.__full_size = self._root.maxsize()
        self.balloon_bindings()

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

        ####################################################################################
        # Grid Counter, Game Started and Show Setting At Startup Variables
        ####################################################################################
        self._p2_btn_grid_pos = 1000
        self._comp_lab_grid_pos = 1000
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
            'Default': '#d9d9d9', #Light gray
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
            self.settings()
        self._difficulty_var.set(self._config.get('mode'))
        
        self._root.after(5800, self.compPlayEngine)
        self._root.after(1200, lambda: self.display_cards_animation([self._player2_btns[i] for i in range(5)]))
        ####################################################################################
        # END
        ####################################################################################

        
    def display_cards_animation(self, p2_btns: list[tk.Button]):

        self._root.after(3700, lambda: setattr(self, '_delay_multiplayer_for_animations', False))

        for card in p2_btns:
            card.config(state='disabled')
        
        btn_duration = 50
        for btn, column in zip(p2_btns, range(1001, 1006)):
            self._root.after(btn_duration, lambda b=btn, c=column: b.grid(row=0, column=c, padx=6, pady=6))
            btn_duration += 250
        
        self._root.after(1500, lambda: self._played_card.grid(row=1, column=1, sticky='e'))
        
        lab_duration = 2000
        for ref_no, column in zip(range(5), range(1001, 1006)):
            self._root.after(
                lab_duration, 
                lambda r=ref_no, c=column: self._computer_labels[r].grid(row=0, column=c, padx=6, pady=6))
            lab_duration += 200

        for card in p2_btns:
            self._root.after(3500, lambda c=card: (
                c.config(state='normal'),
                self._market_btn.config(state='normal')
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
        top = tk.Toplevel(self._root)
        top.transient(self._root)
        top.title(f'{self._title} - Settings')        
        top.geometry(self.set_toplevel_to_center(height=350, width=350))
        top.resizable(False, False)
            
        root_tab = ttk.Notebook(top)
            
        theme_tab = ttk.Frame(root_tab)
        name_tab = ttk.Frame(root_tab)
        mode_tab = ttk.Frame(root_tab)
            
        root_tab.add(theme_tab, text='Themes')
        root_tab.add(name_tab, text='Name')
        root_tab.add(mode_tab, text='Mode')
        
        root_tab.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)
            
        self._choose_theme(theme_tab, root=top)
        self.set_name(name_tab)
        self.choose_difficulty_mode(mode_tab)
        
        show_setting = ttk.Checkbutton(
            top, text='Show Setttings at startup', 
            variable=self._show_setting_at_startup,
            command=lambda: self._write_config(
                'show_setting',
                self._show_setting_at_startup.get()
            )
        )
        disable_difficulty_modes = lambda: (setattr(self, '_game_started', True)
                                            , top.destroy(), top.grab_release())

        self._show_setting_at_startup.set(self._config.get('show_setting'))
        show_setting.place(relx=0.029, rely=0.923, relwidth=0.440, relheight=0.0, height=31)
        ok_btn = ttk.Button(top, text='Ok', command=disable_difficulty_modes)
        ok_btn.place(relx=0.657, rely=0.923, height=25, width=96)
            
        top.focus_set()
        top.protocol('WM_DELETE_WINDOW', disable_difficulty_modes)
        top.grab_set()

    
    def choose_difficulty_mode(self, window: tk.Frame):
        """To choose the mode of the game, whether easy or hard"""
        
        hard_radbtn = ttk.Radiobutton(
            window, 
            text='Hard', 
            var=self._difficulty_var, 
            value='hard',
            command=lambda: self._write_config('mode', self._difficulty_var.get())
            )
            
        medium_radbtn = ttk.Radiobutton(
            window, text='Medium', 
            var=self._difficulty_var, 
            value='medium',
            command=lambda: self._write_config('mode', self._difficulty_var.get())
            )
            
        easy_radbtn = ttk.Radiobutton(
            window, text='Easy', 
            var=self._difficulty_var, 
            value='easy',
            command=lambda: self._write_config('mode', self._difficulty_var.get())
            )
        
        hard_radbtn.place(relx=0.376, rely=0.268, relwidth=0.171, relheight=0.0, height=26)
        medium_radbtn.place(relx=0.376, rely=0.435, relwidth=0.228, relheight=0.0, height=27)
        easy_radbtn.place(relx=0.376, rely=0.602, relwidth=0.171, relheight=0.0, height=26)
        ttk.Label(window, text='Choose Desired Mode',
                 font="-family {Comic Sans MS} -size 16 -weight bold -slant italic").place(
                     relx=0.202, rely=0.033, height=57, width=395)
        ttk.Label(window, text='(Can Only Be Set Once Per Game Session)').place(
            relx=0.202, rely=0.769, height=26, width=225)
        window.focus_set()
        
        if self._game_started:
            for i in [hard_radbtn, medium_radbtn, easy_radbtn]:
                i.configure(state='disabled')  

    def set_toplevel_to_center(self, height: int, width: int):
        self._root.update()
        root_width = self._root.winfo_width()
        root_height = self._root.winfo_height()
        x = self._root.winfo_x() + (root_width - width) // 2
        y = self._root.winfo_y() + (root_height - height) // 2

        return f'{width}x{height}+{x}+{y}'

    def get_actual_theme(self, for_text=False) -> str:
        """
        Get the theme color used by the application.

        Args:
            for_text (bool): Whether the theme is for text or not.
            will return `black` if theme is `Default` and `for_text` is True.
        """
        theme = self._theme_var.get()
        if for_text and theme == 'Default':
            return 'black' #'#000000'
        return self._themes_dict[theme]
    
        
    def _choose_theme(self, window: ttk.Frame, root: tk.Toplevel, event=None):
        """For choosing desired theme from the themes list"""  

        # theme_label = ttk.Label(window, text="Select Theme:",
        #     font="-family {Comic Sans MS} -size 16 -weight bold -slant italic")
        # theme_label.place(relx=0.279, rely=0.014, height=39, width=155)  
        
        theme_radbtns = []
        num_per_row = 2
        # padx, pady = 19, 10
        padx, pady = 20, 8

        for o, i in enumerate(self._themes_dict.keys()):
            rbtn = ttk.Radiobutton(window, text=i.upper(), var=self._theme_var,
                                   value=i, command=self.set_theme)
            rbtn.grid(row=(o // num_per_row), column=o % num_per_row, padx=padx, pady=pady, sticky="w")
            theme_radbtns.append(rbtn)
            
        root.bind("<Down>", lambda event: self.scroll_theme('down'))
        root.bind("<Up>", lambda event: self.scroll_theme('up'))
        root.focus_set()
        
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
        color = self._theme_var.get()

        if color not in self._themes_dict: 
            self._write_config('theme', 'Default')
            return
        
        theme_color = self.get_actual_theme()
        
        try:
            self._root.option_add('*foreground', theme_color)
            for btn_lab in self._depot_comp_labels + self._depot_p2_btns:
                btn_lab.config(bg=theme_color)
            self._played_card.config(bg=theme_color)
            self._market_btn.config(bg=theme_color)
            self._comp_cards_left.config(fg=theme_color)
            self._p2_cards_left.config(fg=theme_color)
            
            theme_color = self.get_actual_theme(for_text=True)
            self._comp_cards_left.config(fg=theme_color)
            self._p2_cards_left.config(fg=theme_color)
            
            self._write_config('theme', color)
        except tk.TclError as e:
            print(e)

    def popup_message(
            self, 
            title: str, 
            text: str, 
            duration: int=900, 
            wraplength: int=140
        ) -> None:
        """Displays popup message containing information for 1 sec approx,
          (or the `duration` arg specification)"""
        top = tk.Toplevel(self._root)
        top.grab_set()
        top.focus_set()
        top.transient(self._root)
        top.title(title.upper())
        
        theme = self.get_actual_theme(for_text=True)
            
        label = tk.Label(top, text=text, foreground=theme, font='Consolas 13 bold',
                padx=20, pady=20, wraplength=wraplength)
        label.pack(fill='both', expand=True)
        
        geometry = self.set_toplevel_to_center(50, 250)
        top.geometry(geometry)
        
        top.after(duration, top.destroy)
        
    
    def set_name(self, window: ttk.Frame):
        """Gets desired name from player"""
        theme = self.get_actual_theme(for_text=True)
        former_name = self._config.get('name')
        entry_var = tk.StringVar(value=former_name)
        
        name_label = ttk.Label(
            window, 
            text='Enter Desired Name:',
            font="-family {Comic Sans MS} -size 16 -weight bold -slant italic"
        )
        name_label.place(relx=0.202, rely=0.067, height=57, width=225)
        
        name_entry = ttk.Entry(
            window, 
            textvariable=entry_var,
            font="-family {Comic Sans MS} -size 16 -weight bold -slant italic",
            foreground=theme, 
            justify='center'
        )
        name_entry.place(relx=0.173, rely=0.334, relheight=0.104, relwidth=0.653)
        
        save_button = ttk.Button(
            window, 
            text='Save', 
            command=lambda: self.save_name_cmd(entry_var)
        )
        save_button.place(relx=0.347, rely=0.669, height=35, width=96)
        
        # ttk.Label(
        #     window, 
        #     text='(Restart To Initiate Changes)'
        # ).place(relx=0.289, rely=0.468, height=16, width=155)
            
    def save_name_cmd(self, name: tk.StringVar):
        """Sets (Registers) the desired name to the configuration file"""
        if name.get():
            self._write_config('name', name.get())
            self.popup_message('Name Saved', f'{name.get()} has been saved successfully...', 400, 200)
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
            self.__check2_played = True
        
        elif player == 'p2':
            self.__check2_played = False
            if not self._onlinePlayerActive:
                self.__checkcomp_played = True
            else:
                self.__checkop_played = True

        elif player == 'op':
            self.__checkop_played = False
            self.__check2_played = True

        self.update_turn_indicator()

    
    def get_player_turn(self, player: Literal['comp', 'p2', 'op']) -> bool:
        """Return bool value for the valid player to play first or next"""
        if player == 'comp':
            return self.__check2_played
            
        elif player == 'p2':
            if self._onlinePlayerActive:
                return self.__checkop_played
            return self.__checkcomp_played
            
        elif player == 'op':
            return self.__check2_played
            
        return False
                
    def update_turn_indicator(self):
        p2_turn = self.get_player_turn('p2')
        comp_turn = self.get_player_turn('comp')
        op_turn = self.get_player_turn('op')

        if p2_turn and not comp_turn:
            self._p2_turn_indicator.config(fg='#000fff000')
            self._comp_turn_indicator.config(fg='red')
            
        elif comp_turn and not p2_turn and not self._onlinePlayerActive:
            self._p2_turn_indicator.config(fg='red')
            self._comp_turn_indicator.config(fg='#000fff000')

        #since its op's turn, we'll use comp's widgets to display the turn indicator
        elif op_turn and not p2_turn:
            self._p2_turn_indicator.config(fg='red')
            self._comp_turn_indicator.config(fg='#000fff000')
        
        #Set names
        p2_name = self._config.get('name').capitalize()
        self._p2_turn_indicator.config(text=p2_name)
        self._player2_frame["label_text"] = p2_name
        if self._onlinePlayerActive:
            op_name = self._onlineNickname if self._onlineNickname else 'OnlinePlayer'
            op_name = op_name.capitalize()
            self._comp_turn_indicator.config(text=op_name)
            self._comp_frame["label_text"] = op_name


    def display_number_of_cards(self, player: Literal['computer', 'player2', 'onlinep']):
        """Display number of cards left/remaining for the player"""
        if player == 'computer':
            no_of_cards = len(self._computer.cards())
            text = 'Last Card...' if no_of_cards == 1 else f"Number of computer cards : {no_of_cards}"
            self._comp_cards_left.config(text=text)
            
        elif player == 'player2':
            no_of_cards = len(self._player2.cards())
            text = 'Last Card...' if no_of_cards == 1 else f"Number of your cards : {no_of_cards}"
            self._p2_cards_left.config(text=text)

        elif player == 'onlinep':
            no_of_cards = len(self._onlinep.cards())
            if self._onlineNickname and self._onlinePlayerActive:
                text = 'Last Card...' if no_of_cards == 1 else f"Number of {self._onlineNickname}'s cards : {no_of_cards}"
            else:
                text = 'Last Card...' if no_of_cards == 1 else f"Number of your cards : {no_of_cards}"
            self._comp_cards_left.config(text=text)
    
    def balloon_bindings(self):
        """Balloon Bindings and Updates"""
        market_balloon = Pmw.Balloon(self._root)
        label_balloon = Pmw.Balloon(self._played_cards_frame)
        p2_balloon = Pmw.Balloon(self._p2_frame_int)
        comp_balloon = Pmw.Balloon(self._comp_frame_int)

        for btn in self._depot_p2_btns:
            p2_balloon.bind(btn, f"{self._config.get('name')}'s Cards")
        
        if not self._onlinePlayerActive:
            for lab in self._depot_comp_labels:
                comp_balloon.bind(lab, "Computer's Cards")
        else:
            op_name = self._onlineNickname if self._onlineNickname else 'OnlinePlayer'
            for lab in self._depot_onlinep_labels:
                comp_balloon.bind(lab, f"{op_name}'s Cards")

        market_balloon.bind(self._market_btn, "Click To Go To Mart (Enter key does the same thing)")
        label_balloon.bind(self._played_card, "Played Cards")

    def repopulate_cards(self, onlinePlayer=False):
        """Repopulates by appending one more container (list) to the Button | Label references and
         one more Button | Label to the depots after the reference containers have all been filled up"""
        
        used_p2_containers = [ref for ref in self._btn_reference if ref]
        used_comp_containers = [ref for ref in self._label_reference if ref]

        p2_full = len(used_p2_containers) == len(self._btn_reference)
        comp_full = len(used_comp_containers) == len(self._label_reference)


        if not p2_full or not comp_full: #Empty containers present: all good
            return

        # No empty containers: have to add some        
        self._btn_reference.append([])
        self._label_reference.append([])
        
        self._depot_p2_btns.append(tk.Button(self._p2_frame_int))
        self._player2_btns[max(self._player2_btns)+1] = self._depot_p2_btns[-1]
        # ic(len(self._depot_p2_btns), len(self._player2_btns))

        if not onlinePlayer:
            self._depot_comp_labels.append(tk.Label(self._comp_frame_int))
            self._computer_labels[max(self._computer_labels)+1] = self._depot_comp_labels[-1]
        else:
            self._depot_onlinep_labels.append(tk.Label(self._comp_frame_int))
            self._onlinep_labels[max(self._onlinep_labels)+1] = self._depot_onlinep_labels[-1]
        self.set_theme() # Sets the theme for the newly added widgets
        ic(len(self._player2_btns), len(self._computer_labels))
    
    def repopulate_cards_(self, onlinePlayer=False):
        """Repopulates by appending one more container (list) to the Button | Label references and
         one more Button | Label to the depots after the reference containers have all been filled up"""
        
        used_container = [ref for ref in self._btn_reference if ref]

        if len(used_container) != len(self._btn_reference): #Empty containers present
            return

        # No empty containers, have to add some        
        self._btn_reference.append([])
        self._label_reference.append([])
        
        self._depot_p2_btns.append(tk.Button(self._p2_frame_int))
        self._player2_btns[-1] = self._depot_p2_btns[-1]
        ic(len(self._depot_p2_btns), len(self._player2_btns))

        if not onlinePlayer:
            self._depot_comp_labels.append(tk.Label(self._comp_frame_int))
            self._computer_labels[-1] = self._depot_comp_labels[-1]
        else:
            self._depot_onlinep_labels.append(tk.Label(self._comp_frame_int))
            self._onlinep_labels[-1] = self._depot_onlinep_labels[-1]
        self.set_theme() # Sets the theme for the newly added widgets
        

    def player2_play(
            self, 
            card: list[tuple[tk.PhotoImage, tuple[str, int]]], 
            card_display_btn: tk.Button, 
            event=None
        ):
        """For player2 (actual player) to play his or her valid card"""
        if self.__check_checkmate:
            return
        
        if self.get_player_turn('p2'):
            try:
                if self._player2.play(card[0]):
                    player = 'op' if self._onlinePlayerActive else 'comp'
                    self.set_player_turn(player)
                    self.p2_request_card_with_20(card)
                    
                    self._played_card.configure(image=card[0][0])

                    if not self._onlinePlayerActive:
                        card_display_btn.after(500, self.compPlayEngine)
                    else:
                        self._onlineClient.send_data(card[0][1], 'CARD')

                    card_display_btn.grid_forget()
                    card.clear()

                    self.display_number_of_cards('player2')
                    self.pick_two(player)
                    self.go_gen_mart(player)
                    self.hold_on(player)
                    self.suspension(player)
                        
                    self._checkmate()
            except Main.WhotException as e:
                tmb.showwarning(title="INVALID MOVE", message=str(e).upper())
        else:
            tmb.showinfo("Not Your Turn", "Its not your turn to play")

    
    def p2_mart(self, power: int=None, event=None):
        """Responsible for making player2 to go to market (pick a card from the market)"""
        
        if not self.get_player_turn('p2') or self.__check_checkmate:
            return
        
        if power:
            if power == 2:
                self._check2 += 1
            elif power == 1:
                self._check1 += 1

        for o, i in enumerate(self._btn_reference):
            if not i:
                self._player2.gomart()
                self._btn_reference[o].append(self._player2.cards()[-1])
                new_btn = self._player2_btns.get(o)

                self._market_btn.grid_forget()
                self._root.after(100, lambda:self._market_btn.grid(row=2, column=0, sticky='w'))

                new_btn.config(image=self._player2.cards()[-1][0],
                            command=lambda: self.player2_play(self._btn_reference[o], self._player2_btns[o]))
        
                self._root.after(250, lambda: new_btn.grid(row=0, column=self._p2_btn_grid_pos, padx=6, pady=6))
        
                self._p2_btn_grid_pos -= 1
                if self._onlinePlayerActive:
                    self._onlineClient.send_data('MARKET', 'MART')
                # else:
                #     new_btn.after(500, self.compPlayEngine)
                break
        
        self.display_number_of_cards('player2')
        self.set_player_turn('comp') if not self._onlinePlayerActive else self.set_player_turn('op') 
        self.repopulate_cards()

        if self._check2 == 1:
            self._root.title(f'{self._title} - PICK TWO')
        elif self._check2 == 0 or not self._check2:
            self._root.title(self._title)
            self._root.after(500, self.compPlayEngine)
        else:
            self._root.title(self._title)
            self._root.after(500, self.compPlayEngine)

    def _check_p2(self, player='comp', event=None):
        """Checks whether player2 clicked the mart button twice (in other words, checks whether player2 has
        picked two cards) and then unfreezes player2 cards (buttons) - for PICK TWO"""

        player = 'comp' if not self._onlinePlayerActive else 'op'
        print(f'picking two for p2 by {player}')
        self.p2_mart(2)
        self.set_player_turn('p2')
        self._root.title(f'{self._title} - PICK TWO')

        if self._check2 == 2: # Done picking two cards
            self.set_player_turn(player)

            for btn in self._depot_p2_btns:
                btn.config(state='normal')
            self._check2 = 0
            self._market_btn.config(command=self.p2_mart)
            self._root.bind("<Return>", self.p2_mart)
            self._root.title(self._title)
        

    def _check_p1(self, player='comp', event=None):
        """Checks whether player2 clicked the mart button once (in other words, checks whether player2 has
        picked one card) and then unfreezes player2 cards (buttons) - for GENERAL MARKET"""
        player = 'comp' if not self._onlinePlayerActive else 'op'
        self.p2_mart(1)
        if self._check1 == 1:
            self.set_player_turn(player)

            for btn in self._depot_p2_btns:
                btn.config(state='normal')
            self._check1 = 0
            self._market_btn.config(command=self.p2_mart)
            self._root.bind("<Return>", self.p2_mart)
        

    def p2_request_card_with_20(self, card: list[tuple[tk.PhotoImage, tuple[str, int]]]):
        """Player2 (actual player) demands a particular card from computer after playing whot 20"""
        
        if len(self._player2.cards()) == 0 or not card[0][1][1] == 20:
            return

        self.set_player_turn('p2')

        card_root = tk.Toplevel(self._root)
        card_root.transient(self._root)
        x, y = self._root.winfo_x(), self._root.winfo_y()
        card_root.geometry('{}x{}+{}+{}'.format(230, 480, x, y))
        card_root.title("Ask for a card")
        card_root.resizable(False, False)

        theme = self._themes_dict.get(self._theme_var.get())
        label_theme, button_theme = theme, theme

        command = lambda card_name, toplev: self._p2_clicked_card(card_name, toplev)

        card_buttons = [
            ('Cross', self._cross_icon),
            ('Circle', self._circle_icon),
            ('Star', self._star_icon),
            ('Triangle', self._triangle_icon),
            ('Square', self._square_icon)
        ]

        for i, (card_name, icon) in enumerate(card_buttons):
            button = tk.Button(card_root, image=icon, command=lambda i=i: command(card_buttons[i][0], card_root), bg=button_theme)
            button.grid(row=i, column=0, pady=3)
            tk.Label(card_root, text=card_name, fg=label_theme).grid(row=i, column=1)

        lab = tk.Label(card_root, text='click your desired button\n to choose a card'.upper(), fg=label_theme)
        lab.grid(row=len(card_buttons), column=1, sticky='e')

        card_root.protocol('WM_DELETE_WINDOW', lambda: self._p2_clicked_card(None, card_root))
        card_root.focus_set()
        card_root.grab_set()

    def _p2_clicked_card(self, card: str, window: tk.Toplevel):
        """Registers player2's Desired card and calls player1 (computer or OP) to respond to the request"""
        if window:
            window.destroy()
            for i in self._depot_p2_btns:
                i.config(state='normal')
            self._market_btn.config(state='normal')
            window.grab_release()
        if card:
            player = 'comp' if not self._onlinePlayerActive else 'op'
            self.set_player_turn(player)
            if not self._onlinePlayerActive:
                self._whot.requests['player2'] = card
                #TODO
                self._player2.requested_card = card
                self._root.after(500, self.computer_response_to_card_20)
            else:
                self._onlineClient.send_data(card, data_type='REQUEST')

    def generate_shuffle_seed(self):
        return int.from_bytes(os.urandom(4), 'big')

    def reinitialize_cards(
            self, 
            onlinePlayer=False, 
            shuffle_seed: int=None, 
            conn_type='server', 
            player_turn: str=None
        ):
        
        self._onlinePlayerActive = onlinePlayer
        self._root.title(self._title)
        [btn.grid_forget() for btn in self._depot_p2_btns]
        [lab.grid_forget() for lab in self._depot_comp_labels]

        self._market_btn.grid_forget()
        self._played_card.grid_forget()

        if shuffle_seed:
            self._whot = Main.Whot(shuffle_seed)
        else:
            self._whot = Main.Whot()
        self._computer = Main.Computer()
        self._player2 = Main.Player2()
        self._onlinep = Main.OnlinePlayer()

        
        self._whot.InitDepot()
        self._whot.InitPlayerCards(onlinePlayer, conn_type)
        self.__check_checkmate = False

        if onlinePlayer:
            try:
                [lab.grid_forget() for lab in self._depot_onlinep_labels]
            except AttributeError as e:
                ic(e)
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
        # Butnrefs and Labrefs
        self._btn_reference: list[list[tuple[tk.PhotoImage, tuple[str, int]]]]
        self._btn_reference = [[] for _ in range(30)]
        self._depot_p2_btns = [tk.Button(self._p2_frame_int) for _ in range(30)]
        
        # Initialize and Display Player2 Buttons and Sync with their Button references (Butrefs)
        self._player2_btns = {i: self._depot_p2_btns[i] for i in range(30)}
        player2_cards = self._player2.cards()
        
        for i in range(5):
            self._btn_reference[i].append(player2_cards[i])
            self._player2_btns[i].config(
                image=player2_cards[i][0], 
                command=lambda i=i: self.player2_play(self._btn_reference[i], self._player2_btns[i]))

        self._label_reference: list[list[tuple[tk.PhotoImage, tuple[str, int]]]]

        if onlinePlayer:
            self._label_reference = [[] for _ in range(30)]
            self._depot_onlinep_labels = [tk.Label(self._comp_frame_int) for _ in range(30)]

            self._onlinep_labels = {i: self._depot_onlinep_labels[i] for i in range(30)}
            for i in range(5):
                self._onlinep_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._onlinep.cards()[i])

            # Overwrite Computer Objects with OnlinePlayer 
            #TODO: is this Necessary??
            self._computer = self._onlinep
            self._depot_comp_labels = self._depot_onlinep_labels
            self._computer_labels = self._onlinep_labels
        else:
            self._label_reference = [[] for _ in range(30)]
            self._depot_comp_labels = [tk.Label(self._comp_frame_int) for _ in range(30)]

            # Initialize and Display Computer Labels and Sync with their Label references (Labrefs)
            self._computer_labels = {i: self._depot_comp_labels[i] for i in range(30)}
            for i in range(5):
                self._computer_labels[i].config(image=self._misc_whot1)
                self._label_reference[i].append(self._computer.cards()[i])

        self._p2_btn_grid_pos, self._comp_lab_grid_pos = 1000, 1000
        # Played_card grid happens in animate_cards
        self._played_card = tk.Label(
            self._played_cards_frame, 
            image=self._whot.PlayedCards()[-1][0]
        )
        self._market_btn = tk.Button(
            self._root, 
            image=self._misc_whot, 
            command=self.p2_mart, state='disabled'
        )
        self._market_btn.grid(row=2, column=0, sticky='w')

    def start_multiplayer_server_client(self, event=None):
        if self._delay_multiplayer_for_animations:
            self.popup_message(title='Please Wait', text='Please wait for animations to finish',
                                wraplength=240)
            return
        
        multiplayer = self.multiplayer_gui()
        print('multiplayer -->', multiplayer)
        if multiplayer is None:
            return
        host, port, nickname, server_choice = multiplayer
        self._server_choice = server_choice
        # self._onlineNickname = nickname

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
                self.send_init_data_to_server(data=json.dumps(init_data), data_type='INIT_DATA')
            except (OSError, ConnectionRefusedError, AttributeError, TimeoutError, tk.TclError) as e:
                print(e)
                self._connectionFailed = True
        
        else: # choice -> 'join server'
            self._onlinePlayerActive = True
            self.start_init_client_thread(host, port)
            init_data = self.get_init_data_from_server(data_type='INIT_DATA')
            seed = init_data['seed']
            player_turn = init_data['player_turn']
            self._onlineNickname = init_data['nickname']
            self._onlineClient.send_data(nickname, data_type='NICKNAME')
            if not self._connectionFailed:
                self.reinitialize_cards(onlinePlayer=True, shuffle_seed=seed, conn_type='client', player_turn=player_turn)
        
        if not self._connectionFailed:
            self.start_listen_for_onlineP_card_thread()
        else:
            self._onlinePlayerActive = False
            self._connectionFailed = False
            self.__restart(force=True)
        self.balloon_bindings()
    
    def multiplayer_gui(self) -> tuple[str, int, str, str] | None:
        root = tk.Toplevel(self._root)
        root.transient(self._root)
        root.title("Multiplayer")
        geometry = self.set_toplevel_to_center(168, 274)
        root.geometry(geometry)
        return_value = None

        config = self._config['multiplayer']

        host_var, port_var = tk.StringVar(value=config['host']), tk.IntVar(value=config['port'])
        nickname_var = tk.StringVar(value=config['nickname'])
        server_var = tk.StringVar(value=config['server_choice'])

        host_label = ttk.Label(root, text='Host:', font="-family {Segoe UI} -size 10 -weight bold")
        host_label.place(relx=0.077, rely=0.06, height=28, width=48)
        port_label = ttk.Label(root, text='Port:', font="-family {Segoe UI} -size 10 -weight bold")
        port_label.place(relx=0.077, rely=0.238, height=23, width=38)

        host_entry = ttk.Entry(root, textvariable=host_var)
        host_entry.place(relx=0.31, rely=0.071, relheight=0.125
                , relwidth=0.569)
        port_entry = ttk.Entry(root, textvariable=port_var)
        port_entry.place(relx=0.31, rely=0.238, relheight=0.125
                , relwidth=0.569)
        
        nickname_label = ttk.Label(root, text='Nickname:', font="-family {Segoe UI} -size 10 -weight bold")
        nickname_label.place(relx=0.036, rely=0.417, height=19, width=68)
        nickname_entry = ttk.Entry(root, textvariable=nickname_var)
        nickname_entry.place(relx=0.303, rely=0.417, relheight=0.125, relwidth=0.569)

        start_server = ttk.Radiobutton(root, text='Start Server', variable=server_var, value='start server')
        start_server.place(relx=0.04, rely=0.655, relwidth=0.343, relheight=0.0, height=25)
        join_server = ttk.Radiobutton(root, text='Join Server', variable=server_var, value='join server')
        join_server.place(relx=0.661, rely=0.655, relwidth=0.307, relheight=0.0, height=25)

        def close_window(exit_btn=False):
            nonlocal return_value
            root.destroy()
            root.quit()

            host, port = host_var.get(), port_var.get()
            nickname, server_choice = nickname_var.get(), server_var.get()

            config['host'] = host
            config['port'] = port
            config['nickname'] = nickname
            config['server_choice'] = server_choice
            ic(self._config)
            self._write_config(plain_save=True)
            if exit_btn:
                return_value = None
            else:
                return_value = (host, port, nickname, server_choice)
            
        connect_btn = ttk.Button(root, text="Ok", command=close_window)
        connect_btn.place(relx=0.35, rely=0.833, height=25, width=86)
        host_entry.select_range(0, tk.END), port_entry.select_range(0, tk.END)
        nickname_entry.select_range(0, tk.END)

        root.protocol('WM_DELETE_WINDOW', lambda: close_window(exit_btn=True))

        root.focus_set()
        root.grab_set()
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
        listen_op_thread = threading.Thread(target=self.listen_for_onlineP_card)
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
            client = socketClient.Client(host, port, nickname, True)
        except ConnectionRefusedError as e:
            print(e)
            self._connectionFailed = True
        else:
            self._onlineClient = client
            print('client -->', self._onlineClient)
            return client
    
    def wait_for_client_to_connect(self, sleep_duration=1):
        while self._onlineClient is None and self._onlinePlayerActive:
            if self._connectionFailed:
                tmb.showerror('Connection Failed', 'No Server To Be Joined')
                return None
            time.sleep(sleep_duration)

    def get_init_data_from_server(self, data_type: str='INIT_DATA'):
        self.wait_for_client_to_connect()
        if data_type == 'INIT_DATA':
            client_init_data = self._onlineClient.client_init_data
            while self._onlinePlayerActive and not all(client_init_data.values()):
                print('client_init_data values -->', client_init_data.values(), all(client_init_data.values()))
                time.sleep(0.5)
            return client_init_data

    def send_init_data_to_server(self, data: int | str, data_type: Literal['INIT_DATA', 'INIT_DATA'] = 'INIT_DATA'):
        self.wait_for_client_to_connect()
        self._onlineClient.send_data(str(data), data_type)


    def listen_for_onlineP_card(self):
        self.wait_for_client_to_connect(2.5)
        
        while self._onlinePlayerActive:
            if self._server_choice == 'start server':
                nick = self._onlineClient.client_data['conn_nickname']
                self._onlineNickname = nick
            card = self._onlineClient.client_data['card']
            mart = self._onlineClient.client_data['mart']
            request = self._onlineClient.client_data['request']
            continue_ = self._onlineClient.client_data['continue']

            if continue_:
                print('\n^^^^ onlinep sent continue')
                self.continue_from_hold_or_suspension()

            if card:
                print('\n@@@@ onlineP sent card', card)
                index = self.get_onlinep_card_index(card)
                self.set_player_turn('op')
                self.onlinePlayer_play(self._label_reference[index][0], self._onlinep_labels[index])

            if mart: # Set for OP to play again
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
                if item[1] == card: # item[1] - ('Square', 2)
                    index = i
                    print(f"Index of {card}: ({i}, {j})")
                    break

        if index is None:
            raise Main.WhotException('Cant Find OnlineP Card In Cardstack')

        return index
            

    def onlinep_mart(self):
        if not self.get_player_turn('op') or self.__check_checkmate:
            print('\nin onlinep mart, its not op turn for mart')
            return

        for o, i in enumerate(self._label_reference):
            if not i:
                self._onlinep.gomart()

                self._label_reference[o].append(self._onlinep.cards()[-1])
                new_lab = self._onlinep_labels.get(o)

                new_lab.config(image=self._misc_whot1)
                new_lab.grid(row=0, column=self._comp_lab_grid_pos, padx=6, pady=6)
                self._comp_lab_grid_pos -=1
                break
        
        client_data = self._onlineClient.client_data
        client_data['mart'] = False # Reset
        self.display_number_of_cards('onlinep')
        self.handle_onlinep_todos()
        
        self.repopulate_cards(onlinePlayer=True)
        self._root.title(self._title)
    
    def handle_onlinep_todos(self, card=None):
        print('\n*** online_todos -->', self._onlinep_todo)
        if self._onlinep_todo['pick_two'] > 0:
            self._onlinep_todo['pick_two'] -= 1
            self.set_player_turn('p2' if self._onlinep_todo['pick_two'] == 0 else 'op')
        
        if self._onlinep_todo['general_market'] > 0:
            self._onlinep_todo['general_market'] -= 1
            self.set_player_turn('p2')
        
        if self._onlinep_todo['hold_on']:
            print('Continuing for P2 from OP')
            # self.popup_message("Continue", "Continue", 400)
            self._onlineClient.send_data('Continue', data_type='CONTINUE')
            self._onlinep_todo['hold_on'] =  False
            self.set_player_turn('p2')

        if self._onlinep_todo['suspension']:
            print('Continuing for P2 from OP')
            # self.popup_message("Continue", "Continue", 400)
            self._onlineClient.send_data('Continue', data_type='CONTINUE')
            self._onlinep_todo['suspension'] = False
            self.set_player_turn('p2')
        
        if card and card[1][1] == 20:
            self.set_player_turn('op')
        
        if not any(self._onlinep_todo.values()):
            print('no True values setting to p2...', self._onlinep_todo.values())
            self.set_player_turn('p2')
        print('joined or started -->', self._server_choice, '\n')

    def onlinep_request_card_with_20(self, request: str):
        #TODO: Make it such that the requested card is the only accepted card to be
        #TODO: played after the request (by one recursion) then market if card unavailable
        
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


    def onlinePlayer_play(self, 
            card: tuple[tk.PhotoImage, tuple[str, int]], 
            card_display_label: tk.Label, 
            event=None
        ):
        """For OnlinePlayer to play their valid card"""

        print(f'onlineplayer just played {card}')
        if self.get_player_turn('op') and not self.__check_checkmate:
            if self._onlinep.play(card):
                self._played_card.configure(image=card[0])
                card_display_label.grid_forget()

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
        
                self._checkmate()
            
            else: # Rare Happening
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
            if self._player2.p2_powerup_2[0] == 2:
                for _ in range(2):
                    self.apply_difficulty()
                    self.set_player_turn('comp')

                self._player2.p2_powerup_2.insert(0, 0)
                self.set_player_turn('p2')
            return
        
        elif player == 'op': # OP
            powerup = self._player2.p2_powerup_2
            if powerup[0] == 2:
                self.set_player_turn('op')
                self._onlinep_todo['pick_two'] = 2
                powerup.insert(0, 0)
                return
        
        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.op_powerup_2
            else:
                powerup = self._computer.comp_powerup_2
        
        
            if powerup[0] == 2:
                print('\nPICK TWO')
                self.popup_message("Pick Two", "Pick two cards from the mart")
                self._root.title(f'{self._title} - PICK TWO')
                for btn in self._depot_p2_btns:
                    btn.config(state='disabled')
                self._market_btn.config(command=self._check_p2)
                self._root.unbind("<Return>")
                self._root.bind("<Return>", self._check_p2)
                powerup.insert(0, 0)
    
    def go_gen_mart(self, player: Literal['p2', 'comp', 'op']):
        """Makes Player go to general market"""

        if player == 'comp':
            if self.get_player_turn('comp'):
                if self._player2.p2_powerup_14[0] == 14:
                    print("Computer Going to gen mart")

                    self.apply_difficulty()
            
                    self._player2.p2_powerup_14.insert(0, 0)
                    self.set_player_turn('p2')
            return
        
        elif player == 'op':
            logging.debug(f'GENERAL MARKET - {player}')
            powerup = self._player2.p2_powerup_14
            if powerup[0] == 14:
                self.set_player_turn('op')
                self._onlinep_todo['general_market'] = 1
                powerup.insert(0, 0)
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.op_powerup_14
            else:
                powerup = self._computer.comp_powerup_14

        if powerup[0] == 14:
            logging.debug(f'GENERAL MARKET - {player}')
            self.popup_message("General Market", "General Market")
            self._root.title(f'{self._title} - GENERAL MARKET')
            for i in self._depot_p2_btns:
                i.config(state='disabled')
            self._market_btn.config(command=self._check_p1)
            self._root.unbind("<Return>")
            self._root.bind("<Return>", self._check_p1)
            powerup.insert(0, 0)

    def hold_on(self, player: Literal['p2', 'comp', 'op']):
        """Makes Player to hold on until the other player plays another card or goes to the mart,
        after playing a card with number 1 in it"""

        if player == 'comp':
            if self._player2.p2_powerup_1[0] == 1:
                self.set_player_turn('p2')
                self._player2.p2_powerup_1.insert(0, 0)
            return
        
        elif player == 'op':
            logging.debug(f'HOLD ON - {player}')
            powerup = self._player2.p2_powerup_1
            if powerup[0] == 1:
                self.set_player_turn('p2')
                self._onlinep_todo['hold_on'] = True
                powerup.insert(0, 0)
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.op_powerup_1
            else:
                powerup = self._computer.comp_powerup_1
        
            if powerup[0] == 1:
                logging.debug(f'HOLD ON - {player}')
                self.popup_message("Hold On", "Hold On")
                self._root.title(f'{self._title} - HOLD ON')
                powerup.insert(0, 0)
                self._checkmate()
                if not self._onlinePlayerActive:
                    self._root.after(500, lambda: self.comp_card_streak(1))
                else:
                    self.set_player_turn('op')
                    # self.continue_from_hold_or_suspension()
                
            # self.set_player_turn('comp')

    def suspension(self, player: Literal['p2', 'comp', 'op']):
        """Just like hold on, it suspends the other player until they play
          another card or go to mart"""
        
        if player =='comp':
            if self._player2.p2_powerup_8[0] == 8:
                self.set_player_turn('p2')
                self._player2.p2_powerup_8.insert(0, 0)
            return
        
        elif player == 'op':
            logging.debug(f'SUSPENSION - {player}')
            powerup = self._player2.p2_powerup_8
            if powerup[0] == 8:
                self.set_player_turn('p2')
                self._onlinep_todo['suspension'] = True
                powerup.insert(0, 0)
                return

        elif player == 'p2':
            if self._onlinePlayerActive:
                powerup = self._onlinep.op_powerup_8
            else:
                powerup = self._computer.comp_powerup_8
            if powerup[0] == 8:
                logging.debug(f'SUSPENSION - {player}')
                self.popup_message("Hold On", "Suspension")
                self._root.title(f'{self._title} - SUSPENSION')

                powerup.insert(0, 0)
                self._checkmate()

                if not self._onlinePlayerActive:
                    self._root.after(500, lambda: self.comp_card_streak(8))
                else:
                    self.set_player_turn('op')
                    # self.continue_from_hold_or_suspension()
            # self.set_player_turn('p2')
    
    def continue_from_hold_or_suspension(self):
        print('\nin continue from suspension or hold, online todos -->', self._onlinep_todo)
        client_data = self._onlineClient.client_data
        continue_ = client_data['continue']
        if continue_:
            self.popup_message("Continue", "Continue", 400)
            client_data['continue'] = False
        
    ##################################################################################################

    def computer_play(
            self, 
            card: tuple[tk.PhotoImage, tuple[str, int]], 
            card_display_label: tk.Label
        ):
        """Plays any cards that are valid, from CompPlayEngine"""
        if not self.get_player_turn('comp') or self.__check_checkmate:
            return
        
        try:
            if self._computer.play(card):
                self._played_card.configure(image=card[0])

                caller_frame = inspect.currentframe().f_back
                caller_info = inspect.getframeinfo(caller_frame)
                grid_info = True if card_display_label.grid_info() else False
                ic(grid_info, caller_info.function)
                logging.debug(f'grid_info: {grid_info}, caller_method: {caller_info.function}')
                if not grid_info:
                    tmb.showwarning("Warning", "Card played isn't even grided yet!\nAttempting next available label")
                    card_display_label = next((i for i in self._computer_labels.values() if i.grid_info()))
                card_display_label.grid_forget()
                
                self.computer_request_card_with_20(card)                     
                self.display_number_of_cards('computer')
                self.pick_two('p2')
                self.go_gen_mart('p2')
                self.hold_on('p2')
                self.suspension('p2')

                self.set_player_turn('p2')
        
                self._checkmate()
            
            else: # Rare Happening
                raise Main.WhotException('Computer Played Invalid Card')
        #TODO
        except Main.WhotException as e:
            tmb.showerror('Computer Error', e)

    def compPlayEngine(self, event=None):
        # logging.debug('Engine triggered')
        if not self.get_player_turn('comp') and not self.__check_checkmate:
            return

        # if self._whot.requests['player2']: #TODO: Redundant???
        #     self.computer_response_to_card_20()

        if self._computer.requested_card_idx is not None:
            idx = self._computer.requested_card_idx
            card = self._label_reference[idx]
            ic(idx, card, self._label_reference.index(card))
            logging.debug(f'[requested_card_idx]: idx: {idx}, card: {card}, label_ref_index(card): {self._label_reference.index(card)}')
            if not card: #comp has somehow played that card (maybe p2 counter requested with whot20)
                self._computer.requested_card_idx = None
                return
            
            last_played_card = self._whot.PlayedCards()[-1]
            if (card[0][1][0] == last_played_card[1][0] or
                card[0][1][1] == last_played_card[1][1] or
                last_played_card[1][1] == 20):
                self.computer_play(
                    card[0], 
                    self._computer_labels.get(idx)
                )
                self._label_reference.pop(self._label_reference.index(card))
                self._computer.requested_card_idx = None
                return
            #card idx now useless as a counter powerup was played by p2
            self._computer.requested_card_idx = None

        containers = [self._found_20, self._found_num, self._found_str]
        lab_ref_idx = None

        for idx, card in enumerate(self._label_reference):
            if not card:
                continue
            
            if card[0][1][1] == 20:
                self.parse_and_remove_comp_cards(containers[0], card, idx)
                lab_ref_idx = idx
                break

            if not self._found_20 and card[0][1][1] == self._whot.PlayedCards()[-1][1][1]:
                self.parse_and_remove_comp_cards(containers[1], card, idx)
                lab_ref_idx = idx
                break

            if not self._found_num and not self._found_20 and card[0][1][0] == self._whot.PlayedCards()[-1][1][0]:
                self.parse_and_remove_comp_cards(containers[2], card, idx)
                lab_ref_idx = idx
                break
        
        # found_valid_card = []
        #! Must not change the order of containers
        found_valid_card = next((container for container in containers if container), None)
        ic(containers)

        if found_valid_card:
            self.comp_engine_play_valid_card(
                containers.index(found_valid_card), 
                found_valid_card[0][0],
                lab_ref_idx
            )
        else:
            # ic('applying difficulty (Mart)...')
            self.apply_difficulty()
        
        for container in containers:
            container.clear()


    def parse_and_remove_comp_cards(
            self, 
            found_card_container: list, 
            card: list[tuple[tk.PhotoImage, tuple[str, int]]],
            index: int):
        """Remove the computer card and add an empty list (card) to the same index in ``self._label_reference``"""
        ic('[parse comp cards]:', index)
        found_card_container.append(card)
        self._label_reference.insert(index, [])
        self._label_reference.pop(self._label_reference.index(card))

    
    def comp_engine_play_valid_card(
            self, 
            found_index: int, 
            card: tuple[tk.PhotoImage, tuple[str, int]],
            lab_ref_idx: int
        ):
        # ic.configureOutput(prefix='[Play Valid Card]: ')

        ic('[play valid card]:', found_index, card, lab_ref_idx, self._computer_labels.get(lab_ref_idx).grid_info())
        logging.debug(f'[Comp Play Valid Card]: {found_index}, {card[1]}, {lab_ref_idx}')
        if found_index == 1: # found num
            if card[1][1] == self._whot.PlayedCards()[-1][1][1]:
                self.computer_play(card, self._computer_labels.get(lab_ref_idx))
        elif found_index == 2: # found str
            if card[1][0] == self._whot.PlayedCards()[-1][1][0]:
                self.computer_play(card, self._computer_labels.get(lab_ref_idx))
        else:
            self.computer_play(card, self._computer_labels.get(lab_ref_idx))
    

    def comp_card_streak(self, card_streak_no: int):
        """This Searches For Similar Cards In Computer's Cardstack And Plays It.
        (Specifically Streaks For When Computer Encounters An 8 0r 1 Card - The Hold On And Suspension Cards)
        """
        
        if not self.__check_checkmate and not self._whot.requests['player2']:
            found_card_streak_no = []
            for idx, i in enumerate(self._label_reference):
                if i and i[0][1][1] == card_streak_no:
                    found_card_streak_no = [idx, i]
                    self._label_reference.insert(idx, [])
                    self._label_reference.pop(self._label_reference.index(i))
                    # print("\nfound a card streak -->", found_card_streak_no, "\n")
                    logging.debug(f'found a card streak --> {found_card_streak_no}')
                    ic(found_card_streak_no)
                    break

            self.set_player_turn('comp')

            #! Issue might be stemming from here
            #! might be supplying labels that arent displayed and we there grid forgetting
            if found_card_streak_no:
                self.computer_play(
                    found_card_streak_no[1][0], 
                    self._computer_labels.get(found_card_streak_no[0])
                )

            else:
                # Computer's continue has to be after it plays a non streak card
                self.compPlayEngine()

                self._root.after(250, lambda: self.popup_message("Continue", "Continue", 400))
                self.set_player_turn('p2')
                
        elif self._whot.requests['player2']:
            self._root.after(500, self.compPlayEngine)

    
    def comp_mart(self, gone_to_mart_before=False):
        """Responsible for making the computer to go to market (pick a card from the mart)
        The 'gone_to_mart_before' argument checks whether the computer has already gone to mart before if the
        `self._computer.gomart` has beeen called before"""

        if not self.get_player_turn('comp') or self.__check_checkmate:
            return
        
        for o, i in enumerate(self._label_reference):
            if not i:
                if not gone_to_mart_before:
                    self._computer.gomart()

                self._label_reference[o].append(self._computer.cards()[-1])

                new_lab = self._computer_labels.get(o)
                if new_lab.grid_info():
                    tmb.showwarning('Warning', 'Card from mart is already grided!')
                    new_lab = next((i for i in self._computer_labels.values() if not i.grid_info()))
                new_lab.config(image=self._misc_whot1)
                new_lab.grid(row=0, column=self._comp_lab_grid_pos, padx=6, pady=6)
                self._comp_lab_grid_pos -=1
                break

        self.display_number_of_cards('computer')
        self.set_player_turn('p2')    
        self.repopulate_cards()
        self._root.title(self._title)


    def computer_request_card_with_20(self, card: tuple[tk.PhotoImage, tuple[str, int]]):
        """Finds a viable (powerup) card to request from player2 after computer plays the Whot 20 card"""
        
        if card[1][1] != 20 or len(self._computer.cards()) == 0:
            return
        
        found_viable_card, idx = '', None

        for idx, i in enumerate(self._label_reference):
            if not i:
                continue
            if i[0][1][1] in [1, 2, 8, 14]:
                found_viable_card = i[0][1][0]
                break
        
        if not found_viable_card:
            f = next(((idx, i) for idx, i in enumerate(self._label_reference) if i and i[0][1][0] != 'whot'))
            idx, found_viable_card = f[0], f[1][0][1][0]

        #there'll always be a viable card, else tis checkmate!
        # print(f'found_viable_card for comp, setting self._whot.requests["computer"] to {found_viable_card}...')
        logging.debug(f'found_viable_card for comp, setting self._whot.requests["computer"] to {found_viable_card}...')
        tmb.showinfo("Request", f"I NEED {found_viable_card.upper()}")
        self._whot.requests['computer'] = found_viable_card
        self._root.title(f'{self._title} - Request {found_viable_card.upper()}')

        self._computer.requested_card_idx = idx
        ic(self._computer.requested_card_idx)
        logging.debug(f'computer requested card idx: {self._computer.requested_card_idx}')
        logging.debug(f'computer request and requests --> {self._whot.requests}')


    def computer_response_to_card_20(self):
        """Generates the computer's appropriate response to the requested
        whot card 20 by player2"""

        if not self.get_player_turn('comp') or self.__check_checkmate:
            return
        
        card = self._whot.requests['player2']
        for o, i in enumerate(self._label_reference):
            if i and i[0][1][0] == card:
                self._found_request.append([o, i])
                self._label_reference.insert(o, [])
                self._label_reference.pop(self._label_reference.index(i))
                break
    
        if self._found_request:
            ic('Computer playing p2 request rn...')
            logging.debug('Computer is playing p2 request rn...')
            i = self._found_request[0]
            self.computer_play(i[1][0], self._computer_labels.get(i[0])) #* The play function should clear p2 request
            self._found_request.clear()
            return

        else:
            ic('couldnt grant p2 request, going to mart...')
            logging.debug("computer doesnt have the card going to mart")
            self.apply_difficulty() #* The mart func will also clear p2 request


    def Manual(self, event=None):
        """See the Manual of the Game"""
        
        text = tk.Toplevel(self._root)
        text.geometry(self.set_toplevel_to_center(420, 650))
        text.title("<Manual>")
        text.transient(self._root)
        text.resizable(False, False)
        text_lab = tks.ScrolledText(text, wrap='word')
        text_lab.grid(row=0, column=0, sticky=tk.NSEW)
        text_lab.insert(1.0, manual)
        text.grid_rowconfigure(1, weight=1)
        text.grid_columnconfigure(0, weight=1)
        text_lab.configure(state='disabled', font=("Comic Sans Ms", 13))
        ttk.Button(text, text="Ok", command=text.destroy).grid()
        
    def _toggle_on_fullscreen(self, event=None):
        self._root.geometry('{}x{}+0+0'.format(*self.__full_size))

    def _toggle_off_fullscreen(self, event=None):
        self._root.geometry(self._orig_size)

    def _checkmate(self):
        """Freezes all the buttons and stops the computer or player2 from playing again
        if any one of the players cards finishes"""
        if len(self._player2.cards()) == 0:
            print("Last Card Has Been Played from you....")
            self.__checkcomp_played = True
            self.__check_checkmate = True
            self._root.unbind("<Return>")
            tmb.showinfo("Checkmate", "You are the winner")
            for i in self._depot_p2_btns:
                i.config(state='disabled')
            self._market_btn.config(state='disabled')
            self._root.title(f'{self._title} - Checkmate')
            self.__restart()
        
        if not self._onlinePlayerActive:
            cards_length = len(self._computer.cards())
            player = "Computer"
        else:
            cards_length = len(self._onlinep.cards())
            player = "OnlinePlayer"

        if cards_length == 0:
            self.__check2_played = True
            self.__check_checkmate = True
            self._root.unbind("<Return>")
            tmb.showinfo("Checkmate", f"The {player} is the winner")
            for i in self._depot_p2_btns:
                i.config(state='disabled')
            self._market_btn.config(state='disabled')
            self._root.title(f'{self._title} - Checkmate')
            self.__restart()
            
    def __restart(self, event=None, force=False):
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
                sys.exit(2)
        else:
            self.reinitialize_cards(onlinePlayer=False)

    def __exit(self):
        if self._onlinePlayerActive:
            self._onlinePlayerActive = False
            if not self._connectionFailed:
                if self._server_choice == 'start server':
                    self._onlineServer.shutdown()
                self._onlineClient.shutdown()
            # self._onlineServer.shutdown()
        
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
