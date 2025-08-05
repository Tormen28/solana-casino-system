from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import time
import threading
import json
import os
from datetime import datetime
import requests
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from helius_integration import initialize_helius, get_helius_client, get_wallet_info_for_game
from dotenv import load_dotenv
from security_integration import (
    SecurityManager, rate_limit, audit_log, 
    validate_withdrawal_security, update_withdrawal_security,
    get_security_status
)
from functools import wraps
import hashlib
import hmac

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'una-clave-secreta-muy-segura-por-defecto')
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar Helius (usar variable de entorno para la API key)
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
if not HELIUS_API_KEY:
    raise EnvironmentError("HELIUS_API_KEY environment variable not set.")
HELIUS_NETWORK = os.getenv('HELIUS_NETWORK', 'devnet')

try:
    helius_client = initialize_helius(HELIUS_API_KEY, HELIUS_NETWORK)
    print(f"✅ Helius inicializado correctamente en {HELIUS_NETWORK}")
except Exception as e:
    print(f"❌ Error inicializando Helius: {e}")
    helius_client = None

# ----------------- Blockchain & Database Setup -----------------
CUSTODIAL_ADDRESS = os.getenv('CUSTODIAL_ADDRESS', 'YOUR_CUSTODIAL_SOL_ADDRESS')
COMMISSION_ADDRESS = os.getenv('COMMISSION_ADDRESS', '')
# Eliminado duplicado: la variable se valida al inicio del archivo
DB_URL = os.getenv('DB_URL', 'sqlite:///game.db')

engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PlayerAccount(Base):
    __tablename__ = 'players'
    wallet = Column(String, primary_key=True, index=True)
    chips = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Modelo de Usuario/Perfil
class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(50), unique=True, nullable=False)
    username = Column(String(50), nullable=False)
    chips = Column(Integer, default=100)  # Fichas iniciales
    total_games = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'username': self.username,
            'chips': self.chips,
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

# Modelo de Transacciones
class UserTransaction(Base):
    __tablename__ = 'user_transactions'
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(50), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # deposit, withdraw, bet, win
    amount = Column(Float, nullable=False)
    signature = Column(String(100), nullable=True)
    status = Column(String(20), default='success')  # success, failed, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String(200), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'wallet_address': self.wallet_address,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'signature': self.signature,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'description': self.description
        }

Base.metadata.create_all(bind=engine)
# Inicializar sistema de seguridad avanzada
try:
    security_manager = SecurityManager()
    # Las tablas se inicializan automáticamente en __init__
    print("✅ Sistema de seguridad avanzada inicializado")
except Exception as e:
    print(f"⚠️ Error inicializando seguridad: {e}")
    security_manager = None



def sync_all_players_chips(players):
    """Sincroniza las fichas de todos los jugadores proporcionados."""
    db = SessionLocal()
    for p in players:
        if not getattr(p, 'is_bot', False):
            profile = db.query(UserProfile).filter_by(username=p.name).first()
            if profile:
                profile.chips = p.chips
    db.commit()
    db.close()

def load_user_chips(username):
    """Carga las fichas del usuario desde la base de datos."""
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter_by(username=username).first()
        if profile:
            return profile.chips
        return 100  # Fichas por defecto si no existe el perfil
    finally:
        db.close()

TOKENS_PER_SOL = 100_000  # 1 SOL = 100 000 fichas
MIN_WITHDRAW_TOKENS = 1_000  # mínimo para retirar (reducido a 1,000 fichas)
WITHDRAW_FEE_PERCENT = 5

# Clases del juego "La Más Alta Gana"
class Card:
    # Orden de mayor a menor: K > Q > J > 10 > ... > 2 > A
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    SUITS = ['♠', '♥', '♦', '♣']
    
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    
    def get_value(self):
        # Retorna el valor numérico (mayor número = mayor valor)
        return Card.RANKS.index(self.rank)
    
    def to_dict(self):
        return {'rank': self.rank, 'suit': self.suit}
    
    def __str__(self):
        return f"{self.rank}{self.suit}"

class Player:
    def __init__(self, sid, name, chips):
        self.sid = sid
        self.name = name
        self.chips = chips
        self.hand = []
        self.is_folded = False
        self.is_bot = False
        self.has_acted = False
        self.current_bet = 0
        self.is_disconnected = False

    def bet(self, amount):
        if self.chips >= amount:
            self.chips -= amount
            return amount
        else:
            # Si no puede cubrir la apuesta, va all-in
            all_in_amount = self.chips
            self.chips = 0
            return all_in_amount

    def fold(self):
        self.is_folded = True
        self.has_acted = True



    def to_dict(self):
        return {
            'id': self.sid, # Frontend uses 'id'
            'name': self.name,
            'chips': self.chips,
            'hand': [c.to_dict() for c in self.hand],
            'is_folded': self.is_folded,
            'has_acted': self.has_acted,
            'current_bet': self.current_bet,
            'is_disconnected': self.is_disconnected,
            'is_bot': self.is_bot,
            'win_streak': 0 # This will be handled in get_state
        }


    def evaluate_hand(self):
        return self.hand[0].get_value() if self.hand else 0

class BotPlayer(Player):
    def __init__(self, sid, name, chips):
        super().__init__(sid, name, chips)
        self.is_bot = True

    def choose_action(self, current_bet, raise_amount):
        card_value = self.evaluate_hand()
        # Simple strategy: raise with K, Q, J. Call with 10, 9, 8. Fold otherwise.
        if card_value >= Card.RANKS.index('J'):
            return 'raise', raise_amount
        elif card_value >= Card.RANKS.index('8'):
            return 'call', current_bet
        else:
            return 'fold', 0

