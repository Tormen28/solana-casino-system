#!/usr/bin/env python3
"""
Pruebas del Sistema de Retiros
Verifica la funcionalidad completa del sistema de retiros de SOL
"""

import requests
import json
import time
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
TEST_WALLET = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
TEST_USERNAME = "test_withdrawal_user"

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"PRUEBA: {test_name}")
    print(f"{'='*60}")

def print_result(success, message):
    status = "✅ ÉXITO" if success else "❌ FALLO"
    print(f"{status}: {message}")
    return success

def test_withdrawal_request_validation():
    """Prueba 1: Validación de solicitudes de retiro"""
    print_test_header("Validación de Solicitudes de Retiro")
    
    # Caso 1: Solicitud con datos incompletos
    try:
        incomplete_data = {
            "wallet_address": TEST_WALLET
            # Faltan chip_amount y destination_address
        }
        response = requests.post(
            f"{BASE_URL}/api/withdraw/request",
            json=incomplete_data,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 400:
            return print_result(True, "Rechaza correctamente solicitudes con datos incompletos")
        else:
            return print_result(False, f"Debería rechazar solicitudes con datos incompletos (código: {response.status_code})")
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def test_withdrawal_insufficient_balance():
    """Prueba 2: Retiro con saldo insuficiente"""
    print_test_header("Retiro con Saldo Insuficiente")
    
    try:
        # Intentar retirar más fichas de las disponibles
        withdrawal_data = {
            "wallet_address": TEST_WALLET,
            "chip_amount": 999999,  # Cantidad muy alta
            "destination_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/withdraw/request",
            json=withdrawal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 400:
            data = response.json()
            if "saldo insuficiente" in data.get('error', '').lower():
                return print_result(True, "Rechaza correctamente retiros con saldo insuficiente")
        
        return print_result(False, f"No rechazó retiro con saldo insuficiente (código: {response.status_code})")
        
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def test_withdrawal_minimum_amount():
    """Prueba 3: Validación de cantidad mínima de retiro"""
    print_test_header("Validación de Cantidad Mínima")
    
    try:
        # Intentar retirar menos del mínimo
        withdrawal_data = {
            "wallet_address": TEST_WALLET,
            "chip_amount": 500,  # Menos del mínimo (1000)
            "destination_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/withdraw/request",
            json=withdrawal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 400:
            data = response.json()
            if "mínimo" in data.get('error', '').lower():
                return print_result(True, "Rechaza correctamente retiros por debajo del mínimo")
        
        return print_result(False, f"No rechazó retiro por debajo del mínimo (código: {response.status_code})")
        
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def test_withdrawal_invalid_address():
    """Prueba 4: Validación de dirección de destino"""
    print_test_header("Validación de Dirección de Destino")
    
    try:
        # Intentar retirar a dirección inválida
        withdrawal_data = {
            "wallet_address": TEST_WALLET,
            "chip_amount": 1000,
            "destination_address": "direccion_invalida"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/withdraw/request",
            json=withdrawal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 400:
            data = response.json()
            if "dirección" in data.get('error', '').lower() or "address" in data.get('error', '').lower():
                return print_result(True, "Rechaza correctamente direcciones inválidas")
        
        return print_result(False, f"No rechazó dirección inválida (código: {response.status_code})")
        
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def test_withdrawal_history_endpoint():
    """Prueba 5: Endpoint de historial de retiros"""
    print_test_header("Endpoint de Historial de Retiros")
    
    try:
        response = requests.get(f"{BASE_URL}/api/withdraw/history/{TEST_WALLET}")
        
        if response.status_code == 200:
            data = response.json()
            if 'withdrawals' in data and isinstance(data['withdrawals'], list):
                return print_result(True, f"Endpoint funciona correctamente - {len(data['withdrawals'])} retiros encontrados")
        
        return print_result(False, f"Endpoint no funciona correctamente (código: {response.status_code})")
        
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def test_withdrawal_fee_calculation():
    """Prueba 6: Cálculo de comisiones"""
    print_test_header("Cálculo de Comisiones")
    
    try:
        # Primero obtener el perfil actual
        profile_response = requests.get(f"{BASE_URL}/api/user/profile/{TEST_WALLET}")
        
        # Actualizar perfil de usuario con fichas suficientes
        profile_data = {
            "wallet_address": TEST_WALLET,
            "username": TEST_USERNAME,
            "chips": 10000  # Suficientes fichas para la prueba
        }
        
        update_response = requests.post(
            f"{BASE_URL}/api/user/profile",
            json=profile_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if update_response.status_code != 200:
            return print_result(False, f"No se pudo actualizar el perfil: {update_response.status_code}")
        
        # Esperar un momento para que se procese
        time.sleep(0.5)
        
        # Simular retiro para verificar cálculo de comisiones
        withdrawal_data = {
            "wallet_address": TEST_WALLET,
            "chip_amount": 1000,
            "destination_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/withdraw/request",
            json=withdrawal_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'fee_amount' in data and 'net_amount' in data:
                fee_amount = data['fee_amount']
                net_amount = data['net_amount']
                gross_amount = data['sol_amount']
                
                # Verificar que fee + net = gross
                if abs((fee_amount + net_amount) - gross_amount) < 0.0001:
                    return print_result(True, f"Comisiones calculadas correctamente: {fee_amount:.4f} SOL de comisión")
                else:
                    return print_result(False, "Error en cálculo de comisiones")
        
        return print_result(False, f"No se pudo procesar el retiro (código: {response.status_code})")
        
    except Exception as e:
        return print_result(False, f"Error en la prueba: {e}")

def run_all_tests():
    """Ejecuta todas las pruebas del sistema de retiros"""
    print("\n🧪 INICIANDO PRUEBAS DEL SISTEMA DE RETIROS")
    print(f"Servidor: {BASE_URL}")
    print(f"Wallet de prueba: {TEST_WALLET}")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        test_withdrawal_request_validation,
        test_withdrawal_insufficient_balance,
        test_withdrawal_minimum_amount,
        test_withdrawal_invalid_address,
        test_withdrawal_history_endpoint,
        test_withdrawal_fee_calculation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            time.sleep(0.5)  # Pausa entre pruebas
        except Exception as e:
            print(f"❌ Error ejecutando {test.__name__}: {e}")
            results.append(False)
    
    # Resumen final
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"RESUMEN DE PRUEBAS DEL SISTEMA DE RETIROS")
    print(f"{'='*60}")
    print(f"✅ Pruebas exitosas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")
    print(f"📊 Tasa de éxito: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema de retiros está funcionando correctamente.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores anteriores.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()