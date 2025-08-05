#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Solución Automática para el Sistema de Depósitos
Configura automáticamente todos los componentes necesarios
"""

import os
import sys
import json
import requests
import subprocess
from datetime import datetime
from dotenv import load_dotenv, set_key

# Cargar variables de entorno
load_dotenv()

class SolucionAutomatica:
    def __init__(self):
        self.env_file = '.env'
        self.pasos_completados = []
        self.errores = []
        
    def paso_1_configurar_webhook_url(self):
        """Paso 1: Configurar URL del webhook usando ngrok"""
        print("\n🔗 PASO 1: CONFIGURAR URL DEL WEBHOOK")
        print("=" * 50)
        
        try:
            # Verificar si ngrok está instalado
            result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ ngrok no está instalado")
                print("📥 Descarga ngrok desde: https://ngrok.com/download")
                print("💡 Después de instalar, ejecuta este script nuevamente")
                return False
                
            print("✅ ngrok está instalado")
            
            # Verificar si ya hay un túnel ngrok activo
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'https' and '5000' in tunnel.get('config', {}).get('addr', ''):
                            webhook_url = tunnel['public_url'] + '/api/webhook/helius'
                            print(f"✅ Túnel ngrok activo encontrado: {webhook_url}")
                            
                            # Actualizar .env
                            set_key(self.env_file, 'WEBHOOK_URL', webhook_url)
                            print(f"✅ WEBHOOK_URL actualizada en {self.env_file}")
                            
                            self.pasos_completados.append("Configuración de WEBHOOK_URL")
                            return True
                            
            except requests.exceptions.ConnectionError:
                pass
                
            # Si no hay túnel activo, mostrar instrucciones
            print("⚠️ No se encontró túnel ngrok activo")
            print("\n📋 INSTRUCCIONES PARA CONFIGURAR NGROK:")
            print("1. Abrir una nueva terminal")
            print("2. Ejecutar: ngrok http 5000")
            print("3. Copiar la URL HTTPS que aparece (ej: https://abc123.ngrok.io)")
            print("4. Ejecutar este script nuevamente")
            
            # Opción manual
            print("\n🔧 CONFIGURACIÓN MANUAL:")
            webhook_url = input("Ingresa la URL del webhook (o presiona Enter para omitir): ").strip()
            
            if webhook_url and webhook_url.startswith('https://'):
                if not webhook_url.endswith('/api/webhook/helius'):
                    webhook_url += '/api/webhook/helius'
                    
                set_key(self.env_file, 'WEBHOOK_URL', webhook_url)
                print(f"✅ WEBHOOK_URL configurada: {webhook_url}")
                self.pasos_completados.append("Configuración manual de WEBHOOK_URL")
                return True
            else:
                print("⏭️ Omitiendo configuración de webhook por ahora")
                return False
                
        except Exception as e:
            self.errores.append(f"Error en paso 1: {e}")
            print(f"❌ Error: {e}")
            return False
            
    def paso_2_configurar_clave_privada(self):
        """Paso 2: Configurar clave privada custodial"""
        print("\n🔐 PASO 2: CONFIGURAR CLAVE PRIVADA CUSTODIAL")
        print("=" * 50)
        
        current_key = os.getenv('CUSTODIAL_PRIVATE_KEY')
        if current_key and current_key != 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE':
            print("✅ CUSTODIAL_PRIVATE_KEY ya está configurada")
            self.pasos_completados.append("Clave privada ya configurada")
            return True
            
        print("⚠️ CUSTODIAL_PRIVATE_KEY no está configurada")
        print("\n📋 INSTRUCCIONES:")
        print("1. Esta clave debe corresponder a la dirección custodial:")
        print(f"   {os.getenv('CUSTODIAL_ADDRESS')}")
        print("2. La clave debe estar en formato Base58")
        print("3. ⚠️ NUNCA compartir esta clave con nadie")
        
        print("\n🔧 OPCIONES:")
        print("1. Configurar clave privada manualmente")
        print("2. Omitir por ahora (el sistema funcionará parcialmente)")
        
        opcion = input("Selecciona una opción (1/2): ").strip()
        
        if opcion == '1':
            private_key = input("Ingresa la clave privada Base58: ").strip()
            
            if len(private_key) > 40:  # Validación básica
                set_key(self.env_file, 'CUSTODIAL_PRIVATE_KEY', private_key)
                print("✅ CUSTODIAL_PRIVATE_KEY configurada")
                self.pasos_completados.append("Configuración de clave privada")
                return True
            else:
                print("❌ Clave privada inválida (muy corta)")
                return False
        else:
            print("⏭️ Omitiendo configuración de clave privada")
            print("💡 El sistema podrá recibir depósitos pero no procesar retiros")
            return False
            
    def paso_3_configurar_webhook_helius(self):
        """Paso 3: Configurar webhook en Helius"""
        print("\n⚙️ PASO 3: CONFIGURAR WEBHOOK EN HELIUS")
        print("=" * 50)
        
        webhook_url = os.getenv('WEBHOOK_URL')
        if not webhook_url or webhook_url == 'https://tu-dominio.com/webhook':
            print("❌ WEBHOOK_URL no configurada. Completar Paso 1 primero.")
            return False
            
        try:
            # Verificar que el servidor local esté ejecutándose
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=5)
            if response.status_code != 200:
                print("❌ Servidor Flask no está ejecutándose")
                print("💡 Ejecutar 'python app.py' en otra terminal")
                return False
                
            print("✅ Servidor Flask está ejecutándose")
            
            # Configurar webhook usando la API local
            webhook_data = {
                'webhook_url': webhook_url
            }
            
            response = requests.post(
                'http://localhost:5000/api/webhook/setup',
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Webhook configurado en Helius")
                print(f"   URL: {result.get('webhook_url')}")
                print(f"   Dirección monitoreada: {result.get('monitored_address')}")
                
                self.pasos_completados.append("Configuración de webhook en Helius")
                return True
            else:
                error_data = response.json()
                print(f"❌ Error configurando webhook: {error_data.get('error')}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ No se puede conectar al servidor Flask")
            print("💡 Asegúrate de que 'python app.py' esté ejecutándose")
            return False
        except Exception as e:
            self.errores.append(f"Error en paso 3: {e}")
            print(f"❌ Error: {e}")
            return False
            
    def paso_4_probar_sistema(self):
        """Paso 4: Probar el sistema completo"""
        print("\n🧪 PASO 4: PROBAR EL SISTEMA")
        print("=" * 50)
        
        try:
            # Verificar estado del sistema
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=5)
            if response.status_code == 200:
                status = response.json()
                
                print("📊 ESTADO DEL SISTEMA:")
                print(f"   Webhook configurado: {'✅' if status.get('webhook_configured') else '❌'}")
                print(f"   Helius disponible: {'✅' if status.get('helius_available') else '❌'}")
                print(f"   Dirección custodial: {status.get('custodial_address')}")
                
                if status.get('webhook_configured') and status.get('helius_available'):
                    print("\n🎉 ¡SISTEMA COMPLETAMENTE CONFIGURADO!")
                    print("\n📋 PRÓXIMOS PASOS:")
                    print("1. Enviar una transacción de prueba pequeña (0.001 SOL)")
                    print("2. Verificar que se procese automáticamente")
                    print("3. Revisar los logs del servidor para confirmar")
                    
                    self.pasos_completados.append("Verificación del sistema")
                    return True
                else:
                    print("⚠️ Sistema parcialmente configurado")
                    return False
            else:
                print("❌ No se puede verificar el estado del sistema")
                return False
                
        except Exception as e:
            self.errores.append(f"Error en paso 4: {e}")
            print(f"❌ Error: {e}")
            return False
            
    def generar_reporte_final(self):
        """Genera un reporte final de la configuración"""
        print("\n📊 REPORTE FINAL DE CONFIGURACIÓN")
        print("=" * 50)
        
        print(f"\n✅ PASOS COMPLETADOS ({len(self.pasos_completados)}):")
        for i, paso in enumerate(self.pasos_completados, 1):
            print(f"{i}. {paso}")
            
        if self.errores:
            print(f"\n❌ ERRORES ENCONTRADOS ({len(self.errores)}):")
            for i, error in enumerate(self.errores, 1):
                print(f"{i}. {error}")
                
        # Estado final
        webhook_url = os.getenv('WEBHOOK_URL')
        private_key = os.getenv('CUSTODIAL_PRIVATE_KEY')
        
        configuracion_completa = (
            webhook_url and webhook_url != 'https://tu-dominio.com/webhook' and
            private_key and private_key != 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE'
        )
        
        if configuracion_completa:
            print("\n🎉 ¡CONFIGURACIÓN COMPLETA!")
            print("El sistema está listo para procesar depósitos automáticamente.")
        else:
            print("\n⚠️ CONFIGURACIÓN PARCIAL")
            print("El sistema funcionará con limitaciones.")
            
        # Guardar reporte
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'pasos_completados': self.pasos_completados,
            'errores': self.errores,
            'configuracion_completa': configuracion_completa,
            'webhook_url': webhook_url,
            'tiene_clave_privada': private_key != 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE'
        }
        
        with open('solucion_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Reporte guardado en: solucion_reporte.json")
        
    def ejecutar_solucion_completa(self):
        """Ejecuta la solución completa paso a paso"""
        print("🛠️ SOLUCIÓN AUTOMÁTICA DEL SISTEMA DE DEPÓSITOS")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        print("\n📋 PASOS A EJECUTAR:")
        print("1. Configurar URL del webhook (ngrok)")
        print("2. Configurar clave privada custodial")
        print("3. Configurar webhook en Helius")
        print("4. Probar el sistema completo")
        
        input("\nPresiona Enter para continuar...")
        
        # Ejecutar pasos
        self.paso_1_configurar_webhook_url()
        self.paso_2_configurar_clave_privada()
        self.paso_3_configurar_webhook_helius()
        self.paso_4_probar_sistema()
        
        # Generar reporte final
        self.generar_reporte_final()
        
if __name__ == '__main__':
    solucion = SolucionAutomatica()
    solucion.ejecutar_solucion_completa()