class GameRoom:
    def __init__(self, room_id, table_bet=100):
        self.room_id = room_id
        self.table_bet = table_bet  # Apuesta base de la mesa (10, 100, 1000)
        self.players = []
        self.deck = []
        self.pot = 0  # Pozo simple como en el original
        self.final_pot = 0  # Pozo final acumulado
        self.raise_amount = 20  # Monto fijo para subir
        self.phase = 'waiting'  # waiting, betting, revealing, finished
        self.current_turn_index = -1
        self.winner = None
        self.win_streaks = {}
        self.players_in_round = []  # Jugadores que siguen en la ronda actual
        self.has_raise = False  # Si alguien ha subido en esta ronda
        self.raiser = None  # Quién subió la apuesta

    def add_player(self, player):
        if len(self.players) < 4:
            self.players.append(player)
            self.win_streaks[player.sid] = 0
            return True
        return False

    def get_player(self, sid):
        return next((p for p in self.players if p.sid == sid), None)

    def start_round(self):
        if len(self.players) < 2:
            return
        
        # Reset round state
        self.pot = 0
        self.current_turn_index = 0
        self.winner = None
        self.players_in_round = self.players.copy()
        self.has_raise = False
        self.raiser = None
        
        # Apuesta inicial automática de todos los jugadores
        for player in self.players:
            if player.chips >= self.table_bet:
                player.chips -= self.table_bet
                self.pot += self.table_bet
                player.is_folded = False
            else:
                # Si un jugador no tiene suficientes fichas, se retira automáticamente
                player.is_folded = True
                self.players_in_round.remove(player)
        
        # Verificar si quedan suficientes jugadores
        if len(self.players_in_round) < 2:
            self.phase = 'finished'
            emit_game_state(self.room_id)
            return
        
        # Create and shuffle deck
        self.deck = [Card(r, s) for r in Card.RANKS for s in Card.SUITS]
        random.shuffle(self.deck)
        
        # Deal one card to each player
        for player in self.players:
            if not player.is_folded:
                player.hand = [self.deck.pop()]
                player.has_acted = False
        
        self.phase = 'betting'  # Fase de apuesta simple
        self.current_turn_index = -1  # Empezar en -1 para que next_turn() vaya al índice 0
        self.next_turn()

    def next_turn(self):
        if all(p.has_acted or p.is_folded for p in self.players if not p.is_disconnected):
            self.resolve_round()
            return

        self.current_turn_index = (self.current_turn_index + 1) % len(self.players)
        player = self.players[self.current_turn_index]
        print(f"Next turn: current_turn_index={self.current_turn_index}, player={player.name}, sid={player.sid}")

        if player.is_folded or player.is_disconnected:
            self.next_turn()
            return

        if player.is_bot:
            action, amount = player.choose_action(self.table_bet, self.raise_amount)
            time.sleep(1) # Simulate bot thinking
            self.handle_player_action(player.sid, action, amount)
        else:
            print(f"Emitting game state for human player: {player.name}")
            emit_game_state(self.room_id)

    def handle_player_action(self, sid, action, amount=0):
        player = self.get_player(sid)
        if not player or player.sid != self.players[self.current_turn_index].sid:
            return

        if self.phase == 'betting':
            if not self.has_raise:  # Primera vuelta: raise o pass
                if action == 'raise':
                    if player.chips >= self.raise_amount:
                        player.chips -= self.raise_amount
                        self.pot += self.raise_amount
                        self.has_raise = True
                        self.raiser = player
                        # Reset has_acted para segunda vuelta
                        for p in self.players_in_round:
                            p.has_acted = False
                    else:
                        # No puede subir, pasa automáticamente
                        action = 'pass'
                elif action == 'pass':
                    # Simplemente pasa
                    pass
            else:  # Segunda vuelta: call o fold (solo para no-raiser)
                if player == self.raiser:
                    # El que subió ya actuó, saltar
                    player.has_acted = True
                    self.next_turn()
                    return
                elif action == 'call':
                    if player.chips >= self.raise_amount:
                        player.chips -= self.raise_amount
                        self.pot += self.raise_amount
                    else:
                        # No puede igualar, se retira
                        action = 'fold'
                elif action == 'fold':
                    player.is_folded = True
                    self.players_in_round.remove(player)

        player.has_acted = True
        
        # Verificar si todos han actuado
        if len(self.players_in_round) == 1:
            self.resolve_round()
        elif all(p.has_acted for p in self.players_in_round if not p.is_folded):
            if self.has_raise and not all(p.has_acted for p in self.players_in_round):
                # Continuar segunda vuelta
                self.next_turn()
            else:
                # Todos actuaron, resolver
                self.resolve_round()
        else:
            self.next_turn()

    def resolve_round(self):
        self.phase = 'revealing'
        active_players = [p for p in self.players_in_round if not p.is_folded]

        if len(active_players) == 1:
            # Solo queda un jugador, gana automáticamente
            self.winner = active_players[0]
        elif len(active_players) == 0:
            # Todos se retiraron, no hay ganador (caso raro)
            self.winner = None
        else:
            # Revelar cartas y determinar ganador por carta más alta
            active_players.sort(key=lambda p: p.evaluate_hand(), reverse=True)
            if len(active_players) > 1 and active_players[0].evaluate_hand() == active_players[1].evaluate_hand():
                # Empate - repetir ronda manteniendo el pozo
                self.winner = None
                socketio.emit('round_tie', {
                    'players': [p.to_dict() for p in self.players],
                    'pot': self.pot,
                    'final_pot': self.final_pot
                }, room=self.room_id)
                # Repetir ronda automáticamente después de 3 segundos
                threading.Timer(3.0, self.start_round).start()
                return
            else:
                self.winner = active_players[0]

        if self.winner:
            # Dividir el pozo: mitad al ganador, mitad al pozo final
            winner_share = self.pot // 2
            final_pot_share = self.pot - winner_share
            
            self.winner.chips += winner_share
            self.final_pot += final_pot_share
            
            # Actualizar rachas
            self.win_streaks[self.winner.sid] = self.win_streaks.get(self.winner.sid, 0) + 1
            for p_sid in self.win_streaks:
                if p_sid != self.winner.sid:
                    self.win_streaks[p_sid] = 0
            
            # Verificar si ganó el juego (3 rondas consecutivas)
            if self.win_streaks[self.winner.sid] >= 3:
                # Ganador del juego se lleva el pozo final
                self.winner.chips += self.final_pot
                self.phase = 'finished'
                socketio.emit('game_over', {
                    'winner_id': self.winner.sid, 
                    'room_id': self.room_id,
                    'final_pot': self.final_pot,
                    'total_winnings': winner_share + self.final_pot
                }, room=self.room_id)
                # Sincronizar fichas finales con la base de datos
                sync_all_players_chips(self.players)
            else:
                socketio.emit('round_over', {
                    'winner_id': self.winner.sid, 
                    'players': [p.to_dict() for p in self.players],
                    'winner_share': winner_share,
                    'final_pot': self.final_pot,
                    'win_streak': self.win_streaks[self.winner.sid]
                }, room=self.room_id)
                # Sincronizar fichas con la base de datos después de cada ronda
                sync_all_players_chips(self.players)
                # Iniciar automáticamente la siguiente ronda después de 4 segundos
                threading.Timer(4.0, self.start_round).start()

        emit_game_state(self.room_id)

    def get_state(self):
        players_data = []
        for p in self.players:
            p_data = p.to_dict()
            p_data['win_streak'] = self.win_streaks.get(p.sid, 0)
            p_data['in_round'] = p in self.players_in_round
            players_data.append(p_data)

        return {
            'room_id': self.room_id,
            'table_bet': self.table_bet,
            'players': players_data,
            'pot': self.pot,
            'final_pot': self.final_pot,
            'phase': self.phase,
            'has_raise': self.has_raise,
            'current_turn': self.players[self.current_turn_index].sid if self.current_turn_index > -1 and len(self.players) > self.current_turn_index else None,
            'winner': self.winner.sid if self.winner else None,
            'players_in_round': len(self.players_in_round)
        }

