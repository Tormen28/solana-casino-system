#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el Sistema de Depósitos
Verifica todos los endpoints y funcionalidades del sistema de depósitos
"""

import requests
import json
import time
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
TEST_WALLET = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Wallet de prueba
CUSTODIAL_ADDRESS = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"  # Dirección custodial de ejemplo

def print_separator(title):
    """Imprime un separador visual"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_get_deposit_address():
    """Prueba el endpoint para obtener la dirección de depósito"""
    print_separator("1. PROBANDO OBTENER DIRECCIÓN DE DEPÓSITO")
    
    try:
        url = f"{BASE_URL}/api/deposit/address/{TEST_WALLET}"
        response = requests.get(url)
        
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            print(f"  - Dirección de depósito: {data.get('deposit_address')}")
            print(f"  - Wallet del usuario: {data.get('user_wallet')}")
            print(f"  - Tasa de conversión: {data.get('conversion_rate')}")
            print(f"  - Depósito mínimo: {data.get('minimum_deposit')}")
            print(f"  - Instrucciones: {data.get('instructions')}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def test_process_deposit():
    """Prueba el endpoint para procesar un depósito"""
    print_separator("2. PROBANDO PROCESAR DEPÓSITO")
    
    try:
        url = f"{BASE_URL}/api/deposit/process"
        
        # Datos de prueba para un depósito
        deposit_data = {
            "wallet_address": TEST_WALLET,
            "sol_amount": 0.01,  # 0.01 SOL = 1000 fichas
            "signature": f"test_signature_{int(time.time())}"  # Signature única
        }
        
        response = requests.post(url, json=deposit_data)
        
        print(f"URL: {url}")
        print(f"Datos enviados: {json.dumps(deposit_data, indent=2)}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Depósito procesado exitosamente:")
            print(f"  - Wallet: {data.get('wallet_address')}")
            print(f"  - SOL depositado: {data.get('sol_deposited')}")
            print(f"  - Fichas agregadas: {data.get('chips_added')}")
            print(f"  - Nuevo balance: {data.get('new_chip_balance')}")
            print(f"  - Signature: {data.get('transaction_signature')}")
            return data.get('transaction_signature')
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return None

def test_deposit_history():
    """Prueba el endpoint para obtener historial de depósitos"""
    print_separator("3. PROBANDO HISTORIAL DE DEPÓSITOS")
    
    try:
        url = f"{BASE_URL}/api/deposit/history/{TEST_WALLET}"
        response = requests.get(url)
        
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            deposits = data.get('deposits', [])
            total = data.get('total', 0)
            
            print(f"✅ Historial obtenido exitosamente:")
            print(f"  - Total de depósitos: {total}")
            
            if deposits:
                print("  - Últimos depósitos:")
                for i, deposit in enumerate(deposits[:3], 1):
                    print(f"    {i}. {deposit.get('description')} - {deposit.get('created_at')}")
            else:
                print("  - No hay depósitos registrados")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def test_duplicate_deposit():
    """Prueba que no se puedan procesar depósitos duplicados"""
    print_separator("4. PROBANDO PROTECCIÓN CONTRA DEPÓSITOS DUPLICADOS")
    
    try:
        url = f"{BASE_URL}/api/deposit/process"
        
        # Usar la misma signature dos veces
        duplicate_signature = f"duplicate_test_{int(time.time())}"
        
        deposit_data = {
            "wallet_address": TEST_WALLET,
            "sol_amount": 0.005,
            "signature": duplicate_signature
        }
        
        # Primer depósito
        print("Enviando primer depósito...")
        response1 = requests.post(url, json=deposit_data)
        print(f"Primer depósito - Status: {response1.status_code}")
        
        # Segundo depósito (duplicado)
        print("Enviando depósito duplicado...")
        response2 = requests.post(url, json=deposit_data)
        print(f"Depósito duplicado - Status: {response2.status_code}")
        
        if response1.status_code == 200 and response2.status_code == 400:
            print("✅ Protección contra duplicados funcionando correctamente")
            return True
        else:
            print(f"❌ Error en protección: Primer depósito: {response1.status_code}, Segundo: {response2.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def test_minimum_deposit():
    """Prueba la validación de depósito mínimo"""
    print_separator("5. PROBANDO VALIDACIÓN DE DEPÓSITO MÍNIMO")
    
    try:
        url = f"{BASE_URL}/api/deposit/process"
        
        # Depósito menor al mínimo (0.0005 SOL < 0.001 SOL)
        deposit_data = {
            "wallet_address": TEST_WALLET,
            "sol_amount": 0.0005,
            "signature": f"min_test_{int(time.time())}"
        }
        
        response = requests.post(url, json=deposit_data)
        
        print(f"Depósito de {deposit_data['sol_amount']} SOL")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Validación de depósito mínimo funcionando correctamente")
            print(f"Error esperado: {response.json().get('error')}")
            return True
        else:
            print(f"❌ Error: Se esperaba status 400, se obtuvo {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def test_user_profile_integration():
    """Prueba la integración con el perfil de usuario"""
    print_separator("6. PROBANDO INTEGRACIÓN CON PERFIL DE USUARIO")
    
    try:
        # Obtener perfil antes del depósito
        profile_url = f"{BASE_URL}/api/user/profile/{TEST_WALLET}"
        response_before = requests.get(profile_url)
        
        if response_before.status_code == 200:
            chips_before = response_before.json().get('chips', 0)
            print(f"Fichas antes del depósito: {chips_before}")
        else:
            chips_before = 0
            print("Usuario nuevo, fichas iniciales: 0")
        
        # Procesar un depósito
        deposit_url = f"{BASE_URL}/api/deposit/process"
        deposit_data = {
            "wallet_address": TEST_WALLET,
            "sol_amount": 0.002,  # 200 fichas
            "signature": f"profile_test_{int(time.time())}"
        }
        
        deposit_response = requests.post(deposit_url, json=deposit_data)
        
        if deposit_response.status_code == 200:
            deposit_result = deposit_response.json()
            chips_added = deposit_result.get('chips_added', 0)
            new_balance_from_deposit = deposit_result.get('new_chip_balance', 0)
            print(f"Fichas agregadas: {chips_added}")
            print(f"Nuevo balance según depósito: {new_balance_from_deposit}")
            
            # Verificar perfil después del depósito
            time.sleep(2)  # Pausa más larga para asegurar sincronización
            response_after = requests.get(profile_url)
            
            if response_after.status_code == 200:
                profile_after = response_after.json()
                chips_after = profile_after.get('chips', 0)
                game_tokens = profile_after.get('game_tokens', 0)
                print(f"Fichas en perfil después del depósito: {chips_after}")
                print(f"Game tokens en perfil: {game_tokens}")
                
                # Verificar tanto chips como game_tokens
                if chips_after == new_balance_from_deposit or game_tokens == new_balance_from_deposit:
                    print("✅ Integración con perfil de usuario funcionando correctamente")
                    return True
                else:
                    print(f"❌ Error: Se esperaba balance {new_balance_from_deposit}, se encontró chips={chips_after}, game_tokens={game_tokens}")
                    print(f"Respuesta completa del perfil: {profile_after}")
                    return False
            else:
                print(f"❌ Error obteniendo perfil después del depósito: {response_after.status_code}")
                print(f"Respuesta: {response_after.text}")
                return False
        else:
            print(f"❌ Error procesando depósito: {deposit_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def main():
    """Función principal que ejecuta todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE DEPÓSITOS")
    print(f"Servidor: {BASE_URL}")
    print(f"Wallet de prueba: {TEST_WALLET}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Lista de pruebas
    tests = [
        ("Obtener dirección de depósito", test_get_deposit_address),
        ("Procesar depósito", test_process_deposit),
        ("Historial de depósitos", test_deposit_history),
        ("Protección contra duplicados", test_duplicate_deposit),
        ("Validación depósito mínimo", test_minimum_deposit),
        ("Integración con perfil", test_user_profile_integration)
    ]
    
    # Ejecutar pruebas
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error ejecutando {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen final
    print_separator("RESUMEN DE PRUEBAS")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 RESULTADO FINAL: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema de depósitos está funcionando correctamente.")
    else:
        print(f"⚠️  {total - passed} pruebas fallaron. Revisar la implementación.")
    
    return passed == total

if __name__ == "__main__":
    main()