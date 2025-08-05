import os
import json
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from decimal import Decimal
import logging
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.pubkey import Pubkey as PublicKey
from solders.system_program import transfer, TransferParams
from solana.rpc.types import TokenAccountOpts
import base58
# from solders.transaction import Transaction
# from solders.pubkey import Pubkey as PublicKey
# from solana.system_program import transfer, TransferParams
# import base58

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WalletBalance:
    """Estructura para almacenar balances de wallet"""
    sol_balance: float
    wallet_address: str

@dataclass
class Transaction:
    """Estructura para transacciones"""
    signature: str
    transaction_type: str
    amount: float
    timestamp: int
    status: str
    from_address: str
    to_address: str

class HeliusIntegration:
    """Clase principal para manejar la integración con Helius y Solana"""
    
    def __init__(self, api_key: str, network: str = "devnet"):
        if not api_key:
            raise ValueError("Helius API key is required.")
        self.api_key = api_key
        self.network = network
        self.base_url = f"https://api.helius.xyz/v0"
        self.rpc_url = f"https://rpc.helius.xyz/?api-key={self.api_key}"
        

        
        # Headers para las requests
        # Comentamos temporalmente el Client para evitar el error del proxy
        # self.client = Client(self.rpc_url)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        logger.info(f"HeliusIntegration inicializada para {network} (modo desarrollo)")
    
    def send_sol(self, destination: str, lamports: int) -> str:
        """Envía SOL desde la cuenta custodial al destino y devuelve la firma de la transacción"""
        # Temporalmente deshabilitado para evitar problemas con Client
        logger.warning("send_sol temporalmente deshabilitado")
        return "mock_transaction_signature"
        # try:
        #     # Configurar la transacción real
        #     custodial_wallet = Keypair.from_seed(os.getenv('CUSTODIAL_WALLET_SEED'))
        #     recent_blockhash = self.client.get_latest_blockhash().value.blockhash
        #     
        #     # Crear instrucción de transferencia
        #     transfer_ix = transfer(TransferParams(
        #         from_pubkey=custodial_wallet.pubkey(),
        #         to_pubkey=PublicKey.from_string(destination),
        #         lamports=lamports
        #     ))
        #     
        #     # Construir y firmar transacción
        #     txn = Transaction().add(transfer_ix)
        #     txn.recent_blockhash = recent_blockhash
        #     txn.sign(custodial_wallet)
        #     
        #     # Enviar transacción
        #     txn_sig = self.client.send_transaction(txn).value
        #     logger.info(f"Transacción enviada: {txn_sig}")
        #     return str(txn_sig)
        # except Exception as e:
        #     logger.error(f"Error enviando SOL: {e}")
        #     raise
    
    def get_sol_balance(self, wallet_address: str) -> float:
        """Obtiene el balance real de SOL de una wallet"""
        try:
            # Usar requests HTTP en lugar del Client para evitar problemas
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [wallet_address]
            }
            
            response = requests.post(self.rpc_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('result') or not data['result'].get('value'):
                return 0.0
            return data['result']['value']['lamports'] / 1_000_000_000
        except Exception as e:
            logger.error(f"Error obteniendo balance SOL para {wallet_address}: {e}")
            return 0.0
    

    
    def get_wallet_balance(self, wallet_address: str) -> WalletBalance:
        """Obtiene el balance completo de una wallet"""
        sol_balance = self.get_sol_balance(wallet_address)
        
        return WalletBalance(
            sol_balance=sol_balance,
            wallet_address=wallet_address
        )
    
    def get_transaction_history(self, wallet_address: str, limit: int = 10) -> List[Transaction]:
        """Obtiene el historial de transacciones de una wallet usando Helius API"""
        try:
            # Usar la API de Helius para obtener transacciones
            url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
            params = {
                "api-key": self.api_key,
                "limit": limit
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            transactions_data = response.json()
            transactions = []
            
            for tx_data in transactions_data:
                # Procesar cada transacción
                tx = Transaction(
                    signature=tx_data.get("signature", ""),
                    transaction_type=self._determine_transaction_type(tx_data),
                    amount=self._extract_amount(tx_data, wallet_address),
                    timestamp=tx_data.get("timestamp", 0),
                    status="success" if tx_data.get("err") is None else "failed",
                    from_address=self._extract_from_address(tx_data),
                    to_address=self._extract_to_address(tx_data)
                )
                transactions.append(tx)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de transacciones para {wallet_address}: {e}")
            return []
    
    def _determine_transaction_type(self, tx_data: Dict) -> str:
        """Determina el tipo de transacción basado en los datos"""
        # Lógica simplificada para determinar el tipo
        if "tokenTransfers" in tx_data and tx_data["tokenTransfers"]:
            return "Token Transfer"
        elif "nativeTransfers" in tx_data and tx_data["nativeTransfers"]:
            return "SOL Transfer"
        else:
            return "Other"
    
    def _extract_amount(self, tx_data: Dict, wallet_address: str) -> float:
        """Extrae la cantidad de la transacción"""
        try:
            # Buscar en transferencias nativas (SOL)
            if "nativeTransfers" in tx_data:
                for transfer in tx_data["nativeTransfers"]:
                    if transfer["fromUserAccount"] == wallet_address:
                        return -float(transfer["amount"]) / 1_000_000_000  # Negativo para salidas
                    elif transfer["toUserAccount"] == wallet_address:
                        return float(transfer["amount"]) / 1_000_000_000   # Positivo para entradas
            
            # Buscar en transferencias de tokens
            if "tokenTransfers" in tx_data:
                for transfer in tx_data["tokenTransfers"]:
                    if transfer["fromUserAccount"] == wallet_address:
                        return -float(transfer["tokenAmount"])  # Negativo para salidas
                    elif transfer["toUserAccount"] == wallet_address:
                        return float(transfer["tokenAmount"])   # Positivo para entradas
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error extrayendo cantidad de transacción: {e}")
            return 0.0
    
    def _extract_from_address(self, tx_data: Dict) -> str:
        """Extrae la dirección de origen de la transacción"""
        try:
            if "nativeTransfers" in tx_data and tx_data["nativeTransfers"]:
                return tx_data["nativeTransfers"][0].get("fromUserAccount", "")
            elif "tokenTransfers" in tx_data and tx_data["tokenTransfers"]:
                return tx_data["tokenTransfers"][0].get("fromUserAccount", "")
            return ""
        except:
            return ""
    
    def _extract_to_address(self, tx_data: Dict) -> str:
        """Extrae la dirección de destino de la transacción"""
        try:
            if "nativeTransfers" in tx_data and tx_data["nativeTransfers"]:
                return tx_data["nativeTransfers"][0].get("toUserAccount", "")
            elif "tokenTransfers" in tx_data and tx_data["tokenTransfers"]:
                return tx_data["tokenTransfers"][0].get("toUserAccount", "")
            return ""
        except:
            return ""
    
    def validate_wallet_address(self, wallet_address: str) -> bool:
        """Valida si una dirección de wallet es válida"""
        try:
            # Una dirección de Solana válida tiene 32-44 caracteres
            if len(wallet_address) < 32 or len(wallet_address) > 44:
                return False
            
            # Intentar obtener información de la cuenta
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [wallet_address]
            }
            
            response = requests.post(self.rpc_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            # Si no hay error en la respuesta, la dirección es válida
            return "error" not in data
            
        except Exception as e:
            logger.error(f"Error validando dirección de wallet {wallet_address}: {e}")
            return False
    

    
    def setup_webhook(self, webhook_url: str, wallet_addresses: List[str]) -> bool:
        """Configura un webhook para monitorear wallets"""
        try:
            # URL de la API de Helius para webhooks
            helius_webhook_url = f"https://api.helius.xyz/v0/webhooks?api-key={self.api_key}"
            
            # Configuración del webhook
            webhook_config = {
                "webhookURL": webhook_url,
                "transactionTypes": ["Any"],
                "accountAddresses": wallet_addresses,
                "webhookType": "enhanced",
                "authHeader": ""
            }
            
            logger.info(f"Configurando webhook en Helius...")
            logger.info(f"URL: {webhook_url}")
            logger.info(f"Direcciones: {wallet_addresses}")
            
            # Realizar petición a Helius
            response = requests.post(
                helius_webhook_url,
                json=webhook_config,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                webhook_data = response.json()
                webhook_id = webhook_data.get('webhookID')
                logger.info(f"Webhook configurado correctamente. ID: {webhook_id}")
                return True
            else:
                logger.error(f"Error configurando webhook: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error configurando webhook: {e}")
            return False
    
    def list_webhooks(self) -> List[Dict]:
        """Lista todos los webhooks configurados en Helius"""
        try:
            # URL para listar webhooks
            helius_list_url = f"https://api.helius.xyz/v0/webhooks?api-key={self.api_key}"
            
            response = requests.get(helius_list_url)
            
            if response.status_code == 200:
                webhooks = response.json()
                logger.info(f"Webhooks encontrados: {len(webhooks)}")
                return webhooks
            else:
                logger.error(f"Error listando webhooks: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error en list_webhooks: {e}")
            return []
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Elimina un webhook específico"""
        try:
            # URL para eliminar webhook
            delete_url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={self.api_key}"
            
            response = requests.delete(delete_url)
            
            if response.status_code == 200:
                logger.info(f"Webhook {webhook_id} eliminado correctamente")
                return True
            else:
                logger.error(f"Error eliminando webhook: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error en delete_webhook: {e}")
            return False

# Instancia global (se inicializará con la API key real)
helius_client: Optional[HeliusIntegration] = None

def initialize_helius(api_key: str, network: str = "devnet"):
    """Inicializa el cliente de Helius"""
    global helius_client
    helius_client = HeliusIntegration(api_key, network)
    return helius_client

def get_helius_client() -> Optional[HeliusIntegration]:
    """Obtiene el cliente de Helius inicializado"""
    return helius_client

# Funciones de utilidad para el juego
def get_wallet_info_for_game(wallet_address: str) -> Dict:
    """Obtiene información de wallet formateada para el juego"""
    if not helius_client:
        return {"error": "Helius no inicializado"}
    
    try:
        balance = helius_client.get_wallet_balance(wallet_address)
        transactions = helius_client.get_transaction_history(wallet_address, 5)
        
        return {
            "wallet_address": wallet_address,
            "sol_balance": balance.sol_balance,
            "recent_transactions": [
                {
                    "signature": tx.signature[:8] + "...",
                    "type": tx.transaction_type,
                    "amount": tx.amount,
                    "timestamp": tx.timestamp
                }
                for tx in transactions
            ]
        }
    except Exception as e:
        logger.error(f"Error obteniendo información de wallet: {e}")
        return {"error": str(e)}

def get_wallet_info():
    """Obtiene información de la wallet del juego"""
    try:
        helius = get_helius_client()
        if not helius:
            return None
            
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        if not custodial_address or custodial_address == 'YOUR_CUSTODIAL_SOL_ADDRESS_HERE':
            return None
            
        balance = helius.get_sol_balance(custodial_address)
        return {
            'address': custodial_address,
            'balance': balance,
            'network': os.getenv('HELIUS_NETWORK', 'devnet')
        }
    except Exception as e:
        logger.error(f"Error obteniendo información de wallet: {e}")
        return None

# ================= SISTEMA DE MONITOREO DE DEPÓSITOS =================

def monitor_deposits():
    """Monitorea depósitos entrantes a la dirección custodial"""
    try:
        helius = get_helius_client()
        if not helius:
            logger.error("Error: No se pudo conectar con Helius")
            return []
            
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        if not custodial_address or custodial_address == 'YOUR_CUSTODIAL_SOL_ADDRESS_HERE':
            logger.error("Error: Dirección custodial no configurada")
            return []
        
        # Obtener transacciones recientes (últimas 10)
        transactions = helius.get_transaction_history(custodial_address, limit=10)
        
        deposits = []
        for tx in transactions:
            # Verificar si es una transacción entrante (depósito)
            if tx.amount > 0 and tx.to_address == custodial_address:
                deposit_info = {
                    'signature': tx.signature,
                    'sender_address': tx.from_address,
                    'custodial_address': tx.to_address,
                    'sol_amount': tx.amount,
                    'timestamp': tx.timestamp,
                    'transaction_type': tx.transaction_type
                }
                deposits.append(deposit_info)
        
        return deposits
        
    except Exception as e:
        logger.error(f"Error monitoreando depósitos: {e}")
        return []

def check_new_deposits(last_checked_signature=None):
    """Verifica nuevos depósitos desde la última verificación"""
    try:
        deposits = monitor_deposits()
        
        if last_checked_signature:
            # Filtrar solo depósitos nuevos
            new_deposits = []
            for deposit in deposits:
                if deposit['signature'] == last_checked_signature:
                    break
                new_deposits.append(deposit)
            return new_deposits
        
        return deposits
        
    except Exception as e:
        logger.error(f"Error verificando nuevos depósitos: {e}")
        return []

# ================= FUNCIONES INDEPENDIENTES PARA WEBHOOKS =================

def setup_webhook(webhook_url, addresses):
    """
    Configura un webhook de Helius para monitorear transacciones
    
    Args:
        webhook_url (str): URL del endpoint webhook
        addresses (list): Lista de direcciones a monitorear
    
    Returns:
        bool: True si se configuró correctamente
    """
    try:
        api_key = os.getenv('HELIUS_API_KEY')
        if not api_key:
            print("❌ HELIUS_API_KEY no configurada")
            return False
        
        # URL de la API de Helius para webhooks
        helius_webhook_url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"
        
        # Configuración del webhook
        webhook_config = {
            "webhookURL": webhook_url,
            "transactionTypes": ["Any"],
            "accountAddresses": addresses,
            "webhookType": "enhanced",
            "authHeader": ""
        }
        
        print(f"🔗 Configurando webhook en Helius...")
        print(f"📍 URL: {webhook_url}")
        print(f"📍 Direcciones: {addresses}")
        
        # Realizar petición a Helius
        response = requests.post(
            helius_webhook_url,
            json=webhook_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            webhook_data = response.json()
            webhook_id = webhook_data.get('webhookID')
            print(f"✅ Webhook configurado correctamente. ID: {webhook_id}")
            
            # Guardar el ID del webhook en variables de entorno (opcional)
            # Esto permitiría gestionar el webhook posteriormente
            return True
        else:
            print(f"❌ Error configurando webhook: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en setup_webhook: {e}")
        return False

def list_webhooks():
    """
    Lista todos los webhooks configurados en Helius
    
    Returns:
        list: Lista de webhooks configurados
    """
    try:
        api_key = os.getenv('HELIUS_API_KEY')
        if not api_key:
            print("❌ HELIUS_API_KEY no configurada")
            return []
        
        # URL para listar webhooks
        helius_list_url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"
        
        response = requests.get(helius_list_url)
        
        if response.status_code == 200:
            webhooks = response.json()
            print(f"📋 Webhooks encontrados: {len(webhooks)}")
            return webhooks
        else:
            print(f"❌ Error listando webhooks: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error en list_webhooks: {e}")
        return []

def delete_webhook(webhook_id):
    """
    Elimina un webhook específico
    
    Args:
        webhook_id (str): ID del webhook a eliminar
    
    Returns:
        bool: True si se eliminó correctamente
    """
    try:
        api_key = os.getenv('HELIUS_API_KEY')
        if not api_key:
            print("❌ HELIUS_API_KEY no configurada")
            return False
        
        # URL para eliminar webhook
        delete_url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={api_key}"
        
        response = requests.delete(delete_url)
        
        if response.status_code == 200:
            print(f"✅ Webhook {webhook_id} eliminado correctamente")
            return True
        else:
            print(f"❌ Error eliminando webhook: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en delete_webhook: {e}")
        return False