game_rooms = {}
player_queue = {}  # {table_bet: [{'sid': sid, 'username': username, 'timestamp': time}]}
queue_timers = {}  # {table_bet: timer_object}

def emit_game_state(room_id):
    if room_id in game_rooms:
        state = game_rooms[room_id].get_state()
        print(f"Emitting game state: phase={state['phase']}, current_turn={state['current_turn']}, has_raise={state['has_raise']}")
        socketio.emit('game_state', state, room=room_id)

def start_game_with_queue(table_bet):
    """Inicia un juego con los jugadores en cola para una mesa específica"""
    if table_bet not in player_queue or len(player_queue[table_bet]) < 2:
        return
    
    # Crear sala con ID único y table_bet específico
    room_id = f"auto_{random.randint(10000, 99999)}"
    game_rooms[room_id] = GameRoom(room_id, table_bet)
    
    # Tomar jugadores de la cola
    players_to_add = player_queue[table_bet][:4]  # Máximo 4 jugadores
    player_queue[table_bet] = player_queue[table_bet][4:]  # Remover jugadores usados
    
    # Agregar jugadores a la sala
    for player_data in players_to_add:
        join_room(room_id, sid=player_data['sid'])
        # Cargar fichas reales del usuario desde la base de datos
        user_chips = load_user_chips(player_data['username'])
        player = Player(player_data['sid'], player_data['username'], user_chips)
        game_rooms[room_id].add_player(player)
        
        # Notificar al jugador que fue emparejado
        socketio.emit('matched', {'room_id': room_id}, room=player_data['sid'])
    
    # Si quedan menos de 2 jugadores en cola, cancelar timer
    if table_bet in player_queue and len(player_queue[table_bet]) < 2:
        if table_bet in queue_timers:
            queue_timers[table_bet].cancel()
            del queue_timers[table_bet]

