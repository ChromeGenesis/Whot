from random import shuffle, choice
import random
from GameImages import images
import tkinter as tk
from typing import Literal
import os

class Whot(images):
    'A Game of cards usually involving two players by default, see manual for more info.'
    def __init__(self, shuffle_seed=None):
        if shuffle_seed:
            random.seed(shuffle_seed)
            print('\n$$$$$ Seed implemented in main -->', shuffle_seed, '$$$$$\n')
        
        super().__init__()
        
    def InitDepot(self):
        'Initialize the depot cards'
        Whot.Cards = self._DepotMarket.copy()
        shuffle(Whot.Cards)

    def NormCards(self):
        'Normalize the cards if startcard has whot 20 in it'

        played_cards = self.PlayedCards()
        if played_cards[-1][1][1] != 20:
            return
        
        misc_cards = [i for i in Whot.Cards[:4] if i not in played_cards]
        Whot.Cards = [i for i in Whot.Cards if i not in misc_cards]
        shuffle(misc_cards)
        played_cards.append(choice(misc_cards))
        self.NormCards()
            
        
    def InitPlayerCards(self, multiplayer=False, server_or_client: Literal['server', 'client']='server'):
        'Initialize player cards and Starting (played) cards'
        if multiplayer:
            # switch ze cards
            if server_or_client == 'client':
                self._startcard2 = Whot.Cards[0:5]
                self._startcard1 = Whot.Cards[5:10] #First 5 cards
            else:
                self._startcard1 = Whot.Cards[0:5] #First 5 cards
                self._startcard2 = Whot.Cards[5:10] #second 5 cards
        else:
            self._startcard1 = Whot.Cards[0:5] #First 5 cards
            self._startcard2 = Whot.Cards[5:10] #second 5 cards
        self.PlayedCards().append(Whot.Cards[10]) #set the played card
        Whot.Cards = Whot.Cards[11:] #remove the first 10 cards and the appended played card from the Whot.Cards

    def LoopDepot(self):
        'Loops depot cards if they are less than or equal to 14'
        if len(Whot.Cards) <= 14:
            self.InitDepot()


    def PlayedCards(self, cards=[]) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        'Returns the played cards in a nested tuple'
        return cards

    def InitComputerCards(self):
        'Initializes the cards for Computer to start'
        global card1
        card1 = self._startcard1

    def InitPlayer2Cards(self):
        'Initializes the cards for Player2 to start'
        global card2
        card2 = self._startcard2
    
    def InitOnlinePlayerCards(self):
        'Initializes the cards for OnlinePlayer to start'
        global card1
        card1 = self._startcard1

    def search_and_append(self, num: int, player: Literal['comp', 'p2', 'op']):
        found_num = False
        for o, i in enumerate(Whot.Cards):
            if i[1][1] == num:
                player_cards = {'comp': card1, 'p2': card2, 'op': card1}
                player_cards[player].append(i)
                Whot.Cards.remove(Whot.Cards[o])
                found_num = True
                break
        return found_num
            
    
class Computer(Whot):
    'Objects and attributes for Computer'
    def __init__(self):
        super().__init__()
        self.comp_powerup_2=[0]
        self.comp_powerup_8=[0]
        self.comp_powerup_1=[0]
        self.comp_powerup_14=[0]
        self.comp_powerup_20=[0]

    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'Computer plays a valid card in their cardstack'

        self.LoopDepot()
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]
            
            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):
                
                print(playcard[1], "Has been played")
                
                powerup_cards = {
                    1: self.comp_powerup_1,
                    2: self.comp_powerup_2,
                    8: self.comp_powerup_8,
                    14: self.comp_powerup_14,
                    20: self.comp_powerup_20
                }
                
                if playcard[1][1] in powerup_cards:
                    powerup_cards[playcard[1][1]].insert(0, playcard[1][1])
                
                self.PlayedCards().append(playcard)
                self.cards().remove(playcard)
                
                return True
            else:
                raise WhotException("Error: Invalid Move!")
        else:
            raise WhotException("Error: Playcard is not in your cardstack!")


    def cards(self) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        "returns Computer's (computer) cards"
        return card1

    def gomart(self):
        'Sends Computer to Market'
        self.LoopDepot()
        self.cards().append(Whot.Cards[11])
        Whot.Cards.remove(Whot.Cards[11])

    def gogenmart(self):
        "General market"
        self.LoopDepot()
        self.cards().append(Whot.Cards[12])
        Whot.Cards.remove(Whot.Cards[12])
        

