import random
import time

class Card:
    RANKS = ['K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2', 'A']
    SUITS = ['♠', '♥', '♦', '♣']
    
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        
    def __str__(self):
        return f"{self.rank}{self.suit}"
    
    def __lt__(self, other):
        return Card.RANKS.index(self.rank) > Card.RANKS.index(other.rank)
    
    def __eq__(self, other):
        return self.rank == other.rank

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in Card.RANKS for suit in Card.SUITS]
        self.shuffle()
        
    def shuffle(self):
        random.shuffle(self.cards)
        
    def deal(self):
        return self.cards.pop() if self.cards else None

class Player:
    def __init__(self, name, chips=1000, is_human=False):
        self.name = name
        self.chips = chips
        self.hand = None
        self.streak = 0
        self.is_human = is_human
        self.in_round = True
        
    def place_bet(self, amount):
        if self.chips < amount:
            return False
        self.chips -= amount
        return amount
    
    def decide_raise(self):
        if self.is_human:
            print(f"\n{self.name}, tu carta: {self.hand}")
            return input("¿Quieres subir? (s/n): ").lower() == 's'
        # Bot: 40% de probabilidad de subir con carta media/alta
        rank_idx = Card.RANKS.index(self.hand.rank)
        return random.random() < 0.4 if rank_idx < 8 else random.random() < 0.7
    
    def decide_call(self):
        if self.is_human:
            print(f"\n{self.name}, tu carta: {self.hand}")
            return input("¿Igualas la subida? (s/n): ").lower() == 's'
        # Bot: 60% de probabilidad de igualar con carta media/alta
        rank_idx = Card.RANKS.index(self.hand.rank)
        return random.random() < 0.6 if rank_idx < 8 else random.random() < 0.8

class Game:
    def __init__(self, players, table_bet=10):
        self.players = players
        self.table_bet = table_bet
        self.deck = Deck()
        self.pot = 0
        self.final_pot = 0
        self.round_winner = None
        self.game_winner = None
        
    def start_round(self):
        # Reiniciar estado de jugadores
        for player in self.players:
            player.in_round = True
            player.hand = None
        
        # Apuesta inicial
        self.pot = 0
        for player in self.players:
            bet = player.place_bet(self.table_bet)
            self.pot += bet
            print(f"{player.name} apuesta {self.table_bet} unidades")
        
        # Repartir cartas
        self.deck = Deck()
        for player in self.players:
            player.hand = self.deck.deal()
        
        # Fase de subida
        raiser = None
        active_players = self.players.copy()
        
        for player in active_players.copy():
            if not player.in_round:
                continue
                
            if raiser is None:  # Nadie ha subido todavía
                if player.decide_raise():
                    bet = player.place_bet(20)
                    if bet:
                        self.pot += bet
                        print(f"\n¡{player.name} sube la apuesta!")
                        raiser = player
                    else:
                        player.in_round = False
                        print(f"{player.name} no puede subir y se retira")
        
        # Procesar decisiones después de una subida
        if raiser:
            for player in active_players.copy():
                if player != raiser and player.in_round:
                    if player.decide_call():
                        bet = player.place_bet(20)
                        if bet:
                            self.pot += bet
                            print(f"{player.name} iguala la subida")
                        else:
                            player.in_round = False
                            print(f"{player.name} no puede igualar y se retira")
                    else:
                        player.in_round = False
                        print(f"{player.name} no iguala y se retira")
        
        # Determinar ganador
        active_players = [p for p in self.players if p.in_round]
        
        # Caso 1: Solo un jugador activo
        if len(active_players) == 1:
            self.round_winner = active_players[0]
            print(f"\n¡{self.round_winner.name} gana por retirada de los demás!")
        
        # Caso 2: Varios jugadores activos
        else:
            print("\n¡Revelación de cartas!")
            highest_card = None
            potential_winners = []
            
            for player in active_players:
                print(f"{player.name} muestra {player.hand}")
                if highest_card is None or player.hand > highest_card:
                    highest_card = player.hand
                    potential_winners = [player]
                elif player.hand == highest_card:
                    potential_winners.append(player)
            
            # Manejar empates
            if len(potential_winners) > 1:
                print("\n¡Empate entre:", ", ".join([p.name for p in potential_winners]), "!")
                print("Se repite la ronda con los mismos jugadores...")
                self.pot *= 2  # Ambas mitades se mantienen
                time.sleep(2)
                return self.start_round()  # Recursividad para repetir ronda
            
            self.round_winner = potential_winners[0]
            print(f"\n¡{self.round_winner.name} gana con {self.round_winner.hand}!")
        
        # Distribuir premios
        winner_share = self.pot // 2
        self.round_winner.chips += winner_share
        self.final_pot += self.pot - winner_share
        
        # Actualizar racha
        self.round_winner.streak += 1
        for player in self.players:
            if player != self.round_winner:
                player.streak = 0
        
        # Verificar ganador del juego
        if self.round_winner.streak >= 3:
            self.game_winner = self.round_winner
            self.final_pot += winner_share  # El pozo final incluye todo
            
        return self.round_winner

# Configuración del juego
if __name__ == "__main__":
    print("¡Bienvenido a 'La Más Alta Gana'!")
    mesa = int(input("Elige mesa (10, 100, 1000): "))
    humanos = int(input("Número de jugadores humanos: "))
    bots = int(input("Número de bots: "))
    
    players = []
    for i in range(humanos):
        name = input(f"Nombre del jugador humano {i+1}: ")
        players.append(Player(name, is_human=True, chips=5000))
    
    for i in range(bots):
        players.append(Player(f"Bot_{i+1}", chips=5000))
    
    game = Game(players, table_bet=mesa)
    round_count = 0
    
    while not game.game_winner:
        round_count += 1
        print(f"\n{'='*50}")
        print(f"RONDA {round_count}")
        print(f"Pozo Final: {game.final_pot} unidades")
        for player in players:
            print(f"{player.name}: {player.chips} fichas | Racha: {player.streak}")
        
        winner = game.start_round()
        print(f"\nResultado ronda:")
        print(f"Ganador: {winner.name} (+{game.pot//2} fichas)")
        print(f"Racha actual: {winner.streak} victorias consecutivas")
        
        if game.game_winner:
            print(f"\n¡{winner.name} ha ganado 3 rondas consecutivas y el juego!")
            print(f"¡Premio final: {game.final_pot} fichas!")
            break
        
        # Rotar orden de jugadores
        players = players[1:] + [players[0]]
        time.sleep(3)