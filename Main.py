from random import shuffle, choice
import random
from GameImages import images
import tkinter as tk
from typing import Literal
import logging
logging.basicConfig(filename='whot.log', level=logging.DEBUG, datefmt='%H:%M:%S')


class Whot(images):
    'A Game of cards usually involving two players by default, see manual for more info.'
    
    Cards: list[tuple[tk.PhotoImage, tuple[str, int]]] = []
    requests: dict[str, str | None] = {
            'player2': None,
            'computer': None,
            'onlineplayer': None
        }
    def __init__(self, shuffle_seed: int=None):
        if shuffle_seed:
            random.seed(shuffle_seed)
            print('\n$$$$$ Seed implemented in main -->', shuffle_seed, '$$$$$\n')

        self.powerup_cards = {
            1: False,
            2: False,
            8: False,
            14: False,
        }

        super().__init__()
        
    def InitDepot(self):
        'Initialize the depot cards'
        Whot.Cards = self._DepotMarket.copy()
        shuffle(Whot.Cards)

    def NormCards(self):
        'Replace the last card if it has a powerup in it'

        played_cards = self.PlayedCards()
        if played_cards[-1][1][1] not in [20, 1, 2, 8, 14]:
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
        'Loops depot cards if they are less than or equal to 6'
        if len(Whot.Cards) <= 6:
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
                Whot.Cards.pop(Whot.Cards.index(i))
                found_num = True
                break
        return found_num
            
    
class Computer(Whot):
    'Objects and attributes for Computer'
    def __init__(self):

        self.requested_card_idx: int = None
        super().__init__()

    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'Computer plays a valid card in their cardstack'

        self.LoopDepot()
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]
            
            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):

                self.handle_requests()
                
                logging.debug(f'[Computer played]; {playcard[1]} length; {len(self.cards())}')
                
                if playcard[1][1] in self.powerup_cards:
                    self.powerup_cards[playcard[1][1]] = True
                
                self.PlayedCards().append(playcard)
                self.cards().remove(playcard)
                
                return True
            else:
                raise WhotException("Error: Invalid Move!")
        else:
            raise WhotException("Error: Playcard is not in your cardstack!")

    def handle_requests(self):
        if self.requests['computer']:
            self.requests['computer'] = None

    def cards(self) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        "returns Computer's (computer) cards"
        return card1

    def gomart(self):
        'Sends Computer to Market'
        self.LoopDepot()
        self.cards().append(Whot.Cards.pop(0))
        self.handle_requests()
        logging.debug(f'[Computer] went to market: {self.cards()[-1][1]}')

        

class Player2(Whot):
    'Objects and attributes for Player2'
    def __init__(self):

        self.requested_card: str = None #TODO: May be deprecated in the future
        super().__init__()
        
    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'Player2 Plays a valid card in his/her cardstack'
        # (<tkinter.PhotoImage object at 0x000001A7D9740110>, ('triangle', 8))

        self.LoopDepot()
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]

            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):
                
                self.handle_requests(playcard)

                logging.debug(f'[Player2 played]; {playcard[1]} length; {len(self.cards())}')

                if playcard[1][1] in self.powerup_cards:
                    self.powerup_cards[playcard[1][1]] = True

                self.PlayedCards().append(playcard)
                self.cards().remove(playcard)

                return True
            else:
                raise WhotException("Error: Invalid Move!")
        else:
            raise WhotException("Error: Playcard is not in your cardstack!")
    
    def handle_requests(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]=None, mart=False):
        if playcard:
            if self.requests['onlineplayer'] or self.requests['computer']:
                request = self.requests['onlineplayer'] or self.requests['computer']
                if playcard[1][0] != request and playcard[1][1] != 20:
                    raise WhotException(f"Error your opponent requested for {request} and not {playcard[1][0]}!")
                else:
                    self.requests['onlineplayer'] = None
                    self.requests['computer'] = None

            if self.requested_card and playcard[1][0] != self.requested_card:
                raise WhotException(f"Nigga Play The Card You Just Requested Hint: {self.requested_card}!")
            else:
                self.requested_card = None
            if mart:
                self.requested_card = None
        else:
            self.requests['onlineplayer'] = None
            self.requests['computer'] = None


    def cards(self) -> list[tuple[tk.PhotoImage, tuple[str, int]]]:
        "returns Player2's cards"
        return card2

    def gomart(self):
        "Sends player2 to market"
        self.LoopDepot()
        self.cards().append(Whot.Cards.pop(0))
        #! incase the player goes to mart from absence of the requested card
        self.handle_requests(mart=True)
        logging.debug(f'[Player2] went to market: {self.cards()[-1][1]}')



class OnlinePlayer(Whot):
    'Objects and attributes for OnlinePlayer'
    def __init__(self):
        
        super().__init__()

    def play(self, playcard: tuple[tk.PhotoImage, tuple[str, int]]):
        'OnlinePlayer Plays a valid card in his/her cardstack'

        self.LoopDepot()
        if playcard in self.cards():
            last_played_card = self.PlayedCards()[-1]

            if (playcard[1][0] == last_played_card[1][0] or
                playcard[1][1] == last_played_card[1][1] or
                playcard[1][1] == 20 or last_played_card[1][1] == 20):
                
                if self.requests['player2']:
                    request = self.requests['player2']
                    if playcard[1][0] != request and playcard[1][1] != 20:
                        raise WhotException(f"Error your opponent requested for {request} and not {playcard[1][0]}!")
                    else:
                        self.requests['player2'] = None

                logging.debug(f'[OnlinePlayer played]; {playcard[1]} length: {len(self.cards())}')

                if playcard[1][1] in self.powerup_cards:
                    self.powerup_cards[playcard[1][1]] = True

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
        self.cards().append(Whot.Cards.pop(0))

        

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
    app.InitDepot()
    app.InitPlayerCards()
    app.InitComputerCards()
    app.InitPlayer2Cards()
    app.NormCards()
    p1 = Computer()
    p2 = Player2()
