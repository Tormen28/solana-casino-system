#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico Completo del Sistema de Depósitos Automáticos
Identifica problemas y propone soluciones específicas
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SistemaDiagnostico:
    def __init__(self):
        self.problemas = []
        self.soluciones = []
        self.estado_actual = {}
        
    def diagnosticar_configuracion(self):
        """Diagnostica la configuración del sistema"""
        print("🔍 DIAGNÓSTICO DE CONFIGURACIÓN")
        print("=" * 50)
        
        # 1. Verificar variables de entorno críticas
        variables_criticas = {
            'HELIUS_API_KEY': os.getenv('HELIUS_API_KEY'),
            'CUSTODIAL_ADDRESS': os.getenv('CUSTODIAL_ADDRESS'),
            'CUSTODIAL_PRIVATE_KEY': os.getenv('CUSTODIAL_PRIVATE_KEY'),
            'WEBHOOK_URL': os.getenv('WEBHOOK_URL'),
            'HELIUS_NETWORK': os.getenv('HELIUS_NETWORK')
        }
        
        for var, valor in variables_criticas.items():
            if not valor or valor in ['YOUR_CUSTODIAL_SOL_ADDRESS_HERE', 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE', 'https://tu-dominio.com/webhook']:
                self.problemas.append(f"❌ {var} no configurada correctamente: {valor}")
                if var == 'WEBHOOK_URL':
                    self.soluciones.append(f"✅ Configurar {var} con la URL pública de tu servidor")
                elif var == 'CUSTODIAL_PRIVATE_KEY':
                    self.soluciones.append(f"✅ Configurar {var} con la clave privada real de la wallet custodial")
                else:
                    self.soluciones.append(f"✅ Configurar {var} con el valor correcto")
            else:
                print(f"✅ {var}: Configurada")
                
        self.estado_actual['configuracion'] = variables_criticas
        
    def diagnosticar_helius_conexion(self):
        """Diagnostica la conexión con Helius"""
        print("\n🌐 DIAGNÓSTICO DE CONEXIÓN HELIUS")
        print("=" * 50)
        
        api_key = os.getenv('HELIUS_API_KEY')
        network = os.getenv('HELIUS_NETWORK', 'devnet')
        
        if not api_key:
            self.problemas.append("❌ HELIUS_API_KEY no configurada")
            self.soluciones.append("✅ Obtener API key de https://helius.xyz y configurarla en .env")
            return
            
        try:
            # Probar conexión con Helius
            url = f"https://api.helius.xyz/v0/addresses/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU/balances?api-key={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Conexión con Helius: OK")
                self.estado_actual['helius_conexion'] = True
            else:
                self.problemas.append(f"❌ Error de conexión Helius: {response.status_code}")
                self.soluciones.append("✅ Verificar API key de Helius y conexión a internet")
                self.estado_actual['helius_conexion'] = False
                
        except Exception as e:
            self.problemas.append(f"❌ Error conectando con Helius: {e}")
            self.soluciones.append("✅ Verificar conexión a internet y API key")
            self.estado_actual['helius_conexion'] = False
            
    def diagnosticar_webhooks(self):
        """Diagnostica el estado de los webhooks"""
        print("\n🔗 DIAGNÓSTICO DE WEBHOOKS")
        print("=" * 50)
        
        webhook_url = os.getenv('WEBHOOK_URL')
        api_key = os.getenv('HELIUS_API_KEY')
        
        if not webhook_url or webhook_url == 'https://tu-dominio.com/webhook':
            self.problemas.append("❌ WEBHOOK_URL no configurada")
            self.soluciones.append("✅ Configurar WEBHOOK_URL con la URL pública de tu servidor")
            self.soluciones.append("✅ Ejemplo: https://tu-dominio.ngrok.io/api/webhook/helius")
            return
            
        if not api_key:
            self.problemas.append("❌ No se puede verificar webhooks sin HELIUS_API_KEY")
            return
            
        try:
            # Listar webhooks existentes
            url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                webhooks = response.json()
                print(f"📋 Webhooks encontrados: {len(webhooks)}")
                
                # Verificar si hay webhook para nuestra dirección custodial
                custodial_address = os.getenv('CUSTODIAL_ADDRESS')
                webhook_activo = False
                
                for webhook in webhooks:
                    if custodial_address in webhook.get('accountAddresses', []):
                        webhook_activo = True
                        print(f"✅ Webhook activo para {custodial_address}")
                        print(f"   URL: {webhook.get('webhookURL')}")
                        print(f"   ID: {webhook.get('webhookID')}")
                        break
                        
                if not webhook_activo:
                    self.problemas.append("❌ No hay webhook configurado para la dirección custodial")
                    self.soluciones.append("✅ Configurar webhook usando el dashboard de administración")
                    self.soluciones.append("✅ Acceder a /webhook-admin en tu aplicación")
                    
                self.estado_actual['webhooks_configurados'] = len(webhooks)
                self.estado_actual['webhook_activo'] = webhook_activo
                
            else:
                self.problemas.append(f"❌ Error listando webhooks: {response.status_code}")
                
        except Exception as e:
            self.problemas.append(f"❌ Error verificando webhooks: {e}")
            
    def diagnosticar_base_datos(self):
        """Diagnostica el estado de la base de datos"""
        print("\n🗄️ DIAGNÓSTICO DE BASE DE DATOS")
        print("=" * 50)
        
        try:
            # Importar modelos desde app.py
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from app import SessionLocal, UserProfile, UserTransaction
            
            db = SessionLocal()
            
            # Verificar tablas
            try:
                profiles_count = db.query(UserProfile).count()
                transactions_count = db.query(UserTransaction).count()
                
                print(f"✅ Perfiles de usuario: {profiles_count}")
                print(f"✅ Transacciones: {transactions_count}")
                
                # Verificar transacción específica del usuario
                user_wallet = 'CR2Z14kNMeaLpfD8HmEL5Z6Nb1vYJXzxWBEQeoBGESLa'
                user_profile = db.query(UserProfile).filter_by(wallet_address=user_wallet).first()
                
                if user_profile:
                    print(f"✅ Perfil del usuario encontrado: {user_profile.chips} fichas")
                    
                    # Verificar transacciones del usuario
                    user_transactions = db.query(UserTransaction).filter_by(wallet_address=user_wallet).all()
                    print(f"✅ Transacciones del usuario: {len(user_transactions)}")
                    
                    for tx in user_transactions[-3:]:  # Últimas 3 transacciones
                        print(f"   - {tx.transaction_type}: {tx.amount} ({tx.status})")
                        
                else:
                    self.problemas.append(f"❌ No se encontró perfil para {user_wallet}")
                    
                self.estado_actual['base_datos'] = {
                    'perfiles': profiles_count,
                    'transacciones': transactions_count,
                    'usuario_encontrado': user_profile is not None
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.problemas.append(f"❌ Error accediendo a la base de datos: {e}")
            self.soluciones.append("✅ Verificar que la aplicación Flask esté ejecutándose")
            
    def diagnosticar_servidor_local(self):
        """Diagnostica el estado del servidor local"""
        print("\n🖥️ DIAGNÓSTICO DEL SERVIDOR LOCAL")
        print("=" * 50)
        
        try:
            # Verificar si el servidor Flask está ejecutándose
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                print("✅ Servidor Flask: Ejecutándose")
                print(f"   Webhook configurado: {status_data.get('webhook_configured')}")
                print(f"   Helius disponible: {status_data.get('helius_available')}")
                print(f"   Dirección custodial: {status_data.get('custodial_address')}")
                
                self.estado_actual['servidor_local'] = True
                self.estado_actual['servidor_status'] = status_data
                
            else:
                self.problemas.append(f"❌ Servidor Flask responde con error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.problemas.append("❌ Servidor Flask no está ejecutándose en localhost:5000")
            self.soluciones.append("✅ Ejecutar 'python app.py' para iniciar el servidor")
            self.estado_actual['servidor_local'] = False
            
        except Exception as e:
            self.problemas.append(f"❌ Error verificando servidor local: {e}")
            
    def generar_plan_solucion(self):
        """Genera un plan de solución paso a paso"""
        print("\n🛠️ PLAN DE SOLUCIÓN PASO A PASO")
        print("=" * 50)
        
        if not self.problemas:
            print("🎉 ¡No se encontraron problemas! El sistema está funcionando correctamente.")
            return
            
        print("\n📋 PROBLEMAS IDENTIFICADOS:")
        for i, problema in enumerate(self.problemas, 1):
            print(f"{i}. {problema}")
            
        print("\n🔧 SOLUCIONES RECOMENDADAS:")
        for i, solucion in enumerate(self.soluciones, 1):
            print(f"{i}. {solucion}")
            
        # Plan específico basado en los problemas encontrados
        print("\n📝 PLAN DE ACCIÓN PRIORITARIO:")
        
        if any('WEBHOOK_URL' in p for p in self.problemas):
            print("\n🔗 PASO 1: Configurar URL del Webhook")
            print("   a) Usar ngrok para exponer tu servidor local:")
            print("      - Instalar ngrok: https://ngrok.com/")
            print("      - Ejecutar: ngrok http 5000")
            print("      - Copiar la URL HTTPS generada")
            print("   b) Actualizar .env con la URL del webhook:")
            print("      WEBHOOK_URL=https://tu-id.ngrok.io/api/webhook/helius")
            
        if any('webhook configurado' in p for p in self.problemas):
            print("\n⚙️ PASO 2: Configurar Webhook en Helius")
            print("   a) Acceder a http://localhost:5000/webhook-admin")
            print("   b) Hacer clic en 'Configurar Webhook'")
            print("   c) Verificar que se configure correctamente")
            
        if any('CUSTODIAL_PRIVATE_KEY' in p for p in self.problemas):
            print("\n🔐 PASO 3: Configurar Clave Privada Custodial")
            print("   a) Obtener la clave privada de tu wallet custodial")
            print("   b) Actualizar CUSTODIAL_PRIVATE_KEY en .env")
            print("   c) ⚠️ NUNCA compartir esta clave privada")
            
        print("\n🧪 PASO 4: Probar el Sistema")
        print("   a) Reiniciar el servidor Flask")
        print("   b) Enviar una transacción de prueba pequeña (0.001 SOL)")
        print("   c) Verificar que se procese automáticamente")
        
    def ejecutar_diagnostico_completo(self):
        """Ejecuta el diagnóstico completo del sistema"""
        print("🚀 DIAGNÓSTICO COMPLETO DEL SISTEMA DE DEPÓSITOS AUTOMÁTICOS")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Ejecutar todos los diagnósticos
        self.diagnosticar_configuracion()
        self.diagnosticar_helius_conexion()
        self.diagnosticar_webhooks()
        self.diagnosticar_base_datos()
        self.diagnosticar_servidor_local()
        
        # Generar plan de solución
        self.generar_plan_solucion()
        
        # Resumen final
        print("\n📊 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 50)
        print(f"Problemas encontrados: {len(self.problemas)}")
        print(f"Soluciones propuestas: {len(self.soluciones)}")
        
        if len(self.problemas) == 0:
            print("\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
        elif len(self.problemas) <= 2:
            print("\n⚠️ Problemas menores - Fácil de solucionar")
        else:
            print("\n🔧 Requiere configuración adicional")
            
        # Guardar reporte
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'problemas': self.problemas,
            'soluciones': self.soluciones,
            'estado_actual': self.estado_actual
        }
        
        with open('diagnostico_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Reporte guardado en: diagnostico_reporte.json")
        
if __name__ == '__main__':
    diagnostico = SistemaDiagnostico()
    diagnostico.ejecutar_diagnostico_completo()