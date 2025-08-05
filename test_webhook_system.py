#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el sistema de webhooks automáticos de Helius
Fase 4: Monitoreo y Webhooks Automáticos
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helius_integration import setup_webhook, list_webhooks, delete_webhook
# Importar modelos de base de datos desde app.py
try:
    from app import SessionLocal, UserProfile, UserTransaction
except ImportError:
    print("❌ Error: No se pudo importar los modelos de base de datos desde app.py")
    print("Asegúrate de que el servidor Flask esté disponible")
    sys.exit(1)

def test_webhook_configuration():
    """Prueba la configuración de webhooks"""
    print("\n🧪 === PRUEBA DE CONFIGURACIÓN DE WEBHOOKS ===")
    
    # URL del webhook (debe apuntar a tu servidor)
    webhook_url = os.getenv('WEBHOOK_URL', 'https://tu-servidor.com/api/webhook/helius')
    custodial_address = os.getenv('CUSTODIAL_ADDRESS')
    
    if not custodial_address:
        print("❌ CUSTODIAL_ADDRESS no configurada en .env")
        return False
    
    print(f"📍 Webhook URL: {webhook_url}")
    print(f"📍 Dirección custodial: {custodial_address}")
    
    # Intentar configurar webhook
    success = setup_webhook(webhook_url, [custodial_address])
    
    if success:
        print("✅ Webhook configurado correctamente")
        return True
    else:
        print("❌ Error configurando webhook")
        return False

def test_list_webhooks():
    """Prueba listar webhooks existentes"""
    print("\n🧪 === PRUEBA DE LISTADO DE WEBHOOKS ===")
    
    webhooks = list_webhooks()
    
    if webhooks:
        print(f"📋 Webhooks encontrados: {len(webhooks)}")
        for i, webhook in enumerate(webhooks, 1):
            print(f"  {i}. ID: {webhook.get('webhookID', 'N/A')}")
            print(f"     URL: {webhook.get('webhookURL', 'N/A')}")
            print(f"     Tipo: {webhook.get('webhookType', 'N/A')}")
            print(f"     Direcciones: {len(webhook.get('accountAddresses', []))}")
        return True
    else:
        print("📋 No se encontraron webhooks configurados")
        return False

def test_webhook_endpoint():
    """Prueba el endpoint webhook local"""
    print("\n🧪 === PRUEBA DE ENDPOINT WEBHOOK LOCAL ===")
    
    # URL del servidor local
    local_url = "http://localhost:5000/api/webhook/helius"
    
    # Datos de prueba simulando un webhook de Helius
    test_webhook_data = {
        "type": "enhanced",
        "transactions": [
            {
                "signature": "test_signature_123456789",
                "nativeTransfers": [
                    {
                        "fromUserAccount": "TestWallet123456789",
                        "toUserAccount": os.getenv('CUSTODIAL_ADDRESS', 'TestCustodial'),
                        "amount": 1000000000  # 1 SOL en lamports
                    }
                ]
            }
        ]
    }
    
    try:
        print(f"📡 Enviando webhook de prueba a: {local_url}")
        response = requests.post(
            local_url,
            json=test_webhook_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook procesado correctamente")
            print(f"📊 Resultado: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error en webhook: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor local")
        print("💡 Asegúrate de que el servidor esté ejecutándose (python app.py)")
        return False
    except Exception as e:
        print(f"❌ Error enviando webhook: {e}")
        return False

def test_webhook_status_endpoint():
    """Prueba el endpoint de estado de webhooks"""
    print("\n🧪 === PRUEBA DE ESTADO DE WEBHOOKS ===")
    
    local_url = "http://localhost:5000/api/webhook/status"
    
    try:
        response = requests.get(local_url, timeout=10)
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Estado obtenido correctamente")
            print(f"📊 Estado: {json.dumps(status, indent=2)}")
            return True
        else:
            print(f"❌ Error obteniendo estado: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor local")
        return False
    except Exception as e:
        print(f"❌ Error obteniendo estado: {e}")
        return False

def test_database_integration():
    """Prueba la integración con la base de datos"""
    print("\n🧪 === PRUEBA DE INTEGRACIÓN CON BASE DE DATOS ===")
    
    try:
        db = SessionLocal()
        
        # Verificar conexión
        profile_count = db.query(UserProfile).count()
        transaction_count = db.query(UserTransaction).count()
        
        print(f"📊 Perfiles de usuario: {profile_count}")
        print(f"📊 Transacciones: {transaction_count}")
        
        # Buscar transacciones de depósito recientes
        recent_deposits = db.query(UserTransaction).filter_by(
            transaction_type='deposit'
        ).order_by(UserTransaction.created_at.desc()).limit(5).all()
        
        if recent_deposits:
            print(f"📋 Últimos {len(recent_deposits)} depósitos:")
            for tx in recent_deposits:
                print(f"  - {tx.wallet_address[:8]}... +{tx.amount} fichas ({tx.created_at})")
        else:
            print("📋 No se encontraron depósitos recientes")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def run_all_tests():
    """Ejecuta todas las pruebas del sistema de webhooks"""
    print("🚀 === INICIANDO PRUEBAS DEL SISTEMA DE WEBHOOKS ===")
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Configuración de Webhooks", test_webhook_configuration),
        ("Listado de Webhooks", test_list_webhooks),
        ("Endpoint Webhook Local", test_webhook_endpoint),
        ("Estado de Webhooks", test_webhook_status_endpoint),
        ("Integración Base de Datos", test_database_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 Ejecutando: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASÓ")
            else:
                print(f"❌ {test_name}: FALLÓ")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Pausa entre pruebas
    
    # Resumen final
    print(f"\n{'='*60}")
    print("📊 === RESUMEN DE PRUEBAS ===")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"  {test_name}: {status}")
    
    print(f"\n📈 Resultado final: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El sistema de webhooks está funcionando correctamente.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa la configuración y los logs.")
    
    return passed == total

if __name__ == "__main__":
    # Verificar variables de entorno
    required_vars = ['HELIUS_API_KEY', 'CUSTODIAL_ADDRESS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("💡 Configura estas variables en tu archivo .env")
        sys.exit(1)
    
    # Ejecutar pruebas
    success = run_all_tests()
    sys.exit(0 if success else 1)