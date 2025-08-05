#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Completo del Sistema de Depósitos Automáticos
Configura ngrok y proporciona instrucciones finales
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime
from dotenv import load_dotenv, set_key

# Cargar variables de entorno
load_dotenv()

class SetupCompleto:
    def __init__(self):
        self.env_file = '.env'
        
    def verificar_ngrok_instalado(self):
        """Verifica si ngrok está instalado"""
        try:
            result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
            
    def iniciar_ngrok(self):
        """Inicia ngrok en segundo plano"""
        print("🚀 Iniciando túnel ngrok...")
        
        try:
            # Verificar si ya hay un túnel activo
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=3)
                if response.status_code == 200:
                    tunnels = response.json().get('tunnels', [])
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'https' and '5000' in tunnel.get('config', {}).get('addr', ''):
                            print(f"✅ Túnel ngrok ya activo: {tunnel['public_url']}")
                            return tunnel['public_url']
            except:
                pass
                
            # Iniciar ngrok
            print("⏳ Iniciando nuevo túnel ngrok...")
            process = subprocess.Popen(
                ['ngrok', 'http', '5000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Esperar a que ngrok se inicie
            print("⏳ Esperando que ngrok se inicie...")
            for i in range(10):
                time.sleep(2)
                try:
                    response = requests.get('http://localhost:4040/api/tunnels', timeout=3)
                    if response.status_code == 200:
                        tunnels = response.json().get('tunnels', [])
                        for tunnel in tunnels:
                            if tunnel.get('proto') == 'https':
                                print(f"✅ Túnel ngrok creado: {tunnel['public_url']}")
                                return tunnel['public_url']
                except:
                    continue
                    
            print("❌ No se pudo obtener la URL de ngrok")
            return None
            
        except Exception as e:
            print(f"❌ Error iniciando ngrok: {e}")
            return None
            
    def configurar_webhook_automatico(self, ngrok_url):
        """Configura el webhook automáticamente"""
        if not ngrok_url:
            return False
            
        webhook_url = ngrok_url + '/api/webhook/helius'
        
        # Actualizar .env
        set_key(self.env_file, 'WEBHOOK_URL', webhook_url)
        print(f"✅ WEBHOOK_URL actualizada: {webhook_url}")
        
        # Configurar en Helius
        try:
            webhook_data = {'webhook_url': webhook_url}
            response = requests.post(
                'http://localhost:5000/api/webhook/setup',
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Webhook configurado en Helius")
                return True
            else:
                print(f"❌ Error configurando webhook en Helius: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error configurando webhook: {e}")
            return False
            
    def verificar_servidor_flask(self):
        """Verifica si Flask está ejecutándose"""
        try:
            response = requests.get('http://localhost:5000/api/webhook/status', timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def mostrar_estado_final(self):
        """Muestra el estado final del sistema"""
        print("\n" + "=" * 60)
        print("📊 ESTADO FINAL DEL SISTEMA")
        print("=" * 60)
        
        # Verificar componentes
        helius_key = os.getenv('HELIUS_API_KEY')
        custodial_address = os.getenv('CUSTODIAL_ADDRESS')
        custodial_key = os.getenv('CUSTODIAL_PRIVATE_KEY')
        webhook_url = os.getenv('WEBHOOK_URL')
        
        componentes = {
            'Helius API Key': helius_key and helius_key != 'your_helius_api_key_here',
            'Dirección Custodial': bool(custodial_address),
            'Clave Privada Custodial': custodial_key and custodial_key != 'YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE',
            'Webhook URL': webhook_url and webhook_url != 'https://tu-dominio.com/webhook',
            'Servidor Flask': self.verificar_servidor_flask()
        }
        
        for componente, estado in componentes.items():
            status = "✅" if estado else "❌"
            print(f"{status} {componente}")
            
        # Calcular completitud
        configurados = sum(componentes.values())
        total = len(componentes)
        porcentaje = (configurados / total) * 100
        
        print(f"\n📈 Configuración completa: {porcentaje:.0f}% ({configurados}/{total})")
        
        return componentes, porcentaje
        
    def mostrar_instrucciones_finales(self, componentes):
        """Muestra las instrucciones finales"""
        print("\n" + "=" * 60)
        print("📋 INSTRUCCIONES FINALES")
        print("=" * 60)
        
        if not componentes['Clave Privada Custodial']:
            print("\n🔐 PASO CRÍTICO: Configurar Clave Privada")
            print("1. Abrir el archivo .env")
            print("2. Buscar: CUSTODIAL_PRIVATE_KEY=YOUR_CUSTODIAL_PRIVATE_KEY_BASE58_HERE")
            print("3. Reemplazar con la clave privada real de la wallet:")
            print(f"   {os.getenv('CUSTODIAL_ADDRESS')}")
            print("4. Guardar el archivo")
            print("\n⚠️ SIN ESTA CLAVE, EL SISTEMA NO PUEDE PROCESAR RETIROS")
            
        if componentes['Webhook URL'] and componentes['Servidor Flask']:
            print("\n🎉 ¡SISTEMA LISTO PARA DEPÓSITOS AUTOMÁTICOS!")
            print("\n📝 CÓMO PROBAR:")
            print("1. Enviar una pequeña cantidad de SOL (ej: 0.001) a:")
            print(f"   {os.getenv('CUSTODIAL_ADDRESS')}")
            print("2. El sistema debería procesar automáticamente en ~30 segundos")
            print("3. Verificar en la aplicación que se agregaron los chips")
            
        print("\n🔧 COMANDOS ÚTILES:")
        print("• Ver estado del webhook: curl http://localhost:5000/api/webhook/status")
        print("• Procesar depósito manual: python process_deposit.py")
        print("• Ver logs del servidor: revisar terminal donde corre 'python app.py'")
        
        print("\n📁 ARCHIVOS IMPORTANTES:")
        print("• .env - Configuración del sistema")
        print("• app.py - Servidor principal")
        print("• process_deposit.py - Procesamiento manual")
        print("• configuracion_reporte.json - Último reporte de estado")
        
    def ejecutar_setup_completo(self):
        """Ejecuta el setup completo del sistema"""
        print("🛠️ SETUP COMPLETO DEL SISTEMA DE DEPÓSITOS")
        print("=" * 60)
        print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Verificar Flask
        if not self.verificar_servidor_flask():
            print("❌ Servidor Flask no está ejecutándose")
            print("💡 Ejecuta 'python app.py' en otra terminal primero")
            return
            
        print("✅ Servidor Flask está ejecutándose")
        
        # Verificar e instalar ngrok si es necesario
        if not self.verificar_ngrok_instalado():
            print("❌ ngrok no está instalado")
            print("📥 Descarga desde: https://ngrok.com/download")
            print("💡 Después de instalar, ejecuta este script nuevamente")
            return
            
        print("✅ ngrok está instalado")
        
        # Iniciar ngrok
        ngrok_url = self.iniciar_ngrok()
        
        if ngrok_url:
            # Configurar webhook
            webhook_configurado = self.configurar_webhook_automatico(ngrok_url)
            
            if webhook_configurado:
                print("\n🎉 ¡CONFIGURACIÓN AUTOMÁTICA COMPLETADA!")
            else:
                print("\n⚠️ Configuración parcial completada")
        else:
            print("\n❌ No se pudo configurar ngrok automáticamente")
            
        # Mostrar estado final
        componentes, porcentaje = self.mostrar_estado_final()
        
        # Mostrar instrucciones finales
        self.mostrar_instrucciones_finales(componentes)
        
        # Guardar reporte final
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'setup_completo': True,
            'porcentaje_completitud': porcentaje,
            'componentes': componentes,
            'ngrok_url': ngrok_url,
            'webhook_configurado': ngrok_url is not None
        }
        
        with open('setup_final_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
            
        print(f"\n💾 Reporte final guardado en: setup_final_reporte.json")
        
if __name__ == '__main__':
    setup = SetupCompleto()
    setup.ejecutar_setup_completo()