class Player2(Whot):
    'Objects and attributes for Player2'
    def __init__(self):
        super().__init__()
        self.p2_powerup_2=[0]
        self.p2_powerup_1=[0]
        self.p2_powerup_8=[0]
        self.p2_powerup_14=[0]
        self.p2_powerup_20=[0]
        
        self.check_requested = False
        self.request: str = ''
        
    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'Player2 Plays a valid card in his/her cardstack'
        # (<tkinter.PhotoImage object at 0x000001A7D9740110>, ('triangle', 8))

        self.LoopDepot()
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]

            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):
                
                if self.check_requested:
                    if playcard[1][0] != self.request and playcard[1][1] != 20:
                        raise WhotException(f"Error your opponent requested for {self.request} and not {playcard[1][0]}!")
                    else:
                        self.check_requested = False
                        self.request = ''

                print(playcard[1], "Has been played")

                powerup_cards = {
                    1: self.p2_powerup_1,
                    2: self.p2_powerup_2,
                    8: self.p2_powerup_8,
                    14: self.p2_powerup_14,
                    20: self.p2_powerup_20
                }

                if playcard[1][1] in powerup_cards:
                    powerup_cards[playcard[1][1]].insert(0, playcard[1][1])

                self.PlayedCards().append(playcard)
                self.cards().remove(playcard)

                return True
            else:
                raise WhotException("Error: Invalid Move!")
        else:
            raise WhotException("Error: Playcard is not in your cardstack!")

    def cards(self) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        "returns Player2's cards"
        return card2

    def gomart(self):
        "Sends player2 to market"
        self.LoopDepot()
        self.cards().append(Whot.Cards[13])
        Whot.Cards.remove(Whot.Cards[13])

    def gogenmart(self):
        "Gen market"
        self.LoopDepot()
        self.cards().append(Whot.Cards[14])
        Whot.Cards.remove(Whot.Cards[14])


class OnlinePlayer(Whot):
    'Objects and attributes for OnlinePlayer'
    def __init__(self):
        super().__init__()
        self.op_powerup_2=[0]
        self.op_powerup_1=[0]
        self.op_powerup_8=[0]
        self.op_powerup_14=[0]
        self.op_powerup_20=[0]

        self.check_requested = False
        self.request: str = ''

    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'OnlinePlayer Plays a valid card in his/her cardstack'

        self.LoopDepot()
        # print(f'\n@@@in main: OP play, card is {playcard} \nand cardstack is {self.cards()}')
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]

            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):
                
                if self.check_requested:
                    if playcard[1][0] != self.request and playcard[1][1] != 20:
                        raise WhotException(f"Error your opponent requested for {self.request} and not {playcard[1][0]}!")
                    else:
                        self.check_requested = False
                        self.request = ''

                print(playcard[1], "Has been played")

                powerup_cards = {
                    1: self.op_powerup_1,
                    2: self.op_powerup_2,
                    8: self.op_powerup_8,
                    14: self.op_powerup_14,
                    20: self.op_powerup_20
                }

                if playcard[1][1] in powerup_cards:
                    powerup_cards[playcard[1][1]].insert(0, playcard[1][1])

                self.PlayedCards().append(playcard)
                self.cards().remove(playcard)

                return True
            else:
                raise WhotException("Error: Invalid Move!")
        else:
            raise WhotException("Error: Playcard is not in your cardstack!")


    def cards(self) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        "returns OnlinePlayer's cards"
        return card1
        
    def gomart(self):
        "Sends OnlinePlayer to market"
        self.LoopDepot()
        self.cards().append(Whot.Cards[13])
        Whot.Cards.remove(Whot.Cards[13])

    def gogenmart(self):
        "Gen market"
        self.LoopDepot()
        self.cards().append(Whot.Cards[14])
        Whot.Cards.remove(Whot.Cards[14])
        

class WhotException(Exception):
    "Exception for the Whot class"
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message

if __name__ == '__main__':
    yap = tk.Tk()
    app = Whot()
    #app.Init()
    app.InitDepot()
    app.InitPlayerCards()
    app.InitComputerCards()
    app.InitPlayer2Cards()
    app.NormCards()
    p1 = Computer()
    p2 = Player2()