#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear transacciones de prueba y verificar el sistema de APIs
"""

import requests
import json
from datetime import datetime
import sqlite3

def create_test_transactions():
    """Crea transacciones de prueba en la base de datos"""
    
    # Conectar a la base de datos
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    
    # Wallet de prueba
    test_wallet = "CR2Z14kNMeaLpfD8HmEL5Z6Nb1vYJXzxWBEQeoBGESLa"
    
    # Crear transacciones de prueba
    test_transactions = [
        {
            'wallet_address': test_wallet,
            'transaction_type': 'deposit',
            'amount': 50000.0,
            'signature': 'dep123abc456def789',
            'status': 'success',
            'description': 'Depósito de 0.5 SOL'
        },
        {
            'wallet_address': test_wallet,
            'transaction_type': 'bet',
            'amount': -100.0,
            'signature': 'bet456def789ghi012',
            'status': 'success',
            'description': 'Apuesta en mesa 100 fichas'
        },
        {
            'wallet_address': test_wallet,
            'transaction_type': 'win',
            'amount': 200.0,
            'signature': 'win789ghi012jkl345',
            'status': 'success',
            'description': 'Victoria en partida - 200 fichas'
        },
        {
            'wallet_address': test_wallet,
            'transaction_type': 'withdraw',
            'amount': -10000.0,
            'signature': 'wit012jkl345mno678',
            'status': 'success',
            'description': 'Retiro de 0.1 SOL'
        }
    ]
    
    # Insertar transacciones
    for tx in test_transactions:
        cursor.execute("""
            INSERT INTO user_transactions 
            (wallet_address, transaction_type, amount, signature, status, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tx['wallet_address'],
            tx['transaction_type'],
            tx['amount'],
            tx['signature'],
            tx['status'],
            tx['description'],
            datetime.utcnow().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Creadas {len(test_transactions)} transacciones de prueba para {test_wallet[:8]}...")

def test_api_endpoints():
    """Prueba los endpoints de la API"""
    base_url = 'http://localhost:5000'
    test_wallet = "CR2Z14kNMeaLpfD8HmEL5Z6Nb1vYJXzxWBEQeoBGESLa"
    
    print("\n🧪 Probando endpoints de la API...")
    
    # Probar GET perfil de usuario
    print("\n1. Probando GET /api/user/profile/<wallet>")
    try:
        response = requests.get(f'{base_url}/api/user/profile/{test_wallet}')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Perfil obtenido: {data['username']} - {data['game_tokens']} fichas")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar POST perfil de usuario
    print("\n2. Probando POST /api/user/profile")
    try:
        payload = {
            'wallet_address': test_wallet,
            'username': 'TestUser_Updated'
        }
        response = requests.post(f'{base_url}/api/user/profile', 
                               json=payload,
                               headers={'Content-Type': 'application/json'})
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Perfil actualizado: {data['username']}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar transacciones de depósitos/retiros
    print("\n3. Probando GET /api/wallet/transactions/<wallet>?type=deposit_withdraw")
    try:
        response = requests.get(f'{base_url}/api/wallet/transactions/{test_wallet}?limit=20&type=deposit_withdraw')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Transacciones depósito/retiro: {data['total']} encontradas")
            for tx in data['transactions'][:2]:  # Mostrar solo las primeras 2
                print(f"      - {tx['transaction_type']}: {tx['amount']} ({tx['description']})")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Probar transacciones de juegos
    print("\n4. Probando GET /api/wallet/transactions/<wallet>?type=games")
    try:
        response = requests.get(f'{base_url}/api/wallet/transactions/{test_wallet}?limit=20&type=games')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Transacciones de juegos: {data['total']} encontradas")
            for tx in data['transactions'][:2]:  # Mostrar solo las primeras 2
                print(f"      - {tx['transaction_type']}: {tx['amount']} ({tx['description']})")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    print("🚀 Iniciando pruebas del sistema de transacciones...")
    
    # Crear transacciones de prueba
    create_test_transactions()
    
    # Probar endpoints
    test_api_endpoints()
    
    print("\n✅ Pruebas completadas!")