def add_bots_to_queue_game(table_bet):
    """Agrega bots automáticamente después del timeout"""
    if table_bet not in player_queue or len(player_queue[table_bet]) == 0:
        return
    
    # Crear sala con table_bet específico
    room_id = f"auto_{random.randint(10000, 99999)}"
    game_rooms[room_id] = GameRoom(room_id, table_bet)
    
    # Agregar jugadores humanos
    human_players = player_queue[table_bet][:4]
    player_queue[table_bet] = []
    
    for player_data in human_players:
        join_room(room_id, sid=player_data['sid'])
        # Cargar fichas reales del usuario desde la base de datos
        user_chips = load_user_chips(player_data['username'])
        player = Player(player_data['sid'], player_data['username'], user_chips)
        game_rooms[room_id].add_player(player)
        socketio.emit('matched', {'room_id': room_id}, room=player_data['sid'])
    
    # Agregar bots hasta completar 4 jugadores
    while len(game_rooms[room_id].players) < 4:
        bot_sid = f"bot_{random.randint(1000, 9999)}"
        bot = BotPlayer(bot_sid, f"Bot_{bot_sid[:4]}", 1000)
        game_rooms[room_id].add_player(bot)
    
    # Limpiar timer
    if table_bet in queue_timers:
        del queue_timers[table_bet]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/game/<room_id>')
def game(room_id):
    return render_template('game.html', room_id=room_id)

