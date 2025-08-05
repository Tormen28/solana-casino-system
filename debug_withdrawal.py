#!/usr/bin/env python3
"""
Script de debug para el sistema de retiros
"""

import requests
import json

BASE_URL = "http://localhost:5000"
TEST_WALLET = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"

def debug_withdrawal():
    print("=== DEBUG SISTEMA DE RETIROS ===")
    
    # 1. Crear/actualizar perfil con fichas
    print("\n1. Actualizando perfil de usuario...")
    profile_data = {
        "wallet_address": TEST_WALLET,
        "username": "test_user",
        "chips": 5000
    }
    
    profile_response = requests.post(
        f"{BASE_URL}/api/user/profile",
        json=profile_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Respuesta perfil: {profile_response.status_code}")
    if profile_response.status_code == 200:
        print(f"Datos: {profile_response.json()}")
    else:
        print(f"Error: {profile_response.text}")
    
    # 2. Verificar perfil
    print("\n2. Verificando perfil...")
    get_profile_response = requests.get(f"{BASE_URL}/api/user/profile/{TEST_WALLET}")
    print(f"Respuesta get perfil: {get_profile_response.status_code}")
    if get_profile_response.status_code == 200:
        profile_data = get_profile_response.json()
        print(f"Fichas disponibles: {profile_data.get('chips', 0)}")
    
    # 3. Intentar retiro
    print("\n3. Intentando retiro...")
    withdrawal_data = {
        "wallet_address": TEST_WALLET,
        "chip_amount": 1000,
        "destination_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    }
    
    print(f"Datos de retiro: {json.dumps(withdrawal_data, indent=2)}")
    
    withdrawal_response = requests.post(
        f"{BASE_URL}/api/withdraw/request",
        json=withdrawal_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Respuesta retiro: {withdrawal_response.status_code}")
    print(f"Contenido: {withdrawal_response.text}")
    
    if withdrawal_response.status_code == 200:
        data = withdrawal_response.json()
        print(f"\n✅ Retiro exitoso:")
        print(f"  - Fichas retiradas: {data.get('chip_amount')}")
        print(f"  - SOL bruto: {data.get('sol_amount')}")
        print(f"  - Comisión: {data.get('fee_amount')}")
        print(f"  - SOL neto: {data.get('net_amount')}")
        print(f"  - Nuevo balance: {data.get('new_chip_balance')}")
    else:
        print(f"\n❌ Error en retiro: {withdrawal_response.text}")

if __name__ == "__main__":
    debug_withdrawal()