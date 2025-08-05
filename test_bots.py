import socketio
import time
import random
import threading

class GameBot:
    def __init__(self, bot_id, room_id='test', table_bet=100):
        self.bot_id = bot_id
        self.name = f'Bot{bot_id}'
        self.room_id = room_id
        self.table_bet = table_bet
        # Habilitar reconexión automática
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=10, reconnection_delay=1)
        self.is_connected = False
        self.game_state = None
        self.my_player_data = None
        
        # Configurar eventos
        self.setup_events()
    
    def setup_events(self):
        @self.sio.event
        def connect():
            print(f'[{self.name}] Conectado al servidor')
            self.is_connected = True
            # Unirse a la sala
            self.sio.emit('join', {
                'username': self.name,
                'room_id': self.room_id,
                'table_bet': self.table_bet
            })
        
        @self.sio.event
        def disconnect():
            print(f'[{self.name}] Desconectado del servidor')
            self.is_connected = False
            # La reconexión se manejará automáticamente
        
        @self.sio.event
        def reconnect():
            print(f'[{self.name}] Reconectado al servidor')
        
        @self.sio.on('game_state')
        def on_game_state(data):
            self.game_state = data
            self.my_player_data = next((p for p in data['players'] if p['name'] == self.name), None)
            
            print(f'[{self.name}] Estado del juego: {data["game_phase"]}')
            print(f'[{self.name}] Jugador actual: {data.get("current_player")}')
            print(f'[{self.name}] Mi SID: {self.sio.sid}')
            
            # Si es mi turno, tomar acción
            if (self.my_player_data and 
                data['current_player'] == self.my_player_data['sid'] and 
                data['game_phase'] == 'betting'):
                print(f'[{self.name}] ¡Es mi turno!')
                self.take_action()
            
            # Si soy el primer bot y el juego está esperando, iniciar ronda
            if (self.bot_id == 1 and 
                data['game_phase'] in ['waiting', 'finished'] and 
                len(data['players']) >= 2):
                time.sleep(2)  # Esperar un poco
                print(f'[{self.name}] Iniciando nueva ronda...')
                self.sio.emit('start_game')
        
        @self.sio.on('error')
        def on_error(data):
            print(f'[{self.name}] Error: {data["message"]}')
    
    def take_action(self):
        if not self.game_state or not self.my_player_data:
            return
        
        # Estrategia simple del bot
        actions = []
        
        card_value = self.my_player_data['hand'][0]['rank']
        card_strength = Card.RANKS.index(card_value)
        
        if self.game_state['current_bet'] == 0:
            # Decisión inicial basada en fuerza de la carta
            if card_strength >= 8:  # J, Q, K
                actions.extend(['raise'] * 8 + ['call'] * 2)
            elif card_strength >= 4:  # 5-10
                actions.extend(['call'] * 7 + ['fold'] * 3)
            else:  # 2-4, A
                actions.extend(['fold'] * 6 + ['call'] * 4)
        else:
            # Decisión ante apuesta existente
            required_to_call = self.game_state['current_bet'] - self.my_player_data['current_bet']
            if required_to_call <= 0:
                return
                
            if card_strength >= 9 and self.my_player_data['chips'] >= required_to_call + self.game_state['raise_amount']:
                actions.extend(['raise'] * 7 + ['call'] * 3)
            elif card_strength >= 6 and self.my_player_data['chips'] >= required_to_call:
                actions.extend(['call'] * 8 + ['fold'] * 2)
            else:
                actions = ['fold']
        
        action = random.choice(actions)
        
        print(f'[{self.name}] Tomando acción: {action}')
        time.sleep(1)  # Simular tiempo de pensamiento
        
        self.sio.emit('player_action', {'action': action})
    
    def connect_to_server(self):
        try:
            if self.is_connected:
                print(f"[{self.name}] Ya está conectado, desconectando primero...")
                self.disconnect_from_server()
                time.sleep(1)  # Esperar un poco antes de reconectar
            
            print(f"[{self.name}] Conectando al servidor...")
            self.sio.connect('http://localhost:5000', wait=True)  # Cambiar a wait=True para asegurar conexión
            time.sleep(0.5)  # Pequeña pausa para asegurar que la conexión se establece
            return True
        except Exception as e:
            print(f"[{self.name}] Error al conectar: {e}")
            return False
    
    def disconnect_from_server(self):
        if self.is_connected:
            self.sio.disconnect()

def run_bot(bot_id, room_id='test', table_bet=100):
    bot = GameBot(bot_id, room_id, table_bet)
    if bot.connect_to_server():
        try:
            # Usar un bucle para mantener el bot funcionando y manejar reconexiones
            while True:
                if not bot.is_connected:
                    time.sleep(1)  # Esperar antes de intentar reconectar
                    bot.connect_to_server()
                time.sleep(0.1)  # Reducir uso de CPU
        except KeyboardInterrupt:
            print(f'[Bot{bot_id}] Deteniendo bot...')
        finally:
            bot.disconnect_from_server()

if __name__ == '__main__':
    import sys
    
    num_bots = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    room_id = sys.argv[2] if len(sys.argv) > 2 else 'test'
    table_bet = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    
    print(f'Iniciando {num_bots} bots en sala "{room_id}" con apuesta {table_bet}')
    
    threads = []
    for i in range(1, num_bots + 1):
        thread = threading.Thread(target=run_bot, args=(i, room_id, table_bet))
        thread.daemon = True
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Esperar entre conexiones
    
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print('\nDeteniendo todos los bots...')