# API Routes for Wallet Integration
@app.route('/api/wallet/balance/<wallet_address>')
def get_wallet_balance(wallet_address):
    """Obtiene el balance de SOL de una wallet"""
    try:
        if helius_client:
            balance = helius_client.get_sol_balance(wallet_address)
            return jsonify({
                'sol_balance': balance,
                'wallet_address': wallet_address
            })
        else:
            return jsonify({'error': 'Helius client not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile/<wallet_address>')
def get_user_profile(wallet_address):
    """Obtiene o crea el perfil de usuario para una wallet"""
    try:
        db = SessionLocal()
        profile = db.query(UserProfile).filter_by(wallet_address=wallet_address).first()
        
        if not profile:
            # Crear nuevo perfil si no existe
            profile = UserProfile(
                wallet_address=wallet_address,
                username=f"User_{wallet_address[:8]}",
                chips=100,  # Fichas iniciales
                total_games=0,
                total_wins=0
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
        # Actualizar last_login
        profile.last_login = datetime.utcnow()
        db.commit()
        
        result = {
            'wallet_address': profile.wallet_address,
            'username': profile.username,
            'game_tokens': profile.chips,
            'total_games': profile.total_games,
            'total_wins': profile.total_wins,
            'created_at': profile.created_at.isoformat() if profile.created_at else None,
            'last_login': profile.last_login.isoformat() if profile.last_login else None
        }
        
        db.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['POST'])
def update_user_profile():
    """Actualiza el perfil de usuario"""
    try:
        data = request.get_json()
        wallet_address = data.get('wallet_address')
        username = data.get('username')
        chips = data.get('chips')  # Permitir actualizar fichas
        
        if not wallet_address:
            return jsonify({'error': 'wallet_address requerido'}), 400
            
        db = SessionLocal()
        profile = db.query(UserProfile).filter_by(wallet_address=wallet_address).first()
        
        if not profile:
            # Crear nuevo perfil si no existe
            profile = UserProfile(
                wallet_address=wallet_address,
                username=username or f"User_{wallet_address[:8]}",
                chips=100,  # Fichas iniciales
                total_games=0,
                total_wins=0
            )
            db.add(profile)
        else:
            # Actualizar username si se proporciona
            if username:
                profile.username = username
            # Actualizar fichas si se proporciona
            if chips is not None:
                profile.chips = chips
            profile.last_login = datetime.utcnow()
        
        db.commit()
        db.refresh(profile)
        
        result = {
            'wallet_address': profile.wallet_address,
            'username': profile.username,
            'game_tokens': profile.chips,
            'total_games': profile.total_games,
            'total_wins': profile.total_wins,
            'created_at': profile.created_at.isoformat() if profile.created_at else None,
            'last_login': profile.last_login.isoformat() if profile.last_login else None
        }
        
        db.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/wallet/transactions/<wallet_address>')
def get_wallet_transactions(wallet_address):
    """Obtiene las transacciones de una wallet"""
    try:
        limit = request.args.get('limit', 20, type=int)
        transaction_type = request.args.get('type', None)
        
        db = SessionLocal()
        query = db.query(UserTransaction).filter_by(wallet_address=wallet_address)
        
        # Filtrar por tipo si se especifica
        if transaction_type:
            if transaction_type == 'deposit_withdraw':
                query = query.filter(UserTransaction.transaction_type.in_(['deposit', 'withdraw']))
            elif transaction_type == 'games':
                query = query.filter(UserTransaction.transaction_type.in_(['bet', 'win']))
            else:
                query = query.filter_by(transaction_type=transaction_type)
        
        transactions = query.order_by(UserTransaction.created_at.desc()).limit(limit).all()
        
        result = {
            'transactions': [tx.to_dict() for tx in transactions],
            'total': len(transactions)
        }
        
        db.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= SISTEMA DE DEPÓSITOS =================

@app.route('/api/deposit/address/<wallet_address>')
def get_deposit_address(wallet_address):
    """Retorna la dirección custodial para depósitos"""
    try:
        # Validar que la wallet address sea válida
        if not wallet_address or len(wallet_address) < 32:
            return jsonify({'error': 'Dirección de wallet inválida'}), 400
            
        # Retornar la dirección custodial desde las variables de entorno
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        if not custodial_address or custodial_address == 'YOUR_CUSTODIAL_SOL_ADDRESS_HERE':
            return jsonify({'error': 'Dirección custodial no configurada'}), 500
            
        return jsonify({
            'deposit_address': custodial_address,
            'user_wallet': wallet_address,
            'conversion_rate': '1 SOL = 100,000 fichas',
            'minimum_deposit': '0.001 SOL (100 fichas)',
            'instructions': 'Envía SOL a esta dirección y las fichas se acreditarán automáticamente'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deposit/process', methods=['POST'])
def process_deposit():
    """Procesa un depósito detectado por webhook o manualmente"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['wallet_address', 'sol_amount', 'signature']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        wallet_address = data['wallet_address']
        sol_amount = float(data['sol_amount'])
        signature = data['signature']
        
        # Validar monto mínimo (0.001 SOL)
        if sol_amount < 0.001:
            return jsonify({'error': 'Monto mínimo de depósito: 0.001 SOL'}), 400
        
        # Calcular fichas (1 SOL = 100,000 fichas)
        tokens_per_sol = int(os.getenv('TOKENS_PER_SOL', 100000))
        chips_to_add = int(sol_amount * tokens_per_sol)
        
        db = SessionLocal()
        
        # Verificar que no se haya procesado esta transacción antes
        existing_tx = db.query(UserTransaction).filter_by(signature=signature).first()
        if existing_tx:
            db.close()
            return jsonify({'error': 'Transacción ya procesada'}), 400
        
        # Obtener o crear perfil de usuario
        profile = db.query(UserProfile).filter_by(wallet_address=wallet_address).first()
        if not profile:
            profile = UserProfile(
                wallet_address=wallet_address,
                username=f"User_{wallet_address[:8]}",
                chips=100  # Fichas iniciales
            )
            db.add(profile)
            db.flush()  # Para obtener el ID
        
        # Agregar fichas al perfil
        profile.chips += chips_to_add
        profile.last_login = datetime.utcnow()
        
        # Crear registro de transacción
        transaction = UserTransaction(
            wallet_address=wallet_address,
            transaction_type='deposit',
            amount=chips_to_add,
            signature=signature,
            status='success',
            description=f'Depósito de {sol_amount} SOL = {chips_to_add} fichas'
        )
        db.add(transaction)
        
        db.commit()
        
        result = {
            'success': True,
            'wallet_address': wallet_address,
            'sol_deposited': sol_amount,
            'chips_added': chips_to_add,
            'new_chip_balance': profile.chips,
            'transaction_signature': signature
        }
        
        db.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deposit/history/<wallet_address>')
def get_deposit_history(wallet_address):
    """Obtiene el historial de depósitos de un usuario"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        db = SessionLocal()
        deposits = db.query(UserTransaction).filter_by(
            wallet_address=wallet_address,
            transaction_type='deposit'
        ).order_by(UserTransaction.created_at.desc()).limit(limit).all()
        
        result = {
            'deposits': [tx.to_dict() for tx in deposits],
            'total': len(deposits)
        }
        
        db.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= FASE 4: WEBHOOKS AUTOMÁTICOS =================

@app.route('/api/webhook/helius', methods=['POST'])
def helius_webhook():
    """Endpoint para recibir webhooks automáticos de Helius"""
    try:
        # Obtener datos del webhook
        webhook_data = request.get_json()
        
        # Log del webhook recibido
        print(f"📨 Webhook recibido: {json.dumps(webhook_data, indent=2)}")
        
        # Validar estructura del webhook
        if not webhook_data or 'type' not in webhook_data:
            return jsonify({'error': 'Webhook inválido'}), 400
        
        # Procesar diferentes tipos de webhooks
        webhook_type = webhook_data.get('type')
        
        if webhook_type == 'enhanced':
            return process_enhanced_webhook(webhook_data)
        elif webhook_type == 'transaction':
            return process_transaction_webhook(webhook_data)
        else:
            print(f"⚠️ Tipo de webhook no soportado: {webhook_type}")
            return jsonify({'message': 'Webhook type not supported'}), 200
            
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return jsonify({'error': str(e)}), 500

def process_enhanced_webhook(webhook_data):
    """Procesa webhooks enhanced de Helius"""
    try:
        # Extraer información de la transacción
        transactions = webhook_data.get('transactions', [])
        
        processed_count = 0
        for tx_data in transactions:
            if process_webhook_transaction(tx_data):
                processed_count += 1
        
        return jsonify({
            'success': True,
            'processed_transactions': processed_count,
            'total_transactions': len(transactions)
        })
        
    except Exception as e:
        print(f"❌ Error procesando enhanced webhook: {e}")
        return jsonify({'error': str(e)}), 500

def process_transaction_webhook(webhook_data):
    """Procesa webhooks de transacciones individuales"""
    try:
        if process_webhook_transaction(webhook_data):
            return jsonify({'success': True, 'message': 'Transaction processed'})
        else:
            return jsonify({'success': False, 'message': 'Transaction not processed'})
            
    except Exception as e:
        print(f"❌ Error procesando transaction webhook: {e}")
        return jsonify({'error': str(e)}), 500

def process_webhook_transaction(tx_data):
    """Procesa una transacción individual del webhook"""
    try:
        # Extraer datos de la transacción
        signature = tx_data.get('signature')
        if not signature:
            print("⚠️ Transacción sin signature")
            return False
        
        # Verificar si es una transacción hacia nuestra dirección custodial
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        if not custodial_address:
            print("⚠️ CUSTODIAL_ADDRESS no configurada")
            return False
        
        # Buscar transferencias SOL hacia la dirección custodial
        native_transfers = tx_data.get('nativeTransfers', [])
        
        for transfer in native_transfers:
            to_address = transfer.get('toUserAccount')
            from_address = transfer.get('fromUserAccount')
            amount_lamports = transfer.get('amount', 0)
            
            # Verificar si es un depósito hacia nuestra dirección
            if to_address == custodial_address and amount_lamports > 0:
                # Convertir lamports a SOL
                sol_amount = amount_lamports / 1_000_000_000  # 1 SOL = 1B lamports
                
                # Procesar el depósito automáticamente
                return auto_process_deposit(from_address, sol_amount, signature)
        
        return False
        
    except Exception as e:
        print(f"❌ Error procesando transacción del webhook: {e}")
        return False

def auto_process_deposit(wallet_address, sol_amount, signature):
    """Procesa automáticamente un depósito detectado por webhook"""
    try:
        # Validar monto mínimo
        if sol_amount < 0.001:
            print(f"⚠️ Depósito muy pequeño: {sol_amount} SOL")
            return False
        
        # Calcular fichas
        tokens_per_sol = int(os.getenv('TOKENS_PER_SOL', 100000))
        chips_to_add = int(sol_amount * tokens_per_sol)
        
        db = SessionLocal()
        
        try:
            # Verificar que no se haya procesado antes
            existing_tx = db.query(UserTransaction).filter_by(signature=signature).first()
            if existing_tx:
                print(f"⚠️ Transacción ya procesada: {signature}")
                return False
            
            # Obtener o crear perfil de usuario
            profile = db.query(UserProfile).filter_by(wallet_address=wallet_address).first()
            if not profile:
                profile = UserProfile(
                    wallet_address=wallet_address,
                    username=f"User_{wallet_address[:8]}",
                    chips=100  # Fichas iniciales
                )
                db.add(profile)
                db.flush()
            
            # Agregar fichas
            profile.chips += chips_to_add
            profile.last_login = datetime.utcnow()
            
            # Crear registro de transacción
            transaction = UserTransaction(
                wallet_address=wallet_address,
                transaction_type='deposit',
                amount=chips_to_add,
                signature=signature,
                status='success',
                description=f'Depósito automático: {sol_amount} SOL = {chips_to_add} fichas'
            )
            db.add(transaction)
            
            db.commit()
            
            print(f"✅ Depósito automático procesado: {wallet_address} +{chips_to_add} fichas")
            
            # Enviar notificación en tiempo real si el usuario está conectado
            send_deposit_notification(wallet_address, sol_amount, chips_to_add)
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error procesando depósito automático: {e}")
        return False

def send_deposit_notification(wallet_address, sol_amount, chips_added):
    """Envía notificación en tiempo real al usuario sobre el depósito"""
    try:
        # Buscar si el usuario está conectado
        notification_data = {
            'type': 'deposit_confirmed',
            'wallet_address': wallet_address,
            'sol_amount': sol_amount,
            'chips_added': chips_added,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'¡Depósito confirmado! +{chips_added} fichas'
        }
        
        # Emitir notificación a todos los clientes (se puede optimizar para enviar solo al usuario específico)
        socketio.emit('deposit_notification', notification_data, broadcast=True)
        
        print(f"📢 Notificación enviada: {wallet_address} +{chips_added} fichas")
        
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")

@app.route('/api/webhook/setup', methods=['POST'])
def setup_webhook_endpoint():
    """Configura un webhook de Helius para monitoreo automático"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return jsonify({'error': 'webhook_url requerida'}), 400
        
        # Obtener dirección custodial
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        if not custodial_address:
            return jsonify({'error': 'CUSTODIAL_ADDRESS no configurada'}), 500
        
        # Configurar webhook usando Helius
        helius = get_helius_client()
        if not helius:
            return jsonify({'error': 'Cliente Helius no disponible'}), 500
        
        # Intentar configurar el webhook
        success = helius.setup_webhook(webhook_url, [custodial_address])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Webhook configurado correctamente',
                'webhook_url': webhook_url,
                'monitored_address': custodial_address
            })
        else:
            return jsonify({'error': 'Error configurando webhook'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook/status')
def webhook_status():
    """Obtiene el estado de los webhooks configurados"""
    try:
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        webhook_url = os.getenv('WEBHOOK_URL')
        
        return jsonify({
            'webhook_configured': bool(webhook_url),
            'webhook_url': webhook_url,
            'custodial_address': custodial_address,
            'helius_available': helius_client is not None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/webhook-admin')
def webhook_admin():
    """Interfaz de administración de webhooks"""
    return render_template('webhook_admin.html')

@app.route('/api/webhook/list')
def list_webhooks_api():
    """API para listar webhooks configurados"""
    try:
        helius = get_helius_client()
        if not helius:
            return jsonify({'error': 'Cliente Helius no disponible'}), 500
        
        webhooks = helius.list_webhooks()
        return jsonify({
            'success': True,
            'webhooks': webhooks,
            'count': len(webhooks)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook/delete/<webhook_id>', methods=['DELETE'])
def delete_webhook_api(webhook_id):
    """API para eliminar un webhook específico"""
    try:
        helius = get_helius_client()
        if not helius:
            return jsonify({'error': 'Cliente Helius no disponible'}), 500
        
        success = helius.delete_webhook(webhook_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Webhook {webhook_id} eliminado correctamente'
            })
        else:
            return jsonify({'error': 'Error eliminando webhook'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/webhook/metrics')
def webhook_metrics():
    """Obtiene métricas del sistema de webhooks"""
    try:
        db = SessionLocal()
        
        # Contar depósitos de hoy
        today = datetime.utcnow().date()
        deposits_today = db.query(UserTransaction).filter(
            UserTransaction.transaction_type == 'deposit',
            UserTransaction.created_at >= today
        ).count()
        
        # Total de transacciones procesadas
        total_processed = db.query(UserTransaction).filter(
            UserTransaction.transaction_type == 'deposit'
        ).count()
        
        # Última actividad
        last_transaction = db.query(UserTransaction).filter(
            UserTransaction.transaction_type == 'deposit'
        ).order_by(UserTransaction.created_at.desc()).first()
        
        last_activity = None
        if last_transaction:
            last_activity = last_transaction.created_at.isoformat()
        
        db.close()
        
        return jsonify({
            'deposits_today': deposits_today,
            'total_processed': total_processed,
            'last_activity': last_activity,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('join_room')
def on_join_room(data):
    room_id = data['room_id']
    username = data.get('username', f"Player_{request.sid[:4]}")
    join_room(room_id)
    if room_id not in game_rooms:
        game_rooms[room_id] = GameRoom(room_id)
    
    # Cargar fichas reales del usuario desde la base de datos
    user_chips = load_user_chips(username)
    player = Player(request.sid, username, user_chips)
    game_rooms[room_id].add_player(player)
    emit_game_state(room_id)

@socketio.on('start_game')
def on_start_game(data):
    room_id = data['room_id']
    if room_id in game_rooms:
        game_rooms[room_id].start_round()
        emit_game_state(room_id)

@socketio.on('add_bot')
def on_add_bot(data):
    room_id = data['room_id']
    if room_id in game_rooms:
        bot_sid = f"bot_{random.randint(1000, 9999)}"
        bot = BotPlayer(bot_sid, f"Bot_{bot_sid[:4]}", 1000)
        game_rooms[room_id].add_player(bot)
        emit_game_state(room_id)

@socketio.on('player_action')
def on_player_action(data):
    room_id = data['room_id']
    action = data['action']
    amount = data.get('amount', 0)
    if room_id in game_rooms:
        game_rooms[room_id].handle_player_action(request.sid, action, amount)

@socketio.on('find_game')
def handle_find_game(data):
    """Maneja la búsqueda de juego automático"""
    username = data.get('username', f'Player_{request.sid[:6]}')
    table_bet = data.get('table_bet', 10)  # Apuesta por defecto
    
    # Inicializar cola si no existe
    if table_bet not in player_queue:
        player_queue[table_bet] = []
    
    # Verificar si el jugador ya está en cola
    player_in_queue = any(p['sid'] == request.sid for p in player_queue[table_bet])
    if player_in_queue:
        socketio.emit('queue_error', {'message': 'Ya estás en la cola de búsqueda'}, room=request.sid)
        return
    
    # Agregar jugador a la cola
    player_data = {
        'sid': request.sid,
        'username': username,
        'timestamp': time.time()
    }
    player_queue[table_bet].append(player_data)
    
    # Emitir estado de cola
    queue_count = len(player_queue[table_bet])
    socketio.emit('waiting_for_player', {
        'queue_count': queue_count,
        'table_bet': table_bet
    }, room=request.sid)
    
    # Si hay suficientes jugadores, iniciar juego inmediatamente
    if queue_count >= 2:
        start_game_with_queue(table_bet)
    else:
        # Configurar timer para agregar bots después de 30 segundos
        if table_bet not in queue_timers:
            timer = threading.Timer(30.0, add_bots_to_queue_game, [table_bet])
            queue_timers[table_bet] = timer
            timer.start()

@socketio.on('cancel_find')
def handle_cancel_find():
    """Maneja la cancelación de búsqueda de juego"""
    # Buscar y remover jugador de todas las colas
    for table_bet, queue in player_queue.items():
        player_queue[table_bet] = [p for p in queue if p['sid'] != request.sid]
        
        # Si la cola queda vacía, cancelar timer
        if len(player_queue[table_bet]) == 0 and table_bet in queue_timers:
            queue_timers[table_bet].cancel()
            del queue_timers[table_bet]
    
    # Notificar al cliente que la búsqueda fue cancelada
    socketio.emit('match_canceled', {}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client {request.sid} disconnected')
    
    # Remover jugador de las colas de búsqueda
    for table_bet, queue in player_queue.items():
        player_queue[table_bet] = [p for p in queue if p['sid'] != request.sid]
        
        # Si la cola queda vacía, cancelar timer
        if len(player_queue[table_bet]) == 0 and table_bet in queue_timers:
            queue_timers[table_bet].cancel()
            del queue_timers[table_bet]
    
    # Limpiar jugador de todas las salas
    for room_id, room in game_rooms.items():
        player = room.get_player(request.sid)
        if player:
            player.is_disconnected = True
            # Optional: remove player if game has not started
            if room.phase == 'waiting':
                room.players.remove(player)
            emit_game_state(room_id)
            break

# ============================================================
# ENDPOINTS DE RETIROS
# ============================================================

@app.route('/api/withdraw/request', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=600)  # Máximo 5 retiros cada 10 minutos
@audit_log(action='withdrawal_request')
def request_withdrawal():
    """Procesa solicitud de retiro de fichas a SOL"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        # Validar datos requeridos
        required_fields = ['wallet_address', 'chip_amount', 'destination_address']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        wallet_address = data['wallet_address']
        destination_address = data['destination_address']
        
        try:
            chip_amount = int(data['chip_amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'chip_amount debe ser un número entero'}), 400
        
        # Validar dirección de destino (básica validación de longitud)
        if len(destination_address) < 32 or len(destination_address) > 44:
            return jsonify({'error': 'Dirección de destino inválida'}), 400
        
        # Validar monto mínimo (1000 fichas = 0.01 SOL)
        if chip_amount < 1000:
            return jsonify({'error': 'Monto mínimo de retiro: 1000 fichas (0.01 SOL)'}), 400
        
        db = SessionLocal()
        
        # Obtener perfil de usuario
        profile = db.query(UserProfile).filter_by(wallet_address=wallet_address).first()
        if not profile:
            db.close()
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Verificar saldo suficiente
        if profile.chips < chip_amount:
            db.close()
            return jsonify({'error': f'Saldo insuficiente. Disponible: {profile.chips} fichas'}), 400
        
        # Calcular SOL a enviar (1 SOL = 100,000 fichas)
        tokens_per_sol = int(os.getenv('TOKENS_PER_SOL', 100000))
        sol_amount = chip_amount / tokens_per_sol
        
        # Calcular comisión del 5%
        withdrawal_fee_percent = float(os.getenv('WITHDRAWAL_FEE_PERCENT', 5.0))
        fee_amount = sol_amount * (withdrawal_fee_percent / 100)
        net_sol_amount = sol_amount - fee_amount
        
        # Validar que el monto neto sea mayor a 0
        if net_sol_amount <= 0:
            db.close()
            return jsonify({'error': 'Monto de retiro muy pequeño después de comisiones'}), 400
        
        # Descontar fichas del perfil
        profile.chips -= chip_amount
        
        # Crear registro de transacción
        withdrawal_tx = UserTransaction(
            wallet_address=wallet_address,
            transaction_type='withdraw',
            amount=chip_amount,  # Usar el campo 'amount' existente para las fichas
            signature=f'withdraw_{int(time.time())}_{wallet_address[:8]}',
            status='pending',
            description=f'Retiro de {chip_amount} fichas = {net_sol_amount:.4f} SOL (fee: {fee_amount:.4f} SOL)'
        )
        db.add(withdrawal_tx)
        
        # TODO: Implementar envío real de SOL usando Helius
        # Por ahora simulamos el envío exitoso
        withdrawal_tx.status = 'completed'
        
        # Guardar datos antes de hacer commit
        new_chip_balance = profile.chips
        transaction_signature = withdrawal_tx.signature
        
        # Hacer commit y cerrar sesión
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Retiro procesado exitosamente',
            'chip_amount': chip_amount,
            'sol_amount': sol_amount,
            'fee_amount': fee_amount,
            'net_amount': net_sol_amount,
            'new_chip_balance': new_chip_balance,
            'transaction_id': transaction_signature
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/withdraw/history/<wallet_address>')
def get_withdrawal_history(wallet_address):
    """Retorna el historial de retiros de un usuario"""
    try:
        if not wallet_address:
            return jsonify({'error': 'Dirección de wallet requerida'}), 400
            
        db = SessionLocal()
        
        # Obtener historial de retiros
        withdrawals = db.query(UserTransaction).filter_by(
            wallet_address=wallet_address,
            transaction_type='withdraw'
        ).order_by(UserTransaction.created_at.desc()).limit(50).all()
        
        withdrawal_list = []
        for tx in withdrawals:
            withdrawal_list.append({
                'transaction_id': tx.signature,
                'amount': tx.amount,  # Campo que existe en el modelo
                'status': tx.status,
                'created_at': tx.created_at.isoformat(),
                'description': tx.description or '',  # Incluir descripción que contiene detalles
                'type': 'withdraw'
            })
        
        db.close()
        
        return jsonify({
            'withdrawals': withdrawal_list,
            'total_withdrawals': len(withdrawal_list)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Endpoints de seguridad avanzada
@app.route('/api/security/status/<wallet_address>')
@rate_limit(max_requests=10, window_seconds=60)
def get_wallet_security_status(wallet_address):
    # Obtener estado de seguridad de una wallet
    try:
        status = get_security_status(wallet_address)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/limits/<wallet_address>')
@rate_limit(max_requests=10, window_seconds=60)
def get_daily_limits(wallet_address):
    # Obtener límites diarios de una wallet
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        limits = security_manager.get_daily_limits(wallet_address)
        return jsonify(limits)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/audit/<wallet_address>')
@rate_limit(max_requests=5, window_seconds=60)
def get_audit_logs(wallet_address):
    # Obtener logs de auditoría de una wallet
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        logs = security_manager.get_audit_logs(wallet_address, limit=50)
        return jsonify({'audit_logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/suspicious')
@rate_limit(max_requests=3, window_seconds=60)
def get_suspicious_activities():
    # Obtener actividades sospechosas (solo admin)
    try:
        if not security_manager:
            return jsonify({'error': 'Sistema de seguridad no disponible'}), 503
            
        activities = security_manager.get_suspicious_activities(limit=100)
        return jsonify({'suspicious_activities': activities})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= ENDPOINTS DE ADMINISTRACIÓN =================

@app.route('/api/users')
def get_all_users():
    """Obtener lista de todos los usuarios registrados"""
    try:
        db_session = SessionLocal()
        users = db_session.query(UserProfile).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'wallet_address': user.wallet_address,
                'balance': user.chips,
                'total_games': user.total_games,
                'total_wins': user.total_wins,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        db_session.close()
        return jsonify(users_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    socketio.run(app, debug=True)
